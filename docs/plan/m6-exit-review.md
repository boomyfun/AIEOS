# M6's exit review

> - **Status:** revision 1 (decisions D-2216 to D-2221 and the decision that approves it; review m6x-R1's points applied). It is not binding, like the Master Plan; it plans, and it approves no specification and no task. M6's exit is decided in the request of the change-set that adds this document and Master Plan revision 5, as its own decision of the decision agent (A41, A51; Master Plan §6, `docs/plan/master-plan.md:102`), DELEGATED and advisory, as M3's (D-415), M4's (D-755) and M5's (D-2018, D-2021) were; it is recorded in the working records (History and Progress) and the decision files, not here.
> - **Sources:** Master Plan revision 4 (`docs/plan/master-plan.md`), §4 M6 (:73-74) and §6 (:102); DM rows A41, A43 and A51 (`docs/pre-genesis/decision-matrix.md:102`, :104, :112), F61 (:294) and F62 (:295); specification 6 revision 7 (`docs/specs/spec-06-mcp-protocol-and-work-orders.md`, DM F61, F62); the task contracts TASK-078 to TASK-080; the open Deferred items DEF-0092, DEF-0094, DEF-0095 and DEF-0096. Line references are to main at 70098e89.

## 1. What the review must rule

- Whether M6 exits now, and with which named limits (Master Plan §6, :102: a milestone with tasks exits when its deliverables' tasks are accepted and the decision agent approves the milestone).
- M6's goal (Master Plan :74): specification 6, about eight tools through which agents pull Work Orders (A43 Q6), and the Context Compiler v1, graph-based, placed in specification 6 beside Work Orders (decision D-752).
- Who decides the move past M6, since two of the tools are not built (section 4).

## 2. M6's state: the goal against accepted work on `main`

| M6 element (Master Plan :74) | Accepted work on `main` | What is left |
|---|---|---|
| Specification 6 | `docs/specs/spec-06-mcp-protocol-and-work-orders.md` revision 7, approved in the owner's place (DM F61, F62, `decision-matrix.md:294`, :295); seven tools (:33): M6 built five of them, and two are carried (section 3) | section 11's open points stay open; the stated choices TASK-080 recorded for its next revision; DEF-0096 |
| The server's frame and `status` | `mcp_server.py` (`status` :174, `handle` :344, `main` :385; TASK-078); the store's read `writer.session_leases` (`writer.py:873`) | not launched in or connected to any runtime (owner act) |
| `acknowledge`, `ask`, `report`, `handoff` | `mcp_server.py` (`claim` :277; TASK-079), one claim record per item through the single writer under the session's live lease | the handoff file written after the submission: the launcher's (specification 7, M7; DEF-0095) |
| The Context Compiler v1 | `context_compiler.py` (`build_work_order` :70; TASK-080), a pure module: the five layers, items, budgets with references and the canonical hash from given values; bounds on its input walk (`MAX_NODES` :61) | its reading of component paths, narrower than the Resume Check's (DEF-0096) |
| `get_work_order` and `query` (specification 6 :37, :38) | none | not built: the readers of their inputs at the base need the launcher (decision D-2171); carried to M7 with it (section 5) |
| `list_tasks` | none | specification 7's, as a core function (decision D-2040 C1) |
| The pull of the Work Order (A43 Q6) | the pull model kept as DM A43 records it (decision D-2050) | an agent can pull its Work Order only once `get_work_order` exists (M7) |

## 3. Named limits at the exit

- The MCP server is not launched in or connected to any runtime: the owner's act (A51 item (4)); nothing calls `build_work_order` but its tests.
- Nothing is measured: the server and the compiler are advisory (A25, C6, CR-001 E1; DEF-0004).
- `get_work_order`, `query` and the readers of their inputs (S3b, decision D-2171), and the handoff file (DEF-0095), are carried to M7; until then M6's goal is met in its parts, not end to end: no agent pulls a Work Order.
- DEF-0092, DEF-0094, DEF-0095 and DEF-0096 stay open with their resume conditions; specification 6 section 11's open points stay open.

## 4. Who decides the move past M6

- Ruled by decision D-2218: the decision agent's (A41, A51), relayed to the owner in plain words.
- Option b, which the owner chose in A51 (`decision-matrix.md:112`), covers the steps to the next milestone; the cases A51 item (4) keeps do not include the plan's milestone contents. The Master Plan's M6 goal is the decision agent's text (`master-plan.md:4`, :12; decision D-752), and a change to it is a `master_plan_update` that the decision agent approves under A51 (`master-plan.md:142`), so carrying two of its tools to M7 is a revision the decision agent makes under A51, as revision 4 followed M4's exit (decision D-757).
- The change is made openly: Master Plan revision 5 in the same change-set as this review (section 5), not left implied by an exit that :102, which ties it to "its deliverables' tasks are accepted", would not allow with a deliverable unbuilt.
- No owner decision changes: DM A43 Q6's pull model stays (decision D-2050); the tools are carried, not dropped; no owner-kept act is changed.

## 5. Proposal

- **Proposed:** M6 exits now, decided by the decision agent (A41, A51; Master Plan §6), DELEGATED, advisory, as M3, M4 and M5 did, with the limits of section 3 named.
- **Master Plan revision 5,** in the same change-set: M6's goal records that `get_work_order` and `query`, with the readers of their inputs, are carried to M7 with the launcher (decision D-2171), that the handoff file (DEF-0095) is carried too, and that `list_tasks` is specification 7's (decision D-2040 C1); M7's goal names the carried tools; the header line and a revision 5 note; no milestone is removed and no owner-kept item is changed.
- M7's work starts in a later session (decision D-2217, on the owner's word to end this session after M6).

## 6. What the owner is told (plain Vietnamese; no question)

Giai đoạn 6 (các công cụ để trợ lý làm việc với hệ thống và phần biên soạn gói việc) đã xong phần làm được: các công cụ báo trạng thái, xác nhận, hỏi, báo cáo và ghi lại các mục bàn giao đã có và được nghiệm thu, cùng với phần biên soạn gói việc cho mỗi phiên. Những phần cần bộ khởi chạy của giai đoạn 7 được chuyển sang giai đoạn 7 cùng với bộ khởi chạy: công cụ để trợ lý tự lấy gói việc của mình, công cụ để trợ lý hỏi lấy thêm tài liệu, phần liệt kê các việc, và việc viết tệp bàn giao. Kế hoạch chung được sửa để ghi rõ điều đó. Agent quyết định đã quyết định kết thúc giai đoạn 6 thay bạn, như các giai đoạn trước, khi lưu bản tổng kết này. Chưa có gì được khởi chạy hay kết nối, và chưa có phép đo nào, nên tất cả chỉ có giá trị tham khảo. Việc khởi chạy và kết nối vẫn là việc của riêng bạn, khi bạn muốn. Giai đoạn 7 bắt đầu ở phiên sau và không cần bạn làm gì lúc này.
