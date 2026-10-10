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

## Why it happens
The working language of the requests and documents is English, and short lines written between tool calls are not checked the way a turn-final reply is.

## Prevention and detection
- Before every line meant for the owner, including one-line progress notes, write it in Vietnamese first; never translate afterwards.
- Before each turn-final reply, check its text for English words; English belongs only in quoted file names, commands the owner may run, and proper names.
- Requests to the decision agent and repository documents stay in English (A7).
