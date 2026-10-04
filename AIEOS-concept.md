# AIEOS — Control Plane for AI Software Engineering

> **Concept Document v0.5**
> Ngày: 2026-10-04 · Trạng thái: **Concept freeze** — thay đổi tiếp theo đi vào technical specs (mục 18)
> v0.3: chuyển trọng tâm từ *"giúp AI tiếp tục làm việc"* sang *"đảm bảo AI không làm project sai"*; gom mô hình về 5 primitives; thêm Constitution, Truth Hierarchy, Capability Boundary, Risk → Autonomy, Assurance Levels, Change Impact Engine, Zero-friction path, ICP.
> v0.4: tái tích hợp continuity — **continuity là phương tiện, correctness là mục tiêu**; thêm Product Hierarchy, Correctness Loop với các verdict (CONTINUE / REPLAN / STOP), và Resume Check.
> v0.5: định nghĩa phạm vi cam kết của "correctness"; 4 luật bất biến; tách **Execution decision** và **Acceptance decision**; phân loại sự kiện reconciliation (drift ≠ violation); **read-set / write-set** trong task contract và Resume Check; thay assurance tuyến tính bằng **Evidence Profile**; Constitution có scope/applicability; mô hình **state & recovery**.

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

### Phạm vi cam kết của "correctness"

Tagline *"AIEOS keeps the project correct"* là marketing. Về kỹ thuật, **không hệ thống nào chứng minh được toàn bộ phần mềm đúng**: test có thể sai, invariant có thể được đặc tả sai, requirement có thể thiếu, lỗi logic có thể lọt qua mọi gate.

Định nghĩa kỹ thuật chính xác:

> **AIEOS bảo toàn tính đúng đắn của project bằng cách thực thi các ràng buộc đã được định nghĩa, yêu cầu bằng chứng kiểm chứng được, và liên tục phát hiện sai lệch giữa trạng thái dự định và trạng thái thực tế.**

| AIEOS cam kết | AIEOS **không** cam kết |
|---|---|
| Thực thi các ràng buộc **đã được định nghĩa** và kiểm tra được | Phát hiện lỗi mà không ràng buộc/evidence nào bao phủ |
| Chặn hành động vi phạm policy **mà runtime enforce được** | Chặn hành động trên runtime không có enforcement |
| Phát hiện thay đổi không còn khớp intent đã khai báo | Biết intent chưa được khai báo |
| Không công nhận "xong" khi thiếu evidence yêu cầu | Đảm bảo bản thân evidence (test) là đúng |
| Báo rõ **cái gì chưa được bao phủ** | Biến "không phát hiện vấn đề" thành "không có vấn đề" |

Hệ quả thiết kế: AIEOS phải **luôn hiển thị vùng chưa được bao phủ** (requirement không có evidence, điều khoản `judgment` chưa review, runtime yếu) — chống **false confidence**, rủi ro lớn nhất của một hệ thống governance.

### Bốn luật bất biến

> **AIEOS không bao giờ cho phép agent tiếp tục dựa trên một project state không còn hợp lệ, và không bao giờ chấp nhận một thay đổi khi chưa đủ evidence.**

1. **Không tiếp tục trên trạng thái lỗi thời.** (Resume Check, 7.2)
2. **Không cấp quyền vượt quá khả năng kiểm soát.** (Capability boundary × adapter assurance, 8.2 · 8.5)
3. **Không công nhận hoàn thành chỉ dựa trên lời agent.** (Acceptance decision, 5.3 · Evidence, 9)
4. **Không để thay đổi upstream âm thầm vô hiệu hoá những gì đã được chấp nhận.** (Reconciliation, Impact, 10)

Mọi tính năng mới phải không vi phạm 4 luật này; mọi bug vi phạm chúng là bug mức nghiêm trọng cao nhất.

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
           ▼                                                   │
   phân loại sự kiện (5.2)                                     │
           ▼                                                   │
   EXECUTION DECISION + ACCEPTANCE DECISION (5.3)              │
     │              │               │                          │
     ▼              ▼               ▼                          │
  CONTINUE        REPLAN       STOP / ESCALATE                 │
     │              │                                          │
     └──────────────┴──────────────────────────────────────────┘
```

### 5.2. Phân loại sự kiện reconciliation

**Drift không đồng nghĩa với violation.** Các sự kiện khác nhau về bản chất, về ai có lỗi, và về cách xử lý:

| Sự kiện | Định nghĩa | Ví dụ | Xử lý mặc định |
|---|---|---|---|
| **INTENT_CHANGE** | Human thay đổi intent (qua CR đã duyệt) | SPEC-012.1 v1 → v2 | Impact analysis → artifact phụ thuộc thành STALE → REPLAN |
| **DRIFT** | Reality ≠ intent, **không rõ bên nào sai** | Module ghi Redis trái ADR-031 | DETECT → CLASSIFY → PROPOSE (sửa code *hoặc* sửa intent); human chọn |
| **VIOLATION** | Hành động phá một policy/ràng buộc **đã biết rõ** | Agent sửa file ngoài write-set; vi phạm INV-001 | Reject thay đổi; STOP session; ghi nhận vào metric của runtime/agent |
| **STALE_EVIDENCE** | Evidence không còn khớp SHA hoặc intent version | Code đổi sau khi test pass | Lên lịch re-verify; **không** chặn thực thi |
| **CONFLICT** | Hai luồng công việc va chạm | Task B đổi interface mà Task A đang đọc | CONTINUE_WITH (biên dịch lại context) hoặc REPLAN tuỳ mức độ (7.2) |

### 5.3. Hai loại quyết định

Hai câu hỏi khác nhau, không được trộn lẫn:

- **Execution decision** — *agent có được tiếp tục thực thi không?* Đưa ra ở Resume Check và trong lúc chạy.
- **Acceptance decision** — *kết quả có được công nhận hoàn thành không?* Đưa ra sau verification.

Thiếu evidence là chuyện **bình thường** trong lúc đang làm — nó không bao giờ là lý do để dừng thực thi, chỉ là lý do để không chấp nhận.

**Execution decisions** — AIEOS biết khi nào agent *không được* tiếp tục:

| Decision | Khi nào | Ví dụ |
|---|---|---|
| **CONTINUE** | Mọi thứ còn hợp lệ | Task READY, context không đổi |
| **CONTINUE_WITH** | Hợp lệ nhưng context đã đổi | Read-set thay đổi không phá interface → Work Order mới |
| **REPLAN** | Kế hoạch mất hiệu lực | INTENT_CHANGE; read-set đổi phá interface; downstream stale |
| **STOP: scope invalid** | Write-set xung đột | File trong write-set đã bị task khác sửa |
| **STOP: runtime insufficient** | Runtime không enforce được capability cần chặn | Task risk high giao cho adapter T1 |
| **STOP: violation** | Session vừa vi phạm policy | Ghi ngoài write-set |
| **BLOCKED** | Dependency chưa sẵn sàng | TASK-140 chưa DONE hoặc đã STALE |
| **ESCALATE** | Hết budget / vượt risk / cần quyết định | Retry quá giới hạn; drift cần human chọn hướng |

**Acceptance decisions** — sau verification:

| Decision | Khi nào |
|---|---|
| **ACCEPT** | Mọi gate pass, evidence profile đủ, policy cho phép auto-accept |
| **NEEDS_REVIEW** | Đủ evidence tự động nhưng risk/policy yêu cầu human duyệt |
| **INSUFFICIENT_EVIDENCE** | Thiếu loại evidence mà profile yêu cầu (9.2) |
| **NEEDS_REWORK** | Gate fail (test, constitution, spec conformance) |
| **REJECT** | Vi phạm không sửa được trong phạm vi task (sai hướng, ngoài scope) |

```text
Resume Check ─► Execution: CONTINUE ─► Agent implements ─► Verification
                                                              │
                                     Acceptance: INSUFFICIENT_EVIDENCE
                                                              │
                                         ─► REWORK (thêm test) hoặc REVIEW
```

### 5.4. Năm primitives

| Primitive | Câu hỏi | Gồm |
|---|---|---|
| **Intent** | Cái gì phải tồn tại? | Vision, Constitution, Requirement, Spec (+AC), Architecture, ADR, Convention |
| **Work** | Cái gì cần làm — và tiếp tục từ đâu? | Plan, Task (execution contract), Dependency, Lease, Session, Handoff, Work Order, Resume Check |
| **Control** | Agent được phép làm gì? | Policy, Risk, Autonomy Budget, Capability Grant, Approval, Escalation |
| **Evidence** | Làm sao biết nó đúng? | Change (SHA), Verification Run, Evidence item, Evidence Profile, Evidence graph |
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

#### Scope & applicability — để Constitution vận hành được ở quy mô lớn

Project lớn có thể có hàng trăm điều khoản. Chạy tất cả cho mọi task là chậm và tạo nhiễu. Mỗi điều khoản khai báo **phạm vi** và **khi nào áp dụng**:

```yaml
  - id: INV-001
    rule: "domain/ không được import infrastructure/"
    scope:
      components: [domain, infrastructure]
      paths: ["src/domain/**"]
    applicability:
      task_types: [implementation, refactoring]
    enforcement:
      mode: blocking               # blocking | warning | advisory
      checker: dependency_rule
      cost: cheap                  # cheap | moderate | expensive
```

Ba thời điểm kiểm tra, mỗi thời điểm chỉ chạy tập điều khoản cần thiết:

| Thời điểm | Tập điều khoản | Mục đích |
|---|---|---|
| **Task-time** (biên dịch Work Order) | Điều khoản có `scope` giao với write-set ∪ read-set của task | Đưa vào context để agent biết trước |
| **Diff-time** (verification) | Điều khoản có `scope` giao với **file thực sự thay đổi** | Gate chặn vi phạm |
| **Project-time** (định kỳ / trước release) | Toàn bộ, kể cả checker `expensive` | Bắt drift tích luỹ, điều khoản cross-cutting |

Điều khoản không khai báo `scope` mặc định là project-wide và chỉ chạy ở project-time — để khuyến khích viết scope cụ thể.

### 6.2. Các thực thể Intent khác

| Thực thể | Vai trò |
|---|---|
| **Requirement** `REQ-012` | WHAT + WHY; có `evidence_profile` (mục 9.2) |
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

write_set:                          # được phép thay đổi
  paths: [src/auth/reset/**, tests/auth/reset/**]
read_set:                           # những gì task DỰA VÀO
  paths:      [src/auth/core/**, src/shared/email/**]
  interfaces: [TokenService, EmailPort]      # symbol/contract cụ thể
  schemas:    [reset_tokens]
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
  success:  all gates pass AND evidence_profile(REQ-012) satisfied
  escalate: [needs_out_of_scope_change, spec_conflict, budget_exhausted, retries_exceeded]
```

Mười hai thành phần: **Objective · Input state · Write-set · Read-set · Forbidden · Dependencies · Constitution · Acceptance criteria · Capabilities · Budget · Verification plan · Exit conditions.**

**Read-set được xác định từ ba nguồn**, vì không thể bắt agent khai báo đầy đủ từ trước:

| Nguồn | Cách lấy | Độ tin cậy |
|---|---|---|
| **Declared** | Planner khai báo trong task contract | Có thể thiếu |
| **Derived** | Static analysis: các symbol mà file trong write-set import/gọi tới | Tốt cho code; không thấy dependency động |
| **Observed** | File agent thực sự đọc trong session (hooks của runtime T3+) | Chính xác nhất, chỉ có ở runtime hỗ trợ |

Read-set hiệu lực = hợp của cả ba. Với runtime T0–T2 (không có observed), AIEOS ghi rõ read-set là *ước lượng* — đúng tinh thần "luôn hiển thị vùng chưa được bao phủ".

### 7.2. Resume Check — trước mỗi session

Một session mới **không hỏi** *"agent trước đã làm đến đâu?"*. Nó hỏi: *"sau những thay đổi vừa xảy ra, project đang ở trạng thái nào và công việc nào còn hợp lệ?"*

Trước khi phát Work Order, AIEOS chạy Resume Check — **deterministic, rẻ, luôn chạy**.

**HEAD thay đổi không có nghĩa là phải dừng.** Hai task cùng xuất phát từ commit A; Task B merge (chỉ sửa `billing.ts`) → HEAD = C. Task A (chỉ sửa `auth.ts`) vẫn tiếp tục an toàn. Nhưng nếu Task B sửa `TokenService` mà Task A đang dựa vào → Task A phải được đánh giá lại. Vì vậy Resume Check xét **cái gì đã thay đổi so với `base_commit`**, giao với **write-set và read-set** của task:

| # | Kiểm tra | So sánh | Kết quả |
|---|---|---|---|
| 1 | **Base freshness** | `base_commit` ↔ HEAD | Không đổi → bỏ qua 2–3. Đổi → tính tập thay đổi `Δ = diff(base, HEAD)` |
| 2 | **Write-set conflict** | `Δ` ∩ write-set | Rỗng → OK. Có giao → **STOP: scope invalid** (hoặc rebase nếu xung đột tự giải được) |
| 3 | **Read-set freshness** | `Δ` ∩ read-set | Rỗng → OK. Có giao, interface/schema **không đổi chữ ký** → **CONTINUE_WITH** (biên dịch lại context). Có giao, **phá interface** → **REPLAN** |
| 4 | **Intent freshness** | `intent_versions` ↔ version hiện tại | Đổi → **REPLAN** (impact analysis xác định mức ảnh hưởng) |
| 5 | **Dependency freshness** | Mọi dependency còn DONE, không STALE | Không → **BLOCKED** |
| 6 | **Constitution** | Reality hiện tại vi phạm điều khoản áp dụng cho task? | Có → **ESCALATE** (không xây tiếp trên nền đang vi phạm) |
| 7 | **Runtime** | Adapter `max_risk` ≥ risk của task | Không → **STOP: runtime insufficient** |
| 8 | **Budget** | Còn token / thời gian / retries / human attention | Không → **ESCALATE** |

Evidence cũ bị stale **không** nằm trong Resume Check — đó là việc của acceptance (STALE_EVIDENCE → re-verify), không phải lý do dừng thực thi.

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
DRAFT ─approve─► READY ─lease─► IN_PROGRESS ─submit─► VERIFYING ─► (acceptance decision)
                   ▲                 │                                 │
                   └─── BLOCKED ◄────┘     ACCEPT ──────────────────────┼─► ACCEPTED ─► DONE
                                           NEEDS_REVIEW ─► IN_REVIEW ───┤
                                           INSUFFICIENT_EVIDENCE ───────┼─► REWORK ─► IN_PROGRESS
                                           NEEDS_REWORK ────────────────┘   (quá retries → ESCALATED)
                                           REJECT ─► REJECTED

  INTENT_CHANGE / CONFLICT phá interface ─► STALE ─► REPLAN   (từ bất kỳ trạng thái sau READY)
  STALE_EVIDENCE trên task DONE           ─► DONE (evidence: stale) ─► re-verify
```

### 7.5. Session protocol & handoff

**Resume Check** (7.2) → Boot (nhận Work Order, không dùng chat history) → Acknowledge (liệt kê giả định; mơ hồ → hỏi) → Work → Submit (diff + report có cấu trúc) → Handoff.

Handoff có cấu trúc: `done`, `not_done`, `assumptions`, `discoveries`, `risks`, `proposals`. **Discoveries và proposals không tự thành sự thật** — chúng vào hàng đợi chờ duyệt.

### 7.6. Coordination

- **Lease độc quyền** trên task + write-set; write-set chồng nhau không chạy song song (hoặc mỗi task một worktree, merge theo thứ tự).
- Write-set của task này giao với read-set của task khác → được chạy song song, nhưng merge của task ghi sẽ kích hoạt Resume Check cho task đọc.
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

### 9.2. Evidence Profile (thay vì một thang assurance tuyến tính)

Các loại evidence **không nằm trên cùng một thang đo**. Formal verification chứng minh một thuộc tính trong phạm vi mô hình, nhưng không thấy vấn đề kiến trúc mà human review thấy. Production telemetry thấy hành vi thực tế mà test không bao phủ. Unit test và security analysis chứng minh những khía cạnh khác nhau. Không loại nào **thay thế** được loại khác.

Vì vậy mỗi requirement khai báo **những loại evidence cần có, theo từng chiều**:

```yaml
requirement: REQ-012
evidence_profile:
  functional:    [unit_test, integration_test]
  security:      [static_security_analysis, human_security_review]
  architecture:  [deterministic_rule]
  operational:   [migration_compatibility_test]
```

Acceptance kiểm tra **từng chiều đủ hay thiếu**, không cộng điểm:

```text
REQ-012  "User không thể reset password của user khác"
  functional    unit_test ✓  integration_test ✓
  security      static_security_analysis ✓  human_security_review ✗   ← thiếu
  architecture  deterministic_rule ✓
  Decision: INSUFFICIENT_EVIDENCE (security: thiếu human_security_review)
```

**Chống bureaucracy:** không bắt user viết profile cho mọi requirement. **Risk level → profile mặc định** (template), requirement chỉ khai báo phần khác biệt:

| Risk | Profile mặc định |
|---|---|
| low | functional: [build, lint] |
| medium | functional: [unit_test] · architecture: [deterministic_rule] |
| high | + integration_test · ai_review (cross-model) · static_security_analysis |
| critical | + human_review · property/fuzz test cho invariant liên quan |

**Quy tắc độc lập:** evidence chỉ được tính khi **người/cái tạo ra nó độc lập với implementer** — agent tự khai báo không bao giờ được tính; AI review cùng model với implementer không được tính cho chiều đòi hỏi review.

**Tier A0–A5** chỉ giữ lại làm **nhãn hiển thị tóm tắt trên UI** (mức kiểm chứng tổng quát của một requirement), **không** phải thang đo toán học, và **không** dùng để quyết định acceptance.

> Không dùng con số kiểu *"assurance 93%"*: không có cơ sở để cộng một unit test với một security review, và con số đó tạo **false confidence**. Thay vào đó: **từng chiều đủ / thiếu, và thiếu cụ thể cái gì.**

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
- Mỗi AC phải map tới evidence thoả evidence profile của requirement.

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
| **Evidence coverage** | % requirement thoả evidence profile; vùng chưa bao phủ được liệt kê rõ |
| **Cost / accepted task** | Token + thời gian |
| **Rework rate** | % task DONE bị mở lại / revert |

---

## 13. State model, lưu trữ & recovery

### 13.1. Hai loại state

| | **Project State** | **Execution State** |
|---|---|---|
| Tuổi thọ | Dài hạn | Tạm thời |
| Tính chất | Authoritative | Recoverable |
| Gồm | Intent, Constitution, accepted changes, evidence hiện hành, architecture reality | Session đang chạy, lease, tiến độ task, checkpoint, retry counter, runtime telemetry |
| Mất đi thì | **Không chấp nhận được** | Chấp nhận được — khôi phục hoặc làm lại |

Một session có thể crash, agent có thể bị kill, máy có thể restart — **project state không được mất theo**.

### 13.2. Phân loại theo độ tin cậy

| Lớp | Ví dụ | Nguồn sự thật | Mất thì |
|---|---|---|---|
| **Authoritative** | Code (Git), intent/constitution files, event log | Chính nó | Không được mất |
| **Derived** | State projection, traceability index, impact graph, read-set derived | Tính lại từ authoritative | Rebuild |
| **Ephemeral** | Lease, session, telemetry, checkpoint chưa submit | Không | Bỏ hoặc làm lại |

**Khi mâu thuẫn:**
- **Code ↔ event log về những gì đã thay đổi** → Git thắng (commit tồn tại là sự thật). Event log được vá bằng cách quét commit trailer `AIEOS-Task:`.
- **Intent files ↔ projection** → file thắng; projection rebuild.
- **Lease ↔ thực tế** → lease hết hạn là hết hạn, bất kể agent nghĩ gì (fencing, bên dưới).

### 13.3. Recovery & tính nhất quán

| Vấn đề | Cơ chế |
|---|---|
| **Crash giữa transaction** (đã commit Git, chưa ghi event) | Khi khởi động: **reconcile Git ↔ event log**; commit có trailer mà không có event → tạo event bù, đưa task về VERIFYING |
| **Duplicate events** (retry ghi) | Mỗi event có **ID idempotent**; ghi trùng bị bỏ qua |
| **Stale writes** — agent "zombie" vẫn chạy sau khi lease hết hạn và task đã giao cho agent khác | **Fencing token**: mỗi lần cấp lease tăng một số đơn điệu; mọi submit phải mang token; token cũ bị từ chối |
| **Ghi đồng thời vào `.aieos/`** | Chỉ AIEOS core ghi, qua một writer duy nhất; agent ghi qua protocol |
| **Projection hỏng** | Xoá và replay event log |

### 13.4. Lưu trữ

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
3. **Evidence graph + evidence profile model**.
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
| **False confidence** — tuyên bố đúng khi kiểm tra không bao phủ lỗi | Phạm vi cam kết rõ ràng (mục 0); luôn hiển thị vùng chưa bao phủ; evidence profile theo chiều; AI review chỉ là một loại evidence |
| **Implementation complexity** — quá nhiều policy, state, gate, graph | Concept freeze; MVP chỉ phần deterministic; profile mặc định theo risk; Constitution có scope |
| **State tự drift khỏi code** | Reconciliation; code là sự thật về hiện trạng |
| **Runtime tự xây tính năng tương tự** | Trung lập đa runtime; định dạng mở; tập trung vào correctness |
| **Cold start với repo có sẵn** | `aieos import`: AI quét repo, đề xuất architecture + constitution, human duyệt |

---

## 16. MVP & Roadmap

### MVP v0.1 — "Claude Code không phá project của tôi"

Mục tiêu đo được: trên một project thật ~100 task, AIEOS **bắt được thay đổi sai mà agent báo là xong**, với human time thấp.

- [ ] `.aieos/` format: constitution (có `check`, `scope`), requirement (+ evidence profile), spec+AC, ADR, task contract (write-set/read-set), handoff
- [ ] `aieos init` / `aieos import` (đề xuất constitution từ repo)
- [ ] `aieos run "<ý định>"` — zero-friction path
- [ ] Resume Check (8 kiểm tra, deterministic) với read-set declared + derived
- [ ] Context Compiler v1 (graph-based, không semantic search)
- [ ] Execution decision + Acceptance decision tách biệt
- [ ] MCP server ~8 tools
- [ ] Adapter **Claude Code (T3)**: hooks enforce write-set, shell allowlist, chặn git push, ghi observed read-set
- [ ] Adapter **Codex (T1/T2)** — để chứng minh core trung lập ngay từ đầu
- [ ] Verification V0–V2, evidence gắn SHA, evidence profile mặc định theo risk (low/medium)
- [ ] Reconciliation deterministic (constitution, scope, stale evidence)
- [ ] Risk rule-based, autonomy L1–L2
- [ ] Event log (event ID idempotent), fencing token, recovery Git ↔ event log khi khởi động
- [ ] Chạy tuần tự (chưa song song)

### v0.2 — Assurance
V3 cross-model review, Change Impact Engine, profile high/critical, drift semantic (AI) với confidence, metrics.

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

---

## 18. Concept freeze

Từ v0.5, concept được **đóng băng**: không thêm primitive, không thêm module. Thay đổi concept chỉ khi technical spec hoặc dogfooding chứng minh một giả định sai.

**Những gì đã đóng băng:**
- Mission, thesis, phạm vi cam kết của correctness, 4 luật bất biến
- 5 primitives và Correctness Loop
- Phân loại sự kiện (INTENT_CHANGE / DRIFT / VIOLATION / STALE_EVIDENCE / CONFLICT)
- Execution decision ≠ Acceptance decision
- Truth Hierarchy; Project State ≠ Execution State

**Bước tiếp theo — technical specs, theo thứ tự:**

| # | Spec | Nội dung |
|---|---|---|
| 1 | **State & Event Model** | Schema các thực thể, danh sách event, projection, recovery, fencing |
| 2 | **`.aieos/` File Format** | Schema YAML/MD cho constitution, requirement, spec, ADR, task contract, handoff |
| 3 | **Resume Check & Decision Engine** | Thuật toán 8 kiểm tra, tính `Δ`, phát hiện thay đổi chữ ký interface, bảng quyết định |
| 4 | **Verification & Evidence** | Gate pipeline, evidence profile, quy tắc độc lập, mapping AC ↔ test |
| 5 | **Adapter Contract + Claude Code adapter** | Interface adapter, khai báo assurance, hooks mapping |
| 6 | **MCP Protocol** | Danh sách tool, input/output, lỗi |
| 7 | **CLI & zero-friction UX** | `aieos run / status / init / import`, luồng duyệt |

**Hoãn lại (P2):** historical intelligence, semantic drift detection bằng AI — chỉ làm sau khi reconciliation deterministic đã ổn định.
