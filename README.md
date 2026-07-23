# claude-skills

Private collection of reusable Claude Code skills, shared across projects.

## Install

Clone once, then symlink each skill into the personal skills directory:

```sh
git clone git@github.com:Chasonnnn/claude-skills.git ~/claude-skills
ln -s ~/claude-skills/board-sync ~/.claude/skills/board-sync
```

New machines: repeat both steps. Updating: `git -C ~/claude-skills pull` (symlinks pick up changes automatically).

## Skills

| Skill | What it does |
| --- | --- |
| [board-sync](board-sync/SKILL.md) | Sync planning state (specs/ADRs/roadmap) to a GitHub Project board as epic issues with nested sub-issues — epics on the board, slices hidden under them — plus an optional stale-issue refresh. |
| [orchestrate](orchestrate/SKILL.md) | Multi-model orchestration: the main session plans/reviews/commits while codex + subagents implement, with cross-model review gates. (Folded in from `orchestrate-skill` with history; that repo is archived.) |

## Conventions

- One directory per skill, `SKILL.md` inside, frontmatter per Claude Code skill format.
- Skills here are project-agnostic: per-project facts (repo, board number, doc paths) are inputs, never hardcoded.
- House style per the `writing-great-skills` reference: user-invoked by default (`disable-model-invocation: true`), ordered steps with checkable completion criteria, gotchas as in-skill reference.
