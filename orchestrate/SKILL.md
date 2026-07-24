---
name: orchestrate
description: >-
  Multi-model orchestration workflow for Claude Code. Use when the user says
  "orchestrate this", "delegate to codex/opus", "multi-model", "act as
  orchestrator", or asks the main session to coordinate CLI agents/subagents.
  Use proactively whenever a session involves delegating substantive
  implementation to CLI agents (codex exec) or subagents while the main model
  plans, reviews every diff, and integrates — i.e. the main model should stop
  writing code by hand and start orchestrating. Encodes the cross-model review
  gate, TDD/spec/parallel-track pipelines, codex + subagent operational
  recipes, and the orchestrator's duties.
---

# Orchestrate

A protocol for a capable, expensive main model to run a team of cheaper, reliable
delegates: it plans, decides, delegates, **reviews every diff**, integrates, and
commits — and never burns its context writing code a delegate could write.

## Cast (parameterize per install — see README)

| Role | Default | Does | Never does |
|---|---|---|---|
| **Orchestrator** | the main session (most capable/expensive model) | plans, decides *with the user*, delegates, reviews every delegate diff, assembles/integrates, runs suites, commits & pushes, keeps memory | writes substantive code (trivial one-liners exempt) |
| **Codex CLI** | `codex exec`, gpt-5.6-sol @ xhigh (`ultra` at orchestrator discretion for large batches / hardest tasks) | token-heavy backend implementation; independent second opinion on large plans/specs | review its own implementation; edit tests it was told not to |
| **Subagent** | Claude Opus @ xhigh (judge stages @ max) | frontend, design taste, repo audits, research fan-outs, TDD test authoring, adversarial review | push; edit outside its track |

Rationale: the orchestrator is expensive and smart; delegates are cheaper and
reliable. Spend the orchestrator's context on **judgment**, not mechanical
execution.

## Non-negotiable protocols

Each earns its place by the failure it prevents. Full detail in
`references/pipelines.md`.

1. **Cross-model review gate** — implementer ≠ reviewer, preferably a different
   model family. codex-built → subagent reviews; subagent-built → codex reviews.
   Merge/push **only** on a clean verdict. Then **re-gate**: a fresh pass that
   verifies each prior finding is truly resolved *and* attacks the new code —
   fixes introduce bugs too. *Prevents:* an implementer blessing its own blind
   spots; a fix round silently adding new P1s.
2. **TDD pipeline (backend)** — test-author subagent writes FAILING tests + an
   interface-contract doc against a frozen interface; orchestrator reviews the
   contract; codex implements to green and **may not edit tests**; adversarial
   review; commit per logic-group. *Prevents:* implementation that defines its
   own success criteria.
3. **Parallel tracks + assembly** — independent tracks run at once (subagents in
   isolated worktrees committing locally; codex in the main checkout leaving work
   **uncommitted**). Freeze names/ids before dispatch; agents "flag loudly rather
   than invent". Orchestrator assembles, reconciles deviations, runs full suites,
   then **one** adversarial review over the whole diff before push. *Prevents:*
   merge chaos and invented interfaces.
4. **Frozen-file protocol (production-critical)** — before refactoring a frozen
   file, land a GOLDEN INVARIANCE TEST pinning its observable contract with
   **inline** expected values; convert one seam at a time, behavior-preserving.
   *Prevents:* a "safe refactor" that silently changes output.
5. **Spec pipeline (big designs)** — research fan-out (read-only explorers) →
   synthesis draft → **adversarial verification** against the code (drafts
   contain confident falsehoods) → final spec with the user's decisions recorded.
   Cap at 2 iterations. *Prevents:* shipping a spec built on plausible fiction.
6. **User decision protocol** — decisions shaping scope/architecture/timeline go
   to the user as structured questions with a **recommended** option; record them
   in the plan/memory. Everything else the orchestrator decides and reports.

## Reviewer output contract (every gate)

Numbered findings `[P1]` must-fix / `[P2]` should-fix / `[NIT]`, each with
`file:line` + a concrete fix. One line per passing check. Ends **exactly**:
`VERDICT: MERGE` (or `PUSH`) or `VERDICT: FIX-FIRST`. No clean verdict → no merge.

## Orchestrator duties (checklist)

- [ ] Review **every** delegate diff before committing. For extractions/refactors:
      line-by-line against the pre-change original via `git show <base>:<file>` —
      moved code byte-similar, helper defaults match, error types preserved.
- [ ] **Scope-of-effect check** before declaring a behavior change complete:
      enumerate the production call sites that must exercise it and verify each
      passes input of the shape/scope the change needs; require one integration
      test through the deployed entry point. Label layer-local eval numbers
      (rule-layer, unit-level) as such — never present them as expected
      deployment deltas until an e2e run confirms propagation. Reviewer gates
      verify the diff-in-scope; only the orchestrator owns the seams.
      *Prevents:* unit-correct changes that silently no-op in production (field
      hit: a multi-line rule fed single-line segments by its deployed call
      site — every gate passed, deployment saw nothing).
- [ ] Commit per logic-group; reviewer-aware body (what, why safe, what pinned it,
      who implemented/reviewed); push only after a clean gate verdict.
- [ ] **Batch pushes; watch CI with a cheap agent.** Push at checkpoints (a
      slice-group lands, session end, before risky ops), not per-commit. After
      every push, spawn a cheap-model watcher subagent (read-only) on the remote
      CI runs: early-warn on first job failure, full per-job report at
      conclusion. Route reds to the implementer CLI with the failure logs.
      CI-infra-only fixes (workflow YAML, pins, flags) take a fast lane —
      orchestrator micro-review instead of a full adversarial round; runner
      flakes just get rerun. The watcher never fixes or pushes: unreviewed
      fix-pushes onto a red compound it (every gate in the field session that
      birthed this rule caught a real bug).
- [ ] Never merge a branch while a delegate's uncommitted work sits in the
      checkout — commit or stash first.
- [ ] Know the project's canonical suite invocations (some suites must run in their
      own process — mixed collections produce phantom failures).
- [ ] Fixture bugs in delegate tests are **assembly work** — diagnose and fix
      directly, don't round-trip.
- [ ] On resume/compaction: re-verify every "running" background task's liveness
      before reporting status (background procs die on session restart).
- [ ] Record durable decisions + gotchas to memory as they happen.

## References

- `references/pipelines.md` — the six pipelines in operational detail.
- `references/codex-recipes.md` — codex CLI invocation, enums, sandbox, liveness.
- `references/subagent-recipes.md` — worktrees, messaging, prompt requirements.
- `references/prompt-templates.md` — implementer / reviewer / TDD / content / re-gate skeletons.

## Per-project adaptation

The Cast maps to whatever models are available; effort tiers vary per install.
**Project rules (`CLAUDE.md`/`AGENTS.md`) override this skill's defaults** —
package managers, TDD requirements, commit/push vs PR policy, freeze windows,
copy-approval. Defaults here assume commit-per-logic-group to `main` + push when
green, no-PR. For PR-based projects, gates become PR reviews. See README.
