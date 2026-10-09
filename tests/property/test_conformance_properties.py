"""Property tests of the conformance files of TASK-002, with fixed seeds (AC7).

The helpers below are repeated in the three test modules of TASK-002, because each CI test folder is discovered
on its own and an import between them is not allowed. Files are read as bytes with pathlib; no fixture or set
module is ever imported or executed.
"""
import random
import unittest
import hashlib
import json
import pathlib
import re
import unicodedata

from aieos_bootstrap.records import check_record

# The repository root, the bound scenario file and the conformance files (docs/specs/conformance-files.md revision 2).
# Files are read with pathlib's read_bytes only; no fixture or set module is ever imported or executed (section 2).
ROOT = pathlib.Path(__file__).resolve().parents[2]
SCENARIO_FILE = 'docs/pre-genesis/conformance-scenarios-initial.md'
SET_FILE = 'tests/conformance/set.py'
FIXTURE_DIR = 'tests/conformance/fixtures'
FIRST, LAST = b"DATA = r'''", b"'''\n"
ACCEPTANCE = ('ACCEPT', 'NEEDS_REVIEW', 'INSUFFICIENT_EVIDENCE', 'NEEDS_REWORK', 'REJECT')
EXECUTION = ('CONTINUE', 'CONTINUE_WITH', 'REPLAN', 'STOP: scope invalid', 'STOP: runtime insufficient',
             'STOP: violation', 'BLOCKED', 'ESCALATE')
STATES = ('DRAFT', 'READY', 'IN_PROGRESS', 'VERIFYING', 'ACCEPTED', 'DONE', 'IN_REVIEW', 'REWORK', 'ESCALATED',
          'REJECTED', 'BLOCKED', 'STALE')
CAPABILITIES = ('Verification', 'Resume Check', 'Risk Engine', 'Capability Boundaries')
EXPECTED_KEYS = ('decision', 'next_state', 'missing', 'reverify', 'approval', 'ai_approval_shown')
REQUEST_KEYS = ('task_id', 'task_content_hash', 'evaluated_commit', 'intent_versions', 'task_state', 'changed_paths',
                'retry_count')
INPUT_KEYS = ('traces_to', 'risk', 'owner_kept_act', 'weakens_evidence', 'delegation_in_force', 'auto_accept',
              'verification_plan', 'evidence_profile', 'applicable_articles', 'policy_version', 'level_version',
              'ruleset_version')
HEX64 = re.compile(r'[0-9a-f]{64}')
COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
TASK = re.compile(r'TASK-[0-9]+')
VERSION = re.compile(r'v[0-9]+')
GATE = re.compile(r'G[0-9]+')
ROW = re.compile(r'^\| ((?:ACC|RISK|RC|ADV)-[0-9]+) \| ')


class Malformed(ValueError):
    """A conformance file that is not in the form of conformance-files.md section 2."""


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
    """The JSON value a conformance file wraps, or Malformed (section 2: the two fixed parts, then canonical JSON)."""
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


def scenario_rows(data=None):
    """Each scenario row of the bound file: (id, row hash, capability, Expected cell), in the file's order."""
    text = (read(SCENARIO_FILE) if data is None else data).decode('utf-8')
    rows, section = [], None
    for line in text.split('\n'):
        if line.startswith('## '):
            section = line
        m = ROW.match(line)
        if not m:
            continue
        cells = line.split(' | ')
        if len(cells) != 6 or not line.endswith(' |'):
            raise Malformed('a row that is not six cells: %s' % m.group(1))
        if section.startswith('## 2. Verification'):
            capability = 'Verification'
        elif section.startswith('## 3. Risk Engine'):
            capability = 'Risk Engine'
        elif section.startswith('## 4. Resume Check'):
            capability = 'Resume Check'
        else:
            capability = cells[1]
        rows.append((m.group(1), sha256(line.encode('utf-8')), capability, cells[4]))
    return rows


def module_path(scenario_id):
    return FIXTURE_DIR + '/' + scenario_id.lower().replace('-', '_') + '.py'


def _is_str(v):
    return isinstance(v, str) and v != ''


def _is_str_list(v):
    return isinstance(v, list) and all(_is_str(x) for x in v)


def _is_int(v, minimum=0):
    return isinstance(v, int) and not isinstance(v, bool) and v >= minimum


def check_set(value, rows=None, files=None):
    """Section 3 against the bound file's rows; ``files`` maps a fixture path to its bytes. Returns a list of errors."""
    rows = scenario_rows() if rows is None else rows
    errors = []
    if not isinstance(value, dict) or set(value) != {'scenario_set_version', 'scenario_set_file_hash',
                                                     'fixture_set_version', 'scenarios'}:
        return ['set: not exactly the four keys of section 3']
    if value['scenario_set_version'] != 2 or isinstance(value['scenario_set_version'], bool):
        errors.append('set: scenario_set_version is not 2')
    if value['scenario_set_file_hash'] != sha256(read(SCENARIO_FILE)):
        errors.append('set: scenario_set_file_hash is not the bound file\'s SHA-256')
    if value['fixture_set_version'] != 1 or isinstance(value['fixture_set_version'], bool):
        errors.append('set: fixture_set_version is not 1')
    entries = value['scenarios']
    if not isinstance(entries, list) or len(entries) != len(rows):
        return errors + ['set: not one entry per scenario row']
    for entry, (sid, row_hash, capability, _cell) in zip(entries, rows):
        if not isinstance(entry, dict) or set(entry) != {'id', 'row_hash', 'capability', 'fixture'}:
            errors.append('set: an entry is not exactly {id, row_hash, capability, fixture}')
            continue
        if entry['id'] != sid or entry['row_hash'] != row_hash or entry['capability'] != capability:
            errors.append('set: entry %s does not match its row' % sid)
        fixture = entry['fixture']
        if fixture is None:
            continue
        if capability != 'Verification':
            errors.append('set: %s is outside the Verification capability and has a fixture' % sid)
        if not isinstance(fixture, dict) or set(fixture) != {'path', 'sha256'}:
            errors.append('set: the fixture of %s is not {path, sha256}' % sid)
            continue
        if fixture['path'] != module_path(sid):
            errors.append('set: the fixture path of %s is not %s' % (sid, module_path(sid)))
        data = (files or {}).get(fixture['path'])
        if data is None or sha256(data) != fixture['sha256']:
            errors.append('set: the fixture of %s is missing or its SHA-256 differs' % sid)
    named = sorted(e['fixture']['path'] for e in entries if isinstance(e, dict) and isinstance(e.get('fixture'), dict))
    if files is not None and named != sorted(files):
        errors.append('set: the fixture files and the entries that name them differ')
    return errors


def _check_request(req, where):
    errors = []
    if not isinstance(req, dict) or set(req) != set(REQUEST_KEYS):
        return ['%s: request is not exactly the keys of specification 2 section 6.5' % where]
    if not (_is_str(req['task_id']) and TASK.fullmatch(req['task_id'])):
        errors.append('%s: task_id' % where)
    if not (isinstance(req['task_content_hash'], str) and HEX64.fullmatch(req['task_content_hash'])):
        errors.append('%s: task_content_hash' % where)
    if not (isinstance(req['evaluated_commit'], str) and COMMIT.fullmatch(req['evaluated_commit'])):
        errors.append('%s: evaluated_commit' % where)
    iv = req['intent_versions']
    if not (isinstance(iv, dict) and all(_is_str(k) and isinstance(v, str) and VERSION.fullmatch(v) for k, v in iv.items())):
        errors.append('%s: intent_versions' % where)
    if req['task_state'] not in STATES:
        errors.append('%s: task_state' % where)
    if not _is_str_list(req['changed_paths']):
        errors.append('%s: changed_paths' % where)
    rc = req['retry_count']
    if not (isinstance(rc, dict) and set(rc) == {'used', 'limit'} and _is_int(rc['used']) and _is_int(rc['limit'])):
        errors.append('%s: retry_count' % where)
    return errors


def _check_inputs(inp, where):
    if not isinstance(inp, dict) or set(inp) != set(INPUT_KEYS):
        return ['%s: inputs is not exactly the keys of section 4' % where]
    errors = []
    if not _is_str_list(inp['traces_to']):
        errors.append('%s: traces_to' % where)
    if inp['risk'] not in ('low', 'medium', 'high', 'critical'):
        errors.append('%s: risk' % where)
    for key in ('owner_kept_act', 'weakens_evidence', 'delegation_in_force', 'auto_accept'):
        if not isinstance(inp[key], bool):
            errors.append('%s: %s' % (where, key))
    if not (_is_str_list(inp['verification_plan']) and all(GATE.fullmatch(g) for g in inp['verification_plan'])):
        errors.append('%s: verification_plan' % where)
    prof = inp['evidence_profile']
    if not (isinstance(prof, list) and all(isinstance(e, dict) and set(e) == {'dimension', 'evidence_types'}
                                           and _is_str(e['dimension']) and _is_str_list(e['evidence_types']) for e in prof)):
        errors.append('%s: evidence_profile' % where)
    arts = inp['applicable_articles']
    if not (isinstance(arts, list) and all(isinstance(a, dict) and set(a) == {'id', 'evidence_required'}
                                           and _is_str(a['id']) and _is_str_list(a['evidence_required']) for a in arts)):
        errors.append('%s: applicable_articles' % where)
    for key in ('policy_version', 'level_version', 'ruleset_version'):
        if not _is_str(inp[key]):
            errors.append('%s: %s' % (where, key))
    return errors


def _check_expected(exp, records, where):
    if not isinstance(exp, dict) or 'not_fixed' not in exp:
        return ['%s: expected has no not_fixed' % where]
    errors = []
    not_fixed = exp['not_fixed']
    if not (_is_str_list(not_fixed) and len(set(not_fixed)) == len(not_fixed) and set(not_fixed) <= set(EXPECTED_KEYS)):
        return ['%s: not_fixed is not a list of distinct keys of expected' % where]
    for key in EXPECTED_KEYS:
        if (key in exp) == (key in not_fixed):
            errors.append('%s: %s is not either present or in not_fixed' % (where, key))
    if set(exp) - set(EXPECTED_KEYS) - {'not_fixed'}:
        errors.append('%s: expected has a key that section 4 does not name' % where)
    ids = {r.get('record_id'): r for r in records if isinstance(r, dict)}
    if 'decision' in exp and not (isinstance(exp['decision'], list) and exp['decision']
                                  and all(d in ACCEPTANCE for d in exp['decision'])):
        errors.append('%s: decision' % where)
    if 'next_state' in exp and not (isinstance(exp['next_state'], list) and exp['next_state']
                                    and all(s in STATES for s in exp['next_state'])):
        errors.append('%s: next_state' % where)
    if 'missing' in exp and not (isinstance(exp['missing'], list) and all(
            isinstance(m, dict) and set(m) == {'dimension', 'evidence_type'} and _is_str(m['dimension'])
            and _is_str(m['evidence_type']) for m in exp['missing'])):
        errors.append('%s: missing' % where)
    if 'reverify' in exp and not (_is_str_list(exp['reverify']) and all(r in ids for r in exp['reverify'])):
        errors.append('%s: reverify' % where)
    if 'approval' in exp:
        a = exp['approval']
        if a is not None and not (isinstance(a, dict) and set(a) == {'record_id', 'source_class'}
                                  and a['record_id'] in ids and ids[a['record_id']].get('source_class') == a['source_class']):
            errors.append('%s: approval' % where)
    if 'ai_approval_shown' in exp and not isinstance(exp['ai_approval_shown'], bool):
        errors.append('%s: ai_approval_shown' % where)
    return errors


def check_fixture(value, entry):
    """Section 4 for one fixture against its set-file entry. Returns a list of errors."""
    if not isinstance(value, dict) or set(value) != {'scenario', 'row_hash', 'cases'}:
        return ['fixture: not exactly scenario, row_hash and cases']
    sid = value['scenario']
    errors = []
    if sid != entry['id'] or value['row_hash'] != entry['row_hash']:
        errors.append('fixture %s: scenario or row_hash differs from its set-file entry' % sid)
    cases = value['cases']
    if not isinstance(cases, list) or len(cases) != (3 if sid == 'ACC-13' else 1):
        return errors + ['fixture %s: not one case per task of the Given' % sid]
    for n, c in enumerate(cases, 1):
        where = '%s case %d' % (sid, n)
        if not isinstance(c, dict) or set(c) != {'request', 'inputs', 'records', 'when', 'expected'}:
            errors.append('%s: not exactly request, inputs, records, when and expected' % where)
            continue
        errors.extend(_check_request(c['request'], where))
        errors.extend(_check_inputs(c['inputs'], where))
        state = c['request'].get('task_state') if isinstance(c['request'], dict) else None
        if not ((c['when'] == 'evaluate' and state == 'VERIFYING') or (c['when'] == 're_evaluate' and state == 'IN_REVIEW')):
            errors.append('%s: when does not agree with task_state' % where)
        records = c['records']
        if not isinstance(records, list):
            errors.append('%s: records is not a list' % where)
            continue
        seen = set()
        for r in records:
            for finding in check_record(r, where=where + ' record'):
                errors.append('%s: %s' % (where, finding.detail))
            rid = r.get('record_id') if isinstance(r, dict) else None
            if rid in seen:
                errors.append('%s: a duplicate record_id %s' % (where, rid))
            seen.add(rid)
        errors.extend(_check_expected(c['expected'], records, where))
    return errors


def load_tree():
    """The set value, the fixture files' bytes by path, and the bound file's rows, as the repository holds them."""
    value = unwrap(read(SET_FILE))
    files = {FIXTURE_DIR + '/' + p.name: p.read_bytes() for p in sorted((ROOT / FIXTURE_DIR).iterdir()) if p.is_file()}
    return value, files, scenario_rows()


def has_control_character(value):
    if isinstance(value, dict):
        return any(has_control_character(k) or has_control_character(v) for k, v in value.items())
    if isinstance(value, list):
        return any(has_control_character(x) for x in value)
    return isinstance(value, str) and any(unicodedata.category(ch) == 'Cc' for ch in value)

SEEDS = (2, 3, 5, 7, 11)


def all_cases():
    value, files, _rows = load_tree()
    for entry in value['scenarios']:
        if entry['fixture']:
            for c in unwrap(files[entry['fixture']['path']])['cases']:
                yield entry['id'], c


def random_value(rng, depth=0):
    kind = rng.randrange(7 if depth < 3 else 4)
    if kind == 0:
        return rng.randrange(-1000, 1000)
    if kind == 1:
        return ''.join(rng.choice('ab"\\/é\x01 x{}[]:,') for _ in range(rng.randrange(6)))
    if kind == 2:
        return rng.choice([True, False, None])
    if kind == 3:
        return 'v%d' % rng.randrange(10)
    if kind == 4:
        return [random_value(rng, depth + 1) for _ in range(rng.randrange(4))]
    return {('k%d' % rng.randrange(20)): random_value(rng, depth + 1) for _ in range(rng.randrange(4))}


class FormPropertiesTest(unittest.TestCase):
    """TASK-002 AC7: properties of the file kind, with fixed seeds."""

    def test_generated_values_round_trip(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(200):
                v = random_value(rng)
                if not isinstance(v, (dict, list)):
                    v = [v]
                data = wrap(v)
                self.assertEqual(unwrap(data), v)
                self.assertEqual(wrap(unwrap(data)), data)

    def test_rewrapping_every_file_is_idempotent(self):
        _value, files, _rows = load_tree()
        for path, data in files.items():
            self.assertEqual(wrap(unwrap(wrap(unwrap(data)))), data, path)

    def test_any_one_byte_change_is_caught(self):
        value, files, rows = load_tree()
        for seed in SEEDS:
            rng = random.Random(seed)
            for path in sorted(files):
                data = bytearray(files[path])
                i = rng.randrange(len(data))
                data[i] = (data[i] + 1 + rng.randrange(255)) % 256
                changed = dict(files)
                changed[path] = bytes(data)
                self.assertNotEqual(check_set(value, rows, changed), [], (seed, path, i))

    def test_reordered_keys_are_not_canonical(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(100):
                keys = sorted({'k%d' % rng.randrange(50) for _ in range(rng.randrange(2, 6))})
                order = keys[:]
                rng.shuffle(order)
                text = '{\n' + ',\n'.join('  "%s": 1' % k for k in order) + '\n}\n'
                data = FIRST + text.encode('utf-8') + LAST
                if order == keys:
                    self.assertEqual(sorted(unwrap(data)), keys)
                else:
                    with self.assertRaises(Malformed):
                        unwrap(data)

    def test_the_same_input_gives_the_same_result(self):
        value, files, rows = load_tree()
        self.assertEqual(check_set(value, rows, files), check_set(value, rows, files))
        self.assertEqual(load_tree(), (value, files, rows))
        cases = list(all_cases())
        self.assertEqual(cases, list(all_cases()))


class InvariantPropertiesTest(unittest.TestCase):
    """TASK-002 AC7: the properties of the invariants the task relates to, over every case of every fixture."""

    def test_inv_005_one_decision_vocabulary(self):
        for sid, c in all_cases():
            for d in c['expected'].get('decision', []):
                self.assertIn(d, ACCEPTANCE, sid)
                self.assertNotIn(d, EXECUTION, sid)

    def test_inv_006_acceptance_order(self):
        for sid, c in all_cases():
            decisions = c['expected'].get('decision', [])
            if 'ACCEPT' in decisions:
                self.assertTrue(c['inputs']['auto_accept'], sid)
            failed_gate = any(r.get('gate') and r.get('outcome') == 'fail' for r in c['records'])
            if failed_gate:
                self.assertNotIn('NEEDS_REVIEW', decisions, sid)
                self.assertNotIn('ACCEPT', decisions, sid)

    def test_inv_007_only_current_evidence(self):
        for sid, c in all_cases():
            req = c['request']
            for r in c['records']:
                if r['fact_kind'] != 'authority' and 'evidence_type' in r:
                    self.assertIn('commit', r, sid)
                    self.assertIn('intent_versions', r, sid)
            by_id = {r['record_id']: r for r in c['records']}
            for rid in c['expected'].get('reverify', []):
                r = by_id[rid]
                self.assertTrue(r['commit'] != req['evaluated_commit'] or r['intent_versions'] != req['intent_versions'], sid)

    def test_inv_008_an_agent_word_is_not_evidence(self):
        for sid, c in all_cases():
            by_id = {r['record_id']: r for r in c['records']}
            approval = c['expected'].get('approval')
            if approval:
                self.assertNotEqual(by_id[approval['record_id']]['source_class'], 'agent_declared', sid)
            if 'missing' not in c['expected']:
                continue
            missing = {(m['dimension'], m['evidence_type']) for m in c['expected']['missing']}
            for entry in c['inputs']['evidence_profile']:
                for t in entry['evidence_types']:
                    of_type = [r for r in c['records'] if r.get('evidence_type') == t and r.get('dimension') == entry['dimension']]
                    if of_type and all(r['source_class'] == 'agent_declared' for r in of_type):
                        self.assertIn((entry['dimension'], t), missing, sid)


if __name__ == '__main__':
    unittest.main()
