DATA = r'''{
  "cases": [
    {
      "expected": {
        "decision": [
          "NEEDS_REVIEW"
        ],
        "next_state": [
          "IN_REVIEW"
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
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "dimension": "scope",
          "evidence_type": "scope_check",
          "fact_kind": "observation",
          "gate": "G0",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "outcome": "pass",
          "record_id": "TASK-101-g0",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-101"
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
          "record_id": "TASK-101-g1",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-101"
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
          "record_id": "TASK-101-g2",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-101"
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
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "task_id": "TASK-101",
        "task_state": "VERIFYING"
      },
      "when": "evaluate"
    }
  ],
  "row_hash": "5d8f9e4949dfe0f9bab7612a8af6a907185e45afdea865800a0598ddf97b0eab",
  "scenario": "ACC-01"
}
'''
