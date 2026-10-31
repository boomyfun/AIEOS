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

Two, in session 87e2584b (2026-10-29):
- **D-3342.** The sed that made exec8p_r.sh was run without a decision naming it; it wrote only to the scratchpad.
- **D-3432.** A diff command run before commit C without its own decision; it only read.

Seven, in session 87e2584b's later part (../History/2026-10/2026-10-29-0446-the-later-part-task-101-the-native-resume-check-in-shadow.md):
- **D-3501.** A Grep for "4300" over the whole bench/go folder, outside the named files; it only read.
- **D-3505.** A sha256sum run without a decision naming it; hash commands since only when a decision names them.
- **D-3527.** Reads of chkx100.py not named by the decision; no rework.
- **D-3549.** A `wc -l` and a Read of the checkpoint before a checkpoint Edit, not named.
- **D-3553.** A Read at a wrong path and a Glob to find copy_3473.sh, needed by D-3552 C4 but not named.
- **D-3554.** Reads to draft the end records (calls 4 to 13 after D-3553), not named by a decision; one Glob listed the whole scratchpad, broader than needed.
- **D-3556.** A Read of place_end.py, a Glob of the five lesson files and two Greps of them, to write the placement script, not named by a decision; they only read.
- **2026-10-30 (session 578ea88b).** I ran read-only commands (greps, lists, hashes, diffs, git status) during steps that a decision approved, which no decision had named one by one; disclosed in the end-records request of D-3903.
- **2026-10-31 (session 85a45f06, D-3968, D-3981, D-3984).** A stray no-op `sed -n 1p /dev/null`, a no-op variable assignment in a grep and a listing piped through sed and tr; read-only, disclosed and accepted as harmless.

## Why it happens
A read is not felt as an act, and right after a compaction the habits of the call form are weakest.

## Prevention and detection
- Before every Bash or PowerShell call, ask: which decision names this exact command? If none, use Read, Grep or Glob, or bring the command first.
- Counts and line totals come from Grep (count mode) or a Read, not from wc.
- Right after a compaction, the first calls are the rereads only (L-0027).
