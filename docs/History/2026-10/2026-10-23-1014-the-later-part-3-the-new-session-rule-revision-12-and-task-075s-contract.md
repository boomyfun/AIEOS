# Session 2026-10-23 10:14 (UTC+7), later part (3): the new session rule, the CI channel's revision 12, and TASK-075's contract

> - **Status:** working record, non-authoritative. Claude wrote it during this session. It is a claim, not evidence. Owner decisions are in `docs/pre-genesis/decision-matrix.md` (DM). Delegated decisions are in the decision files, kept outside the repository.
> - **Session and transcript:** session `58b6a0c7-c6ce-4dee-86b8-192110a4a65c`, after its records commit fb862ef7; its earlier parts are recorded in `2026-10-23-1014-the-pages-d1868-to-d1905-and-the-drafts-of-task-074s-records.md` and `2026-10-23-1014-the-later-part-task-074-landed-and-specification-2-revision-8.md`. A reference such as (:2871) is a line in its main transcript.
> - **Models:** the main session `claude-opus-5-5`; the decision agent on `claude-opus-5-5`, definition revision 13; reviews t75a-R1, t75a-R2, t75b-R1 and t75b-R2 on `claude-sonnet-5-5`; no Fable.
> - **Repository:** main fb862ef7 at the start of this part; the CI channel's revision 12 as fa4e4574 (CI run 39900775702 green); TASK-075's contract as 6eb56b29 (CI run 39902879441 green); this records commit.

## Summary

- **The new session rule.** A forked session relayed a proposal; the decision agent ruled that it reverses an owner rule and put it to the owner as one question (D-1939). The owner answered "có" (:2871). From then on Claude works on without stopping on its own context estimate, writes a checkpoint after each part (C:/Users/Admin/AIEOS-REG0-lite/checkpoints/58b6a0c7-c6ce-4dee-86b8-192110a4a65c.md, append-only), rereads it and the lessons after any compaction, and stops only on a system context warning with no checkpoint written (D-1940). Rule 11 of the rules book was amended in the owner's words, rule 10's "Still in force" line and the memory index line changed (D-1941, under A72, the owner told after); L-0027 and L-0012 gain their lines in this commit.
- **The archive:** the pages D-1936 to D-1941 written (D-1942); the notes and the clone l74 of this session archived, every file compared (D-1943); this session's scratchpad stays for the session's end.
- **The CI channel's revision 12 (D-1946 to D-1950; DM A66):** deterministic_rule lets exactly one new path, src/aieos_bootstrap/claude_code_shell_allow.py, name the project-state directory, with no module, no os name and no mode of open; every other rule unchanged. Committed as fa4e4574 and pushed; its run on main green.
- **TASK-075's contract (D-1944, D-1945, D-1951 to D-1958):** the shell allowlist reader, M5's last open element: a new module reads the policy's `shell_allow` and the contract's `capabilities.shell.allow` at the base from Git objects, each by a fixed grammar that fails closed, checks each with the accepted entry check, and gives the one list of specification 2 section 7.2; the PreToolUse program passes it for Bash and PowerShell calls only. Two review rounds (t75a: four blocking points; t75b: one blocking point), every finding applied; revision 2 read by the decision agent; filled at base fa4e4574 and parsed by the project's own reader; commit C 6eb56b29 pushed, CI green. The owner was told before any code (D-1955 C3).
- **The end.** The owner ended the session (:4508, "kết thúc phiên") before TASK-075's code; the code plan is the next session's first step.

## Decisions

| Date | What | Decided by | Recorded in |
|---|---|---|---|
| 2026-10-23 | The proposal from the fork; the owner's question; the new rule's records | Decision agent (A41, A51), D-1939 to D-1942; the owner's "có" | the decision files; the rules book |
| 2026-10-23 | The archive of n5 and l74 | Decision agent (A41, A51), D-1943 | the decision files |
| 2026-10-23 | TASK-075's shape, the CI channel's revision 12 (A66), the contract, commit C | Decision agent (A41, A51), D-1944 to D-1958 | the decision files |
| 2026-10-23 | The session's end at the owner's word | Decision agent (A41, A51), D-1959 and the decisions that follow | the decision files |

## Problems and mistakes

- **A two-call slip** (two Edit calls in one message on a scratchpad draft; D-1952): listed; work went on under the slip rule of D-1912 C2.
- **A script that stopped on its own check:** make_r2.py (a marker's line wrap); fixed by make_r2b.py, not rerun (D-1955).
- **Turn-final replies that did not tell the owner** of the rules-book change and the CI loosening until the reply after request D-1952 (D-1941 C4, D-1947 C4); told then.
- **The decision agent's catch:** the reading module needed the CI channel's change first; the first contract draft's AC8 contradicted its own tests (D-1952, round t75a).

## State at the end and next step

- **A14:** step 9; M5 in progress, its last element TASK-075.
- **TASK-075:** contract on main (6eb56b29); no code yet.
- **Next:** read the checkpoint file and the lessons; the pages from D-1960; TASK-075's code plan from a clone on task/TASK-075 at 6eb56b29, brought to the decision agent first; then its code, reviews, acceptance and landing; specification 2's stale sentences (AC10); the M5 exit review.
- **Open:** the archive of this session's scratchpad (at its end, D-1959); DEF-0089; DEF-0092; DEF-0093; the rest as before.
