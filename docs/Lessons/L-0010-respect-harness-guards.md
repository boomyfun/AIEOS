# L-0010: Respect guards and security settings

Rule: When a classifier, a permission rule or an OS protection blocks an action, stop: do not retry it unchanged, reword it, split it or route it through another tool or agent, never change security settings yourself, and hand the action or the setting change to the owner.

- Status: active
- Category: governance
- Binding: record only. Related: group B, item 2 of the decision agent's lists keeps security settings and Claude Code settings with the owner.

## Pattern
A guard blocks something the owner has approved, and the approval in chat feels like permission to try again.

## Occurrences
Four blocks in session 2026-10-04-1817 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md), with one mistake:
- **2026-10-05 (:729, :866).** A safety classifier stopped credential-probe content twice. Claude kept the content high-level afterwards. Correct.
- **2026-10-05 (:1796 to :1815).** An OS protection blocked writes to one folder. Claude used another folder and changed no setting. Correct.
- **2026-10-05 (:3932, :3940, :3950).** The Claude Code auto-mode classifier blocked the approved force-push. After the owner wrote "cho phép" in chat (:3936), Claude retried the identical command and was blocked again. This was the mistake: words in chat do not change settings.
- **2026-10-05 (:3961, :3969).** The owner asked Claude to change the settings ("vậy hãy sửa cài đặt đi"). Claude declined and explained how the owner could do it. Correct. The owner added a one-off allow rule and later removed it (:4443).

Blocks in session 2026-10-06-0306 (../History/2026-10/2026-10-06-0306-real-decider-rechecks-and-push.md), handled by stopping:
- **2026-10-06 (:552).** The auto-mode classifier blocked an approved normal push ("[Out-of-Place Publication]"). Claude stopped and gave the owner options. It did not retry until the owner had added a one-command allow rule and told it to run the command (:906, :980).
- **2026-10-06 (:946, :1069).** Two worker commands were denied as "[Auto-Mode Bypass]", and the same warning was attached to a decision-agent handback. Claude stopped each time and told the owner about the first (:1000). The save denied at :946 was redone at :1036, after the owner chose option (a), which included logging those decisions (:1021). The re-read denied at :1069 was not redone.

Two refusals in session 2026-10-09-0024 (../History/2026-10/2026-10-09-0024-ci-revision-and-task-branches.md), handled by rewriting the command in the allowed form:
- **2026-10-09 (:295, :832).** The installed guard (DM A57) refused two commands that held Python's name followed by a space and a dash, one an inline program and one a version query. Both were Claude's malformed commands, not correct commands refused; neither ran. Each was rewritten as a script file run in the allowed form, and both were disclosed to the decision agent (D-180, D-182).

Three refusals in session 2026-10-09-0514 (../History/2026-10/2026-10-09-0514-fixture-file-kind-and-fixture-drafts.md), none retried in the refused form:
- **2026-10-09 (:251, :416).** The owner's command guard refused a one-line program given to Python on the command line without `timeout 110`, and a `grep` pattern that held `<<`; both were read-only and were rewritten in the form the guard's message gives.
- **2026-10-09 (:1189).** The harness's safety check refused a command that began with `rm -rf` on a relative path; nothing ran, and the folder did not exist. No removal command was used for the rest of the session (D-201 C4).

Two refusals in session 2026-10-09-0637 (../History/2026-10/2026-10-09-0637-fixtures-accepted-and-landed.md), none retried in the refused form:
- **2026-10-09 (:164, :792).** The owner's command guard refused a one-line program given to the Python launcher on the command line, and a needless `timeout 110 python -c ""` (Python's name followed by a dash); both were read-only, and each was rewritten in the form the guard's message gives.

One refusal in session 2026-10-09-0856 (../History/2026-10/2026-10-09-0856-runner-contract-and-drafts.md), not retried in any form:
- **2026-10-09 (:332).** The owner's command guard refused a read-only search whose command held Python's name followed by a dash as a search string; the read was redone without that search.

One refusal in session 2026-10-09-1056 (../History/2026-10/2026-10-09-1056-runner-accepted-and-landed.md), not retried in that form:
- **2026-10-09 (:568).** The owner's command guard refused a command that took a value with a here-string (`<<<`); it was rewritten without that form, as the guard's message says.

One refusal in session 2026-10-09-1801 (../History/2026-10/2026-10-09-1801-governor-drafts-and-runner-test-isolation.md), not retried in that form:
- **2026-10-09 (:253).** The owner's command guard refused a read-only scan whose search pattern held the two "less than" signs of a here-string; it was rewritten as a script whose patterns are built from character codes, as the guard's message says (D-223 Q4).

Two occurrences in session 2026-10-09-1918 (../History/2026-10/2026-10-09-1918-governor-accepted-and-landed.md):
- **2026-10-09 (:976).** A filler command (a script called with "--help", output discarded) ran; it wrote nothing. Disclosed in the next request.
- **2026-10-09 (:1843).** A removal command word ran: `rmdir` on a scratchpad folder that did not exist, after a `cd` inside a brace group had changed the working folder unnoticed; nothing was removed. Disclosed in the next request.

Four occurrences in session 2026-10-09-2141 (../History/2026-10/2026-10-09-2141-governor-pinned-genesis-v3-m2-exit.md):
- **2026-10-09 (:268).** A filler fragment ran: a shell function defined and never called; it wrote nothing. Disclosed in the next request.
- **2026-10-09 (:727).** A filler fragment ran: a loop whose body does nothing; it wrote nothing. Disclosed in the next request.
- **2026-10-09 (:866).** A filler fragment ran: a search whose output was discarded; it wrote nothing. Disclosed in the next request.
- **2026-10-09 (:934).** The command guard refused a correct, read-only search (its quoted pattern held a pipe character and the interpreter's name); the pattern was rewritten and run at :939 instead of stopping. The decision agent accepted it once and ruled that a refused correct command is brought to it, with no rewrite and no retry (D-237 Q4).

One occurrence in session 2026-10-09-2339 (../History/2026-10/2026-10-09-2339-spec-3-approved-and-on-main.md):
- **2026-10-09 (:471).** The command guard refused a transcript line piped into Python's name followed by a dash, without `timeout 110`; the command broke the rule, so the program was written to a file and run in the allowed form (:477, :479), as the guard asks for an incorrect command (D-243, D-244 C5).

Occurrences in session 2026-10-10-0138 (../History/2026-10/2026-10-10-0138-conformance-files-r4-and-task-005-contract.md), each my incorrect command, refused before it ran and rewritten as the rule requires:
- **2026-10-10 (:148).** A heredoc to create an empty helper file.
- **2026-10-10 (:324).** Two less-than signs inside a search pattern.
- **2026-10-10 (:1300).** Python's name followed by a dash, to run one test module.

One occurrence in session 2026-10-10-0235 (../History/2026-10/2026-10-10-0235-resume-check-fixtures-accepted.md), my incorrect command, refused before it ran and rewritten as the rule requires:
- **2026-10-10 (:1341).** A filler fragment with Python's name followed by a dash, left in a command meant only to copy a file.

One occurrence in session 2026-10-10-0348 (../History/2026-10/2026-10-10-0348-runner-entry-contract-and-reader-test-split.md), my incorrect command, refused before it ran and rewritten as the rule requires:
- **2026-10-10 (:367).** Python's name followed by a dash, with no timeout, to parse a script.

Seven commands with no effect in session 2026-10-10-0451 (../History/2026-10/2026-10-10-0451-decision-files-d284-d292-and-task-010-landed.md), all mine, found by `tools/filler_count2.py`; five were refused by the guard before they ran:
- **2026-10-10 (:199, :301, :671, :1475).** A heredoc with Python's name and a dash; a pipe into Python's name with a dash; `python -c print(1)`; `python3 --version`.
- **2026-10-10 (:916).** A real check whose search pattern held the forbidden strings; the guard reads a search pattern as a command.
- **2026-10-10 (:541, :984).** `cat > /dev/null` and `sed -n 109p /dev/null` ran and did nothing.

Five commands of mine of the kinds this lesson lists, in session 2026-10-10-0626 (../History/2026-10/2026-10-10-0626-decision-files-d293-d302-and-task-006-landed.md), found by `tools/filler_count3.py`, which now also counts removal commands, heredocs and greps of /dev/null:
- **2026-10-10 (:118, :706).** Python's name with a dash, and a heredoc appending a placeholder line; both refused by the guard before they ran.
- **2026-10-10 (:555).** A removal command (`rm -rf` on a folder that did not exist); it removed nothing, but such a command must not be run at all.
- **2026-10-10 (:320, :1275).** A grep of /dev/null inside a longer command; it ran and did nothing.

Commands of mine of the kinds this lesson lists, in session 2026-10-10-0735 (../History/2026-10/2026-10-10-0735-decision-files-d303-d310-ci-revision-5-and-task-007-contract.md):
- **2026-10-10 (:531).** Python's name with a dash; refused by the guard before it ran.
- **2026-10-10 (:882).** Python's name followed by a file name that does not exist, typed by mistake inside a longer command; it ran and did nothing.
- **2026-10-10 (:999).** A sed edit whose pattern matched nothing; the file stayed unchanged.
- **2026-10-10 (:1134, :1346).** A one-second sleep before a read (a filler), and a one-minute sleep while CI ran, which the harness refused before it ran; it was not retried.
- **2026-10-10 (:1635, :1662).** While rebuilding the session-end records: a sed edit that replaced a line with itself, and a stray call of an earlier reply-composing script inside a longer command (its exclusive write refused, its output discarded); both ran and did nothing.

Commands of mine of the kinds this lesson lists, in session 2026-10-10-1612 (../History/2026-10/2026-10-10-1612-decision-files-d311-d318-the-widening-in-force-and-task-007-landed.md):
- **2026-10-10 (:105).** `ls tools/` run in the repository, where no such folder exists; it failed and the chained commands did not run.
- **2026-10-10 (:276).** Python's name with a dash inside a pipeline; refused by the guard before it ran; not retried in that form.
- **2026-10-10 (:346).** A `git diff --no-index` without GIT_OPTIONAL_LOCKS=0, outside any repository.
- **2026-10-10 (:1084, :1315, :1377, :1506, :1576).** Waits for a handback that paused with `timeout N tail -f <file>`, the first on /dev/null: bounded waits on a condition, but the pause itself is a filler form.
- **2026-10-10 (:1429, :1601).** A helper script called with no arguments inside a longer command; it failed and did nothing.

Commands of mine of the kinds this lesson lists, in session 2026-10-10-1810 (../History/2026-10/2026-10-10-1810-decision-files-d319-d330-contracts-of-task-011-008-012.md):
- **2026-10-10 (:354).** A heredoc to write a scratch file; refused by the guard before it ran; rewritten with the Write tool.
- **2026-10-10 (:404).** A helper script called with no arguments inside a longer command; it failed and did nothing.
- **2026-10-10 (:559).** A filler command with Python's name followed by a dash, inside a pipeline; refused by the guard; not retried in that form.
- **2026-10-10 (:668, :1038).** Python's name inside a grep pattern (with a dash, then alone); both refused by the guard; rewritten without it, the second with the Grep tool.
- **2026-10-10 (:954).** A sed with a bad expression; it failed with no effect.
- **2026-10-10 (later).** A sed edit of a checker script that mangled one line (repaired with the Edit tool before use), and the previous task's brief checker run on this session's briefs, which crashed with no effect.

Commands of mine of the kinds this lesson lists, in session 2026-10-10-1946 (../History/2026-10/2026-10-10-1946-decision-files-d331-d344-task-011-landed.md):
- **2026-10-10 (:294, :1058, :1361).** Filler or no-effect fragments at the head of real commands (`cat > /dev/null < /dev/null`; `git diff --no-index --stat /dev/null /dev/null`; `echo skip > /dev/null`); no effect.
- **2026-10-10 (:1373).** A filler with Python's name followed by a dash; refused by the guard.
- **2026-10-10 (later).** A sed expression holding Python's name; refused by the guard and rewritten without it.
- **2026-10-10 (:942).** An approved one-run push command typed again as a fragment at the head of a hashing command; the executor refused at its first check and changed nothing, but its log was overwritten and recovered from the transcript (decision D-349). Remedy (D-349 C5, D-352 C6): compose each command in full and read it once as written before sending it; never start a command from a fragment; never type a one-run command's path again after its run.

Commands of mine of the kinds this lesson lists, in session 2026-10-10-2044 (../History/2026-10/2026-10-10-2044-decision-files-d345-d355-task-008-landed.md):
- **2026-10-10 (:390).** A draft command holding a no-effect `echo skip` and Python's name followed by a dash; refused by the guard and rewritten as a script, not reworded around it.
- **2026-10-10 (:607).** Four Python runs with fixed arguments in one free-typed compound command, against the remedy of decision D-357 (such a set is first written as a script in the scratchpad, read once, then run).
- **2026-10-10 (later).** A probe run with `timeout 60`, refused by the guard (the rule is `timeout 110`); rerun in the rule's form.

Commands of mine of the kinds this lesson lists, in session 2026-10-10-2141 (../History/2026-10/2026-10-10-2141-decision-files-d356-d366-task-013-landed.md):
- **2026-10-10 (:~150).** A free-typed compound command with an unset variable, so a grep read standard input and hung until it was stopped.
- **2026-10-10 (:971).** A needless line holding Python's name followed by a dash inside a compound command; refused by the guard; the rest ran without that line.
- **2026-10-10 (later).** The mutation probe's copy, edit and two Python runs as one free-typed command, against the remedy of decision D-357.

Commands of mine of the kinds this lesson lists, in session 2026-10-10-2252 (../History/2026-10/2026-10-10-2252-decision-files-d367-d376-task-014-landed.md):
- **2026-10-10 (:322).** A read with Python's name followed by a dash and no timeout; refused by the guard; done with a helper script under `timeout 110` instead.
- **2026-10-10 (later).** A command with a heredoc and a no-effect `echo`; refused by the guard; the text was written with the Write tool.
- **2026-10-10.** A helper script run without its arguments; a failed script chained with the next Python run in one command (against D-357 Q4); a browser wait of ten seconds while a CI run was in progress (:1479). No effect.

Occurrences in session 2026-10-11-0013 (../History/2026-10/2026-10-11-0013-decision-files-d377-d387-recovery-and-the-pin.md), each my incorrect command, refused before it ran and rewritten within the approved step (D-390 Q5):
- **2026-10-11 (:628).** A here-string to compare hashes.
- **2026-10-11 (:991).** Python's name followed by a dash, to run one test module.
- **2026-10-11 (:1246).** The same form inside a search pattern.

Occurrence in session 2026-10-11-0121 (../History/2026-10/2026-10-11-0121-decision-files-d388-d398-and-task-015.md), my incorrect command, refused before it ran and rewritten within the approved step (D-390 Q5):
- **2026-10-11 (:850).** Python's name followed by a dash, without the timeout, to print the last session's browser inputs; rewritten as a script file run with the timeout.
- **2026-10-11 (:1469).** The same form again, in a command with no purpose (a filler command); refused before it ran and not rewritten.

Occurrences in session 2026-10-11-0220 (../History/2026-10/2026-10-11-0220-decision-files-d399-d408-the-writer-and-m3-exit.md), each my incorrect command, refused before it ran and rewritten within the approved step (D-390 Q5):
- **2026-10-11 (:243).** Python's name followed by a dash, in a leftover loop with no purpose (a filler).
- **2026-10-11 (:365).** The same form, to test whether a YAML loader is installed; rewritten as a script file.
- **2026-10-11 (:1305).** The same form inside a search pattern; rewritten without it.

Occurrences in session 2026-10-11-0333 (../History/2026-10/2026-10-11-0333-decision-files-d409-d420-and-specification-4.md), recorded in the next session (decision D-435 C3), each my incorrect command, refused before it ran:
- **2026-10-11 (:319).** A leftover filler at the start of a command, Python's name followed by a dash; the edit was made with the edit tool.
- **2026-10-11 (:1747).** A no-op command of the same form; nothing ran. Remedy: no command that the step does not need.

Occurrences in session 2026-10-11-0538 (../History/2026-10/2026-10-11-0538-conformance-files-revision-7-and-task-017-contract.md), each my incorrect command, refused before it ran (decisions D-437 Q3 and D-448 Q4):
- **2026-10-11 (:359).** A check I added at the end of a command named the forbidden form in its own search pattern; dropped, the rest re-run unchanged. Remedy: no check whose pattern names that form; the guard itself is the check.
- **2026-10-11 (:1545).** A run of one test module in the module-run form; the whole suite was run through tests/run_tests.py instead. Remedy: tests only through tests/run_tests.py.

Occurrences in session 2026-10-11-1318 (../History/2026-10/2026-10-11-1318-runner-entry-accepted-and-fixture-contract-drafted.md), each my incorrect command, refused before it ran (decisions D-453, D-461 and D-462):
- **2026-10-11 (:368).** A here-string in a `sha256sum -c` command; re-run with `echo … | sha256sum -c -`.
- **2026-10-11 (:452).** A purposeless placeholder command with Python's name followed by a dash.
- **2026-10-11 (:1462).** A leftover of the same form at the start of a real command, after D-453's remedy (no command without a purpose); the remedy did not hold. Remedy now: grep each command's text for those forms before sending it.

Occurrence in session 2026-10-11-1439 (../History/2026-10/2026-10-11-1439-fixture-contract-on-main-and-fixture-reviewed.md), my incorrect command, refused before it ran (decision D-466):
- **2026-10-11 (:356).** A grep meant to check a new command file for Python's name followed by a dash held that form in its own pattern; the remedy of session 51321169 ("grep each command for those forms") put the form into the command. Remedy now: that check is done by reading, never by a pattern in a command.

Occurrences in session 2026-10-11-1540 (../History/2026-10/2026-10-11-1540-fixture-accepted-and-runner-tests-pushed.md), each my incorrect command (decisions D-476, D-484):
- **2026-10-11 (:330).** A stray Python-with-a-dash prefix in front of a sed edit; refused before it ran.
- **2026-10-11 (:425).** A check whose own pattern held the forbidden forms (the occurrence of :356 of session 2026-10-11-1439 again); refused before it ran.
- **2026-10-11 (:1585).** A command that began with `rm -rf` on a scratch folder that did not exist; it was not refused, nothing was removed, and the rules forbid any removal command. Remedy (D-484 C4): no removal command at all; a new scratch folder gets a new name.

Occurrences in session 2026-10-11-1800 (../History/2026-10/2026-10-11-1800-runner-tests-accepted-and-set-freeze-for-task-020.md), my incorrect command (decision D-489):
- **2026-10-11 (:442).** A check of my own builder whose grep pattern held the forbidden forms as search strings (the occurrences of :356 of session 2026-10-11-1439 and :425 of session 2026-10-11-1540 again); refused before it ran; not retried unchanged.

Occurrences in session 2026-10-11-1912 (../History/2026-10/2026-10-11-1912-set-entry-accepted-and-on-main-for-task-020.md), each my incorrect command (decisions D-501, D-504):
- **2026-10-11 (:252).** A search whose grep pattern held a Python run form as a search string; refused before it ran; corrected, not retried unchanged.
- **2026-10-11 (:743).** A one-line program piped into Python by its name followed by a dash, without the timeout prefix; refused before it ran; the data was read with grep instead.

Occurrences in session 2026-10-11-2017 (../History/2026-10/2026-10-11-2017-ac-coverage-check-accepted-and-on-main.md), each my incorrect command (decisions D-514, D-518):
- **2026-10-11 (:281).** A one-line program run by Python's name followed by a dash, to print a transcript record; refused before it ran; a small script file was written and run instead.
- **2026-10-11 (:764).** A polling loop for the decision agent's answer that ran Python under a short timeout and waited by reading with a time limit, close to a sleep; refused before it ran; not retried; the answer was checked once instead.

Occurrences in session 2026-10-11-2233 (../History/2026-10/2026-10-11-2233-stale-evidence-computation-accepted-and-on-main.md), each my incorrect command (decisions D-548, D-554):
- **2026-10-11 (:916).** A compile and test command holding Python's name followed by a dash twice; refused before it ran; the compile script of an earlier session was used instead.
- **2026-10-11 (:1892).** A hashing command with a stray no-op tail holding Python's name followed by a dash; refused before it ran; rerun without the tail.

Occurrences in session 2026-10-12-0048 (../History/2026-10/2026-10-12-0048-the-git-reader-accepted-and-on-main.md), the refusals each my incorrect command (decisions D-575, D-577, D-581, D-586):
- **2026-10-12 (:168, :495, :1197, :1922).** Four commands holding Python's name followed by a dash (a no-op, the module flag, the version flag, a no-op tail); refused before they ran; not retried; a runner script was written for the second.
- **2026-10-12 (:676, :677).** The harness's safety classifier withheld one of my responses while I prepared to send TASK-024's code to the decision agent; nothing in it ran; I did not retry, reword or reconstruct it, and asked the owner in one plain question (:679); the owner answered "(a) Làm tiếp" (:683), and the decision agent ruled how to go on (decision D-577).

Occurrences in session 2026-10-12-0215 (../History/2026-10/2026-10-12-0215-the-submission-path-accepted-and-on-main.md), the refusals each my incorrect command (decision D-591):
- **2026-10-12 (:521, :526).** Two commands holding Python's name followed by a dash (a filler piece, then the same form inside a search pattern meant to find the first); refused before they ran; not retried in that form.
- **2026-10-12 (:669, :1120, :1877).** The harness's safety classifier withheld one of my responses three times; nothing in them ran; I did not retry, reword or reconstruct them, and each time asked the owner in one plain question; the owner answered "(a) Làm tiếp" twice (:675, :1130) and "(a) Kết thúc phiên đúng các bước" the third time (:1886), and the decision agent ruled how to go on (decisions D-592, D-596 and D-602).

Occurrences in session 2026-10-12-0333 (../History/2026-10/2026-10-12-0333-release-by-token-accepted-and-the-recovery-contract.md), the refusals each my incorrect command:
- **2026-10-12 (:256, :516).** A command holding a heredoc (writing a helper script; guard rule R1), and a command holding Python's name followed by a dash (an import probe added to a hashing command; guard rule R2); refused before they ran; not retried in that form (decisions D-604 and D-607).

Occurrences in session 2026-10-12-0833 (../History/2026-10/2026-10-12-0833-recovery-at-start-accepted-and-on-main.md), the refusals each my incorrect command:
- **2026-10-12 (:512, :664).** A command holding Python's name followed by a dash (to run one test file), and the same form inside a grep search string looking for that line; both refused by guard rule R2 before they ran; not retried in that form (decisions D-622 and D-625).
- **2026-10-12 (:1244).** A sleep command (`sleep 1;` before a CI listing), against the standing rule; not refused by the guard, and not flagged by the filler check filler_count3.py, a gap of that tool (decision D-625).
- **2026-10-12 (:1867).** A command written by mistake, holding a heredoc and a command with no effect (`echo skip`); refused by guard rule R1 before it ran; not retried (decision D-629).

Occurrences in session 2026-10-12-0944 (../History/2026-10/2026-10-12-0944-the-evaluation-path-accepted-and-on-main.md), each my incorrect command:
- **2026-10-12 (:158, :759, :1071).** A Python run with timeout 100 (refused by guard rule R3, re-issued with timeout 110), and two commands holding Python's name followed by a dash, one a placeholder of no effect and one at the head of a CI read (both refused by R2; not retried in that form) (decisions D-632, D-636 and D-638).
- **2026-10-12 (:309, :638, :1113).** A guard-forbidden string inside a grep pattern, an `rm` of a scratch file the same call had made (not stopped by the guard; against the standing rule), and a no-effect grep inside a broken loop; the first and the last flagged by filler_count3.py, which matches text rather than commands run (decisions D-632, D-635 and D-638).

## Why it happens
- An approval in chat is confused with a change in the harness.
- Retrying is cheap.

## Prevention and detection
- After a block, report it exactly and give two options: the owner runs the command, or the owner changes a setting.
- Retry only after the owner confirms that a setting changed.
- Never present a guess about why a guard fired as fact (L-0008).
