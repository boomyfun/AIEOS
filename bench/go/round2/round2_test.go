package main

// The round-2 program's own tests, run from bench/go as
// `go test -count=1 ./round2 -args <round-2 input document> <round-2 reference document>`. They read only the two
// documents named by those arguments; the reference document is read here only, as the expected output.

import (
	"bytes"
	"errors"
	"flag"
	"fmt"
	"os"
	"strings"
	"testing"
)

// round2Documents reads the two documents named after -args; a missing argument fails the test (it never skips).
func round2Documents(t *testing.T) (input, reference []byte) {
	t.Helper()
	args := flag.Args()
	if len(args) != 2 {
		t.Fatalf("run as: go test -count=1 ./round2 -args <round-2 input document> <round-2 reference document> "+
			"(got %d arguments)", len(args))
	}
	input, err := os.ReadFile(args[0])
	if err != nil {
		t.Fatalf("reading the input document: %v", err)
	}
	reference, err = os.ReadFile(args[1])
	if err != nil {
		t.Fatalf("reading the reference document: %v", err)
	}
	return input, reference
}

func lineDifference(a, b []byte) string {
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

// fileRead serves one document under one name only, so that run2 reads no path in the tests.
func fileRead(name string, data []byte) func(string) ([]byte, error) {
	return func(p string) ([]byte, error) {
		if p != name {
			return nil, errors.New("no such file: " + p)
		}
		return data, nil
	}
}

type writeCounter struct {
	buf    bytes.Buffer
	writes int
}

func (w *writeCounter) Write(p []byte) (int, error) {
	w.writes++
	return w.buf.Write(p)
}

func parsed(t *testing.T, data []byte) *Obj {
	t.Helper()
	v, err := parseJSON(data)
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	o, ok := v.(*Obj)
	if !ok {
		t.Fatalf("not an object")
	}
	return o
}

func listOf(t *testing.T, o *Obj, key string) []any {
	t.Helper()
	l, ok := o.Val(key).([]any)
	if !ok {
		t.Fatalf("%s is not a list", key)
	}
	return l
}

func textOf(t *testing.T, v any) string {
	t.Helper()
	s, err := canonString(v)
	if err != nil {
		t.Fatalf("canon: %v", err)
	}
	return s
}

// sameFields compares a computed entry with the reference's entry key by key, by their canonical texts.
func sameFields(t *testing.T, what string, got map[string]any, want *Obj, keys ...string) {
	t.Helper()
	if len(want.Keys()) != len(keys) || len(got) != len(keys) {
		t.Fatalf("%s: %d keys computed, %d in the reference, want %d", what, len(got), len(want.Keys()), len(keys))
	}
	for _, k := range keys {
		w, ok := want.Get(k)
		if !ok {
			t.Fatalf("%s: the reference lacks %s", what, k)
		}
		if g := textOf(t, got[k]); g != textOf(t, w) {
			t.Errorf("%s: %s is %s, want %s", what, k, g, textOf(t, w))
		}
	}
}

var appendFields = []string{"findings", "line", "reason", "record", "result", "seq"}

func TestWholeDocumentByteEqual(t *testing.T) {
	input, reference := round2Documents(t)
	got, err := buildRound2(input)
	if err != nil {
		t.Fatalf("buildRound2: %v", err)
	}
	if !bytes.Equal(got, reference) {
		t.Fatalf("the document differs from the reference (%d bytes, want %d): %s", len(got), len(reference),
			lineDifference(got, reference))
	}
}

func TestRunWritesTheDocumentOnce(t *testing.T) {
	input, reference := round2Documents(t)
	var out, errOut writeCounter
	if code := run2([]string{"input.json"}, fileRead("input.json", input), &out, &errOut); code != 0 {
		t.Fatalf("exit %d, stderr %q", code, errOut.buf.String())
	}
	if out.writes != 1 || !bytes.Equal(out.buf.Bytes(), reference) {
		t.Fatalf("%d writes; byte-equal %v", out.writes, bytes.Equal(out.buf.Bytes(), reference))
	}
	if errOut.buf.Len() != 0 {
		t.Fatalf("stderr %q", errOut.buf.String())
	}
}

// TestAppendCallFieldByField computes the first append call (an empty log) and the sixth (a fence refusal with its
// record, over the log the first five leave) and compares each with the reference field by field.
func TestAppendCallFieldByField(t *testing.T) {
	input, reference := round2Documents(t)
	calls := listOf(t, parsed(t, input), "append")
	want := listOf(t, parsed(t, reference), "append")
	log := []byte{}
	for i := 0; i <= 5; i++ {
		var entry map[string]any
		entry, log = appendEntry(log, calls[i].(*Obj))
		if i == 0 || i == 5 {
			sameFields(t, fmt.Sprintf("append %d", i), entry, want[i].(*Obj), appendFields...)
		}
	}
	if !strEq(want[0].(*Obj).Val("result"), "appended") {
		t.Fatalf("the reference's first entry is not an appended one")
	}
	if rec, ok := want[5].(*Obj).Val("record").(*Obj); !ok || !strEq(rec.Val("record_id"), "r000005") {
		t.Fatalf("the reference's sixth entry carries no refusal record")
	}
}

// TestReconcileCaseFieldByField computes the first reconcile case (a compensating submission under a lease that
// holds) and the fifth (an expired lease) and compares each with the reference field by field.
func TestReconcileCaseFieldByField(t *testing.T) {
	input, reference := round2Documents(t)
	cases := listOf(t, parsed(t, input), "reconcile")
	want := listOf(t, parsed(t, reference), "reconcile")
	for _, i := range []int{0, 4} {
		got := reconcileEntry(cases[i].(*Obj))
		sameFields(t, fmt.Sprintf("reconcile %d", i), got, want[i].(*Obj), "events", "expired", "findings", "log")
	}
	events := listOf(t, want[0].(*Obj), "events")
	if len(events) != 1 || !strEq(events[0].(*Obj).Val("type"), "task.submitted") ||
		!strEq(events[0].(*Obj).Val("result"), "appended") {
		t.Fatalf("the reference's first case is not one compensating submission")
	}
	if len(listOf(t, want[4].(*Obj), "expired")) != 1 {
		t.Fatalf("the reference's fifth case has not one expired lease")
	}
}

// TestCarriedLog checks the log carried from call to call: an appended result's log becomes the next call's log
// (the entry after an appended one has the next seq and its line follows the earlier lines), and a refused result
// leaves it (the entries after refused ones see the log unchanged).
func TestCarriedLog(t *testing.T) {
	input, reference := round2Documents(t)
	calls := listOf(t, parsed(t, input), "append")
	want := listOf(t, parsed(t, reference), "append")
	log := []byte{}
	lines := []byte{}
	lastSeq := 0
	sawAfterAppended, sawAfterRefused := false, false
	previous := ""
	for i, cv := range calls {
		before := append([]byte(nil), log...)
		var entry map[string]any
		entry, log = appendEntry(log, cv.(*Obj))
		sameFields(t, fmt.Sprintf("append %d", i), entry, want[i].(*Obj), appendFields...)
		switch entry["result"] {
		case "appended":
			seq := entry["seq"].(int)
			if seq != lastSeq+1 {
				t.Fatalf("append %d: seq %d after seq %d", i, seq, lastSeq)
			}
			lines = append(lines, []byte(entry["line"].(string))...)
			if !bytes.Equal(log, lines) || !bytes.HasPrefix(log, before) {
				t.Fatalf("append %d: the new log is not the earlier log followed by the line", i)
			}
			lastSeq = seq
			if previous == "appended" {
				sawAfterAppended = true
			}
			if previous == "refused" {
				sawAfterRefused = true
			}
		default:
			if !bytes.Equal(log, before) {
				t.Fatalf("append %d: a %s result changed the log", i, entry["result"])
			}
		}
		previous = entry["result"].(string)
	}
	if !sawAfterAppended || !sawAfterRefused {
		t.Fatalf("no appended entry after an appended one (%v) or after a refused one (%v)", sawAfterAppended,
			sawAfterRefused)
	}
	// Call 1 follows the appended call 0; call 6 follows the refused calls 3 to 5.
	for _, i := range []int{1, 6} {
		if !strEq(want[i].(*Obj).Val("result"), "appended") || !strEq(want[i-1].(*Obj).Val("result"),
			map[int]string{1: "appended", 6: "refused"}[i]) {
			t.Fatalf("the reference's entries %d and %d are not of the kinds this test names", i-1, i)
		}
	}
}

// mutated is the input document with one change, in its canonical text.
func mutated(t *testing.T, input []byte, f func(doc *Obj)) []byte {
	t.Helper()
	doc := parsed(t, input)
	f(doc)
	text, err := canonicalText(doc)
	if err != nil {
		t.Fatalf("canon: %v", err)
	}
	return text
}

func firstEntry(doc *Obj, key string) *Obj {
	return doc.Val(key).([]any)[0].(*Obj)
}

func TestFailClosed(t *testing.T) {
	input, _ := round2Documents(t)
	type probe struct {
		name string
		args []string
		data []byte
	}
	one := []string{"input.json"}
	probes := []probe{
		{"no argument", []string{}, input},
		{"an extra argument", []string{"input.json", "x"}, input},
		{"a missing file", []string{"other.json"}, input},
		{"empty", one, []byte("")},
		{"not JSON", one, []byte("not json")},
		{"a list", one, []byte("[]\n")},
		{"an empty object", one, []byte("{}\n")},
		{"an extra key", one, []byte("{\n  \"append\": [],\n  \"reconcile\": [],\n  \"x\": 1\n}\n")},
		{"a repeated key", one, []byte("{\"append\":[],\"append\":[],\"reconcile\":[]}\n")},
		{"not canonical", one, []byte("{\"append\": [], \"reconcile\": []}\n")},
		{"no final LF", one, input[:len(input)-1]},
		{"a non-ASCII byte", one, append([]byte("\xc3\xa9"), input...)},
		{"a call without its keys", one, mutated(t, input, func(d *Obj) {
			firstEntry(d, "append").Del("corrects")
		})},
		{"a case without its keys", one, mutated(t, input, func(d *Obj) {
			firstEntry(d, "reconcile").Del("recorder")
		})},
		{"append is not a list", one, mutated(t, input, func(d *Obj) { d.Set("append", newObj()) })},
		{"a time not of the form", one, mutated(t, input, func(d *Obj) {
			firstEntry(d, "append").Set("appended_at", "2026-01-01 00:00:00")
		})},
		{"a time that does not exist", one, mutated(t, input, func(d *Obj) {
			firstEntry(d, "append").Set("appended_at", "2026-02-30T00:00:00Z")
		})},
		{"a lease without expires_at", one, mutated(t, input, func(d *Obj) {
			firstEntry(d, "append").Set("lease", newObj())
		})},
		{"an event type that is a list (TypeError)", one, mutated(t, input, func(d *Obj) {
			firstEntry(d, "append").Set("event_type", []any{})
		})},
		{"commits not a list", one, mutated(t, input, func(d *Obj) {
			firstEntry(d, "reconcile").Set("commits", "none")
		})},
		{"a commit id of the wrong form", one, mutated(t, input, func(d *Obj) {
			c := newObj()
			c.Set("commit", "abc")
			c.Set("message", "m")
			firstEntry(d, "reconcile").Set("commits", []any{c})
		})},
		{"an empty recorder", one, mutated(t, input, func(d *Obj) {
			firstEntry(d, "reconcile").Set("recorder", "")
		})},
		{"a log that is not text", one, mutated(t, input, func(d *Obj) {
			firstEntry(d, "reconcile").Set("log", nil)
		})},
		{"a log line that is a JSON list (a Python type name)", one, mutated(t, input, func(d *Obj) {
			firstEntry(d, "reconcile").Set("log", "[1]\n")
		})},
		{"a log line that is not JSON (Python's own message)", one, mutated(t, input, func(d *Obj) {
			firstEntry(d, "reconcile").Set("log", "{\n")
		})},
		{"a lease that is not an object", one, mutated(t, input, func(d *Obj) {
			firstEntry(d, "reconcile").Set("leases", []any{"x"})
		})},
	}
	for _, p := range probes {
		var out, errOut writeCounter
		code := run2(p.args, fileRead("input.json", p.data), &out, &errOut)
		if code == 0 || out.buf.Len() != 0 || out.writes != 0 {
			t.Errorf("%s: exit %d, %d bytes on standard output", p.name, code, out.buf.Len())
		}
		if errOut.buf.Len() == 0 {
			t.Errorf("%s: nothing on standard error", p.name)
		}
	}
}

// TestComputedNotCopied changes one input value and sees the output follow it: the entries are computed from the
// input, not embedded.
func TestComputedNotCopied(t *testing.T) {
	input, reference := round2Documents(t)
	changed := mutated(t, input, func(d *Obj) {
		firstEntry(d, "append").Set("event_id", "e999999")
	})
	got, err := buildRound2(changed)
	if err != nil {
		t.Fatalf("buildRound2: %v", err)
	}
	if bytes.Equal(got, reference) || !bytes.Contains(got, []byte(`\"event_id\":\"e999999\"`)) {
		t.Fatalf("the output does not follow the input")
	}
}

// TestTextForms checks Python's text forms the findings use, on values the generated input does not hold.
func TestTextForms(t *testing.T) {
	o := newObj()
	o.Set("b", []any{true, nil})
	o.Set("a", "it's")
	for _, c := range []struct {
		v    any
		want string
	}{
		{"a'b", `"a'b"`},
		{"a'\"b", `'a\'"b'`},
		{"tab\there\x01\x7f", `'tab\there\x01\x7f'`},
		{o, `{'b': [True, None], 'a': "it's"}`},
	} {
		if got := pyRepr(c.v); got != c.want {
			t.Errorf("repr: got %s, want %s", got, c.want)
		}
	}
	if got := pyDumps(o); got != `{"a":"it's","b":[true,null]}` {
		t.Errorf("dumps: got %s", got)
	}
	bs := "\\"
	want := `"` + bs + "u00e9" + bs + "ud83d" + bs + "ude00" + bs + "u007f" + bs + `n"`
	if got := pyDumps("\xc3\xa9\xf0\x9f\x98\x80\x7f\n"); got != want {
		t.Errorf("dumps: got %q, want %q", got, want)
	}
	task, fence, bad := trailers("Work\n\nAIEOS-Task: TASK-7\n AIEOS-Fence: e:pq:12")
	if task != "TASK-7" || fence == nil || !strEq(fence.Val("epoch"), "e:pq") ||
		len(bad) != 1 || bad[0] != "trailer: 'AIEOS-Fence' is not at the start of its line" {
		t.Errorf("trailers: %q %v %q", task, fence, bad)
	}
}
