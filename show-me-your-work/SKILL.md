---
name: show-me-your-work
description: "Keep a reviewable decision trail for multi-session or unattended work: a TSV log with one row per decision or user ruling (what, why, evidence, result). Use for /show-me-your-work, runs that span sessions or compactions, and work the user reviews after stepping away."
---

# Show me your work

Keep one canonical log. It must answer "what did we decide, when, and why" after a compaction or in a new session.

## The format

A single TSV file, one row per decision. Cells stay single-line. Evidence is a pointer, not prose.

Copy `references/decision-log-template.tsv` (the header row) to start a clean log. Columns:

- **ts.** ISO8601 timestamp.
- **phase.** The phase or workstream.
- **decision.** What was chosen or done, one line.
- **why.** The reason in plain words. If a principle drove it, say it plainly, not as a jargon tag.
- **evidence.** A link or path that proves it: commit SHA, PR number, `file:line`, artifact URL, job ID, or a results file. Never a paragraph.
- **result.** The outcome or state: `tests green`, `reverted`, `recall 0.97 on saga100`, `INCONCLUSIVE`, `open`.

Example:

```
ts	phase	decision	why	evidence	result
2026-05-24T09:02:00Z	start	new run; rows before are from no other run	first session on this log	session 3c50a1b2	open
2026-05-24T09:40:00Z	ruling	user: label ambiguous mentions as sensitive	a wrong keep costs more than a wrong redact	session 3c50a1b2, 09:38	adopted
2026-05-24T11:15:00Z	eval	kept the current prompt; the variant did not beat it	gap smaller than the bootstrap spread on dev	results/compare.tsv	not promoted
2026-05-25T14:05:00Z	ruling	user: pause experiments until the new gold lands	more ground truth arrives next week	session 9d41e7f0, 14:02	open
```

## Logging a row

Write each entry the way you would tell a teammate what you did. Plain words, concrete actions, no AI speak (the `humanizer` skill applies to log text too).

Use the helper `scripts/log.sh <logfile> <phase> <decision> <why> <evidence> <result>`. It stamps `ts`, writes the header on first use, strips stray tabs and newlines, and prefixes any cell starting with `=`, `+`, `-`, or `@` with a single quote.

Log decision points and checkpoints, not every action: a fork chosen, a unit completed with its verification result, a pivot or revert with its trigger, a blocker surfaced, a gate fixed. For loop runs, one row per iteration. Skip the trivial and self-evident.

Log each user ruling with phase `ruling`: an answer to a question you asked, an approval, a reversal, or a stated principle that later work depends on. Write it as `user: <ruling>`, and point the evidence at the session ID and time.

A run is one agent conversation, including its later turns and any summary of it. A pickup, a replacement agent, or a new session starts a new run. When a run adds to a log that already has rows, its first row has phase `start`, and so does its first row after another run's `start` row. So a run that comes back to a log in a later turn first reads the log's last rows to see whether another run wrote since. A `start` row names the `ts` range of the rows before it that this run did not write, and its evidence names this run's session ID. Use phase `start` for nothing else.

## Read before you act

At the start of a session, after a compaction, and before you ask the user a question, read the `ruling` rows and the last 20 rows. Do not ask again a question that a `ruling` row answers. If new evidence argues against a ruling, say so and cite the row.

## Where it lives

- Work that spans sessions, or that a reviewer must trust: commit the log at `docs/decisions.tsv`.
- One run, or several efforts at once: keep `.audit/<task-slug>.tsv` and leave it out of git.

## Rules

- Append-only. A wrong call gets a new row that supersedes it. Never edit or delete history.
- Prefer evidence produced by committed scripts over hand-made one-offs.

## Audit the log against the transcript

At the end of the run, before handing back, check the log told the truth. Read this run's transcript at `~/.claude/projects/<slug>/<session>.jsonl`, where the slug is the workspace path with each `/` and `.` changed to `-`. Read only this workspace's folder. Walk this run's rows against what actually happened. Each stretch of them begins at one of this run's `start` rows, or at the first row if this run created the log, and ends at the next `start` row of another run:

- Check that every row maps to a real decision, action, or user ruling.
- Check that each row's evidence resolves and shows what the row claims.
- A fork, pivot, abandoned approach, or user ruling that shaped the work but is not logged is a gap. Add it.

Correct the log, not the story. The audit never edits or removes a row. When a row's claim or evidence is wrong, add a row that supersedes it with what actually happened and a pointer that resolves.

## Cross-model review of the trail

For a committed log, or a run longer than a few hours, have a reviewer from a different model family read the trail and the transcript. Follow the model split in the `orchestrate` skill: Claude-made work gets a Codex review through the `codex` skill; Codex-made work gets an `opus-xhigh` subagent. Self-review is not a substitute. The reviewer scans for what the user should look at; it does not redo the work:

- Decisions logged with weak or absent evidence.
- Verification steps skipped or claimed without proof in the transcript.
- Choices that look risky in hindsight (premature, scope-creeping, papering over a symptom).
- Gaps the user would otherwise miss on a casual skim.

End the reply with an "Attention" section. Lead with `reviewed by <model>` on its own line, then list each flag with the row or moment it points to. "No flags" is a valid value.

## Reviewing the trail

`column -s$'\t' -t docs/decisions.tsv` renders it in a terminal. GitHub renders a committed TSV as a table.
