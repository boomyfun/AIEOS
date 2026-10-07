# AIEOS Assurance Model

> **Status: PRE-GENESIS DRAFT — proposed, not ratified.** A14 step 6; revision 3 is A14 step 7 work (working record DEF-0020). Every rule here is a proposal unless it cites a DECIDED row of `decision-matrix.md` (DM, section A), the concept, CR-001 or CR-002 as approved. Nothing here is a Genesis fact; the owner decided the contents of the Genesis bound set, whose item 5 is this model (A49; `genesis-model.md` §3, proposed); it is bound when a Genesis instance is ratified (A14 step 8).
> Revision 3 — 2026-10-07 (revisions 1 and 2, same day). Written under decisions of the decision agent (A41); it is not an owner decision. Normative concept: `AIEOS-concept.md` v0.5 with CR-001 and CR-002 (A22, A52). Rows are cited by ID, concept text by line ("concept line N"), CR-002 by part, entry (Đ1 to Đ10) or point.
> Names (A53): **gov-AIEOS** is what is used to build AIEOS (the self-build and its artifacts); **AIEOS** is the product. For gov-AIEOS, A51 and CR-002 parts 1 to 8 change sections 1 to 6 and 8 to 11. Section 12 states what CR-002 part 9 changes for AIEOS projects whose users choose option b. For every other AIEOS project the product default is unchanged (A35). This revision resolves the note of revision 2 ("revision 3 follows CR-002"). Names of classes and evidence types that CR-002 does not give are proposed here.
> Effect: until the trust-boundary measurements pass, every control described here is **advisory** (DM label rule "anything unmeasured defaults to advisory"; A31; section 9).

## 1. Principle

- The model is `fact_kind × source_class × evidence requirement`; requirements attach to the decision or capability being authorized, and risk only selects defaults (A16, DECIDED). There is no scalar assurance ladder (A16); the A0-A5 tiers are display labels only (concept line 708).
- Untrusted evidence may block or invalidate acceptance but never independently authorizes it (A17, DECIDED).
- Having evidence is not being authorized to accept (A18, DECIDED); human review is evidence and human approval is an authority act (A36, DECIDED). For gov-AIEOS the same holds for the decision agent: its review is evidence and its delegated approval is an authority act, kept as two records (CR-002 part 4 limit 2; Đ5).
- The main mechanism against circular self-validation is the conformance oracle (A19, DECIDED); its sufficiency is subject to C13, which is FAIL by implication (section 9). For gov-AIEOS, the decision agent approves each scenario in the owner's place, bound to that scenario's content (CR-002 part 6); so the same AI approves the scenarios, the rules on what must be reviewed, the reviews and the tasks (CR-002 part 4, "Cái giá").
- Proposed here: every acceptance answers two separate questions: *is the evidence complete?* (the requirement's entries, section 3) and *who or what accepts?* (the policy and the risk class's autonomy level, A35 and A36; for gov-AIEOS, A51 (2); section 6).

## 2. Source classes

Proposed in B3 (revision 24). Summary, not a restatement:

| Class | May block | May satisfy an entry | Notes |
|---|---|---|---|
| `agent_declared` | yes | no | A18; concept line 706 |
| `same_lineage_review` | yes | no; for gov-AIEOS, a **way-2 review** satisfies a non-cross-model `ai_review` entry | a fresh Claude session (A6); way 2: CR-002 part 4, "Chỗ hở đã vá"; A52 |
| `deterministic_tool_local` | yes | no | section 7 |
| `deterministic_tool_external_ci` | yes | yes, if the entry names it | effect: C7, C13 (section 9) |
| `cross_vendor_review` | yes | no (defined, dormant); for AIEOS projects whose users choose option b, section 12 | A6; section 5 |
| `decision_agent` | yes | gov-AIEOS only: its **review** satisfies an entry that names a human review type, within CR-002 part 4 limits 1 to 8; its **delegated approval** never satisfies an evidence entry | A41; A51 (2); CR-002 parts 1 and 4; not independent of the implementer and of the same model line (CR-002 part 4: "không độc lập với implementer và cùng dòng model với nó") |
| `delegate_ai` | yes | AIEOS projects whose users choose option b only: section 12 | CR-002 part 9 |
| `human_authority` | yes | a **review** satisfies entries naming a human evidence type; an **approval** never satisfies an evidence entry | A36 |

- No other class satisfies an entry. Where A6, A17 and A18 say a class never authorizes, that includes satisfying an entry used for acceptance (proposed, B3). Two exceptions exist for gov-AIEOS, each with its own basis: the decision agent's review (A51 (2) with CR-002 part 4, which corrects the concept where A51 contradicts it; A52) and the way-2 review (CR-002 part 4, "Chỗ hở đã vá"; A52, which changes A6 and A47 for that case only).
- A decision of the decision agent that authorizes the worker's actions (A6 as amended by A41) is neither evidence nor an approval of a task. For gov-AIEOS, the decision agent also makes two kinds of record about a task, each under its own decision (A51 (2); CR-002 parts 1 and 4). The decision agent is never the implementer (concept line 544; CR-002 part 4 limit 7).
  - Its **review**: an `observation` from `decision_agent`, with its own evidence type `decision_agent_review`, never labelled `human_review` or human (part 4 limit 3). It is made by the decision agent itself, from what it has read itself, and states what it rests on; a reviewer agent's output is used only where the decision agent has read the work again (limit 1). It satisfies only an entry that names a human review type (`human_review`, `human_security_review`; concept lines 360, 682, 692, 694, 704), and only in gov-AIEOS (limit 4); so it never satisfies an `ai_review` entry. It never satisfies the cross-model entry (concept line 703; CR-001 E10) and never stands in for an entry that a tool produces (limit 6). For a task that carries out or changes an act that A51 item (4) keeps with the owner, it satisfies no human review entry, and the owner reviews and approves the task (limit 5). The implementing session and reviewer agents never produce it (limit 7). It is not V5 (concept line 720; part 4).
  - Its **delegated approval**: an `authority` record from `decision_agent`, recorded "decided by: decision agent (A41, A51)", bound to one task's content hash (A42), never an auto-accept (A35) and never evidence (A36; CR-002 part 1). Its effect is advisory (A31, A41; section 9).
  - Whether a task falls under limit 5 is decided fail closed: when it is unclear, the task is treated as one the owner reviews and approves (proposed here, as A35 does for risk classification).
- A **way-2 review** (CR-002 part 4, "Chỗ hở đã vá"; A52), for gov-AIEOS: a review by a reviewer agent running on a Claude model other than the model that did the work, made under a decision of the decision agent. It is a `same_lineage_review` record with its own evidence type `other_model_review`; it names its own model and the implementer's model, and counts only if they differ (concept line 706: "AI review cùng model với implementer không được tính"). It satisfies only an `ai_review` entry that is not cross-model; never a human review entry and never the cross-model entry (concept line 703; CR-001 E10).
- Any Claude review other than these two still may block and never satisfies an entry (A6, A47).
- The owner's own words always prevail over these records; the owner revokes the delegation in one sentence, with effect from then on only: what was approved or pushed before stays (CR-002 part 1, "Giới hạn"; A1).
- Every satisfying record is bound to the commit SHA and the intent version under evaluation (concept line 728); a change to either makes it stale (concept lines 270, 667, 669).

## 3. Requirements and evidence

- A requirement names the decision or capability it authorizes and, per dimension (concept lines 681-684), the evidence types required and, per type, the classes whose records satisfy it (B4, proposed). Each type is required; none stands in for another (concept lines 674, 687). For gov-AIEOS, CR-002 part 4 relaxes lines 674, 706 and 729 for the decision agent's review only, and only for entries that name a human review type.
- Which records satisfy which entry, for gov-AIEOS (proposed; B3, B4):

| Entry names | Satisfied by | Source |
|---|---|---|
| a tool-produced type (for example `build`, `lint`, `unit_test`, `deterministic_rule`, `property_test`) | `deterministic_tool_external_ci` records of that type | B3; section 7 |
| `ai_review`, not cross-model | `other_model_review` records (way 2) | CR-002 part 4, "Chỗ hở đã vá"; A52 |
| `ai_review (cross-model)` | none while CR-001 E10 is open | concept line 703; section 5 |
| a human review type (`human_review`, `human_security_review`) | `human_authority` reviews; `decision_agent_review` records, except for a task under CR-002 part 4 limit 5 | A36; CR-002 part 4 |

- Evaluation, in the fixed order REJECT > NEEDS_REWORK > INSUFFICIENT_EVIDENCE > NEEDS_REVIEW > ACCEPT (A36, DECIDED):
  - A blocking record of any class gives REJECT or NEEDS_REWORK (concept lines 302-303). A failed gate of the task's verification plan gives NEEDS_REWORK (concept line 302; gates: concept lines 299, 469), so NEEDS_REVIEW and ACCEPT both need every gate passed (B4, proposed).
  - A required type with no satisfying record gives INSUFFICIENT_EVIDENCE. If every missing type is one only a human can produce, the task goes to IN_REVIEW (A36, DECIDED); otherwise to REWORK (concept line 525), and after the retry limit to ESCALATED (concept line 526). When both kinds are missing: REWORK first (proposed; concept line 310 allows either). For gov-AIEOS, a human review type is still treated as a type only a human can produce for this routing, although the decision agent's review satisfies it (CR-002 Đ5).
  - For gov-AIEOS, an ESCALATED task goes to the decision agent, and to the owner if it touches an act that A51 item (4) keeps (CR-002 part 1, "Báo lên").
  - A complete evidence requirement gives NEEDS_REVIEW (concept line 300 as corrected by CR-001 E8 and, for gov-AIEOS, CR-002 Đ5), or ACCEPT only where policy explicitly allows auto-accept (A36, DECIDED; section 6).
- An approval never stands in for missing evidence (proposed, from A36). A task leaves IN_REVIEW for ACCEPTED only when its evidence requirement is complete, re-evaluation in the A36 order gives neither REJECT nor NEEDS_REWORK, and its approval record exists (proposed). For gov-AIEOS, the review and the approval are two separate records, also when the decision agent makes both (CR-002 Đ5; A36).
- At L1 the acceptance authority is an approval record, one per task bound to its content, also under one-click batch approval (A35, A36, A42, DECIDED). It is a human approval record, except:
  - for gov-AIEOS, it is the decision agent's delegated approval (A51 (2); CR-002 Đ5, Đ7, Đ10), and for a task under CR-002 part 4 limit 5 it is the owner's approval;
  - for an AIEOS project whose user chose option b, section 12.
- No task is accepted against an unbaselined spec (B9, proposed).

## 4. Records

Proposed alignment of B5 (unchanged) with B3 (revision 24):

- Each record carries `fact_kind` (claim / observation / interpretation / authority), `source_class` and `recorder` (B5).
- An agent's statement is recorded as a `claim` from `agent_declared`; it is valid only as an observation that the claim was made, and authorizes nothing (A18, DECIDED).
- A result re-fetched from external CI is an `observation` from `deterministic_tool_external_ci`. A locally written record counts at most as a claim unless it can be re-derived from Git or re-fetched from an external channel (B5). A human review is an `observation` from `human_authority`.
- A human approval is an `authority` record from `human_authority`; it is recorded as an Authority Action of the A21 chain (proposed mapping onto A21, which is DECIDED). One IN_REVIEW session that produces both writes two records (A36, DECIDED).
- For gov-AIEOS (section 2): the decision agent's review is an `observation` from `decision_agent` (evidence type `decision_agent_review`) that states what it rests on; its delegated approval is an `authority` record from `decision_agent`, labelled "decided by: decision agent (A41, A51)"; a way-2 review is an `observation` from `same_lineage_review` (evidence type `other_model_review`) that names the reviewer's model and the implementer's model. Each is bound to the commit SHA and the intent version (concept line 728). Each delegated approval is relayed to the owner in plain words after it is made (CR-002 part 1). What rests only on AI review or AI approval is shown as such (concept line 65; CR-002 part 1, "Hiển thị").
- An acceptance decision, including an auto-accept, is an `interpretation` record that cites the records it used (observations, authority records and any blocking records) and the policy and level versions; it is recomputable from them plus a pinned ruleset (proposed; A35, DECIDED, requires the policy and level version on each auto-accept).
- Records written during the bootstrap carry their recorder and are not authoritative (CR-001 E3).

## 5. Default evidence profiles by risk

- **v0.1 defaults** (concept lines 699-702; v0.1 scope at concept line 947): low: functional [build, lint]; medium: functional [unit_test], architecture [deterministic_rule]. The class for each default entry is `deterministic_tool_external_ci` (proposed). Whether `deterministic_rule` belongs to V1 or V2 (concept lines 716-717) is open. Every v0.1 profile has an entry that a tool produces, and limits 6 and 8 of CR-002 part 4 keep it, so no acceptance of gov-AIEOS rests on the implementer's report alone (CR-002 part 5, K1), nor, by the same entries, on the decision agent's review alone.
- **AIEOS's own security-critical parts** (CR-002 Đ9): for gov-AIEOS, the parts of AIEOS that judge work, check its rules and limit authority are treated as security-critical (D-082). There, AI review is the last layer, after the machine checks the risk requires (V0-V2, V4; concept lines 715-719, in the order of concept line 724); only the last sentence of concept line 725 changes. The cost is stated in CR-002 part 4.
- **High and critical** (concept lines 703-704): v0.1 lists defaults for low and medium only; the high and critical profiles and V3 cross-model review come in v0.2 (concept lines 947, 954). The `ai_review (cross-model)` entry is **CR-001 E10, open** (concept line 703; DEF-0008); the G4 gate of the example task (concept line 466) is listed with it in B3. The owner was asked on 2026-10-07 (decision file D-061). CR-002 keeps E10 open (part 5, K4).
- **While E10 is open** (mechanical consequence, not a route): if the high and critical defaults of concept lines 703-704 apply before v0.2 (which profile applies to such tasks in v0.1 is part of owner point 1), no record can satisfy the cross-model entry: for gov-AIEOS, `cross_vendor_review` is dormant (A6), a way-2 review satisfies only non-cross-model `ai_review` entries (A52), and the decision agent's review never satisfies it (CR-002 part 4 limit 6). The entry cannot be removed (section 8). A high or critical task therefore stays at INSUFFICIENT_EVIDENCE; the missing type is not human-only, so it goes to REWORK and, after the retry limit, to ESCALATED (concept lines 525-526). No approval, the owner's or a delegated one, can fill the gap (section 3), and the decision agent cannot settle E10: it stays the owner's (CR-002 part 8). How such tasks are handled meanwhile is open (owner; section 10).
- **The owner's answer** (DM A47): "Câu trả lời là b" (2026-10-07, session 2963e747, transcript :1152), to the question of decision file D-061. Proposed consequence: a high or critical task of gov-AIEOS gets a review by a Claude model other than the one that did the work. It may block, and it never replaces an approval (A17). Under A52, the same kind of review, made under a decision of the decision agent, is a way-2 review and satisfies non-cross-model `ai_review` entries (section 2); otherwise it is advisory (A47). Whether it meets the cross-model entry (concept line 703) stays open (CR-001 E10), and so does the routing above while E10 is open.

## 6. Autonomy and auto-accept

- A project starts at L1 for every risk class; the AIEOS self-build stays at L1; at L1 acceptance ends at NEEDS_REVIEW with one-click batch approval; a risk class is raised to L2 only with metrics and a change request; at L2 auto-accept stays within risk ≤ medium and sufficient assurance; risk classification fails closed (A35, DECIDED; concept lines 621-626).
- For gov-AIEOS (CR-002 Đ7): L1 means no auto-accept, and one approval for each task; the approver is the decision agent at every risk level, including high and critical, except a task under CR-002 part 4 limit 5, which the owner approves. Approving task plans (concept lines 521, 623), requirements and milestones (concept line 624) is also delegated (CR-002 part 1, Đ6); the project is not counted as being at L3 or L4. The rule for raising a level (concept line 626; A35: metrics and a change request) is unchanged; who approves such a change request is section 10 point 2.
- For gov-AIEOS, the deterministic policies that concept line 199 lets be approved in advance are approved by the decision agent in the owner's place (CR-002 Đ2), with the limits of CR-002 part 1: such a policy never accepts a task by itself (auto-accept only as Đ7 allows), never decides an act of A51 item (3) or (4), and is reported to the owner when approved.
- Proposed:
  - `auto_accept` is expressible only for a risk class raised to L2 or above, and only within the L2 limits of A35; any wider bound is not expressible until the owner sets it.
  - Auto-accept reads the policy, risk rules, default profiles and level assignments only from an approved, versioned policy, treated like intent: changed only through an approved change request (concept lines 199, 409; the policy file at concept line 868). Who approves the auto-accept policy and each change to it is an owner point, for gov-AIEOS too (B4; section 10 point 2). A change that weakens evidence requirements is the owner's in any case (CR-002 part 4 limit 8; section 8).
  - A change that touches the policy, the risk rules, the default profiles, the level assignments or the acceptance verifier is never auto-accepted (proposed here; such changes are B1 `critical_cr`; a change touching intent is critical at concept line 601, above the line-622 limit).
  - Fail-closed until C13 or the owner settles it: CI records that rest on agent-modified code (section 9) do not satisfy entries used for `auto_accept`. In effect, `auto_accept` cannot be expressed while C13 is not PASS.
  - "Sufficient assurance" (concept line 622) requires at least a complete evidence requirement; what more, if anything (for example measured adapter assurance, CR-001 E1), is open.

## 7. Where V0 and V1 run

- On the fast path AIEOS generates the artifacts and runs V0+V1 (A35, DECIDED; concept line 793 as corrected by CR-001 E7). The conflict with concept line 729 is stated in B4 (revision 16). CR-002 does not change this section; whether option 1 needs a CR-001 entry stays the owner's (CR-002 part 8).
- Options (proposed; any CR-001 part is the owner's, A22):
  1. **V0+V1 run in external CI on the evaluated commit.** Consistent with B3; local runs stay advisory and may block. Consequences: until a CI channel exists, no task can reach NEEDS_REVIEW, because local records satisfy no entry and an approval cannot stand in for evidence (section 3); and the CI job runs agent-modified code, so it is inside the agent's authority domain (A29; section 9). Its integrity is C7, TBD. Setting it up is implementation, so it comes after step 9 (A14).
  2. **A bootstrap exception:** during the bootstrap, at L1 only, local deterministic records satisfy entries as bootstrap records (not authoritative, CR-001 E3). Needs a B3 change and possibly a CR-001 entry.
- **Chosen: option 1** (proposed; decided by: decision agent (A41), D-062). The CI channel is to be in place before the first task at step 9, so that the self-build never depends on local records and no bootstrap-only counting path has to be retired later (A9: the bootstrap is disposable). Creating the channel touches `.github/` and is the owner's to approve when it is done (A32, A34, A41; A51 item (4)). Whether option 1 needs a CR-001 entry, given concept line 729, is the owner's (A22; section 10).

## 8. Requirements against the risk defaults

- A requirement declares only what differs from its risk default (concept line 697). A requirement is an Intent entity (concept line 403), so every change to one goes through an approved change request (concept line 409); AI drafts and a human approves (A43 Q5, DECIDED); for gov-AIEOS the decision agent approves in the owner's place (CR-002 Đ6).
- Proposed: removing or weakening a default entry is never used to remove the cross-model entry while E10 is open.
- For gov-AIEOS, the decision agent never approves by itself a change that weakens evidence requirements (CR-002 part 4 limit 8). Examples from CR-002: removing an evidence entry or narrowing the scope of the article that requires it; changing an entry to a type its own review can satisfy; letting a kind of review count where it does not count now; lowering the risk of a kind of change. For an unapproved draft, the reference point is the latest version on GitHub. Such a change is the owner's.
- Owner point (open): whether a departure from the risk default needs a specific approval or change class beyond the change request.

## 9. Relation to the measured trust boundary

- The minimal P-CRED baseline is FAIL (DM section D; C2, C13); owner-authority claims (merges, approvals, signatures) are therefore at most advisory (A31; measurement-protocol §1.4), and C13 is FAIL by implication.
- So, in this environment: approval records, the approval of a change request that raises a level, auto-accepts and CI records are all **advisory** (approvals: A31; the rest: proposed reading of C7 TBD and C13 FAIL). The records are still required; only their effect is advisory.
- For gov-AIEOS, the decision agent's delegated approvals and reviews are advisory too (A41: the decision agent is inside the worker's authority domain, A29, so its effect is advisory), and so are way-2 reviews (proposed here: reviewer agents also run inside that domain). For delegated approvals this does not end when the measurements pass: nothing that has been measured stops a wrong approval (CR-002 part 1). A29 stays a target, unmet by design (A51 item (7)).
- A CI job that executes agent-modified code is inside the agent's authority domain (A29, DECIDED). Fixtures, dependencies and configuration from the change are evaluator inputs (A29); so are tests the evaluator runs (C13; measurement-protocol §2.7 item 1). How a record that rests on such inputs may count is C13 design; the candidate controls are B17 (proposed), **not settled here**.
- No hardening is applied and no re-measurement is due (A46, DECIDED); this section changes only when the measurements change.

## 10. Open owner points

CR-002 part 8 keeps the open points of this section with the owner. Two lines speak to points 2 and 6: CR-002 Đ7 says that, after CR-002, a change request that raises a level is approved by the decision agent; and A51 item (3) lets the decision agent ratify a Genesis instance after CR-002. Until that is settled, both points stay the owner's (fail closed).

1. CR-001 E10: whether the review chosen in A47 (another Claude model; under A52, such a review made under a decision of the decision agent is a way-2 review for `ai_review` entries that are not cross-model) meets the cross-model entry, and the meaning of "cross-model"; which profile applies to high and critical tasks in v0.1, and how they are handled while E10 is open (section 5; DEF-0008).
2. Autonomy: raising any risk class to L2 (see the paragraph above for gov-AIEOS; A35 also says the self-build stays at L1); who approves the auto-accept policy and each change to it; any bound above L2; "sufficient assurance"; whether L2 may be used while P-CRED or C13 is not PASS (section 6). Even if a class were raised, no auto-accept can be expressed while C13 is not PASS (section 6). For AIEOS projects whose users choose option b, raising a class to L2 and approving the auto-accept policy stay with the user (CR-002 part 9 point 4; section 12).
3. Whether section 7's choice needs a CR-001 entry (A22; CR-002 part 8).
4. Whether a departure from the risk default needs a specific approval or change class (section 8). A departure that weakens evidence requirements is the owner's in any case (CR-002 part 4 limit 8).
5. The trust-boundary measurements and any hardening (A41; A46; A51 item (4)).
6. Ratifying this model (see the paragraph above). Genesis is to bind it as item 5 of the bound set (A49). This model records who approves what under A51 and CR-002 and changes none of it; any change to who may approve what is the owner's (CR-002 part 8; A22; A51 item (4)).
7. Whether the A41 delegation continues once AIEOS governs its own build, and whether it enters the Genesis instance (A41; CR-002 part 8).

## 11. Not covered

- C13/B17 control design; the provenance chain B6 and P-GH-5; measurements.
- The conformance methodology (A19, B10, B14) beyond the points above.
- The constitution revision under way 1 (CR-002 part 4, "Chỗ hở đã vá"; working record DEF-0020).
- The AIEOS product specifications for option b, such as record formats and projects with several people (CR-002 part 9; the concept §18 specifications, not scheduled).
- Code (A14: none before step 9).

## 12. AIEOS: projects whose users choose option b (CR-002 part 9)

For an AIEOS project whose user chose option b, explicitly and themself, after AIEOS showed them its cost (part 9 point 1), CR-002 part 9 changes sections 2, 3 and 6 as follows (proposed). In this section, "the decision agent" reads as the user's AI approver, and "the owner" as the user (part 9 points 3 and 8). For every other project, the concept and A35 apply unchanged.
- **Classes.** A new class `delegate_ai` holds the records of the AI approver that the user sets up outside the AIEOS core (part 9 point 2; concept line 162 unchanged). Its review satisfies an entry that names a human review type, within part 4 limits 1 to 3 as read here, although it may be the same kind or model as the working AI; its delegated approval satisfies no evidence entry (part 9 point 3; A36). The working AI's own report never counts.
- **Other AI reviews.** In AIEOS, AI from other vendors is not excluded (A6 is about building AIEOS): an `ai_review` entry is satisfied as concept line 706 states, by an AI review whose model is not the implementer's. When the AI approver is from another vendor than the working AI, a separate review of its own also counts for an `ai_review` entry (part 9 point 3, following the owner's words of 2026-10-07, session 1dace763 :1105; A52). The cross-model entry follows CR-001 E10, open.
- **Acceptance authority.** At L1, the AI approver's delegated approval, one per task bound to its content (A42), at every risk level; never an auto-accept (part 9 point 3). ESCALATE goes to the AI approver, except what touches the next point (part 9 point 3). For the tasks of the next two points, the user reviews and approves.
- **What the user keeps** (part 9 point 4): the acts of A51 item (4) in general; acts at a permission prompt; accounts, passwords, access codes, money and security settings; history rewrite and deletion on the remote repository; visibility and publishing; sending messages; the CI and repository settings; the working AI tool's settings and hooks; the AI approver's own instructions and configuration; the scope of what it may approve; raising a class to L2 and approving auto-accept policies; any change that weakens evidence requirements (reference: the version the user last approved), including which code is placed in the group of the next point; and anything the user names. Withdrawing option b takes effect from then on only; what the AI approved before stays.
- **Code about money, blockchain or security.** For the user's financial, blockchain or security-critical code, the AI approver's review satisfies no human review entry; a person reviews and approves the task, or it is not accepted (part 9 point 5; concept line 725; a default set by the decision agent, D-084).
- **Display.** AIEOS always shows which approvals and reviews an AI made, never labels them as a person's, and reports each delegated approval (part 9 point 6; concept line 65).
- **Cost, stated to the user** (part 9 point 7): no person checks the project, except what the two points above keep; the AI approver may be the same kind or model as the working AI and make the same mistakes, while its review still counts; it approves at every risk level, including the project's constitution and the tasks judged under it, and irreversible acts the user did not keep; it sees only what it is given, and nothing stops a wrong approval; when it shares an authority domain with the working AI, A29 is not met; harm can reach the people who use the project's software. The user's choice and kept acts are advisory until AIEOS can tell the user's own acts from the AI's and that has been measured (A31).
