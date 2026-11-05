# L-0046: Test every pattern in a script against the real values it must match, and check every line reference in a comment against the file, by a command before the script is sent

Rule: A regular expression, a filter or a glob that gates a script is run against the real values it must accept and refuse (the real listing, printed by the machine) before the script is sent for a decision, and a comment that names a line, a mode or a position is checked against the file by a command.

- Status: active
- Category: accuracy
- Binding: record only. Related: L-0039 (hashes, mode names and options come from their source by machine), L-0043 (gate every run and copy a script before editing it).

## Pattern
A script gated on a pattern written from a reading of the data, not tested against the data, stops at its first assert or lets a wrong value through. A header comment that names a line number goes stale or is wrong at once. Neither is a hash, a mode name or an option (L-0039), and neither is about gating a run behind a hash or copying before an edit (L-0043).

## Occurrences
Session 6550f093 (2026-11-05; ../History/2026-11/2026-11-05-0931-m8-stage-8-task-119-the-lint-step-first-run-red-and-the-stop-6550f093.md; the worker's own claim until checked):
- D-4884 (shared with the decision agent's reading at D-4883): fetch_p13rec.sh filtered the status lines of the repository with the pattern `^\?\? src/aieos_bootstrap/__pycache__/[A-Za-z0-9_.]+\.pyc$`, written from a reading of the status lines; the four real names (`__init__.cpython-314.pyc`, `eventlog...`, `records...`, `writer...`) contain a hyphen and none matched, so the dry run stopped with "E:/AIEOS is not clean (apart from the lock and the bytecode files)" before anything was fetched; D-4862 had listed those names; a corrected copy (fetch_p13rec2.sh, class `[A-Za-z0-9_.-]+`) ran clean (D-4884).
- D-4885 (a comment slip, harmless): the header comment of push_p13rec.sh says that the MODE line is line 3; it is line 4 (the real copy was made by an Edit that anchored on the text, not on the number); recorded, not changed. Other header comments of the session's scripts named a wrong MODE line number the same way (harmless).

## Why it happens
A pattern is written from a look at two or three names, and a comment is written before the last edit of the script; no step runs the pattern against the full listing or the comment against the file.

## Prevention and detection
- Before sending a script, run each gating pattern against the real listing (printed by the command, not retyped) and see that it accepts every name that must pass and refuses the ones that must not.
- A comment that names a line, a mode or a position is checked by grep -n against the file; or the comment names the text, not the number.
- Anchor an edit on the text, not on a line number.
