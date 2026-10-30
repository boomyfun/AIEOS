# DEF-0113: TASK-104's docstring wording and the echo of logged text

- Status: open
- Opened: 2026-10-30 (session 578ea88b; TASK-104's acceptance, D-3892)
- Deferred by: decision agent (A41, A51), the acceptance decision of TASK-104 (D-3892)
- Decision group: A

## What
Findings of the acceptance review of TASK-104 (a Haiku 5.5 reviewer, D-3890) that change no behaviour and were not fixed in a second task commit:
- (a) `launcher.run_task`'s docstring says each step's name is the reason of a refusal or a raise at it (`src/aieos_bootstrap/launcher.py` :1720-1722). A raise in the dry run of `eventlog.append` gives the reason "log", because the step variable is not changed (`:1753`, `:1782-1784`); the same was already loose for the steps "exists", the class and the intent's id and claim. The test `test_a_raise_in_the_dry_run_gives_log` pins the behaviour; only the sentence is loose.
- (b) The docstring of `tests/unit/test_cli_import.py` `test_this_test_file` (`:612-615`) reads "is longer than it other than the root", a broken phrase; the pin at `:625-627` collects string constants that start with 'C:/' and are longer than 3 characters, and requires the set to equal {ROOT}.
- (c) The finding of `_run_conflict` (`launcher.py` :1685-1687) says "the subject alone can cause this"; it reads as a hint even when no claim of the record_id exists in the log (a line under the claim event id that run never writes).
- (d) The same finding echoes the logged subject and recorder unescaped into one output line; a newline in a stored recorder (a hand-edited or foreign log line) would split the line. Presentation only; the refusal itself is unchanged. A fix would be a one-line filter or `repr` of the logged strings.
- (e) The module docstring's clause "because run_task takes the first claim ... leaves no trace in the log" (`launcher.py` :183-184) is a loose causal clause.

## Why deferred
Each is wording or presentation; a docstring-only task commit would cost a new CI run, a new review and a new push for no change in behaviour (D-3890). The echo (d) is the only item with an effect, and only on a log line that the CLI does not write.

## Resume when
The next task that changes `launcher.run_task` or `launcher.import_task`, or when a stored recorder or subject with a newline is seen in a real log.

## Depends on
TASK-104; DEF-0105.

## Log
- 2026-10-30: opened at TASK-104's acceptance (D-3892).
