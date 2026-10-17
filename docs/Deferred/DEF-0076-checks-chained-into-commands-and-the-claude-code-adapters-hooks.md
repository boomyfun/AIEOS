# DEF-0076: checks chained into commands, and what the Claude Code adapter's hooks must expect

- Status: open
- Opened: 2026-10-17 (session 1947b313; decisions D-1200 Q4, D-1205 Q3)
- Deferred by: decision agent (A41), D-1200 Q4, after the owner's "đồng ý theo đề nghị" (:101).
- Decision group: A (inputs to a contract of M5); B for any install or setting.

## What
- The self-build's call form, which chained a check script into every Bash command, was refused twice by Claude Code's auto-mode safety classifier ("[Auto-Mode Bypass]", session 1947b313 :45, :56). The owner chose to run the check automatically before each command instead (way B, :103), now a PreToolUse hook.
- The question for the part of AIEOS that runs on users' machines (master-plan.md:69; specification 5 section 6): it must not chain checks into commands. As planned it uses hooks, which is the supported form, but the live session also showed:
  - installing hooks and changing settings needs the user's own permission at each step; the classifier refused a Write into the hooks folder in auto mode, and flagged reports that named settings;
  - a hook may not fire, or not refuse, for every tool: a PreToolUse hook with matcher "*" did not refuse a Read it was written to refuse, twice (decisions D-1202, D-1203); specification 5 line 80 already says a hook that does not fire neither refuses nor records, and point 8 (line 105) leaves the tool coverage to the first contract that builds the adapter.
- These are inputs to CC-2 (the channel and the hook entry) and CC-3 (install and measurement, the owner's), not decided here.

## Resume when
- With CC-2's scope, or the owner's word.

## Log
- 2026-10-17: opened (session 1947b313; D-1200, D-1202, D-1203, D-1205).
