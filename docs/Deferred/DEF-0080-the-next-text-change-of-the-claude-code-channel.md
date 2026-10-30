# DEF-0080: the next text change of the Claude Code adapter's channel module

- Status: open
- Opened: 2026-10-18 (session dc541296; decision D-1276 C2)
- Deferred by: decision agent (A41), D-1276, after the way-2 reviews of TASK-063 at its final head.
- Decision group: A (a text and test change of src/aieos_bootstrap/claude_code_channel.py and its tests, in a task of its own).

## What
TASK-063's module (src/aieos_bootstrap/claude_code_channel.py) was accepted with these points carried, each non-blocking:
- The docstring and the contract header say that specification 2 revision 6 "keeps no session key on a record"; section 6.2 has a `session` key for an agent session's own statements, and an observation has none. Narrow the sentence.
- AC5's sentence "no text of hook_result's findings or of the original refers_to is copied into the result" (the decision agent's E3 wording of D-1263) is read as text that redaction removes; a root-relative path kept by AC4 is part of the redacted record. State that reading in the docstring.
- _hook_result_ok checks only the key set, the verdict, the exit code and the record-and-verdict link (not stderr, concern, reason or findings, nor the record's evidence_type against the concern); now, append and release surface only as a "core" refusal. State it.
- Mapping or string subclasses that override their methods are outside the trusted-caller model; state it.
- Untested points: the order of the event_id check before the verdict branches; the property tests do not assert that refusals occur; no single-branch broken copies for the backslash, leading-slash and empty-text checks of the path test.

## Resume when
- With the next change of that module (for example the task that starts the hook process, part CC-3's neighbour), or the owner's word.

## Log
- 2026-10-18: opened (session dc541296; D-1276).
- 2026-10-30: TASK-102 (accepted by decision D-3707 at f25b4576; range fb90baaf..f25b4576; records d3a328bd; the map is docs/records/TASK-102.jsonl :44): settled the session sentence, the AC5 reading, the hook_result statement and the subclass note (src/aieos_bootstrap/claude_code_channel.py:18-20, :51-55, :61-62, :87-88) and, though not in the map, two untested points (tests/unit/test_claude_code_channel.py:201; tests/property/test_claude_code_channel_properties.py:98); open the single-branch broken copies for the backslash, leading-slash and empty-text checks of the path test (a comment only, claude_code_channel.py:204) and the contract-header point (under docs/, outside the write set). Status stays open.
