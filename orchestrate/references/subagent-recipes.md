# Native and Claude subagents

Use the host's supported agent API and delivery semantics. Ordinary subagent final results may arrive automatically; teammates may need explicit messaging. Inspect the available tool contract instead of assuming every final is invisible or every helper reports to the root. Name agents and track their task, checkout, and current completion state. Treat duplicate notifications as the same result.

Isolate concurrent writers in worktrees or separate checkouts. Inspect dependency readiness before installing anything; use the project's package manager, lockfiles, and approved toolchain. Prefer existing verification targets. If a target fails in a worktree, diagnose its assumptions and preserve database/service isolation; do not bypass it against an arbitrary running database.

Give delegates the shared task fields in [prompt-templates.md](prompt-templates.md). Use local commits only when the assignment permits them; do not grant push permission through a generic template. Verify repository state before integrating a delivered result. Do not stash or commit someone else's dirty work as a cleanup shortcut.

For headless Claude review, verify the installed CLI's tool and permission controls. `--allowedTools` preapproves tool calls; it is not a read-only sandbox. Restrict the actual available tools, including connectors, and use applicable host isolation. If an enforceable read-only mode is required but unavailable, report that limitation rather than labeling a prompt restriction a sandbox.

After interruption, inspect the task's current state and artifacts before redispatch. A missing message or quiet log does not establish completion or failure. Send a focused follow-up describing the missing outcome once the state is known.

For CI watching, identify the exact commit and complete expected workflow set. Report missing, queued, running, failed, and successful workflows separately; one completed run or a watch process exiting cannot prove all required checks passed. Use supported waits with bounded status checks. Do not blindly rerun a failure until its cause and possible side effects are understood.
