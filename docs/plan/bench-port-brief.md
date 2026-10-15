# The stack benchmark's port brief

> - **Status:** revision 3. Non-binding, like `docs/plan/m4-exit-review.md`: it plans and decides nothing that a decision matrix (DM) row, a bound document or a task contract decides. Its text is decided by the decision agent (decision D-829); it changes only by a decision of its own, applied to every port not yet written, and each change is recorded as a limit of the benchmark's results (decision D-794 Q5).
> - **Purpose:** the one brief that every language port of the stack benchmark is written from (`docs/plan/m4-exit-review.md` §6; Master Plan §4, the benchmark; DEF-0063), so that the three ports (TypeScript, Go, Rust) are written under the same conditions: round 1 (§1 to §4) and round 2 (§6).
> - **Sources:** the decisions D-765 to D-767, D-773, D-794, D-800, D-814 to D-818, D-827, D-905 and D-917; decision files are kept outside the repository (`docs/WORKING-RECORDS.md`).

## 1. Who writes a port, and from what

- Each port is written by a fresh agent that has seen nothing of the other ports, of their reviews or of the benchmark's earlier work. Its model is named in the port task's contract and differs from the model of that task's five reviewers.
- The writer is given exactly these inputs, and nothing else:
  1. this brief;
  2. the Python source of the bootstrap at commit `aed226dc6d50fc44fac0ae11d39dfb6b3cb1dc79`, of these four files only, each checked by its SHA-256 before it is given:
     - `src/aieos_bootstrap/governor.py` (2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f);
     - `src/aieos_bootstrap/resume_check.py` (e1578939404da0b61d56d9187521b92c923e7cb841acdf15d0afb7155605a135);
     - `src/aieos_bootstrap/records.py` (a85f74851e69979cdce5063c9522237704860c68a89b6f4a26801000c3fcd5b9);
     - `src/aieos_bootstrap/conformance.py` (70cce9106018f7b49ee608e7eb111708044aef6061c1c21ad5e6dad1cedfeacc);
  3. the two exported documents, made at that commit:
     - the fixture document, printed by `tests/unit/test_export_fixtures.py --root tests/conformance` (the input of the port);
     - the reference document, printed by `tests/unit/test_export_reference.py --root tests/conformance` (the output the port must reproduce), with the source of that module (2acae51ba5fcb5762cdf149162fe11406e301abfb0ee862f9a679f59eaa8577d) as the description of its form;
  4. the port task's contract, for its write-set, its build and run commands and its limits.
- If a later task changes one of these files, the port tasks after it name the new commit and hashes in their contracts, and the change is recorded as a limit (the reference's pin changes with it, TASK-041's contract).

## 2. What a port does

- It ports, into its language, the acceptance decision of the governor (`governor.evaluate` and every function it calls) and the Resume Check (`resume_check.check` and every function it calls), with the record forms they use from `records.py`, and the canonical text of `conformance.canonical_text`. Nothing else: not the conformance runner's form and result checks, not the event log, not the writer, not the risk computation (`derive_inputs` and RISK-01 are left out of round 1).
- It reads the fixture document from the path given as its one argument, and for every key of the 19 governor fixtures (`fixtures/<name>`) and the 11 Resume Check fixtures (`fixtures_rc/<name>`) and every case in order, it computes the record exactly as the reference export does (the same arguments, read from the fixture as `conformance.py` reads them; the inputs never changed by a call).
- It computes every record from the case's request, inputs and records in the fixture document. Its code embeds no part of the reference document and uses no case's expected values; only its own tests may read the reference document or the expected values, as the expected output.
- It prints to standard output one document byte-equal to the reference document: one object whose keys are `"<folder>/<file stem>"` (30 keys) and whose values are the lists of that file's case records in case order, in the canonical text (sorted keys, the separators and escaping of `canonical_text`, ASCII only, LF line ends, one final LF), with exactly one placeholder: in every record that has `engine_identity.python`, its value is the text `<engine>`. No other value is replaced; record ids are computed, not copied.
- It fails closed: on a missing or extra argument, a document that is not of the fixture document's form, or any case it cannot compute, it exits non-zero and prints nothing to standard output (the whole document is built before the single write).
- An unexpected error inside a computation is a case it cannot compute. Where the Python returns an error record that names a Python exception type, it fails closed instead: `resume_check.check`'s "an input could not be read: <type>" and "the check could not complete: <type>". No fixture reaches these paths, and the type names are Python's own, so no port can reproduce them; every port treats them alike, and the results state it as a limit.

## 3. Rules for every port

- No third-party package at run time. A build-time tool (a compiler, a type checker) only as the port task's contract names it, at an exact version, checked against its published integrity hash, with install scripts disabled.
- The language's own toolchain (node for TypeScript, the go command for Go, cargo and rustc for Rust) is the one the hosted runners provide: it is not downloaded in the workflow, its version is printed in the run's log, and that version is stated as a limit of the results. The worker's local check uses that version, fetched once and checked against its published hash, in the scratchpad only, or states the difference as a limit (TASK-043's local check ran on the worker machine's node v24.11.1). Any other build-time tool keeps the rule above.
- No file written except standard output and standard error; no network, clock, environment variable, random value or process started; no reading of any path but its one argument.
- The code lives under `bench/<language>/` only (`bench/ts/`, `bench/go/`, `bench/rust/`); no file outside it. No part of AIEOS imports or runs anything under `bench/`; each port task's contract tests this (decision D-800 C3; the risk rules policy, rule R12).
- The same behaviour on Linux and Windows: the benchmark workflow runs the port on both and compares its output with the reference document by `tests/unit/test_export_reference.py --compare` (each port task adds its compare step under its own A66 decision; decision D-814 Q4).
- Its own tests, in its language, for at least: the byte-equality over the whole fixture document; one governor case and one Resume Check case checked field by field; the placeholder; each fail-closed input.
- The results are advisory and feed nothing (A29, A31); the port is disposable.

## 4. How a port is reviewed and counted

- Each port task gets five way-2 reviews from one review template, the same for every port, on a model other than the writer's, and the decision agent's separate review, as any task of its risk class (`bench/**` is high, R12; a task changing `.github/` is critical, R9).
- Findings are counted per task in one table form for criterion 6 (`docs/plan/m4-exit-review.md` §6), the third-party count is split into run-time packages and build-time tools (criterion 2), and the Windows check is the CI's (criterion 4).
- Limits stated with the results: the ports are written one after another, so the order is a bias; every writer and reviewer is an AI of one vendor; round 2 (the event log's append and recovery over a generated log) comes after round 1, and the stack ADR only after both rounds (decision D-794 Q1).

## 5. Revisions

- Revision 0: first text (decisions D-827 and D-829), written after TASK-041 rather than before it as decision D-794 Q6 ordered (a departure recorded in DEF-0063); no port had been written.
- Revision 1 (decision D-854): §2 states how every port treats the two unexpected-error paths of `resume_check.check`, as the TypeScript port (TASK-043) already does (decision D-849); written after that port and before the Go and Rust ports, so it changes no port already written; recorded as a limit of the results (DEF-0063).
- Revision 2 (decision D-855): §3 states that each language's own toolchain is the hosted runners' and is not pinned in the workflow, as the TypeScript port already ran on the runners' node (TASK-043), while any other build-time tool stays pinned; written before the Go and Rust ports, so it changes no port already written; recorded as a limit of the results (DEF-0063).
- Revision 3 (decision D-919): §6 adds round 2 (decision D-905; its export TASK-047, accepted and on `main` at `6b026569b4c62ec5d5b061138d8522d2ab651542`, decisions D-917 and D-918); §1 to §4 are unchanged for round 1, and the headers name both rounds; written before any round-2 port, so it changes no port already written; recorded as a limit of the results (DEF-0063).

## 6. Round 2: the event log's append and recovery over a generated log

**6.1 What it is.** Round 2 is `docs/plan/m4-exit-review.md` §6's "the event log's append and recovery over a generated log" (decision D-905): the two pure computations of the bootstrap, `eventlog.append` (TASK-007) and `recovery.reconcile` (TASK-009), with the record forms of `records.py` they use and `records.check_log`. Not the writer (files and SQLite) and not startup (it starts `git`), which §3 forbids a port to do; so no file behaviour is compared, a limit. The order of the round-2 ports is Rust, Go, TypeScript, the reverse of round 1, so the order bias does not fall on the same language twice (decision D-905); it stays a limit.

**6.2 Who writes it, and from what.** Each round-2 port is written by a fresh agent, as §1 says, given exactly these inputs, and nothing else:
1. this brief;
2. the Python source of the bootstrap at commit `6b026569b4c62ec5d5b061138d8522d2ab651542`, of these four files only, each checked by its SHA-256 before it is given:
   - `src/aieos_bootstrap/eventlog.py` (debee5c25e3113872a74ca8329e1a416a6440d718c1dbe2fbea78751571cdd4b);
   - `src/aieos_bootstrap/recovery.py` (60caf50bab4f5a66e48090f61f8e70c8c3b12bdda7e084b2a1ba2acdaa473f3d);
   - `src/aieos_bootstrap/records.py` (a85f74851e69979cdce5063c9522237704860c68a89b6f4a26801000c3fcd5b9);
   - `src/aieos_bootstrap/conformance.py` (70cce9106018f7b49ee608e7eb111708044aef6061c1c21ad5e6dad1cedfeacc);
3. the two round-2 documents, made at that commit: the input document, printed by `tests/unit/test_export_round2.py --input`, and the reference document, printed by `tests/unit/test_export_round2.py --reference <input document>`, with the source of that module (6fd0c9d2109344a131cf782135ef81a2a24d49d478dc07a955abb0e44b75f6bd) as the description of both forms; each document checked against its pin (`INPUT_SHA256`, `REFERENCE2_SHA256`) before it is given;
4. the port's own round-1 code under `bench/<language>/`, at that commit, which the round-2 code extends and reuses (its canonical text, its JSON reading, its SHA-256), and nothing of the other two ports;
5. the port task's contract.
- If a later task changes one of these files, the same rule as §1 applies (the round-2 pins change with it, TASK-047's contract).

**6.3 What a round-2 port does.**
- It adds to its package a second program, beside the round-1 program and separate from it, whose one argument is the path of the round-2 input document; the round-1 program, its argument rule and its tests stay as they are (a reading for each port task's contract: the round-1 program's fail-closed rule refuses an extra argument, so round 2 does not become a mode of it).
- It reads the input document and computes, exactly as the reference export does: for each append call in order, `eventlog.append` with the log carried from call to call (an `appended` result's new log becomes the next call's log; any other result leaves it), giving `{result, reason, findings, seq, line, record}`; for each reconcile case, `recovery.reconcile`, giving `{log, events, expired, findings}`; every bytes value as text and every datetime in the input's `YYYY-MM-DDTHH:MM:SSZ` text form, read as a UTC time.
- It prints to standard output one document byte-equal to the round-2 reference document: one object with the keys `append` and `reconcile`, in the canonical text of §2; there is no placeholder in round 2 (no record of it carries `engine_identity`).
- It computes every entry from the input document only; its code embeds no part of the reference document; only its own tests may read the reference document, as the expected output.
- It fails closed as §2 says (a missing or extra argument, a document not of the input document's form, a call it cannot compute: non-zero exit and nothing on standard output, the whole document built before the single write). Where the Python builds a text that names a Python type (`records.check_log`'s "the line is a JSON <type>, not an object", and the `TypeError` texts of `eventlog.append`, `recovery.reconcile` and `records.check_log` for an argument of the wrong type), the port fails closed instead; the generated input reaches none of these (the reference holds no such text), and the results state it as a limit, as §2 does for round 1.

**6.4 Rules for a round-2 port.** §3's rules hold unchanged, with these additions:
- SHA-256 (decision D-905 C4): each port uses the SHA-256 its round-1 code already has and adds none: Go the standard library's `crypto/sha256`; TypeScript its own `sha256Hex` in `bench/ts/bytes.ts`; Rust its own `bench/rust/src/sha256.rs`. No new third-party package and no new build-time tool.
- No clock: every time comes from the input document; `now` is the case's `now`.
- Its own tests, in its language, for at least: the byte-equality over the whole round-2 input; one append call and one reconcile case checked field by field; the carried log (an entry after an `appended` one and after a refused one); each fail-closed input; the round-1 tests still passing unchanged.
- The benchmark workflow runs the round-2 program on Linux and Windows after the round-2 export and compares its output with the round-2 reference by `tests/unit/test_export_reference.py --compare` (one object of lists, which `--compare` reads unchanged, TASK-047 AC2); each port task adds that step under its own A66 decision. Each port task also updates TASK-046's pins of its port (the file set, and for Rust `Cargo.lock` if it changes) as a pin update, not a loosening.

**6.5 Review and counting.** As §4, with the port review template unchanged; the round-2 findings are counted per task in the same table form, apart from round 1's.
