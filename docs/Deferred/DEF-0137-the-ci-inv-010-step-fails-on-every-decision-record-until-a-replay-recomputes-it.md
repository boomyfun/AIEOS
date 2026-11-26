# DEF-0137: the CI step INV-010 replay fails on every decision record until a replay recomputes it, so the first real launch's own decision record turns main red (finding F-INV010)

- Status: open
- Opened: 2026-11-15 (session 26136a0a; D-6310, D-6312, D-6314)
- Deferred by: decision agent (A41, A51), D-6310 (the route: a replay that recomputes the decision records; the stop-gap that loosens the step ruled out as the fix)
- Decision group: A (scheduling)
- Blocks v0.1: yes (every task acceptance needs "the aieos-checks and aieos-native runs of the accepted commit succeed"; with the step red, each acceptance would be a stated departure, and the relaunch of the first real run is held behind a green main)
- Scheduled in: M8: before the first decision.acceptance record is committed to a pushed commit; the second real run (D-6606 C1 item 6)

## What
The finding F-INV010, in the decision agent's words (D-6310 C1): "The loop's real launch writes a decision record into the tracked event log; the CI's INV-010 step fails on every decision record until a replay recomputes them; the state commit and push of that record were approved (D-6303, D-6309) without checking that step; main has been red at INV-010 since that push."
The facts (the worker's claims; the decision agent cannot see GitHub): the step "INV-010 replay" (.github/workflows/aieos-checks.yml :630-669) counts every line of type decision.acceptance or decision.execution in every tracked events.jsonl and fails on any; .aieos/events.jsonl holds one, line 13, seq 13, decision.execution CONTINUE_WITH of TASK-136, committed at 4c859678 and pushed at 5b7151ff; the aieos-checks run 43681227728 of 5b7151ff failed at that step and the aieos-native run 43681227743 succeeded. A finished real run also writes decision.acceptance events (execution.py :13, :238; evaluation.py :44-46), which the step fails on too.
The evidence of feasibility: a read-only probe (D-6313) recomputed the record at line 13 from the record, the repository at its head_commit 1e15ed11 and the log up to log_seq 12, with the Resume Check loaded from head_commit (sha256 b03c0b8a..., equal to AIEOS_PINNED_RESUME_CHECK): 25 keys compared, 0 differing. The limits: one record; the readers were those of the tip's working tree; the probe ran on the machine and Python (3.14.0) that wrote the record; nothing was shown for decision.acceptance records, whose inputs (evaluation.py :62-64, "caller data, not bound") have no assembler in src/.

## Why deferred
D-6310 ruled that the step is a true signal and is not loosened as the fix (a stop-gap that names the red record and prints "NOT REPLAYED" is allowed only if the scope note shows the replay cannot land soon, and it does not for decision.execution); main is not rewritten (a history rewrite would launder provenance). The replay of decision.execution is the one task TASK-139; the replay of decision.acceptance is a second task, not yet drafted; the change of the workflow step is its own decision under A66.

## Resume when
TASK-139 has been accepted and its workflow step has landed (main green again); the acceptance replay (task B) must land, or a stop-gap be ruled by the decision agent, before the first decision.acceptance record is committed to a pushed commit.

## Depends on
TASK-138 does not depend on it but waits for a green main (D-6309 C6); DEF-0136 (the run-made evidence gap, a different cause).

## Log
- 2026-11-15: opened (session 26136a0a; decisions D-6310, D-6312, D-6313, D-6314).
- 2026-11-27 (session 228f426b; closure pass 1 of the deferred items, D-7443, D-7444; decided by: decision agent (A41, A51), D-7444): narrowed, stays open. Done: the replay of decision.execution records (TASK-139, TASK-141). Open: decision.acceptance is not replayed (src/aieos_bootstrap/decision_replay.py :40, :57, :493-:495, "NOT REPLAYED: decision.acceptance"). Scheduled in is changed to name that event.
