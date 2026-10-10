"""Property tests of the conformance runner's Resume Check entry (TASK-006 AC13): standard library only, fixed seeds.
Every input is built in memory from the repository's own files and given through the runner's byte reader and records
listing; the frozen Resume Check fixtures under tests/conformance/fixtures_rc are read only as bytes; no file is
written. Each test starts with the governor and the Resume Check absent, restored after the test.

Properties: the same inputs always give the same run record; a one-byte change of a Resume Check fixture never gives
that scenario PASS; a capability other than the bound file's never gives PASS; and, for the invariants the task relates
to: INV-005, every Resume Check result is PASS, FAIL or NOT_RUN and a returned string is never an execution decision
record; INV-006, with no Resume Check no Resume Check scenario is PASS; INV-007, a fixture whose bytes differ from its
set entry's hash is never run; INV-008, a stand-in Resume Check never makes a run count.
"""
import json
import pathlib
import random
import sys
import unittest

from aieos_bootstrap import conformance

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMIT = 'a' * 40
TASK = 'TASK-006'
RC_DIR = 'tests/conformance/fixtures_rc'
RC_IDS = ['RC-%02d' % n for n in range(1, 12)]
TEST_RECORDS = 'docs/records/TEST-6.jsonl'
SEED = 6006


def rc_path(sid):
    return RC_DIR + '/' + sid.lower().replace('-', '_') + '.py'


def base_files():
    files = {}
    for path in (conformance.RUNNER_PATH, conformance.SCENARIO_FILE):
        files[path] = (ROOT / path).read_bytes()
    for folder in (conformance.FIXTURE_DIR, RC_DIR):
        for p in sorted((ROOT / folder).glob('*.py')):
            files[folder + '/' + p.name] = p.read_bytes()
    for p in sorted((ROOT / conformance.RECORDS_DIR).glob('*.jsonl')):
        files[conformance.RECORDS_DIR + '/' + p.name] = p.read_bytes()
    value = conformance.unwrap((ROOT / conformance.SET_FILE).read_bytes())
    for entry in value['scenarios']:
        if entry['id'] in RC_IDS:
            entry['fixture'] = {'path': rc_path(entry['id']), 'sha256': conformance.sha256(files[rc_path(entry['id'])])}
    put_set(files, value)
    return files


def put_set(files, value):
    files[conformance.SET_FILE] = conformance.FIRST + conformance.canonical_text(value) + conformance.LAST
    rec = {'approval_binding': {'hash': conformance.sha256(files[conformance.SET_FILE]), 'kind': 'change_request'},
           'decision_ref': 'D-000', 'fact_kind': 'authority', 'record_id': 'TEST-freeze-' + str(len(files)),
           'recorder': 'a property test', 'source_class': 'decision_agent', 'subject': 'TASK-005'}
    files[TEST_RECORDS] = files.get(TEST_RECORDS, b'') + (json.dumps(rec, sort_keys=True) + '\n').encode('utf-8')


def go(files, check=None, asked=None):
    def read(path):
        if asked is not None:
            asked.append(path)
        return files.get(path)

    def listing():
        return sorted(p for p in files if p.startswith(conformance.RECORDS_DIR + '/') and p.endswith('.jsonl'))
    return conformance.run(ROOT, COMMIT, TASK, read=read, listing=listing, check=check)


def answers():
    out = {}
    for p in sorted((ROOT / RC_DIR).glob('*.py')):
        for case in conformance.unwrap(p.read_bytes())['cases']:
            out[json.dumps(case['inputs'], sort_keys=True)] = case['expected']['decision'][0]
    return out


def stand_in(calls=None):
    by_inputs = answers()

    def check(inputs):
        if calls is not None:
            calls.append(inputs['task_id'])
        return {'record_id': 'EXE-1', 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_external_ci',
                'recorder': 'a stand-in Resume Check', 'subject': inputs['task_id'],
                'decision': by_inputs[json.dumps(inputs, sort_keys=True)]}
    return check


class Absent:
    def find_spec(self, name, path=None, target=None):
        if name in (conformance.GOVERNOR_MODULE, conformance.RESUME_CHECK_MODULE):
            raise ModuleNotFoundError('No module named %r' % name, name=name)
        return None


class Isolated(unittest.TestCase):
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


class Properties(Isolated):
    def test_the_same_inputs_give_the_same_run_record(self):
        files = base_files()
        first = go(files, check=stand_in())
        for _ in range(3):
            again = go(dict(files), check=stand_in())
            self.assertEqual((again.text, again.record), (first.text, first.record))
        self.assertEqual(go(files).text, go(dict(files)).text)

    def test_a_one_byte_change_never_passes(self):
        rng = random.Random(SEED)
        for _ in range(40):
            files = base_files()
            sid = rng.choice(RC_IDS)
            data = bytearray(files[rc_path(sid)])
            i = rng.randrange(len(data))
            data[i] = (data[i] + rng.randrange(1, 256)) % 256
            files[rc_path(sid)] = bytes(data)
            if rng.random() < 0.5:
                value = conformance.unwrap(files[conformance.SET_FILE])
                next(e for e in value['scenarios'] if e['id'] == sid)['fixture']['sha256'] = conformance.sha256(bytes(data))
                put_set(files, value)
            r = go(files, check=stand_in())
            self.assertNotEqual(r.results[sid], conformance.PASS, (sid, i))

    def test_another_capability_never_passes(self):
        rng = random.Random(SEED + 1)
        for _ in range(30):
            files = base_files()
            value = conformance.unwrap(files[conformance.SET_FILE])
            sid = rng.choice(RC_IDS)
            entry = next(e for e in value['scenarios'] if e['id'] == sid)
            entry['capability'] = rng.choice([c for c in conformance.CAPABILITIES if c != 'Resume Check'])
            if rng.random() < 0.5:
                want = conformance.expected_path(sid, entry['capability'])
                if want is not None:
                    entry['fixture']['path'] = want
                    files[want] = files[rc_path(sid)]
            put_set(files, value)
            r = go(files, check=stand_in())
            self.assertEqual(r.results[sid], conformance.NOT_RUN, (sid, entry['capability']))

    def test_inv_005_results_and_returned_strings(self):
        rng = random.Random(SEED + 2)
        right = stand_in()
        values = sorted(conformance.EXECUTION) + ['ACCEPT', 'continue', '']
        for _ in range(20):
            pick = rng.choice(values)
            as_string = rng.random() < 0.5

            def check(inputs):
                return pick if as_string else dict(right(inputs), decision=pick)
            r = go(base_files(), check=check)
            for sid in RC_IDS:
                self.assertIn(r.results[sid], (conformance.PASS, conformance.FAIL, conformance.NOT_RUN))
                if as_string:
                    self.assertEqual((r.results[sid], r.reasons[sid]),
                                     (conformance.NOT_RUN, 'case 1: the call returned no JSON object'))

    def test_inv_006_with_no_resume_check_no_scenario_passes(self):
        r = go(base_files())
        for sid in RC_IDS:
            self.assertEqual(r.results[sid], conformance.NOT_RUN)

    def test_inv_007_a_fixture_unlike_its_hash_is_never_run(self):
        rng = random.Random(SEED + 3)
        for _ in range(20):
            files = base_files()
            sid = rng.choice(RC_IDS)
            files[rc_path(sid)] = files[rc_path(sid)] + b' '
            calls, asked = [], []
            r = go(files, check=stand_in(calls), asked=asked)
            task_id = conformance.unwrap(base_files()[rc_path(sid)])['cases'][0]['inputs']['task_id']
            self.assertEqual(r.reasons[sid], 'the fixture\'s SHA-256 differs from its set entry')
            self.assertEqual(calls.count(task_id), sum(
                conformance.unwrap(files[rc_path(o)])['cases'][0]['inputs']['task_id'] == task_id
                for o in RC_IDS if o != sid))

    def test_inv_008_a_stand_in_never_makes_a_run_count(self):
        rng = random.Random(SEED + 4)
        for _ in range(10):
            files = base_files()
            if rng.random() < 0.5:
                files = {k: v for k, v in files.items() if not k.startswith(RC_DIR + '/')}
            r = go(files, check=stand_in())
            self.assertFalse(r.value['counts'])
            self.assertIn('a stand-in Resume Check (reading)', r.problems)


if __name__ == '__main__':
    unittest.main()
