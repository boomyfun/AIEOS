# Master Plan of the AIEOS self-build

> - **Status:** revision 3. Whether it is ratified is recorded in DM section F, not in this file. It plans; it decides nothing that a decision matrix (DM) row or a bound document decides, and it approves no specification, task or owner act.
> - **Drafted under:** decision agent decisions D-136 (the drafting plan) and D-133 (A14 step 9 started, DM row F9); revision 2 under decision D-174 (C5); revision 3 under decision D-251 (C1). Decision files are kept outside the repository (`docs/WORKING-RECORDS.md`).
> - **Path:** `docs/plan/master-plan.md` is interim. The layout is settled (DM B7 with A59; CR-001 E4, closed by Genesis version 2, A60; specification 2's layout part, F16), but the file moves only when a core exists to write `.aieos/` (constitution INV-004; specification 2 §10 point 2), by a later change.
> - **Sources:** "Concept line N" is a line of `AIEOS-concept.md` (v0.5, byte-identical, A22). "DM A13" is a row of `docs/pre-genesis/decision-matrix.md`. Statuses are those the DM rows record, not a document's own status line (charter §6).

## 1. Status and authority

- This is level 3 of the plan hierarchy: concept → Genesis → Master Plan → milestones → task contracts (DM A13, DECIDED). There is no ROADMAP.md (A13).
- The Master Plan is ratified by Genesis, not bound by it (A13; DM B2, proposed; `genesis-model.md` §4). Genesis binds trust roots, not the project plan (A20).
- No DM row names who ratifies it. On the decision agent's reading in D-136 (A51 item (2); CR-002 part 1 and Đ7, which delegate approving requirements and milestones, concept line 624; `assurance-model.md` §6), for gov-AIEOS (A53) it is a delegated approval of the decision agent in the owner's place, recorded as a DM section F row with advisory effect (A31, A41) and relayed to the owner in plain words. The owner can revoke the delegation in one sentence, with immediate effect (A55).
- Ratifying this plan approves no specification, no task, no change to a bound document and no act that the owner keeps (section 9).

## 2. Scope

- In scope: the gov-AIEOS self-build up to AIEOS v0.1, "Claude Code không phá project của tôi" (concept lines 934-951, with CR-001).
- The first user is the owner, building AIEOS with AIEOS (A43 Q4); the v0.1 measurement project is the self-build (CR-001 E5; DM B13). Agents pull their work from AIEOS (A43 Q6; concept §17 question 3).
- Runtime neutrality for v0.1 is shown by the adapter contract, a T0 manual adapter, a replay adapter and conformance (A12, DECIDED); the second vendor adapter of concept line 946 is out of v0.1 (CR-001 E2).
- AIEOS v0.1 runs one task at a time (concept line 951). Drafting a specification is not a task (section 5).
- Horizons only, not planned here: v0.2 Assurance (lines 953-954), v0.3 Parallel (lines 956-957), v1.0 Team (lines 959-960); the P2 deferrals (line 999).

## 3. Starting state

- Genesis instance 2 (Genesis version 2) is in force, with advisory effect: the owner's yes on its changed texts (DM A60) and the decision agent's ratification, in the owner's place, of its unchanged items (DM F14). It binds the concept and its errata CR-001 and CR-002 (CR-001 E4 closed; E10 closed for gov-AIEOS), the constitution, the authority model, the governance-boundary abstraction, the assurance model, the conformance methodology with the initial scenario set (set version 2, 32 scenarios, bound but not frozen as executable fixtures; F4 for the 30 of set version 1), the bootstrap governor specification and succession rule, and the change classes with the amendment procedure (`docs/genesis/genesis-charter-v2.md` §2). Instance 1 stays recorded (DM F7, F8).
- The governor's identity, a content hash of its code, does not exist yet (charter v2 §2, item 7). No checker exists (constitution §2, §6).
- No code exists. A14 step 9 has started (F9); M0 and M1 have exited (decisions D-154 and D-163).
- The minimal P-CRED baseline is FAIL and C13 is FAIL by implication; no hardening is applied (A46). Anything unmeasured is advisory (the DM label rule; A31; `assurance-model.md` §9); so is every governor and CI output (`governor-spec.md` §10).

## 4. Milestones

For each milestone, what is known now: goal, inputs, deliverables, exit, the owner acts it needs (named here, decided only when the milestone reaches them) and the working records it touches. The rest is set when the milestone starts. Specifications are documents of their own, one per concept §18 entry (lines 987-997); none is drafted here.

**M0. The CI channel and its first checks.**
- Goal: the channel in which V0 and V1 run on the evaluated commit (`assurance-model.md` §7, option 1, chosen in D-062), in place before the first task (section 5).
- Deliverable: a workflow under `.github/` that records the evaluated commit and its changed paths, and runs the first checks that the first tasks' tool entries need, at least the secret scanner of SEC-001 and the pattern rules of SEC-002 (constitution §3). Claude drafts it with plain-words instructions; the decision agent reads it.
- Owner act: creating it, or permitting it directly (constitution SEC-003; A51 item (4)). Whether option 1 needs a CR-001 entry, given concept line 729, is the owner's (`assurance-model.md` §7, §10 point 3).
- Exit (M0's own rule; it has no task): the owner has created the channel, and a run's records are readable. Its runs stay advisory: the job runs agent-modified code (A29; C7, TBD).

**M1. Foundation specifications and the risk rules.**
- Goal: §18 specification 1, State & Event Model (line 991), and specification 2, the `.aieos/` File Format (line 992).
- Deliverables: the two specifications; within them, the field names of the decision contract (`governor-spec.md` §11 point 8; A15), the task contract format (concept §7.1, lines 425-484) and the record formats the governor reads and writes (`governor-spec.md` §3.3). The self-build's risk rules (concept lines 591-601), as an approved, versioned policy (CR-002 Đ2; A35: classification fails closed): without them a change matches no rule and gets no decision (`governor-spec.md` §4 rule 8).
- Owner act: specification 2 proposes the layout (DM B7, proposed) and a text for CR-001 E4; concept errata are the owner's (A22; CR-002 part 8). The layout part stays proposed until the owner closes E4. Done: the owner said yes (A59), Genesis version 2 carries the E4 text (A60), and the layout part is baselined (DM F16).
- Exit: the specifications and the policy approved under A51 (DM B9, proposed: "no task is ACCEPTED against an unbaselined spec").
- Records: DEF-0018 (done).

**M2. The bootstrap governor and the conformance runner.**
- Goal: the first code: the acceptance decision of `governor-spec.md`, and the runner of the frozen scenarios (A19; `conformance-methodology.md` §6).
- Inputs: M0, M1; the 19 scenarios of the Verification capability (ACC-01 to ACC-17, ADV-01, ADV-03; `conformance-scenarios-initial.md`).
- Deliverables: the governor; the runner; the executable fixtures of those scenarios, written in tasks of their own, never by a governor task (constitution GOV-002), each frozen by a fixture-freeze approval on its hash (DM B1, B10); a record store for the governor's records until the event log of M3 exists (open, section 10).
- Constraints: Python 3, standard library only, disposable (A9; constitution INV-002, INV-003); no model call and no code writing (INV-001).
- Exit: the Verification scenarios pass in the CI channel, and the other 13 are `NOT_RUN` until their milestone (`conformance-methodology.md` §3); the first version is accepted and pinned (section 5, points 5 and 6).
- The governor is one of AIEOS's security-critical parts (CR-002 Đ9; `assurance-model.md` §5); the risk rules class its tasks at least high (R3; risk rules §5), so each needs the high profile, with the pair of reviews for the cross-model entry (section 6). Owner point: the first version's acceptance is the owner's, asked once when that version exists (decision D-166).

**M3. Resume Check and decision engine.**
- Goal: §18 specification 3 (line 993) and its code: the eight deterministic checks with declared and derived read-sets (line 941), the execution decision kept apart from the acceptance decision (line 943; A15), the event log with idempotent event ids, fencing and recovery between Git and the event log (line 950), and the core's single writer (concept line 858; constitution INV-004).
- Constraints: built in the bootstrap: Python 3, standard library only, disposable (A9; constitution INV-002, INV-003), as ruled in decision D-251; its code contracts name INV-002 and INV-003.

**M4. Verification and evidence.**
- Goal: §18 specification 4 (line 994) and its code: V0 to V2, evidence bound to a commit, the default profiles for low and medium risk (line 947); deterministic reconciliation of the constitution, the scope and stale evidence (line 948); rule-based risk and autonomy L1 to L2 (line 949), the latter built as a product feature that gov-AIEOS uses only as A54 point 2 and `assurance-model.md` §6 allow.
- Constraints: built in the bootstrap: Python 3, standard library only, disposable (A9; constitution INV-002, INV-003), as ruled in decision D-251; its code contracts name INV-002 and INV-003.

**M5. Adapters.**
- Goal: §18 specification 5 (line 995): the adapter contract, the Claude Code adapter (line 945: hooks that enforce the write-set and the shell allowlist, block `git push`, record the observed read-set; advisory until measured: A25, C6, CR-001 E1), the T0 manual adapter and the replay adapter (A12).
- Owner act: installing hooks or changing Claude Code settings (A51 item (4)); a task that carries out or changes such an act is approved by the owner (CR-002 part 4 limit 5).

**M6. MCP protocol and Work Orders.**
- Goal: §18 specification 6 (line 996): about eight tools (line 944) through which agents pull Work Orders (A43 Q6); the Context Compiler v1, graph-based (line 942; concept §7.3; its placement here is open, section 10).

**M7. CLI and the zero-friction path.**
- Goal: §18 specification 7 (line 997): `aieos init`, `aieos import`, `aieos run` (lines 939-940), `aieos status` (line 800); the zero-friction path (concept §11).

**M8. Self-hosting.**
- Goal: AIEOS governs its own build, per capability, through the stages of A11 that v0.1 reaches (open until the review point at M4's exit, section 5); the delegation continues once AIEOS governs its own build (A55).
- Exit: the v0.1 goal measured as section 7 says.

## 5. Order and dependencies

- Milestones follow the concept's specification order (line 987: "theo thứ tự") and A10's sequence, which puts the Python bootstrap first. Drafting a specification is not a task: it has no task contract and no acceptance decision; a specification is approved under A51 (B9). So M1 may be drafted while M0 waits for the owner. A milestone with tasks starts when the one before it has exited.
- Bootstrap order (proposed reading):
  1. This plan is ratified and on GitHub.
  2. M0: the CI channel is in place before the first task (`assurance-model.md` §7: "The CI channel is to be in place before the first task at step 9"). Creating it is the owner's act (point 1 of section 9). The first checks come with it (M0), so the first tasks' tool entries can be met; until a checker exists, its entries are not met (constitution §2) and the task stays at INSUFFICIENT_EVIDENCE.
  3. M1: the specifications and the risk rules the first code task needs are approved under A51.
  4. Until the governor exists, each task is accepted by one approval of the decision agent (CR-002 Đ7), with the evidence the assurance model requires, except where CR-002 part 4 limits 5 or 8 make the owner the approver (section 6). A tool entry is met only by records from the CI channel (constitution §4), never by local runs. Records written before AIEOS governs its own build carry their recorder and are not authoritative (CR-001 E3; constitution INV-004).
  5. The first governor version has no base version to judge it (`governor-spec.md` §8 point 1 assumes one). It is accepted by the owner (decision D-166: it puts into force the rules on who may approve what), after the Verification scenarios have passed in the CI channel (`governor-spec.md` §8 point 3), and is pinned by its content hash.
  6. Until its identity is bound, a change to the governor is `critical_cr` (`governor-spec.md` §8 point 2). Binding the identity (charter item 7) is a Genesis amendment (`genesis-model.md` §5), decided under A51 unless it touches an owner-kept part. From the pin on, the pinned governor, taken from the base, runs in the CI channel (`governor-spec.md` §7) and judges every change to itself (§8 point 1); its decisions stay advisory (§10).
- Points 2 (the first checks in M0) and 4 to 6 are readings, not bound text. The decision agent ruled points 2 and 4 in decision D-137 and points 5 and 6 in decision D-166.
- The bootstrap's scope (decision D-251): the capabilities of M2 to M4 are built in the bootstrap (A9), and this is its written scope until a further ruling. Not ruled: whether M5 to M7 are bootstrap or native; where the benchmark, the stack ADR and the native stack come (A8, A10, C12; CR-001 E6); and the A11 stages M8 reaches. These are ruled at a review point at M4's exit, before any M5 code contract, with a benchmark plan drafted by then (a document only; nothing runs). The benchmark's criteria and weights are the owner's (A8), asked once when they are drafted. At the review point, an option that keeps the whole of v0.1 in the bootstrap, or that starts capabilities native without A11's stages, goes to the owner as a plain question.

## 6. Acceptance of tasks and milestones

- gov-AIEOS starts at L1: no auto-accept, and each task gets one approval, the decision agent's at every risk level, except a task under CR-002 part 4 limit 5 or limit 8 and the first governor version (decision D-166), which the owner approves (`assurance-model.md` §6, §8; CR-002 Đ7; `governor-spec.md` §4 rule 5). A raise to L2 is only as A54 point 2 allows.
- The approval needs the task's evidence requirement complete (`assurance-model.md` §3); an approval never stands in for evidence (A36).
- For gov-AIEOS, a high or critical task has its default profile from v0.1 (Genesis version 2; `assurance-model.md` §5), and its cross-model entry is met only by the pair of reviews: a way-2 review by a Claude model other than the implementer's, and a separate review of the decision agent that stands for that entry (A59, A60; `assurance-model.md` §3). Without the whole profile it stays at INSUFFICIENT_EVIDENCE. The plan sets no risk class and lowers none (CR-002 part 4 limit 8).
- A milestone with tasks exits when its deliverables' tasks are accepted and the decision agent approves the milestone (CR-002 Đ7, concept line 624; `assurance-model.md` §6). M0 and M1 exit by their own rules (section 4).
- Nothing here relaxes a constitution article or an evidence requirement (CR-002 part 4 limit 8).

## 7. What v0.1 measures

- The goal (concept line 936): on a real project of about 100 tasks, AIEOS catches changes that are wrong although the agent reports them done, with low human time.
- For gov-AIEOS the project is the self-build (CR-001 E5). The metrics are those of concept §12 (lines 810-821), recorded from the event log from M8 on.
- CR-002 K6 (Claude's reading recorded there): human time per task does not reflect the product's L1 mode, and metrics that need a human judge are judged by AI here; so these results are no basis for the product's L1 default or for raising the product's level.
- These are product metrics. Trust-boundary measurements (P-CRED, P-GH, P-LOC, C13) are a different thing and stay the owner's (A30, A46; section 9).

## 8. When code starts

- "Code" here means any program text added to the repository: AIEOS's own source, tests, fixtures, checkers, scripts and workflows.
- The one exception is the M0 workflow with its first checks. It is drafted after this plan is ratified, read by the decision agent, and written to the repository only by the owner or with the owner's direct permission, because the bound assurance model puts the channel before the first task (`assurance-model.md` §7).
- No other code before all of these hold: the drafting plan approved (D-136); this plan ratified and on GitHub; the readings of section 5 ruled; the CI channel in place (M0); the specifications and the risk rules the first code task needs approved (M1), with nothing in that task depending on the proposed layout; the first code task's contract approved by the decision agent; and the start of code relayed to the owner in plain words. That approval and relay are the point at which code may start.
- The first code task's contract has the twelve parts of concept §7.1 (line 473): Objective, Input state, Write-set, Read-set, Forbidden, Dependencies, Constitution, Acceptance criteria, Capabilities, Budget (with the retries the governor reads), Verification plan and Exit conditions; and the fields `traces_to` (an approved specification), `risk` and `autonomy` (L1). Its write-set has new paths only, nothing under `.github/` or `.aieos/`; its constitution articles include at least INV-001, INV-002, INV-003, SEC-001 and SEC-002; its capabilities allow no push and no network. It declares whether it carries out or changes an act that A51 item (4) keeps; with A56, that declaration is how such an act is recognised (`governor-spec.md` §3.2), and a task that declares one is approved by the owner (CR-002 part 4 limit 5). Its text is written later, as its own request.

## 9. Listed, not planned: what stays the owner's

Not complete: A51 item (4), CR-002 parts 4 and 8 and `genesis-model.md` §5 point 3 govern.
1. Creating or changing anything under `.github/` (SEC-003; A51 item (4)).
2. Claude Code settings, hooks, `CLAUDE.md` and the agents folder; any act at a permission prompt (A51 item (4)).
3. Trust-boundary measurements, the measurement protocol and hardening (A30, A46; A51 item (4)); working records DEF-0004 and DEF-0005 are carried as the owner's and not raised (D-038).
4. Concept errata (A22; CR-002 part 8): CR-001 E10 for AIEOS projects, any later erratum, and whether `assurance-model.md` §7's choice needs an entry. CR-001 E4, and E10 for gov-AIEOS, are closed by Genesis version 2 (A60).
5. Autonomy: raising a class beyond what A54 point 2 gives the decision agent, the auto-accept policy, any bound above L2, "sufficient assurance", and L2 while P-CRED or C13 is not PASS (`assurance-model.md` §10 point 2).
6. Business decisions: historical intelligence and open source (concept lines 905, 960; §17 questions 1 and 2; CR-002 part 8).
7. Visibility, accounts, tokens and credentials, money, publishing outside the repository, sending messages, history rewrite or force-push, deleting refs or objects on GitHub (A51 item (4)).
8. Approving a task under CR-002 part 4 limit 5 (it carries out or changes an act of A51 item (4)) or limit 8 (it weakens an evidence requirement).
9. Any change to who may approve what or to the delegation, to bound-set items 1 and 3, and, until the owner says otherwise, to item 5 (`genesis-model.md` §5 point 3).

## 10. Open items

- DEF-0008, CR-001 E10 (cross-model review): closed for gov-AIEOS by Genesis version 2 (A59, A60): high and critical tasks have their default profiles from v0.1, with the pair of reviews (section 6); open for AIEOS projects, which this plan does not cover (section 2).
- DEF-0011: the §18 specifications are scheduled by this plan once it is ratified (M1 to M7); open source and historical intelligence stay the owner's (section 9).
- DEF-0018, the layout: done (A59, A60; DM B7 note, F16); the interim documents move only when a core writes `.aieos/` (specification 2 §10 point 2).
- DEF-0020, the option-b product documents (CR-002 part 9): outside the gov-AIEOS scope of section 2; they wait for the §18 specifications that their rules need (record formats in M1, approval flow in M7, evidence in M4); their placement is open.
- Readings ruled: section 5, points 2 and 4 (decision D-137) and points 5 and 6 (decision D-166); the M2 record store in direction (decision D-166: a records folder in the repository, written only through a reviewed change, and records re-fetched from the CI channel, each counting only as DM B5 allows), with its details left to the first M2 contract. Still for the decision agent to rule on: whether Context Compiler v1 belongs to M6 (the §18 table names no specification for it). Which milestones after M2 are built as bootstrap is ruled in part by decision D-251: M3 and M4 in the bootstrap, with the bootstrap's scope, the review point at M4's exit and the owner's approval of the benchmark's criteria in section 5; open until that review point: whether M5 to M7 are bootstrap or native, where the benchmark, the stack ADR and the native stack come (A8, A10, C12; CR-001 E6), and the A11 stages M8 reaches.

## 11. Change control

- A change to this plan is a `master_plan_update` (DM B1, DELEGATED as bound in instance 2, F14), approved by the decision agent in the owner's place under A51, with the limits of section 9.
- The plan is not bound, so the Genesis amendment procedure (`genesis-model.md` §5) does not apply to it.
- Each revision says what changed and why.
- Revision 2 (decision D-174 C5): carries Genesis instance 2 (A59, A60; F14), the settled layout (B7, F16), the risk rules revision 2 (F15) and the rulings of decisions D-137, D-154, D-163 and D-166 into sections 3 to 6, 9 and 10, and the path note; no milestone, order or owner-kept item is added or removed.
- Revision 3 (decision D-251 C1): records decision D-251's ruling in sections 4, 5 and 10: M3 and M4 in the bootstrap, the bootstrap's scope M2 to M4, the review point at M4's exit and the owner's approval of the benchmark's criteria (A8); the placement it leaves open is not decided here; no milestone, order or owner-kept item is added or removed.
