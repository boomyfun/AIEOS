"""Unit tests of the Capability Boundaries fixture of TASK-057 (docs/specs/conformance-files.md revision 10, sections 2,
5 and 11; docs/tasks/TASK-057.yaml AC1 to AC6 and AC10): the file tests/conformance/fixtures_cb/adv_02.py against that
document and the bound scenario file.

The helpers below are repeated in the three test modules of TASK-057, because each CI test folder is discovered on its
own and an import between them is not allowed. Files are read as bytes with pathlib's read_bytes; the fixture module is
never imported or executed. The checks here are the tests' own: they import only the standard library, never the
conformance runner, the core or the records module, and they never run the core (decision D-1086). The key lists are
held here as values; that they equal the runner's and replay's at base_commit is checked outside the tests (AC2).
"""
import copy
import hashlib
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCENARIO_FILE = 'docs/pre-genesis/conformance-scenarios-initial.md'
FIXTURE = 'tests/conformance/fixtures_cb/adv_02.py'
FIRST, LAST = b"DATA = r'''", b"'''\n"
# ADV-02's Expected cell, held here as text and compared with the bound file (AC3).
EXPECTED_CELL = "STOP: violation; the change is rejected; the violation is recorded in the runtime's and the agent's metrics"
EXPECTED = {'stop': ['STOP: violation'], 'decision': ['REJECT'], 'next_state': ['REJECTED'], 'not_fixed': ['metrics']}
RISKS = ('low', 'medium', 'high', 'critical')
LOW_DEFAULT = [{'dimension': 'functional', 'evidence_types': ['build', 'lint']}]
LOW_PAIRS = {('functional', 'build'), ('functional', 'lint')}
GATES = ('G0', 'G1', 'G2')
# The key lists of section 11's table and of replay.replay's document form (AC2).
CASE_KEYS = {'document', 'continuation', 'evaluation', 'given', 'expected'}
DOCUMENT_KEYS = {'replay_id', 'recorder', 'epoch', 'setup', 'session', 'submission', 'end_at', 'violation'}
SETUP_KEYS = {'type', 'payload', 'event_id', 'appended_at', 'task_id'}
SESSION_KEYS = {'task_id', 'session_id', 'holder', 'inputs', 'code_sha256', 'start_at', 'expires_at', 'expected_token'}
SUBMISSION_KEYS = {'commit_id', 'commit_text', 'event_id', 'at'}
VIOLATION_KEYS = {'observation', 'event_id', 'at'}
OBSERVATION_KEYS = {'record_id', 'fact_kind', 'source_class', 'recorder', 'subject', 'evidence_type', 'outcome',
                    'blocking_kind', 'refers_to'}
CONTINUATION_KEYS = {'session', 'submission', 'end_at'}
EVALUATION_KEYS = {'task_id', 'contract_text', 'declared', 'values', 'extra_records', 'recorder', 'now', 'commits'}
COMMIT_KEYS = {'id', 'text', 'paths'}
GIVEN_KEYS = {'outside_path', 'write_set'}
EXPECTED_KEYS = {'stop', 'decision', 'next_state', 'not_fixed'}
DECLARED_KEYS = {'intent_versions', 'retries'}
VALUE_KEYS = {'contract', 'changed_paths', 'risk_rules', 'owner_kept_rules', 'articles', 'default_profiles',
              'requirement_profiles', 'delegation', 'evidence_comparison', 'auto_accept', 'policy_version',
              'level_version', 'ruleset_version'}
CONTRACT_KEYS = {'traces_to', 'risk', 'owner_kept_act', 'verification_plan'}
RC_INPUT_KEYS = {'task_id', 'log_seq', 'task_state', 'contract', 'contract_hash', 'approved_contract_hash',
                 'head_commit', 'base_is_ancestor', 'commits', 'components', 'interfaces', 'symbols', 'schemas',
                 'derived_read_set', 'observed_read_set', 'intent_current', 'dependencies', 'articles', 'runtime',
                 'risk_rules', 'policy_version', 'budget_use'}
# The keys of an observation record of spec 2 section 6.2 as the extra records use them: a gate result, or a record of
# an evidence type with its dimension.
GATE_RECORD_KEYS = {'record_id', 'fact_kind', 'source_class', 'recorder', 'subject', 'gate', 'outcome', 'commit',
                    'intent_versions'}
TYPE_RECORD_KEYS = {'record_id', 'fact_kind', 'source_class', 'recorder', 'subject', 'evidence_type', 'dimension',
                    'outcome', 'commit', 'intent_versions'}
SOURCE_CLASSES = ('agent_declared', 'same_lineage_review', 'deterministic_tool_local', 'deterministic_tool_external_ci',
                  'cross_vendor_review', 'decision_agent', 'human_authority', 'delegate_ai')
HEX40 = re.compile(r'[0-9a-f]{40}')
HEX64 = re.compile(r'[0-9a-f]{64}')
TASK = re.compile(r'TASK-[0-9]+')
VERSION = re.compile(r'v[0-9]+')
GATE = re.compile(r'G[0-9]+')
TIME = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z')
PATTERN_NAME = re.compile(r'[A-Za-z0-9._*-]+')
PATH_NAME = re.compile(r'[A-Za-z0-9._-]+')
TRAILER = re.compile(r'([A-Za-z][A-Za-z0-9-]*): (.+)')
AMOUNT = re.compile(r'([0-9]+)(k|m|h)?')


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


def adv_row():
    """ADV-02's row line of the bound scenario file and its cells."""
    lines = [l for l in read(SCENARIO_FILE).decode('utf-8').split('\n') if l.startswith('| ADV-02 | ')]
    if len(lines) != 1:
        raise ValueError('ADV-02 has not exactly one row')
    return lines[0], [c.strip() for c in lines[0].strip().strip('|').split('|')]


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


def sample_path(pattern):
    """One path a pattern matches: each "**" and each "*" becomes the name "x" (the tests' reading of "a rule meets a
    write_set pattern", section 9's placeholders)."""
    names = ['x' if n == '**' else n.replace('*', 'x') for n in pattern.split('/')]
    return '/'.join(names)


def contract_write_set(text):
    """The write_set.paths of a contract text written as "write_set:" followed by "  paths: [a, b]", or None."""
    lines = text.split('\n')
    at = [i for i, l in enumerate(lines) if l == 'write_set:']
    if len(at) != 1 or at[0] + 1 >= len(lines):
        return None
    m = re.fullmatch(r'  paths: \[(.*)\]', lines[at[0] + 1])
    if not m:
        return None
    return [x.strip() for x in m.group(1).split(',')] if m.group(1).strip() else []


def commit_parts(text):
    """(parents, message) of a commit's cat-file text, or None when it has no blank line."""
    if '\n\n' not in text:
        return None
    head, message = text.split('\n\n', 1)
    return [l[len('parent '):] for l in head.split('\n') if l.startswith('parent ')], message


def trailers(message):
    """The trailer lines of a message's last paragraph, as (key, value) pairs; [] when it is not all trailers."""
    paragraphs = [p for p in message.split('\n\n') if p.strip()]
    if not paragraphs:
        return []
    found = [TRAILER.fullmatch(l) for l in paragraphs[-1].strip('\n').split('\n')]
    return [(m.group(1), m.group(2)) for m in found] if all(found) else []


def _texts(v):
    return isinstance(v, list) and all(isinstance(x, str) and x for x in v)


def _text(v):
    return isinstance(v, str) and bool(v)


def session_problems(s, label):
    """The form of one session object of replay.replay's document (AC2)."""
    if not isinstance(s, dict) or set(s) != SESSION_KEYS:
        return ['%s is not exactly the keys of a session' % label]
    out = []
    for k in ('task_id', 'session_id', 'holder'):
        if not _text(s[k]):
            out.append('%s %s is not a non-empty string' % (label, k))
    if not (isinstance(s['code_sha256'], str) and HEX64.fullmatch(s['code_sha256'])):
        out.append('%s code_sha256 is not 64 hex digits' % label)
    for k in ('start_at', 'expires_at'):
        if not (isinstance(s[k], str) and TIME.fullmatch(s[k])):
            out.append('%s %s is not a time' % (label, k))
    tok = s['expected_token']
    if not (isinstance(tok, dict) and set(tok) == {'epoch', 'counter'} and _text(tok['epoch'])
            and isinstance(tok['counter'], int) and not isinstance(tok['counter'], bool)):
        out.append('%s expected_token is not {epoch, counter}' % label)
    if not (isinstance(s['inputs'], dict) and set(s['inputs']) == RC_INPUT_KEYS):
        out.append('%s inputs is not exactly the Resume Check inputs' % label)
    return out


def record_problems(rec):
    """The form of one extra record of spec 2 section 6.2: a gate result or a typed record (AC5)."""
    if not isinstance(rec, dict) or set(rec) not in (GATE_RECORD_KEYS, TYPE_RECORD_KEYS):
        return ['an extra record is not exactly the keys of a gate result or of a typed record']
    out = []
    for k in ('record_id', 'recorder', 'subject'):
        if not _text(rec[k]):
            out.append('an extra record %s is not a non-empty string' % k)
    if rec['fact_kind'] != 'observation':
        out.append('an extra record is not an observation')
    if rec['source_class'] not in SOURCE_CLASSES:
        out.append('an extra record source_class is not of DM B3')
    if rec['outcome'] not in ('pass', 'fail', 'blocking'):
        out.append('an extra record outcome is not pass, fail or blocking')
    if not (isinstance(rec['commit'], str) and HEX40.fullmatch(rec['commit'])):
        out.append('an extra record commit is not a full commit id')
    if 'gate' in rec and not (isinstance(rec['gate'], str) and GATE.fullmatch(rec['gate'])):
        out.append('an extra record gate is not G followed by digits')
    iv = rec['intent_versions']
    if not (isinstance(iv, dict) and all(_text(k) and isinstance(v, str) and VERSION.fullmatch(v) for k, v in iv.items())):
        out.append('an extra record intent_versions is malformed')
    return out


def form_problems(value, row_hash):
    """AC2: the fixture's form (section 11's table)."""
    if not isinstance(value, dict) or set(value) != {'scenario', 'row_hash', 'cases'}:
        return ['the fixture is not exactly scenario, row_hash and cases']
    out = []
    if value['scenario'] != 'ADV-02' or value['row_hash'] != row_hash:
        out.append("scenario or row_hash is not ADV-02's")
    cases = value['cases']
    if not (isinstance(cases, list) and len(cases) == 1):
        return out + ['cases is not a list of exactly one case']
    case = cases[0]
    if not isinstance(case, dict) or set(case) != CASE_KEYS:
        return out + ['the case is not exactly document, continuation, evaluation, given and expected']
    doc = case['document']
    if not isinstance(doc, dict) or set(doc) != DOCUMENT_KEYS:
        out.append("the document is not exactly replay's document keys and violation")
    else:
        for k in ('replay_id', 'recorder', 'epoch'):
            if not _text(doc[k]):
                out.append('the document %s is not a non-empty string' % k)
        if doc['submission'] is not None:
            out.append('the document submission is not null')
        if not (isinstance(doc['setup'], list) and doc['setup'] and all(
                isinstance(e, dict) and set(e) == SETUP_KEYS and _text(e['type']) and isinstance(e['payload'], dict)
                and _text(e['event_id']) and isinstance(e['appended_at'], str) and TIME.fullmatch(e['appended_at'])
                and _text(e['task_id']) for e in doc['setup'])):
            out.append('the document setup is not a non-empty list of setup events')
        out.extend(session_problems(doc['session'], 'the document session'))
        if not (isinstance(doc['end_at'], str) and TIME.fullmatch(doc['end_at'])):
            out.append('the document end_at is not a time')
        vio = doc['violation']
        if not (isinstance(vio, dict) and set(vio) == VIOLATION_KEYS and _text(vio['event_id'])
                and isinstance(vio['at'], str) and TIME.fullmatch(vio['at'])
                and isinstance(vio['observation'], dict) and set(vio['observation']) == OBSERVATION_KEYS):
            out.append('the document violation is not exactly observation, event_id and at')
    cont = case['continuation']
    if not isinstance(cont, dict) or set(cont) != CONTINUATION_KEYS:
        out.append('the continuation is not exactly session, submission and end_at')
    else:
        out.extend(session_problems(cont['session'], 'the continuation session'))
        sub = cont['submission']
        if not (isinstance(sub, dict) and set(sub) == SUBMISSION_KEYS and isinstance(sub['commit_id'], str)
                and HEX40.fullmatch(sub['commit_id']) and _text(sub['commit_text']) and _text(sub['event_id'])
                and isinstance(sub['at'], str) and TIME.fullmatch(sub['at'])):
            out.append('the continuation submission is not a submission')
        if not (isinstance(cont['end_at'], str) and TIME.fullmatch(cont['end_at'])):
            out.append('the continuation end_at is not a time')
    ev = case['evaluation']
    if not isinstance(ev, dict) or set(ev) != EVALUATION_KEYS:
        out.append('the evaluation is not exactly the keys of section 11')
    else:
        if not (isinstance(ev['task_id'], str) and TASK.fullmatch(ev['task_id'])):
            out.append('the evaluation task_id is malformed')
        if not _text(ev['contract_text']):
            out.append('the evaluation contract_text is not a non-empty string')
        d = ev['declared']
        if not (isinstance(d, dict) and set(d) == DECLARED_KEYS and isinstance(d['intent_versions'], dict)
                and isinstance(d['retries'], int) and not isinstance(d['retries'], bool)):
            out.append('the evaluation declared is not {intent_versions, retries}')
        v = ev['values']
        if not (isinstance(v, dict) and set(v) == VALUE_KEYS and isinstance(v['contract'], dict)
                and set(v['contract']) == CONTRACT_KEYS):
            out.append('the evaluation values is not exactly the thirteen keys with the contract\'s four')
        if not isinstance(ev['extra_records'], list):
            out.append('the evaluation extra_records is not a list')
        if not _text(ev['recorder']):
            out.append('the evaluation recorder is not a non-empty string')
        if not (isinstance(ev['now'], str) and TIME.fullmatch(ev['now'])):
            out.append('the evaluation now is not a time')
        if not (isinstance(ev['commits'], list) and ev['commits'] and all(
                isinstance(c, dict) and set(c) == COMMIT_KEYS and isinstance(c['id'], str) and HEX40.fullmatch(c['id'])
                and _text(c['text']) and _texts(c['paths']) and c['paths'] and all(path_ok(p) for p in c['paths'])
                for c in ev['commits'])):
            out.append('the evaluation commits is not a non-empty list of {id, text, paths}')
    given = case['given']
    if not (isinstance(given, dict) and set(given) == GIVEN_KEYS and path_ok(given['outside_path'])
            and _texts(given['write_set']) and given['write_set'] and all(pattern_ok(p) for p in given['write_set'])):
        out.append('given is not exactly outside_path and write_set, well formed')
    exp = case['expected']
    if not isinstance(exp, dict) or set(exp) != EXPECTED_KEYS:
        out.append('expected is not exactly stop, decision, next_state and not_fixed')
    return out


def faithfulness_problems(value):
    """AC3: expected comes only from ADV-02's Expected cell."""
    exp = value['cases'][0]['expected']
    out = []
    for key in ('stop', 'decision', 'next_state', 'not_fixed'):
        if exp.get(key) != EXPECTED[key]:
            out.append('expected %s is not %s' % (key, json.dumps(EXPECTED[key])))
    if 'metrics' in exp:
        out.append('metrics is a key of expected')
    return out


def submitted(case):
    """The commits of evaluation.commits whose id is the continuation's submitted commit."""
    cid = case['continuation']['submission']['commit_id']
    return [c for c in case['evaluation']['commits'] if c['id'] == cid]


def approved_hash(case):
    approved = [e for e in case['document']['setup'] if e['type'] == 'task.approved']
    return approved[-1]['payload'].get('contract_hash') if approved else None


def given_problems(value):
    """AC4: the Given of section 11, from the fixture's values alone."""
    case = value['cases'][0]
    doc, ev, given = case['document'], case['evaluation'], case['given']
    obs = doc['violation']['observation']
    out = []
    if not (obs['fact_kind'] == 'observation' and obs['outcome'] == 'blocking' and obs['blocking_kind'] == 'violation'
            and obs['source_class'] == 'deterministic_tool_local' and obs['recorder'] == doc['recorder']):
        out.append("the violation is not a blocking violation observation of class deterministic_tool_local recorded "
                   "by the document's recorder")
    if any(matches(p, given['outside_path']) for p in given['write_set']):
        out.append('outside_path is matched by a pattern of write_set')
    mine = submitted(case)
    if len(mine) != 1:
        out.append('the submitted commit is not exactly once in evaluation.commits')
    else:
        if given['outside_path'] not in mine[0]['paths']:
            out.append("outside_path is not among the submitted commit's paths")
        if ev['values']['changed_paths'] != sorted(mine[0]['paths']):
            out.append("values changed_paths is not the submitted commit's paths, sorted")
    if given['write_set'] != contract_write_set(ev['contract_text']):
        out.append("given write_set is not the contract text's write_set.paths")
    if sha256(ev['contract_text'].encode('utf-8')) != approved_hash(case):
        out.append('the contract text does not hash to the last task.approved contract_hash')
    return out


def amount(text, key):
    """A budget amount as a number: tokens with an optional k (thousands), times in minutes (m) or hours (h)."""
    if isinstance(text, int) and not isinstance(text, bool):
        return text
    m = AMOUNT.fullmatch(text) if isinstance(text, str) else None
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    if key == 'tokens':
        return n * 1000 if unit == 'k' else (n if unit is None else None)
    return n * 60 if unit == 'h' else (n if unit == 'm' else None)


def rc_problems(i, label, approved):
    """AC5: section 9's placeholders for a READY task, every check passing, in one session's Resume Check inputs."""
    out = []
    c = i['contract']
    if i['task_state'] != 'READY':
        out.append('%s task_state is not READY' % label)
    if not (i['approved_contract_hash'] == i['contract_hash'] == approved):
        out.append('%s contract hashes are not the approved contract_hash' % label)
    if i['base_is_ancestor'] is not True:
        out.append('%s base_is_ancestor is not true' % label)
    if i['intent_current'] != c['input_state']['intent_versions']:
        out.append('%s intent_current is not the contract\'s intent_versions' % label)
    top = RISKS.index(i['runtime']['max_risk']) if i['runtime']['max_risk'] in RISKS else -1
    if not (c['risk'] in RISKS and RISKS.index(c['risk']) <= top):
        out.append('%s contract risk is above the runtime\'s max_risk' % label)
    if not all(r['risk'] in RISKS and RISKS.index(r['risk']) <= top for r in i['risk_rules']):
        out.append('%s a risk rule is above the runtime\'s max_risk' % label)
    for p in c['write_set']['paths']:
        if not any(matches(q, sample_path(p)) for r in i['risk_rules'] for q in r['match']['paths']):
            out.append('%s the write_set pattern %s is met by no rule' % (label, p))
    for s in i['symbols']:
        if s['base'] in (None, 'ambiguous') or s['head'] in (None, 'ambiguous'):
            out.append('%s a symbol does not resolve at both commits' % label)
    for s in i['schemas']:
        if not (isinstance(s['base'], dict) and isinstance(s['head'], dict)):
            out.append('%s a schema does not resolve at both commits' % label)
    for dep in i['dependencies'].values():
        if dep != {'state': 'DONE', 'stale_evidence': False}:
            out.append('%s a dependency is not DONE without stale evidence' % label)
    if any(a['violated'] is not False for a in i['articles']):
        out.append('%s an article is violated or has no result' % label)
    budgets = c['autonomy']['budgets']
    for key, use in i['budget_use'].items():
        used, limit = amount(use['used'], key), amount(budgets.get(key), key)
        if used is None or limit is None or used >= limit or use['reported'] is not True:
            out.append('%s the budget %s is not used under its limit' % (label, key))
    return out


def placeholder_problems(value):
    """AC5: section 11's placeholders and the set's section 1 acceptance defaults (decision D-1086 (p2))."""
    case = value['cases'][0]
    ev, given = case['evaluation'], case['given']
    v = ev['values']
    out = []
    if not (v['contract']['risk'] == 'low' and v['contract']['owner_kept_act'] is False
            and v['contract']['verification_plan'] == ['G1', 'G2']):
        out.append('values contract is not risk low, owner_kept_act false and verification_plan [G1, G2]')
    for path in v['changed_paths'] + [given['outside_path']]:
        classes = {r['class'] for r in v['risk_rules'] if any(matches(p, path) for p in r['match'])}
        if classes != {'low'}:
            out.append('the risk rules do not give exactly low to %s' % path)
    dp = v['default_profiles']
    if dp.get('low') != LOW_DEFAULT:
        out.append('default_profiles does not give low exactly the low default')
    if any(e['dimension'] == d and t in e['evidence_types'] for k in dp if k != 'low' for e in dp[k] for d, t in LOW_PAIRS):
        out.append('a profile of another class holds a pair of the low default')
    for key in ('requirement_profiles', 'owner_kept_rules', 'articles'):
        if v[key] != []:
            out.append('values %s is not []' % key)
    if v['auto_accept'] != {k: False for k in RISKS}:
        out.append('auto_accept is not false for every class')
    if v['delegation'] is not True:
        out.append('delegation is not true')
    if v['evidence_comparison'] != {'weakens': False}:
        out.append('evidence_comparison is not {weakens: false}')
    recs = ev['extra_records']
    for rec in recs:
        out.extend(record_problems(rec))
    ids = [r.get('record_id') for r in recs if isinstance(r, dict)]
    if len(ids) != len(set(ids)):
        out.append('a repeated record id')
    cid = case['continuation']['submission']['commit_id']

    def bound(r):
        return (isinstance(r, dict) and r.get('outcome') == 'pass'
                and r.get('source_class') == 'deterministic_tool_external_ci' and r.get('commit') == cid
                and r.get('subject') == ev['task_id'] and r.get('intent_versions') == ev['declared']['intent_versions'])
    for g in GATES:
        if not any(bound(r) and r.get('gate') == g for r in recs):
            out.append('no passing external-CI record of the submitted commit for gate %s' % g)
    for dim, typ in sorted(LOW_PAIRS):
        if not any(bound(r) and r.get('dimension') == dim and r.get('evidence_type') == typ for r in recs):
            out.append('no passing external-CI record of the submitted commit for type %s' % typ)
    approved = approved_hash(case)
    out.extend(rc_problems(case['document']['session']['inputs'], 'the first session', approved))
    out.extend(rc_problems(case['continuation']['session']['inputs'], 'the second session', approved))
    return out


def consistency_problems(value):
    """AC6: the commit text, the observation's refers_to, the trailers and the commit below (decision D-1079 M14)."""
    case = value['cases'][0]
    cont, ev, given = case['continuation'], case['evaluation'], case['given']
    out = []
    mine = submitted(case)
    if len(mine) != 1:
        return ['the submitted commit is not exactly once in evaluation.commits']
    text = cont['submission']['commit_text']
    if text != mine[0]['text']:
        out.append("the submission's commit_text is not the commit table's text")
    if case['document']['violation']['observation']['refers_to'] != given['outside_path']:
        out.append("the observation's refers_to is not outside_path")
    parts = commit_parts(text)
    if parts is None:
        return out + ['the submitted commit text has no message']
    parents, message = parts
    paragraphs = [p for p in message.split('\n\n') if p.strip()]
    if len(paragraphs) < 3:
        out.append('the submitted message has no body between its subject and its trailers')
    tok = cont['session']['expected_token']
    tr = trailers(message)
    if ('AIEOS-Task', ev['task_id']) not in tr:
        out.append('the submitted commit has no AIEOS-Task trailer of the task')
    if ('AIEOS-Fence', '%s:%d' % (tok['epoch'], tok['counter'])) not in tr:
        out.append("the submitted commit has no AIEOS-Fence trailer of the second session's token")
    if len(parents) > 1:
        out.append('the submitted commit has more than one parent')
    for p in parents:
        for c in ev['commits']:
            if c['id'] == p:
                below = commit_parts(c['text'])
                if below is None or any(k == 'AIEOS-Task' for k, _ in trailers(below[1])):
                    out.append('the commit below the submitted one carries an AIEOS-Task trailer')
    return out


def all_problems(data):
    try:
        value = unwrap(data)
    except ValueError as exc:
        return ['AC1: ' + str(exc)]
    line, _ = adv_row()
    out = form_problems(value, sha256(line.encode('utf-8')))
    if out:
        return out
    return (faithfulness_problems(value) + given_problems(value) + placeholder_problems(value)
            + consistency_problems(value))


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
        self.assertEqual(sorted(p.name for p in (ROOT / 'tests/conformance/fixtures_cb').glob('*')
                                if not (p.name == '__pycache__' and p.is_dir())), ['adv_02.py'])


class Ac2FormTest(unittest.TestCase):

    def setUp(self):
        self.value = unwrap(read(FIXTURE))
        line, _ = adv_row()
        self.row_hash = sha256(line.encode('utf-8'))

    def test_the_file_is_well_formed(self):
        self.assertEqual(form_problems(self.value, self.row_hash), [])
        self.assertEqual(all_problems(read(FIXTURE)), [])

    def test_the_row_hash_is_recomputed(self):
        self.assertEqual(self.value['row_hash'], self.row_hash)
        self.assertEqual(self.value['scenario'], 'ADV-02')

    def bad(self, change, why):
        v = copy.deepcopy(self.value)
        change(v)
        self.assertIn(why, form_problems(v, self.row_hash))
        self.assertTrue(all_problems(wrap(v)))

    def test_each_malformed_condition(self):
        case = lambda v: v['cases'][0]
        doc = lambda v: case(v)['document']
        cont = lambda v: case(v)['continuation']
        ev = lambda v: case(v)['evaluation']
        self.bad(lambda v: v.update(extra=1), 'the fixture is not exactly scenario, row_hash and cases')
        self.bad(lambda v: v.update(scenario='ADV-01'), "scenario or row_hash is not ADV-02's")
        self.bad(lambda v: v.update(row_hash='0' * 64), "scenario or row_hash is not ADV-02's")
        self.bad(lambda v: v.update(cases=v['cases'] * 2), 'cases is not a list of exactly one case')
        self.bad(lambda v: case(v).pop('given'),
                 'the case is not exactly document, continuation, evaluation, given and expected')
        self.bad(lambda v: doc(v).pop('violation'), "the document is not exactly replay's document keys and violation")
        self.bad(lambda v: doc(v).update(recorder=''), 'the document recorder is not a non-empty string')
        self.bad(lambda v: doc(v).update(submission=cont(v)['submission']), 'the document submission is not null')
        self.bad(lambda v: doc(v).update(setup=[]), 'the document setup is not a non-empty list of setup events')
        self.bad(lambda v: doc(v)['setup'][0].pop('event_id'), 'the document setup is not a non-empty list of setup events')
        self.bad(lambda v: doc(v)['session'].pop('holder'), 'the document session is not exactly the keys of a session')
        self.bad(lambda v: doc(v)['session'].update(code_sha256='c'), 'the document session code_sha256 is not 64 hex digits')
        self.bad(lambda v: doc(v)['session'].update(start_at='10:00'), 'the document session start_at is not a time')
        self.bad(lambda v: doc(v)['session'].update(expected_token={'epoch': 'e'}),
                 'the document session expected_token is not {epoch, counter}')
        self.bad(lambda v: doc(v)['session']['inputs'].pop('log_seq'),
                 'the document session inputs is not exactly the Resume Check inputs')
        self.bad(lambda v: doc(v).update(end_at=''), 'the document end_at is not a time')
        self.bad(lambda v: doc(v)['violation']['observation'].pop('refers_to'),
                 'the document violation is not exactly observation, event_id and at')
        self.bad(lambda v: doc(v)['violation'].update(at='now'),
                 'the document violation is not exactly observation, event_id and at')
        self.bad(lambda v: cont(v).update(extra=1), 'the continuation is not exactly session, submission and end_at')
        self.bad(lambda v: cont(v)['session'].pop('inputs'), 'the continuation session is not exactly the keys of a session')
        self.bad(lambda v: cont(v).update(submission=None), 'the continuation submission is not a submission')
        self.bad(lambda v: cont(v)['submission'].update(commit_id='3'), 'the continuation submission is not a submission')
        self.bad(lambda v: cont(v).update(end_at=None), 'the continuation end_at is not a time')
        self.bad(lambda v: ev(v).pop('now'), 'the evaluation is not exactly the keys of section 11')
        self.bad(lambda v: ev(v).update(task_id='T-1'), 'the evaluation task_id is malformed')
        self.bad(lambda v: ev(v).update(contract_text=''), 'the evaluation contract_text is not a non-empty string')
        self.bad(lambda v: ev(v)['declared'].pop('retries'), 'the evaluation declared is not {intent_versions, retries}')
        self.bad(lambda v: ev(v)['values'].pop('articles'),
                 "the evaluation values is not exactly the thirteen keys with the contract's four")
        self.bad(lambda v: ev(v)['values']['contract'].pop('risk'),
                 "the evaluation values is not exactly the thirteen keys with the contract's four")
        self.bad(lambda v: ev(v).update(extra_records={}), 'the evaluation extra_records is not a list')
        self.bad(lambda v: ev(v).update(recorder=''), 'the evaluation recorder is not a non-empty string')
        self.bad(lambda v: ev(v).update(now='2026-10-16'), 'the evaluation now is not a time')
        self.bad(lambda v: ev(v).update(commits=[]), 'the evaluation commits is not a non-empty list of {id, text, paths}')
        self.bad(lambda v: ev(v)['commits'][0].update(paths=[]),
                 'the evaluation commits is not a non-empty list of {id, text, paths}')
        self.bad(lambda v: ev(v)['commits'][1].pop('text'),
                 'the evaluation commits is not a non-empty list of {id, text, paths}')
        self.bad(lambda v: case(v)['given'].update(write_set=['docs/***']),
                 'given is not exactly outside_path and write_set, well formed')
        self.bad(lambda v: case(v)['given'].update(outside_path='/src/x.py'),
                 'given is not exactly outside_path and write_set, well formed')
        self.bad(lambda v: case(v)['expected'].update(metrics=[]),
                 'expected is not exactly stop, decision, next_state and not_fixed')

    def test_the_key_lists_are_values(self):
        self.assertEqual(len(VALUE_KEYS), 13)
        self.assertEqual(len(RC_INPUT_KEYS), 22)
        self.assertEqual(DOCUMENT_KEYS - {'violation'}, {'replay_id', 'recorder', 'epoch', 'setup', 'session',
                                                          'submission', 'end_at'})


class Ac3FaithfulnessTest(unittest.TestCase):

    def setUp(self):
        self.value = unwrap(read(FIXTURE))

    def test_the_expected_cell_is_the_bound_one(self):
        _, cells = adv_row()
        self.assertEqual(cells[0], 'ADV-02')
        self.assertEqual(cells[1], 'Capability Boundaries')
        self.assertEqual(cells[4], EXPECTED_CELL)
        self.assertEqual(cells[3], 'the write is observed')

    def test_expected_comes_only_from_the_cell(self):
        self.assertEqual(faithfulness_problems(self.value), [])
        self.assertEqual(self.value['cases'][0]['expected'], EXPECTED)
        self.assertNotIn('metrics', self.value['cases'][0]['expected'])

    def test_other_lists_fail(self):
        for key, val in (('stop', ['STOP: violation', 'CONTINUE']), ('stop', []), ('decision', ['REJECT', 'NEEDS_REVIEW']),
                         ('decision', ['NEEDS_REWORK']), ('next_state', ['REJECTED', 'REWORK']), ('next_state', []),
                         ('not_fixed', []), ('not_fixed', ['metrics', 'decision'])):
            v = copy.deepcopy(self.value)
            v['cases'][0]['expected'][key] = val
            why = 'expected %s is not %s' % (key, json.dumps(EXPECTED[key]))
            self.assertIn(why, faithfulness_problems(v))
            self.assertIn(why, all_problems(wrap(v)))

    def test_metrics_as_a_key_fails(self):
        v = copy.deepcopy(self.value)
        v['cases'][0]['expected']['metrics'] = ['recorded']
        self.assertIn('metrics is a key of expected', faithfulness_problems(v))

    def test_no_expected_element_depends_on_a_placeholder(self):
        text = canon(self.value['cases'][0]['expected'])
        for placeholder in ('TASK-', 'SPEC-', 'src/', 'e-replay', 'G0', 'v1', '333'):
            self.assertNotIn(placeholder, text)


class Ac4GivenTest(unittest.TestCase):

    def setUp(self):
        self.value = unwrap(read(FIXTURE))

    def test_the_given_holds(self):
        self.assertEqual(given_problems(self.value), [])
        case = self.value['cases'][0]
        self.assertEqual(case['given']['write_set'], contract_write_set(case['evaluation']['contract_text']))

    def test_each_given_condition_broken_fails(self):
        def obs(v):
            return v['cases'][0]['document']['violation']['observation']

        def give(v):
            return v['cases'][0]['given']

        def ev(v):
            return v['cases'][0]['evaluation']
        why_obs = ("the violation is not a blocking violation observation of class deterministic_tool_local recorded "
                   "by the document's recorder")
        cases = (
            (lambda v: obs(v).update(outcome='fail'), why_obs),
            (lambda v: obs(v).update(blocking_kind='other'), why_obs),
            (lambda v: obs(v).update(source_class='deterministic_tool_external_ci'), why_obs),
            (lambda v: obs(v).update(fact_kind='claim'), why_obs),
            (lambda v: obs(v).update(recorder='someone-else'), why_obs),
            (lambda v: give(v).update(write_set=['src/**']), 'outside_path is matched by a pattern of write_set'),
            (lambda v: give(v).update(write_set=['outside.py']), 'outside_path is matched by a pattern of write_set'),
            (lambda v: ev(v).update(commits=ev(v)['commits'] + [ev(v)['commits'][0]]),
             'the submitted commit is not exactly once in evaluation.commits'),
            (lambda v: ev(v)['commits'][0].update(paths=['docs/notes/a.md']),
             "outside_path is not among the submitted commit's paths"),
            (lambda v: ev(v)['values'].update(changed_paths=['src/other.py']),
             "values changed_paths is not the submitted commit's paths, sorted"),
            (lambda v: give(v).update(write_set=['docs/notes/**', 'docs/more/**']),
             "given write_set is not the contract text's write_set.paths"),
            (lambda v: ev(v).update(contract_text=ev(v)['contract_text'] + '\n'),
             'the contract text does not hash to the last task.approved contract_hash'),
        )
        for change, why in cases:
            v = copy.deepcopy(self.value)
            change(v)
            self.assertIn(why, given_problems(v), why)

    def test_the_write_set_reader(self):
        self.assertEqual(contract_write_set('task: T\nwrite_set:\n  paths: [a/**, b.md]\n'), ['a/**', 'b.md'])
        self.assertEqual(contract_write_set('task: T\nwrite_set:\n  paths: []\n'), [])
        self.assertIsNone(contract_write_set('task: T\n'))
        self.assertIsNone(contract_write_set('write_set:\n  paths:\n    - a/**\n'))
        self.assertIsNone(contract_write_set('write_set:\n  paths: [a]\nwrite_set:\n  paths: [b]\n'))

    def test_the_matcher_follows_point_6(self):
        for pattern, path, want in (
                ('docs/notes/**', 'docs/notes/a.md', True), ('docs/notes/**', 'docs/notes', False),
                ('docs/notes/**', 'src/outside.py', False), ('src/**', 'src/outside.py', True),
                ('*.py', 'src/outside.py', True), ('outside.py', 'src/outside.py', True),
                ('src/*.py', 'src/a/outside.py', False), ('**/outside.py', 'outside.py', True),
                ('Src/**', 'src/outside.py', False)):
            self.assertEqual(matches(pattern, path), want, (pattern, path))


class Ac5PlaceholdersTest(unittest.TestCase):

    def setUp(self):
        self.value = unwrap(read(FIXTURE))

    def test_the_placeholders_hold(self):
        self.assertEqual(placeholder_problems(self.value), [])
        recs = self.value['cases'][0]['evaluation']['extra_records']
        self.assertEqual(sorted(r.get('gate') or r.get('evidence_type') for r in recs), ['G0', 'G1', 'G2', 'build', 'lint'])
        for rec in recs:
            self.assertEqual(record_problems(rec), [])

    def test_each_placeholder_broken_fails(self):
        def v_(v):
            return v['cases'][0]['evaluation']['values']

        def recs(v):
            return v['cases'][0]['evaluation']['extra_records']

        def rc(v, which):
            part = 'document' if which == 1 else 'continuation'
            return v['cases'][0][part]['session']['inputs']
        why_c = 'values contract is not risk low, owner_kept_act false and verification_plan [G1, G2]'
        cases = (
            (lambda v: v_(v)['contract'].update(risk='high'), why_c),
            (lambda v: v_(v)['contract'].update(owner_kept_act=True), why_c),
            (lambda v: v_(v)['contract'].update(verification_plan=['G1']), why_c),
            (lambda v: v_(v)['risk_rules'][0].update(**{'class': 'medium'}), 'the risk rules do not give exactly low to src/outside.py'),
            (lambda v: v_(v)['risk_rules'].append({'id': 'R2', 'match': ['src/**'], 'class': 'high'}),
             'the risk rules do not give exactly low to src/outside.py'),
            (lambda v: v_(v).update(risk_rules=[]), 'the risk rules do not give exactly low to src/outside.py'),
            (lambda v: v_(v)['default_profiles'].update(low=[{'dimension': 'functional', 'evidence_types': ['build']}]),
             'default_profiles does not give low exactly the low default'),
            (lambda v: v_(v)['default_profiles'].update(high=[{'dimension': 'functional', 'evidence_types': ['lint']}]),
             'a profile of another class holds a pair of the low default'),
            (lambda v: v_(v).update(requirement_profiles=[{'id': 'R1', 'add': []}]), 'values requirement_profiles is not []'),
            (lambda v: v_(v).update(owner_kept_rules=[{'match': ['x/**']}]), 'values owner_kept_rules is not []'),
            (lambda v: v_(v).update(articles=[{'id': 'SEC-001', 'scope': ['**'], 'evidence_required': []}]),
             'values articles is not []'),
            (lambda v: v_(v)['auto_accept'].update(low=True), 'auto_accept is not false for every class'),
            (lambda v: v_(v)['auto_accept'].pop('critical'), 'auto_accept is not false for every class'),
            (lambda v: v_(v).update(delegation=None), 'delegation is not true'),
            (lambda v: v_(v).update(evidence_comparison={'weakens': True}), 'evidence_comparison is not {weakens: false}'),
            (lambda v: recs(v).pop(0), 'no passing external-CI record of the submitted commit for gate G0'),
            (lambda v: recs(v)[1].update(outcome='fail'), 'no passing external-CI record of the submitted commit for gate G1'),
            (lambda v: recs(v)[2].update(commit='1' * 40), 'no passing external-CI record of the submitted commit for gate G2'),
            (lambda v: recs(v)[3].update(source_class='deterministic_tool_local'),
             'no passing external-CI record of the submitted commit for type build'),
            (lambda v: recs(v)[4].update(intent_versions={'SPEC-001': 'v2'}),
             'no passing external-CI record of the submitted commit for type lint'),
            (lambda v: recs(v)[4].update(subject='TASK-101'),
             'no passing external-CI record of the submitted commit for type lint'),
            (lambda v: recs(v)[1].update(record_id=recs(v)[0]['record_id']), 'a repeated record id'),
            (lambda v: recs(v)[0].update(extra=1),
             'an extra record is not exactly the keys of a gate result or of a typed record'),
            (lambda v: recs(v)[0].update(fact_kind='claim'), 'an extra record is not an observation'),
            (lambda v: recs(v)[0].update(commit='abc'), 'an extra record commit is not a full commit id'),
            (lambda v: rc(v, 1).update(task_state='IN_PROGRESS'), 'the first session task_state is not READY'),
            (lambda v: rc(v, 2).update(approved_contract_hash='0' * 64),
             'the second session contract hashes are not the approved contract_hash'),
            (lambda v: rc(v, 1).update(base_is_ancestor=False), 'the first session base_is_ancestor is not true'),
            (lambda v: rc(v, 2).update(intent_current={'SPEC-003': 'v5'}),
             "the second session intent_current is not the contract's intent_versions"),
            (lambda v: rc(v, 1)['contract'].update(risk='critical'), "the first session contract risk is above the runtime's max_risk"),
            (lambda v: rc(v, 2)['risk_rules'][0].update(risk='critical'), "the second session a risk rule is above the runtime's max_risk"),
            (lambda v: rc(v, 1)['risk_rules'][0]['match'].update(paths=['src/**']),
             'the first session the write_set pattern docs/notes/** is met by no rule'),
            (lambda v: rc(v, 2)['symbols'][0].update(head=None), 'the second session a symbol does not resolve at both commits'),
            (lambda v: rc(v, 1)['symbols'][0].update(base='ambiguous'), 'the first session a symbol does not resolve at both commits'),
            (lambda v: rc(v, 2)['schemas'][0].update(base=None), 'the second session a schema does not resolve at both commits'),
            (lambda v: rc(v, 1)['dependencies']['TASK-099'].update(state='READY'),
             'the first session a dependency is not DONE without stale evidence'),
            (lambda v: rc(v, 2)['articles'][0].update(violated=None), 'the second session an article is violated or has no result'),
            (lambda v: rc(v, 1)['budget_use']['retries'].update(used=2), 'the first session the budget retries is not used under its limit'),
            (lambda v: rc(v, 2)['budget_use']['tokens'].update(used='400k'), 'the second session the budget tokens is not used under its limit'),
            (lambda v: rc(v, 1)['budget_use']['wall_time'].update(used='3h'), 'the first session the budget wall_time is not used under its limit'),
            (lambda v: rc(v, 2)['budget_use']['human_attention'].update(reported=False),
             'the second session the budget human_attention is not used under its limit'),
        )
        for change, why in cases:
            v = copy.deepcopy(self.value)
            change(v)
            self.assertIn(why, placeholder_problems(v), why)

    def test_the_amounts(self):
        self.assertEqual((amount('400k', 'tokens'), amount('2h', 'wall_time'), amount('10m', 'human_attention')),
                         (400000, 120, 10))
        self.assertIsNone(amount('2h', 'tokens'))
        self.assertIsNone(amount('ten', 'wall_time'))
        self.assertEqual(amount(2, 'retries'), 2)


class Ac6ConsistencyTest(unittest.TestCase):

    def setUp(self):
        self.value = unwrap(read(FIXTURE))

    def test_the_values_agree(self):
        self.assertEqual(consistency_problems(self.value), [])
        case = self.value['cases'][0]
        _, message = commit_parts(case['continuation']['submission']['commit_text'])
        self.assertEqual(trailers(message), [('AIEOS-Task', 'TASK-100'), ('AIEOS-Fence', 'e-replay:2')])

    def test_each_inconsistency_fails(self):
        def cont(v):
            return v['cases'][0]['continuation']

        def ev(v):
            return v['cases'][0]['evaluation']
        mine = lambda v: [c for c in ev(v)['commits'] if c['id'] == cont(v)['submission']['commit_id']][0]
        below = lambda v: [c for c in ev(v)['commits'] if c['id'] != cont(v)['submission']['commit_id']][0]

        def both(old, new):
            """Replace old by new in the submitted commit's text, in the commit table and in the submission alike."""
            def change(v):
                text = mine(v)['text'].replace(old, new)
                mine(v)['text'] = text
                cont(v)['submission']['commit_text'] = text
            return change
        cases = (
            (lambda v: cont(v)['submission'].update(commit_text=cont(v)['submission']['commit_text'] + 'x\n'),
             "the submission's commit_text is not the commit table's text"),
            (lambda v: v['cases'][0]['document']['violation']['observation'].update(refers_to='src/other.py'),
             "the observation's refers_to is not outside_path"),
            (both('AIEOS-Task: TASK-100', 'AIEOS-Task: TASK-101'), 'the submitted commit has no AIEOS-Task trailer of the task'),
            (both('e-replay:2', 'e-replay:1'), "the submitted commit has no AIEOS-Fence trailer of the second session's token"),
            (lambda v: cont(v)['session']['expected_token'].update(counter=3),
             "the submitted commit has no AIEOS-Fence trailer of the second session's token"),
            (both('\n\nThe body.\n', '\n'), 'the submitted message has no body between its subject and its trailers'),
            (lambda v: below(v).update(text=below(v)['text'] + '\nAIEOS-Task: TASK-099\n'),
             'the commit below the submitted one carries an AIEOS-Task trailer'),
            (both('parent ' + '1' * 40, 'parent ' + '1' * 40 + '\nparent ' + '5' * 40),
             'the submitted commit has more than one parent'),
        )
        for change, why in cases:
            v = copy.deepcopy(self.value)
            change(v)
            self.assertIn(why, consistency_problems(v), why)

    def test_the_trailer_reader(self):
        self.assertEqual(trailers('Subject\n\nBody.\n\nA-B: c\nD: e f\n'), [('A-B', 'c'), ('D', 'e f')])
        self.assertEqual(trailers('Subject\n\nBody with: a colon\nand more\n'), [])
        self.assertEqual(trailers(''), [])
        self.assertEqual(commit_parts('tree t\nparent p\n\nm\n'), (['p'], 'm\n'))
        self.assertIsNone(commit_parts('tree t'))


if __name__ == '__main__':
    unittest.main()
