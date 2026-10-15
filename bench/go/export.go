package main

// The document: every case of the fixture document's governor and Resume Check fixtures, computed as the reference
// export computes it (test_export_reference.py's case_records and document), in the canonical text.

import (
	"errors"
	"fmt"
	"io"
	"strings"
)

const (
	governorFolder = "fixtures"
	rcFolder       = "fixtures_rc"
	riskFolder     = "fixtures_risk" // in the fixture document, but not ported in round 1 (brief section 2)
	usage          = "usage: <binary> <fixture document>"
)

var errNotFixtureDocument = errors.New("not a fixture document")

func notFixture(format string, a ...any) error {
	return fmt.Errorf("%w: %s", errNotFixtureDocument, fmt.Sprintf(format, a...))
}

// buildDocument computes the whole document from the fixture document's bytes, or returns an error: the input is not
// a fixture document, or a case cannot be computed. Nothing is written here.
func buildDocument(data []byte) (out []byte, err error) {
	defer func() {
		if r := recover(); r != nil {
			out, err = nil, fmt.Errorf("%w: an unexpected error: %v", errCannotCompute, r)
		}
	}()
	value, err := parseJSON(data)
	if err != nil {
		return nil, fmt.Errorf("%w: %v", errNotFixtureDocument, err)
	}
	// The fixture document is canonical text, as every fixture file it is made from (conformance.unwrap).
	text, err := canonicalText(value)
	if err != nil || string(text) != string(data) {
		return nil, notFixture("the text is not in the canonical form")
	}
	root, ok := value.(*Obj)
	if !ok {
		return nil, notFixture("the document is not one object")
	}
	doc := map[string]any{}
	count := map[string]int{}
	for _, key := range root.keys {
		folder, stem, ok := strings.Cut(key, "/")
		if !ok || stem == "" || strings.Contains(stem, "/") {
			return nil, notFixture("the key %q is not <folder>/<file stem>", key)
		}
		if folder != governorFolder && folder != rcFolder && folder != riskFolder {
			return nil, notFixture("the key %q names no fixture folder of the document", key)
		}
		fixture, ok := root.vals[key].(*Obj)
		if !ok {
			return nil, notFixture("%s is not an object", key)
		}
		cases, ok := fixture.Val("cases").([]any)
		if !ok || len(cases) == 0 {
			return nil, notFixture("%s: no cases", key)
		}
		count[folder]++
		if folder == riskFolder {
			continue
		}
		recs, err := caseRecords(folder, cases)
		if err != nil {
			return nil, fmt.Errorf("%s: %w", key, err)
		}
		doc[key] = recs
	}
	for _, folder := range []string{governorFolder, rcFolder} {
		if count[folder] == 0 {
			return nil, notFixture("no fixture of the folder %s", folder)
		}
	}
	out, err = canonicalText(doc)
	if err != nil {
		return nil, fmt.Errorf("%w: %v", errCannotCompute, err)
	}
	for _, b := range out {
		if b > 127 || b == '\r' {
			return nil, fmt.Errorf("%w: the document is not ASCII with LF line ends", errCannotCompute)
		}
	}
	return out, nil
}

// caseRecords is the reference's case_records: the record of each case, in case order, each argument read from the
// case as the conformance runner reads it.
func caseRecords(folder string, cases []any) ([]any, error) {
	out := []any{}
	for n, cv := range cases {
		c, ok := cv.(*Obj)
		if !ok {
			return nil, fmt.Errorf("%w: case %d is not an object", errNotFixtureDocument, n+1)
		}
		var rec map[string]any
		var err error
		if folder == governorFolder {
			for _, k := range []string{"request", "inputs", "records"} {
				if !c.Has(k) {
					return nil, fmt.Errorf("%w: case %d lacks %s", errNotFixtureDocument, n+1, k)
				}
			}
			rec, err = evaluate(c.Val("request"), c.Val("inputs"), c.Val("records"))
			if err != nil && !errors.Is(err, errCannotCompute) {
				err = fmt.Errorf("%w: %v", errCannotCompute, err)
			}
		} else {
			if !c.Has("inputs") {
				return nil, fmt.Errorf("%w: case %d lacks inputs", errNotFixtureDocument, n+1)
			}
			rec, err = check(c.Val("inputs"), nil)
		}
		if err != nil {
			return nil, fmt.Errorf("case %d: %w", n+1, err)
		}
		out = append(out, placeholder(folder, rec))
	}
	return out, nil
}

// placeholder is the reference's closed placeholder list: engine_identity.python of the Resume Check's records.
func placeholder(folder string, rec map[string]any) map[string]any {
	if folder != rcFolder {
		return rec
	}
	if ei, ok := rec["engine_identity"].(map[string]any); ok {
		if _, has := ei["python"]; has {
			ei["python"] = enginePlaceholder
		}
	}
	return rec
}

// run is the command line: one argument, the fixture document's path. It writes the whole document to out in one
// write and returns 0, or writes nothing to out and returns non-zero. read is the one file read (os.ReadFile in main).
func run(args []string, read func(string) ([]byte, error), out, errOut io.Writer) int {
	if len(args) != 1 {
		fmt.Fprintln(errOut, usage)
		return 2
	}
	data, err := read(args[0])
	if err != nil {
		fmt.Fprintf(errOut, "the fixture document cannot be read: %v\n", err)
		return 1
	}
	doc, err := buildDocument(data)
	if err != nil {
		fmt.Fprintf(errOut, "failed: %v\n", err)
		return 1
	}
	if _, err := out.Write(doc); err != nil {
		fmt.Fprintf(errOut, "the document cannot be written: %v\n", err)
		return 1
	}
	return 0
}
