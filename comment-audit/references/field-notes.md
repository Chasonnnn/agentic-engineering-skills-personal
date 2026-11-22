# Field notes

Observations from runs of this skill. Each is dated and scoped to one repository. They explain the guards in `SKILL.md`; they are not thresholds.

## Run 1: November 2026

A Python and TypeScript monorepo, about 10,600 comments (4.9% of lines), most of its history written by agents. The project had a decision log and cited it from comments.

**Rates**

- A random sample was about 3% stale.
- Candidates from a retired-name search were 27% stale (26 of 97 in the frontend).
- The inventory signals with no retired-names file, run on the commit before the audit, flagged 11% of all comments. That set held 46% of the comments the audit later changed (67 of 147, matched by text). A flagged comment was about six times as likely to be one of them (5.6% against 0.85%).
- The misses were comments that cited retired product names and spec sections. In this run, a retired-names search found those.
- Net lines shed: about 200. The gain was correctness, not size.

**What went wrong, and which guard caught it**

| Failure | Caught by |
| --- | --- |
| A fix removed a live rule together with the stale clause next to it, four times. | Review |
| Audit evidence was wrong twice: the verdict cited code that did not say what the auditor reported. | Opening the evidence line |
| An auditor proposed a replacement sentence that was false. | Review |
| An implementer shortened a test string so a file stayed under a size gate. | Review |
| An implementer added a line-length suppression to a docstring it had lengthened. | Review |
| Eleven comments cited documents the first auditors could not read. A read-only pass with the decision records open settled all of them; six were stale. | Second pass |

A docstring edit on an API model changed the generated API schema, and the generated file needed a refresh.

**The proof helper**

- The first draft of `prove` gave the same pass for a Python parse and for the lexer of other languages. A review ran 37 real code or directive changes in nine languages through it, and 35 passed as comment-only. Since then a lexer result is `LEXER-ONLY` (exit 3), tool-read comments are compared with their position, and a docstring change is its own verdict.

**What the stale comments pointed at**

- A comment gave the reason a CI dependency audit did not block. The reason had expired, the gate was still off, and it hid a live advisory.
- A message type, an event name, a duplicate file writer, and three API fields that no code used.
- An error code whose name described the wrong reason.

**Ratchet**

- The linter's unused-suppression rule removed 154 dead suppressions in one pass and was the only cheap automatic check.
