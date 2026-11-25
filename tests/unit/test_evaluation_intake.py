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

    def test_the_public_names_are_exactly_two(self):
        public = set()
        for node in self.tree().body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith('_'):
                public.add(node.name)
            elif isinstance(node, ast.Assign):
                public.update(t.id for t in node.targets if isinstance(t, ast.Name) and not t.id.startswith('_'))
        self.assertEqual(public, {'read_ci_data', 'manifest'})
        attrs = {n for n in dir(evaluation_intake) if not n.startswith('_')}
        self.assertEqual(attrs, {'read_ci_data', 'manifest', 'hashlib', 'json', 're', 'ci_evidence',
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


if __name__ == '__main__':
    unittest.main()
