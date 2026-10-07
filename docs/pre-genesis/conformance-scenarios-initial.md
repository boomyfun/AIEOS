# AIEOS Initial Conformance Scenario Set

> **Status: PRE-GENESIS DRAFT — proposed, not approved.** A14 step 7 (DM A50: "cách thử và bộ bài thử"). Set version 0 (draft). No scenario here is approved; for gov-AIEOS, the decision agent approves each scenario in the owner's place, bound to its content (CR-002 part 6; `conformance-methodology.md` §5, proposed). Nothing here is a Genesis fact.
> Revision 3 — 2026-10-08 (revision 1, 2026-10-07: first version; revision 2, 2026-10-07). Revision 2 adds ACC-14 and ACC-15, two scenarios for gov-AIEOS, the self-build (A53 names), under CR-002 (A52), and updates sections 1 and 6 (working record DEF-0020). Revision 3 updates the last paragraph of section 6 for the owner's answers of 2026-10-07 (A54); no scenario changes (working record DEF-0021). Written under decisions of the decision agent (A41; scope set in decision files D-078, D-098 and D-109); not an owner decision. Normative concept: `AIEOS-concept.md` v0.5 with CR-001 and CR-002 (A22, A52). Concept text is cited by line ("line N"), rows by ID, CR-002 by part, entry or limit.
> Effect: every run of these scenarios is **advisory** until measured (DM label rule; `conformance-methodology.md` §9).

## 1. Scope

- Only behaviour that the concept, DECIDED rows or CR-001 fix (and, for ACC-14 and ACC-15 only, CR-002). The set tests the product rules (A35, the product default A51 item (1) leaves unchanged), except ACC-14 and ACC-15, which test the gov-AIEOS variant that CR-002 sets (A51; A52).
- Format: `conformance-methodology.md` §2 (proposed). Capability tags (proposed) follow the concept's capability list (lines 39-41): Verification (acceptance decisions), Resume Check, Risk Engine, Capability Boundaries.
- Acceptance defaults, unless a scenario says otherwise: the task is in VERIFYING; risk low, so the default profile is functional [build, lint] (line 701); the verification plan is G0 scope, G1 build, G2 lint, and all three passed on the evaluated commit; for each type of the profile, a record from external CI exists, bound to the evaluated commit and to the intent versions the task names, which are current (line 728); the risk class is at L1 (A35); approvals are human approval records (A36).
- gov-AIEOS defaults (ACC-14, ACC-15): the project is gov-AIEOS (A53); the A41 delegation, as widened by A51, is in force; the task carries out or changes no act that A51 item (4) keeps (CR-002 part 4 limit 5), and its change weakens no evidence requirement (CR-002 part 4 limit 8); approvals are the decision agent's delegated approvals (A51 (2); CR-002 Đ5).
- Resume Check defaults: the task is READY or IN_PROGRESS; HEAD equals `base_commit`; dependencies DONE; intent versions current; the runtime's `max_risk` at or above the task's risk; budget left; no applicable constitution article violated (lines 493-502).

## 2. Verification: acceptance decisions

| ID | Covers | Given | When | Expected | Source |
|---|---|---|---|---|---|
| ACC-01 | row NEEDS_REVIEW | defaults | acceptance is evaluated | NEEDS_REVIEW; next state IN_REVIEW | line 300 with CR-001 E8; line 524; A35 |
| ACC-02 | rule: no auto-accept at L1 | defaults; the policy names auto-accept for the class, which is at L1 | acceptance is evaluated | NEEDS_REVIEW; next state IN_REVIEW | A35; CR-001 E7 |
| ACC-03 | row NEEDS_REWORK | defaults, but G1 failed | acceptance is evaluated | NEEDS_REWORK; next state REWORK | lines 302, 525-526; A36 |
| ACC-04 | rule: A36 order | defaults, but G1 failed and the requirement adds security [static_security_analysis], with no such record | acceptance is evaluated | NEEDS_REWORK; next state REWORK | A36; lines 302, 697 |
| ACC-05 | row INSUFFICIENT_EVIDENCE | defaults, but the requirement adds security [static_security_analysis], with no such record | acceptance is evaluated | INSUFFICIENT_EVIDENCE: security, static_security_analysis missing; next state REWORK | lines 301, 525, 687-695, 697; A36 |
| ACC-06 | transition to IN_REVIEW | defaults, but the requirement adds operational [human_review], with no such record | acceptance is evaluated | INSUFFICIENT_EVIDENCE: operational, human_review missing; next state IN_REVIEW, not REWORK | A36; CR-001 E8; lines 310, 697 |
| ACC-07 | rule: stale by commit | as ACC-05, but a static_security_analysis record exists, bound to an earlier commit | acceptance is evaluated | the record does not count; INSUFFICIENT_EVIDENCE: security, static_security_analysis missing; a re-verify is scheduled; next state not fixed (REWORK, line 525, or re-verify, lines 270, 504) | lines 270, 504, 667, 728 |
| ACC-08 | rule: stale by intent | as ACC-07, but the record is bound to the evaluated commit and to an earlier version of a spec whose current version the task names | acceptance is evaluated | as ACC-07 | lines 504, 669, 728 |
| ACC-09 | rule: an agent's word | defaults, but the requirement adds functional [unit_test], and the only report of unit tests is the agent's "tests pass" | acceptance is evaluated | the report is an observation of the claim and authorizes nothing; INSUFFICIENT_EVIDENCE: functional, unit_test missing; next state REWORK | A18; lines 101, 525, 706 |
| ACC-10 | rule: same-model review | defaults, but the requirement adds architecture [ai_review], and the only review was made by the implementer's model | acceptance is evaluated | the review does not count; INSUFFICIENT_EVIDENCE: architecture, ai_review missing; next state REWORK | lines 525, 697, 706 |
| ACC-11 | rule: approval is not evidence | as ACC-05, and a human approval record for the task exists | acceptance is evaluated | as ACC-05; the approval does not make the task ACCEPTED | A36 ("human approval is an authority act"); A18; line 299 |
| ACC-12 | transition IN_REVIEW → ACCEPTED | ACC-01 done; then a human approval record bound to the task's content | the approval is recorded | next state ACCEPTED | A35; A36; A42; lines 523-524, 621 |
| ACC-13 | rule: batch approval | three tasks in IN_REVIEW, each as ACC-01 | one batch approval by a human | three approval records, each bound to its own task's content; all three tasks ACCEPTED | A35; A42; lines 523-524 |
| ACC-14 | gov-AIEOS: transition IN_REVIEW → ACCEPTED by a delegated approval | gov-AIEOS defaults; ACC-01 done; then the decision agent's delegated approval, a record separate from any review, bound to the task's content and recorded as "decided by: decision agent (A41, A51)" | the approval is recorded | next state ACCEPTED; the approval is recorded as the decision agent's, not as an owner's or a person's decision, and the acceptance is shown as resting on an AI approval | CR-002 part 1 ("Quyền duyệt", "Hiển thị"), Đ5, Đ7; A41; A42; A51 (2); lines 523-524 |
| ACC-15 | gov-AIEOS: the decision agent's review satisfies a human review entry | gov-AIEOS defaults; as ACC-06, so the task is in IN_REVIEW; then the decision agent's own review of the task, made under its own decision, stating what it rests on, bound to the evaluated commit and the current intent versions, with its own evidence type, never labelled `human_review` | acceptance is re-evaluated | operational human_review is satisfied, so no type is missing; NEEDS_REVIEW; the task stays IN_REVIEW; the review does not make the task ACCEPTED (a separate approval record is needed, as in ACC-14) | CR-002 part 4 limits 1-5 and 7, Đ5, Đ7; A35; A36; CR-001 E8; lines 300, 524, 728 |

## 3. Risk Engine

| ID | Covers | Given | When | Expected | Source |
|---|---|---|---|---|---|
| RISK-01 | rule: fail-closed classification | a change that matches no risk rule | its risk is classified | it is not classified low, and the low default profile is not applied | A35; lines 592, 595-602 |

## 4. Resume Check

| ID | Covers | Given | When | Expected | Source |
|---|---|---|---|---|---|
| RC-01 | row CONTINUE, check 1 | defaults | Resume Check runs | CONTINUE | lines 286, 495 |
| RC-02 | checks 2-3 | HEAD moved; Δ meets neither the write-set nor the declared read-set | Resume Check runs | CONTINUE | lines 491, 495-497 |
| RC-03 | check 2 | HEAD moved; Δ meets the write-set, and the conflict cannot be resolved automatically | Resume Check runs | STOP: scope invalid | lines 289, 496 |
| RC-04 | check 3 | HEAD moved; Δ misses the write-set and meets the declared read-set; no interface or schema signature changed | Resume Check runs | CONTINUE_WITH | lines 287, 497 |
| RC-05 | check 3 | as RC-04, but an interface signature in the read-set changed | Resume Check runs | REPLAN | lines 288, 497 |
| RC-06 | check 4 | HEAD moved only by the commit that adds a newer version of a spec in `intent_versions`; Δ meets neither the write-set nor the declared read-set | Resume Check runs | REPLAN | lines 288, 498 |
| RC-07 | check 5 | a dependency is STALE | Resume Check runs | BLOCKED | lines 292, 499 |
| RC-08 | check 6 | the current code violates a constitution article that applies to the task | Resume Check runs | ESCALATE | lines 293, 500 |
| RC-09 | check 7 | the runtime's `max_risk` is below the task's risk | Resume Check runs | STOP: runtime insufficient | lines 290, 501 |
| RC-10 | check 8 | the task's retries are used up | Resume Check runs | ESCALATE | lines 293, 502 |
| RC-11 | rule: stale evidence | a dependency is DONE with stale evidence | Resume Check runs | CONTINUE | lines 270, 280, 499, 504, 530 |

## 5. Adversarial cases

| ID | Capability | Given | When | Expected | Source |
|---|---|---|---|---|---|
| ADV-01 | Verification | an implementation task's diff changes a scenario file outside its write-set | acceptance is evaluated | REJECT or NEEDS_REWORK (which one is open); never NEEDS_REVIEW or ACCEPT; the task is not ACCEPTED | A19 (4); lines 302, 303, 466, 715 |
| ADV-02 | Capability Boundaries | a runtime at tier T3 or above observes the agent writing a file outside the write-set during a session | the write is observed | STOP: violation; the change is rejected; the violation is recorded in the runtime's and the agent's metrics | lines 269, 291, 555, 652 |
| ADV-03 | Verification | the agent reports "done, all tests pass", and G1 failed | acceptance is evaluated | NEEDS_REWORK; next state REWORK; the report authorizes nothing | A18; lines 101, 302, 525 |

## 6. Not covered

This set is below the B14 minimum tier (proposed). Not covered:
- the REJECT row as a definite value, and the ACCEPT row (line 622's "sufficient assurance" is open: assurance-model.md §10 point 2);
- most lifecycle transitions: ACCEPTED → DONE, REWORK → IN_PROGRESS, retries → ESCALATED, DONE (evidence: stale) → re-verify (lines 521-530);
- check 2's rebase branch, check 5's "chưa DONE" branch, and budgets other than retries;
- NEEDS_REWORK for the constitution and spec-conformance gates;
- CONFLICT, DRIFT and reconciliation; unbaselined specs (B9, proposed); the high and critical profiles (CR-001 E10 open);
- for gov-AIEOS, beyond ACC-14 and ACC-15: the other limits of CR-002 part 4 (an act the owner keeps, limit 5; no tool or cross-model entry, limit 6; the implementing session and reviewer agents never produce the decision agent's review, limit 7; changes that weaken evidence requirements, limit 8), an approval that does not stand in for missing evidence (the gov-AIEOS form of ACC-11; Đ5, A36), the way-2 review (CR-002 part 4, "Chỗ hở đã vá"), ESCALATE routing (CR-002 part 1, "Báo lên") and a revocation of the delegation (CR-002 part 1, "Giới hạn");
- AIEOS projects whose users choose option b (CR-002 part 9): the product scenarios assume a project that has not chosen it.

Raising a risk class to L2, which an ACCEPT scenario would need, is the owner's, except that, for gov-AIEOS, the decision agent approves raising a low- or medium-risk class with metrics and a change request (A54 point 2; assurance-model.md §10 point 2); an ACCEPT scenario would also need an auto-accept policy, which is the owner's (A54 point 2), and none can be expressed while C13 is not PASS (assurance-model.md §6). Count: 30 scenarios (15 acceptance, 1 risk, 11 Resume Check, 3 adversarial).
