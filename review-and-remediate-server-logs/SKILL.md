---
name: review-and-remediate-server-logs
description: Review production or staging server logs, separate expected noise from actionable failures, trace high-signal events to deployed code and configuration, reproduce defects with tests, implement bounded fixes, validate them locally and in CI, and verify the result after deployment. Use when asked to inspect Cloud Run, CloudWatch/ECS, Kubernetes, systemd, container, API, worker, webhook, queue, or application logs; diagnose recurring 4xx/5xx responses, exceptions, warnings, retry loops, concurrency failures, PII leakage, or broken observability; or carry a log finding through remediation and post-deploy confirmation.
---

# Review and Remediate Server Logs

Turn runtime evidence into a verified outcome. Preserve the boundary between observation, code changes, production mutations, and deployment: authorization for one does not imply authorization for the others.

## Workflow

1. Establish scope and authority.
   - Read repository instructions and deployment documentation before running project commands.
   - Determine the environment, provider, project/account, region, services, and time window from live configuration rather than guessing.
   - Clarify whether the request is read-only diagnosis, local remediation, PR publication, deployment, or post-deploy monitoring. Continue through every authorized stage; pause before any unapproved production mutation.
   - Check the worktree before editing. Preserve unrelated changes and inherited services.
   - Never print or retain raw secrets, tokens, request bodies, email addresses, phone numbers, or other PII. Prefer identifiers, counts, hashes, and sanitized error classes.

2. Inventory the live surface.
   - List services, active revisions or task definitions, traffic allocation, health state, and deployed version or image digest.
   - Record the exact query window in UTC and local time.
   - Start with the active revision. Query retired revisions only to distinguish current defects from rollout noise.
   - Read `references/provider-playbooks.md` for the relevant provider commands and query patterns.

3. Collect and cluster evidence.
   - Start broad enough to measure status and severity, then narrow by service, revision, route, status, severity, and structured event name.
   - Cluster events by a stable fingerprint: exception class, normalized message, route/job, status, top stack frame, and relevant provider reason code.
   - For each cluster capture count, first/last timestamp, affected service/revision, success/failure ratio, and one sanitized representative event.
   - Compare failing events with successful requests on the same path. Absence of matching logs is not proof that a subsystem is healthy.

4. Classify and prioritize.
   - `P0`: active outage, security exposure, destructive data risk, or broad authentication failure.
   - `P1`: repeated 5xx responses, durable-event loss, deadlocks, retry storms, broken access control, PII in logs or URLs, or monitoring that drops real errors.
   - `P2`: isolated recovered failures, misleading warnings, degraded diagnostics, noisy expected errors, or a low-frequency correctness risk.
   - `noise`: verified bot traffic, expected unauthenticated 401/403 responses, probes, retired-revision rollout residue, or handled transient failures with successful recovery.
   - Do not dismiss a 4xx by status alone. Validate the caller, endpoint contract, frequency, and whether a success path exists.

5. Trace each actionable cluster.
   - Map the runtime event to its request route, job, webhook, queue, provider boundary, and code path.
   - Confirm the deployed version contains the code being inspected. Account for configuration and migration drift.
   - Inspect transaction boundaries, lock order, idempotency, retry policy, tenant scoping, serialization, and logging fields when relevant.
   - Compare secret or configuration values only through safe metadata or digests. Keep platform, organization, tenant, and user-level integrations separate.
   - State the evidence, hypothesis, and disconfirming check before editing.

6. Reproduce before fixing.
   - Add a failing regression test for every behavior-changing fix when practical.
   - Reproduce the production shape, not a convenient approximation: use the same database engine for locking failures, authenticated and signed requests for webhook failures, realistic concurrency barriers for races, and representative provider error structures.
   - Pin the RED result and confirm it fails for the expected reason.
   - If reproduction is unsafe or impossible, document the evidence boundary and add the closest deterministic contract test without claiming an exact reproduction.

7. Implement the smallest durable remediation.
   - Follow project architecture and local test-first rules.
   - Preserve event durability, idempotency, tenant isolation, and explicit authorization checks.
   - Prefer deterministic transaction and lock ordering over blind retries. Add bounded retries only when the operation is idempotent and the transient classification is proven.
   - Preserve error classes and structured context in diagnostic logs without emitting payloads or secrets.
   - When a second occurrence reveals a defect class, sweep the relevant surface instead of patching incidents one at a time.
   - Keep provider-account changes scoped to the affected account. Never substitute one tenant's credentials for another.

8. Validate before publication.
   - Run focused regression tests first, then the repository's full required tests, type checks, lint/format gates, migrations, and infrastructure validation.
   - Test schema changes from an empty database and through upgrade/downgrade paths when supported.
   - Inspect `git diff --check`, the exact changed-file set, and scans for secrets, PII, absolute machine paths, and unrelated edits.
   - Commit by logical concern. Open or update a PR when required and wait for exact-head CI before recommending merge.

9. Deploy and verify only when authorized.
   - Treat merge, release, deploy, secret rotation, webhook replay, queue replay, and data repair as separate production mutations.
   - Verify the new revision, image, migration head, health checks, and traffic allocation.
   - Run a safe canary through the repaired path. For webhooks or queues, use a provider-supported replay only with explicit authorization and confirmed idempotency.
   - Re-run the original log queries over a clearly stated post-deploy window. Confirm the target fingerprint is absent or reduced, the success path is present, and no new cluster appeared.
   - If credentials must change, deploy compatible code first, rotate the intended account only, then confirm signed traffic succeeds.

10. Clean up and report.
    - Stop only the local servers, containers, monitors, and browser sessions started for this task. Verify they exited and leave inherited services untouched.
    - Report findings by priority, remediation commits or PR, validation evidence, deployment state, and any deferred production action.
    - Distinguish `fixed locally`, `green in CI`, `deployed`, and `verified in production`; never collapse them into “done.”

## Evidence Ledger

Maintain a compact ledger during the run:

| Priority | Fingerprint | Count/window | Active revision? | Root cause | Disposition | Verification |
| --- | --- | --- | --- | --- | --- | --- |
| P1 | `DeadlockDetected` on webhook projection | 6 / 24h | Yes | Conflicting lock order | Fixed in PR | Concurrent regression + CI |

Use sanitized values. Link to durable logs or dashboards when access permits; otherwise record the exact query so another operator can reproduce it.

## Stop Conditions

Stop and request direction when:

- the target environment, account, or service cannot be resolved safely;
- a requested query would expose secrets or raw PII;
- evidence points to destructive data repair, credential rotation, replay, rollback, or deployment that was not authorized;
- local code does not match the deployed artifact and the correct source cannot be identified;
- the fix would materially expand beyond the reported failure class;
- validation cannot distinguish the proposed fix from an unrelated environment failure.

## Resources

- `references/provider-playbooks.md`: Read the matching section for Cloud Run, CloudWatch/ECS, Kubernetes, systemd, or generic JSON logs. Adapt commands to the discovered environment; do not copy placeholder identifiers literally.
