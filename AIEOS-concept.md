# AIEOS — Control Plane for AI Software Engineering

> **Concept Document v0.4**
> Ngày: 2026-10-04 · Trạng thái: Draft
> v0.3: chuyển trọng tâm từ *"giúp AI tiếp tục làm việc"* sang *"đảm bảo AI không làm project sai"*; gom mô hình về 5 primitives; thêm Constitution, Truth Hierarchy, Capability Boundary, Risk → Autonomy, Assurance Levels, Change Impact Engine, Zero-friction path, ICP.
> v0.4: tái tích hợp continuity — **continuity là phương tiện, correctness là mục tiêu**; thêm Product Hierarchy, Correctness Loop với các verdict (CONTINUE / REPLAN / STOP), và Resume Check.

---

## 0. Thesis

| Tầng | Phát biểu |
|---|---|
| **Technical thesis** | AIEOS là một **control plane độc lập với AI model**, duy trì **intent** của project, **giới hạn** việc thực thi của agent, thu thập **evidence kiểm chứng được**, và liên tục **đối chiếu** các thay đổi do AI tạo ra với trạng thái dự định của hệ thống phần mềm. |
| **Product thesis** | AIEOS cho phép developer **giao ngày càng nhiều phần việc phát triển phần mềm cho AI agents mà không mất quyền kiểm soát project**. |
| **Killer capability** | AIEOS cho phép AI agents **làm việc liên tục qua hàng trăm session, agent và model**, trong khi vẫn duy trì **intent** của project, **ranh giới thực thi** và **tính đúng đắn có thể kiểm chứng**. |
| **Tagline** | **Agents write the code. AIEOS keeps the project correct.** |

### Continuity là phương tiện, correctness là mục tiêu

"Giúp AI tiếp tục làm việc" và "đảm bảo AI không làm project sai" **không phải hai thesis cạnh tranh** — chúng là hai tầng của cùng một hệ thống. Không có continuity thì không thể giữ correctness qua hàng trăm session; nhưng continuity *không có* correctness chỉ là memory, thứ đang bị commodity hoá nhanh.

| Continuity kiểu memory *(không bán)* | Continuity kiểu controlled execution *(AIEOS)* |
|---|---|
| Lưu summary → session sau đọc → tiếp tục | Session sau được đưa vào **trạng thái thực thi hợp lệ hiện tại** của project |
| "Hôm qua tôi đang làm gì?" | "Sau mọi thay đổi vừa xảy ra, project đang ở đâu và việc nào còn hợp lệ?" |
| "TASK-142 đã done." | "TASK-142 từng done, nhưng ADR-031 v2 đã vô hiệu giả định của nó → STALE." |
| Luôn nói **Continue** | Nói **Continue**, **Continue với Work Order này**, **Replan**, hoặc **Stop — và đây là lý do** |

> **AIEOS duy trì tính liên tục của quá trình thực thi có kiểm soát (continuity of controlled execution) qua nhiều session, agent và model.**

### Product hierarchy

```text
L1  MISSION      Keep AI-built software correct.                         (WHY)
L2  MECHANISM    Maintain a continuously reconciled project state.       (HOW)
L3  PRIMITIVES   Intent · Work · Control · Evidence · Reconciliation
L4  CAPABILITIES Context Compiler · Task Contracts · Handoffs · Resume Check
                 Capability Boundaries · Risk Engine · Autonomy Budgets
                 Verification · Evidence Graph · Change Impact · Drift Detection
L5  OUTCOME      AI làm việc lâu hơn, qua nhiều session/agent/model,
                 ít can thiệp của con người hơn —
                 MÀ KHÔNG mất correctness và quyền kiểm soát project.
```

Mọi capability ở L4 phải trả lời được: *"nó giữ correctness như thế nào?"* — nếu không trả lời được, nó không thuộc AIEOS.

> "Hệ điều hành cho việc xây dựng phần mềm bằng AI" vẫn là một **phép so sánh marketing** tốt — nhưng **không phải định nghĩa kỹ thuật**. AIEOS không sở hữu compute, process isolation, filesystem hay network. Nó *điều khiển* những hệ thống sở hữu chúng. Không để phép so sánh OS trở thành ràng buộc kiến trúc.

---

## 1. Nỗi đau — tại sao developer *phải* dùng

Kiến trúc tốt chưa đủ; cần nỗi đau đủ rõ để người ta cài và không gỡ.

### 1.1. Người dùng mục tiêu đầu tiên (ICP)

**Solo developer / team 1–5 người dùng AI agents làm phần lớn việc code trên một project phức tạp.**

- 1–5 developers, 2–10 AI agents/sessions song song hoặc nối tiếp
- Project có độ phức tạp thật: backend, SaaS, fintech, crypto, dev tools, infrastructure
- AI viết phần lớn code; con người là người định hướng và duyệt

Vì sao không bắt đầu bằng enterprise: enterprise đòi SSO, RBAC, SOC2, audit export, on-prem, data residency… trước khi core technology được chứng minh. ICP nhỏ cho feedback nhanh và thật: *"AIEOS giúp Claude Code không phá project của tôi."*

### 1.2. Các khoảnh khắc đau (pain moments)

| Khoảnh khắc | Hôm nay | Với AIEOS |
|---|---|---|
| Session mới, agent quên quyết định tuần trước và làm ngược | Phát hiện sau vài ngày, sửa tay | Work Order mang theo ADR liên quan; vi phạm bị chặn ở gate |
| Agent nói "Done, all tests pass" | Tin, merge, sau đó vỡ | Không có evidence gắn commit → không được accept |
| Agent "tiện tay" refactor module khác | Diff 40 file, không dám review | Diff ngoài scope bị từ chối tự động |
| Sau 3 tháng không biết code còn đúng kiến trúc không | Không ai biết | Reconciliation báo drift cụ thể |
| Đổi một quyết định kiến trúc | Không biết ảnh hưởng tới đâu | Impact Engine liệt kê artifact mất hiệu lực + kế hoạch revalidate |

### 1.3. "Aha moment"

> Lần đầu tiên AIEOS **chặn một thay đổi mà agent tuyên bố là xong** — kèm lý do cụ thể (invariant nào bị vi phạm, AC nào chưa có evidence).

Activation metric: số project có ít nhất 1 lần "caught" trong tuần đầu.

---

## 2. Vấn đề kỹ thuật cốt lõi

AI coding agent có ba tính chất nền tảng; mọi thiết kế của AIEOS suy ra từ đây:

1. **Không có trí nhớ bền vững** giữa các session.
2. **Context hữu hạn** và suy giảm chất lượng khi làm việc dài (context explosion, semantic drift).
3. **Tự báo cáo không đáng tin** — và tự review cũng không đáng tin.

| # | Failure mode | Primitive chặn nó |
|---|---|---|
| F1 | Mất context giữa các session | Intent, Work (handoff) |
| F2 | Context sai / thừa | Work (Context Compiler) |
| F3 | Drift kiến trúc | Constitution, Reconciliation |
| F4 | Scope creep | Control (scope, capability) |
| F5 | Hallucinated completion | Evidence |
| F6 | Tự ý thay đổi yêu cầu | Intent (change control), Truth Hierarchy |
| F7 | Trùng lặp, xung đột giữa agents | Work (lease, registry) |
| F8 | Verification cũ vẫn được tin | Evidence (gắn commit SHA) |
| F9 | Không truy vết được | Evidence graph |
| F10 | Kẹt, lặp, đốt tài nguyên | Control (budget, escalation) |
| F11 | Agent làm hành động nguy hiểm ngoài code (push, network, secrets) | Control (capability boundary) |

---

## 3. Ranh giới: Control Plane vs Execution Plane

```text
                       HUMAN AUTHORITY
                             │
┌────────────────────────────▼─────────────────────────────┐
│                  AIEOS — CONTROL PLANE                   │
│                                                          │
│  Intent · Constitution · Policy · Risk · Planning        │
│  Scheduling · Context · Verification · Evidence          │
│  Reconciliation · Impact · Audit                         │
└────────────────────────────┬─────────────────────────────┘
                             │  work order + capability grant
                             │  ▲ result + telemetry
┌────────────────────────────▼─────────────────────────────┐
│                     EXECUTION PLANE                      │
│                                                          │
│  Claude Code · Codex · Cursor · Gemini · custom agents   │
│  Sandboxes / containers · CI · test runners · deploy     │
└────────────────────────────┬─────────────────────────────┘
                             ▼
                 REALITY: Repository (Git) + runtime
```

**AIEOS không bao giờ trở thành một coding agent khác.** Nó không viết code, không chạy model, không sở hữu sandbox. Nó quyết định, cấp quyền, kiểm tra và ghi nhận.

### Non-goals
- Không phải coding agent, IDE, CI, Git hay LLM framework.
- Không phải Jira cho con người.
- Không cung cấp memory chỉ để có memory. AIEOS cung cấp **persistent project state** để agent **resume với đúng intent, context, constraints và evidence**.
- Không điều phối agent chỉ để tăng throughput. AIEOS **điều phối thực thi để bảo toàn correctness và quyền kiểm soát** project.

---

## 4. Truth Hierarchy — ai thắng khi có mâu thuẫn

```text
   HUMAN AUTHORITY        ← nguồn quyền lực duy nhất để thay đổi intent
          │
          ▼
   CONSTITUTION           ← những điều không được phá
          │
          ▼
   INTENT STATE           ← project PHẢI là gì (requirement, spec, architecture, ADR)
          │
          ▼
   WORK (execution plan)  ← đang làm gì để đạt intent
          │
          ▼
   CHANGE                 ← diff thực tế
          │
          ▼
   REALITY                ← code đang tồn tại (sự thật về "cái đang có")
          │
          ▼
   EVIDENCE               ← điều gì đã được chứng minh, tại commit nào
```

**Quy tắc:**
- **Code là sự thật về hiện trạng. Intent là sự thật về mục tiêu.** Khi hai thứ khác nhau → đó là **drift**, không tự động là lỗi của bên nào.
- Reconciliation chỉ được **DETECT → CLASSIFY → PROPOSE**. Không được **DECIDE**.
- Ngoại lệ duy nhất: các **policy deterministic đã được human phê duyệt trước** (ví dụ: "diff ngoài scope → luôn reject").
- Agent **không bao giờ** sửa Intent hay Constitution trực tiếp; chỉ đề xuất Change Request.

Ví dụ:

```text
ADR-031:  "PostgreSQL là source of truth"
Reality:  module mới ghi trực tiếp vào Redis

AIEOS:    DRIFT  · class: architectural · severity: high
          Proposals:
            (a) Code sai → tạo TASK sửa module về PostgreSQL
            (b) Intent lỗi thời → tạo CR sửa ADR-031
          → chờ human chọn
```

---

## 5. Năm primitives & Correctness Loop

Toàn bộ AIEOS gom về 5 khái niệm. Mọi thực thể khác là chi tiết bên trong chúng.

### 5.1. Correctness Loop

Năm primitives tạo thành một vòng lặp khép kín. **"Tiếp tục làm việc" là đầu ra của vòng lặp — chỉ xảy ra sau khi correctness được xác nhận.**

```text
        ┌──────────────────────────────────────────────────────┐
        │                                                      │
        ▼                                                      │
   ┌──────────┐                                                │
   │  INTENT  │  "điều gì phải đúng"                           │
   └────┬─────┘                                                │
        ▼                                                      │
   ┌──────────┐                                                │
   │   WORK   │  "làm việc này" (task contract + work order)   │
   └────┬─────┘                                                │
        ▼                                                      │
   ┌──────────┐                                                │
   │ CONTROL  │  "được phép làm thế này"                       │
   └────┬─────┘                                                │
        ▼                                                      │
      AGENT  ──►  CHANGE                                       │
                    ▼                                          │
   ┌──────────┐                                                │
   │ EVIDENCE │  "chứng minh điều này"                         │
   └────┬─────┘                                                │
        ▼                                                      │
   ┌────────────────┐                                          │
   │ RECONCILIATION │  "điều đó còn đúng không?"               │
   └───────┬────────┘                                          │
     ┌─────┼──────────────┐                                    │
     ▼     ▼              ▼                                    │
  MATCH  DRIFT          VIOLATION                              │
     │     │              │                                    │
     │     ▼              ▼                                    │
     │  invalidate →   STOP + escalate                         │
     │  impact →                                               │
     │  revalidate                                             │
     ▼     ▼                                                   │
 CONTINUE  REPLAN ─────────────────────────────────────────────┘
```

### 5.2. Verdicts — AIEOS biết khi nào agent *không được* tiếp tục

Một hệ thống memory chỉ có một câu trả lời: *Continue*. AIEOS có nhiều câu trả lời, mỗi câu kèm lý do cụ thể:

| Verdict | Khi nào | Ví dụ |
|---|---|---|
| **CONTINUE** | Mọi thứ còn hợp lệ | Task tiếp theo READY, context không đổi |
| **CONTINUE_WITH** | Hợp lệ nhưng context đã đổi | Work Order mới vì dependency vừa merge thay đổi interface |
| **REPLAN** | Downstream mất hiệu lực | "3 artifact stale do ADR-031 v2 — đây là revalidation plan" |
| **STOP: intent changed** | Upstream intent đổi sau khi task bắt đầu | SPEC-012.1 v1 → v2 giữa chừng |
| **STOP: scope invalid** | Phạm vi task không còn đúng | File trong `write` scope đã bị task khác sở hữu |
| **STOP: evidence missing** | Không đủ assurance để chấp nhận | AC2 cần A4, chỉ có A1 |
| **STOP: runtime insufficient** | Runtime không enforce được capability cần chặn | Task risk high giao cho adapter T1 |
| **ESCALATE** | Hết budget / vượt risk / cần quyết định | Retry 3 lần thất bại; drift cần human chọn hướng |

### 5.3. Năm primitives

| Primitive | Câu hỏi | Gồm |
|---|---|---|
| **Intent** | Cái gì phải tồn tại? | Vision, Constitution, Requirement, Spec (+AC), Architecture, ADR, Convention |
| **Work** | Cái gì cần làm — và tiếp tục từ đâu? | Plan, Task (execution contract), Dependency, Lease, Session, Handoff, Work Order, Resume Check |
| **Control** | Agent được phép làm gì? | Policy, Risk, Autonomy Budget, Capability Grant, Approval, Escalation |
| **Evidence** | Làm sao biết nó đúng? | Change (SHA), Verification Run, Evidence item, Assurance level, Evidence graph |
| **Reconciliation** | Thực tế còn khớp intent? | Drift detection, Change Impact Engine, Revalidation plan |

---

## 6. Primitive 1 — Intent

### 6.1. Project Constitution

Tầng cao nhất của intent: **những điều agent tuyệt đối không được phá**, áp lên mọi requirement, spec và task.

**Yêu cầu bắt buộc: mỗi điều khoản phải khai báo cách kiểm tra.** Một Constitution chỉ gồm văn xuôi thì không khác gì `CLAUDE.md` — agent có thể đọc rồi lờ đi.

```yaml
constitution:
  - id: INV-001
    category: architecture
    rule: "domain/ không được import infrastructure/"
    check: deterministic            # dependency-cruiser / import-linter
    tool: { type: dependency_rule, from: "src/domain/**", forbid: "src/infra/**" }
    severity: blocking

  - id: INV-002
    category: correctness
    rule: "Mọi mutation tài chính phải idempotent"
    check: partial                  # deterministic một phần + AI review + test
    tool: { type: pattern, require: "idempotencyKey", in: "src/payments/**/mutations/*" }
    evidence_required: [property_test, ai_review]
    severity: blocking

  - id: SEC-001
    category: security
    rule: "Không có private key dạng plaintext trong repo"
    check: deterministic            # secret scanner
    severity: blocking

  - id: OPS-001
    category: operational
    rule: "Migration phải backward-compatible"
    check: judgment                 # chỉ human/AI review được
    evidence_required: [human_review]
    severity: blocking
```

Ba mức `check`:
- **deterministic** — máy kiểm tra chắc chắn → chặn tự động.
- **partial** — máy bắt được một phần, phần còn lại cần evidence bổ sung.
- **judgment** — không máy nào kiểm tra trọn vẹn được → bắt buộc evidence review, task chạm vào phải qua review.

> Giá trị thật của Constitution nằm ở **tỷ lệ điều khoản deterministic**. AIEOS nên chủ động giúp user chuyển điều khoản `judgment` thành `partial`/`deterministic` theo thời gian.

### 6.2. Các thực thể Intent khác

| Thực thể | Vai trò |
|---|---|
| **Requirement** `REQ-012` | WHAT + WHY; có `assurance_required` (mục 9.2) |
| **Spec** `SPEC-012.1` | Chi tiết hoá; **acceptance criteria kiểm chứng được** |
| **Architecture** `ARC-auth` | Component, trách nhiệm, interface, ranh giới |
| **ADR** `ADR-031` | Quyết định + lý do + phương án bị loại |
| **Convention** | Quy ước code; có thể nâng thành điều khoản Constitution |

Mọi thực thể Intent có **version**. Thay đổi chỉ qua **Change Request** được human duyệt.

---

## 7. Primitive 2 — Work (continuity of controlled execution)

Mọi thành phần của Work — task contract, context compiler, handoff, session protocol, lease — đều là **cơ chế duy trì correctness trong thực thi dài hạn**, không phải tính năng memory:

| Cơ chế | Vai trò về continuity | Vai trò về correctness |
|---|---|---|
| **Task contract** | Định nghĩa đơn vị công việc có thể tiếp tục bởi bất kỳ agent nào | Ranh giới scope, capability, điều kiện "xong" |
| **Context Compiler** | Session mới không cần nhớ gì | Context sai → reasoning sai → code sai → project sai. Context đúng là **cơ chế phòng ngừa** |
| **Resume Check** | Quyết định session tiếp theo bắt đầu từ đâu | Chặn tiếp tục trên giả định đã mất hiệu lực |
| **Handoff** | Chuyển giao giữa session/agent/model | Giả định, rủi ro, việc chưa xong được ghi rõ và kiểm tra lại |
| **Lease** | Nhiều agent làm song song | Không ghi đè, không xung đột |

### 7.1. Task = Bounded Execution Contract

Task không phải "một việc cần làm". Task là **một hợp đồng thực thi có ranh giới**: agent được trao một mục tiêu, một phạm vi, một tập quyền, một ngân sách, và một định nghĩa "xong" kiểm chứng được.

```yaml
task: TASK-142
objective: "Implement POST /auth/reset-request"
traces_to: [REQ-012, SPEC-012.1, SPEC-012.2]

input_state:
  base_commit: 9f3e1a0
  depends_on: [TASK-140]            # phải DONE
  intent_versions: { SPEC-012.1: v2, ADR-031: v1 }

scope:
  write:     [src/auth/reset/**, tests/auth/reset/**]
  read_only: [src/auth/core/**, src/shared/**]
  forbidden: [migrations/**, src/billing/**]

constitution: [INV-001, SEC-001]    # điều khoản áp dụng cho task này

acceptance_criteria:
  - AC1: Luôn trả 202 dù email có tồn tại hay không
  - AC2: Token lưu dạng hash, hết hạn sau 15 phút
  - AC3: Rate limit 5 request/giờ/IP

capabilities:                       # xem 8.2
  shell:   { allow: ["npm test*", "npm run lint", "npm run typecheck"] }
  network: { allow: [] }
  git:     { allow: [commit], forbid: [push, "push --force", rebase] }
  secrets: deny

risk: medium                        # xem 8.3
autonomy:
  max_level: L2
  budgets: { tokens: 400k, wall_time: 45m, retries: 3, human_attention: 10m }

verification_plan:
  - G0 scope · G1 build · G2 tests(AC1–AC3) · G3 constitution · G4 ai_review(cross-model)

exit_conditions:
  success:  all gates pass AND assurance(REQ-012 ACs) >= required
  escalate: [needs_out_of_scope_change, spec_conflict, budget_exhausted, retries_exceeded]
```

Mười một thành phần: **Objective · Input state · Scope · Forbidden · Dependencies · Constitution · Acceptance criteria · Capabilities · Budget · Verification plan · Exit conditions.**

### 7.2. Resume Check — trước mỗi session

Một session mới **không hỏi** *"agent trước đã làm đến đâu?"*. Nó hỏi: *"sau những thay đổi vừa xảy ra, project đang ở trạng thái nào và công việc nào còn hợp lệ?"*

Trước khi phát Work Order, AIEOS chạy Resume Check — **deterministic, rẻ, luôn chạy**:

| Kiểm tra | So sánh | Thất bại → verdict |
|---|---|---|
| Intent version | `intent_versions` trong task ↔ version hiện tại | STOP: intent changed / REPLAN |
| Base commit | `base_commit` ↔ HEAD: file trong scope có bị đổi bởi task khác? | CONTINUE_WITH (rebase context) / STOP: scope invalid |
| Dependencies | Mọi dependency còn DONE và không STALE? | BLOCKED |
| Constitution | Reality hiện tại có đang vi phạm điều khoản task phụ thuộc? | STOP + escalate |
| Evidence trước đó | Evidence của các phần đã làm còn khớp SHA? | CONTINUE_WITH (re-verify) |
| Runtime | Adapter đủ assurance cho risk của task? | STOP: runtime insufficient |
| Budget | Còn token / thời gian / retries / human attention? | ESCALATE |

Chỉ khi Resume Check trả **CONTINUE** hoặc **CONTINUE_WITH**, Context Compiler mới chạy.

### 7.3. Context Compiler → Work Order

Context Compiler biến *project state* + *task contract* thành **Work Order**: context tối thiểu đủ để làm task. Đây là **cơ chế correctness phòng ngừa**: agent không thể làm đúng nếu không được đưa đúng context.

- **Phân tầng**: Constitution áp dụng → Component liên quan → Spec/AC → File liên quan → Handoff gần nhất.
- **Chọn theo graph**: traceability graph + code dependency graph, không tìm kiếm mù.
- **Ngân sách token** theo tầng; vượt thì tóm tắt hoặc chuyển thành tham chiếu.
- **Pull hơn push**: thứ không chắc cần thì để agent truy vấn qua AIEOS tools.
- **Registry**: liệt kê utility/API đã có liên quan → agent dùng lại thay vì viết mới.

### 7.4. Vòng đời task

```text
DRAFT ─approve─► READY ─lease─► IN_PROGRESS ─submit─► VERIFYING ─► VERIFIED ─► ACCEPTED ─► DONE
                   ▲                 │                   │
                   └─── BLOCKED ◄────┘                   ├─ fail ─► REWORK (≤ retries) ─► ESCALATED
                                                         │
     upstream intent đổi / reality drift ───────────────► STALE (từ bất kỳ trạng thái sau READY)
```

### 7.5. Session protocol & handoff

**Resume Check** (7.2) → Boot (nhận Work Order, không dùng chat history) → Acknowledge (liệt kê giả định; mơ hồ → hỏi) → Work → Submit (diff + report có cấu trúc) → Handoff.

Handoff có cấu trúc: `done`, `not_done`, `assumptions`, `discoveries`, `risks`, `proposals`. **Discoveries và proposals không tự thành sự thật** — chúng vào hàng đợi chờ duyệt.

### 7.6. Coordination

- **Lease độc quyền** trên task + write scope; scope chồng nhau không chạy song song (hoặc mỗi task một worktree, merge theo thứ tự).
- Chỉ task có mọi dependency `DONE` mới `READY`.
- Role tách biệt: Planner, Implementer, Reviewer — quyền khác nhau.

---

## 8. Primitive 3 — Control

### 8.1. Kiểm soát ở ba thời điểm

| Thời điểm | Cơ chế | Phụ thuộc |
|---|---|---|
| **Preventive** (trước) | Work Order giới hạn scope; capability grant cấu hình vào runtime | Adapter |
| **Runtime** (trong) | Hook / tool guard / sandbox chặn hành động | Execution plane |
| **Post-hoc** (sau) | Gate kiểm tra diff, constitution, evidence | AIEOS — **luôn có** |

> **AIEOS không thể kiểm soát thứ nó không nhìn thấy.** Kiểm tra diff sau cùng bắt được file ngoài scope, nhưng **không** bắt được `curl` tới server lạ, `git push`, hay đọc secret — những thứ đó xảy ra trước khi có diff. Với hành động không quay lại được, chỉ có preventive/runtime control mới có tác dụng.

### 8.2. Capability Boundary

Câu hỏi không phải *"agent được làm gì?"* mà *"trong task này, agent được cấp những capability nào?"*. Mặc định **deny all**; task contract cấp từng capability.

```yaml
capabilities:
  filesystem: { read: [...], write: [...] }
  shell:      { allow: ["npm test*", "npm run lint"] }
  network:    { allow: ["registry.npmjs.org"] }
  git:        { allow: [commit], forbid: [push, "push --force"] }
  secrets:    deny
  external_side_effects: deny        # gửi email, gọi API thật, deploy
```

**Ranh giới trung thực:** AIEOS *khai báo* capability; **execution plane mới là nơi thực thi** (hooks của runtime, sandbox, container, network policy). Vì vậy AIEOS phải biết adapter thực sự enforce được gì (8.4) và **không cấp task rủi ro cao cho runtime không enforce được capability mà task đó cần chặn**.

### 8.3. Risk → Autonomy

Risk quyết định mọi thứ phía sau:

```text
risk ─► model/agent được dùng
     ─► capabilities được cấp
     ─► context budget
     ─► verification plan + assurance yêu cầu
     ─► cần human approval hay không
     ─► runtime tối thiểu (adapter assurance)
```

Các yếu tố: **impact × blast radius × irreversibility × sensitivity × uncertainty**.

**Cách triển khai thực tế:**
- **MVP: rule-based**, không phải công thức nhân số. Risk = mức cao nhất của các rule khớp (path, loại thay đổi, tag nhạy cảm trên component, điều khoản Constitution bị chạm). Lý do: một công thức nhân 5 số thực chưa được hiệu chỉnh chỉ tạo **độ chính xác giả** — "risk = 0.7" không có nghĩa gì nếu không ai biết 0.7 so với cái gì.
- **Sau này:** hiệu chỉnh bằng dữ liệu thật (task nào ở mức nào thực sự gây rework/incident).

```yaml
risk_rules:
  - match: { paths: ["docs/**", "*.md"] }                 → low
  - match: { paths: ["src/**"] }                          → medium
  - match: { component_tags: [auth, payments, crypto] }   → high
  - match: { paths: ["migrations/**", "contracts/**"] }   → critical
  - match: { touches: [constitution, intent] }            → critical
```

### 8.4. Autonomy Budget

Agent được tự chủ cho tới khi **một** điều kiện bị phá:

```text
risk ≤ allowed_risk
AND budget còn (tokens, wall_time, retries, human_attention)
AND policy thoả
AND verification pass
          │ không
          ▼
       ESCALATE
```

| Level | Ý nghĩa |
|---|---|
| L0 | AI chỉ đề xuất |
| L1 | AI implement, human duyệt mọi task |
| L2 | Auto-accept task ≤ medium risk khi đủ assurance |
| L3 | AI tự plan task trong requirement đã duyệt |
| L4 | AI đề xuất requirement; human duyệt ở mức milestone |

Level của project chỉ được nâng khi **metrics chứng minh** (mục 12).

### 8.5. Adapter: capability ≠ assurance

Adapter không chỉ khai báo *"hỗ trợ MCP"* mà khai báo **mức enforcement thật**:

```yaml
adapter: claude-code
capabilities: { mcp: true, hooks: true, fs_scope: true, headless: true, shell_guard: true }
assurance:    { preventive: strong, runtime: strong, posthoc: strong }
max_risk:     high
```
```yaml
adapter: generic-chat
capabilities: { mcp: false, hooks: false, fs_scope: false, headless: false }
assurance:    { preventive: weak, runtime: none, posthoc: strong }
max_risk:     low
```

Scheduler dùng `max_risk` để **từ chối giao** task vượt mức cho runtime yếu.

| Tier | Runtime có | Mức đảm bảo |
|---|---|---|
| T0 Manual | Chat | Chỉ post-hoc |
| T1 Instructions | Rules file | Post-hoc |
| T2 Tools | MCP | Post-hoc + báo cáo có cấu trúc |
| T3 Enforcement | Hooks / permissions / sandbox | Preventive + runtime + post-hoc |
| T4 Headless | CLI/SDK tự động | Như T3 + điều phối tự động |

---

## 9. Primitive 4 — Evidence

### 9.1. Evidence là first-class

Agent nói "Done." — AIEOS hỏi:

```text
Đổi gì?               → diff, commit SHA
Đáp ứng AC nào?       → mapping AC ↔ evidence
Kiểm tra gì đã chạy?  → verification run
Trên commit nào?      → SHA (code đổi → evidence STALE)
Ai/cái gì kiểm tra?   → tool / model / human (không phải agent tự khai)
Còn hiệu lực không?   → không stale, intent version còn khớp
```

### 9.2. Assurance levels (thay vì PASS/FAIL nhị phân)

Không phải mọi evidence mạnh như nhau:

| Mức | Loại evidence |
|---|---|
| **A0** | Agent tự khai báo — *không tính* |
| **A1** | Unit test, AI review |
| **A2** | Integration test, static analysis, kiểm tra constitution deterministic |
| **A3** | Property / fuzz / mutation test, security analysis |
| **A4** | Human expert review, formal verification |
| **A5** | Production evidence (telemetry, không có incident sau N ngày) |

**Mỗi requirement/AC khai báo mức assurance yêu cầu** (thường suy ra từ risk):

```text
REQ-012  "User không thể reset password của user khác"
  required: A3 + A4
  ├── AC1  unit test           A1 ✓
  │        integration test    A2 ✓
  │        property test       A3 ✓
  └── AC2  security review     A4 ✗  ← thiếu
  Status: UNDER-ASSURED (thiếu A4 cho AC2)
```

> Không dùng một con số kiểu *"assurance 93%"*: không có cơ sở để cộng một unit test với một security review thành phần trăm, và con số đó tạo cảm giác an toàn giả. Thay vào đó: **đạt / chưa đạt mức yêu cầu, và thiếu cụ thể cái gì.**

### 9.3. Verification hierarchy

```text
V0  Diff validation        scope, forbidden paths
V1  Deterministic          build, lint, typecheck, tests, constitution (deterministic)
V2  Static analysis        security scanner, dependency rules, secret scan
V3  AI review              spec conformance, cross-model
V4  Advanced testing       property, fuzz, mutation
V5  Human review
V6  Production evidence
```

- Rẻ và chắc chắn chạy trước; đắt và chủ quan chạy sau, **chỉ khi risk yêu cầu**.
- **AI review chỉ là một lớp evidence**, không phải bảo đảm. Claude viết + GPT review vẫn có thể cùng chung một giả định sai. Với code tài chính / blockchain / security-critical, AI review không bao giờ là lớp cuối.

### 9.4. Quy tắc evidence
- Evidence luôn gắn **commit SHA** và **intent version**.
- Evidence do **AIEOS/CI/tool/human** tạo ra, không do agent tự viết.
- Mỗi AC phải map tới evidence đủ mức yêu cầu.

---

## 10. Primitive 5 — Reconciliation

Đây là năng lực khác biệt nhất: một task manager biết *"TASK-142 = DONE"*; AIEOS biết *"TASK-142 DONE, nhưng 5 commit sau INV-001 không còn đúng."*

### 10.1. Drift detection

Chạy khi có commit mới và định kỳ:

| Loại drift | Ví dụ | Cách phát hiện |
|---|---|---|
| **Constitution** | `domain/` import `infra/` | Deterministic |
| **Scope** | Commit sửa file không thuộc task nào | Deterministic (commit trailer) |
| **Evidence** | Code đổi, evidence cũ thành stale | Deterministic (SHA) |
| **Architecture** | Module mới ghi thẳng Redis trái ADR-031 | Partial: rule + AI |
| **Semantic** | `payment.create()` thiếu idempotency key | Partial: pattern + AI |
| **Orphan code** | Code không truy về requirement nào | Deterministic + heuristic |

**Giới hạn cần nói thẳng:** drift ngữ nghĩa phát hiện bằng AI sẽ có **false positive**. Nếu báo động giả nhiều, user sẽ tắt tính năng. Vì vậy:
- Mỗi cảnh báo có `confidence` và `detection_method`.
- Drift deterministic được ưu tiên hiển thị; drift AI gom thành digest.
- Theo dõi **false positive rate** như một metric sản phẩm chính.

Mọi drift → **DETECT → CLASSIFY → PROPOSE** (sửa code, hoặc sửa intent qua CR). Human quyết định.

### 10.2. Change Impact Engine

Không chỉ đánh dấu `STALE` — mà trả lời *"thay đổi này kéo theo những gì"*:

```text
CR-009: ADR-031 v1 → v2
        │
        ▼ đi theo traceability + dependency graph
Impact report:
  17 artifact mất hiệu lực
   ├── 3 spec cần xem lại            SPEC-012.1, SPEC-014.2, SPEC-020.1
   ├── 4 task DONE cần làm lại       TASK-142, TASK-151, ...
   ├── 2 component cần review        ARC-auth, ARC-session
   ├── 1 điều khoản constitution     INV-001 (cần cập nhật rule)
   └── 11 evidence thành stale
        │
        ▼
Revalidation plan (đề xuất, chờ duyệt):
  TASK-160  Update token store       risk: high
  TASK-161  Re-run property tests    risk: low
  ...
```

**Giới hạn:** độ chính xác phụ thuộc vào **độ đầy đủ của traceability graph**. Liên kết intent→task rất chắc (do AIEOS tạo); liên kết task→code khá chắc (commit trailer); liên kết code→AC qua test là phần yếu nhất và cần được xây dần (test khai báo AC nó chứng minh).

---

## 11. Zero-friction path — chống bureaucracy

**Rủi ro số 1 của AIEOS:** sửa một dòng README mà phải đi qua Requirement → Spec → Task → Lease → … → Accept thì người ta gỡ ngay.

Nguyên tắc: **user nói ý định, AIEOS tự sinh các artifact; user chỉ duyệt khi risk đòi hỏi.**

```bash
aieos run "sửa typo trong README"
#  → task tự sinh · risk: low · V0+V1 · auto-accept · 1 dòng log. Xong.

aieos run "thêm dark mode"
#  → AIEOS đề xuất: REQ + 2 spec + 4 task + risk + verification plan
#  → user: [Approve] [Edit] [Reject]
#  → chạy tự động tới khi cần escalate

aieos status
#  → tiến độ, drift, task đang chờ duyệt, requirement thiếu assurance
```

**Fast path không phải bypass path:** task risk thấp vẫn có V0 (scope) và V1 (deterministic), vẫn được ghi vào event log, vẫn truy vết được. Chỉ phần *thủ tục cho con người* bị lược bỏ, không phải phần *kiểm soát*.

Ngân sách friction: **thời gian human trên mỗi task risk thấp ≈ 0**; human chỉ xuất hiện ở approval điểm quyết định.

---

## 12. Đo lường

| Metric | Ý nghĩa |
|---|---|
| **Caught rate** | Số thay đổi agent báo "xong" nhưng bị AIEOS chặn (có lý do đúng) |
| **First-pass acceptance** | % task pass mọi gate ở lần nộp đầu |
| **Drift false positive rate** | % cảnh báo drift bị user đánh giá sai — phải thấp |
| **Escaped defects** | Lỗi lọt qua mọi gate, phát hiện sau — metric trung thực nhất |
| **Human time / task** | Theo risk level |
| **Assurance coverage** | % requirement đạt mức assurance yêu cầu |
| **Cost / accepted task** | Token + thời gian |
| **Rework rate** | % task DONE bị mở lại / revert |

---

## 13. Lưu trữ

Git-native cho Intent và Constitution; local store cho runtime state.

```text
repo/
├── .aieos/
│   ├── project.yaml            # policy, risk rules, autonomy, adapters
│   ├── constitution.yaml
│   ├── intent/
│   │   ├── requirements/  specs/  architecture/  decisions/  conventions/
│   ├── tasks/                  # task contracts
│   ├── handoffs/
│   └── events.jsonl            # append-only event log
└── src/ ...
(runtime: lease, session → SQLite local, không commit)
```

Chỉ AIEOS core ghi `.aieos/`; agent ghi qua protocol (MCP/CLI).

---

## 14. Định vị & Moat

### Định vị

| Không định vị là | Vì sao |
|---|---|
| AI project management | Quá yếu, đã có nhiều |
| AI memory | Quá nhỏ, là tính năng không phải sản phẩm |
| Multi-agent orchestration | Quá đông đúc |
| **Control plane for AI software engineering** | ✓ — trung tâm là *correctness và control*, không phải *throughput* |

### Moat — thứ khó copy

Những thứ **dễ copy**: CLI, MCP server, web UI, từng adapter riêng lẻ.

Những thứ **có thể thành moat**:
1. **Project state protocol mở** (`.aieos/`: Intent · Work · Evidence) — nếu trở thành chuẩn de-facto.
2. **Reconciliation engine** với false-positive thấp.
3. **Evidence graph + assurance model**.
4. **Risk → autonomy engine**.
5. **Historical intelligence**: dữ liệu *task type × agent × model × context strategy → first-pass rate, cost, escaped defects*. Khi đó scheduler biết *"task loại này, runtime X + chiến lược context Y có first-pass 91%"*.

**Mâu thuẫn cần giải quyết sớm:** moat số 5 cần **dữ liệu tổng hợp nhiều project**, trong khi thiết kế hiện tại là local-first, git-native. Cần quyết định: telemetry opt-in ẩn danh? Bản cloud? Hay chỉ tối ưu trong từng project? Đây là quyết định business, không phải kỹ thuật.

### Đối thủ cần nghiên cứu kỹ
- Bản thân các runtime (Claude Code, Codex, Cursor) — đang tự thêm task management, memory, multi-agent, hooks.
- Công cụ spec-driven development và persistent work state cho agents (vd: AWR). Đây là vùng continuity kiểu memory — AIEOS phải khác ở chỗ continuity luôn đi qua Resume Check, Evidence và Reconciliation.
- Nghiên cứu về "harness engineering" và "agentic SDLC control plane" — xác nhận thesis, nhưng cũng nghĩa là thuật ngữ "control plane" không đủ để khác biệt; **khác biệt phải nằm ở implementation primitives** (Constitution kiểm tra được, Evidence có assurance level, Reconciliation).

Lợi thế cấu trúc: nhà cung cấp runtime có động lực khoá user vào runtime của mình; AIEOS **trung lập** — governance nằm ngoài mọi runtime.

---

## 15. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| **Bureaucracy** — chậm hơn không dùng | Zero-friction path; risk-proportional; đo human time/task |
| **Drift false positive** làm user tắt tính năng | Deterministic trước; confidence; đo FP rate |
| **Constitution chỉ là văn xuôi** | Bắt buộc khai báo `check`; chuyển dần judgment → deterministic |
| **Không kiểm soát được hành động ngoài diff** | Capability boundary + adapter assurance + từ chối giao task rủi ro cho runtime yếu |
| **AI review tạo cảm giác an toàn giả** | Assurance levels; AI review chỉ là A1 |
| **State tự drift khỏi code** | Reconciliation; code là sự thật về hiện trạng |
| **Runtime tự xây tính năng tương tự** | Trung lập đa runtime; định dạng mở; tập trung vào correctness |
| **Cold start với repo có sẵn** | `aieos import`: AI quét repo, đề xuất architecture + constitution, human duyệt |

---

## 16. MVP & Roadmap

### MVP v0.1 — "Claude Code không phá project của tôi"

Mục tiêu đo được: trên một project thật ~100 task, AIEOS **bắt được thay đổi sai mà agent báo là xong**, với human time thấp.

- [ ] `.aieos/` format: constitution (có `check`), requirement, spec+AC, ADR, task contract, handoff
- [ ] `aieos init` / `aieos import` (đề xuất constitution từ repo)
- [ ] `aieos run "<ý định>"` — zero-friction path
- [ ] Resume Check (deterministic) + Context Compiler v1 (graph-based, không semantic search)
- [ ] MCP server ~8 tools
- [ ] Adapter **Claude Code (T3)**: hooks enforce write scope, shell allowlist, chặn git push
- [ ] Adapter **Codex (T1/T2)** — để chứng minh core trung lập ngay từ đầu
- [ ] Verification V0–V2, evidence gắn SHA, assurance A1–A2
- [ ] Reconciliation deterministic (constitution, scope, stale evidence)
- [ ] Risk rule-based, autonomy L1–L2
- [ ] Event log; chạy tuần tự (chưa song song)

### v0.2 — Assurance
V3 cross-model review, Change Impact Engine, assurance A3–A4, drift semantic (AI) với confidence, metrics.

### v0.3 — Parallel
Lease + worktree, nhiều agent song song, role-based agents, thêm adapter.

### v1.0 — Team
Web UI, multi-user, approval workflow, cloud sync, quyết định về historical intelligence.

**Dogfooding:** dùng AIEOS để build AIEOS — và dùng trên Boomy như project thật đầu tiên.

---

## 17. Câu hỏi mở

1. **Historical intelligence**: chấp nhận cloud/telemetry để xây moat dữ liệu, hay giữ hoàn toàn local-first?
2. **Open source**: mở format `.aieos/` + core, thương mại hoá cloud/team?
3. **Dispatch**: MVP để agent *kéo* Work Order qua MCP (đơn giản), hay AIEOS *đẩy* qua headless (tự động hơn)?
4. **Ngôn ngữ đầu tiên** cho constitution checker (TS? Python?) — quyết định theo Boomy.
5. **Tên**: chốt "AIEOS".
