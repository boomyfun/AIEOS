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

Session 43f86835 (2026-11-05; ../History/2026-11/2026-11-05-1258-m8-stage-8-task-121-and-task-122-the-pinned-upgrade-of-the-resume-check-43f86835.md; the worker's own claim until checked):
- D-5013: a broad secret pattern with an unanchored `sk-` matched the words "risk-" and "task-" in six lines; the anchored pattern of D-5013 replaced it.
- D-5011: the push script's `grep -P` does not work in the shell's locale.
- D-5012: a request named line 25 for what was line 26.
Each stopped a script before anything was pushed.

Session f348bb86 (2026-11-06; ../History/2026-11/2026-11-06-0904-m8-stage-8-task-124-the-lint-step-built-landed-and-recorded-f348bb86.md; the worker's own claim until checked):
- D-5182 (the decision agent's): a line count of 52 for a script of 50 lines; D-5197 and D-5198: counts of 60 and 86 for scripts of 59 and 85 lines (the Read tool shows one extra empty last line, and the lines are counted with wc -l); D-5190: a message of 8 lines called 9 (found at D-5191). Each stopped or was corrected before anything ran; the counts of lines are read with wc -l.

Session ce14b08a (2026-11-06; ../History/2026-11/2026-11-06-1701-m8-stage-8-the-decision-files-d5198-to-d5236-and-the-coverage-map-ce14b08a.md; the worker's own claim until checked):
- D-5211, D-5213: a gating assert (line 109 of `make_closing_drafts_124.py`) looked for a run id in decision files that did not hold it; written by the worker, approved by the decision agent, and it stopped on the script's first run before any output was written. The id was taken from the checkpoint entries, not tested against the files the assert read.

Session ce14b08a, later part (2026-11-06; ../History/2026-11/2026-11-06-2156-m8-stage-8-the-deferred-items-triage-and-the-plan-revision-8-ce14b08a.md; the evidence lines are decision-file lines and checkpoint lines named in each item; the worker's own claim until checked):
- The MODE line number in a script's header comment or in my request was wrong five times, in five different scripts, a recurrence of D-4885 (line 15 of this file); cp441 (checkpoint line 1621) lists the first two as owed. None ran with a wrong number. The "fixed before pinning" statements of the last three rest on the worker notes of the decision files named, not on a separate check:
  - plan7_apply.sh said line 6, the line is 5 (D-5248:33); left as harmless, no re-pin (D-5248:34).
  - push_plan7.sh and its request said line 5 (and "5c5"), the line is 4 (D-5249:42); pinned and left.
  - commit_triage.sh said line 5, the line is 4 (D-5275:111); fixed before pinning (worker note).
  - fetch_ff_triage.sh said line 6, the line is 5 (D-5276:54); fixed before pinning (worker note).
  - plan8_apply.sh said line 6, the line is 5 (D-5278:64); fixed before pinning (worker note).
- D-5253:16 and :29 (D-5253 C1, D-5254:21): the line-10 comment of the writer copy named lines 13 and 70 as edited, but lines 13 and 70 are identical; a wrong line reference in a comment, corrected before the pin. D-5253 C5 (:61) asked for the occurrence to be recorded; cp441 lists it as owed.
- D-5260:39: a read-only `git log --since=2026-10-30` over three modules used a date filter that left out TASK-102's own commits of that day; it was not tested against the real list of commits; the range `f25b4576..HEAD` replaced it and printed nothing.

## Why it happens
A pattern is written from a look at two or three names, and a comment is written before the last edit of the script; no step runs the pattern against the full listing or the comment against the file.

## Prevention and detection
- Before sending a script, run each gating pattern against the real listing (printed by the command, not retyped) and see that it accepts every name that must pass and refuses the ones that must not.
- A comment that names a line, a mode or a position is checked by grep -n against the file; or the comment names the text, not the number.
- Anchor an edit on the text, not on a line number.
