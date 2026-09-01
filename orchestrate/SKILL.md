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
| **Codex CLI** | `codex exec`, gpt-5.6-sol — implementation @ **high**, `xhigh` for genuinely complicated slices (ultra retired); adversarial CODE-review gates & re-gates @ **high** only, never xhigh; architectural/major-decision second opinions @ **xhigh** | token-heavy backend implementation; independent second opinion on large plans/specs | review its own implementation; edit tests it was told not to |
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
   **Finder-fixes-verified variant:** reviewer finds →
   the other model (or the orchestrator directly) verifies each finding against
   the code → the finder's session resumes with write access to fix exactly the
   verified set → the other family re-gates the fix delta. Implementer ≠ reviewer
   holds **per round**, not per slice; roles may swap between rounds. Prefer this
   when findings are precise (file:line + prescribed fix) — the finder carries
   the deepest defect context and a handoff transfers nothing but the findings'
   text. *Prevents:* context loss in the find→fix handoff; fixing hallucinated
   findings.
   **Micro-review lane (small diffs):** diffs under ~50 lines may take a direct
   orchestrator line-by-line review instead of a delegate gate round — the
   dispatch→report→verdict cycle costs more than the diff warrants. Hard
   exclusions: logic-groups, and any diff touching the project's
   production-critical surfaces (e.g. scoring/tenancy/auth) gets the full gate
   regardless of size. *Prevents:* 30-minute gate cycles on 20-line fixes.
2. **TDD pipeline (backend)** — test-author subagent writes FAILING tests + an
   interface-contract doc against a frozen interface; orchestrator reviews the
   contract; codex implements to green and **may not edit tests**; adversarial
   review; commit per logic-group. Small slices may run the implementer-authored
   variant: failing tests first with red tails in the report, and the gate
   attacks test integrity explicitly (pipelines §2). *Prevents:* implementation
   that defines its own success criteria.
3. **Parallel tracks + assembly** — independent tracks run at once (subagents in
   isolated worktrees committing locally; codex in the main checkout leaving work
   **uncommitted**). Freeze names/ids before dispatch; agents "flag loudly rather
   than invent". Canon-doc/status headers (e.g. a "Last verified" line) are
   assembly-owned: delegates report the bump, the orchestrator writes it once —
   two tracks bumping the same header is a guaranteed conflict. Orchestrator
   assembles, reconciles deviations, runs full suites, then **one** adversarial
   review over the whole diff before push. *Prevents:* merge chaos and invented
   interfaces.
4. **Frozen-file protocol (production-critical)** — before refactoring a frozen
   file, land a GOLDEN INVARIANCE TEST pinning its observable contract with
   **inline** expected values; convert one seam at a time, behavior-preserving.
   *Prevents:* a "safe refactor" that silently changes output.
5. **Spec pipeline (big designs)** — research fan-out (read-only explorers) →
   synthesis draft → **adversarial verification** against the code (drafts
   contain confident falsehoods) → final spec with the user's decisions recorded.
   Cap at 2 iterations. For major specs run TWO verification lenses **in
   parallel**: a fact-verifier (every citation opened at the cited lines,
   negative claims attacked) and a cross-model architectural second opinion
   (codex @ xhigh). They catch disjoint failure modes — transcription errors
   vs. wrong-shaped designs — and neither substitutes for the other.
   *Prevents:* shipping a spec built on plausible fiction.
6. **User decision protocol** — decisions shaping scope/architecture/timeline go
   to the user as structured questions with a **recommended** option; record them
   in the plan/memory. Everything else the orchestrator decides and reports.
7. **Operational-run pipeline (live systems)** — delegate runs that operate the
   system rather than change it (stack up, live sweeps, runbooks) carry
   enumerated hard-stop conditions, verbatim-evidence capture, a canonical
   run-record file, started-vs-inherited cleanup accounting, and the rule that
   recovery is an orchestrator decision — the delegate stops and reports, never
   improvises a resubmit or state edit. *Prevents:* improvised recovery on live
   state; partial success reported as success; orphaned services.
   **Browser live QA:** live QA that drives a
   browser, when delegated to codex, runs through codex's **chrome-control**
   (the bundled Chrome plugin driving the user's real Chrome) — not
   computer-use — in an interactive codex session (e.g. a Herdr pane), not
   `codex exec`. This and computer-use QA testing are the only codex work
   exempt from exec mode; all implementation stays headless `codex exec`.
   Applies only to browser live QAs. The QA must drive a REAL, VISIBLE
   browser window the owner can watch — a headless run does not satisfy a
   live-QA gate (chrome-control may silently run headless; instruct the
   agent explicitly and have it stop rather than fall back).

## Reviewer output contract (every gate)

Numbered findings `[P1]` must-fix / `[P2]` should-fix / `[NIT]`, each with
`file:line` + a concrete fix. One line per passing check. Ends **exactly**:
`VERDICT: MERGE` (or `PUSH`) or `VERDICT: FIX-FIRST`. No clean verdict → no merge.

## Orchestrator duties (checklist)

- [ ] **Maximize wall-clock concurrency.** Serialize only on true data
      dependencies. When a gate blocks one track, advance the others; run
      independent gates/audits in parallel; a delta re-gate that costs no
      wall-clock (another track is the long pole anyway) is nearly free.
      Never idle waiting on a single delegate while dispatchable work exists.
- [ ] **Automated stall watchdog on background CLI delegates.** Manual tail
      checks don't scale past one delegate: run a watchdog process (log-growth
      based, ~10 min no-growth threshold while the pid lives) over every
      background CLI log; harness-tracked subagents are exempt (they notify).
      Write watchdogs in python — macOS ships bash 3.2 (no associative
      arrays), a field hit. On macOS, wrap every long background run in
      `caffeinate -s` (or arm `caffeinate -s -w <pid>` on one already running) —
      machine sleep wedges sockets into permanent hangs and corrupts in-flight
      test runs, a field hit that cost 6 hours.
- [ ] **Architecture-first on race/state bugs.** Before dispatching a fix for a
      race, stale-state, or synchronization bug, decide where the owned truth
      should live (usually server-side) and change that seam — never dispatch
      rounds that patch client-observable symptoms. *Prevents:* serial
      FIX-FIRST cycles converging on a fragile approximation of the missing
      field (field hit: three gate rounds patching a client timer freeze; one
      server-exposed anchor field ended it and deleted the machinery).
- [ ] **Every delegate diff is reviewed before committing — but the orchestrator
      reads full diffs only in the micro-review lane.** Reading whole diffs
      line-by-line burns exactly the orchestrator context delegation exists to
      save (user directive 2026-09-01). Lanes: gated slices/batches → the
      adversarial gate is the diff reader; the orchestrator reads the verdict +
      P1s and spot-checks only high-risk seams. Micro-review lane (<50 lines,
      no gate) → the orchestrator reads the diff directly (trivially cheap).
      Extractions/refactors → the GATE PROMPT must require line-by-line
      comparison against the pre-change original via `git show <base>:<file>`
      (moved code byte-similar, helper defaults match, error types preserved);
      the orchestrator assigns that check, never performs it.
- [ ] **Verify reviewer findings too, not just delegate diffs.** Before applying
      a gate's [P1] fixes, re-check each factual claim against the repo yourself
      (reviewers assert with confidence either way). This cuts both ways: a gate
      may refute a claim the orchestrator itself "confirmed" — field hit: a root-cause claim traced to a script that turned out to be
      absent from the deployed data path (`supplement_row_count: 0`). Verify,
      then fix; never forward or apply unverified verdicts.
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
- [ ] **Second-occurrence sweep:** when two failures share a defect class, stop
      fixing incidents one at a time — dispatch a class-wide audit and fix every
      instance in one gated round. (Field hit: five instruction/validator-gap
      incidents fixed serially at ~50 min per live cycle; a sweep after #2 would
      have saved two cycles. Detail in pipelines §7.)
- [ ] On resume/compaction: re-verify every "running" background task's liveness
      before reporting status (background procs die on session restart).
- [ ] Product rules bind the orchestrator's OWN artifacts (mockups, docs,
      decision batches) exactly as they bind delegate output — self-review
      against the same checklist before delivering to the user. (Field hit: owner had to catch a no-helper-text violation in
      orchestrator-authored mockups while the orchestrator was enforcing that
      very rule on delegates.)
- [ ] Record durable decisions + gotchas to memory as they happen.

## References

- `references/pipelines.md` — the seven pipelines in operational detail.
- `references/codex-recipes.md` — codex CLI invocation, enums, sandbox, liveness.
- `references/subagent-recipes.md` — worktrees, messaging, prompt requirements,
  headless `claude -p` gates.
- `references/prompt-templates.md` — implementer / reviewer / TDD / content /
  re-gate / operational-run skeletons.

## Per-project adaptation

The Cast maps to whatever models are available; effort tiers vary per install.
**Project rules (`CLAUDE.md`/`AGENTS.md`) override this skill's defaults** —
package managers, TDD requirements, commit/push vs PR policy, freeze windows,
copy-approval. Defaults here assume commit-per-logic-group to `main` + push when
green, no-PR. For PR-based projects, gates become PR reviews. See README.
