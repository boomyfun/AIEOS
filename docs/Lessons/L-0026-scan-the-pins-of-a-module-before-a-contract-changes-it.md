# L-0026: Scan the pins of a module before a contract changes it

Rule: Before drafting a contract that changes an existing module, scan every test and the workflow for lines that pin or enumerate that module (hashes of its code, its import set, its docstring words, module lists) and name each pin in the contract with how it stays met; a pin the contract cannot meet needs the module left alone or the pin in the write-set, decided before the contract is approved.

- Status: active
- Category: process
- Binding: record only. Related: decisions D-1547 and D-1548; L-0004 (check before showing), L-0019 (an erratum cannot widen a write-set).

## Pattern
A contract put new code in a module whose code accepted tests of earlier tasks pin by hash; the pinning tests were forbidden by the contract and its own criteria required every test to pass unchanged, so no code could meet it. The drafting, two review rounds and the approval did not see the pins; the first local suite run did.

## Occurrences
- **2026-10-21 (session 1d7a0412; D-1547).** TASK-069 (approved under D-1537) put session_violation in adapter.py; tests/unit/test_evaluation_violation.py and tests/unit/test_evaluation_repeated.py pin the SHA-256 of adapter.py's code after its docstring (TASK-053, TASK-054). TASK-069 ended on spec_conflict before any code commit; TASK-070 put the call in a new module after a read-only pin scan (D-1548).

## Why it happens
Reviews and drafts read the module to be changed and the tests of that module, not the tests of other tasks that guard it; a hash pin lives far from the module it guards.

## Prevention and detection
- Before a contract's first draft: a read-only scan of tests/ and the workflow for the module's file name, hashes, import-set checks and package enumerations; its output goes with the draft to the decision agent and to at least one reviewer.
- A reviewer lens names "every existing test that pins or enumerates the changed modules".
- The suite runs locally in the scratch clone before the first code commit, under the compile step.
