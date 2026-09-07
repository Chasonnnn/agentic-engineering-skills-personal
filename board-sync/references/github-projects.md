# GitHub Projects mechanics

Commands below use `gh`; apply the repository's auth wrapper where required.

- `gh project view NUMBER --owner OWNER --format json --jq .id` returns the project node ID. `gh project field-list` supplies the Status field and all its option IDs. Resolve the actual board field rather than assuming English status values.
- `gh project item-list --limit N` has a finite limit. Compare fetched items with its total count and increase the limit until complete, or use cursor-paginated GraphQL including `pageInfo.hasNextPage`. Apply the same completeness check to field lists. Retain identity and pagination metadata when filtering output.
- Search results can be capped or delayed. For creation decisions, reconcile a paginated issue inventory including closed issues (`gh api --paginate 'repos/OWNER/REPO/issues?state=all&per_page=100'`) and filter out pull requests. Preserve repository-qualified URLs and exact markers. Paginate comments when locating owned comment markers.
- `gh issue create --body-file FILE` returns a URL. Resolve the issue's database ID with `gh api repos/OWNER/REPO/issues/NUMBER --jq .id`; it is different from its issue number and node ID.
- Link with `gh api repos/OWNER/REPO/issues/EPIC/sub_issues -X POST -F sub_issue_id=DATABASE_ID`. `-F` preserves the integer type. The response represents the child issue, so do not use its sub-issue summary as the parent count. Verify via the paginated parent endpoint `repos/OWNER/REPO/issues/EPIC/sub_issues` and inspect an existing child's `/parent` endpoint before reparenting. A failed lookup is not proof that no parent exists.
- `gh project item-add NUMBER --owner OWNER --url EPIC_URL --format json` returns the item ID. `item-edit` needs project node ID, item ID, field ID, and option ID: `--project-id`, `--id`, `--field-id`, `--single-select-option-id`. Verify the resulting item and status even when the edit prints nothing.

Select only needed fields from large results, while preserving counts/cursors needed to establish completeness. API failures and partial inventories must remain visible.

[GitHub sub-issue API](https://docs.github.com/en/rest/issues/sub-issues) · [Project item listing](https://cli.github.com/manual/gh_project_item-list)
