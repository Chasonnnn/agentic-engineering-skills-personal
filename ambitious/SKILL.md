---
name: ambitious
description: Raise the current task to its most ambitious reachable version along altitude, depth, and range, then do that version.
disable-model-invocation: true
---

# Ambitious

Apply this skill to the task in the arguments. With no arguments, apply it to the current task in the conversation.

The literal request is the minimum. Find the version that a top expert with full access would do, then do that version. Make the work go higher, deeper, or wider. Do not only make it bigger.

## Raise the task

Examine three directions. Use only the directions that change the work.

- **Altitude.** Find the outcome behind the request. Ask what happens after this task, and what goal that serves. Prefer a durable result to a single fix. For example, keep the app crash-free instead of fixing one crash. Replace a report about a problem with a process that detects the problem earlier.
- **Depth.** Name what a top practitioner does beyond the request, the rawest material they start from, and their methods and tools. Then use those methods and tools. New vocabulary is not a new method. Use a database, a statistical model, a profiler, or a test harness where an expert would use one. Start from raw data, logs, and source code, not from summaries. Test the assumptions in the request against that raw material. Where the data allows, find something new, such as an earlier signal, and confirm it on data you did not use to find it.
- **Range.** Describe the job with a verb, not a noun. "Persuade busy people about cause and effect under uncertainty" shows more relevant fields than "make a deck". Select the two to four fields that do this job best. Add one adversary whose job is to break the result, such as a short seller or a forensic accountant. Do the work that each specialist does. Do not imitate how they write or talk.

## Set the target

Set a target that seems too high, then treat it as solvable. Make the target measurable, for example a 200 ms page load instead of "faster". When an approach fails, change the approach before you lower the target. A partial result against a high target, with an honest gap report, is better than a full result against a low target.

## Use an outside check

Do not grade your own work. Select the external check before you start. Use a test, a benchmark, a backtest on held-out data, a simulation, a real run on the target platform, or an independent reviewer. Prefer a check that you can run many times for fast feedback. If no check exists and you can build one, build it as part of the work.

## Get the access

List what the raised goal needs: raw data, logs, crash reports, a version-to-commit map, test machines, connectors, or installed software. Get what you can reach. Ask the user for the rest.

## Proceed

Before the work, write one short block:

- **Asked:** the literal request.
- **Raised to:** the raised goal in one sentence, with a measurable target.
- **Method:** the expert methods, tools, and raw sources.
- **Check:** the external check.
- **Rewritten prompt:** the request rewritten to ask for exactly the raised goal, method, and check. Make it self-contained, so that the user can give it to another session or agent.

Then do the work without waiting for approval.

Ask first only when the raised goal needs authorization that the task does not give. Examples are actions outside the workspace, messages to other people, publication, spend, changes to shared systems, and destructive operations. Do the authorized part, then ask about the rest with a recommendation.

## Limits

- Add only the features, files, and reports that the raised goal needs.
- Altitude needs a real final outcome. For creative or routine work, use depth and range, and keep the literal goal.
- If the task is already at the right level, say so in one line and do it.
- Report the result against the raised target. If you did not reach it, state the gap and what would close it.
