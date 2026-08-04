# agentic-engineering-skills-personal

Private collection of reusable Claude Code skills, shared across projects.

## Install

Clone once, then symlink each skill into the personal skills directory:

```sh
git clone git@github.com:Chasonnnn/agentic-engineering-skills-personal.git ~/agentic-engineering-skills-personal
ln -s ~/agentic-engineering-skills-personal/board-sync ~/.claude/skills/board-sync
ln -s ~/agentic-engineering-skills-personal/codex ~/.claude/skills/codex
ln -s ~/agentic-engineering-skills-personal/github-pr-validation-loop ~/.claude/skills/github-pr-validation-loop
ln -s ~/agentic-engineering-skills-personal/no-use-effect ~/.claude/skills/no-use-effect
ln -s ~/agentic-engineering-skills-personal/orchestrate ~/.claude/skills/orchestrate
ln -s ~/agentic-engineering-skills-personal/review-and-remediate-server-logs ~/.claude/skills/review-and-remediate-server-logs
```

New machines: repeat both steps. Updating: `git -C ~/agentic-engineering-skills-personal pull` (symlinks pick up changes automatically).

## Skills

| Skill | What it does |
| --- | --- |
| [board-sync](board-sync/SKILL.md) | Sync planning state (specs/ADRs/roadmap) to a GitHub Project board as epic issues with nested sub-issues — epics on the board, slices hidden under them — plus an optional stale-issue refresh. |
| [codex](codex/SKILL.md) | Wraps the OpenAI Codex CLI for an independent second opinion: review (pass/fail gate on a diff), challenge (adversarial break-it), consult (ask anything, with session continuity). Ported from [gstack](https://github.com/garrytan/gstack)'s `/codex` skill — see credit note below. |
| [github-pr-validation-loop](github-pr-validation-loop/SKILL.md) | Audit open PRs against the current base branch, reimplement valid findings cleanly, close invalid or superseded noise with evidence, and monitor CI through completion. |
| [no-use-effect](no-use-effect/SKILL.md) | Prefer explicit React data flow, replace ad-hoc Effects with derived state, event handlers, query libraries, or keyed remounting, and contain legitimate external synchronization in named hooks. |
| [orchestrate](orchestrate/SKILL.md) | Multi-model orchestration: the main session plans/reviews/commits while codex + subagents implement, with cross-model review gates. (Folded in from `orchestrate-skill` with history; that repo is archived.) |
| [review-and-remediate-server-logs](review-and-remediate-server-logs/SKILL.md) | Review live server logs, prioritize actionable failures, reproduce and fix their causes, validate through CI, and verify the result after an authorized deployment. |

## Conventions

- One directory per skill, `SKILL.md` inside, frontmatter per Claude Code skill format.
- Skills here are project-agnostic: per-project facts (repo, board number, doc paths) are inputs, never hardcoded.
- House style per the `writing-great-skills` reference: user-invoked by default (`disable-model-invocation: true`), with automatic invocation retained when a skill explicitly defines activation conditions; use ordered steps with checkable completion criteria and keep gotchas in-skill.

## Credit

`codex/` is a standalone port of the `/codex` skill from [gstack](https://github.com/garrytan/gstack) (Garry Tan, MIT license) — the original wraps the OpenAI Codex CLI as one of ~30 skills in a much larger multi-agent toolkit. This port keeps the review/challenge/consult mechanics and drops everything wired into gstack's own infrastructure (telemetry, question-tuning auto-decide, checkpoint mode, gbrain sync, the `D<N>` AskUserQuestion format), so it runs standalone with no dependency on gstack being installed.
