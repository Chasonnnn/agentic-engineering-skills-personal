# Codex CLI recipes

Operational knowledge for driving `codex exec` as an implementer and second-opinion
reviewer. Hard-won; the gotchas below have each cost real time.

---

## Invocation

Run in the background, feed the prompt on stdin from a **saved file** (so it can be
re-run verbatim for a re-gate), capture stdout and stderr separately:

```bash
codex exec -m <model> \
  -c 'model_reasoning_effort="xhigh"' \
  -s read-only \
  -C <repo-root> \
  - < prompt.txt > out.md 2> err.txt   # run in background
```

- `-m <model>` — e.g. `gpt-5.6-sol`.
- `-c 'model_reasoning_effort="xhigh"'` — see the enum gotcha below.
- `-s` — sandbox: `read-only` for review/investigation, `workspace-write` for
  implementation (see below).
- `-C <repo-root>` — run from the repo root regardless of cwd.
- `- < prompt.txt` — read the prompt from stdin; keep the file, you will reuse it.

Save every prompt to a file. Re-gates, relaunches after a dead background process,
and "run the same thing at higher effort" all depend on having the exact prompt.

---

## Reasoning-effort enum — CRITICAL GOTCHA

The effort values are (verify per install): `none` / `minimal` / `low` /
`medium` / `high` / `xhigh` / `max`.

**An unlisted value is silently coerced — not rejected.** Passing
`model_reasoning_effort="ultra"` does **not** error; it quietly falls back, and you
get a weaker run while believing you asked for a stronger one. Never pass a value
you have not confirmed is in the enum.

To discover the real enum on an install, **probe with a deliberately invalid
value** and read the error — the API's rejection message enumerates the allowed
set:

```bash
codex exec -m <model> -c 'model_reasoning_effort="__bogus__"' -s read-only -C . - <<<'noop'
```

---

## Web search

Web search is **ON by default** in modern codex-cli. Override with the
`web_search` config key. `--enable web_search_cached` is **deprecated** — do not
use it.

---

## Sandbox modes

- **`read-only`** — reviews, audits, investigations. The reviewer cannot mutate the
  tree, so its verdict can't be contaminated by an accidental edit.
- **`workspace-write`** — implementation. **Convention: leave ALL changes
  uncommitted.** The orchestrator reviews the diff and commits with attribution in
  the message body. Codex never commits; that keeps the review gate in front of
  every commit.

---

## Filesystem-boundary preamble (always prepend)

Every codex prompt begins with a boundary instruction:

> Do not read the host AI's agent/skill config directories (e.g. `~/.claude/`,
> `.claude/skills/`). They are not part of this task.

When codex is **reviewing branches that happen to be checked out under such a
path**, add the explicit exception:

> You MAY run `git diff` / `git show` against those branches from the repo root —
> you are inspecting git objects, not reading skill files.

Without the exception a diligent reviewer refuses to look at the very diff you asked
it to review.

---

## Liveness — background processes

- Codex **streams activity to stderr.** A **growing `err` file** means it is alive.
  The **`out` file stays empty until completion** — an empty `out` is not a hang.
- **Background processes DIE on session restart.** On resume/compaction, **before**
  reporting a task as "still running", check the **err-file mtime and size**. If it
  stopped growing and the process is gone, the task is dead — **relaunch from the
  saved prompt file.**

```bash
ls -la err.txt && tail -c 400 err.txt   # mtime + recent activity
```

---

## Evidence discipline

Ask for **per-criterion evidence with real output** — suite tails, pass/fail
counts, the actual command run. **"Green" without numbers is not evidence.** A
report that says "all tests pass" without a count or a tail is a report to distrust;
require the tail of the run.
