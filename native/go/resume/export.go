package main

// The document: every case of the fixture document's Resume Check fixtures, computed as the Resume Check-only
// reference export computes it (tests/unit/test_export_resume.py), in the canonical text. The fixture document's
// other round-1 folders (the governor's and the risk derivation's) are read as part of the document's form and
// passed over; this port computes the Resume Check only (TASK-101).

import (
	"errors"
	"fmt"
	"io"
	"strings"
)

const (
	governorFolder = "fixtures"
	rcFolder       = governorFolder + "_rc"
	usage          = "usage: <binary> <fixture document>"
)

// otherFolders are the fixture document's other folders, named by parts as the export modules build them.
var otherFolders = []string{governorFolder, governorFolder + "_risk"}

var errNotFixtureDocument = errors.New("not a fixture document")

func notFixture(format string, a ...any) error {
	return fmt.Errorf("%w: %s", errNotFixtureDocument, fmt.Sprintf(format, a...))
}

// buildDocument computes the Resume Check document from the fixture document's bytes, or returns an error: the input
// is not a fixture document, or a case cannot be computed. Nothing is written here.
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
	rcs := 0
	for _, key := range root.keys {
		folder, stem, ok := strings.Cut(key, "/")
		if !ok || stem == "" || strings.Contains(stem, "/") {
			return nil, notFixture("the key %q is not <folder>/<file stem>", key)
		}
		if folder != rcFolder && !contains(otherFolders, folder) {
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
		if folder != rcFolder {
			continue
		}
		rcs++
		recs, err := caseRecords(cases)
		if err != nil {
			return nil, fmt.Errorf("%s: %w", key, err)
		}
		doc[key] = recs
	}
	if rcs == 0 {
		return nil, notFixture("no fixture of the folder %s", rcFolder)
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

// caseRecords is the reference's case_records for the Resume Check folder: the record of each case, in case order,
// its inputs read from the case as the conformance runner reads them.
func caseRecords(cases []any) ([]any, error) {
	out := []any{}
	for n, cv := range cases {
		c, ok := cv.(*Obj)
		if !ok {
			return nil, fmt.Errorf("%w: case %d is not an object", errNotFixtureDocument, n+1)
		}
		if !c.Has("inputs") {
			return nil, fmt.Errorf("%w: case %d lacks inputs", errNotFixtureDocument, n+1)
		}
		rec, err := check(c.Val("inputs"), nil)
		if err != nil {
			return nil, fmt.Errorf("case %d: %w", n+1, err)
		}
		out = append(out, placeholder(rec))
	}
	return out, nil
}

// placeholder is the reference's closed placeholder list: engine_identity.python of the Resume Check's records.
func placeholder(rec map[string]any) map[string]any {
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
