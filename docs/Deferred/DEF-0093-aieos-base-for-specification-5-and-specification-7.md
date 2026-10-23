# DEF-0093: AIEOS_BASE for specification 5's next revision and specification 7

- Status: open
- Opened: 2026-10-22 (session d12e7fb6; TASK-072's contract, D-1701 M2, D-1703 C2; decision D-1733 for G-8)
- Deferred by: decision agent (A41, A51), at TASK-072's acceptance, as the contract's records obligation (TASK-072.yaml :169-171, AC11).
- Decision group: A (a revision of specification 5 and the drafting of specification 7, each approved in its own decision; nothing here is placed or measured).

## What
- **The proposal.** TASK-072's hook reads the lease task's contract at the commit given by the launcher in the environment variable AIEOS_BASE: the tip of the base branch (main for the self-build) at the grant, written as 40 lowercase hexadecimal characters, never the contract's own input_state.base_commit. This goes beyond specification 5 :108, which names only the session id and the project root as what the launcher passes; specification 5's next revision should carry it, and specification 7 (the launcher) should set it with the session id and the root at the grant.
- **What happens without it:** a launcher that sets only the session id and the root makes every leased session STOP at its first judged call (the contract read as not readable at the base).
- **The base is fixed at the grant:** main moving during a session is not seen (specification 3 :180).
- **G-8 of round t72g, stated (decision D-1733):** the hook cannot show that AIEOS_BASE is the tip of main, nor that the root and its Git state are untouched by the change; a nested runtime chooses its own session id, root and base (specification 5 :115's limit extended to the base); there is no check 0 of the contract against the approved one (specification 3 :175). So the hook's inputs meet GOV-003's rule by assumption on the launched path, and not against a nested runtime, an agent-set base or root, or Git state the agent controls. Its fix needs specification 7's launcher.

## Resume when
- With specification 5's next revision, the drafting of specification 7, a contract that places or wires the hook, or the owner's word.

## Log
- 2026-10-22: opened (session d12e7fb6; TASK-072's acceptance).
- 2026-10-23: specification 5 revision 5 already carries AIEOS_BASE as proposed text (section 11 point 7); its citations of claude_code_pretool_hook.py at section 11 points 6 and 7 (:63-65, :66-67) are stale since TASK-074 changed that module's docstring (the right lines on main are :67-70), for specification 5's next revision (review finding s2r8 R2-5, carried by D-1933 C3); the launcher half stays with specification 7 (session 58b6a0c7).
- 2026-10-23: specification 5 section 11 point 6's text, not only its citations, is stale: it leaves the shell allowlist's source and reading to specification 2's next revision and a later contract, which specification 2 revision 9 section 7.2 and TASK-076 have settled; for specification 5's next revision (review m5x-R1 of the M5 exit review; session 308d8b07).
