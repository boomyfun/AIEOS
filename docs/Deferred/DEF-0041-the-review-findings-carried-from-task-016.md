# DEF-0041: TASK-016's non-blocking review findings in the writer and its tests

- Status: open
- Opened: 2026-10-11 (decision file D-414)
- Deferred by: decision agent (A41, A51), D-414 (TASK-016 accepted with these recorded, no fix in that task; finding (c) also carried as a requirement).
- Decision group: A (code, test and wording within the self-build).

## What
- (a) tests/unit/test_writer.py: the failed read-back (AC2, AC10) is tested only through the private `_append_line`, and the file's bytes after the raise are not asserted, so "repairs nothing" holds by reading of the code, not by a test.
- (b) src/aieos_bootstrap/writer.py: append_event creates `<root>/.aieos/` before eventlog.append decides, so a refused first append leaves an empty folder (allowed by AC1's "when absent"); move the creation after the decision, or say so in the docstring.
- (c) writer.py: a caller-given epoch reused for a recreated store would repeat the fence's tokens; the docstring does not say so. Also a requirement on the contract of the first task that calls the store (DEF-0030; D-414): never give an earlier store's epoch to a recreated store.
- (d) writer.py: a symlinked `.aieos/` or `.aieos/local/` resolves outside the root; not a stated limit.
- (e) tests/unit/test_writer.py: R8's scan covers open, `.open`, `.connect` and the directory string only, and the imports only of writer.py; its allow-list names json, which writer.py does not import.
- (f) tests/unit/test_writer.py: the tables test compares with the module's own constant TABLES, not a literal.
- (g) tests/property/test_writer_properties.py: bare `assert` (no-ops under -O); no expiry or session end in the random sequences.
- (h) tests/unit/test_writer.py: untested: an expired, unremoved lease giving "held"; start_session and end_session raising when no store exists.
- (i) writer.py docstrings: WriteResult.refusal ("the findings say why" holds only for a fence refusal); held_lease "reads only" while it takes BEGIN IMMEDIATE; held_lease and grant_lease do not say an expired, unremoved row counts as held; append_event does not say a store with other tables raises.
- (j) writer.py: a crash between the store file's creation and its first COMMIT leaves a file that every later call refuses (fail closed); not in the docstring.

## Why deferred
D-414: none lets anything be written on a refusal or a token repeat inside one store; all five reviews pass with no weakening; a fix would have meant a second task commit, a push and new reviews or the decision agent's reading for test depth and wording.

## Resume when
The next task that changes src/aieos_bootstrap/writer.py or its test modules; (c)'s requirement at the contract of the first task that calls the store.

## Depends on
TASK-016 accepted (done, D-414).

## Log
- 2026-10-11: opened (decision file D-414).
