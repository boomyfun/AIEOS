DATA = r'''{
  "cases": [
    {
      "expected": {
        "not_fixed": [
          "decision",
          "next_state"
        ],
        "profile_excludes": [
          {
            "dimension": "functional",
            "evidence_type": "build"
          },
          {
            "dimension": "functional",
            "evidence_type": "lint"
          }
        ],
        "risk_not": [
          "low"
        ]
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
          "unmatched/file.txt"
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
      "values": {
        "articles": [],
        "auto_accept": {
          "critical": false,
          "high": false,
          "low": false,
          "medium": false
        },
        "changed_paths": [
          "unmatched/file.txt"
        ],
        "contract": {
          "owner_kept_act": false,
          "risk": "low",
          "traces_to": [
            "SPEC-012"
          ],
          "verification_plan": [
            "G0",
            "G1",
            "G2"
          ]
        },
        "default_profiles": {
          "critical": [
            {
              "dimension": "functional",
              "evidence_types": [
                "unit_test",
                "integration_test",
                "property_test"
              ]
            }
          ],
          "high": [
            {
              "dimension": "functional",
              "evidence_types": [
                "unit_test",
                "integration_test"
              ]
            }
          ],
          "low": [
            {
              "dimension": "functional",
              "evidence_types": [
                "build",
                "lint"
              ]
            }
          ],
          "medium": [
            {
              "dimension": "functional",
              "evidence_types": [
                "unit_test"
              ]
            }
          ]
        },
        "delegation": true,
        "evidence_comparison": {
          "weakens": false
        },
        "level_version": "v1",
        "owner_kept_rules": [],
        "policy_version": "v2",
        "requirement_profiles": [],
        "risk_rules": [
          {
            "class": "low",
            "match": [
              "docs/**",
              "*.md"
            ]
          },
          {
            "class": "medium",
            "match": [
              "src/**",
              "tests/**"
            ]
          },
          {
            "class": "high",
            "match": [
              "src/**",
              "tests/**"
            ]
          },
          {
            "class": "high",
            "match": [
              "docs/plan/**",
              "docs/WORKING-RECORDS.md",
              ".gitattributes",
              ".gitignore"
            ]
          },
          {
            "class": "critical",
            "match": [
              "migrations/**",
              "contracts/**",
              "**/migrations/**",
              "**/contracts/**"
            ]
          },
          {
            "class": "critical",
            "match": [
              "AIEOS-concept.md",
              "docs/pre-genesis/constitution.md",
              "docs/pre-genesis/CR-*.md",
              "docs/specs/**"
            ]
          },
          {
            "class": "critical",
            "match": [
              "docs/pre-genesis/**",
              "docs/genesis/**"
            ]
          },
          {
            "class": "critical",
            "match": [
              "docs/pre-genesis/measurement-protocol.md",
              "docs/pre-genesis/measurements/**"
            ]
          },
          {
            "class": "critical",
            "match": [
              ".github/**",
              ".claude/**",
              "CLAUDE.md"
            ]
          },
          {
            "class": "critical",
            "match": [
              ".aieos/**"
            ]
          },
          {
            "class": "critical",
            "match": [
              "tests/conformance/**"
            ]
          },
          {
            "class": "high",
            "match": [
              "bench/**"
            ]
          }
        ],
        "ruleset_version": "v1"
      },
      "when": "evaluate"
    }
  ],
  "row_hash": "d04e8131768256470e2f2ab872bd18023dc90b9d45bf6853156bdea68c2b06f2",
  "scenario": "RISK-01"
}
'''
