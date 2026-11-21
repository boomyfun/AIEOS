# The evaluation policy of gov-AIEOS

Prose before the block is ignored by the reader. Statements of this file:
- The scopes of the articles are the worker's proposal, each equal to or broader than the constitution's prose scope, and are decided by: decision agent (A41, A51), D-6915 (as corrected there).
- The high and critical default profiles are the text of assurance-model.md revision 5 that the owner approved at A60; that text itself labels their dimension placements "Claude's, proposed" (assurance-model.md :81), and the label is kept.
- The single type property_test for the property/fuzz entry is stricter than assurance-model.md :84 (property_test or fuzz_test): a fuzz_test record alone does not satisfy it.
- owner_kept_rules, delegation and auto_accept are the OWNER'S and are given by the owner's answer "1 không, 2 có, 3 có", main transcript of session dc7cf6ca-d094-4438-af81-93586ed7658b, line 37957 (question 1 không, 2 có, 3 có); no row of the decision matrix records this answer yet (GOV-005), so this file quotes it as the owner's answer and does not present it as a matrix decision.

## 3. The sources

```yaml
# owner_kept_rules: OWNER'S, given by the owner's answer "1 không, 2 có, 3 có", main transcript of session dc7cf6ca-d094-4438-af81-93586ed7658b, line 37957 (question 1 không = option A: the owner-kept paths of the CI's OWNER_PATHS and of OPS-002 :134; no rule for .github/**: changes under .github/ stay the decision agent's under A66 and SEC-003, except write access, secrets, tokens and repository settings, which stay the owner's)
owner_kept_rules:
  - match: [docs/pre-genesis/measurement-protocol.md, docs/pre-genesis/measurements/**]
# articles: the 15 articles that have an evidence_required entry (the other articles add nothing to a profile); every scope below is equal to or BROADER than the constitution's prose, never narrower
articles:
  - id: INV-001
    scope: [src/**]
    evidence_required: [ai_review]
  - id: INV-002
    scope: [src/aieos_bootstrap/**]
    evidence_required: [ai_review]
  - id: INV-003
    scope: [src/aieos_bootstrap/**]
    evidence_required: [human_review]
  - id: INV-004
    scope: [.aieos/**, src/**]
    evidence_required: [ai_review]
  - id: INV-005
    scope: [src/aieos_bootstrap/**]
    evidence_required: [property_test]
  - id: INV-006
    scope: [src/aieos_bootstrap/**]
    evidence_required: [property_test]
  - id: INV-007
    scope: [src/aieos_bootstrap/**, .aieos/**, docs/records/**]
    evidence_required: [property_test]
  - id: INV-008
    scope: [src/aieos_bootstrap/**]
    evidence_required: [property_test]
  - id: GOV-003
    scope: [.github/**, src/aieos_bootstrap/**, tests/conformance/**, docs/pre-genesis/conformance-scenarios-initial.md, docs/records/**, docs/specs/risk-rules-gov-aieos.md, docs/pre-genesis/constitution.md, docs/tasks/**, .aieos/tasks/**, tests/unit/**, tests/integration/**, tests/property/**, tests/run_tests.py, **/Pipfile, **/Pipfile.lock, **/poetry.lock, **/uv.lock, **/constraints*.txt, **/MANIFEST.in, **/tox.ini, **/pytest.ini, **/conftest.py, **/.python-version, **/pyproject.toml, **/setup.cfg, **/setup.py, **/requirements*.txt, **/go/**, **/rust/**, **/ts/**, **/go.mod, **/go.sum, **/Cargo.lock, **/Cargo.toml, **/tsconfig.json, **/package-lock.json, docs/pre-genesis/assurance-model.md, docs/pre-genesis/decision-matrix.md, docs/pre-genesis/governor-spec.md, docs/specs/evaluation-policy-gov-aieos.md]
    evidence_required: [ai_review]
  - id: GOV-004
    scope: [**]
    evidence_required: [human_review]
  - id: GOV-005
    scope: [docs/**]
    evidence_required: [human_review]
  - id: GOV-006
    scope: [docs/pre-genesis/decision-matrix.md]
    evidence_required: [human_review]
  - id: SEC-002
    scope: [**]
    evidence_required: [ai_review]
  - id: OPS-002
    scope: [**]
    evidence_required: [human_review]
  - id: OPS-003
    scope: [docs/**, .aieos/**]
    evidence_required: [ai_review]
# default_profiles: low and medium are assurance-model section 5 :78; high and critical are :81-:84 (the owner's A59 and A60 for gov-AIEOS)
default_profiles:
  low:
    - {dimension: functional, evidence_types: [build, lint]}
  medium:
    - {dimension: functional, evidence_types: [unit_test]}
    - {dimension: architecture, evidence_types: [deterministic_rule]}
  high:
    - {dimension: functional, evidence_types: [unit_test]}
    - {dimension: architecture, evidence_types: [deterministic_rule]}
    - {dimension: functional, evidence_types: [integration_test]}
    - {dimension: security, evidence_types: [static_security_analysis]}
    - {dimension: architecture, evidence_types: ['ai_review (cross-model)']}
  critical:
    - {dimension: functional, evidence_types: [unit_test]}
    - {dimension: architecture, evidence_types: [deterministic_rule]}
    - {dimension: functional, evidence_types: [integration_test]}
    - {dimension: security, evidence_types: [static_security_analysis]}
    - {dimension: architecture, evidence_types: ['ai_review (cross-model)']}
    - {dimension: architecture, evidence_types: [human_review]}
    - {dimension: functional, evidence_types: [property_test]}
# requirement_profiles: the directory .aieos/intent/requirements (spec-02 :32) holds no file at main
requirement_profiles: []
# delegation: OWNER'S, given by the owner's answer "1 không, 2 có, 3 có", main transcript of session dc7cf6ca-d094-4438-af81-93586ed7658b, line 37957 (question 2 có: the delegation is in force; A41 as widened by A51; the matrix rows are the source)
delegation: true
# auto_accept: OWNER'S, given by the owner's answer "1 không, 2 có, 3 có", main transcript of session dc7cf6ca-d094-4438-af81-93586ed7658b, line 37957 (question 3 có: no risk class is auto-accepted; L1: no auto-accept; assurance-model :90 and :94-:97; INV-011)
auto_accept:
  low: false
  medium: false
  high: false
  critical: false
```

Prose after the block is ignored by the reader.
