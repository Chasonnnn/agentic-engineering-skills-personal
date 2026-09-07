# Review scope and verdict

Use the same scope for ordinary review, custom-focus review, and challenge. Unless the user narrows it, include branch changes and current staged, unstaged, and untracked work. State the selected scope before dispatch.

Resolve the requested PR target or base to an existing local ref. Prefer the matching remote-tracking ref when the local branch is absent. Record its commit ID and merge base with HEAD. If resolution or diff generation fails, report INCOMPLETE; do not replace the failure with an empty diff or guess a nonexistent `main`. Fetch only when needed and permitted, and label stale remote information.

Capture a patch and file inventory with checked command exit statuses:

| Requested scope | Tracked diff |
|---|---|
| Branch plus current work | `git diff --binary "$MERGE_BASE" --` |
| Committed branch only | `git diff --binary "$MERGE_BASE" HEAD --` |
| Uncommitted only | `git diff --binary HEAD --` |

For scopes including current work, also enumerate `git ls-files --others --exclude-standard -z` and include each untracked file's content or an explicit limitation. `git diff` does not include untracked files. Detect unresolved conflicts with `git ls-files -u`; do not call conflicted or unreadable input a clean review. Ignored files are excluded unless requested. Empty confirmed scope means NO_CHANGES, not PASS.

Record HEAD, base/merge-base IDs, `git status --short`, and the patch/file inventory with the run. Do not let another writer change the reviewed checkout during review; use an isolated checkout for concurrent work. If the source changes, refresh the scope and review the new delta before applying an earlier verdict. A saved patch alone does not freeze the source files the reviewer can open.

Give the reviewer the patch, scope inventory, user focus, and relevant acceptance criteria. Require inspection of every in-scope file, or a named coverage gap. For refactors, compare the pre-change implementation and callers; for behavior changes, inspect consumers and whether tests exercise the changed path. Distinguish static review from executed tests. Report concrete defects with file:line evidence and a correction; avoid speculative findings and praise.

Run with `--review`. The final response must set `scope_complete`, list checks with their evidence, list unresolved limitations, and include findings with P0/P1/P2/P3 priority, title, evidence, and fix. A partial review may contain valid findings but must set `scope_complete: false` and name what remains. PASS means the reviewer reported complete coverage with no P0/P1 findings and no unresolved limits; it does not prove absence of defects or that tests ran.
