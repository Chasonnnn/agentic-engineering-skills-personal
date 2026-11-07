#!/usr/bin/env python3
"""Claude Code PreToolUse hook (matcher Bash).

Blocks a detached Codex launch. A run started with nohup, setsid, disown or a
trailing `&` leaves the harness, so no completion notice arrives.
"""
import json
import re
import sys

CODEX = re.compile(r'codex_run\.py|\bcodex\s+exec\b')
# A lone `&` that is not part of `&&`, `>&`, `&>` or `|&`.
DETACH = re.compile(r'\b(?:nohup|setsid|disown)\b|(?<![&>|])&(?![&>])')
MESSAGE = (
    'Blocked: detached Codex launch. A detached run sends no completion notice. '
    'Call Bash with run_in_background: true and no nohup, setsid, disown or "&". '
    'Prefix the command with "caffeinate -s" on macOS. '
    'Within 60 seconds, read <out>/stderr.txt and <out>/events.jsonl to confirm the run started.'
)


def blocked(command):
    return bool(CODEX.search(command) and DETACH.search(command))


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
