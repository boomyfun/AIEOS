"""The Resume Check of specification 3 (TASK-008): the eight checks, the decision table and one execution decision record.

check(inputs, code_sha256=None) takes the inputs of specification 3 section 1 as values, in the form of
docs/specs/conformance-files.md section 9, and returns one execution decision record of specification 3 section 9:
the check 0 precondition, the eight checks of section 2, the decision of section 7, the effective read-set of section 4
with the signature verdicts of section 5, the record's ids, and the events of section 10 in the record's state_effect.
Two pure helpers compute from given texts what a caller needs to build the inputs: signature_form (the fixed form of
section 5) and direct_imports (the direct imports of section 4, one level).

Readings (each marked "(reading)" in the task contract):
- Every key of the inputs that is missing or not in its section 9 form gives a record with decision null and error.
  Within well-formed values, a budget use that is not reported, an article with no result, observed_read_set null and
  a budget form that cannot be parsed are uncovered, never an error.
- commits is base_commit..HEAD in the caller's order, each with its paths against its first parent; a path changed by
  several commits takes the last commit's change; renames are not detected.
- Tokens, wall time and human attention are compared by a fixed parse of their forms: tokens a number with an optional
  k (thousand) or m (million); times a number with s, m, h or d. A form that cannot be parsed is uncovered.
- source_class is deterministic_tool_local: the bootstrap's Resume Check runs locally.
- engine_identity is {code_sha256, python}: code_sha256 is the caller's, since a pure module cannot hash its own file
  (null when not given, uncovered then naming it); python is the interpreter's version from sys.version_info.
- record_id is the SHA-256 hex of the task id, log_seq, head_commit, code_sha256 (the empty string when null) and
  "decision.execution", joined by LF; each event of state_effect has its event_id formed the same way with its type.
- A check-4 REPLAN returns no task.stale, since the intent.changed event it must refer to is not an input
  (specification 3 section 12 point 4); every conflict.detected has tasks [], since commit trailers are not an input.
  Both are named in uncovered.
- STOP: violation is a decision taken while a session runs (section 8); this module never returns it.

Limits: check reads nothing, so how its inputs are read from Git, the event log, the files at HEAD and the runtime is
not shown here; the events are returned, not appended, and no lease is granted or released. No Resume Check fixture is
named by the set file until TASK-005b, so no CI conformance run calls check before then.

It imports only the standard library and aieos_bootstrap.records. It opens, writes and removes no file, reads no clock,
starts no process and makes no network call.
"""
import ast
import copy
import hashlib
import re
import sys

from aieos_bootstrap import records

INPUT_KEYS = frozenset({
    'task_id', 'log_seq', 'task_state', 'contract', 'contract_hash', 'approved_contract_hash', 'head_commit',
    'base_is_ancestor', 'commits', 'components', 'interfaces', 'symbols', 'schemas', 'derived_read_set',
    'observed_read_set', 'intent_current', 'dependencies', 'articles', 'runtime', 'risk_rules', 'policy_version',
    'budget_use'})
TASK_STATES = frozenset({'READY', 'REWORK', 'IN_PROGRESS'})
CHANGES = frozenset({'added', 'modified', 'deleted'})
RISKS = ('low', 'medium', 'high', 'critical')
# The order of specification 3 section 7; CONTINUE is the decision when none fires.
ORDER = ('STOP: violation', 'STOP: scope invalid', 'STOP: runtime insufficient', 'ESCALATE', 'BLOCKED', 'REPLAN',
         'CONTINUE_WITH')
RECORDER = 'the Resume Check (aieos_bootstrap.resume_check)'
SOURCE_CLASS = 'deterministic_tool_local'
AMBIGUOUS = 'ambiguous'
UNPARSABLE = 'unparsable'
UNANALYSED = 'unanalysed'
# The subject of an error record whose task_id is malformed: a fixed value that names no task (decision D-359).
NO_TASK = 'TASK-0'

_HEX64 = re.compile(r'[0-9a-f]{64}')
_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_TASK = re.compile(r'TASK-[0-9]+')
_VERSION = re.compile(r'v[0-9]+')
_AMOUNT = re.compile(r'([0-9]+)([a-z]*)')
_TOKEN_UNITS = {'': 1, 'k': 1000, 'm': 1000000}
_TIME_UNITS = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}


class _Bad(Exception):
    """An input that is missing or not in its section 9 form."""


# ---------------------------------------------------------------------------------------------------------------
# Value forms

def _str(v):
    return isinstance(v, str) and v != ''


def _int(v, minimum=0):
    return isinstance(v, int) and not isinstance(v, bool) and v >= minimum


def _strs(v):
    return isinstance(v, list) and all(_str(x) for x in v)


def _need(ok, what):
    if not ok:
        raise _Bad(what)


def _python_version():
    v = sys.version_info
    return '%d.%d.%d' % (v[0], v[1], v[2])


def _ids(task_id, log_seq, head_commit, code_sha256):
    def event_id(event_type):
        text = '\n'.join([task_id if isinstance(task_id, str) else '',
                          str(log_seq) if _int(log_seq) else '',
                          head_commit if isinstance(head_commit, str) else '',
                          code_sha256 or '', event_type])
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    return event_id


# ---------------------------------------------------------------------------------------------------------------
# Patterns (specification 3 section 3; the risk rules section 2 point 6)

def _names_meet(a, b):
    if '*' not in a and '*' not in b:
        return a == b
    if '*' in a and '*' in b:
        return True
    pattern, name = (a, b) if '*' in a else (b, a)
    return re.fullmatch(''.join('[^/]*' if ch == '*' else re.escape(ch) for ch in pattern), name) is not None


def _parts(pattern):
    if '/' not in pattern:
        pattern = '**/' + pattern
    return pattern.split('/')


def meet(a, b):
    """Whether two patterns meet: some path could match both. Names are compared from the root, "**" stands for any
    number of names, "*" for any part of one name; a pattern without "/" is read as "**/" followed by it. A path is a
    pattern with no wildcard, so a path matches a pattern exactly when they meet."""
    if not (isinstance(a, str) and isinstance(b, str)):
        return True
    pa, pb = _parts(a), _parts(b)
    memo = {}

    def go(i, j):
        key = (i, j)
        if key in memo:
            return memo[key]
        if i == len(pa) and j == len(pb):
            ok = True
        elif i < len(pa) and pa[i] == '**':
            ok = go(i + 1, j) or (j < len(pb) and go(i, j + 1))
        elif j < len(pb) and pb[j] == '**':
            ok = go(i, j + 1) or (i < len(pa) and go(i + 1, j))
        elif i < len(pa) and j < len(pb):
            ok = _names_meet(pa[i], pb[j]) and go(i + 1, j + 1)
        else:
            ok = False
        memo[key] = ok
        return ok
    return go(0, 0)


def matches(pattern, path):
    """Whether a path matches a pattern (a path has no wildcard)."""
    return meet(pattern, path)


def _folder(path):
    """A component path: itself, and, when it has no wildcard, the folder it may name (<it>/**)."""
    if '*' in path:
        return [path]
    return [path, path.rstrip('/') + '/**']


# ---------------------------------------------------------------------------------------------------------------
# The inputs (conformance-files.md section 9)

def _check_inputs(inp):
    _need(isinstance(inp, dict), 'inputs is not an object')
    missing = sorted(INPUT_KEYS - set(inp))
    _need(not missing, 'inputs lacks ' + ', '.join(missing))
    extra = sorted(str(k) for k in set(inp) - INPUT_KEYS)
    _need(not extra, 'inputs has keys section 9 does not name: ' + ', '.join(extra))
    _need(isinstance(inp['task_id'], str) and _TASK.fullmatch(inp['task_id']) is not None, 'task_id is not TASK-<digits>')
    _need(_int(inp['log_seq']), 'log_seq is not an integer at least 0')
    _need(inp['task_state'] in TASK_STATES if isinstance(inp['task_state'], str) else False,
          'task_state is not READY, REWORK or IN_PROGRESS')
    for key in ('contract_hash', 'approved_contract_hash'):
        _need(isinstance(inp[key], str) and _HEX64.fullmatch(inp[key]) is not None, key + ' is not 64 lowercase hex digits')
    _need(isinstance(inp['head_commit'], str) and _COMMIT.fullmatch(inp['head_commit']) is not None,
          'head_commit is not a commit id')
    _need(isinstance(inp['base_is_ancestor'], bool), 'base_is_ancestor is not true or false')
    _check_contract(inp['contract'])
    commits = inp['commits']
    _need(isinstance(commits, list), 'commits is not a list')
    for c in commits:
        _need(isinstance(c, dict) and set(c) == {'id', 'paths', 'submitted'}, 'a commit is not {id, paths, submitted}')
        _need(isinstance(c['id'], str) and _COMMIT.fullmatch(c['id']) is not None, 'a commit id is not a commit id')
        _need(isinstance(c['submitted'], bool), 'a commit submitted is not true or false')
        _need(isinstance(c['paths'], list), 'a commit paths is not a list')
        for p in c['paths']:
            _need(isinstance(p, dict) and set(p) == {'path', 'change'} and _str(p['path'])
                  and isinstance(p['change'], str) and p['change'] in CHANGES,
                  'a commit path is not {path, change}')
    _need(isinstance(inp['components'], list), 'components is not a list')
    for c in inp['components']:
        _need(isinstance(c, dict) and _str(c.get('id')) and _strs(c.get('paths')), 'a component is not {id, paths, tags}')
    _need(isinstance(inp['interfaces'], list), 'interfaces is not a list')
    for i in inp['interfaces']:
        _need(isinstance(i, dict) and _str(i.get('id')) and _str(i.get('component')), 'an interface is not {id, component}')
    _need(isinstance(inp['symbols'], list), 'symbols is not a list')
    for s in inp['symbols']:
        _need(isinstance(s, dict) and set(s) == {'interface', 'base', 'head'} and _str(s['interface'])
              and all(s[k] is None or isinstance(s[k], str) for k in ('base', 'head')),
              'a symbol is not {interface, base, head}')
    _need(isinstance(inp['schemas'], list), 'schemas is not a list')
    for s in inp['schemas']:
        _need(isinstance(s, dict) and set(s) == {'name', 'base', 'head'} and _str(s['name'])
              and all(_schema_side(s[k]) for k in ('base', 'head')), 'a schema is not {name, base, head}')
    _need(_strs(inp['derived_read_set']), 'derived_read_set is not a list of paths')
    _need(inp['observed_read_set'] is None or _strs(inp['observed_read_set']),
          'observed_read_set is not a list of paths or null')
    ic = inp['intent_current']
    _need(isinstance(ic, dict) and all(_str(k) and (v is None or _str(v)) for k, v in ic.items()),
          'intent_current is not an object of versions or null')
    deps = inp['dependencies']
    _need(isinstance(deps, dict), 'dependencies is not an object')
    for k, d in deps.items():
        _need(_str(k) and isinstance(d, dict) and set(d) == {'state', 'stale_evidence'}
              and (d['state'] is None or _str(d['state'])) and isinstance(d['stale_evidence'], bool),
              'a dependency is not {state, stale_evidence}')
    _need(isinstance(inp['articles'], list), 'articles is not a list')
    for a in inp['articles']:
        _need(isinstance(a, dict) and _str(a.get('id')) and 'violated' in a
              and (a['violated'] is None or isinstance(a['violated'], bool)),
              'an article is not {id, scope, applicability, violated}')
    rt = inp['runtime']
    _need(isinstance(rt, dict) and set(rt) == {'adapter', 'max_risk'} and _str(rt['adapter'])
          and (rt['max_risk'] is None or (isinstance(rt['max_risk'], str) and rt['max_risk'] in RISKS)),
          'runtime is not {adapter, max_risk}')
    _need(isinstance(inp['risk_rules'], list) and all(isinstance(r, dict) for r in inp['risk_rules']),
          'risk_rules is not a list of rules')
    _need(inp['policy_version'] is None or _str(inp['policy_version']), 'policy_version is not a string or null')
    bu = inp['budget_use']
    _need(isinstance(bu, dict), 'budget_use is not an object')
    for k, u in bu.items():
        _need(_str(k) and isinstance(u, dict) and set(u) == {'used', 'reported'} and isinstance(u['reported'], bool)
              and (_int(u['used']) or isinstance(u['used'], str)), 'a budget use is not {used, reported}')


def _schema_side(v):
    if v is None or v == AMBIGUOUS:
        return True
    return (isinstance(v, dict) and set(v) == {'path', 'sha256'} and _str(v['path'])
            and isinstance(v['sha256'], str) and _HEX64.fullmatch(v['sha256']) is not None)


def _check_contract(c):
    _need(isinstance(c, dict), 'contract is not an object')
    for key in ('input_state', 'write_set', 'read_set', 'constitution', 'task_type', 'risk', 'autonomy',
                'contract_version'):
        _need(key in c, 'contract lacks ' + key)
    s = c['input_state']
    _need(isinstance(s, dict), 'contract input_state is not an object')
    _need(isinstance(s.get('base_commit'), str) and _COMMIT.fullmatch(s['base_commit']) is not None,
          'contract base_commit is not a commit id')
    _need(_strs(s.get('depends_on')), 'contract depends_on is not a list of task ids')
    iv = s.get('intent_versions')
    _need(isinstance(iv, dict) and all(_str(k) and _str(v) for k, v in iv.items()),
          'contract intent_versions is not an object of versions')
    _need(isinstance(c['write_set'], dict) and _strs(c['write_set'].get('paths')), 'contract write_set.paths is not a list')
    rs = c['read_set']
    _need(isinstance(rs, dict) and all(_strs(rs.get(k, [])) for k in ('paths', 'interfaces', 'schemas')),
          'contract read_set is not {paths, interfaces, schemas}')
    _need(_strs(c['constitution']), 'contract constitution is not a list of article ids')
    _need(_str(c['task_type']), 'contract task_type is not a string')
    _need(isinstance(c['risk'], str) and c['risk'] in RISKS, 'contract risk is not low, medium, high or critical')
    _need(isinstance(c['contract_version'], str) and _VERSION.fullmatch(c['contract_version']) is not None,
          'contract contract_version is not v<digits>')
    b = c['autonomy'].get('budgets') if isinstance(c['autonomy'], dict) else None
    _need(isinstance(b, dict) and all(_str(k) and (_int(v) or _str(v)) for k, v in b.items()),
          'contract autonomy.budgets is not an object of limits')


# ---------------------------------------------------------------------------------------------------------------
# The effective read-set and the signatures (sections 4 and 5)

def _read_set(inp):
    rs = inp['contract']['read_set']
    paths = {}
    for source, items in (('declared', rs.get('paths', [])), ('derived', inp['derived_read_set']),
                          ('observed', inp['observed_read_set'] or [])):
        for p in items:
            paths.setdefault(p, [])
            if source not in paths[p]:
                paths[p].append(source)
    entries = [{'entry': p, 'kind': 'path', 'sources': s} for p, s in sorted(paths.items())]
    entries += [{'entry': i, 'kind': 'interface', 'sources': ['declared']} for i in sorted(set(rs.get('interfaces', [])))]
    entries += [{'entry': s, 'kind': 'schema', 'sources': ['declared']} for s in sorted(set(rs.get('schemas', [])))]
    return entries


def _component_paths(inp, component_id):
    """The patterns of a component's paths, or None when the component is unknown or defined more than once."""
    found = [c for c in inp['components'] if c['id'] == component_id]
    if len(found) != 1:
        return None
    out = []
    for p in found[0]['paths']:
        out += _folder(p)
    return out


def _interface_component(inp, name):
    found = [i for i in inp['interfaces'] if i['id'] == name]
    if len(found) != 1:
        return None
    return _component_paths(inp, found[0]['component'])


def _schema_paths(inp, name):
    found = [s for s in inp['schemas'] if s['name'] == name]
    if len(found) != 1:
        return None
    sides = [found[0][k] for k in ('base', 'head')]
    if any(not isinstance(v, dict) for v in sides):
        return None
    return sorted({v['path'] for v in sides})


def _verdicts(inp, entries, delta):
    """The met entries of the effective read-set, each with its verdict and reason (sections 3 and 5)."""
    met, unresolved = [], []
    for e in entries:
        name, kind = e['entry'], e['kind']
        if kind == 'path':
            if any(matches(name, p) for p in delta):
                met.append({'entry': name, 'kind': kind, 'verdict': 'non_breaking',
                            'reason': 'a path entry has no signature; its change is non-breaking'})
            continue
        if kind == 'interface':
            comp = _interface_component(inp, name)
            if comp is None:
                unresolved.append(name)
                if delta:
                    met.append({'entry': name, 'kind': kind, 'verdict': 'breaking',
                                'reason': 'the interface or its component cannot be resolved (fail closed)'})
                continue
            if not any(matches(c, p) for c in comp for p in delta):
                continue
            sym = [s for s in inp['symbols'] if s['interface'] == name]
            if len(sym) != 1:
                verdict, reason = 'breaking', 'no single symbol entry for the interface (fail closed)'
            else:
                b, h = sym[0]['base'], sym[0]['head']
                if b is None or h is None:
                    verdict, reason = 'breaking', 'the symbol is in no file at one commit'
                elif AMBIGUOUS in (b, h):
                    verdict, reason = 'breaking', 'the symbol is defined more than once at one commit'
                elif b != h:
                    verdict, reason = 'breaking', 'the signature differs between base_commit and HEAD'
                else:
                    verdict, reason = 'non_breaking', 'the signature is equal at base_commit and HEAD'
            met.append({'entry': name, 'kind': kind, 'verdict': verdict, 'reason': reason})
            continue
        resolved = _schema_paths(inp, name)
        if resolved is None:
            unresolved.append(name)
            if delta:
                met.append({'entry': name, 'kind': kind, 'verdict': 'breaking',
                            'reason': 'the schema resolves to no file or to more than one at one commit (fail closed)'})
            continue
        if not any(matches(r, p) for r in resolved for p in delta):
            continue
        s = [x for x in inp['schemas'] if x['name'] == name][0]
        if s['base'] == s['head']:
            verdict, reason = 'non_breaking', 'the schema file is the same path with the same content hash'
        else:
            verdict, reason = 'breaking', 'the schema file or its content hash differs'
        met.append({'entry': name, 'kind': kind, 'verdict': verdict, 'reason': reason})
    return met, unresolved


def _task_patterns(inp, entries):
    """write-set and effective read-set as patterns, for check 6."""
    out = list(inp['contract']['write_set']['paths'])
    for e in entries:
        if e['kind'] == 'path':
            out.append(e['entry'])
        elif e['kind'] == 'interface':
            comp = _interface_component(inp, e['entry'])
            out += comp if comp is not None else ['**']
        else:
            sp = _schema_paths(inp, e['entry'])
            out += sp if sp is not None else ['**']
    return out


# ---------------------------------------------------------------------------------------------------------------
# Check 6, check 7 and check 8

def _scope_patterns(inp, scope):
    """An article's scope as patterns: [] for no scope, None when the scope cannot be evaluated."""
    if scope is None:
        return []
    if not isinstance(scope, dict):
        return None
    out = []
    paths = scope.get('paths', [])
    comps = scope.get('components', [])
    if not (_strs(paths) and _strs(comps)):
        return None
    out += paths
    for cid in comps:
        cp = _component_paths(inp, cid)
        if cp is None:
            return None
        out += cp
    return out


def _applicable(inp, article, task_patterns):
    listed = article['id'] in inp['contract']['constitution']
    app = article.get('applicability')
    if app is not None:
        types = app.get('task_types') if isinstance(app, dict) else None
        if _strs(types) and inp['contract']['task_type'] not in types and not listed:
            return False
    if listed:
        return True
    sp = _scope_patterns(inp, article.get('scope'))
    if sp is None:
        return True
    return any(meet(a, b) for a in sp for b in task_patterns)


def _rule_patterns(rule):
    m = rule.get('match')
    if isinstance(m, dict) and _strs(m.get('paths')):
        return m['paths']
    return None


def _task_risk(inp):
    """The task's risk (section 2 check 7) and the write-set patterns no rule meets."""
    risk = inp['contract']['risk']
    unmatched = []
    for wp in inp['contract']['write_set']['paths']:
        hit = False
        for rule in inp['risk_rules']:
            pats = _rule_patterns(rule)
            cls = rule.get('risk') if isinstance(rule.get('risk'), str) and rule.get('risk') in RISKS else 'critical'
            if pats is None or any(meet(p, wp) for p in pats):
                hit = True
                if RISKS.index(cls) > RISKS.index(risk):
                    risk = cls
        if not hit:
            unmatched.append(wp)
    return risk, unmatched


def _amount(name, value):
    """A budget's value as a number, or None when its form cannot be parsed (reading)."""
    if _int(value):
        return value
    if not isinstance(value, str):
        return None
    m = _AMOUNT.fullmatch(value)
    if not m:
        return None
    units = _TOKEN_UNITS if name == 'tokens' else _TIME_UNITS if name in ('wall_time', 'human_attention') else None
    if units is None or m.group(2) not in units:
        return None
    return int(m.group(1)) * units[m.group(2)]


# ---------------------------------------------------------------------------------------------------------------
# The record

def _base(task_id, event_id, code_sha256):
    return {'record_id': event_id('decision.execution'), 'fact_kind': 'interpretation', 'source_class': SOURCE_CLASS,
            'recorder': RECORDER,
            'subject': task_id if isinstance(task_id, str) and _TASK.fullmatch(task_id) else NO_TASK,
            'engine_identity': {'code_sha256': code_sha256, 'python': _python_version()}}


def _error(inputs, code_sha256, reason):
    g = inputs.get if isinstance(inputs, dict) else (lambda k, d=None: d)
    event_id = _ids(g('task_id'), g('log_seq'), g('head_commit'), code_sha256)
    rec = _base(g('task_id'), event_id, code_sha256)
    rec.update({'decision': None, 'error': reason, 'uncovered': [], 'state_effect': []})
    if code_sha256 is None:
        rec['uncovered'].append('engine_identity.code_sha256: not given by the caller')
    if rec['subject'] == NO_TASK:
        rec['uncovered'].append('subject: task_id is malformed, so %s stands for it (decision D-359)' % NO_TASK)
    return rec


def check(inputs, code_sha256=None):
    """One execution decision record of specification 3 section 9 for the given inputs (conformance-files.md section
    9); never raises for a JSON-like value; never changes the inputs."""
    if code_sha256 is not None and not (isinstance(code_sha256, str) and _HEX64.fullmatch(code_sha256)):
        return _error(inputs, None, 'code_sha256 is not 64 lowercase hex digits')
    try:
        _check_inputs(inputs)
    except _Bad as exc:
        return _error(inputs, code_sha256, 'an input is missing or malformed: %s' % exc)
    except Exception as exc:
        return _error(inputs, code_sha256, 'an input could not be read: %s' % type(exc).__name__)
    if inputs['contract_hash'] != inputs['approved_contract_hash']:
        return _error(inputs, code_sha256, 'check 0: the contract at HEAD is not the approved contract')
    try:
        return _decide(copy.deepcopy(inputs), code_sha256)
    except Exception as exc:
        return _error(inputs, code_sha256, 'the check could not complete: %s' % type(exc).__name__)


def _decide(inp, code_sha256):
    c = inp['contract']
    s = c['input_state']
    event_id = _ids(inp['task_id'], inp['log_seq'], inp['head_commit'], code_sha256)
    uncovered = []
    checks = {}

    def put(n, status, outcome=None, detail=''):
        checks[n] = {'check': n, 'status': status, 'outcome': outcome, 'detail': detail}

    # Check 1: base freshness.
    delta = {}
    computed = False
    if s['base_commit'] == inp['head_commit']:
        put(1, 'passed', detail='base_commit equals HEAD')
    elif not inp['base_is_ancestor']:
        put(1, 'fired', 'ESCALATE', 'base_commit is not an ancestor of HEAD')
    else:
        for commit in inp['commits']:
            if commit['submitted']:
                continue
            for p in commit['paths']:
                delta[p['path']] = p['change']
        computed = True
        put(1, 'passed', detail='%d paths changed since base_commit' % len(delta))
    entries = _read_set(inp)
    met, unresolved = [], []
    # Check 2: write-set conflict; check 3: read-set freshness.
    if s['base_commit'] == inp['head_commit']:
        put(2, 'skipped', detail='HEAD equals base_commit')
        put(3, 'skipped', detail='HEAD equals base_commit')
    elif not computed:
        put(2, 'not_run', detail='the delta cannot be computed')
        put(3, 'not_run', detail='the delta cannot be computed')
    else:
        hit = sorted(p for p in delta if any(matches(w, p) for w in c['write_set']['paths']))
        if hit:
            put(2, 'fired', 'STOP: scope invalid', 'delta meets the write-set: ' + ', '.join(hit))
        else:
            put(2, 'passed', detail='delta does not meet the write-set')
        met, unresolved = _verdicts(inp, entries, sorted(delta))
        if not met:
            put(3, 'passed', detail='delta meets no entry of the effective read-set')
        elif any(m['verdict'] == 'breaking' for m in met):
            put(3, 'fired', 'REPLAN', 'a met entry is breaking: ' + ', '.join(m['entry'] for m in met if m['verdict'] == 'breaking'))
        else:
            put(3, 'fired', 'CONTINUE_WITH', 'every met entry is non-breaking')
    # Check 4: intent freshness.
    iv = {}
    moved = []
    for entity, version in sorted(s['intent_versions'].items()):
        current = inp['intent_current'].get(entity)
        iv[entity] = {'contract': version, 'current': current}
        if current != version:
            moved.append(entity)
    if moved:
        put(4, 'fired', 'REPLAN', 'intent moved or missing at HEAD: ' + ', '.join(moved))
    else:
        put(4, 'passed', detail='every intent version is current')
    # Check 5: dependency freshness.
    deps = {}
    blocking = []
    for task in s['depends_on']:
        d = inp['dependencies'].get(task)
        state = d['state'] if d is not None else None
        deps[task] = state
        if state != 'DONE':
            blocking.append(task)
    if blocking:
        put(5, 'fired', 'BLOCKED', 'a dependency is not DONE, is STALE or is unknown: ' + ', '.join(blocking))
    else:
        put(5, 'passed', detail='every dependency is DONE')
    # Check 6: constitution.
    patterns = _task_patterns(inp, entries)
    applicable, violated, no_result = [], [], []
    for a in inp['articles']:
        if _applicable(inp, a, patterns):
            applicable.append(a['id'])
            if a['violated'] is True:
                violated.append(a['id'])
            elif a['violated'] is None:
                no_result.append(a['id'])
    known = {a['id'] for a in inp['articles']}
    for aid in c['constitution']:
        if aid not in known and aid not in applicable:
            applicable.append(aid)
            no_result.append(aid)
    for aid in no_result:
        uncovered.append('article %s: no check result at HEAD' % aid)
    if violated:
        put(6, 'fired', 'ESCALATE', 'an applicable article is violated at HEAD: ' + ', '.join(violated))
    else:
        put(6, 'passed', detail='no applicable article is violated at HEAD')
    # Check 7: runtime.
    task_risk, unmatched = _task_risk(inp)
    max_risk = inp['runtime']['max_risk']
    if max_risk is None or RISKS.index(max_risk) < RISKS.index(task_risk):
        put(7, 'fired', 'STOP: runtime insufficient',
            'max_risk %s is below the task risk %s' % (max_risk, task_risk) if max_risk else 'the runtime has no declaration')
    elif unmatched:
        put(7, 'fired', 'ESCALATE', 'a write-set pattern meets no risk rule: ' + ', '.join(unmatched))
    else:
        put(7, 'passed', detail='max_risk %s covers the task risk %s' % (max_risk, task_risk))
    # Check 8: budget.
    budgets = {}
    over = []
    for name, limit in sorted(c['autonomy']['budgets'].items()):
        use = inp['budget_use'].get(name)
        used = use['used'] if use is not None else None
        reported = bool(use is not None and use['reported'])
        budgets[name] = {'limit': limit, 'used': used, 'reported': reported}
        if not reported:
            uncovered.append('budget %s: use not reported' % name)
            continue
        lim, amt = _amount(name, limit), _amount(name, used)
        if name == 'retries':
            lim, amt = (limit if _int(limit) else None), (used if _int(used) else None)
        if lim is None or amt is None:
            uncovered.append('budget %s: a form that cannot be parsed' % name)
            continue
        if amt > lim:
            over.append(name)
    if over:
        put(8, 'fired', 'ESCALATE', 'a budget is used up: ' + ', '.join(over))
    else:
        put(8, 'passed', detail='every reported budget use is within its limit')

    fired = [checks[n]['outcome'] for n in range(1, 9) if checks[n]['status'] == 'fired']
    outcomes = [o for o in ORDER if o in fired]
    decision = outcomes[0] if outcomes else 'CONTINUE'
    if inp['observed_read_set'] is None:
        uncovered.append('read-set: no observed source, the effective read-set is an estimate')
    if code_sha256 is None:
        uncovered.append('engine_identity.code_sha256: not given by the caller')

    record = _base(inp['task_id'], event_id, code_sha256)
    effect = _effect(decision, checks, inp, event_id, record['record_id'], met, delta, uncovered)
    record.update({
        'decision': decision,
        'contract_hash': inp['contract_hash'],
        'contract_version': c['contract_version'],
        'base_commit': s['base_commit'],
        'head_commit': inp['head_commit'],
        'log_seq': inp['log_seq'],
        'delta': [{'path': p, 'change': delta[p]} for p in sorted(delta)],
        'checks': [checks[n] for n in range(1, 9)],
        'outcomes_fired': outcomes,
        'read_set': {'entries': entries, 'estimate': inp['observed_read_set'] is None,
                     'unresolved': sorted(set(unresolved)), 'unanalysed': []},
        'signatures': met,
        'intent_versions': iv,
        'dependencies': deps,
        'constitution': {'applicable': applicable, 'violated': violated, 'no_result': no_result},
        'runtime': {'adapter': inp['runtime']['adapter'], 'max_risk': max_risk, 'task_risk': task_risk},
        'budgets': budgets,
        'policy_version': inp['policy_version'],
        'uncovered': uncovered,
        'state_effect': effect,
    })
    return record


def _event(event_id, task_id, event_type, payload):
    return {'event_id': event_id(event_type), 'type': event_type, 'payload': payload, 'task_id': task_id}


def _effect(decision, checks, inp, event_id, record_id, met, delta, uncovered):
    """The events of specification 3 section 10 for the decision, in the order the caller would append them."""
    task = inp['task_id']
    if decision == 'REPLAN':
        first = min(n for n in (3, 4) if checks[n]['status'] == 'fired' and checks[n]['outcome'] == 'REPLAN')
        if first == 4:
            uncovered.append('check 4 REPLAN: no task.stale, since the intent.changed event it must refer to is not '
                             'an input (specification 3 section 12 point 4)')
            return []
        hit = sorted({p for m in met for p in delta if m['kind'] != 'interface' and _meets_entry(inp, m, p)})
        conflict = _event(event_id, task, 'conflict.detected',
                          {'tasks': [], 'paths': hit, 'interfaces': sorted(m['entry'] for m in met if m['kind'] == 'interface')})
        uncovered.append('conflict.detected tasks: the commits\' trailers are not an input')
        if inp['task_state'] == 'READY':
            return [conflict]
        return [conflict, _event(event_id, task, 'task.stale', {'cause': 'conflict', 'refers_to': conflict['event_id']})]
    if decision == 'BLOCKED':
        tasks = [t for t in inp['contract']['input_state']['depends_on']
                 if (inp['dependencies'].get(t) or {}).get('state') != 'DONE']
        return [_event(event_id, task, 'task.blocked', {'reason': 'dependency', 'blocked_by': tasks})]
    if decision == 'ESCALATE':
        return [_event(event_id, task, 'task.blocked', {'reason': 'escalate', 'blocked_by': [record_id]})]
    if decision == 'STOP: scope invalid':
        hit = sorted(p for p in delta if any(matches(w, p) for w in inp['contract']['write_set']['paths']))
        conflict = _event(event_id, task, 'conflict.detected', {'tasks': [], 'paths': hit})
        uncovered.append('conflict.detected tasks: the commits\' trailers are not an input')
        return [conflict, _event(event_id, task, 'task.blocked',
                                 {'reason': 'scope_invalid', 'blocked_by': [conflict['event_id']]})]
    return []


def _meets_entry(inp, m, path):
    if m['kind'] == 'path':
        return matches(m['entry'], path)
    resolved = _schema_paths(inp, m['entry'])
    return True if resolved is None else any(matches(r, path) for r in resolved)


# ---------------------------------------------------------------------------------------------------------------
# The two helpers (sections 4 and 5)

def _default_marks(args):
    args = copy.deepcopy(args)
    args.defaults = [ast.Constant(value='<default>') for _ in args.defaults]
    args.kw_defaults = [None if d is None else ast.Constant(value='<default>') for d in args.kw_defaults]
    return args


def _function_form(node):
    kind = 'AsyncFunctionDef' if isinstance(node, ast.AsyncFunctionDef) else 'FunctionDef'
    return '%s(name=%r, args=%s, returns=%s, decorators=[%s])' % (
        kind, node.name, ast.dump(_default_marks(node.args)), ast.dump(node.returns) if node.returns else 'None',
        ', '.join(ast.dump(d) for d in node.decorator_list))


def _class_form(node):
    members = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith('_'):
            members.append(_function_form(item))
        elif isinstance(item, ast.Assign):
            names = [t.id for t in item.targets if isinstance(t, ast.Name) and not t.id.startswith('_')]
            if names:
                members.append('Assign(%s)' % ast.dump(item))
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and not item.target.id.startswith('_'):
            members.append('AnnAssign(%s)' % ast.dump(item))
    return 'ClassDef(name=%r, bases=[%s], keywords=[%s], decorators=[%s], members=[%s])' % (
        node.name, ', '.join(ast.dump(b) for b in node.bases), ', '.join(ast.dump(k) for k in node.keywords),
        ', '.join(ast.dump(d) for d in node.decorator_list), ', '.join(members))


def signature_form(source, name):
    """The fixed form of specification 3 section 5 of the top-level function or class named name in the given Python
    source text: the parser's dump without positions; None when no top-level definition has that name, "ambiguous"
    when more than one does, "unparsable" when the text cannot be parsed (reading)."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, TypeError):
        return UNPARSABLE
    found = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == name]
    if not found:
        return None
    if len(found) > 1:
        return AMBIGUOUS
    node = found[0]
    return _class_form(node) if isinstance(node, ast.ClassDef) else _function_form(node)


def _resolve(module, roots, paths):
    rel = module.replace('.', '/')
    for root in roots:
        prefix = root.rstrip('/') + '/' if root not in ('', '.', './') else ''
        for cand in (prefix + rel + '.py', prefix + rel + '/__init__.py'):
            if cand in paths:
                return cand
    return None


def direct_imports(source, roots, paths):
    """The direct imports of a Python source text (specification 3 section 4, one level): {"paths": the repository
    paths of the imported modules that resolve under the given module roots to one of the given paths, "unresolved":
    the imported names that do not resolve and are not standard-library modules}; "unanalysed" when the text cannot be
    parsed. Relative imports are unresolved (reading: the text's own package is not an input)."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, TypeError):
        return UNANALYSED
    paths = set(paths)
    found, unresolved = set(), set()
    std = getattr(sys, 'stdlib_module_names', frozenset())

    def take(module, also=()):
        for cand in tuple(also) + (module,):
            hit = _resolve(cand, roots, paths)
            if hit:
                found.add(hit)
                return
        if module.split('.')[0] not in std:
            unresolved.add(module)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                take(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                unresolved.add('.' * node.level + (node.module or ''))
                continue
            take(node.module, [node.module + '.' + a.name for a in node.names if a.name != '*'])
    return {'paths': sorted(found), 'unresolved': sorted(unresolved)}


__all__ = ['check', 'signature_form', 'direct_imports', 'meet', 'matches', 'ORDER', 'INPUT_KEYS']
