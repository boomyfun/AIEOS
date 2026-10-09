DATA = r'''{
  "cases": [
    {
      "expected": {
        "approval": null,
        "decision": [
          "INSUFFICIENT_EVIDENCE"
        ],
        "missing": [
          {
            "dimension": "security",
            "evidence_type": "static_security_analysis"
          }
        ],
        "next_state": [
          "REWORK"
        ],
        "not_fixed": [
          "reverify",
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
            "dimension": "security",
            "evidence_types": [
              "static_security_analysis"
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
          "record_id": "TASK-111-g0",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-111"
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
          "record_id": "TASK-111-g1",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-111"
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
          "record_id": "TASK-111-g2",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-111"
        },
        {
          "approval_binding": {
            "hash": "4bd69bf0c0dc8aefe24924fb481ea47a82b17fbe430342ef50d51e7844da56a2",
            "kind": "acceptance"
          },
          "fact_kind": "authority",
          "record_id": "TASK-111-approval",
          "recorder": "a human approver",
          "source_class": "human_authority",
          "subject": "TASK-111"
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
        "task_content_hash": "4bd69bf0c0dc8aefe24924fb481ea47a82b17fbe430342ef50d51e7844da56a2",
        "task_id": "TASK-111",
        "task_state": "VERIFYING"
      },
      "when": "evaluate"
    }
  ],
  "row_hash": "813d8017323e2d0d80b1de310277a1edc24dc4763cc56787040a2ab7735a0450",
  "scenario": "ACC-11"
}
'''
