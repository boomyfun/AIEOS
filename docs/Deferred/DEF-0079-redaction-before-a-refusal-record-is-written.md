# DEF-0079: redaction before a Claude Code adapter's refusal record is written

- Status: open
- Opened: 2026-10-18 (session 89ad39be; decision D-1239 C4)
- Deferred by: decision agent (A41), D-1219 (R2-2) in session dfcb097a; the item was found never opened in session 89ad39be (D-1239 M4, C4).
- Decision group: A (an input to the contract that writes the records); B for any install or setting.

## What
- TASK-061's judge (src/aieos_bootstrap/claude_code.py, its docstring) copies a refused shell command's text into the refusal record's refers_to, so a credential typed into a command would stay in the record; its docstring says that redaction before a record is written is part CC-2's.
- D-1219 ruled this "a Deferred item for CC-2 (redaction before any record is written)"; no file under docs/ named it until this item.
- TASK-062 (CC-2's hook entry) returns judge's record unchanged (its AC3), so it cannot redact; its contract carries this as a limit and sends redaction to point 7's rest of specification 5 section 11, where the record is written (D-1239 M4).

## Resume when
- With the contract that writes an adapter's records to the core (specification 5 section 11 point 7's rest), or the owner's word.

## Log
- 2026-10-18: opened (session 89ad39be; D-1219 R2-2, D-1239 M4 and C4).
