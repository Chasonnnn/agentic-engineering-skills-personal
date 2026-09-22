#!/usr/bin/env python3
"""Shared Codex CLI capture and review completion checks. Python standard library."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys


def review_result(text):
    """A completed process alone cannot establish a completed review."""
    report = json.loads(text)
    if not isinstance(report, dict) or type(report.get('scope_complete')) is not bool:
        raise ValueError('missing boolean scope_complete')
    for key in ('checks', 'limitations', 'findings'):
        if not isinstance(report.get(key), list):
            raise ValueError(f'missing list: {key}')
    for key in ('checks', 'limitations'):
        if any(not isinstance(v, str) or not v.strip() for v in report[key]):
            raise ValueError(f'invalid {key}')
    for finding in report['findings']:
        if not isinstance(finding, dict) or finding.get('priority') not in ('P0', 'P1', 'P2', 'P3'):
            raise ValueError('invalid finding priority')
        if any(not isinstance(finding.get(k), str) or not finding[k].strip()
               for k in ('title', 'evidence', 'fix')):
            raise ValueError('finding lacks title, evidence, or fix')
    if not report['scope_complete'] or not report['checks'] or report['limitations']:
        return 'INCOMPLETE'
    return 'FAIL' if any(f['priority'] in ('P0', 'P1') for f in report['findings']) else 'PASS'


def collect_events(path):
    completed, failed, malformed, thread_id = False, False, False, None
    error_seen = False
    with path.open(encoding='utf-8', errors='replace') as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                kind = event['type']
                if kind == 'thread.started':
                    thread_id = event.get('thread_id')
                elif kind == 'turn.completed':
                    completed = True
                elif kind == 'turn.failed':
                    failed = True
                elif kind == 'error':
                    # Transient stream notices ("Reconnecting... 2/5") arrive as
                    # top-level errors; they only mean failure if the turn never completes.
                    error_seen = True
            except (ValueError, KeyError, TypeError):
                malformed = True
    return completed, failed or (error_seen and not completed), malformed, thread_id


def run(args):
    prompt = Path(args.prompt).read_text(encoding='utf-8')
    if not prompt.strip():
        raise ValueError('prompt is empty')
    repo = Path(args.repo).resolve(strict=True)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)  # Never accept stale evidence or overwrite a run.
    (out / 'prompt.txt').write_text(prompt, encoding='utf-8')
    final = out / 'final.txt'
    command = ['codex', 'exec']
    if args.resume:
        command += ['resume', args.resume]
    command += ['--json', '--output-last-message', str(final),
                '-c', f'sandbox_mode="{args.sandbox}"',
                '-c', f'model_reasoning_effort="{args.effort}"']
    if args.model:
        command += ['-m', args.model]
    if args.review:
        schema = Path(__file__).resolve().with_name('review.schema.json')
        command += ['--output-schema', str(schema)]
    command += ['-']
    (out / 'command.json').write_text(json.dumps({'cwd': str(repo), 'argv': command}, indent=2) + '\n')
    timed_out, interrupted, error, returncode = False, False, None, None
    process = None
    def interrupt(signum, frame):
        raise KeyboardInterrupt
    previous_handlers = {sig: signal.signal(sig, interrupt) for sig in (signal.SIGTERM, signal.SIGINT)}
    with (out / 'events.jsonl').open('wb') as events, (out / 'stderr.txt').open('wb') as errors:
        try:
            process = subprocess.Popen(command, cwd=repo, stdin=subprocess.PIPE, stdout=events,
                                       stderr=errors, start_new_session=True)
            process.communicate(prompt.encode('utf-8'), timeout=args.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        except KeyboardInterrupt:
            interrupted = True
        except OSError as exc:
            error = str(exc)
        finally:
            for sig, handler in previous_handlers.items():
                signal.signal(sig, handler)
            if process is not None:
                if timed_out or interrupted:
                    # Only this local group; external jobs require separate reconciliation.
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.communicate()
                returncode = process.returncode
    completed, failed, malformed, thread_id = collect_events(out / 'events.jsonl')
    response = final.read_text(encoding='utf-8', errors='replace') if final.exists() else ''
    status = 'completed'
    if error or failed or (returncode not in (0, None) and not (timed_out or interrupted)):
        status = 'failed'
    elif timed_out or interrupted or not completed or malformed or not response.strip():
        status = 'incomplete'
    verdict = None
    if args.review:
        verdict = 'INCOMPLETE'
        if status == 'completed':
            try:
                verdict = review_result(response)
            except (ValueError, TypeError) as exc:
                status, error = 'incomplete', str(exc)
    result = {'status': status, 'review_verdict': verdict, 'returncode': returncode,
              'timed_out': timed_out, 'interrupted': interrupted, 'thread_id': thread_id, 'error': error,
              'final': str(final), 'artifacts': str(out)}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if status == 'completed' and verdict not in ('FAIL', 'INCOMPLETE') else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--prompt', required=True, help='UTF-8 prompt file, read through stdin')
    parser.add_argument('--out', required=True, help='New directory for this run')
    parser.add_argument('--model', help='Omit to retain the configured Codex model')
    parser.add_argument('--effort', default='medium')
    parser.add_argument('--sandbox', choices=('read-only', 'workspace-write'), default='read-only')
    parser.add_argument('--resume', help='Explicit session ID; never selects an unrelated latest session')
    parser.add_argument('--review', action='store_true', help='Require structured review completion and verdict')
    parser.add_argument('--timeout', type=float, default=600, help='Local deadline in seconds; no automatic retry')
    args = parser.parse_args()
    if args.review and args.sandbox != 'read-only':
        parser.error('--review requires --sandbox read-only')
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    try:
        return run(args)
    except (OSError, ValueError) as exc:
        print(json.dumps({'status': 'failed', 'review_verdict': 'INCOMPLETE' if args.review else None,
                          'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
