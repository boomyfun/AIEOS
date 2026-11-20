# L-0051: Say a step is done only when it is done, and report every difference a check found

Rule: A request, a checkpoint or a report states as done only what has already happened at the time it is written (the file exists, the command has run), and a report of a diff or a check lists EVERY difference it found, not the categories that the reporter expected; a difference found later is named as a departure of the report.

- Status: active
- Category: process
- Binding: record only. Related: L-0004 (check before showing), L-0007 (evidence proves the proposition), L-0008 (disclose limits at once), L-0014, L-0046; decisions D-6597, D-6598.

## Pattern
Two small overstatements of one session. (1) A request to the decision agent said "checkpoint 96 written" in the same message as the command that was to write it; the command was then refused by the guard and the file was written a few minutes later. (2) The report of the memory write said that the appended text differed from the approved text "only in the heading, bullets 3, 6 and 7"; the diff also showed a fourth difference (the State bullet read "read at D-6596 and D-6597"), and the report mixed line numbers with bullet order.

## Occurrences
- 2026-11-20 (session dc7cf6ca; the worker's own claim until checked): the two cases above. The decision agent found the second one by reading the memory tail itself and recorded it as an undisclosed departure; for the first it ruled that the checkpoint itself records the misstatement openly and that nothing was relied on (D-6597, D-6598).
- 2026-11-20 (session dc7cf6ca, D-6611, D-6613; the worker's own claim until checked): numbers and facts in requests that were not copied from the output at hand and were found wrong by the decision agent or by the worker in the next request: "190+" added lines for the CI revision where the machine gave 171 (D-6613); "the after file has 2106 lines before my edits" where 2106 is the before file and the after file had 2253 (D-6611). None of them reached a repository file; each was found before a write. The practice that follows: copy each number into a request from the command's printed output.

## Why it happens
A message that holds a request and the command that makes its premise true is written as if the command had already run; a diff is read for the differences that were intended, and the report is written from the intention instead of the diff output.

## Prevention and detection
- Send a request only after the thing it says is done exists, or say "will be written by the command below".
- For a diff report, print the whole diff, count its hunks and list every changed line by number; compare the count with the report before sending it.
- Number lines and bullets separately and say which one a number is.
