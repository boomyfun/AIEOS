# L-0007: Evidence must prove the exact proposition

Rule: For every check, state the exact proposition it proves and what it does not cover, and never use a proxy (a local copy, a related object, a sample) as proof of the real thing.

- Status: active
- Category: technical
- Binding: record only.

## Pattern
A check that is cheap to run is presented as proof of something it does not show.

## Occurrences
At least seven in session 2026-10-04-1817 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md):
- **2026-10-05 (:766, :774, :778).** Claude said the `strict` status-check setting proved the merge provenance chain.
- **2026-10-05 (:939, :990).** A faulty check command raised a false CRLF alarm.
- **2026-10-05 (:1056, :1064, :1068).** The local remote-tracking ref was used as if it proved the live remote state.
- **2026-10-05 (:1076, :1084).** Two wrong objects:
  - `git ls-files --eol` reads the index and working tree, not the committed blob;
  - an acceptance check did not exclude merge commits.
- **2026-10-05 (:1102, :1110, :1115).** `git hash-object <path>` was proposed as evidence of what was committed. It was replaced by the index and the commit tree.
- **2026-10-05 (:1212, :1216, :1224).** Two overclaims:
  - a step was called read-only although `git status` may rewrite the index stat cache;
  - the configuration evidence covered only one scope.
- **2026-10-05 (:1513, :1601).** A grep-based extraction was claimed to capture every normative statement. A pilot showed it caught about 30%.

Related: DM A5 recorded a permission as a fact about the runtime, without a check of Claude's own environment (L-0003).

One incident in session 2026-10-06-0306 (../History/2026-10/2026-10-06-0306-real-decider-rechecks-and-push.md):
- **2026-10-06 (D-008 request; found by D-013).** A check of "files not in the manifest" excluded every file named `MANIFEST.sha256`, so it also hid a nested file with that name. Claude reported two files outside the manifest; there were three.

One incident in session 2026-10-06-0602 (../History/2026-10/2026-10-06-0602-rules-book-definition-and-log-split.md):
- **2026-10-06 (D-025, D-026).** Claude used the definition file's SHA-256 as if it showed which definition the running decision agent had been loaded with, and the D-025 request assumed the agent could go on deciding after the change. The harness did not reload the definition until the session was resumed (:1068). D-026 compared its loaded text with the files itself and escalated; the owner then allowed the earlier text to decide the session's remaining steps ("có cho cả hai câu", :1062).

One occurrence in session 2026-10-10-0043 (../History/2026-10/2026-10-10-0043-bootstrap-scope-and-m3-documents.md):
- **2026-10-10 (D-257 request).** A line of my own check script ("placeholder") asserted nothing; it was disclosed and not counted as a check.

One occurrence in session 2026-10-10-0235 (../History/2026-10/2026-10-10-0235-resume-check-fixtures-accepted.md):
- **2026-10-10 (CS-90).** Two of my generator scripts first held an assertion ending in "or True", which asserts nothing; both were removed before the scripts ran.

One occurrence in session 2026-10-10-0451 (../History/2026-10/2026-10-10-0451-decision-files-d284-d292-and-task-010-landed.md):
- **2026-10-10 (D-295).** A check that the new module's whole-file hash differs from the old draft's cannot show that two lines were reused; the decision agent found the two byte-identical lines by reading, and the rework added a phrase check.

Occurrences in session 2026-10-11-2112 (../History/2026-10/2026-10-11-2112-test-to-ac-listing-accepted-and-on-main.md):
- **2026-10-11 (a447 :821, :1664; D-526 to D-528).** The last session's request said a pre-code owner line was "sent byte-equal" as a text block, and its History said the owner was told before any code; neither was checked in the transcript, which holds no such text block before the code (only a thinking block with a paraphrase, and the line in the session-end reply). Then this session's own correction over-claimed twice: first that the line was certainly not sent, then that a text block before a tool call is never kept as text (refuted at :560). The decision files now say only what the transcript shows. A claimed send to the owner is now checked by script in the transcript, by block type and bytes (tools/line_sent.py, D-526 C4, D-527).
- **2026-10-11 (:532).** A pause reply re-laid out the checked line instead of sending it byte-equal; line_sent.py found it (D-528).

Occurrences in session 2026-10-11-2233 (../History/2026-10/2026-10-11-2233-stale-evidence-computation-accepted-and-on-main.md):
- **2026-10-11 (a067 :2036; D-542, D-543).** The last session's closing reply carried its owner texts word for word but re-laid out the checked line around them (a sentence added, the opening and closing reworded); line_sent.py against the checked file gave "sent as text: False". The check was made at this session's start, as the reply promised, and the owner was told.

Occurrences in session 2026-10-15-2351 (../History/2026-10/2026-10-15-2351-the-hardening-on-main-and-round-2s-export-on-its-branch.md):
- **2026-10-16.** A local text scan for bandit's patterns was reported as "every bandit pattern 0"; it was a proxy, not bandit, and missed B105 reading a dict literal `'fencing_token': None` as a hard-coded password, so the branch run's bandit step failed (run 298). A local pattern scan is described as a proxy, never as bandit's result; the CI's bandit run is the evidence.

Occurrences in session ea6ea0a3 (the History of that session):
- **2026-10-25 (D-2933).** TASK-090's draft check chk90, rerun after the drafts were placed in the clone, compared the drafts with the clone's working tree, which already held them, so it could not show a difference from the base; fixed by reading the base from git at the contract commit. A check script reads its base from git, never from a working tree it may have changed.
- **2026-10-25 (D-2932, D-2940).** chk90 checks only part of the deterministic rule; the deterministic rule's own run (det90) found an os.mkdir in a test that chk90 passed. det90 is the check of record; chk90 is a quick proxy.

## Why it happens
- Proxies are cheaper than the real check.
- The same model picks the evidence and judges it.

## Prevention and detection
- Each acceptance criterion names the object it reads (blob, tree, ref, live remote, scope) and has a "does not show" line.
- Use `GIT_OPTIONAL_LOCKS=0` for read-only Git commands.
- Test a check tool on a known case before trusting it.
