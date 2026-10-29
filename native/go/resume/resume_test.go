package main

// The port's own tests, run as `go test -count=1 . -args <fixture document> <Resume Check reference document>`. They
// read only the two documents named by those arguments; the reference document is read here only, as the expected
// output. rcCases, at the end, are the records resume_check.check returned for named inputs in a scratch run of the
// bootstrap (TASK-101 AC4 (c), (d)), written here as literals.

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
		t.Fatalf("run as: go test -count=1 . -args <fixture document> <reference document> (got %d arguments)", len(args))
	}
	fixtures, err := os.ReadFile(args[0])
	if err != nil {
		t.Fatalf("reading the fixture document: %v", err)
	}
	reference, err = os.ReadFile(args[1])
	if err != nil {
		t.Fatalf("reading the reference document: %v", err)
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
		t.Fatalf("the document differs from the reference (%d bytes, want %d): %s", len(got), len(reference),
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

// fieldByField computes the first case of one fixture and compares it with the reference's record key by key.
func fieldByField(t *testing.T, key string) map[string]any {
	t.Helper()
	fixtures, reference := documents(t)
	fv, err := parseJSON(fixtures)
	if err != nil {
		t.Fatal(err)
	}
	rv, err := parseJSON(reference)
	if err != nil {
		t.Fatal(err)
	}
	fixture, ok := fv.(*Obj).Val(key).(*Obj)
	if !ok {
		t.Fatalf("no fixture %s", key)
	}
	recs, err := caseRecords(fixture.Val("cases").([]any)[:1])
	if err != nil {
		t.Fatal(err)
	}
	got := recs[0].(map[string]any)
	want := rv.(*Obj).Val(key).([]any)[0].(*Obj)
	if len(got) != len(want.Keys()) {
		t.Errorf("%s: %d keys, want %d", key, len(got), len(want.Keys()))
	}
	for _, k := range want.Keys() {
		g, ok := got[k]
		if !ok {
			t.Errorf("%s: key %s is missing", key, k)
			continue
		}
		gs, err1 := canonString(g)
		ws, err2 := canonString(want.Val(k))
		if err1 != nil || err2 != nil || gs != ws {
			t.Errorf("%s: field %s differs:\n got  %s\n want %s", key, k, gs, ws)
		}
	}
	return got
}

func TestResumeCheckCaseFieldByField(t *testing.T) {
	got := fieldByField(t, "fixtures_rc/rc_01")
	if _, ok := got["error"]; ok {
		t.Errorf("an error record: %v", got["error"])
	}
	if len(got["checks"].([]any)) != 8 {
		t.Errorf("not eight checks")
	}
}

func TestPlaceholder(t *testing.T) {
	fixtures, _ := documents(t)
	doc, err := buildDocument(fixtures)
	if err != nil {
		t.Fatal(err)
	}
	v, err := parseJSON(doc)
	if err != nil {
		t.Fatal(err)
	}
	rcRecords := 0
	for _, key := range v.(*Obj).Keys() {
		if !strings.HasPrefix(key, rcFolder+"/") {
			t.Errorf("%s: a key of another folder in the document", key)
		}
		for _, r := range v.(*Obj).Val(key).([]any) {
			rcRecords++
			ei, has := r.(*Obj).Get("engine_identity")
			if !has || ei.(*Obj).Val("python") != enginePlaceholder {
				t.Errorf("%s: engine_identity.python is not the placeholder", key)
			}
		}
	}
	if rcRecords == 0 {
		t.Fatal("no Resume Check record")
	}
	// The placeholder is the one value replaced: it appears once per Resume Check record, as that key's value.
	if n := strings.Count(string(doc), enginePlaceholder); n != rcRecords {
		t.Errorf("the placeholder appears %d times, want %d", n, rcRecords)
	}
	if n := strings.Count(string(doc), `"python": "`+enginePlaceholder+`"`); n != rcRecords {
		t.Errorf("the placeholder is the python value %d times, want %d", n, rcRecords)
	}
	// The raw record of the check carries the placeholder too, so no interpreter version can reach the output.
	rec := placeholder(map[string]any{"engine_identity": map[string]any{"code_sha256": nil, "python": "x"}})
	if rec["engine_identity"].(map[string]any)["python"] != enginePlaceholder {
		t.Errorf("placeholder does not replace engine_identity.python")
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
	const rc = "fixtures_rc/rc_01"
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
		{"a repeated key", []string{name}, []byte("{\n  \"fixtures_rc/a\": {},\n  \"fixtures_rc/a\": {}\n}\n")},
		{"a fixture that is a number", []string{name}, doc(func(r *Obj) {
			r.Set(rc, 1)
		})},
		{"a number with a fraction", []string{name}, bytes.Replace(doc(func(r *Obj) {
			firstCase(r, rc).Val("inputs").(*Obj).Set("log_seq", big.NewInt(7))
		}), []byte(`"log_seq": 7`), []byte(`"log_seq": 7.0`), 1)},
		{"an integer of more than 4300 digits", []string{name}, doc(func(r *Obj) {
			n, _ := new(big.Int).SetString("1"+strings.Repeat("0", 4300), 10)
			firstCase(r, rc).Val("inputs").(*Obj).Set("log_seq", n)
		})},
		{"no Resume Check fixture", []string{name}, doc(func(r *Obj) {
			for _, k := range append([]string(nil), r.Keys()...) {
				if strings.HasPrefix(k, rcFolder+"/") {
					r.Del(k)
				}
			}
		})},
		{"an unknown folder", []string{name}, doc(func(r *Obj) { r.Set("other/x", r.Val(rc)) })},
		{"a key without a folder", []string{name}, doc(func(r *Obj) { r.Set("rc_99", r.Val(rc)) })},
		{"an empty file stem", []string{name}, doc(func(r *Obj) { r.Set(rcFolder+"/", r.Val(rc)) })},
		{"a fixture that is not an object", []string{name}, doc(func(r *Obj) { r.Set(rc, "x") })},
		{"no cases", []string{name}, doc(func(r *Obj) { r.Val(rc).(*Obj).Set("cases", []any{}) })},
		{"cases not a list", []string{name}, doc(func(r *Obj) { r.Val(rc).(*Obj).Set("cases", newObj()) })},
		{"a case that is not an object", []string{name}, doc(func(r *Obj) { r.Val(rc).(*Obj).Set("cases", []any{"x"}) })},
		{"a Resume Check case without inputs", []string{name}, doc(func(r *Obj) { firstCase(r, rc).Del("inputs") })},
		{"a record that is not ASCII", []string{name}, doc(func(r *Obj) {
			firstCase(r, rc).Val("inputs").(*Obj).Val("runtime").(*Obj).Set("adapter", "ré")
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

// The unexpected-error paths of resume_check.check fail closed (TASK-101 AC4 (b)): a panic while the inputs are read
// or while the check runs is a case that cannot be computed, never a record; the ValueError of a budget amount is the
// one panic that gives the Python's error record (AC4 (c)).
func TestUnexpectedErrorsFailClosed(t *testing.T) {
	if _, err := guarded(func() string { panic("x") }); !errors.Is(err, errCannotCompute) {
		t.Errorf("a panic while reading the inputs: %v", err)
	}
	if rec, err := notCompleted(nil, nil, cannotCompute{"x"}); rec != nil || !errors.Is(err, errCannotCompute) {
		t.Errorf("a panic while the check runs: %v %v", rec, err)
	}
	rec, err := notCompleted(nil, nil, pyValueError{})
	if err != nil || rec["error"] != "the check could not complete: ValueError" {
		t.Errorf("the ValueError of a budget amount: %v %v", rec, err)
	}
	fixtures, _ := documents(t)
	v, err := parseJSON(fixtures)
	if err != nil {
		t.Fatal(err)
	}
	inputs := firstCase(v.(*Obj), "fixtures_rc/rc_01").Val("inputs").(*Obj)
	inputs.Val("budget_use").(*Obj).Val("tokens").(*Obj).Set("used", strings.Repeat("1", 4301)+"k")
	rec, err = check(inputs, nil)
	if err != nil || rec["error"] != "the check could not complete: ValueError" {
		t.Errorf("a budget amount of 4301 digits: %v %v", rec, err)
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

// The digit bound of Python's int(), found by the scratch run's search, not assumed (TASK-101 AC4 (c)): the largest
// accepted digit count and the smallest refused one, a refused text of leading zeros, and the fixture reader's
// refusal of an integer literal of the smallest refused count.
const (
	pyLargestAcceptedDigits = 4300
	pySmallestRefusedDigits = 4301
)

func TestDigitBound(t *testing.T) {
	if maxIntDigits != pyLargestAcceptedDigits || pySmallestRefusedDigits != pyLargestAcceptedDigits+1 {
		t.Fatalf("the bound %d is not the Python's %d", maxIntDigits, pyLargestAcceptedDigits)
	}
	if amount("tokens", strings.Repeat("9", pyLargestAcceptedDigits)) == nil {
		t.Errorf("the largest accepted digit count is not read")
	}
	for _, s := range []string{strings.Repeat("9", pySmallestRefusedDigits), strings.Repeat("0", pySmallestRefusedDigits)} {
		func() {
			defer func() {
				if _, ok := recover().(pyValueError); !ok {
					t.Errorf("a digit text of %d digits is not refused as the Python's ValueError", len(s))
				}
			}()
			amount("tokens", s)
		}()
	}
	text := "{\n  \"a\": 1" + strings.Repeat("0", pyLargestAcceptedDigits) + "\n}\n"
	if _, err := parseJSON([]byte(text)); err == nil {
		t.Errorf("an integer literal of %d digits is read", pySmallestRefusedDigits)
	}
}

// Each entry of rcCases is checked: its inputs and code_sha256 given to check, the port's record compared with the
// Python's whole record in the canonical text.
func TestPythonComputedRecords(t *testing.T) {
	if len(rcCases) != 49 {
		t.Fatalf("%d cases, want 49", len(rcCases))
	}
	for _, text := range rcCases {
		v, err := parseJSON([]byte(text))
		if err != nil {
			t.Fatal(err)
		}
		c := v.(*Obj)
		name := c.Val("name").(string)
		var code *string
		if s, ok := c.Val("code_sha256").(string); ok {
			code = &s
		}
		got, err := check(c.Val("inputs"), code)
		if err != nil {
			t.Errorf("%s: %v", name, err)
			continue
		}
		want := c.Val("record").(*Obj)
		// The one change: engine_identity.python is the interpreter's version in the Python's record and the
		// placeholder in the port's (TASK-101 AC4 (a)); it is changed here, in the expected record only.
		want.Val("engine_identity").(*Obj).Set("python", enginePlaceholder)
		gs, err1 := canonString(got)
		ws, err2 := canonString(want)
		if err1 != nil || err2 != nil || gs != ws {
			t.Errorf("%s: the record differs: %s", name, firstDifference([]byte(gs), []byte(ws)))
		}
	}
}

// rcCases are the 49 entries of the scratch run's output (SHA-256 5e224c6e0ebb1128...), each its canonical text.
var rcCases = []string{
	`{
  "code_sha256": null,
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "as the fixture",
  "record": {
    "base_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit equals HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 3,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "CONTINUE",
    "delta": [],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": "xyz",
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "row 1, row 2: code_sha256 malformed",
  "record": {
    "decision": null,
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "error": "code_sha256 is not 64 lowercase hex digits",
    "fact_kind": "interpretation",
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "row 1, row 2: a valid code_sha256",
  "record": {
    "base_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit equals HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 3,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "CONTINUE",
    "delta": [],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "a8f502e886d27c1a671172d2542e89a91272b7351293b1e96ce9ccac868c24ad",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "row 1, row 15: an input missing",
  "record": {
    "decision": null,
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "error": "an input is missing or malformed: inputs lacks runtime",
    "fact_kind": "interpretation",
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_current": {
      "SPEC-003": "v4"
    },
    "interfaces": [
      {
        "component": "CMP-API",
        "id": "load_policy"
      }
    ],
    "log_seq": -1,
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
  "name": "row 1, row 15: an input malformed",
  "record": {
    "decision": null,
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "error": "an input is missing or malformed: log_seq is not an integer from 0 to 2**63 - 1",
    "fact_kind": "interpretation",
    "record_id": "1d142c87a4c933920e789156359f70e4ea8e28c10b85470e99af7b40521eeaeb",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
  "inputs": [
    "x"
  ],
  "name": "row 1, row 15: inputs not an object",
  "record": {
    "decision": null,
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "error": "an input is missing or malformed: inputs is not an object",
    "fact_kind": "interpretation",
    "record_id": "85066fbbd28ee64448c27b423099d57cfc496f48353a42149228f2b74149cf27",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-0",
    "uncovered": [
      "engine_identity.code_sha256: not given by the caller",
      "subject: task_id is malformed, so TASK-0 stands for it (decision D-359)"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
    "commits": [],
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
      "risk": "none",
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "row 1, row 19: a failing input of the contract",
  "record": {
    "decision": null,
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "error": "an input is missing or malformed: contract risk is not low, medium, high or critical",
    "fact_kind": "interpretation",
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
  "inputs": {
    "approved_contract_hash": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "row 1: check 0, the contract at HEAD is not the approved contract",
  "record": {
    "decision": null,
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "error": "check 0: the contract at HEAD is not the approved contract",
    "fact_kind": "interpretation",
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
    "task_id": "TASK-x",
    "task_state": "READY"
  },
  "name": "rows 10, 11: task_id malformed",
  "record": {
    "decision": null,
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "error": "an input is missing or malformed: task_id is not TASK-<digits>",
    "fact_kind": "interpretation",
    "record_id": "4cab59bc011825f4d806e0459f07970e60f525105e4f3833a36dbe45e83bc707",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-0",
    "uncovered": [
      "engine_identity.code_sha256: not given by the caller",
      "subject: task_id is malformed, so TASK-0 stands for it (decision D-359)"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_current": {
      "SPEC-003": "v4"
    },
    "interfaces": [
      {
        "component": "CMP-API",
        "id": "load_policy"
      }
    ],
    "log_seq": -1,
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
    "task_id": "TASK-0",
    "task_state": "READY"
  },
  "name": "rows 10, 11: task_id TASK-0 in an error record",
  "record": {
    "decision": null,
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "error": "an input is missing or malformed: log_seq is not an integer from 0 to 2**63 - 1",
    "fact_kind": "interpretation",
    "record_id": "109acdf0fecaf7c5b4c68107c304aae38b30e8188f34613edad40fa985c45e7a",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-0",
    "uncovered": [
      "engine_identity.code_sha256: not given by the caller",
      "subject: task_id is malformed, so TASK-0 stands for it (decision D-359)"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
    "base_is_ancestor": false,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "x/a.txt"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
  "name": "rows 27, 28: base_commit not an ancestor",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit is not an ancestor of HEAD",
        "outcome": "ESCALATE",
        "status": "fired"
      },
      {
        "check": 2,
        "detail": "the delta cannot be computed",
        "outcome": null,
        "status": "not_run"
      },
      {
        "check": 3,
        "detail": "the delta cannot be computed",
        "outcome": null,
        "status": "not_run"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "ESCALATE",
    "delta": [],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "ESCALATE"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "3e3257d93bad8ac838577ea5b3626a7b713825927a3917e5e275813af3c3f3c9",
        "payload": {
          "blocked_by": [
            "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e"
          ],
          "reason": "escalate"
        },
        "task_id": "TASK-100",
        "type": "task.blocked"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
    "base_is_ancestor": false,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "x/a.txt"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "depends_on": [
          "TASK-9"
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
    "dependencies": {},
    "derived_read_set": [],
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
  "name": "row 49: two checks fire (not an ancestor, a dependency unknown)",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit is not an ancestor of HEAD",
        "outcome": "ESCALATE",
        "status": "fired"
      },
      {
        "check": 2,
        "detail": "the delta cannot be computed",
        "outcome": null,
        "status": "not_run"
      },
      {
        "check": 3,
        "detail": "the delta cannot be computed",
        "outcome": null,
        "status": "not_run"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "a dependency is not DONE, is STALE or is unknown: TASK-9",
        "outcome": "BLOCKED",
        "status": "fired"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "ESCALATE",
    "delta": [],
    "dependencies": {
      "TASK-9": null
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "ESCALATE",
      "BLOCKED"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "3e3257d93bad8ac838577ea5b3626a7b713825927a3917e5e275813af3c3f3c9",
        "payload": {
          "blocked_by": [
            "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e"
          ],
          "reason": "escalate"
        },
        "task_id": "TASK-100",
        "type": "task.blocked"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "x/c.txt"
          }
        ],
        "submitted": true
      },
      {
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "added",
            "path": "x/a.txt"
          },
          {
            "change": "deleted",
            "path": "x/b.txt"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
  "name": "row 24: added and deleted changes, a submitted commit skipped",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "2 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "delta meets no entry of the effective read-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "CONTINUE",
    "delta": [
      {
        "change": "added",
        "path": "x/a.txt"
      },
      {
        "change": "deleted",
        "path": "x/b.txt"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "x/a.txt"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
  "name": "row 18: a 64-hex commit",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "1 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "delta meets no entry of the effective read-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "CONTINUE",
    "delta": [
      {
        "change": "modified",
        "path": "x/a.txt"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "c3ba3e205e2af13ef2ae64bdad0c2a82659ebcf79846cc026ccde9e19ba3c71a",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "src/ab.py"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
          "src/a*.py"
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
  "name": "rows 33, 34: a star name meets a delta path",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "1 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta meets the write-set: src/ab.py",
        "outcome": "STOP: scope invalid",
        "status": "fired"
      },
      {
        "check": 3,
        "detail": "delta meets no entry of the effective read-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "STOP: scope invalid",
    "delta": [
      {
        "change": "modified",
        "path": "src/ab.py"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "STOP: scope invalid"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0",
        "payload": {
          "paths": [
            "src/ab.py"
          ],
          "tasks": []
        },
        "task_id": "TASK-100",
        "type": "conflict.detected"
      },
      {
        "event_id": "3e3257d93bad8ac838577ea5b3626a7b713825927a3917e5e275813af3c3f3c9",
        "payload": {
          "blocked_by": [
            "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0"
          ],
          "reason": "scope_invalid"
        },
        "task_id": "TASK-100",
        "type": "task.blocked"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller",
      "conflict.detected tasks: the commits' trailers are not an input"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "src/b.py"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
          "src/a*.py"
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
  "name": "rows 33, 34: a star name meets no delta path",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "1 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "delta meets no entry of the effective read-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "CONTINUE",
    "delta": [
      {
        "change": "modified",
        "path": "src/b.py"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "src/ab.py"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
          "ab.py"
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
  "name": "row 32: a pattern without \"/\"",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "1 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta meets the write-set: src/ab.py",
        "outcome": "STOP: scope invalid",
        "status": "fired"
      },
      {
        "check": 3,
        "detail": "delta meets no entry of the effective read-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "STOP: scope invalid",
    "delta": [
      {
        "change": "modified",
        "path": "src/ab.py"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "STOP: scope invalid"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0",
        "payload": {
          "paths": [
            "src/ab.py"
          ],
          "tasks": []
        },
        "task_id": "TASK-100",
        "type": "conflict.detected"
      },
      {
        "event_id": "3e3257d93bad8ac838577ea5b3626a7b713825927a3917e5e275813af3c3f3c9",
        "payload": {
          "blocked_by": [
            "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0"
          ],
          "reason": "scope_invalid"
        },
        "task_id": "TASK-100",
        "type": "task.blocked"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller",
      "conflict.detected tasks: the commits' trailers are not an input"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "x/a.txt"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
          "src/a*.py"
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
            "src/*_x.py"
          ]
        },
        "risk": "low"
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
  "name": "row 33: two starred names meet",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "1 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "delta meets no entry of the effective read-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "CONTINUE",
    "delta": [
      {
        "change": "modified",
        "path": "x/a.txt"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
            "**"
          ]
        },
        "risk": "extreme"
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
  "name": "row 43: a risk rule of an invalid class",
  "record": {
    "base_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit equals HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 3,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high is below the task risk critical",
        "outcome": "STOP: runtime insufficient",
        "status": "fired"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "STOP: runtime insufficient",
    "delta": [],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "STOP: runtime insufficient"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "critical"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
        "risk": "high"
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
  "name": "row 44: a risk rule without match.paths",
  "record": {
    "base_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit equals HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 3,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk high",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "CONTINUE",
    "delta": [],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "high"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
            "zz/**"
          ]
        },
        "risk": "low"
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
  "name": "row 43: a write-set pattern no rule meets",
  "record": {
    "base_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit equals HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 3,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "a write-set pattern meets no risk rule: src/app/core/**",
        "outcome": "ESCALATE",
        "status": "fired"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "ESCALATE",
    "delta": [],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "ESCALATE"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "02a0fde469e5322baedd4d7c4ddcda136c6e4347c023adbf6f3644ebbbe42027",
        "payload": {
          "blocked_by": [
            "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c"
          ],
          "reason": "escalate"
        },
        "task_id": "TASK-100",
        "type": "task.blocked"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "lib/m.py"
          }
        ],
        "submitted": false
      }
    ],
    "components": [
      {
        "id": "C1",
        "paths": [
          "lib"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "depends_on": [
          "TASK-099"
        ],
        "intent_versions": {
          "SPEC-003": "v4"
        }
      },
      "read_set": {
        "interfaces": [
          "I1"
        ],
        "paths": [],
        "schemas": []
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_current": {
      "SPEC-003": "v4"
    },
    "interfaces": [
      {
        "component": "C1",
        "id": "I1"
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
        "base": "s",
        "head": "s",
        "interface": "I1"
      }
    ],
    "task_id": "TASK-100",
    "task_state": "READY"
  },
  "name": "rows 35, 38: interface met, signature equal (non-wildcard component path)",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "1 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "every met entry is non-breaking",
        "outcome": "CONTINUE_WITH",
        "status": "fired"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "CONTINUE_WITH",
    "delta": [
      {
        "change": "modified",
        "path": "lib/m.py"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "CONTINUE_WITH"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "I1",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [
      {
        "entry": "I1",
        "kind": "interface",
        "reason": "the signature is equal at base_commit and HEAD",
        "verdict": "non_breaking"
      }
    ],
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "lib/m.py"
          }
        ],
        "submitted": false
      }
    ],
    "components": [
      {
        "id": "C1",
        "paths": [
          "lib"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "depends_on": [
          "TASK-099"
        ],
        "intent_versions": {
          "SPEC-003": "v4"
        }
      },
      "read_set": {
        "interfaces": [
          "I1"
        ],
        "paths": [],
        "schemas": []
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_current": {
      "SPEC-003": "v4"
    },
    "interfaces": [
      {
        "component": "C1",
        "id": "I1"
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
        "base": null,
        "head": "s",
        "interface": "I1"
      }
    ],
    "task_id": "TASK-100",
    "task_state": "READY"
  },
  "name": "row 35: the symbol is in no file at one commit",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "1 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "a met entry is breaking: I1",
        "outcome": "REPLAN",
        "status": "fired"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "REPLAN",
    "delta": [
      {
        "change": "modified",
        "path": "lib/m.py"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "REPLAN"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "I1",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [
      {
        "entry": "I1",
        "kind": "interface",
        "reason": "the symbol is in no file at one commit",
        "verdict": "breaking"
      }
    ],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0",
        "payload": {
          "interfaces": [
            "I1"
          ],
          "paths": [],
          "tasks": []
        },
        "task_id": "TASK-100",
        "type": "conflict.detected"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller",
      "conflict.detected tasks: the commits' trailers are not an input"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "lib/m.py"
          }
        ],
        "submitted": false
      }
    ],
    "components": [
      {
        "id": "C1",
        "paths": [
          "lib"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "depends_on": [
          "TASK-099"
        ],
        "intent_versions": {
          "SPEC-003": "v4"
        }
      },
      "read_set": {
        "interfaces": [
          "I1"
        ],
        "paths": [],
        "schemas": []
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_current": {
      "SPEC-003": "v4"
    },
    "interfaces": [
      {
        "component": "C1",
        "id": "I1"
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
        "base": "s",
        "head": "ambiguous",
        "interface": "I1"
      }
    ],
    "task_id": "TASK-100",
    "task_state": "READY"
  },
  "name": "row 35: the symbol is ambiguous",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "1 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "a met entry is breaking: I1",
        "outcome": "REPLAN",
        "status": "fired"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "REPLAN",
    "delta": [
      {
        "change": "modified",
        "path": "lib/m.py"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "REPLAN"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "I1",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [
      {
        "entry": "I1",
        "kind": "interface",
        "reason": "the symbol is defined more than once at one commit",
        "verdict": "breaking"
      }
    ],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0",
        "payload": {
          "interfaces": [
            "I1"
          ],
          "paths": [],
          "tasks": []
        },
        "task_id": "TASK-100",
        "type": "conflict.detected"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller",
      "conflict.detected tasks: the commits' trailers are not an input"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "lib/m.py"
          }
        ],
        "submitted": false
      }
    ],
    "components": [
      {
        "id": "C1",
        "paths": [
          "lib"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "depends_on": [
          "TASK-099"
        ],
        "intent_versions": {
          "SPEC-003": "v4"
        }
      },
      "read_set": {
        "interfaces": [
          "I1"
        ],
        "paths": [],
        "schemas": []
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_current": {
      "SPEC-003": "v4"
    },
    "interfaces": [
      {
        "component": "C1",
        "id": "I1"
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
    "symbols": [],
    "task_id": "TASK-100",
    "task_state": "READY"
  },
  "name": "row 35: no single symbol entry",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "1 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "a met entry is breaking: I1",
        "outcome": "REPLAN",
        "status": "fired"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "REPLAN",
    "delta": [
      {
        "change": "modified",
        "path": "lib/m.py"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "REPLAN"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "I1",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [
      {
        "entry": "I1",
        "kind": "interface",
        "reason": "no single symbol entry for the interface (fail closed)",
        "verdict": "breaking"
      }
    ],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0",
        "payload": {
          "interfaces": [
            "I1"
          ],
          "paths": [],
          "tasks": []
        },
        "task_id": "TASK-100",
        "type": "conflict.detected"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller",
      "conflict.detected tasks: the commits' trailers are not an input"
    ]
  }
}
`,
	`{
  "code_sha256": null,
  "inputs": {
    "approved_contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "articles": [
      {
        "applicability": null,
        "id": "ART-1",
        "scope": {
          "components": [],
          "paths": [
            "zz/**"
          ]
        },
        "violated": null
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "x/a.txt"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "depends_on": [
          "TASK-099"
        ],
        "intent_versions": {
          "SPEC-003": "v4"
        }
      },
      "read_set": {
        "interfaces": [
          "I9"
        ],
        "paths": [],
        "schemas": []
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
  "name": "rows 35, 40: an unresolved interface (\"**\")",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "1 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "a met entry is breaking: I9",
        "outcome": "REPLAN",
        "status": "fired"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "ART-1",
        "INV-001"
      ],
      "no_result": [
        "ART-1",
        "INV-001"
      ],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "REPLAN",
    "delta": [
      {
        "change": "modified",
        "path": "x/a.txt"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "REPLAN"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "I9",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": [
        "I9"
      ]
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [
      {
        "entry": "I9",
        "kind": "interface",
        "reason": "the interface or its component cannot be resolved (fail closed)",
        "verdict": "breaking"
      }
    ],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0",
        "payload": {
          "interfaces": [
            "I9"
          ],
          "paths": [],
          "tasks": []
        },
        "task_id": "TASK-100",
        "type": "conflict.detected"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "article ART-1: no check result at HEAD",
      "article INV-001: no check result at HEAD",
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller",
      "conflict.detected tasks: the commits' trailers are not an input"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "lib/m.py"
          }
        ],
        "submitted": false
      }
    ],
    "components": [
      {
        "id": "C1",
        "paths": [
          "lib"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "depends_on": [
          "TASK-099"
        ],
        "intent_versions": {
          "SPEC-003": "v4"
        }
      },
      "read_set": {
        "interfaces": [
          "I1"
        ],
        "paths": [],
        "schemas": []
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_current": {
      "SPEC-003": "v4"
    },
    "interfaces": [
      {
        "component": "C1",
        "id": "I1"
      },
      {
        "component": "C1",
        "id": "I1"
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
        "base": "s",
        "head": "s",
        "interface": "I1"
      }
    ],
    "task_id": "TASK-100",
    "task_state": "READY"
  },
  "name": "row 36: an interface defined twice",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "1 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "a met entry is breaking: I1",
        "outcome": "REPLAN",
        "status": "fired"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "REPLAN",
    "delta": [
      {
        "change": "modified",
        "path": "lib/m.py"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "REPLAN"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "I1",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": [
        "I1"
      ]
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [
      {
        "entry": "I1",
        "kind": "interface",
        "reason": "the interface or its component cannot be resolved (fail closed)",
        "verdict": "breaking"
      }
    ],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0",
        "payload": {
          "interfaces": [
            "I1"
          ],
          "paths": [],
          "tasks": []
        },
        "task_id": "TASK-100",
        "type": "conflict.detected"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller",
      "conflict.detected tasks: the commits' trailers are not an input"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "lib/m.py"
          }
        ],
        "submitted": false
      }
    ],
    "components": [
      {
        "id": "C1",
        "paths": [
          "lib"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "depends_on": [
          "TASK-099"
        ],
        "intent_versions": {
          "SPEC-003": "v4"
        }
      },
      "read_set": {
        "interfaces": [
          "I1"
        ],
        "paths": [],
        "schemas": []
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_current": {
      "SPEC-003": "v4"
    },
    "interfaces": [
      {
        "component": "C9",
        "id": "I1"
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
        "base": "s",
        "head": "s",
        "interface": "I1"
      }
    ],
    "task_id": "TASK-100",
    "task_state": "READY"
  },
  "name": "row 37: an unknown component",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "1 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "a met entry is breaking: I1",
        "outcome": "REPLAN",
        "status": "fired"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "REPLAN",
    "delta": [
      {
        "change": "modified",
        "path": "lib/m.py"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "REPLAN"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "I1",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": [
        "I1"
      ]
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [
      {
        "entry": "I1",
        "kind": "interface",
        "reason": "the interface or its component cannot be resolved (fail closed)",
        "verdict": "breaking"
      }
    ],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0",
        "payload": {
          "interfaces": [
            "I1"
          ],
          "paths": [],
          "tasks": []
        },
        "task_id": "TASK-100",
        "type": "conflict.detected"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller",
      "conflict.detected tasks: the commits' trailers are not an input"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "lib/m.py"
          }
        ],
        "submitted": false
      }
    ],
    "components": [
      {
        "id": "C1",
        "paths": [
          "lib"
        ],
        "tags": []
      },
      {
        "id": "C1",
        "paths": [
          "lib"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "depends_on": [
          "TASK-099"
        ],
        "intent_versions": {
          "SPEC-003": "v4"
        }
      },
      "read_set": {
        "interfaces": [
          "I1"
        ],
        "paths": [],
        "schemas": []
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_current": {
      "SPEC-003": "v4"
    },
    "interfaces": [
      {
        "component": "C1",
        "id": "I1"
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
        "base": "s",
        "head": "s",
        "interface": "I1"
      }
    ],
    "task_id": "TASK-100",
    "task_state": "READY"
  },
  "name": "row 37: a component defined twice",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "1 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "a met entry is breaking: I1",
        "outcome": "REPLAN",
        "status": "fired"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "REPLAN",
    "delta": [
      {
        "change": "modified",
        "path": "lib/m.py"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "REPLAN"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "I1",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": [
        "I1"
      ]
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [
      {
        "entry": "I1",
        "kind": "interface",
        "reason": "the interface or its component cannot be resolved (fail closed)",
        "verdict": "breaking"
      }
    ],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0",
        "payload": {
          "interfaces": [
            "I1"
          ],
          "paths": [],
          "tasks": []
        },
        "task_id": "TASK-100",
        "type": "conflict.detected"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller",
      "conflict.detected tasks: the commits' trailers are not an input"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "sch/s.json"
          },
          {
            "change": "added",
            "path": "docs/a.md"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "depends_on": [
          "TASK-099"
        ],
        "intent_versions": {
          "SPEC-003": "v4"
        }
      },
      "read_set": {
        "interfaces": [],
        "paths": [],
        "schemas": [
          "S1"
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
          "path": "sch/s.json",
          "sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        },
        "head": {
          "path": "sch/s.json",
          "sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        },
        "name": "S1"
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
  "name": "rows 35, 39: a schema met, the same file",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "2 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "every met entry is non-breaking",
        "outcome": "CONTINUE_WITH",
        "status": "fired"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "CONTINUE_WITH",
    "delta": [
      {
        "change": "added",
        "path": "docs/a.md"
      },
      {
        "change": "modified",
        "path": "sch/s.json"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "CONTINUE_WITH"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "S1",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [
      {
        "entry": "S1",
        "kind": "schema",
        "reason": "the schema file is the same path with the same content hash",
        "verdict": "non_breaking"
      }
    ],
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "sch/s.json"
          },
          {
            "change": "added",
            "path": "docs/a.md"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "depends_on": [
          "TASK-099"
        ],
        "intent_versions": {
          "SPEC-003": "v4"
        }
      },
      "read_set": {
        "interfaces": [],
        "paths": [
          "docs/**"
        ],
        "schemas": [
          "S1"
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
          "path": "sch/s.json",
          "sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        },
        "head": {
          "path": "sch/s.json",
          "sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        },
        "name": "S1"
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
    "task_state": "REWORK"
  },
  "name": "rows 35, 39, 50, 52: a schema breaking, a path entry met, REWORK (task.stale)",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "2 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "a met entry is breaking: S1",
        "outcome": "REPLAN",
        "status": "fired"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "REPLAN",
    "delta": [
      {
        "change": "added",
        "path": "docs/a.md"
      },
      {
        "change": "modified",
        "path": "sch/s.json"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "REPLAN"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "docs/**",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "S1",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [
      {
        "entry": "docs/**",
        "kind": "path",
        "reason": "a path entry has no signature; its change is non-breaking",
        "verdict": "non_breaking"
      },
      {
        "entry": "S1",
        "kind": "schema",
        "reason": "the schema file or its content hash differs",
        "verdict": "breaking"
      }
    ],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0",
        "payload": {
          "interfaces": [],
          "paths": [
            "docs/a.md",
            "sch/s.json"
          ],
          "tasks": []
        },
        "task_id": "TASK-100",
        "type": "conflict.detected"
      },
      {
        "event_id": "b4e79e8f68a2287dbd080b2959425ceb9c7c928f4f8f7869d9dc3724aaf6dc31",
        "payload": {
          "cause": "conflict",
          "refers_to": "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0"
        },
        "task_id": "TASK-100",
        "type": "task.stale"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller",
      "conflict.detected tasks: the commits' trailers are not an input"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "sch/s.json"
          },
          {
            "change": "added",
            "path": "docs/a.md"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "depends_on": [
          "TASK-099"
        ],
        "intent_versions": {
          "SPEC-003": "v4"
        }
      },
      "read_set": {
        "interfaces": [],
        "paths": [],
        "schemas": [
          "S1"
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
          "path": "sch/s.json",
          "sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        },
        "head": "ambiguous",
        "name": "S1"
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
  "name": "row 39: a schema with an ambiguous side",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "2 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "a met entry is breaking: S1",
        "outcome": "REPLAN",
        "status": "fired"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "REPLAN",
    "delta": [
      {
        "change": "added",
        "path": "docs/a.md"
      },
      {
        "change": "modified",
        "path": "sch/s.json"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "REPLAN"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "S1",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": [
        "S1"
      ]
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [
      {
        "entry": "S1",
        "kind": "schema",
        "reason": "the schema resolves to no file or to more than one at one commit (fail closed)",
        "verdict": "breaking"
      }
    ],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0",
        "payload": {
          "interfaces": [],
          "paths": [
            "docs/a.md",
            "sch/s.json"
          ],
          "tasks": []
        },
        "task_id": "TASK-100",
        "type": "conflict.detected"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller",
      "conflict.detected tasks: the commits' trailers are not an input"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "sch/s.json"
          },
          {
            "change": "added",
            "path": "docs/a.md"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "depends_on": [
          "TASK-099"
        ],
        "intent_versions": {
          "SPEC-003": "v4"
        }
      },
      "read_set": {
        "interfaces": [],
        "paths": [],
        "schemas": [
          "S1"
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
          "path": "sch/s.json",
          "sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        },
        "head": {
          "path": "sch/s.json",
          "sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        },
        "name": "S9"
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
  "name": "row 39: a schema not found",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "2 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "a met entry is breaking: S1",
        "outcome": "REPLAN",
        "status": "fired"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "REPLAN",
    "delta": [
      {
        "change": "added",
        "path": "docs/a.md"
      },
      {
        "change": "modified",
        "path": "sch/s.json"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "REPLAN"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "S1",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": [
        "S1"
      ]
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [
      {
        "entry": "S1",
        "kind": "schema",
        "reason": "the schema resolves to no file or to more than one at one commit (fail closed)",
        "verdict": "breaking"
      }
    ],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0",
        "payload": {
          "interfaces": [],
          "paths": [
            "docs/a.md",
            "sch/s.json"
          ],
          "tasks": []
        },
        "task_id": "TASK-100",
        "type": "conflict.detected"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller",
      "conflict.detected tasks: the commits' trailers are not an input"
    ]
  }
}
`,
	`{
  "code_sha256": null,
  "inputs": {
    "approved_contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "articles": [
      {
        "applicability": {
          "task_types": [
            "no-such-type"
          ]
        },
        "id": "ART-1",
        "scope": null,
        "violated": true
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "row 41: task_types filter, not listed",
  "record": {
    "base_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit equals HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 3,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [
        "INV-001"
      ],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "CONTINUE",
    "delta": [],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "article INV-001: no check result at HEAD",
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
  "inputs": {
    "approved_contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "articles": [
      {
        "applicability": null,
        "id": "ART-1",
        "scope": null,
        "violated": true
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "row 42: scope null, not listed",
  "record": {
    "base_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit equals HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 3,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [
        "INV-001"
      ],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "CONTINUE",
    "delta": [],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "article INV-001: no check result at HEAD",
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
  "inputs": {
    "approved_contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "articles": [
      {
        "applicability": null,
        "id": "ART-1",
        "scope": "x",
        "violated": true
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "row 42: scope not an object",
  "record": {
    "base_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit equals HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 3,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "an applicable article is violated at HEAD: ART-1",
        "outcome": "ESCALATE",
        "status": "fired"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "ART-1",
        "INV-001"
      ],
      "no_result": [
        "INV-001"
      ],
      "violated": [
        "ART-1"
      ]
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "ESCALATE",
    "delta": [],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "ESCALATE"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "02a0fde469e5322baedd4d7c4ddcda136c6e4347c023adbf6f3644ebbbe42027",
        "payload": {
          "blocked_by": [
            "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c"
          ],
          "reason": "escalate"
        },
        "task_id": "TASK-100",
        "type": "task.blocked"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "article INV-001: no check result at HEAD",
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
  "inputs": {
    "approved_contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "articles": [
      {
        "applicability": null,
        "id": "ART-1",
        "scope": {
          "components": [
            "C9"
          ],
          "paths": []
        },
        "violated": null
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "row 42: scope naming an unknown component",
  "record": {
    "base_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit equals HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 3,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "ART-1",
        "INV-001"
      ],
      "no_result": [
        "ART-1",
        "INV-001"
      ],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "CONTINUE",
    "delta": [],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "article ART-1: no check result at HEAD",
      "article INV-001: no check result at HEAD",
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
  "inputs": {
    "approved_contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "articles": [
      {
        "applicability": null,
        "id": "ART-1",
        "scope": {
          "components": [
            "C1"
          ],
          "paths": [
            "**"
          ]
        },
        "violated": true
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
    "commits": [],
    "components": [
      {
        "id": "C1",
        "paths": [
          "lib"
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "row 42: scope paths meet the task patterns",
  "record": {
    "base_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit equals HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 3,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "an applicable article is violated at HEAD: ART-1",
        "outcome": "ESCALATE",
        "status": "fired"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "ART-1",
        "INV-001"
      ],
      "no_result": [
        "INV-001"
      ],
      "violated": [
        "ART-1"
      ]
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "ESCALATE",
    "delta": [],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "ESCALATE"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "02a0fde469e5322baedd4d7c4ddcda136c6e4347c023adbf6f3644ebbbe42027",
        "payload": {
          "blocked_by": [
            "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c"
          ],
          "reason": "escalate"
        },
        "task_id": "TASK-100",
        "type": "task.blocked"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "article INV-001: no check result at HEAD",
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
  "inputs": {
    "approved_contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "articles": [
      {
        "applicability": null,
        "id": "ART-1",
        "scope": {
          "components": [],
          "paths": [
            "zz/q.txt"
          ]
        },
        "violated": true
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "row 42: scope paths meet no task pattern",
  "record": {
    "base_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit equals HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 3,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [
        "INV-001"
      ],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "CONTINUE",
    "delta": [],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "article INV-001: no check result at HEAD",
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "used": "1m"
      },
      "retries": {
        "reported": true,
        "used": 1
      },
      "tokens": {
        "reported": true,
        "used": "1500k"
      },
      "wall_time": {
        "reported": true,
        "used": "90000s"
      }
    },
    "commits": [],
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
          "human_attention": "30s",
          "retries": 3,
          "tokens": "2m",
          "wall_time": "1d"
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "rows 47, 48: units s, m, d and tokens m",
  "record": {
    "base_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "budgets": {
      "human_attention": {
        "limit": "30s",
        "reported": true,
        "used": "1m"
      },
      "retries": {
        "limit": 3,
        "reported": true,
        "used": 1
      },
      "tokens": {
        "limit": "2m",
        "reported": true,
        "used": "1500k"
      },
      "wall_time": {
        "limit": "1d",
        "reported": true,
        "used": "90000s"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit equals HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 3,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "a budget is used up: human_attention, wall_time",
        "outcome": "ESCALATE",
        "status": "fired"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "ESCALATE",
    "delta": [],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "ESCALATE"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "02a0fde469e5322baedd4d7c4ddcda136c6e4347c023adbf6f3644ebbbe42027",
        "payload": {
          "blocked_by": [
            "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c"
          ],
          "reason": "escalate"
        },
        "task_id": "TASK-100",
        "type": "task.blocked"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
      "disk": {
        "reported": true,
        "used": "1"
      },
      "tokens": {
        "reported": true,
        "used": "1k"
      },
      "wall_time": {
        "reported": true,
        "used": "1h"
      }
    },
    "commits": [],
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
          "disk": "5",
          "tokens": "12q",
          "wall_time": "h"
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "row 45: forms that cannot be parsed",
  "record": {
    "base_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "budgets": {
      "disk": {
        "limit": "5",
        "reported": true,
        "used": "1"
      },
      "tokens": {
        "limit": "12q",
        "reported": true,
        "used": "1k"
      },
      "wall_time": {
        "limit": "h",
        "reported": true,
        "used": "1h"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit equals HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 3,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "CONTINUE",
    "delta": [],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "budget disk: a form that cannot be parsed",
      "budget tokens: a form that cannot be parsed",
      "budget wall_time: a form that cannot be parsed",
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
      "tokens": {
        "reported": true,
        "used": "9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999"
      }
    },
    "commits": [],
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
          "tokens": "1k"
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "row 45: a budget amount of the largest accepted digit count",
  "record": {
    "base_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "budgets": {
      "tokens": {
        "limit": "1k",
        "reported": true,
        "used": "9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit equals HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 3,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "a budget is used up: tokens",
        "outcome": "ESCALATE",
        "status": "fired"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "ESCALATE",
    "delta": [],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "ESCALATE"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "src/app/util/helpers.py",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "load_policy",
          "kind": "interface",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "record",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "02a0fde469e5322baedd4d7c4ddcda136c6e4347c023adbf6f3644ebbbe42027",
        "payload": {
          "blocked_by": [
            "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c"
          ],
          "reason": "escalate"
        },
        "task_id": "TASK-100",
        "type": "task.blocked"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
      "tokens": {
        "reported": true,
        "used": "99999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999"
      }
    },
    "commits": [],
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
          "tokens": "1k"
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "row 45: a budget amount of the smallest refused digit count",
  "record": {
    "decision": null,
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "error": "the check could not complete: ValueError",
    "fact_kind": "interpretation",
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
      "tokens": {
        "reported": true,
        "used": "00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
      }
    },
    "commits": [],
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
          "tokens": "1k"
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "row 45: a budget amount of leading zeros, refused",
  "record": {
    "decision": null,
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "error": "the check could not complete: ValueError",
    "fact_kind": "interpretation",
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
    "commits": [],
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_current": {
      "SPEC-003": "v4"
    },
    "interfaces": [
      {
        "component": "CMP-API",
        "id": "load_policy"
      }
    ],
    "log_seq": true,
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
  "name": "row 5: log_seq a bool",
  "record": {
    "decision": null,
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "error": "an input is missing or malformed: log_seq is not an integer from 0 to 2**63 - 1",
    "fact_kind": "interpretation",
    "record_id": "1d142c87a4c933920e789156359f70e4ea8e28c10b85470e99af7b40521eeaeb",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "sch/s.json"
          },
          {
            "change": "added",
            "path": "docs/a.md"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "depends_on": [
          "TASK-099"
        ],
        "intent_versions": {
          "SPEC-003": "v4"
        }
      },
      "read_set": {
        "interfaces": [],
        "paths": [
          "docs/**"
        ],
        "schemas": [
          "S1"
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
          "path": "sch/s.json",
          "sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        },
        "head": {
          "path": "sch/s.json",
          "sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        },
        "name": "S1"
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
    "task_state": "IN_PROGRESS"
  },
  "name": "row 17: IN_PROGRESS, a schema breaking (task.stale)",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "2 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "a met entry is breaking: S1",
        "outcome": "REPLAN",
        "status": "fired"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "REPLAN",
    "delta": [
      {
        "change": "added",
        "path": "docs/a.md"
      },
      {
        "change": "modified",
        "path": "sch/s.json"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "REPLAN"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "docs/**",
          "kind": "path",
          "sources": [
            "declared"
          ]
        },
        {
          "entry": "S1",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [
      {
        "entry": "docs/**",
        "kind": "path",
        "reason": "a path entry has no signature; its change is non-breaking",
        "verdict": "non_breaking"
      },
      {
        "entry": "S1",
        "kind": "schema",
        "reason": "the schema file or its content hash differs",
        "verdict": "breaking"
      }
    ],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0",
        "payload": {
          "interfaces": [],
          "paths": [
            "docs/a.md",
            "sch/s.json"
          ],
          "tasks": []
        },
        "task_id": "TASK-100",
        "type": "conflict.detected"
      },
      {
        "event_id": "b4e79e8f68a2287dbd080b2959425ceb9c7c928f4f8f7869d9dc3724aaf6dc31",
        "payload": {
          "cause": "conflict",
          "refers_to": "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0"
        },
        "task_id": "TASK-100",
        "type": "task.stale"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller",
      "conflict.detected tasks: the commits' trailers are not an input"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
    "commits": [],
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
      "contract_version": "version-1",
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
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
  "name": "row 23: a contract_version not v<digits>",
  "record": {
    "decision": null,
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "error": "an input is missing or malformed: contract contract_version is not v<digits>",
    "fact_kind": "interpretation",
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
        "id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "paths": [
          {
            "change": "modified",
            "path": "sch/s.json"
          },
          {
            "change": "added",
            "path": "docs/a.md"
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
        "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "depends_on": [
          "TASK-099"
        ],
        "intent_versions": {
          "SPEC-003": "v4"
        }
      },
      "read_set": {
        "interfaces": [],
        "paths": [],
        "schemas": [
          "S1"
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
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
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
        "base": null,
        "head": {
          "path": "sch/s.json",
          "sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        },
        "name": "S1"
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
  "name": "row 25: a schema with a null side",
  "record": {
    "base_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "2 paths changed since base_commit",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "delta does not meet the write-set",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 3,
        "detail": "a met entry is breaking: S1",
        "outcome": "REPLAN",
        "status": "fired"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "REPLAN",
    "delta": [
      {
        "change": "added",
        "path": "docs/a.md"
      },
      {
        "change": "modified",
        "path": "sch/s.json"
      }
    ],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [
      "REPLAN"
    ],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "S1",
          "kind": "schema",
          "sources": [
            "declared"
          ]
        }
      ],
      "estimate": true,
      "unanalysed": [],
      "unresolved": [
        "S1"
      ]
    },
    "record_id": "1bb7f34070564e48ee32e053bbe49cafad9cba75c63b83b3b823aa47aaea729e",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [
      {
        "entry": "S1",
        "kind": "schema",
        "reason": "the schema resolves to no file or to more than one at one commit (fail closed)",
        "verdict": "breaking"
      }
    ],
    "source_class": "deterministic_tool_local",
    "state_effect": [
      {
        "event_id": "6d9870c1bb8dbb114ccc361850fb6c62891ef55283f027cb2fc4ab1ae038f1f0",
        "payload": {
          "interfaces": [],
          "paths": [
            "docs/a.md",
            "sch/s.json"
          ],
          "tasks": []
        },
        "task_id": "TASK-100",
        "type": "conflict.detected"
      }
    ],
    "subject": "TASK-100",
    "uncovered": [
      "read-set: no observed source, the effective read-set is an estimate",
      "engine_identity.code_sha256: not given by the caller",
      "conflict.detected tasks: the commits' trailers are not an input"
    ]
  }
}
`,
	`{
  "code_sha256": null,
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
    "commits": [],
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
        "interfaces": [],
        "paths": [
          "lib/x.py"
        ],
        "schemas": []
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
    "derived_read_set": [
      "lib/x.py"
    ],
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
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
    "observed_read_set": [
      "lib/x.py",
      "docs/y.md"
    ],
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
  "name": "row 29: declared, derived and observed read-set sources",
  "record": {
    "base_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "budgets": {
      "human_attention": {
        "limit": "10m",
        "reported": true,
        "used": "0m"
      },
      "retries": {
        "limit": 2,
        "reported": true,
        "used": 0
      },
      "tokens": {
        "limit": "400k",
        "reported": true,
        "used": "10k"
      },
      "wall_time": {
        "limit": "2h",
        "reported": true,
        "used": "10m"
      }
    },
    "checks": [
      {
        "check": 1,
        "detail": "base_commit equals HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 2,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 3,
        "detail": "HEAD equals base_commit",
        "outcome": null,
        "status": "skipped"
      },
      {
        "check": 4,
        "detail": "every intent version is current",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 5,
        "detail": "every dependency is DONE",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 6,
        "detail": "no applicable article is violated at HEAD",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 7,
        "detail": "max_risk high covers the task risk medium",
        "outcome": null,
        "status": "passed"
      },
      {
        "check": 8,
        "detail": "every reported budget use is within its limit",
        "outcome": null,
        "status": "passed"
      }
    ],
    "constitution": {
      "applicable": [
        "INV-001"
      ],
      "no_result": [],
      "violated": []
    },
    "contract_hash": "4db988fbcd6707723931f83b044b3ff906ad2c82851ce086090daca5df0f10ce",
    "contract_version": "v1",
    "decision": "CONTINUE",
    "delta": [],
    "dependencies": {
      "TASK-099": "DONE"
    },
    "engine_identity": {
      "code_sha256": null,
      "python": "3.14.0"
    },
    "fact_kind": "interpretation",
    "head_commit": "43ce150f6b4a83acc25b946af3b3f720473ccc93",
    "intent_versions": {
      "SPEC-003": {
        "contract": "v4",
        "current": "v4"
      }
    },
    "log_seq": 7,
    "outcomes_fired": [],
    "policy_version": "v2",
    "read_set": {
      "entries": [
        {
          "entry": "docs/y.md",
          "kind": "path",
          "sources": [
            "observed"
          ]
        },
        {
          "entry": "lib/x.py",
          "kind": "path",
          "sources": [
            "declared",
            "derived",
            "observed"
          ]
        }
      ],
      "estimate": false,
      "unanalysed": [],
      "unresolved": []
    },
    "record_id": "eafdbd5219772b76fa1372a5cb57ba0215d870f3c213e79fd5d22107ca51589c",
    "recorder": "the Resume Check (aieos_bootstrap.resume_check)",
    "runtime": {
      "adapter": "placeholder-adapter",
      "max_risk": "high",
      "task_risk": "medium"
    },
    "signatures": [],
    "source_class": "deterministic_tool_local",
    "state_effect": [],
    "subject": "TASK-100",
    "uncovered": [
      "engine_identity.code_sha256: not given by the caller"
    ]
  }
}
`,
}
