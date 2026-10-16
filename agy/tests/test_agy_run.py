import importlib.util
import json
import os
import signal
import time
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'agy_run.py'
spec = importlib.util.spec_from_file_location('agy_run', SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
REPORT = {'scope_complete': True, 'checks': ['a.py:1 inspected'], 'limitations': [], 'findings': []}
PROMPT = 'literal $(do-not-run) `do-not-run`\nsecond line'


class RunnerTests(unittest.TestCase):
    def invoke(self, behavior='', review=True, timeout=5, extra=()):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt = root / 'prompt source.txt'
            prompt.write_text(PROMPT)
            fake = root / 'agy'
            fake.write_text('#!' + sys.executable + '\n' + '''import json, sys, time
args = sys.argv[1:]
lines = sys.stdin.read().splitlines()
assert len(lines) == 1
assert json.loads(lines[0]) == {'event': 'user', 'message': {'role': 'user', 'content': ''' + repr(PROMPT) + '''}}
assert args[:4] == ['--input-format', 'stream-json', '--output-format', 'stream-json']
assert '-p' not in args and '--print' not in args
result = {'conversation_id': 'test-conversation', 'status': 'SUCCESS', 'response': ''' + repr(json.dumps(REPORT)) + ''',
          'structured_output': ''' + repr(REPORT) + ''', 'usage': {'total_tokens': 10}}
def emit(event):
    print(json.dumps(event), flush=True)
''' + behavior + '''
emit({'event': 'init', 'conversation_id': 'test-conversation', 'init': {}})
emit({'event': 'result', 'result': result})
''')
            fake.chmod(0o700)
            command = [sys.executable, str(SCRIPT), '--repo', str(root), '--prompt', str(prompt),
                       '--out', str(root / 'run output'), '--timeout', str(timeout), *extra]
            if review:
                command.append('--review')
            result = subprocess.run(command, env={**os.environ, 'PATH': str(root) + os.pathsep + os.environ['PATH']},
                                    capture_output=True, text=True)
            record = json.loads((root / 'run output' / 'result.json').read_text())
            argv = json.loads((root / 'run output' / 'command.json').read_text())['argv']
            return result.returncode, record, argv

    def test_complete_review_and_literal_stdin(self):
        code, result, argv = self.invoke()
        self.assertEqual((code, result['status'], result['review_verdict']), (0, 'completed', 'PASS'))
        self.assertEqual(result['conversation_id'], 'test-conversation')
        self.assertEqual(argv[argv.index('--model') + 1], runner.DEFAULT_MODEL)
        self.assertNotIn('--effort', argv)
        self.assertNotIn('--mode', argv)

    def test_structured_output_preferred_over_decorated_response(self):
        behavior = "result['response'] = 'not json'\n"
        code, result, _ = self.invoke(behavior)
        self.assertEqual((code, result['review_verdict']), (0, 'PASS'))

    def test_resume_and_overrides_use_supported_flags(self):
        behavior = ("assert args[args.index('--conversation') + 1] == 'test-conversation'\n"
                    "assert args[args.index('--model') + 1] == 'gemini-3.8-flash-high'\n"
                    "assert args[args.index('--mode') + 1] == 'accept-edits'\n")
        code, result, _ = self.invoke(behavior, review=False, extra=(
            '--resume', 'test-conversation', '--model', 'gemini-3.8-flash-high', '--access', 'accept-edits'))
        self.assertEqual((code, result['status']), (0, 'completed'))

    def test_producer_failure_cannot_pass(self):
        code, result, _ = self.invoke('sys.exit(7)\n')
        self.assertEqual((code, result['status'], result['review_verdict']), (1, 'failed', 'INCOMPLETE'))

    def test_error_result_fails(self):
        behavior = ("emit({'event': 'result', 'result': {'status': 'ERROR', 'error': 'bad model', 'response': ''}})\n"
                    "sys.exit(0)\n")
        code, result, _ = self.invoke(behavior)
        self.assertEqual((code, result['status'], result['error']), (1, 'failed', 'bad model'))

    def test_empty_success_is_incomplete(self):
        code, result, _ = self.invoke('sys.exit(0)\n')
        self.assertEqual((code, result['status']), (1, 'incomplete'))

    def test_denied_actions_without_answer_are_incomplete_and_recorded(self):
        behavior = ("result.update(response='', structured_output=None,"
                    " denied_actions=[{'action': 'write_file', 'display_name': 'WriteToFile'}])\n")
        code, result, _ = self.invoke(behavior, review=False)
        self.assertEqual((code, result['status']), (1, 'incomplete'))
        self.assertEqual(result['denied_actions'][0]['action'], 'write_file')

    def test_malformed_stream_cannot_pass(self):
        _, result, _ = self.invoke("print('not-json')\n")
        self.assertEqual(result['status'], 'incomplete')

    def test_timeout_is_incomplete(self):
        _, result, _ = self.invoke('time.sleep(5)\n', timeout=0.1)
        self.assertTrue(result['timed_out'])
        self.assertEqual(result['review_verdict'], 'INCOMPLETE')

    def test_invalid_review_final_is_incomplete(self):
        behavior = "result.update(response='looks good', structured_output=None)\n"
        _, result, _ = self.invoke(behavior)
        self.assertEqual((result['status'], result['review_verdict']), ('incomplete', 'INCOMPLETE'))

    def test_partial_coverage_and_limits_cannot_pass(self):
        for change in ({'scope_complete': False}, {'checks': []}, {'limitations': ['not reviewed b.py']}):
            self.assertEqual(runner.review_result(json.dumps(REPORT | change)), 'INCOMPLETE')

    def test_priorities_and_evidence(self):
        for priority, verdict in [('P0', 'FAIL'), ('P1', 'FAIL'), ('P2', 'PASS'), ('P3', 'PASS')]:
            finding = {'priority': priority, 'title': 'defect', 'evidence': 'a.py:1', 'fix': 'correct value'}
            self.assertEqual(runner.review_result(json.dumps(REPORT | {'findings': [finding]})), verdict)
        with self.assertRaises(ValueError):
            runner.review_result(json.dumps(REPORT | {'findings': [{'priority': 'P1'}]}))

    def test_interruption_reaps_owned_process(self):
        for sig in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(signal=sig), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                prompt = root / 'prompt.txt'
                prompt.write_text('question')
                fake = root / 'agy'
                fake.write_text('#!' + sys.executable + '\nimport os, pathlib, time\n'
                                + "pathlib.Path('pid').write_text(str(os.getpid()))\ntime.sleep(30)\n")
                fake.chmod(0o700)
                process = subprocess.Popen([sys.executable, str(SCRIPT), '--repo', str(root),
                                            '--prompt', str(prompt), '--out', str(root / 'run'), '--review'],
                                           env={**os.environ, 'PATH': str(root) + os.pathsep + os.environ['PATH']},
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                child = None
                try:
                    deadline = time.monotonic() + 5
                    while not (root / 'pid').exists() and time.monotonic() < deadline:
                        time.sleep(0.02)
                    child = int((root / 'pid').read_text())
                    process.send_signal(sig)
                    process.communicate(timeout=5)
                    result = json.loads((root / 'run' / 'result.json').read_text())
                    self.assertEqual((result['status'], result['review_verdict']), ('incomplete', 'INCOMPLETE'))
                    self.assertTrue(result['interrupted'])
                    with self.assertRaises(ProcessLookupError):
                        os.kill(child, 0)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.communicate()
                    if child:
                        try: os.kill(child, signal.SIGKILL)
                        except ProcessLookupError: pass

    def test_review_requires_read_only(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--repo', '.', '--prompt', 'p', '--out', 'o',
                                 '--review', '--access', 'auto'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)

    def test_existing_output_not_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt = root / 'prompt.txt'
            prompt.write_text('question')
            args = runner.argparse.Namespace(prompt=str(prompt), repo=str(root), out=str(root))
            with self.assertRaises(FileExistsError):
                runner.run(args)


if __name__ == '__main__':
    unittest.main()
