# Prompt templates

Copy-paste skeletons. Fill every `<…>`. Placeholders in `[brackets]` are optional.
The implementation-facing skeletons (a)–(e) assume the orchestrator has already
frozen the interface; (f) is operational and has no interface to freeze.

Every codex prompt is prepended with the **filesystem-boundary preamble** from
`codex-recipes.md`. Subagent prompts carry the **six mandatory contents** from
`subagent-recipes.md`.

**Every SUBAGENT prompt ends with the delivery footer** (observed failure rate
without it: 3 of 3 first-run agents went idle with the report stranded in their
own transcript):

```
DELIVERY: your plain-text output is INVISIBLE to the orchestrator. Before you
stop for any reason, deliver your report (or your blocker) by calling
SendMessage with to: "main". Going idle without a SendMessage = you have
delivered nothing.
```

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
  - Exception you must pre-authorize when the slice DELIBERATELY replaces pinned
    behavior: grant the edit by CATEGORY ("you may edit any pre-existing test
    whose assertions pin <the replaced behavior>; name each edited test + what it
    pinned"), plus known instances, plus the invariants whose assertions may NOT
    weaken. Instance-by-instance grants make a literal delegate stop once per
    conflicting test — each stop is a full round-trip. (Field lesson: two
    consecutive STOPs on adjacent pre-C2/pre-C3 pins.)
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
- RE-KEY AUDIT: if the diff changes how anything is identified/discriminated
  (a key, marker, approver, enum), enumerate every EXISTING artifact identified
  the old way — legacy rows, published records, fixtures — and prove each still
  behaves. New-data-correct + legacy-data-broken is the classic re-key failure.
- ATTACK THE TESTS: for each test, check what it actually EXERCISES vs what its
  name claims — a test that injects the very condition whose absence it should
  cover, or that never reaches the code path (missing flag/config), is asserting
  a false guarantee. Report rigged tests as findings.
- No hidden fallbacks; failures are explicit.

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
   Write NEW attack vectors for this round (isolation-level races after a locking
   fix; legacy shapes after a re-key; lock-ordering after a new lock) — do not
   re-run round N-1's checklist and call it a re-gate.

SCOPE: Do NOT re-litigate proportionality or scope decisions the orchestrator
has already made (how much detail a doc carries, which fixes were adopted
partially and why) — flag only genuine errors in what is present.

[When routing this round's findings onward, the ORCHESTRATOR adds a DECISION
line resolving every either/or the reviewer offered — never leave forks to the
implementer's silent choice.]

OUTPUT CONTRACT (exact):
- Per prior finding: RESOLVED / NOT-RESOLVED + `file:line`.
- New numbered findings `[P1]/[P2]/[NIT]` with `file:line` + concrete fix.
- One line per passing check.
- Final line, exactly: `VERDICT: MERGE` (or `PUSH`) or `VERDICT: FIX-FIRST`.
```

---

## (f) Operational run (live system, no code changes — pipelines §7)

Derive run N+1 from run N's saved prompt file: update the commit, the done-list
(monotonically growing — completed items are never resubmitted), and the stop
conditions learned from the last failure.

```
[filesystem-boundary preamble]

MISSION: <operate the system: run the sweep / execute the runbook> against
<repo at commit>. You do NOT <publish/approve/deploy> — that requires <the
named human gate> and stays untouched.

CONTEXT: <what changed since the last run>. Already DONE and must NOT be
touched or resubmitted: <exact ids>. Read <run-record path> — you will UPDATE
it, keeping prior success entries.

PROCEDURE (hard stop conditions inline):
1. Stand up <stack>; record what YOU started vs what was already running.
   [Known wart: <e.g. sandboxed uv-cache error → rerun outside the sandbox
   once and note it>.]
2. <Readiness check> must PASS; otherwise STOP and report the error verbatim.
3. Do NOT touch: <dead jobs / stale state — exact ids>.
4. <Step> — on failure: capture <the exact rows/fields> VERBATIM, STOP the
   sweep, report. Do not improvise recovery (<name the forbidden moves:
   resubmit, hand-edit state, retry with different flags, reclaim>) —
   recovery is an orchestrator decision.
5. <Per-item loop, with the single-item-failure-stops-the-sweep rule and
   what to capture per item: ids, counts, validator tails>.
6. <Final verification against the live API — enumerate what "correct" looks
   like, e.g. status/approver/publication fields per item>.
7. UPDATE <run-record path>: per item — id, status, outcomes, what a reviewer
   should look at first; note it supersedes <prior records>.
8. CLEANUP: stop everything you started (<list>); <shared infra> stays up.
   Verify <ports> free and say so.

REPO HYGIENE: `git status --short --branch` before and after; this run must
not mutate tracked files — anything unexpected is reported and left
uncommitted. Commit nothing, push nothing. Never print secret values — env
var names only.

REPORT: per item — outcome + evidence verbatim; started/stopped accounting +
port verification; errors verbatim; path to the updated record.
```
