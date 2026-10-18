# DEF-0084: points carried from the review of the hook process's specification drafts

- Status: open
- Opened: 2026-10-18 (session 1c0ea663; decisions D-1335 C7, D-1338)
- Deferred by: decision agent (A41), D-1335 C7, after review round h4b of the drafts of specification 5 revision 4 and specification 2 revision 7.
- Decision group: A (inputs to the contracts that build the hook process, or to a later revision).

## What
- The local store's table `reads` (specification 2 revision 7, draft) has no bound on its size; an agent that controls a session id can add rows; to be stated as a limit or bounded by the contract that builds the accumulation (round h4b, Y2-11).
- Points of the design notes accepted but left to a contract: the cost of fail closed when a lease expires during a run (every later hook call refused until the launcher ends the session), and the rejected alternative; the hook input's own `session_id` kept in the recorder words only (round h4b, Y5-6; D2-4 and D2-5 of the design note).
- More than one lease per session: the writer's grant allows it, while the hook refuses a session without exactly one unexpired lease; whether the core should refuse a second grant to one session (round h4b, Y2-6).
- Further non-blocking points of round h4c that D-1338 C1's dispositions table defers, once that table exists.

## Resume when
- With the contracts that build the hook process (the store lookup and the reads table first), or the owner's word.

## Log
- 2026-10-18: opened (session 1c0ea663; D-1335 C7, D-1338).
