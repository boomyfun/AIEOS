DATA = r'''{
  "cases": [
    {
      "expected": {
        "decision": [
          "REJECT",
          "NEEDS_REWORK"
        ],
        "next_state": [
          "DRAFT",
          "READY",
          "IN_PROGRESS",
          "VERIFYING",
          "DONE",
          "IN_REVIEW",
          "REWORK",
          "ESCALATED",
          "REJECTED",
          "BLOCKED",
          "STALE"
        ],
        "not_fixed": [
          "missing",
          "reverify",
          "approval",
          "ai_approval_shown"
        ]
      },
      "inputs": {
        "applicable_articles": [],
        "auto_accept": false,
        "delegation_in_force": false,
        "evidence_profile": [
          {
            "dimension": "functional",
            "evidence_types": [
              "build",
              "lint"
            ]
          }
        ],
        "level_version": "v1",
        "owner_kept_act": false,
        "policy_version": "v1",
        "risk": "low",
        "ruleset_version": "v1",
        "traces_to": [
          "SPEC-012"
        ],
        "verification_plan": [
          "G0",
          "G1",
          "G2"
        ],
        "weakens_evidence": false
      },
      "records": [
        {
          "blocking_kind": "out_of_scope",
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "dimension": "scope",
          "evidence_type": "scope_check",
          "fact_kind": "observation",
          "gate": "G0",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "outcome": "blocking",
          "record_id": "TASK-901-g0",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-901"
        },
        {
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "dimension": "functional",
          "evidence_type": "build",
          "fact_kind": "observation",
          "gate": "G1",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "outcome": "pass",
          "record_id": "TASK-901-g1",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-901"
        },
        {
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "dimension": "functional",
          "evidence_type": "lint",
          "fact_kind": "observation",
          "gate": "G2",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "outcome": "pass",
          "record_id": "TASK-901-g2",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-901"
        }
      ],
      "request": {
        "changed_paths": [
          "src/feature.py",
          ".aieos/conformance/scenarios.md"
        ],
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "retry_count": {
          "limit": 2,
          "used": 0
        },
        "task_content_hash": "f737bf0eac027a6976b1c1627c1327af443cacce5838436ff78cafe6bce29cf4",
        "task_id": "TASK-901",
        "task_state": "VERIFYING"
      },
      "when": "evaluate"
    }
  ],
  "row_hash": "5aa89d9e65411894a588f358e73bf3fdbf4ebe0c613109065072727b9af067a6",
  "scenario": "ADV-01"
}
'''
