# Codex delegates

Codex invocation, session continuity, timeout handling, artifact capture, and completion checks are owned by the sibling `codex` skill. Read its [execution reference](../../codex/references/execution.md); for reviews also read its [scope reference](../../codex/references/review.md). Use its runner, not a second wrapper.

Resolve the canonical `orchestrate` directory through installation symlinks, then locate `../codex`. Both folders must be available; if separately installed, locate the installed `codex` skill. If it is missing, report the missing dependency rather than inventing another runner. Native subagent orchestration does not require it.

Pass the role defaults from `orchestrate/SKILL.md` explicitly unless the user/project overrides them. Select workspace-write for authorized implementation and read-only plus `--review` for a gate. Prepare a saved task prompt using the applicable template. Leave implementation uncommitted unless the assignment explicitly permits a local commit.

Standing lanes: record the session ID from the first run's `result.json` in the dispatch plan. Send every later message for that track (repair list, next task, next plan-review round) with `--resume <session id>` and a new `--out` directory. Launch each resumed run as a tracked background command so its completion notice reaches the orchestrator. Build lanes use `--model gpt-6.1-sol --sandbox workspace-write`; design and review lanes use `--model gpt-6-astra --sandbox read-only`. Pass `--effort xhigh` on both.

A round-1 review and a final gate need a fresh session. A resumed reviewer is not independent of its earlier rounds; use it only to verify a known findings list.

The orchestrator owns task progress and recovery decisions. Use the runner's artifacts and actual process/repository state to diagnose interruptions. Do not infer a hang from silence or automatically resubmit potentially mutating work.
