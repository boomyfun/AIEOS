# DEF-0128: stale line citations and comments after the pin upgrade of src/aieos_bootstrap/resume_check.py (TASK-122)

- Status: open
- Opened: 2026-11-05 (session 43f86835-8e74-41ad-8a42-ea9e67c52d9b; TASK-122, decision D-5024 C6)
- Deferred by: decision agent (A41, A51), D-5024 (the two entries of this records commit)
- Decision group: A (self-build)
- Blocks v0.1: no (stale citations and comments after the pin upgrade; no behaviour)
- Scheduled in: M8, the CI workflow revision task (each change its own A66 decision), before the M8 exit review

## What
TASK-122 (L 837f4ec3778ee09b9beabf1d38bcd5b564bf27e8, accepted at D-5016) removed the import line and one blank line from src/aieos_bootstrap/resume_check.py, so every line of that file after line 41 now sits 2 lines higher. These texts were outside the contract's write set and stay as they were, and are now stale:

- src/aieos_bootstrap/claude_code_channel.py:23 cites `resume_check.py:290, :405`, and tests/unit/test_claude_code_channel.py:307 pins the cited text `resume_check.py:290`.
- docs/specs/conformance-files.md:133 cites `resume_check.py:731`, and docs/specs/spec-07-cli-and-zero-friction-path.md:49 cites `resume_check.py:529`.
- .github/workflows/aieos-checks.yml:177 says "Set by revision 6 to the version accepted by decision D-363 (the file at commit 99cd8c5c)" above the pin value that TASK-122 changed; the comment still names the old version's decision.
- tests/integration/test_ci_resume_pin_logic.py: the docstring of test_the_env_line_and_its_comment (:84) begins "TASK-121 AC1 and AC6: the pin line is as before"; the pin line is no longer as before. TASK-122 AC2(c) allowed one wording change in that docstring, and the rest stays.

## Why deferred
The contract of TASK-122 forbade these paths (src/aieos_bootstrap/claude_code_channel.py, tests/unit/test_claude_code_channel.py, the whole docs folder) and allowed in the workflow only the two value lines; a comment is not a value line. The test tests/unit/test_claude_code_channel.py pins the cited text `resume_check.py:290`, so changing that citation is a change of a test as well.

## Resume when
A task whose write set covers these files changes the citations and the comments, reading the new line numbers from the then-current file (they are not stated here, so that this entry does not become stale in its turn), and records the change; the part under docs/specs follows that spec's own change rule.

## Depends on
TASK-122; DEF-0129 for the workflow file (the same file changes there under A66, each change its own decision).

## Log
- 2026-11-05: opened (session 43f86835), in the records commit of TASK-122 (decision D-5024 C6).
- 2026-11-06 (session 43f86835): the docstring of test_the_previous_value_line_and_the_two_pins says the previous value Q is 64 lowercase hex digits; since TASK-123 the workflow value is empty and the test checks only the constant OLD_PIN (found by the TASK-123 way-2 reviews, decision D-5053; the contract keeps that line byte for byte, so the stale statement is recorded here and the status stays open).
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass E decision D-5258): read in full; the Resume-when event (a task whose write set covers these files) is not met; the workflow comment part goes with the CI workflow revision task, the citations in claude_code_channel.py and its test with the Claude Code hook fix task's next change of those files. State: open; Blocks v0.1: no (stale citations and comments after the pin upgrade; no behaviour); Scheduled in: M8, the CI workflow revision task (each change its own A66 decision), before the M8 exit review.
