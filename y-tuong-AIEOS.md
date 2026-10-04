\# AI-EOS là gì?



\*\*AI-EOS (AI Engineering Operating System)\*\* là một \*\*hệ thống điều hành/quản trị quá trình phát triển phần mềm bằng AI\*\*.



Nó không phải là một AI coding agent.



Nó nằm \*\*ở phía trên các AI coding agent\*\* như Claude Code, Codex, Cursor, Gemini/GLM..., và quản lý cách các agent đó làm việc trên một dự án.



```text

&#x20;                AI-EOS

&#x20;       ┌─────────────────────┐

&#x20;       │ Governance           │

&#x20;       │ Project Context      │

&#x20;       │ Requirements         │

&#x20;       │ Architecture         │

&#x20;       │ Tasks                │

&#x20;       │ Workflow             │

&#x20;       │ Agent Control        │

&#x20;       │ Verification         │

&#x20;       │ Evidence             │

&#x20;       │ Change Management    │

&#x20;       └──────────┬──────────┘

&#x20;                  │

&#x20;       ┌──────────┼──────────┐

&#x20;       ↓          ↓          ↓

&#x20;  Claude Code   Codex     Cursor/GLM

&#x20;       │          │          │

&#x20;       └──────────┼──────────┘

&#x20;                  ↓

&#x20;             PROJECT

```



\## Mục đích duy nhất của AI-EOS



AI-EOS giải quyết một vấn đề:



> \*\*Làm thế nào để AI có thể xây dựng một phần mềm phức tạp trong thời gian dài, qua rất nhiều task, rất nhiều session, thậm chí nhiều AI khác nhau, mà dự án không bị mất context, drift, mâu thuẫn, trùng lặp, phá architecture hoặc tự ý thay đổi yêu cầu?\*\*



Đây là \*\*core problem\*\*.



\---



\# AI-EOS làm gì?



Nó kiểm soát toàn bộ vòng đời AI làm việc trên project:



```text

Project

&#x20;  ↓

Requirements

&#x20;  ↓

Specifications

&#x20;  ↓

Architecture

&#x20;  ↓

Tasks

&#x20;  ↓

AI Agent

&#x20;  ↓

Implementation

&#x20;  ↓

Verification

&#x20;  ↓

Evidence

&#x20;  ↓

Release

```



AI-EOS phải luôn biết:



> \*\*Project đang là gì?\*\*



> \*\*Đang xây cái gì?\*\*



> \*\*Tại sao phải xây nó?\*\*



> \*\*Đang ở đâu trong quá trình xây dựng?\*\*



> \*\*Task hiện tại là gì?\*\*



> \*\*Task này phụ thuộc vào cái gì?\*\*



> \*\*Agent được phép làm gì?\*\*



> \*\*Agent không được phép làm gì?\*\*



> \*\*Context nào cần cung cấp cho agent?\*\*



> \*\*Những quyết định nào đã được đưa ra?\*\*



> \*\*Những gì đã được implement?\*\*



> \*\*Những gì đã được verify?\*\*



> \*\*Những gì chưa được verify?\*\*



> \*\*Thay đổi nào cần approval?\*\*



> \*\*Khi nào agent phải dừng lại?\*\*



\---



\# Điểm quan trọng nhất: AI-EOS quản lý “state” của việc phát triển phần mềm



Ví dụ một project có 5.000 task và 1.000 AI sessions.



Không thể dựa vào:



```text

Claude nhớ

\+

CLAUDE.md

\+

conversation history

```



để quản lý project.



AI-EOS phải có một \*\*canonical project state\*\*.



Ví dụ:



```text

Project State

│

├── Requirements

├── Specifications

├── Architecture

├── Decisions

├── Tasks

├── Dependencies

├── Agents

├── Permissions

├── Workflow State

├── Current Session

├── Previous Handoffs

├── Changes

├── Approvals

├── Tests

├── Evidence

└── Release State

```



Session mới của Claude không cần “nhớ” session cũ.



Nó \*\*khôi phục project state từ AI-EOS\*\*.



Đây là điểm cực kỳ quan trọng.



\---



\# AI-EOS không thay thế Claude Code



Ví dụ:



```text

AI-EOS

&#x20;  │

&#x20;  │ "TASK-142 được phép thực hiện"

&#x20;  │

&#x20;  ↓

Claude Code

&#x20;  │

&#x20;  │ viết code

&#x20;  ↓

Repository

&#x20;  │

&#x20;  ↓

AI-EOS

&#x20;  │

&#x20;  │ kiểm tra

&#x20;  ├── requirement?

&#x20;  ├── scope?

&#x20;  ├── architecture?

&#x20;  ├── tests?

&#x20;  ├── evidence?

&#x20;  └── approval?

```



Claude là \*\*worker\*\*.



AI-EOS là \*\*control plane\*\*.



\---



\# AI-EOS phải độc lập với AI cụ thể



Đây là mục tiêu startup quan trọng nhất của ý tưởng này.



Không xây:



```text

Claude Engineering OS

```



mà xây:



```text

AI Engineering OS

```



Claude Code chỉ là \*\*một runtime adapter\*\*.



Sau này:



```text

&#x20;                   AI-EOS

&#x20;                     │

&#x20;      ┌──────────────┼──────────────┐

&#x20;      ↓              ↓              ↓

&#x20;Claude Code        Codex         Cursor

&#x20;      │              │              │

&#x20;      └──────────────┼──────────────┘

&#x20;                     ↓

&#x20;                  Project

```



Do đó project governance nằm ở AI-EOS, không nằm trong Claude.



\---



\# AI-EOS khác Jira/Linear như thế nào?



Jira/Linear chủ yếu quản lý:



```text

Issue

Task

Status

Assignee

```



AI-EOS quản lý:



```text

WHY

&#x20;↓

Requirement

&#x20;↓

Specification

&#x20;↓

Architecture

&#x20;↓

Task

&#x20;↓

AI execution

&#x20;↓

Verification

&#x20;↓

Evidence

&#x20;↓

Release

```



Nó quản lý \*\*engineering reasoning + execution state + governance\*\*, không chỉ task management.



\---



\# AI-EOS khác Git như thế nào?



Git trả lời:



> Code đã thay đổi như thế nào?



AI-EOS trả lời:



> \*\*Tại sao thay đổi? Ai được phép thay đổi? Requirement nào yêu cầu thay đổi? Architecture nào cho phép? Task nào thực hiện? Đã verify chưa? Evidence ở đâu? Có approval chưa?\*\*



Git vẫn tồn tại.



AI-EOS nằm phía trên Git.



\---



\# AI-EOS khác CLAUDE.md như thế nào?



CLAUDE.md là:



> Context/instruction cho Claude.



AI-EOS là:



> \*\*Hệ thống quản trị toàn bộ quá trình AI engineering.\*\*



CLAUDE.md, rules, skills, hooks, subagents, permissions... chỉ là \*\*công cụ mà adapter của AI-EOS có thể sử dụng\*\*.



\---



\# AI-EOS có 5 nhiệm vụ cốt lõi



Nếu phải rút toàn bộ ý tưởng xuống mức tối thiểu, tôi sẽ giữ đúng 5 thứ:



\### 1. Context



Đảm bảo AI luôn có \*\*đúng context cần thiết\*\* để làm task.



\### 2. Control



Đảm bảo AI \*\*chỉ được làm những gì nó được phép làm\*\*.



\### 3. Continuity



Đảm bảo công việc có thể tiếp tục chính xác qua \*\*nhiều session, nhiều task, nhiều agent\*\*.



\### 4. Verification



Đảm bảo AI không chỉ nói:



> “Done.”



mà phải chứng minh:



> \*\*“Done và đây là evidence.”\*\*



\### 5. Traceability



Đảm bảo mọi thay đổi đều có chuỗi:



```text

Requirement

&#x20;   ↓

Specification

&#x20;   ↓

Task

&#x20;   ↓

Implementation

&#x20;   ↓

Test

&#x20;   ↓

Evidence

```



\---



\# Và toàn bộ AI-EOS có thể cô đọng thành một câu



> \*\*AI-EOS là một control plane độc lập với AI model, dùng để quản lý context, state, workflow, permissions, tasks, changes và verification của quá trình phát triển phần mềm bằng AI, nhằm đảm bảo nhiều AI agents có thể xây dựng một project phức tạp qua hàng trăm/hàng nghìn sessions mà không làm mất tính nhất quán và khả năng kiểm soát của project.\*\*



Hay nói ngắn hơn nữa:



> \*\*AI-EOS = hệ điều hành cho việc xây dựng phần mềm bằng AI.\*\*



Claude/Codex/Cursor là \*\*developers\*\*.



Project là \*\*system being built\*\*.



AI-EOS là \*\*operating system điều phối và kiểm soát các AI developers đó\*\*.



Và \*\*đó mới là mục đích ban đầu của ý tưởng này\*\*.



