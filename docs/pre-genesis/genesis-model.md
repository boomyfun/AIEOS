# AIEOS Genesis Model

> **Status: PRE-GENESIS DRAFT — proposed, not ratified.** A14 step 7. Every rule here is a proposal unless it cites a DECIDED row of `decision-matrix.md` (DM, section A), the concept, or CR-001 as approved. This document binds nothing: binding is done by the Genesis Charter (A14 step 8), an owner act (A20, kept with the owner by A44; moving along A14 is the owner's under A41). Step 7 follows the owner's yes in A48 ("có, sang bước 7 nhưng để phiên sau.").
> Revision 1 — 2026-10-07. Written under decisions of the decision agent (A41; scope set in decision file D-067); it is not an owner decision. Normative concept: `AIEOS-concept.md` v0.5 with CR-001 (A22). Rows are cited by ID, concept text by line ("concept line N"), the measurement protocol as "MP".
> Effect: the only measurement made is the minimal P-CRED baseline, which is FAIL (DM section D); every authority claim described here is therefore at most **advisory** (A31; section 8).

## 1. Principle

- The concept v0.5 does not use the word Genesis. The DM adds it as a level of the plan hierarchy: concept → Genesis → Master Plan → milestones → task contracts (A13, DECIDED). In the concept, human authority and the constitution are the top two levels of the truth hierarchy (concept lines 175, 178).
- Genesis binds trust roots, not the project plan (A20, DECIDED). A20 calls its list a "Candidate bound set" and says "Exact contents stay PROPOSED (B2) until step 7". This document proposes the exact contents (section 3); deciding them is the owner's (A20; A41 keeps moving along A14 with the owner, and A44 keeps the owner acts of the later steps, A20 and A21 among them, with the owner).
- Proposed meanings (Claude's; B2, proposed, lists the two sets; B1, proposed, makes a change to a bound artifact a `genesis_amendment`): a **bound** artifact changes only through a genesis amendment (section 5); a **ratified, not bound** artifact is accepted under Genesis and changes through ordinary change requests.
- A14 (DECIDED) gives the reason "Genesis must not ratify an unmeasured trust boundary", and MP §6 (line 268) puts the Genesis model after the measurements. A44 records the owner's instruction to resolve the block and complete A14 ("giải quyết chỗ kẹt rồi hoàn thành nốt A14, …"); its sentences "Steps 2-4 of A14 no longer hold up the sequence" and "at steps 7 and 8 the trust boundary is presented as unmeasured" are Claude's wording in that row, not the owner's words. Proposed reading: Genesis may bind the boundary **abstraction** (section 3, row 4), but it ratifies no boundary **implementation** as a trust boundary (sections 4 and 8). The owner's yes to step 7 is A48. MP §6 line 268 is not amended; step 7 proceeds before the measurements on A44 and A48.

## 2. Model and instance

- Genesis binds the model and trust rules; concrete identities live in a Genesis instance/version (A21, DECIDED). Concrete accounts are instance details, not trust roots (A24, DECIDED).
- Proposed:
  - the **model** is the set of rules in this document, once ratified: the bound set, amendment, integrity and ratification;
  - an **instance** (Genesis version N) is one Genesis Charter: the hashes of the bound artifacts, the identities required by A27 that exist (section 3.4), the hash of version N-1 (none for version 1), and the owner's ratification record;
  - instance 1 is drafted at step 8 (A14).
- Every verifier binds to the immutable repository identity, the immutable owner identity, the Genesis version/hash and the signing-key fingerprints, never to a repository name, a login, a branch or a tag (A27, DECIDED).

## 3. The bound set

Proposed: the bound set is the B2 list (proposed), item by item. "DM rows only" means that the content exists only as rows of the DM, with no document of its own.

| # | Item (B2, proposed) | Source | State now | Needed before step 8 can bind it |
|---|---|---|---|---|
| 1 | Concept hash + errata hash | concept v0.5 (A22); `CR-001-concept-errata.md` | Both exist. CR-001 is approved by the owner with E4 and E10 open (CR-001 line 3; E4: CR-001 line 13, working record DEF-0018; E10: CR-001 line 19, working record DEF-0008) | Nothing. Binding fixes a CR-001 text that is expected to change; a later change to the errata is bound by a genesis amendment (B1, proposed; section 5) |
| 2 | Constitution | its form: concept §6.1 (lines 327-397) | Does not exist for the AIEOS project (section 3.1) | Its articles written, each declaring how it is checked (concept line 331) |
| 3 | Authority model | A21, A27, A28, A31, A36 (DECIDED); A41 | DM rows only | A written statement, which may be a part of the Charter (section 3.2) |
| 4 | Governance-boundary abstraction + "every label must be measured" | A2, A4, A25, A26, A29 (DECIDED); DM section E; the DM label rule | DM rows only | A written statement; its labels as section 8 states them |
| 5 | Assurance model | `assurance-model.md` revision 2 (proposed) | Exists, proposed; its §10 owner points are open | The owner's ratification of it (its §10 point 6) |
| 6 | Conformance methodology + initial scenario-set hash | A19 (DECIDED, the primitive); B10, B14 (proposed) | Does not exist; no scenario exists | The methodology written; each scenario approved by the owner and hashed (A19 conditions 1-2) |
| 7 | Bootstrap governor identity + succession rule | A20, B2 (proposed); section 3.3 | No DM row defines it; it does not exist (no code before step 9, A14) | A definition (section 3.3); its identity can exist only once its code exists, from step 9 on |
| 8 | Change classes + amendment procedure | B1 (proposed); section 5 (proposed) | DM rows only; no amendment procedure was written before this document | Section 5, ratified |
| 9a | A27 identities: immutable repository id, immutable owner id | A27 (DECIDED); A21, A24 (DECIDED) | Not recorded in any artifact | Recorded at step 8 |
| 9b | A27 identities: signing-key fingerprints (primary and backup) | A27 (DECIDED); A23 (target only); B11 (proposed); C14 (TBD) | **No owner signing key is recorded** | The keys created (anything touching accounts, passwords or security settings is the owner's, A41), and a verified signature, which is C14 |

### 3.1 Founding laws

- What Claude's step-7 question (quoted in A48) called "các luật nền" (Claude's wording, not an owner decision) is in two places:
  - the concept's four invariant laws (concept lines 67-76), bound through the concept hash (row 1);
  - the project constitution (row 2).
- Proposed reading (Claude's): B2's "constitution" is the AIEOS project's own constitution, in the form of concept §6.1, applied to the AIEOS self-build. Which articles it holds and how each is checked is open (section 9).

### 3.2 Authority model and the decision agent

- The model is the A21 chain: Authority Role → Human Principal → Authentication / Signing Mechanism → Authority Action → Recorded Evidence (A21, DECIDED).
- The decision agent (A41) is not a Human Principal, and its decisions are not Authority Actions of that chain. A41 says (Claude's wording in that row) that a delegated decision "is never an owner decision, never evidence of human authority (A31)", and that "Whether the delegation continues once AIEOS governs its own build (A35) or enters the Genesis authority model (A20, A21) is for the owner to decide then." This document proposes no answer (section 9).

### 3.3 Bootstrap governor (proposed, Claude's reading)

- Definition: the bootstrap governor is the part of the bootstrap implementation (A9, DECIDED: Python 3, standard library only) that evaluates acceptance while AIEOS governs its own build: it reads the bound rules and the records, and computes the acceptance decision. A29 (DECIDED) lists the governor as part of the evaluator, so a change to it is a change to the evaluator. Whether it also emits the execution decisions of A15 (DECIDED: bootstrap and native emit the same JSON decision contract) is open.
- Identity: its pinned version, identified by a content hash.
- Succession rule: per capability, as A11 (DECIDED) states: a native successor takes over a capability only when conformance shows it equivalent to or stricter than the bootstrap. Successors are ratified, not bound (B2, proposed); the succession rule is bound.

### 3.4 Bound items that do not exist yet

Rows 2, 6, 7 and 9b have no artifact, and no A14 step writes them before step 8 (A14). Options; the choice is the owner's and is asked at the end of step 7:

- **(a) Write them before step 8:** the constitution, the conformance methodology with its first scenarios, the governor definition, and the signing keys. Consequences: work and per-scenario owner approvals (A19 condition 1) are added before step 8, which changes the A14 plan (the owner's); the governor's identity still cannot exist before its code (A14), so row 7 stays unbound anyway.
- **(b) Bind what exists, add the rest later.** Instance 1 binds rows 1, 3, 4, 5, 8 and 9a (rows 3, 4 and 8 written into the Charter) and names rows 2, 6, 7 and 9b as "to be bound". Each later binding is a genesis amendment (B1, proposed; section 5) that the owner approves. Consequences: building starts at step 9 with the constitution, the conformance methodology, the governor and the keys unbound; the first tasks rest on the owner's approval at L1 (A35), which is advisory while P-CRED is FAIL (A31); until the fingerprints are bound, instance 1 does not bind the authority signing identity that A27 (DECIDED) names; each later binding is an owner act.
- **(c) Bind placeholders** (a stated "absent" value for each missing item). Consequences: a placeholder proves nothing and A27 binds identities, not placeholders; every later binding is still an amendment, so (c) adds a record without adding a control, and the authority signing identity that A27 names is still not bound.
- Recommendation (Claude's): **(b).** It changes no DECIDED row's text: A14 stays as it is, and A20 calls its list a candidate set. But until the fingerprints are bound by amendment, instance 1 does not bind the authority signing identity that A27 (DECIDED) names. Its later bindings use the amendment path of section 5, which rests on B1 (proposed) and is ratified with this model.

## 4. Ratified, not bound

- B2 (proposed) lists: Master Plan, ADRs, later scenarios, governor successors, the active boundary implementation, measurement results.
- The Master Plan is ratified by Genesis, not bound by it (A13, DECIDED).
- **Conflict.** B2 (proposed) lists the active boundary implementation as ratified, while A14 (DECIDED) says Genesis must not ratify an unmeasured trust boundary. Proposed reading: instance 1 does not ratify the active boundary implementation (A2, DECIDED: `github-public-free`, its capabilities TBD) as a trust boundary; it records it as the current implementation, unmeasured and advisory (section 8). Owner point at ratification (section 9).

## 5. Versioning and amendment (proposed)

- The concept stays byte-identical; corrections go into a separate normative errata document (CR-001), written in Vietnamese (A22, DECIDED).
- Proposed procedure:
  1. A change to a bound artifact is a `genesis_amendment` (B1, proposed); so, proposed here, is a change to the bound set. It is one isolated change, with nothing else in it.
  2. It is judged under the rules of the Genesis version in force, not under the rules it introduces (B1, proposed: "judged under the previous Genesis version").
  3. It is an owner act: the owner ratifies it in their own words, recorded as an Authority Action of the A21 chain; while P-CRED is FAIL this record is advisory (A31).
  4. It produces Genesis version N+1, whose Charter records the hash of version N, so that versions form a chain (A27 binds the Genesis version/hash).
  5. The agent never changes a bound artifact directly; it proposes a change request (proposed; concept line 200 states it for Intent and the Constitution).
- Closing CR-001 E4 or E10 later is an errata change (A22) whose new hash is bound by such an amendment (row 1).

## 6. Integrity and identities

- A27 (DECIDED): verifiers bind to the Genesis version/hash and the signing-key fingerprints; a tag is not proof of owner authorization, which requires a verified signature or other authority evidence.
- Now: no owner signing key is recorded (A23 is a target; B11 proposed; C14 TBD), and no integrity anchor is established (C11, TBD: a place for the Genesis hash and signatures that the agent cannot rewrite; it comes after C4, C10 and C14).
- So instance 1, if it is ratified before then, cannot claim cryptographic integrity or an authenticated ratification. Proposed: its hash is recorded outside it (in the owner's ratification record, and in version 2 as the hash of version 1); it records the missing keys and anchor as open; adding them later is a genesis amendment (section 5).
- This document does not design C11 or the keys.

## 7. Ratification at step 8

- Moving to step 8 and ratifying Genesis are owner acts (A14, A20; A41 keeps moving along A14 with the owner; A44 keeps the owner acts of the later steps with the owner).
- Proposed:
  - at step 8 Claude drafts instance 1, and the owner answers yes or no on it; nothing is bound that the owner has not said yes to;
  - the record of ratification is the owner's words, with date and transcript line, recorded as an Authority Action (A21);
  - while P-CRED is FAIL and C14 is TBD, that record is advisory as an authority claim (A31; MP §1.4 and line 55: Genesis signatures are at most advisory).
- Appearing in the Charter makes no PROPOSED or TBD row an assumption (DM rule 1). PROPOSED content that the owner ratifies at step 8 is decided only through that yes; TBD rows stay TBD until measured (DM rule 2).

## 8. Relation to the unmeasured trust boundary

- Measured: only the minimal P-CRED baseline, FAIL (DM section D; C2), and C13 is FAIL by implication. Every other section C row is TBD. No hardening is applied and no re-measurement is due (A46, DECIDED).
- Proposed, from the DM label rule ("Anything unmeasured defaults to advisory") and A31:
  - every authority claim of a Genesis instance (its ratification, its amendments, approvals under it) is advisory;
  - every governance label it carries is the measured one or, if unmeasured, advisory; "every label must be measured" (B2, proposed) is bound as a rule, not as a claim that labels are measured;
  - it ratifies no boundary implementation as a trust boundary (section 4);
  - measurement results, when they come, are ratified, not bound (B2, proposed), and change only the labels.
- Proposed reading of A14's reason, given A44: Genesis meets "must not ratify an unmeasured trust boundary" by recording the boundary as unmeasured and advisory, not by waiting for the measurements; the measurements resume only if the owner raises them (A44, A46).

## 9. Open owner points

Asked at the end of step 7 (at most three yes/no questions):
1. The bound set of section 3 (A20; B2, proposed).
2. Bound items that do not exist yet: option (b), "Bind what exists, add the rest later" (section 3.4), each later binding a genesis amendment that the owner approves.
3. Moving to step 8 (A14).

Open, not asked now:
4. The scope of the AIEOS constitution: its articles and checks (section 3.1).
5. Whether the A41 delegation enters the Genesis authority model, "for the owner to decide then" (A41; section 3.2; related: assurance model §10 point 7).
6. The active boundary implementation: whether instance 1 records it as unmeasured and does not ratify it as a trust boundary (proposed reading, section 4).
7. Ratifying this model, including the amendment procedure of section 5 and B1 (proposed), at step 8.
8. When the signing keys and the integrity anchor are created (A23, B11 (proposed), C11, C14; anything touching accounts, passwords or security settings is the owner's, A41).
9. The open points of the assurance model (its §10), which travel with row 5.

## 10. Not covered

- The Genesis Charter itself, its hashes and its concrete identities (step 8).
- The texts of the constitution's articles, the conformance methodology, the scenarios, and the governor's implementation.
- C11 and key design; measurements; C13 and B17 (proposed).
- Changes to other documents (the DM beyond a pointer note on B2, the MP, the assurance model, CR-001), B3-B5 (proposed) included.
- Code (A14: none before step 9).
