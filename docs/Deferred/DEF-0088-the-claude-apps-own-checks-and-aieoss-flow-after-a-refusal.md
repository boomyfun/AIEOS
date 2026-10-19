# DEF-0088: the Claude app's own checks and AIEOS's flow after a refusal
- Status: open
- Opened: 2026-10-19 (session dc5d0da2; decision D-1457)
- Deferred by: decision agent (A41, A51), D-1457, on the owner's words of 2026-10-19 (quoted below).
- Decision group: A for this record and for the contract text when it is written; trying AIEOS inside Claude Code's automatic mode is a measurement, the owner's (A51 item (4)).
## What
- The owner's words (session dc5d0da2, main transcript :532): "nếu vậy chúng ta cần phải fix/vá để user không bị chặn, và user có thể nghĩ rằng AIEOS không an toàn để sử dụng". The owner then answered "đồng ý" (:540) to Claude's plan to record it as an item of its own.
- What happened in this self-build: the Claude app's automatic mode put its warning line on decision-agent reports that let work go on after a refusal by the project's command guard (D-1438, D-1450, D-1456), and in session dc5d0da2 it stopped two calls to the decision agent about the warning on D-1456's report (D-1457). The app gave only a short label; Claude's reading of the cause is a guess. The app's checks are outside AIEOS and cannot be changed by it.
- Points Claude proposed (session dc5d0da2, main transcript :536), not yet decided; inputs for the contracts of the Claude Code adapter (M5): (1) a stop by the Claude app's own checks is never followed by an agent's approval to go on; AIEOS stops and tells the user in plain words, and only the user decides; (2) AIEOS's own refusals and the app's stops are told apart in AIEOS's messages, and an AIEOS refusal names the corrected form, so a correction is an ordinary step; (3) before AIEOS says it works inside Claude Code's automatic mode, that is tried and recorded (a measurement, the owner's).
- Point (1) is about the product. In this self-build the owner gave such stops to the decision agent (DM A70, A71); this item does not change that.
## Resume when
- With the next contract of the Claude Code adapter (M5) that handles refusals or messages to the user, or the owner's word.
## Log
- 2026-10-19: opened (session dc5d0da2; D-1457).
- 2026-10-19: the app's notice fell again on a decision-agent report (D-1470) and the app stopped the call that brought it to the decision agent (session bc3137c8, :500); not resent; the owner answered "đồng ý" (:523) (D-1472).
- 2026-10-19: the app's notice fell on a decision-agent report again (D-1481's, which let work go on after a refusal by the project's call-form guard); no call about it was sent to the decision agent; the owner was asked and answered "có" (session b886c732, :332) (D-1482).
- 2026-10-19: two reasoning_extraction refusals of the main session (session aa923cac, :452, :926); none redone; an investigation by metadata only found seven such refusals in three sessions, all on the main session, the cause not visible from our side; the six request ids given to the owner for Anthropic support (D-1503, D-1504); lesson L-0025 (D-1505).
