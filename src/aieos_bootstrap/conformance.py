"""The conformance runner of gov-AIEOS (task TASK-003; docs/specs/conformance-files.md revision 2, section 6), with
the Resume Check entry of task TASK-006 (conformance-files.md revision 4, section 9), the Risk Engine entry of task
TASK-017 (conformance-files.md revision 7, section 10) and the Capability Boundaries entry of task TASK-056
(conformance-files.md revision 10, section 11).

The Capability Boundaries entry (TASK-056): per case, one in-memory stand-in for the writer (a store and a log whose
appends eventlog.append decides, returning the writer's own result types, opening and writing no file) and a read
stand-in answering from the fixture's commit table; then replay.replay, the continuation through adapter.start,
adapter.submit and adapter.end, and evaluation.evaluate_task, all taken from the root, compared as section 11 says.

Limits of TASK-056 (its AC16):
- No Capability Boundaries fixture exists and ADV-02's set entry is null, so a run over the repository's tree gives
  ADV-02 NOT_RUN and its run record is unchanged but for the runner's own hash.
- It checks its inputs and compares values; it never decides an execution decision or an acceptance.
- A passing ADV-02 shows only the core's handling of a recorded observation, never that any hook observes anything
  (C6 and the T3 tier stay unmeasured).
- The fixture's values depend on the exact count of lines the core appends (log_seq), so a core change that adds a
  line shows as NOT_RUN, never FAIL and never PASS.
- In the CI channel the base run takes the runner from the base, so this entry first runs there after it lands on
  main; running ADV-02 needs its fixture and the set file's entry (DEF-0072 step 3).
- The stand-ins copy test code into the runner (a known cost; no new module).

Limits of TASK-017 (its AC15):
- No Risk Engine fixture exists and RISK-01's set entry is null, so a run over the repository's tree gives RISK-01
  NOT_RUN and its run record is unchanged but for the runner's own hash.
- It checks its inputs and compares values; it never decides a classification or an acceptance. It reads the
  policy's rules only from a fixture's values, and its path matcher reads only the pattern forms of the risk rules'
  section 2 point 6, so a fixture with any other form is NOT_RUN, never PASS.
- A derivation that raises on well-formed values is NOT_RUN with its reason shown, never PASS.

``run`` reads the frozen set file, its freeze approval, the fixtures and the bound scenario file from the tree it is
given, which is the base (governor-spec.md section 4 rule 1); chooses each scenario's entry by the capability of its
set entry, which must equal the capability the bound scenario file gives its id; calls the governor's entry point for
a Verification case, or the Resume Check entry point for a Resume Check case, when one exists; compares the observed
decision records with the expected values; and returns the run record and its record of specification 2 section 6.2.
``main`` is the command-line entry.

Limits of TASK-006 (its AC12):
- No Resume Check exists and the set file names no Resume Check fixture, so a run over the repository's tree gives
  every Resume Check scenario NOT_RUN and its run record has exactly TASK-003's keys.
- It checks a Resume Check fixture's form only as far as TASK-006 AC5 says, and compares the observed execution
  decision with the expected one; it never decides an execution or an acceptance, and it does not check how a Resume
  Check derives the inputs of specification 3 section 1, which the fixtures give as values.
- The capability of an id is read from the bound scenario file's table and heading layout; a later revision of that
  file that changes the layout makes its scenarios NOT_RUN, never PASS.
- Running the Resume Check scenarios in the CI channel needs the set file's Resume Check entries and a later revision
  of the CI workflow, which are not part of this module.

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
import datetime
import hashlib
import json
import pathlib
import re
import sys

from aieos_bootstrap import records

RUNNER_PATH = 'src/aieos_bootstrap/conformance.py'
GOVERNOR_PATH = 'src/aieos_bootstrap/governor.py'
GOVERNOR_MODULE = 'aieos_bootstrap.governor'
RESUME_CHECK_PATH = 'src/aieos_bootstrap/resume_check.py'
RESUME_CHECK_MODULE = 'aieos_bootstrap.resume_check'
SET_FILE = 'tests/conformance/set.py'
FIXTURE_DIR = 'tests/conformance/fixtures'
RC_FIXTURE_DIR = 'tests/conformance/fixtures_rc'
RISK_FIXTURE_DIR = 'tests/conformance/fixtures_risk'
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
VERIFICATION, RESUME_CHECK = 'Verification', 'Resume Check'
RC_CASE_KEYS = frozenset({'inputs', 'when', 'expected'})
RC_INPUT_KEYS = frozenset({'task_id', 'log_seq', 'task_state', 'contract', 'contract_hash', 'approved_contract_hash',
                           'head_commit', 'base_is_ancestor', 'commits', 'components', 'interfaces', 'symbols',
                           'schemas', 'derived_read_set', 'observed_read_set', 'intent_current', 'dependencies',
                           'articles', 'runtime', 'risk_rules', 'policy_version', 'budget_use'})
RC_STATES = ('READY', 'REWORK', 'IN_PROGRESS')
EXECUTION = records.EXECUTION_DECISIONS
# TASK-017 (conformance-files.md section 10).
RISK_ENGINE = 'Risk Engine'
RISK_CASE_KEYS = frozenset({'values', 'request', 'records', 'when', 'expected'})
RISK_VALUE_KEYS = frozenset({'contract', 'changed_paths', 'risk_rules', 'owner_kept_rules', 'articles',
                             'default_profiles', 'requirement_profiles', 'delegation', 'evidence_comparison',
                             'auto_accept', 'policy_version', 'level_version', 'ruleset_version'})
RISK_EXPECTED_KEYS = frozenset({'risk_not', 'profile_excludes', 'not_fixed'})
RISKS = ('low', 'medium', 'high', 'critical')
LOW_PAIRS = frozenset({('functional', 'build'), ('functional', 'lint')})
# TASK-056 (conformance-files.md section 11).
CAPABILITY_BOUNDARIES = 'Capability Boundaries'
CB_FIXTURE_DIR = 'tests/conformance/fixtures_cb'
CB_MODULES = ('replay', 'adapter', 'evaluation', 'eventlog', 'writer')
CB_RECORDED = ('replay', 'adapter', 'evaluation')
CB_ROOT_NAME = 'conformance-cb-no-such-root'
CB_CASE_KEYS = frozenset({'document', 'continuation', 'evaluation', 'given', 'expected'})
CB_CONTINUATION_KEYS = frozenset({'session', 'submission', 'end_at'})
CB_EVALUATION_KEYS = frozenset({'task_id', 'contract_text', 'declared', 'values', 'extra_records', 'recorder', 'now',
                                'commits'})
CB_EXPECTED = {'stop': ['STOP: violation'], 'decision': ['REJECT'], 'next_state': ['REJECTED'],
               'not_fixed': ['metrics']}
_TIME = re.compile(r'([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})Z')
_HEX40 = re.compile(r'[0-9a-f]{40}')
_PATTERN_NAME = re.compile(r'[A-Za-z0-9._*-]+')
_PATH_NAME = re.compile(r'[A-Za-z0-9._-]+')

_HEX64 = re.compile(r'[0-9a-f]{64}')
_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_TASK = re.compile(r'TASK-[0-9]+')
_VERSION = re.compile(r'v[0-9]+')
_GATE = re.compile(r'G[0-9]+')
_ROW = re.compile(r'^\| ((?:ACC|RISK|RC|ADV)-[0-9]+) \| ')
_SECTION = re.compile(r'^## [0-9]+\.? (.*)$')


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


def expected_path(scenario_id, capability):
    """The fixture path the runner expects for a set entry's capability (TASK-006 AC3; conformance-files.md section 9;
    TASK-017 AC2, section 10; TASK-056 AC2, section 11): the Verification folder for Verification, the Resume Check
    folder for Resume Check, the Risk Engine folder for Risk Engine, the Capability Boundaries folder for Capability
    Boundaries, None for any other capability (its entry point is absent until its milestone). The module name is
    formed as section 2 says."""
    name = scenario_id.lower().replace('-', '_') + '.py'
    if capability == VERIFICATION:
        return FIXTURE_DIR + '/' + name
    if capability == RESUME_CHECK:
        return RC_FIXTURE_DIR + '/' + name
    if capability == RISK_ENGINE:
        return RISK_FIXTURE_DIR + '/' + name
    if capability == CAPABILITY_BOUNDARIES:
        return CB_FIXTURE_DIR + '/' + name
    return None


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


def _cells(line):
    """The cells of a Markdown table line, stripped, without the empty parts outside its first and last bar."""
    parts = line.split('|')
    return [c.strip() for c in parts[1:-1]] if line.rstrip().endswith('|') else [c.strip() for c in parts[1:]]


def scenario_capabilities(data):
    """The capability the bound scenario file gives each id (TASK-006 AC2, a reading of conformance-files.md section
    9), read from the same row lines whose hashes the run takes: for a row of a table whose header line names a column
    Capability, the row's cell in that column; for any other row, the heading of the numbered section that holds it
    (a line beginning "## " and a number), its text after the number up to the first colon or the line end. A value
    that is not one of section 3's four capabilities, or an id on two rows, gives None."""
    if data is None:
        return {}
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return {}
    caps, seen = {}, set()
    section, header, previous_is_table = None, None, False
    for line in text.split('\n'):
        m = _SECTION.match(line)
        if m:
            section = m.group(1).split(':', 1)[0].strip()
            header, previous_is_table = None, False
            continue
        is_table = line.startswith('|')
        if is_table and not previous_is_table:
            header = _cells(line)
        if not is_table:
            header = None
        previous_is_table = is_table
        row = _ROW.match(line)
        if not row:
            continue
        sid = row.group(1)
        if sid in seen:
            caps[sid] = None
            continue
        seen.add(sid)
        if header is not None and 'Capability' in header:
            cells = _cells(line)
            k = header.index('Capability')
            value = cells[k] if k < len(cells) else None
        else:
            value = section
        caps[sid] = value if value in CAPABILITIES else None
    return caps


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


def _check_rc_inputs(inp):
    if not isinstance(inp, dict) or set(inp) != RC_INPUT_KEYS:
        return ['inputs is not exactly the keys of section 9']
    errors = []
    if not (isinstance(inp['task_id'], str) and _TASK.fullmatch(inp['task_id'])):
        errors.append('task_id')
    if inp['task_state'] not in RC_STATES:
        errors.append('task_state')
    if not isinstance(inp['contract'], dict):
        errors.append('contract')
    for key in ('contract_hash', 'approved_contract_hash'):
        if not _is_hex64(inp[key]):
            errors.append(key)
    if not (isinstance(inp['head_commit'], str) and _COMMIT.fullmatch(inp['head_commit'])):
        errors.append('head_commit')
    if not isinstance(inp['base_is_ancestor'], bool):
        errors.append('base_is_ancestor')
    return ['inputs ' + e for e in errors]


def check_rc_fixture(value, entry):
    """The form of one Resume Check fixture's JSON object against its set entry (TASK-006 AC5; conformance-files.md
    section 9). The runner checks the forms named here only; the other inputs are the Resume Check's to read (reading).
    Returns a list of errors."""
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
        if not isinstance(case, dict) or set(case) != RC_CASE_KEYS:
            errors.append(where + 'not exactly inputs, when and expected')
            continue
        if case['when'] != 'resume':
            errors.append(where + 'when is not resume')
        errors.extend(where + e for e in _check_rc_inputs(case['inputs']))
        exp = case['expected']
        if not (isinstance(exp, dict) and set(exp) == {'decision', 'not_fixed'}):
            errors.append(where + 'expected is not exactly decision and not_fixed')
            continue
        if not (isinstance(exp['decision'], list) and len(exp['decision']) == 1 and isinstance(exp['decision'][0], str)
                and exp['decision'][0] in EXECUTION):
            errors.append(where + 'expected decision is not a list of exactly one execution decision value')
        if exp['not_fixed'] != []:
            errors.append(where + 'expected not_fixed is not the empty list')
    return errors


def pattern_ok(pattern):
    """Whether a path pattern is well formed (TASK-017 AC5; risk rules section 2 point 6): names joined by "/", none
    empty, no leading or trailing "/", each name only ASCII letters, digits, ".", "_", "-" and "*", and "**" only as a
    whole name."""
    if not isinstance(pattern, str) or not pattern:
        return False
    for name in pattern.split('/'):
        if not _PATTERN_NAME.fullmatch(name) or ('**' in name and name != '**') or name in ('.', '..'):
            return False
    return True


def path_ok(path):
    """Whether a changed path is well formed (TASK-017 AC5): the pattern rule without "*". A name "." or ".." is ill
    formed in a path and in a pattern: Git records no such name (point 6 compares "the path as Git records it")."""
    return isinstance(path, str) and bool(path) and all(_PATH_NAME.fullmatch(n) and n not in ('.', '..')
                                                        for n in path.split('/'))


def path_matches(pattern, path):
    """The runner's own matcher (TASK-017 AC5; risk rules section 2 point 6), for well-formed patterns and paths only:
    "*" matches any part of one name and never crosses "/"; "**" as a whole name matches any sequence of names; a
    pattern without "/" matches a file name in any folder; case-sensitive."""
    if '/' not in pattern:
        pattern = '**/' + pattern
    parts, names = pattern.split('/'), path.split('/')
    memo = {}

    def step(i, j):
        if (i, j) not in memo:
            if i == len(parts):
                ok = j == len(names)
            elif parts[i] == '**' and i == len(parts) - 1:
                # A trailing "/**" matches every file at any depth below the folder, so at least one name.
                ok = j < len(names)
            elif parts[i] == '**':
                ok = any(step(i + 1, k) for k in range(j, len(names) + 1))
            else:
                one = re.escape(parts[i]).replace(r'\*', '[^/]*')
                ok = j < len(names) and re.fullmatch(one, names[j]) is not None and step(i + 1, j + 1)
            memo[(i, j)] = ok
        return memo[(i, j)]
    return step(0, 0)


def _patterns_ok(patterns):
    return isinstance(patterns, list) and bool(patterns) and all(pattern_ok(p) for p in patterns)


def _check_values(values):
    """The forms of a Risk Engine case's values that the runner reads, and the Given (TASK-017 AC4, AC5)."""
    if not isinstance(values, dict) or set(values) != RISK_VALUE_KEYS:
        return ['values is not exactly the keys of section 10']
    errors = []
    paths = values['changed_paths']
    if not (isinstance(paths, list) and paths and all(path_ok(p) for p in paths)):
        return ['changed_paths is not a non-empty list of well-formed paths']
    rules = values['risk_rules']
    if not (isinstance(rules, list) and all(isinstance(r, dict) and set(r) == {'match', 'class'}
                                            and _patterns_ok(r['match']) and r['class'] in RISKS for r in rules)):
        errors.append('risk_rules is not a list of {match, class} with well-formed patterns and a risk class')
    elif any(path_matches(p, path) for r in rules for p in r['match'] for path in paths):
        errors.append('the Given does not hold: a changed path matches a risk rule')
    arts = values['articles']
    if not (isinstance(arts, list) and all(isinstance(a, dict) and set(a) == {'id', 'scope', 'evidence_required'}
                                           and _patterns_ok(a['scope']) for a in arts)):
        errors.append('articles is not a list of {id, scope, evidence_required} with well-formed scopes')
    elif any(path_matches(p, path) for a in arts for p in a['scope'] for path in paths):
        errors.append('an article\'s scope matches a changed path')
    if values['requirement_profiles'] != []:
        errors.append('requirement_profiles is not the empty list')
    return errors


def _check_risk_expected(exp):
    if not isinstance(exp, dict) or set(exp) != RISK_EXPECTED_KEYS:
        return ['expected is not exactly risk_not, profile_excludes and not_fixed']
    errors = []
    if exp['risk_not'] != ['low']:
        errors.append('risk_not is not ["low"]')
    pairs = exp['profile_excludes']
    if not (isinstance(pairs, list) and len(pairs) == 2
            and all(isinstance(p, dict) and set(p) == {'dimension', 'evidence_type'} and _is_str(p['dimension'])
                    and _is_str(p['evidence_type']) for p in pairs)
            and {(p['dimension'], p['evidence_type']) for p in pairs} == LOW_PAIRS):
        errors.append('profile_excludes is not exactly the two pairs of the low default')
    nf = exp['not_fixed']
    if not (_is_str_list(nf) and len(nf) == 2 and set(nf) == {'decision', 'next_state'}):
        errors.append('not_fixed is not exactly decision and next_state')
    return errors


def check_risk_fixture(value, entry):
    """The form of one Risk Engine fixture's JSON object against its set entry (TASK-017 AC4, AC5;
    conformance-files.md section 10). Returns a list of errors."""
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
        if not isinstance(case, dict) or set(case) != RISK_CASE_KEYS:
            errors.append(where + 'not exactly values, request, records, when and expected')
            continue
        errors.extend(where + e for e in _check_values(case['values']))
        errors.extend(where + e for e in _check_request(case['request']))
        req, values = case['request'], case['values']
        if isinstance(req, dict) and isinstance(values, dict) and req.get('changed_paths') != values.get('changed_paths'):
            errors.append(where + 'request changed_paths differs from values changed_paths')
        if not (case['when'] == 'evaluate' and isinstance(req, dict) and req.get('task_state') == 'VERIFYING'):
            errors.append(where + 'when is not evaluate with task_state VERIFYING')
        case_records = case['records']
        if not isinstance(case_records, list):
            errors.append(where + 'records is not a list')
        else:
            seen = set()
            for rec in case_records:
                if records.check_record(rec):
                    errors.append(where + 'a record with a check_record finding')
                # A record id that is not a string is a check_record finding already; only strings are compared.
                rid = rec.get('record_id') if isinstance(rec, dict) else None
                if isinstance(rid, str):
                    if rid in seen:
                        errors.append(where + 'a repeated record id')
                    seen.add(rid)
        errors.extend(where + e for e in _check_risk_expected(case['expected']))
    return errors


PROFILE_USED_PROBLEM = ('the decision record has no profile_used list of objects with a string dimension and a list '
                        'of strings required')


def _profile_used_ok(entries):
    """Whether an acceptance return's profile_used is in the form step (3) reads (TASK-017 AC8; spec 2 section 6.4):
    a list of objects, each with a string dimension and a list of strings required. Any other form is not such a
    record, so the scenario is NOT_RUN unless another case fails; a malformed entry never counts as holding nothing."""
    return isinstance(entries, list) and all(isinstance(e, dict) and _is_str(e.get('dimension'))
                                             and _is_str_list(e.get('required')) for e in entries)


def _held(entries, key, pairs):
    """The pairs held by a list of profile entries: an entry holds a pair when its dimension equals the pair's and its
    ``key`` list holds the pair's type."""
    out = set()
    for e in entries:
        if isinstance(e, dict) and isinstance(e.get(key), list):
            out.update((e.get('dimension'), t) for t in e[key] if (e.get('dimension'), t) in pairs)
    return out


def derived_problem(derived, expected):
    """Why the derived inputs fail step (2) of section 10 (TASK-017 AC7), or '' when they pass."""
    if not isinstance(derived, dict) or 'risk' not in derived or 'evidence_profile' not in derived:
        return 'the derived inputs are not an object with risk and evidence_profile'
    risk, profile = derived['risk'], derived['evidence_profile']
    if risk is not None and risk not in RISKS:
        return 'the derived risk is not a risk class or null'
    if profile is not None and not (isinstance(profile, list) and all(
            isinstance(e, dict) and set(e) == {'dimension', 'evidence_types'} and _is_str(e['dimension'])
            and _is_str_list(e['evidence_types']) for e in profile)):
        return 'the derived evidence_profile is not a list of {dimension, evidence_types} or null'
    if risk in expected['risk_not']:
        return 'the derived risk is %s' % risk
    pairs = {(p['dimension'], p['evidence_type']) for p in expected['profile_excludes']}
    if isinstance(profile, list) and _held(profile, 'evidence_types', pairs):
        return 'the derived evidence_profile holds a pair of the low default'
    return ''


def load_derive(root):
    """The governor's derivation (TASK-017 AC3): derive_inputs of the one governor module the runner loads by
    load_governor's rules, or None when it is absent, failed to load or not callable."""
    try:
        import aieos_bootstrap.governor as governor
    except Exception:
        return None
    path = getattr(governor, '__file__', None)
    if not isinstance(path, str) or pathlib.Path(path).resolve() != (root / GOVERNOR_PATH).resolve():
        return None
    derive = getattr(governor, 'derive_inputs', None)
    return derive if callable(derive) else None


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


def load_resume_check(root):
    """The Resume Check entry point (TASK-006 AC4): (check, status), with the rules of load_governor. The module is
    loaded by a plain import statement. It is absent when the import raises ModuleNotFoundError naming it; it is the
    base's only when the loaded module's file is the root's src/aieos_bootstrap/resume_check.py (reading); any other
    failure, or no callable check, is FAILED."""
    try:
        import aieos_bootstrap.resume_check as resume_check
    except ModuleNotFoundError as exc:
        return None, (ABSENT if exc.name == RESUME_CHECK_MODULE else FAILED)
    except Exception:
        return None, FAILED
    path = getattr(resume_check, '__file__', None)
    if not isinstance(path, str) or pathlib.Path(path).resolve() != (root / RESUME_CHECK_PATH).resolve():
        return None, FAILED
    check = getattr(resume_check, 'check', None)
    if not callable(check):
        return None, FAILED
    return check, LOADED


def execution_problem(value):
    """Why a value returned by the Resume Check is not a usable execution decision record (TASK-006 AC6), or '' when
    it is one: not a JSON object, a finding under check_decision for decision.execution, or an error record (its
    decision then null)."""
    if not isinstance(value, dict):
        return 'the call returned no JSON object'
    if records.check_decision('decision.execution', value):
        return 'the call returned a value with a check_decision finding'
    if 'error' in value:
        return 'the call returned an error record'
    return ''


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


def run_scenario(tree, entry, rows, evaluate, caps=None, check=None, derive=None, cb=None, reads=None):
    """One scenario's result and its reason (AC5, AC7; TASK-006 AC3 to AC6; TASK-017 AC2 to AC9; TASK-056 AC2 to AC9):
    NOT_RUN, with none of its cases run, for a fixture condition; NOT_RUN for no entry point; otherwise each case is
    called and compared, and a failed case makes it FAIL before any NOT_RUN of a call. ``caps`` is the capability the
    bound scenario file gives each id (scenario_capabilities); ``evaluate`` is the Verification entry and the Risk
    Engine's acceptance function, ``check`` the Resume Check entry, ``derive`` the Risk Engine's derivation and ``cb``
    the Capability Boundaries entry (load_cb's mapping). ``reads``, when given, is a list to which the id is added
    when the fixture file is read."""
    sid, fixture = entry['id'], entry['fixture']
    if fixture is None:
        return NOT_RUN, 'no fixture'
    capability = entry['capability']
    want = expected_path(sid, capability)
    if want is None:
        return NOT_RUN, 'the entry point of %s is absent until its milestone' % capability
    if fixture['path'] != want:
        return NOT_RUN, 'the fixture path is not %s' % want
    # The row is checked before the file is read, so that only a path built from an id of the bound file is read.
    if rows.get(sid) is None or rows[sid] != entry['row_hash']:
        return NOT_RUN, 'the row hash differs from the bound scenario file'
    # TASK-006 AC3 (as read in decision D-287): the entry's capability against the bound file's, after the row hash
    # and before the file is read.
    if (caps or {}).get(sid) != capability:
        return NOT_RUN, 'the capability differs from the bound scenario file'
    data = tree.read(fixture['path'])
    if data is None:
        return NOT_RUN, 'the fixture file is missing'
    if reads is not None:
        reads.append(sid)
    if sha256(data) != fixture['sha256']:
        return NOT_RUN, 'the fixture\'s SHA-256 differs from its set entry'
    try:
        value = unwrap(data)
    except Malformed as exc:
        return NOT_RUN, 'the fixture is malformed: %s' % exc
    if capability == RESUME_CHECK:
        return _run_rc_cases(value, entry, check)
    if capability == RISK_ENGINE:
        return _run_risk_cases(value, entry, derive, evaluate)
    if capability == CAPABILITY_BOUNDARIES:
        return _run_cb_cases(value, entry, cb, tree.root)
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


def _run_rc_cases(value, entry, check):
    """The Resume Check cases of one well-formed fixture file (TASK-006 AC5, AC6): the form check, then each case is
    called with a copy of its inputs and the observed decision compared with expected.decision only; a failed case
    makes the scenario FAIL before any NOT_RUN of a call."""
    errors = check_rc_fixture(value, entry)
    if errors:
        return NOT_RUN, 'the fixture is malformed: %s' % errors[0]
    if check is None:
        return NOT_RUN, 'the entry point is absent'
    failed, not_run = [], ''
    for n, case in enumerate(value['cases'], 1):
        try:
            observed = check(copy.deepcopy(case['inputs']))
        except Exception as exc:
            observed, problem = None, 'case %d: the call raised %s' % (n, type(exc).__name__)
        else:
            problem = execution_problem(observed)
            if problem:
                problem = 'case %d: %s' % (n, problem)
        if problem:
            not_run = not_run or problem
        elif observed['decision'] not in case['expected']['decision']:
            failed.append('case %d: decision' % n)
    if failed:
        return FAIL, 'not met: ' + ', '.join(failed)
    if not_run:
        return NOT_RUN, not_run
    return PASS, ''


def _run_risk_cases(value, entry, derive, evaluate):
    """The Risk Engine cases of one well-formed fixture file (TASK-017 AC4 to AC9; conformance-files.md section 10):
    the form check and the Given; then per case (1) the derivation, (2) the derived inputs compared at once, (3) only
    when (2) passes, the acceptance call and its profile_used. Every case is run; a failed case makes the scenario
    FAIL before any NOT_RUN; the reason for a NOT_RUN is the scenario's reason in the runner's output."""
    errors = check_risk_fixture(value, entry)
    if errors:
        return NOT_RUN, 'the fixture is malformed: %s' % errors[0]
    if derive is None or evaluate is None:
        return NOT_RUN, 'the entry point is absent'
    failed, not_run = [], ''
    for n, case in enumerate(value['cases'], 1):
        try:
            derived = derive(copy.deepcopy(case['values']))
        except Exception as exc:
            not_run = not_run or 'case %d: the derivation raised %s: %s' % (n, type(exc).__name__, exc)
            continue
        problem = derived_problem(derived, case['expected'])
        if problem:
            failed.append('case %d: %s' % (n, problem))
            continue
        try:
            observed = evaluate(copy.deepcopy(case['request']), copy.deepcopy(derived), copy.deepcopy(case['records']))
        except Exception as exc:
            not_run = not_run or 'case %d: the call raised %s' % (n, type(exc).__name__)
            continue
        problem = decision_problem(observed)
        if not problem and not _profile_used_ok(observed.get('profile_used')):
            problem = PROFILE_USED_PROBLEM
        if problem:
            not_run = not_run or 'case %d: %s' % (n, problem)
            continue
        pairs = {(p['dimension'], p['evidence_type']) for p in case['expected']['profile_excludes']}
        if _held(observed['profile_used'], 'required', pairs):
            failed.append('case %d: profile_used holds a pair of the low default' % n)
    if failed:
        return FAIL, 'not met: ' + ', '.join(failed)
    if not_run:
        return NOT_RUN, not_run
    return PASS, ''


def _time_ok(value):
    """Whether a value is a time text "YYYY-MM-DDTHH:MM:SSZ" naming a real date and time (UTC, whole seconds)."""
    return _utc(value) is not None


def _utc(value):
    m = _TIME.fullmatch(value) if isinstance(value, str) else None
    if m is None:
        return None
    try:
        return datetime.datetime(*(int(g) for g in m.groups()), tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def _utf8(text):
    try:
        text.encode('utf-8')
    except UnicodeError:
        return False
    return True


def _commit_ok(c):
    return (isinstance(c, dict) and set(c) == {'id', 'text', 'paths'} and isinstance(c['id'], str)
            and _HEX40.fullmatch(c['id']) is not None and isinstance(c['text'], str) and _utf8(c['text'])
            and isinstance(c['paths'], list) and all(isinstance(p, str) for p in c['paths']))


def _check_cb_given(case):
    """The Given of section 11, from the fixture's values alone (TASK-056 AC4)."""
    doc, cont, ev, given = case['document'], case['continuation'], case['evaluation'], case['given']
    errors = []
    vio = doc.get('violation')
    obs = vio.get('observation') if isinstance(vio, dict) else None
    if not (isinstance(obs, dict) and obs.get('fact_kind') == 'observation' and obs.get('outcome') == 'blocking'
            and obs.get('blocking_kind') == 'violation' and obs.get('source_class') == 'deterministic_tool_local'
            and 'recorder' in doc and obs.get('recorder') == doc.get('recorder')):
        errors.append('the Given does not hold: the violation is not a blocking violation observation of class '
                      'deterministic_tool_local recorded by the document\'s recorder')
    outside, write_set = given['outside_path'], given['write_set']
    if not (path_ok(outside) and _patterns_ok(write_set)):
        errors.append('the Given does not hold: outside_path or write_set is not well formed')
    elif any(path_matches(p, outside) for p in write_set):
        errors.append('the Given does not hold: outside_path is matched by a pattern of write_set')
    sub = cont['submission']
    cid = sub.get('commit_id') if isinstance(sub, dict) else None
    commit = [c for c in ev['commits'] if c['id'] == cid]
    if len(commit) != 1:
        errors.append('the Given does not hold: the submitted commit is not exactly once in the commit table')
    else:
        if outside not in commit[0]['paths']:
            errors.append('the Given does not hold: outside_path is not among the submitted commit\'s paths')
        values = ev['values']
        if not (isinstance(values, dict) and values.get('changed_paths') == sorted(commit[0]['paths'])):
            errors.append('the Given does not hold: values changed_paths is not the submitted commit\'s paths, sorted')
    setup = doc.get('setup')
    approved = [e for e in setup if isinstance(e, dict) and e.get('type') == 'task.approved'] \
        if isinstance(setup, list) else []
    payload = approved[-1].get('payload') if approved else None
    if not (isinstance(payload, dict)
            and payload.get('contract_hash') == sha256(ev['contract_text'].encode('utf-8'))):
        errors.append('the Given does not hold: the contract text does not hash to the last task.approved '
                      'contract_hash')
    return errors


def check_cb_fixture(value, entry):
    """The form of one Capability Boundaries fixture's JSON object against its set entry, and the Given (TASK-056 AC4;
    conformance-files.md section 11). The replay document's other keys are replay.replay's to check (reading).
    Returns a list of errors."""
    if not isinstance(value, dict) or set(value) != {'scenario', 'row_hash', 'cases'}:
        return ['the fixture is not exactly scenario, row_hash and cases']
    errors = []
    if value['scenario'] != entry['id'] or value['row_hash'] != entry['row_hash']:
        errors.append('scenario or row_hash differs from the set entry')
    cases = value['cases']
    if not isinstance(cases, list) or len(cases) != 1:
        return errors + ['cases is not a list of exactly one case']
    case = cases[0]
    if not isinstance(case, dict) or set(case) != CB_CASE_KEYS:
        return errors + ['the case is not exactly document, continuation, evaluation, given and expected']
    doc = case['document']
    if not (isinstance(doc, dict) and 'violation' in doc and 'submission' in doc and doc['submission'] is None):
        errors.append('document is not an object holding violation and a null submission')
    cont = case['continuation']
    if not (isinstance(cont, dict) and set(cont) == CB_CONTINUATION_KEYS and isinstance(cont['session'], dict)
            and isinstance(cont['submission'], dict) and _time_ok(cont['end_at'])):
        errors.append('continuation is not exactly session, submission (not null) and end_at')
    ev = case['evaluation']
    if not (isinstance(ev, dict) and set(ev) == CB_EVALUATION_KEYS):
        errors.append('evaluation is not exactly the keys of section 11')
    else:
        if not (isinstance(ev['contract_text'], str) and _utf8(ev['contract_text'])):
            errors.append('evaluation contract_text is not a string that encodes as UTF-8')
        if not (isinstance(ev['commits'], list) and ev['commits'] and all(_commit_ok(c) for c in ev['commits'])):
            errors.append('evaluation commits is not a non-empty list of {id, text, paths}')
        if not _time_ok(ev['now']):
            errors.append('evaluation now is not a time "YYYY-MM-DDTHH:MM:SSZ"')
    given = case['given']
    if not (isinstance(given, dict) and set(given) == {'outside_path', 'write_set'}):
        errors.append('given is not exactly outside_path and write_set')
    exp = case['expected']
    if not (isinstance(exp, dict) and set(exp) == set(CB_EXPECTED)):
        errors.append('expected is not exactly stop, decision, next_state and not_fixed')
    else:
        for key, want in sorted(CB_EXPECTED.items()):
            if exp[key] != want:
                errors.append('expected %s is not %s' % (key, json.dumps(want)))
    if errors:
        return errors
    return _check_cb_given(case)


def load_cb(root):
    """The Capability Boundaries entry (TASK-056 AC3): (entry, status). The modules replay, adapter, evaluation, eventlog
    and writer are loaded by plain import statements, guarded as load_governor guards the governor's; each is the
    base's only when its file is the root's src/aieos_bootstrap/<name>.py (reading). It is absent when an import raises
    ModuleNotFoundError naming one of them; any other failure, or a missing callable, is FAILED. The entry is a mapping
    of the functions and values the run calls."""
    try:
        import aieos_bootstrap.replay as cb_replay
        import aieos_bootstrap.adapter as cb_adapter
        import aieos_bootstrap.evaluation as cb_evaluation
        import aieos_bootstrap.eventlog as cb_eventlog
        import aieos_bootstrap.writer as cb_writer
    except ModuleNotFoundError as exc:
        return None, (ABSENT if exc.name in ['aieos_bootstrap.' + m for m in CB_MODULES] else FAILED)
    except Exception:
        return None, FAILED
    modules = (('replay', cb_replay), ('adapter', cb_adapter), ('evaluation', cb_evaluation),
               ('eventlog', cb_eventlog), ('writer', cb_writer))
    for name, module in modules:
        path = getattr(module, '__file__', None)
        if not isinstance(path, str) or pathlib.Path(path).resolve() != (root / cb_path(name)).resolve():
            return None, FAILED
    entry = {'replay': getattr(cb_replay, 'replay', None), 'start': getattr(cb_adapter, 'start', None),
             'submit': getattr(cb_adapter, 'submit', None), 'end': getattr(cb_adapter, 'end', None),
             'evaluate_task': getattr(cb_evaluation, 'evaluate_task', None),
             'append': getattr(cb_eventlog, 'append', None), 'WriteResult': getattr(cb_writer, 'WriteResult', None),
             'StoreResult': getattr(cb_writer, 'StoreResult', None),
             'GRANT_STATES': getattr(cb_writer, 'GRANT_STATES', None),
             'DIFF_FORM': getattr(cb_evaluation, 'DIFF_FORM', None)}
    if not all(callable(entry[k]) for k in ('replay', 'start', 'submit', 'end', 'evaluate_task', 'append',
                                            'WriteResult', 'StoreResult')) \
            or not isinstance(entry['GRANT_STATES'], tuple) or not isinstance(entry['DIFF_FORM'], list):
        return None, FAILED
    return entry, LOADED


def cb_path(name):
    return 'src/aieos_bootstrap/%s.py' % name


def cb_core_root(root):
    """The root given to the core (TASK-056 AC5; decision D-1075 C3): an absolute path built from the absolute form of
    the run's root and a fixed name; nothing is created there."""
    return str(pathlib.Path(root).absolute() / CB_ROOT_NAME)


class _CbStore:
    """The writer's store in memory, by its rules (TASK-056 AC5): the epoch and counter, the leases and the sessions;
    every result is the writer's own StoreResult. It opens and writes no file."""

    def __init__(self, entry):
        self.entry = entry
        self.epoch = None
        self.counter = 0
        self.leases = {}
        self.sessions = {}

    def _r(self, *args, **kwargs):
        return self.entry['StoreResult'](*args, **kwargs)

    def open_store(self, root, epoch=None):
        if self.epoch is None:
            self.epoch = epoch
        elif epoch is not None and epoch != self.epoch:
            raise ValueError('the given epoch differs from the store\'s own epoch')
        return {'epoch': self.epoch, 'counter': self.counter}

    def start_session(self, root, session_id, holder, now):
        if session_id in self.sessions:
            return self._r('refused', 'started', ['started'])
        self.sessions[session_id] = [holder, None]
        return self._r('done')

    def end_session(self, root, session_id, now):
        s = self.sessions.get(session_id)
        if s is None or s[1] is not None:
            return self._r('refused', 'session', ['not started or ended'])
        s[1] = now
        return self._r('done', value=[])

    def grant_lease(self, root, task_id, task_state, holder, session_id, now, expires_at):
        if task_state not in self.entry['GRANT_STATES'] or task_id in self.leases:
            return self._r('refused', 'state', ['no grant'])
        s = self.sessions.get(session_id)
        if s is None or s[0] != holder or s[1] is not None:
            return self._r('refused', 'session', ['not a started session of the holder'])
        self.counter += 1
        self.leases[task_id] = {'task_id': task_id, 'fencing_token': {'epoch': self.epoch, 'counter': self.counter},
                                'expires_at': expires_at}
        return self._r('done', value=copy.deepcopy(self.leases[task_id]))

    def release_lease_token(self, root, task_id, fencing_token):
        lease = self.leases.get(task_id)
        if lease is None:
            return self._r('refused', 'none', ['no lease is held'])
        if lease['fencing_token'] != fencing_token:
            return self._r('refused', 'token', ['another token is held'])
        return self._r('done', value=self.leases.pop(task_id))

    def held_lease(self, root, task_id):
        lease = self.leases.get(task_id)
        return copy.deepcopy(lease) if lease else None


class _CbLog:
    """The event log as bytes in memory (TASK-056 AC5): every append is decided by eventlog.append over the log bytes,
    with the store's held lease for a fenced event, and a fence refusal's record appended as the writer appends it;
    every result is the writer's own WriteResult. It opens and writes no file."""

    def __init__(self, entry, store):
        self.entry = entry
        self.store = store
        self.log = b''

    def read_log(self, root):
        return self.log

    def append_event(self, root, event_type, payload, event_id, appended_at, recorder, task_id=None,
                     fencing_token=None, corrects=None):
        append, result = self.entry['append'], self.entry['WriteResult']
        lease = self.store.leases.get(task_id) if task_id else None
        r = append(self.log, event_type, payload, event_id, appended_at, task_id=task_id, fencing_token=fencing_token,
                   lease=lease, recorder=recorder, record_id='refusal-' + event_id, corrects=corrects)
        if r.result == 'appended':
            self.log += r.line
            return result(r)
        if r.result == 'refused' and r.reason == 'fence' and r.record is not None:
            rec = append(self.log, 'record.added', r.record, 'refusal-of-' + event_id, appended_at, task_id=task_id,
                         recorder=recorder)
            if rec.result == 'appended':
                self.log += rec.line
            return result(r, refusal=rec)
        return result(r)

    def functions(self):
        s = self.store
        return {'open_store': s.open_store, 'append_event': self.append_event, 'start_session': s.start_session,
                'end_session': s.end_session, 'read_log': self.read_log, 'grant_lease': s.grant_lease,
                'release_lease_token': s.release_lease_token, 'held_lease': s.held_lease}


def cb_commit_read(commits, diff_form):
    """The read stand-in (TASK-056 AC5): a function in gitread.run's form that answers only "cat-file -t" and
    "cat-file -p" of a commit of the table (its text) and the pinned diff-tree form followed by such a commit (its
    paths, NUL-separated), and gives an error result for every other read."""
    table = {c['id']: c for c in commits}

    def read(repo, args):
        args = list(args)
        c = table.get(args[-1]) if args else None
        if c is not None and args == ['cat-file', '-t', c['id']]:
            return {'exit': 0, 'out': b'commit\n', 'err': b'', 'error': None}
        if c is not None and args == ['cat-file', '-p', c['id']]:
            return {'exit': 0, 'out': c['text'].encode('utf-8'), 'err': b'', 'error': None}
        if c is not None and args == list(diff_form) + [c['id']]:
            return {'exit': 0, 'out': b''.join(p.encode('utf-8') + b'\0' for p in c['paths']), 'err': b'',
                    'error': None}
        return {'exit': None, 'out': b'', 'err': b'', 'error': 'the runner answers only the reads of its commit table'}
    return read


def _violation_step(result):
    steps = result.get('steps') if isinstance(result, dict) else None
    found = [s.get('result') for s in steps if isinstance(s, dict) and s.get('step') == 'violation'] \
        if isinstance(steps, list) else []
    return found[-1] if found and isinstance(found[-1], dict) else None


def _run_cb_case(case, cb, core_root):
    """Steps (1) to (3) of section 11 for one well-formed case (TASK-056 AC6 to AC9): (result, reason). A failure is
    FAIL whatever a later step does; no later step runs after a failure or a NOT_RUN; a call that raises is NOT_RUN
    with the raised error's type."""
    store = _CbStore(cb)
    log = _CbLog(cb, store)
    fns = log.functions()
    doc = case['document']
    # (1) The replay of the stopped session.
    try:
        r1 = cb['replay'](copy.deepcopy(doc), core_root, fns)
    except Exception as exc:
        return NOT_RUN, 'step 1: the call raised %s' % type(exc).__name__
    if not isinstance(r1, dict):
        return NOT_RUN, 'step 1: the replay returned no mapping'
    vstep = _violation_step(r1)
    if r1.get('result') == 'done':
        stop = vstep.get('decision') if vstep is not None else None
        if stop not in case['expected']['stop']:
            return FAIL, 'not met: step 1: the replay was done and its violation step\'s decision is %r' % (stop,)
    elif r1.get('result') == 'refused' and r1.get('reason') == 'violation':
        if vstep is None:
            return NOT_RUN, 'step 1: refused with reason violation and no violation step (no lease was granted)'
        if vstep.get('reason') == 'core':
            return FAIL, 'not met: step 1: the core refused the violation step (it did not stop the session)'
        return NOT_RUN, 'step 1: the violation step was refused with reason %r' % (vstep.get('reason'),)
    else:
        return NOT_RUN, 'step 1: the replay gave %r with reason %r' % (r1.get('result'), r1.get('reason'))
    # (2) The continuation: a second session on the same log submits the change.
    cont = case['continuation']
    s, sub = cont['session'], cont['submission']
    recorder = doc['recorder']
    read = cb_commit_read(case['evaluation']['commits'], cb['DIFF_FORM'])
    try:
        started = cb['start'](core_root, s.get('task_id'), s.get('session_id'), s.get('holder'),
                              copy.deepcopy(s.get('inputs')), s.get('code_sha256'), _utc(s.get('expires_at')),
                              recorder, _utc(s.get('start_at')), start_session=store.start_session,
                              read_log=log.read_log, append=log.append_event, grant=store.grant_lease,
                              release=store.release_lease_token, held=store.held_lease)
        token = started.get('fencing_token') if isinstance(started, dict) else None
        if not isinstance(started, dict) or started.get('result') != 'done' or token is None:
            return NOT_RUN, 'step 2: the second session got no lease'
        if token != s.get('expected_token'):
            return NOT_RUN, 'step 2: the granted token %r is not the expected %r' % (token, s.get('expected_token'))
        submitted = cb['submit'](core_root, core_root, sub.get('commit_id'), s.get('task_id'), sub.get('event_id'),
                                 recorder, _utc(sub.get('at')), read=read, append=log.append_event,
                                 release=store.release_lease_token, held=store.held_lease)
        if not isinstance(submitted, dict) or submitted.get('result') != 'done':
            return NOT_RUN, 'step 2: the submission was refused'
        ended = cb['end'](core_root, s.get('task_id'), s.get('session_id'), token, _utc(cont['end_at']),
                          release_lease_token=store.release_lease_token, end_session=store.end_session)
        if not isinstance(ended, dict) or ended.get('result') != 'done':
            return NOT_RUN, 'step 2: the end was refused'
    except Exception as exc:
        return NOT_RUN, 'step 2: a call raised %s' % type(exc).__name__
    # (3) The evaluation.
    ev = case['evaluation']
    try:
        r3 = cb['evaluate_task'](core_root, core_root, ev['task_id'], ev['contract_text'].encode('utf-8'),
                                 copy.deepcopy(ev['declared']), copy.deepcopy(ev['values']),
                                 copy.deepcopy(ev['extra_records']), ev['recorder'], _utc(ev['now']), read=read,
                                 read_log=log.read_log, append=log.append_event)
    except Exception as exc:
        return NOT_RUN, 'step 3: the call raised %s' % type(exc).__name__
    if not isinstance(r3, dict) or r3.get('result') != 'evaluated':
        return NOT_RUN, 'step 3: the evaluation gave %r with reason %r' % (
            r3.get('result') if isinstance(r3, dict) else None, r3.get('reason') if isinstance(r3, dict) else None)
    failed = []
    if r3.get('decision') not in case['expected']['decision']:
        failed.append('step 3: decision %r' % (r3.get('decision'),))
    if r3.get('next_task_state') not in case['expected']['next_state']:
        failed.append('step 3: next_state %r' % (r3.get('next_task_state'),))
    if failed:
        return FAIL, 'not met: ' + ', '.join(failed)
    return PASS, ''


def _run_cb_cases(value, entry, cb, root):
    """The Capability Boundaries case of one well-formed fixture file (TASK-056 AC4 to AC9; conformance-files.md section
    11): the form check and the Given; then, with the entry, steps (1) to (3) over one in-memory store and log."""
    errors = check_cb_fixture(value, entry)
    if errors:
        return NOT_RUN, 'the fixture is malformed: %s' % errors[0]
    if cb is None:
        return NOT_RUN, 'the entry point is absent'
    return _run_cb_case(value['cases'][0], cb, cb_core_root(root))


def outcome(counts, results, with_fixture):
    """The record's outcome (AC8): pass exactly when the run counts and every scenario with a fixture is PASS; a run
    with no scenario that has a fixture is fail (reading)."""
    return 'pass' if counts and with_fixture and all(results[i] == PASS for i in with_fixture) else 'fail'


def run(root, commit, task, read=None, listing=None, evaluate=None, check=None, derive=None, cb=None):
    """One conformance run over the tree at ``root``, the base (AC1). ``commit`` and ``task`` are only recorded.
    ``read`` and ``listing`` replace the default byte reader and records listing; ``evaluate`` is a test seam: a run
    with it never counts and its governor_identity is null (AC6). ``check`` is the Resume Check's test seam (TASK-006
    AC4, reading): a run with it never counts, and the run record's resume_check sha256 is null. ``derive`` is the
    Risk Engine derivation's test seam (TASK-017 AC3, reading): a run with it never counts. ``cb`` is the Capability
    Boundaries entry's test seam, a mapping in load_cb's form (TASK-056 AC3, reading): a run with it never counts, and
    the sha256 values of the run record's capability_boundaries are null. Raises ValueError for a commit or task id of
    the wrong form."""
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
    caps = scenario_capabilities(scenario_data)
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

    # TASK-006 AC4, AC7: the Resume Check entry is loaded, and the run record gains resume_check, only when at least
    # one Resume Check entry of the set file has a fixture.
    rc_used = set_value is not None and any(e['capability'] == RESUME_CHECK and e['fixture'] is not None
                                            for e in set_value['scenarios'])
    rc_status, rc_record = None, None
    if check is not None:
        rc_status = STAND_IN
        problems.append('a stand-in Resume Check (reading)')
    elif rc_used:
        check, rc_status = load_resume_check(root)
        if rc_status == LOADED and tree.read(RESUME_CHECK_PATH) is None:
            check, rc_status = None, FAILED
        if rc_status == FAILED:
            problems.append('the Resume Check could not be loaded from the root (reading)')
    if rc_used:
        rc_data = tree.read(RESUME_CHECK_PATH) if rc_status != STAND_IN else None
        rc_record = {'path': RESUME_CHECK_PATH, 'sha256': sha256(rc_data) if rc_data is not None else None}
    rc_entry = check if rc_status in (LOADED, STAND_IN) else None

    # TASK-017 AC3: the Risk Engine's derivation is the loaded governor module's derive_inputs, looked up only when at
    # least one Risk Engine entry of the set file has a fixture; a stand-in derivation never counts. No key is added
    # to the run record (conformance-files.md section 10).
    if derive is not None:
        problems.append('a stand-in derivation (reading)')
    elif set_value is not None and any(e['capability'] == RISK_ENGINE and e['fixture'] is not None
                                       for e in set_value['scenarios']) and status == LOADED:
        derive = load_derive(root)

    # TASK-056 AC3, AC10: the Capability Boundaries entry is loaded only when at least one Capability Boundaries entry
    # of the set file has a fixture; a stand-in entry never counts; a failed load does not count either, and its
    # scenarios are NOT_RUN for "the entry point is absent".
    cb_used = set_value is not None and any(e['capability'] == CAPABILITY_BOUNDARIES and e['fixture'] is not None
                                            for e in set_value['scenarios'])
    cb_status = None
    if cb is not None:
        cb_status = STAND_IN
        problems.append('a stand-in Capability Boundaries entry (reading)')
    elif cb_used:
        cb, cb_status = load_cb(root)
        if cb_status == FAILED:
            problems.append('the Capability Boundaries entry could not be loaded from the root (reading)')
    cb_entry = cb if cb_status in (LOADED, STAND_IN) else None

    entries = set_value['scenarios'] if set_value is not None else [{'id': i, 'fixture': None} for i in order]
    results, reasons, with_fixture, cb_reads = [], {}, [], []
    for entry in entries:
        if set_value is not None and entry['fixture'] is not None:
            with_fixture.append(entry['id'])
        if blocking:
            result, reason = NOT_RUN, 'the run does not count: %s' % blocking[0]
        elif entry['fixture'] is not None and entry['capability'] == RESUME_CHECK and rc_status == FAILED:
            result, reason = NOT_RUN, 'the run does not count: the Resume Check could not be loaded from the root (reading)'
        else:
            reads = cb_reads if entry.get('capability') == CAPABILITY_BOUNDARIES else None
            result, reason = run_scenario(tree, entry, rows, evaluate if status in (LOADED, STAND_IN) else None,
                                          caps, rc_entry, derive, cb_entry, reads)
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
    if rc_record is not None:
        value['resume_check'] = rc_record
    if cb_reads:
        recorded = []
        for name in CB_RECORDED:
            data = tree.read(cb_path(name)) if cb_status != STAND_IN else None
            recorded.append({'path': cb_path(name), 'sha256': sha256(data) if data is not None else None})
        value['capability_boundaries'] = recorded
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
