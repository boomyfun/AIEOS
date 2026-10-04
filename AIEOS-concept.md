# AIEOS — AI Engineering Operating System

> **Concept Document v0.2** — bản hoàn thiện từ `Y-tuong-AIEOS.md`
> Trạng thái: Draft để thảo luận · Ngày: 2026-10-04

---

## 0. Tóm tắt

**Định nghĩa một câu**

> AIEOS là một **control plane độc lập với AI model**, quản lý **context, state, workflow, permissions, tasks, changes và verification** của quá trình phát triển phần mềm bằng AI, để nhiều AI agents có thể xây dựng một project phức tạp qua hàng trăm/hàng nghìn sessions **mà project không mất tính nhất quán và không thoát khỏi tầm kiểm soát**.

**Phép so sánh**

| Thế giới máy tính | Thế giới AIEOS |
|---|---|
| CPU / process | AI agent (Claude Code, Codex, Cursor...) chạy một session |
| Operating System | **AIEOS** |
| Chương trình đang chạy | Project đang được xây |
| Scheduler | Task scheduler + lease (ai được làm gì, khi nào) |
| Memory manager | Context compiler (nạp đúng context vào "RAM" hữu hạn của model) |
| File system | Canonical project state |
| Permissions / syscalls | Policy engine + AIEOS tools (MCP) |
| Device drivers | Runtime adapters |
| Audit log | Event log + evidence |

**Ý tưởng then chốt mà bản gốc mới chạm tới nhưng chưa nói rõ:**

1. **AI agent là một worker không có trí nhớ, context hữu hạn, và tự báo cáo không đáng tin.** Mọi thiết kế của AIEOS đều xuất phát từ ba tính chất này.
2. **State phải sống bên ngoài model.** Model là thứ có thể thay, state thì không.
3. **Không tin lời agent, chỉ tin evidence có thể kiểm chứng.**
4. **Code là sự thật về "cái đã có"; AIEOS là sự thật về "cái được dự định".** Nhiệm vụ của AIEOS là liên tục đối chiếu (reconcile) hai thứ này.

---

## 1. Vấn đề cốt lõi — cụ thể hoá

Bản gốc nêu vấn đề: *"AI build phần mềm phức tạp qua nhiều session mà không bị mất context, drift, mâu thuẫn, trùng lặp, phá architecture, tự ý đổi yêu cầu"*. Để thiết kế được giải pháp, cần tách thành các **failure mode** cụ thể và **nguyên nhân gốc**:

| # | Failure mode | Biểu hiện | Nguyên nhân gốc |
|---|---|---|---|
| F1 | **Mất context** | Session mới không biết quyết định cũ, làm lại hoặc làm ngược | Agent stateless; conversation history không phải nguồn sự thật |
| F2 | **Context sai / thừa** | Agent bị nhồi quá nhiều tài liệu, bỏ sót điều quan trọng | Context window hữu hạn, không có cơ chế chọn lọc |
| F3 | **Drift kiến trúc** | Mỗi session thêm một pattern mới, module phụ thuộc lung tung | Agent tối ưu cục bộ cho task, không thấy toàn cục |
| F4 | **Scope creep** | Sửa task A nhưng "tiện tay" refactor B, C | Không có ranh giới scope được enforce |
| F5 | **Hallucinated completion** | "Done!" nhưng test không chạy, feature thiếu nửa | Agent tự đánh giá chính mình |
| F6 | **Thay đổi yêu cầu ngầm** | Agent "hiểu lại" requirement, code lệch spec | Requirement không có trạng thái khoá / không có change control |
| F7 | **Trùng lặp & xung đột** | 2 agent cùng sửa 1 module, 2 utility function giống nhau | Không có điều phối, không có registry |
| F8 | **Verification cũ** | Test đã pass tuần trước, code đã đổi nhưng vẫn coi là "verified" | Evidence không gắn với phiên bản code cụ thể |
| F9 | **Không truy vết được** | Không biết tại sao dòng code này tồn tại | Không có liên kết requirement → code |
| F10 | **Kẹt / lặp vô hạn** | Agent sửa đi sửa lại cùng một lỗi, đốt token | Không có stop condition, budget, escalation |

> **Tiêu chí thành công của AIEOS:** mỗi failure mode trên đều phải có ít nhất một **cơ chế cụ thể** chặn nó (xem mục 7).

---

## 2. Ranh giới: AIEOS là gì và KHÔNG là gì

### AIEOS LÀ
- **Control plane**: quyết định *ai làm gì, với context nào, trong phạm vi nào, và khi nào được coi là xong*.
- **Nguồn sự thật (system of record)** cho intent, quyết định, tiến độ, evidence của project.
- **Lớp governance** đứng giữa con người và các AI agents.

### AIEOS KHÔNG LÀ (non-goals)
- ❌ Không phải AI coding agent — không tự viết code.
- ❌ Không phải IDE.
- ❌ Không thay Git — Git vẫn là nguồn sự thật về code.
- ❌ Không thay CI — AIEOS *gọi* CI/test runner và thu evidence.
- ❌ Không phải Jira cho con người — người dùng chính của task graph là AI; con người là người phê duyệt.
- ❌ Không phải LLM framework / orchestration library (LangChain, v.v.).

### Vị trí trong hệ thống

```text
                  ┌──────────────────────────┐
                  │          HUMAN           │  intent, approval, quyết định
                  └────────────┬─────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                           AIEOS                             │
│  State · Context · Tasks · Policy · Verification · Changes  │
└───────┬──────────────────┬──────────────────┬───────────────┘
        │ adapter          │ adapter          │ adapter
   ┌────▼─────┐       ┌────▼─────┐       ┌────▼─────┐
   │ Claude   │       │  Codex   │       │ Cursor / │
   │  Code    │       │          │       │ Gemini…  │
   └────┬─────┘       └────┬─────┘       └────┬─────┘
        └──────────────────┼──────────────────┘
                           ▼
              ┌────────────────────────┐
              │ Repository (Git) + CI  │  ← sự thật về code
              └────────────────────────┘
```

---

## 3. Nguyên lý thiết kế

| # | Nguyên lý | Ý nghĩa |
|---|---|---|
| P1 | **State outside the model** | Mọi thứ cần nhớ phải nằm trong AIEOS, không trong chat history hay "trí nhớ" của model. |
| P2 | **Agent is untrusted** | Agent là worker có năng lực nhưng không đáng tin tuyệt đối. Mọi output phải qua kiểm tra. |
| P3 | **Evidence over claims** | "Done" chỉ có nghĩa khi có evidence máy kiểm chứng được, gắn với commit cụ thể. |
| P4 | **Smallest sufficient context** | Cấp context *đủ* cho task, không phải *tất cả*. Context là tài nguyên khan hiếm. |
| P5 | **Explicit scope, fail closed** | Thứ không được cho phép rõ ràng thì bị cấm. Mơ hồ → dừng và hỏi. |
| P6 | **Separation of duties** | Agent viết code không được là agent duy nhất verify code đó. |
| P7 | **Everything is traceable** | Mỗi thay đổi có chuỗi Intent → Requirement → Spec → Task → Change → Evidence. |
| P8 | **Upstream change invalidates downstream** | Spec đổi → task/verification liên quan tự động thành `STALE`. |
| P9 | **Model-agnostic core** | Core không biết Claude hay Codex là gì. Mọi thứ đặc thù nằm trong adapter. |
| P10 | **Process proportional to risk** | Sửa typo không cần quy trình như đổi schema DB. Governance phải có "cấp độ". |

> P10 rất quan trọng: rủi ro lớn nhất của AIEOS là **trở nên quá nặng nề** đến mức không ai muốn dùng.

---

## 4. Mô hình khái niệm (Domain Model)

Đây là phần bản gốc còn thiếu nhiều nhất: **các đối tượng cụ thể mà AIEOS quản lý** và quan hệ giữa chúng.

### 4.1. Ba lớp state

```text
┌─────────────────────────────────────────────────────────────┐
│ 1. INTENT STATE   — "Chúng ta muốn xây gì, tại sao"         │
│    Vision, Requirement, Spec, Architecture, Decision,       │
│    Invariant, Convention                                    │
├─────────────────────────────────────────────────────────────┤
│ 2. EXECUTION STATE — "Đang làm gì, ai làm, đến đâu"         │
│    Plan/Milestone, Task, Dependency, Lease, Session,        │
│    Handoff, Change Request, Approval                        │
├─────────────────────────────────────────────────────────────┤
│ 3. EVIDENCE STATE — "Điều gì đã được chứng minh"            │
│    Change (commit/diff), Verification Run, Evidence,        │
│    Review, Release                                          │
└─────────────────────────────────────────────────────────────┘
          ↕ reconcile liên tục với ↕
┌─────────────────────────────────────────────────────────────┐
│ REALITY — Repository thật (code, tests, dependency graph)   │
└─────────────────────────────────────────────────────────────┘
```

### 4.2. Các thực thể chính

| Thực thể | ID ví dụ | Mô tả | Trạng thái chính |
|---|---|---|---|
| **Vision** | `VIS-1` | Mục tiêu sản phẩm, người dùng, phạm vi | — |
| **Requirement** | `REQ-012` | Điều hệ thống phải làm (WHAT + WHY) | draft → approved → changed → retired |
| **Spec** | `SPEC-012.3` | Chi tiết hoá requirement, có **acceptance criteria** kiểm chứng được | draft → approved → stale |
| **Architecture Component** | `ARC-auth` | Module/bounded context, trách nhiệm, interface, ranh giới | — |
| **Invariant** | `INV-007` | Luật luôn đúng, **máy kiểm tra được** (vd: `domain/` không import `infra/`) | active / waived |
| **Decision (ADR)** | `ADR-031` | Quyết định kỹ thuật + lý do + phương án bị loại | proposed → accepted → superseded |
| **Convention** | `CONV-naming` | Quy ước code (naming, error handling, logging…) | — |
| **Task** | `TASK-142` | Đơn vị công việc nguyên tử cho 1 agent/1 session | xem state machine 6.2 |
| **Lease** | `LSE-…` | Quyền tạm thời của 1 session trên 1 task + 1 file scope | active → released / expired |
| **Session** | `SES-…` | Một lần chạy của 1 agent | — |
| **Handoff** | `HND-…` | Bản ghi có cấu trúc khi session kết thúc | — |
| **Change** | commit SHA | Diff thực tế, gắn với task | — |
| **Verification Run** | `VRF-…` | Một lần chạy kiểm tra, gắn với **commit SHA** | pass / fail / stale |
| **Evidence** | `EVD-…` | Output kiểm chứng: test report, log, screenshot, review | — |
| **Change Request** | `CR-009` | Đề xuất thay đổi Intent State (requirement/spec/architecture) | proposed → approved/rejected |
| **Approval** | `APR-…` | Quyết định của người có thẩm quyền | — |

### 4.3. Traceability graph

```text
VIS-1
 └── REQ-012  "User có thể reset password qua email"
      ├── SPEC-012.1  AC: token hết hạn sau 15 phút
      ├── SPEC-012.2  AC: không tiết lộ email có tồn tại hay không
      │    │
      │    ├── constrained by: ARC-auth, INV-007, ADR-031
      │    │
      │    └── TASK-142  "Implement POST /auth/reset-request"
      │         ├── change:   a1b2c3d
      │         ├── verified: VRF-880 (@a1b2c3d) ✅
      │         └── evidence: EVD-2201 (test report), EVD-2202 (review)
      └── ...
```

Graph này cho phép trả lời *mọi câu hỏi trong bản gốc* bằng **truy vấn**, không cần "nhớ":
- "Tại sao dòng code này tồn tại?" → commit → task → spec → requirement.
- "Requirement này đã xong chưa?" → mọi spec có AC được verify ở commit hiện tại?
- "Đổi ADR-031 thì ảnh hưởng gì?" → mọi task/spec phụ thuộc → đánh dấu `STALE`.

---

## 5. Kiến trúc hệ thống

```text
┌─────────────────────────────────────────────────────────────────────┐
│                          AIEOS CORE                                 │
│                                                                     │
│  ┌───────────────┐   ┌────────────────┐   ┌──────────────────────┐  │
│  │ State Store   │◄──│  Event Log     │   │  Policy Engine       │  │
│  │ (projection)  │   │ (append-only)  │   │  permissions, gates, │  │
│  └──────┬────────┘   └────────────────┘   │  autonomy levels     │  │
│         │                                 └──────────┬───────────┘  │
│  ┌──────▼────────┐   ┌────────────────┐   ┌──────────▼───────────┐  │
│  │ Planner /     │   │ Scheduler &    │   │  Context Compiler    │  │
│  │ Task Graph    │──►│ Lease Manager  │──►│  → Work Order        │  │
│  └───────────────┘   └────────────────┘   └──────────┬───────────┘  │
│                                                      │              │
│  ┌───────────────┐   ┌────────────────┐              │              │
│  │ Change Mgr    │   │ Verification   │◄─── result ──┤              │
│  │ CR, impact,   │   │ Engine (gates) │              │              │
│  │ staleness     │   └────────────────┘              │              │
│  └───────────────┘                                   │              │
│  ┌───────────────┐                                   │              │
│  │ Reconciler    │  so sánh State ↔ Repo, phát hiện drift           │
│  └───────────────┘                                   │              │
└──────────────────────────────────────────────────────┼──────────────┘
                     AIEOS Protocol (CLI + MCP + API)  │
        ┌──────────────────┬───────────────────────────┤
   ┌────▼─────┐       ┌────▼─────┐               ┌─────▼────┐
   │ Adapter: │       │ Adapter: │               │ Human UI │
   │ Claude   │       │ Codex    │   ...         │ CLI/Web  │
   └──────────┘       └──────────┘               └──────────┘
```

### Mô tả từng thành phần

| Thành phần | Trách nhiệm | Chặn failure mode |
|---|---|---|
| **Event Log** | Mọi thay đổi state là một event bất biến (`TaskClaimed`, `SpecApproved`, `VerificationPassed`…). Có thể replay, audit. | F9 |
| **State Store** | Projection đọc nhanh từ event log. | F1 |
| **Planner / Task Graph** | Phân rã Requirement → Spec → Task; quản lý dependency DAG. AI có thể *đề xuất*, con người *phê duyệt*. | F7 |
| **Scheduler & Lease Manager** | Chọn task `READY` tiếp theo; cấp lease độc quyền trên task + file scope; hết hạn thì thu hồi. | F7 |
| **Context Compiler** | Biên dịch "Work Order": chỉ những gì task cần, trong ngân sách token. | F1, F2 |
| **Policy Engine** | Quyết định cái gì được phép, cái gì cần approval, theo risk level. | F4, F6 |
| **Verification Engine** | Chạy chuỗi gate, thu evidence gắn commit SHA. | F5, F8 |
| **Change Manager** | Xử lý Change Request lên Intent State, tính impact, lan truyền `STALE`. | F6, F8 |
| **Reconciler** | Định kỳ so sánh state với repo thật: file ngoài scope bị sửa? invariant bị vi phạm? code không thuộc task nào? | F3, F4 |
| **Watchdog** | Theo dõi budget, số lần retry, vòng lặp → escalate. | F10 |

---

## 6. Vòng đời công việc

### 6.1. Vòng lặp lõi (Core Loop)

```text
   ┌──────────────────────────────────────────────────────────────┐
   │                                                              │
   ▼                                                              │
[1] SELECT      Scheduler chọn task READY (dependencies đã xong)  │
   ▼                                                              │
[2] LEASE       Cấp lease: task + file scope + thời hạn + budget  │
   ▼                                                              │
[3] COMPILE     Context Compiler tạo Work Order                   │
   ▼                                                              │
[4] DISPATCH    Adapter chuyển Work Order thành định dạng native  │
   ▼            (CLAUDE.md/AGENTS.md/rules/hooks) và khởi chạy    │
[5] EXECUTE     Agent làm việc; gọi AIEOS tools khi cần           │
   ▼            (hỏi decision, báo blocker, checkpoint)           │
[6] SUBMIT      Agent nộp: diff + structured report               │
   ▼                                                              │
[7] VERIFY      Gate 0→4 (mục 7.4), evidence gắn commit SHA       │
   ▼                                                              │
[8] ACCEPT      Theo policy: auto-accept hoặc chờ human approval  │
   ▼                                                              │
[9] RECORD      Cập nhật state, handoff, unblock task phụ thuộc ──┘
```

### 6.2. State machine của Task

```text
DRAFT ──approve──► READY ──lease──► IN_PROGRESS ──submit──► VERIFYING
  ▲                  ▲                  │    │                  │
  │                  │             blocked  lease expired       ├─ fail ──► REWORK ──► IN_PROGRESS
  │                  │                  ▼    │                  │              (retry ≤ N, quá N → ESCALATED)
  │                  └──── unblock ── BLOCKED◄┘                 ▼
  │                                                         VERIFIED
  │                                                             │
  │                                          policy/human ──────┤
  │                                                             ▼
  │                                                         ACCEPTED ──► DONE (merged)
  │
  └──── upstream spec/ADR đổi ──── STALE ◄──── (từ bất kỳ trạng thái nào sau READY)
```

### 6.3. Giao thức Session (Session Protocol)

Mỗi session, với bất kỳ agent nào, đều đi qua cùng một giao thức:

1. **Boot** — Agent nhận Work Order (không đọc lịch sử chat cũ).
2. **Acknowledge** — Agent xác nhận đã hiểu task, liệt kê giả định. Nếu mơ hồ → `request_clarification`, không đoán.
3. **Work** — Làm trong scope. Có thể `checkpoint` tiến độ.
4. **Submit** — Nộp diff + report có cấu trúc (đã làm gì, chưa làm gì, giả định, rủi ro, đề xuất).
5. **Handoff** — AIEOS lưu Handoff. Session sau (dù là agent khác) đọc Handoff này thay vì "nhớ".

---

## 7. Cơ chế cho từng trụ cột

Bản gốc có 5 trụ cột (Context, Control, Continuity, Verification, Traceability). Đề xuất bổ sung thêm 2: **Coordination** và **Evolution**, vì đây là hai vấn đề sẽ xuất hiện ngay khi project lớn và có nhiều agent.

### 7.1. Context — "đúng context, đủ context, không thừa"

**Work Order** là sản phẩm của Context Compiler. Ví dụ:

```yaml
work_order: WO-142-1
task: TASK-142
title: Implement POST /auth/reset-request
goal: >
  Cho phép user yêu cầu email reset password mà không tiết lộ email có tồn tại hay không.

traces_to: [REQ-012, SPEC-012.1, SPEC-012.2]

acceptance_criteria:          # Điều kiện "xong" — kiểm chứng được
  - AC1: Luôn trả 202 dù email có tồn tại hay không
  - AC2: Token lưu dạng hash, hết hạn sau 15 phút
  - AC3: Rate limit 5 request/giờ/IP

scope:
  allowed_paths:  [src/auth/reset/**, tests/auth/reset/**]
  read_only:      [src/auth/core/**, src/shared/**]
  forbidden:      [migrations/**, src/billing/**]

constraints:                  # Chỉ những rule LIÊN QUAN tới task này
  - INV-007: domain/ không import infra/
  - ADR-031: Dùng EmailPort, không gọi SMTP trực tiếp
  - CONV-errors: Dùng Result<T,E>, không throw trong domain

relevant_context:             # Đã được chọn lọc
  - file: src/auth/core/token.ts         (interface TokenService)
  - file: src/shared/email/port.ts       (EmailPort)
  - handoff: HND-139                      (task trước đã tạo bảng reset_tokens)

definition_of_done:
  - tests mới cho AC1–AC3 pass
  - toàn bộ test suite auth pass
  - lint + typecheck pass
  - không sửa file ngoài allowed_paths

budget: { max_tokens: 400k, max_wall_time: 45m, max_retries: 3 }

stop_and_ask_if:
  - cần sửa file ngoài scope
  - cần đổi schema DB
  - acceptance criteria mâu thuẫn với code hiện có
```

**Kỹ thuật biên dịch context:**
- **Phân tầng**: Global (vision tóm tắt, invariants cốt lõi) → Component (ARC liên quan) → Task (spec, AC, file) → Handoff gần nhất.
- **Chọn lọc theo graph**: đi theo traceability graph + dependency graph của code, không tìm kiếm mù.
- **Ngân sách token**: mỗi tầng có budget; vượt thì tóm tắt hoặc chuyển thành "tham chiếu, agent tự đọc nếu cần".
- **Pull thay vì push**: thứ không chắc cần thì không nhồi vào, mà để agent truy vấn qua AIEOS tools (`aieos.get_decision("ADR-031")`).

### 7.2. Control — "chỉ làm những gì được phép"

Kiểm soát ở **3 thời điểm**:

| Thời điểm | Cơ chế | Ví dụ |
|---|---|---|
| **Trước** (preventive) | Work Order giới hạn scope; adapter cấu hình permission native của runtime | Claude Code: hooks/permissions chặn ghi ngoài `allowed_paths` |
| **Trong** (runtime) | Hook/tool guard; agent phải gọi `request_approval` cho hành động nhạy cảm | Định cấm `rm -rf`, `git push --force`, sửa migration |
| **Sau** (detective) | Gate kiểm tra diff: file ngoài scope, invariant vi phạm | Diff đụng `src/billing/` → reject tự động |

> Nguyên tắc: **runtime nào không enforce được trước/trong, thì sau vẫn phải chặn được.** Kiểm tra sau (diff-based) là lớp bảo vệ cuối cùng, không phụ thuộc agent nào.

**Policy theo mức rủi ro (P10):**

```yaml
policies:
  - match: { paths: ["docs/**", "*.md"] }
    risk: low
    approval: auto
  - match: { paths: ["src/**"] }
    risk: medium
    approval: auto_if_all_gates_pass
  - match: { paths: ["migrations/**", "src/auth/**", "infra/**"] }
    risk: high
    approval: human_required
  - match: { changes: [requirement, spec, architecture, invariant] }
    risk: critical
    approval: human_required + change_request
```

### 7.3. Continuity — "tiếp tục chính xác qua mọi session"

- **Không có session nào là nguồn sự thật.** Session chỉ đọc/ghi state qua AIEOS.
- **Handoff có cấu trúc** (không phải văn bản tự do):

```yaml
handoff: HND-142
task: TASK-142
status: submitted
done:         [AC1, AC2]
not_done:     [AC3 — rate limiter chưa có, tạo TASK-151 đề xuất]
assumptions:  ["Dùng Redis có sẵn cho rate limit"]
discoveries:  ["TokenService thiếu method revokeAll — cần cho REQ-013"]
risks:        ["Test email dùng mock, chưa test với provider thật"]
proposed:     [{ type: new_task, title: "Rate limit reset endpoint" }]
```

- **Discoveries và proposals không tự động thành sự thật** — chúng vào hàng đợi để human/planner xử lý. Agent không được tự tạo requirement.
- **Knowledge consolidation**: định kỳ gom discoveries/conventions lặp lại thành Convention hoặc ADR chính thức; xoá thứ lỗi thời.

### 7.4. Verification — "Done = có evidence"

**Chuỗi gate (Verification Pipeline):**

| Gate | Loại | Kiểm tra | Ai làm |
|---|---|---|---|
| **G0 Scope** | Deterministic | Diff chỉ nằm trong `allowed_paths` | AIEOS |
| **G1 Build** | Deterministic | Build, lint, typecheck, format | CI/tool |
| **G2 Tests** | Deterministic | Test mới + test regression pass; coverage cho AC | CI/tool |
| **G3 Architecture** | Deterministic | Invariants (dependency rules, layer rules, forbidden APIs) | Tool (vd: dependency-cruiser, ArchUnit) |
| **G4 Spec conformance** | AI review | Code có thực sự đáp ứng từng AC không? Có làm thừa không? | **Agent khác** (P6), có thể model khác |
| **G5 Human review** | Human | Theo policy risk level | Con người |

**Quy tắc evidence:**
- Evidence **luôn gắn commit SHA**. Code đổi → verification cũ tự động `STALE` (chặn F8).
- Evidence phải do **AIEOS/CI tạo ra**, không phải do agent tự viết "tests passed" (chặn F5).
- Mỗi AC phải map tới ít nhất một evidence (test cụ thể, hoặc review cụ thể).

### 7.5. Traceability — "mọi thay đổi đều có lý do"

- Commit message / trailer bắt buộc: `AIEOS-Task: TASK-142`.
- Reconciler phát hiện **code mồ côi**: thay đổi không thuộc task nào → cảnh báo.
- Truy vấn hai chiều: Requirement → code, và code → Requirement.
- Coverage report cấp sản phẩm: *"REQ-012: 3/3 spec verified tại commit HEAD"*.

### 7.6. Coordination — "nhiều agent không giẫm chân nhau" *(mới)*

- **Lease độc quyền** trên task + file scope; hai task có scope chồng nhau không chạy song song (hoặc chạy trên branch/worktree riêng rồi merge theo thứ tự).
- **Dependency DAG**: chỉ task có mọi dependency `DONE` mới `READY`.
- **Registry**: danh mục component/utility/API đã có → đưa vào context để agent dùng lại thay vì viết mới (chặn F7 trùng lặp).
- **Role-based agents**: Planner, Implementer, Reviewer, Fixer — có thể là model khác nhau, mỗi role có quyền khác nhau.

### 7.7. Evolution — "project thay đổi có kiểm soát" *(mới)*

Requirement **sẽ** thay đổi. Vấn đề không phải ngăn thay đổi mà là **thay đổi có ý thức**:

```text
Change Request CR-009: "Token hết hạn 30 phút thay vì 15"
   ▼
Impact Analysis (tự động theo traceability graph)
   → SPEC-012.1, TASK-142 (DONE), VRF-880, tests/auth/reset/expiry.test.ts
   ▼
Approval (human)
   ▼
Apply: SPEC-012.1 v2 → TASK-142 chuyển STALE → sinh TASK-160 "Update expiry to 30m"
```

- Agent **không bao giờ** được sửa Intent State trực tiếp — chỉ được đề xuất CR (chặn F6).
- Mọi artifact Intent có **version**; task ghi lại nó được làm theo version nào.

---

## 8. Adapter — lớp độc lập với AI model

### 8.1. Hợp đồng (Adapter Contract)

Mỗi adapter phải cung cấp:

| Khả năng | Mô tả |
|---|---|
| `render(work_order)` | Chuyển Work Order sang định dạng native: `CLAUDE.md`, `AGENTS.md`, `.cursor/rules`, system prompt… |
| `configure(policy)` | Ánh xạ permission/scope sang cơ chế native (hooks, allowlist, sandbox) |
| `launch(session)` | Khởi chạy agent (headless/CLI/SDK) hoặc hướng dẫn người dùng khởi chạy |
| `connect_tools()` | Cho agent truy cập AIEOS tools (ưu tiên qua **MCP**) |
| `collect(result)` | Thu diff, log, report có cấu trúc |
| `capabilities()` | Khai báo runtime enforce được gì |

### 8.2. Capability tiers

Không phải runtime nào cũng hỗ trợ như nhau. AIEOS phải hoạt động ở **mọi tier**, chỉ khác mức đảm bảo:

| Tier | Runtime có | AIEOS làm được |
|---|---|---|
| **T0 — Manual** | Chỉ có chat | Xuất Work Order để copy-paste; kiểm tra sau bằng diff |
| **T1 — Instructions** | Đọc file rules (AGENTS.md…) | Tự sinh rules file; kiểm tra sau |
| **T2 — Tools** | Hỗ trợ MCP | Agent truy vấn context, báo cáo có cấu trúc |
| **T3 — Enforcement** | Hooks / permission / sandbox | Chặn hành động ngoài scope *trong lúc chạy* |
| **T4 — Headless** | Chạy tự động qua CLI/SDK | Điều phối hoàn toàn tự động, song song |

### 8.3. AIEOS Protocol (các tool agent gọi)

```text
aieos.get_work_order()            aieos.report_progress(checkpoint)
aieos.get_spec(id)                aieos.report_blocker(reason)
aieos.get_decision(id)            aieos.request_clarification(question)
aieos.search_registry(query)      aieos.request_approval(action)
aieos.get_handoff(task)           aieos.propose(task | cr | adr)
                                  aieos.submit(report)
```

> Chiến lược: **MCP server là kênh tích hợp chính**, vì hầu hết các coding agent hiện đại đều hỗ trợ. CLI là kênh dự phòng và kênh cho con người.

---

## 9. Vai trò con người

AIEOS không loại bỏ con người — nó **dời con người lên vị trí có đòn bẩy cao nhất**: định nghĩa intent và phê duyệt quyết định, thay vì review từng dòng code.

### 9.1. Vai trò

| Vai trò | Làm gì |
|---|---|
| **Owner / Product** | Vision, requirement, ưu tiên, phê duyệt CR |
| **Architect** | Architecture, invariant, ADR quan trọng |
| **Reviewer** | Phê duyệt thay đổi rủi ro cao |
| **Operator** | Theo dõi hệ thống, xử lý escalation |

(Một người có thể giữ mọi vai trò — đặc biệt ở giai đoạn đầu.)

### 9.2. Mức tự chủ (Autonomy Levels)

| Level | Mô tả |
|---|---|
| **L0** | AI chỉ đề xuất; con người làm và duyệt mọi thứ |
| **L1** | AI implement; con người duyệt mọi task |
| **L2** | AI implement + auto-accept task low/medium risk khi pass mọi gate |
| **L3** | AI tự plan task trong requirement đã duyệt; con người duyệt requirement/architecture |
| **L4** | AI đề xuất cả requirement; con người duyệt ở mức milestone |

Project có thể nâng dần level khi **metrics chứng minh độ tin cậy** (mục 12).

---

## 10. Xử lý thất bại & Stop Conditions

| Tình huống | Phát hiện | Phản ứng |
|---|---|---|
| Agent cần sửa ngoài scope | Hook / G0 | Dừng, `request_approval` hoặc tạo task mới |
| Spec mơ hồ / mâu thuẫn | Agent báo / G4 | `BLOCKED` + câu hỏi cho human |
| Fail gate lặp lại | Retry counter | Sau N lần → `ESCALATED`, đổi agent/model hoặc hỏi human |
| Vượt budget token/thời gian | Watchdog | Thu hồi lease, lưu checkpoint, escalate |
| Lặp vô hạn (sửa đi sửa lại) | Diff tương tự liên tiếp | Dừng ngay |
| Code drift (sửa ngoài AIEOS) | Reconciler | Tạo "reconciliation task" để con người xác nhận |
| Agent hỏng giữa chừng | Lease hết hạn | Trả task về `READY`, giữ checkpoint |
| Kết quả sai đã merge | Phát hiện sau | Revert theo task (vì mỗi task = 1 changeset rõ ràng) |

---

## 11. Lưu trữ & định dạng

**Khuyến nghị: Git-native cho Intent, local store cho runtime.**

```text
repo/
├── .aieos/
│   ├── project.yaml              # cấu hình, policy, autonomy level
│   ├── intent/
│   │   ├── vision.md
│   │   ├── requirements/REQ-012.md
│   │   ├── specs/SPEC-012.1.md
│   │   ├── architecture/ARC-auth.md
│   │   ├── invariants.yaml       # luật máy kiểm tra được
│   │   ├── decisions/ADR-031.md
│   │   └── conventions/
│   ├── tasks/TASK-142.yaml
│   ├── handoffs/HND-142.yaml
│   ├── evidence/                 # hoặc chỉ lưu tham chiếu tới CI artifact
│   └── events.jsonl              # event log append-only
└── src/ ...
```

- **Ưu điểm**: version cùng code, review qua PR, branch được, không vendor lock-in, AI đọc được trực tiếp.
- **Nhược điểm**: concurrency khi nhiều agent ghi → giải quyết bằng: chỉ AIEOS core ghi `.aieos/` (agent ghi qua protocol), runtime state nóng (lease, session) để trong SQLite local, không commit.
- Về sau (bản team/cloud): đồng bộ lên server, nhưng **file trong repo vẫn là định dạng chuẩn**.

---

## 12. Đo lường — làm sao biết AIEOS hiệu quả?

| Metric | Ý nghĩa |
|---|---|
| **First-pass verification rate** | % task pass mọi gate ngay lần nộp đầu |
| **Scope violation rate** | % session đụng file ngoài scope |
| **Escalation rate** | % task cần con người can thiệp |
| **Rework rate** | % task `DONE` bị mở lại / revert |
| **Drift incidents** | Số lần Reconciler phát hiện vi phạm invariant / code mồ côi |
| **Traceability coverage** | % code thay đổi có task, % requirement có evidence |
| **Cost per accepted task** | Token + thời gian / task được accept |
| **Human time per task** | Thời gian con người bỏ ra / task |

> Câu hỏi then chốt cho startup: **project dùng AIEOS có đi xa hơn (nhiều task hơn, ít drift hơn) với ít công sức con người hơn so với không dùng không?** Cần benchmark được điều này.

---

## 13. Ví dụ end-to-end

```text
1. Human:   "Thêm tính năng reset password."
2. AIEOS:   Planner-agent đề xuất REQ-012 + 3 spec + 4 task. Human duyệt.
3. AIEOS:   TASK-140 (DB table) READY → lease cho Codex.
4. Codex:   Implement, submit. G0–G3 pass. Risk=high (migration) → chờ human. Human duyệt. DONE.
5. AIEOS:   TASK-142 unblock → lease cho Claude Code, Work Order kèm HND-140.
6. Claude:  Làm AC1, AC2. Phát hiện cần rate limiter (ngoài scope) → propose TASK-151, không tự làm.
7. AIEOS:   G0–G3 pass. G4: Reviewer-agent (model khác) phát hiện AC3 chưa có test → REWORK.
8. Claude:  Session mới (không nhớ gì) → đọc Work Order + HND-142 → bổ sung đúng phần thiếu.
9. AIEOS:   Pass mọi gate. Risk=medium → auto-accept (L2). Evidence gắn SHA a1b2c3d.
10. Human:  Một tháng sau, CR-009 đổi thời hạn token → AIEOS đánh dấu TASK-142 STALE,
            tự sinh TASK-160 với đúng context cần thiết.
```

---

## 14. Định vị & khác biệt

| | Giải quyết | AIEOS khác ở |
|---|---|---|
| **Jira / Linear** | Task cho con người | Task cho AI, gắn với spec, context, evidence |
| **Git** | Code đổi như thế nào | *Tại sao* đổi, ai được phép, đã chứng minh chưa |
| **CI** | Code có build/pass test không | CI là một gate; AIEOS biết test đó chứng minh *requirement nào* |
| **CLAUDE.md / AGENTS.md / rules** | Hướng dẫn tĩnh cho 1 agent | Là *output* được AIEOS sinh ra theo từng task |
| **Claude Code / Codex / Cursor** | Viết code | Là worker; AIEOS điều phối chúng |
| **Các công cụ spec-driven / task-manager cho AI** *(cần nghiên cứu kỹ đối thủ)* | Spec → task cho một agent | AIEOS nhấn mạnh: đa agent, đa model, governance, evidence, vòng đời dài |

**Moat tiềm năng:**
1. Định dạng project state mở, trở thành chuẩn (như `package.json` cho dependency).
2. Dữ liệu về hiệu quả: agent/model nào làm tốt loại task nào → scheduler thông minh hơn.
3. Trung lập với nhà cung cấp model — điều mà Anthropic/OpenAI/Cursor khó làm vì họ có động lực khoá người dùng vào runtime của mình.

---

## 15. Rủi ro & cách giảm thiểu

| Rủi ro | Giảm thiểu |
|---|---|
| **Quá nặng nề** — quy trình làm chậm hơn cả không dùng | P10: governance theo risk; mặc định nhẹ; "fast lane" cho task nhỏ |
| **State tự nó drift** khỏi code | Reconciler; code là sự thật về hiện trạng; state chỉ là intent + evidence |
| **Spec rot** — tài liệu lỗi thời | Spec phải có AC gắn test; spec không có evidence → cảnh báo |
| **Chi phí verification cao** (AI review tốn token) | G0–G3 deterministic chạy trước, rẻ; G4 chỉ khi cần |
| **Adapter lạc hậu** khi runtime thay đổi nhanh | Contract tối thiểu; T0/T1 luôn hoạt động; adapter là plugin |
| **Nhà cung cấp model tự làm** tính năng tương tự | Tập trung vào đa model + governance + định dạng mở |
| **Cold start**: project đang có, chưa có state | Chế độ "import": AI quét repo, đề xuất architecture/invariant ban đầu, human duyệt |

---

## 16. MVP & Roadmap

### MVP (v0.1) — chứng minh vòng lặp lõi

**Mục tiêu:** một người + Claude Code (+ Codex) build một project vừa (~100 task) mà ít drift hơn rõ rệt.

Phạm vi:
- [ ] `.aieos/` file format: requirement, spec (có AC), ADR, invariant, task, handoff
- [ ] CLI: `aieos init`, `aieos task next`, `aieos task start`, `aieos verify`, `aieos status`, `aieos trace`
- [ ] Context Compiler v1: sinh Work Order từ task + graph (không cần semantic search)
- [ ] MCP server với ~8 tool cốt lõi
- [ ] Adapter Claude Code (T3: dùng hooks để enforce scope) + adapter Codex (T1/T2)
- [ ] Verification G0–G3 (scope, build/lint/test, invariant cơ bản)
- [ ] Event log + `STALE` khi commit đổi
- [ ] Tuần tự (1 agent tại một thời điểm) — chưa song song

**Không có trong MVP:** web UI, multi-user, chạy song song, G4 AI review tự động, cloud.

### v0.2 — Độ tin cậy
- G4 cross-model review, Change Request + impact analysis, Reconciler, metrics dashboard (CLI).

### v0.3 — Song song & đa agent
- Lease + worktree, chạy nhiều agent song song, role-based agents, adapter Cursor/Gemini.

### v1.0 — Team & sản phẩm
- Web UI, multi-user, approval workflow, đồng bộ cloud, chế độ import cho repo có sẵn.

### Cách tốt nhất để kiểm chứng ý tưởng
> **Dùng AIEOS để build chính AIEOS** (dogfooding) từ v0.1 trở đi. Mọi điểm đau sẽ lộ ra rất nhanh.

---

## 17. Câu hỏi mở cần quyết định

1. **Người dùng mục tiêu đầu tiên** là ai? Solo developer dùng AI build sản phẩm lớn / team nhỏ / doanh nghiệp cần compliance? (Quyết định mức nặng nhẹ của governance.)
2. **Ai viết requirement/spec?** Con người viết, hay AI soạn và con người duyệt? (Khuyến nghị: AI soạn, con người duyệt.)
3. **Mức độ tự động của dispatch**: AIEOS tự khởi chạy agent (headless), hay con người mở agent và agent "kéo" Work Order qua MCP? (Khuyến nghị MVP: kéo qua MCP — đơn giản, tương thích rộng.)
4. **Ngôn ngữ/stack đầu tiên** để làm invariant checker (TypeScript? Python?).
5. **Open source hay closed?** Định dạng `.aieos/` nên mở để thành chuẩn; phần cloud/team có thể là sản phẩm thương mại.
6. **Tên gọi**: AIEOS / AI-EOS — chốt một cách viết thống nhất.

---

## Phụ lục: Định nghĩa cuối cùng

> **AIEOS là một control plane độc lập với AI model, quản lý context, state, workflow, permissions, tasks, changes và verification của quá trình phát triển phần mềm bằng AI — để nhiều AI agents có thể xây dựng một project phức tạp qua hàng trăm/hàng nghìn sessions mà không làm mất tính nhất quán và khả năng kiểm soát của project.**

> **AIEOS = hệ điều hành cho việc xây dựng phần mềm bằng AI.**
> Claude / Codex / Cursor là **developers**.
> Project là **system being built**.
> AIEOS là **operating system** điều phối và kiểm soát các AI developers đó —
> bằng cách giữ **state bên ngoài model**, cấp **đúng context** cho từng task, **giới hạn phạm vi** hành động, và chỉ chấp nhận kết quả khi có **evidence**.
