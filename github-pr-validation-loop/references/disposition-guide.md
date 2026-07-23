# PR Disposition Guide

Use this reference when a PR queue contains a mix of generated PRs, stale fixes, release automation, and real findings.

## Evidence Checklist

For each PR, collect:

- PR number, title, author, URL, base branch, head branch.
- Claimed problem from title/body/comments.
- Files changed and commit headlines.
- Current base code for the same surface.
- Existing or added tests that prove the claim.
- CI/check status if relevant to deciding whether the PR is stale or broken.

## Classification Details

`valid`

- The claim reproduces on current base.
- The PR identifies a real bug, performance issue, security issue, accessibility issue, broken test, or maintainability problem.
- The proposed diff may still be noisy or wrong; validity applies to the finding, not the patch.

`duplicate`

- Current base already includes an equivalent fix.
- Another open PR or current consolidated work covers the same behavioral surface.
- The PR adds only metadata, comments, formatting, or generated scaffolding around a finding already covered elsewhere.

`invalid`

- The reported behavior does not exist on current base.
- The proposed change would regress behavior, violate repo rules, weaken tests, remove needed scoping, or add unsupported compatibility.
- The PR is based on stale code and no longer maps to the current implementation.

`release/tooling`

- Release Please, version bumps, dependency update PRs, generated lockfile refreshes, or CI/tooling PRs.
- Leave open unless the user explicitly asks to handle them.

`needs-info`

- The claim cannot be validated without unavailable data, credentials, production context, or a product decision.
- Do not close as invalid; report the blocker and ask for the missing input.

## Comment Templates

Duplicate or superseded:

```text
Closing as superseded. The underlying finding is covered by <commit-or-pr>, which implements the fix against current <base> without adopting the generated PR branch directly.
```

Invalid:

```text
Closing after validation against current <base>. I could not reproduce the reported issue: <short evidence>. No source changes are needed for this PR.
```

Stale:

```text
Closing as stale against current <base>. The files/behavior this PR changes have moved, and the claimed issue is no longer present in the current implementation.
```

Release/tooling left open:

```text
Leaving this open because it is a release/tooling PR and outside the requested validation scope.
```

## Consolidated Fix Pattern

When several PRs are valid but noisy:

1. Write a short workplan that names the valid findings and explicitly excludes unrelated PR content.
2. Add failing tests first where practical.
3. Implement a clean fix on current base.
4. Run focused tests, full local gates, and formatting/lint checks.
5. Commit and push.
6. Close superseded PRs with a pointer to the landed commit or replacement PR.
7. Monitor CI until the relevant branch run is green.

## Red Flags

- PR includes secrets, raw PII, or public environment variables.
- PR removes authorization, tenant scoping, CSRF checks, or audit logging.
- PR contains broad formatting churn around a tiny behavior change.
- PR includes bot metadata such as scratch notes, temporary scripts, or tool-generated TODO files.
- PR weakens tests to pass instead of fixing product behavior.
- PR claims performance improvement without preserving grouped, distinct, filtered, or scoped query semantics.
