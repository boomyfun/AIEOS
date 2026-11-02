# L-0036: Save an agent's output by script, not by retyping

Rule: Save a reviewer's or helper's output for the records by a script that reads its handback from the transcript and
writes the bytes unchanged, never by retyping it with the Write tool.

- Status: active
- Category: tooling
- Binding: record only. Related: decisions D-3454, D-3465 C2; L-0025 (the reader reads handback blocks only).

## Pattern
The Write tool adds a final line feed, and the harness indents a handback's lines on display; a retyped copy is close
but not equal, and a records script that compares it with the transcript stops.

## Occurrences
- **2026-10-29 (session 87e2584b, D-3454).** The five TASK-100 review outputs, saved by Write, each carried one final
  line feed more than its handback; the first records dry run stopped with exit 5 by its own check; mk_outv100.py wrote
  exact copies, and the records cite those.
- **2026-10-29 (session 87e2584b, D-3500).** cilist_c101.py and fetch_logc101.py were copied by retyping with Write; the
  decision agent checked them line by line; later copies were made by sed or by script.
- **2026-10-30 (session 1c1bf794).** The outputs of the reviews R1 to R5, R1b, R2b, RA, RA2, RG and RG2 were saved by
  review_save2.py (the last handback of the agent, "xb", hash printed), the records script found each reviewer by the
  hash of its saved text in the agent transcripts, and the decision pages were built and copied by scripts with hash
  checks. No retyped copy.
- 2026-11-03 (../History/2026-11/2026-11-02-2326-m8-stage-8-task-116-the-first-contract-the-core-wrote-not-accepted.md, D-4686, D-4687; checkpoint cp268): the G3 review and the SEC-002 review of TASK-116 were saved with the Write tool from the displayed hand-back text, which lacks the spaces at the ends of lines, so the saved files were not byte-identical to the hand-back texts (first differences at 7028 and 1131 characters); I called them saved unedited; the first dry run of the records maker stopped at its own check; the maker now takes the text from the hand-back and asserts that the saved file equals it after the spaces at the ends of lines are removed (D-4687: no re-make needed). The rule broken: "by a script that reads its handback from the transcript and writes the bytes unchanged, never by retyping it with the Write tool".

## Why it happens
A copy that reads the same is taken for a copy that is the same.

## Prevention and detection
- Write review outputs with a script in mk_outv100.py's form (handback blocks only, 'xb', hashes printed).
- A records script compares each saved output with the transcript's handback byte for byte, as make_records_100.py does.
