# DEF-0081: the next text change of read_set_record.py and of TASK-064's AC3 text

- Status: open
- Opened: 2026-10-18 (session 01f64acc; decision D-1296 C3)
- Deferred by: decision agent (A41), D-1296, after the way-2 reviews of TASK-064 at its head.
- Decision group: A (a text and test change of src/aieos_bootstrap/read_set_record.py and its tests, in a task of its own).

## What
TASK-064's module (src/aieos_bootstrap/read_set_record.py) was accepted with these points carried, each non-blocking:
- The fence sentence of the module's docstring (and of the contract header) overstates: eventlog's idempotency check runs before the fence and compares the fencing token, so a repeat after a release or under another token gives "duplicate" or "conflict", not the writer's fence refusal; and "duplicate with the same list" also needs "and the same token". Nothing is appended in any of these cases. Narrow both sentences.
- The fence ties the write to the token, not to a session: say "from the holder of the token".
- A submission also releases the lease (adapter.py:16-17): name adapter.submit beside adapter.end and a violation.
- state['passed'] is set just before append is called, so a non-callable append returns the record although append never ran: set it after the call starts, or state it.
- The integration test (erratum E1 of D-1291) should say that observe's path through the real writer's file and store is untested.
- Untested points: no broken copy for the given list changed in place or for removing observe's record-is-None check; the context's fencing_token passed to append itself (a mutating append); str and list subclasses; a session_id holding NUL, a backslash, ":" or "..".

## Resume when
- With the next change of that module (for example the task that gathers reads in the hook process, part CC-3's neighbour), or the owner's word.

## Log
- 2026-10-18: opened (session 01f64acc; D-1296).
- 2026-10-30: TASK-102 (accepted by decision D-3707 at f25b4576; range fb90baaf..f25b4576; records d3a328bd; the map is docs/records/TASK-102.jsonl :44): settled the fence sentence, "from the holder of the token", adapter.submit named, state['passed'] stated (src/aieos_bootstrap/read_set_record.py:21-33, :57-59, :87-88, :191, :246), the integration test's note (tests/integration/test_read_set_record_store.py:6-7) and three untested points (tests/unit/test_read_set_record.py:65, :110, :198); open the contract-header points and TASK-064's AC3 text; the map's "point 15" matches no point of this item; broken copies for the list changed in place and observe's record-is-None check show no change. Status stays open.
