# L-0019: An erratum cannot widen a write-set

Rule: An erratum cannot add write-set paths: G0 reads the write-set only from the commit that adds the contract; a wider write-set needs a new contract (D-776).

- Status: active
- Category: verification
- Binding: record only. Related: decisions D-359 (G0 reads a contract only where it is added), D-774, D-776 (C5); L-0004 (check before showing).

## Pattern
A contract conflict found during the code is fixed by an erratum that adds paths to the write-set, and the task's commit then touches paths that G0 scope does not see in the contract.

## Occurrences
One in session 2026-10-15-0830 (../History/2026-10/2026-10-15-0830-the-benchmark-workflow-accepted-and-on-main.md):
- **2026-10-15 (D-774 to D-776).** Erratum E2 to TASK-038 added two earlier tests to its write-set; the first task commit 7c6596a0 failed CI run 255 only in G0 scope ("path outside the write-set" for both); TASK-039's contract, with E1 and E2 written into its text, superseded TASK-038.

One in session 2026-10-23-1555 (../History/2026-10/2026-10-23-1555-the-pages-d1960-to-d1964-task-076-landed-specification-2-revision-9-and-m5s-exit.md):
- **2026-10-23 (D-1979).** The missed R8 pin of TASK-075 (L-0026) needed `tests/unit/test_writer.py` in the write-set; G0 reads the contract only at its adding commit 6eb56b29, so TASK-076's contract, with TASK-075's content and the wider write-set, superseded TASK-075 before any code commit.

## Why it happens
An erratum is a recorded reading of a contract; the CI's G0 step reads the contract's bytes at the commit that added them, and no erratum reaches it.

## Prevention and detection
- Before an erratum, check whether it changes what G0 reads (the write-set, the forbidden list, the base); if it does, a new contract is needed.
- Run G0's own parse and scope logic locally over the contract and the planned paths (tools/g0_local39.py in session d8eb2eb5) before the first push.
