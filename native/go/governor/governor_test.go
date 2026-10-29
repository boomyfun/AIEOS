package main

// The native governor's own tests (TASK-100 AC3, AC4), run as `go test -count=1 -v . -args <fixture document>
// <governor reference document>`. They read only the two documents named by those arguments; the governor reference
// is read here only, as the expected output. casesJSON holds the bootstrap's own results for AC4's inputs, computed
// by a scratch run of records.check_record and governor.evaluate at the contract's commit (its script and output are
// in commit X's approval request).

import (
	"bytes"
	"errors"
	"flag"
	"fmt"
	"math/big"
	"os"
	"strings"
	"testing"
)

// documents reads the two documents named after -args; a missing argument fails the test (it never skips).
func documents(t *testing.T) (fixtures, reference []byte) {
	t.Helper()
	args := flag.Args()
	if len(args) != 2 {
		t.Fatalf("run as: go test -count=1 -v . -args <fixture document> <governor reference> (got %d arguments)", len(args))
	}
	fixtures, err := os.ReadFile(args[0])
	if err != nil {
		t.Fatalf("reading the fixture document: %v", err)
	}
	reference, err = os.ReadFile(args[1])
	if err != nil {
		t.Fatalf("reading the governor reference: %v", err)
	}
	return fixtures, reference
}

func firstDifference(a, b []byte) string {
	la, lb := strings.Split(string(a), "\n"), strings.Split(string(b), "\n")
	for i := 0; i < len(la) || i < len(lb); i++ {
		var x, y string
		if i < len(la) {
			x = la[i]
		}
		if i < len(lb) {
			y = lb[i]
		}
		if x != y || i >= len(la) || i >= len(lb) {
			return fmt.Sprintf("line %d: got %q, want %q", i+1, x, y)
		}
	}
	return "no line differs"
}

// memRead serves the fixture document under one name only, so that run reads no path in the tests.
func memRead(name string, data []byte) func(string) ([]byte, error) {
	return func(p string) ([]byte, error) {
		if p != name {
			return nil, errors.New("no such file: " + p)
		}
		return data, nil
	}
}

func TestWholeDocumentByteEqual(t *testing.T) {
	fixtures, reference := documents(t)
	got, err := buildDocument(fixtures)
	if err != nil {
		t.Fatalf("buildDocument: %v", err)
	}
	if !bytes.Equal(got, reference) {
		t.Fatalf("the document differs from the governor reference (%d bytes, want %d): %s", len(got), len(reference),
			firstDifference(got, reference))
	}
}

func TestRunWritesTheDocumentOnce(t *testing.T) {
	fixtures, reference := documents(t)
	var out, errOut countingWriter
	if code := run([]string{"fixtures.json"}, memRead("fixtures.json", fixtures), &out, &errOut); code != 0 {
		t.Fatalf("exit %d, stderr %q", code, errOut.buf.String())
	}
	if out.writes != 1 || !bytes.Equal(out.buf.Bytes(), reference) {
		t.Fatalf("%d writes; byte-equal %v", out.writes, bytes.Equal(out.buf.Bytes(), reference))
	}
	if errOut.buf.Len() != 0 {
		t.Fatalf("stderr %q", errOut.buf.String())
	}
}

type countingWriter struct {
	buf    bytes.Buffer
	writes int
}

func (w *countingWriter) Write(p []byte) (int, error) {
	w.writes++
	return w.buf.Write(p)
}

// The document holds the governor folder's keys only; the fixture document's other folders are passed over.
func TestOnlyGovernorKeys(t *testing.T) {
	fixtures, _ := documents(t)
	doc, err := buildDocument(fixtures)
	if err != nil {
		t.Fatal(err)
	}
	v, err := parseJSON(doc)
	if err != nil {
		t.Fatal(err)
	}
	keys := v.(*Obj).Keys()
	if len(keys) == 0 {
		t.Fatal("no key")
	}
	for _, k := range keys {
		if !strings.HasPrefix(k, governorFolder+"/") {
			t.Errorf("the key %s is not of the governor folder", k)
		}
	}
	fv, err := parseJSON(fixtures)
	if err != nil {
		t.Fatal(err)
	}
	others := 0
	for _, k := range fv.(*Obj).Keys() {
		if !strings.HasPrefix(k, governorFolder+"/") {
			others++
		}
	}
	if others == 0 {
		t.Fatal("the fixture document holds no other folder, so passing them over is not shown")
	}
}

func TestGovernorCaseFieldByField(t *testing.T) {
	fixtures, reference := documents(t)
	fv, err := parseJSON(fixtures)
	if err != nil {
		t.Fatal(err)
	}
	rv, err := parseJSON(reference)
	if err != nil {
		t.Fatal(err)
	}
	const key = "fixtures/acc_01"
	recs, err := caseRecords(fv.(*Obj).Val(key).(*Obj).Val("cases").([]any)[:1])
	if err != nil {
		t.Fatal(err)
	}
	got := recs[0].(map[string]any)
	want := rv.(*Obj).Val(key).([]any)[0].(*Obj)
	if len(got) != len(want.Keys()) {
		t.Errorf("%s: %d keys, want %d", key, len(got), len(want.Keys()))
	}
	for _, k := range want.Keys() {
		gs, err1 := canonString(got[k])
		ws, err2 := canonString(want.Val(k))
		if err1 != nil || err2 != nil || gs != ws {
			t.Errorf("%s: field %s differs:\n got  %s\n want %s", key, k, gs, ws)
		}
	}
	// The record id is computed: "decision-" and the SHA-256 of the record's canonical text without it.
	without := map[string]any{}
	for k, v := range got {
		if k != "record_id" {
			without[k] = v
		}
	}
	text, err := canonString(without)
	if err != nil {
		t.Fatal(err)
	}
	if got["record_id"] != "decision-"+sha256Hex(text+"\n") {
		t.Errorf("record_id is not computed from the record")
	}
}

// mutate parses the fixture document, applies f, and writes it back in the canonical text.
func mutate(t *testing.T, fixtures []byte, f func(root *Obj)) []byte {
	t.Helper()
	v, err := parseJSON(fixtures)
	if err != nil {
		t.Fatal(err)
	}
	f(v.(*Obj))
	out, err := canonicalText(v)
	if err != nil {
		t.Fatal(err)
	}
	return out
}

func firstCase(root *Obj, key string) *Obj {
	return root.Val(key).(*Obj).Val("cases").([]any)[0].(*Obj)
}

func TestFailClosed(t *testing.T) {
	fixtures, _ := documents(t)
	const name = "fixtures.json"
	type tc struct {
		what string
		args []string
		data []byte
	}
	doc := func(f func(root *Obj)) []byte { return mutate(t, fixtures, f) }
	cases := []tc{
		{"no argument", []string{}, fixtures},
		{"an extra argument", []string{name, "other.json"}, fixtures},
		{"a file that cannot be read", []string{"missing.json"}, fixtures},
		{"an empty file", []string{name}, []byte{}},
		{"not JSON", []string{name}, []byte("not json\n")},
		{"a truncated document", []string{name}, fixtures[:len(fixtures)/2]},
		{"not one object", []string{name}, []byte("[]\n")},
		{"not canonical (indent)", []string{name}, bytes.Replace(fixtures, []byte("\n  \""), []byte("\n   \""), 1)},
		{"not canonical (CR LF)", []string{name}, bytes.ReplaceAll(fixtures, []byte("\n"), []byte("\r\n"))},
		{"not canonical (no final LF)", []string{name}, bytes.TrimSuffix(fixtures, []byte("\n"))},
		{"a byte-order mark", []string{name}, append([]byte("\xef\xbb\xbf"), fixtures...)},
		{"not UTF-8", []string{name}, append(append([]byte{}, fixtures[:len(fixtures)-3]...), 0xff, '}', '\n')},
		{"a repeated key", []string{name}, []byte("{\n  \"fixtures/a\": {},\n  \"fixtures/a\": {}\n}\n")},
		{"a fixture that is a number", []string{name}, doc(func(r *Obj) {
			r.Set("fixtures/acc_01", 1)
		})},
		{"a number with a fraction", []string{name}, bytes.Replace(doc(func(r *Obj) {
			firstCase(r, "fixtures/acc_01").Val("request").(*Obj).Val("retry_count").(*Obj).Set("used", big.NewInt(7))
		}), []byte(`"used": 7`), []byte(`"used": 7.0`), 1)},
		{"an integer of more than 4300 digits", []string{name}, doc(func(r *Obj) {
			n, _ := new(big.Int).SetString("1"+strings.Repeat("0", 4300), 10)
			firstCase(r, "fixtures/acc_01").Val("request").(*Obj).Val("retry_count").(*Obj).Set("used", n)
		})},
		{"no governor fixture", []string{name}, doc(func(r *Obj) {
			for _, k := range append([]string(nil), r.Keys()...) {
				if strings.HasPrefix(k, governorFolder+"/") {
					r.Del(k)
				}
			}
		})},
		{"an unknown folder", []string{name}, doc(func(r *Obj) { r.Set("other/x", r.Val("fixtures/acc_01")) })},
		{"a key without a folder", []string{name}, doc(func(r *Obj) { r.Set("acc_99", r.Val("fixtures/acc_01")) })},
		{"an empty file stem", []string{name}, doc(func(r *Obj) { r.Set("fixtures/", r.Val("fixtures/acc_01")) })},
		{"a fixture that is not an object", []string{name}, doc(func(r *Obj) { r.Set("fixtures/acc_01", "x") })},
		{"no cases", []string{name}, doc(func(r *Obj) { r.Val("fixtures/acc_01").(*Obj).Set("cases", []any{}) })},
		{"cases not a list", []string{name}, doc(func(r *Obj) { r.Val("fixtures/acc_01").(*Obj).Set("cases", newObj()) })},
		{"a case that is not an object", []string{name}, doc(func(r *Obj) {
			r.Val("fixtures/acc_01").(*Obj).Set("cases", []any{"x"})
		})},
		{"a governor case without request", []string{name}, doc(func(r *Obj) { firstCase(r, "fixtures/acc_01").Del("request") })},
		{"a governor case without records", []string{name}, doc(func(r *Obj) { firstCase(r, "fixtures/acc_01").Del("records") })},
		// Cases that cannot be computed.
		{"a governor request without a task id (evaluate raises)", []string{name}, doc(func(r *Obj) {
			firstCase(r, "fixtures/acc_01").Val("request").(*Obj).Set("task_id", "task-1")
		})},
		{"a governor request that is not an object (evaluate raises)", []string{name}, doc(func(r *Obj) {
			firstCase(r, "fixtures/acc_01").Set("request", []any{})
		})},
		{"a record that is not ASCII", []string{name}, doc(func(r *Obj) {
			c := firstCase(r, "fixtures/acc_01")
			recs := c.Val("records").([]any)
			for _, x := range recs[:2] {
				x.(*Obj).Set("record_id", "ré")
			}
		})},
	}
	for _, c := range cases {
		var out, errOut bytes.Buffer
		code := run(c.args, memRead(name, c.data), &out, &errOut)
		if code == 0 {
			t.Errorf("%s: exit 0", c.what)
		}
		if out.Len() != 0 {
			t.Errorf("%s: %d bytes on standard output", c.what, out.Len())
		}
		if errOut.Len() == 0 {
			t.Errorf("%s: no reason on standard error", c.what)
		}
		t.Logf("%s: exit %d: %s", c.what, code, strings.TrimSpace(errOut.String()))
	}
}

// Python's json reads big integers exactly; a value just within the 4300-digit bound is kept and printed as is.
func TestBigIntegersKept(t *testing.T) {
	text := "{\n  \"a\": " + strings.Repeat("9", 4300) + "\n}\n"
	v, err := parseJSON([]byte(text))
	if err != nil {
		t.Fatal(err)
	}
	out, err := canonicalText(v)
	if err != nil || string(out) != text {
		t.Errorf("the integer is not kept: %v", err)
	}
}

func cases(t *testing.T, key string) []*Obj {
	t.Helper()
	v, err := parseJSON([]byte(casesJSON))
	if err != nil {
		t.Fatalf("casesJSON: %v", err)
	}
	var out []*Obj
	for _, e := range v.(*Obj).Val(key).([]any) {
		out = append(out, e.(*Obj))
	}
	if len(out) == 0 {
		t.Fatalf("no %s case", key)
	}
	return out
}

// TASK-100 AC4 (a): checkRecord gives records.check_record's whole rule list for each input, in its order.
func TestRecordFormsAC4a(t *testing.T) {
	for _, c := range cases(t, "check") {
		got := checkRecord(c.Val("record"))
		var want []string
		for _, r := range c.Val("rules").([]any) {
			want = append(want, r.(string))
		}
		if strings.Join(got, ",") != strings.Join(want, ",") || len(got) != len(want) {
			t.Errorf("%s: rules %v, want %v", c.Val("name"), got, want)
		}
	}
}

// TASK-100 AC4 (a) and (b): evaluate gives governor.evaluate's whole decision record for each input.
func TestEvaluateAC4b(t *testing.T) {
	for _, c := range cases(t, "evaluate") {
		rec, err := evaluate(c.Val("request"), c.Val("inputs"), c.Val("records"))
		if err != nil {
			t.Errorf("%s: %v", c.Val("name"), err)
			continue
		}
		got, err1 := canonString(rec)
		want, err2 := canonString(c.Val("record"))
		if err1 != nil || err2 != nil || got != want {
			t.Errorf("%s: the record differs: %s", c.Val("name"), firstDifference([]byte(got), []byte(want)))
		}
	}
}

// casesJSON is MYSP/t100/consts/cases.json of session 87e2584b, verbatim.
const casesJSON = `{
  "check": [
    {
      "name": "plain CI gate record",
      "record": {
        "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "dimension": "scope",
        "evidence_type": "scope_check",
        "fact_kind": "observation",
        "gate": "G0",
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "outcome": "pass",
        "record_id": "a1",
        "recorder": "external CI",
        "source_class": "deterministic_tool_external_ci",
        "subject": "TASK-101"
      },
      "rules": []
    },
    {
      "name": "not an object",
      "record": [
        "x"
      ],
      "rules": [
        "6.2:record"
      ]
    },
    {
      "name": "unknown key and missing keys",
      "record": {
        "record_id": "a2",
        "zz": 1
      },
      "rules": [
        "6.2:unknown_key",
        "6.2:missing_key",
        "6.2:missing_key",
        "6.2:missing_key",
        "6.2:missing_key"
      ]
    },
    {
      "name": "read_paths without the read-set type",
      "record": {
        "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "observation",
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "read_paths": [
          "p"
        ],
        "record_id": "a3",
        "recorder": "external CI",
        "source_class": "deterministic_tool_external_ci",
        "subject": "TASK-101"
      },
      "rules": [
        "6.2:read_set_key"
      ]
    },
    {
      "name": "read set: wrong fact kind, class, subject; no read_paths",
      "record": {
        "evidence_type": "observed_read_set",
        "fact_kind": "claim",
        "record_id": "a4",
        "recorder": "r",
        "source_class": "agent_declared",
        "subject": "INT-1"
      },
      "rules": [
        "6.2:read_set_fact_kind",
        "6.2:read_set_source_class",
        "6.2:read_set_subject",
        "6.2:read_set_key"
      ]
    },
    {
      "name": "read set: duplicate read_paths and forbidden keys",
      "record": {
        "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "dimension": "d",
        "evidence_type": "observed_read_set",
        "fact_kind": "observation",
        "gate": "G1",
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "outcome": "pass",
        "read_paths": [
          "p",
          "p"
        ],
        "record_id": "a5",
        "recorder": "r",
        "session": "s",
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101"
      },
      "rules": [
        "6.2:read_set_value",
        "6.2:read_set_forbidden",
        "6.2:read_set_forbidden",
        "6.2:read_set_forbidden",
        "6.2:read_set_forbidden",
        "6.2:read_set_forbidden",
        "6.2:read_set_forbidden"
      ]
    },
    {
      "name": "read set: well formed",
      "record": {
        "evidence_type": "observed_read_set",
        "fact_kind": "observation",
        "read_paths": [
          "a/b.py",
          "c.md"
        ],
        "record_id": "a6",
        "recorder": "r",
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101"
      },
      "rules": []
    },
    {
      "name": "session empty",
      "record": {
        "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "observation",
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "record_id": "a7",
        "recorder": "external CI",
        "session": "",
        "source_class": "deterministic_tool_external_ci",
        "subject": "TASK-101"
      },
      "rules": [
        "6.2:session"
      ]
    },
    {
      "name": "text without a session claim",
      "record": {
        "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "observation",
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "record_id": "a8",
        "recorder": "external CI",
        "source_class": "deterministic_tool_external_ci",
        "subject": "TASK-101",
        "text": "t"
      },
      "rules": [
        "6.2:text"
      ]
    },
    {
      "name": "text in a session claim",
      "record": {
        "acs": [
          "AC1"
        ],
        "fact_kind": "claim",
        "record_id": "a9",
        "recorder": "r",
        "session": "s1",
        "source_class": "agent_declared",
        "subject": "TASK-101",
        "text": "t"
      },
      "rules": []
    },
    {
      "name": "session claim with two acs",
      "record": {
        "acs": [
          "AC1",
          "AC2"
        ],
        "fact_kind": "claim",
        "record_id": "a10",
        "recorder": "r",
        "session": "s1",
        "source_class": "agent_declared",
        "subject": "TASK-101"
      },
      "rules": [
        "6.2:acs"
      ]
    },
    {
      "name": "acs empty",
      "record": {
        "acs": [],
        "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "observation",
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "record_id": "a11",
        "recorder": "external CI",
        "source_class": "deterministic_tool_external_ci",
        "subject": "TASK-101"
      },
      "rules": [
        "6.2:acs"
      ]
    },
    {
      "name": "acs on a gate record",
      "record": {
        "acs": [
          "AC1",
          "AC2"
        ],
        "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "dimension": "functional",
        "evidence_type": "unit_test",
        "fact_kind": "observation",
        "gate": "G2",
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "outcome": "pass",
        "record_id": "a12",
        "recorder": "external CI",
        "source_class": "deterministic_tool_external_ci",
        "subject": "TASK-101"
      },
      "rules": []
    },
    {
      "name": "acs with no gate and no session claim",
      "record": {
        "acs": [
          "AC1"
        ],
        "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "observation",
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "record_id": "a13",
        "recorder": "external CI",
        "source_class": "deterministic_tool_external_ci",
        "subject": "TASK-101"
      },
      "rules": [
        "6.2:acs"
      ]
    },
    {
      "name": "edit claim with text",
      "record": {
        "evidence_type": "contract_edit",
        "fact_kind": "claim",
        "record_id": "a14",
        "recorder": "r",
        "source_class": "agent_declared",
        "subject": "TASK-101",
        "text": "edit"
      },
      "rules": []
    },
    {
      "name": "intent claim with text",
      "record": {
        "evidence_type": "intent",
        "fact_kind": "claim",
        "record_id": "a15",
        "recorder": "r",
        "source_class": "agent_declared",
        "subject": "INT-7",
        "text": "intent"
      },
      "rules": []
    },
    {
      "name": "audit copy, well formed",
      "record": {
        "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "evidence_type": "risk_class",
        "fact_kind": "observation",
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "record_id": "a16",
        "recorder": "external CI",
        "risk_class": "high",
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101"
      },
      "rules": []
    },
    {
      "name": "audit copy with forbidden keys",
      "record": {
        "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "evidence_profile": [
          {
            "x": 1
          }
        ],
        "evidence_type": "evidence_profile",
        "fact_kind": "observation",
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "outcome": "pass",
        "record_id": "a17",
        "recorder": "external CI",
        "risk_class": "low",
        "source_class": "deterministic_tool_external_ci",
        "subject": "TASK-101"
      },
      "rules": [
        "6.2:audit_copy_value",
        "6.2:audit_copy_key",
        "6.2:audit_copy_forbidden"
      ]
    },
    {
      "name": "review fields",
      "record": {
        "basis": [],
        "evidence_type": "decision_agent_review",
        "fact_kind": "observation",
        "models": {
          "a": 1
        },
        "record_id": "a18",
        "recorder": "r",
        "source_class": "decision_agent",
        "stands_for": "",
        "subject": "TASK-101"
      },
      "rules": [
        "6.2:decision_ref",
        "6.2:models",
        "6.2:basis",
        "6.2:stands_for"
      ]
    },
    {
      "name": "blocking without a kind",
      "record": {
        "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "observation",
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "outcome": "blocking",
        "record_id": "a19",
        "recorder": "external CI",
        "source_class": "deterministic_tool_external_ci",
        "subject": "TASK-101"
      },
      "rules": [
        "6.2:blocking_kind"
      ]
    },
    {
      "name": "authority without a binding",
      "record": {
        "fact_kind": "authority",
        "record_id": "a20",
        "recorder": "r",
        "source_class": "human_authority",
        "subject": "TASK-101"
      },
      "rules": [
        "6.2:approval_binding"
      ]
    }
  ],
  "evaluate": [
    {
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
      "name": "as the fixture",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "NEEDS_REVIEW",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "IN_REVIEW",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          }
        ],
        "record_id": "decision-c1954a57f6f063fe7aa769e5c141dbdf5d8890fdbde0491cf5f8764ceb56cded",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 5,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
      }
    },
    {
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
      "name": "error record: a malformed task state",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": null,
        "error": "the request's task_state is malformed",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "DONE",
        "policy_version": "v1",
        "profile_used": [],
        "record_id": "decision-f5190d9bf50e3dce26928da0f17e0b6b69493eae446d37c428e417a1565870af",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": null,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
        "task_state": "DONE"
      }
    },
    {
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
        "risk": "none",
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
      "name": "error record: a malformed input",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": null,
        "error": "the inputs' risk is malformed",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "VERIFYING",
        "policy_version": "v1",
        "profile_used": [],
        "record_id": "decision-ca1c238b58121aba997b75fdee3b578bb738a29fe41db745ce19dbfac6ba953a",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": null,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
      }
    },
    {
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
      "name": "failed gate: rework",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "NEEDS_REWORK",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [
          "G1"
        ],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [
          "G1"
        ],
        "next_task_state": "REWORK",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [
              "build"
            ],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g2"
            ]
          }
        ],
        "record_id": "decision-22052669b20691de40acc9686d78e79a960fd63e5d2eba76769ea37747f982b9",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 2,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
          "outcome": "fail",
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
      }
    },
    {
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
      "name": "failed gate at the retry limit: escalated",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "NEEDS_REWORK",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [
          "G1"
        ],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [
          "G1"
        ],
        "next_task_state": "ESCALATED",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [
              "build"
            ],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g2"
            ]
          }
        ],
        "record_id": "decision-8237de590ac150bfb64ab72365e190cfd3efa8a4d867262f67bf2ec2ab5ca5c6",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 2,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
          "outcome": "fail",
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
          "used": 2
        },
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "task_id": "TASK-101",
        "task_state": "VERIFYING"
      }
    },
    {
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
      "name": "missing gate",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "INSUFFICIENT_EVIDENCE",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [
          "G2"
        ],
        "next_task_state": "REWORK",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [
              "lint"
            ],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1"
            ]
          }
        ],
        "record_id": "decision-a746270d1c9bc393b223c7a6d2a291953ac1a79fdf773be51b6bc53ce94e6fca",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 3,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
      }
    },
    {
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
          },
          {
            "dimension": "architecture",
            "evidence_types": [
              "ai_review (cross-model)"
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
      "name": "cross-model pair present",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "NEEDS_REVIEW",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "IN_REVIEW",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          },
          {
            "dimension": "architecture",
            "missing_types": [],
            "required": [
              "ai_review (cross-model)"
            ],
            "satisfied_by": [
              "TASK-101-dax",
              "TASK-101-w2"
            ]
          }
        ],
        "record_id": "decision-6ba56afbd656584da23c1df931ee15033c8d9b0b09e303a875bbdb4648f9a045",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": [
            {
              "dimension": "architecture",
              "evidence_type": "ai_review (cross-model)"
            }
          ]
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 5,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
        },
        {
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "decision_ref": "D-1",
          "dimension": "architecture",
          "evidence_type": "other_model_review",
          "fact_kind": "observation",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "models": {
            "implementer": "m2",
            "reviewer": "m1"
          },
          "outcome": "pass",
          "record_id": "TASK-101-w2",
          "recorder": "external CI",
          "source_class": "same_lineage_review",
          "subject": "TASK-101"
        },
        {
          "basis": "b",
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "decision_ref": "D-2",
          "dimension": "architecture",
          "evidence_type": "decision_agent_review",
          "fact_kind": "observation",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "outcome": "pass",
          "record_id": "TASK-101-dax",
          "recorder": "external CI",
          "source_class": "decision_agent",
          "stands_for": "ai_review (cross-model)",
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
      }
    },
    {
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
          },
          {
            "dimension": "architecture",
            "evidence_types": [
              "ai_review (cross-model)"
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
      "name": "cross-model pair without the decision agent half",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "INSUFFICIENT_EVIDENCE",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "REWORK",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          },
          {
            "dimension": "architecture",
            "missing_types": [
              "ai_review (cross-model)"
            ],
            "required": [
              "ai_review (cross-model)"
            ],
            "satisfied_by": []
          }
        ],
        "record_id": "decision-3f17514b2facaf7fac492c722d3c429b06b28e3a7d6e9dd8297746286e193aa2",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 3,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
        },
        {
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "decision_ref": "D-1",
          "dimension": "architecture",
          "evidence_type": "other_model_review",
          "fact_kind": "observation",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "models": {
            "implementer": "m2",
            "reviewer": "m1"
          },
          "outcome": "pass",
          "record_id": "TASK-101-w2",
          "recorder": "external CI",
          "source_class": "same_lineage_review",
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
      }
    },
    {
      "inputs": {
        "applicable_articles": [
          {
            "evidence_required": [
              "ai_review"
            ],
            "id": "INV-001"
          }
        ],
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
      "name": "ai_review via way-2",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "NEEDS_REVIEW",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "IN_REVIEW",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          },
          {
            "dimension": "INV-001",
            "missing_types": [],
            "required": [
              "ai_review"
            ],
            "satisfied_by": [
              "TASK-101-w2i"
            ]
          }
        ],
        "record_id": "decision-8c1fe3bef664dd5c6edab0e372bd047dc792d128c536135861425326afcef3af",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": [
            {
              "dimension": "INV-001",
              "evidence_type": "ai_review"
            }
          ]
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 5,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
        },
        {
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "decision_ref": "D-1",
          "dimension": "INV-001",
          "evidence_type": "other_model_review",
          "fact_kind": "observation",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "models": {
            "implementer": "m2",
            "reviewer": "m1"
          },
          "outcome": "pass",
          "record_id": "TASK-101-w2i",
          "recorder": "external CI",
          "source_class": "same_lineage_review",
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
      }
    },
    {
      "inputs": {
        "applicable_articles": [
          {
            "evidence_required": [
              "human_review"
            ],
            "id": "INV-003"
          }
        ],
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
      "name": "human_review via the decision agent",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "NEEDS_REVIEW",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "IN_REVIEW",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          },
          {
            "dimension": "INV-003",
            "missing_types": [],
            "required": [
              "human_review"
            ],
            "satisfied_by": [
              "TASK-101-da3"
            ]
          }
        ],
        "record_id": "decision-f2659c2100b55cfe7700ebfa117b63e23d6afade74d5623ac5bee93d7e936772",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": [
            {
              "dimension": "INV-003",
              "evidence_type": "human_review"
            }
          ]
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 5,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
        },
        {
          "basis": "b",
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "decision_ref": "D-2",
          "dimension": "INV-003",
          "evidence_type": "decision_agent_review",
          "fact_kind": "observation",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "outcome": "pass",
          "record_id": "TASK-101-da3",
          "recorder": "external CI",
          "source_class": "decision_agent",
          "stands_for": "human_review",
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
      }
    },
    {
      "inputs": {
        "applicable_articles": [
          {
            "evidence_required": [
              "human_review"
            ],
            "id": "INV-003"
          }
        ],
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
        "owner_kept_act": true,
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
      "name": "human_review via the decision agent, owner-kept",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "INSUFFICIENT_EVIDENCE",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "IN_REVIEW",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          },
          {
            "dimension": "INV-003",
            "missing_types": [
              "human_review"
            ],
            "required": [
              "human_review"
            ],
            "satisfied_by": []
          }
        ],
        "record_id": "decision-f0f10977b834b565ac0a758a893b90a9443b5085ce6acb4b2bfe8123c3680cb3",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 3,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
        },
        {
          "basis": "b",
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "decision_ref": "D-2",
          "dimension": "INV-003",
          "evidence_type": "decision_agent_review",
          "fact_kind": "observation",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "outcome": "pass",
          "record_id": "TASK-101-da3",
          "recorder": "external CI",
          "source_class": "decision_agent",
          "stands_for": "human_review",
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
      }
    },
    {
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
      "name": "approval at IN_REVIEW by the decision agent",
      "record": {
        "approval_record": "TASK-101-approval",
        "blocking": [],
        "decision": "NEEDS_REVIEW",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "ACCEPTED",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          }
        ],
        "record_id": "decision-c91ef388c01499d6a621656f9a6d7cfd0a3b42daa3fc2f0dd1f0ce4e215a744f",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": true,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 5,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
        },
        {
          "approval_binding": {
            "hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
            "kind": "acceptance"
          },
          "decision_ref": "D-3",
          "fact_kind": "authority",
          "record_id": "TASK-101-approval",
          "recorder": "r",
          "source_class": "decision_agent",
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
        "task_state": "IN_REVIEW"
      }
    },
    {
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
      "name": "approval at IN_REVIEW, delegation not in force",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "NEEDS_REVIEW",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "IN_REVIEW",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          }
        ],
        "record_id": "decision-331dfc4df61905fed9240035a7b0b07c180dfc76bc3fc3719e20b2ddf9ae33e5",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 5,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names",
          "TASK-101-approval: a delegated approval while the delegation is not in force"
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
        },
        {
          "approval_binding": {
            "hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
            "kind": "acceptance"
          },
          "decision_ref": "D-3",
          "fact_kind": "authority",
          "record_id": "TASK-101-approval",
          "recorder": "r",
          "source_class": "decision_agent",
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
        "task_state": "IN_REVIEW"
      }
    },
    {
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
        "owner_kept_act": true,
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
      "name": "approval at IN_REVIEW, owner-kept",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "NEEDS_REVIEW",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "IN_REVIEW",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          }
        ],
        "record_id": "decision-d58f0f993c2fc2c753d69449852675f8530ca6c08de1bc89980d021415684f5a",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 5,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names",
          "TASK-101-approval: a delegated approval where only the owner's counts"
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
        },
        {
          "approval_binding": {
            "hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
            "kind": "acceptance"
          },
          "decision_ref": "D-3",
          "fact_kind": "authority",
          "record_id": "TASK-101-approval",
          "recorder": "r",
          "source_class": "decision_agent",
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
        "task_state": "IN_REVIEW"
      }
    },
    {
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
      "name": "approval at IN_REVIEW by the owner",
      "record": {
        "approval_record": "TASK-101-owner",
        "blocking": [],
        "decision": "NEEDS_REVIEW",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "ACCEPTED",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          }
        ],
        "record_id": "decision-b9e618260ed6813300e09a57d54abfd6d3d3d8bb2e4e5342649a0dd102a2063e",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 5,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
        },
        {
          "approval_binding": {
            "hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
            "kind": "acceptance"
          },
          "decision_ref": "D-3",
          "fact_kind": "authority",
          "record_id": "TASK-101-owner",
          "recorder": "r",
          "source_class": "human_authority",
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
        "task_state": "IN_REVIEW"
      }
    },
    {
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
      "name": "approval bound to another hash",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "NEEDS_REVIEW",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "IN_REVIEW",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          }
        ],
        "record_id": "decision-dfd6e90d9738b6cbf9350cbd4c00b176ead9e09fd844b92e10110f8c9f899006",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 5,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names",
          "TASK-101-approval: an approval not bound to this task's content hash"
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
        },
        {
          "approval_binding": {
            "hash": "0000000000000000000000000000000000000000000000000000000000000000",
            "kind": "acceptance"
          },
          "decision_ref": "D-3",
          "fact_kind": "authority",
          "record_id": "TASK-101-approval",
          "recorder": "r",
          "source_class": "decision_agent",
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
        "task_state": "IN_REVIEW"
      }
    },
    {
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
      "name": "blocking row 1",
      "record": {
        "approval_record": null,
        "blocking": [
          "TASK-101-b1"
        ],
        "decision": "REJECT",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "REJECTED",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          }
        ],
        "record_id": "decision-c4190e5a1edac5e04965a53333792ead6094c912294b6f94ae41bcdb56945695",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 1,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
        },
        {
          "blocking_kind": "out_of_scope",
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "fact_kind": "observation",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "outcome": "blocking",
          "record_id": "TASK-101-b1",
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
      }
    },
    {
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
      "name": "blocking row 2",
      "record": {
        "approval_record": null,
        "blocking": [
          "TASK-101-b2"
        ],
        "decision": "NEEDS_REWORK",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "REWORK",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          }
        ],
        "record_id": "decision-d00c27f8a16bd87f2c68fe270ad331a3eac03e3b51e8e446312d87b83c908bf8",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 2,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
        },
        {
          "blocking_kind": "constitution",
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "fact_kind": "observation",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "outcome": "blocking",
          "record_id": "TASK-101-b2",
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
      }
    },
    {
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
      "name": "a stale record",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "INSUFFICIENT_EVIDENCE",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [
          "G2"
        ],
        "next_task_state": "REWORK",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [
              "lint"
            ],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1"
            ]
          }
        ],
        "record_id": "decision-714cd5c8c2de8b51b4c2f94e0da2ee2c82d8399a7c69d1195fb8eb1485eae463",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [
          "TASK-101-g2"
        ],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 3,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
          "commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
      }
    },
    {
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
      "name": "an audit copy",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "NEEDS_REVIEW",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "IN_REVIEW",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          }
        ],
        "record_id": "decision-c1954a57f6f063fe7aa769e5c141dbdf5d8890fdbde0491cf5f8764ceb56cded",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 5,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
        },
        {
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "evidence_type": "risk_class",
          "fact_kind": "observation",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "record_id": "TASK-101-rc",
          "recorder": "external CI",
          "risk_class": "low",
          "source_class": "deterministic_tool_local",
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
      }
    },
    {
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
      "name": "a read-set record without read_paths",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "NEEDS_REVIEW",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "IN_REVIEW",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          }
        ],
        "record_id": "decision-6195853d0d880e172ffe61bc41337405442bec44d7811de25a814cfaf0b390eb",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 5,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names",
          "TASK-101-rs: not used: 6.2:read_set_key"
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
        },
        {
          "evidence_type": "observed_read_set",
          "fact_kind": "observation",
          "record_id": "TASK-101-rs",
          "recorder": "r",
          "source_class": "deterministic_tool_local",
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
      }
    },
    {
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
      "name": "a gate record with session and acs",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "NEEDS_REVIEW",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "IN_REVIEW",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          }
        ],
        "record_id": "decision-c1954a57f6f063fe7aa769e5c141dbdf5d8890fdbde0491cf5f8764ceb56cded",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 5,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names"
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
          "acs": [
            "AC1"
          ],
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
          "session": "s1",
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
      }
    },
    {
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
      "name": "an edit claim with text",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "NEEDS_REVIEW",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "IN_REVIEW",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          }
        ],
        "record_id": "decision-87dc198858298a7d0a3cf9aa359410c0b79709a23240187ebc87ccb98d7aa3fe",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 5,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names",
          "TASK-101-edit: not used: no commit binding"
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
        },
        {
          "evidence_type": "contract_edit",
          "fact_kind": "claim",
          "record_id": "TASK-101-edit",
          "recorder": "r",
          "source_class": "agent_declared",
          "subject": "TASK-101",
          "text": "edit"
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
      }
    },
    {
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
      "name": "a record of another subject",
      "record": {
        "approval_record": null,
        "blocking": [],
        "decision": "NEEDS_REVIEW",
        "evaluated_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fact_kind": "interpretation",
        "failed_gates": [],
        "governor_identity": null,
        "intent_versions": {
          "SPEC-012": "v3"
        },
        "level_version": "v1",
        "missing_gates": [],
        "next_task_state": "IN_REVIEW",
        "policy_version": "v1",
        "profile_used": [
          {
            "dimension": "functional",
            "missing_types": [],
            "required": [
              "build",
              "lint"
            ],
            "satisfied_by": [
              "TASK-101-g1",
              "TASK-101-g2"
            ]
          }
        ],
        "record_id": "decision-ca2804bbc09425ffa93dda69555ad092474eff99c6252c3c7c7937611b8812bf",
        "recorder": "src/aieos_bootstrap/governor.py",
        "rests_on_ai": {
          "approval": false,
          "entries": []
        },
        "reverify": [],
        "ruleset_version": "v1",
        "scenario_set_hash": null,
        "source_class": "deterministic_tool_local",
        "subject": "TASK-101",
        "table_row": 5,
        "task_content_hash": "74040dfcc89f40925514fae0c267317ac4efc8fca8a7fb4651dea7ed803ec023",
        "uncovered": [
          "advisory: decisions of this governor are advisory (governor-spec.md section 10)",
          "inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
          "identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this module's defaults, not the channel or the identity that specification 2 section 6.4 names",
          "TASK-102-x: about another subject, not read"
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
        },
        {
          "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "fact_kind": "observation",
          "gate": "G9",
          "intent_versions": {
            "SPEC-012": "v3"
          },
          "record_id": "TASK-102-x",
          "recorder": "external CI",
          "source_class": "deterministic_tool_external_ci",
          "subject": "TASK-102"
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
      }
    }
  ]
}
`
