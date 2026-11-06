# Deferred

Work that was put off, one file per item (`Deferred/DEF-NNNN-<slug>.md`). Each file records why the item was deferred, who deferred it, and when it should resume. The general rules are in [`../WORKING-RECORDS.md`](../WORKING-RECORDS.md).

- **Status values:**
  - `open`: waiting for its condition;
  - `waiting-owner`: needs the owner's answer;
  - `resumed`: being worked on;
  - `done`: finished;
  - `dropped`: no longer wanted, with the reason.
- **Changes:** the status changes in place, with a dated line under "Log". Files are never deleted or renumbered.
- **List of open items:** `grep -lE "^- Status: (open|waiting-owner)" docs/Deferred/DEF-*.md`.
- **Who decided to defer:** always recorded. An owner deferral quotes the owner. A decision-agent deferral cites its decision ID. A Claude proposal is labelled as a proposal, not a decision.
- **Decision group:** group B items are decided only by the owner, as in decision-matrix A41.
- **Deferral rule:** `docs/plan/master-plan.md` section 6 (revision 7) sets when an item is opened, unblocked and listed at an exit review.

## Template

```markdown
# DEF-NNNN: <title>

- Status: open
- Opened: YYYY-MM-DD (../History/YYYY-MM/<file>.md)
- Deferred by: <owner: "quote" (transcript :N) | decision agent D-NNN | Claude (proposal, not a decision)>
- Decision group: <A | B | unknown>
- Blocks v0.1: <yes | no (why)>
- Scheduled in: <task or milestone | none>

## What
## Why deferred
## Resume when
## Depends on
## Log
- YYYY-MM-DD: opened.
```
