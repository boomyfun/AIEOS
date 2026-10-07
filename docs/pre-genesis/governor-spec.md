# AIEOS Bootstrap Governor Specification

> **Status: PRE-GENESIS DRAFT — proposed, not ratified.** A14 step 7 (DM A50: the owner's "phần lõi chấm việc", and "đồng ý, chỉ viết mô tả chi tiết"). Every rule here is a proposal unless it cites a DECIDED row of `decision-matrix.md` (DM, section A), the concept, or CR-001; B-rows and the assurance, Genesis, constitution and conformance documents are cited as proposed. Nothing here is a Genesis fact. This is a specification only: no code exists before step 9 (A14).
> Revision 1 — 2026-10-07: first version. Written under decisions of the decision agent (A41; scope set in decision file D-078); not an owner decision. Normative concept: `AIEOS-concept.md` v0.5 with CR-001 (A22). Rows are cited by ID, concept text by line ("concept line N").
> Effect: until measured, every decision the governor emits is **advisory** (DM label rule "Anything unmeasured defaults to advisory"; section 10).
> Form: numbered rules, decision tables and field tables only; no executable code and no pseudo-code.

## 1. Purpose and scope

- The bootstrap governor is the part of the bootstrap implementation that evaluates acceptance while AIEOS governs its own build (genesis-model.md §3.3, proposed; item 7 of the bound set, A49).
- In scope: the **acceptance decision** of concept §5.3 (lines 295-303, line 300 as corrected by CR-001 E8), in the order of A36; its inputs, its records and its own change control.
- Out of scope: execution decisions and the Resume Check (concept §7.2, lines 485-506; §18 spec 3); producing evidence, which AIEOS, CI, tools and humans do, never the agent (concept line 729; where V0+V1 run: assurance-model.md §7, option 1, proposed); reconciliation (§10); planning.
- Boundary with the Resume Check: the governor evaluates a task in VERIFYING (concept line 521), or re-evaluates one in IN_REVIEW (assurance-model.md §3, proposed). It never emits an execution decision. Reading A15 (the decision contract bootstrap and native emit alike) together with A36 ("the acceptance part of concept §5.3, which A15 keeps"), both kinds of decision belong to one contract; this is a reading.
- Overlap: this specification covers the acceptance table and parts of §18 spec 4 (evidence profile, independence rule; concept line 994). The §18 specs are not scheduled (working record DEF-0011).

## 2. Status, identity and succession

- It is bootstrap implementation: Python 3, standard library only, disposable (A9; constitution articles INV-002, INV-003, proposed).
- It is part of the evaluator (A29: the evaluator includes the governor).
- Identity: the content hash of its pinned version (genesis-model.md §3.3, proposed). Every decision record carries it (section 6).
- Succession: per capability; a native successor takes over acceptance only when conformance shows it equivalent to or stricter than the bootstrap (A11). The succession rule is in the bound set (A49), to be bound at step 8; successors are ratified, not bound (B2, proposed).

## 3. Inputs

### 3.1 Evaluation request

| Field | Meaning | Source |
|---|---|---|
| task id | the task evaluated | concept line 430 |
| task content hash | the hash of the task contract together with the evaluated commit; approvals bind to it (proposed) | A42 |
| evaluated commit | the commit SHA under evaluation | concept lines 664, 667, 728 |
| intent versions | the current version of every intent entity the task traces to | concept lines 432, 437, 728 |
| task state | VERIFYING, or IN_REVIEW for re-evaluation | concept lines 521-524 |
| changed paths | the paths the change touches | concept lines 394, 715 |
| retry count | the task's retries used and its limit | concept lines 463, 526 |

### 3.2 From the task contract, the requirements, the policy and the constitution

| Field | Meaning | Source |
|---|---|---|
| traces_to | the requirements and specs the task serves | concept line 432 |
| risk | the highest risk the policy's risk rules give for the changed paths; a lower risk declared in the contract is not used (proposed) | concept lines 592, 595-602, 868; A35 |
| verification plan | the gates that must pass; G0 scope (V0) is always one of them (proposed) | concept lines 465-466, 469, 715 |
| evidence profile | per dimension, the evidence types required: the risk default, with the differences each traced requirement declares; for several requirements, the union of their entries (proposed) | concept lines 676-685, 697-704 |
| applicable articles | the constitution articles whose scope meets the changed paths; their `evidence_required` joins the profile (proposed) | concept lines 347, 360, 367, 389-395 |
| policy version, level version | the approved policy in force and the version of the risk class's level | A35 |
| auto-accept | whether the policy explicitly allows auto-accept for that class | A35, A36 |
| ruleset version | the governor's pinned rules | B5 (proposed) |

- v0.1 has default profiles for low and medium risk only (concept line 947); the high and critical profiles come in v0.2 (concept line 954). Until assurance-model.md §10 point 1 is settled, a high or critical task gets no decision (section 4, rule 7; proposed).

### 3.3 Records

Each record the governor reads has these fields (B5, proposed; assurance-model.md §4, proposed):

| Field | Meaning |
|---|---|
| record id | unique, idempotent (concept line 856) |
| fact_kind | claim, observation, interpretation or authority (B5) |
| source_class | one of the B3 classes (proposed) |
| recorder | who or what wrote it |
| subject | the task id |
| evidence type and dimension | for an observation, what it proves (concept lines 681-684); for a gate result, the gate |
| outcome | pass or fail; or blocking, with its kind: out of scope, forbidden path, violation, constitution, other |
| commit and intent version | what an evidence record or gate result is bound to (concept line 728) |
| approval binding | for an authority record, the task content hash it approves (A42) |

## 4. Input rules

1. Inputs are read from the base or a pinned ref, never from the change under evaluation. B17 (1) (proposed) says this of the evaluator and scenarios; extending it to every input is this specification's proposal (constitution GOV-003, proposed).
2. An evidence record or gate result counts only if it is bound to the evaluated commit and to the current version of every intent entity it concerns. Otherwise it is stale, satisfies nothing, and the decision record requests its re-verify (section 6.1) (concept lines 270, 504, 667-669, 728).
3. A record satisfies an evidence entry only if its outcome is pass, its evidence type and dimension match the entry, and its source class may satisfy it (B3, proposed). Records from `agent_declared` never do (A18; concept line 706); an AI review by the implementer's model never counts for a dimension that requires review (concept line 706).
4. Any record of any class may block (A17; B3, proposed). Rules 2 and 6 do not silence blocking records: a violation record of the task's session, or a blocking record that cannot be bound, keeps blocking (concept line 269; proposed).
5. An approval record is never evidence: it satisfies no evidence entry (A36: "human approval is an authority act"; B3, proposed). It counts only if it is an `authority` record from `human_authority` bound to the task's current content hash (A42); rule 2 does not apply to it.
6. A record that is malformed, or an evidence record that lacks its binding, is not used, and is listed as uncovered (section 6.2).
7. A request with a missing or malformed field gets no decision value: the governor writes a decision record carrying the error (section 6.1), and the task stays where it is.
8. A change that matches no risk rule is never classified low (A35). Until its profile is settled (section 11), it gets no decision value (rule 7; proposed).

## 5. Evaluation

The first row that applies decides, in the A36 order.

| # | Condition | Decision | Next task state | Source |
|---|---|---|---|---|
| 1 | a blocking record of kind out of scope, forbidden path or violation | REJECT (proposed; open, section 11) | REJECTED | concept lines 102, 199, 269, 303, 527, 715 |
| 2 | another blocking record; a gate result that failed; or a failed record for a required evidence type (proposed) | NEEDS_REWORK | REWORK; ESCALATED after the retry limit | concept lines 302, 525-526; A36 |
| 3 | a gate of the plan has no current passing result, or an evidence type of the profile has no satisfying record (rules 2-3) | INSUFFICIENT_EVIDENCE, naming each missing gate (proposed), dimension and type | see the routing table | concept lines 301, 469, 687-695; A36 |
| 4 | every gate passed and the profile is complete, and the policy explicitly allows auto-accept for the risk class at L2 or above, within concept line 622 | ACCEPT | ACCEPTED | concept line 299; A35; A36 |
| 5 | every gate passed and the profile is complete, otherwise | NEEDS_REVIEW | IN_REVIEW | concept line 300 with CR-001 E8; A35 |

- Row 1 follows concept lines 199 ("diff ngoài scope → luôn reject") and 303; a G0 scope failure is recorded as a blocking record of kind out of scope (proposed). Whether every such change is a REJECT is open (section 11).
- Row 4 can never apply to the AIEOS self-build, which stays at L1 (A35). Its "sufficient assurance" is open, and assurance-model.md §6 (proposed) makes auto-accept inexpressible while C13 is not PASS.

Routing after INSUFFICIENT_EVIDENCE (a human-only type is an entry that names only `human_authority`; B3, B4, proposed):

| Missing | Next task state | Source |
|---|---|---|
| only human-only types | IN_REVIEW | A36; CR-001 E8 |
| no human-only type, or both kinds | REWORK first; ESCALATED after the retry limit | concept lines 525-526; assurance-model.md §3 (proposed) |

- The retry limit is the task contract's retries budget (concept line 463). The governor reads the count; counting returns from REWORK to IN_PROGRESS is outside it (proposed).

Leaving IN_REVIEW (re-evaluation when an approval record or a new record for the task is written; proposed):

1. The governor re-evaluates rows 1-3 at the evaluated commit. If one applies, it decides.
2. Otherwise the decision stays NEEDS_REVIEW. If an approval record counts (section 4, rule 5), the decision record cites it and the next state is ACCEPTED, as the effect of that authority act (A35, A36, A42; concept lines 523-524; assurance-model.md §3, proposed). If none counts, the task stays IN_REVIEW.
3. In a batch approval, each task needs its own approval record (A42).
4. For the self-build under A51, whether a decision of the decision agent can be the approval record, with which source class and which effect, is open until CR-002 and a later assurance-model revision (A51 item (5); assurance-model.md §2 says it never replaces a human approval record, proposed). Until then, the human approval record of A35 and A36 stays required.

## 6. Outputs

### 6.1 The decision record

An `interpretation` record (B5, proposed) with these fields; it is the acceptance part of the A15 decision contract, whose field names are fixed at step 9:

| Field | Meaning |
|---|---|
| decision | one of ACCEPT, NEEDS_REVIEW, INSUFFICIENT_EVIDENCE, NEEDS_REWORK, REJECT (concept lines 299-303), or none with an error (section 4, rule 7) |
| next task state | as section 5 |
| task id, task content hash | what was evaluated (A42) |
| evaluated commit, intent versions | what it is bound to (concept line 728) |
| table row | the section 5 row that decided |
| profile used | per dimension: the required types, the satisfying record ids, and the missing types and gates |
| blocking and failed | the blocking record ids and the failed gates |
| re-verify | the stale record ids whose re-verify is requested (section 4, rule 2) |
| approval record | for IN_REVIEW → ACCEPTED, the approval record id |
| policy version, level version | as section 3.2 (A35) |
| governor identity, ruleset version | section 2 |
| scenario-set hash | the conformance set this governor version was run against (this specification's proposal) |
| uncovered | section 6.2 |

### 6.2 What is not covered

- Each decision lists what it did not cover: unused records (section 4, rule 6), `judgment` articles without review, and advisory-only inputs (concept line 65: always show what is not covered).

### 6.3 Recomputability

- The same request, records, policy version and governor identity always give the same decision; any decision can be recomputed by replay (constitution INV-010, proposed; assurance-model.md §4, proposed).

## 7. Where it runs

- For acceptance, the pinned governor, taken from the base, runs in external CI for the evaluated commit, by analogy with where V0+V1 run (assurance-model.md §7, option 1, proposed). A local run's decision is advisory: it may add a blocking outcome, and never moves a task to IN_REVIEW or ACCEPTED (proposed).
- Creating the CI channel touches `.github/`, which stays with the owner (A51 item (4)).
- It writes only its decision records, through the core's single writer (concept line 858).

## 8. Change control of the governor

1. A change to the governor is a change to the evaluator (A29). It is never judged by the version it changes: the base version judges it (section 4, rule 1).
2. Until its identity is bound at step 8, its class is `critical_cr` (B1, proposed: "enforcement or authority changes that are not bound"); after that, a `genesis_amendment` (genesis-model.md §5, proposed).
3. Proposed: every new version runs the whole frozen scenario set first (A19; `conformance-methodology.md` §4, proposed), and is pinned by its content hash.
4. Reading the governor as the "acceptance verifier" of assurance-model.md §6 (A29 lists the two separately), a change to it is never auto-accepted (proposed).

## 9. What it does not do

- It calls no model and writes no code (concept line 162; constitution INV-001, proposed).
- It runs no test or checker; it reads their records.
- It emits no execution decision, changes no record it reads, and changes no policy or level.

## 10. Relation to the trust boundary

- The minimal P-CRED baseline is FAIL, so C13 is FAIL by implication (DM sections C, D). Every decision the governor emits is advisory, and the CI job that runs it executes agent-modified code (A29; assurance-model.md §9, proposed).
- For the self-build under A51, A29 cannot hold by design and stays a target (A51 item (7)).

## 11. Open points

1. Whether the governor also emits execution decisions (genesis-model.md §3.3, proposed; proposed here: no).
2. The source class and effect of a delegated approval record under A51 (section 5; CR-002; a later assurance-model revision).
3. The open owner points of assurance-model.md §10, cited and not resolved here: point 1 (the high and critical profiles and CR-001 E10); point 2 in full (raising a class to L2, bounds above L2, "sufficient assurance", L2 while P-CRED or C13 is not PASS, and the auto-accept policy's approver); point 3 (a CR-001 entry for where V0+V1 run); point 4 (departures from the risk default).
4. The profile for a change that matches no risk rule (section 4, rule 8), and how the profiles of several traced requirements combine (section 3.2).
5. Whether every change outside the write-set is a REJECT (section 5, row 1).
6. The next state after stale evidence (REWORK here; `conformance-methodology.md` §10 point 2).
7. Acceptance against an unbaselined spec (B9, proposed; assurance-model.md §3) and the re-verify of a DONE task with stale evidence (concept lines 504, 530).
8. The field names of the decision contract (step 9).

## 12. Not covered

- Code, the CI workflow and the fixtures (step 9; `.github/` is the owner's).
- The Resume Check and execution decisions (§18 spec 3).
- C13 control design (B17, proposed); measurements (A46).
