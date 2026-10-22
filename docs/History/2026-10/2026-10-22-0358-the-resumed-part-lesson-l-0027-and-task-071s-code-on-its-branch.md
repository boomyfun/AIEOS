# Session 2026-10-22 03:58 (UTC+7), resumed part: the owner's 58%, lesson L-0027 and TASK-071's code on its branch

> - **Status:** working record, non-authoritative. Claude wrote it during this session. It is a claim, not evidence. Owner decisions are in `docs/pre-genesis/decision-matrix.md` (DM). Delegated decisions are in the decision files, kept outside the repository.
> - **Session and transcript:** session `fb20852c-d7c5-4660-b84c-20a7babe7ef1`, the same session as `2026-10-22-0358-the-pages-d1607-to-d1626-the-approval-of-h2as-contract-and-code-part-1.md`, which records its first part. A reference such as (:2174) is a line in its transcript.
> - **Models:** as in the first part: the main session `claude-opus-5-5`; the decision agent on `claude-opus-5-5`, definition revision 12; the reviewers on `claude-sonnet-5-5`; no Fable.
> - **Repository:** main 9ee714b9 (the first part's records); TASK-071's task commit f42c4a6f on task/TASK-071 (pushed, D-1636); this records commit.

## Why the session resumed

The first part ended at a part boundary by the decision agent's slip rule (D-1624 C4, D-1626), with the worker's context estimate at about 80 to 85% (the first part's History says about 80%; the worker's request at its end said about 85%; D-1627 C6). The owner then wrote (:2174): "Bạn thường xuyên tính context window sai dẫn đến việc thường kết thúc phiên rất sớm. Context window hiện tại mới đang là 58%". The decision agent resumed the session (D-1629) and replaced the stop rule: the worker's estimate is never alone a reason to end; only the owner's number of 80% or more, a system context warning or a compaction notice is (D-1629 C3). The owner then asked: "Hãy rút kinh nghiệm hoặc sửa lại cách tính", and lesson L-0027 was written (D-1631).

## Summary

- **Lesson L-0027** written (D-1631, D-1632): the worker's own context estimate is not a reason to end a session; its figures ran 10 to 27 points above the owner's in three sessions in a row, although D-1572 C2 had already forbidden a stop below 80% on a worker estimate alone.
- **TASK-071 code, parts 2 to 4** (D-1630, D-1633 to D-1636): the three task_contract test modules (part 2, 31 tests passing in the scratchpad); session_violation.py's hardening (0), (a) to (d), its test module, the rename of (d), test_the_partial_outcome's held_leases assert and a step-one property class (part 3); then, in a scratch clone at C (D-1634: never in E:/AIEOS; D-1635: a short folder and core.longpaths after the first clone failed on long file names), compile and the suite as the CI runs it: unit 1432, integration 153 (1 skipped), property 179, all passed.
- **The task commit** f42c4a6f on task/TASK-071 at C 5b995234 (nine files, 1261 insertions, 18 deletions, scans 0), pushed as a new branch; remote main unchanged (D-1636). The CI run on it (39698381111) ended "success".
- **The pages** D-1627 to D-1636 written.

## Decisions

| Date | What | Decided by | Recorded in |
|---|---|---|---|
| 2026-10-22 | The session resumed; the new stop rule | Decision agent (A41, A51), D-1629 | `D-1629-…` |
| 2026-10-22 | Lesson L-0027 now | Decision agent (A41, A51), D-1631 | `D-1631-…` |
| 2026-10-22 | TASK-071 code parts 2 to 4; the clone; the task commit and its push | Decision agent (A41, A51), D-1630, D-1633 to D-1636 | the decision files |
| 2026-10-22 | A slip at :2299 | Decision agent (A41, A51), D-1632 | `D-1632-…` |
| 2026-10-22 | The pages, these records, the push | Decision agent, D-1637 and its own later decisions | the next session's pages |

## The owner's words this part

- :2174: "Bạn thường xuyên tính context window sai dẫn đến việc thường kết thúc phiên rất sớm. Context window hiện tại mới đang là 58%".
- The next owner message: "Bạn thường xuyên tính context window sai dẫn đến việc thường kết thúc phiên rất sớm. Hãy rút kinh nghiệm hoặc sửa lại cách tính. Context window hiện tại mới đang là 58%".

## Problems and mistakes

All of these are the worker's errors.
- **The early end** of the first part, the third session in a row ended on a too-high estimate or with room left (L-0027).
- **A sixth text slip** (:2299, one short line before a Write), refused by the call-form guard and listed (D-1632).
- **The first clone** under the app's long scratchpad path failed on file names too long; redone in a short folder (D-1635).
- **A builder bug in the first part's records** noted by the decision agent (D-1627 C6): the first part's History gives about 80% where the worker's last request gave about 85%.
- **Stale header comments** in exec_t071b1.sh (TASK-070 values, not functional), left unedited so its pinned hash held (D-1636).

## State at the end and next step

- **A14:** step 9; M5 in progress; TASK-071 (H2a): contract on main (5b995234), task commit f42c4a6f on task/TASK-071 with a green CI run; not yet accepted.
- **Next:** TASK-071's part 5 (the broken copies AC8 names, each failing at least one test), part 6 (five way-2 reviews on Sonnet 5.5 and the decision agent's own reviews: INV-003's and OPS-002's human_review and the cross-model half), part 7 (acceptance with per-entry coverage by script, L-0022, and the landing on main); then H2b.
- **Open:** as before.
