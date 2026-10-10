"""Property tests of the conformance runner of TASK-003, with fixed seeds (AC12).

The helpers below repeat those of tests/unit/test_runner.py, because each CI test folder is discovered on its own.
Every changed input is built in memory and given to the runner through its byte reader and records listing (AC1);
no file is written. Stand-in governors are test seams (AC6).
Each test starts with the governor absent, whether or not a governor file exists (TASK-004 AC14).
"""
import json
import pathlib
import random
import sys
import unittest

from aieos_bootstrap import conformance
from aieos_bootstrap.records import SOURCE_CLASSES

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMIT = 'a' * 40
TASK = 'TASK-003'
FIRST, LAST = conformance.FIRST, conformance.LAST
TEST_RECORDS = 'docs/records/TEST-9.jsonl'
TRIALS = 30


def real_files():
    files = {}
    for path in (conformance.RUNNER_PATH, conformance.SET_FILE, conformance.SCENARIO_FILE):
        files[path] = (ROOT / path).read_bytes()
    for p in sorted((ROOT / conformance.FIXTURE_DIR).glob('*.py')):
        files[conformance.FIXTURE_DIR + '/' + p.name] = p.read_bytes()
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


def tree_files():
    """real_files() with the Resume Check module and the Resume Check fixtures too, as the tree holds them, so that a
    run over these files equals the run over the tree in either state of the set file (contract AC3)."""
    files = real_files()
    files[conformance.RESUME_CHECK_PATH] = (ROOT / conformance.RESUME_CHECK_PATH).read_bytes()
    for p in sorted((ROOT / conformance.RC_FIXTURE_DIR).glob('*.py')):
        files[conformance.RC_FIXTURE_DIR + '/' + p.name] = p.read_bytes()
    return files


def go(files, evaluate=None):
    def read(path):
        return files.get(path)

    def listing():
        return sorted(p for p in files if p.startswith(conformance.RECORDS_DIR + '/') and p.endswith('.jsonl'))
    return conformance.run(ROOT, COMMIT, TASK, read=read, listing=listing, evaluate=evaluate)


def freeze_line(digest, source_class='decision_agent'):
    rec = {'approval_binding': {'hash': digest, 'kind': 'change_request'}, 'decision_ref': 'D-000',
           'fact_kind': 'authority', 'record_id': 'TEST-freeze-' + source_class, 'recorder': 'a property test',
           'source_class': source_class, 'subject': 'TASK-002'}
    return (json.dumps(rec, sort_keys=True) + '\n').encode('utf-8')


def without_the_set_freeze(files):
    path = conformance.RECORDS_DIR + '/TASK-002.jsonl'
    files[path] = b''.join(ln + b'\n' for ln in files[path].split(b'\n') if ln and b'TASK-002-freeze-set' not in ln)
    return files


def stand_in(files, calls=None, decision=None):
    """Answers each case from its own expected values; records each call's scenario id in ``calls``; ``decision``,
    when given, replaces the decision of every answer."""
    by_request = {}
    for path, data in real_files().items():
        if path.startswith(conformance.FIXTURE_DIR + '/'):
            value = conformance.unwrap(data)
            for case in value['cases']:
                by_request[json.dumps(case['request'], sort_keys=True)] = (value['scenario'], case)

    def evaluate(request, inputs, case_records):
        sid, case = by_request[json.dumps(request, sort_keys=True)]
        if calls is not None:
            calls.append(sid)
        exp = case['expected']
        nf = set(exp['not_fixed'])
        by_dim = {}
        for m in ([] if 'missing' in nf else exp['missing']):
            by_dim.setdefault(m['dimension'], []).append(m['evidence_type'])
        return {
            'record_id': 'DEC-' + request['task_id'], 'fact_kind': 'interpretation',
            'source_class': 'deterministic_tool_external_ci', 'recorder': 'a stand-in governor',
            'subject': request['task_id'],
            'decision': decision if decision is not None else ('NEEDS_REVIEW' if 'decision' in nf else exp['decision'][0]),
            'next_task_state': 'IN_REVIEW' if 'next_state' in nf else exp['next_state'][0],
            'profile_used': [{'dimension': d, 'required': t, 'satisfied_by': [], 'missing_types': t}
                             for d, t in by_dim.items()],
            'reverify': [] if 'reverify' in nf else list(exp['reverify']),
            'approval_record': None if 'approval' in nf or exp['approval'] is None else exp['approval']['record_id'],
            'rests_on_ai': {'entries': [], 'approval': False if 'ai_approval_shown' in nf else exp['ai_approval_shown']},
        }
    return evaluate


def one_byte_changed(data, rng):
    i = rng.randrange(len(data))
    new = rng.choice([b for b in range(256) if b != data[i]])
    return data[:i] + bytes([new]) + data[i + 1:]


def fixture_paths(files):
    return sorted(p for p in files if p.startswith(conformance.FIXTURE_DIR + '/'))


def text_in_order(value, rng):
    """A JSON text in the canonical layout, but with the keys of every object in a random order."""
    if isinstance(value, dict):
        keys = list(value)
        rng.shuffle(keys)
        return '{' + ','.join(json.dumps(k) + ':' + text_in_order(value[k], rng) for k in keys) + '}'
    if isinstance(value, list):
        return '[' + ','.join(text_in_order(x, rng) for x in value) + ']'
    return json.dumps(value, ensure_ascii=False)


class Absent:
    """A meta-path finder that makes the governor absent, as when no governor file exists (TASK-004 AC14)."""

    def find_spec(self, name, path=None, target=None):
        if name == conformance.GOVERNOR_MODULE:
            raise ModuleNotFoundError('No module named %r' % name, name=name)
        return None


def isolate_governor(test):
    """Removes any loaded governor from sys.modules and from the package's attributes and puts Absent first on
    sys.meta_path, so that the test sees the governor absent (TASK-004 AC14). sys.modules, sys.meta_path and the
    package's attribute are restored after the test."""
    modules, meta = dict(sys.modules), list(sys.meta_path)
    package = sys.modules.get('aieos_bootstrap')
    saved = getattr(package, 'governor', None) if package is not None else None
    sys.modules.pop(conformance.GOVERNOR_MODULE, None)
    if package is not None and hasattr(package, 'governor'):
        delattr(package, 'governor')
    sys.meta_path.insert(0, Absent())

    def restore():
        sys.meta_path[:] = meta
        for name in list(sys.modules):
            if name not in modules:
                del sys.modules[name]
        sys.modules.update(modules)
        if package is None:
            return
        if saved is not None:
            package.governor = saved
        elif hasattr(package, 'governor'):
            delattr(package, 'governor')
    test.addCleanup(restore)


class RunnerProperties(unittest.TestCase):
    def setUp(self):
        isolate_governor(self)

    def test_the_same_inputs_give_the_same_run_record(self):
        files = tree_files()
        self.assertEqual(go(files).text, go(tree_files()).text)
        self.assertEqual(go(files, stand_in(files)).text, go(tree_files(), stand_in(files)).text)
        self.assertEqual(go(files).record, conformance.run(ROOT, COMMIT, TASK).record)

    def test_a_one_byte_change_of_a_fixture_never_passes_and_is_never_run(self):
        rng = random.Random(3001)
        cases_of = {p: len(conformance.unwrap(d)['cases']) for p, d in real_files().items()
                    if p.startswith(conformance.FIXTURE_DIR + '/')}
        for _ in range(TRIALS):
            files = real_files()
            path = rng.choice(fixture_paths(files))
            files[path] = one_byte_changed(files[path], rng)
            calls = []
            r = go(files, stand_in(files, calls))
            sid = conformance.unwrap(real_files()[path])['scenario']
            self.assertEqual(r.results[sid], conformance.NOT_RUN)
            self.assertEqual(r.reasons[sid], 'the fixture\'s SHA-256 differs from its set entry')
            # INV-007: a fixture whose bytes differ from its frozen hash is never run.
            self.assertNotIn(sid, calls)
            self.assertEqual(len(calls), 21 - cases_of[path])

    def test_a_one_byte_change_of_the_set_file_makes_the_run_not_count(self):
        rng = random.Random(3002)
        for _ in range(TRIALS):
            files = real_files()
            files[conformance.SET_FILE] = one_byte_changed(files[conformance.SET_FILE], rng)
            r = go(files, stand_in(real_files()))
            self.assertFalse(r.value['counts'])
            self.assertEqual(set(r.results.values()), {conformance.NOT_RUN})

    def test_any_reordering_of_keys_is_malformed(self):
        rng = random.Random(3003)
        files = real_files()
        values = [conformance.unwrap(files[p]) for p in fixture_paths(files)]
        found = 0
        while found < TRIALS:
            value = rng.choice(values)
            text = text_in_order(value, rng)
            reparsed = json.loads(text)
            pretty = json.dumps(reparsed, indent=2, ensure_ascii=False, sort_keys=False) + '\n'
            data = FIRST + pretty.encode('utf-8') + LAST
            if pretty == conformance.canon(reparsed) + '\n':
                continue
            found += 1
            with self.assertRaises(conformance.Malformed):
                conformance.unwrap(data)

    def test_inv_005_results_and_execution_strings(self):
        rng = random.Random(3004)
        execution = ['CONTINUE', 'CONTINUE_WITH', 'REPLAN', 'STOP: scope invalid', 'STOP: runtime insufficient',
                     'STOP: violation', 'BLOCKED', 'ESCALATE']
        pool = list(conformance.ACCEPTANCE) + execution + ['accept', 'PASS', '', 'NEEDS-REVIEW']
        for _ in range(TRIALS):
            decision = rng.choice(pool)
            files = real_files()
            r = go(files, stand_in(files, decision=decision))
            self.assertTrue(set(r.results.values()) <= {conformance.PASS, conformance.FAIL, conformance.NOT_RUN})
            if decision not in conformance.ACCEPTANCE:
                self.assertNotIn(conformance.PASS, r.results.values())
                self.assertNotIn(conformance.FAIL, r.results.values())
        for decision in execution:
            out = stand_in(real_files(), decision=decision)(*first_case())
            self.assertNotEqual(conformance.decision_problem(out), '')

    def test_inv_006_no_governor_no_pass(self):
        rng = random.Random(3005)
        for _ in range(TRIALS):
            files = real_files()
            if rng.random() < 0.5:
                files[TEST_RECORDS] = freeze_line(conformance.sha256(files[conformance.SET_FILE]), 'human_authority')
            r = go(files)
            self.assertNotIn(conformance.PASS, r.results.values())
            self.assertEqual(r.record['outcome'], 'fail')

    def test_inv_008_only_an_approver_makes_the_run_count(self):
        rng = random.Random(3006)
        others = sorted(set(SOURCE_CLASSES) - conformance.APPROVERS)
        self.assertIn('agent_declared', others)
        for _ in range(TRIALS):
            files = without_the_set_freeze(fixed_files())
            cls = rng.choice(others)
            files[TEST_RECORDS] = freeze_line(conformance.sha256(files[conformance.SET_FILE]), cls)
            self.assertFalse(go(files).value['counts'], cls)
        files = without_the_set_freeze(fixed_files())
        files[TEST_RECORDS] = freeze_line(conformance.sha256(files[conformance.SET_FILE]), 'decision_agent')
        self.assertTrue(go(files).value['counts'])


def first_case():
    value = conformance.unwrap(real_files()[conformance.module_path('ACC-01')])
    case = value['cases'][0]
    return case['request'], case['inputs'], case['records']


class FixedSetValue(unittest.TestCase):
    """The fixed set value of TASK-013 (contract AC2): the set file at 1659a8cb, approved by TASK-002's freeze record."""

    def test_the_fixed_value_is_the_frozen_set_file(self):
        data = fixed_files()[conformance.SET_FILE]
        self.assertEqual(conformance.sha256(data), FIXED_SET_SHA256)
        self.assertEqual(conformance.freeze_approval(conformance._Tree(ROOT), FIXED_SET_SHA256), (True, ''))
        value = conformance.unwrap(data)
        self.assertEqual([e['fixture'] for e in value['scenarios'] if e['capability'] == 'Resume Check'], [None] * 11)
        self.assertEqual(value['fixture_set_version'], 1)


if __name__ == '__main__':
    unittest.main()
