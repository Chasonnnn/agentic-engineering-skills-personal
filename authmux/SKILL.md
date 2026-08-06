---
name: authmux
description: Safely route AWS, Google Cloud, GitHub CLI, and SSH operations through repository-bound authmux Authentication Contexts. Use when authmux is installed and a task involves provider status, login, or authenticated commands; when a repository contains `.authmux.toml`; when the user asks an agent to avoid the wrong cloud account, project, GitHub identity, or SSH session; or when multiple projects use different provider identities concurrently. Resolve intent, verify identity evidence, use process-scoped execution where supported, and fail closed instead of switching global credentials or bypassing authmux.
---

# Authmux

Use authmux as the authentication-context boundary for provider CLI work. Provider CLIs and operating-system credential stores retain credential custody; never extract, copy, print, or persist credentials.

## Core Rules

- Read the target repository's `AGENTS.md` and provider/deployment instructions first.
- Prefer a repository Project Binding over an explicit context name.
- Before authenticated work, run `authmux context show` and confirm the selected Authentication Context and Expected Identity are appropriate for the task.
- Run each supported provider command through `authmux exec`; do not launch the entire coding agent inside authmux.
- Never bypass a mismatch, unsupported provider composition, inactive SSH transport, or context-drift failure with a bare provider command.
- Login is explicit and provider-owned. Keep interactive browser, device-code, password, and MFA exchanges attached to the user's terminal; do not reproduce their contents in reports.
- Do not infer expiration or Session Usability from local metadata. Preserve authmux's reported evidence boundary.

## Workflow

### 1. Resolve the intended context

From the repository or a nested directory:

```console
authmux context show
```

Confirm:

- `selection` is `project binding` when `.authmux.toml` is expected;
- the binding source is inside the current Git root;
- the Provider Profile and Expected Identity match the user's project;
- no explicit `--context` is needed for normal project work.

If no binding resolves, stop unless the user or repository instructions already identify the intended context. Do not guess from profile names, the currently active native account, or another repository.

An explicitly confirmed context can be inspected from any directory:

```console
authmux context show --context CONTEXT
```

### 2. Observe authentication state

Inspect one provider in the selected context:

```console
authmux status --provider aws
authmux status --provider gcp
authmux status --provider github
authmux status --provider ssh
```

Inspect every configured context for an agent preflight:

```console
authmux status --all --json
```

Treat the result precisely:

- `identity_match: match` establishes only the reported identity comparison.
- `session_usability: indeterminate` is not live validation.
- `evidence_level: local_metadata` does not prove provider access.
- a nonzero aggregate exit means at least one provider failed; successful observations remain useful, but the failing provider is not ready.
- GitHub status may contact GitHub. AWS and GCP status remain local observations; guarded execution supplies stronger live evidence where supported.

Use JSON for automation. Do not scrape human-readable output when a JSON form exists.

When local configuration or CLI readiness is unclear, diagnose without claiming a live Session:

```console
authmux doctor --provider PROVIDER
```

Doctor results do not replace guarded execution or an active SSH transport preflight.

### 3. Reauthenticate only when required

Use the exact resolved context and one provider:

```console
authmux login CONTEXT --provider aws
authmux login CONTEXT --provider gcp
authmux login CONTEXT --provider github
authmux login CONTEXT --provider ssh
```

Login may mutate provider-owned credential or Session state and may require a browser or MFA. Do not retry with a different identity, switch a shared global profile, capture authorization URLs, or claim success from the native command alone. Verify authmux's post-login result.

When interactive input is unavailable, report the exact login command and stop that provider operation. Do not attempt to automate MFA or obtain a one-time code from another source.

### 4. Execute with the selected context

Inside a bound repository:

```console
authmux exec -- aws s3 ls
authmux exec -- terraform plan
authmux exec -- gcloud projects describe PROJECT_ID
authmux exec -- gh pr list
```

Use an explicit context only outside a bound repository and only after confirming it:

```console
authmux exec --context CONTEXT -- aws sts get-caller-identity
```

Authmux launches the literal argument vector, filters ambient credential variables, applies only the selected Provider Profile, re-resolves the context before spawn, and fails closed on identity mismatch or drift. Preserve the child exit code and do not retry through another context.

### 5. Handle provider-specific boundaries

| Provider | Supported agent path | Boundary |
| --- | --- | --- |
| AWS | `authmux exec -- aws ...`, Terraform, or deployment commands | Guarded execution contacts STS, compares the account to the Expected Identity, and may refresh AWS-owned caches. |
| Google Cloud | `authmux exec -- gcloud ...` for a declared gcloud plane; non-gcloud children require an explicitly declared ADC plane | Local identity/project selection can be checked, but child execution may still discover an expired provider Session. |
| GitHub | `authmux exec -- gh ...` | Only `gh` is supported. `GH_CONFIG_DIR` does not select raw Git SSH keys or a Git credential helper. |
| SSH | Preflight with status, then use native `ssh`, `scp`, or `rsync` | Generic authmux exec is unsupported. Authmux observes reusable OpenSSH transport state, not remote Session expiry. |

For an SSH-dependent automated operation:

```console
authmux status --context CONTEXT --provider ssh --require-active-transport
```

If inactive or unverifiable, stop before submitting work and provide:

```console
authmux login CONTEXT --provider ssh
```

After a successful preflight, use the repository's native SSH host alias normally. A ControlMaster can lapse after sleep, network changes, process termination, or server disconnects; its configured persistence is not an authentication lease.

Raw `git fetch`, `git pull`, and `git push` continue through the repository's native Git/SSH configuration. Do not wrap them in a GitHub authmux context until authmux adds a tested raw-Git selector contract.

## Failure Handling

Stop and report the sanitized failure when:

- the Project Binding is missing, outside the current Git root, or resolves to an unexpected context;
- Expected and Observed Identities mismatch;
- authmux cannot establish the evidence required for guarded execution;
- the provider requires interactive Reauthentication that the user has not completed;
- mixed providers require an explicit `--provider` choice;
- SSH transport is inactive or unverifiable before remote automation;
- a requested child is unsupported by the selected Provider Adapter.

Never work around these conditions by exporting `AWS_PROFILE`, `CLOUDSDK_ACTIVE_CONFIG_NAME`, `GH_TOKEN`, `GOOGLE_APPLICATION_CREDENTIALS`, or another selector/credential manually. Never run `gh auth switch`, silently activate a gcloud configuration, or substitute credentials from another project.

## Completion Report

Report only:

- resolved Authentication Context and provider;
- whether Identity Match and required Session/transport evidence passed;
- the guarded command category and exit outcome;
- the exact sanitized Reauthentication command when blocked.

Do not include provider tokens, one-time codes, signed URLs, raw provider output, full credential paths, or secrets from child environments.
