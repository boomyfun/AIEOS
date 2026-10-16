# DEF-0072: ADV-02's route to a conformance run

- Status: open
- Opened: 2026-10-16 (decision D-1056)
- Deferred by: decision agent (A41), D-1056 (ADV-02's route approved as the scope; its drafting carried to the next session).
- Decision group: A (a specification section and tasks within M5's approved plan).

## What
- **ADV-02** (Capability Boundaries; `docs/pre-genesis/conformance-scenarios-initial.md` line 64) is NOT_RUN: its set entry has no fixture. Specification 5 section 8 (line 81) plans a replay route: the fixture is written in the replay adapter's form, so ADV-02 can run in conformance without a live runtime; a passing ADV-02 then shows only the core's handling of a recorded observation, not that any hook observes anything.
- **The route, in RISK-01's three steps (D-429; DEF-0042):**
  1. Done: `docs/specs/conformance-files.md` revision 10, section 11 "The Capability Boundaries fixture and entry", approved as DM F48 and on main as 2049aeec (D-1063 to D-1066).
  2. In progress: TASK-056, the runner's Capability Boundaries entry (an evaluator change, critical_cr); its contract on main as commit C 274d971e (D-1067 to D-1069). Two task commits on task/TASK-056: 8b56c0e9 (the entry and its tests, D-1076) and c1e0b243 (a bandit B105 false positive in a test removed without suppressing the check, D-1077; CI run 350 passing). Five way-2 reviews on claude-sonnet-5-5, all pass, no blocking finding (D-1078). Dispositions (D-1079), to be done as a third task commit, read by the decision agent (D-244), then the acceptance:
     - M1: _CbStore.grant_lease refuses expires_at not after now and answers a held lease with reason "held", as writer.py does.
     - M2: _CbStore.end_session releases the session's leases, as writer.py does.
     - M3 and M4 (no change, stated as limits in the docstring): the fence refusal's ids are not the writer's digests; the store stand-ins raise no ValueError on bad arguments.
     - M5: the signature test binds each stand-in with inspect.signature(real).bind on the arguments the core passes (AC5's wording).
     - M6: the docstrings say "a reduced copy of the writer's rules", name M3 and M4, drop "as the writer appends it"; __init__.py's first sentence names TASK-056.
     - M7: the module docstring's limits gain AC16's sentence that the in-memory integration test's PASS tests the runner, not the core's conformance, and the write_set gap; check_cb_fixture's docstring names that gap.
     - M8: "a core change that adds a line shows as NOT_RUN" narrowed to what the code does (a change in the number of lines appended before the second session shows as NOT_RUN at step 2); the acceptance request notes the difference from AC16's wording.
     - M9: more R3 cases (the submitted commit absent and twice, a missing task.approved, a later task.approved whose hash differs after a matching one, a row_hash mismatch alone, a non-string commit text, a malformed now); the malformed reason asserted.
     - M10: R7 with REJECT and a wrong next state, and the reverse; R8 shows a step-2 NOT_RUN stops evaluate_task.
     - M11: a run-level test of AC3's counting reading and of the lazy load (no Capability Boundaries fixture, load_cb not called).
     - M12 (no change): test_runner_rc.py's kept assertNotIn still checks the run above it (the decision agent's ruling over R2); stated in the acceptance request.
     - M15: the integration test's docstring says the run does not count because a stand-in is used; the R3 and R6 docstrings claim only what their tests assert.
     - M16: a property test that two runs over the same in-memory files give equal run-record values.
     - The acceptance request also carries AC11's method as an erratum or reading (D-1076 C5): the base runner over its own tree, whose run inputs equal the head's but for the runner's hash, the two run records byte-equal after a placeholder.
  3. A task: ADV-02's fixture and the set file's entry, the set file frozen before the task (conformance-files.md section 7, revision 5), possibly split as D-459 split RISK-01's step 3; test_conformance_files.py's guard that the set file names no ADV-02 fixture is that task's to change. Carried into it by D-1079:
     - M13: a control, run by a test: the same case with the violation removed must not give REJECT from the root's core, so that the fixture's placeholders (every evidence type passing, auto_accept false, delegation true, evidence_comparison not weakening) are shown to hold and a core that ignores the violation cannot pass by a missing-evidence REJECT (R2's finding).
     - M14: the fixture's consistency checked by the fixture task: continuation.submission.commit_text equal to the commit table's text, and the observation's refers_to equal to given.outside_path.
- Rejected: a fixture in section 4's form (the When given, not run; it duplicates the governor's row 1) and deferring until a measured T3 runtime exists.
- Owner-kept acts: none; the T3 tier and C6 stay the owner's to measure.

## Resume when
- At the next session's start, after the definition check and the decision files D-1071 onward: TASK-056's third task commit with M1, M2, M5 to M11, M15 and M16, then the acceptance.

## Log
- 2026-10-16: opened (D-1056).
- 2026-10-17: step 1 done (revision 10 approved as DM F48, on main as 2049aeec; D-1063 to D-1066); step 2's contract, TASK-056, on main as commit C 274d971e (D-1067 to D-1069).
- 2026-10-17: TASK-056's task commits 8b56c0e9 and c1e0b243 on task/TASK-056 (D-1076, D-1077); five reviews pass (D-1078); dispositions M1 to M16, M13 and M14 carried to step 3 (D-1079).
