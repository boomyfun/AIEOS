# DEF-0087: the findings and limits carried from TASK-067

- Status: open
- Opened: 2026-10-19 (session dc5d0da2; decision D-1458)
- Deferred by: decision agent (A41, A51), D-1458, at TASK-067's acceptance, with the points ruled by decisions D-1431, D-1436, D-1441, D-1443 and D-1445.
- Decision group: A (a text and test change of src/aieos_bootstrap/writer.py and its three test files, in a task of its own).

## What
TASK-067 (the reads table and the read-set accumulation: writer.add_reads, stored_reads, remove_reads and migrate_store) was accepted at its head bfb44fe1 with these points carried, each non-blocking:
- **Named departures (decision D-1421):** E1, a path not encodable as UTF-8 gives the finding "unreadable: UnicodeEncodeError", not AC9's literal "unreadable: ValueError"; E2, AC7 (b)'s trace test lets comment lines of exactly the form "-- PRAGMA table_info=" through, so a statement starting with that comment would pass.
- **Untested or narrow points:** no garbage or 0-byte store case for migrate_store and no held-lock case for remove_reads (t67a-R2; t67c-R2's claim that the third commit resolves it is not borne out by the diff, D-1445 C2); "leases" is pinned only with count 0, and broken copies 03, 13 and 16 are narrower than their names (t67a-R3); the property test does not assert that each listed state was generated (t67a-R4); the "unreadable" variants (the open, the catch-all, a non-text stored path, no store result, an lstat ValueError) are not driven with hostile text (t67b-R1 point 1); append_event is not called directly after "migrated", its only store access, held_lease, is (t67b-R1 point 4); the path-read check matches the statement's start only (t67b-R1 point 5); the fixed count 37 in the reasons test is brittle (t67c-R5).
- **Behaviour points:** a REAL stored seq gives a fractional next seq; only a store written outside the writer can hold one (t67a-R5, DA-3); a "?mode=rw" open rolls back a hot journal, which changes bytes, and the code does not say so (t67a-R2); with exactly 10000 stored, a duplicate or an empty call returns "done" 0 (DA-1).
- **Wording (t67a-R4):** _write_store's docstring says every non-done ending names a type, while the non-StoreResult ending gives fixed text; three header limits of the contract are not in the code's docstrings; stored_reads' "creates nothing" has no WAL qualifier; one docstring line is over-long; the commit message's "no other line changes" was not checkable by R4.
- **Limits only:** AC7 (c)'s short form is the lexical root "root/." with no real 8.3 short name (CI runs on Linux) (DA-1); the WAL side-file observation is Windows-only and the existing writer functions are untested on a WAL store; the contract's stated limits (the names-only table check; the 10000 and 4096 bounds and the record a lower bound; the presence, link and open steps apart; a held write lock refusing without a record; stored_reads and remove_reads checking no lease; orphan reads after a late add_reads; a migration during a lookup; now trusted from the caller; a failed COMMIT that may have applied the change; session_lease's docstring stale by design).

## Resume when
- With the next text change of src/aieos_bootstrap/writer.py's reads functions, or before a contract lets a hook-side caller use add_reads, or the owner's word.

## Log
- 2026-10-19: opened (session dc5d0da2; D-1458).
