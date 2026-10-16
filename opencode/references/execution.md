# Shared OpenCode execution

Resolve `OPENCODE_SKILL_DIR` from the canonical directory containing the loaded `opencode/SKILL.md`, following installation symlinks. Use the project's approved Python runtime; the runner requires only the standard library. The CLI installs to `~/.opencode/bin`; if `opencode` is not on `PATH`, prepend that directory. Check `opencode run --help` and `opencode models` if the installed CLI rejects an option or model. Authentication failures come from the CLI or the provider gateway; do not infer login state from credential files or environment variables.

Write the exact authorized task to a prompt file using a file-writing tool or a quoted heredoc. Choose a fresh output directory outside the reviewed source so artifacts do not enter its diff.

```bash
python "$OPENCODE_SKILL_DIR/scripts/opencode_run.py" \
  --repo "$REPO" --prompt "$PROMPT_FILE" --out "$RUN_DIR"
```

- Add `--review` for a review or challenge. OpenCode has no schema flag, so the runner appends `scripts/review.schema.json` to the prompt and validates the JSON answer itself.
- The runner pins `--model cornell/nto.gemini-4-argon` (Gemini 4 Argon through the Cornell AI Gateway). Pass `--model provider/model[#variant]` only for the user's chosen model from `opencode models`. Name the model in the report.
- Add `--resume "$SESSION_ID"` for a contextual follow-up. Use the `session_id` recorded in `result.json` for this task, never `--continue`. The runner refuses an ID that `opencode session list` does not show for the repository, because `opencode run --session` creates a missing session. A resumed reviewer is not a fresh independent reviewer.
- `--access` defaults to `read-only`. OpenCode allows edits and shell commands by default with no sandbox, so the runner denies edit, write, shell, execute, and subagent actions through `OPENCODE_CONFIG_CONTENT`. Read, search, web, and skill tools stay available; keep external-action limits in the prompt. The question tool is denied in every mode, because a headless run cannot answer it.
- Use `--access edit` only for an authorized implementation task; it allows file edits and keeps commands denied, so the delegate cannot run tests. Use `--access full` only for an authorized task in an isolated checkout; it allows unsandboxed shell commands. Review prompts remain read-only.
- `result.json` lists `project_config` when the repository has its own `opencode.json`, `opencode.jsonc`, or `.opencode`. Inspect it before relying on read-only access, because project rules can add permissions.
- Set `--timeout` to the task's deadline (default 900 seconds). The host tool timeout must exceed it or use the host's background execution facility.

The runner records the prompt as sent, argv, the inline permission config, JSON step events, stderr, final answer, and `result.json`. It sends the prompt through stdin, runs a private `--standalone` server inside its own process group, captures producer exit status, treats any `error` event as failure, requires a nonempty answer from the last step, and bounds the process group. `usage` sums `step_finish` events; the final step often reports none, so usage is a lower bound.

`status` is `completed`, `failed`, or `incomplete`. With `--review`, `review_verdict` is `PASS`, `FAIL`, or `INCOMPLETE`; missing completion, invalid output, omitted checks, or reviewer-declared limits cannot yield PASS. P0/P1 findings block a complete review; P2/P3 remain visible. Read findings even when the run is incomplete. The runner checks the response contract, not whether claimed coverage or findings are true.

Nonzero exit means the task failed, is incomplete, or has blocking review findings; inspect `result.json` to distinguish them. A session ID alone proves only that a session started. Never promote partial output into a clean verdict.

For background work, retain the process handle and artifact path. A silent log warrants inspection, not a diagnosis of a hang. Before retrying after interruption or timeout, reconcile repository changes, child processes, and any external jobs. The runner does not automatically replay tasks or cancel external jobs. Check live state again after compaction before reporting that work is running.
