# Subagent recipes

Operational knowledge for running Claude subagents as implementers, reviewers,
test authors, and research explorers.

---

## Worktree isolation

Anything that **mutates files in parallel** runs in an isolated git worktree, so
tracks don't collide in one checkout.

**Fresh worktrees have NO synced dependencies.** The first step in any worktree is
to install them:

```bash
uv sync        # or: npm ci   (per the project's package manager)
```

**Project make-targets often assume the primary checkout** — they run
`docker-compose`, check hard-coded paths, or expect a running service, and **fail
from a worktree.** When a make-target fails in a worktree, **run the underlying
tool directly** rather than debugging the wrapper — e.g. invoke `pytest` against the
known DB port instead of `make test`.

---

## The mandatory contents of an implementation prompt

Every implementation prompt to a subagent must include, without exception:

1. **The frozen interface** — the exact names/ids/signatures it must produce
   against. Ambiguity here becomes an invented interface later.
2. **Verification commands to run**, with the instruction to **"paste the actual
   tail and counts"** — not "confirm it passes".
3. **Report format:** *"your final message is data for the orchestrator, not prose
   for a human."* Structured, per-finding or per-criterion.
4. **Commit locally, never push.**
5. **Per-finding / per-criterion structure** for whatever it's producing.
6. **What is out of scope** — the boundary of its track, so it doesn't "improve"
   adjacent code.

---

## Teammate messaging — the idle-agent failure

Long-running agents can go **IDLE without delivering a report.** A subagent's plain
text output is **invisible** to the orchestrator; only what it sends over the
**messaging channel** arrives. Two consequences:

- **Require agents to deliver results via the messaging channel**, explicitly. An
  agent that "finished" but only wrote prose to its own transcript has delivered
  nothing.
- **When an agent goes silent, do NOT ping-pong messages.** Inspect its
  branch/worktree state **directly** — `git log`, `git status`, `git diff --stat`
  in its worktree — to see what actually exists. Then send **ONE** directive resume
  message listing **exactly what remains**. Don't ask "are you done?"; tell it the
  precise delta.

```bash
git -C <worktree> log --oneline -5
git -C <worktree> status --short
git -C <worktree> diff --stat main...HEAD
```

Two more delivery realities:

- **Duplicate delivery is normal.** The same result often arrives 2–3 times
  (SendMessage report + task-completion notification + idle pings). Act on the
  FIRST arrival; treat repeats as no-ops — never re-dispatch work because a
  duplicate landed.
- **Helper reports route to the top.** When a delegate spawns its own helper,
  the helper's completion report lands with the TOP orchestrator, not its parent.
  Relay the substance to the parent agent with directives — the parent may not
  know its own helper finished.

---

## Naming and the scoreboard

- **Name agents at spawn** so they're addressable for the resume message.
- Keep a **scoreboard of in-flight tracks** — which agent, which branch, what
  state (running / idle / delivered / gated). Report it to the user
  **outcome-first**: what's done and what's blocked, not a play-by-play.

---

## Effort tiers

- Every Opus subagent stage — implementation, test authoring, research, and the
  hardest judge/review gates alike: **`high`**. Do not spend `xhigh` or `max` on
  an Opus subagent; the extra effort has not paid for itself here.

---

## Headless CLI gates (`claude -p`) — the alias-tracking alternative

When gates must run on "the newest \<model\>" and the Agent-tool registry is
version-pinned or mid-session stale, run the reviewer as a headless CLI call
with a **model alias** — never a version pin; aliases auto-track releases:

```bash
cd <worktree> && claude -p --model opus \
  --allowedTools "Read" "Glob" "Grep" \
    "Bash(git diff:*)" "Bash(git show:*)" "Bash(git log:*)" \
    "Bash(rg:*)" "Bash(grep:*)" \
  < gate_prompt.txt > gate_out.md 2> gate_err.txt   # run in background
```

- **The allowlist IS the read-only sandbox**: inspection tools plus git-object
  commands only — the reviewer cannot mutate the tree and never stalls on a
  permission prompt mid-review.
- Same saved-prompt-file discipline as codex: re-gates rerun the exact file.
- Reviewer output contract unchanged (`[P1]/[P2]/[NIT]` + VERDICT line).
- Run it **from the worktree under review** so relative paths in findings
  resolve.

---

## Research fan-out (for the spec pipeline)

Explorer subagents are **read-only** and each gets a **distinct focus** (one
subsystem or concern per agent). They investigate and report; they never edit. The
orchestrator (or a synthesis agent) merges their findings — see the spec pipeline
in `pipelines.md`.

## CI watchers: use one long-lived wait, not a background poll loop

Field hit: a CI-watcher subagent polled with a backgrounded bash
loop; the sandbox's per-call session reset killed the loop silently after its
first iteration and the watcher went idle having reported nothing. Rules:

- The watcher waits with a single long-lived process (`gh run watch`, the
  Monitor tool, or one foreground loop inside one Bash call) — never a
  detached background poll it assumes will keep running.
- Orchestrator side: a watcher going idle well before the runs could have
  concluded is SUSPECT, not done — query it for current state and re-instruct
  rather than assuming CI is green.
