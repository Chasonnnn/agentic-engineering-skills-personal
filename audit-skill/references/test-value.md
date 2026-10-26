# Test value

Apply this guidance to the audited skill's helper tests and testing instructions.

## Identify the protection

For a proposed removal, name the plausible regression, affected consumer, and assertion that would detect it. Trace the helper and callers before deciding that two tests protect the same behavior.

Distinguish redundant protection from lower-value unique protection. Uniqueness alone does not justify retention. A local diagnostic formatter may deserve less protection than authorization, redaction, failure propagation, or isolation. When accepting that trade-off, name the behavior left unguarded; do not call it duplicated.

## Removal candidates

| Pattern | Decision to check |
| --- | --- |
| Cartesian parameter tables | Keep representatives for meaningful branches, boundaries, and interactions. Repeated ordinary values need not cross every independent setting. |
| Helper tests repeated by integration tests | Verify that retained assertions catch the same defect through the same implementation. Merely executing the helper is insufficient. |
| Source searches, copied constants, or wording snapshots | Identify an external requirement or independent expected result. Without one, the test may only mirror implementation details. |
| Tests of mocks or library behavior | Determine whether the assertion checks project wiring or only repeats the fixture or library's own behavior. |
| Historical compatibility and phrase examples | Check current callers and supported behavior. Age or an old test name does not prove that a path is obsolete. |
| Internal tooling and presentation variants | Consider their maintenance cost and consequence of failure, including unique branches. Active code can have lower-priority tests. |

Use history to prioritize inspection. When investigating growth, separate collected cases from declarations and lines of test code.

## Preserve independent checks

An expected value imported from the implementation may verify wiring without guarding the intended value. Strengthening that assertion can be better than deleting it. Literal expectations can provide independent checks of required defaults, immutable text, or public contracts.

Similar test bodies can protect different consumers, languages, parser stages, or independent implementations. Preserve meaningful differences such as nonfinite numbers, encoding boundaries, and failure handling at separate layers.

Inspect both ends of shared fixtures. A consumer rendering saved JSON does not prove that the current producer still emits that JSON. Keep the producer assertion or establish equivalent executable coverage before removing it. A schema or rendered-text check may miss differences in the underlying object.

Coverage overlap can identify candidates, but it measures execution, not assertion strength. A test with no exclusive lines can still be the only independent check of a consequential contract.

## Scope edits and verification

Do not invent a removal quota or coverage allowance. Honor supplied targets and units, including whether a percentage is a minimum or ceiling. Apply cumulative loss limits to the original baseline. Do not meet a removal target by adding skips or hiding tests through runner configuration.

Record retained protection or explicitly accepted loss. Reconcile references across the complete selection; another group may remove a cited replacement. Remove newly orphaned test helpers only after checking other consumers. Keep unrelated production code and coverage settings unchanged.

Reuse baseline evidence when its relevant inputs remain unchanged. Batch planned removals and review fixes before final affected checks. Rerun invalidated checks after corrections; expand only when failures or shared dependencies warrant it. Passing the remaining suite does not prove that deleted assertions were redundant.
