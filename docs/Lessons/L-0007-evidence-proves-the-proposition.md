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

## Why it happens
- Proxies are cheaper than the real check.
- The same model picks the evidence and judges it.

## Prevention and detection
- Each acceptance criterion names the object it reads (blob, tree, ref, live remote, scope) and has a "does not show" line.
- Use `GIT_OPTIONAL_LOCKS=0` for read-only Git commands.
- Test a check tool on a known case before trusting it.
