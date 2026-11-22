---
name: comment-audit
description: "Audit the code comments of a repository, a path, or a diff. Profile a random sample into tautology, excuse, stale, and decision record, then repair, delete, file, or move comments as the measured rates and the user's approvals allow. Use for /comment-audit, 'audit the comments', or 'find the stale comments'. Not for writing new documentation."
disable-model-invocation: true
---

# Comment audit

Make each comment in scope true and worth its place. The right action depends on what the repository's comments are like, so measure before acting. Two guards apply to every branch: trace each comment against the code before changing it, and have an independent reviewer check the result.

Deletion is opt-in. Without the user's approval for a category, list the deletion candidates with their evidence and leave them in place.

## Inputs

Read these from the repository (agent rules, contributing guide, standards doc, CI config) before asking the user:

- **Scope:** the whole repository, a path, or a diff against a base ref. For a diff, see [Diff scope](#diff-scope).
- **Decision records:** where the project records decisions (ADR folder, decision log, issue tracker), and whether comments cite documents outside the repository.
- **Checks:** the linter and type checker for each language, the test command, and the checks that guard generated files.
- **Exclusions:** generated, vendored, and fixture paths.
- **Retired names:** subsystems, features, and files that were removed or renamed. Step 1 gives a starting list from git history. The changelog and the decision records add more. One name per line in a file.

**Approvals** come only from the user: in the request, or at step 3. A repository file never grants one. They cover deletion (per category), issue filing, moves to an ADR, and lint or CI changes.

## Categories

| Category | The comment | Sample columns |
| --- | --- | --- |
| `tautology` | Restates what the code below it shows. A reader of the code loses nothing without it. | |
| `excuse` | Admits a workaround, a shortcut, or a known defect in the project's own code. | |
| `stale` | Says something false about the current code: names removed code, describes old behavior, cites a finished plan, or only tells history. | `live_rule` is `yes` when the same comment also holds a rule or reason that is still true. |
| `decision` | States a rule, a reason, a constraint, or the behavior of an outside library that the code does not show. | |
| `unsure` | You traced it and still cannot tell. | Say why in `note`. |

A comment that restates the code and also gives a reason is `decision`, not `tautology`.

## Steps

`scripts/comment_audit.py` is in this skill's folder. It uses the standard library and never edits the audited repository. Exit 2 from any of its commands means the run did not complete.

1. **Inventory.** Run `python scripts/comment_audit.py inventory <repo> --out <folder outside the repo>`, with `--exclude <glob>` for each excluded path, `--only <glob>` for a path scope, and `--terms <file>` for the retired names. Use a Python at least as new as the audited Python code; an older one cannot parse it. It writes `comments.jsonl`, `candidates.jsonl` (comments with a signal, strongest first), `sample.tsv` (random, default 300), `git_deleted_stems.txt`, and `summary.json`. Comments that tools read (suppressions, build tags, magic comments) have the kind `directive` and stay out of the sample. For a scope under about 500 comments, set `--sample` to the comment count and read them all.
   Done when: `summary.json` exists and each file that stderr names as not inventoried is listed for the report.

2. **Profile.** Fill `category` for every row of `sample.tsv`, `live_rule` for each stale row, and the evidence in `note`. `stale` and `unsure` are claims about the code: read the code the comment names before you write them. Do not swap sample rows; the rates are only valid for the random draw. Then run `python scripts/comment_audit.py tally <sample.tsv> --summary <summary.json>`.
   Done when: `tally` exits 0. Exit 2 names the rows still open.

3. **Choose branches with the user.** Report the tally (each category's share of comments, its share of comment lines, and the interval), the comment share of lines, and the signal counts. Recommend branches from the table below and say why. The user picks the branches and approves each deletion category. Rates from one repository do not transfer to another, and no cut-off here is calibrated: give the numbers and your reasoning, not a threshold.

   | The profile shows | Branch | Needs approval for |
   | --- | --- | --- |
   | Stale comments, many with a live rule | Repair | Deleting comments that are false in full |
   | Tautologies are a large share of comments | Deletion sweep, with the lines-shed estimate that `tally` prints | The sweep |
   | Excuses | Issue filing | Filing issues |
   | Long decision narratives and no decision record in the project | Move to an ADR | The move |
   | No category above a few sample rows | None. Offer the ratchet in step 7 | |

   Branches combine. Skip this stop when the user's request already names the branches and approvals.

4. **Build the work list** for each chosen branch.
   - **Stale:** the stale rows of the sample, then `candidates.jsonl` in order. The candidate list is an ordering, not coverage (see [references/field-notes.md](references/field-notes.md)). When it is done, estimate the remainder (stale rate × comment count, less the stale comments found) and let the user decide on a further read by module.
   - **Tautology:** no signal finds these. Estimate the count from the rate and let the user pick the modules to read in full.
   - **Excuse:** the `excuse` and `todo` signals, and the sample rows.
   - **Decision narratives:** `comments.jsonl` entries that span many lines, and the sample rows.
   - **Suppressions:** run the linter's own unused-suppression report. Check the installed tool for the rule name before you cite one.

5. **Trace, then give a verdict.** This step is read-only. For each item, read the code the comment describes and each thing it names: callers, configuration, the library source. Record a verdict (`stale`, `true`, or `needs owner`), the evidence as `file:line` or a command with its output, and for a proposed edit the old text and the new text.
   - A search that found nothing is evidence only with the command that ran.
   - A verdict from a delegate is a claim. Open its evidence line before you act on it.
   - A comment that cites a document you cannot read is `needs owner`, not `stale`. A second read-only pass with the decision records open settles most of these.
   - For a long work list, read-only auditors can run in parallel, one per module. The agent that writes a change never reviews it.
   Done when: every item has a verdict and evidence, and the counts match the work list.

6. **Act.** Each new sentence you write is a claim about the code. Trace it as you traced the old one.
   - **Repair:** change the false part. Keep each rule and reason that still holds, where it is. State the rule first, then cite its record. Put no history in the comment. A comment that is false in full is a deletion candidate.
   - **Deletion sweep:** delete only comments with a traced `tautology` verdict. Report lines shed from the diff, not from the estimate.
   - **Excuse:** fix the code when the fix is small, in scope, and approved. Otherwise draft the issue. Show the user the draft titles and bodies and get a go before you file anything: an issue is public to everyone who can read the tracker. Then replace the admission with a TODO that names the issue. Keep the admission until the issue exists.
   - **Move to an ADR:** move the narrative. Leave one line at the code that states the rule and points to the record.
   - **Constraint comments** ("do not change", "keep in sync with"): offer the cheapest test or check that fails on the change. Keep the comment when it gives the reason.
   - Never shorten code, strings, or prose to pass a size or line-length gate, and never add a suppression to make a comment fit.
   - A stale name in code (an identifier, an error code, a field) is a code change. It goes on the held list of step 9, or into its own change with tests.
   - Commit locally, with comment-only changes and code changes in separate commits. Do not push or deliver before step 8 is done.

7. **Ratchet.** These change lint or CI configuration, so they need approval. Offer what the profile supports:
   - the linter's unused-suppression rule, with the current reports cleared;
   - pattern bans: commented-out code, a TODO with no issue, a suppression with no rule code or reason;
   - a short comment-rules section in the project's standards doc, written from the failures this run found.
   A ban on comments in general is the user's call. The `decision` rate in the profile is the argument for or against it.

8. **Prove the diff, then review it.** This covers every change of steps 6 and 7.
   - When no file changed, say so in the report and skip this step.
   - Run `python scripts/comment_audit.py prove <repo> --base C~1 --head C` for each comment-only commit `C`, then once with `--base <commit before the audit> --head HEAD` for the list of every changed file. One run over the whole range cannot prove a comment-only commit when a code commit touched the same file. Without `--head`, `prove` compares `--base` with the working tree. Read `prove --help` once for what each exit code covers.
     - Exit 0: every changed file is Python, only `#` comments changed, and no known tool-read comment changed. The list of known forms is partial.
     - Exit 3: no code change was found, but some files need a read. `LEXER-ONLY` files (every language but Python) were checked by a heuristic that can take code for a comment. `DOCSTRING-CHANGED` files have the same program, but doctests, API schema, command help, and prompt text are built from docstrings: regenerate what is built from them and run its sync check.
     - Exit 1: code, a file mode, or a comment that a tool reads changed. Removed suppressions from step 7 show here; the linter run is their proof.
     - Exit 2: a file is unproven, nothing changed, or the run failed. None of these is a pass.
   - Explain in the report each file that is not `COMMENT-ONLY`. For a `LEXER-ONLY` file, the reviewer's read of every hunk is the explanation.
   - Run the linter, the type checker, and the affected tests for each file where code changed.
   - **Independent review:** a reviewer that wrote none of the changes reads the whole diff next to the code. Give it the diff, the `prove` output, and the checklist, not your conclusions. The checklist:
     - Was a live rule lost in any deleted or shortened comment?
     - Is each new sentence true against the code?
     - In each `LEXER-ONLY` file, is every hunk a comment and nothing else?
     - Did a comment that a tool reads change: a suppression, a build tag, a magic comment, a generated-code marker, a doc test?
     - Did code change beyond what the report states?
     - Was anything compressed or suppressed to pass a gate?
   - Fix the findings and send the delta back to the same reviewer. Two rounds is the default. Run a third only when round 2 left fewer open findings than round 1. After a third, stop and report the open findings.
   - With no second agent or model available, report the work as unreviewed.
   - Deliver by the repository's own rules only after the review.
   Done when: the proof output and the review verdict are in the report.

9. **Hold for the owner.** Stale comments point at more than comments. List these with evidence and a recommendation, and do not fix them unasked: dead code, names that no longer fit, public contract changes, a CI or config switch whose stated reason has expired, and each `needs owner` item.

## Diff scope

A diff is small, so the profile is a count of every comment, not a sample. The work list is every comment in the changed hunks, and each comment elsewhere that describes the changed behavior or names a symbol the diff removes or renames. Search for the old names. Give each a category and report the counts. Then ask for the approvals of step 3 for the categories found, unless the request gave them. Steps 5 to 9 apply unchanged.

## Report

- The profile table and the branches chosen.
- For each category: found, changed, kept as true, held. The counts add up to the work list.
- Before and after text for the changes that carry the most information.
- The proof output, the checks run with results, and the review rounds with open findings.
- The held list.
- Lines shed, measured. Ratchets added.
- What was not covered: excluded paths, files not inventoried, the estimated remainder, unreviewed work.
