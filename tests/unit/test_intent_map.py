"""Unit tests of aieos_bootstrap.intent_map (TASK-160, BT3b-2d-3): the mapper of the self-build's intent versions.

The real rows below are whole rows of docs/pre-genesis/decision-matrix.md at the contract's base commit
11bd419d55381aeff55f25db19bba66f8162781a, taken by script (the line n of the output of git show of that file at that
commit, split on the line feed) and written verbatim; the test checks the SHA-256 of each. No test here runs Git, reads or
writes a file other than the module's own source, or makes a temporary folder.
"""
import ast
import copy
import hashlib
import pathlib
import re
import sys
import unittest
from unittest import mock

from aieos_bootstrap import intent_map

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap' / 'intent_map.py'
M = intent_map

# line number of the row -> (the SHA-256 of its UTF-8 bytes, the row)
ROWS = {
    121: ('6d5ef57ed9721c605433ec3110a68afab6031a56e756ea86d476012676c3bfc6',
          r'''| A60 | **Yes on the exact texts of the Genesis amendment to version 2, and no to deleting two stray files: "1 có/ 2 không" (owner decision, 2026-10-08; answers to the questions of decision D-170).** Owner's words, 2026-10-08 (session 5822a9d1-5741-438b-b301-426721ddb30e, transcript :1433, 15:42:30 UTC, 22:42 local; a message of origin human), verbatim: "1 có/ 2 không". The two questions, verbatim as sent in the turn-final reply at :1429, question 2 as its last text (the list numbers omitted): question 1: "Bạn có đồng ý với đúng các văn bản sửa tài liệu nền mà agent quyết định đã xét không? Chúng ghi hai câu trả lời của bạn hôm nay: cách sắp xếp nơi giữ ghi chép cùng câu đính chính ghi kèm bản ý tưởng; và với những việc rủi ro cao và rủi ro cao nhất khi xây chính AIEOS, phải có cả bản soát của một trợ lý chạy phiên bản Claude khác lẫn bản soát của chính agent quyết định, áp dụng ngay từ bây giờ chứ không đợi phiên bản sau; kèm theo là vài chi tiết kỹ thuật do agent chọn để phần chấm việc dùng được quy tắc này, và hai bài thử mới cho nó. Cái giá: cả hai bản soát đều do AI của cùng một hãng làm, nên có thể cùng mắc một lỗi mà không ai thấy. Nếu "có": các văn bản được đưa lên GitHub, nơi nội dung ở lại vĩnh viễn, và thành bản khởi tạo mới, muốn đổi về sau phải làm một bản sửa đổi khác; nếu "không", hoặc bạn chưa trả lời: không có gì thay đổi, và những việc rủi ro cao, gồm việc lập trình phần chấm việc ở chặng tới, chưa được nhận. Agent quyết định khuyên trả lời "có", vì các văn bản ghi đúng hai câu trả lời của bạn, còn phần thêm chỉ là chi tiết để áp dụng chúng và đã ghi rõ là của agent."; question 2: "Có cho Claude xoá hai tệp nháp nhỏ mà Claude lỡ tạo ra ngoài chỗ làm việc tạm hôm nay không? Hai tệp chỉ chứa danh sách tên tệp, không có gì bí mật và không đụng tới dự án. Nếu có: Claude xoá đúng hai tệp ấy; xoá rồi không lấy lại được, nhưng nội dung có thể tạo lại y hệt bất cứ lúc nào. Nếu không, hoặc bạn không trả lời: hai tệp nằm yên và không ảnh hưởng gì. Agent quyết định khuyên trả lời "không", vì giữ chúng không có hại và chúng còn là dấu vết của lỗi.". Both answers match the recommendations ("có" and "không"). The owner's words cover only the quoted text; the rest of this row is Claude's wording. Answer 1 is the owner's yes on exactly the texts that decision D-170 C2 froze, `docs/pre-genesis/CR-001-concept-errata.md` (SHA-256 c1b38babc1fad92ba152a30987b81ed11f516e267aee98666c8bdf75549db6e5), `docs/pre-genesis/CR-002-concept-errata.md` (446c8523339a11c62ada936ba4b3001cde26dc5e3eac6ea234b78cec13b4a3e1), `docs/pre-genesis/assurance-model.md` revision 5 (945615316968a5c064bf88be71add9271bbb9f95692eaa22582b6020fa69cb85), `docs/pre-genesis/governor-spec.md` revision 5 (423a1f3743b124bab7e672f7be5615e18f2a178d9b9991587d5aaa9f6ea37cea), `docs/pre-genesis/conformance-scenarios-initial.md` revision 4 (6b5c0666a1f364f5ecec9ad516c9a749969a1963f4e5dbef566adcbc8c80e24d) and `docs/genesis/genesis-charter-v2.md` (8985f168c837c2c157fd0d8368904f4bb45877ebdf00e586b171a19c23633572), with the charter's changed bindings, item 3 included; they were added as one isolated change by commit 4645125f4d75217679e1d2df87ba81fce7afbe82 (decision D-171). It is the owner's part of the ratification of Genesis instance 2; the decision agent's part, for the items unchanged from version 1, is row F14. With these texts, CR-001 E4 is closed, and CR-001 E10 is closed for gov-AIEOS and stays open for AIEOS projects. Answer 2: the two files that Claude wrote outside its scratchpad by mistake on 2026-10-08 stay, and nothing is done with them (decisions D-168 and D-171). Recorded under decision agent decision D-172 (A41). |'''),  # noqa: E501
    128: ('d64057eba43f657e7640b33c8ec49cef6c591aaf6352fafb5a6dd03bb841621a',
          r'''| A67 | **Yes on the exact texts that record A66, with the ratification of Genesis version 4: "đồng ý tất cả" (owner decision, 2026-10-10; answers to the two questions of decision D-321).** Owner's words, 2026-10-10 (session 72b399d0-d69b-4466-a3e4-ad9adccb0afd, transcript :761, 09:48:10 UTC, 16:48 local; a message of origin human), verbatim: "đồng ý tất cả". The questions were sent as the last text of the turn-final reply at :757, which quoted every changed text verbatim and offered "đồng ý tất cả" as an answer to both; verbatim: question (1): "Bạn có đồng ý với đúng đoạn luật gốc SEC-003 ở mục 1 và việc ghi nó vào bản điều lệ gốc thứ tư, và việc bản điều lệ gốc thứ tư khoá luôn dòng ghi lời bạn trong bảng quyết định, để không ai sửa được mà không hỏi lại không?"; question (2): "Bạn có đồng ý với đúng các đoạn đổi của bản hướng dẫn ở mục 2 và ở b), c), d), và đoạn sổ quy tắc ở mục 3 không? Nếu có, khi Claude ghi bản hướng dẫn, máy sẽ hiện hộp xin phép; bạn bấm cho phép." The owner's words cover only the quoted texts; the rest of this row is Claude's wording. It is the ratification record of Genesis instance 4 (Genesis version 4), `docs/genesis/genesis-charter-v4.md`, SHA-256 89c8d0f2baa90cc63c3b191a52c2b66ee3ee72b4f18439c4bcf4437b07db12e5, added with constitution revision 4 (SHA-256 9b396c3c0f31d3a3fbccf9433cf81eb820b6e0f0a3a7d099e2899043abfe1f5a) in commit a9722122de79a929dcc40d4f6b10ac1f08e85cd2, the owner's ratification in their own words (`genesis-model.md` §5 point 3; the charter's "Who ratifies"); and the owner's yes to the decision agent's definition revision 10 (SHA-256 5228fe63a190f1e3694f1bd70b9982ae182403d56d7ed6b6eaad40f7ab25aa60; see A41, revision-10 marker) and to the line of Claude's rules book that records A66 (SHA-256 bb6de6ea8bc706ad712de2bedf5628ed237750542f7402750461cf126cc37501). With this row, A66 is in force (A66, its effect condition). Recorded under decision agent decisions D-321, D-322 and D-323 (A41). |'''),  # noqa: E501
    275: ('d392f4b56eea98c27d18c8ba159f96cf06c2a8edb61fd90a647a537a752ab385',
          r'''| F32 | Approval in the owner's place of specification 4, Verification & Evidence, `docs/specs/spec-04-verification-and-evidence.md` revision 3 (concept §18, line 994, and lines 947 to 949; Master Plan §4 M4 and §5; A51 items (2), (5); CR-002 header, last paragraph; DM B9, proposed, with its A51 note; the drafting plan for specification 4, decision D-417): SHA-256 48d4f5bf06461ad49409f21bc6ea8d511d17a84eaac15adda14277483176a8d5, the file added in the same commit as this row, at an interim path (the layout is settled, F16; the specifications move only when a core writes the project-state directory). It baselines the specification for gov-AIEOS (B9); the choices it marks "(proposed)" are approved as its content and stay listed in its section 12, and its open points stay open, among them the points it leaves to the next revisions of the governor specification and of specification 2 (its section 12 points 7, 8 and 10) and the list of non-task paths, which is a change to the policy and not made here (its section 12 point 11). Reviewed before approval by five way-2 reviews on claude-sonnet-5-5 of revision 1 (two "pass", three "fail" with five blocking findings, all applied in revision 2) and one way-2 review on claude-sonnet-5-5 of the fixes (revision 2a, "pass", its non-blocking findings applied in revision 3), and read by the decision agent. It restates no bound text and changes none (the assurance model, the governor specification and the constitution are cited, not restated), weakens no evidence requirement (CR-002 part 4 limit 8) and raises no autonomy level: L2 for gov-AIEOS while P-CRED or C13 is not PASS stays the owner's. A delegated approval with advisory effect, which stays advisory even if P-CRED later passes (A31, A41; CR-002 part 1); the owner's one-sentence revocation keeps immediate effect (A55). It approves no task, no code, no change under `.github/` and no act that the owner keeps (A51 item (4); CR-002 parts 4 and 8), and it changes no concept text. No earlier row's text or status changes. | Decided by: decision agent (A41, A51), D-426, 2026-10-11 (session 9dd21f8f-a4fd-4d04-8a61-3d1263c5cc7e, decision agent a06c387b91138c60d, the D-426 handback); relayed to the owner in plain words. | DELEGATED |'''),  # noqa: E501
    314: ('20b370d6fca0fba52ecc1fc64f4698c0e81a0beeb931c51dbb5461d5f922d487',
          r'''| F71 | Approval in the owner's place of specification 1, the State & Event Model, `docs/specs/spec-01-state-and-event-model.md` revision 4 (concept §18, line 991; A51 items (2), (5); DM B9, proposed, with its A51 note; DEF-0026 and DEF-0039; decisions D-255 Q4, D-390 and D-3601): SHA-256 c79897a1f82590046e1f49c3753e934e0b3df2893f0c627dd6ac90c8b8c6eebb, the file changed in the same commit as this row. Revision 4's section 5.3 names, as an effect of `conflict.detected`, specification 3 section 10's STOP: scope invalid beside CONTINUE_WITH and REPLAN: a write-set collision that is not an interface-breaking CONFLICT, after which the task is blocked and gets no `task.stale`; and its section 7 step 1 counts only a lease whose expiry time has not passed, even if the store has not yet expired it, as section 8 does at submission (concept line 849), so a commit made under a lease past its expiry gives the unfenced-write observation, the reading TASK-009 follows (D-390). It also changes its status line and its revision list. No entity, event, state or decision value changes, and no event type is added. Its edits read by the decision agent against their sources (D-3601) and its final text and diff read by the decision agent (the decision that approves this row); no reviewer ran (D-3601). No code changes, nothing is built, launched or measured; C6, A69 and A51 item (4) are untouched. It baselines the revision for gov-AIEOS (B9); the choices it marks "(proposed)" are approved as its content and stay listed in its section 10, and its open points stay open. A delegated approval with advisory effect, which stays advisory even if P-CRED later passes (A31, A41; CR-002 part 1); the owner's one-sentence revocation keeps immediate effect (A55). It approves no task, no code and no act that the owner keeps (A51 item (4); CR-002 parts 4 and 8), and it changes no concept text. Revision 3 stays recorded (F64). No earlier row's text or status changes. | Decided by: decision agent (A41, A51), the decision that approves this row, 2026-10-29 (session 1c1bf794-6b03-4a8a-a03c-4faf37964507); relayed to the owner in plain words. | DELEGATED |'''),  # noqa: E501
    315: ('14986c5a55e832661701133e271f0a2d8521ac99d1bbc77c94c2cfae1cd500a6',
          r'''| F72 | Approval in the owner's place of specification 3, Resume Check & Decision Engine, `docs/specs/spec-03-resume-check-and-decision-engine.md` revision 6 (concept §18, line 993; A51 items (2), (5); DM B9, proposed, with its A51 note; DEF-0083; decisions D-1325, D-1326 C7 and D-3604): SHA-256 fc65d9a6490fa740072bb47dce142e17c6d82dcf0a5c7bc515965c97015eb59a, the file changed in the same commit as this row. Revision 6 changes the citations of its section 1 input table (the row on the base branch's name and the module roots) and of its section 12 point 10 to the keys `base_branch` and `module_roots` of specification 2 section 7 (proposed there), where they said that specification 2 section 7 has no key for them; it also changes its status line and its revision list. No check, rule, input, outcome or decision value changes. Its edits read by the decision agent against their sources (D-3604) and its final text and diff read by the decision agent (the decision that approves this row); no reviewer ran (D-3604). No code changes, nothing is built, launched or measured; C6, A69 and A51 item (4) are untouched. It baselines the revision for gov-AIEOS (B9); the choices it marks "(proposed)" are approved as its content and stay listed in its section 12, and its open points stay open. A delegated approval with advisory effect, which stays advisory even if P-CRED later passes (A31, A41; CR-002 part 1); the owner's one-sentence revocation keeps immediate effect (A55). It approves no task, no code and no act that the owner keeps (A51 item (4); CR-002 parts 4 and 8), and it changes no concept text. Revision 5 stays recorded (F54). No earlier row's text or status changes. | Decided by: decision agent (A41, A51), the decision that approves this row, 2026-10-29 (session 1c1bf794-6b03-4a8a-a03c-4faf37964507); relayed to the owner in plain words. | DELEGATED |'''),  # noqa: E501
    317: ('2f314ab5ed66b02e32873716e8b6fd82e55052630aae2bcd0c29cd3591d266c5',
          r'''| F74 | Approval in the owner's place of specification 6, MCP Protocol and Work Orders, `docs/specs/spec-06-mcp-protocol-and-work-orders.md` revision 8 (concept §18; Master Plan revision 4 §4 M6; A51 items (2), (5); DM B9, proposed, with its A51 note; F62; DEF-0098; decisions D-2403, D-2409 and D-3608): SHA-256 ff2f80e24e8b519d3cb4ab7904e613f6dfb6c5c3a991c63bf38de4826def8b69, the file changed in the same commit as this row. Revision 8 writes into it the stated choices of TASK-083's two tools: `query` answers any item the Work Order holds, in full or by reference, and `out_of_scope` or `not_found` otherwise (section 4); a missing or out-of-form base gives `no_session` for `get_work_order` and `query` (section 4); the answer form of `core_error` with its `detail` (section 8); the Work Order is compiled at each call and is the same object only while the task's last approval and last Resume Check record stay the same (section 5); section 5 and section 11 point 7 now say "nowhere in revision 8"; section 11 points 7 and 13 are widened to name the compiling at each call and the answer form; it also changes its status line, its "Drafted under" line and its revision list. No tool is added and no key or decision value changes. Its edits read by the decision agent against their sources (D-3608) and its final text and diff read by the decision agent (the decision that approves this row); no reviewer ran (D-3608). Nothing is built, launched, connected or measured; C6, A69 and A51 item (4) are untouched. It baselines the revision for gov-AIEOS (B9); the choices it marks "(proposed)" are approved as its content and stay listed in its section 11, and its open points stay open. A delegated approval with advisory effect, which stays advisory even if P-CRED later passes (A31, A41; CR-002 part 1); the owner's one-sentence revocation keeps immediate effect (A55). It approves no task, no code and no act that the owner keeps (A51 item (4); CR-002 parts 4 and 8), and it changes no concept text. Revision 7 stays recorded (F62). No earlier row's text or status changes. | Decided by: decision agent (A41, A51), the decision that approves this row, 2026-10-29 (session 1c1bf794-6b03-4a8a-a03c-4faf37964507); relayed to the owner in plain words. | DELEGATED |'''),  # noqa: E501
    319: ('6bb40d3cf3e4b7b4ac65c88d35b697dc142b5b8b4cb397c389b15ab612167ebf',
          r'''| F76 | Approval in the owner's place of the conformance files document of gov-AIEOS, `docs/specs/conformance-files.md` revision 11 (Master Plan §4 M5; `conformance-methodology.md` §10 point 4; DM B1, B10, with their A51 notes; A51 items (2), (5); CR-002 header, last paragraph; DEF-0043 (e); decisions D-462 and D-3611): SHA-256 efb9903e5981f836be7bd841bdca8fe2140661f7bac7a0aabe62414fac5ceca9, the file changed in the same commit as this row, at an interim path. Revision 11 is wording only: in section 10's table row `values`, `articles` is described as the articles the derivation reads, given as values of the form `{id, scope, evidence_required}`, where it said "the constitution's articles", which cannot be literal while the constitution names its scopes by role and three of them are "all paths"; section 9's row `inputs`, which uses the same words for the Resume Check input `articles`, is not changed by this revision; it also changes its status line, its "What it is" line and its revision list. No rule, key, spelling, placeholder rule, Given, malformedness rule, comparison, path or expected result changes, nothing widens what a fixture accepts, and no fixture or set file changes or is frozen by this row (the frozen RISK-01 fixture, F69, and the set file, F70, are unaffected). Its edit read by the decision agent against its sources (D-3611) and its final text and diff read by the decision agent (the decision that approves this row); no reviewer ran (D-3611). The choices it marks "(proposed)" are approved as its content and stay listed in its section 12. It changes no scenario, no expected result and no rule of the conformance methodology. A delegated approval with advisory effect, which stays advisory even if P-CRED later passes (A31, A41; CR-002 part 1); the owner's one-sentence revocation keeps immediate effect (A55). It approves no task, no code and no act that the owner keeps (A51 item (4); CR-002 parts 4 and 8), and it changes no concept text. Revisions 1 to 10 stay recorded (F18, F20, F27, F28, F30, F33, F41, F45, F48). No earlier row's text or status changes. | Decided by: decision agent (A41, A51), the decision that approves this row, 2026-10-29 (session 1c1bf794-6b03-4a8a-a03c-4faf37964507); relayed to the owner in plain words. | DELEGATED |'''),  # noqa: E501
    328: ('51b40b848dafdc34946ecec89523b3bd8926699472a3f820d63b66120dc3ec9e',
          r'''| F85 | Approval in the owner's place of specification 5, Adapter Contract + Claude Code adapter, `docs/specs/spec-05-adapter-contract.md` revision 8 (concept §18, line 995; A51 items (2), (5); A69; A74; DM B9, proposed, with its A51 note; specification 2 revision 12; TASK-117, accepted at D-4776, its task commit X3 7253aa9c on main; decisions D-4736, D-4737, D-4742, D-4776 and the decision that approves this row): SHA-256 5a0d6f03130b973d137fbf2012ab2d3436c37ef4663296479603fb8af9802056, the file as TASK-117's task commit changed it and unchanged since. Revision 8 replaces, in section 3's last bullet, the sentence "No declaration of it exists, so until one is made and measured, check 7 gives STOP: runtime insufficient for its tasks (the first case above)" so that it stays true after the state commit that puts an unmeasured declaration into the policy file at the base: until that commit none exists and check 7 gives STOP for every task; after it the declaration is read under specification 2 section 7.1 item 2 and the owner's answer A74 (`max_risk` `low`), and check 7 gives STOP for a task above low; the specification names no tier and no measurement for the runtime beyond what the declaration states. Section 11 point 14 is kept as written (no task above low risk leased through the core until the owner has measured the runtime; any interim rule is the owner's). It also changes the status line and the "Drafted under" line. No other rule, requirement, outcome or decision value changes. Its edit was read by the decision agent against its source (specification 2 revision 12) and by the read-only reviews of the TASK-117 change, whose findings the decision agent ruled (D-4776). Nothing is launched, connected or measured; launching a real tool is decided as its own decision (DM A73). It baselines the revision for gov-AIEOS (B9); the choices it marks "(proposed)" are approved as its content and stay listed in its section 11, and its open points stay open. A delegated approval with advisory effect, which stays advisory even if P-CRED later passes (A31, A41; CR-002 part 1); the owner's one-sentence revocation keeps immediate effect (A55). It approves no task, no code and no act that the owner keeps (A51 item (4) as A73 amends it; CR-002 parts 4 and 8), and it changes no concept text. Revision 7 stays recorded (F73). No earlier row's text or status changes. | Decided by: decision agent (A41, A51), the decision that approves this row, 2026-11-05 (session a0a0bdef-5258-47a7-94c1-6ba559edca43); relayed to the owner in plain words. | DELEGATED |'''),  # noqa: E501
    330: ('70d96a7a25e75e11587ba80c6491b1ded46f1402e52d66160736aff5d41c5ce7',
          r'''| F87 | Approval in the owner's place of specification 7, the CLI and the Zero-friction Path, `docs/specs/spec-07-cli-and-zero-friction-path.md` revision 13 (concept §18, line 997; A51 items (2), (5); A73; A75; A77; DM B9, proposed, with its A51 note; DEF-0095; DEF-0101; F86; TASK-134, accepted at D-6205 and effective at D-6208; decisions D-6202, D-6205, D-6208 and D-6219 and the decision that approves this row): SHA-256 b3b36bb338c2a6e5d80e5454b490e4ef9d1e4c856e021e59d828dbf931a15028, the file changed in the same commit as this row. Revision 13 changes three sentences and the revision list: section 3's bullet `aieos launch <task>` (the shipped command now passes the starter of src/aieos_runtime to launcher.launch_outside; for the runtime-starter software only, DM row A75 makes the acceptance the decision agent's and DM row A77 its review step; each real launch is its own decision under DM A73), section 7's account of the handoff file (the shipped command passes the real starter, and no real session has been run) and section 10's item 6; it also changes its status line, its "Drafted under" line and its revision list. The headers of DEF-0095 and DEF-0101 are changed in the same commit, as working records. No rule, command or open point otherwise changes. Its diff against revision 12 was read in full by the decision agent (decision D-6220); no other reviewer read it (decision D-6208). This row approves no task, no code and no launch: no real run has been made, and each real launch, the first included, is its own decision of the decision agent under DM A73 (decisions D-6202 and D-6205). It baselines the revision for gov-AIEOS (B9); the choices it marks "(proposed)" are approved as its content and stay listed in its section 10, and its open points stay open. A delegated approval with advisory effect, which stays advisory even if P-CRED later passes (A31, A41; CR-002 part 1); the owner's one-sentence revocation keeps immediate effect (A55). It approves no task, no code and no act that the owner keeps (A51 item (4) as A73 amends it; CR-002 parts 4 and 8), and it changes no concept text. Revision 12 stays recorded (F86). No earlier row's text or status changes. | Decided by: decision agent (A41, A51), the decision that approves this row, 2026-11-14 (session 86f64e95-6029-4e67-8582-7d92a441a275); relayed to the owner in plain words. | DELEGATED |'''),  # noqa: E501
}

PG = 'docs/pre-genesis/'
SP = 'docs/specs/'
# (line, path, version, SHA-256 of the file as the row names it)
ENTITIES = (
    (121, PG + 'assurance-model.md', 'v5', '945615316968a5c064bf88be71add9271bbb9f95692eaa22582b6020fa69cb85'),
    (121, PG + 'governor-spec.md', 'v5', '423a1f3743b124bab7e672f7be5615e18f2a178d9b9991587d5aaa9f6ea37cea'),
    (121, PG + 'conformance-scenarios-initial.md', 'v4', '6b5c0666a1f364f5ecec9ad516c9a749969a1963f4e5dbef566adcbc8c80e24d'),
    (128, PG + 'constitution.md', 'v4', '9b396c3c0f31d3a3fbccf9433cf81eb820b6e0f0a3a7d099e2899043abfe1f5a'),
    (275, SP + 'spec-04-verification-and-evidence.md', 'v3', '48d4f5bf06461ad49409f21bc6ea8d511d17a84eaac15adda14277483176a8d5'),
    (314, SP + 'spec-01-state-and-event-model.md', 'v4', 'c79897a1f82590046e1f49c3753e934e0b3df2893f0c627dd6ac90c8b8c6eebb'),
    (315, SP + 'spec-03-resume-check-and-decision-engine.md', 'v6',
     'fc65d9a6490fa740072bb47dce142e17c6d82dcf0a5c7bc515965c97015eb59a'),
    (317, SP + 'spec-06-mcp-protocol-and-work-orders.md', 'v8', 'ff2f80e24e8b519d3cb4ab7904e613f6dfb6c5c3a991c63bf38de4826def8b69'),
    (319, SP + 'conformance-files.md', 'v11', 'efb9903e5981f836be7bd841bdca8fe2140661f7bac7a0aabe62414fac5ceca9'),
    (328, SP + 'spec-05-adapter-contract.md', 'v8', '5a0d6f03130b973d137fbf2012ab2d3436c37ef4663296479603fb8af9802056'),
    (330, SP + 'spec-07-cli-and-zero-friction-path.md', 'v13', 'b3b36bb338c2a6e5d80e5454b490e4ef9d1e4c856e021e59d828dbf931a15028'),
)
# SHA-256 at the base commit of two files that no row names
NONE = {'AIEOS-concept.md': '19cfa266334aa20d1ac1bc15f5cf92d0fc6d3bbbd98c13cfcb42ad6fd5a8357c',
        SP + 'evaluation-policy-gov-aieos.md': '0777508cafbc5c0c09fb1718bebbf2f8233c492b0569849137d76da14aef8ddb'}
REAL_DM = '# DM\n\n' + ''.join(row + '\n' for _, row in ROWS.values())
P = 'docs/x.md'
H = 'a' * 64


def matrix(*rows):
    return '# DM\n\n' + ''.join(row + '\n' for row in rows)


def run(*rows, entities=None):
    return M.map_intent_versions({P: H} if entities is None else entities, matrix(*rows))


class Base(unittest.TestCase):
    def refused(self, answer, reason):
        self.assertEqual(set(answer), {'value', 'findings'})
        self.assertIsNone(answer['value'])
        self.assertEqual(len(answer['findings']), 1)
        self.assertEqual(set(answer['findings'][0]), {'reason', 'detail'})
        self.assertEqual(answer['findings'][0]['reason'], reason, answer['findings'])
        self.assertLessEqual(len(answer['findings'][0]['detail']), 200)
        return answer['findings'][0]['detail']

    def mapped(self, answer, value):
        self.assertEqual(answer, {'value': value, 'findings': []})


class TheRealRows(Base):
    def test_each_row_has_its_pinned_bytes(self):
        self.assertEqual(sorted(ROWS), [121, 128, 275, 314, 315, 317, 319, 328, 330])
        for line, (digest, row) in ROWS.items():
            self.assertEqual(hashlib.sha256(row.encode('utf-8')).hexdigest(), digest, line)
            self.assertTrue(row.startswith('| '), line)

    def test_each_entity_alone_from_its_row(self):
        for line, path, version, digest in ENTITIES:
            answer = M.map_intent_versions({path: digest}, matrix(ROWS[line][1]))
            self.mapped(answer, {path: version})

    def test_all_entities_from_all_rows(self):
        entities = {path: digest for _, path, _, digest in ENTITIES}
        self.mapped(M.map_intent_versions(entities, REAL_DM), {path: version for _, path, version, _ in ENTITIES})

    def test_a_row_with_a_second_revision_in_another_form_is_not_counted(self):
        self.assertGreater(len(re.findall(r'revision [0-9]+', ROWS[330][1])), 1)
        line, path, version, digest = ENTITIES[-1]
        self.assertEqual(line, 330)
        self.mapped(M.map_intent_versions({path: digest}, matrix(ROWS[line][1])), {path: version})

    def test_no_row_names_the_two_other_files(self):
        for path, digest in NONE.items():
            self.refused(M.map_intent_versions({path: digest}, REAL_DM), 'no_row')


class TheForms(Base):
    def test_form_a_b_and_c(self):
        for row in ('| A1 | `%s` revision 3 (%s), and more |' % (P, H),
                    '| A2 | the file revision 3 (SHA-256 %s) in a commit |' % H,
                    '| F9 | Record of `%s` revision 3 (notes): SHA-256 %s, the file |' % (P, H)):
            self.mapped(run(row), {P: 'v3'})

    def test_the_accepted_cases_of_the_script(self):
        self.mapped(run('| F9 | Of spec 2, the `docs/` folder, `%s` revision 4 (n): SHA-256 %s |' % (P, H)), {P: 'v4'})
        self.mapped(run('| A1 | `%s` revision 3 (%s) |' % (P, H), '| F9 | Of `%s` revision 3: SHA-256 %s |' % (P, H)),
                    {P: 'v3'})
        self.mapped(run('| F9 | Record of `%s`, still revision 2 (n): SHA-256 %s |' % (P, H)), {P: 'v2'})

    def test_the_refused_cases_of_the_script(self):
        for row in ('| F9 | Of `docs/other.md` revision 4: SHA-256 %s |' % H,
                    '| F9 | Of `%s` revision 4: SHA-256 %s and SHA-256 %s |' % (P, H, H),
                    '| F9 | Of `%s` revision 4 and `%s` revision 5: SHA-256 %s |' % (P, P, H),
                    '| F9 | Record: SHA-256 %s, see `%s` revision 4 |' % (H, P),
                    '| A9 | the file %s was read |' % H,
                    '| A9 | Of `%s` revision 4: SHA-256 %s |' % (P, H)):
            self.refused(run(row), 'form')

    def test_a_naming_row_in_no_form_refuses_beside_a_good_row(self):
        detail = self.refused(run('| A1 | `%s` revision 3 (%s) |' % (P, H), '| A9 | the file %s was read |' % H), 'form')
        self.assertEqual(detail, 'row A9 at line 4 binds the SHA-256 in no form')

    def test_two_revisions(self):
        self.refused(run('| A1 | `%s` revision 3 (%s) |' % (P, H), '| A2 | x revision 4 (SHA-256 %s) |' % H), 'revisions')

    def test_no_row_and_a_line_that_is_not_a_row(self):
        self.refused(run('| A1 | `%s` revision 3 (%s) |' % (P, 'b' * 64)), 'no_row')
        self.refused(run('text `%s` revision 3 (%s)' % (P, H), ' | A1 | revision 3 (SHA-256 %s) |' % H), 'no_row')

    def test_the_path_is_matched_literally(self):
        self.refused(run('| A1 | `docs/xAmd` revision 3 (%s) |' % H), 'form')

    def test_the_revision_of_form_c_ends_at_a_word_boundary(self):
        self.refused(run('| F9 | Of `%s` revision 4x (n): SHA-256 %s |' % (P, H)), 'form')

    def test_a_form_c_row_id_with_a_non_ascii_digit_is_refused(self):
        self.refused(run('| F\u0669 | Of `%s` revision 4 (n): SHA-256 %s |' % (P, H)), 'form')

    def test_the_number_is_written_as_an_integer(self):
        self.mapped(run('| A2 | x revision 007 (SHA-256 %s) |' % H), {P: 'v7'})


class TheTighteningsAndTheOrder(Base):
    def test_a_non_ascii_digit_is_refused_where_the_script_would_take_it(self):
        row = '| A1 | `%s` revision \u0663 (%s) |' % (P, H)
        self.assertIsNotNone(re.search(r'revision (\d+) \(', row))
        self.refused(run(row), 'form')

    def test_a_key_out_of_form_is_refused(self):
        detail = self.refused(run('| A1 | x revision 3 (SHA-256 %s) |' % H, entities={'docs/../x.md': H}), 'entity')
        self.assertIn('position 1 ', detail)

    def test_a_value_with_a_trailing_line_feed_is_refused(self):
        self.refused(run('| A1 | x revision 3 (SHA-256 %s) |' % H, entities={P: H + '\n'}), 'entity')

    def test_other_values_out_of_form(self):
        for value in (H[:63], H + 'a', H.upper(), ''):
            self.refused(run(entities={P: value}), 'entity')

    def test_a_key_or_value_that_is_not_a_str(self):
        self.refused(run(entities={1: H, 'docs/x.md': H}), 'entity')
        self.refused(run(entities={P: 5}), 'entity')

    def test_a_key_with_a_leading_dot_is_taken_by_the_mapper(self):
        self.mapped(run('| A1 | x revision 3 (SHA-256 %s) |' % H, entities={'.github/x.md': H}), {'.github/x.md': 'v3'})

    def test_a_number_that_cannot_be_converted_is_refused_as_form(self):
        if not hasattr(sys, 'get_int_max_str_digits') or sys.get_int_max_str_digits() == 0:
            self.skipTest('this interpreter has no limit of digits for an integer text (Python %s)' % sys.version.split()[0])
        self.refused(run('| A1 | x revision %s (SHA-256 %s) |' % ('1' * 5000, H)), 'form')

    def test_all_entities_are_checked_before_any_row_is_read(self):
        self.refused(run(entities={'docs/a.md': H, 'docs/b.md': 'x'}), 'entity')

    def test_the_first_entity_in_sorted_order_that_fails_ends_the_call(self):
        other = 'b' * 64
        rows = ('| A9 | the file %s was read |' % other,)
        self.refused(run(*rows, entities={'docs/a.md': H, 'docs/b.md': other}), 'no_row')
        self.refused(run(*rows, entities={'docs/b.md': H, 'docs/a.md': other}), 'form')

    def test_the_order_of_form_and_revisions(self):
        rows = ('| A1 | x revision 3 (SHA-256 %s) |' % H, '| A2 | x revision 4 (SHA-256 %s) |' % H,
                '| A9 | the file %s was read |' % H)
        self.refused(run(*rows), 'form')


class TheArgumentsAndTheAnswer(Base):
    def test_the_bound_of_entities(self):
        entities = {'docs/e%03d.md' % n: '%064x' % n for n in range(100)}
        dm = matrix(*('| A%d | x revision 1 (SHA-256 %s) |' % (n, v) for n, v in enumerate(entities.values())))
        answer = M.map_intent_versions(entities, dm)
        self.assertEqual(len(answer['value']), 100)
        entities['docs/e100.md'] = '%064x' % 100
        self.refused(M.map_intent_versions(entities, dm), 'argument')

    def test_the_arguments(self):
        for entities in (None, [], {}, ((P, H),)):
            self.refused(M.map_intent_versions(entities, matrix()), 'argument')
        for dm in (None, b'', 5):
            self.refused(M.map_intent_versions({P: H}, dm), 'argument')

    def test_the_detail_is_cut(self):
        path = 'docs/' + 'x' * 400
        detail = self.refused(run(entities={path: H}), 'no_row')
        self.assertEqual(len(detail), 200)

    def test_an_unexpected_error_is_refused_with_its_type_and_not_raised(self):
        with mock.patch.object(M, '_version', side_effect=LookupError('a text')):
            self.assertEqual(self.refused(run(), 'argument'), 'an unexpected error: LookupError')

    def test_no_argument_is_changed_and_the_value_is_fresh(self):
        entities = {P: H}
        before = copy.deepcopy(entities)
        dm = matrix('| A2 | x revision 3 (SHA-256 %s) |' % H)
        a, b = M.map_intent_versions(entities, dm), M.map_intent_versions(entities, dm)
        self.assertEqual(entities, before)
        self.assertEqual(a, b)
        self.assertIsNot(a['value'], b['value'])
        self.assertIsNot(a['value'], entities)

    def test_the_reasons_are_the_closed_set(self):
        seen = {run().get('findings')[0]['reason'], run(entities={}).get('findings')[0]['reason'],
                run(entities={P: 'x'}).get('findings')[0]['reason'],
                run('| A9 | %s |' % H).get('findings')[0]['reason'],
                run('| A1 | x revision 1 (SHA-256 %s) |' % H,
                    '| A2 | x revision 2 (SHA-256 %s) |' % H).get('findings')[0]['reason']}
        self.assertEqual(seen, {'argument', 'entity', 'no_row', 'form', 'revisions'})


class TheModule(unittest.TestCase):
    def tree(self):
        return ast.parse(SRC.read_bytes().decode('utf-8'))

    def test_the_imports_are_a_subset(self):
        names = set()
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(node.module, 'aieos_bootstrap')
                names.update(a.name for a in node.names)
        self.assertLessEqual(names, {'re', 'base_files'})

    def test_the_only_public_function_of_the_module(self):
        public = sorted(n for n in dir(M) if not n.startswith('_') and callable(getattr(M, n))
                        and getattr(getattr(M, n), '__module__', '') == M.__name__)
        self.assertEqual(public, ['map_intent_versions'])

    def test_no_name_of_a_process_a_file_or_a_dynamic_call(self):
        banned = {'open', 'eval', 'exec', 'compile', 'input', 'breakpoint', '__builtins__', '__import__'}
        modules = {'tempfile', 'shutil', 'subprocess', 'importlib', 'pickle', 'code', 'builtins', 'os', 'sys', 'time',
                   'datetime', 'socket', 'pathlib'}
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.Name):
                self.assertNotIn(node.id, banned)
                self.assertNotIn(node.id, modules)
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, ('open', 'connect', 'write', 'write_text', 'write_bytes', 'unlink', 'mkdir'))

    def test_no_string_holds_a_dot_before_the_name_of_the_project(self):
        needle = '.' + 'aieos'
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertNotIn(needle, node.value.lower())

    def test_no_string_names_a_measure_folder_or_a_fixture_set(self):
        text = SRC.read_bytes().decode('utf-8')
        for word in ('native' + '/', 'bench' + '/', 'fixtures' + '_rc'):
            self.assertNotIn(word, text)

    def test_the_words_of_the_rules_on_words_are_not_in_the_module(self):
        text = SRC.read_bytes().decode('utf-8')
        for word in ('MEAS' + 'URED', 'ENFOR' + 'CED', 'GUARAN' + 'TEED', 'va' + 'lid', 'acc' + 'epted', 'appr' + 'oved'):
            self.assertNotIn(word, text)


if __name__ == '__main__':
    unittest.main()
