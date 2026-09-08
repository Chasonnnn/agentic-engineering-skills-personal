---
name: orchestrate
description: Coordinate CLI agents or subagents for implementation and independent review when the user asks for delegation or a multi-agent workflow.
---

# Orchestrate

Choose task boundaries, delegate ownership, and integration evidence. Use `codex` for a standalone second opinion; orchestration is useful when work needs coordination across delegates.

## Roles and defaults

| Role | Default | Responsibility |
|---|---|---|
| Orchestrator | Main session | Decide scope, coordinate tracks, validate findings, integrate and report |
| Codex CLI | `gpt-6-astra`, medium effort for every session | Implementation, review of another agent's work, and second opinions |
| Claude subagent | Opus, high effort | Implementation, research, test authoring, and independent review |

These are installation defaults. Preserve explicit user/project choices and use available capabilities; do not silently substitute an unavailable model. The orchestrator may implement directly when delegation adds no value.

## Coordination decisions

1. Give each delegate a bounded outcome, owned files or worktree, relevant interfaces, verification criteria, and allowed side effects. Preserve existing dirty work. Freeze shared names and assign one owner to shared integration files when tracks depend on them.
2. Parallelize independent work when authorized. Isolate concurrent writers; a reviewer must see stable source. Read only the applicable procedure in [references/pipelines.md](references/pipelines.md).
3. Keep implementer and reviewer distinct for each reviewed delta, preferably across model families. Small, low-risk changes under roughly 50 lines may receive direct orchestrator review. Production-critical logic and larger logical changes still receive an independent gate.
4. Validate actionable findings against source before assigning fixes. Review the fix delta and confirm prior findings are resolved. If repeated rounds reveal a design problem, reassess it rather than adding patches indefinitely.
5. Review the delegate's evidence and spot-check high-risk seams. The independent reviewer reads the full scoped diff; the orchestrator reads it directly in the small-change lane. Verify affected consumers and integration behavior before claiming an end-to-end result. Match tests to the change and project requirements.
6. Report completed, partial, failed, and unverified work separately. A clean review is one prerequisite, not authorization for publishing or changing live state. Apply existing commit, push, deployment, and memory permissions; this skill grants none.

Use [references/codex-recipes.md](references/codex-recipes.md) for Codex delegation and [references/subagent-recipes.md](references/subagent-recipes.md) for native or Claude agents. Use [references/prompt-templates.md](references/prompt-templates.md) only when constructing a dispatch. Do not load every reference by default.
