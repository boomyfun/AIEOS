# DEF-0086: TASK-067's code, begun and not committed

- Status: open
- Opened: 2026-10-19 (session 799f77cb; decision D-1410 C3)
- Deferred by: decision agent (A41, A51), D-1410 C3: the code stops at a clean point before the session's end.
- Decision group: A (the code of an approved contract, TASK-067 on main at 60345ce1).

## What
- The draft, in session 799f77cb's archive (w67-draft.patch, and the scratch clone w67 at main 60345ce1): writer.py's change (the reads table, add_reads, stored_reads, remove_reads, migrate_store, the private helpers _live_lease, _store_present, _write_store and _read_reads, _store_answer's branch, the module docstring), the three changed tests AC8 names, and new tests for AC1 to AC7 in the three writer test files; 135 tests of the writer and store modules pass in the clone. Not yet done: the AC8 acceptance-time scripts and their weakened-copy runs, the broken copies, the whole suite under the CI's preparation steps, the task branch and its commits, the five way-2 reviews.
- Three points for the decision agent before the code is committed:
  - AC7 (a): a read-only open of a WAL-mode store created "-shm" and "-wal" files beside it; the store's bytes were unchanged and both answers were right (D-1362 C6's form: brought before commit; no text of session_lease is changed for it).
  - The catch-all: a path not encodable as UTF-8 gives the finding "unreadable: UnicodeEncodeError" (a subclass of ValueError, raised inside the unchanged _store_uri); the contract's text says "unreadable: ValueError"; the draft's test asserts the exception's own type.
  - AC7 (b): SQLite's trace reports "-- PRAGMA table_info=…" comment lines for the table check's SELECT over pragma_table_info; the draft's test leaves lines starting with "--" out (the worker's reading).

## Resume when
- At the next session's start, after the pages D-1404 onward.

## Log
- 2026-10-19: opened (session 799f77cb; D-1410).
