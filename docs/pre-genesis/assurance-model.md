# AIEOS Assurance Model

> **Status: PRE-GENESIS DRAFT — proposed, not ratified.** A14 step 6. Every rule here is a proposal unless it cites a DECIDED row of `decision-matrix.md` (DM, section A), the concept, or CR-001 as approved. Nothing here is a Genesis fact; whether Genesis binds this model is decided at steps 7-8 (A20, B2).
> Revision 2 — 2026-10-07 (revision 1, same day: first version). Written under decisions of the decision agent (A41); it is not an owner decision. Normative concept: `AIEOS-concept.md` v0.5 with CR-001 (A22). Rows are cited by ID, concept text by line ("concept line N").
> Effect: until the trust-boundary measurements pass, every control described here is **advisory** (DM label rule "anything unmeasured defaults to advisory"; A31; section 9).

## 1. Principle

- The model is `fact_kind × source_class × evidence requirement`; requirements attach to the decision or capability being authorized, and risk only selects defaults (A16, DECIDED). There is no scalar assurance ladder (A16); the A0-A5 tiers are display labels only (concept line 708).
- Untrusted evidence may block or invalidate acceptance but never independently authorizes it (A17, DECIDED).
- Having evidence is not being authorized to accept (A18, DECIDED); human review is evidence and human approval is an authority act (A36, DECIDED).
- The main mechanism against circular self-validation is the conformance oracle (A19, DECIDED); its sufficiency is subject to C13, which is FAIL by implication (section 9).
- Proposed here: every acceptance answers two separate questions: *is the evidence complete?* (the requirement's entries, section 3) and *who or what accepts?* (the policy and the risk class's autonomy level, A35 and A36; section 6).

## 2. Source classes

Proposed in B3 (revision 16). Summary, not a restatement:

| Class | May block | May satisfy an entry | Notes |
|---|---|---|---|
| `agent_declared` | yes | no | A18; concept line 706 |
| `same_lineage_review` | yes | no | a fresh Claude session (A6); also, for acceptance, a decision of the decision agent (proposed here; A41) |
| `deterministic_tool_local` | yes | no | section 7 |
| `deterministic_tool_external_ci` | yes | yes, if the entry names it | effect: C7, C13 (section 9) |
| `cross_vendor_review` | yes | no (defined, dormant) | A6; section 5 |
| `human_authority` | yes | a **review** satisfies entries naming a human evidence type; an **approval** never satisfies an evidence entry | A36 |

- Where A6, A17 and A18 say a class never authorizes, that includes satisfying an entry used for acceptance (proposed, B3).
- A decision of the decision agent authorizes the worker's actions (A6 as amended by A41) but is never acceptance authority: it never satisfies an entry and never replaces a human approval record (proposed here; A41: never evidence of human authority, and A41 does not change A17-A19, A35 or A36).
- Every satisfying record is bound to the commit SHA and the intent version under evaluation (concept line 728); a change to either makes it stale (concept lines 270, 667, 669).

## 3. Requirements and evidence

- A requirement names the decision or capability it authorizes and, per dimension (concept lines 681-684), the evidence types required and, per type, the classes whose records satisfy it (B4, proposed). Each type is required; none stands in for another (concept lines 674, 687).
- Evaluation, in the fixed order REJECT > NEEDS_REWORK > INSUFFICIENT_EVIDENCE > NEEDS_REVIEW > ACCEPT (A36, DECIDED):
  - A blocking record of any class gives REJECT or NEEDS_REWORK (concept lines 302-303). A failed gate of the task's verification plan gives NEEDS_REWORK (concept line 302; gates: concept lines 299, 469), so NEEDS_REVIEW and ACCEPT both need every gate passed (B4, proposed).
  - A required type with no satisfying record gives INSUFFICIENT_EVIDENCE. If every missing type is one only a human can produce, the task goes to IN_REVIEW (A36, DECIDED); otherwise to REWORK (concept line 525), and after the retry limit to ESCALATED (concept line 526). When both kinds are missing: REWORK first (proposed; concept line 310 allows either).
  - A complete evidence requirement gives NEEDS_REVIEW (concept line 300 as corrected by CR-001 E8), or ACCEPT only where policy explicitly allows auto-accept (A36, DECIDED; section 6).
- An approval never stands in for missing evidence (proposed, from A36). A task leaves IN_REVIEW for ACCEPTED only when its evidence requirement is complete, re-evaluation in the A36 order gives neither REJECT nor NEEDS_REWORK, and its approval record exists (proposed).
- At L1, and for the AIEOS self-build, the acceptance authority is always a human approval record, one per task bound to its content, also under one-click batch approval (A35, A36, A42, DECIDED).
- No task is accepted against an unbaselined spec (B9, proposed).

## 4. Records

Proposed alignment of B5 with B3 (revision 16):

- Each record carries `fact_kind` (claim / observation / interpretation / authority), `source_class` and `recorder` (B5).
- An agent's statement is recorded as a `claim` from `agent_declared`; it is valid only as an observation that the claim was made, and authorizes nothing (A18, DECIDED).
- A result re-fetched from external CI is an `observation` from `deterministic_tool_external_ci`. A locally written record counts at most as a claim unless it can be re-derived from Git or re-fetched from an external channel (B5). A human review is an `observation` from `human_authority`.
- A human approval is an `authority` record from `human_authority`; it is recorded as an Authority Action of the A21 chain (proposed mapping onto A21, which is DECIDED). One IN_REVIEW session that produces both writes two records (A36, DECIDED).
- An acceptance decision, including an auto-accept, is an `interpretation` record that cites the records it used (observations, authority records and any blocking records) and the policy and level versions; it is recomputable from them plus a pinned ruleset (proposed; A35, DECIDED, requires the policy and level version on each auto-accept).
- Records written during the bootstrap carry their recorder and are not authoritative (CR-001 E3).

## 5. Default evidence profiles by risk

- **v0.1 defaults** (concept lines 699-702; v0.1 scope at concept line 947): low: functional [build, lint]; medium: functional [unit_test], architecture [deterministic_rule]. The class for each default entry is `deterministic_tool_external_ci` (proposed). Whether `deterministic_rule` belongs to V1 or V2 (concept lines 716-717) is open.
- **High and critical** (concept lines 703-704): v0.1 lists defaults for low and medium only; the high and critical profiles and V3 cross-model review come in v0.2 (concept lines 947, 954). The `ai_review (cross-model)` entry is **CR-001 E10, open** (concept line 703; DEF-0008); the G4 gate of the example task (concept line 466) is listed with it in B3. The owner was asked on 2026-10-07 (decision file D-061).
- **While E10 is open** (mechanical consequence, not a route): if the high and critical defaults of concept lines 703-704 apply before v0.2 (which profile applies to such tasks in v0.1 is part of owner point 1), no class can satisfy the cross-model entry (`cross_vendor_review` is dormant, `same_lineage_review` never satisfies; B3), and the entry cannot be removed (section 8). A high or critical task therefore stays at INSUFFICIENT_EVIDENCE; the missing type is not human-only, so it goes to REWORK and, after the retry limit, to ESCALATED (concept lines 525-526). The owner's approval cannot fill the gap (section 3). How such tasks are handled meanwhile is open (owner; section 10).
- **The owner's answer** (DM A47): "Câu trả lời là b" (2026-10-07, session 2963e747, transcript :1152), to the question of decision file D-061. Proposed consequence: a high or critical task of the AIEOS self-build gets a review by a Claude model other than the one that did the work. The review is a `same_lineage_review` record (B3): it may block, never satisfies an entry and never replaces the owner's approval (A6, A17). Whether it meets the cross-model entry (concept line 703) stays open (CR-001 E10), and so does the routing above while E10 is open.

## 6. Autonomy and auto-accept

- A project starts at L1 for every risk class; the AIEOS self-build stays at L1; at L1 acceptance ends at NEEDS_REVIEW with one-click batch approval; a risk class is raised to L2 only with metrics and a change request; at L2 auto-accept stays within risk ≤ medium and sufficient assurance; risk classification fails closed (A35, DECIDED; concept lines 621-626).
- Proposed:
  - `auto_accept` is expressible only for a risk class raised to L2 or above, and only within the L2 limits of A35; any wider bound is not expressible until the owner sets it.
  - Auto-accept reads the policy, risk rules, default profiles and level assignments only from an approved, versioned policy, treated like intent: changed only through a human-approved change request (concept lines 199, 409; the policy file at concept line 868). Who approves the policy and its changes is an owner point (B4; section 10).
  - A change that touches the policy, the risk rules, the default profiles, the level assignments or the acceptance verifier is never auto-accepted (proposed here; such changes are B1 `critical_cr`; a change touching intent is critical at concept line 601, above the line-622 limit).
  - Fail-closed until C13 or the owner settles it: CI records that rest on agent-modified code (section 9) do not satisfy entries used for `auto_accept`. In effect, `auto_accept` cannot be expressed while C13 is not PASS.
  - "Sufficient assurance" (concept line 622) requires at least a complete evidence requirement; what more, if anything (for example measured adapter assurance, CR-001 E1), is open.

## 7. Where V0 and V1 run

- On the fast path AIEOS generates the artifacts and runs V0+V1 (A35, DECIDED; concept line 793 as corrected by CR-001 E7). The conflict with concept line 729 is stated in B4 (revision 16).
- Options (proposed; any CR-001 part is the owner's, A22):
  1. **V0+V1 run in external CI on the evaluated commit.** Consistent with B3; local runs stay advisory and may block. Consequences: until a CI channel exists, no task can reach NEEDS_REVIEW, because local records satisfy no entry and an approval cannot stand in for evidence (section 3); and the CI job runs agent-modified code, so it is inside the agent's authority domain (A29; section 9). Its integrity is C7, TBD. Setting it up is implementation, so it comes after step 9 (A14).
  2. **A bootstrap exception:** during the bootstrap, at L1 only, local deterministic records satisfy entries as bootstrap records (not authoritative, CR-001 E3). Needs a B3 change and possibly a CR-001 entry.
- **Chosen: option 1** (proposed; decided by: decision agent (A41), D-062). The CI channel is to be in place before the first task at step 9, so that the self-build never depends on local records and no bootstrap-only counting path has to be retired later (A9: the bootstrap is disposable). Creating the channel touches `.github/` and is the owner's to approve when it is done (A32, A34, A41). Whether option 1 needs a CR-001 entry, given concept line 729, is the owner's (A22; section 10).

## 8. Requirements against the risk defaults

- A requirement declares only what differs from its risk default (concept line 697). A requirement is an Intent entity (concept line 403), so every change to one goes through a human-approved change request (concept line 409); AI drafts and a human approves (A43 Q5, DECIDED).
- Proposed: removing or weakening a default entry is never used to remove the cross-model entry while E10 is open.
- Owner point (open): whether a departure from the risk default needs a specific approval or change class beyond the change request.

## 9. Relation to the measured trust boundary

- The minimal P-CRED baseline is FAIL (DM section D; C2, C13); owner-authority claims (merges, approvals, signatures) are therefore at most advisory (A31; measurement-protocol §1.4), and C13 is FAIL by implication.
- So, in this environment: approval records, the approval of a change request that raises a level, auto-accepts and CI records are all **advisory** (approvals: A31; the rest: proposed reading of C7 TBD and C13 FAIL). The records are still required; only their effect is advisory.
- A CI job that executes agent-modified code is inside the agent's authority domain (A29, DECIDED). Fixtures, dependencies and configuration from the change are evaluator inputs (A29); so are tests the evaluator runs (C13; measurement-protocol §2.7 item 1). How a record that rests on such inputs may count is C13 design; the candidate controls are B17 (proposed), **not settled here**.
- No hardening is applied and no re-measurement is due (A46, DECIDED); this section changes only when the measurements change.

## 10. Open owner points

1. CR-001 E10: whether the review chosen in A47 (another Claude model, advisory) meets the cross-model entry, and the meaning of "cross-model"; which profile applies to high and critical tasks in v0.1, and how they are handled while E10 is open (section 5; DEF-0008).
2. Autonomy (A41 keeps the autonomy levels of A35 with the owner): raising any risk class to L2; who approves the auto-accept policy and each change to it; any bound above L2; "sufficient assurance"; whether L2 may be used while P-CRED or C13 is not PASS (section 6).
3. Whether section 7's choice needs a CR-001 entry (A22).
4. Whether a departure from the risk default needs a specific approval or change class (section 8).
5. The trust-boundary measurements and any hardening (A41; A46).
6. Ratifying this model and whether Genesis binds it (A20, B2; steps 7-8).
7. Whether the A41 delegation continues once AIEOS governs its own build (A41).

## 11. Not covered

- C13/B17 control design; the provenance chain B6 and P-GH-5; measurements.
- The conformance methodology (A19, B10, B14) beyond the points above.
- Code (A14: none before step 9).
