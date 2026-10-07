# AIEOS Conformance Methodology

> **Status: PRE-GENESIS DRAFT — proposed, not ratified.** A14 step 7 (DM A50: "cách thử và bộ bài thử"). Every rule here is a proposal unless it cites a DECIDED row of `decision-matrix.md` (DM, section A), the concept, CR-001 or CR-002 as approved; B-rows and the assurance, Genesis and constitution documents are cited as proposed. Nothing here is a Genesis fact.
> Revision 2 — 2026-10-07 (revision 1, same day: first version). Revision 2 carries CR-002 (A52) for gov-AIEOS, the self-build (A53 names): scenario approval (sections 1, 5 and 10), the sources a scenario may cite (section 2), and the carry-overs of revision 1 (sections 8 and 11) (working record DEF-0020). Written under decisions of the decision agent (A41; scope set in decision files D-078 and D-098); not an owner decision. Normative concept: `AIEOS-concept.md` v0.5 with CR-001 and CR-002 (A22, A52). Rows are cited by ID, concept text by line ("concept line N"), CR-002 by part, entry or limit.
> Effect: every result of a conformance run is **advisory** until measured (DM label rule "Anything unmeasured defaults to advisory"), and C13 is FAIL by implication (A29; section 9).

## 1. Principle

- The primitive is A19 (DECIDED): `Frozen Scenario → Runner → Observed Result → Expected Semantic Result → Pass/Fail`, with its five conditions. A19 calls it the "main mechanism against circular self-validation"; its sufficiency is subject to C13.
- The concept never mentions scenarios or a conformance oracle; "spec conformance" appears only as a gate example (concept line 302) and a V3 item (line 718). This methodology is added by the DM (A11, A12, A19), not by the concept.
- For the self-build, A51 quotes Claude's question, which stated this cost: "mọi lớp kiểm tra, kể cả bộ bài thử (cách chính để AI không tự chấm bài mình) và agent quyết định, đều do AI của cùng một hãng làm; nếu AI hiểu sai ngay từ đầu thì không còn ai ngoài AI phát hiện"; the owner answered "b". For gov-AIEOS, CR-002 part 6 has the decision agent approve the scenarios in the owner's place (section 5); so the same AI approves the scenarios and the rules on what must be reviewed, writes the reviews and approves the tasks (CR-002 part 4, "Cái giá").
- The owner decided the bound set, which includes the conformance methodology and the initial scenario-set hash (A49; genesis-model.md §3 row 6, proposed). The set itself is `conformance-scenarios-initial.md`.

## 2. The scenario model (proposed)

| Field | Meaning |
|---|---|
| `id` | Stable identifier; never reused. |
| `capability` | The capability tested, named after the concept's capability list (lines 39-41); compatibility is evaluated per capability (B10, proposed; A11). |
| `covers` | A decision-table row, a lifecycle transition, an evidence rule or an adversarial case (B14, proposed, names the first, second and fourth; evidence rules are Claude's addition). |
| `given` | The project state before the event, in concept terms. |
| `when` | The event or evaluation. |
| `expected` | The expected semantic result, in concept and DM terms. Required: the decision value, or the set of values the sources allow, with the open choice named. Also, where the sources fix them: the missing dimension and evidence type, the next task state, and the records written. An element the sources do not fix is marked "not fixed". |
| `source` | The concept lines, DECIDED rows, CR-001 entries or, for gov-AIEOS only, CR-002 parts and entries that fix the expected result. A scenario whose result they do not fix is not written. |

- Expected results never use names that a later specification defines, such as reason codes (proposed, from the purpose of A19: no specification should fit the scenarios to itself).
- Executable fixtures (repositories, commits, records) are written from step 9 (A14); each records which scenario it realises.

## 3. Comparing observed and expected results (proposed)

- The comparison is semantic, on the decision, the task state and the records written; never on wording. The decision follows the decision contract of A15.
- A run passes a scenario only if every fixed element is observed and no decision outside the expected set is emitted.
- A scenario that cannot be run (missing fixture, runner error) is `NOT_RUN`, never a pass.

## 4. Freezing and hashing

- Scenarios are hashed (A19 (2)). Proposed: a set is frozen as one file in a canonical form (UTF-8; LF line ends, as B8, proposed, gives `eol=lf`), identified by its SHA-256 and a set version.
- A run records the set hash, the runner and its version (A19 (3)), and the commit under evaluation.

## 5. Approval

- A19 (1) (DECIDED): the owner approves each scenario. For gov-AIEOS, CR-002 part 6 settles who approves: a scenario's expected result states what AIEOS must do, as an acceptance criterion of a Spec does (concept line 404), and Intent changes only through a change request approved by a human (concept line 409); with CR-002 Đ6, for gov-AIEOS that approver is the decision agent, so it approves each scenario in the owner's place, each approval bound to that scenario's content, within CR-002 parts 4 and 8. A19 (2)-(5) are unchanged (CR-002 part 6). This closes the reading of revision 1 (decision file D-078), under which scenario approval waited for CR-002.
- Each such approval is a delegated approval: recorded "decided by: decision agent (A41, A51)", with advisory effect, relayed to the owner in plain words, and shown as resting on an AI approval (CR-002 part 1). It is given only while the delegation is in force; after the owner revokes it, approvals already given stay (CR-002 part 1, "Giới hạn").
- Proposed: removing or re-expecting a scenario (B10) so that a record counts, or a task is accepted, where its approved version does not (for an unapproved draft: where the latest version on GitHub does not), or removing a scenario whose expected result is that a record does not count or a task is not accepted, weakens evidence requirements and is the owner's (CR-002 part 4 limit 8). Whether approving scenarios added to carry out CR-002, such as ACC-14 and ACC-15, falls under this limit is open (section 10, point 5).
- Proposed: each approval is bound to one scenario's content hash, as A42 binds a task approval to its content.
- Until approved, no acceptance may rest on the set.

## 6. Runner and where it runs (proposed)

- The runner and its version are pinned (A19 (3)). The bootstrap runner is part of the bootstrap implementation (A9).
- Only a run in a channel with sufficient authority may be used for acceptance (A19 (5)). By analogy with where V0+V1 run (assurance-model.md §7, option 1, proposed): external CI on the evaluated commit. Local runs may block but satisfy nothing.
- Creating the CI channel touches `.github/`, which stays with the owner (A51 item (4)).

## 7. Isolation (proposed)

- An implementation task cannot modify scenarios to make its tests pass (A19 (4)); constitution.md GOV-002 (proposed) makes it a path rule.
- The candidate controls are those of B17 (proposed, not claimed sufficient), with its revision-21 note for the self-build.

## 8. Change classes

- B10 (proposed) gives the change classes of scenarios, with B1 (proposed). The initial set is in the bound set (A49), to be bound at step 8; later scenarios are ratified, not bound (B2, proposed).

## 9. Coverage, succession and the trust boundary

- Coverage is reported per capability, with what is not covered listed (concept line 65); the exit tiers are B14's (proposed).
- Succession and runtime neutrality rest on conformance (A11, A12).
- While P-CRED is FAIL and C13 is FAIL by implication, a pass is advisory: the CI job that runs it executes agent-modified code and is inside the agent's authority domain (A29; assurance-model.md §9, proposed).

## 10. Open points

1. Closed in revision 2: for gov-AIEOS, the decision agent approves each scenario in the owner's place (CR-002 part 6; section 5).
2. Expected results the sources leave open (REJECT or NEEDS_REWORK for a change outside the write-set; the next state after stale evidence); the §18 specs are not scheduled (working record DEF-0011).
3. The adversarial catalogue and the rest of the B14 minimum tier.
4. The canonical form's details and the fixture format (step 9).
5. Whether the decision agent's approval of scenarios added to carry out CR-002 (ACC-14, ACC-15) is within the owner's approval of CR-002 or falls under CR-002 part 4 limit 8; until the owner answers, such approvals are the owner's (fail closed).

## 11. Not covered

- The runner, the fixtures and the CI workflow (step 9; `.github/` is the owner's).
- C13 control design (B17, proposed); measurements (A46).
- The decision contract's fields (A15; the acceptance part is specified in `governor-spec.md`, proposed; field names at step 9).
