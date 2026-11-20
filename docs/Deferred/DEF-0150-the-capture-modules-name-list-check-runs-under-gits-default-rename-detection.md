# DEF-0150: the capture module's name-list check runs under git's default rename detection, so a capture of a moved file would be refused after the ref is written; one reason word and the docstring are inexact (BT1a, TASK-147)

- Status: closed (2026-11-20, by the task TASK-149 on main at 34eb70ee: the commits fabad6c6 and 34eb70ee; the acceptance text docs/runs/TASK-149-acceptance.md, decided at D-6702)
- Opened: 2026-11-20 (../History/2026-11/2026-11-20-1640-m8-stage-8-bt1a-task-147-the-capture-module-accepted-and-landed-dc7cf6ca.md)
- Deferred by: decision agent (A41, A51), D-6658 (the item and its deadline), D-6659 (the vehicle), D-6660 (the acceptance of TASK-147)
- Decision group: A (scheduling)
- Blocks v0.1: no (nothing calls the module until BT1b); but the item must be fixed before any real call of capture, and at the latest before BT1b is accepted (D-6658 C3)
- Scheduled in: a separate small task BT1c, after the records commit of TASK-147 and before the contract commit of TASK-148; its CI revision 29 is its own decision under A66 and its own commit first (D-6659, D-6664)

## What
The module src/aieos_runtime/task_capture.py (on main since cf7842c5; accepted at D-6660) writes the listed paths of a work tree as one commit on a new task ref through a temporary index. After the ref is written it checks the commit with the pinned form `diff --no-ext-diff --no-textconv --name-only <old> <new>` (CAPTURE_FORMS, pinned by the workflow's check_capture, CI revision 28) and refuses with the reason name-list-mismatch unless the printed names are exactly the listed paths. Neither CAPTURE_OPTIONS nor CAPTURE_ENV_FIXED turns rename detection off.
Reading (from the two blind reviews A1 and B4 of TASK-147, expected and NOT observed; the AC5 harness has no such case): under git's default rename detection a listed deletion and a listed addition of near-identical content may print as one name, so a capture of a moved file would be refused as name-list-mismatch after update-ref has written the ref; a retry then reads ref-exists. It fails closed (a refusal, not a wrong commit), but a real session that moves a file would never be captured.
Two smaller items found by the same reviews: (1) a malformed commit or tree id that git itself printed is refused by the module's argument builder as invalid-argument, a word the contract reserves for validation before any process starts (review A3); it should be git-failed. (2) The module's docstring says the state-name rule "accepts any name that begins with a dot" while the code also refuses a lone dot and names with a slash or a backslash, and it omits the limits AC8 (13), (19) and (20) of the contract (reviews A2 and B1); two statements of the unit test's docstring overstate (review B10).

## Why deferred
The fix needs a change of the pinned diff form, which CI revision 28 pins; .github/** is forbidden in the contract of TASK-147, so the fix could not land inside that task. A third commit for the docstring alone would have cost a retry and a CI run for text in a module that nothing calls (D-6658).

## Resume when
After the records commit of TASK-147 has landed and its CI has been read and accepted (D-6664 R6). The route: (1) CI revision 29 (its own decision under A66 and its own commit) that pins the changed diff form (for example with `--no-renames`, or `-c diff.renames=false` in CAPTURE_OPTIONS; the choice and its reason come with the design); (2) the small task BT1c, with the write set src/aieos_runtime/task_capture.py and tests/unit/test_task_capture.py: the module change that disables rename detection in the diff form and maps a malformed git-output id to git-failed, and the docstring corrections of the items above in the same change; (3) the AC5 harness gets a case with a deleted and an added path of near-identical content.

## Depends on
TASK-147 (the acceptance record docs/runs/TASK-147-acceptance.md, decisions D-6658, D-6659, D-6660); CI revision 28 (c186685b); DEF-0149 (not on main; a draft exists outside the repository, in the scratchpad of session c0dc5bcc: DEF-0149-the-loops-submission-path-cannot-be-completed-after-a-session-that-has-no-shell.md); BT1b (TASK-148) calls the module and must come after this item.

## Log
- 2026-11-20: opened (session dc7cf6ca; decisions D-6658, D-6659, D-6660, D-6664, D-6665).
- 2026-11-20: closed (session dc7cf6ca): CI revision 29 (8ff21ea6, D-6672 to D-6679) pins the diff form with --no-renames; the task TASK-149 (contract commit ef36594d, D-6683) changed the module to that form (fabad6c6, D-6693, D-6694), refuses a malformed id that git printed as git-failed, corrected the docstring and the test wording, and gave the AC5 harness two cases with a deleted and an added path of the same and of near-identical content, each with a positive control; the harness showed the defect on the old module (4 expected FAIL, D-6692) and none on the new one (0 FAIL on the accepted head, D-6701); a second commit (34eb70ee, D-6699, D-6700) corrected two review findings; accepted at D-6702 (docs/runs/TASK-149-acceptance.md); landed on main at 34eb70ee (D-6703, D-6704; the CI of main read at D-6705).
