# DEF-0037: TASK-014's non-blocking review findings in the conformance-file tests

- Status: open
- Opened: 2026-10-10 (decision file D-386)
- Deferred by: decision agent (A41, A51), D-386 (TASK-014 accepted with these recorded, no fix in that task).
- Decision group: A (test code within the self-build).

## What
- The two altered-set cases TASK-014 added to tests/unit/test_conformance_files.py ('a Resume Check fixture at the Verification folder', 'a Verification fixture at the Resume Check folder') also give an error because the moved path is missing from the files map, so they do not isolate the path rule; the base case 'a fixture path' has the same property. Reviewers suggested asserting the error text, or adding the moved path to the files map.
- The comment in tests/integration/test_conformance_set.py's Resume Check branch names test_conformance_rc_set.py where the Resume Check form is checked mainly by test_conformance_rc_files.py.
- The module docstring of tests/integration/test_conformance_rc_set.py still describes what TASK-005 left unchanged.
- The two rewritten tests of test_conformance_rc_set.py keep their base names (test_the_set_file_is_unchanged_and_frozen, test_the_set_names_no_resume_check_fixture), which describe the earlier state; a rename would be tidier.
- Recorded only: TASK-014's commit message says the three set-test modules gained the two wrong-folder cases, while only test_conformance_files.py did; the freeze test binds to the record in the same tree.

## Why deferred
D-386: none weakens a check; a fix would have meant a second task commit, a push, a CI read and new reviews for comments and an error's isolation that the base also lacked.

## Resume when
The next task that changes any of these test modules.

## Depends on
TASK-014 accepted (done, D-386).

## Log
- 2026-10-10: opened (decision file D-386).
