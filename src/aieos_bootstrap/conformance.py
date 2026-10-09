"""The conformance runner of gov-AIEOS (task TASK-003; docs/specs/conformance-files.md revision 2, section 6).

``run`` reads the frozen set file, its freeze approval, the fixtures and the bound scenario file from the tree it is
given, which is the base (governor-spec.md section 4 rule 1); calls the governor's entry point for each case when one
exists; compares the observed decision records with the expected values; and returns the run record and its record of
specification 2 section 6.2. ``main`` is the command-line entry.

Limits (TASK-003 AC11):
- It checks its inputs and compares values; it never decides an acceptance. With no governor every scenario is
  NOT_RUN, and the outcome of a run is fail.
- It does not check how the governor derives the inputs of governor-spec.md section 3.2: the fixtures give them as
  values (conformance-files.md section 1).
- The runner and the governor are taken from the base only when the CI channel runs this module from a checkout of
  the base; the record's source class holds only for a run in the CI channel; how a run's results are read there is
  left to the CI workflow's next revision (AC9).
- It checks that the set file's hash has a freeze approval, not that it is the latest one (AC4).
- The governor-origin check (AC1) reads the module's file name, which code run earlier in the process can set (AC11).
- It reads files as bytes only, never imports or executes a set or fixture module, writes nothing, starts no process
  and makes no network call.

Readings that the contract marks "(reading)" are noted where they are applied.
"""

import copy
import hashlib
import json
import pathlib
import re
import sys

from aieos_bootstrap import records

RUNNER_PATH = 'src/aieos_bootstrap/conformance.py'
GOVERNOR_PATH = 'src/aieos_bootstrap/governor.py'
GOVERNOR_MODULE = 'aieos_bootstrap.governor'
SET_FILE = 'tests/conformance/set.py'
FIXTURE_DIR = 'tests/conformance/fixtures'
SCENARIO_FILE = 'docs/pre-genesis/conformance-scenarios-initial.md'
RECORDS_DIR = 'docs/records'
RECORD_PREFIX = 'conformance-run-'

FIRST, LAST = b"DATA = r'''", b"'''\n"
BOM = b'\xef\xbb\xbf'
PASS, FAIL, NOT_RUN = 'PASS', 'FAIL', 'NOT_RUN'
ABSENT, LOADED, FAILED, STAND_IN = 'absent', 'loaded', 'failed', 'stand-in'

ACCEPTANCE = ('ACCEPT', 'NEEDS_REVIEW', 'INSUFFICIENT_EVIDENCE', 'NEEDS_REWORK', 'REJECT')
STATES = ('DRAFT', 'READY', 'IN_PROGRESS', 'VERIFYING', 'ACCEPTED', 'DONE', 'IN_REVIEW', 'REWORK', 'ESCALATED',
          'REJECTED', 'BLOCKED', 'STALE')
CAPABILITIES = ('Verification', 'Resume Check', 'Risk Engine', 'Capability Boundaries')
SET_KEYS = frozenset({'scenario_set_version', 'scenario_set_file_hash', 'fixture_set_version', 'scenarios'})
ENTRY_KEYS = frozenset({'id', 'row_hash', 'capability', 'fixture'})
CASE_KEYS = frozenset({'request', 'inputs', 'records', 'when', 'expected'})
EXPECTED_KEYS = ('decision', 'next_state', 'missing', 'reverify', 'approval', 'ai_approval_shown')
REQUEST_KEYS = frozenset({'task_id', 'task_content_hash', 'evaluated_commit', 'intent_versions', 'task_state',
                          'changed_paths', 'retry_count'})
INPUT_KEYS = frozenset({'traces_to', 'risk', 'owner_kept_act', 'weakens_evidence', 'delegation_in_force',
                        'auto_accept', 'verification_plan', 'evidence_profile', 'applicable_articles',
                        'policy_version', 'level_version', 'ruleset_version'})
APPROVERS = frozenset({'decision_agent', 'human_authority'})

_HEX64 = re.compile(r'[0-9a-f]{64}')
_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_TASK = re.compile(r'TASK-[0-9]+')
_VERSION = re.compile(r'v[0-9]+')
_GATE = re.compile(r'G[0-9]+')
_ROW = re.compile(r'^\| ((?:ACC|RISK|RC|ADV)-[0-9]+) \| ')


class Malformed(ValueError):
    """A conformance file that is not in the form of conformance-files.md section 2."""


class Run:
    """One run: the run record (``value``, and ``text``, its canonical bytes), its record of specification 2 section
    6.2 (``record``), why it does not count (``problems``, empty when it counts) and why each scenario got its result
    (``reasons``, by scenario id)."""

    def __init__(self, value, text, record, problems, reasons):
        self.value = value
        self.text = text
        self.record = record
        self.problems = problems
        self.reasons = reasons

    @property
    def results(self):
        return {r['id']: r['result'] for r in self.value['results']}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canon(value, indent=0):
    """The canonical JSON text of one value (conformance-files.md section 2), without the final LF."""
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


def canonical_text(value):
    """The canonical JSON text of one value, with its final LF, as UTF-8 bytes."""
    return (canon(value) + '\n').encode('utf-8')


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


def _loads(text):
    return json.loads(text, object_pairs_hook=_pairs, parse_float=_no_float, parse_constant=_no_constant)


def unwrap(data):
    """The JSON value a set or fixture file wraps (AC2), or Malformed: the two fixed parts, then canonical JSON."""
    if not isinstance(data, bytes) or len(data) < len(FIRST) + len(LAST) or not data.startswith(FIRST) \
            or not data.endswith(LAST):
        raise Malformed('the file does not start with the first part and end with the last part')
    text = data[len(FIRST):len(data) - len(LAST)]
    if b"'''" in text:
        raise Malformed("the JSON text holds '''")
    if text.startswith(BOM) or b'\r' in text:
        raise Malformed('a byte-order mark or a CR byte')
    try:
        decoded = text.decode('utf-8')
        value = _loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Malformed('not UTF-8 JSON: %s' % exc) from None
    if canon(value) + '\n' != decoded:
        raise Malformed('the JSON text is not in the canonical form')
    return value


def module_path(scenario_id):
    """The fixture path of a scenario (conformance-files.md section 2): its id in lowercase, '-' replaced by '_'."""
    return FIXTURE_DIR + '/' + scenario_id.lower().replace('-', '_') + '.py'


def _is_str(v):
    return isinstance(v, str) and v != ''


def _is_str_list(v):
    return isinstance(v, list) and all(_is_str(x) for x in v)


def _is_int(v, minimum=0):
    return isinstance(v, int) and not isinstance(v, bool) and v >= minimum


def _is_hex64(v):
    return isinstance(v, str) and _HEX64.fullmatch(v) is not None


class _Tree:
    """The inputs of a run (AC1): one byte reader of paths relative to the root and one listing of the records files.
    By default they are pathlib's read_bytes and a sorted glob under the root; an absent or unreadable file reads as
    None."""

    def __init__(self, root, read=None, listing=None):
        self.root = root
        self._read = read
        self._listing = listing

    def read(self, path):
        if self._read is not None:
            return self._read(path)
        p = self.root / path
        try:
            return p.read_bytes() if p.is_file() else None
        except OSError:
            return None

    def records_files(self):
        if self._listing is not None:
            return list(self._listing())
        return sorted(p.relative_to(self.root).as_posix() for p in (self.root / RECORDS_DIR).glob('*.jsonl')
                      if p.is_file())


def scenario_rows(data):
    """The scenario rows of the bound file: (ids in the file's order, row hash by id). A row hash is the SHA-256 of the
    row line without its line end (decision D-115 C1's method); an id on two rows maps to None (reading)."""
    if data is None:
        return [], {}
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return [], {}
    order, hashes = [], {}
    for line in text.split('\n'):
        m = _ROW.match(line)
        if not m:
            continue
        sid = m.group(1)
        if sid in hashes:
            hashes[sid] = None
        else:
            order.append(sid)
            hashes[sid] = sha256(line.encode('utf-8'))
    return order, hashes


def check_set(value):
    """The form of the set file's JSON object (AC3; conformance-files.md section 3). Returns a list of errors."""
    if not isinstance(value, dict) or set(value) != SET_KEYS:
        return ['the set is not exactly the four keys of section 3']
    errors = []
    if not _is_int(value['scenario_set_version']):
        errors.append('scenario_set_version is not an integer')
    if not _is_hex64(value['scenario_set_file_hash']):
        errors.append('scenario_set_file_hash is not 64 lowercase hex digits')
    if not _is_int(value['fixture_set_version']):
        errors.append('fixture_set_version is not an integer')
    entries = value['scenarios']
    if not isinstance(entries, list) or not entries:
        return errors + ['scenarios is not a non-empty list']
    ids = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != ENTRY_KEYS:
            errors.append('an entry is not exactly {id, row_hash, capability, fixture}')
            continue
        ids.append(entry['id'])
        if not _is_str(entry['id']):
            errors.append('an entry id is not a non-empty string')
        if not _is_hex64(entry['row_hash']):
            errors.append('the row_hash of %s is not 64 lowercase hex digits' % entry['id'])
        if entry['capability'] not in CAPABILITIES:
            errors.append('the capability of %s is not one of section 3' % entry['id'])
        fixture = entry['fixture']
        if fixture is not None and not (isinstance(fixture, dict) and set(fixture) == {'path', 'sha256'}
                                        and _is_str(fixture['path']) and _is_hex64(fixture['sha256'])):
            errors.append('the fixture of %s is not null or exactly {path, sha256}' % entry['id'])
    if len(set(map(str, ids))) != len(ids):
        errors.append('an id names two entries (reading)')
    return errors


def freeze_approval(tree, set_sha):
    """Whether a freeze approval binds the set file's SHA-256 (AC4): a record of a docs/records/*.jsonl file with
    fact_kind authority, source_class decision_agent or human_authority, and approval_binding exactly {kind:
    change_request, hash}, the hash being the set file's. Fail closed (reading): no records file, a file that is
    absent, not UTF-8 or holds a CR byte or a byte-order mark, or any line that is not one JSON object without a
    check_record finding, makes this false. Returns (found, reason)."""
    paths = tree.records_files()
    if not paths:
        return False, 'no records file'
    found = False
    for path in paths:
        data = tree.read(path)
        if data is None or data.startswith(BOM) or b'\r' in data:
            return False, 'the records file %s is unreadable' % path
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            return False, 'the records file %s is not UTF-8' % path
        lines = text.split('\n')
        if lines and lines[-1] == '':
            lines = lines[:-1]
        for number, line in enumerate(lines, 1):
            try:
                rec = _loads(line)
            except (json.JSONDecodeError, Malformed):
                return False, '%s line %d is not one JSON object' % (path, number)
            if not isinstance(rec, dict) or records.check_record(rec):
                return False, '%s line %d is not a record without a finding' % (path, number)
            binding = rec.get('approval_binding')
            if rec.get('fact_kind') == 'authority' and rec.get('source_class') in APPROVERS \
                    and isinstance(binding, dict) and set(binding) == {'kind', 'hash'} \
                    and binding['kind'] == 'change_request' and binding['hash'] == set_sha:
                found = True
    return found, '' if found else 'no freeze approval binds the set file\'s SHA-256'


def _check_request(req):
    if not isinstance(req, dict) or set(req) != REQUEST_KEYS:
        return ['request is not exactly the keys of specification 2 section 6.5']
    errors = []
    if not (isinstance(req['task_id'], str) and _TASK.fullmatch(req['task_id'])):
        errors.append('task_id')
    if not _is_hex64(req['task_content_hash']):
        errors.append('task_content_hash')
    if not (isinstance(req['evaluated_commit'], str) and _COMMIT.fullmatch(req['evaluated_commit'])):
        errors.append('evaluated_commit')
    iv = req['intent_versions']
    if not (isinstance(iv, dict) and all(_is_str(k) and isinstance(v, str) and _VERSION.fullmatch(v)
                                         for k, v in iv.items())):
        errors.append('intent_versions')
    if req['task_state'] not in STATES:
        errors.append('task_state')
    if not _is_str_list(req['changed_paths']):
        errors.append('changed_paths')
    rc = req['retry_count']
    if not (isinstance(rc, dict) and set(rc) == {'used', 'limit'} and _is_int(rc['used']) and _is_int(rc['limit'])):
        errors.append('retry_count')
    return ['request ' + e for e in errors]


def _check_inputs(inp):
    if not isinstance(inp, dict) or set(inp) != INPUT_KEYS:
        return ['inputs is not exactly the keys of section 4']
    errors = []
    if not _is_str_list(inp['traces_to']):
        errors.append('traces_to')
    if inp['risk'] not in ('low', 'medium', 'high', 'critical'):
        errors.append('risk')
    for key in ('owner_kept_act', 'weakens_evidence', 'delegation_in_force', 'auto_accept'):
        if not isinstance(inp[key], bool):
            errors.append(key)
    if not (_is_str_list(inp['verification_plan']) and all(_GATE.fullmatch(g) for g in inp['verification_plan'])):
        errors.append('verification_plan')
    prof = inp['evidence_profile']
    if not (isinstance(prof, list) and all(isinstance(e, dict) and set(e) == {'dimension', 'evidence_types'}
                                           and _is_str(e['dimension']) and _is_str_list(e['evidence_types'])
                                           for e in prof)):
        errors.append('evidence_profile')
    arts = inp['applicable_articles']
    if not (isinstance(arts, list) and all(isinstance(a, dict) and set(a) == {'id', 'evidence_required'}
                                           and _is_str(a['id']) and _is_str_list(a['evidence_required'])
                                           for a in arts)):
        errors.append('applicable_articles')
    for key in ('policy_version', 'level_version', 'ruleset_version'):
        if not _is_str(inp[key]):
            errors.append(key)
    return ['inputs ' + e for e in errors]


def _check_expected(exp, case_records):
    if not isinstance(exp, dict) or 'not_fixed' not in exp:
        return ['expected has no not_fixed']
    not_fixed = exp['not_fixed']
    if not (_is_str_list(not_fixed) and len(set(not_fixed)) == len(not_fixed) and set(not_fixed) <= set(EXPECTED_KEYS)):
        return ['not_fixed is not a list of distinct keys of expected']
    errors = []
    for key in EXPECTED_KEYS:
        if (key in exp) == (key in not_fixed):
            errors.append('expected %s is not either present or in not_fixed' % key)
    if set(exp) - set(EXPECTED_KEYS) - {'not_fixed'}:
        errors.append('expected has a key that section 4 does not name')
    ids = {r.get('record_id'): r for r in case_records if isinstance(r, dict)}
    if 'decision' in exp and not (isinstance(exp['decision'], list) and exp['decision']
                                  and all(d in ACCEPTANCE for d in exp['decision'])):
        errors.append('expected decision')
    if 'next_state' in exp and not (isinstance(exp['next_state'], list) and exp['next_state']
                                    and all(s in STATES for s in exp['next_state'])):
        errors.append('expected next_state')
    if 'missing' in exp and not (isinstance(exp['missing'], list) and all(
            isinstance(m, dict) and set(m) == {'dimension', 'evidence_type'} and _is_str(m['dimension'])
            and _is_str(m['evidence_type']) for m in exp['missing'])):
        errors.append('expected missing')
    if 'reverify' in exp and not (_is_str_list(exp['reverify']) and all(r in ids for r in exp['reverify'])):
        errors.append('expected reverify')
    if 'approval' in exp:
        a = exp['approval']
        if a is not None and not (isinstance(a, dict) and set(a) == {'record_id', 'source_class'}
                                  and a['record_id'] in ids
                                  and ids[a['record_id']].get('source_class') == a['source_class']):
            errors.append('expected approval')
    if 'ai_approval_shown' in exp and not isinstance(exp['ai_approval_shown'], bool):
        errors.append('expected ai_approval_shown')
    return errors


def check_fixture(value, entry):
    """The form of one fixture's JSON object against its set entry (AC5; conformance-files.md section 4). Returns a
    list of errors."""
    if not isinstance(value, dict) or set(value) != {'scenario', 'row_hash', 'cases'}:
        return ['the fixture is not exactly scenario, row_hash and cases']
    errors = []
    if value['scenario'] != entry['id'] or value['row_hash'] != entry['row_hash']:
        errors.append('scenario or row_hash differs from the set entry')
    cases = value['cases']
    if not isinstance(cases, list) or not cases:
        return errors + ['cases is not a non-empty list']
    for n, case in enumerate(cases, 1):
        where = 'case %d: ' % n
        if not isinstance(case, dict) or set(case) != CASE_KEYS:
            errors.append(where + 'not exactly request, inputs, records, when and expected')
            continue
        errors.extend(where + e for e in _check_request(case['request']))
        errors.extend(where + e for e in _check_inputs(case['inputs']))
        state = case['request'].get('task_state') if isinstance(case['request'], dict) else None
        if not ((case['when'] == 'evaluate' and state == 'VERIFYING')
                or (case['when'] == 're_evaluate' and state == 'IN_REVIEW')):
            errors.append(where + 'when does not agree with task_state')
        case_records = case['records']
        if not isinstance(case_records, list):
            errors.append(where + 'records is not a list')
            continue
        seen = set()
        for rec in case_records:
            if records.check_record(rec):
                errors.append(where + 'a record with a check_record finding')
            rid = rec.get('record_id') if isinstance(rec, dict) else None
            if rid in seen:
                errors.append(where + 'a repeated record id')
            seen.add(rid)
        errors.extend(where + e for e in _check_expected(case['expected'], case_records))
    return errors


def load_governor(root):
    """The governor's entry point (AC6): (evaluate, status). The module is loaded by a plain import statement. It is
    absent when the import raises ModuleNotFoundError naming it; it is the base's only when the loaded module's file
    is the root's src/aieos_bootstrap/governor.py (reading); any other failure, or no callable evaluate, is FAILED."""
    try:
        import aieos_bootstrap.governor as governor
    except ModuleNotFoundError as exc:
        return None, (ABSENT if exc.name == GOVERNOR_MODULE else FAILED)
    except Exception:
        return None, FAILED
    path = getattr(governor, '__file__', None)
    if not isinstance(path, str) or pathlib.Path(path).resolve() != (root / GOVERNOR_PATH).resolve():
        return None, FAILED
    evaluate = getattr(governor, 'evaluate', None)
    if not callable(evaluate):
        return None, FAILED
    return evaluate, LOADED


def decision_problem(value):
    """Why a returned value is not a decision record (AC7), or '' when it is one. A record with decision null and
    error present is a decision record; otherwise rests_on_ai must be exactly {entries, approval} with approval a
    boolean (reading: specification 2 section 6.4 names rests_on_ai for gov-AIEOS; section 6 of conformance-files.md
    gives its form)."""
    if not isinstance(value, dict):
        return 'the call returned no JSON object'
    if records.check_decision('decision.acceptance', value):
        return 'the call returned a value with a check_decision finding'
    if value['decision'] is not None:
        ai = value.get('rests_on_ai')
        if not (isinstance(ai, dict) and set(ai) == {'entries', 'approval'} and isinstance(ai['approval'], bool)):
            return 'the decision record has no rests_on_ai of the form {entries, approval}'
    return ''


def _missing_pairs(profile):
    """The {dimension, evidence_type} pairs of profile_used's missing_types, or None when they cannot be read."""
    if not isinstance(profile, list):
        return None
    pairs = set()
    for item in profile:
        if not (isinstance(item, dict) and _is_str(item.get('dimension')) and _is_str_list(item.get('missing_types'))):
            return None
        pairs.update((item['dimension'], t) for t in item['missing_types'])
    return pairs


def compare(expected, observed, case_records):
    """The keys of expected that the observed decision record does not meet (AC7; conformance-files.md section 6).
    A key read from the record that is absent fails its comparison, except approval_record, read as null
    (reading)."""
    not_fixed = set(expected['not_fixed'])
    out = []
    if 'decision' not in not_fixed and ('decision' not in observed or observed['decision'] not in expected['decision']):
        out.append('decision')
    if 'next_state' not in not_fixed and ('next_task_state' not in observed
                                          or observed['next_task_state'] not in expected['next_state']):
        out.append('next_state')
    if 'missing' not in not_fixed:
        pairs = _missing_pairs(observed.get('profile_used'))
        if pairs is None or pairs != {(m['dimension'], m['evidence_type']) for m in expected['missing']}:
            out.append('missing')
    if 'reverify' not in not_fixed:
        seen = observed.get('reverify')
        if not isinstance(seen, list) or not all(r in seen for r in expected['reverify']):
            out.append('reverify')
    if 'approval' not in not_fixed:
        cited = observed.get('approval_record')
        want = expected['approval']
        if want is None:
            if cited is not None:
                out.append('approval')
        else:
            by_id = {r.get('record_id'): r for r in case_records if isinstance(r, dict)}
            if cited != want['record_id'] or cited not in by_id \
                    or by_id[cited].get('source_class') != want['source_class']:
                out.append('approval')
    if 'ai_approval_shown' not in not_fixed:
        ai = observed.get('rests_on_ai')
        if not (isinstance(ai, dict) and ai.get('approval') == expected['ai_approval_shown']
                and isinstance(ai.get('approval'), bool)):
            out.append('ai_approval_shown')
    return out


def run_scenario(tree, entry, rows, evaluate):
    """One scenario's result and its reason (AC5, AC7): NOT_RUN, with none of its cases run, for a fixture condition;
    NOT_RUN for no entry point; otherwise each case is called and compared, and a failed case makes it FAIL before any
    NOT_RUN of a call."""
    sid, fixture = entry['id'], entry['fixture']
    if fixture is None:
        return NOT_RUN, 'no fixture'
    if fixture['path'] != module_path(sid):
        return NOT_RUN, 'the fixture path is not %s' % module_path(sid)
    # The row is checked before the file is read, so that only a path built from an id of the bound file is read.
    if rows.get(sid) is None or rows[sid] != entry['row_hash']:
        return NOT_RUN, 'the row hash differs from the bound scenario file'
    data = tree.read(fixture['path'])
    if data is None:
        return NOT_RUN, 'the fixture file is missing'
    if sha256(data) != fixture['sha256']:
        return NOT_RUN, 'the fixture\'s SHA-256 differs from its set entry'
    try:
        value = unwrap(data)
    except Malformed as exc:
        return NOT_RUN, 'the fixture is malformed: %s' % exc
    errors = check_fixture(value, entry)
    if errors:
        return NOT_RUN, 'the fixture is malformed: %s' % errors[0]
    if evaluate is None:
        return NOT_RUN, 'the entry point is absent'
    failed, not_run = [], ''
    for n, case in enumerate(value['cases'], 1):
        try:
            observed = evaluate(copy.deepcopy(case['request']), copy.deepcopy(case['inputs']),
                                copy.deepcopy(case['records']))
        except Exception as exc:
            observed, problem = None, 'case %d: the call raised %s' % (n, type(exc).__name__)
        else:
            problem = decision_problem(observed)
            if problem:
                problem = 'case %d: %s' % (n, problem)
        if problem:
            not_run = not_run or problem
        else:
            failed.extend('case %d: %s' % (n, key) for key in compare(case['expected'], observed, case['records']))
    if failed:
        return FAIL, 'not met: ' + ', '.join(failed)
    if not_run:
        return NOT_RUN, not_run
    return PASS, ''


def outcome(counts, results, with_fixture):
    """The record's outcome (AC8): pass exactly when the run counts and every scenario with a fixture is PASS; a run
    with no scenario that has a fixture is fail (reading)."""
    return 'pass' if counts and with_fixture and all(results[i] == PASS for i in with_fixture) else 'fail'


def run(root, commit, task, read=None, listing=None, evaluate=None):
    """One conformance run over the tree at ``root``, the base (AC1). ``commit`` and ``task`` are only recorded.
    ``read`` and ``listing`` replace the default byte reader and records listing; ``evaluate`` is a test seam: a run
    with it never counts and its governor_identity is null (AC6). Raises ValueError for a commit or task id of the
    wrong form."""
    if not (isinstance(commit, str) and _COMMIT.fullmatch(commit)):
        raise ValueError('the commit is not a full lowercase hex commit id')
    if not (isinstance(task, str) and _TASK.fullmatch(task)):
        raise ValueError('the task id is not TASK- followed by digits')
    root = pathlib.Path(root)
    tree = _Tree(root, read, listing)
    problems = []

    runner_data = tree.read(RUNNER_PATH)
    runner_sha = sha256(runner_data) if runner_data is not None else None
    if runner_data is None or runner_data != pathlib.Path(__file__).read_bytes():
        problems.append('the running runner is not the root\'s (reading)')

    order, rows = scenario_rows(tree.read(SCENARIO_FILE))
    scenario_data = tree.read(SCENARIO_FILE)
    set_data = tree.read(SET_FILE)
    set_sha = sha256(set_data) if set_data is not None else None
    set_value = None
    if set_data is None:
        problems.append('the set file is missing')
    else:
        try:
            value = unwrap(set_data)
        except Malformed as exc:
            problems.append('the set file is malformed: %s' % exc)
        else:
            errors = check_set(value)
            if errors:
                problems.append('the set file is malformed: %s' % errors[0])
            else:
                set_value = value
    if set_value is not None:
        if scenario_data is None or set_value['scenario_set_file_hash'] != sha256(scenario_data):
            problems.append('scenario_set_file_hash differs from the bound scenario file')
        found, reason = freeze_approval(tree, set_sha)
        if not found:
            problems.append(reason)

    identity = None
    if evaluate is not None:
        status = STAND_IN
    else:
        evaluate, status = load_governor(root)
        if status == LOADED:
            governor_data = tree.read(GOVERNOR_PATH)
            if governor_data is None:
                evaluate, status = None, FAILED
            else:
                identity = sha256(governor_data)
        if status == FAILED:
            problems.append('the governor could not be loaded from the root (reading)')
    blocking = list(problems)
    if status == STAND_IN:
        problems.append('a stand-in governor (reading)')

    entries = set_value['scenarios'] if set_value is not None else [{'id': i, 'fixture': None} for i in order]
    results, reasons, with_fixture = [], {}, []
    for entry in entries:
        if set_value is not None and entry['fixture'] is not None:
            with_fixture.append(entry['id'])
        if blocking:
            result, reason = NOT_RUN, 'the run does not count: %s' % blocking[0]
        else:
            result, reason = run_scenario(tree, entry, rows, evaluate if status in (LOADED, STAND_IN) else None)
        results.append({'id': entry['id'], 'result': result})
        reasons[entry['id']] = reason
    counts = not problems
    value = {
        'set_file_sha256': set_sha,
        'scenario_set_version': set_value['scenario_set_version'] if set_value is not None else None,
        'fixture_set_version': set_value['fixture_set_version'] if set_value is not None else None,
        'runner': {'path': RUNNER_PATH, 'sha256': runner_sha},
        'governor_identity': identity,
        'commit': commit,
        'counts': counts,
        'results': results,
    }
    text = canonical_text(value)
    text_sha = sha256(text)
    by_id = {r['id']: r['result'] for r in results}
    record = {
        'record_id': RECORD_PREFIX + text_sha,
        'fact_kind': 'observation',
        'source_class': 'deterministic_tool_external_ci',
        'recorder': RUNNER_PATH + ' ' + (runner_sha or 'absent at the root'),
        'subject': task,
        'evidence_type': 'conformance_run',
        'dimension': 'functional',
        'outcome': outcome(counts, by_id, with_fixture),
        'commit': commit,
        'refers_to': text_sha,
    }
    return Run(value, text, record, problems, reasons)


def main(argv=None):
    """The command-line entry (AC9): the root, the commit and the task id. Prints the run record's text, then the
    record as one JSON line with its keys sorted; returns 0 for outcome pass, 1 for fail and 2 for wrong arguments.
    It never takes an evaluate function."""
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 3:
        print('usage: conformance.py <root> <commit> <task id>', file=sys.stderr)
        return 2
    try:
        result = run(args[0], args[1], args[2])
    except ValueError as exc:
        print('conformance.py: %s' % exc, file=sys.stderr)
        return 2
    print(result.text.decode('utf-8'), end='')
    print(json.dumps(result.record, sort_keys=True, ensure_ascii=False))
    return 0 if result.record['outcome'] == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())
