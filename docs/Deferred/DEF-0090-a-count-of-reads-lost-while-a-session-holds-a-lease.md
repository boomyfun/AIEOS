# DEF-0090: a count of reads lost while a session holds a lease

- Status: open
- Opened: 2026-10-20 (session b62e2485; decisions D-1478 C3, D-1488 C2 and D-1515)
- Deferred by: decision agent (A41, A51), D-1515, at TASK-068's acceptance, as TASK-068's contract names it (TASK-068.yaml :114-116; D-1469 C1).
- Decision group: A (a revision of specification 2, and the contract that builds the count).
- Blocks v0.1: no (a non-blocking review finding or limit of an accepted task)
- Scheduled in: M8, the adapter, violation-path and Claude Code hook fix task (adapter, replay, violation, claude_code, claude_code_channel, claude_code_reads, claude_code_shell_allow, claude_code_read_hook, claude_code_store, claude_code_pretool_hook, task_contract, session_violation, mcp_server), before the M8 exit review

## What
- TASK-068's read hook program loses a read silently, and nothing records the loss, on every "lost" outcome (a lock held past add_reads' timeout, the bound, a path refused, a damaged store, an exception) and on every "skip" other than "enforce_nothing" ("argument", "refuse", "uncovered", "entry") while the session holds a lease; the read-set stays a lower bound and an estimate (specification 5 :72-73; specification 2 :184).
- Proposed for specification 2's next revision: a count of such lost reads per session and lease, so that the size of the gap is known; where it is kept, who writes it (the hook side may write only through the writer) and how a reader of the read-set sees it are open.

## Resume when
- With specification 2's next revision, or the contract that next changes the read-set's accumulation, or the owner's word.

## Log
- 2026-10-20: opened (session b62e2485; D-1515).
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass A batch 3, decision D-5266 with the ruling of D-5266 C4): read in full; specification 2 was revised after 2026-10-20 several times (the last on 2026-11-04, TASK-117, 7253aa9) without the count: a search of docs/ for a lost-read count finds only this item and TASK-068.yaml:115 and the 'not touched' notes of later contracts (no count found by that search, which is not a proof of absence); B5 builds it after a specification 2 revision approved as its own decision before B5's contract. State: open; Blocks v0.1: no (a non-blocking review finding or limit of an accepted task); Scheduled in: M8, the adapter, violation-path and Claude Code hook fix task (adapter, replay, violation, claude_code, claude_code_channel, claude_code_reads, claude_code_shell_allow, claude_code_read_hook, claude_code_store, claude_code_pretool_hook, task_contract, session_violation, mcp_server), before the M8 exit review.
