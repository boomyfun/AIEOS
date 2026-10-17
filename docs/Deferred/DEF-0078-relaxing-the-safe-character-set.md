# DEF-0078: relaxing the safe character set of the shell checks

- Status: open
- Opened: 2026-10-18 (session dfcb097a; decision D-1223)
- Deferred by: decision agent (A41), D-1223 (F9).
- Decision group: A for a design proposal; B for any live measurement in a Claude Code session (C6, the owner's).

## What
- TASK-061's F9 lets a shell text reach the allowlist only if every character is an ASCII letter or digit, a space, a tab, a newline or one of - _ . / : = , + ; & | ( ). It over-refuses heavily: no quoted argument (git commit -m "x"), no redirection, no "2>&1".
- It replaced three rounds of form-by-form rules (substitutions, escaped quotes, comments, typographic quotes, here-documents), each round finding a new text that the split and bash or PowerShell read differently (L-0009's occurrence of 2026-10-18).
- Any relaxation, for example single-quoted words whose content is itself in the safe set, comes only with a measured run of both shells over the forms found so far and its own decision.

## Resume when
- When CC-2 or a user's allowlist needs quoted arguments, or the owner's word.

## Log
- 2026-10-18: opened (session dfcb097a; D-1223).
- 2026-10-18: noted (session 3d8844e1; D-1231): F9 is unchanged at TASK-061's acceptance; the contract's own capabilities entry "timeout 110 python tests/run_tests.py < /dev/null" can never match under F9 ("<" is outside the set); TASK-062 takes F9 unchanged (D-1236).
