# Session 2026-10-23 15:55 (UTC+7), later part 6: TASK-080, the Context Compiler v1 as a pure module

> - **Status:** working record, non-authoritative. Claude wrote it during this session. It is a claim, not evidence. Owner decisions are in `docs/pre-genesis/decision-matrix.md` (DM). Delegated decisions are in the decision files, kept outside the repository.
> - **Session and transcript:** session `308d8b07-66b8-456a-9196-b673961b7327`, after its records commit 2c0ef3b7; its earlier parts are recorded in the History files of 2026-10-23-1555 named in `2026-10-23-1555-the-later-part-5-specification-6-revision-7-and-task-079-the-mcp-servers-four-claim-tools.md`. This part ran on 2026-10-24, across one compaction of the session's context.
> - **Models:** the main session `claude-opus-5-5`; the decision agent on `claude-opus-5-5`, definition revision 13; contract reviews m80-R1 on `claude-sonnet-5-5`, m80-R2 and m80-R3 on `claude-opus-5-5`; code reviews t80s-S1 and t80s-S2 on `claude-sonnet-5-5`; no Fable.
> - **Repository:** main 2c0ef3b7 at the start of this part; TASK-080's contract as b67d39c6 (CI run 40001220294 green); the code commit b195e62e (CI run 40004794938 green) and the fix commit 9c41ab22 (CI run 40007847684 green) on task/TASK-080; the records commit 1da2720a (CI run 40010658568 green); the task's two commits rebuilt onto main as 2f222857 and 44704566; this records commit.

## Summary

- **M6's third slice split (D-2170, D-2171).** S3 became S3a, TASK-080: a pure Context Compiler; and S3b, the readers of its inputs and the MCP tools get_work_order and query, which wait for the launcher (M7), since no input reader exists (D-2068).
- **TASK-080 (D-2170 to D-2212).** `src/aieos_bootstrap/context_compiler.py` adds build_work_order(inputs), which returns specification 6 revision 7's Work Order from given values: nine keys; five layers (the constitution articles from the Resume Check record, not recomputed; the components met by the declared read-set or named by its interfaces; the traced entries, the ACs and the ADRs; the matched, interface, schema and derived files; the last handoff); items with byte budgets, references taken largest first, ties by ref, never a shortened content; and the canonical hash. It reads, writes and calls nothing, uses only resume_check.meet and matches, and never raises. Accepted under D-2206 at 9c41ab22, change class critical_cr; landed on main as 44704566.
- **The contract (r0 to r2).** Reviews m80-R1 to m80-R3 found that the name "compile" is refused by the deterministic rule (the function became build_work_order), that the pattern reading and the content form were undefined, and that interfaces and schemas had been left out; r2 includes them by specification 3's rules (D-2173 to D-2176).
- **The review found an unbounded walk (D-2192 to D-2197).** Review t80s-S1 found that the input check, bounded only by depth, could run without end on a value holding itself twice or doubling at each level. The fix commit 9c41ab22 bounds the walk at 1,000,000 values and stops it at the first depth finding, with a new AC1 test and a fifteenth broken copy (case 15); review t80s-S2 of the fix approved.
- **The shadow (D-2068).** The governor's evaluate gave NEEDS_REVIEW at table row 5 with nothing missing: no disagreement with the acceptance.
- **DEF-0096 (new).** The Context Compiler reads a component path with no wildcard only as the root-anchored "<it>/**", narrower than the Resume Check's reading; and two wording points from the reviews. Specification 6's next revision decides the reading.

## Decisions

| Date | What | Decided by | Recorded in |
|---|---|---|---|
| 2026-10-24 | S3's plan and split, the pin scan, TASK-080's contract r0 to r2 and its three reviews | Decision agent (A41, A51), D-2170 to D-2176 | docs/tasks/TASK-080.yaml; the decision files |
| 2026-10-24 | Commit C, its push and CI; the owner told of TASK-080 | Decision agent (A41, A51), D-2177 to D-2181 | docs/tasks/TASK-080.yaml; the decision files |
| 2026-10-24 | The clone, the code, the local runs and their one failure, AC10, the code commit, its push and CI, review t80s-S1, the fix commit, its runs and broken copy, its push and CI, review t80s-S2, DA-3 to DA-5 | Decision agent (A41, A51), D-2182 to D-2199 | docs/records/TASK-080.jsonl; the decision files |
| 2026-10-24 | TASK-080's records and acceptance, change class critical_cr; DEF-0096; the records commit; the landing and their pushes | Decision agent (A41, A51), D-2200 to D-2212 | docs/records/TASK-080.jsonl; DEF-0096 |

## Problems and mistakes

- **A pin tripped by a test's own words.** A test docstring named the benchmark folder with its slash, which test_bench_isolation refuses; the first local run found it, and one Edit fixed it before the code commit (D-2185).
- **An unbounded walk found by review, not by the tests.** The input check's depth bound alone did not stop a value that refers to itself twice; t80s-S1 found it, and the fix commit closed it with a test (D-2192).
- **Retyped review copies.** The saved copies of t80s-S1 and t80s-S2 were retyped, not the reviewers' bytes; the records were right, since the builder reads the handbacks themselves, and save80s2.py wrote exact copies (D-2201).
- **An order changed without asking.** The review folder and the fix's review were started before the CI read was brought to the decision agent, against the order D-2197 set; accepted after the fact as an occurrence of L-0014 (D-2198).
- **Slips, each listed; work went on under the slip rule of D-1912 C2.** Multi-call slips since the last records commit: D-2177 (two Writes), D-2178 (a Read and a Glob after the compaction), D-2201 (a copy script written and run in one message), D-2207 (two Writes). A text slip at transcript :20696, found by the guard (D-2195). Departures listed with them: a Write and an Edit of one file (D-2183), an Edit of a broken-copies script before its run (D-2187). The session's count: twenty-one multi-call slips and eleven text slips.
- **A builder's closing hash list names the dry builder.** make_records_080r1.py prints make_records_080.py's hash among its outputs, a leftover path; no record is affected (D-2206 N3).

## State at the end of this part and next step

- **A14:** step 9; M6 under way: specification 6 revision 7 (F62); S1 (TASK-078), S2 (TASK-079) and S3a (TASK-080) on main; S3b waits for the launcher (M7).
- **Next:** M6's exit review, in m5-exit-review.md's form, its plan to the decision agent first; S3b and DEF-0095 carried to M7; the pages from D-2028.
- **Open:** DEF-0004; DEF-0051; DEF-0063; DEF-0089; DEF-0092; DEF-0093; DEF-0094; DEF-0095; DEF-0096; task/TASK-076 to task/TASK-080 on GitHub (their deletion is the owner's); the owner's acts (hook placement, launching and connecting the MCP server, settings, measurement); the scratchpad's last files and the notes folder to the archive at the session's real end.
