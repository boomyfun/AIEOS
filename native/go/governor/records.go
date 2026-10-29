package main

// The record forms of records.py that the governor uses: check_record (with check_audit_copy, check_read_set,
// check_session_claim and their helpers), the state names and the blocking kinds, as records.py holds them at the
// contract's commit (TASK-100 AC4). Only the rule of each finding is kept, in records.py's order, since the governor
// reads only the rule of the first finding.

import (
	"regexp"
	"sort"
)

var (
	reHex64   = regexp.MustCompile(`^[0-9a-f]{64}$`)
	reCommit  = regexp.MustCompile(`^(?:[0-9a-f]{40}|[0-9a-f]{64})$`)
	reTask    = regexp.MustCompile(`^TASK-[0-9]+$`)
	reVersion = regexp.MustCompile(`^v[0-9]+$`)
	reGate    = regexp.MustCompile(`^G[0-9]+$`)
	reIntent  = regexp.MustCompile(`^INT-[0-9]+$`)
)

var (
	stateNames = []string{"DRAFT", "READY", "IN_PROGRESS", "VERIFYING", "ACCEPTED", "DONE", "IN_REVIEW", "REWORK",
		"ESCALATED", "REJECTED", "BLOCKED", "STALE"}
	factKinds     = []string{"claim", "observation", "interpretation", "authority"}
	sourceClasses = []string{"agent_declared", "same_lineage_review", "deterministic_tool_local",
		"deterministic_tool_external_ci", "cross_vendor_review", "decision_agent", "human_authority", "delegate_ai"}
	outcomes       = []string{"pass", "fail", "blocking"}
	blockingKinds  = []string{"out_of_scope", "forbidden_path", "violation", "constitution", "other"}
	bindingKinds   = []string{"contract", "acceptance", "change_request", "baseline"}
	recordRequired = []string{"record_id", "fact_kind", "source_class", "recorder", "subject"}
	recordKeys     = append(append([]string(nil), recordRequired...), "evidence_type", "dimension", "gate", "outcome",
		"blocking_kind", "commit", "intent_versions", "approval_binding", "decision_ref", "models", "basis",
		"stands_for", "refers_to", "risk_class", "evidence_profile", "read_paths", "session", "acs", "text")
	auditCopyTypes     = []string{"risk_class", "evidence_profile"}
	auditCopySources   = []string{"deterministic_tool_local", "deterministic_tool_external_ci"}
	auditCopyForbidden = []string{"outcome", "gate", "blocking_kind", "dimension"}
	riskClasses        = []string{"low", "medium", "high", "critical"}
	readSetType        = "observed_read_set"
	readSetForbidden   = []string{"session", "outcome", "gate", "blocking_kind", "dimension", "commit", "intent_versions"}
)

// isStr is records._is_str (and governor._text: every Go string is valid UTF-8): a non-empty string.
func isStr(v any) bool {
	s, ok := v.(string)
	return ok && s != ""
}

// isStrList is records._is_str_list: a list of non-empty strings.
func isStrList(v any) bool {
	l, ok := v.([]any)
	if !ok {
		return false
	}
	for _, x := range l {
		if !isStr(x) {
			return false
		}
	}
	return true
}

// matches is records._matches: a string that the pattern matches in full.
func matches(re *regexp.Regexp, v any) bool {
	s, ok := v.(string)
	return ok && re.MatchString(s)
}

// in is records._in (and "v in tuple" for a tuple of strings): a string that is one of the values.
func in(values []string, v any) bool {
	s, ok := v.(string)
	if !ok {
		return false
	}
	for _, x := range values {
		if x == s {
			return true
		}
	}
	return false
}

func strEq(v any, s string) bool {
	x, ok := v.(string)
	return ok && x == s
}

func isIntentVersions(v any) bool {
	o, ok := v.(*Obj)
	if !ok {
		return false
	}
	for _, k := range o.keys {
		if !isStr(k) || !matches(reVersion, o.vals[k]) {
			return false
		}
	}
	return true
}

// checkRecord is records.check_record(record) with its defaults: the rules of its findings, in its order.
func checkRecord(record any) []string {
	r, ok := record.(*Obj)
	if !ok {
		return []string{"6.2:record"}
	}
	var f []string
	var unknown []string
	for _, k := range r.keys {
		if !in(recordKeys, k) {
			unknown = append(unknown, k)
		}
	}
	sort.Strings(unknown)
	for range unknown {
		f = append(f, "6.2:unknown_key")
	}
	for _, k := range recordRequired {
		if !r.Has(k) {
			f = append(f, "6.2:missing_key")
		}
	}
	for _, k := range []string{"record_id", "recorder", "subject"} {
		if v, ok := r.Get(k); ok && !isStr(v) {
			f = append(f, "6.2:"+k)
		}
	}
	if v, ok := r.Get("fact_kind"); ok && !in(factKinds, v) {
		f = append(f, "6.2:fact_kind")
	}
	if v, ok := r.Get("source_class"); ok && !in(sourceClasses, v) {
		f = append(f, "6.2:source_class")
	}
	f = append(f, checkOutcome(r)...)
	if v, ok := r.Get("commit"); ok && !matches(reCommit, v) {
		f = append(f, "6.2:commit")
	}
	if v, ok := r.Get("intent_versions"); ok && !isIntentVersions(v) {
		f = append(f, "6.2:intent_versions")
	}
	f = append(f, checkBinding(r)...)
	f = append(f, checkReviewFields(r)...)
	if v, ok := r.Get("gate"); ok && !matches(reGate, v) {
		f = append(f, "6.2:gate")
	}
	for _, k := range []string{"evidence_type", "dimension", "refers_to"} {
		if v, ok := r.Get(k); ok && !isStr(v) {
			f = append(f, "6.2:"+k)
		}
	}
	f = append(f, checkAuditCopy(r)...)
	f = append(f, checkReadSet(r)...)
	f = append(f, checkSessionClaim(r)...)
	return f
}

func isAuditValue(kind string, v any) bool {
	if v == nil {
		return true
	}
	if kind == "risk_class" {
		return in(riskClasses, v)
	}
	l, ok := v.([]any)
	if !ok {
		return false
	}
	for _, e := range l {
		o, ok := e.(*Obj)
		if !ok || !o.keysAre("dimension", "evidence_types") || !isStr(o.Val("dimension")) ||
			!isStrList(o.Val("evidence_types")) {
			return false
		}
	}
	return true
}

func checkAuditCopy(r *Obj) []string {
	var f []string
	kindV := r.Val("evidence_type")
	if !in(auditCopyTypes, kindV) {
		for _, k := range auditCopyTypes {
			if r.Has(k) {
				f = append(f, "6.2:audit_copy_key")
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
		f = append(f, "6.2:audit_copy_fact_kind")
	}
	if !in(auditCopySources, r.Val("source_class")) {
		f = append(f, "6.2:audit_copy_source_class")
	}
	if v, ok := r.Get(kind); !ok {
		f = append(f, "6.2:audit_copy_key")
	} else if !isAuditValue(kind, v) {
		f = append(f, "6.2:audit_copy_value")
	}
	if r.Has(other) {
		f = append(f, "6.2:audit_copy_key")
	}
	for _, k := range []string{"commit", "intent_versions"} {
		if !r.Has(k) {
			f = append(f, "6.2:audit_copy_binding")
		}
	}
	for _, k := range auditCopyForbidden {
		if r.Has(k) {
			f = append(f, "6.2:audit_copy_forbidden")
		}
	}
	return f
}

func checkOutcome(r *Obj) []string {
	var f []string
	outcome, has := r.Get("outcome")
	if has && !in(outcomes, outcome) {
		f = append(f, "6.2:outcome")
	}
	blocking := strEq(outcome, "blocking")
	if blocking && !r.Has("blocking_kind") {
		f = append(f, "6.2:blocking_kind")
	}
	if !blocking && r.Has("blocking_kind") {
		f = append(f, "6.2:blocking_kind")
	}
	if v, ok := r.Get("blocking_kind"); ok && !in(blockingKinds, v) {
		f = append(f, "6.2:blocking_kind")
	}
	return f
}

func checkBinding(r *Obj) []string {
	bv, ok := r.Get("approval_binding")
	if !ok {
		if strEq(r.Val("fact_kind"), "authority") {
			return []string{"6.2:approval_binding"}
		}
		return nil
	}
	b, ok := bv.(*Obj)
	if !(ok && b.keysAre("kind", "hash") && in(bindingKinds, b.Val("kind")) && matches(reHex64, b.Val("hash"))) {
		return []string{"6.2:approval_binding"}
	}
	return nil
}

func checkReviewFields(r *Obj) []string {
	var f []string
	kind := r.Val("evidence_type")
	needsRef := strEq(r.Val("source_class"), "decision_agent") || strEq(kind, "other_model_review")
	if needsRef && !r.Has("decision_ref") {
		f = append(f, "6.2:decision_ref")
	}
	if v, ok := r.Get("decision_ref"); ok && !isStr(v) {
		f = append(f, "6.2:decision_ref")
	}
	if strEq(kind, "other_model_review") && !r.Has("models") {
		f = append(f, "6.2:models")
	}
	if v, ok := r.Get("models"); ok {
		m, isObj := v.(*Obj)
		if !(isObj && m.keysAre("reviewer", "implementer") && isStr(m.Val("reviewer")) && isStr(m.Val("implementer"))) {
			f = append(f, "6.2:models")
		}
	}
	if strEq(kind, "decision_agent_review") {
		for _, k := range []string{"basis", "stands_for"} {
			if !r.Has(k) {
				f = append(f, "6.2:"+k)
			}
		}
	}
	if v, ok := r.Get("basis"); ok {
		l, isList := v.([]any)
		if !(isStr(v) || (isStrList(v) && isList && len(l) > 0)) {
			f = append(f, "6.2:basis")
		}
	}
	if v, ok := r.Get("stands_for"); ok && !isStr(v) {
		f = append(f, "6.2:stands_for")
	}
	return f
}

// isReadPaths is records._is_read_paths: a list of distinct non-empty strings.
func isReadPaths(v any) bool {
	if !isStrList(v) {
		return false
	}
	seen := map[string]bool{}
	for _, x := range v.([]any) {
		s := x.(string)
		if seen[s] {
			return false
		}
		seen[s] = true
	}
	return true
}

// checkReadSet is records.check_read_set (TASK-064): the rules of its findings, in its order.
func checkReadSet(r *Obj) []string {
	var f []string
	if !strEq(r.Val("evidence_type"), readSetType) {
		if r.Has("read_paths") {
			f = append(f, "6.2:read_set_key")
		}
		return f
	}
	if !strEq(r.Val("fact_kind"), "observation") {
		f = append(f, "6.2:read_set_fact_kind")
	}
	if !strEq(r.Val("source_class"), "deterministic_tool_local") {
		f = append(f, "6.2:read_set_source_class")
	}
	if !matches(reTask, r.Val("subject")) {
		f = append(f, "6.2:read_set_subject")
	}
	if v, ok := r.Get("read_paths"); !ok {
		f = append(f, "6.2:read_set_key")
	} else if !isReadPaths(v) {
		f = append(f, "6.2:read_set_value")
	}
	for _, k := range readSetForbidden {
		if r.Has(k) {
			f = append(f, "6.2:read_set_forbidden")
		}
	}
	return f
}

// isEditClaim is records._is_edit_claim (TASK-096): a contract edit's claim with no session.
func isEditClaim(r *Obj) bool {
	return strEq(r.Val("fact_kind"), "claim") && strEq(r.Val("evidence_type"), "contract_edit") &&
		matches(reTask, r.Val("subject")) && !r.Has("session")
}

// isIntentClaim is records._is_intent_claim (TASK-098): an intent's claim with no session.
func isIntentClaim(r *Obj) bool {
	return strEq(r.Val("fact_kind"), "claim") && strEq(r.Val("evidence_type"), "intent") &&
		matches(reIntent, r.Val("subject")) && !r.Has("session")
}

// checkSessionClaim is records.check_session_claim (TASK-077): the rules of its findings, in its order.
func checkSessionClaim(r *Obj) []string {
	var f []string
	if v, ok := r.Get("session"); ok && !isStr(v) {
		f = append(f, "6.2:session")
	}
	sessionClaim := strEq(r.Val("fact_kind"), "claim") && isStr(r.Val("session"))
	if v, ok := r.Get("text"); ok {
		if !isStr(v) {
			f = append(f, "6.2:text")
		} else if !(sessionClaim || isEditClaim(r) || isIntentClaim(r)) {
			f = append(f, "6.2:text")
		}
	}
	if v, ok := r.Get("acs"); ok {
		l, _ := v.([]any)
		if !isReadPaths(v) || len(l) == 0 {
			f = append(f, "6.2:acs")
		} else if sessionClaim {
			if len(l) != 1 {
				f = append(f, "6.2:acs")
			}
		} else if !r.Has("gate") {
			f = append(f, "6.2:acs")
		}
	}
	return f
}
