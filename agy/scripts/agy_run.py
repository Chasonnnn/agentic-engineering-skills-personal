#!/usr/bin/env python3
"""Shared Antigravity CLI (agy) capture and review completion checks. Python standard library."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

# Pinned so a /model change in an interactive agy session cannot turn a Gemini second opinion into another family's.
DEFAULT_MODEL = 'gemini-4-argon-high'
ACCESS_MODES = {'read-only': None, 'accept-edits': 'accept-edits', 'auto': 'auto'}


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
    """Return the terminal result event, the conversation ID, and whether any line was malformed."""
    result, malformed, conversation_id = None, False, None
    with path.open(encoding='utf-8', errors='replace') as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                kind = event['event']
                conversation_id = event.get('conversation_id') or conversation_id
                if kind == 'result':
                    result = event['result']
                    if not isinstance(result, dict):
                        raise TypeError('result is not an object')
                    conversation_id = result.get('conversation_id') or conversation_id
            except (ValueError, KeyError, TypeError):
                malformed = True
    return result, malformed, conversation_id


def final_text(result, review):
    """Prefer the schema-checked object; agy can add tool fields to the raw response text."""
    if review and isinstance(result.get('structured_output'), dict):
        return json.dumps(result['structured_output'], indent=2) + '\n'
    response = result.get('response')
    return response if isinstance(response, str) else ''


def run(args):
    prompt = Path(args.prompt).read_text(encoding='utf-8')
    if not prompt.strip():
        raise ValueError('prompt is empty')
    repo = Path(args.repo).resolve(strict=True)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)  # Never accept stale evidence or overwrite a run.
    (out / 'prompt.txt').write_text(prompt, encoding='utf-8')
    final = out / 'final.txt'
    # One NDJSON message on stdin keeps the prompt out of argv and away from flag parsing.
    message = json.dumps({'event': 'user', 'message': {'role': 'user', 'content': prompt}}) + '\n'
    command = ['agy', '--input-format', 'stream-json', '--output-format', 'stream-json',
               '--disable-slash-commands', '--model', args.model]
    if ACCESS_MODES[args.access]:  # Headless default mode auto-denies file writes and commands.
        command += ['--mode', ACCESS_MODES[args.access]]
    if args.effort:  # Omit to retain the effort encoded in the model name.
        command += ['--effort', args.effort]
    if args.resume:
        command += ['--conversation', args.resume]
    if args.review:
        command += ['--json-schema', str(Path(__file__).resolve().with_name('review.schema.json'))]
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
            process.communicate(message.encode('utf-8'), timeout=args.timeout)
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
    result, malformed, conversation_id = collect_events(out / 'events.jsonl')
    response = final_text(result, args.review) if result else ''
    final.write_text(response, encoding='utf-8')
    denied = (result.get('denied_actions') or []) if result else []
    if result and result.get('status') != 'SUCCESS' and not error:
        error = result.get('error') or f"agy result status {result.get('status')}"
    status = 'completed'
    if error or (returncode not in (0, None) and not (timed_out or interrupted)):
        status = 'failed'
    elif timed_out or interrupted or result is None or malformed or not response.strip():
        status = 'incomplete'
    verdict = None
    if args.review:
        verdict = 'INCOMPLETE'
        if status == 'completed':
            try:
                verdict = review_result(response)
            except (ValueError, TypeError) as exc:
                status, error = 'incomplete', str(exc)
    record = {'status': status, 'review_verdict': verdict, 'returncode': returncode,
              'timed_out': timed_out, 'interrupted': interrupted, 'conversation_id': conversation_id,
              'model': args.model, 'denied_actions': denied, 'usage': result.get('usage') if result else None,
              'error': error, 'final': str(final), 'artifacts': str(out)}
    (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))
    return 0 if status == 'completed' and verdict not in ('FAIL', 'INCOMPLETE') else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--prompt', required=True, help='UTF-8 prompt file, sent through stdin')
    parser.add_argument('--out', required=True, help='New directory for this run')
    parser.add_argument('--model', default=DEFAULT_MODEL, help=f'agy model ID (default {DEFAULT_MODEL}); see `agy models`')
    parser.add_argument('--effort', help='Omit to retain the effort encoded in the model name')
    parser.add_argument('--access', choices=tuple(ACCESS_MODES), default='read-only',
                        help='read-only denies writes and commands; accept-edits allows file edits; auto also allows safe commands')
    parser.add_argument('--resume', help='Explicit conversation ID; never selects an unrelated latest conversation')
    parser.add_argument('--review', action='store_true', help='Require structured review completion and verdict')
    parser.add_argument('--timeout', type=float, default=900, help='Local deadline in seconds; no automatic retry')
    args = parser.parse_args()
    if args.review and args.access != 'read-only':
        parser.error('--review requires --access read-only')
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
