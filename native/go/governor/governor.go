package main

// The governor's acceptance decision: governor.evaluate and every function it calls.

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"math/big"
	"sort"
	"strings"
)

const (
	govModulePath  = "src/aieos_bootstrap/governor.py"
	govSourceClass = "deterministic_tool_local"
	govCI          = "deterministic_tool_external_ci"
	aiReview       = "ai_review"
	crossModel     = "ai_review (cross-model)"
	// The self-build runs at L1 (A35); row 4 needs L2 or above, so it never applies.
	levelAtLeastL2 = false
)

var (
	govRisks          = []string{"low", "medium", "high", "critical"}
	evaluatedStates   = []string{"VERIFYING", "IN_REVIEW"}
	humanTypes        = []string{"human_review", "human_security_review"}
	reviewRecordTypes = []string{"other_model_review", "decision_agent_review"}
	row1Kinds         = []string{"out_of_scope", "forbidden_path", "violation"}
	govRequestKeys    = []string{"task_id", "task_content_hash", "evaluated_commit", "intent_versions", "task_state",
		"changed_paths", "retry_count"}
	govInputKeys = []string{"traces_to", "risk", "owner_kept_act", "weakens_evidence", "delegation_in_force",
		"auto_accept", "verification_plan", "evidence_profile", "applicable_articles", "policy_version",
		"level_version", "ruleset_version"}
	govNotes = []string{
		"advisory: decisions of this governor are advisory (governor-spec.md section 10)",
		"inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository",
		"identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this " +
			"module's defaults, not the channel or the identity that specification 2 section 6.4 names",
	}
)

// errNoTaskID is evaluate's ValueError: no record can name the subject, so the case cannot be computed.
var errNoTaskID = errors.New("the request has no task id of the form TASK-<digits>")

func isCount(v any) bool {
	n, ok := v.(*big.Int)
	return ok && n.Sign() >= 0
}

func contains(list []string, s string) bool {
	for _, x := range list {
		if x == s {
			return true
		}
	}
	return false
}

func sortedSet(items []string) []string {
	seen := map[string]bool{}
	out := []string{}
	for _, s := range items {
		if !seen[s] {
			seen[s] = true
			out = append(out, s)
		}
	}
	sort.Strings(out)
	return out
}

func sha256Hex(s string) string {
	h := sha256.Sum256([]byte(s))
	return hex.EncodeToString(h[:])
}

// govRecordID is governor._record_id: "decision-" and the SHA-256 of the canonical text of the record without
// record_id, with its final LF.
func govRecordID(rec map[string]any) (string, error) {
	without := map[string]any{}
	for k, v := range rec {
		if k != "record_id" {
			without[k] = v
		}
	}
	text, err := canonString(without)
	if err != nil {
		return "", err
	}
	return "decision-" + sha256Hex(text+"\n"), nil
}

// ---------------------------------------------------------------------------------------------------------------
// Input checks

func govRequestErrors(req *Obj) []string {
	if !req.keysAre(govRequestKeys...) {
		return []string{"the request is not exactly the keys of specification 2 section 6.5"}
	}
	var errs []string
	if !matches(reHex64, req.Val("task_content_hash")) {
		errs = append(errs, "task_content_hash")
	}
	if !matches(reCommit, req.Val("evaluated_commit")) {
		errs = append(errs, "evaluated_commit")
	}
	if !isIntentVersions(req.Val("intent_versions")) {
		errs = append(errs, "intent_versions")
	}
	if !in(evaluatedStates, req.Val("task_state")) {
		errs = append(errs, "task_state")
	}
	if !isStrList(req.Val("changed_paths")) {
		errs = append(errs, "changed_paths")
	}
	rc, ok := req.Val("retry_count").(*Obj)
	if !(ok && rc.keysAre("used", "limit") && isCount(rc.Val("used")) && isCount(rc.Val("limit"))) {
		errs = append(errs, "retry_count")
	}
	out := []string{}
	for _, e := range errs {
		out = append(out, "the request's "+e+" is malformed")
	}
	return out
}

func profileForm(v any) bool {
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

func articlesForm(v any) bool {
	l, ok := v.([]any)
	if !ok {
		return false
	}
	for _, e := range l {
		o, ok := e.(*Obj)
		if !ok || !o.keysAre("id", "evidence_required") || !isStr(o.Val("id")) ||
			!isStrList(o.Val("evidence_required")) {
			return false
		}
	}
	return true
}

func govInputsErrors(inputs any) []string {
	inp, ok := inputs.(*Obj)
	if !ok || !inp.keysAre(govInputKeys...) {
		return []string{"the inputs are not exactly the keys of conformance-files.md section 4"}
	}
	var errs []string
	if !isStrList(inp.Val("traces_to")) {
		errs = append(errs, "traces_to")
	}
	if !in(govRisks, inp.Val("risk")) {
		errs = append(errs, "risk")
	}
	for _, k := range []string{"owner_kept_act", "weakens_evidence", "delegation_in_force", "auto_accept"} {
		if _, ok := inp.Val(k).(bool); !ok {
			errs = append(errs, k)
		}
	}
	plan := inp.Val("verification_plan")
	planOK := isStrList(plan)
	if planOK {
		for _, g := range plan.([]any) {
			if !matches(reGate, g) {
				planOK = false
			}
		}
	}
	if !planOK {
		errs = append(errs, "verification_plan")
	}
	if !profileForm(inp.Val("evidence_profile")) {
		errs = append(errs, "evidence_profile")
	}
	if !articlesForm(inp.Val("applicable_articles")) {
		errs = append(errs, "applicable_articles")
	}
	for _, k := range []string{"policy_version", "level_version", "ruleset_version"} {
		if !isStr(inp.Val(k)) {
			errs = append(errs, k)
		}
	}
	out := []string{}
	for _, e := range errs {
		out = append(out, "the inputs' "+e+" is malformed")
	}
	return out
}

func govRecordsErrors(records any) []string {
	recs, ok := records.([]any)
	if !ok {
		return []string{"the records are not a list"}
	}
	seen := map[string]bool{}
	errs := []string{}
	for _, r := range recs {
		var rid any
		if o, ok := r.(*Obj); ok {
			rid = o.Val("record_id")
		}
		if isStr(rid) {
			s := rid.(string)
			if seen[s] {
				errs = append(errs, fmt.Sprintf("the record id %s is used twice", s))
			}
			seen[s] = true
		}
	}
	return errs
}

// ---------------------------------------------------------------------------------------------------------------
// The decision record

func govBase(task string, inputs any) map[string]any {
	rec := map[string]any{
		"fact_kind":         "interpretation",
		"source_class":      govSourceClass,
		"recorder":          govModulePath,
		"subject":           task,
		"governor_identity": nil,
		"scenario_set_hash": nil,
	}
	inp, isObj := inputs.(*Obj)
	for _, k := range []string{"policy_version", "level_version", "ruleset_version"} {
		if isObj && isStr(inp.Val(k)) {
			rec[k] = inp.Val(k)
		} else {
			rec[k] = nil
		}
	}
	return rec
}

func notesList(extra []string) []any {
	out := []any{}
	for _, n := range govNotes {
		out = append(out, n)
	}
	for _, n := range extra {
		out = append(out, n)
	}
	return out
}

func govErrorRecord(task string, req *Obj, inputs any, msg string) (map[string]any, error) {
	rec := govBase(task, inputs)
	rec["decision"] = nil
	rec["error"] = msg
	rec["table_row"] = nil
	rec["profile_used"] = []any{}
	rec["missing_gates"] = []any{}
	rec["blocking"] = []any{}
	rec["failed_gates"] = []any{}
	rec["reverify"] = []any{}
	rec["approval_record"] = nil
	rec["uncovered"] = notesList(nil)
	rec["rests_on_ai"] = map[string]any{"entries": []any{}, "approval": false}
	if matches(reHex64, req.Val("task_content_hash")) {
		rec["task_content_hash"] = req.Val("task_content_hash")
	}
	if matches(reCommit, req.Val("evaluated_commit")) {
		rec["evaluated_commit"] = req.Val("evaluated_commit")
	}
	if isIntentVersions(req.Val("intent_versions")) {
		rec["intent_versions"] = req.Val("intent_versions")
	}
	if in(stateNames, req.Val("task_state")) {
		rec["next_task_state"] = req.Val("task_state")
	}
	id, err := govRecordID(rec)
	if err != nil {
		return nil, err
	}
	rec["record_id"] = id
	return rec, nil
}

// ---------------------------------------------------------------------------------------------------------------
// The profile

type dimTypes struct {
	dimension string
	types     []string
}

// govJoin is governor._join: the profile as (dimension, types) pairs in first-seen order, each type once.
func govJoin(profile, articles []any) []dimTypes {
	var out []dimTypes
	index := map[string]int{}
	add := func(dim string, types []any) {
		n, ok := index[dim]
		if !ok {
			n = len(out)
			index[dim] = n
			out = append(out, dimTypes{dimension: dim, types: []string{}})
		}
		for _, t := range types {
			s := t.(string)
			if !contains(out[n].types, s) {
				out[n].types = append(out[n].types, s)
			}
		}
	}
	for _, e := range profile {
		o := e.(*Obj)
		add(o.Val("dimension").(string), o.Val("evidence_types").([]any))
	}
	for _, a := range articles {
		o := a.(*Obj)
		add(o.Val("id").(string), o.Val("evidence_required").([]any))
	}
	return out
}

func reviewLike(kind string) bool {
	return strings.HasSuffix(kind, "review") || strings.HasPrefix(kind, aiReview)
}

func isWay2(r *Obj) bool {
	m, ok := r.Val("models").(*Obj)
	return strEq(r.Val("source_class"), "same_lineage_review") && strEq(r.Val("evidence_type"), "other_model_review") &&
		ok && !pyEq(m.Val("reviewer"), m.Val("implementer")) && isStr(r.Val("decision_ref"))
}

func isDAReview(r *Obj, standsFor string) bool {
	return strEq(r.Val("source_class"), "decision_agent") && strEq(r.Val("evidence_type"), "decision_agent_review") &&
		strEq(r.Val("stands_for"), standsFor) && r.Has("basis") && isStr(r.Val("decision_ref"))
}

type govInputs struct {
	risk                  string
	ownerKept, weakens    bool
	delegated, autoAccept bool
}

func candidate(r *Obj, kind string, gi govInputs) bool {
	cls, et := r.Val("source_class"), r.Val("evidence_type")
	if contains(humanTypes, kind) {
		if strEq(cls, "human_authority") && strEq(et, kind) {
			return true
		}
		return gi.delegated && !gi.ownerKept && isDAReview(r, kind)
	}
	if kind == aiReview {
		return gi.delegated && isWay2(r)
	}
	if reviewLike(kind) {
		return false
	}
	return strEq(cls, govCI) && strEq(et, kind)
}

func recID(r *Obj) string { return r.Val("record_id").(string) }

// entry is governor._entry: the satisfying record ids and the failed candidate ids of one entry.
func entry(dimension, kind string, current []*Obj, gi govInputs, reserved map[string]bool) ([]string, []string) {
	var rs []*Obj
	for _, r := range current {
		if strEq(r.Val("dimension"), dimension) {
			rs = append(rs, r)
		}
	}
	if kind == crossModel {
		if !(gi.delegated && (gi.risk == "high" || gi.risk == "critical")) {
			return nil, nil
		}
		var way2, da []*Obj
		for _, r := range rs {
			if isWay2(r) {
				way2 = append(way2, r)
			}
		}
		for _, r := range rs {
			if isDAReview(r, crossModel) {
				da = append(da, r)
			}
		}
		var failed, w, d []string
		for _, r := range append(append([]*Obj(nil), way2...), da...) {
			if strEq(r.Val("outcome"), "fail") {
				failed = append(failed, recID(r))
			}
		}
		for _, r := range way2 {
			if strEq(r.Val("outcome"), "pass") {
				w = append(w, recID(r))
			}
		}
		for _, r := range da {
			if strEq(r.Val("outcome"), "pass") {
				d = append(d, recID(r))
			}
		}
		sort.Strings(w)
		sort.Strings(d)
		if len(w) > 0 && len(d) > 0 {
			reserved[w[0]] = true
			return []string{w[0], d[0]}, failed
		}
		return nil, failed
	}
	var sat, failed []string
	for _, r := range rs {
		if !candidate(r, kind, gi) || reserved[recID(r)] {
			continue
		}
		if strEq(r.Val("outcome"), "pass") {
			sat = append(sat, recID(r))
		}
		if strEq(r.Val("outcome"), "fail") {
			failed = append(failed, recID(r))
		}
	}
	sort.Strings(sat)
	sort.Strings(failed)
	return sat, failed
}

// ---------------------------------------------------------------------------------------------------------------
// Records: subject, use, binding, blocking

type labelKind struct{ label, kind string }

func sortRecords(task string, req *Obj, recs []any) ([]labelKind, []*Obj, []*Obj, []string, []string) {
	var blocking []labelKind
	var approvals, current []*Obj
	var stale []string
	notes := []string{}
	commit := req.Val("evaluated_commit")
	versions := req.Val("intent_versions").(*Obj)
	for i, rv := range recs {
		n := i + 1
		r, isObj := rv.(*Obj)
		var rid any
		if isObj {
			rid = r.Val("record_id")
		}
		label := fmt.Sprintf("record %d", n)
		if isStr(rid) {
			label = rid.(string)
		}
		if isObj {
			if subj, ok := r.Val("subject").(string); ok && subj != "" && subj != task {
				notes = append(notes, label+": about another subject, not read")
				continue
			}
		}
		findings := checkRecord(rv)
		if isObj && strEq(r.Val("outcome"), "blocking") {
			kind := "other"
			if in(blockingKinds, r.Val("blocking_kind")) {
				kind = r.Val("blocking_kind").(string)
			}
			blocking = append(blocking, labelKind{label, kind})
			if len(findings) > 0 {
				notes = append(notes, label+": blocking, and not otherwise used: "+findings[0])
			}
			continue
		}
		if len(findings) > 0 {
			notes = append(notes, label+": not used: "+findings[0])
			continue
		}
		if !isStr(rid) {
			notes = append(notes, label+": not used: its record_id cannot be written")
			continue
		}
		if strEq(r.Val("fact_kind"), "authority") {
			approvals = append(approvals, r)
			continue
		}
		if !r.Has("evidence_type") && !r.Has("gate") {
			notes = append(notes, label+": not used: no evidence type or gate")
			continue
		}
		if !r.Has("commit") || !r.Has("intent_versions") {
			notes = append(notes, label+": not used: no commit binding")
			continue
		}
		isStale := !pyEq(r.Val("commit"), commit)
		if !isStale {
			iv := r.Val("intent_versions").(*Obj)
			for _, k := range iv.keys {
				if !pyEq(versions.Val(k), iv.vals[k]) {
					isStale = true
					break
				}
			}
		}
		if isStale {
			stale = append(stale, rid.(string))
			continue
		}
		if !strEq(r.Val("fact_kind"), "observation") {
			notes = append(notes, fmt.Sprintf("%s: not used: a %s, not an observation", label, r.Val("fact_kind").(string)))
			continue
		}
		current = append(current, r)
	}
	return blocking, approvals, current, sortedSet(stale), notes
}

type counted struct {
	rank int
	id   string
}

func approval(req *Obj, gi govInputs, approvals []*Obj, notes *[]string) (any, bool) {
	var cs []counted
	for _, r := range approvals {
		id := recID(r)
		b, ok := r.Val("approval_binding").(*Obj)
		if !(ok && strEq(b.Val("kind"), "acceptance") && pyEq(b.Val("hash"), req.Val("task_content_hash"))) {
			*notes = append(*notes, id+": an approval not bound to this task's content hash")
			continue
		}
		if o, has := r.Get("outcome"); has && !strEq(o, "pass") {
			*notes = append(*notes, id+": an authority record whose outcome is not pass is not an approval")
			continue
		}
		switch {
		case strEq(r.Val("source_class"), "human_authority"):
			cs = append(cs, counted{0, id})
		case strEq(r.Val("source_class"), "decision_agent"):
			if !gi.delegated {
				*notes = append(*notes, id+": a delegated approval while the delegation is not in force")
			} else if gi.ownerKept || gi.weakens {
				*notes = append(*notes, id+": a delegated approval where only the owner's counts")
			} else if isStr(r.Val("decision_ref")) {
				cs = append(cs, counted{1, id})
			}
		default:
			*notes = append(*notes, id+": an approval from a class that cannot approve")
		}
	}
	if len(cs) == 0 {
		return nil, false
	}
	sort.Slice(cs, func(i, j int) bool {
		if cs[i].rank != cs[j].rank {
			return cs[i].rank < cs[j].rank
		}
		return cs[i].id < cs[j].id
	})
	return cs[0].id, cs[0].rank == 1
}

// ---------------------------------------------------------------------------------------------------------------
// Evaluation

func nextAfterRework(req *Obj) string {
	rc := req.Val("retry_count").(*Obj)
	if rc.Val("used").(*big.Int).Cmp(rc.Val("limit").(*big.Int)) >= 0 {
		return "ESCALATED"
	}
	return "REWORK"
}

func strsToAny(l []string) []any {
	out := make([]any, 0, len(l))
	for _, s := range l {
		out = append(out, s)
	}
	return out
}

// evaluate is governor.evaluate: one acceptance decision record, or errNoTaskID where the Python raises ValueError.
func evaluate(request, inputs, records any) (map[string]any, error) {
	req, ok := request.(*Obj)
	if !ok || !matches(reTask, req.Val("task_id")) {
		return nil, errNoTaskID
	}
	task := req.Val("task_id").(string)
	var errs []string
	errs = append(errs, govRequestErrors(req)...)
	errs = append(errs, govInputsErrors(inputs)...)
	errs = append(errs, govRecordsErrors(records)...)
	if len(errs) > 0 {
		return govErrorRecord(task, req, inputs, strings.Join(errs, "; "))
	}
	inp := inputs.(*Obj)
	gi := govInputs{
		risk:       inp.Val("risk").(string),
		ownerKept:  inp.Val("owner_kept_act").(bool),
		weakens:    inp.Val("weakens_evidence").(bool),
		delegated:  inp.Val("delegation_in_force").(bool),
		autoAccept: inp.Val("auto_accept").(bool),
	}

	blocking, approvals, current, stale, notes := sortRecords(task, req, records.([]any))

	plan := []string{"G0"}
	for _, g := range inp.Val("verification_plan").([]any) {
		if s := g.(string); s != "G0" && !contains(plan, s) {
			plan = append(plan, s)
		}
	}
	passed := map[string]bool{}
	var failedGateList []string
	for _, r := range current {
		if !r.Has("gate") || !strEq(r.Val("source_class"), govCI) {
			continue
		}
		g := r.Val("gate").(string)
		if strEq(r.Val("outcome"), "pass") {
			passed[g] = true
		}
		if strEq(r.Val("outcome"), "fail") {
			failedGateList = append(failedGateList, g)
		}
	}
	failedGates := sortedSet(failedGateList)
	missingGates := []string{}
	for _, g := range plan {
		if !passed[g] {
			missingGates = append(missingGates, g)
		}
	}

	byID := map[string]*Obj{}
	for _, r := range current {
		byID[recID(r)] = r
	}
	profileUsed := []any{}
	var missingKinds []string
	var failedRecords []string
	rests := []any{}
	missingAny := false
	for _, dt := range govJoin(inp.Val("evidence_profile").([]any), inp.Val("applicable_articles").([]any)) {
		reserved := map[string]bool{}
		var order []string
		for _, k := range dt.types {
			if k == crossModel {
				order = append(order, k)
			}
		}
		for _, k := range dt.types {
			if k != crossModel {
				order = append(order, k)
			}
		}
		sat := map[string][]string{}
		var missing []string
		for _, kind := range order {
			ids, failed := entry(dt.dimension, kind, current, gi, reserved)
			failedRecords = append(failedRecords, failed...)
			if len(ids) > 0 {
				sat[kind] = ids
			} else {
				missing = append(missing, kind)
			}
		}
		var all []string
		missingTypes := []string{}
		for _, kind := range dt.types {
			if ids, ok := sat[kind]; ok {
				all = append(all, ids...)
				review := true
				for _, i := range ids {
					if !in(reviewRecordTypes, byID[i].Val("evidence_type")) {
						review = false
					}
				}
				if review {
					rests = append(rests, map[string]any{"dimension": dt.dimension, "evidence_type": kind})
				}
			}
			if contains(missing, kind) {
				missingTypes = append(missingTypes, kind)
			}
		}
		if len(missingTypes) > 0 {
			missingAny = true
		}
		missingKinds = append(missingKinds, missingTypes...)
		profileUsed = append(profileUsed, map[string]any{
			"dimension":     dt.dimension,
			"required":      strsToAny(dt.types),
			"satisfied_by":  strsToAny(sortedSet(all)),
			"missing_types": strsToAny(missingTypes),
		})
	}

	var row1, otherBlocking bool
	labels := []string{}
	for _, b := range blocking {
		if contains(row1Kinds, b.kind) {
			row1 = true
		} else {
			otherBlocking = true
		}
		labels = append(labels, b.label)
	}
	sort.Strings(labels)
	reEvaluating := strEq(req.Val("task_state"), "IN_REVIEW")

	var approvalRecord any
	aiApproval := false
	var decision, state string
	var row int
	switch {
	case row1:
		decision, state, row = "REJECT", "REJECTED", 1
	case otherBlocking || len(failedGates) > 0 || len(failedRecords) > 0:
		decision, state, row = "NEEDS_REWORK", nextAfterRework(req), 2
	case len(missingGates) > 0 || missingAny:
		decision, row = "INSUFFICIENT_EVIDENCE", 3
		humanOnly := len(missingGates) == 0
		for _, k := range missingKinds {
			if !contains(humanTypes, k) {
				humanOnly = false
			}
		}
		if humanOnly {
			state = "IN_REVIEW"
		} else {
			state = nextAfterRework(req)
		}
	case gi.autoAccept && levelAtLeastL2 && !reEvaluating:
		decision, state, row = "ACCEPT", "ACCEPTED", 4
	default:
		decision, state, row = "NEEDS_REVIEW", "IN_REVIEW", 5
		if reEvaluating {
			approvalRecord, aiApproval = approval(req, gi, approvals, &notes)
			if approvalRecord != nil {
				state = "ACCEPTED"
			}
		}
	}

	rec := govBase(task, inputs)
	rec["decision"] = decision
	rec["next_task_state"] = state
	rec["table_row"] = row
	rec["task_content_hash"] = req.Val("task_content_hash")
	rec["evaluated_commit"] = req.Val("evaluated_commit")
	rec["intent_versions"] = req.Val("intent_versions")
	rec["profile_used"] = profileUsed
	rec["missing_gates"] = strsToAny(missingGates)
	rec["blocking"] = strsToAny(labels)
	rec["failed_gates"] = strsToAny(failedGates)
	rec["reverify"] = strsToAny(stale)
	rec["approval_record"] = approvalRecord
	rec["uncovered"] = notesList(notes)
	rec["rests_on_ai"] = map[string]any{"entries": rests, "approval": aiApproval}
	id, err := govRecordID(rec)
	if err != nil {
		return nil, err
	}
	rec["record_id"] = id
	return rec, nil
}
