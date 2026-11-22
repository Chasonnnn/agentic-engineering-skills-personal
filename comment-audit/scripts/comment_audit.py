"""Comment audit helpers. Standard library only.

inventory  extract every comment of a git repository, flag candidates, draw a random sample
tally      report category rates from a categorized sample
prove      show that a change left the program unchanged

Nothing here edits the audited repository. `inventory` writes to --out only.
Exit 2 from any command means the run did not complete or proved nothing.
"""

from __future__ import annotations

import argparse
import ast
import csv
import difflib
import io
import json
import math
import random
import re
import subprocess
import sys
import tokenize
from collections import Counter
from fnmatch import fnmatch
from pathlib import Path

PY_EXT = {".py", ".pyi"}
C_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".go", ".rs", ".java", ".kt",
         ".swift", ".c", ".h", ".cc", ".cpp", ".hpp", ".cs", ".scala"}
HASH_EXT = {".sh", ".bash", ".zsh", ".yml", ".yaml", ".toml", ".tf", ".hcl", ".rb"}
HASH_NAMES = {"Makefile", "Dockerfile", "Justfile"}
DASH_EXT = {".sql"}
DATA_EXT = {".json", ".html", ".css", ".scss", ".csv", ".xml", ".graphql", ".proto"}
PARSE_ERRORS = (SyntaxError, ValueError, tokenize.TokenError, RecursionError)
# Comments that a tool reads. A known-forms list: it cannot be complete.
DIRECTIVE = re.compile(
    r"noqa|type:\s*ignore|pragma:|^#!|-\*-|^\W*coding[:=]|vim:|fmt:\s*(?:off|on|skip)"
    r"|\b(?:ruff|mypy|pyright|pylint|isort|yapf|flake8|bandit|pytype|tfsec|checkov)\b\s*[:-]|pyre-|\b(?:yamllint|hadolint)\b"
    r"|eslint-(?:disable|enable|env)|@ts-(?:ignore|expect-error|nocheck|check)|prettier-ignore|biome-ignore|istanbul|c8 ignore|v8 ignore"
    r"|^\W*(?!(?:todo|fixme|note|step|xxx|hack)\b)[\w-]+:\s*(?:ignore|disable|enable|skip|noqa)\b|nosemgrep|nosonar|noinspection|\blgtm\b|skipcq"
    r"|nosec|nolint|gitleaks:allow|shellcheck\s+\w+=|tflint-ignore|react-doctor-|rustfmt::skip|clippy::"
    r"|^\W*go:\w+|^\W*\+build|^\W*\+(?:goose|migrate)|^\W*name:\s*\w+\s+:|^\W*(?:syntax|escape)="
    r"|frozen_string_literal|webpack\w+:|__PURE__|@jsx|<reference\s|sourceMappingURL|@flow|@generated|^\W*code generated .*do not edit"
    r"|^\W*(?:falls?[ -]?through|fallthru)\b|@license|@preserve|spdx-license", re.I)
IDENT = re.compile(
    r"\b(?:[a-z][a-z0-9]*(?:_[a-z0-9]+)+|[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+|_[a-z][a-z0-9_]+"
    r"|[a-z]+[a-z0-9]*[A-Z][A-Za-z0-9]*|(?:[A-Z][a-z0-9]+){2,}[A-Z]?[a-z0-9]*)\b"
)
PATHISH = re.compile(r"(?<![\w/.-])((?:[\w.@()\[\]-]+/)*[\w.@\[\]-]+\.(?:py|tsx?|jsx?|mjs|go|rs|java|sql|sh|md|json|ya?ml|toml|css|html|tf))\b")
WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
SIGNALS = {
    "history": re.compile(
        r"\b(retired|legacy|no longer|used to|formerly|previously|was removed|were removed|deprecated|replaced|renamed"
        r"|originally|backward|once .{1,40} lands|in a follow-up|until we|before the migration)\b", re.I),
    "excuse": re.compile(
        r"\b(hack|hacky|workaround|work around|for now|temporar\w+|quick fix|kludge|band-?aid|ugly|not ideal|should(?:n't| not) be"
        r"|good enough|revisit|bypass\w*)\b", re.I),
    "dated": re.compile(r"\b20\d\d-\d\d-\d\d\b|\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w* 20\d\d\b"),
    "cites": re.compile(r"(?<![\w&])#\d{1,6}\b|\b[A-Z][A-Z0-9]{1,9}-\d+\b|\b(?:plan|phase|wave|step|round|milestone|sprint|finding) [A-Z]?\d+\b|§", re.I),
    "todo": re.compile(r"\b(TODO|FIXME|XXX|HACK)\b"),
}
CATEGORIES = ("tautology", "excuse", "stale", "decision")
WHOLE_LINE = {"c": ("//", "/*", "*", "{/*"), "hash": ("#",), "dash": ("--",)}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def family(path: str) -> str | None:
    p = Path(path)
    if p.suffix in PY_EXT:
        return "py"
    if p.suffix in C_EXT:
        return "c"
    if p.suffix in HASH_EXT or p.name in HASH_NAMES or p.name.startswith("Dockerfile"):
        return "hash"
    if p.suffix in DASH_EXT:
        return "dash"
    return None


class Collector:
    """Builds comment entries; consecutive whole-line comments join into one block."""

    def __init__(self) -> None:
        self.found: list[dict] = []
        self.block: dict | None = None

    def add(self, kind: str, start: int, end: int, text: str, raw: str) -> None:
        joins = kind == "comment" and self.block is not None and self.block["end"] == start - 1
        if not text:
            if joins:
                self.block["end"] = end
            return
        if DIRECTIVE.search(raw):
            self.found.append({"line": start, "end": end, "kind": "directive", "text": raw.strip()})
            self.block = None
        elif joins:
            self.block["text"] += " " + text
            self.block["end"] = end
        else:
            self.found.append({"line": start, "end": end, "kind": kind, "text": text})
            self.block = self.found[-1] if kind == "comment" else None


def docstring_nodes(tree: ast.AST) -> list[tuple[ast.AST, ast.Expr]]:
    nodes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                nodes.append((node, first))
    return nodes


def lex_python(src: str) -> tuple[list[dict], list[str | None]]:
    lines = src.splitlines()
    collector = Collector()
    doc_lines: set[int] = set()
    for _, first in docstring_nodes(ast.parse(src)):
        collector.found.append({"line": first.lineno, "end": first.end_lineno, "kind": "docstring", "text": first.value.value.strip()})
        doc_lines.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    cols: dict[int, int] = {}
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            row, col = tok.start
            cols[row] = col
            whole = lines[row - 1][:col].strip() == ""
            collector.add("comment" if whole else "inline", row, row, tok.string.lstrip("#").strip(), tok.string)
    rows: list[str | None] = []
    for number, line in enumerate(lines, 1):
        text = line[: cols[number]] if number in cols else line
        rows.append(None if number in doc_lines or (number in cols and not text.strip()) else text)
    return sorted(collector.found, key=lambda c: c["line"]), rows


def lex_c(src: str) -> tuple[list[dict], list[str | None]]:
    """A heuristic. It does not know regex literals, JSX text, or strings that span lines."""
    collector = Collector()
    out: list[str] = []
    i, n, line = 0, len(src), 1
    quote: str | None = None
    touched: set[int] = set()
    while i < n:
        ch, two = src[i], src[i : i + 2]
        if quote:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(src[i + 1])
                line += src[i + 1] == "\n"
                i += 2
                continue
            if ch == quote or (ch == "\n" and quote in "'\""):
                quote = None
            line += ch == "\n"
            i += 1
        elif two == "//" and (i == 0 or src[i - 1] != ":"):
            j = src.find("\n", i)
            j = n if j == -1 else j
            start = src.rfind("\n", 0, i) + 1
            touched.add(line)
            collector.add("comment" if src[start:i].strip() == "" else "inline", line, line, src[i + 2 : j].strip(), src[i + 2 : j])
            i = j
        elif two == "/*":
            j = src.find("*/", i + 2)
            j = n - 2 if j == -1 else j
            raw = src[i + 2 : j]
            end = line + raw.count("\n")
            touched.update(range(line, end + 1))
            text = " ".join(part.strip().lstrip("*").strip() for part in raw.splitlines()).strip()
            collector.add("block", line, end, text, text)
            out.append("\n" * raw.count("\n"))
            line = end
            i = j + 2
        else:
            if ch in "'\"`":
                quote = ch
            line += ch == "\n"
            out.append(ch)
            i += 1
    rows: list[str | None] = []
    for number, text in enumerate("".join(out).split("\n"), 1):
        rows.append(text if number not in touched else text.rstrip() if text.strip() else None)
    return collector.found, rows


def lex_lines(src: str, marker: str) -> tuple[list[dict], list[str | None]]:
    """Whole-line comments only. An inline comment stays in the code text."""
    collector = Collector()
    rows: list[str | None] = []
    for row, line in enumerate(src.splitlines(), 1):
        stripped = line.strip()
        if not stripped.startswith(marker) or (row == 1 and stripped.startswith("#!")):
            rows.append(line)
            continue
        rows.append(None)
        collector.add("comment", row, row, stripped[len(marker):].lstrip("#-").strip(), stripped)
    return collector.found, rows


def lex(path: str, src: str) -> tuple[list[dict], list[str | None]] | None:
    """Return (comments, code text per source line; None where the line was only a comment)."""
    kind = family(path)
    if kind is None:
        return None
    found, rows = lex_python(src) if kind == "py" else lex_c(src) if kind == "c" else lex_lines(src, "#" if kind == "hash" else "--")
    for entry in found:
        if entry["kind"] == "directive":
            here = rows[entry["line"] - 1] if entry["line"] <= len(rows) else None
            below = (r.strip() for r in rows[entry["end"]:] if r and r.strip())
            entry["anchor"] = here.strip() if here and here.strip() else next(below, "")
    return found, rows


def inventory(args: argparse.Namespace) -> int:
    repo, out = Path(args.repo).resolve(), Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    tracked = git(repo, "ls-files", "-z").split("\0")[:-1]
    stems = {Path(f).stem for f in tracked}
    comments: list[dict] = []
    corpus: set[str] = set()
    skipped: list[str] = []
    code_lines = 0
    for rel in tracked:
        path = repo / rel
        supported = family(rel) is not None
        if not path.is_file() or path.is_symlink() or not (supported or path.suffix in DATA_EXT):
            continue
        in_scope = not any(fnmatch(rel, g) for g in args.exclude) and (not args.only or any(fnmatch(rel, g) for g in args.only))
        try:
            src = path.read_text(encoding="utf-8-sig")
            lexed = lex(rel, src)
        except (UnicodeDecodeError, OSError, *PARSE_ERRORS) as error:
            if supported and in_scope:
                skipped.append(f"{rel} ({type(error).__name__})")
            continue
        if lexed is None:
            corpus.update(WORD.findall(src))
            continue
        code = [row for row in lexed[1] if row is not None]
        corpus.update(WORD.findall("\n".join(code)))
        if in_scope:
            code_lines += sum(1 for row in code if row.strip())
            comments.extend({"file": rel, **c} for c in lexed[0])
    for entry in skipped:
        print(f"not inventoried: {entry}", file=sys.stderr)
    terms = [t.strip() for t in Path(args.terms).read_text().splitlines() if t.strip() and not t.startswith("#")] if args.terms else []
    term_res = [(t, re.compile(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])", re.I)) for t in terms]
    suffixes = {"/".join(parts[i:]) for parts in (f.split("/") for f in tracked) for i in range(len(parts))}
    for number, c in enumerate(comments):
        c["id"] = number
        text = c["text"]
        c["signals"] = signals = {}
        if c["kind"] == "directive":
            continue
        missing = sorted({t for t in IDENT.findall(text) if t not in corpus})
        for token in set(PATHISH.findall(text)):
            clean = token.lstrip("./")
            known = clean in suffixes if "/" in clean else Path(clean).stem in stems
            if not known and "*" not in token and "<" not in token:
                missing.append("path:" + token)
        if missing:
            signals["unresolved"] = missing
        for name, pattern in SIGNALS.items():
            hits = sorted({m.group(0).lower() for m in pattern.finditer(text)})
            if hits:
                signals[name] = hits
        hits = [t for t, pattern in term_res if pattern.search(text)]
        if hits:
            signals["terms"] = hits
    (out / "comments.jsonl").write_text("".join(json.dumps(c) + "\n" for c in comments), encoding="utf-8")
    strong = ("terms", "unresolved", "cites", "history", "dated", "excuse", "todo")
    candidates = sorted((c for c in comments if c["signals"]), key=lambda c: [name not in c["signals"] for name in strong])
    (out / "candidates.jsonl").write_text("".join(json.dumps(c) + "\n" for c in candidates), encoding="utf-8")

    prose = [c for c in comments if c["kind"] != "directive"]
    sample = random.Random(args.seed).sample(prose, min(args.sample, len(prose)))
    with (out / "sample.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["id", "file", "line", "lines", "kind", "category", "live_rule", "note", "text"])
        for c in sorted(sample, key=lambda c: (c["file"], c["line"])):
            writer.writerow([c["id"], c["file"], c["line"], c["end"] - c["line"] + 1, c["kind"], "", "", "",
                             re.sub(r"\s+", " ", c["text"])[:600]])

    deleted: Counter[str] = Counter()
    if not args.no_git_history:
        gone = git(repo, "log", "--diff-filter=DR", "--name-status", "--format=").splitlines()
        old = {Path(row.split("\t")[1]).stem for row in gone if "\t" in row} - stems
        old = {s for s in old if len(s) >= 5 and re.search(r"[_\-0-9]|[a-z][A-Z]", s)}
        for c in prose:
            deleted.update(old & set(re.findall(r"[\w-]+", c["text"])))
        (out / "git_deleted_stems.txt").write_text(
            "# name of a deleted or renamed file <TAB> comments that still mention it\n"
            + "".join(f"{stem}\t{count}\n" for stem, count in deleted.most_common()), encoding="utf-8")
    comment_lines = sum(c["end"] - c["line"] + 1 for c in prose)
    summary = {
        "repo": str(repo),
        "head": git(repo, "rev-parse", "HEAD").strip(),
        "files_not_inventoried": len(skipped),
        "comments": len(prose),
        "directives": len(comments) - len(prose),
        "comment_lines": comment_lines,
        "code_lines": code_lines,
        "comment_share_of_lines": round(comment_lines / max(1, comment_lines + code_lines), 4),
        "by_kind": Counter(c["kind"] for c in comments),
        "candidates": len(candidates),
        "by_signal": {name: sum(1 for c in comments if name in c["signals"]) for name in strong},
        "sample": {"size": len(sample), "seed": args.seed},
        "git_deleted_stems_mentioned": len(deleted),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


def wilson(hits: int, total: int) -> tuple[float, float]:
    """95% Wilson interval for a proportion."""
    if total == 0:
        return 0.0, 0.0
    z, p = 1.96, hits / total
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return max(0.0, centre - half), min(1.0, centre + half)


def tally(args: argparse.Namespace) -> int:
    with open(args.sample, newline="", encoding="utf-8") as handle:
        rows = [{key: (value or "").strip().lower() for key, value in row.items() if key} for row in csv.DictReader(handle, delimiter="\t")]
    bad = [r.get("id") for r in rows if r.get("category") not in (*CATEGORIES, "unsure")
           or (r["category"] == "stale" and r.get("live_rule") not in ("yes", "no"))]
    if bad or not rows:
        print(f"sample not fully categorized: {len(bad)} rows need a category ({', '.join(CATEGORIES)}, unsure) "
              f"or, for stale rows, live_rule yes/no: ids {bad[:20]}", file=sys.stderr)
        return 2
    summary = json.loads(Path(args.summary).read_text()) if args.summary else None
    population = summary["comments"] if summary else None
    total = len(rows)
    census = population == total
    weight = [int(r.get("lines") or 1) for r in rows]
    groups = {name: [r["category"] == name for r in rows] for name in (*CATEGORIES, "unsure")}
    groups["stale, with a live rule"] = [r["category"] == "stale" and r["live_rule"] == "yes" for r in rows]
    print(f"{'every comment' if census else 'sample'}: {total}" + (f" of {population} comments" if population and not census else ""))
    for name in (*CATEGORIES[:3], "stale, with a live rule", "decision", "unsure"):
        hits = sum(groups[name])
        lines = sum(w for w, member in zip(weight, groups[name]) if member) / sum(weight)
        line = f"{name:<24} {hits:>4}  {hits / total:6.1%} of comments  {lines:6.1%} of comment lines"
        if not census:
            low, high = wilson(hits, total)
            line += f"  95% interval {low:.1%} to {high:.1%}"
            if population:
                line += f" (about {round(low * population)} to {round(high * population)} comments)"
        print(line)
    if summary:
        # Deleting an inline comment sheds no line.
        share = sum(w for w, member, r in zip(weight, groups["tautology"], rows) if member and r.get("kind") != "inline") / sum(weight)
        print(f"lines shed if every tautology goes: about {round(share * summary['comment_lines'])} of {summary['comment_lines']} comment lines")
    return 0


def directives(found: list[dict]) -> list[tuple[str, str]]:
    return sorted((c["text"], c["anchor"]) for c in found if c["kind"] == "directive")


def program(src: str) -> tuple[str, list[str]]:
    """The parsed Python program without docstrings, and the docstrings."""
    tree = ast.parse(src, type_comments=True)
    tree.type_ignores = []  # these hold line numbers; the directive check compares each one with its anchor
    docs = []
    for node, first in docstring_nodes(tree):
        docs.append(first.value.value)
        node.body = node.body[1:] or [ast.Pass()]
    return ast.dump(tree), docs


def loose_lines(kind: str, old: str, new: str) -> list[str]:
    """Changed lines that are not whole-line comments, that end in a backslash (C and Make join the next line), or that are blank with no comment line beside them."""
    a, b = old.splitlines(), new.splitlines()
    loose = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != "equal":
            sides = [("old", n + 1, a[n].strip()) for n in range(i1, i2)] + [("new", n + 1, b[n].strip()) for n in range(j1, j2)]
            # A blank line may go with its comment. Alone, it can be a line of a string that spans lines.
            with_comment = any(text.startswith(WHOLE_LINE[kind]) for _, _, text in sides)
            loose += [f"{side} {number}" for side, number, text in sides
                      if (not with_comment if not text else not text.startswith(WHOLE_LINE[kind]) or text.endswith("\\"))]
    return loose


def verdict(path: str, old: str, new: str) -> str:
    kind = family(path)
    if kind is None:
        return "UNPROVEN (file type not supported)"
    try:
        (old_found, old_rows), (new_found, new_rows) = lex(path, old), lex(path, new)
        if kind == "py":
            (old_tree, old_docs), (new_tree, new_docs) = program(old), program(new)
            same = old_tree == new_tree
        else:
            # Blank lines are left out: deleting a comment often takes the blank line next to it.
            same = [r for r in old_rows if r and r.strip()] == [r for r in new_rows if r and r.strip()]
    except PARSE_ERRORS as error:
        return f"UNPROVEN (does not parse: {type(error).__name__})"
    if not same:
        return "CODE-CHANGED"
    if directives(old_found) != directives(new_found):
        return "DIRECTIVES-CHANGED (a comment that a tool reads was added, removed, changed or moved)"
    if kind == "py":
        return "DOCSTRING-CHANGED (program unchanged; read each changed docstring)" if old_docs != new_docs else "COMMENT-ONLY"
    loose = loose_lines(kind, old, new)
    if loose:
        return f"UNPROVEN (changed lines that are not whole-line comments, end in a backslash, or are blank lines alone: {', '.join(loose[:6])}{' ...' if len(loose) > 6 else ''})"
    return "LEXER-ONLY (no code change found; the lexer is a heuristic, read every hunk)"


def blob(repo: Path, ref: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{path}"], check=True, capture_output=True).stdout


def decode(data: bytes) -> str | None:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None


def prove(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    span = [args.base, args.head] if args.head else [args.base]
    raw = git(repo, "diff", "--raw", "--no-renames", "-z", *span, "--", *args.paths).split("\0")[:-1]
    results: list[tuple[str, str]] = []
    for meta, path in zip(raw[::2], raw[1::2]):
        old_mode, new_mode, _, _, status = meta.lstrip(":").split()
        if status != "M":
            results.append((path, "CODE-CHANGED (file added, deleted or retyped)"))
        elif old_mode != new_mode:
            results.append((path, "CODE-CHANGED (file mode)"))
        elif family(path) is None:
            results.append((path, "UNPROVEN (file type not supported)"))
        else:
            old = decode(blob(repo, args.base, path))
            new = decode(blob(repo, args.head, path) if args.head else (repo / path).read_bytes())
            results.append((path, "UNPROVEN (not UTF-8 text)" if old is None or new is None else verdict(path, old, new)))
    if not args.head:
        for path in git(repo, "ls-files", "--others", "--exclude-standard", "-z", "--", *args.paths).split("\0")[:-1]:
            results.append((path, "CODE-CHANGED (untracked file)"))
    for path, result in results:
        print(f"{result}\t{path}")
    count = Counter(result.split(" ")[0] for _, result in results)
    changed, unproven = count["CODE-CHANGED"] + count["DIRECTIVES-CHANGED"], count["UNPROVEN"]
    to_read = count["LEXER-ONLY"] + count["DOCSTRING-CHANGED"]
    print(f"{len(results)} files: {count['COMMENT-ONLY']} comment-only, {to_read} to read "
          f"(lexer-only or docstring), {changed} changed, {unproven} unproven")
    if not results:
        print("no changed files in this range; nothing was proven", file=sys.stderr)
        return 2
    return 1 if changed else 2 if unproven else 3 if to_read else 0


PROVE_HELP = """Exit codes:
  0  every changed file is Python; only # comments changed, and no known directive changed
  1  code, a file mode, or a comment that a tool reads changed; or a file was added or deleted
  2  a file could not be proven, nothing changed, or the run failed
  3  no code change was found, but some files need a read: LEXER-ONLY and DOCSTRING-CHANGED

Exit 0 has one gap. Comments that tools read (suppressions, build tags, magic comments, generated-code markers,
licence headers) are matched against a list of known forms. The list is partial: a tool-read comment in another
form reads as prose.

DOCSTRING-CHANGED: the parsed program is the same, but doctests, schema descriptions, command help and prompt text
are built from docstrings.

LEXER-ONLY files (every language but Python) need a human read of every hunk. The lexer does not know regex
literals, JSX text, or strings that span lines, so code can read as a comment. Code can also live in comments:
Rust doc tests, the Go cgo preamble. For #- and ---comment languages only whole-line comments count, so an inline
comment edit reads as CODE-CHANGED and a comment-shaped line in a heredoc or block string reads as a comment.
A changed blank line passes only when a comment line changes next to it.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory", help="extract comments, flag candidates, draw a sample")
    inv.add_argument("repo")
    inv.add_argument("--out", required=True, help="output folder; keep it outside the repository")
    inv.add_argument("--sample", type=int, default=300)
    inv.add_argument("--seed", type=int, default=0)
    inv.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                     help="record no comments of matching paths (generated, vendored, fixtures); their names still resolve")
    inv.add_argument("--only", action="append", default=[], metavar="GLOB",
                     help="record comments of matching paths only; names still resolve against the whole repository")
    inv.add_argument("--terms", help="file with one retired name per line; a hit is the strongest signal")
    inv.add_argument("--no-git-history", action="store_true", help="skip the deleted-file-name list")
    inv.set_defaults(run=inventory)
    tal = sub.add_parser("tally", help="category rates of a categorized sample.tsv")
    tal.add_argument("sample")
    tal.add_argument("--summary", help="summary.json of the same inventory, to project counts and lines")
    tal.set_defaults(run=tally)
    pro = sub.add_parser("prove", help="show that a change left the program unchanged", epilog=PROVE_HELP,
                         formatter_class=argparse.RawDescriptionHelpFormatter)
    pro.add_argument("repo")
    pro.add_argument("--base", default="HEAD")
    pro.add_argument("--head", help="compare two commits; default compares --base with the working tree")
    pro.add_argument("paths", nargs="*")
    pro.set_defaults(run=prove)
    args = parser.parse_args()
    try:
        return args.run(args)
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else error.stderr or ""
        print(f"run failed: {' '.join(map(str, error.cmd))}: {detail.strip()}", file=sys.stderr)
    except Exception as error:  # exit 1 means "code changed", so no failure may leave through a traceback
        print(f"run failed: {type(error).__name__}: {error}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
