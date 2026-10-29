# DEF-0062: the review findings and limits carried from TASK-039, the stack benchmark's workflow and fixture export

- Status: open
- Opened: 2026-10-15 (decision D-782)
- Deferred by: decision agent (A41, A51), D-782 (TASK-039 accepted with every non-blocking review finding carried as a limit or a later change; dispositions F1 to F13) and D-784 (the first run read).
- Decision group: A (limits of the benchmark's workflow and export within the self-build); the removal of a branch on GitHub is the owner's.

## What
- **Limits of the export** (tests/unit/test_export_fixtures.py): F1, a file named exactly ".py" would be accepted with an empty stem (the folders are frozen, and the 31-entry test would fail); F2, NaN and Infinity are accepted by the parser and printed as bare tokens; F3, deep nesting raises RecursionError, failing closed with a traceback; F11, the default output path is not run by a test (exercised by the workflow's runs); F13, the naming test lists its classes by hand.
- **The workflow's wording** (.github/workflows/aieos-bench.yml), for its next change under DM A66: F4, the header names its source decisions only up to D-773's erratum E1; F7, "It reads only" is stronger than the file (the export writes into the job's temporary folder); F8, "for the owner only" states the agent's rule, not a GitHub restriction.
- **The toolchain step** fails the job if node, go or rustc is missing on a hosted runner; the first run had all three, with rustc 1.99.0 on Linux and 1.98.1 on Windows (a difference for the port tasks).
- **The ports** (bench/<language>/): `go run` and `cargo run` will write caches outside the workspace and the temporary folder; for the port contracts.
- **F5, a stale comment:** the comment above SET_CHECKS in tests/integration/test_conformance_risk_set.py still says "the three modules" over four entries; for the next task that touches that file.
- **The branch task/TASK-038** (7c6596a0, superseded, never accepted, CI run 255 failing G0 scope) stays on GitHub, unmerged; removing it is the owner's to decide (deleting refs on GitHub, A51 item (4)).

## Why deferred
D-782: every finding is non-blocking (five reviews passed, the decision agent's review passed); F1 and F2 cannot arise without a change to a frozen fixture folder, which needs its own task and freeze approval; the wording points belong to the workflow's next A66 change.

## Resume when
A task that touches the export module, the workflow, the risk set's test or a port; or the owner's word on the TASK-038 branch.

## Log
- 2026-10-15 (session d8eb2eb5): opened with TASK-039's acceptance (D-782) and its first run (D-784). ../History/2026-10/2026-10-15-0830-the-benchmark-workflow-accepted-and-on-main.md
- 2026-10-29: the workflow wording points F4, F7 and F8 are addressed by the benchmark workflow's revision 10 (decision D-3613, under DM A66), in the commit that changes .github/workflows/aieos-bench.yml (F4: the header names the decisions of revisions 6 to 9 and of revision 10; F7: "It does not change the repository"; F8: "for the owner only, by the agent's own rule and not a GitHub restriction", keeping the phrase tests/unit/test_export_fixtures.py :245 asserts); the export limits F1 to F3, F11 and F13, the toolchain step, the ports' caches, F5 and the branch task/TASK-038 remain; Status stays open.
