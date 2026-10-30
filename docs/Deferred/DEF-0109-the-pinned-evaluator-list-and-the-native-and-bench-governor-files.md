# DEF-0109: the pinned evaluator list lacks the native, bench and Go governor and lockfile forms

- Status: open
- Opened: 2026-10-30 (session 1c1bf794; TASK-102's article reviews RG and RG2, decisions D-3705, D-3707)
- Deferred by: decision agent (A41, A51), at TASK-102's acceptance
- Decision group: A

## What
The list of evaluator paths in `.github/workflows/aieos-checks.yml` (:429-436, and a second identical copy at :496-503) names the Python governor tree, the tests, the workflows and several lockfile forms. DM row A29 names the governor, the dependencies and lockfiles and the acceptance verifier as evaluator inputs. The list does not cover the governor files of `native/` and `bench/` (for example `native/go/governor/*.go`, `bench/go/governor.go`, `bench/rust/src/governor.rs`, `bench/ts/governor.ts`) or the forms `go.mod`, `Cargo.lock` and `tsconfig.json` of those trees. The list is also copied in two steps with no check that the copies match. TASK-102 touches none of these files; it is a gap in the rule, not in the task. Whether the native and bench governor files are "the governor" in A29's sense is a reading to settle.

## Why deferred
A change of the workflow's list is a change under `.github/`, which needs its own decision under A66 (DM), and the reading of A29 is for the decision agent's or the owner's later decision.

## Resume when
The next change of the workflow's list of evaluator paths, or when DEF-0107 is taken up.

## Depends on
DEF-0107.

## Log
- 2026-10-30: opened at TASK-102's acceptance (session 1c1bf794).
- 2026-10-30: named in point 7 of DEF-0107's stated policy (D-3740) as part of the next build task, with the CI step; until that task settles the reading, the native, bench and Go governor files are handled as evaluator paths (a handling rule, not a reading of A29); a reading that leaves any of them outside A29's evaluator goes to the owner.
