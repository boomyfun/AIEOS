# The stack benchmark: round-2 results

> - **Status:** advisory; not a choice; no weights applied. A working record like `docs/plan/bench-results-round1.md`: it decides nothing, approves nothing and feeds no gate, record or evidence entry (DM A29, A31). Its text is decided by the decision agent (its own decision); decision files are kept outside the repository (`docs/WORKING-RECORDS.md`).
> - **Scope:** round 2 of the benchmark of `docs/plan/m4-exit-review.md` §6: the event log's append and recovery over a generated log, read as the two pure computations `eventlog.append` and `recovery.reconcile` with `records.check_log` (`docs/plan/bench-port-brief.md` §6; decision D-905). Round 1 is recorded in `docs/plan/bench-results-round1.md`; both rounds now exist, and the stack ADR comes next (decision D-794 Q1). The owner's criteria and weights are the table at `docs/plan/m4-exit-review.md` lines 74-83, with the owner's answer at lines 92-97; they are cited here, not restated, and not applied here.
> - **Sources:** every number below comes from a script run over the hosted runs (`gh run list`, `gh run view <id> --log`) and the repository at commit 049af36f; the script and its output are kept outside the repository with the decision that approved this text.

## 1. The runs

| Benchmark run | Run id | Commit | Round-2 ports present | Result |
|---|---|---|---|---|
| 7 | 38810091491 | 6b026569 (TASK-047, the round-2 export) | none (the export step only) | success, Linux and Windows |
| 8 | 38826682472 | 8b048964 (TASK-048) | rust | success, Linux and Windows |
| 9 | 38843900338 | 1eb1b79d (TASK-049) | rust, go | success, Linux and Windows |
| 10 | 38850814746 | 049af36f (TASK-050) | rust, go, ts | success, Linux and Windows |

Toolchains printed by run 10 (the runners', not pinned; brief §3): node v22.23.3, go1.24.13, rustc 1.99.0 (b940084d7 2026-09-28); Python 3.12.3 on Linux and 3.12.10 on Windows for the round-2 export. They are the same versions as round 1's run 6.

## 2. Per criterion (numbers in `docs/plan/m4-exit-review.md` §6's table)

**1. Correctness against the reference (line 76).** In each port's step, after round 1, the round-2 program runs over the generated input document, its output is compared with the round-2 reference document by `tests/unit/test_export_reference.py --compare` (the step's shell stops on its failure), a no-argument probe checks that the program refuses, and the port's own round-2 tests run (`.github/workflows/aieos-bench.yml` lines 104-108, 123-128 and 146-150 for Linux; 214-218, 233-238 and 256-260 for Windows). In run 10 every port step passed on both runners: TypeScript "86 passed, 0 failed" and "PASS whole input: byte-equal to the reference"; Go "ok aieosbench/round2"; Rust "45 checks passed, 0 failed" and "ok: the whole document is byte-equal to the reference" (run 10 log, Linux lines 160, 245, 272, 380, 425; Windows lines 587, 672, 699, 807, 852). Each port also passed in every run after its round 2 was added (runs 8 to 10 for Rust, 9 and 10 for Go, 10 for TypeScript), and round 1 kept passing in the same runs. All three ports are byte-equal with the round-2 reference on Linux and Windows; none is ruled out. Limits: §3.

**2. Supply-chain size (line 77).** Round 2 added no third-party package and no build-time tool to any port (brief §6.4): at 049af36f, `bench/rust/Cargo.toml` has no dependency table and `bench/rust/Cargo.lock` lists 1 package, the port's own; `bench/go/go.mod` has no require line; `bench/ts` has no package.json, and its one build-time tool stays the type checker TypeScript 6.0.3 of round 1. The table of round 1 (`docs/plan/bench-results-round1.md` §2, criterion 2) holds unchanged for both rounds: TypeScript 0 run-time packages and 1 build-time tool; Go 0 and 0; Rust 0 and 0.

**3. Distribution (line 78).** Unchanged from round 1, a reading: Go and Rust each build round 2 as a second program file (port2), the TypeScript port runs main2.ts as source under node. Reading: Go yes, Rust yes, TypeScript no (a runtime to install).

**4. Windows and Linux behaviour the same (line 79).** In runs 8 to 10 every present port's round-2 step passed on both runners; run 10 shows the same test counts on both (TypeScript 86 and 86, Rust 45 and 45; Go's package test "ok" on both). The Windows check is the CI's only, as in round 1 (brief §4), a departure from line 70's plan carried from round 1.

**5. Speed (line 80).** Not measured in round 2, for round 1's reason: the hosted runs time whole steps that mix building, testing and runner start-up on shared machines. It stays open; before the stack ADR it is measured under its own decision or the owner is asked in plain words whether to leave it unscored (decision D-903).

**6. How well AI agents write and review it (line 81).** Round 2's review findings per task, in round 1's form (five way-2 reviews per task from the port review template revision 1 with the five round-2 fills of decision D-934, on a model other than the writer's; non-blocking findings listed and counted under decision D-864 C2's rule; no blocking finding in any task); counted apart from round 1; AI-judged (CR-002 K6), not a human measure:

| Task | Port | Listed | Counted | Beside the counts |
|---|---|---|---|---|
| TASK-048 | Rust | 20 | 6 | first of round 2 (order Rust, Go, TypeScript, decision D-905); one blank line in lib.rs as a recorded departure |
| TASK-049 | Go | 19 | 3 | two whole round-1 files copied (a Go `package main` cannot be imported), a stated duplication |
| TASK-050 | TypeScript | 18 | 3 | departure W-a (one effect-free command of the writer outside its tool rule), ruled with AC2 at acceptance (decision D-969) |
| TASK-047 | round-2 export, not a port | 20 | 8 | the hardening template, lines 3 and 13 of the briefs corrected for this run (decision D-916); kept out of the per-language comparison |

Round 1's table for comparison: TypeScript 20 listed and 18 counted, Go 19 and 19, Rust 20 and 19 (`docs/plan/bench-results-round1.md` §2, criterion 6). Round 2's counts are lower for every language; the two rounds are different workloads, and this record does not explain the difference.

**7. Type and memory safety (line 82).** Unchanged from round 1, a reading: no new language feature class was needed by round 2 (no unsafe code in the Rust port, its contract; Go without its unsafe package; TypeScript type-checked at build time only).

**8. Ease for the owner to read and maintain (line 83).** The owner's own judgement, asked once when the stack ADR's draft exists (decision D-903). For reference only: round 2 added 3558 lines in 9 files to bench/rust, 3098 lines in 9 files to bench/go (among them the two copied round-1 files) and 1975 lines in 7 files to bench/ts (each count includes the port's tests and, for Rust, Cargo.toml's ten new lines); at commit 049af36f the whole ports are bench/ts 17 files, 4282 lines; bench/go 17 files, 6512 lines; bench/rust 18 files, 7609 lines.

## 3. Limits

- The ports were written one after another; round 2 reversed round 1's order (Rust, Go, TypeScript) so the order bias does not fall on the same language twice, but it remains a bias; every writer and reviewer is an AI of one vendor (brief §4).
- Round 2 compares no file behaviour: the writer (files and SQLite) and startup (it starts `git`) are outside it (brief §6.1). Where the Python builds a text that names a Python type, every port fails closed instead; the generated input reaches none of these (brief §6.3).
- The runners' toolchains are not pinned (brief §3, revision 2); TASK-050's local check ran on node v24.11.1 and the runners on v22.23.3.
- Each port's own round-2 limits (DEF-0063): Rust: the fail-closed inputs tested in-process only; a commit message outside ASCII refused where the Python computes it; the no-argument probe passing on a missing program (TASK-046's carried limit). Go: the fail-closed inputs tested in-process only; the writer's stated limits 1 to 9, among them a year below 1000 refused (read from Linux strftime), an open fidelity question since the benchmark's Python may run on Windows; the two copied round-1 files. TypeScript: W-a; the fail-closed inputs tested in-process only; the writer's stated limits 1 to 8, with the same year-below-1000 question (its limit 5); the record forms written again in r2_records.ts. All ports: the round-2 files pinned by name only (decision D-954, benchmark-wide).
- The review template's five round-2 fills are task facts, not a template revision (decision D-934); the template itself is unchanged since revision 1 (decision D-870).
