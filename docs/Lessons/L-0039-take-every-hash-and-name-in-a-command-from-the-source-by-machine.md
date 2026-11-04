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
- **2026-11-02 (session bdca08a6, D-4441, D-4442 C6, D-4456, D-4474, D-4475).** The request of D-4441 was sent before the hash of cp19.sum was printed and asked the decision agent to read the sum; the value was the true one, and D-4442 C6 then required the sum hash to be printed before every request that relies on it (kept from D-4443 on). The request of D-4456 said the acceptance hash would change with the acceptance text; it hashes the contract and the task head only (D-4459 stated it). The cp52 entry compared the conclusion counts of the D view files with the X files by grep and said they were "run the same way"; the X files have no run-level fields (D-4474; cp53 corrects it). In the drafting of these end records a hash was partly typed from memory in a sentence of cp53 and replaced before the entry was final (D-4475). Why the rule did not stop them: L-0039's rule is about hashes and names in a command; the first and the third slip were about a request's order and about a count compared across files made in different ways, which the Prevention lines (print, compare, copy the exact command) do not name; the last is the kind the rule names, and it was caught before the entry was final.
- 2026-11-02 (../History/2026-11/2026-11-02-0522-m8-stage-8-task-114-the-ci-path-for-a-contract-the-core-writes.md, D-4513, D-4526, D-4535, D-4549): two values typed from memory in cp94; tasks 109 to 112 said to have pushed X to main when only 112 to 114 did; the hash of cp118.md given as the hash of cp118.sum; a draft naming X's own run id and "7 failing tests" for 10.
- 2026-11-02 (../History/2026-11/2026-11-02-1252-m8-stage-8-task-115-the-explicit-owner-kept-act-statement-for-aieos-run.md, D-4635, D-4636; checkpoint lines 1486, 1493): the R115w launch prompt was composed by hand and held two words that the brief does not hold, and my claim that it equalled the brief was wrong; found in D-4636, and the save script then compared with that one replacement stated.

Occurrences in session 08342c65, second part (../History/2026-11/2026-11-03-0157-m8-stage-8-the-continuation-08342c65-part-2-the-tier-answer-route-p1-and-the-task-117-contract.md; the evidence lines are the worker's checkpoint lines, decision-file lines and transcript lines named in each item; the worker's own claim until checked):
- D-4721: "9 lines" for a sum file with 8 (cp line 2097).
- D-4728: the typed part of row A74 v2 (cp lines 2141, 2146).
- D-4705/D-4704: `python -I` prescribed twice and run in the guard form `timeout 110 python <file>` with the reason (cp lines 1990, 1995).

## Why it happens
Long hashes and commands are retyped from memory or from a previous message, and the decision agent repeats what the request says; the guard's forbidden forms are not in the decision agent's view.

## Prevention and detection
- Write the check line from `sha256sum <file> > <name>.sum` and test it with `sha256sum -c <name>.sum`; compare the printed hash with the stated one by a command (grep -c).
- Before a command that names a mode, a branch or an option, grep the script's allowed list for it.
- Put the exact command text in the request by copying it from the file or the shell input, never by summary.
