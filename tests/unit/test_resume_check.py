"""Unit tests of the Resume Check (TASK-008 AC14, rules R1 to R7 and R9): every input is built in memory."""
import copy
import hashlib
import itertools
import re
import sys
import unittest

from aieos_bootstrap import records, resume_check as rc

BASE = '1' * 40
HEAD = '2' * 40
OTHER = '3' * 40
H = 'a' * 64


def inputs(**over):
    """Well-formed inputs whose checks all pass (CONTINUE): one commit changes a path that meets nothing."""
    inp = {
        'task_id': 'TASK-100', 'log_seq': 7, 'task_state': 'IN_PROGRESS',
        'contract': {
            'task': 'TASK-100', 'contract_version': 'v1', 'task_type': 'implementation', 'risk': 'medium',
            'input_state': {'base_commit': BASE, 'depends_on': ['TASK-099'], 'intent_versions': {'SPEC-003': 'v4'}},
            'write_set': {'paths': ['src/app/core/**']},
            'read_set': {'paths': ['src/app/util/helpers.py'], 'interfaces': ['load_policy'], 'schemas': ['record']},
            'constitution': ['INV-001'],
            'autonomy': {'budgets': {'retries': 2, 'tokens': '400k', 'wall_time': '2h', 'human_attention': '10m'}}},
        'contract_hash': H, 'approved_contract_hash': H, 'head_commit': HEAD, 'base_is_ancestor': True,
        'commits': [{'id': OTHER, 'paths': [{'path': 'docs/notes.md', 'change': 'modified'}], 'submitted': False}],
        'components': [{'id': 'CMP-API', 'paths': ['src/app/api/**'], 'tags': []},
                       {'id': 'CMP-CORE', 'paths': ['src/app/core'], 'tags': []}],
        'interfaces': [{'id': 'load_policy', 'component': 'CMP-API'}],
        'symbols': [{'interface': 'load_policy', 'base': 'F(a)', 'head': 'F(a)'}],
        'schemas': [{'name': 'record', 'base': {'path': 'src/app/api/record.json', 'sha256': 'b' * 64},
                     'head': {'path': 'src/app/api/record.json', 'sha256': 'b' * 64}}],
        'derived_read_set': [], 'observed_read_set': [],
        'intent_current': {'SPEC-003': 'v4'},
        'dependencies': {'TASK-099': {'state': 'DONE', 'stale_evidence': False}},
        'articles': [{'id': 'INV-001', 'scope': {'paths': ['src/**'], 'components': []},
                      'applicability': {'task_types': ['implementation']}, 'violated': False}],
        'runtime': {'adapter': 'an-adapter', 'max_risk': 'high'},
        'risk_rules': [{'match': {'paths': ['src/**']}, 'risk': 'medium'}],
        'policy_version': 'v2',
        'budget_use': {'retries': {'used': 0, 'reported': True}, 'tokens': {'used': '10k', 'reported': True},
                       'wall_time': {'used': '10m', 'reported': True}, 'human_attention': {'used': '0m', 'reported': True}},
    }
    inp.update(over)
    return inp


def changed(*paths, change='modified'):
    return [{'id': OTHER, 'paths': [{'path': p, 'change': change} for p in paths], 'submitted': False}]


def status(rec, n):
    c = rec['checks'][n - 1]
    return c['status'], c['outcome']


class R1Inputs(unittest.TestCase):
    def test_the_well_formed_inputs_give_continue(self):
        rec = rc.check(inputs())
        self.assertEqual(rec['decision'], 'CONTINUE')
        self.assertNotIn('error', rec)

    def test_each_missing_key_gives_error(self):
        for key in sorted(rc.INPUT_KEYS):
            inp = inputs()
            del inp[key]
            rec = rc.check(inp)
            self.assertIsNone(rec['decision'], key)
            self.assertIn(key, rec['error'])

    def test_malformed_values_give_error(self):
        bad = {'task_id': 'T-1', 'log_seq': True, 'task_state': 'DONE', 'contract_hash': 'x', 'head_commit': 'abc',
               'base_is_ancestor': 'yes', 'commits': [{'id': OTHER}], 'components': 3, 'interfaces': [{}],
               'symbols': [{'interface': 'x', 'base': 1, 'head': None}], 'schemas': [{'name': 'r', 'base': 2, 'head': None}],
               'derived_read_set': [1], 'observed_read_set': 'x', 'intent_current': {'S': 3},
               'dependencies': {'T': {'state': 'DONE'}}, 'articles': [{'id': 'A'}],
               'runtime': {'adapter': 'a', 'max_risk': 'huge'}, 'risk_rules': [3], 'policy_version': 4,
               'budget_use': {'retries': {'used': 1}}, 'contract': {'risk': 'medium'}}
        for key, value in bad.items():
            rec = rc.check(inputs(**{key: value}))
            self.assertIsNone(rec['decision'], key)
            self.assertIn('error', rec, key)

    def test_an_extra_key_and_a_non_object_give_error(self):
        self.assertIsNone(rc.check(dict(inputs(), extra=1))['decision'])
        for value in (None, [], 'x', 3, 1.5):
            rec = rc.check(value)
            self.assertIsNone(rec['decision'])
            self.assertEqual(records.check_decision('decision.execution', rec), [])

    def test_uncovered_cases_are_not_errors(self):
        rec = rc.check(inputs(observed_read_set=None,
                              budget_use=dict(inputs()['budget_use'], tokens={'used': 'lots', 'reported': True},
                                              wall_time={'used': '10m', 'reported': False})))
        self.assertEqual(rec['decision'], 'CONTINUE')
        self.assertTrue(rec['read_set']['estimate'])
        self.assertTrue(any('tokens' in u for u in rec['uncovered']))
        self.assertTrue(any('wall_time' in u for u in rec['uncovered']))

    def test_the_inputs_are_not_changed(self):
        inp = inputs(commits=changed('src/app/core/x.py'))
        before = copy.deepcopy(inp)
        rc.check(inp)
        self.assertEqual(inp, before)

    def test_check_0_differing_hash_gives_error(self):
        rec = rc.check(inputs(approved_contract_hash='c' * 64))
        self.assertIsNone(rec['decision'])
        self.assertIn('check 0', rec['error'])

    def test_a_bad_code_sha256_gives_error(self):
        self.assertIsNone(rc.check(inputs(), code_sha256='xyz')['decision'])

    def test_log_seq_bound(self):
        # decision D-361, reading R-a: an integer from 0 to 2**63 - 1; beyond it an error record, never a raise
        self.assertEqual(rc.check(inputs(log_seq=2 ** 63 - 1))['decision'], 'CONTINUE')
        for value in (2 ** 63, 10 ** 5000):
            rec = rc.check(inputs(log_seq=value))
            self.assertIsNone(rec['decision'])
            self.assertIn('log_seq', rec['error'])
            self.assertEqual(records.check_decision('decision.execution', rec), [])


class R2Checks(unittest.TestCase):
    def test_check_1_equal_skips_2_and_3(self):
        rec = rc.check(inputs(head_commit=BASE))
        self.assertEqual([status(rec, 2)[0], status(rec, 3)[0]], ['skipped', 'skipped'])
        self.assertEqual(rec['decision'], 'CONTINUE')

    def test_check_1_not_an_ancestor_escalates(self):
        rec = rc.check(inputs(base_is_ancestor=False))
        self.assertEqual(status(rec, 1), ('fired', 'ESCALATE'))
        self.assertEqual([status(rec, 2)[0], status(rec, 3)[0]], ['not_run', 'not_run'])
        self.assertEqual(rec['decision'], 'ESCALATE')

    def test_check_1_submitted_commits_are_left_out(self):
        commits = changed('src/app/core/x.py')
        commits[0]['submitted'] = True
        rec = rc.check(inputs(commits=commits))
        self.assertEqual(rec['delta'], [])
        self.assertEqual(rec['decision'], 'CONTINUE')

    def test_check_1_last_change_wins(self):
        commits = changed('docs/a.md', change='added') + [{'id': BASE, 'paths': [{'path': 'docs/a.md', 'change': 'deleted'}],
                                                           'submitted': False}]
        self.assertEqual(rc.check(inputs(commits=commits))['delta'], [{'path': 'docs/a.md', 'change': 'deleted'}])

    def test_check_2_fires_and_passes(self):
        self.assertEqual(status(rc.check(inputs(commits=changed('src/app/core/x.py'))), 2), ('fired', 'STOP: scope invalid'))
        self.assertEqual(status(rc.check(inputs()), 2), ('passed', None))

    def test_check_3_continue_with_and_replan(self):
        self.assertEqual(status(rc.check(inputs(commits=changed('src/app/util/helpers.py'))), 3), ('fired', 'CONTINUE_WITH'))
        syms = [{'interface': 'load_policy', 'base': 'F(a)', 'head': 'F(a, b)'}]
        rec = rc.check(inputs(commits=changed('src/app/api/policy.py'), symbols=syms))
        self.assertEqual(status(rec, 3), ('fired', 'REPLAN'))
        self.assertEqual(status(rc.check(inputs(commits=changed('src/app/api/policy.py'))), 3), ('fired', 'CONTINUE_WITH'))

    def test_check_4(self):
        self.assertEqual(status(rc.check(inputs(intent_current={'SPEC-003': 'v5'})), 4), ('fired', 'REPLAN'))
        self.assertEqual(status(rc.check(inputs(intent_current={})), 4), ('fired', 'REPLAN'))
        self.assertEqual(status(rc.check(inputs()), 4), ('passed', None))

    def test_check_5(self):
        for dep in ({'state': 'READY', 'stale_evidence': False}, {'state': 'STALE', 'stale_evidence': False},
                    {'state': None, 'stale_evidence': False}):
            rec = rc.check(inputs(dependencies={'TASK-099': dep}))
            self.assertEqual(status(rec, 5), ('fired', 'BLOCKED'), dep)
        self.assertEqual(status(rc.check(inputs(dependencies={})), 5), ('fired', 'BLOCKED'))
        rec = rc.check(inputs(dependencies={'TASK-099': {'state': 'DONE', 'stale_evidence': True}}))
        self.assertEqual(status(rec, 5), ('passed', None))

    def test_check_6(self):
        art = inputs()['articles'][0]
        self.assertEqual(status(rc.check(inputs(articles=[dict(art, violated=True)])), 6), ('fired', 'ESCALATE'))
        rec = rc.check(inputs(articles=[dict(art, violated=None)]))
        self.assertEqual(status(rec, 6), ('passed', None))
        self.assertEqual(rec['constitution']['no_result'], ['INV-001'])
        other = {'id': 'OPS-001', 'scope': {'paths': ['docs/**'], 'components': []}, 'applicability': None, 'violated': True}
        contract = dict(inputs()['contract'], constitution=[])
        rec = rc.check(inputs(contract=contract, articles=[other]))
        self.assertEqual(rec['constitution']['applicable'], [])
        rec = rc.check(inputs(contract=contract, articles=[dict(other, scope={'paths': [], 'components': ['CMP-NONE']})]))
        self.assertEqual(status(rec, 6), ('fired', 'ESCALATE'))
        rec = rc.check(inputs(contract=contract, articles=[dict(other, scope=None)]))
        self.assertEqual(rec['constitution']['applicable'], [])
        rec = rc.check(inputs(contract=contract, articles=[dict(other, scope={'paths': [], 'components': ['CMP-CORE']},
                                                                  applicability={'task_types': ['fixture']})]))
        self.assertEqual(rec['constitution']['applicable'], [])
        rec = rc.check(inputs(contract=contract, articles=[dict(other, scope={'paths': [], 'components': ['CMP-CORE']})]))
        self.assertEqual(status(rec, 6), ('fired', 'ESCALATE'))

    def test_check_7(self):
        self.assertEqual(status(rc.check(inputs(runtime={'adapter': 'a', 'max_risk': 'low'})), 7),
                         ('fired', 'STOP: runtime insufficient'))
        self.assertEqual(status(rc.check(inputs(runtime={'adapter': 'a', 'max_risk': None})), 7),
                         ('fired', 'STOP: runtime insufficient'))
        self.assertEqual(status(rc.check(inputs(risk_rules=[{'match': {'paths': ['docs/**']}, 'risk': 'low'}])), 7),
                         ('fired', 'ESCALATE'))
        rec = rc.check(inputs(risk_rules=[{'match': {'paths': ['src/app/**']}, 'risk': 'critical'}]))
        self.assertEqual(rec['runtime']['task_risk'], 'critical')
        self.assertEqual(status(rec, 7), ('fired', 'STOP: runtime insufficient'))
        self.assertEqual(status(rc.check(inputs()), 7), ('passed', None))

    def test_check_8(self):
        use = inputs()['budget_use']
        self.assertEqual(status(rc.check(inputs(budget_use=dict(use, retries={'used': 2, 'reported': True}))), 8),
                         ('passed', None))
        self.assertEqual(status(rc.check(inputs(budget_use=dict(use, retries={'used': 3, 'reported': True}))), 8),
                         ('fired', 'ESCALATE'))
        self.assertEqual(status(rc.check(inputs(budget_use=dict(use, tokens={'used': '401k', 'reported': True}))), 8),
                         ('fired', 'ESCALATE'))
        self.assertEqual(status(rc.check(inputs(budget_use=dict(use, wall_time={'used': '3h', 'reported': True}))), 8),
                         ('fired', 'ESCALATE'))
        rec = rc.check(inputs(budget_use=dict(use, wall_time={'used': '3h', 'reported': False})))
        self.assertEqual(status(rec, 8), ('passed', None))
        self.assertTrue(any('wall_time' in u for u in rec['uncovered']))

    def test_every_check_runs_after_one_fires(self):
        rec = rc.check(inputs(base_is_ancestor=False, intent_current={}, runtime={'adapter': 'a', 'max_risk': 'low'}))
        self.assertEqual(rec['outcomes_fired'], ['STOP: runtime insufficient', 'ESCALATE', 'REPLAN'])
        self.assertEqual(len(rec['checks']), 8)


class R3Patterns(unittest.TestCase):
    def test_matches(self):
        for pattern, path, want in (('src/**', 'src/a/b.py', True), ('src/*.py', 'src/a/b.py', False),
                                    ('*.py', 'src/a/b.py', True), ('src/a/*', 'src/a/b.py', True),
                                    ('docs/**', 'src/a.py', False), ('**/b.py', 'b.py', True)):
            self.assertEqual(rc.matches(pattern, path), want, (pattern, path))

    def test_meet(self):
        for a, b, want in (('src/**', 'src/app/**', True), ('src/*.py', 'src/x.py', True), ('src/*', 'docs/*', False),
                           ('a/*/c', 'a/b*/c', True), ('x.py', 'src/**', True), ('docs/a.md', 'docs/b.md', False)):
            self.assertEqual(rc.meet(a, b), want, (a, b))

    def test_fail_closed_on_an_undecidable_pattern(self):
        self.assertTrue(rc.meet(None, 'src/a.py'))

    def test_many_stars_in_one_name_end_quickly(self):
        # way-2 review R3 (decision D-361): a regular expression would backtrack for a very long time here
        pattern = 'x/' + '*a' * 40 + '*b'
        self.assertFalse(rc.meet(pattern, 'x/' + 'a' * 200))
        self.assertTrue(rc.meet(pattern, 'x/' + 'a' * 200 + 'b'))

    def test_the_name_match_equals_the_regular_expression_on_small_cases(self):
        # decision D-361 C2 (c): every pattern up to 6 characters over a, b and *, against every name up to 6
        # characters over a and b, as the earlier construction with one "[^/]*" per star decided it
        def names(alphabet):
            for size in range(7):
                for t in itertools.product(alphabet, repeat=size):
                    yield ''.join(t)
        plain = list(names('ab'))
        for pattern in names('ab*'):
            if '*' not in pattern:
                continue
            rx = re.compile(''.join('[^/]*' if ch == '*' else re.escape(ch) for ch in pattern))
            for name in plain:
                self.assertEqual(rc._names_meet(pattern, name), rx.fullmatch(name) is not None, (pattern, name))

    def test_a_folder_component_stands_for_its_files(self):
        art = {'id': 'GOV-9', 'scope': {'paths': [], 'components': ['CMP-CORE']}, 'applicability': None, 'violated': True}
        contract = dict(inputs()['contract'], constitution=[], write_set={'paths': ['src/app/core/x.py']})
        rec = rc.check(inputs(contract=contract, articles=[art],
                              risk_rules=[{'match': {'paths': ['src/**']}, 'risk': 'medium'}]))
        self.assertEqual(rec['constitution']['applicable'], ['GOV-9'])


class R4ReadSet(unittest.TestCase):
    def verdict(self, rec, entry):
        return [(s['verdict'], s['reason']) for s in rec['signatures'] if s['entry'] == entry][0][0]

    def test_path_interface_and_schema_verdicts(self):
        rec = rc.check(inputs(commits=changed('src/app/util/helpers.py')))
        self.assertEqual(self.verdict(rec, 'src/app/util/helpers.py'), 'non_breaking')
        for sym, want in ((('F', 'F'), 'non_breaking'), (('F', 'G'), 'breaking'), ((None, 'F'), 'breaking'),
                          (('ambiguous', 'ambiguous'), 'breaking')):
            rec = rc.check(inputs(commits=changed('src/app/api/policy.py'),
                                  symbols=[{'interface': 'load_policy', 'base': sym[0], 'head': sym[1]}]))
            self.assertEqual(self.verdict(rec, 'load_policy'), want, sym)
        same = {'path': 'src/app/api/record.json', 'sha256': 'b' * 64}
        for head, want in ((same, 'non_breaking'), (dict(same, sha256='c' * 64), 'breaking')):
            rec = rc.check(inputs(commits=changed('src/app/api/record.json'),
                                  schemas=[{'name': 'record', 'base': same, 'head': head}]))
            self.assertEqual(self.verdict(rec, 'record'), want)

    def test_unresolvable_entries_are_breaking(self):
        rec = rc.check(inputs(interfaces=[], schemas=[]))
        self.assertEqual(self.verdict(rec, 'load_policy'), 'breaking')
        self.assertEqual(self.verdict(rec, 'record'), 'breaking')
        self.assertEqual(rec['decision'], 'REPLAN')
        self.assertEqual(rec['read_set']['unresolved'], ['load_policy', 'record'])

    def test_sources_and_the_estimate(self):
        rec = rc.check(inputs(derived_read_set=['src/app/util/helpers.py'], observed_read_set=None))
        entry = [e for e in rec['read_set']['entries'] if e['entry'] == 'src/app/util/helpers.py'][0]
        self.assertEqual(entry['sources'], ['declared', 'derived'])
        self.assertTrue(rec['read_set']['estimate'])
        self.assertFalse(rc.check(inputs())['read_set']['estimate'])


class R5Order(unittest.TestCase):
    def test_every_pair_gives_the_earlier(self):
        use = inputs()['budget_use']
        makers = {
            'STOP: scope invalid': {'commits': ['src/app/core/x.py']},
            'STOP: runtime insufficient': {'runtime': {'adapter': 'a', 'max_risk': 'low'}},
            'ESCALATE': {'budget_use': dict(use, retries={'used': 9, 'reported': True})},
            'BLOCKED': {'dependencies': {}},
            'REPLAN': {'intent_current': {}},
            'CONTINUE_WITH': {'commits': ['src/app/util/helpers.py']},
        }
        for a, b in itertools.combinations(list(makers), 2):
            over, paths = {}, []
            for m in (makers[a], makers[b]):
                for k, v in m.items():
                    if k == 'commits':
                        paths += v
                    else:
                        over[k] = v
            if paths:
                over['commits'] = changed(*paths)
            rec = rc.check(inputs(**over))
            self.assertEqual(rec['decision'], a, (a, b, rec['outcomes_fired']))
            self.assertEqual(rec['outcomes_fired'][:2], [a, b], (a, b))

    def test_never_stop_violation(self):
        self.assertNotIn('STOP: violation', rc.check(inputs(base_is_ancestor=False))['outcomes_fired'])


def all_decisions():
    use = inputs()['budget_use']
    return {
        'CONTINUE': inputs(),
        'CONTINUE_WITH': inputs(commits=changed('src/app/util/helpers.py')),
        'REPLAN': inputs(commits=changed('src/app/api/policy.py'),
                         symbols=[{'interface': 'load_policy', 'base': 'F', 'head': 'G'}]),
        'BLOCKED': inputs(dependencies={}),
        'ESCALATE': inputs(budget_use=dict(use, retries={'used': 5, 'reported': True})),
        'STOP: scope invalid': inputs(commits=changed('src/app/core/x.py')),
        'STOP: runtime insufficient': inputs(runtime={'adapter': 'a', 'max_risk': None}),
    }


class R6Records(unittest.TestCase):
    def test_no_check_decision_finding_for_every_decision_and_an_error(self):
        for want, inp in all_decisions().items():
            for code in (None, 'f' * 64):
                rec = rc.check(inp, code_sha256=code)
                self.assertEqual(rec['decision'], want)
                self.assertEqual(records.check_decision('decision.execution', rec), [], want)
        for inp in (inputs(approved_contract_hash='c' * 64), inputs(task_id=5), {}):
            rec = rc.check(inp)
            self.assertEqual(records.check_decision('decision.execution', rec), [])

    def test_the_subject_of_an_error_record(self):
        # decision D-359, E1: "TASK-0" exactly when task_id is missing or malformed, named in uncovered
        line = 'subject: task_id is malformed, so TASK-0 stands for it (decision D-359)'
        missing = inputs()
        del missing['task_id']
        for inp in (missing, inputs(task_id='T-1'), inputs(task_id=5)):
            rec = rc.check(inp)
            self.assertIsNone(rec['decision'])
            self.assertEqual(rec['subject'], 'TASK-0')
            self.assertIn(line, rec['uncovered'])
        rec = rc.check(inputs(log_seq=True))
        self.assertIsNone(rec['decision'])
        self.assertEqual(rec['subject'], 'TASK-100')
        self.assertNotIn(line, rec['uncovered'])

    def test_the_record_keys(self):
        rec = rc.check(inputs())
        want = set(records.RECORD_REQUIRED) | {'decision'} | set(records.EXECUTION_KEYS) - {'intent_versions'} | {'intent_versions'}
        self.assertEqual(set(rec) - {'error'}, want)
        self.assertEqual(rec['fact_kind'], 'interpretation')
        self.assertEqual(rec['source_class'], 'deterministic_tool_local')
        self.assertEqual(rec['subject'], 'TASK-100')


class R7IdsAndEffects(unittest.TestCase):
    def test_the_ids_formula(self):
        rec = rc.check(inputs(), code_sha256='f' * 64)
        text = '\n'.join(['TASK-100', '7', HEAD, 'f' * 64, 'decision.execution'])
        self.assertEqual(rec['record_id'], hashlib.sha256(text.encode('utf-8')).hexdigest())
        no_code = rc.check(inputs())
        text = '\n'.join(['TASK-100', '7', HEAD, '', 'decision.execution'])
        self.assertEqual(no_code['record_id'], hashlib.sha256(text.encode('utf-8')).hexdigest())
        self.assertNotEqual(rc.check(inputs(log_seq=8))['record_id'], no_code['record_id'])

    def test_engine_identity(self):
        v = sys.version_info
        rec = rc.check(inputs())
        self.assertEqual(rec['engine_identity'], {'code_sha256': None, 'python': '%d.%d.%d' % (v[0], v[1], v[2])})
        self.assertTrue(any('code_sha256' in u for u in rec['uncovered']))
        rec = rc.check(inputs(), code_sha256='f' * 64)
        self.assertEqual(rec['engine_identity']['code_sha256'], 'f' * 64)
        self.assertFalse(any('code_sha256' in u for u in rec['uncovered']))

    def test_the_events_per_decision(self):
        types = {d: [e['type'] for e in rc.check(i)['state_effect']] for d, i in all_decisions().items()}
        self.assertEqual(types, {'CONTINUE': [], 'CONTINUE_WITH': [], 'REPLAN': ['conflict.detected', 'task.stale'],
                                 'BLOCKED': ['task.blocked'], 'ESCALATE': ['task.blocked'],
                                 'STOP: scope invalid': ['conflict.detected', 'task.blocked'],
                                 'STOP: runtime insufficient': []})
        rec = rc.check(all_decisions()['REPLAN'])
        conflict, stale = rec['state_effect']
        self.assertEqual(stale['payload'], {'cause': 'conflict', 'refers_to': conflict['event_id']})
        self.assertEqual(conflict['payload']['tasks'], [])
        esc = rc.check(all_decisions()['ESCALATE'])
        self.assertEqual(esc['state_effect'][0]['payload'], {'reason': 'escalate', 'blocked_by': [esc['record_id']]})
        stop = rc.check(all_decisions()['STOP: scope invalid'])
        self.assertEqual(stop['state_effect'][1]['payload']['blocked_by'], [stop['state_effect'][0]['event_id']])

    def test_a_ready_replan_and_a_check_4_replan(self):
        rec = rc.check(dict(all_decisions()['REPLAN'], task_state='READY'))
        self.assertEqual([e['type'] for e in rec['state_effect']], ['conflict.detected'])
        rec = rc.check(inputs(intent_current={'SPEC-003': 'v5'}))
        self.assertEqual(rec['decision'], 'REPLAN')
        self.assertEqual(rec['state_effect'], [])
        self.assertTrue(any('check 4' in u for u in rec['uncovered']))

    def test_each_event_payload_has_no_finding(self):
        for want, inp in all_decisions().items():
            for e in rc.check(inp)['state_effect']:
                self.assertEqual(records.check_payload(e['type'], e['payload']), [], (want, e['type']))
                self.assertEqual(set(e), {'event_id', 'type', 'payload', 'task_id'})


class R9Helpers(unittest.TestCase):
    SRC = ('import os\nfrom pkg import mod\nfrom pkg.sub import thing\nimport missing.lib\nfrom . import near\n'
           '@dec\ndef f(a: int, b=1, *, c=2) -> str:\n    return a\n'
           'class K(Base):\n    x: int = 1\n    _h = 2\n    def m(self, y):\n        pass\n    def _p(self):\n        pass\n')

    def test_signature_form(self):
        f = rc.signature_form(self.SRC, 'f')
        self.assertTrue(f.startswith("FunctionDef(name='f'"))
        self.assertIn("decorators=[Name(id='dec'", f)
        self.assertEqual(f, rc.signature_form('\n\n' + self.SRC + '# a comment\n', 'f'))
        self.assertNotEqual(f, rc.signature_form(self.SRC.replace('b=1', 'b=3').replace('-> str', '-> int'), 'f'))
        self.assertEqual(rc.signature_form(self.SRC.replace('b=1', 'b=3'), 'f'), f)
        k = rc.signature_form(self.SRC, 'K')
        self.assertIn("name='m'", k)
        self.assertNotIn("_p", k)
        self.assertNotIn("'_h'", k)
        self.assertIsNone(rc.signature_form(self.SRC, 'g'))
        self.assertEqual(rc.signature_form(self.SRC + 'def f():\n    pass\n', 'f'), 'ambiguous')
        self.assertEqual(rc.signature_form('def (:', 'f'), 'unparsable')

    def test_direct_imports(self):
        paths = ['src/pkg/__init__.py', 'src/pkg/mod.py', 'src/pkg/sub.py']
        out = rc.direct_imports(self.SRC, ['src', ''], paths)
        self.assertEqual(out['paths'], ['src/pkg/mod.py', 'src/pkg/sub.py'])
        self.assertEqual(out['unresolved'], ['.', 'missing.lib'])
        self.assertEqual(rc.direct_imports('import (', ['src'], paths), 'unanalysed')


if __name__ == '__main__':
    unittest.main()
