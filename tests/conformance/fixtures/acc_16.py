DATA = r'''{
  "cases": [
    {
      "expected": {
        "approval": null,
        "decision": [
          "NEEDS_REVIEW"
        ],
        "missing": [],
        "next_state": [
          "IN_REVIEW"
        ],
        "not_fixed": [
          "reverify",
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
          "record_id": "TASK-116-g0",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-116"
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
          "record_id": "TASK-116-g1",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-116"
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
          "record_id": "TASK-116-g2",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-116"
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
          "record_id": "TASK-116-unit",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-116"
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
          "record_id": "TASK-116-integration",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-116"
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
          "record_id": "TASK-116-rule",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-116"
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
          "record_id": "TASK-116-ssa",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-116"
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
          "record_id": "TASK-116-way2",
          "recorder": "a reviewer agent",
          "source_class": "same_lineage_review",
          "subject": "TASK-116"
        },
        {
          "basis": "the change and the way-2 review, read in full by the decision agent",
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "decision_ref": "D-904",
          "dimension": "architecture",
          "evidence_type": "decision_agent_review",
          "fact_kind": "observation",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "outcome": "pass",
          "record_id": "TASK-116-da-review",
          "recorder": "decision agent",
          "source_class": "decision_agent",
          "stands_for": "ai_review (cross-model)",
          "subject": "TASK-116"
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
        "task_content_hash": "7b3a643294a63d0eab3fd46cfb00d83e2bdd64882de3af65c4b8ae968146945a",
        "task_id": "TASK-116",
        "task_state": "VERIFYING"
      },
      "when": "evaluate"
    }
  ],
  "row_hash": "71f3bfca8ed71889327b73080c968ef21c6ac442f4157ad82de2a01093448981",
  "scenario": "ACC-16"
}
'''
