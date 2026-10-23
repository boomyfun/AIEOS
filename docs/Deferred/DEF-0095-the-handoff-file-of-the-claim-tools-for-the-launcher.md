# DEF-0095: the handoff file of the claim tools, for the launcher

- Status: open
- Opened: 2026-10-24 (session 308d8b07; decisions D-2131 and D-2134 and the acceptance decision of TASK-079, D-2161)
- Deferred by: decision agent (A41, A51), D-2131 (the handoff file outside TASK-079) and D-2161 (TASK-079's acceptance).
- Decision group: A (a task of specification 7, M7, the launcher's).

## What
TASK-079 (the MCP server's four claim tools) records a handoff as claim records at once, each with refers_to "handoffs/<task>-<session>.md#<list>/<n>", and writes no file. Specification 6 section 7 has the core write handoffs/<task id>-<session id>.md from those records, in their order, after the submission or the session's end without one, with `commit` when the session submitted one (specification 2 section 5.2). No code writes that file yet; how it reaches Git (which tree, who commits it, how it stays out of the agent's commit) and which handoff is "the last" for the Context Compiler's layer 5 are open (specification 6 section 11 point 6).

## Why deferred
D-2131: the file is written after the submission or the session's end, which the launcher makes (specification 5 :112; specification 7); TASK-079 builds only the in-session tools.

## Resume when
With specification 7's launcher (M7), or the first task that ends or submits a session and writes the handoff file.

## Depends on
TASK-079 (the handoff's claim records); specification 6 section 7 and section 11 point 6; specification 2 section 5.2.

## Log
- 2026-10-24: opened (session 308d8b07; TASK-079's acceptance, D-2161).
