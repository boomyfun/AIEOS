# DEF-0077: interpreter entries in the Claude Code adapter's shell allowlist

- Status: open
- Opened: 2026-10-18 (session dfcb097a; decision D-1223)
- Deferred by: decision agent (A41), D-1223, after the way-2 re-review of TASK-061 (R5's ruling (b)).
- Decision group: A (an input to CC-2's contract); B for any install or setting.

## What
- TASK-061's judge (src/aieos_bootstrap/claude_code.py) matches each simple command against the caller's allowlist (specification 5 section 11 point 6). An entry for a program that runs code (bash, sh, powershell, cmd, python, a script) admits whatever that code does, a push built from parts included; the module states this as a limit and cannot see inside the program.
- To decide in CC-2 (the channel and the hook entry): forbid bare interpreter entries in the allowlist the adapter is given, or admit them only with fixed arguments, and say how the allowlist is set and checked.

## Resume when
- With CC-2's scope, or the owner's word.

## Log
- 2026-10-18: opened (session dfcb097a; D-1223).
