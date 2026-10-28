# M8 plan: self-hosting in v0.1

> - **Status:** advisory plan, revision 1. Decided by: decision agent (A41, A51), decision D-3334 (M8's start and this plan's frame) and the decision that approves this text. Not a specification and not a task contract; it changes no Master Plan line.
> - **Sources:** Master Plan §4 M8 (`docs/plan/master-plan.md` :82-85), §5 :95-96, §6 :104, §7 :108-113; `docs/plan/m7-exit-review.md` §3, §4; `docs/plan/stack-adr.md` §5, §6; `docs/pre-genesis/governor-spec.md` §2, §8; `docs/specs/risk-rules-gov-aieos.md` rules 2, 3, R2, R3, R9, R12; `.github/workflows/aieos-bench.yml` :112-131; `.github/workflows/aieos-checks.yml` :1657-1660; constitution INV-002; decisions D-2068, D-3336.

## 1. Task order

1. **The native governor, shadow** (TASK-099): a Go port of the acceptance decision of `governor.evaluate` (`src/aieos_bootstrap/governor.py` :413), traced to `governor-spec.md` §5 and §6.
2. **The native Resume Check, shadow**: a Go port of `resume_check.check` (`src/aieos_bootstrap/resume_check.py` :518), traced to specification 3.
3. Then the open links of section 7, each its own task.
4. **The native risk derivation, shadow**, after section 7's links: a Go port of the governor's `derive_inputs` (risk and evidence profile), traced to `risk-rules-gov-aieos.md` and `governor-spec.md` §3.2. Master Plan :84 names only the governor and the Resume Check as reaching shadow in v0.1; risk is next in the takeover order and is not needed for M8's exit (D-3336).
- The order is the Master Plan's (:84: "governor, Resume Check, risk"). The stateful writer stays in the bootstrap; it is not ported in v0.1 (:84).

## 2. What "shadow" means

- Each native port runs beside the bootstrap and **decides nothing**: it writes no record, feeds no record, and no acceptance reads it (Master Plan :84; `governor-spec.md` §2: a successor takes over only after conformance shows it equivalent or stricter, A11).
- Its check is byte-equal output against the bootstrap's over the frozen conformance fixtures (`tests/conformance/`), in CI, on Linux and Windows, as the benchmark did (`aieos-bench.yml` :112-131).
- TASK-099 runs over the fixtures only. Running the native governor on each acceptance's real records is not part of TASK-099 and would be its own later decision. D-2068's shadow, the bootstrap governor's evaluate beside the decision agent's decision at each acceptance, is unchanged.
- The Resume Check's shadow runs over the fixtures only until its inputs have a full source (D-2068; DEF-0100).

## 3. Where the code lives, and bench/go

- The code goes under a top-level `native/go/`, with its tests beside it, as Go's convention puts them.
- Before TASK-099's contract, a risk-rules revision v5 adds one rule, `native/**` high (proposed), as its own decision: today no rule matches that path (risk rules, rule 2: no class, no decision).
- Not under `src/`: the CI's deterministic_rule step fails on any file under `src/` or `tests/` that is not Python (`aieos-checks.yml` :1657-1660, the INV-002 file rule), and narrowing that rule is rejected (D-3336).
- `bench/go/` stays the benchmark's and is not changed or moved. A task may copy from it only into its own write-set, and the copy is reviewed as new code with the task's full reviews; nothing in `bench/go/` counts as accepted code.
- The contract tests that no part of the bootstrap imports or runs the native code, as D-800 C3 does for `bench/`.

## 4. Toolchain

- Go is the runners' own, with `GOTOOLCHAIN=local`, `GOPROXY=off`, `CGO_ENABLED=0` (`aieos-bench.yml` :115); standard library only, no module download.
- Nothing is installed on the owner's machine. The worker does not run Go locally; any wish to do so is an owner question first.

## 5. The workflow change

- The native ports need CI steps: build, vet, format check, run over the fixtures, byte-compare with the bootstrap's export, tests. That is a change under `.github/` (R9, critical), decided as its own decision under DM A66, with no write access, no secret and no token. It is named in TASK-099's contract; its text is not part of this plan.

## 6. Readings for the decision agent to rule

- **(i) Is the native shadow governor a "governor version"?** Proposed reading: no. A governor version is the one that emits acceptance decision records and is pinned by its content hash (`governor-spec.md` §2, §8 point 3), and D-166's owner acceptance covers the first one, which has "no base version to judge it" (Master Plan :95). A shadow port has the bootstrap as its base, emits none and is pinned as nothing, so D-166 does not apply to it. Who approves a native version's takeover of acceptance (successors are ratified, `governor-spec.md` §2) is decided before that stage, after v0.1; this plan does not decide it.
- **(ii) Is it "a change to the governor"?** Proposed reading: no, since it changes no file of the bootstrap governor and no input the governor reads (§8 point 1). The CI step that runs the port is under `.github/`, in the evaluator (R9, critical), and is its own A66 decision (section 5). The port's class comes from the `native/**` rule (section 3) and R3's governor tag: high; so, as for any high task of gov-AIEOS, its cross-model entry needs the pair of reviews (Master Plan :104; A59, A60). The plan sets no risk class and lowers none (CR-002 part 4 limit 8).
- Ruled by decision D-3336: (i) no; (ii) no.

## 7. The open links, in M8's order

- After task 2, each its own task, in this order: DEF-0105 (the reader of `.aieos/tasks`, import's root form, G2); DEF-0101 (the base-tip check, check 0, max_risk: needed before any runtime launch); DEF-0095 (the handoff file after a submission). DEF-0098, DEF-0100, DEF-0102, DEF-0104 and DEF-0106 are taken up when a task touches them.
- Owner acts, none scheduled here, each asked separately (A51 item (4)): a real runtime starter (`aieos launch`); connecting the MCP server to a runtime; real use of the commands; hooks and settings; any measurement.

## 8. The metrics of §7

- Concept §12's metrics (lines 810-821) are recorded from the event log from M8 on (Master Plan :111). Proposed: a read-only report over the event log, after section 7's links, as its own task; until then each task's acceptance record is the source. These are product metrics, not trust-boundary measurements (Master Plan :113).

## 9. M8's exit

- As Master Plan :85 says: the v0.1 goal measured as §7 says. The exit review follows M7's form (`docs/plan/m7-exit-review.md`), decided by the decision agent (A41, A51), the owner told in plain words.
