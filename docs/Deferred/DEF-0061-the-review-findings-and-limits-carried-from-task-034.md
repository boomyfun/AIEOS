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
- 2026-10-15 (session 043ab97b): TASK-035, the hardening of the scope-drift caller, accepted and on `main` (659dad56; decision D-733; records CS-188, D-734): done: m1 (a name listed twice and a raw control character in a name stop the run; a C-quoted name is kept as an entry that never matches), m2 (a walked element's mode must fit its type), m3 (the event id and payload taken inside the append's guard), m4 (the docstring, with reading R1, unprobed, and limit L2), t3, t4 and part of t5 (a mixed trailer; the facts after a claims and an append refusal; naming tests in the integration and property modules), with the review findings P1, P4, P5 and P6 fixed by test (decisions D-731, D-732). Still carried here, to M4's exit review point: t1, t2 and the rest of t5 (contracts and risk_rules in the claims input asserted directly; the tautological negative control); L1 (a merge is not read against its first parent); added: L2 (a raw newline inside a name from a non-quoting reader can make an in-form line for an element no other line names) and P7 (the append handler formats an event id with %s, so an id whose text conversion raises would escape; as at the base, unreachable from repository input). ../History/2026-10/2026-10-15-0422-the-scope-drift-callers-hardening-accepted-and-on-main.md
- 2026-10-15 (session 218e5c55): M4 exited with named limits (decision D-756; docs/plan/m4-exit-review.md §3, after the owner chose Option C on 2026-10-15). Limit L-d: t1, t2, the rest of t5, L1, L2 and P7 stay carried, to a task that touches scope_reconcile.py (ranked fifth in the review's §4).
- 2026-10-30: TASK-102 (accepted by decision D-3707 at f25b4576; range fb90baaf..f25b4576; records d3a328bd; the map is docs/records/TASK-102.jsonl :44): settled t5 in part (contracts and risk_rules in the claims input, tests/unit/test_scope_reconcile.py:432) and t1 in part (the base-read test asserts "reconciled" and the rerun test cannot pass vacuously, tests/property/test_scope_reconcile_properties.py:140, :157-158); open the rest of t5, the tautological negative control (test_scope_reconcile.py:561-563 builds a local set), the rest of t1 (the oracle reuses rules_from_policy and evaluator_from_workflow, never generates a differing hash, has no coverage counters), t2, L1, L2, P7. Status stays open.
