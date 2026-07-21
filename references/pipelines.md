# Pipelines

The six protocols in operational detail. Each is a sequence with an explicit
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

---

## 2. TDD pipeline (backend features)

Order is fixed. The point is that **the implementation never gets to define its own
success criteria.**

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
