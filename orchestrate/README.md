# orchestrate

A Claude Code **skill** that encodes a multi-model orchestration workflow: a
capable, expensive main model (the *orchestrator*) plans, delegates, reviews every
diff, and integrates — while cheaper, reliable delegates (`codex exec`, subagents)
do the token-heavy implementation and independent review.

It is a practitioner's manual, not marketing. Every rule is tied to the concrete
failure it prevents. Written for an experienced engineer-operator.

## What's in here

| File | Purpose |
|---|---|
| `SKILL.md` | Entry point. Cast, the seven non-negotiable protocols, orchestrator duties. Read first. |
| `references/pipelines.md` | The seven pipelines (review gate, TDD, parallel tracks, frozen-file, spec, user-decision, operational-run) in operational detail. |
| `references/codex-recipes.md` | `codex exec` invocation, the reasoning-effort enum gotcha, sandbox modes, liveness, the filesystem-boundary preamble. |
| `references/subagent-recipes.md` | Worktree isolation, teammate messaging when an agent goes idle, the mandatory contents of an implementation prompt. |
| `references/prompt-templates.md` | Copy-paste skeletons: codex implementer, adversarial reviewer, TDD test author, content/pack author, re-gate, operational run. |

## Install

```bash
git clone git@github.com:Chasonnnn/agentic-engineering-skills-personal.git ~/agentic-engineering-skills-personal
ln -s ~/agentic-engineering-skills-personal/orchestrate ~/.claude/skills/orchestrate
```

Claude Code discovers skills under `~/.claude/skills/`. The skill activates on
phrases like "orchestrate this", "delegate to codex/opus", "act as orchestrator",
or proactively when a session starts delegating implementation to CLI
agents/subagents.

## Update

```bash
git -C ~/agentic-engineering-skills-personal pull
```

## Per-project adaptation

This skill ships **defaults**, not laws. Adapt on two axes:

### 1. The Cast — which models play which role

The defaults assume the interactive session's model orchestrates, `codex exec`
implements backend, and a Claude Opus subagent handles frontend/design/review;
the per-role effort tiers live in the Cast table in `SKILL.md`. Remap freely:

- **Orchestrator** = whatever runs the interactive session (the most
  capable/expensive model you have).
- **Implementer** = any strong CLI coding agent (`codex exec`, another Claude
  session, etc.). The only hard rule is that it is *not* the reviewer.
- **Reviewer** = a **different model family** from the implementer, ideally.
- **Effort tiers** (`high`, `xhigh`, …) are per-install — verify each value on
  your CLI with the two-step probe in `codex-recipes.md` before relying on it.

### 2. Project rules override this skill

When the project's `CLAUDE.md` / `AGENTS.md` conflicts with these defaults, **the
project wins**. Read the project's rules first and let them override:

- **Package managers** (this skill is manager-agnostic; the project names `uv` /
  `npm` / etc.).
- **TDD requirement** — some projects mandate it for all backend work; honor that
  over the skill's "backend features" scoping.
- **Commit/push vs PR** — the skill's default is commit-per-logic-group to `main`
  + push when green (no PR). For **PR-based** projects, the review **gates become
  PR reviews**: the reviewer's `VERDICT: MERGE` maps to an approving PR review,
  and pushes become merges.
- **Freeze windows** — respect the project's pilot/production freeze milestones;
  hold risky merges behind them (see the frozen-file protocol).
- **Copy-approval** — if the project requires user sign-off on user-visible copy,
  route wording changes to the user as options rather than shipping them.

## Contributing back

Edit files locally, commit, and push to `origin/main`. The skill is versioned in
git; `git pull` picks up updates on every machine it's installed on.
