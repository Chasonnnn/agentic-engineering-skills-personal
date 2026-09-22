# PR disposition

| Classification | Evidence required | Action within authorized scope |
|---|---|---|
| Valid | Current-base behavior needs correction; the supplied patch may still be wrong | Fix and test, publish in the consolidated PR, then close the source PR with that link |
| Duplicate | An equivalent fix covers the same behavior | Consolidate the fix; close with a link to the published replacement or already integrated fix |
| Invalid | Affirmative source or test evidence refutes the claim or shows it no longer applies | Explain the evidence and close directly |
| Release/tooling | Automation, dependency, or workflow update | Leave unless included in the request |
| Needs-info | Missing context or inconclusive reproduction | Name the missing evidence; do not close as invalid |

Record PR URL, claimed problem, current base/head SHAs, relevant source and tests, disposition, and replacement state. A moved file or an unsuccessful reproduction does not alone prove the problem disappeared. Do not label a valid finding invalid merely because its proposed patch weakens tests or removes a required boundary.

Closure after publishing the consolidated replacement:

```text
The validated finding is fixed in [replacement PR], commit [SHA].
Validation: [relevant evidence]. Closing this source PR in favor of that replacement.
The replacement remains open; [current CI state and remaining gates]. It has not been merged or deployed.
```

If the equivalent fix is already integrated, cite its base commit instead. Local-only fixes, unpublished commits, and unverified proposed coverage do not justify closing valid source PRs.

Invalid closure:

```text
At [base SHA], [specific source/test evidence] contradicts [the claim].
Closing because [bounded reason].
```

Under the default workflow, closure in favor of the consolidated open replacement is expected after local validation and publication. Respect explicit read-only limits and excluded drafts. Preserve one auditable mapping from each closed source PR to its replacement commit; do not mark unresolved findings as covered.

Treat credential changes, removed authorization/tenant boundaries, broad churn, weakened tests, and unsupported performance claims as review evidence. Apply project and user scope to the decision; these signals do not themselves authorize a wider rewrite or require stopping all independent work.
