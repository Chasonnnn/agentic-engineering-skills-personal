import json
from pathlib import Path
import subprocess
import sys
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'hooks' / 'git_commit_worktree_guard.py'


def run(command, tool='Bash'):
    payload = json.dumps({'tool_name': tool, 'tool_input': {'command': command}})
    return subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True, text=True)


class GuardTests(unittest.TestCase):
    def test_blocks_a_commit_and_a_removal_in_one_command(self):
        for command in [
            'git commit -m "x" && git worktree remove ../wt',
            'git commit -m "x"\ngit worktree remove --force ../wt',
            'git -C "$WT" commit -q -F msg.txt; git worktree remove --force "$WT"',
            'cd wt && git add -A && git commit -m x; cd .. && git worktree  remove wt',
            'git worktree remove wt && git commit -m "after"',
            'git -c user.name=a commit -m x || true; git -C repo worktree remove wt',
        ]:
            with self.subTest(command=command):
                result = run(command)
                self.assertEqual(result.returncode, 2)
                self.assertIn('Run the commit alone', result.stderr)

    def test_allows_each_command_alone_and_near_names(self):
        for command in [
            'git commit -m "x"',
            'git worktree remove --force ../wt',
            'git commit -m "x" && git worktree list',
            'git commit -m "x" && git worktree prune',
            'git commit-tree abc && git worktree remove wt',
            'git status; git worktree remove wt',
            'commit=$(git rev-parse HEAD); git worktree remove wt',
            'git worktree add ../wt && git commit -m "x"',
        ]:
            with self.subTest(command=command):
                self.assertEqual(run(command).returncode, 0)

    def test_ignores_other_tools_and_bad_input(self):
        self.assertEqual(run('git commit -m x && git worktree remove wt', tool='Write').returncode, 0)
        result = subprocess.run([sys.executable, str(HOOK)], input='not json', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
