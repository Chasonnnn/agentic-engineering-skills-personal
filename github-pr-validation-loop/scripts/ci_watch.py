#!/usr/bin/env python3
"""Poll GitHub Actions branch runs until the selected head SHA is done."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from typing import Any


RUN_FIELDS = [
    "databaseId",
    "workflowName",
    "status",
    "conclusion",
    "headSha",
    "displayTitle",
    "url",
    "createdAt",
]

SUCCESS_CONCLUSIONS = {"success", "skipped", "neutral"}
FAILURE_CONCLUSIONS = {"failure", "cancelled", "timed_out", "action_required"}


def run_command(command: list[str]) -> str:
    result = subprocess.run(command, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"command failed: {' '.join(command)}")
    return result.stdout


def current_branch() -> str:
    return run_command(["git", "branch", "--show-current"]).strip()


def head_sha() -> str:
    return run_command(["git", "rev-parse", "HEAD"]).strip()


def fetch_runs(branch: str, repo: str | None, limit: int) -> list[dict[str, Any]]:
    command = [
        "gh",
        "run",
        "list",
        "--branch",
        branch,
        "--limit",
        str(limit),
        "--json",
        ",".join(RUN_FIELDS),
    ]
    if repo:
        command.extend(["--repo", repo])
    return json.loads(run_command(command) or "[]")


def summarize(runs: list[dict[str, Any]]) -> str:
    lines = []
    for run in runs:
        state = run.get("conclusion") or run.get("status")
        lines.append(f"{run.get('workflowName')} [{state}] {run.get('url')}")
    return "\n".join(lines)


def select_runs(runs: list[dict[str, Any]], sha: str | None) -> list[dict[str, Any]]:
    if sha:
        return [run for run in runs if run.get("headSha", "").startswith(sha)]
    if not runs:
        return []
    latest_sha = runs[0].get("headSha")
    return [run for run in runs if run.get("headSha") == latest_sha]


def terminal_state(runs: list[dict[str, Any]]) -> tuple[bool, int]:
    if not runs:
        return False, 2
    conclusions = [run.get("conclusion") for run in runs]
    statuses = [run.get("status") for run in runs]
    if any(status != "completed" for status in statuses):
        return False, 2
    if any(conclusion in FAILURE_CONCLUSIONS for conclusion in conclusions):
        return True, 1
    if all(conclusion in SUCCESS_CONCLUSIONS for conclusion in conclusions):
        return True, 0
    return True, 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="GitHub repository in owner/name form.")
    parser.add_argument("--branch", default=None, help="Branch to watch. Defaults to current branch.")
    parser.add_argument("--head-sha", default=None, help="Head SHA prefix to watch. Defaults to current HEAD.")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()

    branch = args.branch or current_branch()
    sha = args.head_sha if args.head_sha is not None else head_sha()
    deadline = time.monotonic() + args.timeout

    while True:
        try:
            selected = select_runs(fetch_runs(branch, args.repo, args.limit), sha)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1

        if selected:
            print(summarize(selected), flush=True)
            done, exit_code = terminal_state(selected)
            if done:
                return exit_code
        else:
            print(f"No runs found yet for branch={branch} head_sha={sha or '<latest>'}", flush=True)

        if time.monotonic() >= deadline:
            print("Timed out waiting for GitHub Actions runs.", file=sys.stderr)
            return 2
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
