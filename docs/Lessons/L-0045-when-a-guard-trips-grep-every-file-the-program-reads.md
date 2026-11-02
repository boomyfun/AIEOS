# L-0045: When a guard trips, grep every file the program reads

Rule: When a program stops on a byte guard (here the records maker refusing any record that holds a main run id), grep every file the program reads for the pattern, not only the program and the files you think of as its own, before the next run.

- Status: active
- Category: process
- Binding: record only. Related: D-4630, D-4631, D-4633, D-4634, L-0039.

## Pattern
The records maker of TASK-115 refuses a record that holds the id of a run on main (such a run printed "no task" and no record may cite it). Its first dry run stopped at that guard because the two main run ids stood in the maker's own ZNOTE text (D-4630; fixed under D-4631). After that fix, the next dry run (dry2) stopped at the same guard; my grep after that stop covered the maker, the two review texts and the two CI files, not the acceptance text draft (acc-text-115.dry.txt, line 3) that the maker reads as an input; the decision agent found the cause in D-4633 (its lines 25 and 26 name the missed input and the files my grep covered), and D-4634 put the rule on the lessons list.

## Occurrences
- 2026-11-02 (../History/2026-11/2026-11-02-1252-m8-stage-8-task-115-the-explicit-owner-kept-act-statement-for-aieos-run.md, D-4630, D-4631, D-4632, D-4633, D-4634): as in Pattern; the first stop (D-4630) came from the ZNOTE text, the second (dry2) from the acceptance draft.

## Why it happens
The grep covered the files I thought of as "the maker's"; the program opens more files than that (its inputs), and a guard on the output sees everything the program read.

## Prevention and detection
- Before the first grep after a guard stop, list the files the program opens (read its source for the paths it reads) and grep all of them.
- When a program has a guard on a byte pattern, run the same grep over its inputs before the first run, not after the first stop.
