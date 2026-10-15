# DEF-0063: the stack benchmark's route and conditions after TASK-040

- Status: open
- Opened: 2026-10-15 (decision D-794)
- Deferred by: decision agent (A41), D-794 (the TypeScript port's scope note), with D-795, D-796, D-800 C3 and D-802 to D-805.
- Decision group: A (the order of the benchmark's tasks within the owner's direction, A8 and Master Plan revision 4 §4).

## What
- **TASK-040** (the risk rules policy v4, RISK-01's next fixture version, the next set file and the pins): its first task commit is on task/TASK-040 (eb130f30, CI run 267 passing); the five way-2 reviews, the decision agent's review, the acceptance (citing DM F42 to F44 and the AC8 script's output and hash, conformance files section 8 (i)), the landing and the records remain. RISK-01's first conformance run over policy v4 is the base run after landing.
- **The reference export task** (next free id at its contract): the bootstrap's own decision records over every fixture case in the canonical form, printed by a test module; a closed placeholder list for engine-identity fields; a test that the document is byte-identical across two runs and on Linux and Windows; a compare step in aieos-bench.yml, skipped while no port exists, under its own A66 decision (D-794 C2).
- **The port brief**, written once before the first port and unchanged between ports; each port written by a fresh subagent given only the brief, the Python source and the fixtures (D-794 Q5, C4).
- **The TypeScript port** (bench/ts/): Node's type stripping on erasable syntax only, the ts step changed to `node main.ts` under its own A66 decision; a type-check step with tsc fetched at an exact version and checked against its published integrity hash, install scripts disabled, no secret, read-only permissions (option A); no package.json and no node_modules; a test that no AIEOS module imports or runs bench/ (D-794 C3, D-800 C3).
- **The Go and Rust ports**, the results task, round 2 (the event log's append and recovery over a generated log, never committed), and the stack ADR after both rounds (D-794 Q1); dropping round 2 is its own decision, told to the owner.
- **Equal conditions:** the same expected values and tests, one review template with findings counted per task in one table form, the third-party count split into run-time packages and build-time tools, the Windows check in CI only; the order bias stated as a limit in the results.

## Why deferred
D-794 to D-805: each step is its own task or decision, in this order, after TASK-040.

## Resume when
TASK-040 is accepted and on main.

## Log
- 2026-10-15 (session 5551e765): opened; TASK-040 contracted (D-804) and its first task commit pushed (D-805).
