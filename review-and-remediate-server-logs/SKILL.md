---
name: review-and-remediate-server-logs
description: Diagnose server-log failures and carry authorized fixes through validation and post-deployment verification.
---

# Review and remediate server logs

Resolve the environment, account, services, time window, and requested outcome from project context. Continue through authorized diagnosis, fixes, and verification. Publication, deployment, replay, credential rotation, and data repair are not implied by read-only log access. Preserve dirty work and inherited services.

## Evidence

Use the approved authentication path and the matching section of [references/provider-playbooks.md](references/provider-playbooks.md). Identify active revisions, traffic allocation, and deployed source/image before mapping a log event to local code.

Collect bounded, sanitized data. Select safe fields before command output reaches the transcript. Do not print or save raw credentials, payloads, or personal data as a temporary step toward sanitization. If necessary fields cannot be safely isolated, change the query or report the evidence limit. Hashing low-entropy personal values or secrets does not make them safe to disclose.

Record absolute query bounds, service/revision, filters, sampling, pagination, and retention limits. Label counts from capped results as observed samples or lower bounds. Use aggregate queries or complete pagination for population counts and ratios; compare numerator and denominator from the same window and population. Separate application from request logs to avoid double counting.

Cluster by stable error class, route/job, frame, or provider code. Keep a compact ledger of priority, fingerprint, count/window and coverage, deployed revision, hypothesis, correction, and verification. Compare the failure and success paths. Absence of matching logs does not prove health, especially with sampling or ingestion delay.

## Diagnosis and correction

Prioritize by impact: outages and exposure, durable-event loss and repeated server failures, then recovered failures and diagnostic noise. A 4xx is not automatically expected; verify its caller, contract, frequency, and available success path. Treat platform failures, configuration drift, and application defects separately.

Trace actionable clusters through deployed callers and relevant transaction, concurrency, tenant, retry, and logging boundaries. State evidence and a disconfirming check before editing. Reproduce the production shape where practical: the relevant database engine, signed request structure, or concurrency condition. Where exact reproduction is unavailable, state the limit and test the closest meaningful contract without claiming equivalence.

Implement the smallest durable correction within scope. Preserve event durability, idempotency, tenant isolation, and useful diagnostics without payload leakage. A repeated incident can justify checking a shared cause in the relevant surface; it does not automatically authorize a broad rewrite.

Run focused regression checks and project-required gates. For schema changes, validate applicable migration paths. Inspect changed files for unrelated work and exposed data before authorized publication. Report validation failures separately from environment/setup failures.

## Deployment verification

After an authorized deployment, verify artifact identity, applicable migrations, health, and traffic. Run a safe canary through the repaired path and repeat the original query over a stated post-deployment window. Report target-fingerprint change, observed success traffic, new failures, and coverage limits. Low traffic or a short quiet window does not establish that the defect is eliminated.

Replays and credential changes need the authorization and idempotency or rollout plan appropriate to the operation. Do not blindly prescribe code-first rotation during an active exposure; use the incident's containment and compatibility requirements.

Stop dependent work when the target identity is unresolved, the deployed source cannot be identified, or the next action exceeds authorization. Continue independent permitted work. Cleanup only task-owned resources intended to be temporary. Report findings, local fixes, CI, deployment, live verification, and unresolved actions as distinct states.
