"""Unit tests of the conformance files of TASK-002 (docs/specs/conformance-files.md revision 2; AC1 to AC4).

The helpers below are repeated in the three test modules of TASK-002, because each CI test folder is discovered
on its own and an import between them is not allowed. Files are read as bytes with pathlib; no fixture or set
module is ever imported or executed.
"""
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


# TASK-002 AC4: for each realised scenario, the text of its Expected cell (equal to the bound file, checked below)
# and the expected values of its cases. Built by script from the bound file and the fixture files.
EXPECTED_CELLS = {
    'ACC-01': (
        'NEEDS_REVIEW; next state IN_REVIEW',
        [
            {'decision': ['NEEDS_REVIEW'], 'next_state': ['IN_REVIEW'], 'not_fixed': ['missing', 'reverify', 'approval', 'ai_approval_shown']},
        ],
    ),
    'ACC-02': (
        'NEEDS_REVIEW; next state IN_REVIEW',
        [
            {'decision': ['NEEDS_REVIEW'], 'next_state': ['IN_REVIEW'], 'not_fixed': ['missing', 'reverify', 'approval', 'ai_approval_shown']},
        ],
    ),
    'ACC-03': (
        'NEEDS_REWORK; next state REWORK',
        [
            {'decision': ['NEEDS_REWORK'], 'next_state': ['REWORK'], 'not_fixed': ['missing', 'reverify', 'approval', 'ai_approval_shown']},
        ],
    ),
    'ACC-04': (
        'NEEDS_REWORK; next state REWORK',
        [
            {'decision': ['NEEDS_REWORK'], 'next_state': ['REWORK'], 'not_fixed': ['missing', 'reverify', 'approval', 'ai_approval_shown']},
        ],
    ),
    'ACC-05': (
        'INSUFFICIENT_EVIDENCE: security, static_security_analysis missing; next state REWORK',
        [
            {'decision': ['INSUFFICIENT_EVIDENCE'], 'missing': [{'dimension': 'security', 'evidence_type': 'static_security_analysis'}], 'next_state': ['REWORK'], 'not_fixed': ['reverify', 'approval', 'ai_approval_shown']},
        ],
    ),
    'ACC-06': (
        'INSUFFICIENT_EVIDENCE: operational, human_review missing; next state IN_REVIEW, not REWORK',
        [
            {'decision': ['INSUFFICIENT_EVIDENCE'], 'missing': [{'dimension': 'operational', 'evidence_type': 'human_review'}], 'next_state': ['IN_REVIEW'], 'not_fixed': ['reverify', 'approval', 'ai_approval_shown']},
        ],
    ),
    'ACC-07': (
        'the record does not count; INSUFFICIENT_EVIDENCE: security, static_security_analysis missing; a re-verify is scheduled; next state not fixed (REWORK, line 525, or re-verify, lines 270, 504)',
        [
            {'decision': ['INSUFFICIENT_EVIDENCE'], 'missing': [{'dimension': 'security', 'evidence_type': 'static_security_analysis'}], 'not_fixed': ['next_state', 'approval', 'ai_approval_shown'], 'reverify': ['TASK-107-ssa']},
        ],
    ),
    'ACC-08': (
        'as ACC-07',
        [
            {'decision': ['INSUFFICIENT_EVIDENCE'], 'missing': [{'dimension': 'security', 'evidence_type': 'static_security_analysis'}], 'not_fixed': ['next_state', 'approval', 'ai_approval_shown'], 'reverify': ['TASK-108-ssa']},
        ],
    ),
    'ACC-09': (
        'the report is an observation of the claim and authorizes nothing; INSUFFICIENT_EVIDENCE: functional, unit_test missing; next state REWORK',
        [
            {'approval': None, 'decision': ['INSUFFICIENT_EVIDENCE'], 'missing': [{'dimension': 'functional', 'evidence_type': 'unit_test'}], 'next_state': ['REWORK'], 'not_fixed': ['reverify', 'ai_approval_shown']},
        ],
    ),
    'ACC-10': (
        'the review does not count; INSUFFICIENT_EVIDENCE: architecture, ai_review missing; next state REWORK',
        [
            {'decision': ['INSUFFICIENT_EVIDENCE'], 'missing': [{'dimension': 'architecture', 'evidence_type': 'ai_review'}], 'next_state': ['REWORK'], 'not_fixed': ['reverify', 'approval', 'ai_approval_shown']},
        ],
    ),
    'ACC-11': (
        'as ACC-05; the approval does not make the task ACCEPTED',
        [
            {'approval': None, 'decision': ['INSUFFICIENT_EVIDENCE'], 'missing': [{'dimension': 'security', 'evidence_type': 'static_security_analysis'}], 'next_state': ['REWORK'], 'not_fixed': ['reverify', 'ai_approval_shown']},
        ],
    ),
    'ACC-12': (
        'next state ACCEPTED',
        [
            {'next_state': ['ACCEPTED'], 'not_fixed': ['decision', 'missing', 'reverify', 'approval', 'ai_approval_shown']},
        ],
    ),
    'ACC-13': (
        "three approval records, each bound to its own task's content; all three tasks ACCEPTED",
        [
            {'approval': {'record_id': 'TASK-131-approval', 'source_class': 'human_authority'}, 'next_state': ['ACCEPTED'], 'not_fixed': ['decision', 'missing', 'reverify', 'ai_approval_shown']},
            {'approval': {'record_id': 'TASK-132-approval', 'source_class': 'human_authority'}, 'next_state': ['ACCEPTED'], 'not_fixed': ['decision', 'missing', 'reverify', 'ai_approval_shown']},
            {'approval': {'record_id': 'TASK-133-approval', 'source_class': 'human_authority'}, 'next_state': ['ACCEPTED'], 'not_fixed': ['decision', 'missing', 'reverify', 'ai_approval_shown']},
        ],
    ),
    'ACC-14': (
        "next state ACCEPTED; the approval is recorded as the decision agent's, not as an owner's or a person's decision, and the acceptance is shown as resting on an AI approval",
        [
            {'ai_approval_shown': True, 'approval': {'record_id': 'TASK-114-approval', 'source_class': 'decision_agent'}, 'next_state': ['ACCEPTED'], 'not_fixed': ['decision', 'missing', 'reverify']},
        ],
    ),
    'ACC-15': (
        'operational human_review is satisfied, so no type is missing; NEEDS_REVIEW; the task stays IN_REVIEW; the review does not make the task ACCEPTED (a separate approval record is needed, as in ACC-14)',
        [
            {'approval': None, 'decision': ['NEEDS_REVIEW'], 'missing': [], 'next_state': ['IN_REVIEW'], 'not_fixed': ['reverify', 'ai_approval_shown']},
        ],
    ),
    'ACC-16': (
        'architecture ai_review (cross-model) is satisfied, so no type is missing; NEEDS_REVIEW; next state IN_REVIEW; neither review makes the task ACCEPTED (a separate approval record is needed, as in ACC-14)',
        [
            {'approval': None, 'decision': ['NEEDS_REVIEW'], 'missing': [], 'next_state': ['IN_REVIEW'], 'not_fixed': ['reverify', 'ai_approval_shown']},
        ],
    ),
    'ACC-17': (
        "the reviewer agent's review alone does not count for the entry; INSUFFICIENT_EVIDENCE: architecture, ai_review (cross-model) missing; next state REWORK, because the missing type is not one only a human can produce",
        [
            {'decision': ['INSUFFICIENT_EVIDENCE'], 'missing': [{'dimension': 'architecture', 'evidence_type': 'ai_review (cross-model)'}], 'next_state': ['REWORK'], 'not_fixed': ['reverify', 'approval', 'ai_approval_shown']},
        ],
    ),
    'ADV-01': (
        'REJECT or NEEDS_REWORK (which one is open); never NEEDS_REVIEW or ACCEPT; the task is not ACCEPTED',
        [
            {'decision': ['REJECT', 'NEEDS_REWORK'], 'next_state': ['DRAFT', 'READY', 'IN_PROGRESS', 'VERIFYING', 'DONE', 'IN_REVIEW', 'REWORK', 'ESCALATED', 'REJECTED', 'BLOCKED', 'STALE'], 'not_fixed': ['missing', 'reverify', 'approval', 'ai_approval_shown']},
        ],
    ),
    'ADV-03': (
        'NEEDS_REWORK; next state REWORK; the report authorizes nothing',
        [
            {'approval': None, 'decision': ['NEEDS_REWORK'], 'next_state': ['REWORK'], 'not_fixed': ['missing', 'reverify', 'ai_approval_shown']},
        ],
    ),
}


class FileKindTest(unittest.TestCase):
    """AC1: the file kind and the canonical form (section 2)."""

    def test_every_conformance_file_is_wrapped_canonical_json(self):
        value, files, _rows = load_tree()
        self.assertIsInstance(value, dict)
        for path, data in files.items():
            with self.subTest(path=path):
                self.assertIsInstance(unwrap(data), dict)
                self.assertEqual(wrap(unwrap(data)), data)

    def test_no_control_character_in_any_fixture(self):
        _value, files, _rows = load_tree()
        for path, data in files.items():
            with self.subTest(path=path):
                self.assertFalse(has_control_character(unwrap(data)))

    def test_canonical_form_of_values(self):
        self.assertEqual(canon({}), '{}')
        self.assertEqual(canon([]), '[]')
        self.assertEqual(canon({'b': 1, 'a': [True, None]}), '{\n  "a": [\n    true,\n    null\n  ],\n  "b": 1\n}')
        self.assertEqual(canon('a"b\\c\x01'), '"a\\"b\\\\c\\u0001"')
        self.assertEqual(canon('é/x'), '"é/x"')
        with self.assertRaises(Malformed):
            canon(1.5)

    def test_altered_files_are_malformed(self):
        good = wrap({'a': [1, 'x'], 'b': {}})
        self.assertEqual(unwrap(good), {'a': [1, 'x'], 'b': {}})
        text = good[len(FIRST):len(good) - len(LAST)]
        bad = {
            'no first part': text + LAST,
            'no last part': FIRST + text,
            'no final LF': good[:-1],
            'a comment before the first part': b'# x\n' + good,
            'a CR byte': good.replace(b'\n', b'\r\n', 1),
            'a byte-order mark': FIRST + b'\xef\xbb\xbf' + text + LAST,
            "three quotes inside": FIRST + text.replace(b'"x"', b"\"'''\"") + LAST,
            'keys out of order': FIRST + b'{\n  "b": {},\n  "a": [\n    1,\n    "x"\n  ]\n}\n' + LAST,
            'an indent of four': FIRST + b'{\n    "a": [],\n    "b": {}\n}\n' + LAST,
            'one line': FIRST + b'{"a": [], "b": {}}\n' + LAST,
            'a fraction': FIRST + b'{\n  "a": 1.0\n}\n' + LAST,
            'an exponent': FIRST + b'{\n  "a": 1e2\n}\n' + LAST,
            'a short escape': FIRST + b'{\n  "a": "\\n"\n}\n' + LAST,
            'an escaped slash': FIRST + b'{\n  "a": "\\/"\n}\n' + LAST,
            'an escaped letter': FIRST + b'{\n  "a": "\\u00e9"\n}\n' + LAST,
            'a duplicate key': FIRST + b'{\n  "a": 1,\n  "a": 1\n}\n' + LAST,
            'a constant JSON lacks': FIRST + b'{\n  "a": NaN\n}\n' + LAST,
            'not UTF-8': FIRST + b'{\n  "a": "\xff"\n}\n' + LAST,
            'trailing space': FIRST + b'{\n  "a": 1 \n}\n' + LAST,
            'an empty list on two lines': FIRST + b'{\n  "a": [\n  ]\n}\n' + LAST,
            'an uppercase hex escape': FIRST + b'{\n  "a": "\\u001F"\n}\n' + LAST,
            'no final LF in the JSON text': FIRST + text[:-1] + LAST,
            'a doubled final LF': FIRST + text + b'\n' + LAST,
            'a raw control character': FIRST + b'{\n  "a": "\x01"\n}\n' + LAST,
            'empty': b'',
        }
        for name, data in bad.items():
            with self.subTest(case=name):
                with self.assertRaises(Malformed):
                    unwrap(data)

    def test_wrap_refuses_three_quotes(self):
        with self.assertRaises(Malformed):
            wrap({'a': "'''"})


class SetFileTest(unittest.TestCase):
    """AC2: the set file (section 3) against the bound scenario file and the fixtures folder."""

    def test_the_set_file(self):
        value, files, rows = load_tree()
        self.assertEqual(check_set(value, rows, files), [])
        self.assertEqual(len(rows), 32)
        self.assertEqual([e['id'] for e in value['scenarios']], [r[0] for r in rows])
        with_fixture = [e['id'] for e in value['scenarios'] if e['fixture']]
        self.assertEqual(with_fixture, [r[0] for r in rows if r[2] == 'Verification'])
        self.assertEqual(len(with_fixture), 19)
        self.assertEqual(sum(1 for e in value['scenarios'] if e['fixture'] is None), 13)

    def test_rows_are_read_from_the_bound_file(self):
        rows = scenario_rows()
        self.assertEqual(rows[0][0], 'ACC-01')
        self.assertEqual(rows[-1][0], 'ADV-03')
        self.assertEqual({r[2] for r in rows}, set(CAPABILITIES))
        self.assertEqual([r[0] for r in rows if r[2] == 'Capability Boundaries'], ['ADV-02'])

    def test_a_row_that_is_not_six_cells_is_malformed(self):
        data = read(SCENARIO_FILE).replace(b'| ACC-01 | row NEEDS_REVIEW | defaults |', b'| ACC-01 | row NEEDS_REVIEW |', 1)
        self.assertNotEqual(data, read(SCENARIO_FILE))
        with self.assertRaises(Malformed):
            scenario_rows(data)

    def test_altered_sets_give_errors(self):
        value, files, rows = load_tree()

        def changed(edit):
            v = json.loads(json.dumps(value))
            edit(v)
            return check_set(v, rows, files)

        first = next(i for i, e in enumerate(value['scenarios']) if e['fixture'])
        cases = {
            'a fifth key': lambda v: v.update(extra=1),
            'set version': lambda v: v.update(scenario_set_version=3),
            'set file hash': lambda v: v.update(scenario_set_file_hash='0' * 64),
            'fixture set version': lambda v: v.update(fixture_set_version=2),
            'an entry removed': lambda v: v['scenarios'].pop(),
            'two entries swapped': lambda v: v['scenarios'].insert(0, v['scenarios'].pop(1)),
            'a row hash': lambda v: v['scenarios'][0].update(row_hash='0' * 64),
            'a capability': lambda v: v['scenarios'][0].update(capability='Resume Check'),
            'a fixture hash': lambda v: v['scenarios'][first]['fixture'].update(sha256='0' * 64),
            'a fixture path': lambda v: v['scenarios'][first]['fixture'].update(path='tests/conformance/x.py'),
            'a fixture dropped': lambda v: v['scenarios'][first].update(fixture=None),
            'a fixture outside Verification': lambda v: v['scenarios'][17].update(
                fixture=dict(v['scenarios'][first]['fixture'])),
            'an entry with an extra key': lambda v: v['scenarios'][0].update(note='x'),
            'a fixture that is not {path, sha256}': lambda v: v['scenarios'][first]['fixture'].pop('sha256'),
        }
        for name, edit in cases.items():
            with self.subTest(case=name):
                self.assertNotEqual(changed(edit), [])

    def test_an_unnamed_fixture_file_gives_an_error(self):
        value, files, rows = load_tree()
        more = dict(files)
        more[FIXTURE_DIR + '/extra.py'] = wrap({})
        self.assertNotEqual(check_set(value, rows, more), [])


class FixtureTest(unittest.TestCase):
    """AC3: each fixture file (section 4) against its set-file entry and specification 2's forms."""

    def setUp(self):
        self.value, self.files, self.rows = load_tree()
        self.entries = {e['id']: e for e in self.value['scenarios'] if e['fixture']}

    def fixture(self, sid):
        return unwrap(self.files[self.entries[sid]['fixture']['path']])

    def test_every_fixture(self):
        for sid, entry in self.entries.items():
            with self.subTest(scenario=sid):
                self.assertEqual(check_fixture(self.fixture(sid), entry), [])

    def test_altered_fixtures_give_errors(self):

        def changed(edit, sid='ACC-07'):
            v = json.loads(json.dumps(self.fixture(sid)))
            edit(v)
            return check_fixture(v, self.entries[sid])

        c = lambda v: v['cases'][0]
        cases = {
            'scenario id': lambda v: v.update(scenario='ACC-08'),
            'row hash': lambda v: v.update(row_hash='0' * 64),
            'a second case': lambda v: v['cases'].append(v['cases'][0]),
            'a case key missing': lambda v: c(v).pop('when'),
            'when against task_state': lambda v: c(v).update(when='re_evaluate'),
            'request key missing': lambda v: c(v)['request'].pop('retry_count'),
            'request commit': lambda v: c(v)['request'].update(evaluated_commit='abc'),
            'request hash': lambda v: c(v)['request'].update(task_content_hash='A' * 64),
            'request task id': lambda v: c(v)['request'].update(task_id='T-1'),
            'request state': lambda v: c(v)['request'].update(task_state='DONE!'),
            'request versions': lambda v: c(v)['request'].update(intent_versions={'SPEC-012': '3'}),
            'request retries': lambda v: c(v)['request'].update(retry_count={'used': -1, 'limit': 2}),
            'inputs key missing': lambda v: c(v)['inputs'].pop('auto_accept'),
            'inputs risk': lambda v: c(v)['inputs'].update(risk='severe'),
            'inputs flag': lambda v: c(v)['inputs'].update(owner_kept_act='no'),
            'inputs plan': lambda v: c(v)['inputs'].update(verification_plan=['scope']),
            'inputs profile': lambda v: c(v)['inputs'].update(evidence_profile=[{'dimension': 'security'}]),
            'inputs articles': lambda v: c(v)['inputs'].update(applicable_articles=[{'id': 'INV-001'}]),
            'a malformed record': lambda v: c(v)['records'][0].update(source_class='someone'),
            'a duplicate record id': lambda v: c(v)['records'].append(dict(c(v)['records'][0])),
            'an expected key both fixed and not fixed': lambda v: c(v)['expected'].update(next_state=['REWORK']),
            'an expected key neither': lambda v: c(v)['expected'].pop('reverify'),
            'an unknown expected key': lambda v: c(v)['expected'].update(reason='x'),
            'not_fixed names an unknown key': lambda v: c(v)['expected']['not_fixed'].append('reason'),
            'a decision outside the five': lambda v: c(v)['expected'].update(decision=['CONTINUE']),
            'an empty decision list': lambda v: c(v)['expected'].update(decision=[]),
            'a missing pair malformed': lambda v: c(v)['expected'].update(missing=[{'dimension': 'security'}]),
            'reverify names no record': lambda v: c(v)['expected'].update(reverify=['TASK-107-none']),
            'a fixture key added': lambda v: v.update(note='x'),
            'request paths': lambda v: c(v)['request'].update(changed_paths=['']),
            'inputs traces': lambda v: c(v)['inputs'].update(traces_to='SPEC-012'),
            'inputs policy version': lambda v: c(v)['inputs'].update(policy_version=''),
            'records not a list': lambda v: c(v).update(records={}),
            'expected without not_fixed': lambda v: c(v)['expected'].pop('not_fixed'),
        }
        self.assertEqual(changed(lambda v: None), [])
        for name, edit in cases.items():
            with self.subTest(case=name):
                self.assertNotEqual(changed(edit), [])
        approval = lambda v: (c(v)['expected'].update(approval={'record_id': 'TASK-111-approval',
                                                                 'source_class': 'decision_agent'}))
        self.assertNotEqual(changed(approval, 'ACC-11'), [])
        unknown = lambda v: c(v)['expected'].update(approval={'record_id': 'TASK-111-none', 'source_class': 'human_authority'})
        self.assertNotEqual(changed(unknown, 'ACC-11'), [])
        state = lambda v: c(v)['expected'].update(next_state=['DONE!'])
        self.assertNotEqual(changed(state, 'ACC-11'), [])
        shown = lambda v: c(v)['expected'].update(ai_approval_shown='yes')
        self.assertNotEqual(changed(shown, 'ACC-14'), [])


def cell_mismatches(data=None):
    """AC4: the ids whose Expected cell in the bound file (or in the given bytes) differs from the table's text."""
    cells = {sid: cell for sid, _h, _c, cell in scenario_rows(data)}
    return sorted(sid for sid, (cell, _expected) in EXPECTED_CELLS.items() if cells.get(sid) != cell)


def expected_mismatches(realised):
    """AC4: the ids whose fixture's expected values differ from the table's values, or that only one side names."""
    both = set(realised) & set(EXPECTED_CELLS)
    wrong = [sid for sid in both if [c['expected'] for c in realised[sid]['cases']] != EXPECTED_CELLS[sid][1]]
    return sorted(set(realised) ^ set(EXPECTED_CELLS)) + sorted(wrong)


def realised_fixtures():
    """The parsed fixture of every realised scenario, by id, as the set file names them."""
    value, files, _rows = load_tree()
    return {e['id']: unwrap(files[e['fixture']['path']]) for e in value['scenarios'] if e['fixture']}


class FaithfulnessTest(unittest.TestCase):
    """AC4: each fixture's expected values against its scenario's Expected cell (section 5)."""

    def test_cells_equal_the_bound_file(self):
        self.assertEqual(cell_mismatches(), [])

    def test_a_changed_cell_is_caught(self):
        lines = read(SCENARIO_FILE).split(b'\n')
        i = next(k for k, line in enumerate(lines) if line.startswith(b'| ACC-05 | '))
        cell = b' | ' + EXPECTED_CELLS['ACC-05'][0].encode('utf-8') + b' | '
        self.assertEqual(lines[i].count(cell), 1)
        lines[i] = lines[i].replace(cell, cell[:-3] + b'; changed | ')
        self.assertEqual(cell_mismatches(b'\n'.join(lines)), ['ACC-05'])

    def test_fixtures_hold_the_table_values(self):
        self.assertEqual(expected_mismatches(realised_fixtures()), [])

    def test_a_changed_expected_value_is_caught(self):
        realised = realised_fixtures()
        realised['ACC-05']['cases'][0]['expected']['next_state'] = ['IN_REVIEW']
        self.assertEqual(expected_mismatches(realised), ['ACC-05'])

    def test_a_missing_or_extra_fixture_is_caught(self):
        realised = realised_fixtures()
        realised['RC-01'] = realised.pop('ACC-05')
        self.assertEqual(expected_mismatches(realised), ['ACC-05', 'RC-01'])


if __name__ == '__main__':
    unittest.main()
