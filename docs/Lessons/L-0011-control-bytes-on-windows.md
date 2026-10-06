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

## Why it happens
- Git Bash heredocs interpret quotes and backslashes.
- Python text mode on Windows writes CRLF.

## Prevention and detection
- Use the Write tool for any multi-line script or text, and run scripts from files.
- In Python, open files with `newline='\n'` or in binary mode.
- Before appending, assert that no `\r` byte is present. After writing, hash the file and compare.
- Consider a `.gitattributes` with `eol=lf` (DEF-0006).
