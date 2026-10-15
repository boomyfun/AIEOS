# The stack benchmark: round-1 results

> - **Status:** advisory; not a choice; no weights applied. A working record like `docs/plan/m4-exit-review.md`: it decides nothing, approves nothing and feeds no gate, record or evidence entry (DM A29, A31). Its text is decided by the decision agent (decision D-904); decision files are kept outside the repository (`docs/WORKING-RECORDS.md`).
> - **Scope:** round 1 of the benchmark of `docs/plan/m4-exit-review.md` §6 (the governor's acceptance decision and the Resume Check over the 30 frozen fixtures; `docs/plan/bench-port-brief.md` §2). Round 2 (the event log's append and recovery over a generated log) comes next, and the stack ADR only after both rounds (decision D-794 Q1). The owner's criteria and weights are the table at `docs/plan/m4-exit-review.md` lines 74-83, with the owner's answer quoted at lines 92-97; they are cited here, not restated, and not applied to round 1 alone (decision D-903).
> - **Sources:** every number below comes from a script run over the hosted runs' logs (`gh run view <id> --log`) and the repository at commit 2f136dbb; the script and its output are kept outside the repository with the decision that approved this text.

## 1. The runs

| Benchmark run | Run id | Commit | Ports present | Result |
|---|---|---|---|---|
| 3 | 38737399240 | 22bc141e (TASK-043) | ts | success, Linux and Windows |
| 4 | 38749703476 | b8f876cf (TASK-044) | ts, go | success, Linux and Windows |
| 5 | 38767539125 | 1c6117c7 (TASK-045) | ts, go, rust | success, Linux and Windows |
| 6 | 38776247835 | 2f136dbb (TASK-046) | ts, go, rust, with the no-argument probes | success, Linux and Windows |

Toolchains printed by every run (the runners', not pinned; brief §3): node v22.23.3, go1.24.13, rustc 1.99.0 (b940084d7 2026-09-28); Python 3.12.3 on Linux and 3.12.10 on Windows for the reference export.

## 2. Per criterion (numbers in `docs/plan/m4-exit-review.md` §6's table)

**1. Correctness against the frozen fixtures (line 76).** Each port's step builds or checks the port, runs it on the fixture document and compares its output with the reference document byte for byte (`tests/unit/test_export_reference.py --compare`, which fails the step on any difference), then runs the port's own tests. In run 6 every port step passed on both runners: TypeScript "OK: 34 passed, 0 failed", Go "ok aieosbench", Rust "65 passed, 0 failed" (run 6 log, Windows lines 141, 160, 258; Linux lines 401, 420, 518). Each port also passed in every run after it was added (runs 3 to 6 for TypeScript, 4 to 6 for Go, 5 and 6 for Rust). All three ports are byte-equal with the reference on Linux and Windows; none is ruled out. Limits: the reference's pin and the brief's revisions 1 and 2 (the two unexpected-error paths fail closed; the runners' toolchains); each port's stated limits (DEF-0063).

**2. Supply-chain size (line 77).** Third-party packages needed for the workload, split as DEF-0063 and the brief §4 set:

| Port | Run-time packages | Build-time tools | Source |
|---|---|---|---|
| TypeScript | 0 (no package.json, no node_modules in bench/ts) | 1: the type checker TypeScript 6.0.3, fetched by the workflow and checked by its integrity value | `.github/workflows/aieos-bench.yml` lines 70 and 158 |
| Go | 0 | 0 | `bench/go/go.mod` (2 lines, no require) |
| Rust | 0 | 0 | `bench/rust/Cargo.toml` (no dependency table); `bench/rust/Cargo.lock` (1 package, the port's own) |

The languages' own toolchains (node, go, cargo and rustc) are the runners' and are not counted (brief §3).

**3. Distribution (line 78).** A reading, marked as such: Go and Rust each build one program file (the probe of run 6 ran it); the TypeScript port runs as source under node, with no build output. Reading: Go yes, Rust yes, TypeScript no (a runtime to install).

**4. Windows and Linux behaviour the same (line 79).** Each run has a Linux and a Windows job; in runs 3 to 6 every present port's step passed on both, with the same test counts on both. One observed difference with no effect: the Rust test target's path is printed with a backslash on Windows (run 6). Departure: line 70 of the exit review plans "run in the CI channel on Linux and locally on Windows"; the brief §4 line 45 later set the Windows check as the CI's only, and this record follows the brief.

**5. Speed (line 80).** Not measured in round 1. The hosted runs time whole steps that mix building, testing and runner start-up on shared machines, so their durations are not the workload's run time. The criterion stays open: before the stack ADR it is either measured under its own decision or the owner is asked in plain words whether to leave it unscored (decision D-903).

**6. How well AI agents write and review it (line 81).** Review findings per task, in one form (five way-2 reviews per task from one template, on a model other than the writer's; non-blocking findings listed and counted under decision D-864 C2's rule; a reviewer's "not applicable" note is no finding and is neither listed nor counted in any task; no blocking finding in any task); AI-judged (CR-002 K6), not a human measure:

| Task | Port | Listed | Counted | Beside the counts |
|---|---|---|---|---|
| TASK-043 | TypeScript | 20 | 18 | superseded TASK-042 (a conflict with an earlier workflow test, decision D-844); its download added review surface the other ports do not have |
| TASK-044 | Go | 19 | 19 | erratum E1 to its contract (decision D-858) |
| TASK-045 | Rust | 20 | 19 | its contract's revision 0 returned for changes (MODIFY, decision D-872) and redrafted |
| TASK-046 | hardening, not a port | 17 | 10 | over all three ports; kept out of the per-language comparison |

**7. Type and memory safety (line 82).** A language property; a reading, marked as such: Rust's compiler checks types and memory safety (no unsafe code is allowed in the port, TASK-045's contract); Go checks types and manages memory, with no pointer arithmetic outside its unsafe package (not used); TypeScript checks types at build time only (the type check step) and runs on node's memory management.

**8. Ease for the owner to read and maintain (line 83).** The owner's own judgement, asked once when the stack ADR's draft exists (decision D-903). For reference only, the sizes at commit 2f136dbb: bench/ts 10 files, 2307 lines; bench/go 8 files, 3414 lines; bench/rust 11 files, 4051 lines (each count includes the port's tests and its build files).

## 3. Limits

- The ports were written one after another, so the order is a bias; every writer and reviewer is an AI of one vendor; round 2 is not yet run (brief §4 line 46).
- The runners' toolchains are not pinned and clippy's lints move with Rust's version (brief §3, revision 2); TASK-043's local check ran on node v24.11.1; TASK-045's local check was for the gnu target, the hosted Windows runner builds for its own default; the Rust distribution's hash is self-attested by its publisher.
- The port brief was written after TASK-041 rather than before it, a departure with nothing depending on it (DEF-0063); the review template's revision 1 (decision D-870).
- Each port's own limits (DEF-0063), among them TASK-045's lone surrogate escape refused where Python accepts it and its document form read as byte-exact canonical text.
- TASK-046's limits: the probes check standard output only (the workflow header's "print nothing" and the task commit's "no output" mean standard output); the Rust forbidden-form scan is textual (it misses an alias such as `use std as s;` and a grouped import, and a form in a comment or string is a false hit, failing closed); the Rust probe would pass on a missing program, a gap closed for run 6 only by a check of that run's log (decision D-900), to be fixed at the next change of the benchmark workflow.
- Criterion 4 follows the brief's CI-only Windows check, a departure from line 70's plan (above).
