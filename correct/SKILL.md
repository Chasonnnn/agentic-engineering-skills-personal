---
name: correct
description: "Find the mistakes agents keep repeating in this repo or workflow and make each one impossible. Try architecture first, then types, then a lint or check whose error names the fix, then a test, and write docs last. Prove each check fails on a real past mistake. Use for /correct, or when the user says 'so we won't make this again'."
disable-model-invocation: true
---

# Correct

The user keeps correcting agents for the same mistakes. Change the repo, or the skill that drives the workflow, so the next agent cannot make them.

Assume every contributor is an agent that sees only the files it opened, copies the nearest example, and takes the shortest path that compiles. Design the repo so a change that looks right from one file is right for the whole repo.

`/retro` finds and proposes environment fixes. This skill builds them and proves them. When a `/retro` or `/retro-week` report exists for this repo, start from its findings.

## Find the mistake classes

Read these sources:

- Recent commits, reverts, and PR review comments.
- The repo's CLAUDE.md, AGENTS.md, and comments that explain workarounds.
- This repo's session logs at `~/.claude/projects/<slug>/*.jsonl`, where the slug is the repo path with each `/` and `.` changed to `-`. Look for user prompts that correct the agent: "why did you", "are you sure", "still", "again", "you didn't". Read only this repo's folder.
- Memory files and skills that the corrections name, such as `empire-ai-best-practices`.

Group the mistakes into classes. A class counts once it has happened twice. Ask the user when a correction could belong to two classes.

## Fix each class at the highest level that works

1. **Eliminate it with architecture.** Give each piece of state one owner and each task one supported way. Hide internals so the wrong import fails. Replace hand-synced lists with one source of truth. Delete old ways and dead code an agent would copy.
2. **Enforce it with types so the bad state cannot be written.** If bad code still compiles, add a lint or CI check whose error names the file, type, or function to use instead. If the pattern is already common, fail only when a change adds more.
3. **Test the behavior.** Fix or delete any test that still passes when the behavior it checks breaks, or that fails when only the internals change.
4. **Write docs or agent rules last, only for judgment calls.** Nothing fails when an agent skips them.

Operational mistakes (cluster jobs, AWS, deploys, pollers, auth) have no compiler. Fix them in a script that the workflow skill tells the agent to run, and make the script fail loudly on the bad state. A paragraph in the skill is level 4.

## Fix and prove

Fix the most frequent classes now, one commit each. Prove each new check fails on a real past mistake: replay the commit, the input, or the command that went wrong, and paste the failure. Run the same command locally and in CI. Exceptions go on the offending line with a reason, an expiry date, and the user's approval.

Follow the commit and PR rules in the global CLAUDE.md. Use stacked PRs when the classes review and pass CI on their own.

## Keep the rule table

Keep a table in `docs/agent-rules.md` that pairs each rule with what enforces it. Add one pointer line to it from CLAUDE.md or AGENTS.md. Do not put the table in CLAUDE.md. When the user corrects you, fix the mistake and add the rule. If the rule was already there and nothing enforces it, that is a repeat, so fix it at the highest level in the same change. Drop a rule once its mistake cannot happen.

**Reply:** each class with its evidence, the level you picked, why a higher level did not work, and the proof that its check fails on the past mistake.
