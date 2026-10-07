# AIEOS Genesis Model

> **Status: PRE-GENESIS DRAFT — proposed, not ratified.** A14 step 7. Every rule here is a proposal unless it cites a DECIDED row of `decision-matrix.md` (DM, section A), the concept, or CR-001 as approved. This document binds nothing: binding is done by the Genesis Charter (A14 step 8). Step 7 follows the owner's yes in A48 ("có, sang bước 7 nhưng để phiên sau.").
> Revision 3 — 2026-10-07 (revision 1, same day: first version; revision 2, same day: the owner's answers A49, A50 and A51). Revision 3 points rows 2, 6 and 7 to their drafts and notes that their approval under A51 waits for CR-002. Written under decisions of the decision agent (A41; scope set in decision file D-067; revision 2 under decision files D-072 and D-073; revision 3 under decision files D-078, D-079 and D-080); it is not an owner decision. Normative concept: `AIEOS-concept.md` v0.5 with CR-001 (A22). Rows are cited by ID, concept text by line ("concept line N"), the measurement protocol as "MP".
> Effect: the only measurement made is the minimal P-CRED baseline, which is FAIL (DM section D); every authority claim described here, owner or delegated, is therefore at most **advisory** (A31, A41; section 8).

## 1. Principle

- The concept v0.5 does not use the word Genesis. The DM adds it as a level of the plan hierarchy: concept → Genesis → Master Plan → milestones → task contracts (A13, DECIDED). In the concept, human authority and the constitution are the top two levels of the truth hierarchy (concept lines 175, 178).
- Genesis binds trust roots, not the project plan (A20, DECIDED). A20 calls its list a "Candidate bound set" and says "Exact contents stay PROPOSED (B2) until step 7". The owner decided the exact contents: section 3 without the signing key (A49).
- Proposed meanings (Claude's; B2, proposed, lists the two sets; B1, proposed, makes a change to a bound artifact a `genesis_amendment`): a **bound** artifact changes only through a genesis amendment (section 5); a **ratified, not bound** artifact is accepted under Genesis and changes through ordinary change requests.
- A14 (DECIDED) gives the reason "Genesis must not ratify an unmeasured trust boundary", and MP §6 (line 268) puts the Genesis model after the measurements. A44 records the owner's instruction to resolve the block and complete A14 ("giải quyết chỗ kẹt rồi hoàn thành nốt A14, …"); its sentences "Steps 2-4 of A14 no longer hold up the sequence" and "at steps 7 and 8 the trust boundary is presented as unmeasured" are Claude's wording in that row, not the owner's words. Proposed reading: Genesis may bind the boundary **abstraction** (section 3, row 4), but it ratifies no boundary **implementation** as a trust boundary (sections 4 and 8). The owner's yes to step 7 is A48. MP §6 line 268 is not amended; step 7 proceeds before the measurements on A44 and A48.

## 2. Model and instance

- Genesis binds the model and trust rules; concrete identities live in a Genesis instance/version (A21, DECIDED). Concrete accounts are instance details, not trust roots (A24, DECIDED).
- Proposed:
  - the **model** is the set of rules in this document, once ratified: the bound set, amendment, integrity and ratification;
  - an **instance** (Genesis version N) is one Genesis Charter: the hashes of the bound artifacts, the immutable repository and owner identities (A27), the hash of version N-1 (none for version 1), and the ratification record;
  - instance 1 is drafted at step 8 (A14).
- Genesis and every verifier bind to the immutable repository identity, the immutable owner identity and the Genesis version/hash, never to a repository name, an owner display name or login, a branch or a tag (A27, DECIDED; its signing-identity clause is superseded by A49).

## 3. The bound set

The bound set is the B2 list (proposed), item by item, as the owner decided it: without row 9b (A49). "DM rows only" means that the content exists only as rows of the DM, with no document of its own.

| # | Item (B2, proposed) | Source | State now | Needed before step 8 can bind it |
|---|---|---|---|---|
| 1 | Concept hash + errata hash | concept v0.5 (A22); `CR-001-concept-errata.md` | Both exist. CR-001 is approved by the owner with E4 and E10 open (CR-001 line 3; E4: CR-001 line 13, working record DEF-0018; E10: CR-001 line 19, working record DEF-0008). A51 needs a further errata, CR-002 (working record DEF-0019) | Nothing. Binding fixes errata texts that are expected to change; a later change to the errata is bound by a genesis amendment (B1, proposed; section 5) |
| 2 | Constitution | its form: concept §6.1 (lines 327-397) | Drafted, proposed: `constitution.md` revision 1 (A50; section 3.1); not approved | Its articles written, each declaring how it is checked (concept line 331) |
| 3 | Authority model | A21, A27, A28, A31, A36, A49, A51 (DECIDED); A41 | DM rows only | A written statement, which may be a part of the Charter (section 3.2) |
| 4 | Governance-boundary abstraction + "every label must be measured" | A2, A4, A25, A26, A29 (DECIDED); DM section E; the DM label rule | DM rows only | A written statement; its labels as section 8 states them |
| 5 | Assurance model | `assurance-model.md` revision 2 (proposed) | Exists, proposed; its §10 owner points are open; for the self-build, A51 changes parts of it | Its ratification (section 7) |
| 6 | Conformance methodology + initial scenario-set hash | A19 (DECIDED, the primitive); B10, B14 (proposed) | Drafted, proposed: `conformance-methodology.md` and `conformance-scenarios-initial.md` revision 1 (A50); no scenario approved | The methodology written; each scenario approved and hashed (A19 conditions 1-2; for the self-build, approval under A51 waits for CR-002: `conformance-methodology.md` §5, proposed) |
| 7 | Bootstrap governor identity + succession rule | A20, B2 (proposed); section 3.3 | Specification drafted, proposed: `governor-spec.md` revision 1 (A50); no code before step 9 (A14) | A definition (section 3.3); its identity can exist only once its code exists, from step 9 on |
| 8 | Change classes + amendment procedure | B1 (proposed); section 5 (proposed) | DM rows only; no amendment procedure was written before this document | Section 5, ratified |
| 9a | A27 identities: immutable repository id, immutable owner id | A27 (DECIDED); A21, A24 (DECIDED) | Not recorded in any artifact | Recorded at step 8 |
| 9b | A27 signing-key fingerprints | A49 (DECIDED) | Dropped by the owner: no owner signing key is created or bound | — |

### 3.1 Founding laws

- What Claude's step-7 question (quoted in A48) called "các luật nền" (Claude's wording, not an owner decision) is in two places:
  - the concept's four invariant laws (concept lines 67-76), bound through the concept hash (row 1);
  - the project constitution (row 2).
- Proposed reading (Claude's): B2's "constitution" is the AIEOS project's own constitution, in the form of concept §6.1, applied to the AIEOS self-build. It is to be written at step 7 (A50); for the self-build it is approved by the decision agent under A51 once the owner approves CR-002 covering concept line 409.

### 3.2 Authority model and the decision agent

- The model is the A21 chain: Authority Role → Human Principal → Authentication / Signing Mechanism → Authority Action → Recorded Evidence (A21, DECIDED). With no owner signing key (A49), the mechanism is authentication only.
- The decision agent (A41) is not a Human Principal. For the self-build, A51 makes it approve in the owner's place: its approval is a delegated approval with advisory effect, recorded "decided by: decision agent (A41, A51)" (A51). Whether the delegation enters the Genesis authority model as a role stays open (A41; section 9).

### 3.3 Bootstrap governor (proposed, Claude's reading)

- Definition: the bootstrap governor is the part of the bootstrap implementation (A9, DECIDED: Python 3, standard library only) that evaluates acceptance while AIEOS governs its own build: it reads the bound rules and the records, and computes the acceptance decision. A29 (DECIDED) lists the governor as part of the evaluator, so a change to it is a change to the evaluator. The detailed specification (A50) settles whether it also emits the execution decisions of A15 (DECIDED: bootstrap and native emit the same JSON decision contract).
- Identity: its pinned version, identified by a content hash.
- Succession rule: per capability, as A11 (DECIDED) states: a native successor takes over a capability only when conformance shows it equivalent to or stricter than the bootstrap. Successors are ratified, not bound (B2, proposed); the succession rule is bound.

### 3.4 Bound items that did not exist

- Rows 2, 6, 7 and 9b had no artifact, and no A14 step wrote them before step 8. Revision 1 listed three options: (a) write them before step 8; (b) bind what exists and add the rest later; (c) bind placeholders. Claude recommended (b), and question 2 of Claude's message (decision file D-068) asked the owner yes or no on it.
- The owner chose option (a) without the keys: rows 2, 6 and 7 are written now, at step 7, with the governor as a specification only (A50), approved under A51 once the owner approves CR-002 (A51 item (5)); row 9b is dropped (A49).
- Consequences: work is added at step 7 (A14, A50); the governor's identity still exists only from step 9 (row 7); with no signing key, the authority signing identity that A27 named is never bound (section 6).

## 4. Ratified, not bound

- B2 (proposed) lists: Master Plan, ADRs, later scenarios, governor successors, the active boundary implementation, measurement results.
- The Master Plan is ratified by Genesis, not bound by it (A13, DECIDED).
- **Conflict.** B2 (proposed) lists the active boundary implementation as ratified, while A14 (DECIDED) says Genesis must not ratify an unmeasured trust boundary. Proposed reading: instance 1 does not ratify the active boundary implementation (A2, DECIDED: `github-public-free`, its capabilities TBD) as a trust boundary; it records it as the current implementation, unmeasured and advisory (section 8). Open point at ratification (section 9).

## 5. Versioning and amendment (proposed)

- The concept stays byte-identical; corrections go into a separate normative errata document (CR-001), written in Vietnamese (A22, DECIDED).
- Proposed procedure:
  1. A change to a bound artifact is a `genesis_amendment` (B1, proposed); so, proposed here, is a change to the bound set. It is one isolated change, with nothing else in it.
  2. It is judged under the rules of the Genesis version in force, not under the rules it introduces (B1, proposed: "judged under the previous Genesis version").
  3. It is ratified by the owner in their own words, or, for the self-build, by the decision agent under A51 once CR-002 is approved; either record is advisory while P-CRED is FAIL (A31, A41).
  4. It produces Genesis version N+1, whose Charter records the hash of version N, so that versions form a chain (A27 binds the Genesis version/hash).
  5. The agent never changes a bound artifact directly; it proposes a change request (proposed; concept line 200 states it for Intent and the Constitution).
- Closing CR-001 E4 or E10 later, or approving CR-002 after instance 1 is ratified, is an errata change (A22) whose new hash is bound by such an amendment (row 1).

## 6. Integrity and identities

- A27 (DECIDED): verifiers bind to the Genesis version/hash; a tag is not proof of owner authorization, which requires a verified signature or other authority evidence. With no signing key (A49), only "other authority evidence" remains.
- No owner signing key will be created (A49; A23 superseded, B11 (proposed) superseded; C14 not pursued), and no integrity anchor is established (C11, TBD: a place for the Genesis hash that the agent cannot rewrite).
- So no Genesis instance can claim cryptographic integrity or an authenticated ratification; this is lasting, not temporary. Proposed: its hash is recorded outside it (in the ratification record, and in version 2 as the hash of version 1); the anchor (C11) stays open.
- This document does not design C11.

## 7. Ratification at step 8

- "Chưa sang bước 8" holds now (A50). For the self-build, once the A50 artifacts are done, moving to step 8 is the decision agent's under A51, relayed to the owner in plain words before any step-8 work; ratifying a Genesis instance waits until the owner approves CR-002 (A51).
- Proposed:
  - at step 8 Claude drafts instance 1, and the approver (the owner, or the decision agent under A51 after CR-002) answers yes or no on it; nothing is bound without that yes;
  - the record of ratification names who approved, with date and transcript line;
  - while P-CRED is FAIL, that record is advisory as an authority claim (A31; A41 for delegated approvals; MP §1.4 and line 55).
- Appearing in the Charter makes no PROPOSED or TBD row an assumption (DM rule 1). PROPOSED content ratified at step 8 becomes DECIDED (the owner's yes) or DELEGATED (the decision agent's yes under A51) only through that yes; TBD rows stay TBD until measured (DM rule 2).

## 8. Relation to the unmeasured trust boundary

- Measured: only the minimal P-CRED baseline, FAIL (DM section D; C2), and C13 is FAIL by implication. Every other section C row is TBD. No hardening is applied and no re-measurement is due (A46, DECIDED).
- Proposed, from the DM label rule ("Anything unmeasured defaults to advisory") and A31:
  - every authority claim of a Genesis instance (its ratification, its amendments, approvals under it, owner or delegated) is advisory;
  - every governance label it carries is the measured one or, if unmeasured, advisory; "every label must be measured" (B2, proposed) is bound as a rule, not as a claim that labels are measured;
  - it ratifies no boundary implementation as a trust boundary (section 4);
  - measurement results, when they come, are ratified, not bound (B2, proposed), and change only the labels.
- For the self-build under A51, the same model family writes, checks and approves, so A29 cannot hold by design; it stays a target, like C13 (A51).
- Proposed reading of A14's reason, given A44: Genesis meets "must not ratify an unmeasured trust boundary" by recording the boundary as unmeasured and advisory, not by waiting for the measurements; the measurements resume only if the owner raises them (A44, Claude's wording in that row; A46).

## 9. Open points

Answered at the end of step 7:
1. The bound set of section 3: yes, without the signing key (A49).
2. Bound items that did not exist: rows 2, 6 and 7 written now, the governor as a specification only (A50); row 9b dropped (A49).
3. Moving to step 8: not yet (A50); later, for the self-build, the decision agent's under A51.

Open:
4. The AIEOS constitution's articles and checks: drafted in `constitution.md` (proposed; A50); approved under A51 after CR-002 (section 3.1).
5. Whether the A41 delegation enters the Genesis authority model, "for the owner to decide then" (A41, Claude's wording in that row; section 3.2).
6. The active boundary implementation: whether instance 1 records it as unmeasured and does not ratify it as a trust boundary (proposed reading, section 4).
7. Ratifying this model, including the amendment procedure of section 5 and B1 (proposed), at step 8 (section 7).
8. The integrity anchor (C11); the signing keys are dropped (A49).
9. CR-002, the further errata A51 requires, to be approved by the owner (DEF-0019).
10. The open points of the assurance model (its §10), which travel with row 5.

## 10. Not covered

- The Genesis Charter itself, its hashes and its concrete identities (step 8).
- The texts of the constitution, the conformance methodology, the scenarios and the governor specification (separate documents, A50: `constitution.md`, `conformance-methodology.md`, `conformance-scenarios-initial.md`, `governor-spec.md`), and the governor's implementation.
- C11 design; measurements; C13 and B17 (proposed).
- Changes to other documents (the DM beyond the pointer notes, the MP, the assurance model beyond its header note, CR-001), B3-B5 (proposed) included.
- Code (A14: none before step 9).
