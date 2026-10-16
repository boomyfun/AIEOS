package main

// The record forms of records.py with their full finding texts, as round 2 needs them: check_log (with its line
// checks), check_payload, check_record, check_audit_copy, check_decision and the fence form. The round-1 copy
// records.go keeps only the rule of each finding, so the forms are written here again with their texts; its lists,
// patterns and helpers are reused.

import (
	"bytes"
	"fmt"
	"math/big"
	"regexp"
	"sort"
	"strings"
)

var (
	eventTypes = []string{"task.drafted", "task.approved", "task.blocked", "task.unblocked", "task.submitted",
		"decision.acceptance", "decision.execution", "task.done", "task.stale", "task.replanned", "intent.changed",
		"drift.detected", "violation.detected", "evidence.stale", "conflict.detected", "record.added"}
	envelopeRequired    = []string{"event_id", "type", "appended_at", "seq", "payload"}
	envelopeKeys        = []string{"event_id", "type", "appended_at", "seq", "payload", "task_id", "fencing_token", "corrects"}
	acceptanceDecisions = []string{"ACCEPT", "NEEDS_REVIEW", "INSUFFICIENT_EVIDENCE", "NEEDS_REWORK", "REJECT"}
	executionDecisions  = []string{"CONTINUE", "CONTINUE_WITH", "REPLAN", "STOP: scope invalid",
		"STOP: runtime insufficient", "STOP: violation", "BLOCKED", "ESCALATE"}
	acceptanceKeys = []string{"task_content_hash", "evaluated_commit", "intent_versions", "next_task_state",
		"table_row", "profile_used", "missing_gates", "blocking", "failed_gates", "reverify", "approval_record",
		"policy_version", "level_version", "governor_identity", "ruleset_version", "scenario_set_hash", "uncovered",
		"rests_on_ai"}
	profileKeys   = []string{"dimension", "required", "satisfied_by", "missing_types"}
	executionKeys = []string{"contract_hash", "contract_version", "base_commit", "head_commit", "log_seq", "delta",
		"checks", "outcomes_fired", "read_set", "signatures", "intent_versions", "dependencies", "constitution",
		"runtime", "budgets", "policy_version", "engine_identity", "uncovered", "state_effect"}
	executionOrder = []string{"STOP: violation", "STOP: scope invalid", "STOP: runtime insufficient", "ESCALATE",
		"BLOCKED", "REPLAN", "CONTINUE_WITH"}
	checkKeys          = []string{"check", "status", "outcome", "detail"}
	checkStatuses      = []string{"passed", "fired", "skipped", "not_run"}
	recordPayloadTypes = []string{"record.added", "violation.detected", "decision.acceptance", "decision.execution"}
	decisionTypes      = []string{"decision.acceptance", "decision.execution"}
	executionLists     = []string{"delta", "signatures", "uncovered", "state_effect"}
	executionObjects   = []string{"read_set", "dependencies", "constitution", "runtime", "budgets"}

	reTime   = regexp.MustCompile(`^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?Z$`)
	reChange = regexp.MustCompile(`^CHG-[0-9]+$`)
	rePython = regexp.MustCompile(`^[0-9]+\.[0-9]+\.[0-9]+$`)
	bom      = []byte{0xef, 0xbb, 0xbf}
)

// finding is str(records.Finding(rule, detail)).
func finding(rule, format string, a ...any) string {
	return rule + ": " + fmt.Sprintf(format, a...)
}

// isInt is records._is_int: an integer (never a boolean), at least minimum when one is given.
func isInt(v any, minimum *big.Int) bool {
	n, ok := v.(*big.Int)
	return ok && (minimum == nil || n.Cmp(minimum) >= 0)
}

var (
	zero = big.NewInt(0)
	one  = big.NewInt(1)
)

// keysOf are the keys of an object (nil for any other value).
func keysOf(v any) []string {
	if o, ok := v.(*Obj); ok {
		return o.keys
	}
	return nil
}

// sortedKeysNotIn is sorted(k for k in o if k not in allowed...).
func sortedKeysNotIn(o *Obj, allowed ...[]string) []string {
	var out []string
	for _, k := range o.keys {
		known := false
		for _, a := range allowed {
			if in(a, k) {
				known = true
			}
		}
		if !known {
			out = append(out, k)
		}
	}
	sort.Strings(out)
	return out
}

// eventTypeIn is "event_type in <a frozenset of strings>": a list or an object as event_type is unhashable, where the
// Python raises TypeError (fail closed).
func eventTypeIn(values []string, v any) bool {
	switch v.(type) {
	case []any, *Obj:
		failClosed("an unhashable event type (TypeError)")
	}
	return in(values, v)
}

func daysIn(year, month int) int {
	switch month {
	case 2:
		if year%4 == 0 && (year%100 != 0 || year%400 == 0) {
			return 29
		}
		return 28
	case 4, 6, 9, 11:
		return 30
	}
	return 31
}

// validDateTime is whether datetime.datetime(y, m, d, H, M, S) exists.
func validDateTime(y, m, d, hh, mm, ss int) bool {
	return y >= 1 && y <= 9999 && m >= 1 && m <= 12 && d >= 1 && d <= daysIn(y, m) && hh <= 23 && mm <= 59 &&
		ss <= 59
}

func atoi(s string) int {
	n := 0
	for _, c := range []byte(s) {
		n = n*10 + int(c-'0')
	}
	return n
}

// isTime is records._is_time.
func isTime(v any) bool {
	s, ok := v.(string)
	if !ok {
		return false
	}
	m := reTime.FindStringSubmatch(s)
	if m == nil {
		return false
	}
	return validDateTime(atoi(m[1]), atoi(m[2]), atoi(m[3]), atoi(m[4]), atoi(m[5]), atoi(m[6]))
}

// ---------------------------------------------------------------------------------------------------------------
// check_record, check_audit_copy and their helpers, with texts

type formTest struct {
	test func(any) bool
	text string
}

var (
	versionForm = formTest{func(v any) bool { return matches(reVersion, v) }, "v followed by digits"}
	hashForm    = formTest{func(v any) bool { return matches(reHex64, v) }, "64 lowercase hex digits"}
	strForm     = formTest{isStr, "a non-empty string"}
	listForm    = formTest{isStrList, "a list of non-empty strings (reading: section 6.3 says lists of strings)"}
	commitForm  = formTest{func(v any) bool { return matches(reCommit, v) }, "a full lowercase hex commit id"}
	boolForm    = formTest{func(v any) bool { _, ok := v.(bool); return ok }, "true or false"}
	changeForm  = formTest{func(v any) bool { return matches(reChange, v) }, "CHG- followed by digits"}
)

func oneOf(values ...string) formTest {
	return formTest{func(v any) bool { return in(values, v) }, "one of " + strings.Join(values, ", ")}
}

var payloadForms = map[string]map[string]formTest{
	"task.drafted":   {"contract_version": versionForm, "contract_hash": hashForm},
	"task.approved":  {"contract_version": versionForm, "contract_hash": hashForm, "approval_record": strForm},
	"task.blocked":   {"reason": strForm, "blocked_by": listForm},
	"task.unblocked": {"reason": strForm},
	"task.submitted": {"commit": commitForm, "compensating": boolForm},
	"task.done":      {"decision_record": strForm},
	"task.stale":     {"cause": oneOf("intent_change", "conflict"), "refers_to": strForm},
	"task.replanned": {"contract_version": versionForm, "contract_hash": hashForm},
	"intent.changed": {"entity": strForm, "from_version": versionForm, "to_version": versionForm,
		"change_request": changeForm},
	"drift.detected": {"paths": listForm, "entities": listForm},
	"evidence.stale": {"records": listForm, "reason": oneOf("commit", "intent_version")},
}

// keysAndForms is records._keys_and_forms.
func keysAndForms(obj *Obj, forms map[string]formTest, rule, where string) []string {
	var f []string
	names := make([]string, 0, len(forms))
	for k := range forms {
		names = append(names, k)
	}
	sort.Strings(names)
	for _, key := range sortedKeysNotIn(obj, names) {
		f = append(f, finding(rule+":unknown_key", "%s has the key %s, which section 6.3 does not name", where,
			pyStrRepr(key)))
	}
	for _, key := range names {
		v, ok := obj.Get(key)
		if !ok {
			f = append(f, finding(rule+":missing_key", "%s lacks %s", where, pyStrRepr(key)))
			continue
		}
		if !forms[key].test(v) {
			f = append(f, finding(rule+":"+key, "%s %s is not %s", where, pyStrRepr(key), forms[key].text))
		}
	}
	return f
}

// recordFindings is records.check_record(record, extra_keys, where, section) for a record that is an object (every
// caller in round 2 gives one).
func recordFindings(r *Obj, extra []string, where, section string) []string {
	var f []string
	names := "section 6.2 does not name"
	if section != "6.2" {
		names = fmt.Sprintf("sections 6.2 and %s do not name", section)
	}
	for _, key := range sortedKeysNotIn(r, recordKeys, extra) {
		f = append(f, finding(section+":unknown_key", "%s has the key %s, which %s", where, pyStrRepr(key), names))
	}
	for _, key := range recordRequired {
		if !r.Has(key) {
			f = append(f, finding("6.2:missing_key", "%s lacks %s (reading: required)", where, pyStrRepr(key)))
		}
	}
	for _, key := range []string{"record_id", "recorder", "subject"} {
		if v, ok := r.Get(key); ok && !isStr(v) {
			f = append(f, finding("6.2:"+key, "%s %s is not a non-empty string", where, pyStrRepr(key)))
		}
	}
	if v, ok := r.Get("fact_kind"); ok && !in(factKinds, v) {
		f = append(f, finding("6.2:fact_kind", "%s fact_kind is not claim, observation, interpretation or authority", where))
	}
	if v, ok := r.Get("source_class"); ok && !in(sourceClasses, v) {
		f = append(f, finding("6.2:source_class", "%s source_class is not one of the classes of DM B3", where))
	}
	f = append(f, outcomeFindings(r, where)...)
	if v, ok := r.Get("commit"); ok && !matches(reCommit, v) {
		f = append(f, finding("6.2:commit", "%s commit is not a full lowercase hex commit id", where))
	}
	if v, ok := r.Get("intent_versions"); ok && !isIntentVersions(v) {
		f = append(f, finding("6.2:intent_versions", "%s intent_versions does not map ids to versions v<digits>", where))
	}
	f = append(f, bindingFindings(r, where)...)
	f = append(f, reviewFindings(r, where)...)
	if v, ok := r.Get("gate"); ok && !matches(reGate, v) {
		f = append(f, finding("6.2:gate", "%s gate is not G followed by digits", where))
	}
	for _, key := range []string{"evidence_type", "dimension", "refers_to"} {
		if v, ok := r.Get(key); ok && !isStr(v) {
			f = append(f, finding("6.2:"+key, "%s %s is not a non-empty string", where, pyStrRepr(key)))
		}
	}
	f = append(f, auditCopyFindings(r, where)...)
	return f
}

// auditCopyFindings is records.check_audit_copy.
func auditCopyFindings(r *Obj, where string) []string {
	var f []string
	kindV := r.Val("evidence_type")
	if !in(auditCopyTypes, kindV) {
		for _, key := range auditCopyTypes {
			if r.Has(key) {
				f = append(f, finding("6.2:audit_copy_key", "%s carries %s, but its evidence_type is not %s", where,
					pyStrRepr(key), pyStrRepr(key)))
			}
		}
		return f
	}
	kind := kindV.(string)
	other := auditCopyTypes[0]
	if kind == auditCopyTypes[0] {
		other = auditCopyTypes[1]
	}
	if !strEq(r.Val("fact_kind"), "observation") {
		f = append(f, finding("6.2:audit_copy_fact_kind", "%s is an audit copy whose fact_kind is not observation", where))
	}
	if !in(auditCopySources, r.Val("source_class")) {
		f = append(f, finding("6.2:audit_copy_source_class", "%s is an audit copy whose source_class is neither "+
			"deterministic_tool_local nor deterministic_tool_external_ci", where))
	}
	if v, ok := r.Get(kind); !ok {
		f = append(f, finding("6.2:audit_copy_key", "%s is a %s audit copy that lacks its key %s", where, kind,
			pyStrRepr(kind)))
	} else if !isAuditValue(kind, v) {
		f = append(f, finding("6.2:audit_copy_value", "%s %s is not null or a value of its form", where, pyStrRepr(kind)))
	}
	if r.Has(other) {
		f = append(f, finding("6.2:audit_copy_key", "%s is a %s audit copy that carries %s", where, kind, pyStrRepr(other)))
	}
	for _, key := range []string{"commit", "intent_versions"} {
		if !r.Has(key) {
			f = append(f, finding("6.2:audit_copy_binding", "%s is an audit copy that lacks %s", where, pyStrRepr(key)))
		}
	}
	for _, key := range auditCopyForbidden {
		if r.Has(key) {
			f = append(f, finding("6.2:audit_copy_forbidden", "%s is an audit copy that carries %s", where, pyStrRepr(key)))
		}
	}
	return f
}

func outcomeFindings(r *Obj, where string) []string {
	var f []string
	outcome, has := r.Get("outcome")
	if has && !in(outcomes, outcome) {
		f = append(f, finding("6.2:outcome", "%s outcome is not pass, fail or blocking", where))
	}
	blocking := strEq(outcome, "blocking")
	if blocking && !r.Has("blocking_kind") {
		f = append(f, finding("6.2:blocking_kind", "%s has outcome blocking but no blocking_kind", where))
	}
	if !blocking && r.Has("blocking_kind") {
		f = append(f, finding("6.2:blocking_kind", "%s has blocking_kind without outcome blocking", where))
	}
	if v, ok := r.Get("blocking_kind"); ok && !in(blockingKinds, v) {
		kinds := append([]string(nil), blockingKinds...)
		sort.Strings(kinds)
		f = append(f, finding("6.2:blocking_kind", "%s blocking_kind is not one of %s", where, strings.Join(kinds, ", ")))
	}
	return f
}

func bindingFindings(r *Obj, where string) []string {
	bv, ok := r.Get("approval_binding")
	if !ok {
		if strEq(r.Val("fact_kind"), "authority") {
			return []string{finding("6.2:approval_binding", "%s is an authority record without approval_binding", where)}
		}
		return nil
	}
	b, ok := bv.(*Obj)
	if !(ok && b.keysAre("kind", "hash") && in(bindingKinds, b.Val("kind")) && matches(reHex64, b.Val("hash"))) {
		return []string{finding("6.2:approval_binding", "%s approval_binding is not {kind, hash} with kind contract, "+
			"acceptance, change_request or baseline and a 64-hex hash", where)}
	}
	return nil
}

func reviewFindings(r *Obj, where string) []string {
	var f []string
	kind := r.Val("evidence_type")
	needsRef := strEq(r.Val("source_class"), "decision_agent") || strEq(kind, "other_model_review")
	if needsRef && !r.Has("decision_ref") {
		f = append(f, finding("6.2:decision_ref", "%s needs decision_ref (a decision_agent record or an "+
			"other_model_review)", where))
	}
	if v, ok := r.Get("decision_ref"); ok && !isStr(v) {
		f = append(f, finding("6.2:decision_ref", "%s decision_ref is not a non-empty string", where))
	}
	if strEq(kind, "other_model_review") && !r.Has("models") {
		f = append(f, finding("6.2:models", "%s is an other_model_review without models", where))
	}
	if v, ok := r.Get("models"); ok {
		m, isObj := v.(*Obj)
		if !(isObj && m.keysAre("reviewer", "implementer") && isStr(m.Val("reviewer")) && isStr(m.Val("implementer"))) {
			f = append(f, finding("6.2:models", "%s models is not {reviewer, implementer} with non-empty strings", where))
		}
	}
	if strEq(kind, "decision_agent_review") {
		for _, key := range []string{"basis", "stands_for"} {
			if !r.Has(key) {
				f = append(f, finding("6.2:"+key, "%s is a decision_agent_review without %s", where, key))
			}
		}
	}
	if v, ok := r.Get("basis"); ok {
		l, isList := v.([]any)
		if !(isStr(v) || (isStrList(v) && isList && len(l) > 0)) {
			f = append(f, finding("6.2:basis", "%s basis is not a non-empty string or list of strings (reading)", where))
		}
	}
	if v, ok := r.Get("stands_for"); ok && !isStr(v) {
		f = append(f, finding("6.2:stands_for", "%s stands_for is not a non-empty string", where))
	}
	return f
}

// ---------------------------------------------------------------------------------------------------------------
// check_decision and the execution keys

func isProfile(v any) bool {
	l, ok := v.([]any)
	if !ok {
		return false
	}
	for _, item := range l {
		o, ok := item.(*Obj)
		if !ok || !o.keysAre(profileKeys...) {
			return false
		}
	}
	return true
}

// decisionFindings is records.check_decision for a payload that is an object and a type of DECISION_TYPES (its only
// caller, check_payload, gives no other).
func decisionFindings(eventType string, payload *Obj, where string) []string {
	acceptance := eventType == "decision.acceptance"
	extra := []string{"decision", "error"}
	if acceptance {
		extra = append(extra, acceptanceKeys...)
	} else {
		extra = append(extra, executionKeys...)
	}
	viewed := payload
	if !acceptance && payload.Has("intent_versions") {
		viewed = newObj()
		for _, k := range payload.keys {
			if k != "intent_versions" {
				viewed.Set(k, payload.vals[k])
			}
		}
	}
	f := recordFindings(viewed, extra, where, "6.4")
	if !acceptance {
		f = append(f, executionFindings(payload, where)...)
	}
	decision, has := payload.Get("decision")
	if !has {
		return append(f, finding("6.4:decision", "%s lacks decision", where))
	}
	errV, hasError := payload.Get("error")
	if (decision == nil) != hasError {
		f = append(f, finding("6.4:error", "%s decision must be null exactly when error is present", where))
	}
	if hasError && !isStr(errV) {
		f = append(f, finding("6.4:error", "%s error is not a non-empty string (reading)", where))
	}
	allowed, name := executionDecisions, "execution"
	if acceptance {
		allowed, name = acceptanceDecisions, "acceptance"
	}
	if decision != nil && !in(allowed, decision) {
		f = append(f, finding("6.4:decision", "%s decision %s is not one of the %d %s values", where, pyRepr(decision),
			len(allowed), name))
	}
	if subject, ok := payload.Get("subject"); ok && isStr(subject) && !matches(reTask, subject) {
		f = append(f, finding("6.4:subject", "%s subject is not a task id (reading: TASK- followed by digits)", where))
	}
	if acceptance {
		if v, ok := payload.Get("task_content_hash"); ok && !matches(reHex64, v) {
			f = append(f, finding("6.4:task_content_hash", "%s task_content_hash is not 64 lowercase hex digits", where))
		}
		if v, ok := payload.Get("evaluated_commit"); ok && !matches(reCommit, v) {
			f = append(f, finding("6.4:evaluated_commit", "%s evaluated_commit is not a full lowercase hex commit id", where))
		}
		if v, ok := payload.Get("fact_kind"); ok && !strEq(v, "interpretation") {
			f = append(f, finding("6.4:fact_kind", "%s fact_kind is not interpretation", where))
		}
		if v, ok := payload.Get("next_task_state"); ok && !in(stateNames, v) {
			f = append(f, finding("6.4:next_task_state", "%s next_task_state is not a state name of section 2", where))
		}
		if v, ok := payload.Get("profile_used"); ok && !isProfile(v) {
			f = append(f, finding("6.4:profile_used", "%s profile_used is not a list of objects with exactly "+
				"dimension, required, satisfied_by and missing_types", where))
		}
	}
	return f
}

// isChecks is records._is_checks.
func isChecks(v any) bool {
	l, ok := v.([]any)
	if !ok || len(l) != 8 {
		return false
	}
	seen := map[int64]bool{}
	for _, item := range l {
		o, ok := item.(*Obj)
		if !ok || !o.keysAre(checkKeys...) {
			return false
		}
		c := o.Val("check")
		if !isInt(c, one) || c.(*big.Int).Cmp(big.NewInt(8)) > 0 || !in(checkStatuses, o.Val("status")) {
			return false
		}
		if strEq(o.Val("status"), "fired") {
			if !in(executionDecisions, o.Val("outcome")) {
				return false
			}
		} else if o.Val("outcome") != nil {
			return false
		}
		if _, ok := o.Val("detail").(string); !ok {
			return false
		}
		n := c.(*big.Int).Int64()
		if seen[n] {
			return false // sorted(seen) == [1..8] with eight items holds only when none repeats
		}
		seen[n] = true
	}
	return len(seen) == 8
}

func orderIndex(s string) int {
	for i, x := range executionOrder {
		if x == s {
			return i
		}
	}
	return -1
}

// firedOK is the first condition on outcomes_fired: a list of fired values without repeats in section 7's order.
func firedOK(v any) ([]any, bool) {
	l, ok := v.([]any)
	if !ok {
		return nil, false
	}
	for _, x := range l {
		if !in(executionOrder, x) {
			return nil, false
		}
	}
	for i := 1; i < len(l); i++ {
		// No repeats and sorted by the order's index: each index strictly greater than the one before.
		if orderIndex(l[i].(string)) <= orderIndex(l[i-1].(string)) {
			return nil, false
		}
	}
	return l, true
}

// executionFindings is records._check_execution_keys.
func executionFindings(payload *Obj, where string) []string {
	var f []string
	bad := func(key, text string) {
		f = append(f, finding("6.4:"+key, "%s %s is not %s", where, key, text))
	}
	for _, key := range []string{"base_commit", "head_commit"} {
		if v, ok := payload.Get(key); ok && !matches(reCommit, v) {
			bad(key, "a full lowercase hex commit id")
		}
	}
	if v, ok := payload.Get("log_seq"); ok && !isInt(v, zero) {
		bad("log_seq", "an integer at least 0")
	}
	if v, ok := payload.Get("contract_hash"); ok && !matches(reHex64, v) {
		bad("contract_hash", "64 lowercase hex digits")
	}
	if v, ok := payload.Get("contract_version"); ok && !matches(reVersion, v) {
		bad("contract_version", "v followed by digits")
	}
	if v, ok := payload.Get("engine_identity"); ok {
		ident, isObj := v.(*Obj)
		if !(isObj && ident.keysAre("code_sha256", "python") &&
			(ident.Val("code_sha256") == nil || matches(reHex64, ident.Val("code_sha256"))) &&
			matches(rePython, ident.Val("python"))) {
			bad("engine_identity", "an object with exactly code_sha256 (null or 64 lowercase hex digits) and python "+
				"(X.Y.Z)")
		}
	}
	if v, ok := payload.Get("checks"); ok && !isChecks(v) {
		bad("checks", "eight objects with exactly check (1 to 8, each once), status, outcome and detail")
	}
	if v, ok := payload.Get("outcomes_fired"); ok {
		fired, good := firedOK(v)
		if !good {
			bad("outcomes_fired", "a list of fired execution values without repeats in the order of section 7")
		} else if decision := payload.Val("decision"); decision != nil {
			want := "CONTINUE"
			if len(fired) > 0 {
				want = fired[0].(string)
			}
			if !strEq(decision, want) {
				bad("outcomes_fired", "a list whose first value is the decision (CONTINUE when it is empty)")
			}
		}
	}
	if v, ok := payload.Get("policy_version"); ok && !(v == nil || isStr(v)) {
		bad("policy_version", "a non-empty string or null")
	}
	if v, ok := payload.Get("intent_versions"); ok && !isIntentVersions(v) && !isEntryVersions(v) {
		bad("intent_versions", "in the record form or an object mapping each entry to exactly {contract, current} "+
			"(reading)")
	}
	for _, key := range executionLists {
		if v, ok := payload.Get(key); ok {
			if _, isList := v.([]any); !isList {
				bad(key, "a list")
			}
		}
	}
	for _, key := range executionObjects {
		if v, ok := payload.Get(key); ok {
			if _, isObj := v.(*Obj); !isObj {
				bad(key, "an object")
			}
		}
	}
	return f
}

// isEntryVersions is the second form of a decision.execution's intent_versions: each entry {contract, current}.
func isEntryVersions(v any) bool {
	o, ok := v.(*Obj)
	if !ok {
		return false
	}
	for _, k := range o.keys {
		e, ok := o.vals[k].(*Obj)
		if !isStr(k) || !ok || !e.keysAre("contract", "current") {
			return false
		}
		for _, x := range e.keys {
			if e.vals[x] != nil && !isStr(e.vals[x]) {
				return false
			}
		}
	}
	return true
}

// ---------------------------------------------------------------------------------------------------------------
// check_payload, the fence and the task_id

// payloadFindings is records.check_payload(event_type, payload, where).
func payloadFindings(eventType, payload any, where string) []string {
	if !eventTypeIn(eventTypes, eventType) {
		return []string{finding("6.3:type", "%s is not an event type of section 6.3", pyRepr(eventType))}
	}
	t := eventType.(string)
	p, ok := payload.(*Obj)
	if !ok {
		return []string{finding("6.1:payload", "%s is not a JSON object", where)}
	}
	if in(decisionTypes, t) {
		return decisionFindings(t, p, where)
	}
	if t == "record.added" {
		return recordFindings(p, nil, where, "6.2")
	}
	if t == "violation.detected" {
		f := recordFindings(p, nil, where, "6.2")
		for _, kw := range [][2]string{{"fact_kind", "observation"}, {"outcome", "blocking"}, {"blocking_kind", "violation"}} {
			if !strEq(p.Val(kw[0]), kw[1]) {
				f = append(f, finding("6.3:violation", "%s %s is not %s", where, kw[0], kw[1]))
			}
		}
		return f
	}
	if t == "conflict.detected" {
		forms := map[string]formTest{"tasks": listForm}
		for _, key := range []string{"paths", "interfaces"} {
			if p.Has(key) {
				forms[key] = listForm
			}
		}
		f := keysAndForms(p, forms, "6.3", where)
		if !p.Has("paths") && !p.Has("interfaces") {
			f = append(f, finding("6.3:missing_key", "%s has neither paths nor interfaces", where))
		}
		return f
	}
	return keysAndForms(p, payloadForms[t], "6.3", where)
}

// fenceFindings is records._check_fence(obj, event_type), the object's fencing_token given as (has, token).
func fenceFindings(has bool, t any, eventType any) []string {
	if !has {
		if strEq(eventType, "task.submitted") {
			return []string{finding("6.1:fencing_token", "task.submitted lacks fencing_token")}
		}
		return nil
	}
	o, isObj := t.(*Obj)
	ok := isObj && o.keysAre("epoch", "counter") && isInt(o.Val("counter"), zero) &&
		(isStr(o.Val("epoch")) || isInt(o.Val("epoch"), zero))
	if !ok {
		return []string{finding("6.1:fencing_token", "fencing_token is not {epoch, counter} with counter an integer of "+
			"0 or more and epoch a non-empty string or an integer of 0 or more (reading)")}
	}
	return nil
}

// taskIDFindings is records._check_task_id for a known event type.
func taskIDFindings(obj *Obj, eventType string, payload any) []string {
	var f []string
	taskID, has := obj.Get("task_id")
	if has && !matches(reTask, taskID) {
		f = append(f, finding("6.1:task_id", "task_id is not TASK- followed by digits (reading)"))
	}
	var subject any
	if p, ok := payload.(*Obj); ok && in(recordPayloadTypes, eventType) {
		subject = p.Val("subject")
	}
	subjectIsTask := matches(reTask, subject)
	needed := strings.HasPrefix(eventType, "task.") || strings.HasPrefix(eventType, "decision.") || subjectIsTask
	if needed && !has {
		f = append(f, finding("6.1:task_id", "%s lacks task_id", eventType))
	}
	if has && subjectIsTask && !pyEq(taskID, subject) {
		f = append(f, finding("6.1:task_id", "task_id differs from the record subject %s", pyRepr(subject)))
	}
	if has && (eventType == "record.added" || eventType == "violation.detected") && isStr(subject) && !subjectIsTask {
		f = append(f, finding("6.1:task_id", "a record about an intent entity carries task_id (reading)"))
	}
	return f
}

// ---------------------------------------------------------------------------------------------------------------
// check_log

// lineReport is records.LineReport: event is nil when the line has a finding; duplicateOf is 0 for None.
type lineReport struct {
	number      int
	event       *Obj
	findings    []string
	duplicateOf int
}

// logReport is records.LogReport.
type logReport struct {
	textFindings []string
	lines        []lineReport
}

// findings is LogReport.findings() as the texts str(f), in its order.
func (r logReport) findings() []string {
	out := append([]string(nil), r.textFindings...)
	for _, l := range r.lines {
		out = append(out, l.findings...)
	}
	return out
}

type firstLine struct {
	number int
	key    string
}

type logState struct {
	previousSeq *big.Int // nil for None
	firstLine   map[string]firstLine
}

// intText is records._int_text.
func intText(n *big.Int) string {
	if n.BitLen() <= 64 {
		return n.String()
	}
	return fmt.Sprintf("an integer of %d bits", n.BitLen())
}

func checkSeq(obj *Obj, number int, state *logState) []string {
	seqV, has := obj.Get("seq")
	var expected *big.Int
	if state.previousSeq == nil {
		expected = big.NewInt(int64(number))
	} else {
		expected = new(big.Int).Add(state.previousSeq, one)
	}
	seq, isInteger := seqV.(*big.Int)
	if isInteger {
		state.previousSeq = seq
	} else {
		state.previousSeq = nil
	}
	if !has {
		return nil
	}
	if !isInteger {
		return []string{finding("6.1:seq", "seq is not an integer")}
	}
	if seq.Cmp(expected) != 0 {
		return []string{finding("6.1:seq", "seq is %s; expected %s", intText(seq), intText(expected))}
	}
	return nil
}

// onlyJSONWhitespace is whether a line is empty or JSON whitespace only, where json.loads says "Expecting value".
func onlyJSONWhitespace(raw []byte) bool {
	for _, c := range raw {
		if c != ' ' && c != '\t' && c != '\r' && c != '\n' {
			return false
		}
	}
	return true
}

func checkLine(number int, raw []byte, state *logState) lineReport {
	if onlyJSONWhitespace(raw) {
		// json.loads: JSONDecodeError("Expecting value", s, len(s)); the line holds no LF.
		state.previousSeq = nil
		return lineReport{number: number, findings: []string{finding("6.1:json",
			"the line is not one JSON object (Expecting value: line 1 column %d (char %d))", len(raw)+1, len(raw))}}
	}
	value, err := parseJSON(raw)
	if err != nil {
		// The Python's finding holds the text of a UnicodeDecodeError's reason or of json's own error, which the port
		// does not reproduce (a stated limit): fail closed.
		failClosed("a log line that is not one JSON value: %v", err)
	}
	obj, ok := value.(*Obj)
	if !ok {
		// "the line is a JSON <type>, not an object" names a Python type (the brief's section 6.3): fail closed.
		failClosed("a log line that is a JSON value but not an object")
	}
	var f []string
	for _, key := range envelopeRequired {
		if !obj.Has(key) {
			f = append(f, finding("6.1:missing_key", "the line lacks %s", pyStrRepr(key)))
		}
	}
	for _, key := range sortedKeysNotIn(obj, envelopeKeys) {
		f = append(f, finding("2:unknown_key", "the line has the key %s, which section 6.1 does not name", pyStrRepr(key)))
	}
	eventID := obj.Val("event_id")
	if obj.Has("event_id") && !isStr(eventID) {
		f = append(f, finding("6.1:event_id", "event_id is not a non-empty string"))
	}
	eventType := obj.Val("type")
	knownType := in(eventTypes, eventType)
	if obj.Has("type") && !knownType {
		f = append(f, finding("6.1:type", "type is not an event type of section 6.3"))
	}
	payload := obj.Val("payload")
	if _, isObj := payload.(*Obj); obj.Has("payload") && !isObj {
		f = append(f, finding("6.1:payload", "payload is not a JSON object"))
	}
	f = append(f, checkSeq(obj, number, state)...)
	if v, ok := obj.Get("appended_at"); ok && !isTime(v) {
		f = append(f, finding("6.1:appended_at", "appended_at is not a UTC time YYYY-MM-DDTHH:MM:SS[.fraction]Z "+
			"that exists on the calendar"))
	}
	duplicateOf := 0
	without := newObj()
	for _, k := range obj.keys {
		if k != "seq" && k != "appended_at" {
			without.Set(k, obj.vals[k])
		}
	}
	key := sameText(without)
	id, idIsStr := eventID.(string)
	idIsStr = idIsStr && id != ""
	if idIsStr {
		if first, seen := state.firstLine[id]; seen {
			if key == first.key {
				duplicateOf = first.number
			} else {
				f = append(f, finding("6.1:duplicate_event_id", "event_id %s is on line %d with other content "+
					"(reading: only an identical repeat is an ignored duplicate)", pyStrRepr(id), first.number))
			}
		}
	}
	tokenV, hasToken := obj.Get("fencing_token")
	if knownType {
		f = append(f, taskIDFindings(obj, eventType.(string), payload)...)
		f = append(f, fenceFindings(hasToken, tokenV, eventType)...)
	} else if hasToken {
		f = append(f, fenceFindings(true, tokenV, nil)...)
	}
	if corrects, ok := obj.Get("corrects"); ok {
		c, isS := corrects.(string)
		if _, known := state.firstLine[c]; !(isS && c != "" && known) {
			f = append(f, finding("6.1:corrects", "corrects is not the event_id of an earlier line (reading)"))
		}
	}
	if _, isObj := payload.(*Obj); knownType && isObj {
		f = append(f, payloadFindings(eventType, payload, "payload")...)
	}
	if idIsStr {
		if _, seen := state.firstLine[id]; !seen {
			state.firstLine[id] = firstLine{number, key}
		}
	}
	rep := lineReport{number: number, findings: f, duplicateOf: duplicateOf}
	if len(f) == 0 {
		rep.event = obj
	}
	return rep
}

// checkLog is records.check_log for bytes.
func checkLog(raw []byte) logReport {
	var text []string
	if bytes.HasPrefix(raw, bom) {
		text = append(text, finding("2:bom", "the text starts with a byte-order mark"))
	}
	if bytes.IndexByte(raw, '\r') >= 0 {
		text = append(text, finding("2:cr", "the text holds a CR byte; line ends are LF only"))
	}
	parts := bytes.Split(raw, []byte{'\n'})
	if len(parts[len(parts)-1]) == 0 {
		parts = parts[:len(parts)-1]
	}
	state := &logState{firstLine: map[string]firstLine{}}
	lines := make([]lineReport, 0, len(parts))
	for n, part := range parts {
		lines = append(lines, checkLine(n+1, part, state))
	}
	return logReport{textFindings: text, lines: lines}
}
