# Conditional workflows

## Independent review and repair

Assign a stable diff to a reviewer who did not implement it. Require scope, completion state, actionable findings with file:line evidence and corrections, and one line per check actually performed. P0/P1 blocks; incomplete coverage remains INCOMPLETE even with no findings. Codex reviews use the sibling skill's structured review contract. Other reviewers report the same information in prose. A review verdict expresses review status, not permission to merge or push.

Verify findings before repair. Resolve choices needed by the implementer in the repair assignment. Recheck prior findings and review the new delta; keep implementer and reviewer distinct for that round. The original finder may repair verified findings if another agent reviews its changes. Reassess persistent failures rather than prescribing a fixed number of rounds or expanding scope automatically.

## TDD and behavior-preserving refactors

Use a separate test author when the project requires it or an independent contract adds value. Agree on the interface and expected behavior, then demonstrate that tests fail for the intended missing behavior. Give the implementer explicit test ownership: protect independent acceptance tests, but allow justified changes to tests that intentionally pin replaced behavior. Report a disputed test rather than silently weakening it.

For production-critical refactors, establish a meaningful before/after invariant before changing the seam. Use expected values independent of the new implementation. Honor project freeze windows. Test through affected callers when unit correctness would not establish that the change reaches the intended behavior.

## Parallel implementation and assembly

Separate independent tracks and freeze their shared interfaces. Assign one owner to shared files, canonical status headers, and assembly edits. Delegates report interface deviations; the orchestrator resolves them before integration.

Integrate only known task-owned changes. Check the combined behavior and relevant project suites, then review the assembled diff. Independent track passes do not establish integration correctness. Inspect uncommitted state before branch operations; avoid overwriting another track's work.

## Specifications and research

Use distinct read-only research questions when a fan-out adds value. Synthesize source-backed claims, then verify consequential factual claims against the cited code or primary sources. For major designs, run a fact-verifier and an independent architecture critique in parallel; they catch disjoint failures. Cap draft-verify iterations at two, then surface remaining disputes to the user. Preserve unresolved decisions and evidence gaps. Ask the user when a material choice cannot be resolved from existing authorization and context.

## Live operations

Before dispatch, specify the authorized system, readiness checks, owned run record, completion criteria, and failure conditions that require stopping. Define retry boundaries based on the operation's side effects; do not treat a local timeout as proof that an external job stopped.

Record per-item identifiers and outcomes, exact relevant errors, and services started versus inherited. Reconcile prior outcomes before continuing a run so completed work is not resubmitted. Preserve prior records. Cleanup only task-owned resources intended to be temporary; keep services the user requested to remain running.

For visible browser QA, use the user's requested browser and supported tooling and preserve the required visible surface. If unavailable, report the unmet QA condition instead of substituting source inspection or a headless run.

If two incidents share a defect class rather than only a symptom, stop iterating incident by incident: dispatch a read-only class-wide audit within the authorized scope and fix every instance in one gated round. Two similar symptoms alone do not authorize a repository-wide rewrite; confirm the shared class first.
