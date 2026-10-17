# L-0023: Do not chain a check into each command; let the software run it

Rule: Never make a check a prefix that every command must chain before its real work; run it as a hook that the software calls before each tool call, and expect that installing it needs the owner's (or user's) own permission and that it may not fire for every tool until measured (D-1200, D-1203).

- Status: active
- Category: tooling
- Binding: record only. Related: decisions D-1173, D-1178, D-1185 (the call form), D-1200 to D-1203 (way B); DEF-0073; DEF-0076; L-0010 (respect harness guards).

## Pattern
A guard is put into the command text itself ("cd <folder> && bash <check> && <command>"), so every command depends on a script the safety layer cannot see; the safety layer refuses the commands, labelled "[Auto-Mode Bypass]", likely because it reads the form as a way around itself (its reasoning is not shown).

## Occurrences
One, in session 2026-10-17-2011 (../History/2026-10/2026-10-17-2011-way-b-installed-and-the-claude-code-adapters-first-part-coded.md):
- **2026-10-17 (D-1200).** The start's third command in the call form was refused twice by the auto-mode classifier, "[Auto-Mode Bypass]" (:45, :56); no Bash could run until the owner chose way B (:103) and installed the hook (:299, :325).

## Why it happens
The call form grew session by session as a mechanical guard against slips (D-1173, D-1178), before a hook that worked existed (DEF-0073); in session 1947b313 the safety layer refused the form, which earlier sessions had run; whether the layer changed or why it refused is not known (its reasoning is not shown).

## Prevention and detection
- Put checks in hooks, installed by the owner; keep commands plain, two steps in a script file.
- When a design for users' machines needs a guard, plan it as a hook with the user's permission, and test whether it fires for each tool (DEF-0076).
