# L-0047: A script made from another script is compared, in its output, with the committed output of the first

Rule: When a maker or a writer is derived from an earlier one, compare the form of its output (escapes, separators, paths, wording of fixed sentences) with the committed output of the earlier one by a command before the output is brought for reading.

- Status: active
- Category: accuracy
- Binding: record only. Related: L-0046 (test every pattern against the real values), L-0039 (take names from the source by machine), L-0043 (the D-5361 occurrence: a derived writer's copied header).

## Pattern
A derived script inherits the earlier script's text and adds its own edits; an escape or a fixed sentence that was right for one task is wrong or false for the next, and the new output reads as plausible.

## Occurrences
- 2026-11-19 (../History/2026-11/2026-11-19-1806-m8-stage-8-the-records-of-tasks-140-141-and-144-and-the-push-of-their-branch-c0dc5bcc.md, D-6496 correction 1; checkpoint 16 lists it): the line-30 record of TASK-144.jsonl (the limits record) carried the path of a lasting copy with four backslash characters per separator; the committed TASK-141.jsonl line 32 has two. The decision agent found it at the word-for-word reading; the maker was changed by exact replacements (v4) and the real run asserted that no four backslashes in a row remain.

## Why it happens
The worker's own account: the maker chain TASK-139 -> 140 -> 141 -> 144 was edited by replacing task names and numbers; the escapes of one place were written again by hand in the new one.

## Prevention and detection
- After a derived maker's dry run, diff its output against the committed output of the earlier task line by line (the fixed parts must match, the task parts differ).
- Put the form checks of D-6496 C2 (no four backslashes, record counts, the number of the reading decision) into the real run as asserts.
