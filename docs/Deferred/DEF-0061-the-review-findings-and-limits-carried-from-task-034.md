# DEF-0061: the review findings and limits carried from TASK-034, the scope-drift caller

- Status: open
- Opened: 2026-10-15 (decision D-719)
- Deferred by: decision agent (A41), D-719 (option C at the level checkpoint: TASK-034 accepted with every non-blocking review finding carried) and D-720 (the limits stated with the acceptance).
- Decision group: A (limits of the scope-drift caller within the self-build).

## What
- **m1, a crafted parent tree's names** (R2, R3, R5; settled for R3 by D-719): scope_reconcile's tree listing keeps the last of two lines with the same name, and its name pattern admits a tab, while a name holding a newline splits the listing into a fake extra line; a crafted parent tree could so override a path element. The parent is governed history, so this is hardening, not a fail-open path in use.
- **m2, the entry mode** (R2, R5): the mode is not checked against the type, so a symbolic link (mode 120000, a blob) at the policy's or the workflow's path is read as the file (the outcome stays fail closed: no rules or an empty evaluator list).
- **m3, AC9's letter** (R2): the append loop reads the event id before its try, so AC9's "no exception escapes" holds only because the accepted scope_drift.claims always gives event_id (stated with the acceptance, D-720).
- **m4, two docstring sentences** (R4): that a name with "/" or NUL is out of form; that a missing approval or value is recorded only in facts.contracts.
- **t1 to t5, test depth** (R3, R5): the property oracle reuses rules_from_policy and evaluator_from_workflow, never generates a differing hash, has no coverage counters, and its rerun test can pass vacuously, and its base-read test does not assert "reconciled" (t1); the real policy's eleven rules are checked by count and shape, not each match list (t2); no direct test of matching contract bytes with a path outside the write-set (t3); the stand-ins use 64-hex ids only, the 40-hex form covered by the real-Git case (t4); no test of a mixed good and bad trailer, of facts as a mapping after a claims or append refusal, or of contracts and risk_rules in the claims input; a tautological negative control; no naming test in the integration and property files (t5).
- **L1, a merge** (contract limit; from DEF-0060): a merge commit is not read against its first parent (gitread pins no diff form for it); it is named uncovered.
- **Unapproved scratch edits** (D-720 C4): option (B)'s edits for m1 to m4 and two tests were begun in the session's scratch clone before D-719's answer; never committed or pushed, they carry no approval, and a hardening task may start from them only through its own scope note, contract and review.

## Why deferred
D-719: at about 70% of the context window a fix round would have ended the session past its stop band; every finding is non-blocking (five reviews passed), m1 to m3 are unreachable or bounded by trusted history today, and the test-depth findings are limits of the evidence, not defects.

## Resume when
At a small hardening task (m1 to m3 with tests, t4) scheduled before M4's exit review point, which a later decision names; the rest at that task or at the review point.

## Depends on
TASK-034 (accepted, decision D-720); TASK-033 (scope_drift.py); TASK-024 (gitread.py); DEF-0030 (the core's caller).

## Log
- 2026-10-15: opened (decisions D-719 and D-720; session 9a3d9254).
