# L-0025: Keep the session clear of reasoning-extraction refusals

Rule: Never read or print raw session transcripts (use only counts, file lists, narrow matches or scripts that print metadata, never text or thinking); never ask any agent, in a request, a brief, a prompt or a tool input, to write out, restate, log or quote reasoning, thinking or private notes, or to fill a fixed reasoning section (ask for a short summary of the evidence instead); keep messages to agents short; and after a refusal, record its request id, redo nothing and bring it to whoever the delegation names.

- Status: active
- Category: tooling
- Binding: record only; the owner's words of 2026-10-19 (session aa923cac): "hãy rút ra bài học kinh nghiệm để đảm bảo không lặp lại và không bị chặn, ở cuối mỗi phiên hãy đưa vào cả prompt bắt đầu phiên sau để claude biết cách làm việc cho phiên sau". Related: decisions D-1503, D-1504 (C2); L-0024; DEF-0088.

## Pattern
The main session (claude-opus-5-5) was refused in the category reasoning_extraction seven times in three sessions (2026-10-12, 2026-10-17, 2026-10-19), each time while it was writing, or had just written, a message for another agent. No decision-agent or reviewer instance was refused in that category. The refusal names only the category; which words of the context it acted on cannot be seen from our side.

## Occurrences
- **2026-10-12 (session 556c5dd4, :315-316).** During the Write of a decision request.
- **2026-10-17 (session 2375f48d, :1746, :1772, :1777-1778).** After a guard refusal and an owner message; after two Greps of the session's own transcript in content mode; during the Writes of a decision request.
- **2026-10-19 (session aa923cac, :452, :926).** During the Write of the guard's listing note, after a guard refusal; and the request after the Write of the review entries (D-1503, D-1504).

## Why it happens
The official refusal documentation says that this category comes from a prompt that asks the model to put its thinking or reasoning in the output, verbatim or in a fixed format, and that such wording can sit anywhere in the context (a system prompt, a skill, a tool description). Our work brings much text of that shape into the main session's context: raw transcript lines (which can hold thinking records), many fixed-format messages to and from agents, and requests for texts "verbatim" and "in full". Which of these acted is not known; only Anthropic can tell, from the request ids.

## Prevention and detection
- Read transcripts only through counts, file lists, narrow -o matches or metadata scripts such as refusals.py; never Read a .jsonl file or print its lines with a shell command.
- In requests, briefs and prompts, ask for findings, evidence and a short summary; never for reasoning, thinking, a trace or notes written out, in full or in a fixed section.
- Keep each message to an agent as short as its required items allow; no text beside any tool call.
- After a refusal: record the request id and the line, redo and reword nothing, bring it to the decision agent (DM A70, A71), and tell the owner; the owner may send the ids to Anthropic support.
- Every next-session prompt requires reading this lesson exactly and in full, as for L-0014 and L-0024.
