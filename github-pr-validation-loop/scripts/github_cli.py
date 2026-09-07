"""Run gh directly or through an explicitly selected authmux context."""
import json
import subprocess


class CliError(RuntimeError):
    def __init__(self, returncode, stderr, command):
        self.returncode = returncode
        self.stderr = stderr
        self.command = command
        super().__init__(stderr.strip() or f'CLI exited {returncode}')


def add_auth_options(parser):
    parser.add_argument('--authmux', action='store_true', help='Run gh through authmux exec')
    parser.add_argument('--context', help='Explicit authorized authmux context for an unbound repository')


def gh_json(args, options, timeout=60):
    command = ['gh', *args]
    if options.context and not options.authmux:
        raise ValueError('--context requires --authmux')
    if options.authmux:
        prefix = ['authmux', 'exec']
        if options.context:
            prefix += ['--context', options.context]
        command = prefix + ['--'] + command
    result = subprocess.run(command, check=False, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise CliError(result.returncode, result.stderr, command)
    return json.loads(result.stdout)
