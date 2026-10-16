# DEF-0072: ADV-02's route to a conformance run

- Status: open
- Opened: 2026-10-16 (decision D-1056)
- Deferred by: decision agent (A41), D-1056 (ADV-02's route approved as the scope; its drafting carried to the next session).
- Decision group: A (a specification section and tasks within M5's approved plan).

## What
- **ADV-02** (Capability Boundaries; `docs/pre-genesis/conformance-scenarios-initial.md` line 64) is NOT_RUN: its set entry has no fixture. Specification 5 section 8 (line 81) plans a replay route: the fixture is written in the replay adapter's form, so ADV-02 can run in conformance without a live runtime; a passing ADV-02 then shows only the core's handling of a recorded observation, not that any hook observes anything.
- **The route, in RISK-01's three steps (D-429; DEF-0042):**
  1. Done: `docs/specs/conformance-files.md` revision 10, section 11 "The Capability Boundaries fixture and entry", approved as DM F48 and on main as 2049aeec (D-1063 to D-1066).
  2. Done: TASK-056, the runner's Capability Boundaries entry (an evaluator change, critical_cr). Contract on main as commit C 274d971e (D-1067 to D-1069); task commits 8b56c0e9, c1e0b243 (D-1076, D-1077) and 74df0b29, the review fixes M1, M2, M5 to M11, M15 and M16 (D-1079, D-1083); five way-2 reviews pass (D-1078); accepted, bound to 74df0b29, AC11 read by the decision agent (D-1084); on main as three rebuilt commits ending at c200a431 (CS-269). Carried as limits:
     - M3 and M4: the fence refusal's ids are not the writer's digests; the store stand-ins raise no ValueError on bad arguments (named in the docstrings).
     - M8: the module docstring states what the code does (a change in the number of lines the core appends before the second session shows as NOT_RUN at step 2); AC16's own sentence is wider than the code.
     - M12: test_runner_rc.py's kept assertNotIn still checks the run above it (the decision agent's ruling over R2, D-1079).
     - The AC4 write_set gap (moved to TASK-057, D-1085); AC3's counting reading and AC12's rc assertion form (D-1076); the stand-ins copy test code into the runner (AC16).
     - src/aieos_bootstrap/__init__.py's first sentence lists TASK-056 but not TASK-017 or TASK-051 to TASK-055 (D-1083).
  3. In progress, split by D-1085 as D-459 split RISK-01's step 3:
     - TASK-057, ADV-02's fixture (a fixture task, risk critical): contract revision 0 approved (D-1087) and on main as commit C 27f801c0 (CS-270, D-1088); no code yet. Its placeholders are the scenario set's acceptance defaults (risk low, functional [build, lint], G0 to G2; D-1086 (p2)); its tests are pure and never import or run the core (D-1086); it also checks the Given's condition that given.write_set equals the contract text's write_set.paths (D-1085), and M14 (commit_text against the commit table's text; refers_to against given.outside_path). The first task commit's request shows the tests' matcher agreeing with the governor's `matches` (D-1087).
     - TASK-058, the runner tests made to hold in both states of ADV-02's set entry (an implementation task): the 22 failing runner and governor-conformance tests of the scratch run (D-1085), classified first, no assertion weaker; and, moved here from the fixture task by D-1086 (amending D-1079's placement of M13), M13's control with the profile met (the same case without the violation, through the root's core: NEEDS_REVIEW / IN_REVIEW, no missing gate, no missing type) and the fixture's ADV-02 PASS through the root's core and the runner's entry over an in-memory set file.
     - TASK-059, the set file's ADV-02 entry with its freeze first (section 7, revision 5), and the 7 failing test_conformance_* tests; after TASK-057 and TASK-058.
- Rejected: a fixture in section 4's form (the When given, not run; it duplicates the governor's row 1) and deferring until a measured T3 runtime exists.
- Owner-kept acts: none; the T3 tier and C6 stay the owner's to measure.

## Resume when
- At the next session's start, after the definition check and the decision files D-1081 onward: TASK-057's code under its contract (27f801c0), then TASK-058 and TASK-059.

## Log
- 2026-10-16: opened (D-1056).
- 2026-10-17: step 1 done (revision 10 approved as DM F48, on main as 2049aeec; D-1063 to D-1066); step 2's contract, TASK-056, on main as commit C 274d971e (D-1067 to D-1069).
- 2026-10-17: TASK-056's task commits 8b56c0e9 and c1e0b243 on task/TASK-056 (D-1076, D-1077); five reviews pass (D-1078); dispositions M1 to M16, M13 and M14 carried to step 3 (D-1079).
- 2026-10-17: step 2 done: TASK-056's third task commit 74df0b29 (D-1083), accepted and on main as c200a431 (D-1084). Step 3 split into TASK-057 to TASK-059 (D-1085); M13's control moved to TASK-058 and the write_set check to TASK-057 (D-1085, D-1086); TASK-057's commit C on main as 27f801c0 (D-1087, D-1088).
