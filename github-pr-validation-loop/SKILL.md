---
name: github-pr-validation-loop
description: Validate a GitHub PR queue, fix valid findings in small logical commits, publish one consolidated replacement PR, and close resolved or invalid source PRs.
disable-model-invocation: true
---

# GitHub PR validation loop

Treat a PR's claim and proposed implementation separately. Validate against the current target branch. The default workflow is to fix valid findings, commit the fixes in small logical groups, push one consolidated replacement PR, and close the covered source PRs. Close invalid PRs directly with evidence. Do not merge the original PRs or the replacement PR.

An explicit narrower request, such as read-only review, no Git changes, or preserving selected drafts, overrides this default. Complete the actions included in the workflow request without repeatedly asking for permission; unrelated work, deployment, and production data changes remain outside its scope.

## Queue and decisions

Identify the repository, base revisions, requested PR set, and existing dirty work. Preserve unrelated files and staged changes. Use the repository's approved GitHub authentication path. Read [references/disposition-guide.md](references/disposition-guide.md) when classifying or closing mixed queues.

`scripts/pr_snapshot.py` provides a bounded summary, not a complete diff or authoritative check suite. It reports queue truncation, missing file details, and view errors; exit 2 means incomplete coverage. Increase the requested limit or query the remaining scope before claiming a complete queue audit. Reopen full bodies, paginated file/commit details, and current checks when needed for a decision. The snapshot records base/head IDs, but recheck them before mutation.

For manual inspection, supported view fields include `title,body,files,commits,statusCheckRollup,headRefOid,baseRefOid`; there is no `checks` field. Supply an explicit repository when outside its checkout.

Classify as valid, duplicate, invalid, release/tooling, or needs-info. Inspect relevant current-base callers and tests, and reproduce consequential bug claims where practical. Failure to reproduce alone is not evidence that a claim is false. A bad proposed patch can still identify a valid problem.

## Resolution and publication

1. For invalid findings, document the affirmative source or test evidence and close the PR directly. Do not invent a fix for a false claim or treat inconclusive evidence as invalid.
2. For valid findings, implement the smallest repo-native correction instead of merging or blindly adopting the original patch. Consolidate overlapping findings into one correction. Preserve project test-first requirements and independently check that tests exercise the claimed behavior.
3. Use one repair branch and make small commits organized by logical behavior or dependency group. Keep each fix with its regression tests and required manifest, lockfile, or generated-contract changes. Inspect the staged files before each commit; preserve unrelated dirty work and keep generated notes out of the commits.
4. Run the project's relevant local gates, inspect the full commit set, push the branch, and create or update one consolidated PR for all in-scope fixes. Its description must map source PRs to fixes and record validation and remaining limits. Do not create a separate replacement PR for every finding.
5. Once a validated fix is available in that replacement PR, close the corresponding valid source PRs and duplicates with a link to it. State that the replacement is still open and whether CI is pending; do not imply it has merged or deployed. A local-only fix is not sufficient for closure. If publication is blocked, keep those source PRs open and report the blocker. Invalid PR closures need not wait for replacement publication.
6. Follow the replacement's required CI on its exact current head. Diagnose failures, make further small logical commits for necessary corrections, and push them to the same PR. Recheck source PR revisions and coverage before closure; read back every external mutation to verify its result.

Preserve explicitly excluded drafts and unrelated product, release, or tooling work. Needs-info findings stay open with the missing evidence identified. Do not manufacture an empty replacement PR when there are no valid fixes.

Broad formatting or credential-related code is a reason to inspect scope and risk, not an automatic new permission round when the requested work already covers it. Actual secret rotation, destructive operations, deployment, and merging retain their own authorization boundaries.

## CI evidence

`scripts/ci_watch.py` requires a full SHA and explicit expected workflow IDs. Resolve that set from applicable workflow triggers and project requirements before running; observed runs cannot tell you which required workflow is missing. The default event is `push`; pass the intended event when different. It fetches paginated exact-head runs, selects the newest run/attempt per expected workflow, and waits for every selected workflow to succeed. Skipped, neutral, cancelled, and failed required runs are not silently green.

```bash
python scripts/ci_watch.py --repo OWNER/REPO --branch BRANCH --head-sha FULL_SHA \
  --workflow-id FIRST_ID --workflow-id SECOND_ID --event push
```

Both Python helpers accept `--authmux` and optional `--context CONTEXT` for a context already authorized outside a bound repository. They wrap each `gh` leaf command; do not wrap the whole Python process through authmux. Without `--authmux`, they use native gh for environments whose policy permits it. Resolve script paths from this skill's directory and use the approved Python runtime.

Both helpers stop immediately on authmux exit 10, preserving its event and the stopped leaf argv on stderr. Follow the authmux handoff for that exact operation; do not blindly rerun the whole snapshot as its continuity retry.

Watcher exit codes: 0 means the declared workflow set passed; 1 means a required workflow failed; 2 means timeout, missing/incomplete evidence, or query failure. This does not prove branch protection, external CI, deployments, or every job contract is satisfied. Inspect required checks and per-job results separately when those determine readiness. PR merge refs and merge queues may run on a different SHA; verify the actual required revision instead of substituting a branch run.

Report each disposition, the small logical commits, the consolidated PR link, verified source-PR closures, validation, exact-head CI evidence, and remaining work. Keep local, pushed, integrated, deployed, and verified states distinct.
