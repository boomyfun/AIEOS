DATA = r'''{
  "cases": [
    {
      "expected": {
        "decision": [
          "CONTINUE"
        ],
        "not_fixed": []
      },
      "inputs": {
        "approved_contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
        "articles": [
          {
            "applicability": {
              "task_types": [
                "implementation",
                "refactoring"
              ]
            },
            "id": "INV-001",
            "scope": {
              "components": [],
              "paths": [
                "src/**"
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
            "id": "0ea5c2ee34af538f4772f2af5caf19ecdd428cd3",
            "paths": [
              {
                "change": "modified",
                "path": "docs/notes.md"
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
          },
          {
            "id": "CMP-CORE",
            "paths": [
              "src/app/core/**"
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
            },
            "max_level": "L1"
          },
          "constitution": [
            "INV-001"
          ],
          "contract_version": "v1",
          "input_state": {
            "base_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
              "src/app/core/**"
            ]
          }
        },
        "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
        "dependencies": {
          "TASK-099": {
            "stale_evidence": false,
            "state": "DONE"
          }
        },
        "derived_read_set": [],
        "head_commit": "5c15dc27b67ce1bac16c2d11856d9298f66f90bf",
        "intent_current": {
          "SPEC-003": "v4"
        },
        "interfaces": [
          {
            "component": "CMP-API",
            "id": "load_policy"
          }
        ],
        "log_seq": 7,
        "observed_read_set": null,
        "policy_version": "v2",
        "risk_rules": [
          {
            "match": {
              "paths": [
                "src/**"
              ]
            },
            "risk": "medium"
          }
        ],
        "runtime": {
          "adapter": "placeholder-adapter",
          "max_risk": "high"
        },
        "schemas": [
          {
            "base": {
              "path": "src/app/api/record.json",
              "sha256": "327659b714dff6e0742d9315b5cfa034b0521915a1ba6cc8adc76cb910b75cc5"
            },
            "head": {
              "path": "src/app/api/record.json",
              "sha256": "327659b714dff6e0742d9315b5cfa034b0521915a1ba6cc8adc76cb910b75cc5"
            },
            "name": "record"
          }
        ],
        "symbols": [
          {
            "base": "FunctionDef(name='load_policy', args=arguments(args=[arg(arg='path', annotation=Name(id='str', ctx=Load()))]), body=[Pass()], returns=Name(id='dict', ctx=Load()))",
            "head": "FunctionDef(name='load_policy', args=arguments(args=[arg(arg='path', annotation=Name(id='str', ctx=Load()))]), body=[Pass()], returns=Name(id='dict', ctx=Load()))",
            "interface": "load_policy"
          }
        ],
        "task_id": "TASK-100",
        "task_state": "READY"
      },
      "when": "resume"
    }
  ],
  "row_hash": "c4b4e0157262949fb6df4b209befe61a5c4fe8bd7c4c4da7a4ba995d22981519",
  "scenario": "RC-02"
}
'''
