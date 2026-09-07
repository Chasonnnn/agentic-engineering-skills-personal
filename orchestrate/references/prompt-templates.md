# Delegate prompts

Include fields that affect the task. Omit irrelevant fields rather than requiring every delegate to follow every workflow.

```text
Outcome: [bounded deliverable and acceptance criteria]
Source: [repository, revision or stable diff, relevant references]
Ownership: [files/worktree; shared interfaces and other active writers]
Permissions: [permitted edits, tests, commits and external actions]
Verification: [applicable project commands and expected behavior]
Report: changes/findings, evidence per criterion, unresolved limits, artifact paths.
```

## Review addition

```text
Review [exact scope] independently. Inspect the full scoped diff and relevant
callers. For refactors compare the pre-change behavior; for changed identifiers
check existing data and consumers. Assess whether tests exercise the claimed
path. Report actionable defects with priority, file:line evidence and correction.
Name omitted scope and distinguish static checks from executed tests. Missing
evidence is incomplete review, not a clean verdict.
```

Codex uses the shared runner's `--review` response schema. Do not append a contradictory MERGE/PUSH output contract.

## Repair addition

```text
Resolve [verified findings and chosen approach] within [owned scope]. Preserve
[acceptance invariants]. Report evidence for each correction and any remaining
limits. The next reviewer will verify the prior findings and inspect this delta.
```

## Test-author addition

```text
Write acceptance tests for [behavior and interface] without implementing it.
Demonstrate the relevant failure before implementation. Do not stub the target
behavior into existence. Identify proposed interface choices and test ownership.
```

## Operational addition

```text
Operate [authorized system and task]. Prior completed IDs: [record]. Readiness:
[checks]. Stop on [specific conditions]; retries permitted only for [bounded,
safe cases]. Record per-item outcomes and exact relevant errors at [path]. Track
resources started versus inherited and apply [task-owned cleanup]. Completion
requires [observable end state], not merely successful submission.
```
