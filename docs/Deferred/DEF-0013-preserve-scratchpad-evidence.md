# DEF-0013: Copy the scratchpad-only evidence into the working folder

- Status: done
- Opened: 2026-10-06 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md)
- Deferred by: Claude (proposal, not a decision)
- Decision group: A ("adding new files to the working folder", decision agent group A)

## What
Some evidence that DM row A41 and decisions D-003 to D-005 rely on exists only in the session scratchpad. The scratchpad is a temporary folder (`%LOCALAPPDATA%\Temp\claude\E--AIEOS\<session id>\scratchpad`) and may be cleared. It holds:
- `decider\aieos-decider.pre-activation.md`: the pre-activation copy of the agent definition. A41 records its SHA-256, and D-005 condition C4 hashed it.
- `decider\activate.py`: the evidence for D-004 R2 (the five edits outside the status section).
- the decision-agent requests and raw outputs for D-003 to D-005, and the pre-append copies of the decision log;
- the memory pre-write backups (`remedy\`);
- the CS-3 v2 drafting rounds (`cs3v2\r1`, `cs3v2\r2`) and the extracts of the owner's questions.

The proposal is to copy these files unchanged into the working folder and to record their SHA-256 values.

## Why deferred
It was noticed while these records were prepared, and it was not raised in the session.

## Resume when
First thing in the next session, before the scratchpad can be cleared.

## Depends on
Nothing now. D-006 was a stand-in decision; the real decision agent confirmed it as D-008.

## Log
- 2026-10-06: noted while preparing these records.
- 2026-10-06: the folders `decider\`, `cs3v2\` and `remedy\` were copied unchanged to `%USERPROFILE%\AIEOS-REG0-lite\sessions\0302fdd2-6f1e-4542-b031-0dde532ea849\scratchpad-evidence\`, with a SHA-256 manifest (`MANIFEST.sha256`); decided by: decision agent (A41), D-006 (stand-in).
- 2026-10-06 (correction, session 5fd3e494): the archive holds five folders, not three: `decider\`, `cs3v2\`, `remedy\`, `records\` and `rev\`. `MANIFEST.sha256` lists their 253 files, and `sha256sum -c` passed again in session 5fd3e494. Two more files, copied after D-006 without a decision, are outside the manifest (L-0001). D-006 was a stand-in decision; the real decision agent confirmed it as D-008.
- 2026-10-06 (correction, session 5fd3e494; found by D-013): three files are outside the manifest, not two: `decider\D-006-raw.txt`, `decider\decision-log.pre-D006.md` and `records\exec6\MANIFEST.sha256`.
