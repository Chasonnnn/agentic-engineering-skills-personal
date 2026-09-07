---
name: github-pr-validation-loop
description: Validate a GitHub PR queue against current base code and resolve or consolidate findings within the requested scope.
disable-model-invocation: true
---

# GitHub PR validation loop

Treat a PR's claim and proposed implementation separately. Validate against the current target branch. Keep read-only audit, local fixes, publication, and PR closure within existing user authorization; do not turn a review request into a cleanup campaign.

## Queue and decisions

Identify the repository, base revisions, requested PR set, and existing dirty work. Preserve unrelated files and staged changes. Use the repository's approved GitHub authentication path. Read [references/disposition-guide.md](references/disposition-guide.md) when classifying or closing mixed queues.

`scripts/pr_snapshot.py` provides a bounded summary, not a complete diff or authoritative check suite. It reports queue truncation, missing file details, and view errors; exit 2 means incomplete coverage. Increase the requested limit or query the remaining scope before claiming a complete queue audit. Reopen full bodies, paginated file/commit details, and current checks when needed for a decision. The snapshot records base/head IDs, but recheck them before mutation.

For manual inspection, supported view fields include `title,body,files,commits,statusCheckRollup,headRefOid,baseRefOid`; there is no `checks` field. Supply an explicit repository when outside its checkout.

Classify as valid, duplicate, invalid, release/tooling, or needs-info. Inspect relevant current-base callers and tests, and reproduce consequential bug claims where practical. Failure to reproduce alone is not evidence that a claim is false. A bad proposed patch can still identify a valid problem.

## Resolution

Implement the smallest repo-native correction for valid findings. Consolidate related changes when useful; do not automatically adopt bot commits. Preserve project test-first requirements and independently check that tests exercise the claimed behavior. Keep generated notes and unrelated cleanup out of commits.

Close invalid PRs only with affirmative evidence. Close superseded work after the replacement is integrated, or when the user explicitly authorizes closing in favor of a linked open replacement. A local fix alone is not a landed replacement. Leave unrelated release/tooling PRs alone. Comments are external writes and require authorization from the requested resolution task.

Validate focused behavior and the project's required gates, inspect the exact commit set, then publish when authorized. Broad formatting or credential-related code is a reason to inspect scope and risk, not an automatic new permission round if the requested work already covers it. Actual secret rotation, destructive operations, and deployment retain their own task boundaries.

## CI evidence

`scripts/ci_watch.py` requires a full SHA and explicit expected workflow IDs. Resolve that set from applicable workflow triggers and project requirements before running; observed runs cannot tell you which required workflow is missing. The default event is `push`; pass the intended event when different. It fetches paginated exact-head runs, selects the newest run/attempt per expected workflow, and waits for every selected workflow to succeed. Skipped, neutral, cancelled, and failed required runs are not silently green.

```bash
python scripts/ci_watch.py --repo OWNER/REPO --branch BRANCH --head-sha FULL_SHA \
  --workflow-id FIRST_ID --workflow-id SECOND_ID --event push
```

Both Python helpers accept `--authmux` and optional `--context CONTEXT` for a context already authorized outside a bound repository. They wrap each `gh` leaf command; do not wrap the whole Python process through authmux. Without `--authmux`, they use native gh for environments whose policy permits it. Resolve script paths from this skill's directory and use the approved Python runtime.

Both helpers stop immediately on authmux exit 10, preserving its event and the stopped leaf argv on stderr. Follow the authmux handoff for that exact operation; do not blindly rerun the whole snapshot as its continuity retry.

Watcher exit codes: 0 means the declared workflow set passed; 1 means a required workflow failed; 2 means timeout, missing/incomplete evidence, or query failure. This does not prove branch protection, external CI, deployments, or every job contract is satisfied. Inspect required checks and per-job results separately when those determine readiness. PR merge refs and merge queues may run on a different SHA; verify the actual required revision instead of substituting a branch run.

Report each disposition, replacement links, validation, exact-head CI evidence, and remaining work. Keep local, pushed, integrated, deployed, and verified states distinct.
