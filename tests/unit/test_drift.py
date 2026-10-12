"""Unit tests of aieos_bootstrap.drift (task TASK-030, its rules R1 to R8); every rule has at least one passing case and
one failing case. Each test names the criteria it stands for in its own docstring."""

import ast
import copy
import hashlib
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import drift, governor, records

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap' / 'drift.py'
C = 'a' * 40
OTHER = 'b' * 40
REC = 'aieos-core (test)'


def result(article, outcome, rid=None, commit=C, gate='G3', **over):
    """A rule result in the article-id form of specification 2 section 6.2."""
    r = {'record_id': rid or 'res-%s-%s' % (article, outcome), 'fact_kind': 'observation',
         'source_class': 'deterministic_tool_external_ci', 'recorder': 'ci', 'subject': C, 'commit': commit,
         'gate': gate, 'outcome': outcome, 'refers_to': article}
    r.update(over)
    return r


def inputs(**over):
    """A well-formed input: two articles whose scope meets src/x.py, one failing and one passing."""
    base = {
        'base_commit': C,
        'changed_paths': ['src/x.py', 'docs/a.md'],
        'articles': [{'id': 'SEC-001', 'scope': ['**'], 'evidence_required': ['secret_scan']},
                     {'id': 'INV-001', 'scope': ['src/**']},
                     {'id': 'GOV-001', 'scope': ['AIEOS-concept.md']}],
        'rule_results': [result('SEC-001', 'fail'), result('INV-001', 'pass')],
        'task_records': [],
        'recorder': REC,
    }
    base.update(over)
    return base


def unc(res):
    return {(u['ref'], u['detail']) for u in res['uncovered']}


def arts(res):
    return [e['payload']['refers_to'] for e in res['events']]


def digest(*parts):
    return hashlib.sha256('\n'.join(parts).encode('utf-8')).hexdigest()


class InputForm(unittest.TestCase):
    """R1."""

    def test_well_formed_has_no_error(self):
        """TASK-030 AC1 and TASK-030 AC13: a well-formed input gives error None, with a 40-character and with a
        64-character base commit."""
        self.assertIsNone(drift.violations(inputs())['error'])
        long_commit = 'c' * 64
        res = drift.violations(inputs(base_commit=long_commit,
                                      rule_results=[result('SEC-001', 'fail', commit=long_commit)]))
        self.assertIsNone(res['error'])
        self.assertEqual(res['events'][0]['payload']['commit'], long_commit)

    def test_each_malformed_form_names_its_key(self):
        """TASK-030 AC1 and TASK-030 AC8 and TASK-030 AC13: each malformed form gives an error naming its key, no event,
        no already entry and no uncovered entry."""
        cases = [
            ('base_commit', 'A' * 40), ('base_commit', 'a' * 39), ('base_commit', None),
            ('changed_paths', 'src/x.py'), ('changed_paths', ['src/x.py', 3]),
            ('articles', {'id': 'SEC-001'}), ('articles', [{'id': '', 'scope': []}]), ('articles', [{'id': 'SEC-001'}]),
            ('articles', [{'id': 'SEC-001', 'scope': []}, {'id': 'SEC-001', 'scope': []}]), ('articles', ['SEC-001']),
            ('rule_results', {}), ('rule_results', ['x']), ('task_records', None), ('task_records', [1]),
            ('recorder', ''), ('recorder', 7),
        ]
        for key, value in cases:
            res = drift.violations(inputs(**{key: value}))
            self.assertTrue(res['error'].startswith(key), (key, value, res['error']))
            self.assertEqual((res['events'], res['already'], res['uncovered']), ([], [], []))

    def test_missing_unknown_and_not_a_mapping(self):
        """TASK-030 AC1 and TASK-030 AC13: a missing key, an unknown key and a non-mapping input are errors."""
        i = inputs()
        del i['recorder']
        self.assertEqual(drift.violations(i)['error'], 'inputs lacks recorder')
        self.assertEqual(drift.violations(inputs(extra=1))['error'], 'inputs has an unknown key: extra')
        self.assertEqual(drift.violations([])['error'], 'inputs is not a mapping')

    def test_first_failing_key_in_order(self):
        """TASK-030 AC1 and TASK-030 AC13: with two malformed keys, the first in the order is named."""
        res = drift.violations(inputs(base_commit='x', recorder=''))
        self.assertTrue(res['error'].startswith('base_commit'))

    def test_a_malformed_entry_is_not_an_input_error(self):
        """TASK-030 AC1 and TASK-030 AC13: a malformed entry inside rule_results or task_records is no input error."""
        res = drift.violations(inputs(rule_results=[{'record_id': 'bad'}], task_records=[{'gate': 'G3'}]))
        self.assertIsNone(res['error'])


class Articles(unittest.TestCase):
    """R2."""

    def test_a_scope_met_and_one_not_met(self):
        """TASK-030 AC2 and TASK-030 AC13: SEC-001 and INV-001 apply; GOV-001's scope meets no changed path, so it gives
        no event and no uncovered entry."""
        res = drift.violations(inputs(rule_results=[result('SEC-001', 'fail'), result('INV-001', 'fail'),
                                                    result('GOV-001', 'fail')]))
        self.assertEqual(arts(res), ['INV-001', 'SEC-001'])
        self.assertNotIn('GOV-001', {u[0] for u in unc(res)})

    def test_a_scope_that_cannot_be_evaluated_applies(self):
        """TASK-030 AC2 and TASK-030 AC13: a scope that is not a non-empty list of non-empty strings applies and is
        uncovered."""
        for scope in (None, [], [''], 'src/**', ['src/**', 3]):
            res = drift.violations(inputs(articles=[{'id': 'OPS-001', 'scope': scope}],
                                          rule_results=[result('OPS-001', 'fail')]))
            self.assertEqual(arts(res), ['OPS-001'], scope)
            self.assertIn(('OPS-001', 'scope cannot be evaluated'), unc(res))

    def test_empty_changed_paths_meets_no_evaluable_scope(self):
        """TASK-030 AC2 and TASK-030 AC13: no changed path, no evaluable scope met, so no event and no uncovered entry
        for those articles."""
        res = drift.violations(inputs(changed_paths=[]))
        self.assertEqual(res['events'], [])
        self.assertEqual(res['uncovered'], [])

    def test_matching_is_the_governors(self):
        """TASK-030 AC2 and TASK-030 AC13: "*" does not cross "/" (governor.matches), so src/* does not meet
        src/a/b.py while src/** does."""
        one = drift.violations(inputs(changed_paths=['src/a/b.py'], articles=[{'id': 'INV-001', 'scope': ['src/*']}],
                                      rule_results=[result('INV-001', 'fail')]))
        two = drift.violations(inputs(changed_paths=['src/a/b.py'], articles=[{'id': 'INV-001', 'scope': ['src/**']}],
                                      rule_results=[result('INV-001', 'fail')]))
        self.assertEqual((arts(one), arts(two)), ([], ['INV-001']))

    def test_governor_matches_is_the_function_called(self):
        """TASK-030 AC2 and TASK-030 AC13: the selection goes through governor.matches itself: a stand-in that matches
        nothing removes every evaluable article, and the real function is called with (pattern, path) pairs."""
        calls = []
        real = governor.matches

        def spy(pattern, path):
            calls.append((pattern, path))
            return real(pattern, path)

        with mock.patch.object(governor, 'matches', spy):
            res = drift.violations(inputs())
        self.assertIn(('src/**', 'src/x.py'), calls)
        self.assertEqual(arts(res), ['SEC-001'])
        with mock.patch.object(governor, 'matches', lambda pattern, path: False):
            none = drift.violations(inputs())
        self.assertEqual((none['events'], none['uncovered']), ([], []))

    def test_other_article_keys_are_not_read(self):
        """TASK-030 AC2 and TASK-030 AC13: an applicability by task type does not stop an article from applying."""
        a = {'id': 'INV-001', 'scope': ['src/**'], 'applicability': {'task_types': ['refactoring']}}
        res = drift.violations(inputs(articles=[a], rule_results=[result('INV-001', 'fail')]))
        self.assertEqual(arts(res), ['INV-001'])


class RuleResults(unittest.TestCase):
    """R3."""

    def test_a_failing_result_gives_an_event_a_passing_one_does_not(self):
        """TASK-030 AC3 and TASK-030 AC13: SEC-001 fails, INV-001 passes."""
        res = drift.violations(inputs())
        self.assertEqual(arts(res), ['SEC-001'])
        self.assertNotIn('INV-001', {u[0] for u in unc(res)})

    def test_pass_and_fail_together_fail(self):
        """TASK-030 AC3 and TASK-030 AC13: one pass and one fail for the same article give an event."""
        res = drift.violations(inputs(rule_results=[result('INV-001', 'pass', 'p'), result('INV-001', 'fail', 'f'),
                                                    result('SEC-001', 'pass')]))
        self.assertEqual(arts(res), ['INV-001'])

    def test_no_result_is_uncovered_never_passed(self):
        """TASK-030 AC3 and TASK-030 AC13: an applicable article with no result gives an uncovered entry and no
        event."""
        res = drift.violations(inputs(rule_results=[result('SEC-001', 'pass')]))
        self.assertEqual(res['events'], [])
        self.assertIn(('INV-001', 'no rule result'), unc(res))

    def test_a_result_for_another_commit_gate_or_article_is_no_result(self):
        """TASK-030 AC3 and TASK-030 AC4 and TASK-030 AC13: a failing result for another commit or gate is not usable,
        and one for another article is not read."""
        for r in (result('SEC-001', 'fail', commit=OTHER), result('SEC-001', 'fail', gate='G2'),
                  result('SEC-009', 'fail')):
            res = drift.violations(inputs(rule_results=[r, result('INV-001', 'pass')]))
            self.assertEqual(res['events'], [], r)
            self.assertIn(('SEC-001', 'no rule result'), unc(res))

    def test_a_result_for_an_article_that_does_not_apply_is_not_read(self):
        """TASK-030 AC3 and TASK-030 AC13: GOV-001 does not apply; its failing result gives nothing."""
        res = drift.violations(inputs(rule_results=[result('SEC-001', 'pass'), result('INV-001', 'pass'),
                                                    result('GOV-001', 'fail')]))
        self.assertEqual((res['events'], res['uncovered']), ([], []))


class UnusableResults(unittest.TestCase):
    """R4."""

    def test_each_unusable_form_is_named(self):
        """TASK-030 AC4 and TASK-030 AC13: a result that check_record refuses, that is not an observation, that is not
        G3, not this commit, or whose outcome is not pass or fail is named by its record_id and counts as no result."""
        bad = [
            result('SEC-001', 'fail', 'u1', fact_kind='claim'),
            result('SEC-001', 'fail', 'u2', gate=None),
            result('SEC-001', 'fail', 'u3', commit=OTHER),
            result('SEC-001', 'blocking', 'u4', blocking_kind='violation'),
            result('SEC-001', 'fail', 'u5', unknown_key=1),
            result('SEC-001', 'fail', 'u6', source_class='nowhere'),
        ]
        for r in bad:
            res = drift.violations(inputs(rule_results=[r, result('INV-001', 'pass')]))
            self.assertIn((r['record_id'], 'not a usable rule result'), unc(res), r)
            self.assertIn(('SEC-001', 'no rule result'), unc(res), r)
            self.assertEqual(res['events'], [], r)

    def test_named_by_index_without_a_record_id(self):
        """TASK-030 AC4 and TASK-030 AC13: an entry with no non-empty string record_id is named by its index."""
        res = drift.violations(inputs(rule_results=[result('INV-001', 'pass'), {'outcome': 'fail'},
                                                    dict(result('SEC-001', 'fail'), record_id='')]))
        self.assertIn(('rule_results[1]', 'not a usable rule result'), unc(res))
        self.assertIn(('rule_results[2]', 'not a usable rule result'), unc(res))

    def test_a_usable_result_is_not_named(self):
        """TASK-030 AC4 and TASK-030 AC13: the usable results of the base input give no such entry."""
        self.assertFalse([u for u in unc(drift.violations(inputs())) if u[1] == 'not a usable rule result'])

    def test_a_usable_form_without_refers_to_is_not_named_and_counts_for_no_article(self):
        """TASK-030 AC3 and TASK-030 AC4 and TASK-030 AC13: refers_to aside, the form is usable, so it is not named; it
        names no article, so SEC-001 has no result."""
        r = result('SEC-001', 'fail')
        del r['refers_to']
        res = drift.violations(inputs(rule_results=[r, result('INV-001', 'pass')]))
        self.assertNotIn((r['record_id'], 'not a usable rule result'), unc(res))
        self.assertIn(('SEC-001', 'no rule result'), unc(res))


class OneFinding(unittest.TestCase):
    """R5."""

    def test_a_matching_task_record_gives_no_event(self):
        """TASK-030 AC5 and TASK-030 AC13: the task's own failing G3 record for SEC-001 at this commit suppresses the
        event, and SEC-001 is listed in already."""
        res = drift.violations(inputs(task_records=[result('SEC-001', 'fail', 'task-g3')]))
        self.assertEqual((res['events'], res['already']), ([], ['SEC-001']))

    def test_a_record_differing_in_gate_article_commit_or_outcome_does_not_match(self):
        """TASK-030 AC5 and TASK-030 AC13: each difference leaves the event in place."""
        for r in (result('SEC-001', 'fail', gate='G2'), result('INV-001', 'fail'),
                  result('SEC-001', 'fail', commit=OTHER), result('SEC-001', 'pass')):
            res = drift.violations(inputs(task_records=[r]))
            self.assertEqual((arts(res), res['already']), (['SEC-001'], []), r)

    def test_a_malformed_or_non_observation_record_does_not_match(self):
        """TASK-030 AC5 and TASK-030 AC13: a record otherwise matching but malformed, or not an observation, does not
        match and the event is given (fail closed)."""
        for r in (result('SEC-001', 'fail', fact_kind='claim'), result('SEC-001', 'fail', unknown_key=1),
                  result('SEC-001', 'fail', source_class='nowhere')):
            res = drift.violations(inputs(task_records=[r]))
            self.assertEqual((arts(res), res['already']), (['SEC-001'], []), r)

    def test_a_task_record_alone_gives_nothing(self):
        """TASK-030 AC5 and TASK-030 AC13: a task record for a passing article does not make it fail or list it."""
        res = drift.violations(inputs(task_records=[result('INV-001', 'fail')]))
        self.assertEqual((arts(res), res['already']), (['SEC-001'], []))


class Events(unittest.TestCase):
    """R6."""

    def test_payload_keys_values_and_ids(self):
        """TASK-030 AC6 and TASK-030 AC13: the payload's exact keys and values, the record id and the event id."""
        [e] = drift.violations(inputs())['events']
        self.assertEqual(set(e), {'event_id', 'event_type', 'payload'})
        self.assertEqual(e['event_type'], 'violation.detected')
        self.assertEqual(e['event_id'], digest('violation.detected', C, 'SEC-001'))
        self.assertEqual(e['payload'], {
            'record_id': digest('violation', C, 'SEC-001'), 'fact_kind': 'observation',
            'source_class': 'deterministic_tool_local', 'recorder': REC, 'subject': C, 'commit': C,
            'outcome': 'blocking', 'blocking_kind': 'violation', 'refers_to': 'SEC-001'})

    def test_check_payload_finds_nothing_and_no_task_id(self):
        """TASK-030 AC6 and TASK-030 AC13: records.check_payload finds nothing in each payload, and no event carries a
        task_id; a payload changed to break the form is found."""
        res = drift.violations(inputs(rule_results=[result('SEC-001', 'fail'), result('INV-001', 'fail')]))
        for e in res['events']:
            self.assertEqual(records.check_payload('violation.detected', e['payload']), [])
            self.assertNotIn('task_id', e)
        broken = dict(res['events'][0]['payload'], outcome='fail')
        self.assertTrue(records.check_payload('violation.detected', broken))

    def test_events_sorted_and_ids_stable(self):
        """TASK-030 AC6 and TASK-030 AC13: events sorted by article id; the same inputs give the same ids, another
        commit other ids."""
        i = inputs(rule_results=[result('SEC-001', 'fail'), result('INV-001', 'fail')])
        a, b = drift.violations(i), drift.violations(copy.deepcopy(i))
        self.assertEqual(arts(a), ['INV-001', 'SEC-001'])
        self.assertEqual([e['event_id'] for e in a['events']], [e['event_id'] for e in b['events']])
        j = inputs(base_commit=OTHER, rule_results=[result('SEC-001', 'fail', commit=OTHER), result('INV-001', 'pass',
                                                                                                    commit=OTHER)])
        self.assertNotEqual(drift.violations(j)['events'][0]['event_id'], a['events'][1]['event_id'])


class Result(unittest.TestCase):
    """R7."""

    def test_keys_sorting_and_no_duplicates(self):
        """TASK-030 AC8 and TASK-030 AC13: exactly the four keys; uncovered sorted by (ref, detail), no duplicate."""
        res = drift.violations(inputs(articles=[{'id': 'Z-1', 'scope': None}, {'id': 'A-1', 'scope': None}],
                                      rule_results=[{'record_id': 'x'}, {'record_id': 'x'}]))
        self.assertEqual(set(res), {'events', 'already', 'uncovered', 'error'})
        pairs = [(u['ref'], u['detail']) for u in res['uncovered']]
        self.assertEqual(pairs, sorted(set(pairs)))
        self.assertTrue(all(set(u) == {'ref', 'detail'} for u in res['uncovered']))

    def test_pure(self):
        """TASK-030 AC8 and TASK-030 AC13: the input is not changed and a second call is equal; a changed input gives
        another result."""
        i = inputs(task_records=[result('INV-001', 'fail')])
        before = copy.deepcopy(i)
        first = drift.violations(i)
        self.assertEqual(i, before)
        self.assertEqual(drift.violations(i), first)
        self.assertNotEqual(drift.violations(inputs(rule_results=[])), first)


class Purity(unittest.TestCase):
    """R8."""

    def test_imports(self):
        """TASK-030 AC9 and TASK-030 AC13: the module imports only hashlib, re, aieos_bootstrap.governor and
        aieos_bootstrap.records."""
        tree = ast.parse(SRC.read_bytes().decode('utf-8'))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.update('%s.%s' % (node.module, a.name) for a in node.names)
        self.assertEqual(names, {'hashlib', 're', 'aieos_bootstrap.governor', 'aieos_bootstrap.records'})

    def test_no_file_clock_or_dynamic_calls(self):
        """TASK-030 AC7 and TASK-030 AC9 and TASK-030 AC13: no open, write, clock, environment, exec, eval, compile,
        __import__ or assert; a seeded call is found by the same check."""
        text = SRC.read_bytes().decode('utf-8')

        def found(source):
            tree = ast.parse(source)
            called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
            attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            return (called & {'open', 'exec', 'eval', 'compile', '__import__'}
                    or attrs & {'write', 'write_text', 'write_bytes', 'time', 'now', 'environ', 'getenv', 'system'}
                    or [n for n in ast.walk(tree) if isinstance(n, ast.Assert)])

        self.assertFalse(found(text))
        self.assertTrue(found(text + '\nopen("x")\n'))
        self.assertNotIn('importlib', text)
        self.assertNotIn('.aieos', text)

    def test_docstring_states_limits(self):
        """TASK-030 AC7 and TASK-030 AC11 and TASK-030 AC13: the docstring names the caller TASK-031, the step
        mapping, the non-fast-forward limit, and that nothing is appended or run."""
        doc = ' '.join(ast.get_docstring(ast.parse(SRC.read_bytes().decode('utf-8'))).split())
        for s in ('TASK-031', 'maps the CI\'s steps to article ids', 'not a fast-forward', 'appends nothing',
                  'runs no rule', 'no scope-drift or stale-evidence finding', 'not checked against Git'):
            self.assertIn(s, doc)


if __name__ == '__main__':
    unittest.main()
