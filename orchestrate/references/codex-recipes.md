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

## Reasoning-effort enum — CRITICAL GOTCHA (revised)

The documented effort values (from the API's own rejection message) are:
`none` / `minimal` / `low` / `medium` / `high` / `xhigh` / `max`.

**The rejection-message enum is a FLOOR, not the full truth.** Verified
2026-07-21 on gpt-5.6-sol: `model_reasoning_effort="ultra"` is absent from the
400-error enum yet is ACCEPTED and HONORED — the request completes and burns an
anomalously large reasoning-token count on a trivial prompt (~15k tokens for a
one-word reply), and the Codex GUI exposes Ultra ("consumes usage limits
faster"). An earlier version of this file claimed ultra was silently coerced;
that was an inference from the enum listing, never round-tripped. Wrong.

Probe in two steps — never conclude from the error message alone:

1. **Invalid-value probe** to get the documented floor:
   ```bash
   codex exec -m <model> -c 'model_reasoning_effort="__bogus__"' -s read-only -C . - <<<'noop'
   ```
   A 400 with `invalid_enum_value` lists the documented set.
2. **Round-trip probe** for any candidate beyond the floor (e.g. `ultra`):
   ```bash
   echo 'reply with exactly: PROBE-OK' | codex exec -m <model> -c 'model_reasoning_effort="ultra"' -s read-only -C . -
   ```
   A 400 → genuinely invalid. A completed reply → honored; anomalously high
   `tokens used` for a trivial prompt confirms a real heavier tier (a silent
   coercion to a lower tier would burn few tokens).

Policy under this skill: default `xhigh`; use `ultra` at the orchestrator's
discretion for **large batches or genuinely hard single tasks** (hardest
concurrency implementations, make-or-break design second opinions, final
adversarial verification). It consumes usage limits materially faster.

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

## Parallel codex runs

Two codex processes on the same repo are safe when at most one is
`workspace-write` — a read-only review can run alongside an implementation.
One mandatory clause when the working tree is dirty (the parallel task's
uncommitted work): the review prompt must pin itself to **git objects only** —
"review `git diff <a>...<b>` / `git show`; NEVER read the working tree." Without
it the reviewer reads half-finished parallel work as if it were the change under
review.

---

## Evidence discipline

Ask for **per-criterion evidence with real output** — suite tails, pass/fail
counts, the actual command run. **"Green" without numbers is not evidence.** A
report that says "all tests pass" without a count or a tail is a report to distrust;
require the tail of the run.
