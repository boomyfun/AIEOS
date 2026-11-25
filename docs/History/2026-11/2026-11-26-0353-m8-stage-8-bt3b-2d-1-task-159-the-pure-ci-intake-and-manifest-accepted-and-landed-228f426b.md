# Session 2026-11-26, twelfth stretch (UTC+7, D-7109 to D-7154): M8 stage 8, the owner's answers recorded, and BT3b-2d-1 = TASK-159 (the pure CI intake and the manifest): contract landed, built, reviewed, accepted, landed on main and CI accepted

> - **Status:** working record, non-authoritative; written by Claude from the checkpoint file and the decision files; a claim, not evidence. Owner decisions are in `docs/pre-genesis/decision-matrix.md` (DM). The acceptance of TASK-159 is the decision agent's (D-7150) and the evidence is same-lineage, not independent.
> - **Session and transcript:** session `228f426b-33cd-4e2a-bb1d-86cdfeccd36d`, the continuation of `0be70981-5509-45c7-8aef-d99c1e965c5a`; the worker's checkpoints are in `AIEOS-REG0-lite/checkpoints` (the file named by the session id).
> - **Models:** the main session `claude-sonnet-5-5` (the worker, as the app states it; no scan of all transcripts was run for this page); every decision-agent instance recorded by script `claude-opus-5-5`; the reviewer runs of TASK-159 `claude-haiku-5-5` in their own sessions with read-only tools (D-6206: never Fable).
> - **Dates:** all times are UTC+7.
> - **Repository:** at the start of this stretch main = origin/main = a20ed449fd17ab2592eab4c19feaf19a50c790ab; the records of the owner's answers landed as 6f27bdc76ef0ef15077bddb4522469c55b9247ea; the TASK-159 contract as f1fec8a4d698a5f88ef4c33672033578c09c0926; the task as 0772a67e92eefac469f59af7d8a7defaa71bf177; main = origin/main = 0772a67e92eefac469f59af7d8a7defaa71bf177 after the landing.

## Summary

- **The owner's answers:** DM rows A81 and A82 and log lines of DEF-0153 and DEF-0154 landed as 6f27bdc7 (D-7109 to D-7116); the owner's question about deleting the local branch records/TASK-155 was asked (D-7116) and is open.
- **The plan of BT3b-2d:** every run-made contract is refused before evaluation (empty traces_to and intent_versions); the fix reads versions from the decision matrix (D-7118, D-7119, DEF-0156); the order is 2d-1, 2d-3, 2d-2.
- **The task:** TASK-159 (risk high): src/aieos_bootstrap/evaluation_intake.py with read_ci_data and manifest (50 tests), eligible_run in ci_evidence, parse_json refuses a lone surrogate, one entry more in EVIDENCE_DEFINING_PATHS (seventeen). Nine paths.
- **The contract:** drafts v1 to v7 with Haiku 5.5 draft reviews; the five expected base-test failures predicted on scratch clones (D-7120 to D-7127); landed with its CI accepted (D-7128 to D-7134).
- **The build:** in a scratch clone; a Haiku 5.5 draft review gave BLOCK on the build and it was fixed (D-7139); the task commit was made in a second scratch clone and its diff matched the reviewed diff section by section (D-7141, D-7142).
- **The landing:** the task branch was pushed (D-7144), its CI matched 7 of 7 items (D-7146), the review pair gave APPROVE (Haiku 5.5) and APPROVE (decision agent, D-7149), the task was accepted (D-7150), main was fast-forwarded (D-7151) and pushed (D-7152), and the main CI matched 6 of 6 items (D-7154).
- **Departures recorded:** the base tests against the head tree were not run again on the final bytes before the commit (D-7150); the expected shape of the main run was written after the push (D-7153).
- **Route slips (the worker's):** a path too long in a scratch commit (D-7111); a Co-Authored-By trailer against D-6473, caught before its push (D-7112); texts for the owner not relayed in time (D-7125); refusals by the owner's guards (D-7117, D-7121, D-7136, D-7142, D-7147), nothing refused was redone in the same form; a literal that a whole-repo test refuses and literal non-ASCII characters in the build, fixed (D-7137, D-7138); a wrong range value, corrected (D-7140).

## Open

- The records commit of TASK-159 (this page, the acceptance text, log lines, lessons) and its push.
- BT3b-2d-3 (the mapper), 2d-2 (`aieos evaluate`, the append), the G3 task of DM A82, BT5; the second real run only when the owner says so; DEF-0136, DEF-0152, DEF-0153, DEF-0154, DEF-0155 and DEF-0156 stay open.
- The session's closing writes (memory update, next prompt) are not done at the time of this page.
