# L-0014: Bring every step to the decision agent

Rule: Bring every step that needs a decision to the decision agent before taking it, with every item its definition requires, the definition check included; this covers ending a turn that the owner would have to resume, a change to an approved order, and any departure from a decision.

- Status: active
- Category: process
- Binding: the owner's words of 2026-10-07 (session df962768, transcript :910), recorded in the delegation section of the rules book.

## Pattern
Claude took a step that a decision should have covered without bringing it to the decision agent first, or sent a request that lacked an item the decision agent's definition requires. The owner then became the gate that the decision agent is meant to be.

## Occurrences
- **2026-10-07 (session 1dace763, transcript :1264, :1269).** The scratchpad was archived before the D-087 relay, although D-087 set "C1, then C2, then C4" and "archive, last". The change of order was not brought to the decision agent first (reviewed in D-088).
- **2026-10-07 (../History/2026-10/2026-10-07-1815-def-0020-assurance-model-and-constitution.md, transcript :488).** Claude ended a turn to show six decision files in full, so that the owner had to send a message for the work to go on (:496). The stop was Claude's choice and was not brought to the decision agent (D-089).
- **2026-10-07 (same session, request D-089).** The request did not state the definition file's SHA-256; the decision agent escalated and decided nothing else until it was resubmitted (D-089, first handback).
- **2026-10-08 (../History/2026-10/2026-10-08-1219-master-plan-ratified.md, transcript :1754, :1758, :1767).** After decision D-142 had said to end the session, the owner wrote "Kết thúc phiên tại đây." with questions (:1754). Claude did not bring the message to the decision agent first (D-135 C2, D-141 C7), ran a read-only check (:1758), and ended its reply with an owner question about continuing that it had not brought first (:1767). Nothing was written. Found and recorded under decision D-143, which treated the question as superseded; the History of session 2026-10-08-1512, written at its end, carries the line.

## Why it happens
- Claude treats a step as mechanical (a display, a change of order, a turn end) and does not see it as a decision.
- The request checklist of the decision agent's definition was not applied before sending.

## Prevention and detection
- Before ending a turn, changing an approved order or taking any step a decision does not name, ask: which decision covers this exact step? If none, bring it to the decision agent first.
- Before sending a request, check it against the nine items of the decision agent's definition, and put the definition check (machine output) at its top.
- Never end a turn only so that the owner decides whether the work goes on; that decision is the decision agent's (:910).
