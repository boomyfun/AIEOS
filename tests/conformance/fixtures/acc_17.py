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
            "evidence_type": "ai_review (cross-model)"
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
        "delegation_in_force": true,
        "evidence_profile": [
          {
            "dimension": "functional",
            "evidence_types": [
              "unit_test",
              "integration_test"
            ]
          },
          {
            "dimension": "architecture",
            "evidence_types": [
              "deterministic_rule",
              "ai_review (cross-model)"
            ]
          },
          {
            "dimension": "security",
            "evidence_types": [
              "static_security_analysis"
            ]
          }
        ],
        "level_version": "v1",
        "owner_kept_act": false,
        "policy_version": "v1",
        "risk": "high",
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
          "record_id": "TASK-117-g0",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-117"
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
          "record_id": "TASK-117-g1",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-117"
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
          "record_id": "TASK-117-g2",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-117"
        },
        {
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "dimension": "functional",
          "evidence_type": "unit_test",
          "fact_kind": "observation",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "outcome": "pass",
          "record_id": "TASK-117-unit",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-117"
        },
        {
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "dimension": "functional",
          "evidence_type": "integration_test",
          "fact_kind": "observation",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "outcome": "pass",
          "record_id": "TASK-117-integration",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-117"
        },
        {
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "dimension": "architecture",
          "evidence_type": "deterministic_rule",
          "fact_kind": "observation",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "outcome": "pass",
          "record_id": "TASK-117-rule",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-117"
        },
        {
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "dimension": "security",
          "evidence_type": "static_security_analysis",
          "fact_kind": "observation",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "outcome": "pass",
          "record_id": "TASK-117-ssa",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-117"
        },
        {
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "decision_ref": "D-903",
          "dimension": "architecture",
          "evidence_type": "other_model_review",
          "fact_kind": "observation",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "models": {
            "implementer": "model-a",
            "reviewer": "model-b"
          },
          "outcome": "pass",
          "record_id": "TASK-117-way2",
          "recorder": "a reviewer agent",
          "source_class": "same_lineage_review",
          "subject": "TASK-117"
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
        "task_content_hash": "504bb9f9b928b6539c8eb288a17020b93b0292033177ceea1e054ec1f6745482",
        "task_id": "TASK-117",
        "task_state": "VERIFYING"
      },
      "when": "evaluate"
    }
  ],
  "row_hash": "5b5b56095d5e2bdc0560f49a7bc7f75c6b76fe7866d17ebd487ed8cb8a496e5c",
  "scenario": "ACC-17"
}
'''
