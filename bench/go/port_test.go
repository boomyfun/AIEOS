package main

// The port's own tests, run as `go test -count=1 . -args <fixture document> <reference document>`. They read only
// the two documents named by those arguments; the reference document is read here only, as the expected output.

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
	folder, _, _ := strings.Cut(key, "/")
	recs, err := caseRecords(folder, fixture.Val("cases").([]any)[:1])
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

func TestGovernorCaseFieldByField(t *testing.T) {
	got := fieldByField(t, "fixtures/acc_01")
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
	if got["decision"] == nil || got["table_row"] == nil {
		t.Errorf("no decision value: %v", got["error"])
	}
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
		for _, r := range v.(*Obj).Val(key).([]any) {
			rec := r.(*Obj)
			ei, has := rec.Get("engine_identity")
			if strings.HasPrefix(key, rcFolder+"/") {
				rcRecords++
				if !has || ei.(*Obj).Val("python") != enginePlaceholder {
					t.Errorf("%s: engine_identity.python is not the placeholder", key)
				}
			} else if has {
				t.Errorf("%s: a governor record has engine_identity", key)
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
	rec := placeholder(rcFolder, map[string]any{"engine_identity": map[string]any{"code_sha256": nil, "python": "x"}})
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
		{"no Resume Check fixture", []string{name}, doc(func(r *Obj) {
			for _, k := range append([]string(nil), r.Keys()...) {
				if strings.HasPrefix(k, rcFolder+"/") {
					r.Del(k)
				}
			}
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
		{"cases not a list", []string{name}, doc(func(r *Obj) { r.Val("fixtures_rc/rc_01").(*Obj).Set("cases", newObj()) })},
		{"a case that is not an object", []string{name}, doc(func(r *Obj) {
			r.Val("fixtures/acc_01").(*Obj).Set("cases", []any{"x"})
		})},
		{"a governor case without request", []string{name}, doc(func(r *Obj) { firstCase(r, "fixtures/acc_01").Del("request") })},
		{"a governor case without records", []string{name}, doc(func(r *Obj) { firstCase(r, "fixtures/acc_01").Del("records") })},
		{"a Resume Check case without inputs", []string{name}, doc(func(r *Obj) { firstCase(r, "fixtures_rc/rc_01").Del("inputs") })},
		// Cases that cannot be computed.
		{"a governor request without a task id (evaluate raises)", []string{name}, doc(func(r *Obj) {
			firstCase(r, "fixtures/acc_01").Val("request").(*Obj).Set("task_id", "task-1")
		})},
		{"a governor request that is not an object (evaluate raises)", []string{name}, doc(func(r *Obj) {
			firstCase(r, "fixtures/acc_01").Set("request", []any{})
		})},
		{"a budget amount Python's int() refuses (the check could not complete)", []string{name}, doc(func(r *Obj) {
			bu := firstCase(r, "fixtures_rc/rc_01").Val("inputs").(*Obj).Val("budget_use").(*Obj)
			bu.Val("tokens").(*Obj).Set("used", strings.Repeat("9", 4301)+"k")
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

// The two unexpected-error paths of resume_check.check fail closed: a panic while the inputs are read or while the
// check runs is a case that cannot be computed, never a record.
func TestUnexpectedErrorsFailClosed(t *testing.T) {
	if _, err := guarded(func() string { panic("x") }); !errors.Is(err, errCannotCompute) {
		t.Errorf("a panic while reading the inputs: %v", err)
	}
	fixtures, _ := documents(t)
	v, err := parseJSON(fixtures)
	if err != nil {
		t.Fatal(err)
	}
	inputs := firstCase(v.(*Obj), "fixtures_rc/rc_01").Val("inputs").(*Obj)
	inputs.Val("budget_use").(*Obj).Val("tokens").(*Obj).Set("used", strings.Repeat("1", 4301)+"k")
	rec, err := check(inputs, nil)
	if rec != nil || !errors.Is(err, errCannotCompute) {
		t.Errorf("the check did not fail closed: %v %v", rec, err)
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
