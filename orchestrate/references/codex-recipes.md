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
  --json \
  - < prompt.txt > out.jsonl 2> err.txt   # run in background
```

- `-m <model>` — e.g. `gpt-5.6-sol`.
- `-c 'model_reasoning_effort="xhigh"'` — see the enum gotcha below.
- `-s` — sandbox: `read-only` for review/investigation, `workspace-write` for
  implementation (see below).
- `-C <repo-root>` — run from the repo root regardless of cwd.
- `--json` — **always.** Streams JSONL events (file reads, edits, commands,
  agent messages) to stdout as they happen, so liveness checks answer "what is
  it doing" instead of "is the pid alive." Costs nothing in attention: the
  orchestrator still gets one completion notification; the event file is only
  tailed on demand (never read whole — reasoning deltas make it large). Extract
  the final report from the last agent-message event (verify the exact event
  shape once per codex version) rather than expecting buffered markdown.
- `- < prompt.txt` — read the prompt from stdin; keep the file, you will reuse it.
- `--output-last-message <file>` — **always for review gates.** Writes the final
  agent message (the findings + verdict) to a file so it survives intact.
  Field incident 2026-08-02: a `--json | tail -c N` pipeline clipped findings
  1–12 of a FIX-FIRST verdict; recovery meant parsing `~/.codex/sessions`
  rollout files. Tail for liveness, read the verdict from the file.

Save every prompt to a file. Re-gates, relaunches after a dead background process,
and "run the same thing at higher effort" all depend on having the exact prompt.

---

## Resuming a session (`codex exec resume`)

For the finder-fixes-verified pattern (pipelines §1): resume the reviewer's own
session so it fixes its findings with full context intact.

```bash
codex exec resume <thread-id> \
  -c 'sandbox_mode="workspace-write"' \
  --json --output-last-message out.md \
  - < fix-prompt.txt > stream.jsonl 2>&1   # run in background
```

- The thread id is in the original run's JSONL: first event,
  `{"type":"thread.started","thread_id":"..."}`.
- **`resume` rejects `-s` and `-C`** (field hit 2026-08-10, two failed launches).
  Sandbox is widened via `-c 'sandbox_mode="workspace-write"'`; cwd, model, and
  effort are inherited from the original session — which is what you want, and
  also why you must NOT resume a read-only reviewer session expecting a
  different working directory.
- `--json`, `-o/--output-last-message`, and stdin prompts work as in `exec`.
- The resumed turn keeps the session's full transcript: state your role change
  explicitly in the prompt ("you now have write access and will fix your own
  findings") plus any orchestrator adjudications, and nothing else — the
  context is already there.

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

Policy under this skill (user directive 2026-08-02):

- **Adversarial CODE-review gates / re-gates: `high` — never xhigh or ultra.**
  Review quality saturates at high; the heavier tiers mainly burn usage limits
  and wall-clock on a read-only diff review.
- **Architectural / major-decision second opinions (specs, plans, design
  docs): `xhigh`** (user directive 2026-08-09). These are judgment tasks, not
  checklist reviews — the heavier tier earns its cost here.
- **Implementation: default `xhigh`**; `ultra` at the orchestrator's discretion
  for large batches or genuinely hard single implementation tasks only. It
  consumes usage limits materially faster.

---

## Web search

Web search is **ON by default** in modern codex-cli. Override with the
`web_search` config key. `--enable web_search_cached` is **deprecated** — do not
use it.

---

## Sandbox modes

- **`read-only`** — reviews, audits, investigations. The deliberate safety
  property is **no writes**: the reviewer cannot mutate the tree, so its
  verdict can't be contaminated by an accidental edit. Losing network is a
  side effect of choosing the strict mode (codex's sandbox ties writes and
  network to one permissiveness dial for `codex exec`, not two independent
  switches) — it is not itself a goal, and most reviews don't need network
  anyway. If a review genuinely needs a network call (e.g. "is this really the
  latest version"), `read-only` is the wrong tool — it blocks the call the
  same way `workspace-write` does (see next section) and hits the same
  headless-hang failure mode. Handle that by doing the specific network step
  myself and handing codex the answer, same as the `workspace-write` fix
  below — not by escalating the review's sandbox.
- **`workspace-write`** — implementation. **Convention: leave ALL changes
  uncommitted.** The orchestrator reviews the diff and commits with attribution in
  the message body. Codex never commits; that keeps the review gate in front of
  every commit.
- **NEVER `danger-full-access` or `--dangerously-bypass-approvals-and-sandbox`**
  without the user explicitly asking for it in those words. These remove ALL
  sandboxing — full filesystem read/write anywhere on the machine, not just the
  repo, plus unrestricted network. They are not "unblock network," they are
  "no sandbox at all." User correction 2026-08-08: reached for
  `danger-full-access` to fix a network hang (see next section); wrong tool —
  the right fix needs no sandbox escalation at all.

### CRITICAL: explicit `-s` bypasses guardian auto-review — omit it when network may be needed

If the install's `~/.codex/config.toml` sets `approvals_reviewer =
"guardian_subagent"` + `guardian_approval = true` under `[features]` (check
before assuming — this is user-config-specific, not a codex-cli default), an
**on-request** approval (the default `approval_policy`) that the sandbox blocks
gets auto-reviewed by an AI guardian instead of blocking on a human — which
works fine even in headless `codex exec`, since nothing needs a human at a
keyboard.

**But passing `-s <mode>` explicitly on the CLI appears to skip that wiring.**
Field-verified 2026-08-08: two `codex exec -s workspace-write` tasks that each
needed a network call (`uv sync` hitting PyPI; version-checking hitting npm)
stalled indefinitely — alive pid, 0% CPU, zero event-stream growth for 15+
minutes, repeated across 3 relaunches. A control call with **no `-s` flag at
all** (relying purely on config defaults, which already resolve to
`workspace-write`) ran an equivalent network command (`npm view <pkg> version`)
to completion in ~20s, auto-approved by the guardian.

**Rule:** if a codex task might touch the network (package installs, registry/
version checks, external API calls, anything beyond local git/file/test
commands), **omit `-s` entirely** and let config resolve it — don't pass
`workspace-write` explicitly even though it's the "same" nominal mode. Reserve
explicit `-s read-only` for tasks that are read-only AND need no network (pure
code review against files already on disk). If a task stalls anyway with no
`-s` flag, that's a genuine hang per the Liveness section below, not this gotcha.

### Known macOS sandbox wart: the uv cache

`workspace-write` sandboxing on macOS blocks `~/.cache/uv`
(`failed to open file …/sdists-v9/.git: Operation not permitted`), so any stack
launcher or make-target that shells out to `uv` fails on its first sandboxed
attempt. This is expected, not a task failure — pre-authorize the retry in the
prompt: *"if the sandboxed launcher hits the uv-cache permission error, rerun it
outside the sandbox and note it."* Field record: hit on 5 consecutive
operational runs (2026-07-26/27); each agent burned a retry rediscovering it
until the prompt named it.

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

- With `--json` (the default above), a **growing `out.jsonl`** is the primary
  liveness signal and `tail -2 out.jsonl` shows the current activity. The `err`
  stream remains a secondary signal (non-json runs stream activity there; their
  `out` file stays empty until completion — an empty `out` alone is not a hang).
- **Alive-but-silent is a hang.** A live pid whose event stream has not grown
  for many minutes is stalled, not thinking: even at xhigh, codex interleaves
  tool calls that would show as events. Kill and relaunch from the saved prompt
  file. (Field hit: a buffered run sat 69+ minutes with a live pid, zero stream
  growth, zero file writes — unobservable precisely because it lacked `--json`.)
- **Session-start is part of liveness — a pid is not a session.** codex writes a
  rollout file under `~/.codex/sessions/<Y/M/D>/` (containing the prompt) at
  session start; no rollout with your prompt + no first event within ~2–3 min
  means the exec is stuck in a pre-session retry loop (auth, rate limit,
  contention from parallel codex sessions) and will not recover. Field hit
  2026-08-03: a gate sat 3h on a live pid having never opened a session; a
  "process alive" check wrongly reported it working. Arm a watchdog at launch
  (no first event in N min → alert) instead of trusting pid checks.
- **Background processes DIE on session restart.** On resume/compaction, **before**
  reporting a task as "still running", check the **event-file mtime and size**. If it
  stopped growing and the process is gone, the task is dead — **relaunch from the
  saved prompt file.**

```bash
ls -la out.jsonl && tail -2 out.jsonl   # mtime + current activity
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
