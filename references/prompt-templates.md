# Prompt templates

Copy-paste skeletons. Fill every `<…>`. Placeholders in `[brackets]` are optional.
All five assume the orchestrator has already frozen the interface.

Every codex prompt is prepended with the **filesystem-boundary preamble** from
`codex-recipes.md`. Subagent prompts carry the **six mandatory contents** from
`subagent-recipes.md`.

---

## (a) Codex implementer

```
[filesystem-boundary preamble]

TASK: Implement <feature> in <repo-root>, sandbox workspace-write.

FROZEN INTERFACE (produce exactly these — flag loudly rather than invent if any is
ambiguous or wrong; do not silently deviate):
<names / signatures / ids / file paths>

CONSTRAINTS:
- Do NOT edit tests. If a test looks wrong, STOP and report it as a test-change
  request — do not change it.
- Follow the project's package manager and style (<uv/npm/...>).
- Leave ALL changes UNCOMMITTED. Do not commit, do not push.
- No fallback/default behavior that hides errors — fail explicitly.
- [Seam: where <symbol> from a parallel track belongs, leave a single
  `# ASSEMBLY: <symbol>` marker instead of inlining.]

VERIFY (run these and paste the ACTUAL tail + pass/fail counts):
<exact test/lint commands>

REPORT (this is data for the orchestrator, not prose):
- Per-criterion: <criterion> → PASS/FAIL + evidence.
- Files touched + one line each on what changed.
- Any interface deviation, with why.
- Anything you flagged rather than invented.
```

---

## (b) Adversarial reviewer (codex or subagent — different family from implementer)

```
[filesystem-boundary preamble + git-inspection exception if the branch is under a
config path]

ROLE: Adversarial reviewer. The implementer is NOT you. Assume the diff is wrong
until proven otherwise. Sandbox read-only.

REVIEW: <branch or uncommitted diff> in <repo-root>.
Base for comparison: `git show <base>:<file>` for extractions/refactors — check
moved code is byte-similar, helper defaults match, error types preserved.

CHECK (attack, don't rubber-stamp):
- Correctness against the frozen interface: <interface>.
- Error paths, edge cases, concurrency/late-writer races, orphaned rows after
  migrations, read paths that bypass new joins/constraints.
- No hidden fallbacks; failures are explicit.
- Tests actually exercise the behavior (not tautological / not skipped).

OUTPUT CONTRACT (exact):
- Numbered findings, each `[P1]` (must-fix) / `[P2]` (should-fix) / `[NIT]`,
  each with `file:line` and a CONCRETE fix.
- One line per passing check.
- Final line, exactly: `VERDICT: MERGE`  (or `PUSH`)  or  `VERDICT: FIX-FIRST`.
```

---

## (c) TDD test author

```
TASK: Write FAILING tests + an interface-contract doc for <feature>. You do NOT
implement it.

FROZEN INTERFACE (test against exactly this):
<names / signatures / exceptions>

TESTS:
- Cover expected behavior AND key failure modes.
- Must FAIL for the right reason now: ImportError / AttributeError / assertion —
  because the code doesn't exist yet. NEVER skip or xfail.
- Do not stub the thing under test into existence.

INTERFACE-CONTRACT DOC (deliver alongside the tests):
- Every name, signature, and exception the tests import.
- Mark any choice you had to make `(proposed)` so the orchestrator can ratify it.

VERIFY: run the suite, paste the tail showing the tests fail for the stated reason.
REPORT: test files + the contract doc. Data, not prose.
```

---

## (d) Content / pack author

```
TASK: Author <content: pack / dataset / fixture / doc> at <path>.

SOURCE OF TRUTH: <spec / schema / existing example to match>.
FROZEN SCHEMA (ids, field names, shapes — match exactly, flag rather than invent):
<schema>

CONSTRAINTS:
- Match the existing format/style of <reference file> exactly.
- No fabricated stats/quotes/claims — every factual value traces to a source.
- [User-visible copy: propose 2–4 wording options, do not finalize.]
- Commit locally to your branch, never push.

VERIFY: <validation/build/lint command> — paste the actual output.
REPORT: files written, how each was validated, any schema deviation + why.
```

---

## (e) Re-gate after fixes

```
[filesystem-boundary preamble]

ROLE: Re-gate reviewer. A fix round just landed. Fixes introduce bugs too — a real
re-gate has caught brand-new P1s (unfenced late-writer overwrite, read path
bypassing a new strict join, migration leaving orphaned dependents).

DO BOTH:
1. For EACH prior finding <paste prior [P1]/[P2] list>, verify it is GENUINELY
   resolved — not merely silenced. Cite the fixing `file:line`.
2. Attack the NEW code with FRESH angles — treat the fix diff as new surface:
   races, bypassed constraints, orphaned rows, changed observable behavior.

OUTPUT CONTRACT (exact):
- Per prior finding: RESOLVED / NOT-RESOLVED + `file:line`.
- New numbered findings `[P1]/[P2]/[NIT]` with `file:line` + concrete fix.
- One line per passing check.
- Final line, exactly: `VERDICT: MERGE` (or `PUSH`) or `VERDICT: FIX-FIRST`.
```
