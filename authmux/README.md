# Authmux skill

Portable operating guidance for agents that use authmux to keep provider identities process-scoped and fail closed on wrong-account or wrong-project work.

## Requirements

- `authmux` installed on `PATH`.
- User-owned Authentication Contexts configured outside project repositories.
- Optional repository-local `.authmux.toml` Project Bindings.
- Native provider CLIs and credential stores remain authoritative.

The package contains no account names, account IDs, organization names, usernames, host aliases, credential paths, or credentials.

## Install

Clone the personal skills repository, then symlink this directory into the agent runtimes you use:

```sh
ln -s ~/agentic-engineering-skills-personal/authmux ~/.claude/skills/authmux
ln -s ~/agentic-engineering-skills-personal/authmux ~/.codex/skills/authmux
```

Do not copy user configuration into the skill. Each machine keeps its own authmux configuration and native provider Sessions.

## Activation

The skill may activate automatically when authmux is installed and a task involves authenticated provider CLI work, or when a repository contains `.authmux.toml`. Invoke it explicitly as `$authmux` when you want a full authentication preflight before cloud, GitHub CLI, or SSH operations.
