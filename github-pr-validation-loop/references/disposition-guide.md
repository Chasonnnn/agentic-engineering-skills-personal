# PR disposition

| Classification | Evidence required | Action within authorized scope |
|---|---|---|
| Valid | Current-base behavior needs correction; the supplied patch may still be wrong | Implement or adapt a verified fix |
| Duplicate | An equivalent fix covers the same behavior | Link evidence; distinguish planned from integrated coverage |
| Invalid | Affirmative source or test evidence refutes the claim or shows it no longer applies | Explain that evidence before closing |
| Release/tooling | Automation, dependency, or workflow update | Leave unless included in the request |
| Needs-info | Missing context or inconclusive reproduction | Name the missing evidence; do not close as invalid |

Record PR URL, claimed problem, current base/head SHAs, relevant source and tests, disposition, and replacement state. A moved file or an unsuccessful reproduction does not alone prove the problem disappeared. Do not label a valid finding invalid merely because its proposed patch weakens tests or removes a required boundary.

Superseded closure:

```text
The finding is covered by [replacement], now integrated into [base at SHA].
Validation: [relevant evidence]. Closing this PR as superseded.
```

Invalid closure:

```text
At [base SHA], [specific source/test evidence] contradicts [the claim].
Closing because [bounded reason].
```

For a user-authorized closure in favor of an open replacement, explicitly say it is open and retain its remaining gates. Do not imply that publication alone means the fix landed.

Treat credential changes, removed authorization/tenant boundaries, broad churn, weakened tests, and unsupported performance claims as review evidence. Apply project and user scope to the decision; these signals do not themselves authorize a wider rewrite or require stopping all independent work.
