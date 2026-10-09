"""Unit tests of the bootstrap governor of TASK-004 (AC13, rules R1 to R9). Every failing case is built in memory; the
only file read is the module's own source, with pathlib's read_bytes (AC10).
"""
import ast
import copy
import hashlib
import pathlib
import unittest

from aieos_bootstrap import governor
from aieos_bootstrap import records

ROOT = pathlib.Path(__file__).resolve().parents[2]
TASK = 'TASK-500'
COMMIT = 'a' * 40
HASH = 'c' * 64
IV = {'SPEC-001': 'v2'}
CI = 'deterministic_tool_external_ci'


def request(**changes):
    r = {'task_id': TASK, 'task_content_hash': HASH, 'evaluated_commit': COMMIT, 'intent_versions': dict(IV),
         'task_state': 'VERIFYING', 'changed_paths': ['src/x.py'], 'retry_count': {'used': 0, 'limit': 2}}
    r.update(changes)
    return r


def inputs(profile=None, **changes):
    i = {'traces_to': ['SPEC-001'], 'risk': 'low', 'owner_kept_act': False, 'weakens_evidence': False,
         'delegation_in_force': True, 'auto_accept': False, 'verification_plan': ['G0', 'G1'],
         'evidence_profile': profile if profile is not None else [{'dimension': 'functional', 'evidence_types': ['build']}],
         'applicable_articles': [], 'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1'}
    i.update(changes)
    return i


def rec(rid, **fields):
    r = {'record_id': rid, 'fact_kind': 'observation', 'source_class': CI, 'recorder': 'external CI',
         'subject': TASK, 'commit': COMMIT, 'intent_versions': dict(IV), 'outcome': 'pass'}
    r.update(fields)
    return {k: v for k, v in r.items() if v is not None}


def gates():
    return [rec('g0', gate='G0', evidence_type='scope_check', dimension='scope'),
            rec('g1', gate='G1', evidence_type='build', dimension='functional')]


def way2(rid='w', dim='architecture', reviewer='model-b', **f):
    return rec(rid, source_class='same_lineage_review', recorder='a reviewer agent', evidence_type='other_model_review',
               dimension=dim, decision_ref='D-1', models={'reviewer': reviewer, 'implementer': 'model-a'}, **f)


def da_review(rid='d', dim='architecture', stands_for='ai_review (cross-model)', **f):
    return rec(rid, source_class='decision_agent', recorder='decision agent', evidence_type='decision_agent_review',
               dimension=dim, decision_ref='D-2', basis='read in full', stands_for=stands_for, **f)


def approval(rid='ap', source='human_authority', hash_=HASH, **f):
    return rec(rid, fact_kind='authority', source_class=source, recorder='an approver', commit=None,
               intent_versions=None, outcome=None, approval_binding={'kind': 'acceptance', 'hash': hash_}, **f)


def run(req=None, inp=None, rs=None):
    return governor.evaluate(req or request(), inp or inputs(), gates() if rs is None else rs)


def missing(out):
    return {(p['dimension'], t) for p in out['profile_used'] for t in p['missing_types']}


FORBIDDEN_CALLS = {'open', 'exec', 'eval', 'compile', '__import__'}


def imports_and_calls(source):
    """The imported names and the names called directly in a module's source (AC1, AC10)."""
    tree = ast.parse(source)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(node.module + '.' + a.name for a in node.names)
    calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    return names, calls


class R1PurityAndDeterminism(unittest.TestCase):
    def test_the_same_arguments_give_the_same_record_and_are_not_changed(self):
        req, inp, rs = request(), inputs(), gates() + [approval()]
        before = copy.deepcopy((req, inp, rs))
        first = governor.evaluate(req, inp, rs)
        self.assertEqual((req, inp, rs), before)
        self.assertEqual(governor.evaluate(req, inp, rs), first)

    def test_a_different_argument_gives_a_different_record_id(self):
        self.assertNotEqual(run()['record_id'], run(req=request(task_content_hash='d' * 64))['record_id'])

    def test_imports_only_the_standard_library_and_records(self):
        names, calls = imports_and_calls((ROOT / 'src/aieos_bootstrap/governor.py').read_bytes().decode('utf-8'))
        self.assertEqual(names, {'hashlib', 're', 'aieos_bootstrap.records'})
        self.assertFalse(calls & FORBIDDEN_CALLS)

    def test_the_import_and_call_check_finds_a_breach(self):
        names, calls = imports_and_calls('import os\nfrom subprocess import run\nopen("x")\neval("1")\n')
        self.assertEqual(names, {'os', 'subprocess.run'})
        self.assertEqual(calls & FORBIDDEN_CALLS, {'open', 'eval'})

    def test_no_execution_decision(self):
        self.assertIn(run()['decision'], records.ACCEPTANCE_DECISIONS)


class R2InputChecks(unittest.TestCase):
    def test_no_task_id_raises(self):
        for bad in (None, [], 'TASK-1', {}, request(task_id='task-1'), request(task_id=7)):
            with self.assertRaises(ValueError):
                governor.evaluate(bad, inputs(), gates())

    def assertError(self, out, state='VERIFYING'):
        self.assertIsNone(out['decision'])
        self.assertTrue(out['error'])
        self.assertIsNone(out['table_row'])
        self.assertEqual(records.check_decision('decision.acceptance', out), [])
        if state is None:
            self.assertNotIn('next_task_state', out)
        else:
            self.assertEqual(out['next_task_state'], state)
        for key in ('record_id', 'fact_kind', 'source_class', 'recorder', 'subject', 'uncovered', 'rests_on_ai'):
            self.assertIn(key, out)

    def test_each_malformed_request_field(self):
        for key, bad in (('task_content_hash', 'x'), ('evaluated_commit', 'abc'), ('intent_versions', {'S': '2'}),
                         ('changed_paths', [1]), ('retry_count', {'used': -1, 'limit': 2}),
                         ('retry_count', {'used': True, 'limit': 2})):
            self.assertError(run(req=request(**{key: bad})))
        self.assertError(run(req=request(task_state='DONE')), state='DONE')
        self.assertError(run(req=request(task_state='NOPE')), state=None)
        r = request()
        del r['changed_paths']
        self.assertError(run(req=r))
        self.assertError(run(req=dict(request(), extra=1)))

    def test_each_malformed_input(self):
        for key, bad in (('traces_to', 'SPEC-001'), ('risk', None), ('risk', 'severe'), ('owner_kept_act', 1),
                         ('weakens_evidence', None), ('delegation_in_force', None), ('auto_accept', 'no'),
                         ('verification_plan', ['X1']), ('evidence_profile', [{'dimension': 'f'}]),
                         ('applicable_articles', [{'id': 'INV-001'}]), ('policy_version', ''),
                         ('level_version', None), ('ruleset_version', 3)):
            self.assertError(run(inp=inputs(**{key: bad})))
        i = inputs()
        del i['risk']
        self.assertError(run(inp=i))
        self.assertError(governor.evaluate(request(), [], gates()))

    def test_records_not_a_list_and_a_repeated_id(self):
        self.assertError(governor.evaluate(request(), inputs(), {'g0': gates()[0]}))
        self.assertError(run(rs=gates() + [rec('g1', evidence_type='lint', dimension='functional')]))

    def test_a_well_formed_request_is_not_an_error(self):
        out = run()
        self.assertNotIn('error', out)
        self.assertEqual(out['decision'], 'NEEDS_REVIEW')

    def test_a_malformed_record_is_not_used_and_listed(self):
        bad = rec('g1', gate='G1', evidence_type='build', dimension='functional', fact_kind='fact')
        out = run(rs=[gates()[0], bad])
        self.assertEqual(out['decision'], 'INSUFFICIENT_EVIDENCE')
        self.assertTrue(any(u.startswith('g1: not used') for u in out['uncovered']))
        out = run(rs=gates() + ['not a record'])
        self.assertTrue(any(u.startswith('record 3: not used') for u in out['uncovered']))

    def test_a_record_id_that_cannot_be_written_is_not_used(self):
        out = run(rs=[gates()[0], rec('g\ud800', gate='G1', evidence_type='build', dimension='functional')])
        self.assertEqual(out['decision'], 'INSUFFICIENT_EVIDENCE')
        self.assertTrue(any('cannot be written' in u for u in out['uncovered']))


class R3Binding(unittest.TestCase):
    def test_a_bound_record_satisfies(self):
        self.assertEqual(missing(run()), set())

    def test_another_commit_is_stale(self):
        out = run(rs=[gates()[0], rec('g1', gate='G1', evidence_type='build', dimension='functional', commit='b' * 40)])
        self.assertEqual(out['reverify'], ['g1'])
        self.assertEqual(missing(out), {('functional', 'build')})
        self.assertEqual(out['missing_gates'], ['G1'])

    def test_another_intent_version_or_an_unknown_entity_is_stale(self):
        for iv in ({'SPEC-001': 'v1'}, {'SPEC-001': 'v2', 'SPEC-009': 'v1'}):
            out = run(rs=[gates()[0], rec('g1', gate='G1', evidence_type='build', dimension='functional', intent_versions=iv)])
            self.assertEqual(out['reverify'], ['g1'])
            self.assertEqual(out['decision'], 'INSUFFICIENT_EVIDENCE')

    def test_an_evidence_record_without_its_binding_is_not_used(self):
        out = run(rs=[gates()[0], rec('g1', gate='G1', evidence_type='build', dimension='functional', commit=None)])
        self.assertEqual(out['reverify'], [])
        self.assertTrue(any(u == 'g1: not used: no commit binding' for u in out['uncovered']))
        self.assertEqual(out['decision'], 'INSUFFICIENT_EVIDENCE')

    def test_rule_2_does_not_apply_to_an_approval(self):
        out = run(req=request(task_state='IN_REVIEW'), rs=gates() + [approval()])
        self.assertEqual(out['approval_record'], 'ap')
        self.assertEqual(out['next_task_state'], 'ACCEPTED')


class R4Satisfaction(unittest.TestCase):
    def check(self, profile, extra, want_missing, **inp):
        out = run(inp=inputs(profile=profile, **inp), rs=gates() + extra)
        self.assertEqual(missing(out), want_missing)
        return out

    def test_a_tool_type_only_from_the_ci_channel(self):
        prof = [{'dimension': 'security', 'evidence_types': ['static_security_analysis']}]
        ok = rec('s', evidence_type='static_security_analysis', dimension='security')
        self.check(prof, [ok], set())
        for cls in ('deterministic_tool_local', 'agent_declared', 'same_lineage_review'):
            self.check(prof, [dict(ok, source_class=cls)], {('security', 'static_security_analysis')})
        self.check(prof, [dict(ok, dimension='functional')], {('security', 'static_security_analysis')})
        self.check(prof, [dict(ok, outcome='fail')], {('security', 'static_security_analysis')})

    def test_agent_declared_never_satisfies(self):
        prof = [{'dimension': 'functional', 'evidence_types': ['unit_test']}]
        claim = rec('c', source_class='agent_declared', evidence_type='unit_test', dimension='functional')
        self.check(prof, [claim], {('functional', 'unit_test')})
        self.check(prof, [dict(claim, fact_kind='claim')], {('functional', 'unit_test')})

    def test_a_human_review(self):
        prof = [{'dimension': 'operational', 'evidence_types': ['human_review']}]
        human = rec('h', source_class='human_authority', evidence_type='human_review', dimension='operational')
        self.check(prof, [human], set())
        self.check(prof, [dict(human, evidence_type='human_security_review')], {('operational', 'human_review')})

    def test_the_decision_agents_review_for_a_human_type(self):
        prof = [{'dimension': 'operational', 'evidence_types': ['human_review']}]
        d = da_review(dim='operational', stands_for='human_review')
        self.check(prof, [d], set())
        self.check(prof, [d], {('operational', 'human_review')}, delegation_in_force=False)
        self.check(prof, [d], {('operational', 'human_review')}, owner_kept_act=True)
        self.check(prof, [dict(d, stands_for='human_security_review')], {('operational', 'human_review')})
        self.check(prof, [dict(d, source_class='same_lineage_review', decision_ref='D-3')], {('operational', 'human_review')})
        no_basis = {k: v for k, v in d.items() if k != 'basis'}
        out = self.check(prof, [no_basis], {('operational', 'human_review')})
        self.assertTrue(any(u.startswith('d: not used') for u in out['uncovered']))

    def test_the_decision_agents_review_never_for_a_tool_type_or_plain_ai_review(self):
        for kind in ('deterministic_rule', 'ai_review'):
            prof = [{'dimension': 'architecture', 'evidence_types': [kind]}]
            self.check(prof, [da_review(stands_for=kind)], {('architecture', kind)})

    def test_ai_review_by_a_way_2_review(self):
        prof = [{'dimension': 'architecture', 'evidence_types': ['ai_review']}]
        self.check(prof, [way2()], set())
        self.check(prof, [way2(reviewer='model-a')], {('architecture', 'ai_review')})
        self.check(prof, [way2()], {('architecture', 'ai_review')}, delegation_in_force=False)
        self.check(prof, [rec('r', source_class='same_lineage_review', evidence_type='ai_review', dimension='architecture')],
                   {('architecture', 'ai_review')})

    def test_the_cross_model_entry_only_by_the_pair(self):
        prof = [{'dimension': 'architecture', 'evidence_types': ['ai_review (cross-model)']}]
        want = {('architecture', 'ai_review (cross-model)')}
        out = self.check(prof, [way2(), da_review()], set(), risk='high')
        self.assertEqual(out['profile_used'][0]['satisfied_by'], ['d', 'w'])
        self.check(prof, [way2(), da_review()], set(), risk='critical')
        self.check(prof, [way2(), da_review()], want, risk='medium')
        self.check(prof, [way2()], want, risk='high')
        self.check(prof, [da_review()], want, risk='high')
        self.check(prof, [way2(), da_review()], want, risk='high', delegation_in_force=False)
        self.check(prof, [way2(reviewer='model-a'), da_review()], want, risk='high')
        self.check(prof, [way2(), da_review(stands_for='human_review')], want, risk='high')

    def test_a_way_2_review_in_the_pair_is_not_counted_again(self):
        prof = [{'dimension': 'architecture', 'evidence_types': ['ai_review', 'ai_review (cross-model)']}]
        self.check(prof, [way2(), da_review()], {('architecture', 'ai_review')}, risk='high')
        self.check(prof, [way2(), way2('w2'), da_review()], set(), risk='high')

    def test_a_review_type_the_table_does_not_name_is_never_satisfied(self):
        prof = [{'dimension': 'security', 'evidence_types': ['security_review']}]
        self.check(prof, [rec('s', evidence_type='security_review', dimension='security')], {('security', 'security_review')})

    def test_an_applicable_article_joins_under_its_id(self):
        arts = [{'id': 'INV-001', 'evidence_required': ['ai_review']}]
        out = self.check(None, [way2(dim='INV-001')], set(), applicable_articles=arts)
        self.assertEqual([p['dimension'] for p in out['profile_used']], ['functional', 'INV-001'])
        self.check(None, [way2(dim='architecture')], {('INV-001', 'ai_review')}, applicable_articles=arts)


class R5BlockingAndApprovals(unittest.TestCase):
    def test_any_class_may_block_also_an_unused_or_stale_record(self):
        base = dict(outcome='blocking', blocking_kind='violation', evidence_type='scope_check', dimension='scope')
        for extra in ({'source_class': 'agent_declared'}, {'commit': 'b' * 40}, {'commit': None}, {'fact_kind': 'x'}):
            out = run(rs=gates() + [rec('v', **dict(base, **extra))])
            self.assertEqual(out['decision'], 'REJECT', extra)
            self.assertEqual(out['blocking'], ['v'])

    def test_a_blocking_record_of_another_task_does_not_block(self):
        out = run(rs=gates() + [rec('v', subject='TASK-9', outcome='blocking', blocking_kind='violation')])
        self.assertEqual(out['decision'], 'NEEDS_REVIEW')
        no_subject = {k: v for k, v in rec('v', outcome='blocking', blocking_kind='violation').items() if k != 'subject'}
        self.assertEqual(run(rs=gates() + [no_subject])['decision'], 'REJECT')

    def test_an_approval_counts_only_when_leaving_in_review(self):
        self.assertIsNone(run(rs=gates() + [approval()])['approval_record'])
        out = run(req=request(task_state='IN_REVIEW'), rs=gates() + [approval()])
        self.assertEqual((out['decision'], out['next_task_state'], out['approval_record']), ('NEEDS_REVIEW', 'ACCEPTED', 'ap'))
        self.assertFalse(out['rests_on_ai']['approval'])

    def test_each_approval_condition(self):
        req = request(task_state='IN_REVIEW')
        self.assertEqual(run(req=req, rs=gates() + [approval(hash_='d' * 64)])['next_task_state'], 'IN_REVIEW')
        self.assertEqual(run(req=req, rs=gates() + [dict(approval(), approval_binding={'kind': 'contract', 'hash': HASH})])['next_task_state'], 'IN_REVIEW')
        self.assertEqual(run(req=req, rs=gates() + [approval(source=CI)])['next_task_state'], 'IN_REVIEW')
        da = approval(source='decision_agent', decision_ref='D-5')
        out = run(req=req, rs=gates() + [da])
        self.assertEqual((out['next_task_state'], out['approval_record']), ('ACCEPTED', 'ap'))
        self.assertTrue(out['rests_on_ai']['approval'])
        for key in ('owner_kept_act', 'weakens_evidence'):
            self.assertEqual(run(req=req, inp=inputs(**{key: True}), rs=gates() + [da])['next_task_state'], 'IN_REVIEW')
        self.assertEqual(run(req=req, inp=inputs(delegation_in_force=False), rs=gates() + [da])['next_task_state'], 'IN_REVIEW')
        out = run(req=req, inp=inputs(owner_kept_act=True), rs=gates() + [da, approval('ap2')])
        self.assertEqual(out['approval_record'], 'ap2')

    def test_the_owners_approval_is_cited_before_the_decision_agents(self):
        out = run(req=request(task_state='IN_REVIEW'), rs=gates() + [approval('a1', source='decision_agent', decision_ref='D-5'), approval('a2')])
        self.assertEqual(out['approval_record'], 'a2')
        self.assertFalse(out['rests_on_ai']['approval'])

    def test_an_approval_never_satisfies_evidence(self):
        prof = [{'dimension': 'operational', 'evidence_types': ['human_review']}]
        ap = dict(approval(), evidence_type='human_review', dimension='operational')
        out = run(inp=inputs(profile=prof), rs=gates() + [ap])
        self.assertEqual(missing(out), {('operational', 'human_review')})


class R6RiskAndRule8(unittest.TestCase):
    def test_no_risk_gives_no_decision(self):
        self.assertIsNone(run(inp=inputs(risk=None))['decision'])

    def test_a_path_that_no_rule_matches_gives_no_decision(self):
        values = derive_values(changed_paths=['src/x.py', 'odd/y.txt'])
        inp = governor.derive_inputs(values)
        self.assertIsNone(inp['risk'])
        self.assertIsNone(run(inp=inp)['decision'])

    def test_the_cross_model_entry_follows_the_given_risk(self):
        prof = [{'dimension': 'architecture', 'evidence_types': ['ai_review (cross-model)']}]
        self.assertEqual(run(inp=inputs(profile=prof, risk='high'), rs=gates() + [way2(), da_review()])['decision'], 'NEEDS_REVIEW')
        self.assertEqual(run(inp=inputs(profile=prof, risk='low'), rs=gates() + [way2(), da_review()])['decision'], 'INSUFFICIENT_EVIDENCE')


class R7Table(unittest.TestCase):
    def test_row_1_for_each_kind(self):
        for kind in ('out_of_scope', 'forbidden_path', 'violation'):
            out = run(rs=gates() + [rec('b', outcome='blocking', blocking_kind=kind)])
            self.assertEqual((out['decision'], out['next_task_state'], out['table_row']), ('REJECT', 'REJECTED', 1))

    def test_row_2_for_each_cause_and_the_retry_limit(self):
        failed_gate = [gates()[0], rec('g1', gate='G1', evidence_type='build', dimension='functional', outcome='fail')]
        for kind in ('constitution', 'other'):
            out = run(rs=gates() + [rec('b', outcome='blocking', blocking_kind=kind)])
            self.assertEqual((out['decision'], out['table_row']), ('NEEDS_REWORK', 2))
        out = run(rs=failed_gate)
        self.assertEqual((out['decision'], out['next_task_state'], out['failed_gates']), ('NEEDS_REWORK', 'REWORK', ['G1']))
        prof = [{'dimension': 'functional', 'evidence_types': ['build', 'unit_test']}]
        out = run(inp=inputs(profile=prof), rs=gates() + [rec('u', evidence_type='unit_test', dimension='functional', outcome='fail')])
        self.assertEqual(out['decision'], 'NEEDS_REWORK')
        out = run(inp=inputs(profile=prof), rs=gates() + [rec('u', evidence_type='unit_test', dimension='functional', outcome='fail', source_class='agent_declared')])
        self.assertEqual(out['decision'], 'INSUFFICIENT_EVIDENCE')
        out = run(req=request(retry_count={'used': 2, 'limit': 2}), rs=failed_gate)
        self.assertEqual(out['next_task_state'], 'ESCALATED')

    def test_row_3_and_the_routing(self):
        out = run(rs=gates()[:1])
        self.assertEqual((out['decision'], out['next_task_state'], out['missing_gates']), ('INSUFFICIENT_EVIDENCE', 'REWORK', ['G1']))
        human = [{'dimension': 'functional', 'evidence_types': ['build']}, {'dimension': 'ops', 'evidence_types': ['human_review']}]
        self.assertEqual(run(inp=inputs(profile=human))['next_task_state'], 'IN_REVIEW')
        both = human + [{'dimension': 'security', 'evidence_types': ['static_security_analysis']}]
        self.assertEqual(run(inp=inputs(profile=both))['next_task_state'], 'REWORK')
        self.assertEqual(run(req=request(retry_count={'used': 3, 'limit': 2}), inp=inputs(profile=both))['next_task_state'], 'ESCALATED')
        self.assertEqual(run(inp=inputs(profile=human), rs=gates()[:1])['next_task_state'], 'REWORK')

    def test_g0_is_always_a_gate(self):
        out = run(inp=inputs(verification_plan=['G1']), rs=gates()[1:])
        self.assertEqual(out['missing_gates'], ['G0'])

    def test_row_4_never_applies_now_and_row_5(self):
        out = run(inp=inputs(auto_accept=True))
        self.assertEqual((out['decision'], out['next_task_state'], out['table_row']), ('NEEDS_REVIEW', 'IN_REVIEW', 5))

    def test_the_order_of_the_rows(self):
        both = gates()[:1] + [rec('g1', gate='G1', evidence_type='build', dimension='functional', outcome='fail'),
                              rec('b', outcome='blocking', blocking_kind='out_of_scope')]
        self.assertEqual(run(rs=both)['table_row'], 1)
        self.assertEqual(run(rs=both[:2], inp=inputs(profile=[{'dimension': 'x', 'evidence_types': ['lint']}]))['table_row'], 2)

    def test_re_evaluation(self):
        req = request(task_state='IN_REVIEW')
        out = run(req=req, rs=gates()[:1] + [approval()])
        self.assertEqual((out['decision'], out['next_task_state'], out['approval_record']), ('INSUFFICIENT_EVIDENCE', 'REWORK', None))
        out = run(req=req)
        self.assertEqual((out['decision'], out['next_task_state']), ('NEEDS_REVIEW', 'IN_REVIEW'))
        out = run(req=req, rs=gates() + [approval(), rec('b', outcome='blocking', blocking_kind='violation')])
        self.assertEqual(out['decision'], 'REJECT')


class R8RecordKeys(unittest.TestCase):
    KEYS = {'record_id', 'fact_kind', 'source_class', 'recorder', 'subject', 'decision', 'next_task_state', 'table_row',
            'task_content_hash', 'evaluated_commit', 'intent_versions', 'profile_used', 'missing_gates', 'blocking',
            'failed_gates', 'reverify', 'approval_record', 'policy_version', 'level_version', 'ruleset_version',
            'governor_identity', 'scenario_set_hash', 'uncovered', 'rests_on_ai'}

    def test_the_keys_and_check_decision(self):
        out = run()
        self.assertEqual(set(out), self.KEYS)
        self.assertEqual(records.check_decision('decision.acceptance', out), [])
        self.assertEqual((out['source_class'], out['recorder'], out['subject']),
                         ('deterministic_tool_local', 'src/aieos_bootstrap/governor.py', TASK))
        self.assertIsNone(out['governor_identity'])
        self.assertIsNone(out['scenario_set_hash'])
        self.assertEqual((out['policy_version'], out['level_version'], out['ruleset_version']), ('v2', 'v1', 'v1'))

    def test_the_record_id_is_the_hash_of_the_canonical_form(self):
        out = run()
        text = governor.canon({k: v for k, v in out.items() if k != 'record_id'}) + '\n'
        self.assertEqual(out['record_id'], 'decision-' + hashlib.sha256(text.encode('utf-8')).hexdigest())

    def test_rests_on_ai_both_ways(self):
        prof = [{'dimension': 'ops', 'evidence_types': ['human_review']}]
        d = da_review(dim='ops', stands_for='human_review')
        out = run(inp=inputs(profile=prof), rs=gates() + [d])
        self.assertEqual(out['rests_on_ai']['entries'], [{'dimension': 'ops', 'evidence_type': 'human_review'}])
        h = rec('h', source_class='human_authority', evidence_type='human_review', dimension='ops')
        out = run(inp=inputs(profile=prof), rs=gates() + [d, h])
        self.assertEqual(out['rests_on_ai']['entries'], [])
        self.assertEqual(run()['rests_on_ai'], {'entries': [], 'approval': False})


def derive_values(**changes):
    v = {
        'contract': {'traces_to': ['SPEC-001'], 'risk': 'low', 'owner_kept_act': False, 'verification_plan': ['G0', 'G1']},
        'changed_paths': ['src/x.py'],
        'risk_rules': [{'id': 'R1', 'match': ['docs/**', '*.md'], 'class': 'low'},
                       {'id': 'R2', 'match': ['src/**', 'tests/**'], 'class': 'medium'},
                       {'id': 'R9', 'match': ['.github/**'], 'class': 'critical'}],
        'owner_kept_rules': [{'id': 'OPS-002', 'match': ['docs/pre-genesis/measurement-protocol.md']}],
        'articles': [{'id': 'INV-002', 'scope': ['src/**'], 'evidence_required': ['ai_review']},
                     {'id': 'SEC-003', 'scope': ['.github/**'], 'evidence_required': ['human_review']}],
        'default_profiles': {'medium': [{'dimension': 'functional', 'evidence_types': ['unit_test']}],
                             'critical': [{'dimension': 'functional', 'evidence_types': ['unit_test', 'integration_test']}]},
        'requirement_profiles': [{'id': 'SPEC-001', 'add': [{'dimension': 'security', 'evidence_types': ['static_security_analysis']}]},
                                 {'id': 'SPEC-002', 'add': [{'dimension': 'ops', 'evidence_types': ['human_review']}]}],
        'delegation': True,
        'evidence_comparison': {'weakens': False},
        'auto_accept': {},
        'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1',
    }
    v.update(changes)
    return v


class R9Derivation(unittest.TestCase):
    def test_a_derived_object_is_a_valid_input(self):
        inp = governor.derive_inputs(derive_values())
        self.assertEqual(set(inp), governor.INPUT_KEYS)
        self.assertNotIn('error', run(inp=inp))

    def test_the_risk_is_the_highest_matched_never_a_lower_declared_one(self):
        self.assertEqual(governor.derive_inputs(derive_values())['risk'], 'medium')
        self.assertEqual(governor.derive_inputs(derive_values(changed_paths=['README.md', '.github/w.yml']))['risk'], 'critical')
        self.assertEqual(governor.derive_inputs(derive_values(changed_paths=['docs/a.md']))['risk'], 'low')
        contract = dict(derive_values()['contract'], risk='high')
        self.assertEqual(governor.derive_inputs(derive_values(contract=contract))['risk'], 'high')

    def test_a_path_no_rule_matches_gives_no_risk(self):
        self.assertIsNone(governor.derive_inputs(derive_values(changed_paths=['src/x.py', 'other.txt']))['risk'])
        self.assertIsNone(governor.derive_inputs(derive_values(risk_rules=[]))['risk'])

    def test_a_rule_that_cannot_be_evaluated_matches(self):
        rules = derive_values()['risk_rules'] + [{'id': 'R3', 'match': {'component_tags': ['governor']}, 'class': 'high'}]
        self.assertEqual(governor.derive_inputs(derive_values(risk_rules=rules, changed_paths=['docs/a.md']))['risk'], 'high')
        rules = derive_values()['risk_rules'] + [{'id': 'R?', 'match': ['src/**'], 'class': 'severe'}]
        self.assertEqual(governor.derive_inputs(derive_values(risk_rules=rules))['risk'], 'critical')

    def test_the_owner_kept_act(self):
        self.assertFalse(governor.derive_inputs(derive_values())['owner_kept_act'])
        self.assertTrue(governor.derive_inputs(derive_values(changed_paths=['docs/pre-genesis/measurement-protocol.md']))['owner_kept_act'])
        contract = dict(derive_values()['contract'], owner_kept_act=True)
        self.assertTrue(governor.derive_inputs(derive_values(contract=contract))['owner_kept_act'])
        self.assertTrue(governor.derive_inputs(derive_values(owner_kept_rules=[{'id': 'X', 'match': None}]))['owner_kept_act'])
        self.assertTrue(governor.derive_inputs(derive_values(owner_kept_rules='unreadable'))['owner_kept_act'])

    def test_weakens_evidence_unless_a_comparison_says_otherwise(self):
        self.assertFalse(governor.derive_inputs(derive_values())['weakens_evidence'])
        for comp in (None, {'weakens': True}, {'weakens': 'no'}, {}):
            self.assertTrue(governor.derive_inputs(derive_values(evidence_comparison=comp))['weakens_evidence'])

    def test_the_delegation_from_the_pinned_value(self):
        self.assertTrue(governor.derive_inputs(derive_values())['delegation_in_force'])
        self.assertFalse(governor.derive_inputs(derive_values(delegation=False))['delegation_in_force'])
        inp = governor.derive_inputs(derive_values(delegation=None))
        self.assertIsNone(inp['delegation_in_force'])
        self.assertIsNone(run(inp=inp)['decision'])

    def test_the_profile_and_the_articles(self):
        inp = governor.derive_inputs(derive_values())
        self.assertEqual(inp['applicable_articles'], [{'id': 'INV-002', 'evidence_required': ['ai_review']}])
        self.assertEqual(inp['evidence_profile'], [
            {'dimension': 'functional', 'evidence_types': ['unit_test']},
            {'dimension': 'security', 'evidence_types': ['static_security_analysis']},
            {'dimension': 'INV-002', 'evidence_types': ['ai_review']}])
        reqs = derive_values()['requirement_profiles'] + [{'id': 'SPEC-001', 'add': [{'dimension': 'functional', 'evidence_types': ['unit_test', 'property_test']}]}]
        inp = governor.derive_inputs(derive_values(requirement_profiles=reqs))
        self.assertEqual(inp['evidence_profile'][0], {'dimension': 'functional', 'evidence_types': ['unit_test', 'property_test']})
        arts = [{'id': 'SEC-X', 'scope': None, 'evidence_required': ['human_review']}]
        self.assertEqual(governor.derive_inputs(derive_values(articles=arts))['applicable_articles'][0]['id'], 'SEC-X')
        inp = governor.derive_inputs(derive_values(changed_paths=['docs/a.md']))
        self.assertIsNone(inp['evidence_profile'])
        self.assertIsNone(run(inp=inp)['decision'])

    def test_the_plan_and_auto_accept(self):
        contract = dict(derive_values()['contract'], verification_plan=['G2', 'G0'])
        self.assertEqual(governor.derive_inputs(derive_values(contract=contract))['verification_plan'], ['G0', 'G2'])
        self.assertTrue(governor.derive_inputs(derive_values(auto_accept={'medium': True}))['auto_accept'])
        self.assertFalse(governor.derive_inputs(derive_values(auto_accept={'low': True}))['auto_accept'])

    def test_malformed_values_raise(self):
        for bad in ({}, dict(derive_values(), extra=1), derive_values(changed_paths=[]),
                    derive_values(contract={'traces_to': []}), derive_values(articles=[{'id': 'X'}]),
                    derive_values(requirement_profiles=[{'id': 'SPEC-001'}])):
            with self.assertRaises(ValueError):
                governor.derive_inputs(bad)

    def test_the_patterns(self):
        m = governor.matches
        self.assertTrue(m('docs/**', 'docs/a/b.md'))
        self.assertTrue(m('*.md', 'docs/a/b.md'))
        self.assertTrue(m('**/contracts/**', 'a/contracts/x.sql'))
        self.assertTrue(m('docs/pre-genesis/CR-*.md', 'docs/pre-genesis/CR-002.md'))
        self.assertFalse(m('docs/*.md', 'docs/a/b.md'))
        self.assertFalse(m('src/**', 'srcx/a.py'))
        self.assertFalse(m('CLAUDE.md', 'docs/CLAUDE.mdx'))


if __name__ == '__main__':
    unittest.main()
