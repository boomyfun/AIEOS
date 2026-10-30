# DEF-0096: the Context Compiler's reading of component paths, and two wording points carried from TASK-080

- Status: open
- Opened: 2026-10-24 (session 308d8b07; decisions D-2188, D-2192 and D-2199, and TASK-080's acceptance, D-2206)
- Deferred by: decision agent (A41, A51), D-2192 (O1 to a DEF item, no code change), D-2199 (S2-1 to the same item) and D-2206 (TASK-080's acceptance, N1).
- Decision group: A (a point for specification 6's next revision and the next change to context_compiler.py).

## What
1. O1: context_compiler._folder reads a component path with no wildcard only as the root-anchored "<it>/**", while resume_check._folder gives both the path itself and "<it>/**", and resume_check.meet reads a pattern without "/" as "**/" followed by it. So a slash-less component path (for example "Makefile") is met anywhere by the Resume Check but only at the root by the Context Compiler, and a component path that names a file is never met by that file in the Context Compiler. The code follows TASK-080's contract (its header: "a component path with no wildcard is read as "<it>/**"") and specification 3 :57; no test pins either reading for these two shapes, so a change to either module's reading drifts without a test failing (DA-4 R-3).
2. S2-1: _json_value's docstring in context_compiler.py says it appends a finding for each part of the value that is not JSON, which overstates the case after a depth finding or the node bound, after which nothing more is walked; the module's Limits sentence names both bounds but not the stop after a depth finding.
3. N1: review t80s-S2's GOV-003 line, quoted verbatim in record TASK-080-way2-t80s-S2-GOV-003, cites "the comment at context_compiler.py:21-22" for the comment that is at :59-60.

## Why deferred
D-2192 and D-2199: the code follows the contract's text, and the gap only narrows the Work Order; the reading of component paths is specification 6's to decide in its next revision (section 11), and a wording change alone does not justify another commit, run and review. N1 is a reviewer's citation, kept verbatim in the records.

## Resume when
Specification 6's next revision, or the next task that changes context_compiler.py or resume_check's pattern reading (S3b, with the launcher, M7).

## Depends on
TASK-080 (context_compiler.py at 9c41ab22); specification 3 :55-57; specification 6 sections 6 and 11; TASK-008 (resume_check.meet, matches and _folder).

## Log
- 2026-10-24: opened (session 308d8b07; TASK-080's acceptance, D-2206).
- 2026-10-29: specification 6 revision 8 (DM F74) does not take up this item; it stays open for a later revision of specification 6 or for the next task that changes context_compiler.py or resume_check's pattern reading.
- 2026-10-30: TASK-102 (accepted by decision D-3707 at f25b4576; range fb90baaf..f25b4576; records d3a328bd; the map is docs/records/TASK-102.jsonl :44): settled the O1 pin test (tests/unit/test_context_compiler.py:391) and the _json_value docstring and Limits sentence (src/aieos_bootstrap/context_compiler.py:130-134, :37-39); open O1's decision (context_compiler.py:294-295), the file case, N1. Status stays open.
