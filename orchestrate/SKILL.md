---
name: orchestrate
description: >-
  Coordinate CLI agents or subagents for implementation and independent review.
  Use when the user says "orchestrate this", "delegate to codex/opus",
  "multi-model", "act as orchestrator", or asks for a multi-agent workflow.
  Use proactively whenever a session delegates substantive implementation to
  codex exec or subagents while the main session plans, reviews, and integrates.
---

# Orchestrate

Choose task boundaries, delegate ownership, and integration evidence. Use `codex` for a standalone second opinion; orchestration is useful when work needs coordination across delegates.

## Roles and defaults

| Role | Default | Responsibility |
|---|---|---|
| Orchestrator | Main session | Decide scope, coordinate tracks, validate findings, integrate and report |
| Codex CLI | `gpt-6-astra`, `xhigh` effort for every session (owner decision 2026-09-10; pass `--effort xhigh` to the runner or leave it unset so `~/.codex/config.toml` applies; never pass medium unless the user asks) | Backend implementation, review of another agent's work, and second opinions |
| Claude subagent | Opus 5.5 (`claude-opus-5-5`) via the `opus-xhigh` agent type, whose frontmatter pins the model and effort; the Agent tool's `model` field cannot express a full model ID and the `opus` alias can resolve to an older Opus. `opus-max` only when the task earns it | Frontend implementation, research, test authoring, and independent review |

Implementation boundary: Codex owns backend work; the Opus subagent owns frontend work. Mock-ups, HTML pages, decision books and review pages always go to an Opus subagent, even when the orchestrator could write them directly. Server-side code counts as backend even when it lives in the frontend app (route handlers, server actions, proxies, auth plumbing). React components and the design surface stay with Opus. Cross-model review follows from this split: Codex-built backend gets an Opus gate, Opus-built frontend gets a Codex gate.

These are installation defaults. Preserve explicit user/project choices and use available capabilities; do not silently substitute an unavailable model. The orchestrator may implement directly when delegation adds no value.

## Coordination decisions

1. Give each delegate a bounded outcome, owned files or worktree, relevant interfaces, verification criteria, and allowed side effects. Preserve existing dirty work. Freeze shared names and assign one owner to shared integration files when tracks depend on them.
2. Parallelize independent work. Serialize only on true data dependencies; never idle on one delegate while dispatchable work exists, and advance other tracks while a gate blocks one. Isolate concurrent writers; a reviewer must see stable source. Read only the applicable procedure in [references/pipelines.md](references/pipelines.md).
3. Keep implementer and reviewer distinct for each reviewed delta, preferably across model families. Small, low-risk changes under roughly 50 lines may receive direct orchestrator review. Production-critical logic and larger logical changes still receive an independent gate.
4. Validate actionable findings against source before assigning fixes. Review the fix delta and confirm prior findings are resolved. If repeated rounds reveal a design problem, reassess it rather than adding patches indefinitely.
5. Review the delegate's evidence and spot-check high-risk seams. The independent reviewer reads the full scoped diff; the orchestrator reads it directly in the small-change lane. Verify affected consumers and integration behavior before claiming an end-to-end result. Match tests to the change and project requirements.
6. Report completed, partial, failed, and unverified work separately. A clean review is one prerequisite, not authorization for publishing or changing live state. Apply existing commit, push, deployment, and memory permissions; this skill grants none.

## Field rules

Each rule comes from an observed failure. Apply them without waiting for a repeat.

- Wrap every long background run on macOS in `caffeinate -s` (or arm `caffeinate -s -w <pid>` on a running one). Machine sleep wedges sockets into permanent hangs and corrupts in-flight test runs. Run a log-growth watchdog over background CLI logs (about 10 minutes without growth while the pid lives); write it in Python, since macOS bash 3.2 lacks associative arrays. Harness-tracked subagents are exempt.
- Delegated browser live QA runs through codex chrome-control in an interactive session, the only codex work exempt from headless `codex exec`. It must drive a visible browser window; chrome-control can silently run headless, and a headless run does not satisfy a live-QA gate. Instruct the agent to stop rather than fall back.
- For race, stale-state, or synchronization bugs, decide where the owned truth should live (usually server-side) and change that seam before dispatching any fix. Do not dispatch rounds that patch client-observable symptoms.
- When two failures share a defect class, stop fixing incidents one at a time. Dispatch one read-only class-wide audit and fix every instance in one gated round.
- Product and writing rules bind the orchestrator's own artifacts (mockups, docs, decision batches) exactly as they bind delegate output. Self-review against the same checklist before delivering.
- Fixture bugs in delegate-written tests are assembly work: diagnose and fix directly instead of a round-trip. CI-infra-only fixes (workflow YAML, pins, flags) take the small-change lane; runner flakes get rerun, not reviewed.
- Know the project's canonical suite invocations. Some suites must run in their own process; mixed collections produce phantom failures.

## Research sessions and peer panels

Sessions that orchestrate research (literature fan-outs, experiment audits, label adjudication) follow the same decisions with these additions.

- Keep a dispatch ledger for the session: every delegated item with owner, state (queued, running, blocked, delivered, verified) and artifact path. Answer "what is running and what has not started" from the ledger, and advance every queued item before reporting; a request that was accepted but never dispatched is a failure to report on its own line.
- Herdr peer panels (another Fable, Astra or Codex session in the same workspace) are collaborators, not delegates. Read a peer's panel before dispatching overlapping work. Changes to experiments, data or services owned by a peer go to that peer as a request; do not edit them from this session. Record what was handed off in the ledger.
- Codex quota exhaustion is a distinct stall cause. When the CLI reports it, mark affected items blocked, switch the gate to the cross-family fallback (Opus implements, Fable reviews, or the reverse), and resume the recorded Codex sessions when the user says quota is restored instead of redispatching from scratch.
- Label, score and rubric adjudication uses blind evaluators across model families (one Fable, one Astra, or Opus when a family is unavailable) with identical prompts and no access to each other's output. Compare agreement before treating either result as ground truth.
- Around a launch or data-collection window, dispatch a read-only Opus log-watcher on a fixed cadence (the user's stated interval, default 5 to 10 minutes) that reports errors and milestones and never restarts services or edits code.
- Research and audit sessions end in an HTML report built by an Opus subagent unless the user asks for another format. Product and writing rules apply to it.

Use [references/codex-recipes.md](references/codex-recipes.md) for Codex delegation and [references/subagent-recipes.md](references/subagent-recipes.md) for native or Claude agents. Use [references/prompt-templates.md](references/prompt-templates.md) only when constructing a dispatch. Do not load every reference by default.
