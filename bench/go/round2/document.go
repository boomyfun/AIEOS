package main

// The round-2 document: the input document read back as test_export_round2.parse_input reads it, every append call
// and reconcile case computed as reference_document computes it, and the whole output in the canonical text.

import (
	"errors"
	"fmt"
	"io"
)

const usage2 = "usage: port2 <round-2 input document>"

var (
	callKeys = []string{"event_type", "payload", "event_id", "appended_at", "task_id", "fencing_token", "corrects",
		"lease", "recorder", "record_id"}
	caseKeys = []string{"log", "commits", "leases", "now", "recorder"}

	errNotInput   = errors.New("not a round-2 input document")
	errNotCompute = errors.New("a call or case cannot be computed")
)

// daysFromCivil is the number of days from 1970-01-01 to a date of the proleptic Gregorian calendar.
func daysFromCivil(y, m, d int) int64 {
	if m <= 2 {
		y--
	}
	era := y / 400
	yoe := y - era*400
	mp := (m + 9) % 12
	doy := (153*mp+2)/5 + d - 1
	doe := yoe*365 + yoe/4 - yoe/100 + doy
	return int64(era)*146097 + int64(doe) - 719468
}

// timeValue is test_export_round2.time_value: a text of exactly the form YYYY-MM-DDTHH:MM:SSZ that strftime writes
// back unchanged, read as an aware UTC datetime. A year below 1000 is refused: strftime's %Y writes it without its
// leading zeros on the C library the reference is made with, so the text does not come back (a stated reading).
func timeValue(v any) utcTime {
	s, ok := v.(string)
	if !ok {
		failClosed("a time is not text")
	}
	form := len(s) == 20 && s[4] == '-' && s[7] == '-' && s[10] == 'T' && s[13] == ':' && s[16] == ':' && s[19] == 'Z'
	if form {
		for _, i := range []int{0, 1, 2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18} {
			if s[i] < '0' || s[i] > '9' {
				form = false
			}
		}
	}
	if !form {
		failClosed("a time is not YYYY-MM-DDTHH:MM:SSZ: %q", s)
	}
	y, mo, d, h, mi, se := atoi(s[0:4]), atoi(s[5:7]), atoi(s[8:10]), atoi(s[11:13]), atoi(s[14:16]), atoi(s[17:19])
	if y < 1000 || !validDateTime(y, mo, d, h, mi, se) {
		failClosed("a time is not YYYY-MM-DDTHH:MM:SSZ: %q", s)
	}
	return utcTime{text: s, seconds: daysFromCivil(y, mo, d)*86400 + int64(h*3600+mi*60+se)}
}

// leaseValue is test_export_round2._lease_value: nil for None; an object with expires_at, read as a time.
func leaseValue(v any) *lease {
	if v == nil {
		return nil
	}
	o, ok := v.(*Obj)
	if !ok || !o.Has("expires_at") {
		failClosed("a lease is not an object with expires_at")
	}
	return &lease{obj: o, expires: timeValue(o.Val("expires_at"))}
}

// parseInput is test_export_round2.parse_input: the input document read back, refused unless it is the canonical
// text of one object with append and reconcile, each call and case with exactly its keys.
func parseInput(data []byte) (*Obj, error) {
	for _, b := range data {
		if b > 127 {
			return nil, fmt.Errorf("%w: the text is not ASCII", errNotInput)
		}
	}
	value, err := parseJSON(data)
	if err != nil {
		return nil, fmt.Errorf("%w: %v", errNotInput, err)
	}
	doc, ok := value.(*Obj)
	if !ok || !doc.keysAre("append", "reconcile") {
		return nil, fmt.Errorf("%w: not one object with append and reconcile", errNotInput)
	}
	if text, err := canonicalText(doc); err != nil || string(text) != string(data) {
		return nil, fmt.Errorf("%w: not its canonical text", errNotInput)
	}
	for _, part := range []struct {
		key  string
		keys []string
	}{{"append", callKeys}, {"reconcile", caseKeys}} {
		list, ok := doc.Val(part.key).([]any)
		if !ok {
			return nil, fmt.Errorf("%w: %s is not a list", errNotInput, part.key)
		}
		for _, item := range list {
			o, ok := item.(*Obj)
			if !ok || !o.keysAre(part.keys...) {
				return nil, fmt.Errorf("%w: an entry of %s without exactly its keys", errNotInput, part.key)
			}
		}
	}
	return doc, nil
}

// appendEntry computes one append call, from the carried log, as {result, reason, findings, seq, line, record}.
func appendEntry(log []byte, call *Obj) (map[string]any, []byte) {
	c := appendCall{
		eventType:  call.Val("event_type"),
		payload:    call.Val("payload"),
		eventID:    call.Val("event_id"),
		appendedAt: timeValue(call.Val("appended_at")),
		taskID:     call.Val("task_id"),
		fencingTok: call.Val("fencing_token"),
		corrects:   call.Val("corrects"),
		lease:      leaseValue(call.Val("lease")),
		recorder:   call.Val("recorder"),
		recordID:   call.Val("record_id"),
	}
	r := appendEvent(log, c)
	if r.result == "appended" {
		log = r.log
	}
	var line any
	if r.line != nil {
		line = string(r.line)
	}
	var record any
	if r.record != nil {
		record = r.record
	}
	return map[string]any{"result": r.result, "reason": r.reason, "findings": r.findings, "seq": r.seq,
		"line": line, "record": record}, log
}

// caseLeases is [_lease_value(x) for x in case['leases']] followed by _check_arguments's lease rule: iterating an
// empty text or an empty object gives no lease, as in the Python.
func caseLeases(v any) []*lease {
	var items []any
	switch x := v.(type) {
	case []any:
		items = x
	case string:
		if x != "" {
			failClosed("a lease is not an object with expires_at")
		}
	case *Obj:
		if len(x.keys) > 0 {
			failClosed("a lease is not an object with expires_at")
		}
	default:
		failClosed("the leases are not iterable (TypeError)")
	}
	out := []*lease{}
	for _, item := range items {
		l := leaseValue(item)
		if l == nil || !l.obj.keysAre(leaseKeys...) {
			failClosed("a lease is not a mapping with exactly task_id, fencing_token and expires_at")
		}
		out = append(out, l)
	}
	return out
}

// reconcileEntry computes one reconcile case as {log, events, expired, findings}, its arguments read as
// reference_document reads them and checked as recovery._check_arguments checks them.
func reconcileEntry(c *Obj) map[string]any {
	logText, ok := c.Val("log").(string)
	if !ok {
		failClosed("the log is not text (AttributeError)")
	}
	for i := 0; i < len(logText); i++ {
		if logText[i] > 127 {
			failClosed("the log is not ASCII (UnicodeEncodeError)")
		}
	}
	list, ok := c.Val("commits").([]any)
	if !ok {
		failClosed("the commits are not given as a list")
	}
	leases := caseLeases(c.Val("leases"))
	now := timeValue(c.Val("now"))
	commits := []commit{}
	for _, item := range list {
		o, ok := item.(*Obj)
		if !ok || !o.keysAre("commit", "message") {
			failClosed("a commit is not a mapping with exactly commit and message")
		}
		if !matches(reCommit40, o.Val("commit")) {
			failClosed("a commit id is not 40 lowercase hex digits")
		}
		message, ok := o.Val("message").(string)
		if !ok {
			failClosed("a commit message is not a string")
		}
		commits = append(commits, commit{id: o.Val("commit").(string), message: message})
	}
	recorder := c.Val("recorder")
	if !isStr(recorder) {
		failClosed("the recorder is not a non-empty string")
	}
	r := reconcile([]byte(logText), commits, leases, now, recorder.(string))
	expired := make([]any, len(r.expired))
	for i, l := range r.expired {
		// _lease_text: the lease with expires_at written back by time_text, which gives the input's text again.
		expired[i] = l.obj
	}
	return map[string]any{"log": string(r.log), "events": r.events, "expired": expired, "findings": r.findings}
}

// buildRound2 computes the whole round-2 document from the input document's bytes, or returns an error. Nothing is
// written here.
func buildRound2(data []byte) (out []byte, err error) {
	defer func() {
		if p := recover(); p != nil {
			out = nil
			if s, ok := p.(stop); ok {
				err = fmt.Errorf("%w: %s", errNotCompute, s.why)
			} else {
				err = fmt.Errorf("%w: an unexpected error: %v", errNotCompute, p)
			}
		}
	}()
	doc, err := parseInput(data)
	if err != nil {
		return nil, err
	}
	log := []byte{}
	appends := []any{}
	for _, call := range doc.Val("append").([]any) {
		var entry map[string]any
		entry, log = appendEntry(log, call.(*Obj))
		appends = append(appends, entry)
	}
	cases := []any{}
	for _, c := range doc.Val("reconcile").([]any) {
		cases = append(cases, reconcileEntry(c.(*Obj)))
	}
	out, err = canonicalText(map[string]any{"append": appends, "reconcile": cases})
	if err != nil {
		return nil, fmt.Errorf("%w: %v", errNotCompute, err)
	}
	for _, b := range out {
		if b > 127 || b == '\r' {
			return nil, fmt.Errorf("%w: the document is not ASCII with LF line ends", errNotCompute)
		}
	}
	return out, nil
}

// run2 is the round-2 command line: one argument, the input document's path. It writes the whole document to out
// in one write and returns 0, or writes nothing to out and returns non-zero. read is the one file read
// (os.ReadFile in main).
func run2(args []string, read func(string) ([]byte, error), out, errOut io.Writer) int {
	if len(args) != 1 {
		fmt.Fprintln(errOut, usage2)
		return 2
	}
	data, err := read(args[0])
	if err != nil {
		fmt.Fprintf(errOut, "the round-2 input document cannot be read: %v\n", err)
		return 1
	}
	doc, err := buildRound2(data)
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
