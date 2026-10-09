DATA = r'''{
  "cases": [
    {
      "expected": {
        "approval": {
          "record_id": "TASK-131-approval",
          "source_class": "human_authority"
        },
        "next_state": [
          "ACCEPTED"
        ],
        "not_fixed": [
          "decision",
          "missing",
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
          "record_id": "TASK-131-g0",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-131"
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
          "record_id": "TASK-131-g1",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-131"
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
          "record_id": "TASK-131-g2",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-131"
        },
        {
          "approval_binding": {
            "hash": "d9089a4e867dea5459fefb4dcc3e729f88f261ea33221c9eaff37c5c4656c2b6",
            "kind": "acceptance"
          },
          "fact_kind": "authority",
          "record_id": "TASK-131-approval",
          "recorder": "a human approver",
          "source_class": "human_authority",
          "subject": "TASK-131"
        },
        {
          "approval_binding": {
            "hash": "94160b507e8fd2e7667e9bad09a7976a6c2b8da87cf2ee85f17f247c86e787c4",
            "kind": "acceptance"
          },
          "fact_kind": "authority",
          "record_id": "TASK-132-approval",
          "recorder": "a human approver",
          "source_class": "human_authority",
          "subject": "TASK-132"
        },
        {
          "approval_binding": {
            "hash": "d1e6dd8989e31fbe3e1fc7b934b3414db00d62da00af04c47a267045d14756f5",
            "kind": "acceptance"
          },
          "fact_kind": "authority",
          "record_id": "TASK-133-approval",
          "recorder": "a human approver",
          "source_class": "human_authority",
          "subject": "TASK-133"
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
        "task_content_hash": "d9089a4e867dea5459fefb4dcc3e729f88f261ea33221c9eaff37c5c4656c2b6",
        "task_id": "TASK-131",
        "task_state": "IN_REVIEW"
      },
      "when": "re_evaluate"
    },
    {
      "expected": {
        "approval": {
          "record_id": "TASK-132-approval",
          "source_class": "human_authority"
        },
        "next_state": [
          "ACCEPTED"
        ],
        "not_fixed": [
          "decision",
          "missing",
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
          "record_id": "TASK-132-g0",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-132"
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
          "record_id": "TASK-132-g1",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-132"
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
          "record_id": "TASK-132-g2",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-132"
        },
        {
          "approval_binding": {
            "hash": "d9089a4e867dea5459fefb4dcc3e729f88f261ea33221c9eaff37c5c4656c2b6",
            "kind": "acceptance"
          },
          "fact_kind": "authority",
          "record_id": "TASK-131-approval",
          "recorder": "a human approver",
          "source_class": "human_authority",
          "subject": "TASK-131"
        },
        {
          "approval_binding": {
            "hash": "94160b507e8fd2e7667e9bad09a7976a6c2b8da87cf2ee85f17f247c86e787c4",
            "kind": "acceptance"
          },
          "fact_kind": "authority",
          "record_id": "TASK-132-approval",
          "recorder": "a human approver",
          "source_class": "human_authority",
          "subject": "TASK-132"
        },
        {
          "approval_binding": {
            "hash": "d1e6dd8989e31fbe3e1fc7b934b3414db00d62da00af04c47a267045d14756f5",
            "kind": "acceptance"
          },
          "fact_kind": "authority",
          "record_id": "TASK-133-approval",
          "recorder": "a human approver",
          "source_class": "human_authority",
          "subject": "TASK-133"
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
        "task_content_hash": "94160b507e8fd2e7667e9bad09a7976a6c2b8da87cf2ee85f17f247c86e787c4",
        "task_id": "TASK-132",
        "task_state": "IN_REVIEW"
      },
      "when": "re_evaluate"
    },
    {
      "expected": {
        "approval": {
          "record_id": "TASK-133-approval",
          "source_class": "human_authority"
        },
        "next_state": [
          "ACCEPTED"
        ],
        "not_fixed": [
          "decision",
          "missing",
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
          "record_id": "TASK-133-g0",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-133"
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
          "record_id": "TASK-133-g1",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-133"
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
          "record_id": "TASK-133-g2",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-133"
        },
        {
          "approval_binding": {
            "hash": "d9089a4e867dea5459fefb4dcc3e729f88f261ea33221c9eaff37c5c4656c2b6",
            "kind": "acceptance"
          },
          "fact_kind": "authority",
          "record_id": "TASK-131-approval",
          "recorder": "a human approver",
          "source_class": "human_authority",
          "subject": "TASK-131"
        },
        {
          "approval_binding": {
            "hash": "94160b507e8fd2e7667e9bad09a7976a6c2b8da87cf2ee85f17f247c86e787c4",
            "kind": "acceptance"
          },
          "fact_kind": "authority",
          "record_id": "TASK-132-approval",
          "recorder": "a human approver",
          "source_class": "human_authority",
          "subject": "TASK-132"
        },
        {
          "approval_binding": {
            "hash": "d1e6dd8989e31fbe3e1fc7b934b3414db00d62da00af04c47a267045d14756f5",
            "kind": "acceptance"
          },
          "fact_kind": "authority",
          "record_id": "TASK-133-approval",
          "recorder": "a human approver",
          "source_class": "human_authority",
          "subject": "TASK-133"
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
        "task_content_hash": "d1e6dd8989e31fbe3e1fc7b934b3414db00d62da00af04c47a267045d14756f5",
        "task_id": "TASK-133",
        "task_state": "IN_REVIEW"
      },
      "when": "re_evaluate"
    }
  ],
  "row_hash": "95056ff8e30ef9b6374830b30f94180811443c33a291a1ee07575ceb3bb9733e",
  "scenario": "ACC-13"
}
'''
