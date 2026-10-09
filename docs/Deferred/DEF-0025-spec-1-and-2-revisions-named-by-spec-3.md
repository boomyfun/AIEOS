# DEF-0025: The next revisions of specifications 1 and 2 that specification 3 names

- Status: done
- Opened: 2026-10-10 (decision files D-244 C4 and D-245)
- Deferred by: decision agent (A41), D-244 C4: specification 3 settles points of specifications 1 and 2 and uses specification 2 beyond its current text without changing either file (D-243 (P3)); their next revisions record it.
- Decision group: A (specification revisions under A51, B9).

## What
- Specification 1: §10 points 7 and 9 (settled by specification 3 §10 and §9), and point 8 (whether `task.stale` may start from READY; specification 3 §12 point 6 proposes yes when the Resume Check finds it).
- Specification 2: §10 point 6 (settled by specification 3 §9); `refers_to` carrying a constitution article's id on a check observation (specification 3 §12 point 8); the `task.blocked` reasons `dependency`, `escalate` and `scope_invalid` (point 5); policy keys for the base branch and the module roots in §7 (point 10); the `task.stale` cause for an intent change with no `intent.changed` event (point 4).

## Why deferred
Specification 3 was approved without changing specifications 1 and 2 (D-243 (P3); D-244 Q2); their texts stay as approved until a revision.

## Resume when
Before any M3 code contract that implements those points.

## Depends on
Specification 3 (DM F23).

## Log
- 2026-10-10: opened (decision files D-244 and D-245). ../History/2026-10/2026-10-09-2339-spec-3-approved-and-on-main.md
- 2026-10-10: done: specifications 1 and 2 revision 2 record every point of "What" (DM F25, F26; decision D-255), commit 236e546; the one point found outside it is DEF-0026. ../History/2026-10/2026-10-10-0043-bootstrap-scope-and-m3-documents.md
