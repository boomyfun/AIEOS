"""Unit tests of aieos_bootstrap.evaluation_intake (TASK-159, BT3b-2d-1): read_ci_data, which turns the saved texts of
the CI runs of a task commit into eligible run mappings, and manifest. Every case is built in memory; the log lines of
the checkout step and the field names of the two JSON forms are cut from one real run (aieos-checks 45669166895); no
test reads a log or a JSON file, and none runs a process or writes a file.
"""
import ast
import copy
import hashlib
import json
import pathlib
import sys
import unittest
from unittest import mock

from aieos_bootstrap import ci_evidence
from aieos_bootstrap import eval_inputs
from aieos_bootstrap import evaluation_intake
from aieos_bootstrap import evaluation_sources
from aieos_bootstrap import gate_records
from aieos_bootstrap import governor
from aieos_bootstrap import records

EI = evaluation_intake
SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap' / 'evaluation_intake.py'
TASK = 'TASK-159'
COMMIT = '6f27bdc76ef0ef15077bddb4522469c55b9247ea'
OTHER = 'f' * 40
POLICY_REF = 'a' * 40
SHA = 'c' * 64
CHECKS = '.github/workflows/aieos-checks.yml'
NATIVE = '.github/workflows/aieos-native.yml'
STEP = 'Fetch the pushed commit, its history and main (no third-party action, no token)'
STAMP = '2026-11-25T17:51:44.8338246Z'
SHA_LINE = 'checks\t' + STEP + '\t' + STAMP + '   SHA: ' + COMMIT
LOG = ('checks\tSet up job\t2026-11-25T17:51:43.0000000Z Complete job name: checks\n' + SHA_LINE + '\n')
NATIVE_LOG = 'linux\tnative governor\t2026-11-25T17:51:44.8338246Z PASS\n'
RUN_KEYS = {'run_id', 'attempt', 'head_sha', 'event', 'head_branch', 'workflow_path', 'status', 'conclusion', 'steps',
            'log'}


def api(run_id=100, attempt=1, **changes):
    value = {'id': run_id, 'run_attempt': attempt, 'head_sha': COMMIT, 'event': 'push', 'head_branch': 'task/' + TASK,
             'status': 'completed', 'conclusion': 'success', 'path': CHECKS, 'name': 'aieos-checks',
             'actor': {'login': 'x', 'id': 1}}
    value.update(changes)
    return value


def view(run_id=100, attempt=1, **changes):
    value = {'databaseId': run_id, 'attempt': attempt, 'headSha': COMMIT, 'event': 'push', 'headBranch': 'task/' + TASK,
             'status': 'completed', 'conclusion': 'success', 'workflowName': 'aieos-checks',
             'jobs': [{'name': 'checks', 'conclusion': 'success', 'status': 'completed',
                       'steps': [{'name': 'Set up job', 'conclusion': 'success', 'number': 1},
                                 {'name': STEP, 'conclusion': 'success', 'number': 2}]}]}
    value.update(changes)
    return value


def three(run_id=100, attempt=1, a=None, v=None, log=LOG):
    stem = 'run-%d-%d.' % (run_id, attempt)
    return {stem + 'api.json': json.dumps(api(run_id, attempt) if a is None else a),
            stem + 'view.json': json.dumps(view(run_id, attempt) if v is None else v),
            stem + 'log': log}


def many(*groups):
    out = {}
    for group in groups:
        out.update(group)
    return out


def read(files, task_id=TASK, commit=COMMIT):
    return EI.read_ci_data(files, task_id, commit)


class Base(unittest.TestCase):
    def refused(self, answer, reason):
        self.assertEqual(set(answer), {'result', 'runs', 'files', 'findings'})
        self.assertEqual(answer['result'], 'refused')
        self.assertIsNone(answer['runs'])
        self.assertIsNone(answer['files'])
        self.assertEqual(len(answer['findings']), 1)
        self.assertEqual(set(answer['findings'][0]), {'reason', 'detail'})
        self.assertEqual(answer['findings'][0]['reason'], reason, answer['findings'][0]['detail'])
        self.assertLessEqual(len(answer['findings'][0]['detail']), 200)
        return answer['findings'][0]['detail']


class AC3Present(Base):
    def test_one_attempt_gives_one_run_mapping_and_the_hash_of_every_file(self):
        files = three()
        answer = read(files)
        self.assertEqual(answer['result'], 'present')
        self.assertEqual(answer['findings'], [])
        self.assertEqual(len(answer['runs']), 1)
        run = answer['runs'][0]
        self.assertEqual(set(run), RUN_KEYS)
        self.assertEqual(set(run), set(ci_evidence._RUN_KEYS))
        self.assertEqual((run['run_id'], run['attempt'], run['head_sha'], run['event'], run['head_branch']),
                         (100, 1, COMMIT, 'push', 'task/' + TASK))
        self.assertEqual((run['workflow_path'], run['status'], run['conclusion']), (CHECKS, 'completed', 'success'))
        self.assertEqual(run['steps'], [{'name': 'Set up job', 'conclusion': 'success'},
                                        {'name': STEP, 'conclusion': 'success'}])
        self.assertEqual(run['log'], LOG)
        self.assertEqual(answer['files'], [{'name': n, 'sha256': hashlib.sha256(files[n].encode('utf-8')).hexdigest()}
                                           for n in sorted(files)])

    def test_the_run_mappings_are_taken_by_ci_evidence(self):
        detect = 'checks\tG0 task detection (the contract commit on main)\t2026-11-20T17:12:03.0000000Z '
        log = (detect + '##[endgroup]\n'
               + detect + 'G0 detect: task ' + TASK + ' contract commit ' + OTHER + ' base ' + POLICY_REF + '\n'
               + detect + 'G0 contract sha256 ' + SHA + '\n' + LOG)
        runs = read(three(log=log))['runs']
        out = ci_evidence.ci_evidence(TASK, COMMIT, SHA, {'SPEC-001': 'v2'}, [{'gate': 'G0', 'check': 'scope'}],
                                      ['src/x.py'], runs, 'external CI')
        self.assertIsNone(out['refusal'])
        self.assertEqual([(r['run_id'], r['attempt']) for r in out['evidence']['runs']], [(100, 1)])

    def test_a_null_conclusion_is_kept(self):
        files = three(a=api(status='in_progress', conclusion=None), v=view(status='in_progress', conclusion=None))
        self.assertIsNone(read(files)['runs'][0]['conclusion'])

    def test_the_steps_of_every_job_come_in_order(self):
        v = view()
        v['jobs'].append({'steps': [{'name': 'later', 'conclusion': None}]})
        steps = read(three(v=v))['runs'][0]['steps']
        self.assertEqual([s['name'] for s in steps], ['Set up job', STEP, 'later'])
        self.assertIsNone(steps[-1]['conclusion'])

    def test_two_attempts_and_two_runs_sorted_by_id_and_attempt(self):
        files = many(three(101, 1), three(100, 2), three(100, 1))
        runs = read(files)['runs']
        self.assertEqual([(r['run_id'], r['attempt']) for r in runs], [(100, 1), (100, 2), (101, 1)])

    def test_a_run_of_another_workflow_is_listed_in_files_and_absent_from_runs(self):
        native = three(200, 1, a=api(200, 1, path=NATIVE, name='aieos-native'), v=view(200, 1), log=NATIVE_LOG)
        answer = read(many(three(), native))
        self.assertEqual([r['run_id'] for r in answer['runs']], [100])
        self.assertEqual(len(answer['files']), 6)
        self.assertIn('run-200-1.log', [f['name'] for f in answer['files']])
        pin = evaluation_sources.pinned_governor([NATIVE_LOG])
        self.assertIsNone(pin['value'])
        self.assertEqual(pin['findings'][0]['reason'], 'pin')

    def test_a_trailing_carriage_return_of_the_commit_line_is_removed_once(self):
        self.assertEqual(read(three(log=SHA_LINE + '\r\n'))['result'], 'present')
        self.refused(read(three(log=SHA_LINE + '\r\r\n')), 'binding')

    def test_no_argument_is_mutated(self):
        files = three()
        before = copy.deepcopy(files)
        read(files)
        self.assertEqual(files, before)


class AC3Arguments(Base):
    def test_a_form_that_is_not_the_stated_one_is_refused_as_argument(self):
        rows = ((None, TASK, COMMIT), ([], TASK, COMMIT), ({1: 'x'}, TASK, COMMIT), ({'run-1-1.log': b'x'}, TASK, COMMIT),
                (three(), 'task-159', COMMIT), (three(), None, COMMIT), (three(), TASK, 'a' * 39),
                (three(), TASK, COMMIT.upper()), (three(), TASK, None))
        for files, task_id, commit in rows:
            self.refused(EI.read_ci_data(files, task_id, commit), 'argument')

    def test_the_argument_check_comes_first(self):
        self.refused(read({'other': 'x'}, task_id='x'), 'argument')

    def test_an_unexpected_error_is_a_refusal_with_the_type_name(self):
        def boom(value, task_id, commit):
            raise RuntimeError('hidden')
        with mock.patch.object(ci_evidence, 'eligible_run', boom):
            detail = self.refused(read(three()), 'argument')
        self.assertEqual(detail, 'an unexpected error: RuntimeError')


class AC3Names(Base):
    def test_a_name_out_of_the_three_forms_is_refused(self):
        for name in ('x', 'run-1-1.txt', 'run-0-1.log', 'run-1-0.log', 'run-01-1.log', 'run-1-01.log', 'run-1.log',
                     'Run-1-1.log', 'run-1-1.log ', 'run-' + '1' * 20 + '-1.log', 'run-1-1.api.json\n'):
            files = three()
            files[name] = 'x'
            self.refused(read(files), 'files')

    def test_the_largest_number_of_nineteen_digits_is_a_name(self):
        n = int('9' * 19)
        self.assertEqual(read(three(n, 1, a=api(n, 1), v=view(n, 1)))['result'], 'present')

    def test_an_attempt_without_one_of_its_three_files_is_refused(self):
        for kind in ('api.json', 'view.json', 'log'):
            files = three()
            del files['run-100-1.' + kind]
            self.refused(read(files), 'files')

    def test_no_file_at_all_is_refused(self):
        self.refused(read({}), 'files')

    def test_a_text_that_utf8_cannot_write_is_refused_as_plain_before_the_json(self):
        files = three(log=SHA_LINE + '\n\ud800')
        files['run-100-1.api.json'] = '{'
        self.refused(read(files), 'plain')


class AC3Json(Base):
    def test_a_text_that_parse_json_refuses_is_json(self):
        for kind in ('api.json', 'view.json'):
            for text in ('{', 'NaN', '{"a": 1, "a": 2}', ''):
                files = three()
                files['run-100-1.' + kind] = text
                self.refused(read(files), 'json')

    def test_a_surrogate_escape_in_a_view_text_is_json(self):
        files = three()
        files['run-100-1.view.json'] = json.dumps(view(workflowName='x')).replace('"x"', '"\\ud800"')
        self.refused(read(files), 'json')

    def test_every_attempt_is_parsed_before_any_binding(self):
        files = many(three(100, 1, a=api(head_sha=OTHER)), three(101, 1))
        files['run-101-1.view.json'] = '{'
        self.refused(read(files), 'json')


class AC3Binding(Base):
    def test_a_parsed_value_that_is_not_an_object_is_refused(self):
        for kind in ('api.json', 'view.json'):
            for text in ('null', '[]', '1', '"x"'):
                files = three()
                files['run-100-1.' + kind] = text
                self.refused(read(files), 'binding')

    def test_each_missing_key_is_refused(self):
        for key in ('id', 'run_attempt', 'head_sha', 'event', 'head_branch', 'status', 'conclusion', 'path'):
            a = api()
            del a[key]
            self.refused(read(three(a=a)), 'binding')
        for key in ('databaseId', 'attempt', 'headSha', 'event', 'headBranch', 'status', 'conclusion', 'jobs'):
            v = view()
            del v[key]
            self.refused(read(three(v=v)), 'binding')

    def test_each_pair_that_differs_is_refused(self):
        rows = (('api', 'id', 101), ('api', 'run_attempt', 2), ('api', 'head_sha', OTHER), ('api', 'event', 'x'),
                ('api', 'head_branch', 'main'), ('api', 'status', 'queued'), ('api', 'conclusion', 'failure'),
                ('view', 'databaseId', 101), ('view', 'attempt', 2), ('view', 'headSha', OTHER), ('view', 'event', 'x'),
                ('view', 'headBranch', 'main'), ('view', 'status', 'queued'), ('view', 'conclusion', None))
        for side, key, value in rows:
            files = three(a=api(**{key: value})) if side == 'api' else three(v=view(**{key: value}))
            self.refused(read(files), 'binding')

    def test_both_objects_that_name_another_number_than_the_file_name_are_refused(self):
        self.refused(read(three(a=api(101, 1), v=view(101, 1))), 'binding')
        self.refused(read(three(a=api(100, 2), v=view(100, 2))), 'binding')

    def test_a_bool_or_a_float_is_no_number(self):
        for value in (True, 1.0, '1'):
            self.refused(read(three(a=api(run_attempt=value), v=view(attempt=value))), 'binding')
        self.refused(read(three(1, 1, a=api(True, 1), v=view(True, 1))), 'binding')

    def test_a_value_that_is_not_a_text_is_refused_even_when_both_sides_agree(self):
        for mine, theirs in (('head_sha', 'headSha'), ('event', 'event'), ('head_branch', 'headBranch'),
                             ('status', 'status'), ('conclusion', 'conclusion')):
            self.refused(read(three(a=api(**{mine: 1}), v=view(**{theirs: 1}))), 'binding')

    def test_the_path_is_a_text_and_comes_from_the_api_object_only(self):
        for value in (None, 1, ['x']):
            self.refused(read(three(a=api(path=value))), 'binding')
        self.refused(read(three(a=api(path=NATIVE), v=view(path=CHECKS))), 'run')

    def test_the_jobs_and_the_steps_have_their_forms(self):
        rows = ({}, 'x', [1], [{}], [{'steps': {}}], [{'steps': [1]}], [{'steps': [{'name': 'a'}]}],
                [{'steps': [{'conclusion': None}]}], [{'steps': [{'name': '', 'conclusion': None}]}],
                [{'steps': [{'name': 1, 'conclusion': None}]}], [{'steps': [{'name': 'a', 'conclusion': 1}]}])
        for jobs in rows:
            self.refused(read(three(v=view(jobs=jobs))), 'binding')

    def test_an_eligible_log_without_the_line_of_the_commit_is_refused(self):
        rows = ('', SHA_LINE.replace(COMMIT, OTHER), SHA_LINE.replace('checks\t', 'linux\t', 1),
                SHA_LINE.replace(STEP, 'Set up job'), SHA_LINE.replace('Z   SHA', 'Z  SHA'),
                SHA_LINE.replace('Z   SHA', 'Z    SHA'), SHA_LINE + ' ', SHA_LINE + 'x', SHA_LINE.replace('\t', ' '),
                'checks\t' + STEP + '\t  SHA: ' + COMMIT, SHA_LINE.replace(STAMP, 'x' + STAMP))
        for log in rows:
            self.refused(read(three(log=log + '\n')), 'binding')

    def test_a_line_separator_other_than_the_line_feed_does_not_split(self):
        self.refused(read(three(log='x\x0c' + SHA_LINE + '\n')), 'binding')

    def test_every_eligible_log_must_hold_the_line(self):
        self.refused(read(many(three(100, 1), three(101, 1, log='x\n'))), 'binding')

    def test_a_log_of_a_run_that_is_not_eligible_needs_no_line(self):
        native = three(200, 1, a=api(200, 1, path=NATIVE), v=view(200, 1), log='')
        self.assertEqual(read(many(three(), native))['result'], 'present')


class AC3RunAndAttempts(Base):
    def test_no_eligible_run_is_refused(self):
        for change in ({'path': NATIVE}, ):
            self.refused(read(three(a=api(**change))), 'run')
        self.refused(read(three(), commit=OTHER), 'run')
        self.refused(read(three(), task_id='TASK-158'), 'run')

    def test_a_gap_in_the_attempts_is_refused(self):
        self.refused(read(many(three(100, 1), three(100, 3))), 'attempts')
        self.refused(read(three(100, 2)), 'attempts')

    def test_an_attempt_of_an_eligible_run_that_is_not_eligible_is_refused(self):
        other = three(100, 2, a=api(100, 2, path=NATIVE), v=view(100, 2))
        self.refused(read(many(three(100, 1), other)), 'attempts')
        first = three(100, 1, a=api(100, 1, path=NATIVE), v=view(100, 1))
        self.refused(read(many(first, three(100, 2))), 'attempts')

    def test_the_attempts_come_before_the_content_check(self):
        self.refused(read(three(100, 2, log='x\n')), 'attempts')

    def test_the_reasons_are_a_closed_set(self):
        seen = {read(None)['findings'][0]['reason'], read({})['findings'][0]['reason'],
                read(three(log='\ud800'))['findings'][0]['reason'], read(three(a=[]))['findings'][0]['reason'],
                read(three(), commit=OTHER)['findings'][0]['reason'],
                read(three(100, 2))['findings'][0]['reason']}
        files = three()
        files['run-100-1.api.json'] = '{'
        seen.add(read(files)['findings'][0]['reason'])
        self.assertEqual(seen, {'argument', 'files', 'plain', 'binding', 'run', 'attempts', 'json'})


PROVENANCE = [{'path': 'docs/specs/x.md', 'commit': POLICY_REF, 'blob': 'b' * 40, 'sha256': SHA}]
CI = {'head_sha': COMMIT, 'runs': [{'run_id': 100, 'attempt': 1, 'log_sha256': SHA}]}
FILES = [{'name': 'run-100-1.log', 'sha256': SHA}]


def make(**changes):
    a = {'task_id': TASK, 'evaluated_commit': COMMIT, 'policy_ref': POLICY_REF, 'contract_sha256': SHA,
         'provenance': copy.deepcopy(PROVENANCE), 'ci': copy.deepcopy(CI), 'files': copy.deepcopy(FILES),
         'recorder': 'external CI'}
    a.update(changes)
    return EI.manifest(**a)


class AC4Manifest(unittest.TestCase):
    def refused(self, answer, reason):
        self.assertEqual(set(answer), {'result', 'text', 'sha256', 'record', 'findings'})
        self.assertEqual(answer['result'], 'refused')
        self.assertEqual((answer['text'], answer['sha256'], answer['record']), (None, None, None))
        self.assertEqual(len(answer['findings']), 1)
        self.assertEqual(answer['findings'][0]['reason'], reason, answer['findings'][0]['detail'])
        return answer['findings'][0]['detail']

    def test_the_text_is_the_canonical_json_and_the_sha_is_of_its_bytes(self):
        answer = make(recorder='r\u00e9')
        self.assertEqual(set(answer), {'result', 'text', 'sha256', 'record', 'findings'})
        self.assertEqual((answer['result'], answer['findings']), ('present', []))
        value = {'task_id': TASK, 'evaluated_commit': COMMIT, 'policy_ref': POLICY_REF, 'contract_sha256': SHA,
                 'provenance': PROVENANCE, 'ci': CI, 'files': FILES}
        self.assertEqual(answer['text'], json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False))
        self.assertEqual(answer['sha256'], hashlib.sha256(answer['text'].encode('utf-8')).hexdigest())
        self.assertNotIn('r\u00e9', answer['text'])

    def test_a_character_outside_ascii_is_written_as_itself(self):
        self.assertIn('\u00e9', make(ci={'k': '\u00e9'})['text'])

    def test_the_record_has_exactly_its_keys_and_values(self):
        answer = make()
        digest = answer['sha256']
        record_id = hashlib.sha256(('evaluation-manifest\n' + TASK + '\n' + COMMIT + '\n' + digest).encode('utf-8')).hexdigest()
        self.assertEqual(answer['record'], {'record_id': record_id, 'fact_kind': 'observation',
                                            'source_class': 'deterministic_tool_local', 'recorder': 'external CI',
                                            'subject': TASK, 'evidence_type': 'evaluation_manifest', 'commit': COMMIT,
                                            'refers_to': digest, 'basis': [answer['text']]})
        self.assertEqual(records.check_payload('record.added', answer['record']), [])

    def test_the_record_changes_no_decision_and_adds_one_note(self):
        request = {'task_id': TASK, 'task_content_hash': 'c' * 64, 'evaluated_commit': COMMIT,
                   'intent_versions': {'SPEC-001': 'v2'}, 'task_state': 'VERIFYING', 'changed_paths': ['src/x.py'],
                   'retry_count': {'used': 0, 'limit': 2}}
        inputs = {'traces_to': ['SPEC-001'], 'risk': 'low', 'owner_kept_act': False, 'weakens_evidence': False,
                  'delegation_in_force': True, 'auto_accept': False, 'verification_plan': ['G0', 'G1'],
                  'evidence_profile': [{'dimension': 'functional', 'evidence_types': ['build']}],
                  'applicable_articles': [], 'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1'}
        steps = [{'name': n, 'conclusion': 'success'} for n in ('G0 task detection (the contract commit on main)',
                                                              'G0 scope (V0)', 'G1 build')]
        made = gate_records.gate_records(TASK, COMMIT, {'SPEC-001': 'v2'},
                                         [{'gate': 'G0', 'check': 'scope'}, {'gate': 'G1', 'check': 'build'}], steps,
                                         {k: list(v) for k, v in gate_records.DEFAULT_CHECK_MAP.items()}, 'external CI')
        self.assertTrue(made['records'])
        record = make()['record']
        without = governor.evaluate(copy.deepcopy(request), copy.deepcopy(inputs), copy.deepcopy(made['records']))
        with_it = governor.evaluate(copy.deepcopy(request), copy.deepcopy(inputs),
                                    copy.deepcopy(made['records']) + [record])
        self.assertEqual(set(without), set(with_it))
        for key in set(without) - {'record_id', 'uncovered'}:
            self.assertEqual(without[key], with_it[key], key)
        added = [n for n in with_it['uncovered'] if n not in without['uncovered']]
        self.assertEqual(added, [record['record_id'] + ': not used: no commit binding'])
        self.assertEqual(len(with_it['uncovered']), len(without['uncovered']) + 1)

    def test_a_form_that_is_not_the_stated_one_is_refused_as_argument(self):
        rows = ({'task_id': 'x'}, {'evaluated_commit': 'a'}, {'policy_ref': None}, {'contract_sha256': 'a' * 40},
                {'provenance': {}}, {'ci': []}, {'files': {}}, {'recorder': ''}, {'recorder': None},
                {'recorder': '\ud800'})
        for change in rows:
            self.refused(make(**change), 'argument')

    def test_data_that_is_not_plain_is_refused(self):
        deep = []
        for _ in range(60):
            deep = [deep]
        for change in ({'provenance': [(1,)]}, {'ci': {1: 2}}, {'files': [float('nan')]}, {'files': [deep]}):
            self.refused(make(**change), 'plain')

    def test_a_lone_surrogate_in_the_data_is_refused_as_plain(self):
        self.refused(make(ci={'k': '\ud800'}), 'plain')

    def test_an_integer_over_the_interpreter_limit_is_refused_as_plain(self):
        if not hasattr(sys, 'get_int_max_str_digits'):
            self.skipTest('this interpreter has no limit of digits for an integer text (Python %s)' % sys.version.split()[0])
        limit = sys.get_int_max_str_digits()
        if limit == 0:
            self.skipTest('this interpreter has no limit of digits for an integer text (Python %s)' % sys.version.split()[0])
        self.refused(make(ci={'n': 10 ** (limit + 1)}), 'plain')

    def test_an_unexpected_error_is_a_refusal_with_the_type_name(self):
        def boom(value):
            raise RuntimeError('hidden')
        with mock.patch.object(EI.evaluation_derive, 'plain_data_problem', boom):
            self.assertEqual(self.refused(make(), 'argument'), 'an unexpected error: RuntimeError')

    def test_no_argument_is_mutated(self):
        provenance, ci, files = copy.deepcopy(PROVENANCE), copy.deepcopy(CI), copy.deepcopy(FILES)
        make(provenance=provenance, ci=ci, files=files)
        self.assertEqual((provenance, ci, files), (PROVENANCE, CI, FILES))


class AC6TheModule(unittest.TestCase):
    def tree(self):
        return ast.parse(SRC.read_bytes().decode('utf-8'))

    def test_the_imports_are_among_the_stated_ones(self):
        names = set()
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.update(node.module + '.' + a.name for a in node.names)
        self.assertTrue(names <= {'hashlib', 'json', 're', 'aieos_bootstrap.ci_evidence',
                                  'aieos_bootstrap.evaluation_derive', 'aieos_bootstrap.evaluation_sources'}, names)

    def test_the_public_names_are_exactly_three(self):
        public = set()
        for node in self.tree().body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith('_'):
                public.add(node.name)
            elif isinstance(node, ast.Assign):
                public.update(t.id for t in node.targets if isinstance(t, ast.Name) and not t.id.startswith('_'))
        self.assertEqual(public, {'read_ci_data', 'manifest', 'read_reviews'})
        attrs = {n for n in dir(evaluation_intake) if not n.startswith('_')}
        self.assertEqual(attrs, {'read_ci_data', 'manifest', 'read_reviews', 'hashlib', 'json', 're', 'ci_evidence',
                                 'evaluation_derive', 'evaluation_sources'})

    def test_no_name_of_a_process_a_file_a_clock_or_a_dynamic_call(self):
        banned = {'open', 'eval', 'exec', 'compile', 'input', 'breakpoint', '__builtins__', '__import__'}
        modules = {'tempfile', 'shutil', 'subprocess', 'importlib', 'pickle', 'code', 'builtins', 'os', 'sys', 'time',
                   'datetime', 'socket', 'pathlib'}
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.Name):
                self.assertNotIn(node.id, banned)
                self.assertNotIn(node.id, modules)
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, ('open', 'connect', 'write', 'write_text', 'write_bytes', 'unlink', 'mkdir',
                                             'environ', 'now'))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'replace':
                self.assertGreater(len(node.args), 1)

    def test_the_words_of_the_rules_on_words_and_names_are_not_in_the_module(self):
        text = SRC.read_bytes().decode('utf-8')
        for word in ('MEAS' + 'URED', 'ENFOR' + 'CED', 'GUARAN' + 'TEED', 'va' + 'lid', 'acc' + 'epted', 'appr' + 'oved',
                     'native' + '/', 'bench' + '/', 'fixtures' + '_rc'):
            self.assertNotIn(word, text)


# TASK-166: the maker of the review records.
PROFILE = [{'dimension': 'SEC-002', 'evidence_types': ['ai_review']},
           {'dimension': 'GOV-004', 'evidence_types': ['human_review']},
           {'dimension': 'GOV-006', 'evidence_types': ['human_security_review']},
           {'dimension': 'crossed', 'evidence_types': ['ai_review (cross-model)']},
           {'dimension': 'functional', 'evidence_types': ['build', 'lint']}]
IV = {'SPEC-001': 'v2'}
OTHER_ID = '453dc3a92daaf8842badc7e33fc37873c68896f4f942342feb09564a9bd5da82'
AGENT_ID = '9aa6c597a1e8e9cbc2ac270b4e3e6893e7999fdc7b5eed647e0881c079cfa946'


def other_model(**changes):
    e = {'dimension': 'SEC-002', 'evidence_type': 'other_model_review', 'commit': COMMIT, 'outcome': 'pass',
         'decision_ref': 'D-1', 'models': {'reviewer': 'm-a', 'implementer': 'm-b'}}
    e.update(changes)
    return e


def agent_review(**changes):
    e = {'dimension': 'GOV-004', 'evidence_type': 'decision_agent_review', 'commit': COMMIT, 'outcome': 'fail',
         'decision_ref': 'D-2', 'basis': 'b-\u00e9', 'stands_for': 'human_review'}
    e.update(changes)
    return e


def reviews(value, task_id=TASK, commit=COMMIT, profile=None, intent_versions=None, recorder='external CI'):
    text = value if type(value) is str else json.dumps(value)
    return EI.read_reviews(text, task_id, commit, copy.deepcopy(PROFILE) if profile is None else profile,
                           dict(IV) if intent_versions is None else intent_versions, recorder)


def common(ident, source, kind, dimension, outcome, decision):
    return {'record_id': ident, 'fact_kind': 'observation', 'source_class': source, 'recorder': 'external CI',
            'subject': TASK, 'commit': COMMIT, 'intent_versions': {'SPEC-001': 'v2'}, 'evidence_type': kind,
            'dimension': dimension, 'outcome': outcome, 'decision_ref': decision}


class ReviewsBase(unittest.TestCase):
    def refused(self, answer, reason):
        self.assertEqual(set(answer), {'result', 'records', 'sha256', 'findings'})
        self.assertEqual((answer['result'], answer['records'], answer['sha256']), ('refused', None, None), answer)
        self.assertEqual(len(answer['findings']), 1)
        self.assertEqual(set(answer['findings'][0]), {'reason', 'detail'})
        self.assertEqual(answer['findings'][0]['reason'], reason, answer['findings'][0]['detail'])
        self.assertLessEqual(len(answer['findings'][0]['detail']), 200)


class TASK166Records(ReviewsBase):
    def test_each_type_gives_its_exact_record(self):
        """TASK-166 AC2: the two records, their classes and literal ids; each passes check_record; the SHA-256 is of
        the text."""
        iv = dict(IV)
        text = json.dumps([other_model(), agent_review()])
        answer = reviews(text, intent_versions=iv)
        first = common(OTHER_ID, 'same_lineage_review', 'other_model_review', 'SEC-002', 'pass', 'D-1')
        first['models'] = {'reviewer': 'm-a', 'implementer': 'm-b'}
        second = common(AGENT_ID, 'decision_agent', 'decision_agent_review', 'GOV-004', 'fail', 'D-2')
        second.update(basis='b-\u00e9', stands_for='human_review')
        self.assertEqual(answer, {'result': 'present', 'records': [first, second],
                                  'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(), 'findings': []})
        for record in answer['records']:
            self.assertEqual(records.check_record(record), [])
            self.assertIsNot(record['intent_versions'], iv)

    def test_the_types_each_review_can_stand_under(self):
        """TASK-166 AC2: an other_model_review under ai_review or the cross-model pair, a decision_agent_review under
        the type it stands for."""
        for entry in (other_model(dimension='crossed'),
                      agent_review(dimension='crossed', stands_for='ai_review (cross-model)'),
                      agent_review(dimension='GOV-006', stands_for='human_security_review')):
            answer = reviews([entry])
            self.assertEqual(answer['result'], 'present', answer)
            self.assertEqual(records.check_record(answer['records'][0]), [])

    def test_equal_entries_make_one_record(self):
        """TASK-166 AC2: entries equal in canonical text give one record, in the order of their first place."""
        reordered = dict(reversed(list(other_model().items())))
        answer = reviews([other_model(), agent_review(), reordered])
        self.assertEqual([r['record_id'] for r in answer['records']], [OTHER_ID, AGENT_ID])

    def test_a_hundred_entries_are_the_most(self):
        """TASK-166 AC2: 100 entries are read and 101 refuse."""
        many_entries = [other_model(decision_ref='D-%d' % n) for n in range(100)]
        self.assertEqual(len(reviews(many_entries)['records']), 100)
        self.refused(reviews(many_entries + [other_model()]), 'entry')

    def test_each_wrong_entry_refuses_the_whole_file(self):
        """TASK-166 AC2: a missing or extra key, source_class, a human type, another type, a wrong outcome, commit,
        models, basis or stands_for, and a dimension the profile does not ask for."""
        missing = other_model()
        del missing['decision_ref']
        bad = (missing, dict(other_model(), note='x'), dict(agent_review(), source_class='human_authority'),
               agent_review(evidence_type='human_review'), agent_review(evidence_type='human_security_review'),
               other_model(evidence_type='ai_review'), other_model(evidence_type=['other_model_review']), 'x', [],
               other_model(outcome='blocking'), other_model(outcome=True), other_model(commit=OTHER),
               other_model(models={'reviewer': 'm', 'implementer': 'm'}), other_model(models={'reviewer': 'm-a'}),
               other_model(models={'reviewer': '', 'implementer': 'm'}), other_model(models=['m-a', 'm-b']),
               other_model(decision_ref=''), other_model(dimension=''), other_model(dimension=7),
               agent_review(basis=''), agent_review(basis=['b']), agent_review(stands_for='ai_review'),
               agent_review(stands_for=['human_review']), agent_review(stands_for='human_security_review'),
               other_model(dimension='GOV-004'), other_model(dimension='absent'), agent_review(dimension='SEC-002'),
               agent_review(dimension='functional'))
        for entry in bad:
            self.refused(reviews([other_model(), entry]), 'entry')

    def test_a_text_that_is_no_list_of_entries_refuses(self):
        """TASK-166 AC2: no list and an empty list refuse with entry; a text parse_json refuses gives json."""
        for text in ('{}', '"x"', '[]', '1'):
            self.refused(reviews(text), 'entry')
        for text in ('', '[', '\ufeff[]', '[{"a": 1, "a": 2}]', '[NaN]'):
            self.refused(reviews(text), 'json')

    def test_arguments_out_of_form_refuse(self):
        """TASK-166 AC2: each argument out of form gives argument, and no raise leaves the function."""
        good = [other_model()]
        for answer in (EI.read_reviews(b'[]', TASK, COMMIT, PROFILE, IV, 'r'), reviews('\ud800'),
                       reviews(good, task_id='x'), reviews(good, commit='a'), reviews(good, profile={}),
                       reviews(good, profile=[{'dimension': 'SEC-002'}]),
                       reviews(good, profile=[{'dimension': 'SEC-002', 'evidence_types': 'ai_review'}]),
                       reviews(good, intent_versions={'SPEC-001': '2'}), reviews(good, intent_versions=[]),
                       reviews(good, recorder=''), reviews(good, recorder=None)):
            self.refused(answer, 'argument')
        with mock.patch.object(EI.evaluation_sources, 'parse_json', mock.Mock(side_effect=RuntimeError('hidden'))):
            answer = reviews(good)
        self.refused(answer, 'argument')
        self.assertEqual(answer['findings'][0]['detail'], 'an unexpected error: RuntimeError')

    def test_no_argument_is_mutated(self):
        """TASK-166 AC2: the profile and the intent versions are unchanged."""
        profile, iv = copy.deepcopy(PROFILE), dict(IV)
        reviews([other_model(), agent_review()], profile=profile, intent_versions=iv)
        self.assertEqual((profile, iv), (PROFILE, IV))


class TASK166Manifest(unittest.TestCase):
    def test_without_a_reviews_hash_the_answer_is_the_one_of_before(self):
        """TASK-166 AC3: None gives the same text and record as no argument."""
        self.assertEqual(make(reviews_sha256=None), make())
        self.assertNotIn('reviews_sha256', make()['text'])

    def test_with_a_reviews_hash_the_text_holds_it(self):
        """TASK-166 AC3: the text holds the key and the record's id follows the text."""
        answer = make(reviews_sha256='d' * 64)
        value = {'task_id': TASK, 'evaluated_commit': COMMIT, 'policy_ref': POLICY_REF, 'contract_sha256': SHA,
                 'provenance': PROVENANCE, 'ci': CI, 'files': FILES, 'reviews_sha256': 'd' * 64}
        self.assertEqual(answer['text'], json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False))
        self.assertEqual(answer['record']['refers_to'], hashlib.sha256(answer['text'].encode('utf-8')).hexdigest())
        self.assertNotEqual(answer['record']['record_id'], make()['record']['record_id'])

    def test_a_reviews_hash_out_of_form_is_refused(self):
        """TASK-166 AC3: anything but 64 lowercase hexadecimal characters refuses with argument."""
        for value in ('d' * 63, 'D' * 64, '', 5):
            answer = make(reviews_sha256=value)
            self.assertEqual((answer['result'], answer['findings'][0]['reason']), ('refused', 'argument'), value)


# AC6: a run-made low task, from the real input assembler to the governor. The log lines are cuts of aieos-checks
# 44780942904, as the tests of eval_inputs hold them; the values of the sources are fixtures, not policy.
LOW_TASK = 'TASK-150'
LOW_COMMIT = '06880dd8d00b69fa2a9f25fc4036a635bdd31fc0'
LOW_SHA = '7c45fd60c17666c085b2c5d6583a01e70988e2fcf3c0fad1117a8f673eb504ff'
G0_STEP = 'checks\tG0 task detection (the contract commit on main)\t'
LOW_LOG = ('checks\tSet up job\t2026-11-20T17:11:58.6217825Z Complete job name: checks\n'
           + G0_STEP + '2026-11-20T17:12:03.3557860Z   AIEOS_ARGS: detect\n'
           + G0_STEP + '2026-11-20T17:12:03.3558218Z ##[endgroup]\n'
           + G0_STEP + '2026-11-20T17:12:03.4046970Z G0 detect: task TASK-150 contract commit '
           '3572f9585da94f9ec2fb749a25e46a9e040f0033 base f48804f6e3001a3c9dd070437e7ce339d7881150\n'
           + G0_STEP + '2026-11-20T17:12:03.4068619Z G0 contract sha256 ' + LOW_SHA + '\n'
           'checks\tCollect the pushed commits and their changed paths\t\ufeff2026-11-20T17:12:03.4097193Z '
           '##[group]Run set -euo pipefail\n')
LOW_STEPS = ['G0 task detection (the contract commit on main)', 'G0 scope (V0)', 'G1 build',
             'lint (pyflakes 4.0.3, pinned by version and hash)',
             "SEC-001 secret scan (tip tree; every commit's message, file names and added lines)",
             "SEC-002 pattern rules (every commit's added lines)", 'OPS-002 owner-kept paths', 'INV-010 replay',
             'deterministic_rule (INV-001, INV-002, INV-004)', 'OPS-003 pattern rules',
             'static_security_analysis (bandit, every package pinned by version and hash)']
LOW_PLAN = [{'gate': 'G0', 'check': 'scope'}, {'gate': 'G1', 'check': 'build'}, {'gate': 'G2', 'check': 'lint'},
            {'gate': 'G3', 'check': 'constitution', 'args': ['AC1', 'AC2']}]
HUMAN = ('GOV-004', 'GOV-005', 'OPS-002')
AI = ('SEC-002', 'OPS-003')


def low_inputs():
    run = {'run_id': 100, 'attempt': 1, 'head_sha': LOW_COMMIT, 'event': 'push', 'head_branch': 'task/' + LOW_TASK,
           'workflow_path': CHECKS, 'status': 'completed', 'conclusion': 'success',
           'steps': [{'name': n, 'conclusion': 'success'} for n in LOW_STEPS], 'log': LOW_LOG}
    contract = {'task': LOW_TASK, 'traces_to': ['SPEC-001'], 'risk': 'low', 'owner_kept_act': 'false',
                'verification_plan': copy.deepcopy(LOW_PLAN),
                'autonomy': {'max_level': 'L1', 'budgets': {'tokens': '400k', 'wall_time': '2h', 'retries': '1',
                                                            'human_attention': '0m'}}}
    articles = ([{'id': i, 'scope': ['**'], 'evidence_required': ['human_review']} for i in HUMAN]
                + [{'id': i, 'scope': ['**'], 'evidence_required': ['ai_review']} for i in AI])
    sources = {'intent_versions': {'SPEC-001': 'v2'},
               'owner_kept_rules': [{'id': 'OPS-002', 'match': ['docs/pre-genesis/measurement-protocol.md']}],
               'articles': articles,
               'default_profiles': {'low': [{'dimension': 'functional', 'evidence_types': ['build', 'lint']}]},
               'requirement_profiles': [], 'evidence_comparison': {'weakens': False}, 'delegation': True,
               'auto_accept': {}, 'level_version': 'v1', 'ruleset_version': 'v1', 'policy_version': 'v2',
               'risk_rules': [{'match': ['docs/**'], 'class': 'low'}]}
    out = eval_inputs.eval_inputs(LOW_TASK, LOW_COMMIT, 'b' * 40, contract, LOW_SHA, ['docs/Deferred/a.md'], [run],
                                  sources, [], 'external CI')
    assert out['refusal'] is None, out['refusal']
    return out


def low_reviews(failed=None):
    base = {'commit': LOW_COMMIT, 'outcome': 'pass', 'decision_ref': 'D-9'}
    entries = [dict(base, dimension=d, evidence_type='decision_agent_review', basis='read', stands_for='human_review')
               for d in HUMAN]
    entries += [dict(base, dimension=d, evidence_type='other_model_review',
                     models={'reviewer': 'm-a', 'implementer': 'm-b'}) for d in AI]
    for entry in entries:
        if entry['dimension'] == failed:
            entry['outcome'] = 'fail'
    return json.dumps(entries)


def low_decision(text):
    out = low_inputs()
    derived = governor.derive_inputs(copy.deepcopy(out['values']))
    given = []
    if text is not None:
        answer = EI.read_reviews(text, LOW_TASK, LOW_COMMIT, derived['evidence_profile'],
                                 out['declared']['intent_versions'], 'external CI')
        assert answer['result'] == 'present', answer
        given = answer['records']
    request = {'task_id': LOW_TASK, 'task_content_hash': 'c' * 64, 'evaluated_commit': LOW_COMMIT,
               'intent_versions': {'SPEC-001': 'v2'}, 'task_state': 'VERIFYING',
               'changed_paths': ['docs/Deferred/a.md'], 'retry_count': {'used': 0, 'limit': 1}}
    decision = governor.evaluate(request, derived, out['ci_records'] + given)
    return decision['decision'], decision['table_row'], decision['next_task_state']


class TASK166TheOutcome(unittest.TestCase):
    def test_every_review_passed_gives_row_five(self):
        """TASK-166 AC6: with the gate, build and lint records and a passing review per article dimension, the decision
        is NEEDS_REVIEW, row 5, next state IN_REVIEW."""
        self.assertEqual(low_decision(low_reviews()), ('NEEDS_REVIEW', 5, 'IN_REVIEW'))

    def test_one_failed_review_gives_row_two(self):
        """TASK-166 AC6: a failed review entry gives rework."""
        for failed in ('GOV-004', 'SEC-002'):
            self.assertEqual(low_decision(low_reviews(failed))[:2], ('NEEDS_REWORK', 2), failed)

    def test_without_the_reviews_row_three_as_before(self):
        """TASK-166 AC6: without the reviews the evidence is insufficient."""
        self.assertEqual(low_decision(None)[:2], ('INSUFFICIENT_EVIDENCE', 3))


if __name__ == '__main__':
    unittest.main()
