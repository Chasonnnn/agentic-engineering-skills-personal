---
name: board-sync
description: Sync planning state (specs/ADRs/roadmap) to a GitHub Project board as epic issues with nested sub-issues — epics visible on the board, slices hidden under them — plus an optional stale-issue refresh.
disable-model-invocation: true
---

## Inputs (collect before acting; ask only for what context doesn't already supply)

- Repo (`owner/name`) and project board (number + owner org/user).
- Source-of-truth docs: the batch/workstream spec (defines the slices), decision records (ADRs), roadmap/state doc.
- A format-reference issue — an existing epic to mimic. If none given, use the most recently updated epic already on the board.
- Scope: epic+sub-issues only, or also the stale-issue refresh.

## Model

- One **epic** per batch/workstream; one **sub-issue** per slice. Sub-issue bodies carry scope + acceptance criteria but the spec file stays the source of truth — link to it, don't duplicate it.
- **Only epics go on the board.** Slices are nested via GitHub's parent/sub-issue relation and are never added as board items — they're browsable inside the epic's pane.
- Every issue body this skill creates carries a marker `<!-- board-sync:<project-key>:<slice-key> -->` so re-runs update in place instead of duplicating.

## Steps

1. **Discover conventions.** `gh issue view <ref> --json title,body,labels` for the body structure and label set to match; `gh project field-list <num> --owner <org>` and `gh project item-list <num> --owner <org> --format json --limit 100` for the Status field options in use. Done when: you can name the body sections, labels, and Status value you will apply.
2. **Reconcile existing state.** `gh search issues --repo <repo> "board-sync:<project-key> in:body"` (fallback: `gh issue list --search`). Anything already marked gets `gh issue edit`, not re-creation. Done when: every slice is mapped to create-or-update.
3. **Epic.** Create/update the epic: goal, decision basis (ADR references), batch/slice structure, spec pointer, definition of done. Marker in body.
4. **Sub-issues.** Create/update one per slice (marker in each), then link each to the epic: `gh api repos/<owner>/<repo>/issues/<epic_number>/sub_issues -X POST -F sub_issue_id=<id>` — `sub_issue_id` is the numeric database `id` (`gh api .../issues/<n> --jq .id`), **not** the issue number. Done when: `GET .../issues/<epic_number>/sub_issues` lists exactly the slice set.
5. **Board.** `gh project item-add <num> --owner <org> --url <epic-url>` — the epic only. Set its Status with `gh project item-edit` (project-id, item-id, field-id, single-select-option-id — item-id comes from the item-add/item-list JSON, not the issue). Done when: the epic sits on the board with the right status and zero sub-issues appear as board items.
6. **Stale refresh (if in scope).** Walk open issues; where the source docs changed an issue's reality, add a 2–4 sentence status comment citing the decision/doc that changed it. **Close only when the docs explicitly state the work is done or dead, with evidence; otherwise comment.** Done when: every touched issue is listed with a one-line rationale.
7. **Report.** Epic URL/number; slice→sub-issue table with nesting confirmed; board + status result; touched-issues list; anything blocked with the exact failing command.

## Reference — gotchas

- Board mutations need the `project` token scope. On a scope/permission error: finish the issue-level work, capture the exact command + error, and tell the user to run `gh auth refresh -h github.com -s project` themselves. Never self-escalate, never loop on the failing call.
- The sub-issues API takes numeric database ids; passing issue numbers fails or links the wrong issue. Always resolve via `--jq .id` first.
- Epic lifecycle: the epic stays open while any sub-issue is open; close sub-issues as slices land; close the epic when all are done and set its board Status accordingly.
- Cross-org reuse: nothing here is repo-specific — the marker key, reference issue, and source docs are the only per-project inputs.
