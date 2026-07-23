# agentic-engineering-skills-personal

Private collection of reusable Claude Code skills, shared across projects.

## Install

Clone once, then symlink each skill into the personal skills directory:

```sh
git clone git@github.com:Chasonnnn/agentic-engineering-skills-personal.git ~/agentic-engineering-skills-personal
ln -s ~/agentic-engineering-skills-personal/board-sync ~/.claude/skills/board-sync
ln -s ~/agentic-engineering-skills-personal/github-pr-validation-loop ~/.claude/skills/github-pr-validation-loop
ln -s ~/agentic-engineering-skills-personal/orchestrate ~/.claude/skills/orchestrate
```

New machines: repeat both steps. Updating: `git -C ~/agentic-engineering-skills-personal pull` (symlinks pick up changes automatically).

## Skills

| Skill | What it does |
| --- | --- |
| [board-sync](board-sync/SKILL.md) | Sync planning state (specs/ADRs/roadmap) to a GitHub Project board as epic issues with nested sub-issues — epics on the board, slices hidden under them — plus an optional stale-issue refresh. |
| [github-pr-validation-loop](github-pr-validation-loop/SKILL.md) | Audit open PRs against the current base branch, reimplement valid findings cleanly, close invalid or superseded noise with evidence, and monitor CI through completion. |
| [orchestrate](orchestrate/SKILL.md) | Multi-model orchestration: the main session plans/reviews/commits while codex + subagents implement, with cross-model review gates. (Folded in from `orchestrate-skill` with history; that repo is archived.) |

## Conventions

- One directory per skill, `SKILL.md` inside, frontmatter per Claude Code skill format.
- Skills here are project-agnostic: per-project facts (repo, board number, doc paths) are inputs, never hardcoded.
- House style per the `writing-great-skills` reference: user-invoked by default (`disable-model-invocation: true`), ordered steps with checkable completion criteria, gotchas as in-skill reference.
