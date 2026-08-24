# Pipelines

The seven protocols in operational detail. Each is a sequence with an explicit
gate; none is optional for the class of work it covers.

---

## 1. Cross-model review gate

The load-bearing rule of the whole system: **the implementer never reviews its own
work, and the reviewer is preferably a different model family.**

- codex-built → a subagent reviews.
- subagent-built → codex reviews.

Same model family shares blind spots; a different family attacks from a different
prior. Route accordingly.

### Reviewer output contract (identical for every gate)

- Numbered findings, each tagged `[P1]` (must-fix, blocks merge) / `[P2]`
  (should-fix) / `[NIT]`.
- Each finding carries a `file:line` and a **concrete** fix — not "consider
  improving error handling" but the change to make.
- One line per passing check, so the orchestrator sees what was actually verified.
- Ends on a line that is **exactly** `VERDICT: MERGE` (or `VERDICT: PUSH`) or
  `VERDICT: FIX-FIRST`. Nothing merges without a clean verdict.

### Re-gate (mandatory after any fix round)

A fix round is new code; new code gets reviewed. The re-gate is a **fresh
adversarial pass** that does two things:

1. Verifies each prior finding is *genuinely* resolved (not papered over).
2. Attacks the new code with **new angles** — the fix itself is a change that can
   break things.

This is not ceremony. A real re-gate on a fix round surfaced **three new P1s**:

- an unfenced late-worker path that could overwrite a just-written record;
- a read path that bypassed the new strict join the fix had added;
- a migration that left orphaned dependent rows.

None existed before the fix. Skipping the re-gate would have shipped all three.

### Running the loop (multi-round mechanics)

- **Fresh angles every round.** A re-gate prompt that only says "verify the fixes"
  finds nothing; write new attack vectors per round (isolation-level races after a
  locking fix, legacy data shapes after a re-key, consumer sweeps after a serving
  change). The subtlety of findings should *increase* per round — that's the gate
  digging, not failing.
- **Embed decisions in the routing.** When a reviewer offers "fix A or fix B,"
  the orchestrator resolves the fork **in the fix-round message** ("DECISION: …").
  Routing findings without decisions buys an extra round when the implementer
  picks the wrong branch silently.
- **Track convergence.** Findings-per-round should fall (a real sequence: 8 → 5 →
  4 → …). Flat or rising counts after round 3 mean the approach is wrong, not the
  execution — stop the loop, reassess the design, or escalate to the user.
- **Evidence for the cross-model rule:** in one working day the gate caught bugs
  in *both directions* — codex found a subagent's concurrency holes across four
  rounds; a subagent found codex's legacy-data regression plus a test rigged to
  miss it. Same-family review would likely have caught neither.

### Finder-fixes-verified variant (role swap per round)

The default loop routes findings back to the original
implementer. This variant routes them to the **finder** instead:

1. Reviewer/audit model produces findings (file:line + concrete fix each).
2. A different party verifies each finding against the code before any fix is
   authorized — the other model, or the orchestrator directly for a short list
   (open the cited lines yourself; findings are asserted with confidence
   whether right or wrong).
3. The finder's session **resumes with write access** and fixes exactly the
   verified set — nothing beyond it. For codex, `codex exec resume <thread-id>`
   preserves the full review context (resume flag gotchas in codex-recipes.md).
4. The other model family re-gates the fix delta as usual.

Prefer it over implementer-fixes when findings are precise and prescriptive
(security hardening, contract mismatches): the fix is essentially specified,
and the finder holds the deepest context on each defect — handing back to the
original implementer transfers nothing but the text of the findings. Do NOT use
it for findings that require re-design or the original implementation intent;
those go back to the implementer.

The integrity rule, stated precisely: **implementer ≠ reviewer per round.** The
model that authored a diff never verdicts that diff; who authored the previous
round is irrelevant. First round: A builds, B reviews. Fix round: B fixes, A
(or a fresh A-family session) re-gates.

---

## 2. TDD pipeline (backend features)

Order is fixed. The point is that **the implementation never gets to define its own
success criteria.**

**Red-tests sequencing in commit-to-main repos** (green-push gate, no PRs): commit
the failing tests LOCALLY first as their own logic-group, implement on top, push
only when the whole set is green. TDD discipline without ever publishing red.

1. **Test-author subagent** writes FAILING tests **plus an interface-contract
   doc** — every name, signature, and exception the tests import, with any open
   choices marked `(proposed)`. Written against a **frozen interface** the
   orchestrator specified. Tests must **fail for the right reason**
   (`ImportError` / `AttributeError` / assertion) — never `skip`/`xfail`. A test
   that fails because the module doesn't exist yet is correct; a test that is
   skipped proves nothing.
2. **Orchestrator reviews the contract** — this is the cheap moment to catch a
   wrong signature or a missing exception, before any implementation exists.
3. **Codex implements to green** and **may not edit the tests.** If a test looks
   wrong to the implementer, that is a **test-change request routed back to the
   orchestrator** — never a unilateral edit. This is what keeps the criteria
   honest.
4. **Adversarial review** (cross-model gate, §1).
5. **Orchestrator commits per logic-group.**

### Small-slice variant (gate-verified TDD)

The full pipeline costs a dedicated test-author round. For **small slices** — a
bounded fix group, one setting plus plumbing, a single-seam change — an
implementer-authored variant is acceptable:

- the implementer writes the failing tests FIRST and pastes the **red tails**
  (fail-for-the-right-reason evidence) in its report, then implements to green;
- the adversarial gate carries the test-integrity check **explicitly**: no
  assertion weakened, no test edited to pass, tests pin the stated behavior —
  the tests are first-class attack surface, not an afterthought.

The separation of powers moves from author-vs-implementer to
implementer-vs-gate. Use the **full** pipeline when the slice is large, the
interface is contested, or the implementer defining its own tests is the fox
guarding the henhouse (scoring logic, security boundaries, anything it has an
incentive to under-test). Field evidence: five consecutive fix
branches ran the variant — failing-first tails in every report, gates checking
test integrity every round — ~20 commits, zero weakened-assertion findings.

---

## 3. Parallel tracks + assembly

Independent work (content, tests, refactors) runs **simultaneously**. The
orchestrator is the integration point.

### Dispatch

- Subagents run in **isolated git worktrees**, committing **locally** to their own
  branch (never push).
- Codex runs in the **main checkout**, leaving all changes **UNCOMMITTED** for the
  orchestrator to review.
- **Interface freeze before dispatch:** freeze every shared name/id in every prompt.
  Instruct agents to **"flag loudly rather than invent"** on any ambiguity. Expect
  small justified deviations — reconcile them at assembly, don't forbid them
  (forbidding produces silent wrong guesses instead).
- **Seam convention:** where a parallel track's symbol will replace inline code,
  the agent leaves a single `# ASSEMBLY:` marker comment at that spot. The
  orchestrator swaps it in during assembly.

### Assembly (orchestrator only)

1. Merge worktree branches.
2. Apply the `# ASSEMBLY:` seam swaps the tracks flagged.
3. Reconcile interface deviations against the frozen names.
4. Run the **full** suites.
5. **One** adversarial review over the whole assembled diff — then push.

**Sequencing hazard:** never merge a branch while a delegate's uncommitted work
sits in the checkout. Commit or stash the dirty tree first, or the merge tangles
with unreviewed changes.

---

## 4. Frozen-file protocol (pilot / production-critical code)

Before converting or refactoring a frozen file:

1. Land a **GOLDEN INVARIANCE TEST** that pins the file's observable contract with
   **inline expected values** — literals written by hand, **never re-derived from
   the code under test** (re-deriving just asserts the code equals itself). This
   test must pass **before and after** the change.
2. Convert **one seam at a time**, each step behavior-preserving.
3. Hold the risky merges **behind the freeze milestone** — don't land them mid-freeze.

The invariance test is the thing that makes a "behavior-preserving refactor"
actually preserving instead of merely claimed.

---

## 5. Spec pipeline (big designs)

Drafts written by any model contain **confident falsehoods** about the codebase.
The pipeline exists to catch them before they become a spec.

1. **Parallel research fan-out** — read-only explorer subagents, each with a
   **distinct focus** (one per subsystem/concern). Read-only: they investigate,
   they don't touch files.
2. **Synthesis draft** — one agent (or the orchestrator) merges the findings into a
   draft.
3. **Adversarial verification round** — attack the draft's **factual claims against
   the actual code.** This is not a style pass; it checks whether each asserted
   constraint, key, or invariant is real. A real verification round caught **6+**
   errors in one draft, including a **nonexistent constraint** the draft relied on
   and an **unusable replay key**.
4. **Final spec** with the **user's decisions recorded** inline (see §6).

Run **codex as an independent second opinion** at ~max effort against the draft.
**Cap at 2 iterations** — past that, the spec is either good enough or the design
question needs the user.

---

## 6. User decision protocol

Not every decision is the orchestrator's to make.

- Decisions that shape **scope, architecture, or timeline** → go to the **user** as
  a **structured question with a recommended option** (and the tradeoff for each
  alternative). Record the decision in the plan and in memory.
- **Everything else** the orchestrator decides and **reports** (doesn't ask).

The failure this prevents: burning a round-trip asking the user about something
reversible and low-stakes, *and* the opposite — silently making an
architecture-shaping call the user needed to own.

---

## 7. Operational-run pipeline (live systems, no code changes)

For delegate runs that **operate** the system rather than change it — stand up a
stack, run a live generation/ingestion sweep, execute a runbook, produce an
evidence record. Not implementation (nothing to diff), not review (nothing to
verdict), so pipelines 1–6 don't cover them — and the failure modes are
different: improvised recovery corrupting live state, partial success reported
as success, orphaned services, outcomes that exist only in a chat transcript.

Every operational prompt carries, without exception (template (f) in
`prompt-templates.md`):

1. **Hard stop conditions, enumerated per anticipated failure shape.** "A
   single item's failure stops the sweep at that item; capture X verbatim and
   report." The delegate's best moments come from these clauses — field run: the agent stopped at a `failed_permanent` job and reported
   instead of improvising a workaround, *because* the prompt said "a fresh
   submit needs an override — an orchestrator decision, do not improvise one."
2. **Verbatim-evidence capture.** Exact error text, full status rows, validator
   tails. The orchestrator diagnoses from the record; a paraphrase is not
   evidence. (Field payoff: a quoted 6-gram in one error string localized a
   fix to a single missing function word.)
3. **Recovery is the orchestrator's decision.** The delegate reports and stops;
   name the specific forbidden improvisations (resubmit, hand-edit DB state,
   retry with different flags, reclaim a dead job).
4. **A canonical run-record file the delegate owns** — per-item ids, statuses,
   outcomes, reviewer first-look notes, with explicit superseding language.
   State lives in the record, not the transcript; successive runs UPDATE it,
   keeping prior success entries.
5. **Started-vs-inherited accounting + cleanup.** What the delegate started vs
   what was already running; stop everything it started; verify ports free and
   say so; name the shared infra that stays up.
6. **Repo hygiene assertion.** `git status --short --branch` before and after;
   operational runs must not mutate tracked files; anything unexpected is
   reported and left uncommitted.

Sequencing with fix loops: a live failure routes into the normal
implement→gate→merge pipeline, then the **next** operational run is a fresh
prompt derived from the previous one (same saved file, updated commit / done-ids
/ stop conditions). Keep every run's prompt and report — the Nth prompt is a
small edit of the (N−1)th, and the done-list must grow monotonically so
completed items are never resubmitted.

### The second-occurrence sweep rule

When two live failures share a defect **class** (not just a symptom — e.g. "a
validator enforces a contract the generation prompt never states"), stop
iterating incident-by-incident: dispatch a **class-wide audit** — one read-only
pass enumerating every instance of the class — and fix them in one gated round.
Field evidence: the instruction/validator-gap class surfaced
**five times** across a live mint pipeline (grounding vocabulary, scaffolding
blocklist, reviewer-overlap rule, rubric echo, one missing preposition), each
discovered one ~50-minute live cycle at a time; a sweep after occurrence two
would have saved roughly two full cycles. The eventual fix that ended the
tail — replacing one-word-per-incident connective additions with the closed
function-word class, once, gated — is the same rule applied to the fix itself.

*Prevents:* improvised recovery on live state; silent partial success; orphaned
processes; per-incident whack-a-mole on a class-shaped problem.
