# L-0039: Take every hash, mode name and option of a command from its source by machine, and check it against the file before the command is approved

Rule: Never retype a hash, a mode name or an option into a command or a request; copy it from the tool's own output (sha256sum's printed line, the script's allowed list), compare it with the file by a command before the request is sent, and when a decision's command carries a form the owner's guard forbids (python -I) or a name the script does not accept (dry4), say so in the request instead of running it as written.

- Status: active
- Category: accuracy
- Binding: record only. Related: L-0011 (control bytes and forms on Windows), L-0014 (a changed command comes back as a request), L-0030.

## Pattern
A decision's condition quoted a SHA-256 with one character missing, and the check line built from it was refused by sha256sum, so the copy did not run (fail closed, no harm). A later command named a mode (dry4) that the script's allowed list did not have, so the script stopped at its first assert. A decision prescribed python -I, which the guard forbids. A summary of a command in a request carried a caret that the command did not have.

## Occurrences
- **2026-10-30 (session 578ea88b, D-3892 C7, D-3893 C2).** The hash in the page-copy command had 63 characters; the worker had typed the same slip in its own request text; the check refused; the next request used the hash printed by sha256sum.
- **2026-10-30 (session 578ea88b, D-3893 C4, D-3894).** `make_records_104e.py dry4` stopped at the mode list; one token added by an exact-replacement script, with the diff shown.
- **2026-10-30 (session 578ea88b, D-3892 C7, D-3890).** `python -I` was prescribed twice; run in the guard form `timeout 110 python <file> < /dev/null` and disclosed.
- **2026-10-30 (session 578ea88b, D-3899).** The summary of the (2b) command in a request had a caret; the command as typed had none (main transcript :7224).
- **2026-10-31 (session 85a45f06, D-3968 C1, D-3970 C2, D-3970 request).** The gate hash in two of the decision agent's commands differed from the machine value by one character, and my request retyped the hash of a dry-run output with the tail of the definition hash; the machine value was used and the slips disclosed.
- **2026-11-01 (session a048abb9, D-4339, D-4341, D-4391).** A hash typed from memory in a checkpoint sentence (D-4339), the hash-from-memory slips of the R111 stretch (D-4341) and a wrong test-file hash in the first draft of TASK-112's acceptance text (D-4391); each caught by a check or replaced by the sha256sum value before use.
- **2026-11-01 (session a048abb9, D-4401, D-4403).** Counts taken by eye or by grep hits and not by machine from the right object: the notes of the page builder were 26, not 27 (the checkpoint said 27), and the copies of the D-4293 hand-back were one, not five (grep hits in other instances' search results were counted as hand-backs); the builder's own count lines (`copies 1`, `pages 109`) were the check that showed it.

## Why it happens
Long hashes and commands are retyped from memory or from a previous message, and the decision agent repeats what the request says; the guard's forbidden forms are not in the decision agent's view.

## Prevention and detection
- Write the check line from `sha256sum <file> > <name>.sum` and test it with `sha256sum -c <name>.sum`; compare the printed hash with the stated one by a command (grep -c).
- Before a command that names a mode, a branch or an option, grep the script's allowed list for it.
- Put the exact command text in the request by copying it from the file or the shell input, never by summary.
