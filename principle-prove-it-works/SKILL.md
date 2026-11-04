---
name: principle-prove-it-works
description: "Apply after completing a task, before declaring done. Verify against the real artifact (run the feature, read the actual value, inspect the diff), not a proxy, self-report, or 'it compiles.'"
disable-model-invocation: true
---

# Prove It Works

Verify every task output by checking the real thing directly. Do not infer from proxies, self-reports, or "it compiles."

**Why:** Unverified work has unknown correctness. Indirect verification (file mtimes, output freshness, agent self-reports, cached screenshots) feels cheaper than direct observation. Acting on a wrong inference costs far more than checking the source.

Check the real thing, not a proxy:
- Check process liveness directly, not through derived state. A poller or watcher counts as working only after it has caught a known event, such as a job you know failed.
- Read the actual value, not a cached or derived representation.
- Confirm the revision you test is the one the claim is about: compare `git rev-parse HEAD` with the remote branch after a pull.
- Read job state from its source: `squeue` or `sacct` on the cluster, `aws ecs describe-services` for a service, the run's own output file. A submitted job is not a finished job.
- Confirm a published page or artifact by reading it back, not by the publish call's success.
- Confirm a delegate's claim against the files or the diff, not its report.
- When verification fails, suspect the observation method before suspecting the system.

## Script the check when you can

The strongest proof is a deterministic script that re-runs the same comparison, not a one-time eyeball. Write the script, run it, and keep its output as an artifact a reviewer can re-run instead of trusting your word.

Keep the artifact visible for the user. For work that spans sessions, record the result in the decision log (the `show-me-your-work` skill).
