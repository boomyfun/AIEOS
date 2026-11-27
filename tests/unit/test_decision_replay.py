"""Unit tests of aieos_bootstrap.decision_replay (task TASK-139; erratum E1, decision D-6325): the replay of one logged
decision.execution record over stand-ins (a stand-in engine, a stand-in engine text, a stand-in inputs builder, a stand-in read), the
refusals of the configuration read, the engine file comparison, the command-line entry's plumbing, the zero-pin case, the refusal of
decision.acceptance lines, and what the module may not contain. The log of every case is the real log of the tree up to line 13, read
with pathlib's read_bytes; the engine text is the real engine's file; no test runs Git, starts a process, imports tempfile, subprocess
or shutil, or writes a file."""

import json
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import decision_replay, resume_check, violation

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[2]
LOG = (ROOT / '.aieos' / 'events.jsonl').read_bytes().replace(b'\r\n', b'\n').split(b'\n')[:13]
ENGINE_TEXT = (ROOT / 'src' / 'aieos_bootstrap' / 'resume_check.py').read_bytes().replace(b'\r\n', b'\n').decode('utf-8')
LOG13 = b'\n'.join(LOG) + b'\n'
RECORD = json.loads(LOG[12].decode('utf-8'))
PAYLOAD = RECORD['payload']
PIN = PAYLOAD['engine_identity']['code_sha256']
SRC = ROOT / 'src' / 'aieos_bootstrap' / 'decision_replay.py'
HEAD = '1e15ed11892393f940d9000fed6c6060b83961d9'
TIP = '7976d8a69a597d73ea77a4d321eff34dc2f95ee3'


class Engine:
    """A stand-in engine: its check returns a copy of the logged payload after the given changes."""
    INPUT_KEYS = frozenset({'task_id'})

    def __init__(self, change=None, raises=False, drop=None):
        self.change = change or {}
        self.raises = raises
        self.drop = drop
        self.__file__ = str(ROOT / 'src' / 'aieos_bootstrap' / 'resume_check.py')

    def check(self, inputs, code_sha256):
        if self.raises:
            raise ValueError('stand-in')
        out = json.loads(json.dumps(PAYLOAD))
        out.update(self.change)
        if self.drop is not None:
            del out[self.drop]
        return out


def log_with(**changes):
    """The log up to line 13 with the logged record's payload changed (the record is the real one otherwise)."""
    event = json.loads(LOG[12].decode('utf-8'))
    event['payload'].update(changes)
    line = json.dumps(event, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return b'\n'.join(LOG[:12] + [line]) + b'\n'


def text_both(repo, commit, read):
    return ENGINE_TEXT, None


def builder_ok(repo, head, task_id, cut_log, runtime, read):
    return {'task_id': task_id}, None


def replay(index=12, pins=None, log=LOG13, engine=None, text=text_both, builder=builder_ok, checked=TIP):
    return decision_replay.replay_execution('/repo', log, index, [PIN] if pins is None else pins, checked_commit=checked,
                                            engine=engine or Engine(), engine_text=text, build_inputs=builder)


class ReplayTests(unittest.TestCase):
    def test_pass(self):
        self.assertEqual(replay(), (True, []))

    def test_the_real_record_has_the_form_the_tests_rely_on(self):
        self.assertEqual((RECORD['type'], RECORD['seq'], PAYLOAD['log_seq'], PAYLOAD['head_commit']), ('decision.execution', 13, 12, HEAD))
        self.assertEqual(PIN, decision_replay._sha(ENGINE_TEXT))

    def test_a_changed_decision_fails(self):
        ok, found = replay(engine=Engine({'decision': 'CONTINUE'}))
        self.assertFalse(ok)
        self.assertIn('decision', found[0])

    def test_a_changed_record_id_fails(self):
        ok, found = replay(engine=Engine({'record_id': 'x' * 64}))
        self.assertFalse(ok)
        self.assertIn('record_id', found[0])

    def test_every_key_is_compared_the_probe_keys(self):
        for key in sorted(PAYLOAD):
            if key == 'engine_identity':
                continue
            ok, found = replay(engine=Engine({key: 'changed'}))
            self.assertFalse(ok, key)
            self.assertIn(key, found[0])

    def test_an_added_key_of_the_recomputed_record_fails(self):
        ok, found = replay(engine=Engine({'extra_key': 1}))
        self.assertFalse(ok)
        self.assertIn('extra_key', found[0])

    def test_only_the_python_value_differs_still_passes(self):
        ident = dict(PAYLOAD['engine_identity'], python='0.0.0')
        self.assertEqual(replay(engine=Engine({'engine_identity': ident})), (True, []))
        findings, notes = decision_replay.replay_detail('/repo', LOG13, 12, [PIN], checked_commit=TIP, engine=Engine({'engine_identity': ident}),
                                                       engine_text=text_both, build_inputs=builder_ok)
        self.assertEqual(findings, [])
        self.assertTrue(any('python' in n and '0.0.0' in n for n in notes))

    def test_a_changed_code_sha256_of_the_recomputed_record_fails(self):
        ident = dict(PAYLOAD['engine_identity'], code_sha256='0' * 64)
        ok, found = replay(engine=Engine({'engine_identity': ident}))
        self.assertFalse(ok)
        self.assertIn('engine_identity.code_sha256', found[0])

    def test_zero_accepted_engines_fails_every_record(self):
        ok, found = replay(pins=[])
        self.assertFalse(ok)
        self.assertTrue(any('accepted engine' in f and '0 accepted' in f for f in found))

    def test_an_engine_that_is_not_accepted_fails(self):
        ok, found = replay(pins=['1' * 64])
        self.assertFalse(ok)
        self.assertTrue(any('not an accepted engine' in f for f in found))

    def test_the_engine_at_head_commit_must_equal_the_record(self):
        ok, found = replay(text=lambda repo, commit, read: (ENGINE_TEXT + '\n', None))
        self.assertFalse(ok)
        self.assertTrue(any('head_commit is not the record' in f for f in found))

    def test_an_engine_that_differs_at_the_checked_commit_fails_closed(self):
        def text(repo, commit, read):
            return (ENGINE_TEXT, None) if commit == HEAD else (ENGINE_TEXT + '# later\n', None)
        ok, found = replay(text=text)
        self.assertFalse(ok)
        self.assertTrue(any('no historical-engine loader' in f for f in found))

    def test_a_missing_engine_at_head_commit_fails(self):
        ok, found = replay(text=lambda repo, commit, read: (None, ['no such file']))
        self.assertFalse(ok)
        self.assertTrue(any('engine at head_commit' in f for f in found))

    def test_a_checked_commit_that_is_not_a_commit_id_fails(self):
        ok, found = replay(checked='HEAD')
        self.assertFalse(ok)
        self.assertEqual(found, ['engine: the checked commit is not a commit id'])

    def test_a_refusal_of_the_inputs_fails(self):
        ok, found = replay(builder=lambda *a: (None, ['git_inputs: no']))
        self.assertFalse(ok)
        self.assertIn('inputs', found[0])

    def test_an_exception_of_the_engine_is_a_finding(self):
        ok, found = replay(engine=Engine(raises=True))
        self.assertFalse(ok)
        self.assertIn('raised ValueError', found[0])

    def test_an_exception_of_a_reader_is_a_finding(self):
        def boom(*a):
            raise RuntimeError('boom')
        ok, found = replay(builder=boom)
        self.assertFalse(ok)
        self.assertIn('raised RuntimeError', found[0])

    def test_an_exception_of_the_engine_text_reader_is_a_finding(self):
        def boom(repo, commit, read):
            raise OSError('boom')
        ok, found = replay(text=boom)
        self.assertEqual((ok, found), (False, ['replay: a step raised OSError']))

    def test_an_exception_of_records_check_log_is_a_finding(self):
        with mock.patch.object(decision_replay.records, 'check_log', side_effect=RuntimeError('boom')):
            ok, found = replay()
        self.assertEqual((ok, found), (False, ['replay: a step raised RuntimeError']))

    def test_an_exception_of_the_read_function_is_a_finding(self):
        def boom(repo, args, timeout):
            raise OSError('boom')
        ok, found = decision_replay.replay_execution('/repo', LOG13, 12, [PIN], read=boom, engine=Engine(), build_inputs=builder_ok)
        self.assertFalse(ok)
        self.assertTrue(found and all(isinstance(f, str) and f for f in found))

    def test_the_arguments_are_checked(self):
        self.assertFalse(replay(index=-1)[0])
        self.assertFalse(replay(index=99)[0])
        self.assertEqual(decision_replay.replay_execution('/repo', 'text', 12, [PIN], engine=Engine()),
                         (False, ['argument: log_bytes is not bytes or index is not a non-negative int']))
        self.assertEqual(decision_replay.replay_execution('/repo', LOG13, 12, 'abc', engine=Engine()),
                         (False, ['argument: accepted_engines is not a list of 64-hex strings']))
        self.assertEqual(decision_replay.replay_execution('/repo', LOG13, 12, ['short'], engine=Engine()),
                         (False, ['argument: accepted_engines is not a list of 64-hex strings']))

    def test_a_log_that_check_log_refuses_fails(self):
        ok, found = replay(log=LOG13 + b'not json\n')
        self.assertFalse(ok)
        self.assertIn('log:', found[0])

    def test_a_line_that_is_not_a_decision_record_fails(self):
        ok, found = replay(index=11)
        self.assertFalse(ok)
        self.assertIn('decision.execution', found[0])

    def test_a_seq_that_is_not_log_seq_plus_one_fails(self):
        changed = json.loads(LOG[12].decode('utf-8'))
        changed['payload']['log_seq'] = 11
        line = json.dumps(changed, sort_keys=True, separators=(',', ':')).encode('utf-8')
        ok, found = replay(log=b'\n'.join(LOG[:12] + [line]) + b'\n')
        self.assertFalse(ok)
        self.assertEqual(found, ['record: seq 13 is not log_seq + 1 (12)'])

    def test_a_record_at_the_first_line_has_no_cut_log(self):
        # a one-line log whose only line is the real record with seq 1 and log_seq 0: records.check_log accepts it, so the
        # `index == 0` branch of the cut is the one that fires
        first = json.loads(LOG[12].decode('utf-8'))
        first['seq'] = 1
        first['payload']['log_seq'] = 0
        log = json.dumps(first, sort_keys=True, separators=(',', ':')).encode('utf-8') + b'\n'
        ok, found = replay(index=0, log=log)
        self.assertFalse(ok)
        self.assertEqual(found, ['log: a record on the first line has no earlier line to recompute from'])

    def test_a_logged_key_that_the_recomputed_record_lacks_fails(self):
        ok, found = replay(engine=Engine(drop='subject'))
        self.assertFalse(ok)
        self.assertIn('subject', found[0])

    def test_an_extra_key_whose_value_is_the_old_absent_marker_still_fails(self):
        ok, found = replay(engine=Engine({'extra_key': '<absent>'}))
        self.assertFalse(ok)
        self.assertIn('extra_key', found[0])

    def test_values_are_compared_by_their_json_type(self):
        checks = json.loads(json.dumps(PAYLOAD['checks']))
        self.assertEqual(checks[0]['check'], 1)
        checks[0]['check'] = True          # True == 1 in Python; the canonical JSON texts differ
        ok, found = replay(engine=Engine({'checks': checks}))
        self.assertFalse(ok)
        self.assertIn('checks', found[0])
        ok, found = replay(engine=Engine({'log_seq': 12.0}))
        self.assertFalse(ok)
        self.assertIn('log_seq', found[0])

    def test_inputs_with_other_keys_than_the_engines_fail(self):
        ok, found = replay(builder=lambda repo, head, task_id, cut_log, runtime, read: ({'task_id': task_id, 'extra': 1}, None))
        self.assertFalse(ok)
        self.assertEqual(found, ['inputs: the keys are not exactly the engine\'s INPUT_KEYS'])
        ok, found = replay(builder=lambda repo, head, task_id, cut_log, runtime, read: ({}, None))
        self.assertEqual((ok, found), (False, ['inputs: the keys are not exactly the engine\'s INPUT_KEYS']))

    def test_a_changed_logged_head_commit_fails_on_the_engine_at_that_commit(self):
        def text(repo, commit, read):
            return (ENGINE_TEXT, None) if commit == HEAD else ('another engine\n', None)
        ok, found = replay(log=log_with(head_commit='b' * 40), text=text)
        self.assertFalse(ok)
        self.assertTrue(any('head_commit is not the record' in f for f in found), found)

    def test_a_changed_logged_code_sha256_fails(self):
        ident = dict(PAYLOAD['engine_identity'], code_sha256='2' * 64)
        ok, found = replay(log=log_with(engine_identity=ident))
        self.assertFalse(ok)
        self.assertTrue(any('not an accepted engine' in f for f in found), found)

    def test_a_changed_logged_record_id_fails_on_the_record_id(self):
        ok, found = replay(log=log_with(record_id='3' * 64))
        self.assertFalse(ok)
        self.assertEqual(found, ['record: the recomputed record differs from the logged one at: record_id'])

    def test_a_logged_head_commit_that_is_not_a_commit_id_fails(self):
        # records.check_log refuses the form of head_commit before the module's own commit-id check is reached; the finding names it
        ok, found = replay(log=log_with(head_commit='not-a-commit'))
        self.assertEqual((ok, found), (False, ['log: line 13: 6.4:head_commit: payload head_commit is not a full lowercase hex commit id']))


class ConfigAndPathTests(unittest.TestCase):
    def test_config_refused_keys(self):
        self.assertEqual(decision_replay.config_refused(b''), ([], None))
        self.assertEqual(decision_replay.config_refused(b'core.bare\nfalse\0'), ([], None))
        self.assertEqual(decision_replay.config_refused(b'Filter.lfs.clean\nx\0'), ([b'Filter.lfs.clean'], None))
        self.assertEqual(decision_replay.config_refused(b'CORE.WorkTree\n/x\0'), ([b'CORE.WorkTree'], None))
        self.assertEqual(decision_replay.config_refused(b'core.worktreex\n1\0'), ([], None))

    def test_config_refused_malformed(self):
        self.assertIsNone(decision_replay.config_refused(b'core.bare\nfalse')[0])
        self.assertIsNone(decision_replay.config_refused('text')[0])
        self.assertIsNone(decision_replay.config_refused(b'\nvalue\0')[0])

    def test_engine_file_matches_compares_the_normalised_paths(self):
        # this test claims dots and separators only: os.path.normcase is the identity on a POSIX runner, so a letter-case
        # case would test the platform, not the module (the module's docstring states that it uses normcase on both sides)
        repo = str(ROOT)
        want = str(ROOT / 'src' / 'aieos_bootstrap' / 'resume_check.py')
        self.assertTrue(decision_replay.engine_file_matches(want, repo))
        # string forms (pathlib would drop the dot and the dotdot parts before the module sees them)
        self.assertTrue(decision_replay.engine_file_matches(str(ROOT) + '/src/./aieos_bootstrap/resume_check.py', repo))
        self.assertTrue(decision_replay.engine_file_matches(str(ROOT) + '/src/x/../aieos_bootstrap/resume_check.py', repo))
        self.assertFalse(decision_replay.engine_file_matches(str(ROOT) + '/src/x/aieos_bootstrap/resume_check.py', repo))
        self.assertFalse(decision_replay.engine_file_matches(str(ROOT / 'other' / 'resume_check.py'), repo))
        self.assertFalse(decision_replay.engine_file_matches(None, repo))


def clean_read(repo, args, timeout):
    if args[0] == 'config':
        return {'exit': 0, 'out': b'core.bare\nfalse\0', 'err': b'', 'error': None}
    if args[0] == 'status':
        return {'exit': 0, 'out': b'', 'err': b'', 'error': None}
    return {'exit': 0, 'out': (TIP + '\n').encode(), 'err': b'', 'error': None}


class MainTests(unittest.TestCase):
    def run_main(self, argv, read=clean_read, engine=None, paths=None, files=None, detail=None, engine_text=ENGINE_TEXT, no_engine=False):
        lines = []
        paths = ['a/b.py', '.aieos/events.jsonl'] if paths is None else paths
        text = (LOG13 + b'{"type":"decision.acceptance","seq":14,"payload":{"record_id":"r"}}\n').decode('utf-8') if files is None else files

        def read_file(repo, commit, path, read=None):
            return ({'blob': 'b', 'text': engine_text if path == decision_replay.ENGINE_PATH else text}, None)
        with mock.patch.object(decision_replay.base_files, 'list_paths', return_value=(paths, None)), \
                mock.patch.object(decision_replay.base_files, 'read_file', side_effect=read_file), \
                mock.patch.object(decision_replay, 'replay_detail', detail or (lambda *a, **k: ([], ['engine_identity.python recorded x, recomputed y (reported only)']))):
            rc = decision_replay.main(argv, read=read, out=lines.append, engine=None if no_engine else (engine or Engine()))
        return rc, lines

    def test_a_replayed_record_prints_replayed_and_a_note(self):
        rc, lines = self.run_main([str(ROOT), PIN], files=LOG13.decode('utf-8'))
        self.assertEqual(rc, 0)
        self.assertTrue(any(l.startswith('REPLAYED ') and l.endswith(':13 ok') for l in lines))
        self.assertTrue(any(l.startswith('NOTE ') for l in lines))
        self.assertIn('decision records: 1, replayed and passed: 1, failed: 0', lines[-1])

    def test_an_acceptance_line_is_not_replayed_and_fails(self):
        # records.check_log is stubbed to find nothing, so the exit code 1 comes from the acceptance rule alone
        class NoFindings:
            lines = []

            def findings(self):
                return []
        with mock.patch.object(decision_replay.records, 'check_log', return_value=NoFindings()):
            rc, lines = self.run_main([str(ROOT), PIN])
        self.assertEqual(rc, 1)
        self.assertTrue(any(l.startswith('NOT REPLAYED: decision.acceptance') for l in lines))
        self.assertFalse(any(': log: line ' in l for l in lines))
        self.assertIn('failed: 1', lines[-1])

    def test_the_engine_is_not_imported_with_zero_pins(self):
        with mock.patch.object(decision_replay, '_engine_module', side_effect=AssertionError('the engine was imported')) as imp:
            rc, lines = self.run_main([str(ROOT)], files=LOG13.decode('utf-8'), no_engine=True)
        self.assertEqual(rc, 1)
        imp.assert_not_called()
        self.assertTrue(any('not an accepted engine (0 accepted); it is not imported' in l for l in lines), lines)

    def test_the_engine_is_not_imported_when_its_hash_is_not_a_pin(self):
        with mock.patch.object(decision_replay, '_engine_module', side_effect=AssertionError('the engine was imported')) as imp:
            rc, lines = self.run_main([str(ROOT), PIN], files=LOG13.decode('utf-8'), engine_text=ENGINE_TEXT + '# changed\n', no_engine=True)
        self.assertEqual(rc, 1)
        imp.assert_not_called()

    def test_the_engine_is_imported_once_after_the_gates_when_its_hash_is_a_pin(self):
        stand_in = Engine()
        with mock.patch.object(decision_replay, '_engine_module', return_value=stand_in) as imp:
            rc, lines = self.run_main([str(ROOT), PIN], files=LOG13.decode('utf-8'), no_engine=True)
        self.assertEqual(rc, 0, lines)
        imp.assert_called_once_with()

    def test_the_engine_is_not_imported_when_the_tree_gate_fails(self):
        def read(repo, args, timeout):
            if args[0] == 'status':
                return {'exit': 0, 'out': b' M x\0', 'err': b'', 'error': None}
            return clean_read(repo, args, timeout)
        with mock.patch.object(decision_replay, '_engine_module', side_effect=AssertionError('the engine was imported')) as imp:
            rc, lines = self.run_main([str(ROOT), PIN], read=read, files=LOG13.decode('utf-8'), no_engine=True)
        self.assertEqual(rc, 1)
        imp.assert_not_called()

    def test_record_text_is_escaped_in_the_printed_lines(self):
        rc, lines = self.run_main([str(ROOT), PIN], files=LOG13.decode('utf-8'), paths=['x\nFAKE LINE/events.jsonl'])
        self.assertTrue(all('\n' not in l for l in lines))
        self.assertFalse(any(l.startswith('FAKE LINE') for l in lines))

    def test_notes_are_printed_on_a_failure_too(self):
        rc, lines = self.run_main([str(ROOT), PIN], files=LOG13.decode('utf-8'),
                                  detail=lambda *a, **k: (['record: differs at x'], ['engine_identity.python recorded 1, recomputed 2 (reported only)']))
        self.assertEqual(rc, 1)
        self.assertTrue(any(l.startswith('NOTE engine_identity.python') for l in lines))

    def test_a_failed_replay_fails(self):
        rc, lines = self.run_main([str(ROOT), PIN], files=LOG13.decode('utf-8'), detail=lambda *a, **k: (['record: differs at x'], []))
        self.assertEqual(rc, 1)
        self.assertTrue(any(l.startswith('FAIL ') for l in lines))

    def test_no_decision_record_passes(self):
        rc, lines = self.run_main([str(ROOT), PIN], files=(b'\n'.join(LOG[:12]) + b'\n').decode('utf-8'))
        self.assertEqual(rc, 0, lines)
        self.assertIn('decision records: 0', lines[-1])

    def test_an_unparsable_line_that_names_a_decision_fails(self):
        rc, lines = self.run_main([str(ROOT), PIN], files='decision.execution but not json\n')
        self.assertEqual(rc, 1)
        self.assertTrue(any('an unparsable line names a decision record' in l for l in lines))

    def test_a_line_that_is_not_an_object_and_names_a_decision_fails(self):
        rc, lines = self.run_main([str(ROOT), PIN], files='["decision.execution"]\n')
        self.assertEqual(rc, 1)
        self.assertTrue(any('not an object names a decision record' in l for l in lines))

    def test_a_log_that_check_log_refuses_fails_even_without_a_decision_record(self):
        rc, lines = self.run_main([str(ROOT), PIN], files='{"type":"task.drafted","seq":1}\n')
        self.assertEqual(rc, 1)
        self.assertTrue(any(l.startswith('FAIL: ') and ': log: line ' in l for l in lines))

    def test_the_entry_prints_its_limits_before_the_summary(self):
        rc, lines = self.run_main([str(ROOT), PIN], files=LOG13.decode('utf-8'))
        limits = [l for l in lines if l.startswith('LIMIT: ')]
        self.assertEqual(len(limits), len(decision_replay.LIMITS))
        self.assertTrue(any('historical-engine loader' in l for l in limits))
        self.assertTrue(any('NOT what head_commit' in l for l in limits))
        self.assertTrue(any('skip-worktree' in l for l in limits))
        self.assertLess(lines.index(limits[-1]), len(lines) - 1)

    def test_an_exception_inside_the_entry_is_a_failure_line_and_exit_one(self):
        lines = []
        with mock.patch.object(decision_replay.base_files, 'list_paths', side_effect=RecursionError('deep')):
            rc = decision_replay.main([str(ROOT), PIN], read=clean_read, out=lines.append, engine=Engine())
        self.assertEqual(rc, 1)
        self.assertEqual(lines, ['FAIL: the entry stopped: RecursionError'])

    def test_with_no_event_log_the_entry_notes_it_and_passes(self):
        rc, lines = self.run_main([str(ROOT), PIN], paths=['a/b.py'])
        self.assertEqual(rc, 0)
        self.assertTrue(any(l.startswith('NOTE: no tracked file is named events.jsonl') for l in lines))

    def test_arguments(self):
        # every case uses a log text that passes (LOG13), so the exit code and the printed lines come from the argument gate alone
        good = LOG13.decode('utf-8')
        rc, lines = self.run_main([], files=good)
        self.assertEqual((rc, lines), (1, ['usage: decision_replay <repo> [--governor-pin <sha256>] [<accepted engine sha256> ...]']))
        rc, lines = self.run_main([str(ROOT), 'zz'], files=good)
        self.assertEqual((rc, lines), (1, ['FAIL: an accepted engine argument is not 64 lowercase hex characters']))
        rc, lines = self.run_main(['relative/path'], files=good)
        self.assertEqual(rc, 1)
        self.assertTrue(lines and lines[0].startswith('FAIL: repo is not an absolute path'), lines)

    def test_the_engine_file_must_be_the_repositorys(self):
        other = Engine()
        other.__file__ = str(ROOT / 'elsewhere' / 'resume_check.py')
        rc, lines = self.run_main([str(ROOT), PIN], engine=other, files=LOG13.decode('utf-8'))
        self.assertEqual((rc, lines), (1, ["FAIL: the engine file is not the repository's src/aieos_bootstrap/resume_check.py"]))

    def test_a_filter_key_in_the_configuration_fails(self):
        def read(repo, args, timeout):
            if args[0] == 'config':
                return {'exit': 0, 'out': b'filter.x.clean\ny\0', 'err': b'', 'error': None}
            return clean_read(repo, args, timeout)
        rc, lines = self.run_main([str(ROOT), PIN], read=read, files=LOG13.decode('utf-8'))
        self.assertEqual((rc, lines), (1, ['FAIL: tree: the configuration names 1 filter driver or work tree keys']))

    def test_a_changed_working_tree_fails(self):
        def read(repo, args, timeout):
            if args[0] == 'status':
                return {'exit': 0, 'out': b' M x\0', 'err': b'', 'error': None}
            return clean_read(repo, args, timeout)
        rc, lines = self.run_main([str(ROOT), PIN], read=read)
        self.assertEqual(rc, 1)
        self.assertTrue(any('changes against HEAD' in l for l in lines))

    def test_the_status_form_names_dot_git_only(self):
        seen = []

        def read(repo, args, timeout):
            seen.append(list(args))
            return clean_read(repo, args, timeout)
        self.run_main([str(ROOT), PIN], read=read, files='')
        status = [a for a in seen if a[0] == 'status'][0]
        self.assertEqual(status[-1], ':(exclude).git')
        self.assertLess([a[0] for a in seen].index('config'), [a[0] for a in seen].index('status'))

    def test_a_refused_listing_fails(self):
        lines = []
        with mock.patch.object(decision_replay.base_files, 'list_paths', return_value=(None, ['a symbolic link'])):
            rc = decision_replay.main([str(ROOT), PIN], read=clean_read, out=lines.append, engine=Engine())
        self.assertEqual(rc, 1)
        self.assertTrue(any('tree listing' in l for l in lines))

    def test_a_refused_read_of_a_log_fails(self):
        lines = []

        def read_file(repo, commit, path, read=None):
            # only the log path is refused: the engine path is read, so the engine gate passes and the exit code comes from the log read
            if path == decision_replay.ENGINE_PATH:
                return {'blob': 'b', 'text': ENGINE_TEXT}, None
            return None, ['too big']
        with mock.patch.object(decision_replay.base_files, 'list_paths', return_value=(['x/events.jsonl'], None)), \
                mock.patch.object(decision_replay.base_files, 'read_file', side_effect=read_file):
            rc = decision_replay.main([str(ROOT), PIN], read=clean_read, out=lines.append, engine=Engine())
        self.assertEqual(rc, 1)
        self.assertIn('FAIL: x/events.jsonl: too big', lines)
        self.assertFalse(any(l.startswith('FAIL') and 'accepted engine' in l for l in lines), lines)

    def test_only_files_named_events_jsonl_are_read(self):
        read_paths = []

        def read_file(repo, commit, path, read=None):
            read_paths.append(path)
            return {'blob': 'b', 'text': ''}, None
        with mock.patch.object(decision_replay.base_files, 'list_paths', return_value=(['events.jsonl', 'd/events.jsonl', 'd/myevents.jsonl', 'd/events.jsonl.bak'], None)), \
                mock.patch.object(decision_replay.base_files, 'read_file', side_effect=read_file):
            decision_replay.main([str(ROOT), PIN], read=clean_read, out=lambda s: None, engine=Engine())
        self.assertEqual([p for p in read_paths if p != decision_replay.ENGINE_PATH], ['events.jsonl', 'd/events.jsonl'])


class NoFindings:
    lines = []

    def findings(self):
        return []


DETECTED = {'type': 'violation.detected', 'event_id': 'launch-x/pretool/t1', 'task_id': 'TASK-136', 'seq': 14,
            'payload': {'blocking_kind': 'violation', 'evidence_type': 'shell_not_allowed', 'subject': 'TASK-136'}}
STOP = {'type': 'decision.execution', 'event_id': 'launch-x/pretool/t1/decision', 'task_id': 'TASK-136', 'seq': 15,
        'payload': {'decision': violation.DECISION, 'recorder': violation.RECORDER, 'refers_to': 'launch-x/pretool/t1',
                    'record_id': 'launch-x/pretool/t1/decision-record', 'subject': 'TASK-136'}}


def _line(event):
    return json.dumps(event, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _changed(base, **top):
    event = json.loads(json.dumps(base))
    event.update(top)
    return event


def _payload_changed(base, **changes):
    event = json.loads(json.dumps(base))
    event['payload'].update(changes)
    return event


def _log_with_violation(detected=DETECTED, stop=STOP):
    # the log of the real tree up to line 13, then the violation.detected line and the record of the violation path
    return LOG13 + _line(detected) + b'\n' + _line(stop) + b'\n'


class ViolationPathTests(unittest.TestCase):
    # Each condition of the form that violation_path_record requires has a test below that fails if that condition ALONE is removed (the mutation check of the worker, build2_t141, removes each in turn).
    def lines_with(self, detected=DETECTED, stop=STOP):
        return _log_with_violation(detected, stop).split(b'\n')

    def recognised(self, detected=DETECTED, stop=STOP):
        return decision_replay.violation_path_record(self.lines_with(detected, stop), 14)

    def test_the_form_that_the_violation_path_writes_is_recognised(self):
        self.assertTrue(self.recognised())

    def test_a_resume_check_record_is_not_a_violation_path_record(self):
        self.assertFalse(decision_replay.violation_path_record(LOG13.split(b'\n'), 12))

    # NEGATIVES: (what is changed, the earlier line, the record, a substring that the entry's own output must hold when it replays and fails the record)
    NEGATIVES = (
        ('the decision is another one', DETECTED, _payload_changed(STOP, decision='CONTINUE'), ': record'),
        ('the recorder is another one', DETECTED, _payload_changed(STOP, recorder='another recorder'), ': record'),
        ('the record carries a head_commit', DETECTED, _payload_changed(STOP, head_commit=HEAD), ': record'),
        ('the event_id is not refers_to plus /decision (refers_to still names the earlier line)', DETECTED, _changed(STOP, event_id='another id'), ': record'),
        ('refers_to and event_id both name a line that does not exist', DETECTED, _changed(_payload_changed(STOP, refers_to='nothing'), event_id='nothing/decision'), ': record'),
        ('the earlier line is not of type violation.detected (its event_id still matches)', _changed(DETECTED, type='record.added'), STOP, ': record'),
        ('the earlier line is of another task', _changed(DETECTED, task_id='TASK-137'), STOP, ': record'),
        ('the record is of another type with the same form', DETECTED, _changed(STOP, type='decision.acceptance'), 'NOT REPLAYED: decision.acceptance'),
    )

    def test_each_condition_of_the_form_is_tested_alone(self):
        for what, detected, stop, _ in self.NEGATIVES:
            with self.subTest(what):
                self.assertFalse(self.recognised(detected, stop), what)

    def test_the_earlier_line_must_stand_before_the_record(self):
        log = LOG13 + _line(STOP) + b'\n' + _line(DETECTED) + b'\n'
        self.assertFalse(decision_replay.violation_path_record(log.split(b'\n'), 13))

    def test_unusable_lines_are_never_recognised_and_never_raise(self):
        for line in (b'not json', b'[1, 2]', b'\xff\xfe', b'{"type":"decision.execution","payload":5}', b'', b'{"type":"decision.execution","task_id":3}'):
            self.assertFalse(decision_replay.violation_path_record([line], 0), line)
        self.assertFalse(decision_replay.violation_path_record([], 0))
        self.assertFalse(decision_replay.violation_path_record([_line(STOP)], 5))
        self.assertFalse(decision_replay.violation_path_record([_line(STOP)], -5))

    def entry(self, text, argv=None, detail=None):
        # the entry over a synthetic log; check_log is stubbed (the lines are synthetic); with no detail the REAL replay_detail runs
        lines = []

        def read_file(repo, commit, path, read=None):
            return ({'blob': 'b', 'text': ENGINE_TEXT if path == decision_replay.ENGINE_PATH else text}, None)
        with mock.patch.object(decision_replay.base_files, 'list_paths', return_value=(['.aieos/events.jsonl'], None)), \
                mock.patch.object(decision_replay.base_files, 'read_file', side_effect=read_file), \
                mock.patch.object(decision_replay.records, 'check_log', return_value=NoFindings()):
            if detail is not None:
                with mock.patch.object(decision_replay, 'replay_detail', detail):
                    rc = decision_replay.main(argv or [str(ROOT), PIN], read=clean_read, out=lines.append, engine=Engine())
            else:
                rc = decision_replay.main(argv or [str(ROOT), PIN], read=clean_read, out=lines.append, engine=Engine())
        return rc, lines

    def test_the_entry_reports_the_record_not_replayed_and_counts_it_apart(self):
        rc, lines = self.entry(_log_with_violation().decode('utf-8'), detail=lambda *a, **k: ([], []))
        self.assertEqual(rc, 0, lines)
        self.assertTrue(any(l.startswith('REPLAYED ') and l.endswith(':13 ok') for l in lines))
        self.assertTrue(any(l.startswith('NOT REPLAYED: violation-path record (no Resume Check ran) ') and l.endswith(':15') for l in lines), lines)
        self.assertIn('decision records: 2, replayed and passed: 1, failed: 0, not replayed (violation path): 1', lines[-1])

    def test_a_log_with_only_the_recognised_record_exits_0_with_nothing_replayed(self):
        rc, lines = self.entry((_line(DETECTED) + b'\n' + _line(STOP) + b'\n').decode('utf-8'))
        self.assertEqual(rc, 0, lines)
        self.assertFalse(any(l.startswith('REPLAYED ') for l in lines))
        self.assertIn('decision records: 1, replayed and passed: 0, failed: 0, not replayed (violation path): 1', lines[-1])

    def test_with_no_accepted_engine_the_recognised_record_fails_too(self):
        # the engine gate comes first: with zero accepted pins every decision.execution line fails, a recognised one included
        rc, lines = self.entry((_line(DETECTED) + b'\n' + _line(STOP) + b'\n').decode('utf-8'), argv=[str(ROOT)])
        self.assertEqual(rc, 1, lines)
        self.assertFalse(any(l.startswith('NOT REPLAYED: violation-path record') for l in lines))
        self.assertTrue(any(l.startswith('FAIL ') and 'not an accepted engine' in l for l in lines), lines)
        self.assertIn('decision records: 1, replayed and passed: 0, failed: 1, not replayed (violation path): 0', lines[-1])

    def test_each_negative_fails_through_the_real_record_finding(self):
        # the REAL replay_detail runs (no stub): the record of the log is replayed and fails through the record finding of _record (or, for another type, the acceptance rule)
        for what, detected, stop, expected in self.NEGATIVES:
            with self.subTest(what):
                rc, lines = self.entry((_line(detected) + b'\n' + _line(stop) + b'\n').decode('utf-8'))
                self.assertEqual(rc, 1, (what, lines))
                self.assertFalse(any(l.startswith('NOT REPLAYED: violation-path record') for l in lines), (what, lines))
                self.assertTrue(any(expected in l and (l.startswith('FAIL ') or l.startswith('NOT REPLAYED')) for l in lines), (what, lines))
                self.assertIn('failed: 1, not replayed (violation path): 0', lines[-1])

    def test_a_late_violation_detected_line_fails_the_record_through_the_real_finding(self):
        rc, lines = self.entry((_line(STOP) + b'\n' + _line(DETECTED) + b'\n').decode('utf-8'))
        self.assertEqual(rc, 1, lines)
        self.assertTrue(any(l.startswith('FAIL ') and ': record' in l for l in lines), lines)

    def test_an_acceptance_line_still_fails_beside_a_recognised_record(self):
        text = _log_with_violation().decode('utf-8') + '{"type":"decision.acceptance","seq":16,"payload":{"record_id":"r"}}\n'
        rc, lines = self.entry(text, detail=lambda *a, **k: ([], []))
        self.assertEqual(rc, 1)
        self.assertTrue(any(l.startswith('NOT REPLAYED: decision.acceptance') for l in lines))
        self.assertIn('failed: 1, not replayed (violation path): 1', lines[-1])

    def test_the_printed_limits_name_the_exception_and_its_forged_pair_limit(self):
        rc, lines = self.entry(_log_with_violation().decode('utf-8'), detail=lambda *a, **k: ([], []))
        self.assertTrue(any(l.startswith('LIMIT: ') and 'violation-path record' in l and 'forged pair' in l for l in lines), lines)

    def test_the_docstring_states_the_exception_its_limit_and_the_gate_order(self):
        doc = ' '.join(decision_replay.__doc__.split())
        for part in ('TASK-141', 'violation_path_record', 'NOT REPLAYED: violation-path record', 'no Resume Check ran', 'a forged pair of such lines',
                     'a recognised record included', 'the module violation'):
            self.assertIn(part, doc)

    def test_the_constants_are_taken_from_the_violation_module(self):
        text = SRC.read_bytes().decode('utf-8')
        self.assertIn('violation.DECISION', text)
        self.assertIn('violation.RECORDER', text)
        self.assertNotIn('STOP: violation', text)


class CarriedFindingTests(unittest.TestCase):
    """TASK-167 AC8: DEF-0144 items 1, 2, 3 and 16."""
    lines_with = ViolationPathTests.lines_with
    recognised = ViolationPathTests.recognised
    entry = ViolationPathTests.entry

    def test_a_task_id_that_is_not_a_text_is_not_recognised(self):
        self.assertFalse(self.recognised(_changed(DETECTED, task_id=3), _changed(STOP, task_id=3)))

    def test_an_earlier_line_that_cannot_be_read_or_is_no_object_is_skipped(self):
        for line in (b'not json', b'[1]', b'7'):
            with self.subTest(line):
                self.assertTrue(decision_replay.violation_path_record([line, _line(DETECTED), _line(STOP)], 2))

    def test_a_negative_index_is_never_recognised(self):
        self.assertTrue(decision_replay.violation_path_record([_line(DETECTED), _line(STOP)], 1))
        self.assertFalse(decision_replay.violation_path_record([_line(DETECTED), _line(STOP)], -1))

    def test_an_engine_pin_that_does_not_match_fails_the_recognised_record_too(self):
        rc, lines = self.entry((_line(DETECTED) + b'\n' + _line(STOP) + b'\n').decode('utf-8'), argv=[str(ROOT), '0' * 64])
        self.assertEqual(rc, 1, lines)
        self.assertFalse(any(l.startswith('NOT REPLAYED: violation-path record') for l in lines))
        self.assertIn('decision records: 1, replayed and passed: 0, failed: 1, not replayed (violation path): 0', lines[-1])

    def test_two_records_that_are_not_recognised_both_fail(self):
        first = _payload_changed(STOP, decision='CONTINUE')
        second = _changed(_payload_changed(STOP, recorder='another recorder'), seq=16, event_id='launch-x/pretool/t1/decision-2')
        rc, lines = self.entry((_line(DETECTED) + b'\n' + _line(first) + b'\n' + _line(second) + b'\n').decode('utf-8'))
        self.assertEqual(rc, 1, lines)
        self.assertIn('decision records: 2, replayed and passed: 0, failed: 2, not replayed (violation path): 0', lines[-1])


class SourceTests(unittest.TestCase):
    def test_the_module_has_no_dynamic_act_and_names_no_state_folder(self):
        import ast
        text = SRC.read_bytes().decode('utf-8')
        names = {n.id for n in ast.walk(ast.parse(text)) if isinstance(n, ast.Name)}
        self.assertFalse(names & {'exec', 'eval', 'compile', '__import__', 'open', 'input', 'breakpoint', '__builtins__'})
        self.assertNotIn('.' + 'aieos', text)
        for word in ('MEAS' + 'URED', 'ENFOR' + 'CED', 'GUARAN' + 'TEED'):
            self.assertNotIn(word, text)
        mods = {a.name.split('.')[0] for n in ast.walk(ast.parse(text)) if isinstance(n, ast.Import) for a in n.names}
        mods |= {n.module.split('.')[0] for n in ast.walk(ast.parse(text)) if isinstance(n, ast.ImportFrom) and n.module}
        self.assertFalse(mods & {'importlib', 'subprocess', 'tempfile', 'shutil', 'sqlite3', 'builtins', 'pickle'})

    def test_the_docstring_states_the_erratum_and_the_limits(self):
        doc = ' '.join(decision_replay.__doc__.split())
        for part in ('erratum E1', 'D-6325', 'D-6327', 'no historical-engine loader', 'NOT that it is what head_commit', 'no skip list',
                     'the one name the form needs', 'decision.acceptance', 'not atomically', 'matched by its text', 'lazy fetch', 'skip-worktree', '-B -P', 'refs/replace', 'erratum E1.7',
                     'canonical JSON text'):
            self.assertIn(part, doc)

    def test_the_module_imports_no_engine_or_reader_at_load(self):
        for name in ('resume_check', 'execution', 'resume_inputs', 'resume_log_inputs'):
            self.assertFalse(hasattr(decision_replay, name), name)

    def test_the_lazy_engine_import_is_the_checked_trees_resume_check(self):
        self.assertIs(decision_replay._engine_module(), resume_check)

    def test_the_safe_path_guard_reads_the_flag_without_failing_on_an_old_python(self):
        class Flags:
            safe_path = True
        self.assertTrue(decision_replay._safe_path_ok(Flags()))
        Flags.safe_path = False
        self.assertFalse(decision_replay._safe_path_ok(Flags()))
        self.assertFalse(decision_replay._safe_path_ok(object()))
        self.assertFalse(decision_replay._safe_path_ok(None))

    def test_the_guard_stands_before_the_modules_other_imports(self):
        text = SRC.read_bytes().decode('utf-8')
        guard = text.index("if __name__ == '__main__' and not _safe_path_ok(sys.flags):")
        for needle in ('import datetime', 'import hashlib', 'import json', 'import aieos_bootstrap', 'from aieos_bootstrap import'):
            self.assertLess(guard, text.index('\n' + needle), needle)

    def test_replay_execution_with_no_engine_refuses_and_imports_nothing(self):
        with mock.patch.object(decision_replay, '_engine_module', side_effect=AssertionError('the engine was imported')) as imp:
            ok, found = decision_replay.replay_execution('/repo', LOG13, 12, [PIN], checked_commit=TIP, engine_text=text_both, build_inputs=builder_ok)
        self.assertEqual(ok, False)
        self.assertTrue(found and found[0].startswith('engine: no engine was given'))
        imp.assert_not_called()


if __name__ == '__main__':
    unittest.main()
