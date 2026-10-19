# DEF-0089: the findings and limits carried from TASK-068

- Status: open
- Opened: 2026-10-20 (session b62e2485; decisions D-1510, D-1511, D-1513 and D-1515)
- Deferred by: decision agent (A41, A51), D-1515, at TASK-068's acceptance, with the points ruled by decisions D-1510, D-1511 and D-1513.
- Decision group: A (a text and test change of src/aieos_bootstrap/claude_code_read_hook.py, src/aieos_bootstrap/claude_code_store.py and their tests, and the next revision of docs/tasks/TASK-068.yaml's header, in a task of its own).

## What
TASK-068 (the read hook program of the Claude Code adapter) was accepted at its head 3c6668ac with these points carried, each non-blocking (round t68r, reviews R1 to R5 on claude-sonnet-5-5; the decision agent's reviews DA-1 to DA-3):
- **A named departure (D-1510 C2):** E1, AC4's "after each case ... (a dump)" is not met by the "recorded once" case, which checks the stored reads through writer.stored_reads and takes no dump of the store's tables.
- **Sentences that say more than the code does (D-1510 C1), not limits:** P1 "a hook killed by that timeout stores nothing" (read: may store nothing; a kill after COMMIT may have stored the read; the contract header says the same, so the two are fixed together); P2 "never raises" and "exit code 0 on every outcome" (read: for exceptions inheriting Exception only; a BaseException, or a failure before main runs, can give a non-zero exit and text); P3 "a PostToolUse hook runs after the read" (read: as documented, unmeasured).
- **Wording:** P4 claude_code_store's module docstring still calls the hook entry "a later contract's"; P5 the clock window's "kept because" reason is muddled (the limit itself is right); P6 specification line numbers in the module docstring go stale; DA-1 (ii) RESULT_KEYS is a public constant the contract does not name.
- **Untested or narrow points:** P7 a bytes subclass for stdin_bytes and a str-subclass session id (both fail closed); P8 no broken copy runs the integration class, and the two-leases and expired-lease cases assert the reason prefix, not the count; P9 the property test asserts only the fail-closed direction; P10 the separation check ignores relative imports and is lexical (a dynamic import in another hook-side module is not seen; DA-1 (iii)); P12 broken copies B29 and B30 remove one pinned phrase per check; DA-1 (i) a StoreResult whose findings is not iterable ends in step (6)'s "entry: TypeError", not step (5)'s fixed finding.
- **Other:** P11 the contract cites a real session id (TASK-068.yaml :16-17, :549); R2's point that an evidence script kept outside the repository holds a user-folder path (no action; it is never committed, and every records commit's scans cover it); DA-3 (iii) review R5's line references at two of its points do not match the file (its reading agrees with the code).
- **Limits only:** the contract's stated limits (C6 and P-LOC unmeasured; no hook placed, no matcher, no setting, nothing measured; the silent loss; the clock window in the fail-open direction; reads through other tools not seen; standard input read whole; no test starts a process).

## Resume when
- With the next text change of claude_code_read_hook.py or claude_code_store.py, or TASK-068.yaml's next revision (for P1 and P11), or before any contract wires the hook or its placement is put to the owner (whichever comes first), or the owner's word.

## Log
- 2026-10-20: opened (session b62e2485; D-1515).
