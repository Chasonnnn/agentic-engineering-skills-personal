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
- Every issue body this skill creates carries a marker `<!-- board-sync:<project-key>:<slice-key> -->` so re-runs update in place instead of duplicating. The same convention covers **comments** this skill posts (e.g. an epic evidence comment gets `<project-key>:<epic-key>-evidence`) — search for the marker before posting so re-runs don't stack duplicates.
- **All bodies via `--body-file`** from a scratchpad `.md` — never inline `--body "..."` (em-dashes, backticks, and `#123` refs get mangled or history-expanded by the shell).

## Steps

1. **Pre-flight id capture.** One block, up front: `gh project view <num> --owner <org> --format json --jq .id` → the project **node id** (`PVT_...`); `gh project field-list <num> --owner <org>` → the Status **field id** (`PVTSSF_...`) and the **full** option-id map (read every option — the board's visible items may not use them all). Start a scratchpad map `{slice → issue# → db id}` and keep it current all run. Done when: node id, field id, and option map are cached.
2. **Discover conventions.** `gh issue view <ref> --json title,body,labels` for the body structure and labels — **mimic the reference epic's labels even if that means none** (categorization may ride title prefixes). Board state via `gh project item-list <num> --owner <org> --format json --limit 100` — ALWAYS filtered at call time (`--jq` or a python one-liner); shape gotcha: the issue number is nested at `content.number` but board Status is top-level `status`. Record the pre-change board item count for the later leak-check. Done when: body sections, labels, Status value, and baseline count are known.
3. **Reconcile existing state.** `gh search issues --repo <repo> "board-sync:<project-key> in:body"` (fallback: `gh issue list --search`). An empty result is NOT proof of absence when prior epics predate the marker convention — supplement with title searches for the workstream keys (`"WS12 in:title"`) before concluding create-not-update. Anything already found gets `gh issue edit`, not re-creation. Done when: every slice is mapped to create-or-update.
4. **Epic first.** Write the body (goal, decision basis, batch/slice structure, spec pointer, DoD, marker) to scratchpad; create with `--body-file`. `gh issue create` prints only the URL — derive the number from the trailing path segment (`${url##*/}`). Done when: epic number is in the map.
5. **Sub-issues, then links — fixed order.** Write bodies (they may now reference the epic `#`), create each sub-issue (capture number), fetch each **database id** (`gh api repos/<o>/<r>/issues/<n> --jq .id`), then link: `gh api repos/<o>/<r>/issues/<epic_number>/sub_issues -X POST -F sub_issue_id=<db_id>` — must be `-F` (typed integer; `-f` sends a string and the API rejects it) and the db id, **never** the issue number. Verify twice: each POST response's `.sub_issues_summary.total` increments, and a final `gh api .../issues/<epic_number>/sub_issues --jq '.[] | "#\(.number) \(.title)"'` (never dump raw — each element embeds a ~5KB repository object) lists exactly the slice set. Done when: the verified list matches.
6. **Board.** `gh project item-add <num> --owner <org> --url <epic-url> --format json` — epic only; capture the returned item id (`PVTI_...`). Set Status: `gh project item-edit --project-id <PVT_…> --id <PVTI_…> --field-id <PVTSSF_…> --single-select-option-id <opt>` — all four ids required (node id from step 1, item id from item-add; the project **number** does not work as `--project-id`). `item-edit` prints nothing on success — verify via the assertions: board item-count delta == number of epics added, AND filtering item-list for `content.number >= <first new number>` returns only the epic(s). Done when: both assertions pass.
7. **Stale refresh (if in scope).** Walk open issues; where the source docs changed an issue's reality, add a 2–4 sentence status comment (via `--body-file`) citing the decision/doc that changed it. **Close only when the docs explicitly state the work is done or dead, with evidence; otherwise comment.** Done when: every touched issue is listed with a one-line rationale.
8. **Report.** Epic URL/number; slice→sub-issue table with nesting confirmed; board + status result with the leak-check numbers; touched-issues list; anything blocked with the exact failing command.

## Reference — gotchas

- **Auth:** the token often already carries the `project` scope — attempt the mutations first. Only on a scope/permission error: finish the issue-level work, capture the exact command + error, and tell the user to run `gh auth refresh -h github.com -s project` themselves. Never self-escalate, never loop on the failing call.
- **Two big-JSON endpoints must always be filtered at call time:** `gh project item-list` (60KB+ raw) and `issues/{n}/sub_issues` (full embedded repository objects). Raw dumps blow the context for nothing.
- **The four-id plumbing** is the step that bites: `item-edit` needs project node id + item id + field id + option id, and `field-list` alone never yields the node id — that's what `project view --jq .id` is for.
- Epic lifecycle: the epic stays open while any sub-issue is open; close sub-issues as slices land; close the epic when all are done and set its board Status accordingly. Syncing an **already-completed** workstream retroactively: create → link → close all sub-issues → close the epic — linking requires nothing about state, and closing after linking does not disturb the parent/sub-issue relation.
- Cross-org reuse: nothing here is repo-specific — the marker key, reference issue, and source docs are the only per-project inputs.
