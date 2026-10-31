# L-0026: Scan the pins of a module before a contract changes it

Rule: Before drafting a contract that changes an existing module, scan every test and the workflow for lines that pin or enumerate that module (hashes of its code, its import set, its docstring words, module lists) and name each pin in the contract with how it stays met; a pin the contract cannot meet needs the module left alone or the pin in the write-set, decided before the contract is approved.

- Status: active
- Category: process
- Binding: record only. Related: decisions D-1547 and D-1548; L-0004 (check before showing), L-0019 (an erratum cannot widen a write-set).

## Pattern
A contract put new code in a module whose code accepted tests of earlier tasks pin by hash; the pinning tests were forbidden by the contract and its own criteria required every test to pass unchanged, so no code could meet it. The drafting, two review rounds and the approval did not see the pins; the first local suite run did.

## Occurrences
- **2026-10-21 (session 1d7a0412; D-1547).** TASK-069 (approved under D-1537) put session_violation in adapter.py; tests/unit/test_evaluation_violation.py and tests/unit/test_evaluation_repeated.py pin the SHA-256 of adapter.py's code after its docstring (TASK-053, TASK-054). TASK-069 ended on spec_conflict before any code commit; TASK-070 put the call in a new module after a read-only pin scan (D-1548).

One in session 2026-10-23-1555 (../History/2026-10/2026-10-23-1555-the-pages-d1960-to-d1964-task-076-landed-specification-2-revision-9-and-m5s-exit.md):
- **2026-10-23 (D-1975).** TASK-075 (contracted under D-1955) let `claude_code_shell_allow.py` name the project-state directory; `tests/unit/test_writer.py` R8 pins the exact set of modules allowed to do so, and neither the contract nor its two review rounds named it, although the CI channel's revision 12 had been changed for that module. The first local suite run in the clone found it, before any code commit; TASK-076 put R8 in its write-set (D-1979).

One in session 2026-10-23-1555 (../History/2026-10/2026-10-23-1555-the-later-part-4-task-078-the-mcp-servers-frame-and-its-status-tool.md):
- **2026-10-23 (D-2109).** TASK-078's plan ran a read-only pin scan before drafting, as this lesson asks, but its findings named R8 and the hook lists and missed the three tests of `tests/unit/test_writer.py` that fix where new writer code may stand (R14 at :860-880, R20 at :1694-1737 and TASK-067's marker test); the decision agent accepted the scan without them (D-2106). Both contract reviews found them before commit C (blocking); revision r1 placed the new function above the TASK-066 marker and named the three pins. A scan by patterns finds the lines; reading which of them constrain the planned change is the step that was missed.
- **2026-10-31 (../History/2026-10/2026-10-31-1018-m8-stage-8-task-107-the-shared-resolution-of-a-task-contract-s-path.md, D-4035 to D-4037).** TASK-105's pin scan covered the module's own tests and the hook lists but not another task's test on the changed module's own imports: tests/unit/test_resume_inputs.py (TASK-085 AC7) pinned base_inputs.py's imports and used attributes and was found only by the full run; it was outside the write set.

## Why it happens
Reviews and drafts read the module to be changed and the tests of that module, not the tests of other tasks that guard it; a hash pin lives far from the module it guards.

## Prevention and detection
- Before a contract's first draft: a read-only scan of tests/ and the workflow for the module's file name, hashes, import-set checks and package enumerations; its output goes with the draft to the decision agent and to at least one reviewer.
- A reviewer lens names "every existing test that pins or enumerates the changed modules".
- The suite runs locally in the scratch clone before the first code commit, under the compile step.
