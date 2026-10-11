"""Unit tests of aieos_bootstrap.stale (task TASK-023, its rules R1 to R8); every rule has at least one passing case
and one failing case. Each test names the criteria it stands for in its own docstring."""

import ast
import copy
import hashlib
import pathlib
import unittest

from aieos_bootstrap import records, stale

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap' / 'stale.py'
T = 'TASK-099'
ACC = 'a' * 40
C1 = 'b' * 40
C2 = 'c' * 40
OTHER = 'd' * 40


def inputs(**over):
    """A well-formed input: one record bound to the accepted commit, one path entry, one later commit changing it."""
    base = {
        'task_id': T, 'accepted_commit': ACC, 'trigger_commit': C2,
        'records': [{'record_id': 'r1', 'commit': ACC, 'intent_versions': {'spec': 'v1'}}],
        'intent_current': {'spec': 'v1'},
        'read_set': [{'entry': 'docs/a.md', 'kind': 'path', 'patterns': ['docs/a.md']}],
        'read_set_estimate': False,
        'base_commits': [{'commit': C1, 'paths': ['src/x.py'], 'submitted_by_task': False},
                         {'commit': C2, 'paths': ['docs/a.md'], 'submitted_by_task': False}],
        'earlier_events': [],
    }
    base.update(over)
    return base


def unc(result):
    return {(u['rule'], u['ref'], u['detail']) for u in result['uncovered']}


class InputForm(unittest.TestCase):
    """R1."""

    def test_well_formed_has_no_error(self):
        """TASK-023 AC1: a well-formed input gives error None."""
        self.assertIsNone(stale.stale(inputs())['error'])

    def test_each_malformed_form_names_its_key(self):
        """TASK-023 AC1 and AC8: each malformed form gives an error naming its key, no stale id, no event and no
        uncovered entry."""
        cases = [
            ('task_id', 'TASK-99'), ('accepted_commit', 'A' * 40), ('trigger_commit', 'e' * 39),
            ('records', [{'record_id': ''}]), ('records', [{'record_id': 'r', 'commit': 'x'}]),
            ('records', [{'record_id': 'r', 'intent_versions': {'s': '1'}}]),
            ('records', [{'record_id': 'r'}, {'record_id': 'r'}]),
            ('intent_current', {'s': 'version 1'}), ('read_set', [{'entry': 'a', 'kind': 'file', 'patterns': None}]),
            ('read_set', [{'entry': 'a', 'kind': 'path'}]), ('read_set_estimate', 'yes'),
            ('base_commits', [{'commit': ACC, 'paths': [], 'submitted_by_task': False}]),
            ('base_commits', [{'commit': C1, 'paths': [], 'submitted_by_task': False}] * 2),
            ('base_commits', [{'commit': C1, 'paths': [], 'submitted_by_task': 0}]),
            ('earlier_events', [{'reason': 'other', 'records': []}]),
        ]
        for key, value in cases:
            r = stale.stale(inputs(**{key: value}))
            self.assertTrue(r['error'].startswith(key), (key, r['error']))
            self.assertEqual(r, {'stale': {'commit': [], 'intent_version': []}, 'events': [], 'uncovered': [],
                                 'error': r['error']})

    def test_first_failing_key_is_named(self):
        """TASK-023 AC1: with two malformed keys, the first in AC1's order is named."""
        r = stale.stale(inputs(records='x', task_id='bad'))
        self.assertTrue(r['error'].startswith('task_id'))

    def test_missing_and_unknown_keys(self):
        """TASK-023 AC1: a missing key and an unknown key are malformed; a non-mapping is malformed."""
        x = inputs()
        del x['read_set']
        self.assertIn('read_set', stale.stale(x)['error'])
        self.assertIn('unknown key', stale.stale(inputs(extra=1))['error'])
        self.assertIsNotNone(stale.stale([])['error'])


class RuleTwo(unittest.TestCase):
    """R2."""

    def test_differing_version_is_stale(self):
        """TASK-023 AC2: a record whose version differs from the current one is stale with reason intent_version."""
        r = stale.stale(inputs(intent_current={'spec': 'v2'}))
        self.assertEqual(r['stale']['intent_version'], ['r1'])

    def test_equal_version_is_not_stale(self):
        """TASK-023 AC2: an equal version is not stale."""
        self.assertEqual(stale.stale(inputs())['stale']['intent_version'], [])

    def test_missing_current_version_is_uncovered_only(self):
        """TASK-023 AC2: an id with no current version is uncovered and does not by itself make the record stale."""
        r = stale.stale(inputs(intent_current={}))
        self.assertEqual(r['stale']['intent_version'], [])
        self.assertIn(('rule 2', 'r1', 'no current version of spec'), unc(r))


class RuleThree(unittest.TestCase):
    """R3."""

    def test_path_entry_met(self):
        """TASK-023 AC3: a later commit changing a path entry makes the record stale with reason commit."""
        self.assertEqual(stale.stale(inputs())['stale']['commit'], ['r1'])

    def test_path_entry_not_met(self):
        """TASK-023 AC3: a commit changing no read-set path makes nothing stale."""
        bc = [{'commit': C1, 'paths': ['src/x.py'], 'submitted_by_task': False}]
        self.assertEqual(stale.stale(inputs(base_commits=bc))['stale']['commit'], [])

    def test_wildcard_path_entry(self):
        """TASK-023 AC3: a path entry with a wildcard is matched by resume_check's rules."""
        rs = [{'entry': 'docs/**', 'kind': 'path', 'patterns': ['docs/**']}]
        self.assertEqual(stale.stale(inputs(read_set=rs))['stale']['commit'], ['r1'])

    def test_interface_and_schema_patterns(self):
        """TASK-023 AC3: an interface or schema entry is met through its resolved patterns, and not otherwise."""
        for kind in ('interface', 'schema'):
            rs = [{'entry': 'pkg.f', 'kind': kind, 'patterns': ['docs/*.md']}]
            self.assertEqual(stale.stale(inputs(read_set=rs))['stale']['commit'], ['r1'])
            rs = [{'entry': 'pkg.f', 'kind': kind, 'patterns': ['src/other/**']}]
            self.assertEqual(stale.stale(inputs(read_set=rs))['stale']['commit'], [])

    def test_submitted_commit_ignored(self):
        """TASK-023 AC3: a commit the task's own submission made does not meet the read-set."""
        bc = [{'commit': C2, 'paths': ['docs/a.md'], 'submitted_by_task': True}]
        self.assertEqual(stale.stale(inputs(base_commits=bc))['stale']['commit'], [])

    def test_unresolved_entry_uncovered(self):
        """TASK-023 AC3: an entry with patterns None is uncovered and meets nothing."""
        rs = [{'entry': 'pkg.f', 'kind': 'interface', 'patterns': None},
              {'entry': 'docs/a.md', 'kind': 'path', 'patterns': None}]
        r = stale.stale(inputs(read_set=rs))
        self.assertEqual(r['stale']['commit'], [])
        self.assertIn(('rule 3', 'pkg.f', 'not resolved by the caller'), unc(r))
        self.assertIn(('rule 3', 'docs/a.md', 'not resolved by the caller'), unc(r))

    def test_estimate_flag(self):
        """TASK-023 AC3: an estimate read-set gives one uncovered entry; a complete one gives none."""
        self.assertIn(('rule 3', 'read_set', 'the read-set is an estimate'), unc(stale.stale(inputs(read_set_estimate=True))))
        self.assertEqual(unc(stale.stale(inputs())), set())


class Order(unittest.TestCase):
    """R4."""

    def test_record_at_later_commit_not_stale(self):
        """TASK-023 AC4: a record bound to the meeting commit itself is not stale; one bound to an earlier base commit
        is."""
        recs = [{'record_id': 'late', 'commit': C2, 'intent_versions': {}},
                {'record_id': 'mid', 'commit': C1, 'intent_versions': {}}]
        self.assertEqual(stale.stale(inputs(records=recs))['stale']['commit'], ['mid'])

    def test_meeting_commit_before_record(self):
        """TASK-023 AC4: a meeting commit earlier than the record's commit does not make it stale."""
        bc = [{'commit': C1, 'paths': ['docs/a.md'], 'submitted_by_task': False},
              {'commit': C2, 'paths': ['src/x.py'], 'submitted_by_task': False}]
        recs = [{'record_id': 'r', 'commit': C2, 'intent_versions': {}}]
        self.assertEqual(stale.stale(inputs(base_commits=bc, records=recs))['stale']['commit'], [])

    def test_unknown_commit_stale_and_uncovered(self):
        """TASK-023 AC4: a record commit outside the accepted commit and the base commits is earlier than all, stale,
        and named "commit order not known"."""
        recs = [{'record_id': 'u', 'commit': OTHER, 'intent_versions': {}}]
        r = stale.stale(inputs(records=recs))
        self.assertEqual(r['stale']['commit'], ['u'])
        self.assertIn(('rule 3', 'u', 'commit order not known'), unc(r))

    def test_unknown_commit_without_meeting_commit(self):
        """TASK-023 AC4: with no meeting commit, an unknown record commit is uncovered but not stale."""
        recs = [{'record_id': 'u', 'commit': OTHER, 'intent_versions': {}}]
        r = stale.stale(inputs(records=recs, base_commits=[]))
        self.assertEqual(r['stale']['commit'], [])
        self.assertIn(('rule 3', 'u', 'commit order not known'), unc(r))


class Uncheckable(unittest.TestCase):
    """R5."""

    def test_no_intent_versions_and_no_commit(self):
        """TASK-023 AC5: a record with neither is uncovered for both rules and stale by neither."""
        r = stale.stale(inputs(records=[{'record_id': 'n'}], intent_current={'spec': 'v9'}))
        self.assertEqual(r['stale'], {'commit': [], 'intent_version': []})
        self.assertEqual(unc(r), {('rule 2', 'n', 'no intent_versions'), ('rule 3', 'n', 'no commit')})

    def test_empty_intent_versions_is_uncovered(self):
        """TASK-023 AC5: an empty intent_versions is uncovered for rule 2 like a missing one; a non-empty one is not."""
        r = stale.stale(inputs(records=[{'record_id': 'e', 'commit': ACC, 'intent_versions': {}}]))
        self.assertIn(('rule 2', 'e', 'no intent_versions'), unc(r))
        r = stale.stale(inputs(records=[{'record_id': 'e', 'commit': ACC, 'intent_versions': {'spec': 'v1'}}]))
        self.assertNotIn(('rule 2', 'e', 'no intent_versions'), unc(r))

    def test_checkable_record_not_uncovered(self):
        """TASK-023 AC5: a record with both fields gives no uncovered entry about itself."""
        self.assertFalse([u for u in stale.stale(inputs())['uncovered'] if u['ref'] == 'r1'])


class Events(unittest.TestCase):
    """R6."""

    def test_event_form_and_id(self):
        """TASK-023 AC6: one event per reason with stale ids, its id derived from the task, the trigger and the
        reason, and check_payload finds nothing."""
        r = stale.stale(inputs(intent_current={'spec': 'v2'}))
        self.assertEqual([e['payload']['reason'] for e in r['events']], ['commit', 'intent_version'])
        for e in r['events']:
            want = hashlib.sha256(('evidence.stale\n%s\n%s\n%s' % (T, C2, e['payload']['reason'])).encode('utf-8'))
            self.assertEqual(e['event_id'], want.hexdigest())
            self.assertEqual((e['event_type'], e['task_id']), ('evidence.stale', T))
            self.assertEqual(records.check_payload('evidence.stale', e['payload']), [])
            self.assertEqual(set(e), {'event_id', 'event_type', 'task_id', 'payload'})

    def test_dedup_by_reason(self):
        """TASK-023 AC6: ids an earlier event of the same reason listed are left out; another reason's do not count."""
        r = stale.stale(inputs(earlier_events=[{'reason': 'commit', 'records': ['r1']}]))
        self.assertEqual(r['events'], [])
        self.assertEqual(r['stale']['commit'], ['r1'])
        r = stale.stale(inputs(earlier_events=[{'reason': 'intent_version', 'records': ['r1']}]))
        self.assertEqual([e['payload']['records'] for e in r['events']], [['r1']])

    def test_no_event_when_nothing_stale(self):
        """TASK-023 AC6: nothing stale gives no event."""
        self.assertEqual(stale.stale(inputs(base_commits=[]))['events'], [])


class Result(unittest.TestCase):
    """R7."""

    def test_keys_sorting_and_no_duplicates(self):
        """TASK-023 AC8: the keys, the sorted lists and the uncovered entries without duplicates."""
        recs = [{'record_id': 'z'}, {'record_id': 'a', 'commit': ACC}, {'record_id': 'm', 'commit': ACC}]
        rs = [{'entry': 'x', 'kind': 'schema', 'patterns': None}, {'entry': 'x', 'kind': 'interface', 'patterns': None},
              {'entry': 'docs/a.md', 'kind': 'path', 'patterns': ['docs/a.md']}]
        r = stale.stale(inputs(records=recs, read_set=rs))
        self.assertEqual(set(r), {'stale', 'events', 'uncovered', 'error'})
        self.assertEqual(r['stale']['commit'], ['a', 'm'])
        keys = [(u['rule'], u['ref'], u['detail']) for u in r['uncovered']]
        self.assertEqual(keys, sorted(set(keys)))
        self.assertTrue(all(set(u) == {'rule', 'ref', 'detail'} for u in r['uncovered']))

    def test_purity(self):
        """TASK-023 AC8: the input is not changed and a second call gives an equal result."""
        x = inputs(intent_current={'spec': 'v2'}, read_set_estimate=True)
        before = copy.deepcopy(x)
        first = stale.stale(x)
        self.assertEqual(x, before)
        self.assertEqual(stale.stale(x), first)


class Module(unittest.TestCase):
    """R8."""

    def test_imports(self):
        """TASK-023 AC9: the module imports only hashlib, re and aieos_bootstrap.resume_check."""
        tree = ast.parse(SRC.read_bytes().decode('utf-8'))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.update('%s.%s' % (node.module, a.name) for a in node.names)
        self.assertEqual(names, {'hashlib', 're', 'aieos_bootstrap.resume_check'})

    def test_no_file_clock_or_dynamic_calls(self):
        """TASK-023 AC7 and AC9: no open, write, clock, environment, exec, eval, compile, __import__ or assert."""
        text = SRC.read_bytes().decode('utf-8')
        tree = ast.parse(text)
        called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertFalse(called & {'open', 'exec', 'eval', 'compile', '__import__'})
        self.assertFalse(attrs & {'write', 'write_text', 'write_bytes', 'time', 'now', 'environ', 'getenv', 'system'})
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Assert)])
        self.assertNotIn('importlib', text)
        self.assertNotIn('.aieos', text)

    def test_docstring_states_limits(self):
        """TASK-023 AC7 and AC11: the docstring names rule 1, DEF-0030, DEF-0042 point 10 and the caller's facts."""
        doc = ast.get_docstring(ast.parse(SRC.read_bytes().decode('utf-8')))
        for s in ('rule 1', 'DEF-0030', 'DEF-0042 point', 'appends nothing', 'not checked against Git'):
            self.assertIn(s, ' '.join(doc.split()))


if __name__ == '__main__':
    unittest.main()
