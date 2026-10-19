# DEF-0090: a count of reads lost while a session holds a lease

- Status: open
- Opened: 2026-10-20 (session b62e2485; decisions D-1478 C3, D-1488 C2 and D-1515)
- Deferred by: decision agent (A41, A51), D-1515, at TASK-068's acceptance, as TASK-068's contract names it (TASK-068.yaml :114-116; D-1469 C1).
- Decision group: A (a revision of specification 2, and the contract that builds the count).

## What
- TASK-068's read hook program loses a read silently, and nothing records the loss, on every "lost" outcome (a lock held past add_reads' timeout, the bound, a path refused, a damaged store, an exception) and on every "skip" other than "enforce_nothing" ("argument", "refuse", "uncovered", "entry") while the session holds a lease; the read-set stays a lower bound and an estimate (specification 5 :72-73; specification 2 :184).
- Proposed for specification 2's next revision: a count of such lost reads per session and lease, so that the size of the gap is known; where it is kept, who writes it (the hook side may write only through the writer) and how a reader of the read-set sees it are open.

## Resume when
- With specification 2's next revision, or the contract that next changes the read-set's accumulation, or the owner's word.

## Log
- 2026-10-20: opened (session b62e2485; D-1515).
