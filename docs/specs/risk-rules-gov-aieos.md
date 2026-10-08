# The self-build's risk rules (gov-AIEOS), policy version v1

> - **Status:** revision 2. Whether it is approved is recorded in DM section F, not in this file. It decides nothing that a decision matrix (DM) row or a bound document decides.
> - **Drafted under:** decision agent decisions D-146 (the M1 drafting plan, item 3) and D-157 (Master Plan §4 M1); revision 2 under decision D-174 (C4). Decision files are kept outside the repository (`docs/WORKING-RECORDS.md`).
> - **Path:** `docs/specs/risk-rules-gov-aieos.md` is interim, like specifications 1 and 2. In specification 2's layout these rules are the `risk_rules` of `.aieos/project.yaml` (specification 2 §7); that file is written only by a core, which does not exist yet (constitution INV-004).
> - **Sources:** "concept line N" is a line of `AIEOS-concept.md` (v0.5, unchanged, A22). "Spec 2" is `docs/specs/spec-02-aieos-file-format.md` revision 1 (DM F12). "(proposed)" marks a choice of this policy where the concept is silent or says less; each one is also listed in section 7.

## 1. Purpose and scope

- The rule-based risk classification of concept §8.3 for gov-AIEOS (A53), the work on this repository: "Risk = mức cao nhất của các rule khớp" (line 592). The class of a change decides its verification plan, the assurance it needs and whether human approval is needed (lines 580-587); for gov-AIEOS the approver is the decision agent at every class, except for a task under CR-002 part 4 limit 5 or 8, which the owner approves (CR-002 Đ7; `assurance-model.md` §6; Master Plan §6).
- A deterministic policy approved in advance (concept line 199): for gov-AIEOS the decision agent approves it in the owner's place (CR-002 Đ2), within CR-002 part 1: it never accepts a task by itself, decides no act of A51 item (3) or (4), and is reported to the owner when approved.
- Not in scope: the evidence profiles of each class (`assurance-model.md` §5, bound in Genesis instance 2, advisory); autonomy levels (every class is at L1, A35; A54 point 2); the acceptance decision (`governor-spec.md`); acts the owner keeps. These rules set only a change's risk class. No rule of this policy is a rule for owner-kept acts: the owner-kept act input is set by the task contract's declaration and the constitution's path rules (A56; `governor-spec.md` §3.2; spec 2 §5.1).

## 2. How the rules are applied

1. A change's class is the highest class among the rules that match any of its changed paths (line 592). The order is low, medium, high, critical (lines 597-601, 699-704; spec 2 §5.1).
2. A change with a changed path that no rule matches gets no class, even when its other paths match: it is never low (A35), and it gets no decision value (`governor-spec.md` §4 rule 8) until this policy covers that path (proposed). This is stricter than rule 8 and scenario RISK-01, which speak of a change that matches no rule; the governor reads this policy per path.
3. Rules are read from the base or a pinned ref, never from the change they classify (`governor-spec.md` §4 rule 1). A rule that cannot be evaluated matches every path it could cover (fail closed; proposed). Rule R3 cannot be evaluated until an approved architecture entity names the components, their paths and their tags (spec 2 §4.2); until then it matches every path under `src/**` and `tests/**` (proposed).
4. A `risk` declared in a task contract that is lower than this policy gives is not used (`governor-spec.md` §3.2; spec 2 §5.1); one that is higher is used (proposed).
5. A renamed file counts under its old and its new path, and a deleted file under its path (proposed).
6. Patterns (proposed): paths are relative to the repository root and compared case-sensitively with the path as Git records it. `*` matches any part of one name and never crosses `/`. `**` matches any sequence of names, so a trailing `/**` matches every file at any depth below that folder, and `**/x/**` matches `x` at any depth. A pattern without `/` matches a file name in any folder, as Git's ignore patterns do. No other pattern character is used.

## 3. The rules

```yaml
policy_version: v1
risk_rules:
  # R1, low: concept line 597.
  - match: { paths: ["docs/**", "*.md"] }
    risk: low
  # R2, medium: concept line 598; tests/** with the source tree (proposed).
  - match: { paths: ["src/**", "tests/**"] }
    risk: medium
  # R3, high: concept line 599, kept; and AIEOS's own security-critical parts (CR-002 Đ9; tag names proposed).
  - match: { component_tags: [auth, payments, crypto, governor, verification, policy, authority] }
    risk: high
  # R4, high (proposed): the Master Plan, the working-records rules and repository configuration.
  - match: { paths: ["docs/plan/**", "docs/WORKING-RECORDS.md", ".gitattributes", ".gitignore"] }
    risk: high
  # R5, critical: concept line 600, kept, and the same folders at any depth (proposed).
  - match: { paths: ["migrations/**", "contracts/**", "**/migrations/**", "**/contracts/**"] }
    risk: critical
  # R6, critical: concept line 601 (touches constitution or intent), spelled as paths of gov-AIEOS (proposed).
  - match: { paths: ["AIEOS-concept.md", "docs/pre-genesis/constitution.md", "docs/pre-genesis/CR-*.md", "docs/specs/**"] }
    risk: critical
  # R7, critical (proposed): the pre-genesis documents, the Genesis-bound documents and the decision matrix.
  - match: { paths: ["docs/pre-genesis/**", "docs/genesis/**"] }
    risk: critical
  # R8, critical (proposed): the measurement protocol and the measurements.
  - match: { paths: ["docs/pre-genesis/measurement-protocol.md", "docs/pre-genesis/measurements/**"] }
    risk: critical
  # R9, critical (proposed): the CI channel, and Claude Code's project files.
  - match: { paths: [".github/**", ".claude/**", "CLAUDE.md"] }
    risk: critical
  # R10, critical (proposed): the project-state directory, the policy file included.
  - match: { paths: [".aieos/**"] }
    risk: critical
```

## 4. Why each rule is where it is

- **R1 to R6 keep the concept's example rules** (lines 597-601) and lower none of them. R6 spells "touches: [constitution, intent]" as paths, because spec 2 §7 names `touches` but does not say how it is evaluated: the constitution, and the intent of gov-AIEOS, read here as the concept, its errata (CR-001, CR-002) and the specifications (concept §6.2; this policy is under `docs/specs/` and so critical too). Their places under `.aieos/` depend on spec 2's proposed layout and are covered by R10.
- **R3** adds four tags for the parts of AIEOS that judge work, check its rules and limit authority, which CR-002 Đ9 treats as security-critical for gov-AIEOS (`assurance-model.md` §5): the governor, the verification gates and conformance runner, the policy reader, and the authority records. The concept's own three tags stay. A change to the governor is also `critical_cr` until its identity is bound (`governor-spec.md` §8 point 2); that is a change class, not a risk class, and R3 does not lower it.
- **R4:** the Master Plan is ratified in the owner's place (delegated, advisory; DM F10) and decides when code starts (Master Plan §8); `docs/WORKING-RECORDS.md` holds the public-safety rules that constitution SEC-002 takes as its source; `.gitattributes` and `.gitignore` change how every file is stored or tracked. Without R4 they would be low (R1) or have no class.
- **R7:** a change to a Genesis-bound document is a Genesis amendment (constitution GOV-004; `genesis-model.md` §5); the decision matrix holds the owner's decisions (constitution GOV-005, GOV-006); and the whole `docs/pre-genesis/` folder is in the scope of GOV-005 and OPS-003. Without R7 they would be low (R1).
- **R8, R9:** R8 overlaps R7 on purpose, so that the measurement files stay critical if R7 is ever narrowed. R9's files are those of acts that A51 item (4) keeps with the owner (anything under `.github/`, constitution SEC-003; Claude Code's settings, `CLAUDE.md` and the agents folder). Both set only a class (section 1).
- **R10:** only the core writes `.aieos/` (concept line 879; constitution INV-004), and a change that touches the policy, the risk rules or the default profiles is never auto-accepted (`assurance-model.md` §6).
- **Low is not without checks.** The records (`docs/History/`, `docs/Progress/`, `docs/Deferred/`, `docs/Lessons/`) are low, but the constitution articles whose scope meets a changed path still add their `evidence_required` to its profile (`governor-spec.md` §3.2, "applicable articles"), for example GOV-005 for the records.
- **No rule** covers a new top-level file or folder other than `src/` and `tests/`: such a change gets no class until this policy is changed (section 2, point 2). Concept line 592 also names "loại thay đổi" and "điều khoản Constitution bị chạm" as rule inputs; spec 2 §7 has no key for the kind of change and does not say how `touches` names an article, so v1 uses paths and tags only (section 7).

## 5. What the classes mean now

- v0.1 has default profiles for low and medium (concept line 947). For gov-AIEOS, Genesis instance 2 applies the high and critical defaults of concept lines 703-704 from v0.1, cumulative on medium, with the dimensions that `assurance-model.md` §5 sets (CR-001 E10, as marked for Genesis version 2; A59, A60). Their `ai_review (cross-model)` entry is met only by the pair of reviews of `assurance-model.md` §3 and §5: a way-2 review by a Claude model other than the implementer's, and a separate review of the decision agent that stands for that entry; one alone meets nothing (`governor-spec.md` §4 rule 3). For AIEOS projects, CR-001 E10 stays open; that is outside this policy (section 1).
- So a task that touches a path of R3 to R10 is accepted only with the complete evidence profile of its class, the pair included, and one approval: the decision agent's, or the owner's for a task under CR-002 part 4 limit 5 or 8 and for the first governor version (`assurance-model.md` §6; Master Plan §6; decision D-166). This includes every code task of milestone M2: the governor, the conformance runner, their tests and fixtures under `src/**` and `tests/**` count as tagged by R3 (section 2, point 3) until an architecture names the components, so they are at least high. It also includes any task that changes the decision matrix, the Master Plan, a specification, `CLAUDE.md` or a file under `.claude/`.
- Changes to the records are low (section 4).
- Nothing here changes an evidence requirement, a level or who approves what (CR-002 part 4 limit 8; A51 item (4)): the profiles are those of the bound assurance model, not of this policy (section 1).

## 6. Change control

- This policy is versioned (`policy_version`). A change to it is a change request, approved by the decision agent in the owner's place (CR-002 Đ2), except a change that lowers the class of a kind of change or otherwise weakens an evidence requirement, which is the owner's (CR-002 part 4 limit 8). A change to it is itself critical (R6, and R10 once it lives in `.aieos/`).
- The reference for this first version (CR-002 part 4 limit 8; A54 point 4) is the repository on GitHub before it was drafted, where the only risk rules were the concept's examples (lines 595-602) and a change that matches no rule is never low (A35). R1 to R10 lower none of the concept's rules, and every path those rules do not cover is, under this version, either without a class (section 2) or high or critical (R3 over `src/**` and `tests/**`, R4, R5, R7 to R10).
- A change to the component tags or paths of an architecture entity that would lower the class of any change counts as a change to this policy, with the same limits (proposed).
- When a document named in R4 to R9 moves (spec 2 §10 point 2), the rule moves with it in the same change; the layout is settled (CR-001 E4, Genesis version 2; DM A60), and the rules move into `.aieos/project.yaml` (spec 2 §7) when a core exists to write that file (constitution INV-004). Neither move changes a class.

## 7. Open points

1. Closed for gov-AIEOS in revision 2: high and critical tasks of gov-AIEOS, the governor's own included, are handled as section 5 says (Genesis instance 2; A59, A60; `assurance-model.md` §10 point 1, closed for gov-AIEOS). For AIEOS projects, CR-001 E10 stays open; that is outside this policy (section 1).
2. For the owner, if it arises: any later rule that classes a change lower than the concept's example rules (lines 595-602) or than this version (CR-002 part 4 limit 8). This version lowers none.
3. The components, their paths and tags, in an approved architecture entity (spec 2 §4.2), which makes R3 evaluable; no milestone of the Master Plan delivers one yet. Whether `governor-spec.md` §3.2's weakens-evidence input covers a change to component tags (section 6) is for that document's next revision.
4. The source tree's top-level name (`src/`) and `tests/` with it, to be set by the first code task's contract, whose write-set has new paths only (Master Plan §8); fixture paths get their own rule then.
5. Rules by kind of change and by constitution article touched (concept line 592), which spec 2 §7 cannot express yet.
6. The choices marked "(proposed)": the per-path reading of section 2 point 2; the fail-closed reading of an unevaluable rule and of R3 before an architecture exists; a higher declared risk; renames and deletions; the pattern rules of section 2, point 6; `tests/**` in R2; R3's four tags; R4; R5's any-depth folders; R6's path spelling; R7 to R10; the tag-change rule of section 6.

## 8. Revisions

- Revision 0: first draft (D-146, D-157).
- Revision 1: applies the thirteen findings of one read-only checker round (claude-sonnet-5-5), each verified against its source lines: exact pattern semantics; R3's fail-closed reading over `tests/**` too; tag changes counted as policy changes; the per-path rule marked; `docs/pre-genesis/**` and `docs/WORKING-RECORDS.md` raised; R5 at any depth; R6's `.aieos/` paths left to R10; the first version's reference; status labels; what low still checks.
- Revision 2: carries Genesis instance 2 (A59, A60; decision D-174 C4): section 5 states how high and critical tasks of gov-AIEOS are handled, section 7 point 1 is closed for gov-AIEOS, and sections 1 and 6 name instance 2 and the settled layout. The rules of section 3, the policy version and every class are unchanged.
