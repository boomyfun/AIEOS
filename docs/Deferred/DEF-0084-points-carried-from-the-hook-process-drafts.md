# DEF-0084: points carried from the review of the hook process's specification drafts

- Status: open
- Opened: 2026-10-18 (session 1c0ea663; decisions D-1335 C7, D-1338)
- Deferred by: decision agent (A41), D-1335 C7, after review round h4b of the drafts of specification 5 revision 4 and specification 2 revision 7.
- Decision group: A (inputs to the contracts that build the hook process, or to a later revision).

## What
- The local store's table `reads` (specification 2 revision 7, draft) has no bound on its size; an agent that controls a session id can add rows; to be stated as a limit or bounded by the contract that builds the accumulation (round h4b, Y2-11).
- Points of the design notes accepted but left to a contract: the cost of fail closed when a lease expires during a run (every later hook call refused until the launcher ends the session), and the rejected alternative; the hook input's own `session_id` kept in the recorder words only (round h4b, Y5-6; D2-4 and D2-5 of the design note).
- More than one lease per session: the writer's grant allows it, while the hook refuses a session without exactly one unexpired lease; whether the core should refuse a second grant to one session (round h4b, Y2-6).
- Points of round h4c that its dispositions table defers (session 9a7be298; D-1346): the functions the hook and the launcher need that the base code does not have (a token-less observe, reading and removing a session's stored reads, finding a task's leftover sessions), the separation of the hook's entry points from the core-only path and a test of it, the write lock that the store lookup takes and its refusal cost, the source of the base commit for the contract, the record's place among specification 1 §7's start steps, the lease length the launcher sets, an unreadable contract on every concern and its cost in section 8, a global hook placement under a parent folder whose `.aieos/` holds a lease row (round h4c, Y1-4, Y1-6, Y1-7, Y2-8, Y2-10, Y3-2, Y5-7, Y5-9).
- Points of round h4d that add content (session 9a7be298; D-1348 C3): who removes the stored reads after a lease holder's record (Y1-1, second part); whether the core's append accepts a token-less record while an expired lease row of the task is still present, and the record's slot against specification 1 §7 (Y1-3, Y2-6); whitespace-only values, a link or junction as the store file, and where the upward search ends (Y2-4); how the hook's violation path is fenced, and that it never writes an observed read-set record (Y4-6); D2-4, D2-5 and D3-2's "not a holding" named in the text (Y5-7); "no hook program's function reaches it" as a requirement that the contract tests (Y5-8).

## Resume when
- With the contracts that build the hook process (the store lookup and the reads table first), or the owner's word.

## Log
- 2026-10-18: opened (session 1c0ea663; D-1335 C7, D-1338).
- 2026-10-18: the deferred points of rounds h4c and h4d added (session 9a7be298; D-1346, D-1348 C3); specification 5 revision 4 and specification 2 revision 7 landed on main (F55, F56); still open for the contracts.
- 2026-10-18: TASK-066's contract takes Y2-4, Y2-8, h4b Y2-6 in part, Y1-6 and Y5-8 (its check of calls) and the base commit's source; the other points stay open (session 747e2eff; D-1364).
- 2026-10-19: TASK-067, accepted under D-1458, took h4b Y2-11 (the bound), h4c's "reading and removing a session's stored reads", h4d Y1-1's second part (remove_reads), h4c Y2-8 for the write path and h4d Y2-4's whitespace-only values for paths (TASK-067.yaml:116-125); the other points stay open; written late, in session bc3137c8 (D-1474 C4).
