"""Unit tests of the Resume Check fixtures of TASK-005 (docs/specs/conformance-files.md revision 4, sections 2 and 9;
docs/tasks/TASK-005.yaml AC1 to AC5).

The helpers below are repeated in the three test modules of TASK-005, because each CI test folder is discovered on its
own and an import between them is not allowed. Files are read as bytes with pathlib; no fixture module is ever imported
or executed. Every failing case is built in memory from an altered copy of a real fixture.
"""
import copy
import hashlib
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCENARIO_FILE = 'docs/pre-genesis/conformance-scenarios-initial.md'
FIXTURE_DIR = 'tests/conformance/fixtures_rc'
FIRST, LAST = b"DATA = r'''", b"'''\n"
# The A15 execution decision values (specification 3 section 7, with CONTINUE when no check fires).
EXECUTION = ('CONTINUE', 'CONTINUE_WITH', 'REPLAN', 'BLOCKED', 'ESCALATE', 'STOP: violation', 'STOP: scope invalid',
             'STOP: runtime insufficient')
# The acceptance values of concept lines 299-303; TASK-005's AC8 list is read as these five (decision D-269).
ACCEPTANCE = ('ACCEPT', 'NEEDS_REVIEW', 'INSUFFICIENT_EVIDENCE', 'NEEDS_REWORK', 'REJECT')
# The 22 inputs of conformance-files.md section 9, in the order of its inputs row.
INPUT_KEYS = ('task_id', 'log_seq', 'task_state', 'contract', 'contract_hash', 'approved_contract_hash', 'head_commit',
              'base_is_ancestor', 'commits', 'components', 'interfaces', 'symbols', 'schemas', 'derived_read_set',
              'observed_read_set', 'intent_current', 'dependencies', 'articles', 'runtime', 'risk_rules',
              'policy_version', 'budget_use')
CONTRACT_KEYS = ('input_state', 'write_set', 'read_set', 'constitution', 'task_type', 'risk', 'autonomy')
RISKS = ('low', 'medium', 'high', 'critical')
STATES = ('DRAFT', 'READY', 'IN_PROGRESS', 'VERIFYING', 'ACCEPTED', 'DONE', 'IN_REVIEW', 'REWORK', 'ESCALATED',
          'REJECTED', 'BLOCKED', 'STALE')
# Each scenario's expected value with the text of its Expected cell (AC3); the test below checks the text against the
# bound file, and the fixture against the value.
EXPECTED = {
    'RC-01': ('CONTINUE', 'CONTINUE'),
    'RC-02': ('CONTINUE', 'CONTINUE'),
    'RC-03': ('STOP: scope invalid', 'STOP: scope invalid'),
    'RC-04': ('CONTINUE_WITH', 'CONTINUE_WITH'),
    'RC-05': ('REPLAN', 'REPLAN'),
    'RC-06': ('REPLAN', 'REPLAN'),
    'RC-07': ('BLOCKED', 'BLOCKED'),
    'RC-08': ('ESCALATE', 'ESCALATE'),
    'RC-09': ('STOP: runtime insufficient', 'STOP: runtime insufficient'),
    'RC-10': ('ESCALATE', 'ESCALATE'),
    'RC-11': ('CONTINUE', 'CONTINUE'),
}
HEX64 = re.compile(r'[0-9a-f]{64}')
COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
TASK = re.compile(r'TASK-[0-9]+')
VERSION = re.compile(r'v[0-9]+')
AMOUNT = re.compile(r'([0-9]+)([kmsh]?)')


class Malformed(ValueError):
    """A fixture file that is not in the form of conformance-files.md section 2."""


def read(path):
    return (ROOT / path).read_bytes()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canon(value, indent=0):
    """The canonical JSON text of one value (section 2), without the final LF."""
    pad = ' ' * (indent + 2)
    if isinstance(value, dict):
        if not value:
            return '{}'
        items = (pad + canon(k) + ': ' + canon(value[k], indent + 2) for k in sorted(value))
        return '{\n' + ',\n'.join(items) + '\n' + ' ' * indent + '}'
    if isinstance(value, list):
        if not value:
            return '[]'
        return '[\n' + ',\n'.join(pad + canon(x, indent + 2) for x in value) + '\n' + ' ' * indent + ']'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if value is None:
        return 'null'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        out = []
        for ch in value:
            if ch in '"\\':
                out.append('\\' + ch)
            elif ord(ch) < 0x20:
                out.append('\\u%04x' % ord(ch))
            else:
                out.append(ch)
        return '"' + ''.join(out) + '"'
    raise Malformed('a value of type %s has no canonical form' % type(value).__name__)


def wrap(value):
    text = (canon(value) + '\n').encode('utf-8')
    if b"'''" in text:
        raise Malformed("the JSON text holds ''' and cannot be wrapped")
    return FIRST + text + LAST


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise Malformed('a duplicate key: %s' % key)
        out[key] = value
    return out


def _no_float(text):
    raise Malformed('a number with a fraction or an exponent: %s' % text)


def _no_constant(text):
    raise Malformed('a constant that JSON does not have: %s' % text)


def unwrap(data):
    """The JSON value a fixture file wraps, or Malformed (section 2: the two fixed parts, then canonical JSON)."""
    if not isinstance(data, bytes) or not data.startswith(FIRST) or not data.endswith(LAST) or len(data) < len(FIRST) + len(LAST):
        raise Malformed('the file does not start with the first part and end with the last part')
    text = data[len(FIRST):len(data) - len(LAST)]
    if b"'''" in text:
        raise Malformed("the JSON text holds '''")
    if text.startswith(b'\xef\xbb\xbf') or b'\r' in text:
        raise Malformed('a byte-order mark or a CR byte')
    try:
        decoded = text.decode('utf-8')
        value = json.loads(decoded, object_pairs_hook=_pairs, parse_float=_no_float, parse_constant=_no_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Malformed('not UTF-8 JSON: %s' % exc) from None
    if canon(value) + '\n' != decoded:
        raise Malformed('the JSON text is not in the canonical form')
    return value


def rc_rows(data=None):
    """Each Resume Check row of the bound file: {id: (row hash, Expected cell)}."""
    text = (read(SCENARIO_FILE) if data is None else data).decode('utf-8')
    rows = {}
    for line in text.split('\n'):
        m = re.match(r'^\| (RC-[0-9]+) \| ', line)
        if m:
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            rows[m.group(1)] = (sha256(line.encode('utf-8')), cells[4])
    return rows


def module_path(sid):
    return FIXTURE_DIR + '/' + sid.lower().replace('-', '_') + '.py'


def is_str(x):
    return isinstance(x, str) and x != ''


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


# Path patterns (AC4): a literal path, or a folder followed by /**; meets and matches as specification 3 section 3
# decides them for these two forms.
def pattern_ok(p):
    if not is_str(p) or p.startswith('/') or '\\' in p:
        return False
    body = p[:-3] if p.endswith('/**') else p
    return body != '' and '*' not in body


def matches(pattern, path):
    if pattern.endswith('/**'):
        return path.startswith(pattern[:-2])
    return pattern == path


def meets(p, q):
    if p.endswith('/**') and q.endswith('/**'):
        return p[:-2].startswith(q[:-2]) or q[:-2].startswith(p[:-2])
    if p.endswith('/**'):
        return matches(p, q)
    if q.endswith('/**'):
        return matches(q, p)
    return p == q


def delta(inputs):
    """The paths of the commits of base_commit..HEAD that no task.submitted event of this task names (S3 check 1)."""
    return sorted({e['path'] for c in inputs['commits'] if not c['submitted'] for e in c['paths']})


def read_set_met(inputs, d):
    """The declared read-set entries that Δ meets (S3 section 3): paths, interfaces by their component, schemas by file."""
    rs = inputs['contract']['read_set']
    met = []
    met += [('path', p) for p in rs['paths'] if any(matches(p, x) for x in d)]
    comps = {c['id']: c for c in inputs['components']}
    for i in inputs['interfaces']:
        if i['id'] in rs['interfaces'] and any(matches(p, x) for p in comps[i['component']]['paths'] for x in d):
            met.append(('interface', i['id']))
    for s in inputs['schemas']:
        if s['name'] in rs['schemas'] and any(isinstance(v, dict) and v['path'] in d for v in (s['base'], s['head'])):
            met.append(('schema', s['name']))
    return met


def amount(text):
    """A time budget of specification 2 section 5.1 in seconds: a whole number with s, m or h."""
    m = AMOUNT.fullmatch(text) if isinstance(text, str) else None
    if not m or m.group(2) not in ('s', 'm', 'h'):
        raise Malformed('a time amount of no known form: %r' % (text,))
    return int(m.group(1)) * {'s': 1, 'm': 60, 'h': 3600}[m.group(2)]


def tokens(text):
    m = AMOUNT.fullmatch(text) if isinstance(text, str) else None
    if not m or m.group(2) not in ('', 'k', 'm'):
        raise Malformed('a token amount of no known form: %r' % (text,))
    return int(m.group(1)) * {'': 1, 'k': 1000, 'm': 1000000}[m.group(2)]


def budget_value(name, x):
    return x if name == 'retries' else tokens(x) if name == 'tokens' else amount(x)


def check_form(value, sid, rows):
    """AC1 (the path) and AC2: the fixture's structure and value forms. Returns a list of errors."""
    if not isinstance(value, dict) or set(value) != {'scenario', 'row_hash', 'cases'}:
        return ['the fixture is not exactly scenario, row_hash and cases']
    errors = []
    if value['scenario'] != sid:
        errors.append('scenario is not %s' % sid)
    if sid not in rows or value['row_hash'] != rows[sid][0]:
        errors.append('row_hash differs from the bound row')
    cases = value['cases']
    if not isinstance(cases, list) or len(cases) != 1:
        return errors + ['cases does not hold exactly one case']
    case = cases[0]
    if not isinstance(case, dict) or set(case) != {'inputs', 'when', 'expected'}:
        return errors + ['the case is not exactly inputs, when and expected']
    if case['when'] != 'resume':
        errors.append('when is not resume')
    exp = case['expected']
    if not isinstance(exp, dict) or set(exp) != {'decision', 'not_fixed'}:
        errors.append('expected is not exactly decision and not_fixed')
    else:
        if exp['not_fixed'] != []:
            errors.append('not_fixed is not []')
        if not (isinstance(exp['decision'], list) and len(exp['decision']) == 1 and exp['decision'][0] in EXECUTION):
            errors.append('decision is not a list of exactly one A15 value')
    i = case['inputs']
    if not isinstance(i, dict) or set(i) != set(INPUT_KEYS):
        return errors + ['inputs are not exactly the 22 keys of section 9']
    if not (isinstance(i['task_id'], str) and TASK.fullmatch(i['task_id'])):
        errors.append('task_id is not TASK- followed by digits')
    if not (is_int(i['log_seq']) and i['log_seq'] >= 0):
        errors.append('log_seq is not an integer of 0 or more')
    if i['task_state'] not in ('READY', 'REWORK', 'IN_PROGRESS'):
        errors.append('task_state is not READY, REWORK or IN_PROGRESS')
    c = i['contract']
    if not isinstance(c, dict) or not set(CONTRACT_KEYS) <= set(c):
        return errors + ['contract lacks a key of section 9']
    st = c['input_state']
    if not (isinstance(st, dict) and {'base_commit', 'depends_on', 'intent_versions'} <= set(st)
            and isinstance(st['base_commit'], str) and COMMIT.fullmatch(st['base_commit'])
            and isinstance(st['depends_on'], list) and all(isinstance(t, str) and TASK.fullmatch(t) for t in st['depends_on'])
            and isinstance(st['intent_versions'], dict)
            and all(is_str(k) and isinstance(v, str) and VERSION.fullmatch(v) for k, v in st['intent_versions'].items())):
        errors.append('contract.input_state is not in the form of spec 2 section 5.1')
        return errors
    if not (isinstance(c['write_set'], dict) and isinstance(c['write_set'].get('paths'), list)
            and all(pattern_ok(p) for p in c['write_set']['paths'])):
        errors.append('write_set.paths is not a list of literal or folder/** patterns')
    rs = c['read_set']
    if not (isinstance(rs, dict) and set(rs) == {'paths', 'interfaces', 'schemas'}
            and all(pattern_ok(p) for p in rs['paths']) and all(is_str(x) for x in rs['interfaces'] + rs['schemas'])):
        errors.append('read_set is not {paths, interfaces, schemas} of the allowed forms')
    if not (isinstance(c['constitution'], list) and all(is_str(x) for x in c['constitution'])):
        errors.append('constitution is not a list of article ids')
    if not is_str(c['task_type']) or c['risk'] not in RISKS:
        errors.append('task_type or risk is not of its form')
    au = c['autonomy']
    if not (isinstance(au, dict) and isinstance(au.get('budgets'), dict)
            and set(au['budgets']) == {'tokens', 'wall_time', 'retries', 'human_attention'}):
        errors.append('autonomy.budgets is not the four budgets of spec 2 section 5.1')
        return errors
    for k in ('contract_hash', 'approved_contract_hash'):
        if not (isinstance(i[k], str) and HEX64.fullmatch(i[k])):
            errors.append('%s is not 64 lowercase hex' % k)
    if not (isinstance(i['head_commit'], str) and COMMIT.fullmatch(i['head_commit'])):
        errors.append('head_commit is not a full lowercase hex commit id')
    if not isinstance(i['base_is_ancestor'], bool):
        errors.append('base_is_ancestor is not true or false')
    for cm in i['commits'] if isinstance(i['commits'], list) else [None]:
        if not (isinstance(cm, dict) and set(cm) == {'id', 'paths', 'submitted'} and isinstance(cm['id'], str)
                and COMMIT.fullmatch(cm['id']) and isinstance(cm['submitted'], bool) and isinstance(cm['paths'], list)
                and all(isinstance(e, dict) and set(e) == {'path', 'change'} and pattern_ok(e['path']) and not e['path'].endswith('/**')
                        and e['change'] in ('added', 'modified', 'deleted') for e in cm['paths'])):
            errors.append('a commit is not {id, paths, submitted} with paths of {path, change}')
    if not (isinstance(i['components'], list) and all(isinstance(x, dict) and set(x) == {'id', 'paths', 'tags'}
                                                       and all(pattern_ok(p) for p in x['paths']) for x in i['components'])):
        errors.append('components are not {id, paths, tags}')
    if not (isinstance(i['interfaces'], list) and all(isinstance(x, dict) and set(x) == {'id', 'component'} for x in i['interfaces'])):
        errors.append('interfaces are not {id, component}')
    if not (isinstance(i['symbols'], list) and all(isinstance(x, dict) and set(x) == {'interface', 'base', 'head'} for x in i['symbols'])):
        errors.append('symbols are not {interface, base, head}')
    if not (isinstance(i['schemas'], list) and all(isinstance(x, dict) and set(x) == {'name', 'base', 'head'} for x in i['schemas'])):
        errors.append('schemas are not {name, base, head}')
    if not (isinstance(i['derived_read_set'], list) and all(pattern_ok(p) for p in i['derived_read_set'])):
        errors.append('derived_read_set is not a list of path entries')
    if not (i['observed_read_set'] is None or (isinstance(i['observed_read_set'], list) and all(pattern_ok(p) for p in i['observed_read_set']))):
        errors.append('observed_read_set is not a list or null')
    if not (isinstance(i['intent_current'], dict) and set(i['intent_current']) == set(st['intent_versions'])
            and all(v is None or (isinstance(v, str) and VERSION.fullmatch(v)) for v in i['intent_current'].values())):
        errors.append('intent_current is not one version or null per entity of intent_versions')
    dep = i['dependencies']
    if not (isinstance(dep, dict) and set(dep) == set(st['depends_on'])
            and all(isinstance(v, dict) and set(v) == {'state', 'stale_evidence'} and (v['state'] is None or v['state'] in STATES)
                    and isinstance(v['stale_evidence'], bool) for v in dep.values())):
        errors.append('dependencies are not one {state, stale_evidence} per task of depends_on')
    if not (isinstance(i['articles'], list) and all(isinstance(a, dict) and set(a) == {'id', 'scope', 'applicability', 'violated'}
                                                     and a['violated'] in (True, False, None) and not is_int(a['violated'])
                                                     for a in i['articles'])):
        errors.append('articles are not {id, scope, applicability, violated}')
    rt = i['runtime']
    if not (isinstance(rt, dict) and set(rt) == {'adapter', 'max_risk'} and (rt['max_risk'] is None or rt['max_risk'] in RISKS)):
        errors.append('runtime is not {adapter, max_risk}')
    if not (isinstance(i['risk_rules'], list) and all(isinstance(r, dict) and set(r) == {'match', 'risk'} and r['risk'] in RISKS
                                                       and isinstance(r['match'], dict) and all(pattern_ok(p) for p in r['match'].get('paths', []))
                                                       for r in i['risk_rules'])) or not is_str(i['policy_version']):
        errors.append('risk_rules or policy_version are not in the form of spec 2 section 7')
    bu = i['budget_use']
    if not (isinstance(bu, dict) and set(bu) == set(au['budgets'])
            and all(isinstance(v, dict) and set(v) == {'used', 'reported'} and isinstance(v['reported'], bool) for v in bu.values())):
        errors.append('budget_use is not one {used, reported} per budget')
    return errors


def check_expected(value, sid):
    """AC3: the fixture's expected decision is the one value its scenario's Expected cell names."""
    want = EXPECTED[sid][0]
    return [] if value['cases'][0]['expected']['decision'] == [want] else ['expected.decision is not [%s]' % want]


def under(name, use, limit):
    return budget_value(name, use) < budget_value(name, limit)


def rule_risk(i):
    """The task's risk as check 7 computes it: the contract's, raised by every rule whose pattern meets the write-set."""
    ws = i['contract']['write_set']['paths']
    classes = [r['risk'] for r in i['risk_rules'] for p in r['match'].get('paths', []) if any(meets(p, w) for w in ws)]
    return max([i['contract']['risk']] + classes, key=RISKS.index)


def applies(article, i):
    """Whether an article applies to the task (S3 check 6): its scope meets write-set or read-set paths, and its
    applicability names the task type (an article with no scope is project-wide and not in the task-time set)."""
    sc = article['scope']
    if not sc:
        return False
    task_paths = i['contract']['write_set']['paths'] + i['contract']['read_set']['paths']
    hit = any(meets(p, q) for p in sc.get('paths', []) for q in task_paths)
    types = (article['applicability'] or {}).get('task_types')
    return hit and (types is None or i['contract']['task_type'] in types)


def check_placeholders(value, sid):
    """AC4: the placeholder constraints of section 9, with its exceptions."""
    i = value['cases'][0]['inputs']
    c = i['contract']
    errors = []
    d = delta(i)
    if i['approved_contract_hash'] != i['contract_hash']:
        errors.append('approved_contract_hash differs from contract_hash')
    if i['base_is_ancestor'] is not True:
        errors.append('base_is_ancestor is not true')
    if sid != 'RC-06' and i['intent_current'] != c['input_state']['intent_versions']:
        errors.append('intent_current differs from intent_versions')
    if sid != 'RC-09':
        mr = i['runtime']['max_risk']
        if mr is None or RISKS.index(rule_risk(i)) > RISKS.index(mr):
            errors.append('the task risk is above runtime.max_risk')
        for w in c['write_set']['paths']:
            if not any(meets(p, w) for r in i['risk_rules'] for p in r['match'].get('paths', [])):
                errors.append('a write_set pattern is met by no risk rule')
    for s in i['symbols'] + i['schemas']:
        if s['base'] in (None, 'ambiguous') or s['head'] in (None, 'ambiguous'):
            errors.append('an interface or schema entry does not resolve at both commits')
    if sid not in ('RC-03', 'RC-04', 'RC-05') and read_set_met(i, d):
        errors.append('Δ meets the read-set where the scenario needs it to miss')
    for t, dep in i['dependencies'].items():
        if sid == 'RC-07' and dep['state'] == 'STALE' or sid == 'RC-11' and dep['stale_evidence']:
            continue
        if dep['state'] != 'DONE' or dep['stale_evidence']:
            errors.append('dependency %s is not DONE with current evidence' % t)
    for a in i['articles']:
        if applies(a, i) and a['violated'] is not False and not (sid == 'RC-08' and a['violated'] is True):
            errors.append('applicable article %s is violated or has no result' % a['id'])
    for name, limit in c['autonomy']['budgets'].items():
        if sid == 'RC-10' and name == 'retries':
            continue
        if not under(name, i['budget_use'][name]['used'], limit):
            errors.append('budget %s is not under its limit' % name)
    if sid in ('RC-02', 'RC-03', 'RC-04', 'RC-05', 'RC-06'):
        others = i['derived_read_set'] + (i['observed_read_set'] or [])
        if any(matches(p, x) for p in others for x in d):
            errors.append('the derived or observed read-set meets Δ')
    return errors


def check_given(value, sid):
    """AC5: the scenario's own Given."""
    i = value['cases'][0]['inputs']
    c = i['contract']
    base = c['input_state']['base_commit']
    d = delta(i)
    ws_met = [x for x in d if any(matches(p, x) for p in c['write_set']['paths'])]
    met = read_set_met(i, d)
    errors = []
    moved = sid in ('RC-02', 'RC-03', 'RC-04', 'RC-05', 'RC-06')
    if moved:
        if i['head_commit'] == base or not i['commits']:
            errors.append('HEAD has not moved')
    elif i['head_commit'] != base or i['commits']:
        errors.append('HEAD is not base_commit with no commits (the defaults)')
    if sid == 'RC-02' and (ws_met or met):
        errors.append('Δ meets the write-set or the declared read-set')
    if sid == 'RC-03' and (not ws_met or any(cm['submitted'] for cm in i['commits'])):
        errors.append('Δ does not meet the write-set, or a commit is submitted')
    if sid in ('RC-04', 'RC-05') and (ws_met or not met):
        errors.append('Δ meets the write-set or misses the declared read-set')
    if sid == 'RC-04' and any(s['base'] != s['head'] for s in i['symbols'] + i['schemas']):
        errors.append('an interface or schema signature changed')
    if sid == 'RC-05':
        met_ifs = {n for k, n in met if k == 'interface'}
        if not any(s['interface'] in met_ifs and s['base'] != s['head'] for s in i['symbols']):
            errors.append('no signature of a met interface changed')
    if sid == 'RC-06':
        iv, cur = c['input_state']['intent_versions'], i['intent_current']
        changed = [k for k in iv if cur[k] != iv[k]]
        paths = [e['path'] for cm in i['commits'] for e in cm['paths']]
        ok = (len(i['commits']) == 1 and len(changed) == 1 and len(paths) == 1
              and paths[0].endswith('/' + changed[0] + '.md') and cur[changed[0]] is not None
              and int(cur[changed[0]][1:]) > int(iv[changed[0]][1:]) and not ws_met and not met)
        if not ok:
            errors.append('HEAD did not move only by one commit adding a newer version of one intent entity')
    deps = list(i['dependencies'].values())
    if sid == 'RC-07' and not any(x['state'] == 'STALE' for x in deps):
        errors.append('no dependency is STALE')
    if sid == 'RC-08' and [a['violated'] for a in i['articles'] if applies(a, i)].count(True) != 1:
        errors.append('not exactly one applicable article is violated')
    if sid == 'RC-09' and not (i['runtime']['max_risk'] is not None
                               and RISKS.index(i['runtime']['max_risk']) < RISKS.index(c['risk'])):
        errors.append('runtime.max_risk is not below the task risk')
    if sid == 'RC-10' and not i['budget_use']['retries']['used'] > c['autonomy']['budgets']['retries']:
        errors.append('retries are not over the limit')
    if sid == 'RC-11' and not any(x['state'] == 'DONE' and x['stale_evidence'] for x in deps):
        errors.append('no dependency is DONE with stale evidence')
    return errors


def all_errors(value, sid, rows):
    errors = check_form(value, sid, rows)
    if errors:
        return errors
    return check_expected(value, sid) + check_placeholders(value, sid) + check_given(value, sid)


def real(sid):
    return unwrap(read(module_path(sid)))


class FileKindTest(unittest.TestCase):
    """AC1: the file kind, the canonical form and the path."""

    def test_every_fixture_unwraps_and_reserialises_to_the_same_bytes(self):
        for sid in EXPECTED:
            data = read(module_path(sid))
            self.assertEqual(wrap(unwrap(data)), data, sid)

    def test_the_path_is_the_module_name_of_the_id(self):
        self.assertEqual(module_path('RC-01'), 'tests/conformance/fixtures_rc/rc_01.py')
        self.assertNotEqual(module_path('RC-10'), 'tests/conformance/fixtures/rc_10.py')

    def test_altered_files_are_malformed(self):
        data = read(module_path('RC-01'))
        bad = [data[1:], data[:-1], data.replace(b'\n', b'\r\n'), data.replace(b'  "cases"', b'"cases"', 1),
               FIRST + b'{"a": 1.5}\n' + LAST, FIRST + b"{\n  \"a\": \"'''\"\n}\n" + LAST,
               FIRST + b'{\n  "a": 1,\n  "a": 2\n}\n' + LAST, FIRST + b'\xef\xbb\xbf{}\n' + LAST]
        for n, b in enumerate(bad):
            with self.assertRaises(Malformed, msg=str(n)):
                unwrap(b)

    def test_a_value_with_triple_quotes_cannot_be_wrapped(self):
        with self.assertRaises(Malformed):
            wrap({'a': "'''"})


class FormTest(unittest.TestCase):
    """AC2: the structure and the value forms of section 9."""

    def setUp(self):
        self.rows = rc_rows()

    def test_every_real_fixture_has_no_finding(self):
        for sid in EXPECTED:
            self.assertEqual(all_errors(real(sid), sid, self.rows), [], sid)

    def alter(self, sid, change):
        v = copy.deepcopy(real(sid))
        change(v)
        return check_form(v, sid, self.rows)

    def test_each_form_rule_fails_on_an_altered_copy(self):
        cases = {
            'an extra top key': lambda v: v.update(extra=1),
            'another scenario': lambda v: v.update(scenario='RC-02'),
            'a wrong row hash': lambda v: v.update(row_hash='0' * 64),
            'two cases': lambda v: v['cases'].append(copy.deepcopy(v['cases'][0])),
            'when evaluate': lambda v: v['cases'][0].update(when='evaluate'),
            'two decisions': lambda v: v['cases'][0]['expected']['decision'].append('REPLAN'),
            'no decision': lambda v: v['cases'][0]['expected'].update(decision=[]),
            'an acceptance value': lambda v: v['cases'][0]['expected'].update(decision=['ACCEPT']),
            'not_fixed not empty': lambda v: v['cases'][0]['expected'].update(not_fixed=['decision']),
            'a missing input': lambda v: v['cases'][0]['inputs'].pop('symbols'),
            'an extra input': lambda v: v['cases'][0]['inputs'].update(records=[]),
            'a task id': lambda v: v['cases'][0]['inputs'].update(task_id='T-1'),
            'a negative log_seq': lambda v: v['cases'][0]['inputs'].update(log_seq=-1),
            'a task state': lambda v: v['cases'][0]['inputs'].update(task_state='DONE'),
            'a contract key': lambda v: v['cases'][0]['inputs']['contract'].pop('risk'),
            'a base commit': lambda v: v['cases'][0]['inputs']['contract']['input_state'].update(base_commit='HEAD'),
            'an intent version': lambda v: v['cases'][0]['inputs']['contract']['input_state']['intent_versions'].update({'SPEC-003': '4'}),
            'a write-set pattern': lambda v: v['cases'][0]['inputs']['contract']['write_set'].update(paths=['src/*.py']),
            'a read-set key': lambda v: v['cases'][0]['inputs']['contract']['read_set'].pop('schemas'),
            'a budget': lambda v: v['cases'][0]['inputs']['contract']['autonomy']['budgets'].pop('tokens'),
            'a contract hash': lambda v: v['cases'][0]['inputs'].update(contract_hash='abc'),
            'a head commit': lambda v: v['cases'][0]['inputs'].update(head_commit='abc'),
            'base_is_ancestor': lambda v: v['cases'][0]['inputs'].update(base_is_ancestor=1),
            'a commit': lambda v: v['cases'][0]['inputs'].update(commits=[{'id': 'x'}]),
            'a change value': lambda v: v['cases'][0]['inputs'].update(commits=[{'id': 'a' * 40, 'paths': [{'path': 'a.py', 'change': 'renamed'}], 'submitted': False}]),
            'a component': lambda v: v['cases'][0]['inputs']['components'][0].pop('tags'),
            'an interface': lambda v: v['cases'][0]['inputs']['interfaces'][0].pop('component'),
            'a symbol': lambda v: v['cases'][0]['inputs']['symbols'][0].pop('head'),
            'a schema': lambda v: v['cases'][0]['inputs']['schemas'][0].pop('base'),
            'a derived entry': lambda v: v['cases'][0]['inputs'].update(derived_read_set=['/abs']),
            'an observed read-set': lambda v: v['cases'][0]['inputs'].update(observed_read_set='none'),
            'intent_current': lambda v: v['cases'][0]['inputs'].update(intent_current={}),
            'a dependency': lambda v: v['cases'][0]['inputs'].update(dependencies={'TASK-099': {'state': 'GONE', 'stale_evidence': False}}),
            'an article': lambda v: v['cases'][0]['inputs']['articles'][0].update(violated='no'),
            'a runtime': lambda v: v['cases'][0]['inputs'].update(runtime={'adapter': 'x', 'max_risk': 'huge'}),
            'a risk rule': lambda v: v['cases'][0]['inputs'].update(risk_rules=[{'match': {}, 'risk': 'huge'}]),
            'a budget use': lambda v: v['cases'][0]['inputs']['budget_use'].pop('retries'),
        }
        for name, change in cases.items():
            self.assertNotEqual(self.alter('RC-01', change), [], name)


class FaithfulnessTest(unittest.TestCase):
    """AC3: expected.decision comes only from the scenario's own Expected cell."""

    def test_the_held_expected_cells_equal_the_bound_file(self):
        rows = rc_rows()
        self.assertEqual(sorted(rows), sorted(EXPECTED))
        for sid, (_value, cell) in EXPECTED.items():
            self.assertEqual(rows[sid][1], cell, sid)

    def test_each_fixture_expects_its_cell_value(self):
        for sid in EXPECTED:
            self.assertEqual(check_expected(real(sid), sid), [], sid)
            self.assertEqual(real(sid)['cases'][0]['expected']['decision'], [EXPECTED[sid][0]], sid)

    def test_another_value_fails(self):
        v = copy.deepcopy(real('RC-04'))
        v['cases'][0]['expected']['decision'] = ['CONTINUE']
        self.assertNotEqual(check_expected(v, 'RC-04'), [])

    def test_an_altered_bound_row_changes_the_row_hash(self):
        data = read(SCENARIO_FILE)
        altered = data.replace(b'| RC-01 | row CONTINUE', b'| RC-01 | row  CONTINUE', 1)
        self.assertNotEqual(rc_rows(altered)['RC-01'][0], rc_rows(data)['RC-01'][0])


class PlaceholderTest(unittest.TestCase):
    """AC4: the placeholder constraints of section 9, each failing on an altered copy, and its exceptions."""

    def failing(self, sid, change):
        v = copy.deepcopy(real(sid))
        change(v['cases'][0]['inputs'])
        return check_placeholders(v, sid)

    def test_each_constraint_fails_when_broken(self):
        cases = {
            'approved hash': lambda i: i.update(approved_contract_hash='0' * 64),
            'not an ancestor': lambda i: i.update(base_is_ancestor=False),
            'intent not current': lambda i: i.update(intent_current={'SPEC-003': 'v5'}),
            'runtime below a rule': lambda i: i['risk_rules'].append({'match': {'paths': ['src/app/**']}, 'risk': 'critical'}),
            'an unmatched write pattern': lambda i: i['contract']['write_set']['paths'].append('lib/**'),
            'an unresolved symbol': lambda i: i['symbols'][0].update(head=None),
            'an ambiguous schema': lambda i: i['schemas'][0].update(base='ambiguous'),
            'a dependency not DONE': lambda i: i['dependencies']['TASK-099'].update(state='IN_PROGRESS'),
            'stale evidence': lambda i: i['dependencies']['TASK-099'].update(stale_evidence=True),
            'an article violated': lambda i: i['articles'][0].update(violated=True),
            'an article without a result': lambda i: i['articles'][0].update(violated=None),
            'a budget used up': lambda i: i['budget_use']['tokens'].update(used='400k'),
            'Δ meets the read-set': lambda i: i.update(head_commit='b' * 40, commits=[{'id': 'c' * 40, 'paths': [{'path': 'src/app/util/helpers.py', 'change': 'modified'}], 'submitted': False}]),
        }
        for name, change in cases.items():
            self.assertNotEqual(self.failing('RC-01', change), [], name)

    def test_the_derived_read_set_must_miss_delta(self):
        self.assertNotEqual(self.failing('RC-02', lambda i: i.update(derived_read_set=['docs/notes.md'])), [])

    def test_section_9_exceptions_hold_only_for_their_scenario(self):
        for sid, change in (('RC-06', lambda i: i.update(intent_current={'SPEC-003': 'v5'})),
                            ('RC-09', lambda i: i['runtime'].update(max_risk='low')),
                            ('RC-07', lambda i: i['dependencies']['TASK-099'].update(state='STALE')),
                            ('RC-11', lambda i: i['dependencies']['TASK-099'].update(stale_evidence=True)),
                            ('RC-08', lambda i: i['articles'][0].update(violated=True)),
                            ('RC-10', lambda i: i['budget_use']['retries'].update(used=3))):
            self.assertEqual(self.failing(sid, change), [], sid)
            self.assertNotEqual(self.failing('RC-01', change), [], sid + ' on RC-01')


class GivenTest(unittest.TestCase):
    """AC5: each scenario's own Given, each failing on an altered copy."""

    def failing(self, sid, change):
        v = copy.deepcopy(real(sid))
        change(v['cases'][0]['inputs'])
        return check_given(v, sid)

    def test_every_given_holds(self):
        for sid in EXPECTED:
            self.assertEqual(check_given(real(sid), sid), [], sid)

    def test_each_given_fails_when_broken(self):
        cases = [
            ('RC-01', lambda i: i.update(head_commit='b' * 40)),
            ('RC-02', lambda i: i.update(commits=[], head_commit=i['contract']['input_state']['base_commit'])),
            ('RC-02', lambda i: i['commits'][0]['paths'][0].update(path='src/app/core/x.py')),
            ('RC-03', lambda i: i['commits'][0].update(submitted=True)),
            ('RC-03', lambda i: i['commits'][0]['paths'][0].update(path='docs/x.md')),
            ('RC-04', lambda i: i['symbols'][0].update(head='changed')),
            ('RC-04', lambda i: i['commits'][0]['paths'][0].update(path='docs/x.md')),
            ('RC-05', lambda i: i['symbols'][0].update(head=i['symbols'][0]['base'])),
            ('RC-06', lambda i: i.update(intent_current=dict(i['contract']['input_state']['intent_versions']))),
            ('RC-06', lambda i: i['commits'][0]['paths'].append({'path': 'docs/y.md', 'change': 'added'})),
            ('RC-06', lambda i: i['commits'][0]['paths'][0].update(path='src/app/util/helpers.py')),
            ('RC-07', lambda i: i['dependencies']['TASK-099'].update(state='DONE')),
            ('RC-08', lambda i: i['articles'][0].update(violated=False)),
            ('RC-09', lambda i: i['runtime'].update(max_risk='medium')),
            ('RC-10', lambda i: i['budget_use']['retries'].update(used=2)),
            ('RC-11', lambda i: i['dependencies']['TASK-099'].update(stale_evidence=False)),
        ]
        for sid, change in cases:
            self.assertNotEqual(self.failing(sid, change), [], sid)


class PatternTest(unittest.TestCase):
    """The two pattern forms of AC4, decided as specification 3 section 3 decides them."""

    def test_forms(self):
        self.assertTrue(pattern_ok('src/app/core/**'))
        self.assertTrue(pattern_ok('src/app/util/helpers.py'))
        for p in ('src/*.py', '**', '/abs', 'a\\b', ''):
            self.assertFalse(pattern_ok(p), p)

    def test_meets_and_matches(self):
        self.assertTrue(matches('src/app/**', 'src/app/x.py'))
        self.assertFalse(matches('src/app/**', 'src/application.py'))
        self.assertTrue(meets('src/**', 'src/app/core/**'))
        self.assertTrue(meets('src/app/x.py', 'src/app/**'))
        self.assertFalse(meets('src/app/x.py', 'src/app/y.py'))
        self.assertFalse(meets('docs/**', 'src/**'))


if __name__ == '__main__':
    unittest.main()
