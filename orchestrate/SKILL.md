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

| Role | Model | Effort | Work |
|---|---|---|---|
| Orchestrator | The session model (Fable or Opus, whichever panel runs this skill) | `high`; the user adjusts it | Decide scope, dispatch, validate findings, integrate, commit, report |
| Codex design lane | `gpt-6-astra` | `xhigh` | On the user's explicit request only: work plan review, design critique, second opinions |
| Codex build lane | `gpt-6.1-sol` | `xhigh` | Backend implementation, bug fixes, sequential tasks in one track |
| Claude subagent | Opus 5.5 via the `opus-high` agent type | `high` | Frontend, artifacts, mock-ups, HTML pages, prompt text, code review |
| Chore agent | Sonnet via the `sonnet-high` agent type | `medium` | CI watch, board updates, log watch; read-only on code |

Pass `--model` and `--effort` to the Codex runner for each lane; do not rely on `~/.codex/config.toml`. Use the agent types, whose frontmatter pins model and effort: the Agent tool's `model` field cannot express a full model ID, and an unpinned subagent inherits the session model. Escalate one task to `opus-xhigh` or `opus-max` only when it earns it. Fable is an orchestrator only: no Fable delegates, reviewers or raters.

Implementation boundary: Sol owns backend work, including server-side code that lives in the frontend app (route handlers, server actions, proxies, auth plumbing). Opus owns React components, the design surface, and every mock-up, HTML page, decision book and review page. Opus writes all prompt, schema-description and participant-facing text; Codex writes none. One fresh Opus reviewer reviews all built work; there is no dual review. Astra runs only when the user explicitly asks for a second opinion, plan review or design critique. The orchestrator never dispatches Astra on its own judgment.

These are installation defaults. Preserve explicit user/project choices and use available capabilities; do not silently substitute an unavailable model.

## The orchestrator never blocks

The orchestrator's turn must stay free to receive delegate reports and dispatch the next track.

- The orchestrator dispatches, reads reports, decides, and commits. It implements nothing, including one-line follow-ups and test fixes; those go to the standing lane that owns the track.
- Any command that can exceed about 2 minutes (full suites, builds, browser QA, data jobs) runs as a tracked background command or on a delegate, never in the foreground.
- Each delegate writes its full report to a file and returns at most five lines: verdict, counts, the report path, and what it needs. Read the file only when a decision depends on it.
- Never wait on one delegate while dispatchable work exists.

## Standing lanes

Open one long-lived session per track and keep it for the whole track. Do not spawn a new agent per task.

- **Build lane:** one Sol session per track, started with the runner and continued with `--resume <session id>`. It implements, repairs gate findings, and takes the track's next sequential task with its context intact. Record each lane's session ID, worktree and state in the dispatch plan.
- **Design lane:** opened only on the user's explicit request. One Astra session per piece of work, resumed for each round of plan review or second opinion.
- **Opus lane:** one named Opus subagent per frontend track or review, continued with SendMessage.
- Start a fresh session only for the final independent gate, for a stalled or exhausted lane, or for a new unrelated track.
- **Remote machine:** when the project has an always-on second machine, send full suites, delivery checkpoints, stress runs and Docker lanes to it in its own worktree. The orchestrator's machine keeps short affected checks.

## Coordination decisions

1. Give each lane a bounded outcome, owned files or worktree, relevant interfaces, and allowed side effects. Preserve existing dirty work. Freeze shared names and assign one owner to shared integration files when tracks depend on them.
2. Before the first dispatch, write a dispatch plan in the session: one line per track naming its lane, session ID, the tracks that run concurrently, and the data dependency that forces any serialization. Re-issue the plan whenever a track is added. Parallelize independent work and serialize only on true data dependencies. Split work by context, not by role: one lane builds a feature and its tests. Isolate concurrent writers; a reviewer must see stable source.
3. Before implementation, write the acceptance list for the change to a file: each criterion and the check that proves it. The implementer and every reviewer receive the same file. Run the review loop in [references/pipelines.md](references/pipelines.md): two rounds by default, three at most.
4. Validate findings against source and merge them into one list before the implementer sees any. Reviewers never message the implementer and never spawn agents of their own.
5. Review the delegate's evidence and spot-check high-risk seams. Verify affected consumers and integration behavior before claiming an end-to-end result. Match tests to the change and project requirements.
6. Report completed, partial, failed, and unverified work separately. A clean review is one prerequisite, not authorization for publishing or changing live state. Apply existing commit, push, deployment, and memory permissions; this skill grants none.

## Field rules

Each rule comes from an observed failure. Apply them without waiting for a repeat.

- Wrap every long background run on macOS in `caffeinate -s` (or arm `caffeinate -s -w <pid>` on a running one). Machine sleep wedges sockets into permanent hangs and corrupts in-flight test runs. Run a log-growth watchdog over background CLI logs (about 10 minutes without growth while the pid lives); write it in Python, since macOS bash 3.2 lacks associative arrays. Harness-tracked subagents are exempt. Launch Codex runs as the codex skill's `references/execution.md` specifies; never detach them.
- Delegated browser live QA runs through codex chrome-control in an interactive session, the only codex work exempt from headless `codex exec`. It must drive a visible browser window; chrome-control can silently run headless, and a headless run does not satisfy a live-QA gate. Instruct the agent to stop rather than fall back.
- For race, stale-state, or synchronization bugs, decide where the owned truth should live (usually server-side) and change that seam before dispatching any fix. Do not dispatch rounds that patch client-observable symptoms.
- When two failures share a defect class, stop fixing incidents one at a time. Dispatch one read-only class-wide audit and fix every instance in one gated round.
- Product and writing rules bind the orchestrator's own artifacts (mockups, docs, decision batches) exactly as they bind delegate output. Self-review against the same checklist before delivering.
- Fixture bugs in delegate-written tests and CI-infra-only fixes (workflow YAML, pins, flags) go to the track's standing lane as one resumed message, with no review round. Runner flakes get rerun, not reviewed.
- Know the project's canonical suite invocations. Some suites must run in their own process; mixed collections produce phantom failures.

## Research sessions and peer panels

Sessions that orchestrate research (literature fan-outs, experiment audits, label adjudication) follow the same decisions with these additions.

- Keep a dispatch ledger for the session: every delegated item with owner, state (queued, running, blocked, delivered, verified) and artifact path. Answer "what is running and what has not started" from the ledger, and advance every queued item before reporting; a request that was accepted but never dispatched is a failure to report on its own line.
- Herdr peer panels (another Claude or Codex session in the same workspace) are collaborators, not delegates. Read a peer's panel before dispatching overlapping work. Changes to experiments, data or services owned by a peer go to that peer as a request; do not edit them from this session. Record what was handed off in the ledger.
- Codex quota exhaustion is a distinct stall cause. When the CLI reports it, mark affected items blocked, move the build to an Opus lane, keep the gate with a fresh Opus reviewer, and resume the recorded Codex sessions when the user says quota is restored instead of redispatching from scratch.
- Label, score and rubric adjudication uses blind evaluators across model families (one Astra, one Opus) with identical prompts and no access to each other's output. Compare agreement before treating either result as ground truth.
- Around a launch or data-collection window, dispatch a read-only `sonnet-high` log-watcher on a fixed cadence (the user's stated interval, default 5 to 10 minutes) that reports errors and milestones and never restarts services or edits code.
- Research and audit sessions end in an HTML report built by an Opus subagent unless the user asks for another format. Product and writing rules apply to it.

Use [references/codex-recipes.md](references/codex-recipes.md) for Codex delegation and [references/subagent-recipes.md](references/subagent-recipes.md) for native or Claude agents. Use [references/prompt-templates.md](references/prompt-templates.md) only when constructing a dispatch. Do not load every reference by default.
