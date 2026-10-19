# DEF-0085: the next text change of the store lookup (writer.session_lease and claude_code_store)

- Status: open
- Opened: 2026-10-19 (session fb812044; decision D-1376 C2)
- Deferred by: decision agent (A41, A51), D-1376, after the five way-2 reviews of TASK-066 at its head 3998a378 (all pass).
- Decision group: A (a text and test change of src/aieos_bootstrap/writer.py's lookup and src/aieos_bootstrap/claude_code_store.py, and their tests, in a task of its own).

## What
TASK-066's code was reviewed with these points carried, each non-blocking:
- **The lexical search (fail-open):** judge's upward search starts at os.path.abspath of the working folder and climbs lexical parents, as the contract says; a working folder reached through a link from outside the project's tree finds no store and gives "enforce_nothing". The docstring states that a hook call outside every project's folder tree is not judged, but not that the tree is lexical (reviews R4, R5).
- The WAL state: the docstrings say a journal or WAL state a read-only connection cannot use is refused; no test builds a WAL-mode store, and whether a read-only open of one reads it or creates its side files is untested (the writer itself never makes one) (R2, R4).
- claude_code_store's docstring says any exception inside gives "entry"; an exception while checking now gives "argument: now (<type>)"; the implementer's reading R-d has the same breadth (R4).
- judge's check of now (a class named datetime in the type's MRO) and the writer's (isinstance) differ; both fail closed; stated only in a reading, not in the code (R4).
- _map accepts "done"/"tied" with a lease on the search path, where no session id is given; the real lookup cannot give it; a guard would make "tied" impossible without a session id (R5).
- Untested points: AC9's short-name case of the link check is not exercised as written (the stand-in's key is never looked up; the next real call covers part) (R3); mutation J9 is caught only by the unit module, not the property test (R3); mutation M9 (the deferred BEGIN) is caught only by a source-text check, since under read-only mode BEGIN IMMEDIATE behaves the same in every behavioural test (R3, R4, R5).
- A limit only: the presence and link stand-ins patch functions of the global os module for one call (safe in a single-threaded suite) (R1).

## Resume when
- With the next text change of either module, or before any contract lets a hook call act on judge's "enforce_nothing" (whichever comes first), or the owner's word.

## Log
- 2026-10-19: opened (session fb812044; D-1376).
- 2026-10-19: TASK-067 took its writer-side points (the WAL state, mutation M9, AC9's short-name case) by AC7 (a) to (c), accepted under D-1458; its claude_code_store points and its second trigger stay open (session dc5d0da2).
