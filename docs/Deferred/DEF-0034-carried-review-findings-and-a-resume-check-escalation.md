# DEF-0034: TASK-011's carried review findings and TASK-008's escalation

- Status: open
- Opened: 2026-10-10 (decision files D-349, D-351 and D-352)
- Deferred by: decision agent (A41), D-349 (the dispositions of TASK-011's way-2 findings) and D-352 (TASK-008 carried whole with a ruling).
- Decision group: A (task contracts and readings within the self-build; a specification revision under A51, B9, for F-a).

## What
- **F-a (TASK-011's way-2 R1, R2, R5):** records.check_decision lets a fired check of an execution decision record carry the outcome CONTINUE, while outcomes_fired refuses CONTINUE, and nothing ties the fired checks to outcomes_fired. This follows TASK-011's AC2 text ("an execution decision value when status is fired"). TASK-008's contract says which outcome a fired check carries; specification 3's next revision may state the tie.
- **F-d (TASK-011's way-2 R2):** the property module of TASK-011 corrupts each checked key coarsely and takes its expected sets from the module's own constants; the unit tests pin the finer cases. For a later task that touches records.py's tests.
- **TASK-008's escalation (D-352):** with resume_check.py in the tree, the existing test `test_runner_rc_run.R7RepositoryTree.test_with_no_resume_check_the_eleven_are_not_run` cannot pass, while AC9 lets only one assertion of that module change. Ruling: an erratum reading of AC9 (D-337's shape): test R7 may change only by adding context that makes the import of aieos_bootstrap.resume_check fail with ModuleNotFoundError for that one test, every existing line byte-equal, shown by a script diff; the dependence of the module's :126 assertion on test order shown safe or fixed within the same limits; the erratum cited in the acceptance and checked by the reviewers. The draft's placeholder subject "TASK-0" for an error record with a malformed task id is not approved: it comes with AC6 and AC7's text in the branch push request, and unless the contract allows it, it is a spec_conflict under AC7.

## Why deferred
D-349: F-a and F-d meet TASK-011's contract text; changing them is the business of TASK-008 or the specification revision. D-352: at 63.9% of the session's context, TASK-008's ruling, checks, push, CI and reviews could not reach acceptance in the session's bands.

## Resume when
TASK-008's code in the next session, from the draft archived with session 2c78123d's scratchpad (t008c/), under D-352 C3 and C4; F-a also at the next revision of specification 3.

## Depends on
TASK-011 accepted (done, D-351).

## Log
- 2026-10-10: opened (decision files D-349, D-351 and D-352).
- 2026-10-10: TASK-008's part done: TASK-008 accepted and on main with its AC9 assertion, decision D-352's and D-359's errata and the subject "TASK-0" stated by decision D-359 (decision D-363); F-a and F-d stay open.
- 2026-10-11 (session 22aadea0): the "Resume when" above names TASK-008's code, which is accepted (decision file D-363); TASK-008's escalation was settled there. F-a and F-d stay open, for the next revision of specification 3 or the next task that changes records.py or its tests (D-415 C3). ../History/2026-10/2026-10-11-0220-decision-files-d399-d408-the-writer-and-m3-exit.md
