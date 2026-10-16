#!/usr/bin/env python3
"""Shared OpenCode CLI capture and review completion checks. Python standard library."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys

# Pinned by the owner: the opencode.json default model failed gateway auth when this skill was written.
DEFAULT_MODEL = 'cornell/nto.gemini-4-argon'
# OpenCode allows writes and shell commands by default, with no sandbox; access is enforced by inline config.
COMMAND_ACTIONS = ('shell', 'bash', 'execute', 'subagent', 'task')
DENIED_ACTIONS = {
    'read-only': ('edit', 'write') + COMMAND_ACTIONS + ('question',),
    'edit': COMMAND_ACTIONS + ('question',),
    'full': ('question',),  # A headless run cannot answer a question.
}
PROJECT_CONFIGS = ('opencode.json', 'opencode.jsonc', '.opencode')


def opencode_bin():
    """The installer adds ~/.opencode/bin through ~/.zshrc, which a shell started earlier has not read."""
    return shutil.which('opencode') or str(Path.home() / '.opencode' / 'bin' / 'opencode')


REVIEW_CONTRACT = ('\n\nReturn only one JSON object that matches this JSON Schema, with no prose and no code fence:\n')


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


def strip_fence(text):
    """OpenCode has no schema enforcement, so tolerate one surrounding code fence."""
    match = re.fullmatch(r'\s*```(?:json)?\s*\n(.*)\n\s*```\s*', text, re.S)
    return match.group(1) if match else text


def collect_events(path):
    """Return the final step's text, errors, the session ID, summed step usage, and malformed state."""
    final_parts, errors, malformed, session_id = [], [], False, None
    usage = {'steps': 0, 'input': 0, 'output': 0, 'reasoning': 0, 'cache_read': 0, 'cache_write': 0, 'cost': 0.0}
    with path.open(encoding='utf-8', errors='replace') as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                kind = event['type']
                session_id = event.get('sessionID') or session_id
                part = event.get('part') or {}
                if kind == 'step_start':
                    final_parts = []  # Only the last step carries the answer.
                elif kind == 'text':
                    final_parts.append(part['text'])
                elif kind == 'error':
                    error = event.get('error')
                    if isinstance(error, dict):
                        errors.append(error.get('message') or json.dumps(error))
                    else:
                        errors.append(str(error))
                elif kind == 'step_finish':
                    tokens = part.get('tokens') or {}
                    cache = tokens.get('cache') or {}
                    usage['steps'] += 1
                    for key in ('input', 'output', 'reasoning'):
                        usage[key] += int(tokens.get(key) or 0)
                    usage['cache_read'] += int(cache.get('read') or 0)
                    usage['cache_write'] += int(cache.get('write') or 0)
                    usage['cost'] += float(part.get('cost') or 0)
            except (ValueError, KeyError, TypeError, AttributeError):
                malformed = True
    return ''.join(final_parts), errors, malformed, session_id, usage


def known_session(repo, session_id, timeout):
    """`--session` creates a missing session, so a mistyped ID would silently lose context."""
    listing = subprocess.run([opencode_bin(), 'session', 'list', '--standalone', '--format', 'json', '-n', '100000'],
                             cwd=repo, capture_output=True, text=True, timeout=timeout)
    if listing.returncode != 0:
        raise ValueError(f'cannot list sessions: {listing.stderr.strip() or listing.returncode}')
    return any(isinstance(s, dict) and s.get('id') == session_id for s in json.loads(listing.stdout))


def run(args):
    prompt = Path(args.prompt).read_text(encoding='utf-8')
    if not prompt.strip():
        raise ValueError('prompt is empty')
    repo = Path(args.repo).resolve(strict=True)
    if args.resume and not known_session(repo, args.resume, min(args.timeout, 120)):
        raise ValueError(f'unknown session for this project: {args.resume}')
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)  # Never accept stale evidence or overwrite a run.
    if args.review:
        schema = Path(__file__).resolve().with_name('review.schema.json').read_text(encoding='utf-8')
        prompt += REVIEW_CONTRACT + schema
    (out / 'prompt.txt').write_text(prompt, encoding='utf-8')
    final = out / 'final.txt'
    # A private server ends with the process group, so a timeout cannot leave a turn running elsewhere.
    command = [opencode_bin(), 'run', '--standalone', '--format', 'json', '--model', args.model]
    if args.agent:
        command += ['--agent', args.agent]
    if args.resume:
        command += ['--session', args.resume]
    config = {'permissions': [{'action': a, 'resource': '*', 'effect': 'deny'} for a in DENIED_ACTIONS[args.access]]}
    project_config = [name for name in PROJECT_CONFIGS if (repo / name).exists()]
    (out / 'command.json').write_text(json.dumps({'cwd': str(repo), 'argv': command,
                                                  'OPENCODE_CONFIG_CONTENT': config}, indent=2) + '\n')
    env = {**os.environ, 'OPENCODE_CONFIG_CONTENT': json.dumps(config)}
    timed_out, interrupted, error, returncode = False, False, None, None
    process = None
    def interrupt(signum, frame):
        raise KeyboardInterrupt
    previous_handlers = {sig: signal.signal(sig, interrupt) for sig in (signal.SIGTERM, signal.SIGINT)}
    with (out / 'events.jsonl').open('wb') as events, (out / 'stderr.txt').open('wb') as errors:
        try:
            process = subprocess.Popen(command, cwd=repo, env=env, stdin=subprocess.PIPE, stdout=events,
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
    response, stream_errors, malformed, session_id, usage = collect_events(out / 'events.jsonl')
    if args.review:
        response = strip_fence(response)
    final.write_text(response, encoding='utf-8')
    if stream_errors and not error:
        error = '; '.join(stream_errors)
    status = 'completed'
    if error or (returncode not in (0, None) and not (timed_out or interrupted)):
        status = 'failed'
    elif timed_out or interrupted or malformed or not response.strip():
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
              'timed_out': timed_out, 'interrupted': interrupted, 'session_id': session_id,
              'model': args.model, 'access': args.access, 'project_config': project_config, 'usage': usage,
              'error': error, 'final': str(final), 'artifacts': str(out)}
    (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))
    return 0 if status == 'completed' and verdict not in ('FAIL', 'INCOMPLETE') else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--prompt', required=True, help='UTF-8 prompt file, sent through stdin')
    parser.add_argument('--out', required=True, help='New directory for this run')
    parser.add_argument('--model', default=DEFAULT_MODEL,
                        help=f'provider/model[#variant] (default {DEFAULT_MODEL}); see `opencode models`')
    parser.add_argument('--agent', help='Omit to retain the configured OpenCode agent')
    parser.add_argument('--access', choices=tuple(DENIED_ACTIONS), default='read-only',
                        help='read-only denies edits and commands; edit allows file edits; full allows edits and commands')
    parser.add_argument('--resume', help='Explicit session ID; never selects an unrelated latest session')
    parser.add_argument('--review', action='store_true', help='Require structured review completion and verdict')
    parser.add_argument('--timeout', type=float, default=900, help='Local deadline in seconds; no automatic retry')
    args = parser.parse_args()
    if args.review and args.access != 'read-only':
        parser.error('--review requires --access read-only')
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    try:
        return run(args)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'failed', 'review_verdict': 'INCOMPLETE' if args.review else None,
                          'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
