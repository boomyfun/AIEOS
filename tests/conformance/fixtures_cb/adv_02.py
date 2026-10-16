DATA = r'''{
  "cases": [
    {
      "continuation": {
        "end_at": "2026-10-16T12:40:00Z",
        "session": {
          "code_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
          "expected_token": {
            "counter": 2,
            "epoch": "e-replay"
          },
          "expires_at": "2026-10-16T13:00:00Z",
          "holder": "agent-1",
          "inputs": {
            "approved_contract_hash": "77b7c8fbaa03652aee270e94dfb5f2d0811c6c75ce693aeb76112514e2c74290",
            "articles": [
              {
                "applicability": {
                  "task_types": [
                    "implementation"
                  ]
                },
                "id": "INV-001",
                "scope": {
                  "components": [],
                  "paths": [
                    "src/app/**"
                  ]
                },
                "violated": false
              }
            ],
            "base_is_ancestor": true,
            "budget_use": {
              "human_attention": {
                "reported": true,
                "used": "0m"
              },
              "retries": {
                "reported": true,
                "used": 0
              },
              "tokens": {
                "reported": true,
                "used": "10k"
              },
              "wall_time": {
                "reported": true,
                "used": "10m"
              }
            },
            "commits": [
              {
                "id": "3333333333333333333333333333333333333333",
                "paths": [
                  {
                    "change": "modified",
                    "path": "docs/other.md"
                  }
                ],
                "submitted": false
              }
            ],
            "components": [
              {
                "id": "CMP-API",
                "paths": [
                  "src/app/api/**"
                ],
                "tags": []
              }
            ],
            "contract": {
              "autonomy": {
                "budgets": {
                  "human_attention": "10m",
                  "retries": 2,
                  "tokens": "400k",
                  "wall_time": "2h"
                }
              },
              "constitution": [
                "INV-001"
              ],
              "contract_version": "v1",
              "input_state": {
                "base_commit": "1111111111111111111111111111111111111111",
                "depends_on": [
                  "TASK-099"
                ],
                "intent_versions": {
                  "SPEC-003": "v4"
                }
              },
              "read_set": {
                "interfaces": [
                  "load_policy"
                ],
                "paths": [
                  "src/app/util/helpers.py"
                ],
                "schemas": [
                  "record"
                ]
              },
              "risk": "medium",
              "task": "TASK-100",
              "task_type": "implementation",
              "write_set": {
                "paths": [
                  "docs/notes/**"
                ]
              }
            },
            "contract_hash": "77b7c8fbaa03652aee270e94dfb5f2d0811c6c75ce693aeb76112514e2c74290",
            "dependencies": {
              "TASK-099": {
                "stale_evidence": false,
                "state": "DONE"
              }
            },
            "derived_read_set": [],
            "head_commit": "2222222222222222222222222222222222222222",
            "intent_current": {
              "SPEC-003": "v4"
            },
            "interfaces": [
              {
                "component": "CMP-API",
                "id": "load_policy"
              }
            ],
            "log_seq": 5,
            "observed_read_set": [],
            "policy_version": "v2",
            "risk_rules": [
              {
                "match": {
                  "paths": [
                    "docs/**"
                  ]
                },
                "risk": "medium"
              }
            ],
            "runtime": {
              "adapter": "an-adapter",
              "max_risk": "high"
            },
            "schemas": [
              {
                "base": {
                  "path": "src/app/api/record.json",
                  "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                },
                "head": {
                  "path": "src/app/api/record.json",
                  "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                },
                "name": "record"
              }
            ],
            "symbols": [
              {
                "base": "F(a)",
                "head": "F(a)",
                "interface": "load_policy"
              }
            ],
            "task_id": "TASK-100",
            "task_state": "READY"
          },
          "session_id": "session-2",
          "start_at": "2026-10-16T12:00:00Z",
          "task_id": "TASK-100"
        },
        "submission": {
          "at": "2026-10-16T12:30:00Z",
          "commit_id": "3333333333333333333333333333333333333333",
          "commit_text": "tree 4444444444444444444444444444444444444444\u000aparent 1111111111111111111111111111111111111111\u000aauthor Tester <tester> 1700000000 +0000\u000acommitter Tester <tester> 1700000000 +0000\u000a\u000aDo the work\u000a\u000aThe body.\u000a\u000aAIEOS-Task: TASK-100\u000aAIEOS-Fence: e-replay:2\u000a",
          "event_id": "submitted-1"
        }
      },
      "document": {
        "end_at": "2026-10-16T10:40:00Z",
        "epoch": "e-replay",
        "recorder": "replay:session-one",
        "replay_id": "adv-02",
        "session": {
          "code_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
          "expected_token": {
            "counter": 1,
            "epoch": "e-replay"
          },
          "expires_at": "2026-10-16T11:00:00Z",
          "holder": "agent-1",
          "inputs": {
            "approved_contract_hash": "77b7c8fbaa03652aee270e94dfb5f2d0811c6c75ce693aeb76112514e2c74290",
            "articles": [
              {
                "applicability": {
                  "task_types": [
                    "implementation"
                  ]
                },
                "id": "INV-001",
                "scope": {
                  "components": [],
                  "paths": [
                    "src/app/**"
                  ]
                },
                "violated": false
              }
            ],
            "base_is_ancestor": true,
            "budget_use": {
              "human_attention": {
                "reported": true,
                "used": "0m"
              },
              "retries": {
                "reported": true,
                "used": 0
              },
              "tokens": {
                "reported": true,
                "used": "10k"
              },
              "wall_time": {
                "reported": true,
                "used": "10m"
              }
            },
            "commits": [
              {
                "id": "3333333333333333333333333333333333333333",
                "paths": [
                  {
                    "change": "modified",
                    "path": "docs/other.md"
                  }
                ],
                "submitted": false
              }
            ],
            "components": [
              {
                "id": "CMP-API",
                "paths": [
                  "src/app/api/**"
                ],
                "tags": []
              }
            ],
            "contract": {
              "autonomy": {
                "budgets": {
                  "human_attention": "10m",
                  "retries": 2,
                  "tokens": "400k",
                  "wall_time": "2h"
                }
              },
              "constitution": [
                "INV-001"
              ],
              "contract_version": "v1",
              "input_state": {
                "base_commit": "1111111111111111111111111111111111111111",
                "depends_on": [
                  "TASK-099"
                ],
                "intent_versions": {
                  "SPEC-003": "v4"
                }
              },
              "read_set": {
                "interfaces": [
                  "load_policy"
                ],
                "paths": [
                  "src/app/util/helpers.py"
                ],
                "schemas": [
                  "record"
                ]
              },
              "risk": "medium",
              "task": "TASK-100",
              "task_type": "implementation",
              "write_set": {
                "paths": [
                  "docs/notes/**"
                ]
              }
            },
            "contract_hash": "77b7c8fbaa03652aee270e94dfb5f2d0811c6c75ce693aeb76112514e2c74290",
            "dependencies": {
              "TASK-099": {
                "stale_evidence": false,
                "state": "DONE"
              }
            },
            "derived_read_set": [],
            "head_commit": "2222222222222222222222222222222222222222",
            "intent_current": {
              "SPEC-003": "v4"
            },
            "interfaces": [
              {
                "component": "CMP-API",
                "id": "load_policy"
              }
            ],
            "log_seq": 2,
            "observed_read_set": [],
            "policy_version": "v2",
            "risk_rules": [
              {
                "match": {
                  "paths": [
                    "docs/**"
                  ]
                },
                "risk": "medium"
              }
            ],
            "runtime": {
              "adapter": "an-adapter",
              "max_risk": "high"
            },
            "schemas": [
              {
                "base": {
                  "path": "src/app/api/record.json",
                  "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                },
                "head": {
                  "path": "src/app/api/record.json",
                  "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                },
                "name": "record"
              }
            ],
            "symbols": [
              {
                "base": "F(a)",
                "head": "F(a)",
                "interface": "load_policy"
              }
            ],
            "task_id": "TASK-100",
            "task_state": "READY"
          },
          "session_id": "session-1",
          "start_at": "2026-10-16T10:00:00Z",
          "task_id": "TASK-100"
        },
        "setup": [
          {
            "appended_at": "2026-10-16T09:00:00Z",
            "event_id": "drafted-1",
            "payload": {
              "contract_hash": "77b7c8fbaa03652aee270e94dfb5f2d0811c6c75ce693aeb76112514e2c74290",
              "contract_version": "v1"
            },
            "task_id": "TASK-100",
            "type": "task.drafted"
          },
          {
            "appended_at": "2026-10-16T09:01:00Z",
            "event_id": "approved-1",
            "payload": {
              "approval_record": "appr-1",
              "contract_hash": "77b7c8fbaa03652aee270e94dfb5f2d0811c6c75ce693aeb76112514e2c74290",
              "contract_version": "v1"
            },
            "task_id": "TASK-100",
            "type": "task.approved"
          }
        ],
        "submission": null,
        "violation": {
          "at": "2026-10-16T10:20:00Z",
          "event_id": "violation-1",
          "observation": {
            "blocking_kind": "violation",
            "evidence_type": "write_outside_write_set",
            "fact_kind": "observation",
            "outcome": "blocking",
            "record_id": "obs-1",
            "recorder": "replay:session-one",
            "refers_to": "src/outside.py",
            "source_class": "deterministic_tool_local",
            "subject": "TASK-100"
          }
        }
      },
      "evaluation": {
        "commits": [
          {
            "id": "3333333333333333333333333333333333333333",
            "paths": [
              "src/outside.py"
            ],
            "text": "tree 4444444444444444444444444444444444444444\u000aparent 1111111111111111111111111111111111111111\u000aauthor Tester <tester> 1700000000 +0000\u000acommitter Tester <tester> 1700000000 +0000\u000a\u000aDo the work\u000a\u000aThe body.\u000a\u000aAIEOS-Task: TASK-100\u000aAIEOS-Fence: e-replay:2\u000a"
          },
          {
            "id": "1111111111111111111111111111111111111111",
            "paths": [
              "docs/a.md"
            ],
            "text": "tree 4444444444444444444444444444444444444444\u000aauthor Tester <tester> 1700000000 +0000\u000acommitter Tester <tester> 1700000000 +0000\u000a\u000aMain\u000a\u000aThe body.\u000a"
          }
        ],
        "contract_text": "task: TASK-100\u000awrite_set:\u000a  paths: [docs/notes/**]\u000a",
        "declared": {
          "intent_versions": {
            "SPEC-001": "v1"
          },
          "retries": 2
        },
        "extra_records": [
          {
            "commit": "3333333333333333333333333333333333333333",
            "fact_kind": "observation",
            "gate": "G0",
            "intent_versions": {
              "SPEC-001": "v1"
            },
            "outcome": "pass",
            "record_id": "g0-1",
            "recorder": "ci",
            "source_class": "deterministic_tool_external_ci",
            "subject": "TASK-100"
          },
          {
            "commit": "3333333333333333333333333333333333333333",
            "fact_kind": "observation",
            "gate": "G1",
            "intent_versions": {
              "SPEC-001": "v1"
            },
            "outcome": "pass",
            "record_id": "g1-1",
            "recorder": "ci",
            "source_class": "deterministic_tool_external_ci",
            "subject": "TASK-100"
          },
          {
            "commit": "3333333333333333333333333333333333333333",
            "fact_kind": "observation",
            "gate": "G2",
            "intent_versions": {
              "SPEC-001": "v1"
            },
            "outcome": "pass",
            "record_id": "g2-1",
            "recorder": "ci",
            "source_class": "deterministic_tool_external_ci",
            "subject": "TASK-100"
          },
          {
            "commit": "3333333333333333333333333333333333333333",
            "dimension": "functional",
            "evidence_type": "build",
            "fact_kind": "observation",
            "intent_versions": {
              "SPEC-001": "v1"
            },
            "outcome": "pass",
            "record_id": "build-1",
            "recorder": "ci",
            "source_class": "deterministic_tool_external_ci",
            "subject": "TASK-100"
          },
          {
            "commit": "3333333333333333333333333333333333333333",
            "dimension": "functional",
            "evidence_type": "lint",
            "fact_kind": "observation",
            "intent_versions": {
              "SPEC-001": "v1"
            },
            "outcome": "pass",
            "record_id": "lint-1",
            "recorder": "ci",
            "source_class": "deterministic_tool_external_ci",
            "subject": "TASK-100"
          }
        ],
        "now": "2026-10-16T13:00:00Z",
        "recorder": "aieos-core",
        "task_id": "TASK-100",
        "values": {
          "articles": [],
          "auto_accept": {
            "critical": false,
            "high": false,
            "low": false,
            "medium": false
          },
          "changed_paths": [
            "src/outside.py"
          ],
          "contract": {
            "owner_kept_act": false,
            "risk": "low",
            "traces_to": [
              "SPEC-001"
            ],
            "verification_plan": [
              "G1",
              "G2"
            ]
          },
          "default_profiles": {
            "low": [
              {
                "dimension": "functional",
                "evidence_types": [
                  "build",
                  "lint"
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
              "id": "R-placeholder",
              "match": [
                "src/**"
              ]
            }
          ],
          "ruleset_version": "v1"
        }
      },
      "expected": {
        "decision": [
          "REJECT"
        ],
        "next_state": [
          "REJECTED"
        ],
        "not_fixed": [
          "metrics"
        ],
        "stop": [
          "STOP: violation"
        ]
      },
      "given": {
        "outside_path": "src/outside.py",
        "write_set": [
          "docs/notes/**"
        ]
      }
    }
  ],
  "row_hash": "d11a86217d650c426e5f3897c5cd797af656d610db573aeae4a6184292652742",
  "scenario": "ADV-02"
}
'''
