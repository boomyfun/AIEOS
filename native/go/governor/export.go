package main

// The document: every case of the fixture document's governor fixtures, computed as the governor-only reference
// export computes it (tests/unit/test_export_governor.py), in the canonical text. The fixture document's other
// round-1 folders (the Resume Check's and the risk derivation's) are read as part of the document's form and passed
// over; this port computes the governor only (TASK-100; m8-plan.md section 1, item 1).

import (
	"errors"
	"fmt"
	"io"
	"strings"
)

const (
	governorFolder = "fixtures"
	usage          = "usage: <binary> <fixture document>"
)

// otherFolders are the fixture document's other folders, named by parts as the export modules build them.
var otherFolders = []string{governorFolder + "_rc", governorFolder + "_risk"}

var (
	errNotFixtureDocument = errors.New("not a fixture document")
	errCannotCompute      = errors.New("the case cannot be computed")
)

func notFixture(format string, a ...any) error {
	return fmt.Errorf("%w: %s", errNotFixtureDocument, fmt.Sprintf(format, a...))
}

// buildDocument computes the governor document from the fixture document's bytes, or returns an error: the input is
// not a fixture document, or a case cannot be computed. Nothing is written here.
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
	governors := 0
	for _, key := range root.keys {
		folder, stem, ok := strings.Cut(key, "/")
		if !ok || stem == "" || strings.Contains(stem, "/") {
			return nil, notFixture("the key %q is not <folder>/<file stem>", key)
		}
		if folder != governorFolder && !contains(otherFolders, folder) {
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
		if folder != governorFolder {
			continue
		}
		governors++
		recs, err := caseRecords(cases)
		if err != nil {
			return nil, fmt.Errorf("%s: %w", key, err)
		}
		doc[key] = recs
	}
	if governors == 0 {
		return nil, notFixture("no fixture of the folder %s", governorFolder)
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

// caseRecords is the reference's case_records for the governor folder: the record of each case, in case order, each
// argument read from the case as the conformance runner reads it.
func caseRecords(cases []any) ([]any, error) {
	out := []any{}
	for n, cv := range cases {
		c, ok := cv.(*Obj)
		if !ok {
			return nil, fmt.Errorf("%w: case %d is not an object", errNotFixtureDocument, n+1)
		}
		for _, k := range []string{"request", "inputs", "records"} {
			if !c.Has(k) {
				return nil, fmt.Errorf("%w: case %d lacks %s", errNotFixtureDocument, n+1, k)
			}
		}
		rec, err := evaluate(c.Val("request"), c.Val("inputs"), c.Val("records"))
		if err != nil {
			if !errors.Is(err, errCannotCompute) {
				err = fmt.Errorf("%w: %v", errCannotCompute, err)
			}
			return nil, fmt.Errorf("case %d: %w", n+1, err)
		}
		out = append(out, rec)
	}
	return out, nil
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
