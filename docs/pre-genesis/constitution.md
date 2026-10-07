# AIEOS Project Constitution

> **Status: PRE-GENESIS DRAFT — proposed, not ratified.** A14 step 7 (DM A50: "thực hiện ngay bộ luật nền riêng của dự án"). Every article is a proposal. Its sources are DECIDED rows and rules of `decision-matrix.md` (DM), the concept, or CR-001; B-rows and the assurance, Genesis and conformance documents are cited as proposed, and working records as non-authoritative. Nothing here is a Genesis fact.
> Revision 1 — 2026-10-07: first version. Written under decisions of the decision agent (A41; scope set in decision file D-078); not an owner decision. Normative concept: `AIEOS-concept.md` v0.5 with CR-001 (A22). Rows are cited by ID, concept text by line ("concept line N").
> Effect: every enforcement named here is a **target**; until that enforcement is measured, its effect is **advisory** (DM label rule "Anything unmeasured defaults to advisory"; A31). For the self-build, A29 stays a target, unmet by design (A51 item (7)).

## 1. What this is

- The AIEOS project's own constitution: the articles that AI working on AIEOS must not break. This is Claude's reading of the "constitution" of B2 (proposed) and of genesis-model.md §3.1 (proposed). It is item 2 of the bound set the owner decided (A49), to be bound at step 8.
- Its form is that of concept §6.1 (lines 327-397): every article declares how it is checked (line 331). The concept's four invariant laws (lines 67-76) are to be bound through the concept hash (A49; genesis-model.md §3 row 1) and are not restated; some articles make them checkable for AIEOS's own code and cite them.
- It applies to the AIEOS self-build, the work on this repository (genesis-model.md §3.1, proposed).

## 2. Fields

Each article has the fields of concept §6.1: `id`, `category` (architecture, correctness, security, operational; lines 336-357), `rule`, `check` (deterministic, partial or judgment; lines 364-367), `tool` where the check is deterministic or partial (lines 339, 346), `evidence_required` where the check is partial or judgment (lines 347, 360), `severity`, `scope`, `applicability` and `enforcement` (mode, checker, cost; lines 377-386).
- Added here (Claude's additions): a `source` for each article; and a fifth category, `governance`, for articles about AIEOS's own records and bound artifacts.
- `tool` and `enforcement.checker` name the kind of checker. Checkers are built from step 9 (A14); none exists now. Paths are named by role, because the layout is open (B7, proposed; CR-001 E4; working record DEF-0018).
- `enforcement.mode` is the target mode; its effect is advisory until measured (header).
- Check times follow concept lines 389-395. An article whose scope is "all paths" runs at diff-time and at project-time.

## 3. Articles

### INV-001 · architecture · The core does not write code or run a model
- Rule: the AIEOS core decides, grants, checks and records; it writes no code, runs no model and owns no sandbox. Source: concept line 162.
- Check: partial; tool: dependency rule, the core's modules import no model-client library; evidence_required: [ai_review].
- Severity: blocking. Scope: the core's source tree. Applicability: implementation, refactoring. Enforcement: blocking, dependency_rule, cheap.

### INV-002 · architecture · Bootstrap in Python 3, standard library only
- Rule: the bootstrap implementation uses Python 3 and its standard library only. Source: A9.
- Check: partial; tool: import rule, every import resolves to the standard library or to the bootstrap's own modules, and no third-party code is copied in; evidence_required: [ai_review].
- Severity: blocking. Scope: the bootstrap source tree. Applicability: implementation, refactoring. Enforcement: blocking, import_rule, cheap.

### INV-003 · architecture · The bootstrap stays disposable
- Rule: "the bootstrap implementation is disposable and must not become an accidental second core". Source: A9 (its stated invariant); A11.
- Check: judgment; evidence_required: [human_review].
- Severity: blocking. Scope: the bootstrap source tree. Applicability: implementation, refactoring. Enforcement: blocking, review, expensive.

### INV-004 · architecture · Only the core writes the project-state directory
- Rule: only the AIEOS core writes the project-state directory, through a single writer; agents change it only through the protocol. Records written before AIEOS governs its own build carry their recorder and are not authoritative. Source: concept lines 858, 879; CR-001 E3.
- Check: partial; tool: path rule, an agent task's diff that touches the directory is rejected; evidence_required: [ai_review].
- Severity: blocking. Scope: the project-state directory. Applicability: all task types. Enforcement: blocking, path_rule, cheap.

### INV-005 · correctness · One decision vocabulary and one decision contract
- Rule: execution decisions use exactly the concept §5.3 vocabulary, and bootstrap and native emit the same decision contract. Source: A15.
- Check: partial; tool: schema rule on the decision contract, and the conformance scenarios (`conformance-scenarios-initial.md`, proposed); evidence_required: [property_test].
- Severity: blocking. Scope: the decision engine and the governor. Applicability: implementation, refactoring. Enforcement: blocking, schema_rule, cheap.

### INV-006 · correctness · Acceptance in A36's order
- Rule: acceptance is evaluated in the fixed order of A36, with ACCEPT only where policy explicitly allows it. Source: A36; concept lines 299-303 with CR-001 E8.
- Check: partial; tool: the conformance scenarios (proposed); evidence_required: [property_test].
- Severity: blocking. Scope: the governor. Applicability: implementation, refactoring. Enforcement: blocking, conformance, moderate.

### INV-007 · correctness · Only current evidence counts
- Rule: evidence counts only when bound to the evaluated commit SHA and the current intent version; stale evidence never satisfies an entry. Source: concept lines 728, 270, 667-669.
- Check: partial; tool: record schema rule (SHA and intent version present), and the conformance scenarios (proposed); evidence_required: [property_test].
- Severity: blocking. Scope: the governor and evidence records. Applicability: implementation, refactoring. Enforcement: blocking, schema_rule, cheap.

### INV-008 · correctness · An agent's word is not evidence
- Rule: a record whose source is the implementing agent never satisfies an evidence entry. Source: A18; concept line 706; law 3 (line 73).
- Check: partial; tool: source-class rule (B3, proposed), and the conformance scenarios (proposed); evidence_required: [property_test].
- Severity: blocking. Scope: the governor. Applicability: implementation, refactoring. Enforcement: blocking, source_class_rule, cheap.

### INV-009 · correctness · Append-only event log
- Rule: the event log is append-only, and every event has an idempotent ID. Source: concept lines 856, 874.
- Check: deterministic; tool: diff rule (no line of the log removed or changed) and uniqueness rule on event IDs.
- Severity: blocking. Scope: the event log. Applicability: all task types. Enforcement: blocking, diff_rule, cheap.

### INV-010 · correctness · Acceptance decisions are recomputable
- Rule: every acceptance decision records the records, policy version and level version it used, and can be recomputed from them. Source: A35 (policy and level version on each auto-accept); B5 and assurance-model.md §4 (proposed).
- Check: deterministic; tool: replay, recompute each decision from its cited records with the pinned ruleset and compare.
- Severity: blocking. Scope: the governor and its records. Applicability: implementation, refactoring. Enforcement: blocking, replay, moderate.

### INV-011 · correctness · No auto-accept in the self-build
- Rule: the self-build stays at L1, and an approval under A51 is a delegated approval, not an auto-accept. Source: A35; A51 item (2).
- Check: deterministic; tool: policy rule, the self-build's policy allows no auto-accept for any risk class.
- Severity: blocking. Scope: the policy. Applicability: all task types. Enforcement: blocking, policy_rule, cheap.

### GOV-001 · governance · The concept stays byte-identical
- Rule: `AIEOS-concept.md` v0.5 is never edited; corrections go only into separate normative errata documents written in Vietnamese, and an errata takes effect only with the owner's own yes. Source: A22; A41 revision-9 marker ("CR-002 and any other concept errata stay with the owner").
- Check: deterministic; tool: hash rule, the file's SHA-256 equals the concept hash to be bound at step 8 (A49); until then, the value at this revision, `19cfa266334aa20d1ac1bc15f5cf92d0fc6d3bbbd98c13cfcb42ad6fd5a8357c`.
- Severity: blocking. Scope: the concept file. Applicability: all task types. Enforcement: blocking, hash_rule, cheap.

### GOV-002 · governance · Implementation tasks do not edit scenarios
- Rule: an implementation task does not modify conformance scenarios at all. Source: A19 (4) ("an implementation task cannot modify scenarios to make its tests pass"); this stricter, checkable form is Claude's reading.
- Check: deterministic; tool: path rule, the scenario files are in every implementation task's forbidden set (concept line 445).
- Severity: blocking. Scope: the scenario files. Applicability: implementation, refactoring. Enforcement: blocking, path_rule, cheap.

### GOV-003 · governance · The evaluator is not taken from the change it judges
- Rule: the evaluator and its inputs, as A29 lists them, are taken from the base or a pinned ref, never from the change under evaluation. Source: A29, a target for the self-build (A51 item (7)); B17 (1) (proposed; not claimed sufficient, B17).
- Check: partial; tool: CI rule, evaluator paths are read from the base ref; evidence_required: [ai_review].
- Severity: blocking. Scope: the evaluator paths. Applicability: all task types. Enforcement: blocking, ci_rule, cheap.

### GOV-004 · governance · Bound artifacts change only by amendment
- Rule: a change to a Genesis-bound artifact is one isolated genesis amendment, judged under the Genesis version in force. Source: B1 (proposed); genesis-model.md §5 (proposed); the bound set of A49.
- Check: partial; tool: path rule, a change touching a bound artifact touches nothing else and declares its class; evidence_required: [human_review].
- Severity: blocking. Scope: the bound artifacts (A49). Applicability: all task types. Enforcement: blocking, path_rule, cheap.

### GOV-005 · governance · No unearned owner labels
- Rule: nothing is presented as an owner decision unless a DECIDED row records it, and owner words are attributed only to text quoted as such; delegated decisions are labelled "decided by: decision agent (A41)", or "(A41, A51)" under A51. Source: DM Axis 1 (DECIDED, DELEGATED); A41; A51 item (2).
- Check: judgment; evidence_required: [human_review].
- Severity: blocking. Scope: the DM, the records and the pre-genesis documents. Applicability: all task types. Enforcement: blocking, review, expensive.

### GOV-006 · governance · Measured and owner-quoted text stay the owner's
- Rule: no row is set to MEASURED except through the owner's approval of a measurement, and a DELEGATED change never alters an owner's quoted words or an earlier row's text. Source: DM rule 2; DM note of revision 21 (A51).
- Check: partial; tool: diff rule, a DM change by the agent only adds rows, markers or notes; evidence_required: [human_review].
- Severity: blocking. Scope: the DM. Applicability: all task types. Enforcement: blocking, diff_rule, cheap.

### SEC-001 · security · No secrets in the repository
- Rule: no secret, token, password or private key in the repository's contents, file names or commit messages. Source: concept lines 350-354 (example SEC-001); A41 (a secret scan of every pushed commit).
- Check: deterministic; tool: secret scanner.
- Severity: blocking. Scope: all paths. Applicability: all task types. Enforcement: blocking, secret_scan, cheap.

### SEC-002 · security · New public text stays public-safe
- Rule: new public text holds no e-mail address and no name of an unrelated project, as the public-safety rules of `docs/WORKING-RECORDS.md` (a non-authoritative working record) say; account names that a DECIDED row records (A24) are not affected. Source: WORKING-RECORDS "Public-safety rules"; A1 (public history is permanent); this article is Claude's addition.
- Check: partial; tool: pattern rule for e-mail addresses and credentials; evidence_required: [ai_review].
- Severity: blocking. Scope: all paths. Applicability: all task types. Enforcement: blocking, pattern_rule, cheap.

### SEC-003 · security · `.github/` only with the owner's own yes
- Rule: no file under `.github/` is added, changed or deleted without the owner's own yes. Source: A41 (a normal push carries no change under `.github/`); A51 item (4).
- Check: deterministic; tool: path rule, a change under `.github/` is routed to the owner.
- Severity: blocking. Scope: `.github/`. Applicability: all task types. Enforcement: blocking, path_rule, cheap.

### OPS-001 · operational · History rewrite only with the owner's own yes
- Rule: no history rewrite and no force-push without the owner's own yes. Source: A41, question 2 as answered "đồng ý tất cả.": "muốn xoá hẳn phải ghi đè lịch sử, và việc đó luôn phải hỏi bạn"; A51 item (4).
- Check: deterministic; tool: push rule, fast-forward only, no force flags (A41: "fast-forward only, with no force").
- Severity: blocking. Scope: the repository's refs. Applicability: all task types. Enforcement: blocking, push_rule, cheap.

### OPS-002 · operational · The owner's other acts stay the owner's
- Rule: no act that A51 item (4) keeps with the owner is done without the owner's own yes; among them, any change to the measurement protocol, deleting refs or objects on GitHub, and any change to visibility, settings, tokens or credentials. Source: A51 item (4); A41.
- Check: partial; tool: path rule (a change to `docs/pre-genesis/measurement-protocol.md` is routed to the owner) and push rule (no ref deletion); evidence_required: [human_review].
- Severity: blocking. Scope: all paths and the repository's refs. Applicability: all task types. Enforcement: blocking, path_rule, cheap.

### OPS-003 · operational · Unmeasured means advisory
- Rule: a control or label that has not been measured is shown as advisory, and what is not covered is shown. Source: DM label rule; A31; concept line 65.
- Check: partial; tool: pattern rule, every label other than advisory cites a MEASURED row; evidence_required: [ai_review].
- Severity: blocking. Scope: the DM, the pre-genesis documents and AIEOS's own reports. Applicability: all task types. Enforcement: blocking, pattern_rule, cheap.

## 4. Approval and change (proposed)

- This draft is approved by no one yet. The constitution is Intent: it changes only through a human-approved change request, and the agent only proposes (concept lines 200, 409). It is approved by the owner, or, for the self-build under A51, by the decision agent once the owner approves CR-002 (A51 item (5); working record DEF-0019).
- Once bound by Genesis, an article changes only by a genesis amendment (genesis-model.md §5, proposed).
- Turning `judgment` articles into `partial` or `deterministic` ones over time is the direction the concept gives (line 369).
- For the self-build, no record can now satisfy an `ai_review` entry: a review by another Claude model is a `same_lineage_review` record that never satisfies an entry (A47; B3 and assurance-model.md §2, proposed), and the cross-model entry is open (CR-001 E10). Who produces `human_review` evidence for the self-build is open too (assurance-model.md §2, proposed, says a decision of the decision agent never satisfies an entry; A51; CR-002). Partial and judgment articles therefore cannot reach a complete profile until these are settled.

## 5. Open points

1. Approval of this constitution: by the owner, or under A51 after CR-002 (section 4).
2. The `governance` category, a Claude addition to the concept's four.
3. The paths of every `scope`, once the layout is settled (B7, proposed; CR-001 E4).
4. Which records can satisfy `ai_review` and `human_review` entries for the self-build (section 4; CR-001 E10; CR-002).

## 6. Not covered

- The machine-readable constitution file and every checker (step 9; A14).
- Rules bound to a time or a process step, such as no code before step 9 (A14) and deciding irreversible actions on their own (A32); they are DM rows, not articles.
- Measurements, hardening and C13 control design (A46; B17, proposed).
- Any article for projects other than AIEOS itself.
