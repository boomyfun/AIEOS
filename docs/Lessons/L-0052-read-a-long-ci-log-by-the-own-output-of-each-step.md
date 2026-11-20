# L-0052: Read a long CI log by the own output of each step, with the step list checked against the run's job record

Rule: A CI log of 100 KB or more is read by a pinned read-only script (or by the Grep tool; D-6589 C1) that gives the step list from the log's own step field next to the step list of the run's job record (the job JSON of the run), the lines each step wrote after the last group end (its own output, not its echoed script), the matching lines of those outputs with their numbers and the count of matches that lie in echoed script text; a script is brought to the decision agent with its sha256 before it runs and is run once per log, in the form that the owner's command guard allows.

- Status: active
- Category: process
- Binding: record only. Related: L-0021, L-0030, L-0039, L-0046; decisions D-5290 (C2), D-6581, D-6588, D-6589, D-6596.

## Pattern
The first method for reading the log of a green run was to read every line that has text after the time stamp. For a log of 318 KB this was too large; the first substitute script printed in full every step of the main rules and so wrote an output larger than the log, and the matches of the words "fail" and "error" were nearly all echoed script text.

## Occurrences
- 2026-11-20 (session dc7cf6ca; the worker's own claim until checked): the CI read of 4d61f514 used the first substitute (D-6588 C3) and the decision agent accepted the read with two departures (no -I; an output larger than the log; D-6589). D-6589 C1 fixed the method above; it was used on both logs of cd95bc05 (ci_read2.py, D-6596) and every step matched its record in the job JSON.

## Why it happens
A log echoes the source of every step before its output, so any word search matches the source; a log is long because of the echoes and not because of the results.

## Prevention and detection
- Take the result of a step from the lines after its last group end, and count the matches that lie in the echoed text separately.
- Compare the step names of the log with the steps of the run's job record, in both directions, and name any step that has no counterpart.
- A step that finishes in under a second is explained from its own last line (for example "no task"), not assumed.
