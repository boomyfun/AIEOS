# DEF-0009: Open owner decisions in DM section P (P5, P6, P7)

- Status: open
- Opened: 2026-10-05 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md)
- Deferred by: owner, by authorizing the commit of the two pre-genesis files ("Đồng ý đưa toàn bộ vào hai file", transcript :814; see the source notes in the session History). The deferral wording for P5 and P6 came from a pasted advisor review (:756), which is advisory text. P7 was opened by CS-2, which the owner approved ("duyệt hash đã chính xác", :3487).
- Decision group: B (section P rows; decision agent group B, items 5 and 6)

## What
- **P5:** the owner's review capacity in hours per week. A planning input.
- **P6:** whether WSL interop may be restricted for the agent's environment. Deferred until the P-CRED and P-LOC results. A38 records a native Windows runtime, so P6 may be moot, but only the owner can say so.
- **P7:** under A35, does one-click batch approval produce one approval record per task, bound to that task's SHA?

## Why deferred
The DM statuses:
- P5 is not needed before Genesis.
- P6 waits for measurements.
- P7 must be decided before the acceptance semantics.

## Resume when
- P7: before A14 step 6.
- P6: after P-CRED and P-LOC (DEF-0004).
- P5: when planning needs it.

## Depends on
DEF-0004, for P6.

## Log
- 2026-10-05: P5 and P6 deferred (238fae0); P7 added by CS-2 (5390902).
