DATA = r'''{
  "cases": [
    {
      "expected": {
        "decision": [
          "INSUFFICIENT_EVIDENCE"
        ],
        "missing": [
          {
            "dimension": "architecture",
            "evidence_type": "ai_review"
          }
        ],
        "next_state": [
          "REWORK"
        ],
        "not_fixed": [
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
          },
          {
            "dimension": "architecture",
            "evidence_types": [
              "ai_review"
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
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "dimension": "scope",
          "evidence_type": "scope_check",
          "fact_kind": "observation",
          "gate": "G0",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "outcome": "pass",
          "record_id": "TASK-110-g0",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-110"
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
          "record_id": "TASK-110-g1",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-110"
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
          "record_id": "TASK-110-g2",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-110"
        },
        {
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "dimension": "architecture",
          "evidence_type": "ai_review",
          "fact_kind": "observation",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "models": {
            "implementer": "model-a",
            "reviewer": "model-a"
          },
          "outcome": "pass",
          "record_id": "TASK-110-review",
          "recorder": "a reviewer agent",
          "source_class": "same_lineage_review",
          "subject": "TASK-110"
        }
      ],
      "request": {
        "changed_paths": [
          "src/feature.py"
        ],
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "retry_count": {
          "limit": 2,
          "used": 0
        },
        "task_content_hash": "068d21e248d3b260312f6e36ce076a76a3a8201b83d999d671ed46781d89b54a",
        "task_id": "TASK-110",
        "task_state": "VERIFYING"
      },
      "when": "evaluate"
    }
  ],
  "row_hash": "5cbc91bc2b2835ed7305b44b18fad9866e630ac32b7a9d4ace0e953a4eb602b1",
  "scenario": "ACC-10"
}
'''
