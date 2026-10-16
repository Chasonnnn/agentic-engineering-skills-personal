# Shared agy execution

Resolve `AGY_SKILL_DIR` from the canonical directory containing the loaded `agy/SKILL.md`, following installation symlinks. Use the project's approved Python runtime; the runner requires only the standard library. Check `agy --help` and `agy models` if the installed CLI rejects an option or model. Authentication failures come from the CLI; do not infer login state from credential files or environment variables.

Write the exact authorized task to a prompt file using a file-writing tool or a quoted heredoc. Choose a fresh output directory outside the reviewed source so artifacts do not enter its diff.

```bash
python "$AGY_SKILL_DIR/scripts/agy_run.py" \
  --repo "$REPO" --prompt "$PROMPT_FILE" --out "$RUN_DIR"
```

- Add `--review` for a review or challenge; it enforces the structured response in `scripts/review.schema.json` through `agy --json-schema`.
- The runner pins `--model gemini-4-argon-high` (Gemini 4 Argon, High). Pass `--model` only for the user's chosen model ID from `agy models`. Pass `--effort` only for the user's chosen value; the model ID already carries a thinking level.
- Add `--resume "$CONVERSATION_ID"` for a contextual follow-up. Use the `conversation_id` recorded in `result.json` for this task, never `--continue`. A resumed reviewer is not a fresh independent reviewer.
- `--access` defaults to `read-only`: headless agy auto-denies file writes and shell commands and records them in `denied_actions`. It does not remove read, web, or browser tools; keep external-action limits in the prompt.
- Use `--access accept-edits` only for an authorized implementation task. It allows file edits; shell commands stay denied, so the delegate cannot run tests. `--access auto` also allows commands that agy classifies as safe, but agy can deny writes in a workspace that is not trusted. Review prompts remain read-only.
- Set `--timeout` to the task's deadline (default 900 seconds). The host tool timeout must exceed it or use the host's background execution facility.

The runner records the prompt, argv, NDJSON step events, stderr, final answer, and `result.json`. It sends the prompt as one stream-json message on stdin, disables slash-command expansion, captures producer exit status, requires a `SUCCESS` result event and a nonempty final response, and bounds the local process group. For reviews, `final.txt` holds the schema-checked `structured_output`, not the raw response text.

`status` is `completed`, `failed`, or `incomplete`. With `--review`, `review_verdict` is `PASS`, `FAIL`, or `INCOMPLETE`; missing completion, invalid output, omitted checks, or reviewer-declared limits cannot yield PASS. P0/P1 findings block a complete review; P2/P3 remain visible. Read findings even when the run is incomplete. The runner checks the response contract, not whether claimed coverage or findings are true.

An empty response with `denied_actions` means the delegate stopped at a permission it needed; report it as incomplete and name the denied actions. Nonzero exit means the task failed, is incomplete, or has blocking review findings; inspect `result.json` to distinguish them. A conversation ID alone proves only that a conversation started. Never promote partial output into a clean verdict.

For background work, retain the process handle and artifact path. A silent log warrants inspection, not a diagnosis of a hang. Before retrying after interruption or timeout, reconcile repository changes, child processes, and any external jobs. The runner does not automatically replay tasks or cancel external jobs. Check live state again after compaction before reporting that work is running.
