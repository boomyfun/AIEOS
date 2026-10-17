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
- 2026-10-18: added (session 3d8844e1; D-1231): besides interpreters, entries for git with any arguments (git -c with help.autocorrect, or a setting that runs a program), xargs, find with -exec and timeout admit whatever they run; CC-2 checks every entry against the safe set and refuses an entry holding any whitespace other than a space (TASK-061's split treats other Unicode whitespace in an entry as a space). TASK-062's outline takes this as its AC4 (D-1236).
- 2026-10-18: noted (session 89ad39be; D-1244, D-1247): TASK-062's allowlist form check refuses a minimum of first words, script suffixes and git forms (its AC4); names outside those lists that run code still pass and are named in the module's docstring: other interpreter names and versions (python3.12, pythonw, iex, Invoke-Expression, source, ".", wscript, cscript, mshta, bun), other script suffixes (".vbs", ".jar"), a name with a trailing dot or space, and git options after the subcommand (git log --output=); to be decided with the next allowlist contract.
