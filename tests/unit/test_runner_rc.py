"""Unit tests of the conformance runner's Resume Check entry (TASK-006, rules R1 to R6 of its AC13).

Every input is built in memory from the repository's own files and given to the runner through its byte reader and
records listing; no file is written. The frozen Resume Check fixtures under tests/conformance/fixtures_rc are read
only as bytes. Stand-in Resume Checks are test seams (AC4). Each test starts with the governor and the Resume Check
absent (finders on sys.meta_path), restored after the test, unless it installs a fake module; no importlib is used.
"""
import copy
import json
import pathlib
import sys
import types
import unittest

from aieos_bootstrap import conformance

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMIT = 'a' * 40
TASK = 'TASK-006'
FIRST, LAST = conformance.FIRST, conformance.LAST
RC_DIR = 'tests/conformance/fixtures_rc'
TEST_RECORDS = 'docs/records/TEST-6.jsonl'
RC_IDS = ['RC-%02d' % n for n in range(1, 12)]


def real_files():
    """The files a run reads, by path, as the repository holds them, with the Resume Check fixtures."""
    files = {}
    for path in (conformance.RUNNER_PATH, conformance.SET_FILE, conformance.SCENARIO_FILE):
        files[path] = (ROOT / path).read_bytes()
    for folder in (conformance.FIXTURE_DIR, RC_DIR):
        for p in sorted((ROOT / folder).glob('*.py')):
            files[folder + '/' + p.name] = p.read_bytes()
    for p in sorted((ROOT / conformance.RECORDS_DIR).glob('*.jsonl')):
        files[conformance.RECORDS_DIR + '/' + p.name] = p.read_bytes()
    return files


FIXED_SET_SHA256 = '158323324f2803bceee870403bc6c0e297c407fbe50902d60bec90624cc95208'


def fixed_files():
    """real_files() with the set file replaced by the fixed set value of TASK-013 (contract AC2): the tree's set value
    with every Resume Check entry's fixture null and fixture_set_version 1, written as the runner writes a set file.
    It is the set file at 1659a8cb, whose hash TASK-002's freeze record approves, so no freeze line is added; in the
    null state it equals real_files() byte for byte."""
    files = real_files()
    value = conformance.unwrap(files[conformance.SET_FILE])
    for entry in value['scenarios']:
        if entry['capability'] == 'Resume Check':
            entry['fixture'] = None
    value['fixture_set_version'] = 1
    files[conformance.SET_FILE] = FIRST + conformance.canonical_text(value) + LAST
    return files


def go(files, check=None, evaluate=None, commit=COMMIT, task=TASK, asked=None):
    """A run over an in-memory tree, through the runner's reader and listing; ``asked`` collects the paths read."""
    def read(path):
        if asked is not None:
            asked.append(path)
        return files.get(path)

    def listing():
        return sorted(p for p in files if p.startswith(conformance.RECORDS_DIR + '/') and p.endswith('.jsonl'))
    return conformance.run(ROOT, commit, task, read=read, listing=listing, evaluate=evaluate, check=check)


def wrap(value):
    return FIRST + conformance.canonical_text(value) + LAST


def freeze_line(digest):
    rec = {'approval_binding': {'hash': digest, 'kind': 'change_request'}, 'decision_ref': 'D-000',
           'fact_kind': 'authority', 'record_id': 'TEST-freeze-' + digest[:16], 'recorder': 'a unit test',
           'source_class': 'decision_agent', 'subject': 'TASK-005'}
    return (json.dumps(rec, sort_keys=True) + '\n').encode('utf-8')


def set_value(files):
    return conformance.unwrap(files[conformance.SET_FILE])


def put_set(files, value):
    """Writes a set value into the tree with a freeze approval for its new hash."""
    files[conformance.SET_FILE] = wrap(value)
    files[TEST_RECORDS] = files.get(TEST_RECORDS, b'') + freeze_line(conformance.sha256(files[conformance.SET_FILE]))


def rc_path(sid):
    return RC_DIR + '/' + sid.lower().replace('-', '_') + '.py'


def with_rc(files, ids=None):
    """The set file with the given Resume Check entries pointing at their frozen fixtures, frozen again."""
    value = set_value(files)
    for entry in value['scenarios']:
        if entry['id'] in (RC_IDS if ids is None else ids):
            entry['fixture'] = {'path': rc_path(entry['id']), 'sha256': conformance.sha256(files[rc_path(entry['id'])])}
    put_set(files, value)
    return files


def rc_value(files, sid):
    return conformance.unwrap(files[rc_path(sid)])


def put_rc(files, sid, value):
    """Replaces a Resume Check fixture's value, points its set entry at the new bytes and freezes the new set."""
    data = wrap(value)
    files[rc_path(sid)] = data
    sv = set_value(files)
    for entry in sv['scenarios']:
        if entry['id'] == sid:
            entry['fixture'] = {'path': rc_path(sid), 'sha256': conformance.sha256(data)}
    put_set(files, sv)


def record(decision, subject='TASK-1'):
    """An execution decision record with no check_decision finding."""
    return {'record_id': 'EXE-' + subject, 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_external_ci',
            'recorder': 'a stand-in Resume Check', 'subject': subject, 'decision': decision}


def stand_in(change=None):
    """A stand-in Resume Check that answers each case of the frozen fixtures from its own expected decision; ``change``
    may alter the answer: change(scenario id, answer) returns the new answer or raises."""
    by_inputs = {}
    for p in sorted((ROOT / RC_DIR).glob('*.py')):
        value = conformance.unwrap(p.read_bytes())
        for case in value['cases']:
            by_inputs[json.dumps(case['inputs'], sort_keys=True)] = (value['scenario'], case)

    def check(inputs):
        sid, case = by_inputs[json.dumps(inputs, sort_keys=True)]
        out = record(case['expected']['decision'][0], inputs['task_id'])
        return change(sid, out) if change else out
    return check


class Absent:
    """A meta-path finder that makes the governor and the Resume Check absent."""

    def find_spec(self, name, path=None, target=None):
        if name in (conformance.GOVERNOR_MODULE, conformance.RESUME_CHECK_MODULE):
            raise ModuleNotFoundError('No module named %r' % name, name=name)
        return None


class Failing:
    """A meta-path finder whose search for the Resume Check raises the given error."""

    def __init__(self, error):
        self.error = error

    def find_spec(self, name, path=None, target=None):
        if name == conformance.RESUME_CHECK_MODULE:
            raise self.error
        return None


class Watching:
    """A meta-path finder that notes every search for the Resume Check and finds nothing itself."""

    def __init__(self):
        self.asked = 0

    def find_spec(self, name, path=None, target=None):
        if name == conformance.RESUME_CHECK_MODULE:
            self.asked += 1
        return None


class Isolated(unittest.TestCase):
    """Restores sys.modules, sys.meta_path and the package's attributes after each test, and starts each test with
    the governor and the Resume Check absent."""

    def setUp(self):
        self._modules = dict(sys.modules)
        self._meta = list(sys.meta_path)
        package = sys.modules.get('aieos_bootstrap')
        saved = {n: getattr(package, n) for n in ('governor', 'resume_check') if hasattr(package, n)}
        for n in ('governor', 'resume_check'):
            sys.modules.pop('aieos_bootstrap.' + n, None)
            if hasattr(package, n):
                delattr(package, n)
        sys.meta_path.insert(0, Absent())

        def restore():
            sys.meta_path[:] = self._meta
            for name in list(sys.modules):
                if name not in self._modules:
                    del sys.modules[name]
            sys.modules.update(self._modules)
            for n in ('governor', 'resume_check'):
                if hasattr(package, n):
                    delattr(package, n)
            for n, v in saved.items():
                setattr(package, n, v)
        self.addCleanup(restore)

    def install(self, check=None, file=None):
        """A fake Resume Check module in sys.modules (no file is written)."""
        module = types.ModuleType(conformance.RESUME_CHECK_MODULE)
        module.__file__ = str(ROOT / conformance.RESUME_CHECK_PATH) if file is None else file
        if check is not None:
            module.check = check
        sys.modules[conformance.RESUME_CHECK_MODULE] = module
        return module


class R1CapabilityReading(Isolated):
    TEXT = '\n'.join([
        '# Scenarios', '| ACC-90 | before any heading |',
        '## 2. Verification: acceptance decisions', '', '| ID | Covers |', '|---|---|', '| ACC-91 | x |',
        '## 4. Resume Check', '', '| ID | Covers |', '|---|---|', '| RC-91 | x |',
        '## 7. Not a capability', '| ID | Covers |', '|---|---|', '| RC-92 | x |',
        '## 5. Adversarial cases', '| ID | Capability | Given |', '|---|---|---|',
        '| ADV-91 | Capability Boundaries | g |', '| ADV-92 | Verification | g |', '| ADV-93 | Other | g |',
        '| ADV-94 | Verification | g |', '| ADV-94 | Verification | g |', ''])

    def test_each_reading_rule(self):
        caps = conformance.scenario_capabilities(self.TEXT.encode('utf-8'))
        self.assertEqual(caps['ACC-91'], 'Verification')        # a section heading with a colon
        self.assertEqual(caps['RC-91'], 'Resume Check')         # a section heading without a colon
        self.assertEqual(caps['ADV-91'], 'Capability Boundaries')  # a Capability column
        self.assertEqual(caps['ADV-92'], 'Verification')
        self.assertIsNone(caps['ACC-90'])                       # no capability: no numbered section holds the row
        self.assertIsNone(caps['RC-92'])                        # an unknown heading
        self.assertIsNone(caps['ADV-93'])                       # an unknown cell
        self.assertIsNone(caps['ADV-94'])                       # an id on two rows

    def test_the_bound_file(self):
        caps = conformance.scenario_capabilities(real_files()[conformance.SCENARIO_FILE])
        order, _ = conformance.scenario_rows(real_files()[conformance.SCENARIO_FILE])
        self.assertEqual(sorted(caps), sorted(order))
        for sid in order:
            want = {'ACC': 'Verification', 'RISK': 'Risk Engine', 'RC': 'Resume Check'}.get(sid.split('-')[0])
            if want:
                self.assertEqual(caps[sid], want, sid)
        self.assertEqual((caps['ADV-01'], caps['ADV-02'], caps['ADV-03']),
                         ('Verification', 'Capability Boundaries', 'Verification'))

    def test_no_text(self):
        self.assertEqual(conformance.scenario_capabilities(None), {})
        self.assertEqual(conformance.scenario_capabilities(b'\xff\xfe'), {})


class R2EntryAndPath(Isolated):
    def result(self, files, sid, check=None):
        asked = []
        r = go(files, check=stand_in() if check is None else check, asked=asked)
        return r.results[sid], r.reasons[sid], asked

    def test_a_resume_check_fixture_in_its_folder_passes(self):
        result, reason, asked = self.result(with_rc(real_files(), ['RC-01']), 'RC-01')
        self.assertEqual((result, reason), (conformance.PASS, ''))
        self.assertIn(rc_path('RC-01'), asked)

    def test_a_capability_other_than_the_bound_files(self):
        files = real_files()
        value = set_value(files)
        entry = next(e for e in value['scenarios'] if e['id'] == 'RC-01')
        entry.update(capability='Verification', fixture={'path': conformance.module_path('RC-01'), 'sha256': '0' * 64})
        files[conformance.module_path('RC-01')] = files[rc_path('RC-01')]
        put_set(files, value)
        result, reason, asked = self.result(files, 'RC-01')
        self.assertEqual((result, reason), (conformance.NOT_RUN, 'the capability differs from the bound scenario file'))
        self.assertNotIn(conformance.module_path('RC-01'), asked)

    def test_no_capability_in_the_bound_file(self):
        files = with_rc(real_files(), ['RC-01'])
        data = files[conformance.SCENARIO_FILE].replace(b'\n## 4. Resume Check', b'\n## 4. Resumption')
        self.assertNotEqual(data, files[conformance.SCENARIO_FILE])
        files[conformance.SCENARIO_FILE] = data
        value = set_value(files)
        value['scenario_set_file_hash'] = conformance.sha256(data)
        put_set(files, value)
        result, reason, asked = self.result(files, 'RC-01')
        self.assertEqual((result, reason), (conformance.NOT_RUN, 'the capability differs from the bound scenario file'))
        self.assertNotIn(rc_path('RC-01'), asked)

    def test_a_verification_fixture_in_the_resume_check_folder(self):
        files = real_files()
        value = set_value(files)
        entry = next(e for e in value['scenarios'] if e['id'] == 'ACC-01')
        entry['fixture']['path'] = RC_DIR + '/acc_01.py'
        files[RC_DIR + '/acc_01.py'] = files[conformance.module_path('ACC-01')]
        put_set(files, value)
        result, reason, asked = self.result(files, 'ACC-01')
        self.assertEqual(result, conformance.NOT_RUN)
        self.assertEqual(reason, 'the fixture path is not ' + conformance.module_path('ACC-01'))
        self.assertNotIn(RC_DIR + '/acc_01.py', asked)

    def test_a_resume_check_fixture_in_the_verification_folder(self):
        files = real_files()
        value = set_value(files)
        entry = next(e for e in value['scenarios'] if e['id'] == 'RC-01')
        entry['fixture'] = {'path': conformance.module_path('RC-01'), 'sha256': conformance.sha256(files[rc_path('RC-01')])}
        files[conformance.module_path('RC-01')] = files[rc_path('RC-01')]
        put_set(files, value)
        result, reason, asked = self.result(files, 'RC-01')
        self.assertEqual((result, reason), (conformance.NOT_RUN, 'the fixture path is not ' + rc_path('RC-01')))
        self.assertNotIn(conformance.module_path('RC-01'), asked)

    def test_an_unrouted_capability(self):
        files = real_files()
        value = set_value(files)
        for sid, cap in (('RISK-01', 'Risk Engine'), ('ADV-02', 'Capability Boundaries')):
            entry = next(e for e in value['scenarios'] if e['id'] == sid)
            self.assertEqual(entry['capability'], cap)
            path = conformance.module_path(sid)
            entry['fixture'] = {'path': path, 'sha256': conformance.sha256(files[conformance.module_path('ACC-01')])}
            files[path] = files[conformance.module_path('ACC-01')]
        put_set(files, value)
        asked = []
        r = go(files, check=stand_in(), asked=asked)
        for sid, cap in (('RISK-01', 'Risk Engine'), ('ADV-02', 'Capability Boundaries')):
            self.assertEqual((r.results[sid], r.reasons[sid]),
                             (conformance.NOT_RUN, 'the entry point of %s is absent until its milestone' % cap))
            self.assertNotIn(conformance.module_path(sid), asked)

    def test_the_expected_path(self):
        self.assertEqual(conformance.expected_path('ACC-01', 'Verification'), conformance.module_path('ACC-01'))
        self.assertEqual(conformance.expected_path('RC-11', 'Resume Check'), RC_DIR + '/rc_11.py')
        self.assertIsNone(conformance.expected_path('RISK-01', 'Risk Engine'))
        self.assertIsNone(conformance.expected_path('ADV-02', 'Capability Boundaries'))


class R3EntryPoint(Isolated):
    def test_absent(self):
        r = go(with_rc(real_files()))
        for sid in RC_IDS:
            self.assertEqual((r.results[sid], r.reasons[sid]), (conformance.NOT_RUN, 'the entry point is absent'))
        self.assertEqual(r.problems, [])
        self.assertTrue(r.value['counts'])
        self.assertEqual(conformance.load_resume_check(ROOT), (None, conformance.ABSENT))

    def failed(self, r):
        self.assertFalse(r.value['counts'])
        self.assertIn('the Resume Check could not be loaded from the root (reading)', r.problems)
        for sid in RC_IDS:
            self.assertEqual(r.results[sid], conformance.NOT_RUN)
        self.assertEqual(r.results['ACC-01'], conformance.NOT_RUN)  # the governor is absent here
        self.assertEqual(r.reasons['ACC-01'], 'the entry point is absent')

    def test_a_failing_import(self):
        sys.meta_path.insert(0, Failing(ImportError('broken')))
        self.failed(go(with_rc(real_files())))
        sys.meta_path[0] = Failing(ModuleNotFoundError('No module named x', name='x'))
        self.assertEqual(conformance.load_resume_check(ROOT), (None, conformance.FAILED))

    def test_a_module_from_elsewhere(self):
        self.install(check=stand_in(), file=str(ROOT / 'elsewhere' / 'resume_check.py'))
        self.failed(go(with_rc(real_files())))

    def test_no_callable_check(self):
        module = self.install()
        module.check = 'not callable'
        self.failed(go(with_rc(real_files())))

    def test_a_loaded_module_whose_file_the_root_lacks(self):
        self.install(check=stand_in())
        self.failed(go(with_rc(real_files())))

    def test_a_loaded_module(self):
        self.install(check=stand_in())
        files = with_rc(real_files())
        files[conformance.RESUME_CHECK_PATH] = b'# the Resume Check at the root\n'
        r = go(files)
        self.assertEqual(r.problems, [])
        self.assertTrue(r.value['counts'])
        for sid in RC_IDS:
            self.assertEqual(r.results[sid], conformance.PASS)
        self.assertEqual(r.value['resume_check'], {'path': conformance.RESUME_CHECK_PATH,
                                                   'sha256': conformance.sha256(files[conformance.RESUME_CHECK_PATH])})

    def test_a_stand_in_never_counts(self):
        for files in (with_rc(real_files()), real_files()):
            r = go(files, check=stand_in())
            self.assertFalse(r.value['counts'])
            self.assertIn('a stand-in Resume Check (reading)', r.problems)
        self.assertEqual(go(with_rc(real_files()), check=stand_in()).value['resume_check']['sha256'], None)

    def test_no_load_when_no_resume_check_entry_has_a_fixture(self):
        watching = Watching()
        sys.meta_path.insert(0, watching)
        r = go(fixed_files())
        self.assertEqual(watching.asked, 0)
        self.assertNotIn(conformance.RESUME_CHECK_MODULE, sys.modules)
        self.assertNotIn('resume_check', r.value)
        go(with_rc(fixed_files(), ['RC-01']))
        self.assertEqual(watching.asked, 1)


class R4FixtureForm(Isolated):
    def malformed(self, change):
        files = with_rc(fixed_files(), ['RC-01'])
        value = copy.deepcopy(rc_value(files, 'RC-01'))
        change(value)
        put_rc(files, 'RC-01', value)
        calls = []

        def check(inputs):
            calls.append(inputs)
            return record('CONTINUE')
        r = go(files, check=check)
        return r.results['RC-01'], r.reasons['RC-01'], calls

    def test_the_frozen_fixtures_are_well_formed(self):
        files = real_files()
        value = set_value(files)
        for sid in RC_IDS:
            entry = next(e for e in value['scenarios'] if e['id'] == sid)
            self.assertEqual(conformance.check_rc_fixture(rc_value(files, sid), entry), [], sid)

    def test_each_malformed_condition(self):
        def inputs(key, v):
            return lambda f: f['cases'][0]['inputs'].__setitem__(key, v)

        def expected(v):
            return lambda f: f['cases'][0].__setitem__('expected', v)
        bad = {
            'an extra top key': lambda f: f.__setitem__('extra', 1),
            'another scenario': lambda f: f.__setitem__('scenario', 'RC-02'),
            'another row_hash': lambda f: f.__setitem__('row_hash', '0' * 64),
            'cases not a list': lambda f: f.__setitem__('cases', {}),
            'no case': lambda f: f.__setitem__('cases', []),
            'a case with an extra key': lambda f: f['cases'][0].__setitem__('records', []),
            'a case without when': lambda f: f['cases'][0].pop('when'),
            'when is not resume': lambda f: f['cases'][0].__setitem__('when', 'evaluate'),
            'inputs without a key': lambda f: f['cases'][0]['inputs'].pop('budget_use'),
            'inputs with an extra key': inputs('extra', 1),
            'a bad task_id': inputs('task_id', 'task-1'),
            'a bad task_state': inputs('task_state', 'VERIFYING'),
            'a contract that is not an object': inputs('contract', []),
            'a bad contract_hash': inputs('contract_hash', 'A' * 64),
            'a bad approved_contract_hash': inputs('approved_contract_hash', '0' * 63),
            'a bad head_commit': inputs('head_commit', 'b' * 39),
            'a base_is_ancestor that is not a boolean': inputs('base_is_ancestor', 1),
            'expected with an extra key': expected({'decision': ['CONTINUE'], 'not_fixed': [], 'next_state': ['READY']}),
            'expected without not_fixed': expected({'decision': ['CONTINUE']}),
            'two decisions': expected({'decision': ['CONTINUE', 'REPLAN'], 'not_fixed': []}),
            'no decision': expected({'decision': [], 'not_fixed': []}),
            'an acceptance value': expected({'decision': ['ACCEPT'], 'not_fixed': []}),
            'a decision that is not a list': expected({'decision': 'CONTINUE', 'not_fixed': []}),
            'a non-empty not_fixed': expected({'decision': ['CONTINUE'], 'not_fixed': ['decision']}),
        }
        for name, change in bad.items():
            with self.subTest(name):
                result, reason, calls = self.malformed(change)
                self.assertEqual(result, conformance.NOT_RUN)
                self.assertTrue(reason.startswith('the fixture is malformed: '), reason)
                self.assertEqual(calls, [])

    def test_a_wrapped_file_rule_comes_first(self):
        files = with_rc(real_files(), ['RC-01'])
        data = files[rc_path('RC-01')].replace(b'\n', b'\r\n', 1)
        files[rc_path('RC-01')] = data
        value = set_value(files)
        next(e for e in value['scenarios'] if e['id'] == 'RC-01')['fixture']['sha256'] = conformance.sha256(data)
        put_set(files, value)
        r = go(files, check=stand_in())
        self.assertTrue(r.reasons['RC-01'].startswith('the fixture is malformed: '), r.reasons['RC-01'])


class R5CallAndComparison(Isolated):
    def run_rc(self, check, files=None):
        r = go(with_rc(real_files(), ['RC-01']) if files is None else files, check=check)
        return r.results['RC-01'], r.reasons['RC-01']

    def test_a_decision_in_the_list_passes(self):
        self.assertEqual(self.run_rc(stand_in()), (conformance.PASS, ''))

    def test_a_decision_outside_the_list_fails(self):
        def other(sid, out):
            out['decision'] = 'ESCALATE' if out['decision'] != 'ESCALATE' else 'CONTINUE'
            return out
        self.assertEqual(self.run_rc(stand_in(other)), (conformance.FAIL, 'not met: case 1: decision'))

    def test_the_comparison_is_on_the_value_only(self):
        def worded(sid, out):
            out['recorder'] = 'any wording at all'
            return out
        self.assertEqual(self.run_rc(stand_in(worded)), (conformance.PASS, ''))

    def test_each_not_run_rule(self):
        def raises(inputs):
            raise RuntimeError('no')

        def changed(update):
            def check(inputs):
                out = stand_in()(inputs)
                out.update(update)
                return out
            return check
        cases = {
            'the call raised RuntimeError': raises,
            'the call returned no JSON object': lambda inputs: 'CONTINUE',
            'the call returned a value with a check_decision finding': changed({'decision': 'ACCEPT'}),
            'a key that check_decision does not know': changed({'next_task_state': 'DONE'}),
            'the call returned an error record': changed({'decision': None, 'error': 'the log could not be read'}),
        }
        for name, check in cases.items():
            with self.subTest(name):
                result, reason = self.run_rc(check)
                self.assertEqual(result, conformance.NOT_RUN)
                self.assertTrue(reason.startswith('case 1: the call '), reason)
        self.assertEqual(self.run_rc(cases['a key that check_decision does not know'])[1],
                         'case 1: the call returned a value with a check_decision finding')

    def test_fail_comes_before_not_run(self):
        files = with_rc(real_files(), ['RC-01'])
        value = copy.deepcopy(rc_value(files, 'RC-01'))
        second = copy.deepcopy(value['cases'][0])
        second['inputs']['task_id'] = 'TASK-2'
        value['cases'].append(second)
        put_rc(files, 'RC-01', value)
        want = value['cases'][0]['expected']['decision'][0]

        def check(inputs):
            if inputs['task_id'] != 'TASK-2':
                raise RuntimeError('first case')
            return record('ESCALATE' if want != 'ESCALATE' else 'CONTINUE', 'TASK-2')
        self.assertEqual(self.run_rc(check, files), (conformance.FAIL, 'not met: case 2: decision'))

    def test_the_call_gets_a_copy_of_the_inputs(self):
        files = with_rc(fixed_files(), ['RC-01'])
        before = rc_value(files, 'RC-01')['cases'][0]['inputs']
        seen = []

        def check(inputs):
            seen.append(inputs == before)
            inputs.clear()
            return record(rc_value(files, 'RC-01')['cases'][0]['expected']['decision'][0])
        self.assertEqual(self.run_rc(check, files), (conformance.PASS, ''))
        self.assertEqual(seen, [True])


class R6RunRecord(Isolated):
    def test_the_key_is_absent_without_a_resume_check_fixture(self):
        r = go(fixed_files())
        self.assertEqual(set(r.value), {'set_file_sha256', 'scenario_set_version', 'fixture_set_version', 'runner',
                                        'governor_identity', 'commit', 'counts', 'results'})

    def test_the_key_is_present_with_one(self):
        r = go(with_rc(real_files(), ['RC-01']))
        self.assertEqual(r.value['resume_check'], {'path': conformance.RESUME_CHECK_PATH, 'sha256': None})
        self.assertEqual(conformance.unwrap(FIRST + r.text + LAST), r.value)

    def test_the_outcome_with_a_resume_check_scenario(self):
        self.install(check=stand_in())
        files = with_rc(real_files(), ['RC-01'])
        files[conformance.RESUME_CHECK_PATH] = b'# the Resume Check at the root\n'
        value = set_value(files)
        for entry in value['scenarios']:
            if entry['capability'] == 'Verification':
                entry['fixture'] = None
        put_set(files, value)
        r = go(files)
        self.assertEqual((r.results['RC-01'], r.value['counts'], r.record['outcome']), (conformance.PASS, True, 'pass'))
        sys.modules.pop(conformance.RESUME_CHECK_MODULE)
        r = go(files)
        self.assertEqual((r.results['RC-01'], r.record['outcome']), (conformance.NOT_RUN, 'fail'))


class FixedSetValue(unittest.TestCase):
    """The fixed set value of TASK-013 (contract AC2): the set file at 1659a8cb, approved by TASK-002's freeze record.
    Limits (contract AC9): until TASK-014 lands, the present state is run only by a scratch simulation; if TASK-014
    changes the set file beyond the eleven Resume Check fixtures and fixture_set_version, this pin fails on purpose
    (fail closed), and TASK-014 must bring it."""

    def test_the_fixed_value_is_the_frozen_set_file(self):
        data = fixed_files()[conformance.SET_FILE]
        self.assertEqual(conformance.sha256(data), FIXED_SET_SHA256)
        self.assertEqual(conformance.freeze_approval(conformance._Tree(ROOT), FIXED_SET_SHA256), (True, ''))
        value = conformance.unwrap(data)
        self.assertEqual([e['fixture'] for e in value['scenarios'] if e['capability'] == 'Resume Check'], [None] * 11)
        self.assertEqual(value['fixture_set_version'], 1)


if __name__ == '__main__':
    unittest.main()
