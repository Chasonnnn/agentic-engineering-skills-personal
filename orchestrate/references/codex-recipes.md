# Codex delegates

Codex invocation, session continuity, timeout handling, artifact capture, and completion checks are owned by the sibling `codex` skill. Read its [execution reference](../../codex/references/execution.md); for reviews also read its [scope reference](../../codex/references/review.md). Use its runner, not a second wrapper.

Resolve the canonical `orchestrate` directory through installation symlinks, then locate `../codex`. Both folders must be available; if separately installed, locate the installed `codex` skill. If it is missing, report the missing dependency rather than inventing another runner. Native subagent orchestration does not require it.

Pass the role defaults from `orchestrate/SKILL.md` explicitly unless the user/project overrides them. Select workspace-write for authorized implementation and read-only plus `--review` for a gate. Prepare a saved task prompt using the applicable template. Leave implementation uncommitted unless the assignment explicitly permits a local commit.

A follow-up can resume the recorded session. A fresh independent review needs a fresh session. If a verified finding is routed to its finder for repair, that agent becomes the implementer for the new delta; assign another reviewer.

The orchestrator owns task progress and recovery decisions. Use the runner's artifacts and actual process/repository state to diagnose interruptions. Do not infer a hang from silence or automatically resubmit potentially mutating work.
