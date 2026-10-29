"""Unit tests of the Risk Engine fixture of TASK-018 (docs/specs/conformance-files.md revision 7, sections 2, 5 and 10;
docs/tasks/TASK-018.yaml AC1 to AC5 and AC9): the file tests/conformance/fixtures_risk/risk_01.py against that document,
the bound scenario file and the risk rules.

The helpers below are repeated in the three test modules of TASK-018, because each CI test folder is discovered on its
own and an import between them is not allowed. Files are read as bytes with pathlib's read_bytes; the fixture module is
never imported or executed. The checks here are the tests' own: they import only the standard library, never the
conformance runner, the governor or the records module.
"""
import copy
import hashlib
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCENARIO_FILE = 'docs/pre-genesis/conformance-scenarios-initial.md'
RULES_FILE = 'docs/specs/risk-rules-gov-aieos.md'
FIXTURE = 'tests/conformance/fixtures_risk/risk_01.py'
FIRST, LAST = b"DATA = r'''", b"'''\n"
# RISK-01's Expected cell, held here as text and compared with the bound file (AC3).
EXPECTED_CELL = 'it is not classified low, and the low default profile is not applied'
RISKS = ('low', 'medium', 'high', 'critical')
LOW_DEFAULT = [{'dimension': 'functional', 'evidence_types': ['build', 'lint']}]
LOW_PAIRS = {('functional', 'build'), ('functional', 'lint')}
VALUE_KEYS = {'contract', 'changed_paths', 'risk_rules', 'owner_kept_rules', 'articles', 'default_profiles',
              'requirement_profiles', 'delegation', 'evidence_comparison', 'auto_accept', 'policy_version',
              'level_version', 'ruleset_version'}
CONTRACT_KEYS = {'traces_to', 'risk', 'owner_kept_act', 'verification_plan'}
REQUEST_KEYS = {'task_id', 'task_content_hash', 'evaluated_commit', 'intent_versions', 'task_state', 'changed_paths',
                'retry_count'}
STATES = ('DRAFT', 'READY', 'IN_PROGRESS', 'VERIFYING', 'ACCEPTED', 'DONE', 'IN_REVIEW', 'REWORK', 'ESCALATED',
          'REJECTED', 'BLOCKED', 'STALE')
# The keys of an observation record of spec 2 section 6.2 as the fixture uses them, and the DM B3 source classes.
RECORD_KEYS = {'record_id', 'fact_kind', 'source_class', 'recorder', 'subject', 'evidence_type', 'dimension', 'gate',
               'outcome', 'commit', 'intent_versions'}
SOURCE_CLASSES = ('agent_declared', 'same_lineage_review', 'deterministic_tool_local', 'deterministic_tool_external_ci',
                  'cross_vendor_review', 'decision_agent', 'human_authority', 'delegate_ai')
HEX64 = re.compile(r'[0-9a-f]{64}')
COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
TASK = re.compile(r'TASK-[0-9]+')
VERSION = re.compile(r'v[0-9]+')
GATE = re.compile(r'G[0-9]+')
PATTERN_NAME = re.compile(r'[A-Za-z0-9._*-]+')
PATH_NAME = re.compile(r'[A-Za-z0-9._-]+')


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
    raise ValueError('a value of type %s has no canonical form' % type(value).__name__)


def wrap(value):
    return FIRST + (canon(value) + '\n').encode('utf-8') + LAST


def unwrap(data):
    """The JSON value the file wraps (AC1), or ValueError: the two fixed parts, then canonical JSON."""
    if not data.startswith(FIRST) or not data.endswith(LAST) or len(data) < len(FIRST) + len(LAST):
        raise ValueError('the file does not start with the first part and end with the last part')
    text = data[len(FIRST):len(data) - len(LAST)]
    if b"'''" in text or b'\r' in text:
        raise ValueError("the JSON text holds ''' or a CR byte")
    value = json.loads(text.decode('utf-8'))
    if canon(value) + '\n' != text.decode('utf-8'):
        raise ValueError('the JSON text is not in the canonical form')
    return value


def risk_row():
    """RISK-01's row line of the bound scenario file and its cells."""
    lines = [l for l in read(SCENARIO_FILE).decode('utf-8').split('\n') if l.startswith('| RISK-01 | ')]
    if len(lines) != 1:
        raise ValueError('RISK-01 has not exactly one row')
    return lines[0], [c.strip() for c in lines[0].strip().strip('|').split('|')]


def policy_rules():
    """The rules of the risk rules' section 3 in {match, class} form, in order; R3, which matches component tags, by
    section 2 point 3's fail-closed reading (every path under src/** and tests/**)."""
    text = read(RULES_FILE).decode('utf-8')
    block = text.split('## 3. The rules')[1].split('```yaml')[1].split('```')[0]
    found = re.findall(r'^  # (R\d+), [^\n]*\n  - match: \{ (paths|component_tags): \[([^\]]*)\] \}\n    risk: (\w+)$',
                       block, re.M)
    if len(found) != block.count('- match:'):
        raise ValueError('a rule of section 3 was not read')
    out = []
    for rid, kind, items, cls in found:
        match = [x.strip().strip('"') for x in items.split(',')] if kind == 'paths' else ['src/**', 'tests/**']
        out.append((rid, {'match': match, 'class': cls}))
    return out, 'until then it matches every path under `src/**` and `tests/**`' in text


def pattern_ok(p):
    return isinstance(p, str) and bool(p) and all(
        PATTERN_NAME.fullmatch(n) and ('**' not in n or n == '**') and n not in ('.', '..') for n in p.split('/'))


def path_ok(p):
    return isinstance(p, str) and bool(p) and all(PATH_NAME.fullmatch(n) and n not in ('.', '..') for n in p.split('/'))


def matches(pattern, path):
    """The tests' own matcher of point 6's forms (risk rules section 2): a pattern without "/" is "**/" + pattern;
    "*" matches any part of one name; "**" any sequence of names, and a trailing "/**" at least one name."""
    if '/' not in pattern:
        pattern = '**/' + pattern
    parts = pattern.split('/')
    rx = ''
    for i, part in enumerate(parts):
        last = i == len(parts) - 1
        if part == '**':
            rx += '[^/]+(?:/[^/]+)*' if last else '(?:[^/]+/)*'
        else:
            rx += ''.join('[^/]*' if c == '*' else re.escape(c) for c in part) + ('' if last else '/')
    return re.fullmatch(rx, path) is not None


def _texts(v):
    return isinstance(v, list) and all(isinstance(x, str) and x for x in v)


def record_problems(rec):
    """The forms of one observation record of spec 2 section 6.2 as section 10's placeholder uses it."""
    if not isinstance(rec, dict) or set(rec) != RECORD_KEYS:
        return ['a record is not exactly the keys of an observation record']
    out = []
    for k in ('record_id', 'recorder', 'subject', 'evidence_type', 'dimension'):
        if not (isinstance(rec[k], str) and rec[k]):
            out.append('a record %s is not a non-empty string' % k)
    if rec['fact_kind'] != 'observation':
        out.append('a record is not an observation')
    if rec['source_class'] not in SOURCE_CLASSES:
        out.append('a record source_class is not of DM B3')
    if rec['outcome'] not in ('pass', 'fail', 'blocking'):
        out.append('a record outcome is not pass, fail or blocking')
    if not (isinstance(rec['commit'], str) and COMMIT.fullmatch(rec['commit'])):
        out.append('a record commit is not a full commit id')
    if not (isinstance(rec['gate'], str) and GATE.fullmatch(rec['gate'])):
        out.append('a record gate is not G followed by digits')
    iv = rec['intent_versions']
    if not (isinstance(iv, dict) and all(isinstance(k, str) and k and isinstance(v, str) and VERSION.fullmatch(v)
                                         for k, v in iv.items())):
        out.append('a record intent_versions is malformed')
    return out


def request_problems(req):
    """The forms of an evaluation request of spec 2 section 6.5."""
    if not isinstance(req, dict) or set(req) != REQUEST_KEYS:
        return ['the request is not exactly the keys of an evaluation request']
    out = []
    if not (isinstance(req['task_id'], str) and TASK.fullmatch(req['task_id'])):
        out.append('the request task_id is malformed')
    if not (isinstance(req['task_content_hash'], str) and HEX64.fullmatch(req['task_content_hash'])):
        out.append('the request task_content_hash is malformed')
    if not (isinstance(req['evaluated_commit'], str) and COMMIT.fullmatch(req['evaluated_commit'])):
        out.append('the request evaluated_commit is malformed')
    iv = req['intent_versions']
    if not (isinstance(iv, dict) and all(isinstance(v, str) and VERSION.fullmatch(v) for v in iv.values())):
        out.append('the request intent_versions is malformed')
    if req['task_state'] not in STATES:
        out.append('the request task_state is not a state')
    if not (_texts(req['changed_paths']) and req['changed_paths'] and all(path_ok(p) for p in req['changed_paths'])):
        out.append('the request changed_paths is malformed')
    rc = req['retry_count']
    if not (isinstance(rc, dict) and set(rc) == {'limit', 'used'} and all(
            isinstance(rc[k], int) and not isinstance(rc[k], bool) and rc[k] >= 0 for k in rc)):
        out.append('the request retry_count is malformed')
    return out


def profile_ok(profile):
    return isinstance(profile, list) and all(
        isinstance(e, dict) and set(e) == {'dimension', 'evidence_types'} and isinstance(e['dimension'], str)
        and e['dimension'] and _texts(e['evidence_types']) for e in profile)


def holds_low_pair(profile):
    return any((e['dimension'], t) in LOW_PAIRS for e in profile for t in e['evidence_types'])


def form_problems(value, row_hash):
    """AC2: the fixture's form (section 10's table)."""
    if not isinstance(value, dict) or set(value) != {'scenario', 'row_hash', 'cases'}:
        return ['the fixture is not exactly scenario, row_hash and cases']
    out = []
    if value['scenario'] != 'RISK-01' or value['row_hash'] != row_hash:
        out.append('scenario or row_hash is not RISK-01\'s')
    if not (isinstance(value['cases'], list) and value['cases']):
        return out + ['cases is not a non-empty list']
    for case in value['cases']:
        if not isinstance(case, dict) or set(case) != {'values', 'request', 'records', 'when', 'expected'}:
            out.append('a case is not exactly values, request, records, when and expected')
            continue
        v = case['values']
        if not isinstance(v, dict) or set(v) != VALUE_KEYS:
            out.append('values is not exactly the thirteen keys')
            continue
        c = v['contract']
        if not (isinstance(c, dict) and set(c) == CONTRACT_KEYS and _texts(c['traces_to'])
                and c['risk'] in RISKS and isinstance(c['owner_kept_act'], bool)
                and _texts(c['verification_plan']) and all(GATE.fullmatch(g) for g in c['verification_plan'])):
            out.append('values contract is malformed')
        if not (_texts(v['changed_paths']) and v['changed_paths'] and all(path_ok(p) for p in v['changed_paths'])):
            out.append('values changed_paths is malformed')
        if not (isinstance(v['risk_rules'], list) and all(
                isinstance(r, dict) and set(r) == {'match', 'class'} and _texts(r['match']) and r['match']
                and all(pattern_ok(p) for p in r['match']) and r['class'] in RISKS for r in v['risk_rules'])):
            out.append('values risk_rules is malformed')
        if not (isinstance(v['owner_kept_rules'], list) and all(
                isinstance(r, dict) and set(r) == {'match'} and _texts(r['match']) for r in v['owner_kept_rules'])):
            out.append('values owner_kept_rules is malformed')
        if not (isinstance(v['articles'], list) and all(
                isinstance(a, dict) and set(a) == {'id', 'scope', 'evidence_required'} and _texts(a['scope'])
                and a['scope'] and all(pattern_ok(p) for p in a['scope']) and _texts(a['evidence_required'])
                for a in v['articles'])):
            out.append('values articles is malformed')
        dp = v['default_profiles']
        if not (isinstance(dp, dict) and set(dp) == set(RISKS) and all(profile_ok(dp[k]) for k in RISKS)):
            out.append('values default_profiles is malformed')
        if not (isinstance(v['requirement_profiles'], list) and all(
                isinstance(r, dict) and set(r) == {'id', 'add'} and profile_ok(r['add']) for r in v['requirement_profiles'])):
            out.append('values requirement_profiles is malformed')
        if v['delegation'] not in (True, False, None):
            out.append('values delegation is malformed')
        ec = v['evidence_comparison']
        if not (ec is None or (isinstance(ec, dict) and set(ec) == {'weakens'} and isinstance(ec['weakens'], bool))):
            out.append('values evidence_comparison is malformed')
        aa = v['auto_accept']
        if not (isinstance(aa, dict) and set(aa) == set(RISKS) and all(isinstance(aa[k], bool) for k in RISKS)):
            out.append('values auto_accept is malformed')
        for k in ('policy_version', 'level_version', 'ruleset_version'):
            if not (isinstance(v[k], str) and v[k]):
                out.append('values %s is not a string' % k)
        out.extend(request_problems(case['request']))
        if isinstance(case['request'], dict) and case['request'].get('changed_paths') != v['changed_paths']:
            out.append('the request changed_paths differs from values changed_paths')
        if not (case['when'] == 'evaluate' and isinstance(case['request'], dict)
                and case['request'].get('task_state') == 'VERIFYING'):
            out.append('when is not evaluate with task_state VERIFYING')
        recs = case['records']
        if not isinstance(recs, list):
            out.append('records is not a list')
        else:
            for rec in recs:
                out.extend(record_problems(rec))
            ids = [r.get('record_id') for r in recs if isinstance(r, dict)]
            if len(ids) != len(set(ids)):
                out.append('a repeated record id')
        exp = case['expected']
        if not isinstance(exp, dict) or set(exp) != {'risk_not', 'profile_excludes', 'not_fixed'}:
            out.append('expected is not exactly risk_not, profile_excludes and not_fixed')
    return out


def faithfulness_problems(value):
    """AC3: expected comes only from RISK-01's Expected cell."""
    out = []
    for case in value['cases']:
        exp = case['expected']
        if exp['risk_not'] != ['low']:
            out.append('risk_not is not ["low"]')
        pairs = exp['profile_excludes']
        if not (isinstance(pairs, list) and len(pairs) == 2 and all(
                isinstance(p, dict) and set(p) == {'dimension', 'evidence_type'} for p in pairs)
                and {(p['dimension'], p['evidence_type']) for p in pairs} == LOW_PAIRS):
            out.append('profile_excludes is not exactly the two pairs of the low default')
        if not (isinstance(exp['not_fixed'], list) and sorted(exp['not_fixed']) == ['decision', 'next_state']):
            out.append('not_fixed is not exactly decision and next_state')
    return out


def placeholder_problems(value):
    """AC4: section 10's placeholders."""
    out = []
    for case in value['cases']:
        v, req, recs = case['values'], case['request'], case['records']
        if v['contract']['risk'] != 'low' or v['contract']['owner_kept_act'] is not False:
            out.append('contract.risk is not low or owner_kept_act is not false')
        dp = v['default_profiles']
        if dp['low'] != LOW_DEFAULT:
            out.append('default_profiles does not give low exactly the low default')
        if any(holds_low_pair(dp[k]) for k in ('medium', 'high', 'critical')):
            out.append('a profile of another class holds a pair of the low default')
        if v['requirement_profiles'] != []:
            out.append('requirement_profiles is not []')
        if v['owner_kept_rules'] != []:
            out.append('owner_kept_rules is not []')
        if v['delegation'] is not True:
            out.append('delegation is not true')
        if v['evidence_comparison'] != {'weakens': False}:
            out.append('evidence_comparison is not {weakens: false}')
        if any(v['auto_accept'][k] is not False for k in RISKS):
            out.append('auto_accept is not false for every class')
        if v['articles'] != []:
            out.append('articles is not []')
        if any(matches(p, path) for a in v['articles'] for p in a['scope'] for path in v['changed_paths']):
            out.append('an article\'s scope meets a changed path')
        c = req['evaluated_commit']
        for g in v['contract']['verification_plan']:
            if not any(r['gate'] == g and r['outcome'] == 'pass' and r['commit'] == c for r in recs):
                out.append('no passing record of the evaluated commit for gate %s' % g)
        for dim, typ in sorted(LOW_PAIRS):
            if not any(r['dimension'] == dim and r['evidence_type'] == typ and r['outcome'] == 'pass'
                       and r['commit'] == c for r in recs):
                out.append('no passing record of the evaluated commit for type %s' % typ)
    return out


def rules_problems(value, rules):
    """AC5: the policy's rules as values, and the Given: no changed path is matched by any rule or article scope."""
    out = []
    for case in value['cases']:
        v = case['values']
        if v['risk_rules'] != [r for _, r in rules]:
            out.append('risk_rules is not the policy of section 3 in order')
        for path in v['changed_paths']:
            if any(matches(p, path) for r in v['risk_rules'] for p in r['match']):
                out.append('a rule matches the changed path %s' % path)
            if any(matches(p, path) for a in v['articles'] for p in a['scope']):
                out.append('an article\'s scope matches the changed path %s' % path)
    return out


def all_problems(data):
    try:
        value = unwrap(data)
    except ValueError as exc:
        return ['AC1: ' + str(exc)]
    line, _ = risk_row()
    out = form_problems(value, sha256(line.encode('utf-8')))
    if out:
        return out
    rules, _ = policy_rules()
    return faithfulness_problems(value) + placeholder_problems(value) + rules_problems(value, rules)


class Ac1FileKindTest(unittest.TestCase):

    def test_the_file_is_wrapped_canonical_json(self):
        data = read(FIXTURE)
        value = unwrap(data)
        self.assertEqual(wrap(value), data)
        self.assertNotIn(b'\r', data)
        self.assertEqual(data.count(b"'''"), 2)

    def test_altered_wrappings_fail(self):
        data = read(FIXTURE)
        for bad in (data.replace(FIRST, b"DATA = '''", 1), data[:-1], data.replace(b'\n', b'\r\n'),
                    data.replace(b'  "cases"', b'"cases"', 1), FIRST + json.dumps(unwrap(data)).encode() + LAST):
            self.assertTrue(all_problems(bad), bad[:40])
            self.assertTrue(all_problems(bad)[0].startswith('AC1: '))

    def test_the_path_and_folder(self):
        # The CI's G1 build step compiles src and tests, so a __pycache__ folder may be there; it alone is skipped.
        self.assertEqual(sorted(p.name for p in (ROOT / 'tests/conformance/fixtures_risk').glob('*')
                                if not (p.name == '__pycache__' and p.is_dir())), ['risk_01.py'])


class Ac2FormTest(unittest.TestCase):

    def setUp(self):
        self.value = unwrap(read(FIXTURE))
        line, _ = risk_row()
        self.row_hash = sha256(line.encode('utf-8'))

    def test_the_file_is_well_formed(self):
        self.assertEqual(form_problems(self.value, self.row_hash), [])
        self.assertEqual(all_problems(read(FIXTURE)), [])

    def test_the_row_hash_is_recomputed(self):
        self.assertEqual(self.value['row_hash'], self.row_hash)
        self.assertEqual(self.value['scenario'], 'RISK-01')

    def bad(self, change, why):
        v = copy.deepcopy(self.value)
        change(v)
        problems = form_problems(v, self.row_hash)
        self.assertIn(why, problems)
        self.assertTrue(all_problems(wrap(v)))

    def test_each_malformed_condition(self):
        case = lambda v: v['cases'][0]
        self.bad(lambda v: v.update(extra=1), 'the fixture is not exactly scenario, row_hash and cases')
        self.bad(lambda v: v.update(scenario='RISK-02'), 'scenario or row_hash is not RISK-01\'s')
        self.bad(lambda v: v.update(row_hash='0' * 64), 'scenario or row_hash is not RISK-01\'s')
        self.bad(lambda v: v.update(cases=[]), 'cases is not a non-empty list')
        self.bad(lambda v: case(v).pop('when'), 'a case is not exactly values, request, records, when and expected')
        self.bad(lambda v: case(v)['values'].pop('articles'), 'values is not exactly the thirteen keys')
        self.bad(lambda v: case(v)['values']['contract'].update(risk='none'), 'values contract is malformed')
        self.bad(lambda v: case(v)['values'].update(changed_paths=[]), 'values changed_paths is malformed')
        self.bad(lambda v: case(v)['values']['risk_rules'][0].update(match=['docs/***']), 'values risk_rules is malformed')
        self.bad(lambda v: case(v)['values']['risk_rules'][0].update(match=[]), 'values risk_rules is malformed')
        self.bad(lambda v: case(v)['values']['risk_rules'][0].update(**{'class': 'none'}), 'values risk_rules is malformed')
        self.bad(lambda v: case(v)['values'].update(owner_kept_rules=[{}]), 'values owner_kept_rules is malformed')
        self.bad(lambda v: case(v)['values'].update(articles=[{'id': 'X', 'scope': [], 'evidence_required': ['a']}]),
                 'values articles is malformed')
        self.bad(lambda v: case(v)['values']['default_profiles'].pop('high'), 'values default_profiles is malformed')
        self.bad(lambda v: case(v)['values'].update(requirement_profiles=[{'id': 'R'}]), 'values requirement_profiles is malformed')
        self.bad(lambda v: case(v)['values'].update(delegation='yes'), 'values delegation is malformed')
        self.bad(lambda v: case(v)['values'].update(evidence_comparison={'weakens': 'no'}), 'values evidence_comparison is malformed')
        self.bad(lambda v: case(v)['values']['auto_accept'].update(low='no'), 'values auto_accept is malformed')
        self.bad(lambda v: case(v)['values'].update(policy_version=''), 'values policy_version is not a string')
        self.bad(lambda v: case(v)['request'].update(task_id='T-1'), 'the request task_id is malformed')
        self.bad(lambda v: case(v)['request'].update(changed_paths=['other/file.txt']),
                 'the request changed_paths differs from values changed_paths')
        self.bad(lambda v: case(v)['request'].update(task_state='DRAFT'), 'when is not evaluate with task_state VERIFYING')
        self.bad(lambda v: case(v).update(when='resume'), 'when is not evaluate with task_state VERIFYING')
        self.bad(lambda v: case(v)['records'][0].update(commit='abc'), 'a record commit is not a full commit id')
        self.bad(lambda v: case(v)['records'][0].update(source_class='an_agent'), 'a record source_class is not of DM B3')
        self.bad(lambda v: case(v)['records'][1].update(record_id=case(v)['records'][0]['record_id']), 'a repeated record id')
        self.bad(lambda v: case(v)['expected'].pop('not_fixed'),
                 'expected is not exactly risk_not, profile_excludes and not_fixed')

    def test_each_further_malformed_condition(self):
        """The request, record and contract conditions that test_each_malformed_condition leaves out, each alone."""
        case = lambda v: v['cases'][0]
        self.bad(lambda v: case(v)['request'].update(retry_count={'limit': -1, 'used': 0}), 'the request retry_count is malformed')
        self.bad(lambda v: case(v)['request'].update(intent_versions={'X': '1'}), 'the request intent_versions is malformed')
        self.bad(lambda v: case(v)['request'].update(task_content_hash='0' * 63), 'the request task_content_hash is malformed')
        self.bad(lambda v: case(v)['request'].update(extra=1), 'the request is not exactly the keys of an evaluation request')
        self.bad(lambda v: case(v)['records'][0].update(gate='0'), 'a record gate is not G followed by digits')
        self.bad(lambda v: case(v)['records'][0].update(outcome='ok'), 'a record outcome is not pass, fail or blocking')
        self.bad(lambda v: case(v)['records'][0].update(intent_versions={'X': '1'}), 'a record intent_versions is malformed')
        self.bad(lambda v: case(v)['records'][0].update(extra=1), 'a record is not exactly the keys of an observation record')
        self.bad(lambda v: case(v)['values']['contract'].update(extra=1), 'values contract is malformed')

    def test_the_request_and_records_forms(self):
        case = self.value['cases'][0]
        self.assertEqual(request_problems(case['request']), [])
        for rec in case['records']:
            self.assertEqual(record_problems(rec), [])
        self.assertTrue(request_problems({}))
        self.assertTrue(record_problems({'record_id': 'x'}))


class Ac3FaithfulnessTest(unittest.TestCase):

    def setUp(self):
        self.value = unwrap(read(FIXTURE))

    def test_the_expected_cell_is_the_bound_one(self):
        _, cells = risk_row()
        self.assertEqual(cells[0], 'RISK-01')
        self.assertEqual(cells[4], EXPECTED_CELL)
        self.assertEqual(cells[2], 'a change that matches no risk rule')
        self.assertEqual(len(cells), 6)

    def test_expected_comes_only_from_the_cell(self):
        self.assertEqual(faithfulness_problems(self.value), [])
        exp = self.value['cases'][0]['expected']
        self.assertEqual(exp['risk_not'], ['low'])
        self.assertEqual(exp['profile_excludes'], [{'dimension': 'functional', 'evidence_type': 'build'},
                                                   {'dimension': 'functional', 'evidence_type': 'lint'}])
        self.assertEqual(exp['not_fixed'], ['decision', 'next_state'])

    def test_other_lists_fail(self):
        for key, val, why in (
                ('risk_not', ['low', 'medium'], 'risk_not is not ["low"]'),
                ('risk_not', [], 'risk_not is not ["low"]'),
                ('profile_excludes', [{'dimension': 'functional', 'evidence_type': 'build'}],
                 'profile_excludes is not exactly the two pairs of the low default'),
                ('profile_excludes', [{'dimension': 'functional', 'evidence_type': 'build'},
                                      {'dimension': 'functional', 'evidence_type': 'unit_test'}],
                 'profile_excludes is not exactly the two pairs of the low default'),
                ('not_fixed', ['decision'], 'not_fixed is not exactly decision and next_state'),
                ('not_fixed', ['decision', 'next_state', 'missing'], 'not_fixed is not exactly decision and next_state')):
            v = copy.deepcopy(self.value)
            v['cases'][0]['expected'][key] = val
            self.assertIn(why, faithfulness_problems(v))
            self.assertIn(why, all_problems(wrap(v)))

    def test_no_expected_element_names_a_value_of_the_case(self):
        """No string of the request or the records appears in the expected element, so it does not depend on them."""
        case = self.value['cases'][0]
        req = case['request']
        taken = [req['task_id'], req['task_content_hash'], req['evaluated_commit']] + sorted(req['intent_versions'].values())
        taken += [r['record_id'] for r in case['records']]
        text = canon(case['expected'])
        for s in taken:
            self.assertNotIn(s, text, s)

    def test_no_expected_element_depends_on_a_placeholder(self):
        exp = self.value['cases'][0]['expected']
        text = canon(exp)
        for placeholder in ('SPEC-', 'TASK-', 'G0', 'unmatched', 'v1', 'v2'):
            self.assertNotIn(placeholder, text)


class Ac4PlaceholdersTest(unittest.TestCase):

    def setUp(self):
        self.value = unwrap(read(FIXTURE))

    def test_the_placeholders_hold(self):
        self.assertEqual(placeholder_problems(self.value), [])
        self.assertEqual(self.value['cases'][0]['values']['articles'], [])

    def test_each_placeholder_broken_fails(self):
        def v_(v):
            return v['cases'][0]['values']
        cases = (
            (lambda v: v_(v)['contract'].update(risk='medium'), 'contract.risk is not low or owner_kept_act is not false'),
            (lambda v: v_(v)['contract'].update(owner_kept_act=True), 'contract.risk is not low or owner_kept_act is not false'),
            (lambda v: v_(v)['default_profiles'].update(low=[{'dimension': 'functional', 'evidence_types': ['build']}]),
             'default_profiles does not give low exactly the low default'),
            (lambda v: v_(v)['default_profiles'].update(high=[{'dimension': 'functional', 'evidence_types': ['lint']}]),
             'a profile of another class holds a pair of the low default'),
            (lambda v: v_(v).update(requirement_profiles=[{'id': 'R1', 'add': []}]), 'requirement_profiles is not []'),
            (lambda v: v_(v).update(owner_kept_rules=[{'match': ['x/**']}]), 'owner_kept_rules is not []'),
            (lambda v: v_(v).update(delegation=False), 'delegation is not true'),
            (lambda v: v_(v).update(evidence_comparison=None), 'evidence_comparison is not {weakens: false}'),
            (lambda v: v_(v)['auto_accept'].update(critical=True), 'auto_accept is not false for every class'),
            (lambda v: v_(v).update(articles=[{'id': 'SEC-003', 'scope': ['.github/**'], 'evidence_required': ['x']}]),
             'articles is not []'),
            (lambda v: v_(v).update(articles=[{'id': 'SEC-001', 'scope': ['**'], 'evidence_required': ['x']}]),
             'an article\'s scope meets a changed path'),
            (lambda v: v['cases'][0]['records'].pop(0), 'no passing record of the evaluated commit for gate G0'),
            (lambda v: v['cases'][0]['records'][1].update(outcome='fail'), 'no passing record of the evaluated commit for type build'),
            (lambda v: v['cases'][0]['records'][2].update(commit='b' * 40), 'no passing record of the evaluated commit for type lint'),
        )
        for change, why in cases:
            v = copy.deepcopy(self.value)
            change(v)
            self.assertIn(why, placeholder_problems(v), why)


class Ac5RulesTest(unittest.TestCase):

    def setUp(self):
        self.value = unwrap(read(FIXTURE))
        self.rules, self.fail_closed = policy_rules()

    def test_the_policy_is_read_rule_by_rule(self):
        self.assertTrue(self.fail_closed)
        self.assertEqual([rid for rid, _ in self.rules], ['R%d' % i for i in range(1, 14)])
        got = self.value['cases'][0]['values']['risk_rules']
        self.assertEqual(len(got), len(self.rules))
        for (rid, want), have in zip(self.rules, got):
            self.assertEqual(have, want, rid)
        self.assertEqual(got[2], {'match': ['src/**', 'tests/**'], 'class': 'high'})
        self.assertEqual(rules_problems(self.value, self.rules), [])

    def test_every_pattern_is_well_formed(self):
        for r in self.value['cases'][0]['values']['risk_rules']:
            for p in r['match']:
                self.assertTrue(pattern_ok(p), p)
        for p in self.value['cases'][0]['values']['changed_paths']:
            self.assertTrue(path_ok(p), p)

    def test_the_given_holds(self):
        v = self.value['cases'][0]['values']
        for path in v['changed_paths']:
            self.assertFalse(any(matches(p, path) for r in v['risk_rules'] for p in r['match']), path)

    def test_a_changed_rule_list_fails(self):
        for change, why in (
                (lambda rr: rr.pop(), 'risk_rules is not the policy of section 3 in order'),
                (lambda rr: rr.reverse(), 'risk_rules is not the policy of section 3 in order'),
                (lambda rr: rr[2].update(match=['src/auth/**']), 'risk_rules is not the policy of section 3 in order'),
                (lambda rr: rr[0].update(**{'class': 'medium'}), 'risk_rules is not the policy of section 3 in order')):
            v = copy.deepcopy(self.value)
            change(v['cases'][0]['values']['risk_rules'])
            self.assertIn(why, rules_problems(v, self.rules))

    def test_a_path_a_rule_matches_breaks_the_given(self):
        for path in ('docs/x.md', 'README.md', 'src/a.py', 'tests/conformance/x.py', '.github/w.yml', 'a/contracts/b'):
            v = copy.deepcopy(self.value)
            v['cases'][0]['values']['changed_paths'] = [path]
            v['cases'][0]['request']['changed_paths'] = [path]
            self.assertIn('a rule matches the changed path %s' % path, rules_problems(v, self.rules), path)

    def test_an_article_scope_that_matches_breaks_the_given(self):
        """An article whose scope meets a changed path is named by the rules check, for each changed path."""
        for path in self.value['cases'][0]['values']['changed_paths']:
            v = copy.deepcopy(self.value)
            v['cases'][0]['values']['articles'] = [{'id': 'X', 'scope': ['**'], 'evidence_required': ['x']}]
            self.assertIn("an article's scope matches the changed path %s" % path, rules_problems(v, self.rules), path)

    def test_the_matcher_follows_point_6(self):
        for pattern, path, want in (
                ('docs/**', 'docs/a.md', True), ('docs/**', 'docs', False), ('docs/**', 'docs/x/y.md', True),
                ('*.md', 'a.md', True), ('*.md', 'x/y/a.md', True), ('*.md', 'a.mdx', False),
                ('**/contracts/**', 'a/contracts/b', True), ('**/contracts/**', 'contracts/b', True),
                ('contracts/**', 'a/contracts/b', False), ('docs/pre-genesis/CR-*.md', 'docs/pre-genesis/CR-001.md', True),
                ('docs/pre-genesis/CR-*.md', 'docs/pre-genesis/x/CR-001.md', False), ('CLAUDE.md', 'x/CLAUDE.md', True),
                ('.gitignore', '.gitignore', True), ('src/**', 'unmatched/file.txt', False),
                ('Docs/**', 'docs/a.md', False)):
            self.assertEqual(matches(pattern, path), want, (pattern, path))

    def test_the_three_readings_and_case(self):
        """The readings of point 6 that the property module's second reading shares, and case, each pinned by a case."""
        for pattern, path, want in (
                ('a*.md', 'a.md', True), ('a/**/b', 'a/b', True), ('a/**', 'a/b', True), ('a/**', 'a', False),
                ('*.MD', 'a.md', False), ('docs/**', 'DOCS/a.md', False), ('CLAUDE.md', 'x/claude.md', False)):
            self.assertEqual(matches(pattern, path), want, (pattern, path))

    def test_ill_formed_patterns_and_paths(self):
        for p in ('', '/docs', 'docs/', 'a//b', 'a/***/b', 'a/b**', 'a/./b', 'a/../b', 'a b', 'a?'):
            self.assertFalse(pattern_ok(p), p)
        for p in ('', 'a/*', '/a', 'a/', 'a/../b', '.'):
            self.assertFalse(path_ok(p), p)


if __name__ == '__main__':
    unittest.main()
