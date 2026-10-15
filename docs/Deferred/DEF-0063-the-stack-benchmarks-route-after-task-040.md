# DEF-0063: the stack benchmark's route and conditions after TASK-040

- Status: open
- Opened: 2026-10-15 (decision D-794)
- Deferred by: decision agent (A41), D-794 (the TypeScript port's scope note), with D-795, D-796, D-800 C3 and D-802 to D-805.
- Decision group: A (the order of the benchmark's tasks within the owner's direction, A8 and Master Plan revision 4 §4).

## What
- **TASK-040** (the risk rules policy v4, RISK-01's next fixture version, the next set file and the pins): accepted (D-811) and on main (163da2f7, D-812; records 1121c235, D-813). RISK-01's first CI run over policy v4 was the conformance base run of TASK-041's first task-branch push, run 272 (38716266030): PASS (D-814, D-818). Carried from its reviews to the policy's next version, no later than the TypeScript port task: R12's reason states as a fact a condition on later code (no AIEOS module imports or runs bench/), and the revision line does not name the header lines (D-810 dispositions 1 to 3).
- **The reference export task, TASK-041** (D-814, D-815): contracted (commit C 6fe1c7aa, D-816) and its first task commit on task/TASK-041 (3a9190db, run 272 passing, D-818): tests/unit/test_export_reference.py (the bootstrap's decision records over the 30 round-1 fixtures in the canonical form; one closed placeholder, engine_identity.python; the pinned hash 01aeec8f…; a compare mode), one step per job in aieos-bench.yml (DM A66, bytes 6cb5e2b3…), one allow-list entry. Its five reviews, the decision agent's reviews, acceptance, landing and records remain; each port task adds its own compare line under its own A66 decision (D-814 Q4); RISK-01 is out of round 1. The workflow header's description (lines 2 to 4) does not name the new step: for the first port task's A66 change (D-818).
- **The port brief**, written once before the first port and unchanged between ports; each port written by a fresh subagent given only the brief, the Python source and the fixtures (D-794 Q5, C4).
- **The TypeScript port** (bench/ts/): Node's type stripping on erasable syntax only, the ts step changed to `node main.ts` under its own A66 decision; a type-check step with tsc fetched at an exact version and checked against its published integrity hash, install scripts disabled, no secret, read-only permissions (option A); no package.json and no node_modules; a test that no AIEOS module imports or runs bench/ (D-794 C3, D-800 C3).
- **The Go and Rust ports**, the results task, round 2 (the event log's append and recovery over a generated log, never committed), and the stack ADR after both rounds (D-794 Q1); dropping round 2 is its own decision, told to the owner.
- **Equal conditions:** the same expected values and tests, one review template with findings counted per task in one table form, the third-party count split into run-time packages and build-time tools, the Windows check in CI only; the order bias stated as a limit in the results.

## Why deferred
D-794 to D-805: each step is its own task or decision, in this order, after TASK-040.

## Resume when
TASK-040 is accepted and on main (done, D-811 to D-813); next, TASK-041's acceptance.

## Log
- 2026-10-15 (session 5551e765): opened; TASK-040 contracted (D-804) and its first task commit pushed (D-805).
- 2026-10-15 (session 976ca2a9): TASK-040 accepted and on main (D-811 to D-813); a wrong statement corrected: the records commit 1121c235's message names its own push as RISK-01's first run over v4, but run 270's base run printed "a push to main whose head commit has 0 trailer lines; no run", and run 269's ran the base 8d980541 (v3); the first run over v4 was run 272, PASS (D-814); TASK-041 contracted and its first task commit pushed (D-815 to D-818).
