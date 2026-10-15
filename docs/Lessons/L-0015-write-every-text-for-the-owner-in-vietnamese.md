# L-0015: Write every text the owner sees in plain Vietnamese

Rule: Write every text the owner sees in plain Vietnamese without technical words, progress lines and status included, and check it before each turn-final reply; requests to the decision agent and repository documents stay in English.

- Status: active
- Category: communication
- Binding: record only. Related: item 1 of the owner's session prompt ("Trả lời tôi bằng tiếng Việt, không dùng từ kỹ thuật."); decision D-137 C7; L-0013 (questions to the owner in plain words).

## Pattern
Claude's requests to the decision agent, its plans and the repository documents are in English. Claude carried that language into the text the owner reads: short progress lines between tool calls, and a status section.

## Occurrences
Five in session 2026-10-08-1219 (../History/2026-10/2026-10-08-1219-master-plan-ratified.md):
- **2026-10-08 (:429, :495, :500).** Three progress lines in English.
- **2026-10-08 (:715).** The status part of a turn-final reply in English; the decision agent's relay above it was in Vietnamese. The owner asked (:719): "prompt đã ghi rất rõ trả lời tôi bằng tiếng Việt, tại sao lại trả lời bằng tiếng Anh". Claude answered at :732; the request to the decision agent first named only :715.
- **2026-10-08 (:961).** One more English progress line, after D-137 had set the rule (a narration-kind record).

One more in that session, found later by the decision agent (decision D-142); that session's History and this lesson first named five:
- **2026-10-08 (:1384).** A progress line in English ("Now I'm updating the check program…"), after D-137 had set the rule.

One possible occurrence in session 2026-10-08-1512 (decision D-143; that session's History, written at its end, carries the line on :1384 and this one):
- **2026-10-08 (:274).** Possible: the worker reports an English lead sentence; the transcript record :274 holds only the Vietnamese text; whether the owner saw it is not known.

One in session 2026-10-08-1702 (../History/2026-10/2026-10-08-1702-spec-1-approved-spec-2-drafted.md, section "Later in the session"), found by the decision agent (decision D-151):
- **2026-10-08 (:969).** A progress line began with the English word "I" ("I chỉnh câu lệnh đề xuất cho đúng khuôn lần trước, rồi kiểm và gửi."), a typo for "Tôi"; Claude did not disclose it.

One in session 2026-10-08-1825 (../History/2026-10/2026-10-08-1825-m1-done-spec-2-and-risk-rules.md), disclosed by Claude in the D-157 request:
- **2026-10-08 (:801).** A progress line was written in English ("Now the three exact changes E1 to E3, word for word as the agent set them.").

One group in session 2026-10-09-0153 (../History/2026-10/2026-10-09-0153-task-001-landed.md), found by Claude and disclosed in the D-188 request:
- **2026-10-09 (:705, :948, :1009, :1024).** Four short progress lines in English ("Now the local test runner." and three like it).

One group in session 2026-10-09-0856 (../History/2026-10/2026-10-09-0856-runner-contract-and-drafts.md), found by Claude and disclosed in the D-208 request:
- **2026-10-09 (:194, :336).** Two progress lines shown to the owner in English ("Now the results of the D-203 condition steps." and a line on the guard's refusal).

Three lines, found by Claude and disclosed to the decision agent (D-211, D-213):
- **2026-10-09 (a266 :722).** A progress line in English in session 2026-10-09-0856, which that session's History left out (a correction, ../History/2026-10/2026-10-09-1056-runner-accepted-and-landed.md).
- **2026-10-09 (:433, :960).** Two progress lines in English in session 2026-10-09-1056, each a short line before an Edit; the second after a decision's reminder to read every line before sending it.

Three in session 2026-10-09-1248 (../History/2026-10/2026-10-09-1248-ci-revision-3-and-governor-contract.md):
- **2026-10-09 (:691, :881, :943).** Three short progress lines in English, each written just before an Edit in the scratchpad.

Three lines of session 2026-10-09-1248, found in session 2026-10-09-1801 (../History/2026-10/2026-10-09-1801-governor-drafts-and-runner-test-isolation.md) and left out of that session's History:
- **2026-10-09 (cb45 :1123, :1505, :1685).** Three short progress lines in English, each written just before an Edit or a script in the scratchpad ("Now C1, …", "Now E2 …", "Now the executor's …").

Five in session 2026-10-09-2339 (../History/2026-10/2026-10-09-2339-spec-3-approved-and-on-main.md), found by Claude and disclosed in the D-243 and D-244 requests:
- **2026-10-09 (:351).** A progress line in English ("Now I fix the builder so the "OK" lines are cited …").
- **2026-10-09 (before :477).** A progress line in English about the guard refusal, reported by Claude; the transcript holds it as no text record.
- **2026-10-10 (:718, :833, :913).** Three short progress lines in English before Edit calls ("Now I apply the corrections to the draft." and two like it). From then on the English-line scan ran by machine before every reply and request (D-244 C5).

Four in session 2026-10-10-0043 (../History/2026-10/2026-10-10-0043-bootstrap-scope-and-m3-documents.md), found by the machine scan and disclosed in the D-250 and D-255 requests:
- **2026-10-10 (:147, :252, :301).** Three short progress lines in English before tool calls ("Now I'll do the same for this session: …" and two like it).
- **2026-10-10 (:890).** One more, "Now the edits in the builder.", after the scan had run before each reply; the scan caught it before the next request.

Eight in session 2026-10-10-0138 (../History/2026-10/2026-10-10-0138-conformance-files-r4-and-task-005-contract.md), found by the machine scan and disclosed in the next request each time:
- **2026-10-10 (:88, :167, :366, :631, :653, :1040, :1438, :1523).** Short progress lines in English before tool calls ("Now the archive of session 8f790446." and seven like it); the scan ran before each request, not before each progress line.

Four in session 2026-10-10-0235 (../History/2026-10/2026-10-10-0235-resume-check-fixtures-accepted.md), found by the machine scan and disclosed in the next request each time:
- **2026-10-10 (:191, :582, :690, :1340).** Short progress lines in English before tool calls.

Five in session 2026-10-10-0348 (../History/2026-10/2026-10-10-0348-runner-entry-contract-and-reader-test-split.md), found by the machine scan and disclosed in the next request each time:
- **2026-10-10 (:403, :620, :870, :889, :1341).** Short progress lines in English before tool calls; the last three came after the decision agent asked for a scan before each line (D-284 C3).

Occurrences in session 2026-10-10-0451 (../History/2026-10/2026-10-10-0451-decision-files-d284-d292-and-task-010-landed.md):
- **2026-10-10 (:551).** One short progress line in English before a tool call in this session.
- **2026-10-10 (session 3d249e7e, found now by machine).** That session had seven English lines (:403, :620, :870, :889, :1230, :1341, :1630), not five; :1230 had been missed and the reply at :1407 had said five.

Occurrences in session 2026-10-10-0626 (../History/2026-10/2026-10-10-0626-decision-files-d293-d302-and-task-006-landed.md):
- **2026-10-10 (:1020, :1382, :1729).** Three short progress lines in English before a tool call, each beginning "Now"; all found by `tools/english_lines.py` and brought to the decision agent.

One occurrence in session 2026-10-10-0735 (../History/2026-10/2026-10-10-0735-decision-files-d303-d310-ci-revision-5-and-task-007-contract.md):
- **2026-10-10 (:1461).** A short progress line in English before a tool call ("Now I'll fill the placeholders …"); found by `tools/english_lines.py` at the session-end check and brought to the decision agent.

Three occurrences in session 2026-10-10-1612 (../History/2026-10/2026-10-10-1612-decision-files-d311-d318-the-widening-in-force-and-task-007-landed.md):
- **2026-10-10 (:855, :872, :1284).** Short progress lines in English before tool calls ("Now the unit tests.", "Now replace the NaN test …", "Now the common brief and the five briefs."); found by `tools/english_lines.py` and brought to the decision agent.

Four occurrences in session 2026-10-10-1810 (../History/2026-10/2026-10-10-1810-decision-files-d319-d330-contracts-of-task-011-008-012.md):
- **2026-10-10 (:145, :771, :1009, :1775).** Short progress lines in English before tool calls ("Now run defcheck, …", "I'll apply the edits …", "Applying the five edits.", "Now the commit message …"), in long runs of tool calls while drafting English texts; found by `tools/english_lines.py` and brought to the decision agent (D-331, D-335, D-341). Remedy: no text before a tool call unless it is a deliberate Vietnamese line.

Nine occurrences found in session 2026-10-10-1946 (../History/2026-10/2026-10-10-1946-decision-files-d331-d344-task-011-landed.md):
- **2026-10-10 (:494, :518, :567, :627, :958, :1146, :1269).** Short English lines before tool calls ("Now read the contract …", "Meanwhile, the TASK-011 script checks …", "Now the C2 comparison by script."), the last three after the decision agent's remedies (D-348 C5, D-350 C4); found by `tools/english_lines.py`.
- **2026-10-10 (session 675f09ef :2267, :2449).** Two English lines of the previous session that came after its History was built.

English text lines of mine, in sessions 2026-10-10-1946 and 2026-10-10-2044:
- **2026-10-10 (2c78 :1561, :1692).** Two English lines of session 2c78123d found after its History was built (decisions D-353 C7 and D-357).
- **2026-10-10 (:921).** "Now the five briefs." before a tool call; found by english_lines.py and reported in the next request.

English text lines of mine, in session 2026-10-10-2141 (../History/2026-10/2026-10-10-2141-decision-files-d356-d366-task-013-landed.md):
- **2026-10-10 (:907).** "Fix the insertion point to handle a module without top-level functions." before a tool call; found by english_lines.py and reported in the next request.
- **2026-10-10 (:1502, :1687).** "Write the TASK-013 records builder, its basis file and the draft acceptance text." and "Now the change-set builder for the session-end records." before tool calls; found by english_lines.py before the session-end request.

English text lines of mine, in session 2026-10-10-2252 (../History/2026-10/2026-10-10-2252-decision-files-d367-d376-task-014-landed.md):
- **2026-10-10 and 2026-10-11 (:730, :794, :1132, :1840, :1882).** "Now the two briefs.", "Now the revised bullet, as a second build of revision 5.", "Now the TASK-014 contract check, in the same shape.", "Now the change-set builder." and "Now the commit message and the dry run." before tool calls; found by english_lines.py before the next request. Remedy (D-383 C5): no text block before a tool call except a Vietnamese line checked before sending; the last two slipped after it was accepted.

Five in session 2026-10-11-0013 (../History/2026-10/2026-10-11-0013-decision-files-d377-d387-recovery-and-the-pin.md), found by Claude with english_lines.py and disclosed in the next request:
- **2026-10-11 (:432, :456).** Two short English lines before tool calls ("Now the writer …", "Now the gated command file, then the request.").
- **2026-10-11 (:803, :818, :909).** Three more after the remedy stated at D-389 (check before each request and each reply); the remedy failed twice (D-391 C5). The rule since: check the steps listing before every tool-call batch that carries text, not only before requests.

Two in session 2026-10-11-0121 (../History/2026-10/2026-10-11-0121-decision-files-d388-d398-and-task-015.md), found by Claude with english_lines.py and disclosed in the next request:
- **2026-10-11 (:386, :876).** "Now the writer and its gated command file." and "Now the code change in the clone." before tool calls; the second after the remedy stated at D-400 C4 (a Vietnamese line only before a tool-call batch that carries text). Remedy since (D-404 C4): write the Vietnamese line first and nothing else in that text block.

Four in session 2026-10-11-0333 (../History/2026-10/2026-10-11-0333-decision-files-d409-d420-and-specification-4.md), found by Claude with english_lines.py and disclosed in the next request:
- **2026-10-11 (:607, :833).** Two one-line English text blocks before tool calls, the second after the remedy stated in D-423. The rule since (D-424 C4): no text block before a tool call except a planned progress line, and the steps listing checked for text lines after each turn.
- **2026-10-11 (:1438, :1479).** Two more one-line English text blocks before tool calls, after D-424 C4's rule, while the session-end files were built; found by the check before the session-end request.

Occurrences in session 2026-10-11-0333, recorded in the next session (decision D-435 C3):
- **2026-10-11 (:1795, :1812).** Two more one-line English text blocks before tool calls while files were being built, after D-431 C5.

Occurrences in session 2026-10-11-0538 (../History/2026-10/2026-10-11-0538-conformance-files-revision-7-and-task-017-contract.md):
- **2026-10-11 (:1059, :1202, :1258).** Three one-line English text blocks before tool calls while files were being built, each right after the harness asked for a word on what Claude was doing; the last two after the remedy stated for the first. Remedy accepted in decision D-445: a harness prompt is answered only by a Vietnamese line checked by english_lines.py, or not at all while files are being built.
- **2026-10-11 (the session's start).** Three Vietnamese text blocks written before tool calls, the start report among them, have no record in the transcript; the start report went into a turn-final reply instead (decision D-437).

Occurrences in session 2026-10-11-1318 (../History/2026-10/2026-10-11-1318-runner-entry-accepted-and-fixture-contract-drafted.md):
- **2026-10-11 (:380, :606, :1476, :1548, :1613).** Five one-line English text blocks before tool calls; the rule of D-454 (no text block in a message that holds a tool call, except a Vietnamese line answering a harness prompt) did not hold four times after it was set, and the stricter rule of D-462 (no text block at all in a message that holds a tool call) did not hold at :1613.

Occurrences in session 2026-10-11-1439 (../History/2026-10/2026-10-11-1439-fixture-contract-on-main-and-fixture-reviewed.md):
- **2026-10-11 (:510, :954, :1708).** Three one-line English text blocks before tool calls, after the remedies of D-454 and D-462.
- **2026-10-11 (:402 to :593, :1409, :1460).** Harness-asked Vietnamese lines sent without the check in their own call first, after D-466 accepted that remedy; at :1460 the check ran after sending. All were Vietnamese; the remedy failed three times (D-467, D-472).
- **2026-10-11 (the start report; the owner line after :778).** Two lines sent as text before tool calls have no record in the transcript; both are repeated in the session-end reply.

Occurrences in session 2026-10-11-1540 (../History/2026-10/2026-10-11-1540-fixture-accepted-and-runner-tests-pushed.md):
- **2026-10-11 (:110, :245, :383, :898, :1159, :1540, :1684).** Seven one-line English text blocks before tool calls; all but the first after D-475 C5's remedy (no text block in a message that holds a tool call, except a harness-asked Vietnamese line already checked). The remedy was a promise and failed six times; the decision agent asked for a mechanical one (D-485 C4).
- **2026-10-11 (:90).** The first harness-asked line was sent before it was checked (D-465 C1 broken); every later Vietnamese line was checked first in its own call.
- **2026-10-11 (the start report and later lines).** Several checked Vietnamese lines were displayed but not stored as text records, so the steps listing misses them (D-477); they are repeated in the session-end reply.
- **Correction (D-473 C4):** the occurrence of session 2026-10-11-1439 that says the remedy "failed three times (D-467, D-472)" should read "D-466, D-467, D-472".
- Remedy proposed (mechanical, D-485 C4): at every pre_request run, english_lines.py's output over the whole steps listing is compared with the list of English lines already reported; any new one is a stop: it goes to the decision agent before any other step. Whether a hook should block an English text block is an owner matter (hooks are the owner's, A51 item (4)).

Occurrences in session 2026-10-11-1800 (../History/2026-10/2026-10-11-1800-runner-tests-accepted-and-set-freeze-for-task-020.md):
- **2026-10-11 (:204, :425, :615, :1245, :1635).** Five one-line English text blocks before tool calls. The mechanical stop of decision D-485 C4 (the steps listing's English lines at every pre_request run) caught each at the next request, and each went to the decision agent (decisions D-489, D-490, D-494, D-498); three came after decision D-489 C5 made "no text block in a message that holds a tool call, except a pre-checked Vietnamese line" binding. The check finds them but does not prevent them; by decision D-490 C5 the owner is asked whether to install a machine block (a hook is the owner's, A51 item (4)).

Occurrences in session 2026-10-11-1912 (../History/2026-10/2026-10-11-1912-set-entry-accepted-and-on-main-for-task-020.md):
- **2026-10-11 (:594, :810, :1047).** Three one-line English working notes as text blocks in messages holding tool calls, none a relay to the owner; each caught at the next pre_request run and brought to the decision agent (decisions D-502, D-504, D-505), which then forbade any text block in a message with a tool call (D-502 C1) and put owner lines only in messages with no tool call (D-504). Two Vietnamese progress lines were also sent unchecked at the start (:243, :332; decision D-501). The owner's answer on a machine block is still open.

Occurrences in session 2026-10-11-2017 (../History/2026-10/2026-10-11-2017-ac-coverage-check-accepted-and-on-main.md):
- **2026-10-11 (:999, :1171, :1379, :1432, :1467, :1484).** Six one-line English working notes as text blocks in messages holding tool calls, none an owner line; each caught at the next pre_request run and brought to the decision agent (decisions D-519, D-520, D-522, D-523); the third came after decision D-520 C5 required a check of each such message before sending it, and the last three after decision D-522 C4 said such a message holds tool calls only. The owner had answered "không" to a machine block (DM A68), so detection stays after the fact. Remedy (D-522 C4): every message with a tool call holds tool calls only, except a pre-checked owner line allowed by decision D-517 C3.

Occurrences in session 2026-10-11-2112 (../History/2026-10/2026-10-11-2112-test-to-ac-listing-accepted-and-on-main.md):
- **2026-10-11 (:560, :668, :847, :1265, :1420, :1486, :1823).** Seven one-line English working notes as text blocks in messages holding tool calls, none an owner line; each caught at the next pre_request run and brought to the decision agent (decisions D-528, D-529, D-531, D-535, D-536, D-537, D-539). Five (:847, :1265, :1420, :1486, :1823) followed the harness's prompt to say what I was doing (:840, :1262, :1403, :1483, :1730). The rule stands: no text at all before a tool call, whatever the prompt; an owner line goes only as a checked turn-final reply (decision D-527).

Occurrences in session 2026-10-11-2233 (../History/2026-10/2026-10-11-2233-stale-evidence-computation-accepted-and-on-main.md):
- **2026-10-11 (:788, :908, :1117, :1843, :1990).** Five one-line English working notes as text blocks in messages holding tool calls, and one Vietnamese progress line in the same position (:1178), none an owner line; each listed in the next request (decisions D-547, D-548, D-550, D-551, D-554, D-555). Most followed the harness's prompt to say what I was doing. The rule stands: no text at all in a message with a tool call; an owner line goes only as a checked turn-final reply (decisions D-527, D-545 Q4).

Occurrences in session 2026-10-11-2336 (../History/2026-10/2026-10-11-2336-spec-2-revision-3-and-the-git-reader-contract.md):
- **2026-10-12 (:70, :118, :312, :1049, :1526, :1648, :1784).** Seven text blocks: two Vietnamese progress lines sent when the harness asked for a status, four one-line English working notes, and a Vietnamese progress line before the session-end request, each in a message holding a tool call; none an owner relay; each caught at the next pre_request run and listed in the next request (decisions D-557, D-558, D-565, D-571, D-572).

Occurrences in session 2026-10-12-0048 (../History/2026-10/2026-10-12-0048-the-git-reader-accepted-and-on-main.md):
- **2026-10-12 (:167, :644, :813, :898, :917, :1212, :1285, :1370, :1482, :1632, :1751, :1827, :1844).** Thirteen one-line English working notes as text blocks in messages holding tool calls, none an owner line, most after the harness's prompt to say what I was doing; aid (a), a check run first in every gated command, kept every mutation from running until each was listed in a request to the decision agent (decisions D-575 to D-586). Two turn-final replies were sent without a checked draft (:679, :758) and one not byte-equal to its checked draft (:861; decisions D-577, D-579).

Occurrences in session 2026-10-12-0215 (../History/2026-10/2026-10-12-0215-the-submission-path-accepted-and-on-main.md):
- **2026-10-12 (:253, :654, :922, :1109, :1246, :1276, :1718, :1862).** Eight one-line English working notes as text blocks in messages holding tool calls, none an owner line, most after the harness's prompt to say what I was doing; aid (a) stopped the next gated run until each was listed in a request to the decision agent (decisions D-589 to D-602). Of the three turn-final questions after classifier stops, one was sent without a checked draft (:671; decision D-592) and one reworded from its checked draft (:1882).

Occurrences in session 2026-10-12-0333 (../History/2026-10/2026-10-12-0333-release-by-token-accepted-and-the-recovery-contract.md):
- **2026-10-12 (:255, :574, :1457, :1494, :1739, :1923).** Text blocks in messages holding tool calls (English working notes, and once a Vietnamese status line), all while working between requests to the decision agent; aid (a) stopped the next gated run until each was listed (decisions D-604, D-608, D-614, D-617 and D-619). Four turn-final replies carried only a status line while I waited for background work (:1070, :1118, :1138, :1152); the decision agent ruled the practice (decision D-611 C5).

Occurrences in session 2026-10-12-0833 (../History/2026-10/2026-10-12-0833-recovery-at-start-accepted-and-on-main.md):
- **2026-10-12 (:1285, :1301, :1821).** English working notes in messages holding tool calls, while preparing the second review round, against the owner's item 5 of this session's prompt ("trong một lượt có chạy lệnh thì không viết chữ nào khác", 2026-10-12, :3); aid (a) stopped the next gated command until both were listed (decision D-625), and from then on any further one stops it until brought to the decision agent (D-625 C2); one more followed at :1821, while preparing the session's end, and was brought to the decision agent (decision D-629).

Occurrences in session 2026-10-12-0944 (../History/2026-10/2026-10-12-0944-the-evaluation-path-accepted-and-on-main.md):
- **2026-10-12 (:196, :545, :668, :758, :1168, :1400, :1508, :1673).** Eight short English working notes in messages holding tool calls, each right after a harness note asking what was being done, against the owner's item 5 of this session's prompt and decision D-625 C2, then D-632 C4 and D-636's rule (a); each brought to the decision agent and listed before the next gated command, and from D-636 on the owner told the running count in each turn-final reply (decisions D-632 to D-640).

Occurrences in session 2026-10-12-1122 (../History/2026-10/2026-10-12-1122-the-audit-copies-accepted-and-on-main.md):
- **2026-10-12 (:170, :182, :274, :1062, :1229, :1437, :1595, :1615).** Eight short English working notes in messages holding tool calls, each right after a harness note asking what was being done, :1595 written while waiting for a reviewer, against the owner's item 5 of this session's prompt ("kể cả khi đang chờ hay khi được nhắc báo đang làm gì") and decision D-632 C4's carried rule; each brought to the decision agent and listed before the next gated command, the owner told the running count; decision D-656 C4's check before every tool call did not hold for the last two (decisions D-644 to D-657).
- **2026-10-12 (before :1230).** Turn-final progress replies sent without a draft_check2 run (decisions D-575 and D-577); all were in Vietnamese; from decision D-655 C3 on, every turn-final reply was checked and confirmed by line_sent.

Occurrences in session 2026-10-12-1245 (../History/2026-10/2026-10-12-1245-constitution-drift-accepted-and-the-reconciliation-contract.md):
- **2026-10-12 (:375, :651, :898, :962, :1357).** Five short English working notes in messages holding tool calls, none after a harness note, each announcing the next file to write, against the owner's item 5 of this session's prompt and decision D-666 C1's rule; each caught by the textblock check before the next gated command, brought to the decision agent and listed, the owner told the count (decisions D-662, D-664, D-666 and D-668).

Occurrences in session 2026-10-14-2219 (../History/2026-10/2026-10-14-2219-the-reconciliation-caller-accepted-and-on-main.md):
- **2026-10-14 (:792, :1081, :1150).** Three short English working notes in messages holding tool calls, the first two right after a harness note, each announcing the next file or step, against the owner's item 5 of this session's prompt; each caught by the textblock check before the next gated command, brought to the decision agent and listed, the owner told (decisions D-678 and D-680).

Occurrences in session 2026-10-14-2320 (../History/2026-10/2026-10-14-2320-the-execution-path-accepted-and-on-main.md):
- **2026-10-14 to 2026-10-15 (:529, :689, :1229, :1497, :1800).** Five English text blocks before tool calls ("Now update the writer WANT values and rebuild the command.", "Now the pause-reply draft.", "Now the readings file.", "Applying the test-side fixes.", "Writing the session-end work builder now."), none right after a harness note; each caught by the textblock check before the next gated command, brought to the decision agent, listed, and told to the owner.

Occurrences in session 2026-10-15-0028 (../History/2026-10/2026-10-15-0028-the-policy-list-and-scope-drift-accepted-and-on-main.md):
- **2026-10-15.** Nine English text blocks before tool calls, by the textblock check: :347, :517, :623, :1379, :1431, :1529, :1605, :1875 and :2079, each a short line announcing the next step. The decision agent's instruction after the third (D-698 C3: re-read this lesson before each turn that calls tools and write no text) did not hold. Each was listed before the next gated command and brought to the decision agent, and the owner was told. (The decision agent's running count reached "eleven" at D-708; the check lists nine.)

Occurrences in session 2026-10-15-0229 (../History/2026-10/2026-10-15-0229-the-scope-drift-caller-accepted-and-on-main.md):
- **2026-10-15.** Eight English text blocks before tool calls, by the textblock check: :169, :222, :765, :965, :1060, :1167, :1369 and :1736, each a short line announcing the next step; each listed before the next gated command and brought to the decision agent, and the owner was told.

Occurrences in session 2026-10-15-0422 (../History/2026-10/2026-10-15-0422-the-scope-drift-callers-hardening-accepted-and-on-main.md):
- **2026-10-15.** Seven English text blocks before tool calls, by the textblock check: :184, :293, :382, :780, :947, :1587 and :1675, each a short line announcing the next step; each listed before the next gated command and brought to the decision agent, and the owner was told.

Occurrences in session 2026-10-15-0531 (../History/2026-10/2026-10-15-0531-the-autonomy-levels-feature-accepted-and-on-main.md):
- **2026-10-15.** Nine English text blocks before tool calls, by the textblock check: :162, :309, :560, :573, :797, :994, :1454, :1561 and :1653, each a short line announcing the next step; each listed before the next gated command and brought to the decision agent, and the owner was told.

Occurrences in session 2026-10-15-0659 (../History/2026-10/2026-10-15-0659-m4-exited-specification-5-and-the-benchmark-workflow-contract.md):
- **2026-10-15.** Four English text blocks before tool calls, by the textblock check: :579, :942, :1027 and :1692, each a short line announcing the next step; each listed before the next gated command and brought to the decision agent, and the owner was told.

Occurrences in session 2026-10-15-0830 (../History/2026-10/2026-10-15-0830-the-benchmark-workflow-accepted-and-on-main.md):
- **2026-10-15.** Eight English text blocks before tool calls, by the textblock check: :345, :526, :963, :1280, :1301, :1445, :2051 and :2163, each a short line announcing the next step; each listed before the next gated command and brought to the decision agent, and the owner was told.

Occurrences in session 2026-10-15-1007 (../History/2026-10/2026-10-15-1007-policy-v4-route-and-task-040-contracted.md):
- **2026-10-15.** Nine English text blocks before tool calls: :458, :942, :1029, :1180, :1526, :1799, :1855, :1986 and :2091, each a short line announcing the next step; the first stopped a gated run; from the call after :1799 a scratch check (tools/tbq.sh) runs first in every Bash command and caught the last four at once (D-804 C3); each listed before the next gated command and brought to the decision agent, and the owner was told.

## Why it happens
The working language of the requests and documents is English, and short lines written between tool calls are not checked the way a turn-final reply is.

## Prevention and detection
- Before every line meant for the owner, including one-line progress notes, write it in Vietnamese first; never translate afterwards.
- Before each turn-final reply, check its text for English words; English belongs only in quoted file names, commands the owner may run, and proper names.
- Requests to the decision agent and repository documents stay in English (A7).
