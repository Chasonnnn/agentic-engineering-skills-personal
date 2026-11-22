#!/usr/bin/env python3
"""Claude Code PreToolUse hook (matcher Bash).

Blocks a command that holds both `git commit` and `git worktree remove`. A
pre-commit hook can refuse the commit. The shell then runs the next line, and
the removal deletes the files that were not committed.
"""
import json
import re
import sys

# The subcommand after `git` and its options, within one simple command.
COMMIT = re.compile(r'\bgit\b[^\n;|&]*?\scommit\b(?!-)')
REMOVE = re.compile(r'\bgit\b[^\n;|&]*?\sworktree\s+remove\b')
MESSAGE = (
    'Blocked: this command has both "git commit" and "git worktree remove". '
    'A refused commit does not stop the next line, and the removal then deletes the uncommitted files. '
    'Run the commit alone. Confirm the new sha with "git log -1". Remove the worktree in a later call. '
    'If the two are only text here (a commit message, a file body), write that text with the Write tool '
    'and pass it from a file.'
)


def blocked(command):
    return bool(COMMIT.search(command) and REMOVE.search(command))


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    command = (payload.get('tool_input') or {}).get('command') or ''
    if payload.get('tool_name') == 'Bash' and blocked(command):
        print(MESSAGE, file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
