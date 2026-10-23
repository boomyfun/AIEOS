# DEF-0094: the session sentences left stale by TASK-077

- Status: open
- Opened: 2026-10-23 (session 308d8b07; decision D-2061 and the acceptance decision of TASK-077, D-2089)
- Deferred by: decision agent (A41, A51), D-2061 (the stale sentences left, each resumed at its module's next text change) and D-2089 (TASK-077's acceptance).
- Decision group: A (a text change of each module and of tests/unit/test_t0.py, in a task of its own or with the module's next change).

## What
TASK-077 (the record checker accepts the keys session, acs and text) made records.py accept a `session` key, so three sentences that say it has none are no longer true; they were left by decision D-2061, outside TASK-077's write-set:
- src/aieos_bootstrap/t0.py :48: "The session is named only in the recorder's words, since records.py has no ``session`` key (specification 2"; tests/unit/test_t0.py :359 pins it and changes with it.
- src/aieos_bootstrap/claude_code.py :77: "session only in the recorder's words (records.py has no ``session`` key)."
- src/aieos_bootstrap/claude_code_channel.py :18-19: "specification 2 revision 6 keeps no session key on a record (section 6.2)".
What each module does is unchanged: none of them writes a `session` key, and naming the session in the recorder's words stays allowed.

## Why deferred
D-2061: the modules are outside TASK-077's write-set; a text change of each belongs with its next change, with its pins.

## Resume when
With the next text change of t0.py (and test_t0.py :359), of claude_code.py, or of claude_code_channel.py, each for its own sentence; or a task that writes the `session` key from these modules.

## Depends on
TASK-077 (records.py's `session` key); DEF-0051 (what the key may count for).

## Log
- 2026-10-23: opened (session 308d8b07; TASK-077's acceptance, D-2089).
