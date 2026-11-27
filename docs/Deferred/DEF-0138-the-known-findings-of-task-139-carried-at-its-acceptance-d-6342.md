# DEF-0138: the known findings of TASK-139 carried at its acceptance (D-6342): the docstring of decision_replay.py (F1, N1, N4, N5), the brief's errata line (N3), the engine file that runs is not hashed again (B2), the replay of decision.acceptance records (task B)

- Status: open
- Opened: 2026-11-15 (the History page of the session 26136a0a is written at its end; this line names the session)
- Deferred by: decision agent (A41, A51), D-6342 C2 (the acceptance of TASK-139: the known findings carried to the next change of decision_replay.py)
- Decision group: A (scheduling)
- Blocks v0.1: no (none is a breach of the contract of TASK-139 as amended by erratum E1 to E1.7; the INV-010 step runs the entry and main is green at 9148f6b7)
- Scheduled in: M8 or later, with the next change to src/aieos_bootstrap/decision_replay.py (task B, the replay of decision.acceptance records, or any change of the A66 step that touches the module)

## What
Findings carried at the acceptance of TASK-139 (the task commit 233dff49, accepted at D-6342), each not applied because each is text only or a stated limit and a second task commit would need new bytes, a new dry pair, a new CI run and new reviews (D-6342 option 3):
1. F1 (the decision agent's review, D-6340 :60): the docstring of src/aieos_bootstrap/decision_replay.py, step 1 (:15), says the payload must hold "engine_identity (code_sha256, python)"; _record (:215) checks only code_sha256, so a record without python is not refused there. A documentation overstatement; fix the sentence or the check.
2. N1 (D-6334 C4, :89): the docstring at :33-34 says "imported engine file" for a path that is checked before the import.
3. N2 (D-6334 C4, :90): the no-pin FAIL line was cut by the run script of the evidence; the build's own run shows it whole (build_real_out.txt of the lasting copy TASK-139): CLOSED, kept here for the list.
4. N3 (D-6334 C4, :91): the review brief's errata line names E1.1 to E1.6 only (the brief predates E1.7); a brief of a later review of this module names E1 to E1.7.
5. N4 (D-6342 :65, item (4) of its request): the docstring repeats "encoded as UTF-8".
6. N5 (D-6342 :65, item (4) of its request): the comment at decision_replay.py :98 says "before every other import" while :70 says the guard comes after `import sys`.
7. B2 (round 3, carried to the A66 step as a stated limit, D-6335 C4): the engine file that runs is the repository's own file, checked by path and by hash against the record, the pin and the commit, but not hashed again at the moment it runs.
8. B3 (round 3, a condition of the A66 step, D-6335 C4): a src top-level module that shadows a standard-library module under PYTHONPATH=src: CLOSED by the A66 step (revision 21 refuses a src name that is a standard-library module name or sitecustomize or usercustomize); kept here for the list.
9. Task B (D-6312 C2, as D-6342 :72 states): the replay of decision.acceptance records is not done; the entry fails every decision.acceptance line with "NOT REPLAYED", so no such line may be committed to a tracked events.jsonl until a replay exists. The record of a STOP: violation decision.execution (violation.py) is also not replayable by the entry (its payload has none of head_commit, log_seq, engine_identity and runtime; D-6351): a state commit of such a line turns the INV-010 step red; the standing gate of D-6351 C1 checks the exact bytes before any such commit.

## Why deferred
None is a defect against the contract of TASK-139 as amended; the entry replays line 13 of the tracked log on the CI runner; the INV-010 step is green; items 3 and 8 are closed; items 1, 2, 4, 5 and 6 are text; items 7 and 9 are stated limits with their own tasks.

## Resume when
With the next change to src/aieos_bootstrap/decision_replay.py, or at the M8 exit review, or when a run's state commit would hold a decision.acceptance or STOP: violation line.

## Depends on
DEF-0137 (the INV-010 step; its status is its own decision).

## Log
- 2026-11-15: opened (session 26136a0a; decisions D-6335, D-6336, D-6340, D-6342).
- 2026-11-27 (session 228f426b; TASK-167, accepted at D-7586, commit 837f17bfdfb912553b2a0a1cada3f2bf90165666, docs/runs/TASK-167-acceptance.md; main CI runs 45970100776 and 45970100753 success): done by AC8 of TASK-167: items 1, 5 and 6, and item 2, which was already true at the base (D-7559 C4) and is listed in AC8; read by reviewer A of the second review round on lines the third commit did not change. Item 9: the replay of decision.acceptance records is done in code; the workflow passes no governor pin yet (DEF-0137). Items 3 and 8 were closed before. Open: item 4 (a brief naming the errata E1.1 to E1.7 of TASK-139) and item 7 (a stated limit). Status unchanged.
- 2026-11-27 (session 228f426b; TASK-168, accepted at D-7616, commit 269d2d0acbdfaaaabaeb27ac466d482f4761bd1c, docs/runs/TASK-168-acceptance.md; main CI runs 45992897418 and 45992897460 success): not done: item 4 (a brief of a later review of this module naming the errata E1.1 to E1.7 of TASK-139; the briefs of this task named this task's own errata) and item 7 (a stated limit); what remains of item 9 is carried by DEF-0137. Status and schedule unchanged.
