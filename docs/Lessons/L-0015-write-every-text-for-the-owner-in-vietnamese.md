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

## Why it happens
The working language of the requests and documents is English, and short lines written between tool calls are not checked the way a turn-final reply is.

## Prevention and detection
- Before every line meant for the owner, including one-line progress notes, write it in Vietnamese first; never translate afterwards.
- Before each turn-final reply, check its text for English words; English belongs only in quoted file names, commands the owner may run, and proper names.
- Requests to the decision agent and repository documents stay in English (A7).
