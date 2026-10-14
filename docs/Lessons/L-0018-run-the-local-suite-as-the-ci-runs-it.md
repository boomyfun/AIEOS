# L-0018: Run the local suite as the CI runs it

Rule: Before any local test result is brought as evidence for a push, run the suite under the CI's own preparation steps (at least the G1 build step's compiling of src and tests), not only the test command.

- Status: active
- Category: verification
- Binding: record only. Related: decision D-470 (C5); L-0004 (check before showing); L-0007 (never a proxy as proof).

## Pattern
A local run of tests/run_tests.py is taken as the same evidence as the CI's test steps, although the CI prepares the checkout first and the local run does not.

## Occurrences
One in session 2026-10-11-1439 (../History/2026-10/2026-10-11-1439-fixture-contract-on-main-and-fixture-reviewed.md):
- **2026-10-11 (:1090 to :1208).** TASK-018's suite passed locally ("Ran 592 tests", OK) and CI run 129 failed in unit_test and integration_test: the workflow's G1 step compiles src and tests, which puts a `__pycache__` folder in the new fixture folder, and two tests listed every entry. Reproduced by compiling a clean clone first; fixed in the second commit; run 130 passed.

Occurrences in session 2026-10-15-0229 (../History/2026-10/2026-10-15-0229-the-scope-drift-caller-accepted-and-on-main.md):
- **2026-10-15 (D-717).** The local checks before TASK-034's first push ran the suite on a compiled tree, the naming and text scans and the deterministic_rule and OPS-003 rules, but not bandit; the branch's CI run 233 failed only its bandit step (B324, hashlib.sha1 in the test stand-ins), fixed in a second commit. Proposal, for its own decision (D-717 C4): run bandit locally, or an equivalent scan of the added lines for bandit's high-severity patterns, before a first push.

## Why it happens
The local run was treated as a proxy for the CI's run without checking what the CI does before its test command.

## Prevention and detection
- Compile the clone (SP/t018/compile_tree.py, the G1 step's effect) before the suite whose result goes into a push request.
- When a test lists a folder, expect build artefacts in it.
