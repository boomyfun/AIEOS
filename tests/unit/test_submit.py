"""Unit tests of aieos_bootstrap.submit (task TASK-025, its rules R1 to R8); every rule has at least one passing case
and one failing case. The Git reader and the writer's functions are replaced by stand-ins that record their calls, so
no git starts and no file is touched here. Each test names the criteria it stands for in its own docstring."""

import ast
import datetime
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import gitread
from aieos_bootstrap import submit
from aieos_bootstrap import writer

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / 'src' / 'aieos_bootstrap' / 'submit.py'
FS_ROOT = str(ROOT / 'no-such-state-root')
REPO = str(ROOT)
COMMIT = 'a' * 40
TREE = 'b' * 40
TASK = 'TASK-025'
NOW = datetime.datetime(2026, 10, 12, 9, 30, 0, tzinfo=datetime.timezone.utc)
FENCE = {'epoch': 'e0', 'counter': 7}
HEADER = ('tree %s\nauthor Tester <tester> 1700000000 +0000\ncommitter Tester <tester> 1700000000 +0000\n\n' % TREE)


def commit_bytes(message):
    return (HEADER + message).encode('utf-8')


GOOD = 'Subject line\n\nBody text.\n\nAIEOS-Task: TASK-025\nAIEOS-Fence: e0:7\n'


class Reader:
    """A stand-in for gitread.run: answers cat-file -t and cat-file -p from the values given."""

    def __init__(self, message=GOOD, kind=b'commit\n', t=None, p=None, raises=None):
        self.calls = []
        self.t = t if t is not None else {'exit': 0, 'out': kind, 'err': b'', 'error': None}
        self.p = p if p is not None else {'exit': 0, 'out': commit_bytes(message), 'err': b'', 'error': None}
        self.raises = raises

    def __call__(self, repo, args, *rest):
        self.calls.append((repo, list(args)) + rest)
        if self.raises is not None:
            raise self.raises
        return self.t if args[1] == '-t' else self.p


class Written:
    def __init__(self, result, reason=None, findings=(), refusal=None):
        self.result = result
        self.reason = reason
        self.findings = tuple(findings)
        self.refusal = refusal


class Calls:
    """Stand-ins for append, release and held, recording their calls."""

    def __init__(self, written=None, held_lease=None, append_raises=None, release_raises=None, held_raises=None):
        self.append_calls = []
        self.release_calls = []
        self.held_calls = []
        self.written = written if written is not None else Written('appended')
        self.held_lease = held_lease
        self.append_raises = append_raises
        self.release_raises = release_raises
        self.held_raises = held_raises

    def append(self, *args, **kwargs):
        self.append_calls.append((args, kwargs))
        if self.append_raises is not None:
            raise self.append_raises
        return self.written

    def release(self, *args):
        self.release_calls.append(args)
        if self.release_raises is not None:
            raise self.release_raises
        return self.released if hasattr(self, 'released') else Released('done', {'task_id': TASK, 'fencing_token': FENCE,
                                                                                 'expires_at': NOW})

    def held(self, *args):
        self.held_calls.append(args)
        if self.held_raises is not None:
            raise self.held_raises
        return self.held_lease


class Released:
    """A stand-in for the writer's StoreResult of release_lease_token (TASK-028)."""

    def __init__(self, result, value=None):
        self.result = result
        self.value = value


class Raising:
    """A stand-in result whose every attribute raises (TASK-028 AC6, DEF-0053 F5)."""

    def __getattr__(self, name):
        raise RuntimeError(name)


def run(reader=None, calls=None, **kw):
    reader = reader or Reader()
    calls = calls or Calls()
    args = dict(root=FS_ROOT, repo=REPO, commit_id=COMMIT, task_id=TASK, event_id='ev-1', recorder='worker', now=NOW)
    args.update(kw)
    r = submit.submit(read=reader, append=calls.append, release=calls.release, held=calls.held, **args)
    return r, reader, calls


class Arguments(unittest.TestCase):
    def test_well_formed_arguments_reach_the_read(self):
        """TASK-025 AC1 and TASK-025 AC13: well-formed arguments reach the read with the two pinned forms."""
        r, reader, _ = run()
        self.assertEqual(r['result'], 'submitted')
        self.assertEqual([c[1] for c in reader.calls], [['cat-file', '-t', COMMIT], ['cat-file', '-p', COMMIT]])

    def test_each_wrong_argument_is_refused_before_the_read(self):
        """TASK-025 AC1, TASK-025 AC6 and TASK-025 AC13: each wrong argument in turn gives reason argument, read not
        called."""
        cases = [
            {'root': ''}, {'root': 'relative/root'}, {'root': None}, {'repo': 'relative'}, {'repo': b'/x'},
            {'commit_id': 'A' * 40}, {'commit_id': 'a' * 39}, {'commit_id': 'a' * 64}, {'commit_id': None},
            {'task_id': 'TASK-'}, {'task_id': 'task-1'}, {'task_id': 25}, {'event_id': ''}, {'event_id': None},
            {'recorder': ''}, {'recorder': 3}, {'now': NOW.replace(tzinfo=None)},
            {'now': NOW.replace(microsecond=5)},
            {'now': NOW.astimezone(datetime.timezone(datetime.timedelta(hours=7)))}, {'now': '2026-10-12T09:30:00Z'},
        ]
        for case in cases:
            with self.subTest(case=case):
                r, reader, calls = run(**case)
                self.assertEqual((r['result'], r['reason']), ('refused', 'argument'))
                self.assertTrue(r['findings'])
                self.assertEqual(reader.calls, [])
                self.assertEqual(calls.append_calls, [])


class Reading(unittest.TestCase):
    def test_each_failing_read_is_refused_with_nothing_appended(self):
        """TASK-025 AC2 and TASK-025 AC13: a refused form, a refused PATH, a timeout, a non-zero exit, an object that
        is not a commit and bytes out of form each give reason git, and append is not called."""
        bad = {'exit': None, 'out': b'', 'err': b'', 'error': 'PATH has an empty or relative entry'}
        cases = [
            Reader(t=bad), Reader(t={'exit': None, 'out': b'', 'err': b'', 'error': 'timeout'}),
            Reader(t={'exit': 128, 'out': b'', 'err': b'fatal', 'error': None}), Reader(kind=b'tree\n'),
            Reader(kind=b'commit'), Reader(p=bad), Reader(p={'exit': 1, 'out': b'', 'err': b'', 'error': None}),
            Reader(p={'exit': 0, 'out': b'not a commit object', 'err': b'', 'error': None}),
            Reader(p={'exit': 0, 'out': b'\xff\xfe', 'err': b'', 'error': None}), Reader(t={'out': b'commit\n'}),
            Reader(raises=OSError('x')),
        ]
        for reader in cases:
            with self.subTest(t=reader.t, p=reader.p):
                r, _, calls = run(reader=reader)
                self.assertEqual((r['result'], r['reason']), ('refused', 'git'))
                self.assertTrue(r['findings'])
                self.assertEqual(calls.append_calls, [])
                self.assertEqual(calls.release_calls, [])

    def test_a_non_commit_type_stops_before_the_second_read(self):
        """TASK-025 AC2: cat-file -p is called only when cat-file -t gave exactly commit."""
        r, reader, _ = run(reader=Reader(kind=b'blob\n'))
        self.assertEqual(r['reason'], 'git')
        self.assertEqual(len(reader.calls), 1)


    def test_the_exit_code_is_checked_on_its_own(self):
        """TASK-025 AC2 and TASK-025 AC13: a non-zero exit is refused even when the output would pass: exit 128 with
        b"commit\\n" on cat-file -t, and exit 1 with a well-formed commit on cat-file -p (decision D-598, F7)."""
        for reader in (Reader(t={'exit': 128, 'out': b'commit\n', 'err': b'', 'error': None}),
                       Reader(p={'exit': 1, 'out': commit_bytes(GOOD), 'err': b'', 'error': None})):
            with self.subTest(t=reader.t['exit'], p=reader.p['exit']):
                r, _, calls = run(reader=reader)
                self.assertEqual((r['result'], r['reason']), ('refused', 'git'))
                self.assertIn('exited with', ' '.join(r['findings']))
                self.assertEqual(calls.append_calls, [])


class Trailers(unittest.TestCase):
    def refused_before_writer(self, message, task_id=TASK):
        r, _, calls = run(reader=Reader(message=message), task_id=task_id)
        self.assertEqual((r['result'], r['reason']), ('refused', 'trailer'), message)
        self.assertTrue(r['findings'])
        self.assertEqual((calls.append_calls, calls.release_calls, calls.held_calls), ([], [], []))
        return r

    def test_one_paragraph_message_is_refused(self):
        """TASK-025 AC3 and TASK-025 AC13: a one-paragraph message "AIEOS-Task: TASK-025" with a fence line has no body
        and is refused before the writer (DEF-0052 F6)."""
        r = self.refused_before_writer('AIEOS-Task: TASK-025\nAIEOS-Fence: e0:7\n')
        self.assertIn('body', ' '.join(r['findings']))

    def test_task_key_cases_are_refused_before_the_writer(self):
        """TASK-025 AC3 and TASK-025 AC13: a missing, doubled, misspelled or different task key, or one named outside
        the last paragraph, is refused with append, release and held not called."""
        for message in ('Subject\n\nBody.\n\nAIEOS-Fence: e0:7\n',
                        'Subject\n\nBody.\n\nAIEOS-Task: TASK-025\nAIEOS-Task: TASK-025\nAIEOS-Fence: e0:7\n',
                        'Subject\n\nBody.\n\naieos-task: TASK-025\nAIEOS-Fence: e0:7\n',
                        'Subject\n\nBody.\n\nAIEOS-Task: TASK-24x\nAIEOS-Fence: e0:7\n',
                        'Subject\n\nAIEOS-Task: TASK-025\n\nAIEOS-Task: TASK-025\nAIEOS-Fence: e0:7\n'):
            with self.subTest(message=message):
                self.refused_before_writer(message)
        r = self.refused_before_writer(GOOD, task_id='TASK-024')
        self.assertIn('TASK-025', ' '.join(r['findings']))

    def test_missing_or_malformed_fence_reaches_the_writer_with_no_token(self):
        """TASK-025 AC3, TASK-025 AC4, TASK-025 AC5 and TASK-025 AC13: an identified commit with no usable fence (none,
        malformed, doubled or misspelled) reaches append once with fencing_token None; the stand-in's refusal is
        returned, and release and held are not called."""
        for fence_lines in ('', 'AIEOS-Fence: e0\n', 'AIEOS-Fence: e0:x\n', 'AIEOS-Fence: e0:7\nAIEOS-Fence: e0:8\n',
                            'aieos-fence: e0:7\n'):
            with self.subTest(fence=fence_lines):
                calls = Calls(written=Written('refused', 'fence', ['fence: the event carries no fencing_token'],
                                              refusal=Written('appended')))
                r, _, calls = run(reader=Reader(message='Subject\n\nBody.\n\nAIEOS-Task: TASK-025\n' + fence_lines),
                                  calls=calls)
                self.assertEqual((r['result'], r['reason']), ('refused', 'fence'))
                self.assertEqual(len(calls.append_calls), 1)
                self.assertIsNone(calls.append_calls[0][1]['fencing_token'])
                self.assertIn('no usable AIEOS-Fence', ' '.join(r['findings']))
                self.assertIn('refusal record was appended', ' '.join(r['findings']))
                self.assertEqual((calls.release_calls, calls.held_calls), ([], []))

    def test_a_fence_value_naming_the_task_key_is_still_a_fence_finding(self):
        """TASK-025 AC3, TASK-025 AC13 and decision D-598 F1: a malformed fence value that contains the text
        "AIEOS-Task" is classed by the key its finding names first (AIEOS-Fence), so the commit reaches append once with
        fencing_token None and the writer's refusal is returned; a finding on the task key is still refused before the
        writer."""
        for value in ('AIEOS-Task', 'AIEOS-Task:x', 'AIEOS-Task: TASK-025'):
            with self.subTest(value=value):
                calls = Calls(written=Written('refused', 'fence', ['fence: the event carries no fencing_token']))
                r, _, calls = run(reader=Reader(message='S\n\nB.\n\nAIEOS-Task: TASK-025\nAIEOS-Fence: %s\n' % value),
                                  calls=calls)
                self.assertEqual((r['result'], r['reason']), ('refused', 'fence'))
                self.assertEqual(len(calls.append_calls), 1)
                self.assertIsNone(calls.append_calls[0][1]['fencing_token'])
                self.assertEqual((calls.release_calls, calls.held_calls), ([], []))
        self.assertEqual(submit._first_key("trailer: AIEOS-Fence 'AIEOS-Task' is not <epoch>:<counter>"), 'AIEOS-Fence')
        self.assertEqual(submit._first_key("trailer: 'aieos-task' is not spelled 'AIEOS-Task'"), 'AIEOS-Task')
        self.assertIsNone(submit._first_key('trailer: something else'))
        r, _, calls = run(reader=Reader(message='S\n\nB.\n\naieos-task: TASK-025\nAIEOS-Fence: AIEOS-Fence:1\n'))
        self.assertEqual((r['result'], r['reason'], calls.append_calls), ('refused', 'trailer', []))

    def test_a_raising_trailer_read_is_a_refusal(self):
        """TASK-025 AC6 and decision D-598 F4: an exception while the trailers are read gives refused, trailer, with
        nothing appended (a stand-in for recovery.trailers raises; a str subclass cannot reach it, since parse_commit
        decodes the commit's bytes into a plain str)."""
        with mock.patch.object(submit.recovery, 'trailers', side_effect=RuntimeError('x')):
            r, _, calls = run()
        self.assertEqual((r['result'], r['reason']), ('refused', 'trailer'))
        self.assertIn('RuntimeError', ' '.join(r['findings']))
        self.assertEqual(calls.append_calls, [])

    def test_a_well_formed_message_reaches_the_writer_with_its_token(self):
        """TASK-025 AC3, TASK-025 AC4 and TASK-025 AC13: a two-paragraph message with the task and a fence reaches
        append with {epoch, counter}."""
        r, _, calls = run()
        self.assertEqual(calls.append_calls[0][1]['fencing_token'], FENCE)
        self.assertEqual(r['findings'], [])


class Append(unittest.TestCase):
    def test_the_exact_append_call(self):
        """TASK-025 AC4 and TASK-025 AC13: one call append(root, "task.submitted", {commit, compensating false},
        event_id, now, recorder, task_id=..., fencing_token=...), the counter an integer."""
        _, _, calls = run()
        self.assertEqual(calls.append_calls, [((FS_ROOT, 'task.submitted', {'commit': COMMIT, 'compensating': False},
                                                'ev-1', NOW, 'worker'), {'task_id': TASK, 'fencing_token': FENCE})])
        self.assertIs(calls.append_calls[0][0][2]['compensating'], False)
        self.assertIsInstance(calls.append_calls[0][1]['fencing_token']['counter'], int)

    def test_a_large_counter_and_a_colon_in_the_epoch(self):
        """TASK-025 AC4: the fence is split at its last colon, as recovery.trailers splits it."""
        _, _, calls = run(reader=Reader(message='S\n\nB.\n\nAIEOS-Task: TASK-025\nAIEOS-Fence: a:b:123456789\n'))
        self.assertEqual(calls.append_calls[0][1]['fencing_token'], {'epoch': 'a:b', 'counter': 123456789})


class Outcome(unittest.TestCase):
    def test_appended_releases_once(self):
        """TASK-025 AC5, TASK-025 AC6, TASK-025 AC13 and TASK-028 AC5: after appended, release is called once, with the
        commit's token, and held is not."""
        r, _, calls = run()
        self.assertEqual(r['result'], 'submitted')
        self.assertIsNone(r['reason'])
        self.assertEqual(calls.release_calls, [(FS_ROOT, TASK, FENCE)])
        self.assertEqual(calls.held_calls, [])
        self.assertEqual(r['released']['task_id'], TASK)

    def test_duplicate_with_the_same_token_releases(self):
        """TASK-025 AC5, TASK-025 AC13 and TASK-028 AC5: after duplicate, held is read once and the lease is released, by
        the commit's token, when its token is the commit's."""
        calls = Calls(written=Written('duplicate'), held_lease={'task_id': TASK, 'fencing_token': {'counter': 7, 'epoch': 'e0'},
                                                                 'expires_at': NOW})
        r, _, calls = run(calls=calls)
        self.assertEqual(r['result'], 'duplicate')
        self.assertEqual(calls.held_calls, [(FS_ROOT, TASK)])
        self.assertEqual(calls.release_calls, [(FS_ROOT, TASK, FENCE)])

    def test_duplicate_with_another_or_no_lease_does_not_release(self):
        """TASK-025 AC5 and TASK-025 AC13: after duplicate, a held lease with a different token, a token of another
        type, or no lease, is not released."""
        for lease in ({'task_id': TASK, 'fencing_token': {'epoch': 'e0', 'counter': 8}, 'expires_at': NOW},
                      {'task_id': TASK, 'fencing_token': {'epoch': 'e1', 'counter': 7}, 'expires_at': NOW},
                      {'task_id': TASK, 'fencing_token': {'epoch': 'e0', 'counter': '7'}, 'expires_at': NOW}, None):
            with self.subTest(lease=lease):
                r, _, calls = run(calls=Calls(written=Written('duplicate'), held_lease=lease))
                self.assertEqual(r['result'], 'duplicate')
                self.assertEqual(len(calls.held_calls), 1)
                self.assertEqual(calls.release_calls, [])
                self.assertIn('nothing was released', ' '.join(r['findings']))

    def test_refused_neither_releases_nor_reads_the_lease(self):
        """TASK-025 AC5, TASK-025 AC6 and TASK-025 AC13: a refusal of the writer is returned with its reason and
        findings, release and held not called."""
        for reason in ('fence', 'event', 'conflict', 'log'):
            with self.subTest(reason=reason):
                r, _, calls = run(calls=Calls(written=Written('refused', reason, ['why'])))
                self.assertEqual((r['result'], r['reason']), ('refused', reason))
                self.assertIn('why', r['findings'])
                self.assertEqual((calls.release_calls, calls.held_calls), ([], []))


class Result(unittest.TestCase):
    def test_the_result_keys(self):
        """TASK-025 AC6 and TASK-025 AC13: every result has exactly the five keys."""
        for kw in ({}, {'task_id': 'x'}, {'reader': Reader(kind=b'tree\n')}):
            with self.subTest(kw=kw):
                r = run(**kw)[0]
                self.assertEqual(set(r), set(submit.RESULT_KEYS))
                self.assertEqual(set(submit.RESULT_KEYS), {'result', 'reason', 'findings', 'appended', 'released'})

    def test_exceptions_from_the_writer_do_not_escape(self):
        """TASK-025 AC6 and TASK-025 AC13: an exception from append gives refused, store; one from release after an
        appended or duplicate event keeps that result with a finding; one from held keeps duplicate."""
        r, _, _ = run(calls=Calls(append_raises=ValueError('x')))
        self.assertEqual((r['result'], r['reason']), ('refused', 'store'))
        self.assertIn('ValueError', ' '.join(r['findings']))
        r, _, _ = run(calls=Calls(release_raises=OSError('x')))
        self.assertEqual(r['result'], 'submitted')
        self.assertIn('not released', ' '.join(r['findings']))
        r, _, _ = run(calls=Calls(written=Written('duplicate'), held_lease={'fencing_token': FENCE},
                                  release_raises=RuntimeError('x')))
        self.assertEqual(r['result'], 'duplicate')
        self.assertIn('RuntimeError', ' '.join(r['findings']))
        r, _, calls = run(calls=Calls(written=Written('duplicate'), held_raises=OSError('x')))
        self.assertEqual(r['result'], 'duplicate')
        self.assertEqual(calls.release_calls, [])

    def test_a_writer_that_accepts_an_event_with_no_token_is_not_trusted(self):
        """TASK-025 AC3 and TASK-025 AC6: if the writer were to append an event with no token, submit still refuses and
        releases nothing."""
        r, _, calls = run(reader=Reader(message='S\n\nB.\n\nAIEOS-Task: TASK-025\n'), calls=Calls(written=Written('appended')))
        self.assertEqual((r['result'], r['reason']), ('refused', 'store'))
        self.assertEqual(calls.release_calls, [])

    def test_a_duplicate_with_no_token_is_not_trusted(self):
        """TASK-025 AC3, TASK-025 AC6 and decision D-598 F8: if the writer were to call an event with no token a
        duplicate, submit refuses with reason store and calls neither held nor release."""
        r, _, calls = run(reader=Reader(message='S\n\nB.\n\nAIEOS-Task: TASK-025\n'),
                          calls=Calls(written=Written('duplicate'), held_lease={'fencing_token': FENCE}))
        self.assertEqual((r['result'], r['reason']), ('refused', 'store'))
        self.assertEqual((calls.held_calls, calls.release_calls), ([], []))

    def test_an_argument_whose_methods_raise_is_a_refusal(self):
        """TASK-025 AC1, TASK-025 AC6 and decision D-598 F4: a datetime whose tzinfo's utcoffset raises gives refused,
        argument, and read is not called."""
        class Bad(datetime.tzinfo):
            def utcoffset(self, dt):
                raise RuntimeError('no offset')

            def dst(self, dt):
                return None

        r, reader, _ = run(now=datetime.datetime(2026, 10, 12, 9, 30, 0, tzinfo=Bad()))
        self.assertEqual((r['result'], r['reason']), ('refused', 'argument'))
        self.assertIn('RuntimeError', ' '.join(r['findings']))
        self.assertEqual(reader.calls, [])


class Defaults(unittest.TestCase):
    def test_the_four_defaults_are_the_real_functions(self):
        """TASK-025 AC7 and TASK-025 AC13: with read, append, release and held None, the functions called are
        gitread.run, writer.append_event, writer.release_lease_token and writer.held_lease, resolved at call time
        (TASK-028 AC7)."""
        reader = Reader()
        calls = Calls(written=Written('appended'))
        with mock.patch.object(gitread, 'run', reader), mock.patch.object(writer, 'append_event', calls.append), \
                mock.patch.object(writer, 'release_lease_token', calls.release), mock.patch.object(writer, 'held_lease', calls.held):
            r = submit.submit(FS_ROOT, REPO, COMMIT, TASK, 'ev-1', 'worker', NOW)
        self.assertEqual(r['result'], 'submitted')
        self.assertEqual((len(reader.calls), len(calls.append_calls), len(calls.release_calls)), (2, 1, 1))
        calls = Calls(written=Written('duplicate'), held_lease=None)
        with mock.patch.object(gitread, 'run', Reader()), mock.patch.object(writer, 'append_event', calls.append), \
                mock.patch.object(writer, 'release_lease_token', calls.release), mock.patch.object(writer, 'held_lease', calls.held):
            submit.submit(FS_ROOT, REPO, COMMIT, TASK, 'ev-1', 'worker', NOW)
        self.assertEqual(len(calls.held_calls), 1)
        self.assertEqual(gitread.run.__module__, 'aieos_bootstrap.gitread')


class TokenRelease(unittest.TestCase):
    def test_a_done_release_gives_its_value(self):
        """TASK-028 AC5 and TASK-028 AC11: a release result "done" gives released equal to its value, with no finding."""
        calls = Calls()
        calls.released = Released('done', {'task_id': TASK, 'fencing_token': FENCE, 'expires_at': NOW})
        r, _, calls = run(calls=calls)
        self.assertEqual((r['result'], r['released'], r['findings']), ('submitted', calls.released.value, []))

    def test_any_other_release_result_releases_nothing(self):
        """TASK-028 AC5 and TASK-028 AC11: a refused, None or unknown release result gives released None and the
        finding, after an appended and after a duplicate event."""
        for released in (Released('refused'), None, Released('maybe', {'task_id': TASK}), Released(['done'])):
            for written, lease, result in ((Written('appended'), None, 'submitted'),
                                           (Written('duplicate'), {'fencing_token': FENCE}, 'duplicate')):
                with self.subTest(released=released, written=written.result):
                    calls = Calls(written=written, held_lease=lease)
                    calls.released = released
                    r, _, calls = run(calls=calls)
                    self.assertEqual((r['result'], r['released']), (result, None))
                    self.assertEqual(calls.release_calls, [(FS_ROOT, TASK, FENCE)])
                    self.assertIn('nothing was released', ' '.join(r['findings']))

    def test_a_release_result_whose_attributes_raise(self):
        """TASK-028 AC6 and TASK-028 AC11: a release result whose attributes raise gives released None and a finding
        naming the exception's type; nothing escapes."""
        calls = Calls()
        calls.released = Raising()
        r, _, _ = run(calls=calls)
        self.assertEqual((r['result'], r['released']), ('submitted', None))
        self.assertIn('RuntimeError', ' '.join(r['findings']))

    def test_a_writer_result_whose_attributes_raise_or_are_out_of_form(self):
        """TASK-028 AC6 and TASK-028 AC11 (DEF-0053 F5): an append result whose attributes raise, whose findings are not
        iterable or not strings, or whose result is not a string gives refused, store, with a finding; release is not
        called."""
        cases = ((Raising(), 'RuntimeError'), (Written('refused', 'fence', ()), None), (Written(['appended']), 'TypeError'))
        bad_findings = Written('refused', 'fence')
        bad_findings.findings = 5
        not_strings = Written('refused', 'fence')
        not_strings.findings = (b'x',)
        for written, name in cases[:1] + cases[2:] + ((bad_findings, 'TypeError'), (not_strings, 'TypeError')):
            with self.subTest(written=written):
                r, _, calls = run(calls=Calls(written=written))
                self.assertEqual((r['result'], r['reason']), ('refused', 'store'))
                self.assertIn(name, ' '.join(r['findings']))
                self.assertEqual(calls.release_calls, [])
        r, _, _ = run(calls=Calls(written=cases[1][0]))
        self.assertEqual((r['result'], r['reason']), ('refused', 'fence'))


IMPORTS = {'datetime', 'json', 'os', 're', 'aieos_bootstrap.gitread', 'aieos_bootstrap.recovery', 'aieos_bootstrap.writer'}
# Every dotted name rooted at an imported module that the module may use, followed to its end (decision D-598, F2, F6).
CHAINS = {'writer.append_event', 'writer.release_lease_token', 'writer.held_lease', 'gitread.run', 'gitread.parse_commit',
          'recovery.trailers', 'recovery.TASK_KEY', 'recovery.FENCE_KEY', 'os.path.isabs', 'datetime.datetime',
          'datetime.timedelta', 'json.dumps', 're.compile'}
NAMES = ('open', 'exec', 'eval', 'compile', '__import__', 'subprocess', 'environ', 'getenv', 'input', 'breakpoint')


def chain(node):
    """The dotted name of an attribute chain rooted at a Name (for example os.path.exists), or None."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    return '.'.join([node.id] + parts[::-1])


def purity_findings(source):
    """AC8's checks over one module's source: its imports, every chain rooted at a module it imports, the bare names
    it uses, and texts that must not occur in its code. Returns the findings (an empty list when it is pure)."""
    tree = ast.parse(source)
    found = []
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.update('%s.%s' % (node.module, a.name) for a in node.names)
    found += ['import %s' % m for m in sorted(imported - IMPORTS)]
    roots = {m.split('.')[-1] for m in imported}
    outer = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and id(node) not in outer:
            name = chain(node)
            if name and name.split('.')[0] in roots and name not in CHAINS:
                found.append('chain %s' % name)
    found += ['name %s' % n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id in NAMES]
    doc = ast.get_docstring(tree, clean=False)
    code = source.replace(doc, '', 1) if doc else source  # the code, without the module's docstring
    for bad in ('utcnow', 'import time', 'os.environ', 'getenv', 'open_store', 'grant_lease', 'start_session',
                'end_session', 'expire_leases', 'held_leases', '.aieos', 'assert '):
        if bad in code:
            found.append('text %s' % bad)
    return found


class Purity(unittest.TestCase):
    def test_imports_and_calls(self):
        """TASK-025 AC8, TASK-025 AC10 and TASK-025 AC13: the module imports only the standard library's datetime, json,
        os and re and the package's gitread, recovery and writer; every chain rooted at those modules is one it may use
        (the writer only through append, release and held, os only through os.path.isabs, no clock); it names no process,
        file, environment or store-changing call."""
        self.assertEqual(purity_findings(MODULE.read_text(encoding='utf-8')), [])

    def test_planted_bad_sources_are_caught(self):
        """TASK-025 AC8 and TASK-025 AC13: the same check fails on planted sources that import subprocess, read the clock
        through datetime.datetime.now, look at a file through os.path.exists, call another writer function, or open a
        file (its failing cases)."""
        head = 'import datetime\nimport os\nfrom aieos_bootstrap import writer\n'
        for source, expected in (('import subprocess\n', 'import subprocess'),
                                 (head + 'x = datetime.datetime.now(datetime.timezone.utc)\n', 'chain datetime.datetime.now'),
                                 (head + 'y = os.path.exists("x")\n', 'chain os.path.exists'),
                                 (head + 'z = writer.grant_lease\n', 'chain writer.grant_lease'),
                                 (head + 'w = open("x")\n', 'name open')):
            with self.subTest(source=source):
                self.assertIn(expected, purity_findings(source))


if __name__ == '__main__':
    unittest.main()
