package main

// The Resume Check: resume_check.check and every function it calls.

import (
	"errors"
	"fmt"
	"math/big"
	"regexp"
	"sort"
	"strings"
)

const (
	rcRecorder    = "the Resume Check (aieos_bootstrap.resume_check)"
	rcSourceClass = "deterministic_tool_local"
	ambiguous     = "ambiguous"
	noTask        = "TASK-0"
	// enginePlaceholder is the one placeholder of the reference document: engine_identity.python, which in the
	// Python is the interpreter's version, is written as this text by every port.
	enginePlaceholder = "<engine>"
)

var (
	rcInputKeys = []string{"task_id", "log_seq", "task_state", "contract", "contract_hash", "approved_contract_hash",
		"head_commit", "base_is_ancestor", "commits", "components", "interfaces", "symbols", "schemas",
		"derived_read_set", "observed_read_set", "intent_current", "dependencies", "articles", "runtime",
		"risk_rules", "policy_version", "budget_use"}
	rcTaskStates = []string{"READY", "REWORK", "IN_PROGRESS"}
	rcChanges    = []string{"added", "modified", "deleted"}
	rcRisks      = []string{"low", "medium", "high", "critical"}
	rcOrder      = []string{"STOP: violation", "STOP: scope invalid", "STOP: runtime insufficient", "ESCALATE",
		"BLOCKED", "REPLAN", "CONTINUE_WITH"}
	maxLogSeq  = new(big.Int).Lsh(big.NewInt(1), 63)
	reAmount   = regexp.MustCompile(`^([0-9]+)([a-z]*)$`)
	tokenUnits = map[string]int64{"": 1, "k": 1000, "m": 1000000}
	timeUnits  = map[string]int64{"s": 1, "m": 60, "h": 3600, "d": 86400}
)

// errCannotCompute marks a case the port cannot compute: where the Python would return "an input could not be
// read: <type>" or "the check could not complete: <type>", the port fails closed (the brief's section 2).
var errCannotCompute = errors.New("the case cannot be computed")

// cannotCompute is raised (as a panic) inside the check and turned into errCannotCompute by check.
type cannotCompute struct{ why string }

func rcInt(v any) bool { return isCount(v) }

func riskIndex(r string) int {
	for i, x := range rcRisks {
		if x == r {
			return i
		}
	}
	panic(cannotCompute{"an unknown risk " + r})
}

func idsFunc(taskID, logSeq, headCommit any, code *string) func(string) string {
	return func(eventType string) string {
		parts := []string{"", "", "", "", eventType}
		if s, ok := taskID.(string); ok {
			parts[0] = s
		}
		if n, ok := logSeq.(*big.Int); ok && n.Sign() >= 0 && n.Cmp(maxLogSeq) < 0 {
			parts[1] = n.String()
		}
		if s, ok := headCommit.(string); ok {
			parts[2] = s
		}
		if code != nil {
			parts[3] = *code
		}
		return sha256Hex(strings.Join(parts, "\n"))
	}
}

// ---------------------------------------------------------------------------------------------------------------
// Patterns

func starMatch(pattern, name string) bool {
	pr, nr := []rune(pattern), []rune(name)
	p, n := 0, 0
	star, mark := -1, 0
	for n < len(nr) {
		switch {
		case p < len(pr) && pr[p] == '*':
			star, mark = p, n
			p++
		case p < len(pr) && pr[p] == nr[n]:
			p++
			n++
		case star >= 0:
			mark++
			p, n = star+1, mark
		default:
			return false
		}
	}
	for p < len(pr) && pr[p] == '*' {
		p++
	}
	return p == len(pr)
}

func namesMeet(a, b string) bool {
	sa, sb := strings.Contains(a, "*"), strings.Contains(b, "*")
	if !sa && !sb {
		return a == b
	}
	if sa && sb {
		return true
	}
	if sa {
		return starMatch(a, b)
	}
	return starMatch(b, a)
}

func patternParts(p string) []string {
	if !strings.Contains(p, "/") {
		p = "**/" + p
	}
	return strings.Split(p, "/")
}

// meet is resume_check.meet for two strings: whether some path could match both patterns.
func meet(a, b string) bool {
	pa, pb := patternParts(a), patternParts(b)
	memo := map[[2]int]bool{}
	var walk func(i, j int) bool
	walk = func(i, j int) bool {
		key := [2]int{i, j}
		if v, ok := memo[key]; ok {
			return v
		}
		var ok bool
		switch {
		case i == len(pa) && j == len(pb):
			ok = true
		case i < len(pa) && pa[i] == "**":
			ok = walk(i+1, j) || (j < len(pb) && walk(i, j+1))
		case j < len(pb) && pb[j] == "**":
			ok = walk(i, j+1) || (i < len(pa) && walk(i+1, j))
		case i < len(pa) && j < len(pb):
			ok = namesMeet(pa[i], pb[j]) && walk(i+1, j+1)
		default:
			ok = false
		}
		memo[key] = ok
		return ok
	}
	return walk(0, 0)
}

func pathMatches(pattern, path string) bool { return meet(pattern, path) }

func folder(path string) []string {
	if strings.Contains(path, "*") {
		return []string{path}
	}
	return []string{path, strings.TrimRight(path, "/") + "/**"}
}

// ---------------------------------------------------------------------------------------------------------------
// The inputs

func strsOf(v any) []string {
	l := v.([]any)
	out := make([]string, 0, len(l))
	for _, x := range l {
		out = append(out, x.(string))
	}
	return out
}

func checkInputs(v any) string {
	inp, ok := v.(*Obj)
	if !ok {
		return "inputs is not an object"
	}
	var missing, extra []string
	for _, k := range rcInputKeys {
		if !inp.Has(k) {
			missing = append(missing, k)
		}
	}
	sort.Strings(missing)
	if len(missing) > 0 {
		return "inputs lacks " + strings.Join(missing, ", ")
	}
	for _, k := range inp.keys {
		if !contains(rcInputKeys, k) {
			extra = append(extra, k)
		}
	}
	sort.Strings(extra)
	if len(extra) > 0 {
		return "inputs has keys section 9 does not name: " + strings.Join(extra, ", ")
	}
	if !matches(reTask, inp.Val("task_id")) {
		return "task_id is not TASK-<digits>"
	}
	if n, ok := inp.Val("log_seq").(*big.Int); !ok || n.Sign() < 0 || n.Cmp(maxLogSeq) >= 0 {
		return "log_seq is not an integer from 0 to 2**63 - 1"
	}
	if !in(rcTaskStates, inp.Val("task_state")) {
		return "task_state is not READY, REWORK or IN_PROGRESS"
	}
	for _, k := range []string{"contract_hash", "approved_contract_hash"} {
		if !matches(reHex64, inp.Val(k)) {
			return k + " is not 64 lowercase hex digits"
		}
	}
	if !matches(reCommit, inp.Val("head_commit")) {
		return "head_commit is not a commit id"
	}
	if _, ok := inp.Val("base_is_ancestor").(bool); !ok {
		return "base_is_ancestor is not true or false"
	}
	if msg := checkContract(inp.Val("contract")); msg != "" {
		return msg
	}
	commits, ok := inp.Val("commits").([]any)
	if !ok {
		return "commits is not a list"
	}
	for _, cv := range commits {
		c, ok := cv.(*Obj)
		if !(ok && c.keysAre("id", "paths", "submitted")) {
			return "a commit is not {id, paths, submitted}"
		}
		if !matches(reCommit, c.Val("id")) {
			return "a commit id is not a commit id"
		}
		if _, ok := c.Val("submitted").(bool); !ok {
			return "a commit submitted is not true or false"
		}
		paths, ok := c.Val("paths").([]any)
		if !ok {
			return "a commit paths is not a list"
		}
		for _, pv := range paths {
			p, ok := pv.(*Obj)
			if !(ok && p.keysAre("path", "change") && isStr(p.Val("path")) && in(rcChanges, p.Val("change"))) {
				return "a commit path is not {path, change}"
			}
		}
	}
	comps, ok := inp.Val("components").([]any)
	if !ok {
		return "components is not a list"
	}
	for _, cv := range comps {
		c, ok := cv.(*Obj)
		if !(ok && isStr(c.Val("id")) && isStrList(c.Val("paths"))) {
			return "a component is not {id, paths, tags}"
		}
	}
	ifaces, ok := inp.Val("interfaces").([]any)
	if !ok {
		return "interfaces is not a list"
	}
	for _, iv := range ifaces {
		i, ok := iv.(*Obj)
		if !(ok && isStr(i.Val("id")) && isStr(i.Val("component"))) {
			return "an interface is not {id, component}"
		}
	}
	syms, ok := inp.Val("symbols").([]any)
	if !ok {
		return "symbols is not a list"
	}
	for _, sv := range syms {
		s, ok := sv.(*Obj)
		good := ok && s.keysAre("interface", "base", "head") && isStr(s.Val("interface"))
		if good {
			for _, k := range []string{"base", "head"} {
				if _, isS := s.Val(k).(string); s.Val(k) != nil && !isS {
					good = false
				}
			}
		}
		if !good {
			return "a symbol is not {interface, base, head}"
		}
	}
	schemas, ok := inp.Val("schemas").([]any)
	if !ok {
		return "schemas is not a list"
	}
	for _, sv := range schemas {
		s, ok := sv.(*Obj)
		if !(ok && s.keysAre("name", "base", "head") && isStr(s.Val("name")) && schemaSide(s.Val("base")) &&
			schemaSide(s.Val("head"))) {
			return "a schema is not {name, base, head}"
		}
	}
	if !isStrList(inp.Val("derived_read_set")) {
		return "derived_read_set is not a list of paths"
	}
	if o := inp.Val("observed_read_set"); !(o == nil || isStrList(o)) {
		return "observed_read_set is not a list of paths or null"
	}
	ic, ok := inp.Val("intent_current").(*Obj)
	if ok {
		for _, k := range ic.keys {
			if v := ic.vals[k]; !isStr(k) || !(v == nil || isStr(v)) {
				ok = false
			}
		}
	}
	if !ok {
		return "intent_current is not an object of versions or null"
	}
	deps, ok := inp.Val("dependencies").(*Obj)
	if !ok {
		return "dependencies is not an object"
	}
	for _, k := range deps.keys {
		d, ok := deps.vals[k].(*Obj)
		if !(isStr(k) && ok && d.keysAre("state", "stale_evidence")) {
			return "a dependency is not {state, stale_evidence}"
		}
		_, sb := d.Val("stale_evidence").(bool)
		if st := d.Val("state"); !((st == nil || isStr(st)) && sb) {
			return "a dependency is not {state, stale_evidence}"
		}
	}
	arts, ok := inp.Val("articles").([]any)
	if !ok {
		return "articles is not a list"
	}
	for _, av := range arts {
		a, ok := av.(*Obj)
		good := ok && isStr(a.Val("id")) && a.Has("violated")
		if good {
			if _, isB := a.Val("violated").(bool); a.Val("violated") != nil && !isB {
				good = false
			}
		}
		if !good {
			return "an article is not {id, scope, applicability, violated}"
		}
	}
	rt, ok := inp.Val("runtime").(*Obj)
	if !(ok && rt.keysAre("adapter", "max_risk") && isStr(rt.Val("adapter")) &&
		(rt.Val("max_risk") == nil || in(rcRisks, rt.Val("max_risk")))) {
		return "runtime is not {adapter, max_risk}"
	}
	rules, ok := inp.Val("risk_rules").([]any)
	if ok {
		for _, r := range rules {
			if _, isO := r.(*Obj); !isO {
				ok = false
			}
		}
	}
	if !ok {
		return "risk_rules is not a list of rules"
	}
	if pv := inp.Val("policy_version"); !(pv == nil || isStr(pv)) {
		return "policy_version is not a string or null"
	}
	bu, ok := inp.Val("budget_use").(*Obj)
	if !ok {
		return "budget_use is not an object"
	}
	for _, k := range bu.keys {
		u, ok := bu.vals[k].(*Obj)
		good := isStr(k) && ok && u.keysAre("used", "reported")
		if good {
			_, rb := u.Val("reported").(bool)
			_, us := u.Val("used").(string)
			good = rb && (rcInt(u.Val("used")) || us)
		}
		if !good {
			return "a budget use is not {used, reported}"
		}
	}
	return ""
}

func schemaSide(v any) bool {
	if v == nil || strEq(v, ambiguous) {
		return true
	}
	o, ok := v.(*Obj)
	return ok && o.keysAre("path", "sha256") && isStr(o.Val("path")) && matches(reHex64, o.Val("sha256"))
}

func checkContract(v any) string {
	c, ok := v.(*Obj)
	if !ok {
		return "contract is not an object"
	}
	for _, k := range []string{"input_state", "write_set", "read_set", "constitution", "task_type", "risk", "autonomy",
		"contract_version"} {
		if !c.Has(k) {
			return "contract lacks " + k
		}
	}
	s, ok := c.Val("input_state").(*Obj)
	if !ok {
		return "contract input_state is not an object"
	}
	if !matches(reCommit, s.Val("base_commit")) {
		return "contract base_commit is not a commit id"
	}
	if !isStrList(s.Val("depends_on")) {
		return "contract depends_on is not a list of task ids"
	}
	iv, ok := s.Val("intent_versions").(*Obj)
	if ok {
		for _, k := range iv.keys {
			if !isStr(k) || !isStr(iv.vals[k]) {
				ok = false
			}
		}
	}
	if !ok {
		return "contract intent_versions is not an object of versions"
	}
	ws, ok := c.Val("write_set").(*Obj)
	if !(ok && isStrList(ws.Val("paths"))) {
		return "contract write_set.paths is not a list"
	}
	rs, ok := c.Val("read_set").(*Obj)
	if ok {
		for _, k := range []string{"paths", "interfaces", "schemas"} {
			if v, has := rs.Get(k); has && !isStrList(v) {
				ok = false
			}
		}
	}
	if !ok {
		return "contract read_set is not {paths, interfaces, schemas}"
	}
	if !isStrList(c.Val("constitution")) {
		return "contract constitution is not a list of article ids"
	}
	if !isStr(c.Val("task_type")) {
		return "contract task_type is not a string"
	}
	if !in(rcRisks, c.Val("risk")) {
		return "contract risk is not low, medium, high or critical"
	}
	if !matches(reVersion, c.Val("contract_version")) {
		return "contract contract_version is not v<digits>"
	}
	var b *Obj
	if a, ok := c.Val("autonomy").(*Obj); ok {
		b, _ = a.Val("budgets").(*Obj)
	}
	ok = b != nil
	if ok {
		for _, k := range b.keys {
			if v := b.vals[k]; !isStr(k) || !(rcInt(v) || isStr(v)) {
				ok = false
			}
		}
	}
	if !ok {
		return "contract autonomy.budgets is not an object of limits"
	}
	return ""
}

// ---------------------------------------------------------------------------------------------------------------
// The effective read-set and the signatures

type rsEntry struct {
	entry, kind string
	sources     []string
}

func (e rsEntry) value() map[string]any {
	return map[string]any{"entry": e.entry, "kind": e.kind, "sources": strsToAny(e.sources)}
}

type metEntry struct {
	entry, kind, verdict, reason string
}

func (m metEntry) value() map[string]any {
	return map[string]any{"entry": m.entry, "kind": m.kind, "verdict": m.verdict, "reason": m.reason}
}

type rc struct {
	inp        *Obj
	contract   *Obj
	components []*Obj
	interfaces []*Obj
	symbols    []*Obj
	schemas    []*Obj
}

func objs(v any) []*Obj {
	var out []*Obj
	for _, x := range v.([]any) {
		out = append(out, x.(*Obj))
	}
	return out
}

func listOr(o *Obj, k string) []string {
	if v, ok := o.Get(k); ok {
		return strsOf(v)
	}
	return nil
}

func (c *rc) readSet() []rsEntry {
	rs := c.contract.Val("read_set").(*Obj)
	var order []string
	sources := map[string][]string{}
	add := func(source string, items []string) {
		for _, p := range items {
			if _, ok := sources[p]; !ok {
				order = append(order, p)
				sources[p] = []string{}
			}
			if !contains(sources[p], source) {
				sources[p] = append(sources[p], source)
			}
		}
	}
	add("declared", listOr(rs, "paths"))
	add("derived", strsOf(c.inp.Val("derived_read_set")))
	if o := c.inp.Val("observed_read_set"); o != nil {
		add("observed", strsOf(o))
	}
	sort.Strings(order)
	var entries []rsEntry
	for _, p := range order {
		entries = append(entries, rsEntry{p, "path", sources[p]})
	}
	for _, i := range sortedSet(listOr(rs, "interfaces")) {
		entries = append(entries, rsEntry{i, "interface", []string{"declared"}})
	}
	for _, s := range sortedSet(listOr(rs, "schemas")) {
		entries = append(entries, rsEntry{s, "schema", []string{"declared"}})
	}
	return entries
}

// componentPaths is _component_paths: nil (with false) when the component is unknown or defined more than once.
func (c *rc) componentPaths(id string) ([]string, bool) {
	var found []*Obj
	for _, x := range c.components {
		if strEq(x.Val("id"), id) {
			found = append(found, x)
		}
	}
	if len(found) != 1 {
		return nil, false
	}
	out := []string{}
	for _, p := range strsOf(found[0].Val("paths")) {
		out = append(out, folder(p)...)
	}
	return out, true
}

func (c *rc) interfaceComponent(name string) ([]string, bool) {
	var found []*Obj
	for _, x := range c.interfaces {
		if strEq(x.Val("id"), name) {
			found = append(found, x)
		}
	}
	if len(found) != 1 {
		return nil, false
	}
	return c.componentPaths(found[0].Val("component").(string))
}

func (c *rc) schemaByName(name string) []*Obj {
	var found []*Obj
	for _, x := range c.schemas {
		if strEq(x.Val("name"), name) {
			found = append(found, x)
		}
	}
	return found
}

func (c *rc) schemaPaths(name string) ([]string, bool) {
	found := c.schemaByName(name)
	if len(found) != 1 {
		return nil, false
	}
	var paths []string
	for _, k := range []string{"base", "head"} {
		side, ok := found[0].Val(k).(*Obj)
		if !ok {
			return nil, false
		}
		paths = append(paths, side.Val("path").(string))
	}
	return sortedSet(paths), true
}

func anyMatch(patterns, paths []string) bool {
	for _, p := range patterns {
		for _, x := range paths {
			if pathMatches(p, x) {
				return true
			}
		}
	}
	return false
}

func (c *rc) verdicts(entries []rsEntry, delta []string) ([]metEntry, []string) {
	met := []metEntry{}
	unresolved := []string{}
	for _, e := range entries {
		name, kind := e.entry, e.kind
		if kind == "path" {
			if anyMatch([]string{name}, delta) {
				met = append(met, metEntry{name, kind, "non_breaking", "a path entry has no signature; its change is non-breaking"})
			}
			continue
		}
		if kind == "interface" {
			comp, ok := c.interfaceComponent(name)
			if !ok {
				unresolved = append(unresolved, name)
				if len(delta) > 0 {
					met = append(met, metEntry{name, kind, "breaking", "the interface or its component cannot be resolved (fail closed)"})
				}
				continue
			}
			if !anyMatch(comp, delta) {
				continue
			}
			var sym []*Obj
			for _, s := range c.symbols {
				if strEq(s.Val("interface"), name) {
					sym = append(sym, s)
				}
			}
			var verdict, reason string
			if len(sym) != 1 {
				verdict, reason = "breaking", "no single symbol entry for the interface (fail closed)"
			} else {
				b, h := sym[0].Val("base"), sym[0].Val("head")
				switch {
				case b == nil || h == nil:
					verdict, reason = "breaking", "the symbol is in no file at one commit"
				case strEq(b, ambiguous) || strEq(h, ambiguous):
					verdict, reason = "breaking", "the symbol is defined more than once at one commit"
				case !pyEq(b, h):
					verdict, reason = "breaking", "the signature differs between base_commit and HEAD"
				default:
					verdict, reason = "non_breaking", "the signature is equal at base_commit and HEAD"
				}
			}
			met = append(met, metEntry{name, kind, verdict, reason})
			continue
		}
		resolved, ok := c.schemaPaths(name)
		if !ok {
			unresolved = append(unresolved, name)
			if len(delta) > 0 {
				met = append(met, metEntry{name, kind, "breaking", "the schema resolves to no file or to more than one at one commit (fail closed)"})
			}
			continue
		}
		if !anyMatch(resolved, delta) {
			continue
		}
		s := c.schemaByName(name)[0]
		verdict, reason := "breaking", "the schema file or its content hash differs"
		if pyEq(s.Val("base"), s.Val("head")) {
			verdict, reason = "non_breaking", "the schema file is the same path with the same content hash"
		}
		met = append(met, metEntry{name, kind, verdict, reason})
	}
	return met, unresolved
}

func (c *rc) taskPatterns(entries []rsEntry) []string {
	out := append([]string(nil), strsOf(c.contract.Val("write_set").(*Obj).Val("paths"))...)
	for _, e := range entries {
		switch e.kind {
		case "path":
			out = append(out, e.entry)
		case "interface":
			if comp, ok := c.interfaceComponent(e.entry); ok {
				out = append(out, comp...)
			} else {
				out = append(out, "**")
			}
		default:
			if sp, ok := c.schemaPaths(e.entry); ok {
				out = append(out, sp...)
			} else {
				out = append(out, "**")
			}
		}
	}
	return out
}

// ---------------------------------------------------------------------------------------------------------------
// Check 6, check 7 and check 8

// scopePatterns is _scope_patterns: [] for no scope, false when the scope cannot be evaluated.
func (c *rc) scopePatterns(scope any) ([]string, bool) {
	if scope == nil {
		return []string{}, true
	}
	o, ok := scope.(*Obj)
	if !ok {
		return nil, false
	}
	paths, hasP := o.Get("paths")
	if !hasP {
		paths = []any{}
	}
	comps, hasC := o.Get("components")
	if !hasC {
		comps = []any{}
	}
	if !(isStrList(paths) && isStrList(comps)) {
		return nil, false
	}
	out := append([]string{}, strsOf(paths)...)
	for _, cid := range strsOf(comps) {
		cp, ok := c.componentPaths(cid)
		if !ok {
			return nil, false
		}
		out = append(out, cp...)
	}
	return out, true
}

func (c *rc) applicable(article *Obj, taskPatterns []string) bool {
	constitution := strsOf(c.contract.Val("constitution"))
	listed := contains(constitution, article.Val("id").(string))
	if app := article.Val("applicability"); app != nil {
		var types any
		if o, ok := app.(*Obj); ok {
			types = o.Val("task_types")
		}
		if isStrList(types) && !contains(strsOf(types), c.contract.Val("task_type").(string)) && !listed {
			return false
		}
	}
	if listed {
		return true
	}
	sp, ok := c.scopePatterns(article.Val("scope"))
	if !ok {
		return true
	}
	for _, a := range sp {
		for _, b := range taskPatterns {
			if meet(a, b) {
				return true
			}
		}
	}
	return false
}

func rulePatterns(rule *Obj) ([]string, bool) {
	m, ok := rule.Val("match").(*Obj)
	if ok && isStrList(m.Val("paths")) {
		return strsOf(m.Val("paths")), true
	}
	return nil, false
}

func (c *rc) taskRisk() (string, []string) {
	risk := c.contract.Val("risk").(string)
	unmatched := []string{}
	for _, wp := range strsOf(c.contract.Val("write_set").(*Obj).Val("paths")) {
		hit := false
		for _, rv := range c.inp.Val("risk_rules").([]any) {
			rule := rv.(*Obj)
			pats, ok := rulePatterns(rule)
			cls := "critical"
			if in(rcRisks, rule.Val("risk")) {
				cls = rule.Val("risk").(string)
			}
			match := !ok
			for _, p := range pats {
				if !match && meet(p, wp) {
					match = true
				}
			}
			if match {
				hit = true
				if riskIndex(cls) > riskIndex(risk) {
					risk = cls
				}
			}
		}
		if !hit {
			unmatched = append(unmatched, wp)
		}
	}
	return risk, unmatched
}

// amount is _amount: a budget's value as a number, or nil when its form cannot be parsed. A digit text that
// Python's int() refuses (more than 4300 digits) raises ValueError in the Python; it panics with pyValueError.
func amount(name string, value any) *big.Int {
	if rcInt(value) {
		return value.(*big.Int)
	}
	s, ok := value.(string)
	if !ok {
		return nil
	}
	m := reAmount.FindStringSubmatch(s)
	if m == nil {
		return nil
	}
	var units map[string]int64
	switch name {
	case "tokens":
		units = tokenUnits
	case "wall_time", "human_attention":
		units = timeUnits
	default:
		return nil
	}
	unit, ok := units[m[2]]
	if !ok {
		return nil
	}
	if len(m[1]) > maxIntDigits {
		panic(pyValueError{})
	}
	n, _ := new(big.Int).SetString(m[1], 10)
	return n.Mul(n, big.NewInt(unit))
}

// ---------------------------------------------------------------------------------------------------------------
// The record

func rcBase(taskID any, eventID func(string) string, code *string) map[string]any {
	subject := noTask
	if matches(reTask, taskID) {
		subject = taskID.(string)
	}
	var codeV any
	if code != nil {
		codeV = *code
	}
	return map[string]any{
		"record_id":    eventID("decision.execution"),
		"fact_kind":    "interpretation",
		"source_class": rcSourceClass,
		"recorder":     rcRecorder,
		"subject":      subject,
		// The Python writes the interpreter's version here; the reference document and every port write the
		// placeholder.
		"engine_identity": map[string]any{"code_sha256": codeV, "python": enginePlaceholder},
	}
}

func rcError(inputs any, code *string, reason string) map[string]any {
	var taskID, logSeq, head any
	if o, ok := inputs.(*Obj); ok {
		taskID, logSeq, head = o.Val("task_id"), o.Val("log_seq"), o.Val("head_commit")
	}
	rec := rcBase(taskID, idsFunc(taskID, logSeq, head, code), code)
	uncovered := []any{}
	if code == nil {
		uncovered = append(uncovered, "engine_identity.code_sha256: not given by the caller")
	}
	if rec["subject"] == noTask {
		uncovered = append(uncovered, "subject: task_id is malformed, so "+noTask+" stands for it (decision D-359)")
	}
	rec["decision"] = nil
	rec["error"] = reason
	rec["uncovered"] = uncovered
	rec["state_effect"] = []any{}
	return rec
}

// check is resume_check.check(inputs, code_sha256) (the reference export gives no code_sha256: nil there).
// Where the Python returns its two error records that name a Python exception type, it returns errCannotCompute,
// except the ValueError of a budget amount, which gives the Python's record (TASK-101 AC4 (b), (c)).
func check(inputs any, code *string) (rec map[string]any, err error) {
	if code != nil && !reHex64.MatchString(*code) {
		return rcError(inputs, nil, "code_sha256 is not 64 lowercase hex digits"), nil
	}
	if msg, err := guarded(func() string { return checkInputs(inputs) }); err != nil {
		return nil, err // "an input could not be read: <type>"
	} else if msg != "" {
		return rcError(inputs, code, "an input is missing or malformed: "+msg), nil
	}
	inp := inputs.(*Obj)
	if !pyEq(inp.Val("contract_hash"), inp.Val("approved_contract_hash")) {
		return rcError(inputs, code, "check 0: the contract at HEAD is not the approved contract"), nil
	}
	defer func() {
		if r := recover(); r != nil {
			rec, err = notCompleted(inputs, code, r)
		}
	}()
	return decide(inp, code), nil
}

func guarded(f func() string) (msg string, err error) {
	defer func() {
		if r := recover(); r != nil {
			msg, err = "", fmt.Errorf("%w: an input could not be read: %v", errCannotCompute, r)
		}
	}()
	return f(), nil
}

// pyValueError is raised (as a panic) where the Python's int() raises ValueError: a digit text of more than 4300
// digits (TASK-101 AC4 (c)).
type pyValueError struct{}

// notCompleted is check's handling of a panic in decide: the ValueError of a budget amount gives the Python's error
// record "the check could not complete: ValueError"; any other panic fails closed (errCannotCompute, AC4 (b)).
func notCompleted(inputs any, code *string, r any) (map[string]any, error) {
	if _, ok := r.(pyValueError); ok {
		return rcError(inputs, code, "the check could not complete: ValueError"), nil
	}
	return nil, fmt.Errorf("%w: the check could not complete: %v", errCannotCompute, r)
}

type checkResult struct {
	status  string
	outcome any
	detail  string
}

func decide(inp *Obj, code *string) map[string]any {
	c := inp.Val("contract").(*Obj)
	s := c.Val("input_state").(*Obj)
	st := &rc{inp: inp, contract: c, components: objs(inp.Val("components")), interfaces: objs(inp.Val("interfaces")),
		symbols: objs(inp.Val("symbols")), schemas: objs(inp.Val("schemas"))}
	eventID := idsFunc(inp.Val("task_id"), inp.Val("log_seq"), inp.Val("head_commit"), code)
	uncovered := []any{}
	checks := map[int]checkResult{}
	put := func(n int, status string, outcome any, detail string) {
		checks[n] = checkResult{status, outcome, detail}
	}
	writePaths := strsOf(c.Val("write_set").(*Obj).Val("paths"))
	baseIsHead := pyEq(s.Val("base_commit"), inp.Val("head_commit"))

	// Check 1: base freshness.
	delta := map[string]string{}
	computed := false
	switch {
	case baseIsHead:
		put(1, "passed", nil, "base_commit equals HEAD")
	case !inp.Val("base_is_ancestor").(bool):
		put(1, "fired", "ESCALATE", "base_commit is not an ancestor of HEAD")
	default:
		for _, cv := range inp.Val("commits").([]any) {
			commit := cv.(*Obj)
			if commit.Val("submitted").(bool) {
				continue
			}
			for _, pv := range commit.Val("paths").([]any) {
				p := pv.(*Obj)
				delta[p.Val("path").(string)] = p.Val("change").(string)
			}
		}
		computed = true
		put(1, "passed", nil, fmt.Sprintf("%d paths changed since base_commit", len(delta)))
	}
	sortedDelta := make([]string, 0, len(delta))
	for p := range delta {
		sortedDelta = append(sortedDelta, p)
	}
	sort.Strings(sortedDelta)
	entries := st.readSet()
	met, unresolved := []metEntry{}, []string{}
	// Check 2: write-set conflict; check 3: read-set freshness.
	var writeHit []string
	for _, p := range sortedDelta {
		if anyMatch(writePaths, []string{p}) {
			writeHit = append(writeHit, p)
		}
	}
	switch {
	case baseIsHead:
		put(2, "skipped", nil, "HEAD equals base_commit")
		put(3, "skipped", nil, "HEAD equals base_commit")
	case !computed:
		put(2, "not_run", nil, "the delta cannot be computed")
		put(3, "not_run", nil, "the delta cannot be computed")
	default:
		if len(writeHit) > 0 {
			put(2, "fired", "STOP: scope invalid", "delta meets the write-set: "+strings.Join(writeHit, ", "))
		} else {
			put(2, "passed", nil, "delta does not meet the write-set")
		}
		met, unresolved = st.verdicts(entries, sortedDelta)
		var breaking []string
		for _, m := range met {
			if m.verdict == "breaking" {
				breaking = append(breaking, m.entry)
			}
		}
		switch {
		case len(met) == 0:
			put(3, "passed", nil, "delta meets no entry of the effective read-set")
		case len(breaking) > 0:
			put(3, "fired", "REPLAN", "a met entry is breaking: "+strings.Join(breaking, ", "))
		default:
			put(3, "fired", "CONTINUE_WITH", "every met entry is non-breaking")
		}
	}
	// Check 4: intent freshness.
	ivOut := map[string]any{}
	var moved []string
	civ := s.Val("intent_versions").(*Obj)
	ivKeys := append([]string(nil), civ.keys...)
	sort.Strings(ivKeys)
	current := inp.Val("intent_current").(*Obj)
	for _, entity := range ivKeys {
		version := civ.vals[entity]
		cur := current.Val(entity)
		ivOut[entity] = map[string]any{"contract": version, "current": cur}
		if !pyEq(cur, version) {
			moved = append(moved, entity)
		}
	}
	if len(moved) > 0 {
		put(4, "fired", "REPLAN", "intent moved or missing at HEAD: "+strings.Join(moved, ", "))
	} else {
		put(4, "passed", nil, "every intent version is current")
	}
	// Check 5: dependency freshness.
	depsOut := map[string]any{}
	var blocking []string
	dependencies := inp.Val("dependencies").(*Obj)
	dependsOn := strsOf(s.Val("depends_on"))
	depState := func(task string) any {
		if d, ok := dependencies.Val(task).(*Obj); ok {
			return d.Val("state")
		}
		return nil
	}
	for _, task := range dependsOn {
		state := depState(task)
		depsOut[task] = state
		if !strEq(state, "DONE") {
			blocking = append(blocking, task)
		}
	}
	if len(blocking) > 0 {
		put(5, "fired", "BLOCKED", "a dependency is not DONE, is STALE or is unknown: "+strings.Join(blocking, ", "))
	} else {
		put(5, "passed", nil, "every dependency is DONE")
	}
	// Check 6: constitution.
	patterns := st.taskPatterns(entries)
	applicable, violated, noResult := []string{}, []string{}, []string{}
	known := map[string]bool{}
	for _, av := range inp.Val("articles").([]any) {
		a := av.(*Obj)
		id := a.Val("id").(string)
		known[id] = true
		if st.applicable(a, patterns) {
			applicable = append(applicable, id)
			switch v := a.Val("violated"); {
			case v == true:
				violated = append(violated, id)
			case v == nil:
				noResult = append(noResult, id)
			}
		}
	}
	for _, aid := range strsOf(c.Val("constitution")) {
		if !known[aid] && !contains(applicable, aid) {
			applicable = append(applicable, aid)
			noResult = append(noResult, aid)
		}
	}
	for _, aid := range noResult {
		uncovered = append(uncovered, "article "+aid+": no check result at HEAD")
	}
	if len(violated) > 0 {
		put(6, "fired", "ESCALATE", "an applicable article is violated at HEAD: "+strings.Join(violated, ", "))
	} else {
		put(6, "passed", nil, "no applicable article is violated at HEAD")
	}
	// Check 7: runtime.
	taskRisk, unmatched := st.taskRisk()
	rt := inp.Val("runtime").(*Obj)
	maxRisk := rt.Val("max_risk")
	switch {
	case maxRisk == nil:
		put(7, "fired", "STOP: runtime insufficient", "the runtime has no declaration")
	case riskIndex(maxRisk.(string)) < riskIndex(taskRisk):
		put(7, "fired", "STOP: runtime insufficient",
			fmt.Sprintf("max_risk %s is below the task risk %s", maxRisk.(string), taskRisk))
	case len(unmatched) > 0:
		put(7, "fired", "ESCALATE", "a write-set pattern meets no risk rule: "+strings.Join(unmatched, ", "))
	default:
		put(7, "passed", nil, fmt.Sprintf("max_risk %s covers the task risk %s", maxRisk.(string), taskRisk))
	}
	// Check 8: budget.
	budgetsOut := map[string]any{}
	var over []string
	budgets := c.Val("autonomy").(*Obj).Val("budgets").(*Obj)
	bKeys := append([]string(nil), budgets.keys...)
	sort.Strings(bKeys)
	budgetUse := inp.Val("budget_use").(*Obj)
	for _, name := range bKeys {
		limit := budgets.vals[name]
		var used any
		reported := false
		if u, ok := budgetUse.Val(name).(*Obj); ok {
			used = u.Val("used")
			reported = u.Val("reported").(bool)
		}
		budgetsOut[name] = map[string]any{"limit": limit, "used": used, "reported": reported}
		if !reported {
			uncovered = append(uncovered, "budget "+name+": use not reported")
			continue
		}
		var lim, amt *big.Int
		if name == "retries" {
			if rcInt(limit) {
				lim = limit.(*big.Int)
			}
			if rcInt(used) {
				amt = used.(*big.Int)
			}
		} else {
			lim, amt = amount(name, limit), amount(name, used)
		}
		if lim == nil || amt == nil {
			uncovered = append(uncovered, "budget "+name+": a form that cannot be parsed")
			continue
		}
		if amt.Cmp(lim) > 0 {
			over = append(over, name)
		}
	}
	if len(over) > 0 {
		put(8, "fired", "ESCALATE", "a budget is used up: "+strings.Join(over, ", "))
	} else {
		put(8, "passed", nil, "every reported budget use is within its limit")
	}

	fired := map[string]bool{}
	for n := 1; n <= 8; n++ {
		if checks[n].status == "fired" {
			fired[checks[n].outcome.(string)] = true
		}
	}
	outcomesFired := []string{}
	for _, o := range rcOrder {
		if fired[o] {
			outcomesFired = append(outcomesFired, o)
		}
	}
	decision := "CONTINUE"
	if len(outcomesFired) > 0 {
		decision = outcomesFired[0]
	}
	observedNone := inp.Val("observed_read_set") == nil
	if observedNone {
		uncovered = append(uncovered, "read-set: no observed source, the effective read-set is an estimate")
	}
	if code == nil {
		uncovered = append(uncovered, "engine_identity.code_sha256: not given by the caller")
	}

	record := rcBase(inp.Val("task_id"), eventID, code)
	recordID := record["record_id"].(string)
	taskID := inp.Val("task_id").(string)
	event := func(eventType string, payload map[string]any) map[string]any {
		return map[string]any{"event_id": eventID(eventType), "type": eventType, "payload": payload, "task_id": taskID}
	}
	// _effect: the events of specification 3 section 10 for the decision.
	effect := []any{}
	switch decision {
	case "REPLAN":
		first := 4
		if checks[3].status == "fired" && strEq(checks[3].outcome, "REPLAN") {
			first = 3
		}
		if first == 4 {
			uncovered = append(uncovered, "check 4 REPLAN: no task.stale, since the intent.changed event it must "+
				"refer to is not an input (specification 3 section 12 point 4)")
			break
		}
		var hit, ifaces []string
		for _, m := range met {
			if m.kind == "interface" {
				ifaces = append(ifaces, m.entry)
				continue
			}
			for _, p := range sortedDelta {
				if st.meetsEntry(m, p) {
					hit = append(hit, p)
				}
			}
		}
		conflict := event("conflict.detected", map[string]any{"tasks": []any{}, "paths": strsToAny(sortedSet(hit)),
			"interfaces": strsToAny(sortedCopy(ifaces))})
		uncovered = append(uncovered, "conflict.detected tasks: the commits' trailers are not an input")
		effect = append(effect, conflict)
		if !strEq(inp.Val("task_state"), "READY") {
			effect = append(effect, event("task.stale", map[string]any{"cause": "conflict",
				"refers_to": conflict["event_id"]}))
		}
	case "BLOCKED":
		tasks := []string{}
		for _, t := range dependsOn {
			if !strEq(depState(t), "DONE") {
				tasks = append(tasks, t)
			}
		}
		effect = append(effect, event("task.blocked", map[string]any{"reason": "dependency",
			"blocked_by": strsToAny(tasks)}))
	case "ESCALATE":
		effect = append(effect, event("task.blocked", map[string]any{"reason": "escalate",
			"blocked_by": []any{recordID}}))
	case "STOP: scope invalid":
		conflict := event("conflict.detected", map[string]any{"tasks": []any{}, "paths": strsToAny(writeHit)})
		uncovered = append(uncovered, "conflict.detected tasks: the commits' trailers are not an input")
		effect = append(effect, conflict, event("task.blocked", map[string]any{"reason": "scope_invalid",
			"blocked_by": []any{conflict["event_id"]}}))
	}

	deltaOut := []any{}
	for _, p := range sortedDelta {
		deltaOut = append(deltaOut, map[string]any{"path": p, "change": delta[p]})
	}
	checksOut := []any{}
	for n := 1; n <= 8; n++ {
		ch := checks[n]
		checksOut = append(checksOut, map[string]any{"check": n, "status": ch.status, "outcome": ch.outcome,
			"detail": ch.detail})
	}
	entriesOut := []any{}
	for _, e := range entries {
		entriesOut = append(entriesOut, e.value())
	}
	metOut := []any{}
	for _, m := range met {
		metOut = append(metOut, m.value())
	}
	record["decision"] = decision
	record["contract_hash"] = inp.Val("contract_hash")
	record["contract_version"] = c.Val("contract_version")
	record["base_commit"] = s.Val("base_commit")
	record["head_commit"] = inp.Val("head_commit")
	record["log_seq"] = inp.Val("log_seq")
	record["delta"] = deltaOut
	record["checks"] = checksOut
	record["outcomes_fired"] = strsToAny(outcomesFired)
	record["read_set"] = map[string]any{"entries": entriesOut, "estimate": observedNone,
		"unresolved": strsToAny(sortedSet(unresolved)), "unanalysed": []any{}}
	record["signatures"] = metOut
	record["intent_versions"] = ivOut
	record["dependencies"] = depsOut
	record["constitution"] = map[string]any{"applicable": strsToAny(applicable), "violated": strsToAny(violated),
		"no_result": strsToAny(noResult)}
	record["runtime"] = map[string]any{"adapter": rt.Val("adapter"), "max_risk": maxRisk, "task_risk": taskRisk}
	record["budgets"] = budgetsOut
	record["policy_version"] = inp.Val("policy_version")
	record["uncovered"] = uncovered
	record["state_effect"] = effect
	return record
}

func sortedCopy(l []string) []string {
	out := append([]string{}, l...)
	sort.Strings(out)
	return out
}

func (c *rc) meetsEntry(m metEntry, path string) bool {
	if m.kind == "path" {
		return pathMatches(m.entry, path)
	}
	resolved, ok := c.schemaPaths(m.entry)
	if !ok {
		return true
	}
	return anyMatch(resolved, []string{path})
}
