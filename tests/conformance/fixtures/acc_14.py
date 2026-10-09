DATA = r'''{
  "cases": [
    {
      "expected": {
        "ai_approval_shown": true,
        "approval": {
          "record_id": "TASK-114-approval",
          "source_class": "decision_agent"
        },
        "next_state": [
          "ACCEPTED"
        ],
        "not_fixed": [
          "decision",
          "missing",
          "reverify"
        ]
      },
      "inputs": {
        "applicable_articles": [],
        "auto_accept": false,
        "delegation_in_force": true,
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
          "record_id": "TASK-114-g0",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-114"
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
          "record_id": "TASK-114-g1",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-114"
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
          "record_id": "TASK-114-g2",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-114"
        },
        {
          "approval_binding": {
            "hash": "185a8c8c00f805309229d7f204150c6e9965aac7ff7cb710a71095d9956b26d3",
            "kind": "acceptance"
          },
          "decision_ref": "D-901",
          "fact_kind": "authority",
          "record_id": "TASK-114-approval",
          "recorder": "decided by: decision agent (A41, A51)",
          "source_class": "decision_agent",
          "subject": "TASK-114"
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
        "task_content_hash": "185a8c8c00f805309229d7f204150c6e9965aac7ff7cb710a71095d9956b26d3",
        "task_id": "TASK-114",
        "task_state": "IN_REVIEW"
      },
      "when": "re_evaluate"
    }
  ],
  "row_hash": "8c1fcdea20f6ac1b9f8b5fe15efc0f8ce61d95acf2eb910a14d8e955eb644070",
  "scenario": "ACC-14"
}
'''
