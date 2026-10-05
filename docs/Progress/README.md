# Progress

A ledger of finished, verifiable outcomes, one file per month (`Progress/YYYY-MM.md`), oldest entry first. The general rules are in [`../WORKING-RECORDS.md`](../WORKING-RECORDS.md).

- **What belongs here:** finished outcomes only, each with its evidence. Examples: a commit, an executed change-set, a closed diagnostic, a created tool.
- **What does not:** plans and intentions. Those belong in History or Deferred.
- **Size:** each month starts a new file, so no file grows without limit, and closed months are not edited.

## Entry template

```markdown
## YYYY-MM-DD: <title>
- What: <one or two sentences>
- Evidence: <commit id | record path | decision id>
- A14 step: <number of the work sequence in decision-matrix A14, or "outside A14">
- Session: ../History/YYYY-MM/<file>.md
```
