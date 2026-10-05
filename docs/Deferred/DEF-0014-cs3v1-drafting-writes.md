# DEF-0014: Writes from the CS-3 v1 drafting turns that no decision covers

- Status: open
- Opened: 2026-10-05 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md)
- Deferred by: Claude (proposal, not a decision). D-002 told the worker to raise `exec_cs_v2.py`, under D-003 or in its own request; that was not done.
- Decision group: A to keep the files ("adding new files to the working folder"); B to delete them or move them out (as D-001 reasoned)

## What
In the CS-3 v1 drafting turns (2026-10-05, :4078 to :4329), Claude wrote into the working folder's `CS\` without an authorization that named these writes (L-0001):
- new files: `gen_cs3.py`, the CS-3 v1 plan, diffs, notes and before/after files, and `exec_cs_v2.py` (:4097);
- in-place edits of `rehearsal_tests.py` (:4097), `verify_independent.py` (:4113) and `make_plan_doc.py` (:4212, :4225).

D-001 decided only the 11 copies in `CS\records`. D-003 to D-005 checked and used `exec_cs_v2.py` and the edited tools for CS-3 v2, but no decision says whether the earlier writes would have been approved, as the definition's rule on things already done requires. The owner did not answer Claude's question whether "Soạn CS-n" allows drafting files in `CS\` (:4344), and it was not among the items handed to the decision agent at :4439.

## Why deferred
It was not raised in the session.

## Resume when
With DEF-0001: put it to the real decision agent, to be decided as if not done.

## Depends on
DEF-0001.

## Log
- 2026-10-05: writes made (:4078 to :4329); listed in Claude's self-audit (:4344).
- 2026-10-06: D-002 said to raise `exec_cs_v2.py` (decision log).
- 2026-10-06 (session 5fd3e494): D-007 C4 says this goes to the decision agent as its own request. The request must include the list of CS-3 v1 files, and an unedited `diff -u` of `rehearsal_tests.py`, `verify_independent.py` and `make_plan_doc.py` against their `_cs2` editions in `CS\records`. It does not block anything else.
