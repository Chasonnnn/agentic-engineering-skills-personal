# agentic-engineering-skills-personal

Private collection of reusable Claude Code skills, shared across projects.

## Install

Clone once, then symlink each skill into the personal skills directory:

```sh
git clone git@github.com:Chasonnnn/agentic-engineering-skills-personal.git ~/agentic-engineering-skills-personal
ln -s ~/agentic-engineering-skills-personal/agy ~/.claude/skills/agy
ln -s ~/agentic-engineering-skills-personal/ambitious ~/.claude/skills/ambitious
ln -s ~/agentic-engineering-skills-personal/audit-skill ~/.claude/skills/audit-skill
ln -s ~/agentic-engineering-skills-personal/board-sync ~/.claude/skills/board-sync
ln -s ~/agentic-engineering-skills-personal/authmux ~/.claude/skills/authmux
ln -s ~/agentic-engineering-skills-personal/codex ~/.claude/skills/codex
ln -s ~/agentic-engineering-skills-personal/github-pr-validation-loop ~/.claude/skills/github-pr-validation-loop
ln -s ~/agentic-engineering-skills-personal/no-use-effect ~/.claude/skills/no-use-effect
ln -s ~/agentic-engineering-skills-personal/opencode ~/.claude/skills/opencode
ln -s ~/agentic-engineering-skills-personal/orchestrate ~/.claude/skills/orchestrate
ln -s ~/agentic-engineering-skills-personal/retro ~/.claude/skills/retro
ln -s ~/agentic-engineering-skills-personal/review-and-remediate-server-logs ~/.claude/skills/review-and-remediate-server-logs
ln -s ~/agentic-engineering-skills-personal/blast-radius ~/.claude/skills/blast-radius
ln -s ~/agentic-engineering-skills-personal/bro ~/.claude/skills/bro
ln -s ~/agentic-engineering-skills-personal/correct ~/.claude/skills/correct
ln -s ~/agentic-engineering-skills-personal/ketchup ~/.claude/skills/ketchup
ln -s ~/agentic-engineering-skills-personal/principle-explain-the-number ~/.claude/skills/principle-explain-the-number
ln -s ~/agentic-engineering-skills-personal/principle-prove-it-works ~/.claude/skills/principle-prove-it-works
ln -s ~/agentic-engineering-skills-personal/show-me-your-work ~/.claude/skills/show-me-your-work
```

Agent definitions used by `orchestrate` load from `~/.claude/agents/`:

```sh
mkdir -p ~/.claude/agents
for f in opus-high opus-xhigh opus-max sonnet-high Explore; do
  ln -s ~/agentic-engineering-skills-personal/agents/$f.md ~/.claude/agents/$f.md
done
```

Workflows (Claude Code `Workflow` tool scripts) load from `~/.claude/workflows/`:

```sh
mkdir -p ~/.claude/workflows
ln -s ~/agentic-engineering-skills-personal/workflows/retro-week.js ~/.claude/workflows/retro-week.js
```

Mods (Claude Code function-hook plugins) load from `CLAUDE_CODE_PLUGIN_DIRS` in the `env` block of `~/.claude/settings.json`:

```json
"CLAUDE_CODE_PLUGIN_DIRS": "~/agentic-engineering-skills-personal/mods/progress"
```

New machines: repeat both steps. Updating: `git -C ~/agentic-engineering-skills-personal pull` (symlinks pick up changes automatically).

## Skills

| Skill | What it does |
| --- | --- |
| [agy](agy/SKILL.md) | User-invoked (`/agy`). Wraps the Antigravity CLI (`agy`) for a Gemini 4 Argon second opinion with the same review, challenge, and consult modes and verdict contract as `codex`. Pinned to `gemini-4-argon-high`; read-only by default. |
| [ambitious](ambitious/SKILL.md) | User-invoked (`/ambitious`). Raises the current task along altitude, depth, and range, sets a measurable target with an outside check, then does the raised version. Based on [Felix Rieseberg's article](https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/). |
| [audit-skill](audit-skill/SKILL.md) | Audit or improve skill instructions and helpers with source-specific evidence; includes optional comparison guidance and the Provencher article reference. |
| [authmux](authmux/SKILL.md) | Resolve repository-bound authentication intent, verify provider identity evidence, route supported CLI commands through process-scoped contexts, and fail closed before wrong-account or wrong-project work. |
| [blast-radius](blast-radius/SKILL.md) | Find what a change breaks beyond the diff before it ships, prove the one safety fact by running code, and check live state (active users, in-flight work, rollback) for deploys. Ported from pstack. |
| [board-sync](board-sync/SKILL.md) | Sync planning state (specs/ADRs/roadmap) to a GitHub Project board as epic issues with nested sub-issues — epics on the board, slices hidden under them — plus an optional stale-issue refresh. |
| [bro](bro/SKILL.md) | Restate the last reply in plain words when the user says "what do you mean" or "I don't understand". Ported from pstack. |
| [codex](codex/SKILL.md) | Wraps the OpenAI Codex CLI for an independent second opinion: review (PASS/FAIL/INCOMPLETE on an explicit diff scope), challenge (adversarial break-it), consult (ask anything, with session continuity). Ported from [gstack](https://github.com/garrytan/gstack)'s `/codex` skill — see credit note below. |
| [correct](correct/SKILL.md) | User-invoked (`/correct`). Turn repeated agent mistakes into checks that fail, highest level first (architecture, types, lint, test, docs), each proven on a past mistake. Ported from pstack. |
| [dependency-modernization](dependency-modernization/SKILL.md) | Upgrade dependencies with official release review, local feature adoption, compatibility checks, and measured validation. |
| [github-pr-validation-loop](github-pr-validation-loop/SKILL.md) | Audit open PRs against the current base branch, reimplement valid findings cleanly, close invalid or superseded noise with evidence, and monitor CI through completion. |
| [ketchup](ketchup/SKILL.md) | Catch-up brief: what changed since the user's last message, live job and PR state, and numbered calls waiting on the user with a pick each. Ported from pstack. |
| [no-use-effect](no-use-effect/SKILL.md) | Prefer explicit React data flow, replace ad-hoc Effects with derived state, event handlers, query libraries, or keyed remounting, and contain legitimate external synchronization in named hooks. |
| [opencode](opencode/SKILL.md) | User-invoked (`/opencode`). Wraps the OpenCode CLI for a second opinion from any model it serves, with the same review, challenge, and consult modes and verdict contract as `codex`. Pinned to `cornell/nto.gemini-4-argon`; read-only by default through inline permission rules. |
| [orchestrate](orchestrate/SKILL.md) | Coordinates delegates, independent review, and integration; shares CLI execution with `codex`. (Folded in from `orchestrate-skill` with history; that repo is archived.) |
| [principle-explain-the-number](principle-explain-the-number/SKILL.md) | Reference principle (not auto-invoked): before trusting a metric, name its limiter, setup, data, spread, and rule out stale config or skipped work. The orchestrate review template points to it. Ported from pstack. |
| [principle-prove-it-works](principle-prove-it-works/SKILL.md) | Reference principle (not auto-invoked): verify against the real artifact, not a proxy. The orchestrate review template points to it. Ported from pstack. |
| [retro](retro/SKILL.md) | User-invoked (`/retro`). Retrospective on a coding session: proposes environment fixes (navigation pointers, automated checks, reviewer rules, steering-file cleanup, tool economy, information access), ranked by severity. |
| [review-and-remediate-server-logs](review-and-remediate-server-logs/SKILL.md) | Review live server logs, prioritize actionable failures, reproduce and fix their causes, validate through CI, and verify the result after an authorized deployment. |
| [show-me-your-work](show-me-your-work/SKILL.md) | Append-only TSV decision log, including user rulings, read at session start and after compaction so later sessions do not reopen settled questions. Ported from pstack. |

## Workflows

| Workflow | What it does |
| --- | --- |
| [retro-week](workflows/retro-week.js) | Runs `retro` over every Claude Code session from the past N days, one agent per repo, then dedupes, ranks, and checks each finding against current repo state. Args: `{days: 7, today: "YYYY-MM-DD"}`. |

## Mods

| Mod | What it does |
| --- | --- |
| [progress](mods/progress) | Progress bars above the prompt: the `mcp__progress__track` tool, a hairline bar with stage notches and a moving shine (heavy-rule text bar in the terminal), elapsed time, subagent strips, a done line that fades out, a status-line fallback while hidden, and session names taken from the open bar or a one-time Haiku call. Commands: `/bars`, `/bars-clear`, `/bars-demo`. |

## Conventions

- One directory per skill, `SKILL.md` inside, frontmatter per Claude Code skill format. Mods live under `mods/`, one plugin folder each.
- Skills here are project-agnostic: per-project facts (repo, board number, doc paths) are inputs, never hardcoded.
- Preserve each skill's invocation policy. Keep discovery concise, load conditional detail through references, and retain exact procedures where correctness requires them.

## Credit

`codex/` is a standalone port of the `/codex` skill from [gstack](https://github.com/garrytan/gstack) (Garry Tan, MIT license) — the original wraps the OpenAI Codex CLI as one of ~30 skills in a much larger multi-agent toolkit. This port keeps the review/challenge/consult mechanics and drops everything wired into gstack's own infrastructure (telemetry, question-tuning auto-decide, checkpoint mode, gbrain sync, the `D<N>` AskUserQuestion format), so it runs standalone with no dependency on gstack being installed.

`blast-radius/`, `bro/`, `correct/`, `ketchup/`, `principle-explain-the-number/`, `principle-prove-it-works/` and `show-me-your-work/` are ported from [pstack](https://github.com/cursor/plugins/tree/main/pstack) (Lauren Tan, MIT license) on 2026-11-04. The ports drop the Cursor adapter and pstack cross-references, and map them to local skills (`orchestrate`, `codex`, `humanizer`, `dataviz`). They are maintained here and do not track upstream.

## Helper validation

Use the approved project/host Python runtime. Helpers use the standard library.

```sh
claude plugin validate mods/progress && claude plugin test mods/progress
python -m unittest discover -s codex/tests -v
python -m unittest discover -s github-pr-validation-loop/tests -v
```

The PR snapshot JSON now contains `coverage` and `pull_requests`; exit 2 signals incomplete coverage. The CI watcher requires explicit workflow IDs and a full commit SHA. See its skill for event selection, authentication, and remaining readiness checks.
