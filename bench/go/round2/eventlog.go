package main

// The event log's append rules: eventlog.append and every function it calls.

import (
	"bytes"
	"math/big"
)

var leaseKeys = []string{"task_id", "fencing_token", "expires_at"}

// utcTime is an aware UTC datetime as round 2 reads it: its text (YYYY-MM-DDTHH:MM:SSZ, which both
// test_export_round2.time_text and eventlog._time_text write back unchanged) and a value that orders times.
type utcTime struct {
	text    string
	seconds int64
}

// lease is a lease given to append or reconcile: the object as the input gives it, its expires_at read as a time
// (test_export_round2._lease_value).
type lease struct {
	obj     *Obj
	expires utcTime
}

// appendResult is eventlog.AppendResult; seq, line and record are nil for None.
type appendResult struct {
	result   string
	reason   any
	seq      any
	line     []byte
	log      []byte
	findings []string
	record   map[string]any
}

func refused(reason string, findings []string, seq any, record map[string]any) appendResult {
	if findings == nil {
		findings = []string{}
	}
	return appendResult{result: "refused", reason: reason, seq: seq, findings: findings, record: record}
}

// appendCall holds the arguments of eventlog.append after log; a nil value is Python's None (the argument not
// given), and lease is nil for None.
type appendCall struct {
	eventType  any
	payload    any
	eventID    any
	appendedAt utcTime
	taskID     any
	fencingTok any
	corrects   any
	lease      *lease
	recorder   any
	recordID   any
}

// refusalRecord is eventlog.refusal_record.
func refusalRecord(eventID, taskID, recorder, recordID any) map[string]any {
	return map[string]any{"record_id": recordID, "fact_kind": "observation",
		"source_class": "deterministic_tool_local", "recorder": recorder, "subject": taskID,
		"evidence_type": "refused_submission", "outcome": "fail", "refers_to": eventID}
}

// leaseFindings is eventlog._lease_findings.
func leaseFindings(l *lease, taskID, fencingToken any, appendedAt utcTime) []string {
	if l == nil {
		return []string{"fence: no lease is given"}
	}
	if !l.obj.keysAre(leaseKeys...) {
		return []string{"fence: the lease is not a mapping with exactly task_id, fencing_token and expires_at"}
	}
	var found []string
	if fencingToken == nil {
		found = append(found, "fence: the event carries no fencing_token")
	}
	if !pyEq(l.obj.Val("task_id"), taskID) {
		found = append(found, "fence: the lease is on "+pyRepr(l.obj.Val("task_id"))+", not on the event's task "+
			pyRepr(taskID))
	}
	leaseToken := sameText(l.obj.Val("fencing_token"))
	if fencingToken != nil && leaseToken != sameText(fencingToken) {
		found = append(found, "fence: the event's fencing_token is not the lease's")
	}
	// expires_at is always an aware UTC datetime here (the input's text read by time_value).
	if !(l.expires.seconds > appendedAt.seconds) {
		found = append(found, "fence: the lease expired at or before the append time")
	}
	return found
}

// sameEventText is eventlog._same_text: the canonical text of the keys that make an event the same event.
func sameEventText(get func(string) (any, bool)) string {
	sub := map[string]any{}
	for _, k := range []string{"type", "payload", "task_id", "fencing_token", "corrects"} {
		if v, ok := get(k); ok {
			sub[k] = v
		}
	}
	return sameText(sub)
}

// appendEvent is eventlog.append(log, ...).
func appendEvent(log []byte, c appendCall) appendResult {
	// AC1: the given log.
	report := checkLog(log)
	logFindings := report.findings()
	if len(log) > 0 && !bytes.HasSuffix(log, []byte{'\n'}) {
		logFindings = append(logFindings, "2:lf: the log does not end with LF")
	}
	if len(logFindings) > 0 {
		return refused("log", logFindings, nil, nil)
	}

	// AC2: idempotency by event_id.
	newEvent := map[string]any{"type": c.eventType, "payload": c.payload}
	for _, kv := range []struct {
		key   string
		value any
	}{{"task_id", c.taskID}, {"fencing_token", c.fencingTok}, {"corrects", c.corrects}} {
		if kv.value != nil {
			newEvent[kv.key] = kv.value
		}
	}
	getNew := func(k string) (any, bool) { v, ok := newEvent[k]; return v, ok }
	knownIDs := map[string]bool{}
	for _, line := range report.lines {
		old := line.event
		oldID := old.Val("event_id").(string) // a line without a finding has a non-empty string event_id
		knownIDs[oldID] = true
		if line.duplicateOf == 0 && pyEq(oldID, c.eventID) {
			seq := old.Val("seq")
			if sameEventText(old.Get) == sameEventText(getNew) {
				return appendResult{result: "duplicate", seq: seq, findings: []string{}}
			}
			return refused("conflict", []string{"event_id " + pyRepr(c.eventID) + " is on the line with seq " +
				seq.(*big.Int).String() + " with another event"}, seq, nil)
		}
	}

	// AC3: the new event's own form.
	var findings []string
	if !isStr(c.eventID) {
		findings = append(findings, "6.1:event_id: event_id is not a non-empty string")
	}
	// appended_at is always an aware UTC datetime here (the input's text read by time_value).
	if c.taskID != nil && !matches(reTask, c.taskID) {
		findings = append(findings, "6.1:task_id: task_id is not TASK- followed by digits (reading)")
	}
	if c.fencingTok != nil {
		findings = append(findings, fenceFindings(true, c.fencingTok, nil)...)
	}
	if c.corrects != nil {
		s, ok := c.corrects.(string)
		if !(ok && s != "" && knownIDs[s]) {
			findings = append(findings, "6.1:corrects: corrects is not the event_id of a line of the log (reading)")
		}
	}
	findings = append(findings, payloadFindings(c.eventType, c.payload, "payload")...)
	var lineBytes []byte
	if len(findings) == 0 {
		obj := map[string]any{}
		for k, v := range newEvent {
			obj[k] = v
		}
		obj["event_id"] = c.eventID
		obj["appended_at"] = c.appendedAt.text
		obj["seq"] = len(report.lines) + 1
		lineBytes = []byte(pyDumps(obj) + "\n")
	}
	if len(findings) > 0 {
		return refused("event", findings, nil, nil)
	}

	// AC6, AC7: the fence.
	if c.fencingTok != nil || strEq(c.eventType, "task.submitted") {
		var fence []string
		if c.taskID == nil {
			fence = []string{"fence: the event names no task_id, so no lease can be on its task"}
		} else {
			fence = leaseFindings(c.lease, c.taskID, c.fencingTok, c.appendedAt)
		}
		if len(fence) > 0 {
			if c.taskID == nil {
				return refused("fence", append(fence, "fence: no refusal record, the event names no task_id"), nil, nil)
			}
			if !(isStr(c.recorder) && isStr(c.recordID)) {
				return refused("fence", append(fence, "fence: no refusal record, recorder and record_id are not both "+
					"non-empty strings"), nil, nil)
			}
			return refused("fence", fence, nil, refusalRecord(c.eventID, c.taskID, c.recorder, c.recordID))
		}
	}

	// AC4: the whole log after the append.
	newLog := append(append([]byte(nil), log...), lineBytes...)
	if after := checkLog(newLog).findings(); len(after) > 0 {
		return refused("log_after", after, nil, nil)
	}

	// AC5: the given bytes are an exact prefix, followed by exactly one line.
	if !(bytes.Equal(newLog[:len(log)], log) && bytes.Equal(newLog[len(log):], lineBytes) &&
		bytes.Count(lineBytes, []byte{'\n'}) == 1) {
		failClosed("the append-only property failed (AC5)")
	}
	return appendResult{result: "appended", seq: len(report.lines) + 1, line: lineBytes, log: newLog,
		findings: []string{}}
}
