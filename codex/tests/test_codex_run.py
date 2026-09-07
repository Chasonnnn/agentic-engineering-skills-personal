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

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'codex_run.py'
spec = importlib.util.spec_from_file_location('codex_run', SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
REPORT = {'scope_complete': True, 'checks': ['a.py:1 inspected'], 'limitations': [], 'findings': []}


class RunnerTests(unittest.TestCase):
    def invoke(self, behavior='', review=True, timeout=5, resume=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt = root / 'prompt source.txt'
            prompt.write_text('literal $(do-not-run) `do-not-run`\nsecond line')
            fake = root / 'codex'
            fake.write_text('#!' + sys.executable + '\n' + '''import json, pathlib, sys, time
args = sys.argv[1:]
assert sys.stdin.read() == 'literal $(do-not-run) `do-not-run`\\nsecond line'
assert '-s' not in args and '-C' not in args
''' + behavior + '''
print(json.dumps({'type':'thread.started','thread_id':'test-session'}), flush=True)
pathlib.Path(args[args.index('--output-last-message')+1]).write_text(''' + repr(json.dumps(REPORT)) + ''')
print(json.dumps({'type':'turn.completed'}), flush=True)
''')
            fake.chmod(0o700)
            command = [sys.executable, str(SCRIPT), '--repo', str(root), '--prompt', str(prompt),
                       '--out', str(root / 'run output'), '--timeout', str(timeout)]
            if review:
                command.append('--review')
            if resume:
                command += ['--resume', 'test-session']
            result = subprocess.run(command, env={**os.environ, 'PATH': str(root) + os.pathsep + os.environ['PATH']},
                                    capture_output=True, text=True)
            record = json.loads((root / 'run output' / 'result.json').read_text())
            return result.returncode, record

    def test_complete_review_and_literal_stdin(self):
        code, result = self.invoke()
        self.assertEqual((code, result['status'], result['review_verdict']), (0, 'completed', 'PASS'))

    def test_resume_uses_supported_configuration_flags(self):
        code, result = self.invoke("assert args[:3] == ['exec', 'resume', 'test-session']\n", review=False, resume=True)
        self.assertEqual((code, result['status']), (0, 'completed'))

    def test_producer_failure_cannot_pass(self):
        code, result = self.invoke('sys.exit(7)\n')
        self.assertEqual((code, result['status'], result['review_verdict']), (1, 'failed', 'INCOMPLETE'))

    def test_empty_success_is_incomplete(self):
        code, result = self.invoke('sys.exit(0)\n')
        self.assertEqual((code, result['status']), (1, 'incomplete'))

    def test_failure_event_overrides_later_completion(self):
        _, result = self.invoke("print(json.dumps({'type':'turn.failed'}))\n")
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['review_verdict'], 'INCOMPLETE')

    def test_malformed_stream_cannot_pass(self):
        _, result = self.invoke("print('not-json')\n")
        self.assertEqual(result['status'], 'incomplete')

    def test_timeout_is_incomplete(self):
        _, result = self.invoke('time.sleep(5)\n', timeout=0.1)
        self.assertTrue(result['timed_out'])
        self.assertEqual(result['review_verdict'], 'INCOMPLETE')

    def test_completion_without_final_is_incomplete(self):
        _, result = self.invoke("print(json.dumps({'type':'turn.completed'})); sys.exit(0)\n")
        self.assertEqual(result['status'], 'incomplete')

    def test_invalid_review_final_is_incomplete(self):
        _, result = self.invoke("pathlib.Path(args[args.index('--output-last-message')+1]).write_text('looks good'); print(json.dumps({'type':'turn.completed'})); sys.exit(0)\n")
        self.assertEqual(result['review_verdict'], 'INCOMPLETE')

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
                fake = root / 'codex'
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
