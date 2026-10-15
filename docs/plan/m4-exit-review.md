# M4's exit review point

> - **Status:** revision 0 (decisions D-752, D-753 and D-755), with the owner's answers of 2026-10-15 recorded in §7. It is not binding, like the Master Plan; it plans, and it approves no specification and no task. The owner's answers in §7 are the owner's acts (A8; Master Plan §5); the rest is the decision agent's, advisory. M4's exit is recorded in the working records (History and Progress) and the decision files, not here.
> - **Sources:** Master Plan revision 3 (`docs/plan/master-plan.md`), §5 line 88 and §10 line 131 (the review point and its questions); DM rows A8 to A11, C12, C13 (`docs/pre-genesis/decision-matrix.md` lines 64-67, 184-185); CR-001 E6 (`docs/pre-genesis/CR-001-concept-errata.md:15`); specification 4 revision 3 (DM F32); decisions D-251 (M3 and M4 in the bootstrap), D-415 (M3's exit with limits), D-748 (DEF-0030 point (i) placed here); the open Deferred items that name this point (DEF-0030, DEF-0058, DEF-0059, DEF-0061). Concept lines are `AIEOS-concept.md` (v0.5, A22).

## 1. What the review point must rule

From Master Plan §5 (line 88), before any M5 code contract:
- (a) whether M5 to M7 are built in the bootstrap or native;
- (b) where the benchmark, the stack ADR and the native stack come (A8, A10, C12; CR-001 E6);
- (c) the A11 stages that M8 reaches in v0.1;
- with a benchmark plan drafted by then (a document only; nothing runs). The benchmark's criteria and weights are the owner's (A8), asked once.
- From §10 (line 131): whether Context Compiler v1 belongs to M6.
- An option that keeps the whole of v0.1 in the bootstrap, or that starts capabilities native without A11's stages, goes to the owner as a plain question (line 88).
- And, before those: whether M4 exits now, with named limits, as M3 did (D-415).

## 2. M4's state: specification 4 against accepted work

| Spec 4 | What it asks | Accepted work on `main` | What is left |
|---|---|---|---|
| §2 gates V0-V2 | G0 to G3 in the CI channel on the evaluated commit | the CI workflow (revision 8); V2's dependency rule carried in substance by the deterministic_rule step (DEF-0042, D-559) | spec 4 line 31 is out of date (DEF-0042); for spec 4's next revision |
| §3 stale evidence | rules 1 to 3 | rule 1 in the governor (its rule 2); rules 2 and 3 `stale.py` (TASK-023) | point 10 (does the governor stale by rule 3) stays the governor spec's |
| §4 profiles | one pure function, one record | the governor's `derive_inputs`; the audit copy `verification_records.py` (TASK-029) | whether the governor reads the record (point 10) |
| §5 independence | records state class, recorder, models | spec 2 revision 3 keys (F36); the governor's way-2 and decision-agent review checks | the checking of `session`, `ci_run` and the implementer trailer (DEF-0051) |
| §6 AC mapping | coverage check; test-to-AC listing; a record key | `ac_coverage.py` (TASK-021), `ac_tests.py` (TASK-022); the `acs` key (F36) | 180 earlier criteria named by no test, as data (DEF-0049) |
| §7 reconciliation | constitution, scope, stale; in CI and in the core | `drift.py` (TASK-030), `reconcile.py` (TASK-031), `scope_drift.py` (TASK-033), `scope_reconcile.py` (TASK-034, TASK-035); policy v3's non-task list (F38) | never run at a real base commit (DEF-0058); DEF-0061's t1, t2, rest of t5, L1, L2, P7 |
| §8 risk | one pure classification function; RISK-01 | the governor's classification; RISK-01's fixture, runner entry and set entry (TASK-017 to TASK-020), PASS in every base run since run 150 (advisory) | the policy's machine-readable form (point 12) |
| §9 autonomy L1-L2 | a product feature only | `autonomy.py` (TASK-036), no caller | the governor's row 4 wiring (a governor change); gov-AIEOS stays L1 |
| §10 records | the audit copies through the single writer | TASK-029; the writer (TASK-016, TASK-028) | — |
| core caller (§7 item 4; D-415 C3) | submission, recovery at start, evaluation, execution | `gitread.py` (TASK-024), `submit.py` (TASK-025), `startup.py` (TASK-026), `evaluation.py` (TASK-027), release by token (TASK-028), `execution.py` (TASK-032) | the session-start caller of `execute` (DEF-0059; spec 3 §1); DEF-0030 point (i), the Resume Check's READY to STALE alignment (D-748) |

Reading (proposed): every section of specification 4 has its computation accepted and on `main`; what is left is wiring into a runtime that does not exist yet (M5 to M7), hardening that fails closed, and open points that belong to other documents' revisions. None of it weakens an evidence requirement or blocks a later milestone's specification.

## 3. Proposal: M4 exits with named limits

- **Proposed (P1):** M4 exits now, decided by the decision agent (A41, A51; Master Plan §6), DELEGATED, advisory, as M3 did (D-415), with these limits named in the exit record:
  - L-a: `autonomy.py` has no caller; the governor's row 4 is not wired; gov-AIEOS stays L1 (spec 4 §9; Master Plan §9 item 5).
  - L-b: DEF-0030 point (i), the Resume Check's READY to STALE alignment, fails safe; carried with TASK-037 as its form (D-748).
  - L-c: no session-start caller of `execute`; the core's paths are never run end to end on a real project-state directory (DEF-0059; DEF-0030).
  - L-d: the reconciliation callers never run at a real base commit (DEF-0058); DEF-0061's remaining items.
  - L-e: spec 4's open points 7 to 12 and line 31; spec 2's point 11 (DEF-0042, DEF-0051).
- **Alternative (P2):** TASK-037 before the exit. Lost: it is a three-part critical change to a pinned module for a behaviour that already fails safe; it does not change what M5 needs; and it is better weighed with the native stack choice (a native Resume Check would be a new version anyway under A11).

## 4. Candidates for the next work, ranked (proposed)

1. **The benchmark plan and the owner's criteria and weights** (A8; this document's §6): it gates every M5 code contract (line 88).
2. **Specification 5 (adapters) drafting** (Master Plan M5; concept line 995): drafting is not a task (§5), so it can start while the benchmark waits; it names the runtime that L-c needs.
3. **TASK-037** (L-b): when the decision agent judges the pin change worth it before M5, or folded into the first Resume Check takeover under A11.
4. **Spec 4 revision 4** (L-e; line 31): a documentation change, low cost.
5. **DEF-0061's remaining test items** (L-d): low value; at a task that touches `scope_reconcile.py`.
6. **The governor's row 4 wiring** (L-a): no effect for gov-AIEOS while it stays L1; with the first product project, or in M8.

## 5. The scope questions

**(a) and (b): bootstrap or native for M5 to M7, and where the benchmark comes.** Three options:
- **Option A, all of v0.1 in the bootstrap, the benchmark after v0.1:** M5 to M7 also in Python 3 standard library; the benchmark, the stack ADR and the native stack after v0.1. **Ruled out by the decision agent (D-752):** postponing the benchmark and the stack ADR past v0.1 strains A9's invariant ("the bootstrap implementation is disposable and must not become an accidental second core") most and gains little, since A8 says the benchmark does not block the bootstrap anyway. The owner is not asked about it.
- **Option B, benchmark now, M5 to M7 native:** the benchmark plan now, run after the owner approves its criteria and weights; the stack ADR; M5 to M7 written native. Gains: A10's sequence as written; nothing written twice. Costs: M5 code waits for the benchmark and the ADR; two languages in the build for a time; new capabilities start native without A11's bootstrap stage, so by line 88 it goes to the owner.
- **Option C, benchmark now, M5 to M7 in the bootstrap, native takeover per capability (A11):** the benchmark and ADR proceed in parallel; M5 to M7 are built in the bootstrap; each capability is then taken over by native through shadow and assisted stages, proven by conformance. Gains: follows A10 and A11 without an exception; nothing waits; A9's risk bounded by a named takeover order. Costs: the most total work (each capability written twice). With (c)'s stages below, every working part of v0.1 stays in the bootstrap (native only shadows and decides nothing), which is a reading of line 88's first trigger ("keeps the whole of v0.1 in the bootstrap"); so by line 88 it goes to the owner as well as B.
- **Recommendation: Option C** (decided by: decision agent (A41, A51), D-752, for the recommendation only). The choice between B and C is the owner's (§7 Q2).
- **The owner chose Option C** (answer "Câu 2: 1", 2026-10-15, session 218e5c55, transcript :809; §7), so (c) below applies.

**(c) The A11 stages M8 reaches in v0.1 (proposed, if the owner chooses Option C):** in v0.1 AIEOS governs its own build with the bootstrap capabilities (stage "bootstrap" for all); native versions of the governor and the Resume Check reach "shadow" (run beside the bootstrap, compared by conformance, deciding nothing); "assisted", "native takeover" and "bootstrap retirement" come after v0.1. The order of takeover: the pure computations with frozen conformance fixtures first (governor, Resume Check, risk), the stateful writer last.

**Context Compiler v1 (line 131):** in M6 (ruled by the decision agent, D-752), beside Work Orders, since concept §7.3 (line 508) makes the Work Order its output and line 506 runs it only after a CONTINUE; it gets its own section of specification 6.

## 6. The benchmark plan (draft; a document only, nothing runs)

- Purpose: choose the native stack among TS, Go and Rust (A8), for the stack ADR (CR-001 E6; C12).
- Candidates: TypeScript (Node), Go, Rust (A8).
- Method: one reference workload written in each candidate: the governor's acceptance decision and the Resume Check over the frozen conformance fixtures of M2 and M3 (byte-equal decision records required), plus the event log's append and recovery over a generated log; the same tests in each; run in the CI channel on Linux and locally on Windows; results as records, advisory.
- When it runs: only by its own decision, after the owner has approved the criteria and weights (A8). It is not a trust-boundary measurement (Master Plan §9 item 3 names P-CRED, P-GH, P-LOC and C13). A run in the CI channel needs its own workflow decision under A66, with no secret and no write access; anything that needs either stays the owner's.
- Criteria and weights: the weights are the owner's answer to Q1 (2026-10-15, :809, §7), approving them before any run as A8 requires; no criterion was added or dropped:

| # | Criterion | How it is scored | Weight |
|---|---|---|---|
| 1 | Correctness against the frozen fixtures (byte-equal records) | pass or fail; a fail rules a candidate out | must (fixed in the question) |
| 2 | Supply-chain size (dependencies needed for the workload; INV-002's spirit) | count of third-party packages | cao (high) |
| 3 | Distribution (one binary, no runtime to install) | yes / partly / no | thấp (low) |
| 4 | Windows and Linux behaviour the same (paths, line ends, processes) | test pass on both | vừa (medium) |
| 5 | Speed (run time of the workload; start-up time of the CLI) | measured, relative | thấp (low) |
| 6 | How well AI agents write and review it (review findings per task in the workload) | counted from the reviews; AI-judged (CR-002 K6), not a human measure | cao (high) |
| 7 | Type and memory safety | language property | thấp (low) |
| 8 | Ease for the owner to read and maintain | the owner's own judgement when the results come | vừa (medium) |

## 7. Questions for the owner (drafted once, plain Vietnamese; one message with both questions, sent only after the decision agent approves this draft; it ends the turn)

- **Q1 (A8: the criteria and weights):** "Câu 1. Để chọn công nghệ lâu dài cho AIEOS (một trong ba ngôn ngữ lập trình đã chọn từ trước), Claude sẽ so ba bên theo các tiêu chí dưới đây. Với mỗi tiêu chí, bạn ghi một trong bốn chữ: cao, vừa, thấp, hoặc bỏ. Tiêu chí (1) là bắt buộc, không cần ghi. Bạn được thêm tiêu chí của mình. (1) Chạy đúng y như bản hiện có; sai là bị loại. (2) Ít phải dùng phần mềm do người ngoài viết. (3) Dễ cài: chỉ một tệp là chạy được. (4) Chạy giống nhau trên các loại máy tính khác nhau. (5) Chạy nhanh. (6) AI viết và rà soát dễ, ít lỗi (do AI chấm, không phải người chấm). (7) Ít loại lỗi nguy hiểm ngay từ cách viết. (8) Bạn thấy dễ đọc và dễ giữ lâu dài; điểm này do chính bạn chấm khi có kết quả. Đề xuất của Claude: (2) và (6) cao; (4) và (8) vừa; (3), (5) và (7) thấp."
- **Q2 (line 88: Option C or Option B):** "Câu 2. Các phần mới của AIEOS (phần nối với công cụ AI, phần giao việc, phần phê duyệt) nên làm theo cách nào? Cách 1 (đề xuất): tiếp tục làm bằng bản tạm hiện nay để không phải chờ, trong lúc đó chọn công nghệ lâu dài; bản đầu tiên vẫn chạy bằng bản tạm, phiên bản lâu dài chỉ chạy song song để so; cái giá là mỗi phần phải viết hai lần. Cách 2: chờ chọn xong công nghệ lâu dài rồi làm thẳng bằng nó; không viết hai lần nhưng phải chờ, và bỏ qua bước làm tạm. Bạn trả lời "1" hoặc "2"."
- Both outcomes: "1" is Option C with (c)'s stages; "2" is Option B, and (c) is redrafted for B before Master Plan revision 4. The message also carries D-751's and D-752's FOR THE OWNER texts verbatim, the slip count and the level as an estimate. If the owner hands a choice back, it is re-asked once in one line. No M5 code contract and no Master Plan revision 4 before the answers.
- Sent once, as the turn-final reply of session 218e5c55 at transcript :756 (2026-10-15).
- The owner first asked for an explanation (:760, a question, not an answer: "hãy giải thích câu 2 cho tôi, chọn công nghệ là sao, chọn công nghệ cho AIEOS hay gov-AIEOS, công nghệ lâu dài nghĩa là gì?"); it was answered by an explanation at :805 (decision D-754), which left both questions open.
- **The owner's answers** (2026-10-15, session 218e5c55, transcript :809), verbatim:

  > Câu trả lời của tôi:
  > Câu 1: (2) cao, (6) cao, (4) vừa, (8) vừa, (3) thấp, (5) thấp, (7) thấp. Câu 2: 1.

  Read by decision D-755 as the owner's own answers, given value by value: Q1's weights as in §6's table (criterion (1) a must, none added or dropped); Q2 "1", Option C.

## 8. Where this goes (D-752 M6)

1. Draft 1 to the decision agent as a request, with its diff against draft 0 (done: D-753).
2. The owner message of §7, once the decision agent approved draft 1 (done: :756; answers :809).
3. After the answers, one change-set: this document as `docs/plan/m4-exit-review.md` (new; non-binding, like the Master Plan; home approved in D-752), with the owner's answers recorded verbatim; M4's exit record in the History and Progress (as D-415); the limits L-a to L-e as Deferred log lines (DEF-0030, DEF-0042, DEF-0058, DEF-0059, DEF-0061), no new item. M4's exit is decided in that change-set's request, as its own decision, with its push.
4. Master Plan revision 4 (a `master_plan_update`, decided by the decision agent under A51; §11), later and separately: §4 M5 to M8, §5's bootstrap scope, §10's open items closed.
