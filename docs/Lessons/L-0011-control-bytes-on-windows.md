# L-0011: Control bytes when writing files on Windows

Rule: On this Windows machine, write scripts and records with the Write tool or with LF-only binary-mode writes, never through shell heredocs or text-mode writes, and check the bytes (no CR, backslashes intact, expected hash) before appending, committing or hashing.

- Status: active
- Category: technical
- Binding: record only.

## Pattern
Text passes through a shell or a text-mode writer and comes out changed: quotes and backslashes break a heredoc, or CRLF line endings appear.

## Occurrences
At least eight in session 2026-10-04-1817 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md).

Heredocs:
- A 12 KB Python script failed in a Bash heredoc (compaction summary, :1235).
- A generator script failed (:2311).
- Quotes were misparsed (:3782).
- The D-005 log append failed on Windows backslash paths, so nothing was written (2026-10-06, :4937).

Line endings:
- The repository has no `.gitattributes` to fix line endings (:990).
- Rehearsal tests failed after `git restore` left stat-dirty index entries (:2649 to :2670).
- Python text mode wrote the D-003 raw text with 115 carriage returns. The append guard caught it (2026-10-06, :4715).
- Captured command outputs for the CS-3 v2 record had CRLF and were normalised to LF (:5037).

One incident in session 2026-10-06-0306 (../History/2026-10/2026-10-06-0306-real-decider-rechecks-and-push.md):
- **2026-10-06.** A path written inside a non-raw Python string turned `\r` (in `\req`) into a CR byte in a request draft. The CR check caught it before the request was sent, and the byte was fixed with a binary replace.

Two incidents in session 2026-10-06-0602 (../History/2026-10/2026-10-06-0602-rules-book-definition-and-log-split.md):
- **2026-10-06 (D-022 W3).** A CR check put `$'\r'` inside a double-quoted command substitution and printed 30, the number of lines containing the letter r. A Python re-check showed 0 CR bytes; the hash had already matched.
- **2026-10-06 (D-025 request update).** Python heredocs dropped doubled backslashes. In one, the script's own assertion stopped it before any write; the script was then written with the Write tool.

One incident in session 2026-10-07-0358 (../History/2026-10/2026-10-07-0358-a14-step-7-genesis-model.md):
- **2026-10-07 (D-067 request).** Three corrections to a scratchpad request file were applied by a Python script passed through a shell heredoc. The file had 0 CR bytes and the replaced texts had no backslashes; scripts were written with the Write tool from then on.

One incident in session 2026-10-07-0742 (../History/2026-10/2026-10-07-0742-a14-step-7-drafts-and-decision-files.md):
- **2026-10-07 (:274).** A stray empty heredoc in a read-only Bash command started an interactive Python prompt, which hung until the background task was stopped. Nothing was written.

Two incidents in session 2026-10-07-0921 (../History/2026-10/2026-10-07-0921-cr-002-approved.md):
- **2026-10-07 (:243).** A read-only transcript comparison was run as a Python heredoc in a Bash command. It wrote nothing.
- **2026-10-07 (D-085 request).** An empty heredoc hung a Bash command until it was moved to the background and stopped with TaskStop. Nothing was written; the edit was then made with the Edit tool.

One incident in session 2026-10-07-1815 (../History/2026-10/2026-10-07-1815-def-0020-assurance-model-and-constitution.md):
- **2026-10-07 (:184, :185, :200).** An empty heredoc in a read-only Bash command started an interactive Python that looped printing errors; it was moved to the background and stopped with TaskStop. Only the harness's own output files were written, and they were left in place (D-088). From then on no Bash command used `<<` (D-088 C4).

One incident in session 2026-10-07-2144 (../History/2026-10/2026-10-07-2144-def-0020-steps-3-4-and-owner-answers.md):
- **2026-10-07 (:286, :287, :295, :304).** A stray empty heredoc (`python - "$AG" <<'X'`) at the end of a read-only Bash command started an interactive Python; it was moved to the background and stopped with TaskStop. Its harness output file, about 270 MB, was left in place (D-098). The eye check alone had failed for the fourth session in a row, so from then on every Bash command that runs Python starts with `timeout 110`, and no Bash command uses `<<` or `python -` (D-098 C2).

One incident in session 2026-10-08-0010 (../History/2026-10/2026-10-08-0010-a51-approvals-and-draft-genesis-charter.md):
- **2026-10-08 (:1342).** A read-only Bash command piped `grep` output into `python -c` without `timeout 110`; it stopped at once with an encoding error and wrote nothing (D-119). The guard of D-098 C2 stands: every Python run in a Bash command starts with `timeout 110`, and none reads from a pipe without it.

One incident in session 2026-10-08-0211 (../History/2026-10/2026-10-08-0211-ratification-of-genesis-instance-1.md):
- **2026-10-08 (:225).** A read-only Bash command ended with `timeout 110 python - < /dev/null`, a `python -` run that the D-098 C2 guard bans; with an empty program from `/dev/null` it ran nothing and wrote nothing (D-125). The guard stands; the next slip that it does not contain makes a mechanical block a point for the single owner question (D-125 C4).

## Why it happens
- Git Bash heredocs interpret quotes and backslashes.
- Python text mode on Windows writes CRLF.

## Prevention and detection
- Use the Write tool for any multi-line script or text, and run scripts from files.
- In Python, open files with `newline='\n'` or in binary mode.
- Before appending, assert that no `\r` byte is present. After writing, hash the file and compare.
- Consider a `.gitattributes` with `eol=lf` (DEF-0006).
