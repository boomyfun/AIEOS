# L-0048: Read the constants of an executor against the owner's standing rules before it is released, and assert the forbidden text absent

Rule: Before an executor, a message template or a commit-message constant is released, read every constant that ends up in a commit, a record or a public text and check it against the owner's standing rules (here: no Co-Authored-By trailer since the owner's "có" at transcript 26136a0a :28501); the release command asserts that the forbidden text is absent.

- Status: active
- Category: process
- Binding: record only. Related: L-0044 (read the owner's standing rules before a choice), L-0043, L-0039; decisions D-6473, D-6569, D-6570, D-6571, D-6578.

## Pattern
An executor reused under an owner's rule kept a constant that breaks the rule (CS/session_capture.py :85 hard-codes "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" in TASK_TRAILERS). The rehearsal printed the full messages, and neither the worker nor the decision agent read them for the rule, so two new local commits carried the line.

## Occurrences
- 2026-11-20 (session dc7cf6ca; the worker's own claim until checked): the capture of TASK-137 (D-6569) made the state commit de152471 and the task-branch commit 9377cb5c, both with the trailer; found by the worker in the after-checks' printed messages, before any push; D-6570 and D-6571 replaced both commits by plumbing (same tree, parent, identity and dates, the message minus that one line; D-6571 pinned the script); the decision agent noted its own miss at D-6569 :51 (it read the rehearsal's message text and accepted it). The state commit made later (D-6578) was checked in its dry output and carries no trailer.

## Why it happens
A reused script keeps its old constants; "the executor is approved" is read as "its output is acceptable"; a rehearsal that prints a message is not read as a check against the standing rules.

## Prevention and detection
- Grep an executor's source for the owner's forbidden strings (Co-Authored-By and the like) before it is released; read the whole message that its dry run prints.
- The release command asserts the absence (the commit script asserts "co-authored" is absent from its message constant and from the new object).
- A future executor copy for a later task drops the trailer (D-6570 C4).
