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

One occurrence in session ea6ea0a3 (the History of that session):
- **2026-10-25 (D-2941 to D-2944).** TASK-090's first code commit fa324e53 passed every local run, but its CI run 40144226012 failed only its bandit step: B608 read a test helper's INSERT built with "%" as string-built SQL. Fixed in 0fbde1ed by executemany with "?". The proposal of D-717 C4 was still not in the steps: before commit X, grep the added lines for bandit's patterns (B608: SQL built with % or format or +; B105: password-like constant names), as a proxy (L-0007), the CI's bandit run staying the evidence.
- **2026-10-31 (../History/2026-10/2026-10-31-1018-m8-stage-8-task-107-the-shared-resolution-of-a-task-contract-s-path.md, D-4053).** A test pinned a SHA-256 of `ast.dump` of the hook module; it passed on the author's Python 3.14 and failed on the runner's 3.12 (aieos-checks run 41181364463). Prevention added: a pin on a syntax tree's dump is not portable; pin a digest of the text (the source lines without the docstring line ranges) or run the suite on the CI's interpreter before the push.
- **2026-11-01 (../History/2026-11/2026-11-01-1050-m8-stage-8-task-111-and-task-112-the-handoff-write-and-the-metrics-report.md, D-4335; mine).** TASK-111's code commit X was pushed without a local bandit run and without the scan of the added lines for the form that bandit flags (B105 and B106: a string literal given to an argument named for a token), and its composed test had never run on Linux, because all local runs were on Windows; the CI run of X was red for those two reasons (checkpoint line 170); Y fixed both. The lesson already held the rule ("Before commit X, scan the added lines for bandit's B608 and B105 forms", its Prevention section, from D-717 C4 and D-2941 to D-2944); the scan was not run (checkpoint line 170); this is the third bandit recurrence (D-717, D-2941 to D-2944, D-4335): the prevention line was in the file but not in the checks run before commit X (the checkpoint's list of H inputs calls it an L-0018/L-0007 recurrence, line 289). Added: the request for a code commit shows the raw output of that scan; a test that touches a platform path and has run only on Windows is named as not verified on Linux, with the CI run as its first evidence.

## Why it happens
The local run was treated as a proxy for the CI's run without checking what the CI does before its test command.

## Prevention and detection
- Compile the clone (SP/t018/compile_tree.py, the G1 step's effect) before the suite whose result goes into a push request.
- When a test lists a folder, expect build artefacts in it.
- Before commit X, scan the added lines for bandit's B608 and B105 forms; a hit is fixed or named before the push.
