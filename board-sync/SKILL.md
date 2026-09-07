---
name: board-sync
description: Sync planning documents to GitHub Project epics and nested sub-issues, with optional stale-issue reconciliation.
disable-model-invocation: true
---

# Board sync

Resolve the repository, board owner/number, source documents, stable project/workstream keys, and requested scope from context. Ask only for missing inputs. Use the approved GitHub authentication path; where authmux applies, route each `gh` leaf command through it. A preview request produces a proposed change set, not mutations. Comments, closures, and board edits must be within the user's request.

## Data model

One epic represents a workstream; its slices are sub-issues. Only epics go on the board. Keep acceptance criteria in issue bodies and link the authoritative spec. Match an existing relevant epic's structure and labels, including an intentional absence of labels.

Use `<!-- board-sync:<project-key>:<slice-key> -->` in owned issue bodies. Use a distinct stable marker for owned evidence comments. Reconcile exact markers before writing. Preserve human content when updating; ambiguous ownership requires resolution, not replacement. Prepare multiline bodies with `--body-file` or structured API input.

## Reconciliation

1. Capture the board's node ID, Status field ID, full option map, and item IDs. Enumerate all relevant board items and open/closed issues; do not treat a capped search as a complete inventory. Search markers first, then known workstream titles for older unmarked issues. Confirm candidates by repository, identity, and source references; titles alone do not establish a match. Create only after absence is established. Stop duplicate creation when multiple candidates match.
2. Map each epic/slice to its existing or new issue. Capture issue number, database ID, and URL separately. Update existing issues in place, including completed work where requested. Refresh the map after each mutation so a partial rerun resumes from actual state.
3. Create/update the epic, then slices. Inspect current parent and child relations before linking. Existing correct links are no-ops; do not move a slice from another parent without task authorization. Verify the final paginated child set contains the intended slices. Report unrelated existing children rather than deleting them to force equality.
4. Add only missing epic board items, then set their Status using the board's configured option IDs. Verify each intended epic's item identity and actual Status, and verify that this task did not add its slices to the board. Match repository-qualified issue URLs or node IDs, not issue numbers alone. Counts are diagnostics, not proof: concurrent users may change the board.
5. If stale refresh or lifecycle updates are requested, reconcile source evidence with issue state. Close only work established as completed or abandoned within that scope. An epic remains open while its required slices remain open. Preserve historical outcomes and avoid duplicate evidence comments.

Read [references/github-projects.md](references/github-projects.md) for API ID handling and pagination. Report epic URLs, slice links, verified membership/status, changes, and any incomplete inventory or failed operation. A permission error is a partial outcome; continue independent authorized work and use the configured authentication handoff without changing identities or repeatedly retrying mutations.
