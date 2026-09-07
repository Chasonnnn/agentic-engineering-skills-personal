# orchestrate

Coordinates delegates, independent review, and integration. `codex` provides standalone second opinions and the shared CLI runner.

Install both sibling directories from this repository for Codex-backed delegation. Existing symlinks to the repository continue to work. Native subagent workflows do not depend on the Codex runner.

The entrypoint holds role defaults and coordination decisions. References cover conditional workflows, delegate prompts, native agent handling, and the connection to the Codex runner. User and project instructions override installation defaults. Neither skill grants commit, push, merge, deployment, or memory-write permission.
