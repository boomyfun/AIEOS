# L-0047: Count the input of a bounded run first, and never start a process per file in a list builder

Rule: Before a run whose input is every file newer than a reference file (or any tree of unknown size) is released, a cheap count by folder (a find with counts only) is released and run first; a list builder works in batches (find, awk, xargs) and never starts a subshell or a program per file.

- Status: active
- Category: process
- Binding: record only. Related: L-0043, L-0046; decisions D-5940, D-5941, D-5942 (C7).

## Pattern
A script written for a small input meets a large one, runs under a fixed time limit and gives no output. A subshell or a program started for each file multiplies the cost by the number of files, and the size of the input was never probed.

## Occurrences
- Session 7d0b3852 (2026-11-13; the worker's own claim until checked): D-5940 released one run of gen_list_t131.sh with a 110 s limit and no size probe (the decision agent's release of the worker's draft); it timed out with no output, because five git work trees in the scratchpad (4975 files outside their .git folders, test copies from the TASK-130 fix work) fell under the 'newer than t129.sum' rule and the script started several processes for each file (a subshell with tr for each name, a stat for each size). D-5941 released one count by folder and a batched copy, gen_list_t131b.sh, that drops git work trees; D-5942 released its run.

## Why it happens
The input looked small when the script was written; the limit of the run was a number to meet, and no step measured the input before the run.

## Prevention and detection
- Before the first run of a list builder over a tree, run a count by folder (a find that prints counts only) and read it.
- Write the list with batch tools (find, awk, xargs); no subshell and no program per file.
- A run with a time limit and an unprobed input is brought back to the decision agent as such.
