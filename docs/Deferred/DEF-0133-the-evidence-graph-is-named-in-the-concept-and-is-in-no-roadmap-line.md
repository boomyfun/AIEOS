# DEF-0133: the evidence graph is a named part of the Evidence primitive and is in no roadmap line

- Status: open
- Opened: 2026-11-06 (../History/2026-11/2026-11-06-1701-m8-stage-8-the-decision-files-d5198-to-d5236-and-the-coverage-map-ce14b08a.md)
- Deferred by: decision agent (A41, A51), D-5246 (the gaps of the coverage map, D-5245)
- Decision group: A (a question of scheduling); whether it is dropped as an idea is the owner's, since it names a part of a concept primitive
- Blocks v0.1: no (it is in no line of concept section 16, lines 934-960, and no search of src or docs found it; the evidence records and the profile it would organise are built)
- Scheduled in: M8, at its exit review

## What
Concept line 320 lists "Evidence graph" in the Evidence primitive (with Change (SHA), Verification Run, Evidence item and Evidence Profile). The concept also names it in the architecture (line 41), as the one primitive against failure mode F9, 'Không truy vết được' (line 132), and as a possible moat (line 901). No module, specification or roadmap line names it (Grep of src and docs found no "evidence graph"). The records bound to commits and intent versions exist (records.py, verification_records.py); a graph over them does not.

## Why deferred
Found by the coverage map (decisions D-5244 and D-5245): not out of v0.1 by any cited line, and not in the v0.1 list either. It is put as an item so that it is neither forgotten nor reworded away.

## Resume when
At the M8 exit review, which gives it one state under the deferral rule's point (3), or earlier if a task needs it; dropping it as an idea is the owner's (Decision group).

## Depends on
None.

## Log
- 2026-11-06: opened (session ce14b08a; decisions D-5245, D-5246).
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass F batch 3, decision D-5269 (C3)): read in full; a Grep over src, docs/specs and docs/plan finds 'evidence graph' only in docs/plan/master-plan.md; Resume-when is the M8 exit review, which gives it one state under the deferral rule's point (3); scheduling it into M8 again at that review does not count as a state (one of: a later milestone with a reason, done, or an owner question to drop it); dropping it as an idea is the owner's and is not asked now. State: open; Blocks v0.1: no (it is in no line of concept section 16, lines 934-960, and no search of src or docs found it; the evidence records and the profile it would organise are built); Scheduled in: M8, at its exit review.
