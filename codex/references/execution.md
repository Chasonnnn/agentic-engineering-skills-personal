# Shared Codex execution

Resolve `CODEX_SKILL_DIR` from the canonical directory containing the loaded `codex/SKILL.md`, following installation symlinks. Use the project's approved Python runtime; the runner requires only the standard library. Check `codex exec --help` and `codex exec resume --help` if the installed CLI rejects an option. Authentication failures come from the CLI; do not infer login state from credential files or environment variables.

Write the exact authorized task to a prompt file using a file-writing tool or a quoted heredoc. Choose a fresh output directory outside the reviewed source so artifacts do not enter its diff.

```bash
python "$CODEX_SKILL_DIR/scripts/codex_run.py" \
  --repo "$REPO" --prompt "$PROMPT_FILE" --out "$RUN_DIR" \
  --sandbox read-only --effort high
```

- Add `--review` for a review or challenge; it requires the structured response in `scripts/review.schema.json`.
- Add `--model` only for the user's chosen model or the calling skill's configured role. Otherwise the CLI retains its configured model. Review/challenge default to high; consult defaults to medium unless the caller specifies otherwise. Forward explicit supported effort overrides.
- Add `--resume "$SESSION_ID"` for a contextual follow-up. Use an ID recorded for this task, never `--last`. A resumed reviewer is not a fresh independent reviewer.
- Use `--sandbox workspace-write` only for an authorized implementation task. Sandbox selection does not grant external-action permission; keep that boundary in the task. Review prompts remain read-only. Configured connectors and host permissions still apply.
- Set `--timeout` to the task's deadline (default 600 seconds). The host tool timeout must exceed it or use the host's background execution facility.

The runner records the prompt, argv, JSONL events, stderr, final answer, and `result.json`. It passes prompts through stdin, captures producer exit status, requires a completed turn and nonempty final response, and bounds the local process group. No log parser prints model reasoning as a user answer.

`status` is `completed`, `failed`, or `incomplete`. With `--review`, `review_verdict` is `PASS`, `FAIL`, or `INCOMPLETE`; missing completion, invalid output, omitted checks, or reviewer-declared limits cannot yield PASS. P0/P1 findings block a complete review; P2/P3 remain visible. Read findings even when the run is incomplete. The runner checks the response contract, not whether claimed coverage or findings are true.

Nonzero exit means the task failed, is incomplete, or has blocking review findings; inspect `result.json` to distinguish them. A thread ID alone proves only that a session started. Never promote partial output into a clean verdict.

For background work, retain the process handle and artifact path. A silent log warrants inspection, not a diagnosis of a hang. Before retrying after interruption or timeout, reconcile repository changes, child processes, and any external jobs. The runner does not automatically replay tasks or cancel external jobs. Check live state again after compaction before reporting that work is running.
