---
name: blast-radius
description: "Find what a change could break beyond the diff before it ships, and prove the one fact it is safe because of by running real code. Use for /blast-radius, 'what could this break', 'is it safe to ship while people are using it', or a deploy to a live service or study."
---

# Blast radius

Find what a change breaks somewhere else, before it ships. Listing the callers is not the job: grep does that in a second. The job is the breakage grep does not show.

## Do not trust your own writeup

A blast-radius writeup that sounds right is worthless. It reads as convincing whether or not it is true. Find the one or two facts the whole thing depends on and prove them by running code.

### How sure are you

For each fact the change's safety depends on, get it as far down this list as is cheap, and say where it stopped.

1. You said so. Worthless on its own.
2. You pointed at the line. A real `file:line`, or the library's own source.
3. You showed the bad case cannot happen. You walked the failure step by step and it does not reach.
4. You ran it. A script or test that calls the real code and fails loudly if you are wrong.
5. You reproduced it in the running app or a staging copy.

Step 4 is usually one small script that imports the same library the app ships and calls the exact function you are worried about.

## Steps

1. Read the change. The diff, the symbols it adds, changes, and deletes, and what it now does differently, including the part the diff does not spell out. Pull the PR and its commits with `gh`.
2. Find the one fact it is safe because of. Most changes that look risky are safe because of a single fact, like "this call only drops already-dead cache entries". Find that fact. If it holds, most risky cases are cleared at once.
3. Look where grep stops. Read the source of the library you call, and check its pinned version and any local patch. Work out when things run: async order, teardown, retries, timeouts. Follow what a symbol search misses: the JSON an API returns, a DB column, a wire format, a prompt or rubric that another service reads, a feature flag, a scheduled job, code three hops downstream.
4. For a live system, check the running state too:
   - Who is using it now: active participants or sessions, running jobs, open connections. Get the count from the live source, not from a dashboard cache.
   - What happens to in-flight work during the rollout: a request mid-call, a session mid-task, a job mid-write, a migration against live rows.
   - Whether old and new versions can run side by side during the rollout.
   - The rollback path, and whether rollback loses data written in between.
   - The check you will run right after the deploy to confirm it worked.
5. Be honest about each risk. Give it a real chance of happening and a real cost if it does. Keep the risks you confirmed. List the ones you checked and cleared separately. Cite a real `file:line`. A search that finds nothing is still an answer. Never make up a caller or an API.
6. Prove the one fact. Write a script or test that runs the real code, run it, and paste what happened.
7. For a big or wide change, get a second opinion from another model family with the `codex` skill in challenge mode, and merge the findings. Different models catch different real bugs.

## What to hand back

- **What it does.** What changed, including the part that is not obvious.
- **The one fact it is safe because of.** State it, say which step you got it to, and show the proof. If you could not prove it, write unproven.
- **Live state.** For a live system: who is active, what happens to in-flight work, the rollback path, and the post-deploy check.
- **Risks.** Each names how it breaks, the `file:line`, how likely and how bad, and how to check.
- **Cleared.** What you checked and why it is fine.
- **Before you merge or deploy.** The cheapest test or repro that catches the real bug, including the script you wrote.

Do not deploy or change live state as part of this skill. Deployment follows the user's existing permissions.
