# DEF-0095: the handoff file of the claim tools, for the launcher

- Status: open
- Opened: 2026-10-24 (session 308d8b07; decisions D-2131 and D-2134 and the acceptance decision of TASK-079, D-2161)
- Deferred by: decision agent (A41, A51), D-2131 (the handoff file outside TASK-079) and D-2161 (TASK-079's acceptance).
- Decision group: A (a task of specification 7, M7, the launcher's).

## What
TASK-079 (the MCP server's four claim tools) records a handoff as claim records at once, each with refers_to "handoffs/<task>-<session>.md#<list>/<n>", and writes no file. Specification 6 section 7 has the core write handoffs/<task id>-<session id>.md from those records, in their order, after the submission or the session's end without one, with `commit` when the session submitted one (specification 2 section 5.2). Closed by TASK-087 (decision D-3006): handoff_file.compose builds the file's text from those records in specification 2 section 5.2's form, and writer.write_handoff writes it create-only to .aieos/handoffs/<task>-<session>.md inside the project-state directory (INV-001; decision D-2979). Still open: nothing calls handoff_file.write but its tests, so the CLI frame's wiring after the launcher's end and after a submission is open; how the file reaches Git (which tree, who commits it, how it stays out of the agent's commit) and which handoff is "the last" for the Context Compiler's layer 5, whose reader looks under docs/handoffs/ at the base (base_inputs.py), are open (specification 6 section 11 point 6); abnormal ends and crashes write no file.

## Why deferred
D-2131: the file is written after the submission or the session's end, which the launcher makes (specification 5 :112; specification 7); TASK-079 builds only the in-session tools.

## Resume when
With the CLI frame's task that wires handoff_file.write after the launcher's end and after a submission; this item closes when the file is written in a real session, reaches Git by a stated rule, and the Context Compiler reads it as "the last handoff".

## Depends on
TASK-079 (the handoff's claim records); specification 6 section 7 and section 11 point 6; specification 2 section 5.2.

## Log
- 2026-10-24: opened (session 308d8b07; TASK-079's acceptance, D-2161).
- 2026-10-25: TASK-087 accepted (decision D-3006): the file's composing and create-only writing closed; its wiring, its way into Git and its reader stay open (session ea6ea0a3; decisions D-2970, D-2979, D-3006).
