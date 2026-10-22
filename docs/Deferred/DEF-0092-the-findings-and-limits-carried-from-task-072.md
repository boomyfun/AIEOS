# DEF-0092: the findings and limits carried from TASK-072

- Status: open
- Opened: 2026-10-22 (session d12e7fb6; decisions D-1731 to D-1737 and the acceptance decision of TASK-072)
- Deferred by: decision agent (A41, A51), at TASK-072's acceptance, with the points ruled by decisions D-1731 (DA-1), D-1732 (DA-2), D-1733 (G-1 to G-9), D-1735 (round t72s) and D-1736 (DA-4).
- Decision group: A (a text and test change of src/aieos_bootstrap/claude_code_pretool_hook.py and its tests in a task of its own; G-1 to G-7 and G-9 a change under .github/, each its own A66 decision, or a separate decision for G-4).

## What
TASK-072 (H2b: the PreToolUse hook program of the Claude Code adapter) was accepted at its head fd80f2bf with these points carried, each non-blocking and failing closed:
- **N1 (D-1731):** two checks stricter than the contract (a lease task of the form TASK-<digits>; a "read" whose write_set is a non-empty list of str); stated in the docstring since the fix round F1.
- **N2 (D-1731):** the module uses claude_code_store.KEYS, claude_code_hook.RESULT_KEYS and claude_code_channel.RECORDER_JOIN, constants not in the contract's read_set.interfaces.
- **N3 and S1-6a (D-1731, D-1735):** "an input that is not bytes ... the entry then refuses it without a record" is true on the judged path only; on the bad-base and contract paths such an input still gets a record with the empty-bytes hash (main cannot reach it).
- **N4 and S1-6b (D-1731, D-1735):** the hook parses bytes(stdin) while the entry parses the object itself; bytes() honours a __bytes__ override (main cannot reach it).
- **N5 (D-1731; R2-4):** the seam check is lexical: importlib or __import__ with a concatenated string, and "import aieos_bootstrap as ab; ab.task_contract", pass it alone; the module is held by AC6's exact import set and deny set; stronger seam rules for a later task.
- **N6 and T6 (D-1731, D-1732):** round t72r-R1 read the diff only to its line 891; the tests and the pin edits were reviewed by t72r-R2 alone among the round t72r reviewers; round t72s read the final state, f1.diff included.
- **N7 (D-1731):** AC9's phrases are pinned with whitespace folded and case kept, not byte for byte.
- **T1 to T3 (D-1732):** the stdin-not-bytes and POSIX-root no_record cases do not assert that nothing reached the core; the ids test reaches some fallback inputs only through _ids; AC8's "arbitrary" holds for the input bytes, environments and folders coming from small fixed sets.
- **T4 and S1-4 (D-1732, D-1735):** the property module's docstring says "stand-ins only", while test_the_real_tie_over_folders runs the real store lookup over the host's folders (read only, host-dependent, not hermetic; D-1728 C4).
- **S1-1 to S1-3 (D-1735):** main's "which would let the call go ahead" is stated as fact while exit codes are cited and unmeasured; "about 50 seconds" counts the git calls only, not the store lookup's or the core path's waits; F1's parenthesis on the bad-base and contract paths for a non-Windows root is untested.
- **S1-5 (D-1735):** no test pins that the entry and the channel stay real in the property cases.
- **R-4 (D-1736):** claude_code_pretool_hook keeps copies of the store's refusal words (STORE_REASONS), of the judge's record form (_contract_record) and of the session id and task forms; native takeover (A11) carries or retires them with their sources.
- **The AC1 departures (D-1732), ruled sound:** the store refusals search, link and entry are shown by stand-ins only (no folder or link can be made in the writer's test modules); the tables subcase is compared by the store's full dump and the log, since writer.held_leases refuses that store.
- **GOV-003's gaps of round t72g (D-1733), each deferred:** G-1 (docs/tasks/** not in the pinned evaluator list; the hook and G0 read the contract on main); G-2 (the normative inputs not listed; a standing item, to be decided before the owner is asked to place the hook); G-3 (conformance inputs partly listed); G-4 (the runtime not pinned; no path list can pin it; a separate decision); G-5 (lockfile and configuration forms missing); G-6 (event logs outside docs/records/**); G-7 (the GOV-003 step only reports; "never auto-accepted" rests on the acceptance decision); G-9 (replace refs, grafts, alternates and an outer repository; a stated limit, no new defence). G-8 is carried by DEF-0093.
- **Round t72c and revision 4b (D-1705 C4):** t72c-R1c-1 to R1c-6 and t72c-R2c-1 to R2c-5 were applied into the contract text (revisions 4, 4b and 4c; D-1705); h4c Y2-10, Y5-7 and Y5-9 stay deferred without a reason of their own, their reasons not checked against h4c's dispositions.

## Resume when
- With the next text change of claude_code_pretool_hook.py or its tests, a contract that places or wires the hook (G-2 first), the next workflow revision (G-1 to G-7, each its own A66 decision), native takeover of the hook (R-4), or the owner's word.

## Log
- 2026-10-22: opened (session d12e7fb6; TASK-072's acceptance).
- 2026-10-23: G-2 closed by the CI channel's revision 9 (098fe9b4; decisions D-1795 to D-1798): docs/specs/risk-rules-gov-aieos.md and docs/pre-genesis/constitution.md added to GOV-003's pinned list, in both of its copies; the specifications the code only cites (governor-spec.md, assurance-model.md, spec-02 to spec-05) stay off it as a stated limit; G-1, G-3 to G-7 and G-9 stay open (session 4ad18bf8).
- 2026-10-23: G-1 closed by the CI channel's revision 10 (213bd8ba; decisions D-1801 to D-1803): docs/tasks/** added to GOV-003's pinned list, in both of its copies; limit: G0 still reads a contract only at its contract commit, and the report does not block a change; G-3 to G-7 and G-9 stay open (session 4ad18bf8).
