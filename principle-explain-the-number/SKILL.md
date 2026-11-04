---
name: principle-explain-the-number
description: "Apply before you measure, and before you trust, report, or act on a number you measured: an eval score, a recall or F1, a speedup, a latency, a cost, or a count. Find what limits it, and rule out that it measured something other than the work you think."
disable-model-invocation: true
---

# Explain the Number

- **Write the decision before you run.** Name the result that would change a decision, and the noise floor. Stop when the run-to-run spread is larger than the effect.
- **Ask "why not double?"** Name what bounds the result. For performance, that is a resource or code path, such as a core, a lock, the disk, the network, a rate limit, or the load generator itself. Get it from a profile or from counters taken during a run, then map it to source. A guess from reading the code is not a limiter. If you cannot say why the number is not twice as good, you do not know what you measured.
- **List what else the number could be measuring, and rule out each one with evidence.** The usual suspects are errors, skipped or cached work, code that never ran, an untuned side (one left on default settings), noise, and a piece too small to matter end to end.
- **Keep the evidence with the number.** Put the run count, the spread, and the limiter in the notes or a linked artifact.

## Eval results

For a model, prompt, or annotation result, also state and check:

- **Which setup produced it.** The exact config, model, prompt version, and commit. Confirm it is the promoted or record setup when you compare against the record. A number from a stale setup is the most common wrong number.
- **Which data.** The split, its size, and the gold or codebook version. When the gold changed between two runs, the runs are not comparable until you re-score both.
- **How much it can move.** On a small dev set, give a bootstrap interval or the count behind the rate ("11 of 12", not only "0.92"). Do not promote a checkpoint on a gap smaller than that spread.
- **Whether every item ran.** Count predictions against items. Look for empty outputs, parse failures, timeouts, and refusals scored as negatives.
- **Where the errors are.** Read a sample of false positives and false negatives before you explain the score. A metric shift that the error sample does not show is a scoring or data change, not a model change.
- **Whether it holds.** Check that the gap holds across trials, seeds, or models, and that the scenario matters to the decision.

You skipped this when a run started without the result that would change a decision, when a number has no run count, no spread, or no named setup and data, or when you reported a rate without the count behind it.

Distinct from [Prove It Works](../principle-prove-it-works/SKILL.md), which checks that an output is real.
