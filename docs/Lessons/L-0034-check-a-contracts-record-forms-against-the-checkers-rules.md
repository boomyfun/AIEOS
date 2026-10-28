# L-0034: Check a contract's record forms against the checker's rules

Rule: At r0, when a contract names a record or an event that an existing checker validates (records.py's record and
claim rules, eventlog's append rules), cite the checker's rule lines in the contract and check each named form against
them by a script or a test before the reviews.

- Status: active
- Category: process
- Binding: record only. Related: decisions D-3296 (r3), D-3315 (C3); L-0031 (a contract's keys, not its record forms).

## Pattern
A contract fixes the shape of a record its code will append. Reviews read the contract against the specification,
not against the checker the log runs, so a field the checker requires is left out; only a run that appends through the
real checker finds it, after the code is written.

## Occurrences
One, in session ea6ea0a3 (2026-10-29, TASK-098):
- **D-3296.** r2's step 7 named the intent's claim as {record_id, fact_kind claim, source_class the caller's, recorder,
  subject, evidence_type intent, text}. records.py :478-483 requires decision_ref on every decision_agent record, so the
  log refused the claim. Two reviews and the decision agent's read of r2 missed it; the first placement's unit run found
  it (twelve failures and one error in test_cli_run.py). The fix cost a contract revision r3 (commit C2), a push, a new
  clone and the code redone.

## Why it happens
The record's form is written from the specification's words, and the checker's own rules sit in code that no review
of the contract is asked to read.

## Prevention and detection
- In the contract, cite the checker's rule lines for each record or event it names.
- At r0, build each named record and pass it through records.check_record (or the append check) in a scratch script
  before the reviews; any finding goes back into the draft.
- The reviewer brief asks for each named record form against the cited checker lines as its own item.
