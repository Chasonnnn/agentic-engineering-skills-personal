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

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'opencode_run.py'
spec = importlib.util.spec_from_file_location('opencode_run', SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
REPORT = {'scope_complete': True, 'checks': ['a.py:1 inspected'], 'limitations': [], 'findings': []}
PROMPT = 'literal $(do-not-run) `do-not-run`\nsecond line'


class RunnerTests(unittest.TestCase):
    def invoke(self, behavior='', review=True, timeout=5, extra=(), answer=None):
        answer = json.dumps(REPORT) if answer is None else answer
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt = root / 'prompt source.txt'
            prompt.write_text(PROMPT)
            fake = root / 'opencode'
            fake.write_text('#!' + sys.executable + '\n' + '''import json, os, sys, time
args = sys.argv[1:]
if args[:2] == ['session', 'list']:
    print(json.dumps([{'id': 'ses_known'}]))
    sys.exit(0)
text = sys.stdin.read()
assert text.startswith(''' + repr(PROMPT) + ''')
assert args[:5] == ['run', '--standalone', '--format', 'json', '--model']
config = json.loads(os.environ['OPENCODE_CONFIG_CONTENT'])
denied = {rule['action'] for rule in config['permissions'] if rule['effect'] == 'deny'}
def emit(kind, **fields):
    print(json.dumps({'type': kind, 'sessionID': 'ses_known', **fields}), flush=True)
answer = ''' + repr(answer) + '''
''' + behavior + '''
emit('step_start', part={'type': 'step-start'})
emit('text', part={'type': 'text', 'text': 'draft before a tool call'})
emit('step_finish', part={'type': 'step-finish', 'cost': 0.5, 'tokens': {'input': 10, 'output': 2, 'reasoning': 1, 'cache': {'read': 3, 'write': 0}}})
emit('step_start', part={'type': 'step-start'})
emit('text', part={'type': 'text', 'text': answer})
''')
            fake.chmod(0o700)
            command = [sys.executable, str(SCRIPT), '--repo', str(root), '--prompt', str(prompt),
                       '--out', str(root / 'run output'), '--timeout', str(timeout), *extra]
            if review:
                command.append('--review')
            result = subprocess.run(command, env={**os.environ, 'PATH': str(root) + os.pathsep + os.environ['PATH']},
                                    capture_output=True, text=True)
            run_dir = root / 'run output'
            if not (run_dir / 'result.json').exists():
                return result.returncode, json.loads(result.stderr), None, None
            record = json.loads((run_dir / 'result.json').read_text())
            sent = json.loads((run_dir / 'command.json').read_text())
            return result.returncode, record, sent, (run_dir / 'final.txt').read_text()

    def test_complete_review_uses_last_step_and_literal_stdin(self):
        code, result, sent, final = self.invoke()
        self.assertEqual((code, result['status'], result['review_verdict']), (0, 'completed', 'PASS'))
        self.assertEqual(json.loads(final), REPORT)
        self.assertEqual(sent['argv'][sent['argv'].index('--model') + 1], runner.DEFAULT_MODEL)
        self.assertEqual((result['session_id'], result['usage']['steps'], result['usage']['input']), ('ses_known', 1, 10))

    def test_read_only_denies_edits_and_commands(self):
        behavior = "assert {'edit', 'write', 'shell', 'execute', 'subagent', 'question'} <= denied\n"
        code, result, _, _ = self.invoke(behavior)
        self.assertEqual((code, result['access']), (0, 'read-only'))

    def test_edit_access_still_denies_commands(self):
        behavior = "assert 'edit' not in denied and 'write' not in denied and {'shell', 'execute'} <= denied\n"
        code, result, _, _ = self.invoke(behavior, review=False, answer='done', extra=('--access', 'edit'))
        self.assertEqual((code, result['status']), (0, 'completed'))

    def test_review_contract_appended_to_prompt(self):
        code, _, _, _ = self.invoke("assert 'JSON Schema' in text and '\"scope_complete\"' in text\n")
        self.assertEqual(code, 0)

    def test_fenced_review_json_accepted(self):
        code, result, _, _ = self.invoke(answer='```json\n' + json.dumps(REPORT) + '\n```')
        self.assertEqual((code, result['review_verdict']), (0, 'PASS'))

    def test_known_session_resumes(self):
        behavior = "assert args[args.index('--session') + 1] == 'ses_known'\n"
        code, result, _, _ = self.invoke(behavior, review=False, answer='done', extra=('--resume', 'ses_known'))
        self.assertEqual((code, result['status']), (0, 'completed'))

    def test_unknown_session_fails_before_running(self):
        code, result, sent, _ = self.invoke("raise SystemExit('must not run')\n", review=False,
                                            extra=('--resume', 'ses_typo'))
        self.assertEqual((code, result['status'], sent), (1, 'failed', None))
        self.assertIn('unknown session', result['error'])

    def test_error_event_fails(self):
        behavior = "emit('error', error={'type': 'provider.auth', 'message': 'bad key'}); sys.exit(1)\n"
        code, result, _, _ = self.invoke(behavior)
        self.assertEqual((code, result['status'], result['error']), (1, 'failed', 'bad key'))

    def test_error_event_with_zero_exit_fails(self):
        behavior = "emit('error', error={'message': 'stream ended'}); sys.exit(0)\n"
        _, result, _, _ = self.invoke(behavior)
        self.assertEqual((result['status'], result['review_verdict']), ('failed', 'INCOMPLETE'))

    def test_producer_failure_cannot_pass(self):
        code, result, _, _ = self.invoke('sys.exit(7)\n')
        self.assertEqual((code, result['status'], result['review_verdict']), (1, 'failed', 'INCOMPLETE'))

    def test_empty_success_is_incomplete(self):
        code, result, _, _ = self.invoke('sys.exit(0)\n')
        self.assertEqual((code, result['status']), (1, 'incomplete'))

    def test_answer_before_last_step_is_not_final(self):
        behavior = "emit('step_start', part={}); emit('text', part={'text': 'partial'}); emit('step_start', part={}); sys.exit(0)\n"
        _, result, _, final = self.invoke(behavior, review=False)
        self.assertEqual((result['status'], final), ('incomplete', ''))

    def test_malformed_stream_cannot_pass(self):
        _, result, _, _ = self.invoke("print('not-json')\n")
        self.assertEqual(result['status'], 'incomplete')

    def test_timeout_is_incomplete(self):
        _, result, _, _ = self.invoke('time.sleep(5)\n', timeout=0.1)
        self.assertTrue(result['timed_out'])
        self.assertEqual(result['review_verdict'], 'INCOMPLETE')

    def test_invalid_review_final_is_incomplete(self):
        _, result, _, _ = self.invoke(answer='looks good')
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

    def test_project_config_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'opencode.json').write_text('{}')
            (root / 'prompt.txt').write_text('question')
            fake = root / 'opencode'
            fake.write_text('#!' + sys.executable + '\nimport json, sys\nsys.stdin.read()\n'
                            "print(json.dumps({'type': 'text', 'sessionID': 's', 'part': {'text': 'ok'}}))\n")
            fake.chmod(0o700)
            subprocess.run([sys.executable, str(SCRIPT), '--repo', str(root), '--prompt', str(root / 'prompt.txt'),
                            '--out', str(root / 'run')], capture_output=True,
                           env={**os.environ, 'PATH': str(root) + os.pathsep + os.environ['PATH']})
            result = json.loads((root / 'run' / 'result.json').read_text())
            self.assertEqual((result['status'], result['project_config']), ('completed', ['opencode.json']))

    def test_interruption_reaps_owned_process(self):
        for sig in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(signal=sig), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                prompt = root / 'prompt.txt'
                prompt.write_text('question')
                fake = root / 'opencode'
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
                                 '--review', '--access', 'full'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)

    def test_existing_output_not_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt = root / 'prompt.txt'
            prompt.write_text('question')
            args = runner.argparse.Namespace(prompt=str(prompt), repo=str(root), out=str(root), resume=None)
            with self.assertRaises(FileExistsError):
                runner.run(args)


if __name__ == '__main__':
    unittest.main()
