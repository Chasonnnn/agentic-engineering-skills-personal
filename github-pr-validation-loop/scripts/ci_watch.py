#!/usr/bin/env python3
"""Wait for explicit GitHub Actions workflows on an exact commit and event."""
import argparse
import json
import math
import re
import subprocess
import sys
import time
from urllib.parse import urlencode
from github_cli import CliError, add_auth_options, gh_json


def git(*args):
    return subprocess.check_output(['git', *args], text=True, stderr=subprocess.PIPE).strip()


def fetch_runs(options, timeout):
    query = urlencode({'head_sha': options.head_sha, 'branch': options.branch,
                       'event': options.event, 'per_page': 100})
    pages = gh_json(['api', '--paginate', '--slurp',
                     f'repos/{options.repo}/actions/runs?{query}'], options, timeout)
    if not isinstance(pages, list) or not pages:
        raise ValueError('missing workflow response pages')
    runs = []
    totals = []
    for page in pages:
        totals.append(page['total_count'])
        runs.extend(page['workflow_runs'])
    # Filtered Actions searches have a 1000-result cap; never infer completeness at it.
    if max(totals) >= 1000 or len({run['id'] for run in runs}) < max(totals):
        raise ValueError('workflow run inventory incomplete or capped')
    return runs


def assess(runs, sha, branch, event, expected):
    latest = {}
    for run in runs:
        if (run.get('head_sha'), run.get('head_branch'), run.get('event')) != (sha, branch, event):
            continue
        workflow = run.get('workflow_id')
        if workflow not in expected:
            continue
        previous = latest.get(workflow)
        rank = (run['id'], run.get('run_attempt', 1))
        if previous is None or rank > (previous['id'], previous.get('run_attempt', 1)):
            latest[workflow] = run
    report = []
    for workflow in sorted(expected):
        run = latest.get(workflow)
        report.append({'workflow_id': workflow, 'state': 'missing' if run is None else
                       (run.get('conclusion') if run.get('status') == 'completed' else run.get('status')),
                       'run_id': run['id'] if run else None,
                       'url': run.get('html_url') if run else None})
    if any(r.get('status') == 'completed' and r.get('conclusion') != 'success' for r in latest.values()):
        return 'failed', report
    if len(latest) == len(expected) and all(r.get('status') == 'completed' and r.get('conclusion') == 'success' for r in latest.values()):
        return 'passed', report
    return 'pending', report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, help='owner/name')
    parser.add_argument('--branch', help='Defaults to current local branch')
    parser.add_argument('--head-sha', help='Full commit SHA; defaults to local HEAD')
    parser.add_argument('--workflow-id', action='append', type=int, required=True,
                        help='Required workflow ID; repeat for the complete expected set')
    parser.add_argument('--event', default='push', help='Expected trigger event; default push')
    parser.add_argument('--interval', type=float, default=30)
    parser.add_argument('--timeout', type=float, default=1800)
    add_auth_options(parser)
    options = parser.parse_args()
    try:
        options.branch = options.branch or git('branch', '--show-current')
        options.head_sha = options.head_sha or git('rev-parse', 'HEAD')
        if not re.fullmatch(r'[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', options.head_sha):
            raise ValueError('a full commit SHA is required')
        options.head_sha = options.head_sha.lower()
        if (not options.branch or not all(math.isfinite(v) for v in (options.interval, options.timeout))
                or min(options.interval, options.timeout, *options.workflow_id) <= 0):
            raise ValueError('branch, positive workflow IDs, interval and timeout are required')
        deadline = time.monotonic() + options.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                print(json.dumps({'status': 'incomplete', 'reason': 'deadline exceeded'}))
                return 2
            runs = fetch_runs(options, min(60, remaining))
            state, workflows = assess(runs, options.head_sha, options.branch, options.event, set(options.workflow_id))
            print(json.dumps({'status': state, 'head_sha': options.head_sha, 'event': options.event,
                              'workflows': workflows}), flush=True)
            if state != 'pending':
                return 0 if state == 'passed' else 1
            time.sleep(max(0, min(options.interval, deadline - time.monotonic())))
    except CliError as exc:
        print(str(exc), file=sys.stderr)
        if exc.returncode == 10:
            print('Stopped leaf argv: ' + json.dumps(exc.command), file=sys.stderr)
            return 10
        return 2
    except (OSError, subprocess.SubprocessError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'incomplete', 'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
