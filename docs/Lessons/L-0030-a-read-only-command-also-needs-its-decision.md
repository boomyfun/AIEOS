# L-0030: A read-only command also needs its decision

Rule: Bring every command to the decision agent before it runs, a read-only one too (a count, a sed, a test -e, a wc); use the Read, Grep and Glob tools for reads instead, and never run a command only to look.

- Status: active
- Category: process
- Binding: record only. Related: decisions D-2809, D-2843, D-2881, D-2888 (C3: a fourth Bash call without a decision ends the session at the next checkpoint), D-2889; L-0014.

## Pattern
A read seems harmless, and a shell command is the quickest way to make it, so the worker runs it without a decision. The rule covers every command, not only those that write.

## Occurrences
Four, in session 3797498a (2026-10-24 to 2026-10-25):
- **D-2809.** A read-only sed of a contract outside the approved steps.
- **D-2843.** A chained "test -e … && … ||" check.
- **D-2881.** A read-only sed.
- **D-2889 (b).** A wc -l of the checkpoint file right after a compaction; the fourth, so the session ended at that checkpoint under D-2888 C3.

One, in session ea6ea0a3 (2026-10-25, D-3049):
- A Bash command in the `python -c` form, meant to copy a script, was sent without a decision; the guard's rule R2
  refused it before it ran, so nothing was written; it was not resent, and the file was written by the Write tool.

One, in session ea6ea0a3 (2026-10-25, D-3141):
- A command meant to run a script was sent before the script existed and before any decision named it; it exited 2
  and touched nothing; recorded with TASK-094's records.

One, in session ea6ea0a3 (the specification revisions, D-3185):
- mkdraft6 was run without a decision naming it; it wrote only to the scratchpad; recorded with TASK-096's records.

## Why it happens
A read is not felt as an act, and right after a compaction the habits of the call form are weakest.

## Prevention and detection
- Before every Bash or PowerShell call, ask: which decision names this exact command? If none, use Read, Grep or Glob, or bring the command first.
- Counts and line totals come from Grep (count mode) or a Read, not from wc.
- Right after a compaction, the first calls are the rereads only (L-0027).
