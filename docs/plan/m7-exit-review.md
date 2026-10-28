# M7's exit review

> - **Status:** revision 1 (decisions D-3323, D-3324 and the decision that approves it). Like the Master Plan, it is not binding: it plans, and it approves no specification and no task. M7's exit is decided in the request of the change-set that adds this document and Master Plan revision 6, as its own decision of the decision agent (A41, A51; Master Plan §6, `docs/plan/master-plan.md:104`). That decision is DELEGATED and advisory, as M3's to M6's were (M6: D-2218). It is recorded in the working records (History and Progress) and in the decision files, not here.
> - **Sources:**
>   - Master Plan revision 5 (`docs/plan/master-plan.md`): §4 M7 (:77-79) and §6 (:104);
>   - `docs/plan/m6-exit-review.md` §3 (:24-29);
>   - specification 7 revision 3 (`docs/specs/spec-07-cli-and-zero-friction-path.md`);
>   - the task contracts and records TASK-081 to TASK-098;
>   - the open Deferred items DEF-0090 to DEF-0096, DEF-0098, DEF-0100 to DEF-0102 and DEF-0104 (DEF-0097 and DEF-0099 are done, and DEF-0103 is closed), and the new DEF-0105 and DEF-0106;
>   - `docs/plan/m5-exit-review.md`, for DEF-0093.
>   Line references are to main at cd0d50d7.

## 1. What the review must rule

- Whether M7 exits now, and with which named limits. Master Plan §6 (:104): a milestone with tasks exits when its deliverables' tasks are accepted and the decision agent approves the milestone.
- M7's goal (Master Plan :78): specification 7's `aieos init`, `aieos import`, `aieos run` and `aieos status`, and the zero-friction path (concept §11). With it come the items carried from M6 (:79).
- Who decides the move to M8 (section 4).

## 2. M7's state: the goal against accepted work on `main`

| M7 element (Master Plan :78-79) | Accepted work on `main` | What is left |
|---|---|---|
| `aieos init` (spec 7 :28) | `writer.init_layout` and the CLI's `init` (TASK-095) | where the interim documents move on the self-build stays open (spec 7 §10 point 4) |
| `aieos import` (spec 7 :29) | `writer.write_contract`, `launcher.import_task` (TASK-097) | the drafting session needs the owner's launch; the root's form is accepted only in its Windows form (DEF-0105) |
| `aieos run` (spec 7 :30) | `launcher.run_task`, `scope_drift.path_class` and the CLI's `run` (TASK-098) | the limits stated at its acceptance (DEF-0105, DEF-0106) |
| `aieos status` (spec 7 :31) | `execution.status_report` (TASK-093) | parts with no reader yet show "not available" (spec 7 §10 point 5) |
| The approval flow (spec 7 §4) | `launcher.approval_act`: approve, reject and edit (TASK-096) | the approval record of a requirement or a specification in a proposal set stays open (spec 7 §10 point 3) |
| The launcher, `aieos launch`, `aieos end` (spec 7 §3, §5) | `launcher.start` and `end` (TASK-086), the read-set record at the end (TASK-089), the gone sessions' records at the next start (TASK-090), `end_outside` (TASK-092), `launch_outside` with no runtime starter (TASK-094; the owner's "có", D-3154) | the base-tip check, check 0 and max_risk (DEF-0101); a real runtime starter is the owner's act |
| `get_work_order` and `query`, with the readers of their inputs (carried from M6) | `base_files` (TASK-081), `base_inputs.work_order_inputs` (TASK-082), the two MCP tools at `AIEOS_BASE` (TASK-083) | the MCP server is not connected to any runtime (owner act); TASK-083's departures from specification 6 (DEF-0098) |
| The handoff file (DEF-0095; carried from M6) | `handoff_file` (TASK-087); written after a done end with commit None (TASK-094) | the write after a submission, how the file reaches Git, and the reader of "the last handoff" (DEF-0095) |
| `list_tasks` as a core function (carried from M6) | `execution.list_tasks` (TASK-084) and the CLI (TASK-091) | none |
| The Work Order pull: only after CONTINUE or CONTINUE_WITH, and after the Resume Check on a task still IN_PROGRESS (spec 6 §5, §11 point 14) | the Resume Check's inputs (TASK-085, TASK-088); the check before every grant (TASK-086); the Work Order only under a granted lease (TASK-083) | no agent has pulled a Work Order in a real session, since nothing is launched |
| The zero-friction path (concept §11; spec 7 §2) | the parts above, each built and tested | not end to end (section 3) |

## 3. Named limits at the exit

- **Owner acts.** Nothing is launched or connected. Running `aieos launch` with a real runtime starter, connecting the MCP server to a runtime, and real use of the commands on a real project stay the owner's acts (A51 item (4)); each is asked separately.
- **Nothing is measured.** Everything built is advisory (A25, C6, CR-001 E1; DEF-0004).
- **The zero-friction path works in its parts, not end to end.** No reader yet reads the contracts drafted under `.aieos/tasks/`, and who commits them is not settled. A larger intent needs a launched session, and each session needs the owner's launch (spec 7 §2 :22). Carried in DEF-0105, which also holds:
  - import's Windows-only root form;
  - the same intent recorded under another `--by` refused "conflict" after the template's write.
- **Text items for later revisions,** carried in DEF-0106:
  - `launcher.py` :120-121's text on the second caller of the departure from specification 5 :125;
  - specification 4 :61's open point;
  - the markers `contract_edit` and `intent` for specification 2's next revision;
  - TASK-098's docstring sentence on the lowercased classing (departure D-3290);
  - the CLI's docstring at `cli.py` :3, which names specification 7 revision 2.
- **Deferred items still open.** Each stays open with the resume condition its own file states:
  - DEF-0095: the handoff file after a submission, its way to Git, and the reader of "the last handoff";
  - DEF-0096: the Context Compiler's reading of component paths;
  - DEF-0101: the base-tip check, check 0 and max_risk;
  - DEF-0098: TASK-083's departures from specification 6. Specification 7 :56's "Specification 6's tool contracts are unchanged" and §10 point 8 no longer hold in the code;
  - DEF-0100: the Resume Check's inputs with no full source (TASK-088);
  - DEF-0102: read_set_record's part left open after TASK-089 and TASK-090;
  - DEF-0104: end_outside's two edge limits (TASK-092);
  - DEF-0093: carried from M5. Its launcher half stays with specification 7, and so does the limit that the root and its Git state stay untouched (specification 7 :49);
  - DEF-0092 and DEF-0094: named open at M6's exit.
  - DEF-0090 and DEF-0091: open from M5, unchanged by M7.
  - Any other Deferred item marked open stays open as its own file states.
- Specification 7 section 10's open points stay open.
- **The accepted contracts' own stated limits stand,** each as its contract states it. Among them:
  - TASK-098 (:174-198):
    - only the self-build's policy file is read;
    - the templates' read set "**" is refused past the base reader's bounds;
    - a rerun after a refused task.drafted append is refused "exists";
    - concurrent runs may choose the same intent number;
    - both templates are owner-kept;
    - auto-accept and the automatic run are not built.
  - TASK-095 (:103-106): `init` writes no ignore rule for `local/`.
  - TASK-096 (:174-180): the source class is the caller's statement and is not proven.
  - TASK-093 (:86-88): the departure from "the same core reads".

## 4. Who decides the move to M8

- The decision agent decides (A41, A51), as decision D-2218 ruled for M6. The owner is told in plain words before any M8 work starts.
- The move to M8 changes no owner decision and no owner-kept act. M8's stages are those of Master Plan §4 (:81-84).

## 5. Proposal

- **Proposed:** M7 exits now, decided by the decision agent (A41, A51; Master Plan §6), DELEGATED and advisory, with the limits of section 3 named.
- **Master Plan revision 6,** in the same change-set:
  - M7's entry gains an "Exited with named limits" line;
  - §11 gains a revision 6 note;
  - the header line changes.
  No milestone is removed, and no order or owner-kept item is changed.
- **In the same change-set:** DEF-0105 and DEF-0106 are added, and the logs of DEF-0095 and DEF-0101 each gain a line.
- M8's work starts only after the owner has been told (section 6).

## 6. What the owner is told (plain Vietnamese; no question)

Giai đoạn 7 (các lệnh để bạn dùng hệ thống và con đường ít phiền nhất) đã xong phần làm được. Đã có và đã được nghiệm thu:
- lệnh tạo khung dự án;
- lệnh nhập một dự án có sẵn;
- lệnh ghi một ý định và lập việc từ ý định đó;
- lệnh xem tình trạng;
- cách duyệt, từ chối hoặc ghi chú để sửa một việc;
- bộ khởi chạy phiên làm việc và các công cụ để trợ lý tự lấy gói việc của mình.

Một số điểm còn để ngỏ, đã được ghi lại để làm ở giai đoạn sau. Chưa có gì được khởi chạy hay kết nối, và chưa có phép đo nào, nên tất cả chỉ có giá trị tham khảo. Việc khởi chạy, kết nối và dùng thật trên một dự án thật vẫn là việc của riêng bạn, khi bạn muốn. Agent quyết định đã quyết định kết thúc giai đoạn 7 thay bạn, như các giai đoạn trước. Giai đoạn 8 (hệ thống tự quản việc xây dựng chính nó) là giai đoạn tiếp theo, và chưa có việc nào của giai đoạn 8 bắt đầu trước khi bạn được báo.
