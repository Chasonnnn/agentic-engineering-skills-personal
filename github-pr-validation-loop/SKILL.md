---
name: github-pr-validation-loop
description: Audit and resolve GitHub pull request queues by validating each open PR against the current base branch, classifying valid/invalid/duplicate/release PRs, implementing clean consolidated fixes with test-first workflow when findings are valid, closing invalid or superseded PRs with evidence, pushing accepted fixes, and monitoring CI until relevant branch runs are green. Use when asked to review, triage, validate, close, consolidate, fix, or land open GitHub PRs.
disable-model-invocation: true
---

# GitHub PR Validation Loop

## Overview

Use this skill to turn a noisy PR queue into a verified outcome: valid findings become clean repo-native fixes, duplicates and invalid PRs are closed with evidence, and pushed work is followed through until CI is green.

Do not treat a PR diff as trusted implementation. Treat it as a finding report that must be checked against the current base branch.

## Workflow

1. Establish the operating surface.
   - Read local repository instructions first (`AGENTS.md`, `CONTRIBUTING.md`, or equivalent).
   - Check `git status --short --branch` before mutating anything.
   - Note ahead/behind state, unstaged files, and staged files separately. If unrelated staged files already exist, use a path-limited commit or otherwise avoid including them.
   - Identify the base branch and the exact open PR set.
   - Preserve unrelated local changes. Do not create a branch, commit, push, or close PRs if the user requested read-only audit only.

2. Snapshot the PR queue.
   - Prefer `scripts/pr_snapshot.py` for a compact queue summary.
   - Otherwise use `gh pr list` plus `gh pr view <number> --json title,body,files,commits,checks,statusCheckRollup`.
   - Capture enough evidence to compare the PR claim, touched files, and current base implementation.

3. Classify each PR.
   - `valid`: the finding is real on current base and needs a fix.
   - `duplicate`: current base or another planned consolidated fix already covers it.
   - `invalid`: the finding is false, obsolete, harmful, or unsupported by code/tests.
   - `release/tooling`: release automation, dependency bot, or workflow PR that should be left alone unless explicitly in scope.
   - `needs-info`: cannot be resolved without more access, reproduction data, or user intent.

4. Validate before acting.
   - Inspect current base code, not just the PR branch.
   - Compare the PR diff with existing behavior and tests.
   - For bug claims, reproduce with a failing test where practical.
   - For performance claims, verify generated SQL, algorithmic behavior, or measurable cost.
   - For accessibility/UI claims, verify the DOM or source pattern and add a bounded regression test when feasible.

5. Resolve valid findings with a clean implementation.
   - Do not cherry-pick or directly adopt bot commits unless the user explicitly asks.
   - Consolidate related valid findings into one curated fix when that reduces churn.
   - Write or update tests first when applicable.
   - Keep generated metadata, scratch files, and unrelated refactors out of the fix.
   - Run focused tests first, then full repo gates required by local instructions.

6. Close invalid or superseded PRs.
   - Close only after recording evidence.
   - Use a short comment that states the disposition and why.
   - For superseded PRs, include the replacement commit or PR URL.
   - Leave release PRs and unrelated active work open unless they are explicitly part of the request.

7. Push and monitor.
   - Push only the intended commits.
   - Monitor branch-level GitHub runs; commit-scoped status can lag.
   - Prefer `scripts/ci_watch.py --branch <branch> --head-sha <sha>` when available.
   - Do not report the work complete until local gates pass and the relevant CI run has completed, or until you clearly state that CI is still running.

8. Report the result.
   - List each PR with its disposition.
   - Include replacement commit/PR information for valid consolidated fixes.
   - Summarize tests and CI.
   - Call out anything left open intentionally and any local dirty files that were not part of the work.

## Decision Rules

- Valid PRs are evidence, not patches. Re-implement the smallest correct fix in the codebase's style.
- A PR is duplicate only when current base or the consolidated fix fully covers the finding.
- A PR is invalid only when you can explain why the claim does not hold on current base or would make behavior worse.
- If multiple PRs are valid but noisy, make one clean fix and close the originals as superseded after the fix lands.
- If a PR touches secrets, credentials, destructive migrations, broad formatting, or production operations, pause and get explicit user confirmation before acting.

## Resources

- `scripts/pr_snapshot.py`: Build a compact JSON or Markdown snapshot of open PRs using `gh`.
- `scripts/ci_watch.py`: Poll GitHub Actions branch runs until the relevant head SHA is green, failed, or timed out.
- `references/disposition-guide.md`: Use for classification details and close-comment templates when the queue has mixed valid, duplicate, invalid, and release PRs.
