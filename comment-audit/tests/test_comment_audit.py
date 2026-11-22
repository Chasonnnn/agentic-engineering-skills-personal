import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'comment_audit.py'
sys.path.insert(0, str(SCRIPT.parent))
import comment_audit  # noqa: E402  (path set above)


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)


class Repo:
    def __init__(self, root):
        self.root = Path(root)
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'test')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True, text=True).stdout.strip()

    def write(self, files):
        for name, content in files.items():
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                (self.root / name).write_bytes(content)
            else:
                (self.root / name).write_text(content)

    def commit(self, files):
        self.write(files)
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'change')
        return self.git('rev-parse', 'HEAD')


PY = '"""Module."""\nURL = "http://x/#frag"  # keeps the fragment\n# The cap is 3 because the vendor rejects more.\nLIMIT = 3\nx = compute()  # noqa: F821\ny = other()\n'
TS = "const sep = 'a//b';\n// vendor endpoint\n/* The parser\n * needs two passes. */\nexport const n = 1;\n"
SH = '#!/bin/sh\n# Retries twice because the mirror drops the first call.\ncurl "$URL"\n'


class LexTests(unittest.TestCase):
    def test_python_separates_comment_docstring_directive_and_string(self):
        found, rows = comment_audit.lex('a.py', PY)
        self.assertEqual([c['kind'] for c in found], ['docstring', 'inline', 'comment', 'directive'])
        self.assertEqual(found[3]['anchor'], 'x = compute()')
        self.assertIn('URL = "http://x/#frag"  ', rows)

    def test_c_style_keeps_slashes_in_a_string_and_joins_a_block(self):
        found, rows = comment_audit.lex('a.ts', TS)
        self.assertEqual([(c['kind'], c['text']) for c in found],
                         [('comment', 'vendor endpoint'), ('block', 'The parser needs two passes.')])
        self.assertEqual([r for r in rows if r], ["const sep = 'a//b';", 'export const n = 1;'])

    def test_c_style_reads_no_comment_in_an_unquoted_url(self):
        found, _ = comment_audit.lex('a.tsx', 'const a = <p>https://example.com/a</p>;\n')
        self.assertEqual(found, [])

    def test_line_languages_keep_the_shebang_and_code(self):
        found, rows = comment_audit.lex('a.sh', SH)
        self.assertEqual([c['text'] for c in found], ['Retries twice because the mirror drops the first call.'])
        self.assertEqual(rows, ['#!/bin/sh', None, 'curl "$URL"'])

    def test_empty_comment_lines_make_no_entry(self):
        found, _ = comment_audit.lex('a.py', '#\nx = 1\n# a\n#\n# b\n')
        self.assertEqual([(c['text'], c['line'], c['end']) for c in found], [('a b', 3, 5)])


class ProveTests(unittest.TestCase):
    def prove(self, before, after, name='a.py'):
        with tempfile.TemporaryDirectory() as root:
            repo = Repo(root)
            repo.commit({name: before})
            repo.write({name: after})
            return run('prove', root)

    def assert_verdict(self, result, code, word):
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertIn(word, result.stdout)

    def test_python_comment_edit_is_proven(self):
        self.assert_verdict(self.prove(PY, PY.replace('the vendor rejects more', 'the vendor rejects four')), 0, 'COMMENT-ONLY')

    def test_a_comment_line_above_a_type_ignore_is_proven(self):
        body = 'x: int = "a"  # type: ignore[assignment]\n'
        self.assert_verdict(self.prove('# The cap.\n' + body, body), 0, 'COMMENT-ONLY')

    def test_other_languages_never_reach_exit_zero(self):
        self.assert_verdict(self.prove(TS, TS.replace('vendor endpoint', 'billing endpoint'), 'a.ts'), 3, 'LEXER-ONLY')
        self.assert_verdict(self.prove(TS, TS.replace('needs two passes', 'needs one pass'), 'a.ts'), 3, 'LEXER-ONLY')
        self.assert_verdict(self.prove(SH, SH.replace('Retries twice', 'Retries once'), 'a.sh'), 3, 'LEXER-ONLY')
        self.assert_verdict(self.prove('const a = 1;\n\n// old note\nconst b = 2;\n', 'const a = 1;\nconst b = 2;\n', 'a.ts'), 3, 'LEXER-ONLY')

    def test_code_edit_fails(self):
        self.assert_verdict(self.prove(PY, PY.replace('LIMIT = 3', 'LIMIT = 4')), 1, 'CODE-CHANGED')
        self.assert_verdict(self.prove(TS, TS.replace('n = 1', 'n = 2'), 'a.ts'), 1, 'CODE-CHANGED')
        self.assert_verdict(self.prove(SH, SH.replace('curl', 'wget'), 'a.sh'), 1, 'CODE-CHANGED')

    def test_string_that_looks_like_a_comment_fails(self):
        self.assert_verdict(self.prove(PY, PY.replace('#frag', '#other')), 1, 'CODE-CHANGED')
        self.assert_verdict(self.prove(TS, TS.replace("'a//b'", "'a//c'"), 'a.ts'), 1, 'CODE-CHANGED')

    def test_code_hidden_by_a_regex_literal_is_not_a_pass(self):
        before = "export const trim = (s) => s.replace(/\\/*$/, '');\nexport const check = (u) => u.isAdmin;\n/** Doc. */\n"
        self.assert_verdict(self.prove(before, before.replace('u.isAdmin', 'true'), 'a.ts'), 2, 'not whole-line comments')

    def test_a_blank_line_that_changes_alone_is_unproven(self):
        self.assert_verdict(self.prove('const p = `a\nb`;\n', 'const p = `a\n\nb`;\n', 'a.ts'), 2, 'blank lines alone')
        self.assert_verdict(self.prove('body: |\n  one\n\n  two\n', 'body: |\n  one\n  two\n', 'a.yml'), 2, 'blank lines alone')

    def test_a_comment_that_gains_a_trailing_backslash_is_unproven(self):
        self.assert_verdict(self.prove('// set the limit\nint limit = 3;\n', '// set the limit \\\nint limit = 3;\n', 'a.c'), 2, 'backslash')
        self.assert_verdict(self.prove('# build target\nall: build\n', '# build target \\\nall: build\n', 'Makefile'), 2, 'backslash')

    def test_removed_changed_or_moved_directive_fails(self):
        self.assert_verdict(self.prove(PY, PY.replace('  # noqa: F821', '')), 1, 'DIRECTIVES-CHANGED')
        self.assert_verdict(self.prove(PY.replace('noqa', 'NOQA'), PY.replace('  # noqa: F821', '')), 1, 'DIRECTIVES-CHANGED')
        self.assert_verdict(self.prove('x = f()  # ty: ignore[arg]\n', 'x = f()\n'), 1, 'DIRECTIVES-CHANGED')
        moved = PY.replace('  # noqa: F821', '').replace('y = other()', 'y = other()  # noqa: F821')
        self.assert_verdict(self.prove(PY, moved), 1, 'DIRECTIVES-CHANGED')
        ts = '// eslint-disable-next-line no-console\nconsole.log(1);\nconsole.log(2);\n'
        self.assert_verdict(self.prove(ts, 'console.log(1);\n// eslint-disable-next-line no-console\nconsole.log(2);\n', 'a.ts'), 1, 'DIRECTIVES-CHANGED')
        self.assert_verdict(self.prove('const a = /*#__PURE__*/ f();\n', 'const a =  f();\n', 'a.js'), 1, 'DIRECTIVES-CHANGED')
        self.assert_verdict(self.prove('/*! @license MIT */\nconst a = 1;\n', '/*! licence note */\nconst a = 1;\n', 'a.js'), 1, 'DIRECTIVES-CHANGED')
        self.assert_verdict(self.prove('x = f()  # NOSONAR\n', 'x = f()\n'), 1, 'DIRECTIVES-CHANGED')
        self.assert_verdict(self.prove('x = f()  # lgtm[py/code-injection]\n', 'x = f()\n'), 1, 'DIRECTIVES-CHANGED')
        self.assert_verdict(self.prove('# TODO: skip when empty\nx = 1\n', '# TODO: skip when blank\nx = 1\n'), 0, 'COMMENT-ONLY')
        self.assert_verdict(self.prove('-- +goose Up\nSELECT 1;\n', '-- +goose Down\nSELECT 1;\n', 'a.sql'), 1, 'DIRECTIVES-CHANGED')

    def test_docstring_edit_needs_a_read(self):
        self.assert_verdict(self.prove(PY, PY.replace('"""Module."""', '"""Module two."""')), 3, 'DOCSTRING-CHANGED')
        self.assert_verdict(self.prove(PY, PY.replace('"""Module."""', '"""Module. """')), 3, 'DOCSTRING-CHANGED')

    def test_unsupported_unparsed_binary_and_empty_runs_are_not_passes(self):
        self.assert_verdict(self.prove('{"a": 1}\n', '{"a": 2}\n', 'a.json'), 2, 'UNPROVEN')
        self.assert_verdict(self.prove(PY, PY + 'def broken(:\n'), 2, 'does not parse')
        self.assert_verdict(self.prove(b'# \xe9\nx=1\n', b'# \xe8\nx=1\n', 'a.sh'), 2, 'not UTF-8')
        deep = '# a\nx = ' + '(' * 90 + '1' + ')' * 90 + '\n' + 'y = ' + '-' * 3000 + '1\n'
        self.assert_verdict(self.prove(deep, deep.replace('# a', '# b')), 2, 'does not parse: RecursionError')
        self.assertEqual(self.prove(PY, PY).returncode, 2)

    def test_added_untracked_and_mode_changed_files_fail(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Repo(root)
            repo.commit({'a.py': PY, 'run.sh': SH})
            repo.write({'new.py': 'x = 1\n'})
            self.assert_verdict(run('prove', root), 1, 'untracked')
            repo.git('add', 'new.py')
            self.assert_verdict(run('prove', root), 1, 'added')
            repo.git('rm', '-q', '-f', 'new.py')
            os.chmod(repo.root / 'run.sh', 0o755)
            self.assert_verdict(run('prove', root), 1, 'file mode')

    def test_changed_outranks_unproven_and_head_selects_the_commit(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Repo(root)
            first = repo.commit({'a.py': PY, 'b.json': '{}\n'})
            second = repo.commit({'a.py': PY.replace('vendor', 'supplier')})
            repo.write({'a.py': PY.replace('LIMIT = 3', 'LIMIT = 4'), 'b.json': '{"a": 1}\n'})
            self.assert_verdict(run('prove', root, '--base', first, '--head', second), 0, 'COMMENT-ONLY')
            self.assert_verdict(run('prove', root), 1, 'UNPROVEN')

    def test_unproven_outranks_a_file_to_read(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Repo(root)
            repo.commit({'a.ts': TS, 'b.json': '{}\n'})
            repo.write({'a.ts': TS.replace('vendor endpoint', 'billing endpoint'), 'b.json': '{"a": 1}\n'})
            result = run('prove', root)
            self.assert_verdict(result, 2, 'LEXER-ONLY')
            self.assertIn('UNPROVEN', result.stdout)

    def test_a_failed_run_exits_two(self):
        with tempfile.TemporaryDirectory() as root:
            Repo(root).commit({'a.py': PY})
            result = run('prove', root, '--base', 'no-such-ref')
            self.assertEqual(result.returncode, 2)
            self.assertIn('run failed', result.stderr)


class InventoryTests(unittest.TestCase):
    def test_flags_unresolved_names_and_terms_and_scopes(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as out:
            repo = Repo(root)
            repo.commit({'old_exporter.py': 'x = 1\n', 'a.py': 'def load_rows():\n    return 1\n'})
            repo.git('rm', '-q', 'old_exporter.py')
            repo.commit({
                'a.py': ('def load_rows():\n'
                         '    # load_rows feeds the report through build_client.\n'
                         '    # Kept in step with write_summary_rows in old_exporter.\n'
                         '    return 1\n'
                         '# The batch queue drains first.\n'
                         'y = 2  # noqa: F841\n'),
                'gen/client.py': 'def build_client():\n    return 1\n',
                'lib/b.py': '# Call load_rows before this.\nz = 3\n',
                'bom.py': '﻿# A byte order mark is fine.\nq = 1\n',
                'latin.sh': b'# caf\xe9\necho 1\n',
            })
            terms = Path(out) / 'terms.txt'
            terms.write_text('batch queue\n')
            result = run('inventory', root, '--out', out, '--terms', terms, '--exclude', 'gen/*')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr.strip(), 'not inventoried: latin.sh (UnicodeDecodeError)')
            summary = json.loads(result.stdout)
            self.assertEqual((summary['comments'], summary['directives'], summary['files_not_inventoried']), (4, 1, 1))
            comments = {c['text']: c for c in map(json.loads, (Path(out) / 'comments.jsonl').read_text().splitlines())}
            self.assertEqual(comments['load_rows feeds the report through build_client. Kept in step with write_summary_rows in old_exporter.']['signals'],
                             {'unresolved': ['old_exporter', 'write_summary_rows']})
            self.assertEqual(comments['The batch queue drains first.']['signals'], {'terms': ['batch queue']})
            self.assertEqual((Path(out) / 'git_deleted_stems.txt').read_text().splitlines()[1], 'old_exporter\t1')
            scoped = run('inventory', root, '--out', out, '--only', 'lib/*')
            self.assertEqual(json.loads(scoped.stdout)['comments'], 1)
            self.assertEqual(json.loads((Path(out) / 'comments.jsonl').read_text())['signals'], {})

    def test_sample_is_seeded_random_and_holds_no_directive(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as out:
            body = ''.join(f'# Reason number {n} for the value.\nv{n} = {n}  # noqa: E501\n' for n in range(40))
            Repo(root).commit({'a.py': body})
            draws = []
            for seed in (1, 1, 2):
                run('inventory', root, '--out', out, '--sample', 10, '--seed', seed)
                rows = (Path(out) / 'sample.tsv').read_text().splitlines()
                self.assertEqual(rows[0].split('\t'), ['id', 'file', 'line', 'lines', 'kind', 'category', 'live_rule', 'note', 'text'])
                self.assertTrue(all(row.split('\t')[4] == 'comment' for row in rows[1:]))
                draws.append([int(row.split('\t')[0]) for row in rows[1:]])
            self.assertEqual(draws[0], draws[1])
            self.assertNotEqual(draws[0], draws[2])
            self.assertNotEqual(draws[0], sorted(range(0, 80, 2))[:10])


class TallyTests(unittest.TestCase):
    HEADER = 'id\tfile\tline\tlines\tkind\tcategory\tlive_rule\tnote\ttext\n'

    def tally(self, rows, summary=None):
        with tempfile.TemporaryDirectory() as root:
            sample = Path(root) / 'sample.tsv'
            sample.write_text(self.HEADER + ''.join(f'{i}\ta.py\t1\t{lines}\tcomment\t{cat}\t{live}\t\tt\n' for i, (cat, live, lines) in enumerate(rows)))
            if summary is None:
                return run('tally', sample)
            (Path(root) / 'summary.json').write_text(json.dumps(summary))
            return run('tally', sample, '--summary', Path(root) / 'summary.json')

    ROWS = [('stale', 'yes', 4), ('stale', 'no', 1), ('tautology', '', 1), ('decision', '', 4)]

    def test_uncategorized_rows_stop_the_tally(self):
        self.assertEqual(self.tally([('stale', 'yes', 1), ('', '', 1)]).returncode, 2)
        self.assertEqual(self.tally([('stale', '', 1)]).returncode, 2)
        self.assertEqual(self.tally([('unsure', '', 1)]).returncode, 0)

    def test_reports_comment_rates_line_shares_and_projection(self):
        result = self.tally(self.ROWS, {'comments': 1000, 'comment_lines': 3000})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r'stale\s+2\s+50\.0% of comments\s+50\.0% of comment lines\s+95% interval 15\.0% to 85\.0% \(about 150 to 850 comments\)')
        self.assertRegex(result.stdout, r'stale, with a live rule\s+1\s+25\.0% of comments\s+40\.0% of comment lines')
        self.assertIn('about 300 of 3000 comment lines', result.stdout)

    def test_inline_tautologies_shed_no_line(self):
        with tempfile.TemporaryDirectory() as root:
            sample = Path(root) / 'sample.tsv'
            sample.write_text(self.HEADER + '0\ta.py\t1\t1\tinline\ttautology\t\t\tt\n1\ta.py\t2\t1\tcomment\tdecision\t\t\tt\n')
            (Path(root) / 'summary.json').write_text(json.dumps({'comments': 1000, 'comment_lines': 1000}))
            self.assertIn('about 0 of 1000 comment lines', run('tally', sample, '--summary', Path(root) / 'summary.json').stdout)

    def test_a_census_prints_exact_counts(self):
        result = self.tally(self.ROWS, {'comments': 4, 'comment_lines': 10})
        self.assertIn('every comment: 4', result.stdout)
        self.assertNotIn('interval', result.stdout)

    def test_wilson_matches_known_values(self):
        low, high = comment_audit.wilson(9, 300)
        self.assertAlmostEqual(low, 0.0159, places=4)
        self.assertAlmostEqual(high, 0.0560, places=4)


if __name__ == '__main__':
    unittest.main()
