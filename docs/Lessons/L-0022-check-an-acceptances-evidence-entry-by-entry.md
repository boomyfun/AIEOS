# L-0022: Check an acceptance's evidence entry by entry, by script

Rule: Before an acceptance request, list by script every entry of the task's profile joined with its articles' evidence_required and the one record that meets each (type, stands_for, source and commit), refusing an entry with none or a record counted twice, and report the governor's output over those records as data; never judge coverage from a review's basis text (D-1092, D-1098).

- Status: active
- Category: verification
- Binding: record only. Related: decisions D-1089, D-1092, D-1098; DEF-0074; L-0004 (check coverage criteria rule by rule); L-0007 (state what a check proves).

## Pattern
An acceptance is approved on records whose basis text says a review served several entries, while the bound text counts one review for one entry, so entries are missing without anyone seeing it.

## Occurrences
One, found in session 2026-10-17-0436 (../History/2026-10/2026-10-17-0436-adv-02s-fixture-reviewed-twice-and-the-records-form-found.md):
- **2026-10-17 (D-1089, D-1092, D-1098).** TASK-039, TASK-041 and TASK-043 to TASK-055 were accepted with one decision-agent review record whose basis claimed both the architecture human_review and the cross-model half, and with no record for OPS-002's human_review in TASK-039 to TASK-056; a later governor run showed that no task's records are in the form the governor reads. Opened as DEF-0074.

## Why it happens
The acceptance requests and their reading checked that the reviews were made and passed, by their text, not that each profile entry had its own record in the form the governor counts.

## Prevention and detection
- Run the per-entry script before every acceptance request and paste its unedited output; report the governor's output beside it, with the known reason while DEF-0074 is open.
