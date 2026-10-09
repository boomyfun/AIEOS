"""Unit tests of the conformance runner of TASK-003 (AC1 to AC9, rules R1 to R9 of AC12).

Every malformed input is built in memory from the repository's own files and given to the runner through its byte
reader and records listing (AC1); no file is written. Stand-in governors are test seams (AC6). The governor's loading
cases use sys.modules and sys.meta_path, restored after each test; no governor file and no importlib are used.
"""
import contextlib
import copy
import io
import json
import pathlib
import sys
import types
import unittest

from aieos_bootstrap import conformance
from aieos_bootstrap.records import check_record

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMIT = 'a' * 40
TASK = 'TASK-003'
FIRST, LAST = conformance.FIRST, conformance.LAST
TEST_RECORDS = 'docs/records/TEST-9.jsonl'


def real_files():
    """The files a run reads, by path, as the repository holds them."""
    files = {}
    for path in (conformance.RUNNER_PATH, conformance.SET_FILE, conformance.SCENARIO_FILE):
        files[path] = (ROOT / path).read_bytes()
    for p in sorted((ROOT / conformance.FIXTURE_DIR).glob('*.py')):
        files[conformance.FIXTURE_DIR + '/' + p.name] = p.read_bytes()
    for p in sorted((ROOT / conformance.RECORDS_DIR).glob('*.jsonl')):
        files[conformance.RECORDS_DIR + '/' + p.name] = p.read_bytes()
    return files


def go(files, evaluate=None, root=ROOT, commit=COMMIT, task=TASK):
    """A run over an in-memory tree, through the runner's reader and listing."""
    def read(path):
        return files.get(path)

    def listing():
        return sorted(p for p in files if p.startswith(conformance.RECORDS_DIR + '/') and p.endswith('.jsonl'))
    return conformance.run(root, commit, task, read=read, listing=listing, evaluate=evaluate)


def wrap(value):
    return FIRST + conformance.canonical_text(value) + LAST


def freeze_line(digest, source_class='decision_agent', kind='change_request'):
    rec = {'approval_binding': {'hash': digest, 'kind': kind}, 'decision_ref': 'D-000', 'fact_kind': 'authority',
           'record_id': 'TEST-freeze-' + digest[:12] + '-' + source_class + '-' + kind, 'recorder': 'a unit test',
           'source_class': source_class, 'subject': 'TASK-002'}
    return (json.dumps(rec, sort_keys=True) + '\n').encode('utf-8')


def set_value(files):
    return conformance.unwrap(files[conformance.SET_FILE])


def put_set(files, value, freeze=True):
    """Writes a set value into the tree and, if asked, a freeze approval for its new hash."""
    files[conformance.SET_FILE] = wrap(value)
    if freeze:
        files[TEST_RECORDS] = files.get(TEST_RECORDS, b'') + freeze_line(conformance.sha256(files[conformance.SET_FILE]))


def put_fixture(files, sid, data):
    """Replaces a fixture's bytes, points its set entry at the new hash and freezes the new set."""
    path = conformance.module_path(sid)
    files[path] = data
    value = set_value(files)
    for entry in value['scenarios']:
        if entry['id'] == sid:
            entry['fixture']['sha256'] = conformance.sha256(data)
    put_set(files, value)


def fixture(files, sid):
    return conformance.unwrap(files[conformance.module_path(sid)])


def only(key, value):
    """An expected value that fixes one key and names the other five in not_fixed."""
    return {key: value, 'not_fixed': [k for k in conformance.EXPECTED_KEYS if k != key]}


def answer(request, inputs, case_records, expected):
    """A decision record that meets every fixed key of ``expected``."""
    nf = set(expected['not_fixed'])
    by_dim = {}
    for m in ([] if 'missing' in nf else expected['missing']):
        by_dim.setdefault(m['dimension'], []).append(m['evidence_type'])
    approval = None if 'approval' in nf or expected['approval'] is None else expected['approval']['record_id']
    return {
        'record_id': 'DEC-' + request['task_id'], 'fact_kind': 'interpretation',
        'source_class': 'deterministic_tool_external_ci', 'recorder': 'a stand-in governor',
        'subject': request['task_id'], 'task_content_hash': request['task_content_hash'],
        'evaluated_commit': request['evaluated_commit'],
        'decision': 'NEEDS_REVIEW' if 'decision' in nf else expected['decision'][0],
        'next_task_state': 'IN_REVIEW' if 'next_state' in nf else expected['next_state'][0],
        'profile_used': [{'dimension': d, 'required': t, 'satisfied_by': [], 'missing_types': t} for d, t in by_dim.items()],
        'reverify': [] if 'reverify' in nf else list(expected['reverify']),
        'approval_record': approval,
        'rests_on_ai': {'entries': [], 'approval': False if 'ai_approval_shown' in nf else expected['ai_approval_shown']},
    }


def stand_in(files=None, change=None):
    """A stand-in governor that answers each case of the repository's own fixtures from its own expected values
    (``files`` is not read, so the answers stay those of the frozen fixtures whatever a test changes); ``change`` may
    alter the answer: change(scenario id, case number, answer) returns the new answer or raises."""
    by_request = {}
    for path, data in real_files().items():
        if path.startswith(conformance.FIXTURE_DIR + '/'):
            value = conformance.unwrap(data)
            for n, case in enumerate(value['cases'], 1):
                by_request[json.dumps(case['request'], sort_keys=True)] = (value['scenario'], n, case)

    def evaluate(request, inputs, case_records):
        sid, n, case = by_request[json.dumps(request, sort_keys=True)]
        out = answer(request, inputs, case_records, case['expected'])
        return change(sid, n, out) if change else out
    return evaluate


class RestoreImports(unittest.TestCase):
    """Restores sys.modules and sys.meta_path after each test."""

    def setUp(self):
        self._modules = dict(sys.modules)
        self._meta = list(sys.meta_path)
        self.addCleanup(self._restore)

    def _restore(self):
        sys.meta_path[:] = self._meta
        for name in list(sys.modules):
            if name not in self._modules:
                del sys.modules[name]
        sys.modules.update(self._modules)
        package = sys.modules.get('aieos_bootstrap')
        if package is not None and 'aieos_bootstrap.governor' not in self._modules and hasattr(package, 'governor'):
            delattr(package, 'governor')


def fake_governor(evaluate=None, file=None):
    module = types.ModuleType(conformance.GOVERNOR_MODULE)
    module.__file__ = str(ROOT / conformance.GOVERNOR_PATH) if file is None else file
    if evaluate is not None:
        module.evaluate = evaluate
    return module


class Failing:
    """A meta-path finder whose search for the governor raises the given error."""

    def __init__(self, error):
        self.error = error

    def find_spec(self, name, path=None, target=None):
        if name == conformance.GOVERNOR_MODULE:
            raise self.error
        return None


class R1ReaderAndRoot(unittest.TestCase):
    def test_inputs_come_only_through_the_reader(self):
        files = real_files()
        r = go(files)
        self.assertTrue(r.value['counts'])
        self.assertEqual(r.text, conformance.run(ROOT, COMMIT, TASK).text)
        del files[conformance.SET_FILE]
        self.assertFalse(go(files).value['counts'])

    def test_the_running_runner_must_be_the_roots(self):
        files = real_files()
        self.assertEqual(go(files).problems, [])
        files[conformance.RUNNER_PATH] = files[conformance.RUNNER_PATH] + b'# another runner\n'
        r = go(files)
        self.assertFalse(r.value['counts'])
        self.assertIn('the running runner is not the root\'s (reading)', r.problems)
        self.assertEqual(set(r.results.values()), {conformance.NOT_RUN})

    def test_the_commit_and_task_are_only_recorded(self):
        files = real_files()
        a, b = go(files, commit='b' * 40), go(files, commit='c' * 40, task='TASK-77')
        self.assertEqual(a.value['results'], b.value['results'])
        self.assertEqual((b.value['commit'], b.record['commit'], b.record['subject']), ('c' * 40, 'c' * 40, 'TASK-77'))
        for commit, task in (('B' * 40, TASK), ('a' * 39, TASK), (COMMIT, 'task-3'), (COMMIT, '')):
            with self.assertRaises(ValueError):
                go(files, commit=commit, task=task)


class R2CanonicalForm(unittest.TestCase):
    def test_a_wrapped_canonical_file_is_read(self):
        value = {'b': [1, 'x', None, True], 'a': {}, 'c': [], 'd': 'quote " backslash \\ tab \t'}
        self.assertEqual(conformance.unwrap(wrap(value)), value)
        self.assertEqual(conformance.unwrap(wrap({'é': 'ü'})), {'é': 'ü'})

    def test_each_rule_has_its_failing_case(self):
        good = wrap({'a': [1, 'x'], 'b': {}})
        text = good[len(FIRST):len(good) - len(LAST)]
        bad = {
            'no first part': text + LAST,
            'no last part': FIRST + text,
            'no final LF of the module': good[:-1],
            'a comment before the first part': b'# x\n' + good,
            'three quotes inside': FIRST + text.replace(b'"x"', b"\"'''\"") + LAST,
            'a CR byte': good.replace(b'\n', b'\r\n', 1),
            'a byte-order mark': FIRST + b'\xef\xbb\xbf' + text + LAST,
            'not UTF-8': FIRST + b'{\n  "a": "\xff"\n}\n' + LAST,
            'keys out of order': FIRST + b'{\n  "b": {},\n  "a": [\n    1,\n    "x"\n  ]\n}\n' + LAST,
            'an indent of four': FIRST + b'{\n    "a": 1\n}\n' + LAST,
            'a fraction': FIRST + b'{\n  "a": 1.5\n}\n' + LAST,
            'an exponent': FIRST + b'{\n  "a": 1e3\n}\n' + LAST,
            'a duplicate key': FIRST + b'{\n  "a": 1,\n  "a": 1\n}\n' + LAST,
            'NaN': FIRST + b'{\n  "a": NaN\n}\n' + LAST,
            'an escaped slash': FIRST + b'{\n  "a": "\\/"\n}\n' + LAST,
            'an uppercase hex escape': FIRST + b'{\n  "a": "\\u001F"\n}\n' + LAST,
            'a raw control character': FIRST + b'{\n  "a": "\x01"\n}\n' + LAST,
            'an empty list on two lines': FIRST + b'{\n  "a": [\n  ]\n}\n' + LAST,
            'no final LF of the JSON text': FIRST + b'{\n  "a": 1\n}' + LAST,
            'a doubled final LF': FIRST + b'{\n  "a": 1\n}\n\n' + LAST,
            'trailing space': FIRST + b'{\n  "a": 1 \n}\n' + LAST,
            'not JSON': FIRST + b'DATA\n' + LAST,
        }
        for name, data in bad.items():
            with self.subTest(name):
                with self.assertRaises(conformance.Malformed):
                    conformance.unwrap(data)

    def test_the_run_record_is_canonical(self):
        r = go(real_files())
        self.assertEqual(conformance.unwrap(FIRST + r.text + LAST), r.value)
        with self.assertRaises(conformance.Malformed):
            conformance.canonical_text({'a': 1.5})


class R3DoesNotCount(unittest.TestCase):
    def test_the_real_set_counts(self):
        r = go(real_files())
        self.assertTrue(r.value['counts'])
        self.assertEqual(r.problems, [])

    def assert_blocked(self, files, problem):
        r = go(files)
        self.assertFalse(r.value['counts'])
        self.assertTrue(r.problems and r.problems[0].startswith(problem), r.problems)
        self.assertEqual(set(r.results.values()), {conformance.NOT_RUN})
        return r

    def test_a_missing_set_file(self):
        files = real_files()
        del files[conformance.SET_FILE]
        r = self.assert_blocked(files, 'the set file is missing')
        order, _ = conformance.scenario_rows(files[conformance.SCENARIO_FILE])
        self.assertEqual([x['id'] for x in r.value['results']], order)
        self.assertEqual((r.value['set_file_sha256'], r.value['scenario_set_version']), (None, None))

    def test_a_set_file_not_wrapped(self):
        files = real_files()
        files[conformance.SET_FILE] = b'DATA = 1\n'
        self.assert_blocked(files, 'the set file is malformed')

    def test_set_forms(self):
        cases = {
            'a fifth key': lambda v: v.update(extra=1),
            'a version that is no integer': lambda v: v.update(scenario_set_version='2'),
            'a boolean version': lambda v: v.update(fixture_set_version=True),
            'a hash of the wrong form': lambda v: v.update(scenario_set_file_hash='A' * 64),
            'no scenarios': lambda v: v.update(scenarios=[]),
            'an entry with a fifth key': lambda v: v['scenarios'][0].update(extra=1),
            'a capability outside section 3': lambda v: v['scenarios'][0].update(capability='Other'),
            'a fixture of the wrong form': lambda v: v['scenarios'][0].update(fixture={'path': 'x'}),
            'an id twice': lambda v: v['scenarios'][1].update(id=v['scenarios'][0]['id']),
        }
        for name, change in cases.items():
            with self.subTest(name):
                files = real_files()
                value = set_value(files)
                change(value)
                put_set(files, value)
                self.assert_blocked(files, 'the set file is malformed')

    def test_a_scenario_set_file_hash_that_differs(self):
        files = real_files()
        value = set_value(files)
        value['scenario_set_file_hash'] = '0' * 64
        put_set(files, value)
        self.assert_blocked(files, 'scenario_set_file_hash differs')

    def test_a_missing_or_changed_scenario_file(self):
        # The bound file itself is absent or differs, not the set's hash (way-2 review R5, finding 1).
        for name in ('missing', 'changed'):
            with self.subTest(name):
                files = real_files()
                if name == 'missing':
                    del files[conformance.SCENARIO_FILE]
                else:
                    files[conformance.SCENARIO_FILE] += b'\n'
                self.assert_blocked(files, 'scenario_set_file_hash differs')

    def test_a_set_without_its_freeze_approval(self):
        files = real_files()
        value = set_value(files)
        value['fixture_set_version'] = 2
        put_set(files, value, freeze=False)
        self.assert_blocked(files, 'no freeze approval binds')

    def test_a_stand_in_never_counts_but_its_results_are_computed(self):
        files = real_files()
        r = go(files, evaluate=stand_in(files))
        self.assertFalse(r.value['counts'])
        self.assertEqual(r.problems, ['a stand-in governor (reading)'])
        self.assertIsNone(r.value['governor_identity'])
        self.assertEqual(list(r.results.values()).count(conformance.PASS), 19)
        self.assertEqual(r.record['outcome'], 'fail')


class R4FreezeApproval(unittest.TestCase):
    def without_the_set_freeze(self):
        files = real_files()
        path = conformance.RECORDS_DIR + '/TASK-002.jsonl'
        files[path] = b''.join(ln + b'\n' for ln in files[path].split(b'\n') if ln and b'TASK-002-freeze-set' not in ln)
        return files

    def test_the_real_approval_and_two_approvals_of_one_hash(self):
        files = real_files()
        self.assertEqual(conformance.freeze_approval(conformance._Tree(ROOT), conformance.sha256(files[conformance.SET_FILE])), (True, ''))
        files[TEST_RECORDS] = freeze_line(conformance.sha256(files[conformance.SET_FILE]), 'human_authority')
        self.assertTrue(go(files).value['counts'])

    def test_a_human_authority_approval_counts(self):
        files = self.without_the_set_freeze()
        self.assertFalse(go(files).value['counts'])
        files[TEST_RECORDS] = freeze_line(conformance.sha256(files[conformance.SET_FILE]), 'human_authority')
        self.assertTrue(go(files).value['counts'])

    def test_failing_cases(self):
        digest = conformance.sha256(real_files()[conformance.SET_FILE])
        cases = {
            'no records file': None,
            'another hash only': freeze_line('0' * 64),
            'a wrong kind': freeze_line(digest, kind='acceptance'),
            'an agent_declared source': freeze_line(digest, 'agent_declared'),
            'a same_lineage_review source': freeze_line(digest, 'same_lineage_review'),
            'a malformed line': freeze_line(digest) + b'not json\n',
            'a line with a check_record finding': freeze_line(digest) + b'{"record_id": "x"}\n',
            'a CR byte': freeze_line(digest).replace(b'\n', b'\r\n'),
            'a byte-order mark': b'\xef\xbb\xbf' + freeze_line(digest),
            'not UTF-8': freeze_line(digest) + b'\xff\n',
        }
        for name, data in cases.items():
            with self.subTest(name):
                files = self.without_the_set_freeze()
                if data is None:
                    for path in [p for p in files if p.startswith(conformance.RECORDS_DIR + '/')]:
                        del files[path]
                else:
                    files[TEST_RECORDS] = data
                r = go(files)
                self.assertFalse(r.value['counts'])
                self.assertEqual(set(r.results.values()), {conformance.NOT_RUN})

    def test_an_unreadable_listed_file(self):
        files = real_files()
        r = conformance.run(ROOT, COMMIT, TASK, read=files.get,
                            listing=lambda: [conformance.RECORDS_DIR + '/TASK-002.jsonl', TEST_RECORDS])
        self.assertIn('the records file %s is unreadable' % TEST_RECORDS, r.problems)


class R5FixtureConditions(unittest.TestCase):
    def result(self, files, sid, evaluate=None):
        r = go(files, evaluate=evaluate or stand_in(real_files()))
        return r.results[sid], r.reasons[sid], r

    def test_a_well_formed_fixture_is_run(self):
        result, reason, r = self.result(real_files(), 'ACC-01')
        self.assertEqual((result, reason), (conformance.PASS, ''))

    def test_conditions_on_the_entry(self):
        def no_fixture(v):
            v['scenarios'][0]['fixture'] = None

        def wrong_path(v):
            v['scenarios'][0]['fixture']['path'] = conformance.FIXTURE_DIR + '/other.py'

        def wrong_hash(v):
            v['scenarios'][0]['fixture']['sha256'] = '0' * 64

        def wrong_row(v):
            v['scenarios'][0]['row_hash'] = '0' * 64

        def unknown_id(v):
            v['scenarios'][0]['id'] = 'ACC-99'
        for change, reason in ((no_fixture, 'no fixture'), (wrong_path, 'the fixture path is not'),
                               (wrong_hash, 'the fixture\'s SHA-256 differs'), (wrong_row, 'the row hash differs'),
                               (unknown_id, 'the fixture path is not')):
            with self.subTest(reason):
                files = real_files()
                value = set_value(files)
                sid = value['scenarios'][0]['id']
                change(value)
                put_set(files, value)
                r = go(files, evaluate=stand_in(real_files()))
                sid = value['scenarios'][0]['id']
                self.assertEqual(r.results[sid], conformance.NOT_RUN)
                self.assertTrue(r.reasons[sid].startswith(reason), r.reasons[sid])

    def test_a_missing_fixture_file(self):
        files = real_files()
        del files[conformance.module_path('ACC-01')]
        result, reason, _ = self.result(files, 'ACC-01')
        self.assertEqual((result, reason), (conformance.NOT_RUN, 'the fixture file is missing'))

    def test_an_id_with_no_row(self):
        files = real_files()
        value = set_value(files)
        entry = value['scenarios'][0]
        path = conformance.FIXTURE_DIR + '/acc_99.py'
        entry.update(id='ACC-99', fixture={'path': path, 'sha256': conformance.sha256(files[conformance.module_path('ACC-01')])})
        files[path] = files[conformance.module_path('ACC-01')]
        put_set(files, value)
        r = go(files, evaluate=stand_in(real_files()))
        self.assertEqual(r.reasons['ACC-99'], 'the row hash differs from the bound scenario file')

    def test_an_id_on_two_rows(self):
        # D-210 P4: an id on more than one row of the bound file binds no row, so its fixture is never run. The set's
        # scenario_set_file_hash follows the changed file (and is frozen), so that only this condition differs.
        files = real_files()
        data = files[conformance.SCENARIO_FILE]
        row = next(x for x in data.decode('utf-8').split('\n') if x.startswith('| ACC-01 | '))
        files[conformance.SCENARIO_FILE] = data + row.encode('utf-8') + b'\n'
        self.assertIsNotNone(conformance.scenario_rows(data)[1]['ACC-01'])
        order, rows = conformance.scenario_rows(files[conformance.SCENARIO_FILE])
        self.assertIsNone(rows['ACC-01'])
        self.assertEqual(order.count('ACC-01'), 1)
        value = set_value(files)
        value['scenario_set_file_hash'] = conformance.sha256(files[conformance.SCENARIO_FILE])
        put_set(files, value)
        calls = []
        evaluate = stand_in()

        def counting(request, inputs, case_records):
            calls.append(request['task_id'])
            return evaluate(request, inputs, case_records)
        r = go(files, evaluate=counting)
        self.assertEqual(r.problems, ['a stand-in governor (reading)'])
        self.assertEqual((r.results['ACC-01'], r.reasons['ACC-01']),
                         (conformance.NOT_RUN, 'the row hash differs from the bound scenario file'))
        self.assertEqual(r.results['ACC-02'], conformance.PASS)
        cases = sum(len(conformance.unwrap(d)['cases']) for p, d in real_files().items()
                    if p.startswith(conformance.FIXTURE_DIR + '/'))
        self.assertEqual(len(calls), cases - len(fixture(files, 'ACC-01')['cases']))

    def test_a_path_outside_the_fixtures_is_never_read(self):
        files = real_files()
        value = set_value(files)
        sid = '../../../outside'
        value['scenarios'][0].update(id=sid, fixture={'path': conformance.module_path(sid), 'sha256': '0' * 64})
        put_set(files, value)
        asked = []

        def read(path):
            asked.append(path)
            return files.get(path)
        r = conformance.run(ROOT, COMMIT, TASK, read=read, evaluate=stand_in(),
                            listing=lambda: sorted(p for p in files if p.startswith(conformance.RECORDS_DIR + '/')))
        self.assertEqual(r.reasons[sid], 'the row hash differs from the bound scenario file')
        self.assertNotIn(conformance.module_path(sid), asked)
        self.assertTrue(r.problems == ['a stand-in governor (reading)'])

    def test_malformed_fixtures_are_not_run(self):
        def case(v):
            return v['cases'][0]
        changes = {
            'not wrapped': None,
            'a fourth key': lambda v: v.update(extra=1),
            'a scenario that differs': lambda v: v.update(scenario='ACC-02'),
            'a row hash that differs': lambda v: v.update(row_hash='0' * 64),
            'no cases': lambda v: v.update(cases=[]),
            'a case with a sixth key': lambda v: case(v).update(extra=1),
            'a request without a key': lambda v: case(v)['request'].pop('retry_count'),
            'a request task id of the wrong form': lambda v: case(v)['request'].update(task_id='T-1'),
            'a request hash of the wrong form': lambda v: case(v)['request'].update(task_content_hash='x'),
            'a request state outside section 2': lambda v: case(v)['request'].update(task_state='DOING'),
            'a request retry count of the wrong form': lambda v: case(v)['request'].update(retry_count={'used': -1, 'limit': 2}),
            'inputs without a key': lambda v: case(v)['inputs'].pop('risk'),
            'inputs risk of the wrong form': lambda v: case(v)['inputs'].update(risk='extreme'),
            'inputs flag of the wrong form': lambda v: case(v)['inputs'].update(auto_accept='no'),
            'inputs gate of the wrong form': lambda v: case(v)['inputs'].update(verification_plan=['X1']),
            'a record with a finding': lambda v: case(v)['records'].append({'record_id': 'x'}),
            'a repeated record id': lambda v: case(v)['records'].append(copy.deepcopy(case(v)['records'][0])),
            'when not agreeing with task_state': lambda v: case(v).update(when='re_evaluate'),
            'an expected key both present and not fixed': lambda v: case(v)['expected']['not_fixed'].append('decision'),
            'an expected key neither present nor not fixed': lambda v: case(v)['expected'].pop('decision'),
            'an expected decision outside the five': lambda v: case(v)['expected'].update(decision=['CONTINUE']),
            'an expected state outside section 2': lambda v: case(v)['expected'].update(next_state=['DOING']),
            'an expected missing of the wrong form': lambda v: case(v)['expected'].update(missing=[{'dimension': 'x'}]),
            'an expected reverify naming no record': lambda v: case(v)['expected'].update(reverify=['nothing']),
            'an expected ai_approval_shown of the wrong form': lambda v: case(v)['expected'].update(ai_approval_shown=1),
            'an expected key that section 4 does not name': lambda v: case(v)['expected'].update(extra=1),
        }
        for name, change in changes.items():
            with self.subTest(name):
                files = real_files()
                calls = []
                evaluate = stand_in(real_files())

                def counting(request, inputs, case_records):
                    calls.append(request['task_id'])
                    return evaluate(request, inputs, case_records)
                if change is None:
                    data = b'DATA = None\n'
                else:
                    value = fixture(files, 'ACC-01')
                    self.assertIn('decision', value['cases'][0]['expected'])
                    change(value)
                    data = wrap(value)
                put_fixture(files, 'ACC-01', data)
                r = go(files, evaluate=counting)
                self.assertEqual(r.results['ACC-01'], conformance.NOT_RUN)
                self.assertTrue(r.reasons['ACC-01'].startswith('the fixture is malformed'), r.reasons['ACC-01'])
                # 21 cases in all, one of them ACC-01's: none of the malformed fixture's cases is run (X3).
                self.assertEqual(len(calls), 20)

    def test_an_approval_of_the_wrong_class_is_malformed(self):
        files = real_files()
        sid = next(s for s in ('ACC-12', 'ACC-14', 'ACC-13') if any(
            c['expected'].get('approval') for c in fixture(files, s)['cases']))
        value = fixture(files, sid)
        c = next(c for c in value['cases'] if c['expected'].get('approval'))
        c['expected']['approval']['source_class'] = 'agent_declared'
        put_fixture(files, sid, wrap(value))
        r = go(files, evaluate=stand_in(real_files()))
        self.assertTrue(r.reasons[sid].startswith('the fixture is malformed'))


class R6EntryPoint(RestoreImports):
    def test_absent(self):
        r = go(real_files())
        self.assertTrue(r.value['counts'])
        self.assertIsNone(r.value['governor_identity'])
        self.assertEqual(sorted(set(r.reasons.values())), ['no fixture', 'the entry point is absent'])

    def test_loaded_from_the_root(self):
        files = real_files()
        files[conformance.GOVERNOR_PATH] = b'# the bytes of a governor\n'
        sys.modules[conformance.GOVERNOR_MODULE] = fake_governor(stand_in(files))
        r = go(files)
        self.assertTrue(r.value['counts'])
        self.assertEqual(r.value['governor_identity'], conformance.sha256(files[conformance.GOVERNOR_PATH]))
        self.assertEqual(list(r.results.values()).count(conformance.PASS), 19)
        self.assertEqual(r.record['outcome'], 'pass')

    def assert_failed(self, files):
        r = go(files)
        self.assertFalse(r.value['counts'])
        self.assertIn('the governor could not be loaded from the root (reading)', r.problems)
        self.assertEqual(set(r.results.values()), {conformance.NOT_RUN})
        self.assertIsNone(r.value['governor_identity'])

    def test_an_import_error_inside_the_governor(self):
        sys.meta_path.insert(0, Failing(ImportError('a failure inside the governor')))
        self.assert_failed(real_files())

    def test_a_missing_dependency_of_the_governor(self):
        sys.meta_path.insert(0, Failing(ModuleNotFoundError('no module', name='a_dependency')))
        self.assert_failed(real_files())

    def test_an_error_while_loading(self):
        sys.meta_path.insert(0, Failing(ValueError('a broken governor')))
        self.assert_failed(real_files())

    def test_no_callable_evaluate(self):
        files = real_files()
        files[conformance.GOVERNOR_PATH] = b'# a governor\n'
        sys.modules[conformance.GOVERNOR_MODULE] = fake_governor()
        self.assert_failed(files)
        sys.modules[conformance.GOVERNOR_MODULE].evaluate = 'not callable'
        self.assert_failed(files)

    def test_a_governor_that_is_not_the_roots(self):
        files = real_files()
        files[conformance.GOVERNOR_PATH] = b'# a governor\n'
        sys.modules[conformance.GOVERNOR_MODULE] = fake_governor(stand_in(files), file=str(ROOT / 'elsewhere.py'))
        self.assert_failed(files)
        sys.modules[conformance.GOVERNOR_MODULE] = fake_governor(stand_in(files))
        del files[conformance.GOVERNOR_PATH]
        self.assert_failed(files)

    def test_a_stand_in_is_never_loaded_and_never_counts(self):
        files = real_files()
        files[conformance.GOVERNOR_PATH] = b'# a governor\n'
        sys.modules[conformance.GOVERNOR_MODULE] = fake_governor(stand_in(files))
        r = go(files, evaluate=stand_in(files))
        self.assertFalse(r.value['counts'])
        self.assertIsNone(r.value['governor_identity'])


class R7Comparison(unittest.TestCase):
    def one(self, sid, change):
        files = real_files()
        r = go(files, evaluate=stand_in(files, lambda s, n, out: change(out) if s == sid else out))
        return r.results[sid], r.reasons[sid]

    def keys(self, sid):
        return set(fixture(real_files(), sid)['cases'][0]['expected']) - {'not_fixed'}

    def test_each_rule(self):
        files = real_files()
        cases = {sid: fixture(files, sid)['cases'] for sid in ('ACC-%02d' % i for i in range(1, 18))}

        def outside(values, allowed):
            return next(v for v in values if v not in allowed)
        changes = {
            'decision': lambda o, e: dict(o, decision=outside(conformance.ACCEPTANCE, e['decision'])),
            'next_state': lambda o, e: dict(o, next_task_state=outside(conformance.STATES, e['next_state'])),
            'missing': lambda o, e: dict(o, profile_used=o['profile_used'] + [
                {'dimension': 'x', 'required': ['y'], 'satisfied_by': [], 'missing_types': ['y']}]),
            'ai_approval_shown': lambda o, e: dict(o, rests_on_ai={'entries': [], 'approval': not e['ai_approval_shown']}),
        }
        for key, change in changes.items():
            with self.subTest(key):
                sid = next(s for s in sorted(cases) if key in cases[s][0]['expected'])
                r = go(files, evaluate=stand_in(files, lambda s, n, o: change(o, cases[s][n - 1]['expected']) if s == sid else o))
                self.assertEqual(r.results[sid], conformance.FAIL)
                self.assertIn(key, r.reasons[sid])
                self.assertEqual(list(r.results.values()).count(conformance.PASS), 18)

    def test_missing_is_a_set(self):
        exp = only('missing', [{'dimension': 'functional', 'evidence_type': 'unit_test'},
                               {'dimension': 'architecture', 'evidence_type': 'ai_review'},
                               {'dimension': 'functional', 'evidence_type': 'integration_test'}])

        def profile(*items):
            return {'profile_used': [{'dimension': d, 'required': t, 'satisfied_by': [], 'missing_types': t} for d, t in items]}
        self.assertEqual(conformance.compare(exp, profile(('architecture', ['ai_review']),
                                                          ('functional', ['integration_test', 'unit_test'])), []), [])
        self.assertEqual(conformance.compare(exp, profile(('functional', ['unit_test']), ('architecture', ['ai_review']),
                                                          ('functional', ['integration_test'])), []), [])
        for wrong in (profile(('functional', ['unit_test', 'integration_test'])),
                      profile(('functional', ['unit_test', 'integration_test']), ('architecture', ['ai_review', 'x'])),
                      {'profile_used': [{'dimension': 'functional', 'missing_types': 'unit_test'}]}, {}):
            self.assertEqual(conformance.compare(exp, wrong, []), ['missing'])
        sid = next(s for s in ('ACC-%02d' % i for i in range(1, 18))
                   if any(c['expected'].get('missing') for c in fixture(real_files(), s)['cases']))
        self.assertEqual(self.one(sid, lambda o: dict(o, profile_used=[]))[0], conformance.FAIL)

    def test_reverify_is_a_subset(self):
        sid = next(s for s in ('ACC-%02d' % i for i in range(1, 18))
                   if any(c['expected'].get('reverify') for c in fixture(real_files(), s)['cases']))
        self.assertEqual(self.one(sid, lambda o: dict(o, reverify=o['reverify'] + ['another']))[0], conformance.PASS)
        self.assertEqual(self.one(sid, lambda o: dict(o, reverify=[]))[0], conformance.FAIL)

    def test_approval(self):
        files = real_files()
        sid_null = next(s for s in ('ACC-%02d' % i for i in range(1, 18))
                        if any('approval' in c['expected'] and c['expected']['approval'] is None for c in fixture(files, s)['cases']))
        self.assertEqual(self.one(sid_null, lambda o: dict(o, approval_record='some-record'))[0], conformance.FAIL)
        o = self.one(sid_null, lambda o: {k: v for k, v in o.items() if k != 'approval_record'})
        self.assertEqual(o[0], conformance.PASS)
        exp = only('approval', {'record_id': 'R-1', 'source_class': 'human_authority'})
        recs =[{'record_id': 'R-1', 'source_class': 'decision_agent'}, {'record_id': 'R-2', 'source_class': 'human_authority'}]
        self.assertEqual(conformance.compare(exp, {'approval_record': 'R-1'}, recs), ['approval'])
        self.assertEqual(conformance.compare(exp, {'approval_record': 'R-2'}, recs), ['approval'])
        recs[0]['source_class'] = 'human_authority'
        self.assertEqual(conformance.compare(exp, {'approval_record': 'R-1'}, recs), [])

    def test_ai_approval_shown_both_ways(self):
        for want in (True, False):
            exp = only('ai_approval_shown', want)
            self.assertEqual(conformance.compare(exp, {'rests_on_ai': {'entries': [], 'approval': want}}, []), [])
            self.assertEqual(conformance.compare(exp, {'rests_on_ai': {'entries': [], 'approval': not want}}, []),
                             ['ai_approval_shown'])

    def test_not_fixed_keys_are_not_compared_and_absent_keys_fail(self):
        nf = {'decision': 'decision', 'next_state': 'next_task_state', 'missing': 'profile_used',
              'reverify': 'reverify', 'ai_approval_shown': 'rests_on_ai'}
        values = {'decision': ['ACCEPT'], 'next_state': ['DONE'], 'missing': [], 'reverify': [], 'ai_approval_shown': False}
        everything = dict(values, approval=None, not_fixed=[])
        for key, field in nf.items():
            with self.subTest(key):
                observed = {'decision': 'ACCEPT', 'next_task_state': 'DONE', 'profile_used': [], 'reverify': [],
                            'rests_on_ai': {'entries': [], 'approval': False}}
                self.assertEqual(conformance.compare(everything, observed, []), [])
                del observed[field]
                self.assertEqual(conformance.compare(everything, observed, []), [key])
                exp = dict(everything, not_fixed=[key])
                del exp[key]
                self.assertEqual(conformance.compare(exp, observed, []), [])

    def test_not_a_decision_record(self):
        def raises(o):
            raise RuntimeError('a governor error')
        for name, change in (('raises', raises), ('a list', lambda o: [o]),
                             ('an execution string', lambda o: dict(o, decision='CONTINUE')),
                             ('no rests_on_ai', lambda o: {k: v for k, v in o.items() if k != 'rests_on_ai'}),
                             ('a rests_on_ai of the wrong form', lambda o: dict(o, rests_on_ai={'approval': True})),
                             ('a record without record_id', lambda o: {k: v for k, v in o.items() if k != 'record_id'})):
            with self.subTest(name):
                result, reason = self.one('ACC-01', change)
                self.assertEqual(result, conformance.NOT_RUN)
                self.assertTrue(reason.startswith('case 1: '), reason)

    def test_an_error_record_is_compared(self):
        def error(o):
            o = {k: v for k, v in o.items() if k != 'rests_on_ai'}
            return dict(o, decision=None, error='no decision possible')
        self.assertEqual(self.one('ACC-01', error)[0], conformance.FAIL)

    def test_fail_before_not_run(self):
        def change(sid, n, out):
            if sid != 'ACC-13':
                return out
            if n == 1:
                return dict(out, next_task_state='STALE')
            raise RuntimeError('a governor error')
        files = real_files()
        self.assertEqual(len(fixture(files, 'ACC-13')['cases']), 3)
        r = go(files, evaluate=stand_in(files, change))
        self.assertEqual(r.results['ACC-13'], conformance.FAIL)

    def test_copies_are_passed(self):
        files = real_files()
        evaluate = stand_in(files)

        def mutating(request, inputs, case_records):
            out = evaluate(request, inputs, case_records)
            case_records.clear()
            inputs.clear()
            return out
        r = go(files, evaluate=mutating)
        self.assertEqual(list(r.results.values()).count(conformance.PASS), 19)


class R8RunRecord(RestoreImports):
    def test_keys_order_and_record(self):
        files = real_files()
        r = go(files)
        self.assertEqual(set(r.value), {'set_file_sha256', 'scenario_set_version', 'fixture_set_version', 'runner',
                                        'governor_identity', 'commit', 'counts', 'results'})
        self.assertEqual([x['id'] for x in r.value['results']], [e['id'] for e in set_value(files)['scenarios']])
        self.assertEqual(r.value['runner'], {'path': conformance.RUNNER_PATH,
                                             'sha256': conformance.sha256(files[conformance.RUNNER_PATH])})
        self.assertEqual(r.value['set_file_sha256'], conformance.sha256(files[conformance.SET_FILE]))
        self.assertEqual(set(r.record), {'record_id', 'fact_kind', 'source_class', 'recorder', 'subject',
                                         'evidence_type', 'dimension', 'outcome', 'commit', 'refers_to'})
        self.assertEqual(check_record(r.record), [])
        self.assertEqual(r.record['refers_to'], conformance.sha256(r.text))
        self.assertEqual(r.record['record_id'], conformance.RECORD_PREFIX + conformance.sha256(r.text))
        self.assertEqual((r.record['fact_kind'], r.record['source_class'], r.record['evidence_type'],
                          r.record['dimension']), ('observation', 'deterministic_tool_external_ci', 'conformance_run',
                                                   'functional'))

    def test_outcome_pass_and_fail(self):
        files = real_files()
        self.assertEqual(go(files).record['outcome'], 'fail')
        files[conformance.GOVERNOR_PATH] = b'# a governor\n'
        sys.modules[conformance.GOVERNOR_MODULE] = fake_governor(stand_in(files))
        self.assertEqual(go(files).record['outcome'], 'pass')
        sys.modules[conformance.GOVERNOR_MODULE] = fake_governor(
            stand_in(files, lambda s, n, o: dict(o, next_task_state='STALE') if s == 'ADV-03' else o))
        self.assertEqual(go(files).record['outcome'], 'fail')

    def test_outcome_function(self):
        self.assertEqual(conformance.outcome(True, {'A': 'PASS'}, ['A']), 'pass')
        self.assertEqual(conformance.outcome(False, {'A': 'PASS'}, ['A']), 'fail')
        self.assertEqual(conformance.outcome(True, {'A': 'NOT_RUN'}, ['A']), 'fail')
        self.assertEqual(conformance.outcome(True, {'A': 'NOT_RUN'}, []), 'fail')


class R9Main(RestoreImports):
    def call(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = conformance.main(args)
        return code, out.getvalue()

    def test_output_and_return_values(self):
        code, out = self.call([str(ROOT), COMMIT, TASK])
        self.assertEqual(code, 1)
        text, line = out[:-1].rsplit('\n', 1)
        r = conformance.run(ROOT, COMMIT, TASK)
        self.assertEqual((text + '\n').encode('utf-8'), r.text)
        self.assertEqual(json.loads(line), r.record)
        self.assertEqual(line, json.dumps(r.record, sort_keys=True))
        # A run with outcome pass needs a governor file at the root, which no test writes; main's mapping of outcome
        # pass to 0 is checked with run replaced for this test (restored afterwards).
        files = real_files()
        files[conformance.GOVERNOR_PATH] = b'# a governor\n'
        sys.modules[conformance.GOVERNOR_MODULE] = fake_governor(stand_in(files))
        passing = go(files)
        self.assertEqual(passing.record['outcome'], 'pass')
        self.addCleanup(setattr, conformance, 'run', conformance.run)
        conformance.run = lambda root, commit, task: passing
        self.assertEqual(self.call([str(ROOT), COMMIT, TASK]), (0, passing.text.decode('utf-8')
                                                               + json.dumps(passing.record, sort_keys=True) + '\n'))

    def test_wrong_arguments(self):
        for args in ([], [str(ROOT), COMMIT], [str(ROOT), 'x', TASK], [str(ROOT), COMMIT, 'x'],
                     [str(ROOT), COMMIT, TASK, 'extra']):
            with self.subTest(args):
                self.assertEqual(self.call(args)[0], 2)


if __name__ == '__main__':
    unittest.main()
