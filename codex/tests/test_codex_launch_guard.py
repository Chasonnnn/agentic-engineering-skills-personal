import json
from pathlib import Path
import subprocess
import sys
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'hooks' / 'codex_launch_guard.py'


def run(command, tool='Bash', background=None):
    tool_input = {'command': command}
    if background is not None:
        tool_input['run_in_background'] = background
    payload = json.dumps({'tool_name': tool, 'tool_input': tool_input})
    return subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True, text=True)


class GuardTests(unittest.TestCase):
    def test_blocks_detached_launches(self):
        for command in [
            'nohup caffeinate -i -s python3 codex_run.py --out /tmp/r > log 2>&1 &',
            'python codex_run.py --out r &',
            'python codex_run.py --out r & echo $!',
            'setsid python codex_run.py --out r',
            'python codex_run.py --out r & disown',
            'nohup codex exec - < prompt.txt > out.jsonl &',
        ]:
            with self.subTest(command=command):
                result = run(command)
                self.assertEqual(result.returncode, 2)
                self.assertIn('run_in_background: true', result.stderr)

    def test_blocks_detach_even_with_background_flag(self):
        self.assertEqual(run('nohup python codex_run.py --out r &', background=True).returncode, 2)

    def test_allows_tracked_and_unrelated_commands(self):
        for command, background in [
            ('caffeinate -s python codex_run.py --out r 2>&1 | tail -5', True),
            ('python codex_run.py --out r && cat r/result.json', None),
            ('python codex_run.py --out r >/dev/null 2>&1', None),
            ('python codex_run.py --out r &> log', None),
            ('nohup make test &', None),
            ('grep -n codex_run.py README.md', None),
        ]:
            with self.subTest(command=command):
                self.assertEqual(run(command, background=background).returncode, 0)

    def test_ignores_other_tools_and_bad_input(self):
        self.assertEqual(run('nohup python codex_run.py &', tool='Write').returncode, 0)
        result = subprocess.run([sys.executable, str(HOOK)], input='not json', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
