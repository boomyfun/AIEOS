# Session 2026-10-23 15:55 (UTC+7), later part 2: specification 6 and specification 2 revision 10

> - **Status:** working record, non-authoritative. Claude wrote it during this session. It is a claim, not evidence. Owner decisions are in `docs/pre-genesis/decision-matrix.md` (DM). Delegated decisions are in the decision files, kept outside the repository.
> - **Session and transcript:** session `308d8b07-66b8-456a-9196-b673961b7327`, after its records commit 5d3bad30; its earlier parts are recorded in `2026-10-23-1555-the-pages-d1960-to-d1964-task-076-landed-specification-2-revision-9-and-m5s-exit.md` and `2026-10-23-1555-the-later-part-the-resumed-session-the-archive-and-the-pages-d1965-to-d2027.md`. A reference such as (:8286) is a line in its main transcript.
> - **Models:** the main session `claude-opus-5-5`; the decision agent on `claude-opus-5-5`, definition revision 13; reviews m6-R1, m6-R3, m6-R5, m6-R7 and s2r10-R1 on `claude-sonnet-5-5`, and m6-R2, m6-R4, m6-R6, m6-R8 and m6-R9 on `claude-opus-5-5`; no Fable.
> - **Repository:** main 5d3bad30 at the start of this part; specification 2 revision 10 and DM F60 as e3edad21 (CI run 39953226644 green); specification 6 revision 6 and DM F61 as b27b1f3e (CI run 39954122946 green); this records commit.

## Summary

- **Specification 6, MCP Protocol and Work Orders (M6; D-2030 to D-2045, D-2050 to D-2056; DM F61).** A source map, an outline, and revisions 0 to 6, reviewed by m6-R1 to m6-R9 in five rounds. The reviews moved the session's start, submission and end out of the tools to the launcher (specification 5 :112), made seven in-session tools under one lease rule with no token in any tool, gave the Work Order a field for the contract's keys, and kept every claim at `agent_declared`. Its prerequisite in specification 2 is met by revision 10; the bootstrap record checker's task that adds `text`, `session` and `acs` is still to come before the tools that write claims.
- **Specification 2 revision 10 (D-2045 to D-2049; DM F60).** The record key `text` for a session's claim, `acs` for a report entry, and the string form of a handoff item's `refers_to`; reviewed by s2r10-R1, whose one blocking point (the checker also lacks `session`) was applied.
- **The dispatch question.** D-2042 put to the owner whether the v0.1 dispatch, the launcher fixing the task and the agent pulling its own Work Order through MCP, keeps the owner's choice (b) of DM A43 Q6. The owner asked (:8286): "câu hỏi nào? hãy cho tôi đầy đủ câu hỏi. Tại sao không hỏi agent quyết định và tại sao agent quyết định không quyết định trả lời các câu hỏi này?" D-2050 withdrew the question and decided it: the design keeps (b) as DM A43 Q6 records it, the pull option of concept §17 item 3.
- **A shadow mode (D-2042 item B).** A proposal relayed from a forked side session, asked by the owner there, was approved in a narrowed form: from the next task, a read-only bootstrap Resume Check in a scratch clone before its contract commit, and the governor's evaluate at every acceptance, each difference named; nothing decided, placed or written in the repository's state.

## Decisions

| Date | What | Decided by | Recorded in |
|---|---|---|---|
| 2026-10-23 | Specification 6: plan, source map, outline, revisions 0 to 6, reviews, approval, commit | Decision agent (A41, A51), D-2030, D-2035 to D-2045, D-2050 to D-2056 | DM F61; the decision files |
| 2026-10-23 | Specification 2 revision 10 | Decision agent (A41, A51), D-2045 to D-2050 | DM F60; the decision files |
| 2026-10-23 | The shadow mode, narrowed | Decision agent (A41, A51), D-2042 item B | the decision files |
| 2026-10-23 | The dispatch question withdrawn and decided | Decision agent (A41, A51), D-2050 | the decision files; specification 6 §1, §11 point 4 |

## Problems and mistakes

- **An over-escalation by the decision agent.** D-2042 put the dispatch question to the owner as a reading of an owner decision; DM A43 Q6's own row already reads (b) as the pull option of concept §17 item 3, which the design does, so no owner answer was needed. The owner's question at :8286 led D-2050 to withdraw and decide it, naming the escalation its own error.
- **Slips, each listed; work went on under the slip rule of D-1912 C2:** two-call slips D-2037 (a cite output saved and a checkpoint Edit in one message) and D-2039 (a copy run and a brief Edit in one message); text slips :6421 (D-2031) and :7972 (D-2047). The session's count: seven two-call slips (D-1965, D-1973, D-1974, D-1984, D-2007, D-2037, D-2039) and four text slips (:3610, :5328, :6421, :7972); the decision agent's D-2047 C3 had miscounted the text slips as five.
- **Scripts that stopped on their own checks, each replaced by a new file under a decision and not rerun:** cp_exec6.py (an ordering fault in its replacements, D-2053), fixed by cp_exec6b.py (D-2054); D-2054 also corrected the counts of the fix as first described.
- **A failed Edit:** a checkpoint Edit whose anchor matched five places wrote nothing; redone with a unique anchor (D-2051).

## State at the end of this part and next step

- **A14:** step 9; M6 under way: specification 6 approved (F61), no M6 task yet.
- **Next:** the bootstrap record checker's task (records.py adding `text`, `session` and `acs`), its plan to the decision agent first, with the shadow Resume Check before its contract commit (D-2042 C3, D-2048 C3); the pages from D-2028.
- **Open:** DEF-0004; DEF-0089; DEF-0092; DEF-0093; the owner's acts (hook placement, connecting the MCP server, settings, measurement); the scratchpad's last files and the notes folder to the archive at the session's real end.
