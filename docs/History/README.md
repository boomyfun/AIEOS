# History

One file per working session: what was asked, what was done and decided (and by whom), what went wrong, and what was left open. The general rules are in [`../WORKING-RECORDS.md`](../WORKING-RECORDS.md).

- **Path:** `History/YYYY-MM/YYYY-MM-DD-HHMM-<slug>.md`, where the date and time are the session's start in local time (UTC+7).
- **When:** written at the end of the session. Never edited afterwards, except to fix a factual error, with a dated note at the end of the file.
- **Status:** non-authoritative. A History file never overrides the decision matrix or the decision log.

## Template

```markdown
# Session YYYY-MM-DD HH:MM to YYYY-MM-DD HH:MM (UTC+7): <title>

- Status: working record, non-authoritative; written by Claude at the end of the session; a claim, not evidence.
- Session id: <id>; transcript: <id>.jsonl (on the owner's machine; "transcript :N" means line N).
- Model: <model id of the worker>.
- Repository at start: <commit>; at end: <local main>, GitHub main <commit>.

## Summary
## Timeline
## Decisions
| Date | What | Decided by | Recorded in |
|---|---|---|---|
## Changes made
## Problems and mistakes
## Deferred and open at the end
## State at the end and next step
```

"Decided by" is one of these:
- the owner (with a quote);
- the decision agent (`D-NNN`);
- Claude under the owner's delegation (used only before 2026-10-06, when the decision agent took over under DM A41).

Advisors (other AI models) never decide.
