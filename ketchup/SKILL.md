---
name: ketchup
description: "Catch the user up on what changed since their last message, in plain words, and list every call waiting on them with what they need to decide it from the reply alone. Use for /ketchup, 'catch me up', 'where are we', or a 'what's the status' question about the whole session or run. Not for the status of one named job."
---

# Ketchup

Catch the user up on what changed since the last message they wrote before this request, and help them understand each change, not only where it stands. Then lay out every call waiting on them so they can make it from your reply alone. Notifications, peer-panel messages and subagent results are not their messages. Assume the user remembers their last message and nothing after it. After a compaction, treat the summary as the record of what happened before it.

Use the voice of `bro`: plain words, short sentences, no jargon, like one person catching up another. Follow the writing rules in the global CLAUDE.md. Say what changed for the user, not how you did it. Say "the tests pass", not "CI is green". Leave out hashes, file paths, commands, build numbers, and test counts unless the user needs one to act. Call each PR, branch, job, or agent by a name the user would know, not by a label you invented. Explain each label the first time it appears ("wave 1", "held", "lever stack"), or leave it out. If a fact needs context to make sense, give the context or leave the fact out.

## Gather what changed

Keep this turn read-only: do not change code, start a job, deploy, or post anything. Collect:

- Your own work since that message.
- Delegate results and the orchestrate dispatch ledger, when one exists: what is running, blocked, delivered, or not started.
- Herdr peer panels that touched the same work.
- Background tasks, Monitor watches, and Workflow runs.
- Live state of each PR, CI run, remote job (Empire AI Slurm, AWS), artifact, or study that this session touched. Query it with read-only commands. Do not report a state from memory.

Check each number you will show against the facts it comes from, and say so when you correct one.

An action item is a call or step only the user can take, such as a product or research choice, an approval, an irreversible action, a login, or access you lack. Include any still waiting on the user, even one raised before their last message. Work you can still do yourself is not an action item. Never make up a call to fill the reply. A step the user did not ask for and the work does not need is not an action item, unless it is irreversible and waiting on the user: give it one line.

One call can cover many items, such as each PR in a set awaiting merge. For each item, collect its link, what it changes for users or for the study, the evidence behind your pick, its risk, and your pick. Write "unknown" for a fact the call needs that you do not know. Leave out a link you do not have.

## Write the reply

Spend words on the calls, not on the story. Keep what happened under 100 words, and shorter when less happened. Leave out work that changed nothing for the user. Give each item about 30 words. The reply grows with the number of items. Never cut items or shrink them to stay under a word count: no count in place of a list, and no link in place of an item. A link can add depth, but the reply alone must be enough to decide.

Open with one short sentence that names what waits on the user, or says nothing does. If nothing happened and nothing waits on the user, say so and stop.

Then sum up in one short bullet per thing the user asked for: what came of it, and whether it is done, still running, failed, or not checked. Write each line the way you would say it out loud: "Search was slow from a missing index", not "Search review: done". Name any bug found and fixed on the way. Each line must stay true when read alone. Never mark something done that still waits on the user. Under the summary, give at most three short lines that change what the user knows or must do. Then name in one line any work left that you can do yourself.

Then list the action items as a numbered list, so the user can answer "1. yes 2. no". Ask the call the user owns, such as merge, approve, relabel, or pick, and give your pick. A step you would take first goes in your pick. So does anything that must happen first, and anything that cannot be undone.

Fit the shape to the call. A call about one item is one numbered entry: the call, your pick, what it changes, the evidence, and its risk. When items share a call, write the call and your pick once, then give each item its own sub-bullet, riskiest first. Give each item's risk even when it is low, such as "Low risk: only the colors change." Say what waiting costs only when it is more than a delay, such as a deadline, a live study, or lost data.

For a call between options, give every option the work weighed, each with what it gets the user and what it costs, and the current state when there is one. Those costs are the call's risk, so add no separate risk line.

## Visuals

The terminal shows Markdown only. It does not render Mermaid, images, or charts.

- In the terminal, draw a small ASCII diagram only when a mechanism, a dependency chain, or a before and after is easier to grasp as a picture. Keep it to at most six boxes with at most eight words each. A Markdown table is not a diagram.
- When the user asks for a page, or the brief needs a chart of numbers, publish one private Artifact and use the `dataviz` skill for its charts. Link it under the summary. The reply text alone must still be enough to decide.
- Never draw a status list or a list of action items. Never give a fact twice. Never invent a number, and never draw a screen you did not capture.
