package main

// Recovery between Git and the event log at start: recovery.reconcile and every function it calls.

import (
	"bytes"
	"math/big"
	"regexp"
	"sort"
	"strings"
)

const (
	taskKey  = "AIEOS-Task"
	fenceKey = "AIEOS-Fence"
	idPrefix = "recovery"
)

var (
	reCommit40  = regexp.MustCompile(`^[0-9a-f]{40}$`)
	reCounter   = regexp.MustCompile(`^[0-9]+$`)
	reParagraph = regexp.MustCompile("\n[ \t]*\n")
)

// commit is one commit given to reconcile: its id and its message (both strings, as _check_arguments requires).
type commit struct {
	id      string
	message string
}

// recoveryResult is recovery.RecoveryResult.
type recoveryResult struct {
	log      []byte
	events   []any
	expired  []*lease
	findings []string
}

// recoveryID is recovery._id: the SHA-256 hex digest of "recovery", the commit id and the kind, joined by LF.
func recoveryID(commitID, kind string) string {
	return hexDigest(strings.Join([]string{idPrefix, commitID, kind}, "\n"))
}

// trailers is recovery.trailers: (task, fence, findings), task "" for None and fence nil for None.
func trailers(message string) (string, *Obj, []string) {
	var paragraphs []string
	for _, p := range reParagraph.Split(strings.Trim(message, "\n"), -1) {
		if pyStrip(p) != "" {
			paragraphs = append(paragraphs, p)
		}
	}
	var last []string
	if len(paragraphs) > 0 {
		last = strings.Split(paragraphs[len(paragraphs)-1], "\n")
	}
	keys := map[string]string{strings.ToLower(taskKey): taskKey, strings.ToLower(fenceKey): fenceKey}
	found := map[string][]string{taskKey: nil, fenceKey: nil}
	var findings []string
	for i := 0; i+1 < len(paragraphs); i++ {
		for _, line := range strings.Split(paragraphs[i], "\n") {
			key, _, sep := strings.Cut(line, ":")
			if _, named := keys[pyLower(pyStrip(key))]; sep && named {
				findings = append(findings, "trailer: "+pyStrRepr(pyStrip(key))+" is named outside the last paragraph")
			}
		}
	}
	for _, line := range last {
		key, value, sep := strings.Cut(line, ":")
		name := pyStrip(key)
		spelled, named := keys[pyLower(name)]
		if !(sep && named) {
			continue
		}
		if name != spelled {
			findings = append(findings, "trailer: "+pyStrRepr(name)+" is not spelled "+pyStrRepr(spelled))
			continue
		}
		if key != name {
			findings = append(findings, "trailer: "+pyStrRepr(name)+" is not at the start of its line")
		}
		found[name] = append(found[name], pyStrip(value))
	}
	for _, key := range []string{taskKey, fenceKey} {
		if n := len(found[key]); n > 1 {
			findings = append(findings, "trailer: "+key+" is given "+big.NewInt(int64(n)).String()+" times")
		}
	}
	task := ""
	if len(found[taskKey]) == 1 {
		t := found[taskKey][0]
		if reTask.MatchString(t) {
			task = t
		} else {
			findings = append(findings, "trailer: "+taskKey+" "+pyStrRepr(t)+" is not TASK- followed by digits")
		}
	}
	var fence *Obj
	if len(found[fenceKey]) == 1 {
		v := found[fenceKey][0]
		cut := strings.LastIndex(v, ":")
		if cut > 0 && reCounter.MatchString(v[cut+1:]) {
			counter := v[cut+1:]
			if len(counter) > maxIntDigits {
				// int() refuses a decimal text of more than 4300 digits: ValueError, a case reconcile cannot compute.
				failClosed("a fence counter of more than 4300 digits")
			}
			n, _ := new(big.Int).SetString(counter, 10)
			fence = newObj()
			fence.Set("epoch", v[:cut])
			fence.Set("counter", n)
		} else {
			findings = append(findings, "trailer: "+fenceKey+" "+pyStrRepr(v)+" is not <epoch>:<counter>")
		}
	}
	return task, fence, findings
}

type usedKey struct{ task, token string }

// observation is recovery.observation.
func observation(commitID, taskID, recorder string) map[string]any {
	return map[string]any{"record_id": recoveryID(commitID, "unfenced_write"), "fact_kind": "observation",
		"source_class": "deterministic_tool_local", "recorder": recorder, "subject": taskID,
		"evidence_type": "unfenced_write", "outcome": "fail", "refers_to": commitID}
}

// reconcile is recovery.reconcile, its arguments already of the forms _check_arguments requires (the reader of
// the input document fails closed where _check_arguments raises).
func reconcile(log []byte, commits []commit, leases []*lease, now utcTime, recorder string) recoveryResult {
	expired := []*lease{}
	for _, l := range leases {
		if !(l.expires.seconds > now.seconds) {
			expired = append(expired, l)
		}
	}
	report := checkLog(log)
	damaged := report.findings()
	if len(log) > 0 && !bytes.HasSuffix(log, []byte{'\n'}) {
		damaged = append(damaged, "2:lf: the log does not end with LF")
	}
	if len(damaged) > 0 {
		out := make([]string, len(damaged))
		for i, f := range damaged {
			out[i] = "log: " + f
		}
		return recoveryResult{log: log, events: []any{}, expired: expired, findings: out}
	}

	findings := []string{}
	events := []any{}
	given := map[string]bool{}
	for _, c := range commits {
		given[c.id] = true
	}
	named := map[string]bool{}
	used := map[usedKey]bool{}
	// _submissions: the task.submitted events of the log (free of findings), each first line; step 2 and the sets
	// named and used are read from them in their order.
	for _, line := range report.lines {
		e := line.event
		if line.duplicateOf != 0 || e == nil || !strEq(e.Val("type"), "task.submitted") {
			continue
		}
		commitID := e.Val("payload").(*Obj).Val("commit")
		taskID := e.Val("task_id")
		token := sameText(e.Val("fencing_token"))
		// Step 2: Git wins.
		if c, ok := commitID.(string); !ok || !given[c] {
			findings = append(findings, "step 2: the log's task.submitted of "+pyStr(taskID)+" names the commit "+
				pyStr(commitID)+", which is not among the given commits; nothing is appended")
		}
		named[pyStr(commitID)] = true
		used[usedKey{pyStr(taskID), token}] = true
	}

	add := func(eventType string, payload map[string]any, eventID, taskID string, fencingToken *Obj, l *lease) bool {
		call := appendCall{eventType: eventType, payload: mapObj(payload), eventID: eventID, appendedAt: now,
			taskID: taskID, lease: l, recorder: recorder, recordID: recoveryID(eventID, "refused_submission")}
		if fencingToken != nil {
			call.fencingTok = fencingToken
		}
		r := appendEvent(log, call)
		if r.result == "refused" {
			findings = append(findings, "step 1: eventlog.append refused the "+eventType+" of "+taskID+" (reason "+
				pyStr(r.reason)+"): "+strings.Join(r.findings, "; "))
			return false
		}
		if r.result == "appended" {
			log = r.log
		}
		events = append(events, map[string]any{"event_id": eventID, "type": eventType, "task_id": taskID,
			"result": r.result})
		return true
	}

	// Step 1, oldest first.
	for _, c := range commits {
		taskID, fence, bad := trailers(c.message)
		if len(bad) > 0 {
			for _, f := range bad {
				findings = append(findings, "commit "+c.id+": "+f)
			}
			continue
		}
		if taskID == "" || named[c.id] {
			continue
		}
		token, hasToken := "", fence != nil
		if hasToken {
			token = sameText(fence)
		}
		var held *lease
		if hasToken && !used[usedKey{taskID, token}] {
			for _, l := range leases {
				if pyEq(l.obj.Val("task_id"), taskID) && sameText(l.obj.Val("fencing_token")) == token &&
					l.expires.seconds > now.seconds {
					held = l
					break
				}
			}
		}
		if held != nil {
			if add("task.submitted", map[string]any{"commit": c.id, "compensating": true},
				recoveryID(c.id, "task.submitted"), taskID, fence, held) {
				used[usedKey{taskID, token}] = true
				named[c.id] = true
			}
		} else {
			add("record.added", observation(c.id, taskID, recorder), recoveryID(c.id, "record.added"), taskID, nil, nil)
		}
	}
	return recoveryResult{log: log, events: events, expired: expired, findings: findings}
}

// mapObj is a payload built by recovery as an object of the form the log's reader gives (its keys sorted, which
// changes no text: every text of an object sorts its keys).
func mapObj(m map[string]any) *Obj {
	o := newObj()
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		o.Set(k, m[k])
	}
	return o
}
