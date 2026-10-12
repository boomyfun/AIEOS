"""Unit tests of aieos_bootstrap.startup (task TASK-026, its rules R1 to R12); every rule has at least one passing case
and one failing case. The Git reader and the writer's functions are replaced by stand-ins: the reader answers from a
table of commits, and the stand-in writer keeps a log as bytes and the leases as a list, deciding each append with
eventlog.append as the real writer does, so no git starts and no file is touched here. Each test names the criteria it
stands for in its own docstring."""

import ast
import datetime
import pathlib
import unittest

from aieos_bootstrap import eventlog
from aieos_bootstrap import gitread
from aieos_bootstrap import recovery
from aieos_bootstrap import startup
from aieos_bootstrap import writer

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / 'src' / 'aieos_bootstrap' / 'startup.py'
FS_ROOT = str(ROOT / 'no-such-state-root')
REPO = str(ROOT)
TREE = 'b' * 40
TASK = 'TASK-026'
REC = 'aieos-core'
UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 10, 12, 10, 0, 0, tzinfo=UTC)
H1 = datetime.timedelta(hours=1)
FENCE = {'epoch': 'e0', 'counter': 3}
LEASE = {'task_id': TASK, 'fencing_token': FENCE, 'expires_at': NOW + H1}
PLAIN = 'Initial commit\n'
WORK = 'Do some work\n\nThe body.\n'
FENCED = 'Do the task\n\nThe body.\n\nAIEOS-Task: TASK-026\nAIEOS-Fence: e0:3\n'
UNFENCED = 'Do the task\n\nThe body.\n\nAIEOS-Task: TASK-026\n'


def cid(n):
    return '%040x' % n


def ok(out):
    return {'exit': 0, 'out': out, 'err': b'', 'error': None}


def commit_bytes(parents, message):
    head = 'tree %s\n' % TREE + ''.join('parent %s\n' % p for p in parents)
    head += 'author Tester <tester> 1700000000 +0000\ncommitter Tester <tester> 1700000000 +0000\n\n'
    return (head + message).encode('utf-8')


class Repo:
    """A stand-in for gitread.run: HEAD and the commits from a table {id: (parents, message)}; ``fail`` maps "HEAD"
    or an id to the result (or exception) given instead."""

    def __init__(self, table, head, fail=None):
        self.table = table
        self.head = head
        self.fail = fail or {}
        self.calls = []

    def __call__(self, repo, args, *rest):
        self.calls.append((repo, list(args)) + rest)
        key = 'HEAD' if args[0] == 'rev-parse' else args[-1]
        if key in self.fail:
            given = self.fail[key]
            if isinstance(given, BaseException):
                raise given
            return given
        if key == 'HEAD':
            return ok((self.head + '\n').encode('ascii'))
        parents, message = self.table[key]
        return ok(commit_bytes(parents, message))

    def reads(self):
        return [c[1][-1] for c in self.calls if c[1][0] == 'cat-file']


def line_history(*messages):
    """A line of history, oldest first: ids cid(1) .. cid(n); returns (table, head)."""
    table = {}
    for i, message in enumerate(messages, 1):
        table[cid(i)] = ([cid(i - 1)] if i > 1 else [], message)
    return table, cid(len(messages))


class Done:
    def __init__(self, value):
        self.result = 'done'
        self.value = value


class Refused:
    def __init__(self, reason):
        self.result = 'refused'
        self.reason = reason
        self.value = None


class Store:
    """A stand-in writer that keeps a log and the leases; append decides with eventlog.append and the held lease, as
    writer.append_event does; ``stop_after`` raises on the append after that many have been made."""

    def __init__(self, log=b'', leases=None, stop_after=None, release_gives=None, release_raises=None):
        self.log = log
        self.leases = list(leases or [])
        self.stop_after = stop_after
        self.release_gives = release_gives
        self.release_raises = release_raises
        self.calls = []

    def read_log(self, root):
        self.calls.append(('read_log', root))
        return self.log

    def held(self, root):
        self.calls.append(('leases', root))
        return [dict(x) for x in self.leases]

    def append(self, root, event_type, payload, event_id, appended_at, recorder, task_id=None, fencing_token=None):
        self.calls.append(('append', event_type, payload, event_id, appended_at, recorder, task_id, fencing_token))
        if self.stop_after is not None and len([c for c in self.calls if c[0] == 'append']) > self.stop_after:
            raise RuntimeError('stopped')
        lease = next((x for x in self.leases if x['task_id'] == task_id), None)
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id,
                            fencing_token=fencing_token, lease=lease, recorder=recorder, record_id='r' + event_id)
        if r.result == 'appended':
            self.log += r.line
        return r

    def release(self, root, task_id, token):
        self.calls.append(('release', task_id, token))
        if self.release_raises is not None:
            raise self.release_raises
        if self.release_gives is not None:
            return self.release_gives
        for x in self.leases:
            if x['task_id'] == task_id and x['fencing_token'] == token:
                self.leases.remove(x)
                return Done(x)
        return Refused('none')

    def expire(self, root, now):
        self.calls.append(('expire', now))
        gone = [x for x in self.leases if not x['expires_at'] > now]
        for x in gone:
            self.leases.remove(x)
        return gone

    def names(self):
        return [c[0] for c in self.calls]

    def appends(self):
        return [c for c in self.calls if c[0] == 'append']


def run(table, top, store, **kw):
    reader = kw.pop('reader', None) or Repo(table, top)
    r = startup.recover(FS_ROOT, REPO, REC, NOW, read=reader, read_log=store.read_log, append=store.append,
                        leases=store.held, release=store.release, expire=store.expire, **kw)
    return r, reader


def submitted_line(commit, compensating=False):
    """The bytes of a log holding one task.submitted of TASK-026 with FENCE for the commit, built by eventlog."""
    r = eventlog.append(b'', 'task.submitted', {'commit': commit, 'compensating': compensating}, 'ev-sub', NOW,
                        task_id=TASK, fencing_token=FENCE, lease=LEASE, recorder=REC, record_id='rec-sub')
    return r.log


class R1Arguments(unittest.TestCase):
    """TASK-026's R1: AC1."""

    def test_good_arguments_read_head(self):
        """TASK-026 AC1 and TASK-026 AC15: arguments in form are accepted and the walk starts at HEAD."""
        table, head = line_history(PLAIN)
        r, reader = run(table, head, Store())
        self.assertEqual(r['result'], 'recovered')
        self.assertEqual(reader.calls[0][1], ['rev-parse', '--verify', '--end-of-options', 'HEAD'])

    def test_each_wrong_argument_refused_before_read(self):
        """TASK-026 AC1 and TASK-026 AC15: each argument wrong in turn gives refused, reason argument, a finding
        naming it, and read is not called."""
        good = {'root': FS_ROOT, 'repo': REPO, 'recorder': REC, 'now': NOW}
        wrong = [('root', 'relative/path'), ('root', ''), ('root', None), ('repo', 'relative'), ('repo', b'/x'),
                 ('recorder', ''), ('recorder', 7), ('now', NOW.replace(tzinfo=None)),
                 ('now', NOW.replace(microsecond=5)),
                 ('now', NOW.astimezone(datetime.timezone(H1))), ('now', '2026-10-12T10:00:00Z'),
                 ('head', 'A' * 40), ('head', 'a' * 39), ('head', 7), ('max_commits', 0), ('max_commits', True),
                 ('max_commits', 100001), ('max_commits', 5.0)]
        for name, value in wrong:
            with self.subTest(name=name, value=value):
                store = Store()
                reader = Repo({}, cid(1))
                args = dict(good)
                kw = {}
                if name in args:
                    args[name] = value
                else:
                    kw[name] = value
                r = startup.recover(args['root'], args['repo'], args['recorder'], args['now'], read=reader,
                                    read_log=store.read_log, append=store.append, leases=store.held,
                                    release=store.release, expire=store.expire, **kw)
                self.assertEqual((r['result'], r['reason']), ('refused', 'argument'))
                self.assertTrue(any(name in f for f in r['findings']), r['findings'])
                self.assertEqual(reader.calls, [])
                self.assertEqual(store.calls, [])

    def test_given_head_skips_rev_parse(self):
        """TASK-026 AC1 and TASK-026 AC15: a given head is walked from without rev-parse; the bounds 1 and 100000
        are accepted."""
        table, head = line_history(PLAIN)
        for bound in (1, 100000):
            r, reader = run(table, head, Store(), head=head, max_commits=bound)
            self.assertEqual(r['result'], 'recovered')
            self.assertEqual([c[1][0] for c in reader.calls], ['cat-file'])


class R2Walk(unittest.TestCase):
    """TASK-026's R2: AC2."""

    def test_line_of_history(self):
        """TASK-026 AC2 and TASK-026 AC15: a line of history is read once per commit with cat-file -p."""
        table, head = line_history(PLAIN, WORK, WORK)
        r, reader = run(table, head, Store())
        self.assertEqual(r['result'], 'recovered')
        self.assertEqual(sorted(reader.reads()), sorted(table))
        for c in reader.calls[1:]:
            self.assertEqual(c[1][:2], ['cat-file', '-p'])

    def test_merge_and_commit_reached_twice(self):
        """TASK-026 AC2 and TASK-026 AC15: a merge's two parents are both followed, and a commit reached twice is
        read once."""
        table = {cid(1): ([], PLAIN), cid(2): ([cid(1)], WORK), cid(3): ([cid(1)], WORK),
                 cid(4): ([cid(2), cid(3)], WORK)}
        r, reader = run(table, cid(4), Store())
        self.assertEqual(r['result'], 'recovered')
        self.assertEqual(sorted(reader.reads()), sorted(table))
        self.assertEqual(len(reader.reads()), 4)

    def test_each_failing_read_refuses_with_nothing_appended(self):
        """TASK-026 AC2 and TASK-026 AC15: a refused form, a timeout, a non-zero exit, an exception, a result out of
        form, an object that is not a commit and a bad HEAD answer each give refused, reason git, and nothing is
        read from the store, appended, released or expired."""
        table, head = line_history(PLAIN, UNFENCED)
        bad = [
            (head, {'exit': None, 'out': b'', 'err': b'', 'error': 'refused: the form'}),
            (head, {'exit': None, 'out': b'', 'err': b'', 'error': 'timeout'}),
            (cid(1), {'exit': 128, 'out': b'', 'err': b'fatal', 'error': None}),
            (cid(1), OSError('no git')),
            (cid(1), {'out': b''}),
            (cid(1), ok(b'not a commit object')),
            (cid(1), ok(b'\xff\xfe')),
            ('HEAD', ok(b'deadbeef\n')),
            ('HEAD', ok((head + '\n\n').encode())),
            ('HEAD', {'exit': 1, 'out': b'', 'err': b'', 'error': None}),
        ]
        for key, given in bad:
            with self.subTest(key=key, given=given):
                store = Store()
                r, _ = run(table, head, store, reader=Repo(table, head, fail={key: given}))
                self.assertEqual((r['result'], r['reason']), ('refused', 'git'))
                self.assertTrue(r['findings'] and all(f.startswith('git: ') for f in r['findings']))
                self.assertEqual(store.calls, [])
                self.assertEqual((r['appended'], r['released'], r['expired']), ([], [], []))

    def test_parent_not_forty_hex_refused(self):
        """TASK-026 AC2 and TASK-026 AC15: a parent id of 64 hexadecimal characters is refused (reason git)."""
        table = {cid(2): (['c' * 64], WORK)}
        store = Store()
        r, _ = run(table, cid(2), store)
        self.assertEqual((r['result'], r['reason']), ('refused', 'git'))
        self.assertEqual(store.calls, [])

    def test_bound(self):
        """TASK-026 AC2 and TASK-026 AC15: more than max_commits distinct commits gives refused, reason bound, with
        nothing read further and nothing appended; exactly max_commits passes."""
        table, head = line_history(PLAIN, WORK, WORK, UNFENCED)
        store = Store()
        r, reader = run(table, head, store, max_commits=3)
        self.assertEqual((r['result'], r['reason']), ('refused', 'bound'))
        self.assertEqual(len(reader.reads()), 3)
        self.assertEqual(store.calls, [])
        r, reader = run(table, head, Store(), max_commits=4)
        self.assertEqual(r['result'], 'recovered')


class R3OrderAndBody(unittest.TestCase):
    """TASK-026's R3: AC3."""

    def given(self, table, head):
        seen = []

        def spy(log, commits, leases, now, recorder):
            seen.append(commits)
            return original(log, commits, leases, now, recorder)
        original = recovery.reconcile
        recovery.reconcile = spy
        try:
            r, _ = run(table, head, Store())
        finally:
            recovery.reconcile = original
        return r, seen[0]

    def test_parents_before_children(self):
        """TASK-026 AC3 and TASK-026 AC15: commits are given as {commit, message}, parents before children, a merge's
        parents in header order; a line of history oldest first."""
        table = {cid(1): ([], WORK), cid(2): ([cid(1)], WORK), cid(3): ([cid(1)], WORK),
                 cid(4): ([cid(3), cid(2)], WORK), cid(5): ([cid(4)], WORK)}
        r, commits = self.given(table, cid(5))
        self.assertEqual([c['commit'] for c in commits], [cid(1), cid(3), cid(2), cid(4), cid(5)])
        self.assertEqual(set(commits[0]), {'commit', 'message'})
        self.assertEqual(commits[0]['message'], WORK)
        table, head = line_history(WORK, WORK, WORK)
        r, commits = self.given(table, head)
        self.assertEqual([c['commit'] for c in commits], [cid(1), cid(2), cid(3)])

    def test_one_paragraph_with_task_left_out_with_finding(self):
        """TASK-026 AC3 and TASK-026 AC15: a one-paragraph message whose trailers give a task, or a finding (a
        mis-cased key), is not given; left_out lists it and a finding names it; nothing is appended for it."""
        for message in ('AIEOS-Task: TASK-026\n', 'aieos-task: TASK-026\n'):
            with self.subTest(message=message):
                table = {cid(1): ([], message)}
                store = Store()
                r, commits = self.given(table, cid(1))
                self.assertEqual(commits, [])
                self.assertEqual(r['left_out'], [cid(1)])
                self.assertTrue(any(cid(1) in f and f.startswith('left out: ') for f in r['findings']))
                self.assertEqual(store.appends(), [])

    def test_one_paragraph_without_trailer_left_out_silently(self):
        """TASK-026 AC3 and TASK-026 AC15: a one-paragraph message with no trailer is not given and not listed."""
        table = {cid(1): ([], PLAIN), cid(2): ([cid(1)], WORK)}
        r, commits = self.given(table, cid(2))
        self.assertEqual([c['commit'] for c in commits], [cid(2)])
        self.assertEqual(r['left_out'], [])
        self.assertEqual(r['findings'], [])


class R4Reconcile(unittest.TestCase):
    """TASK-026's R4: AC4."""

    def test_log_and_leases_read_once_and_findings_copied(self):
        """TASK-026 AC4 and TASK-026 AC15: the log and the leases are read once each before reconcile (the log once
        more after the appends), and reconcile's other findings are copied."""
        table, head = line_history(PLAIN, 'Two\n\nBody.\n\nAIEOS-Task: TASK-026\nAIEOS-Task: TASK-027\n')
        store = Store()
        r, _ = run(table, head, store)
        self.assertEqual(r['result'], 'recovered')
        self.assertEqual(store.names()[:2], ['read_log', 'leases'])
        self.assertEqual(store.names().count('read_log'), 2)
        self.assertEqual(store.names().count('leases'), 1)
        self.assertTrue(any('is given 2 times' in f for f in r['findings']), r['findings'])

    def test_damaged_log_refused(self):
        """TASK-026 AC4 and TASK-026 AC15: a damaged log gives refused, reason log, its "log: " findings, and nothing
        appended, released or expired."""
        table, head = line_history(UNFENCED)
        for log in (b'not json\n', submitted_line(cid(9))[:-1]):
            with self.subTest(log=log):
                store = Store(log=log, leases=[LEASE])
                r, _ = run(table, head, store)
                self.assertEqual((r['result'], r['reason']), ('refused', 'log'))
                self.assertTrue(r['findings'] and all(f.startswith('log: ') for f in r['findings']))
                self.assertEqual(store.names(), ['read_log', 'leases'])


class R5Appends(unittest.TestCase):
    """TASK-026's R5: AC5."""

    def test_exact_append_calls(self):
        """TASK-026 AC5 and TASK-026 AC15: each event reconcile appended goes to append once, in order, with the line's
        own type, payload, event_id, task_id and token; the log after equals reconcile's log."""
        table, head = line_history(PLAIN, FENCED, UNFENCED)
        store = Store(leases=[LEASE])
        given = [{'commit': cid(2), 'message': FENCED}, {'commit': cid(3), 'message': UNFENCED}]
        expected = recovery.reconcile(b'', given,
                                      [LEASE], NOW, REC)
        r, _ = run(table, head, store)
        self.assertEqual(r['result'], 'recovered')
        self.assertEqual(store.log, expected.log)
        calls = store.appends()
        self.assertEqual([c[1] for c in calls], ['task.submitted', 'record.added'])
        self.assertEqual(calls[0][2], {'commit': cid(2), 'compensating': True})
        self.assertEqual(calls[0][6:], (TASK, FENCE))
        self.assertEqual(calls[1][6:], (TASK, None))
        self.assertEqual(calls[1][2]['refers_to'], cid(3))
        self.assertEqual([c[3] for c in calls], [e['event_id'] for e in expected.events])
        self.assertEqual(r['appended'], [e['event_id'] for e in expected.events])
        for c in calls:
            self.assertEqual((c[4], c[5]), (NOW, REC))

    def test_refused_append_stops_the_rest(self):
        """TASK-026 AC5 and TASK-026 AC15: an append refused (or raising) stops the appends there, partial, reason
        store, a finding naming the event, and nothing is released or expired."""
        table, head = line_history(PLAIN, FENCED, UNFENCED)

        class Refuse(Store):
            def append(self, *args, **kw):
                self.calls.append(('append',) + args[1:])
                return Refused('fence')
        for store in (Refuse(leases=[LEASE]), Store(leases=[LEASE], stop_after=0)):
            with self.subTest(store=type(store).__name__):
                r, _ = run(table, head, store)
                self.assertEqual((r['result'], r['reason']), ('partial', 'store'))
                self.assertEqual(len(store.appends()), 1)
                self.assertTrue(any(store.appends()[0][3] in f for f in r['findings']))
                self.assertNotIn('release', store.names())
                self.assertNotIn('expire', store.names())

    def test_log_inequality_finding(self):
        """TASK-026 AC5 and TASK-026 AC15: when the log read after the appends differs from reconcile's, a finding
        says so and the result is partial, with nothing released or expired."""
        table, head = line_history(PLAIN, UNFENCED)

        class Drift(Store):
            def append(self, *args, **kw):
                r = Store.append(self, *args, **kw)
                self.log = self.log.replace(b'"outcome":"fail"', b'"outcome":"pass"')
                return r
        store = Drift()
        r, _ = run(table, head, store)
        self.assertEqual((r['result'], r['reason']), ('partial', 'store'))
        self.assertTrue(any('not reconcile\'s log' in f for f in r['findings']))
        self.assertNotIn('expire', store.names())


class R6Release(unittest.TestCase):
    """TASK-026's R6: AC6."""

    def test_compensating_submission_released_by_token(self):
        """TASK-026 AC6 and TASK-026 AC15: the lease of a compensating submission is released by its token."""
        table, head = line_history(PLAIN, FENCED)
        store = Store(leases=[LEASE])
        r, _ = run(table, head, store)
        self.assertEqual(r['result'], 'recovered')
        self.assertEqual([c for c in store.calls if c[0] == 'release'], [('release', TASK, FENCE)])
        self.assertEqual(r['released'], [LEASE])
        self.assertEqual(store.leases, [])

    def test_earlier_logged_submission_releases(self):
        """TASK-026 AC6 and TASK-026 AC15: a held lease whose task and token an earlier logged task.submitted names
        is released, though nothing is appended in this run."""
        table, head = line_history(PLAIN, FENCED)
        store = Store(log=submitted_line(cid(2)), leases=[LEASE])
        r, _ = run(table, head, store)
        self.assertEqual(r['result'], 'recovered')
        self.assertEqual(store.appends(), [])
        self.assertEqual(r['released'], [LEASE])

    def test_other_token_or_task_not_released(self):
        """TASK-026 AC6 and TASK-026 AC15: a held lease of another token, or of a task no task.submitted names, is not
        released; no release for an observation."""
        other_token = {'task_id': TASK, 'fencing_token': {'epoch': 'e0', 'counter': 4}, 'expires_at': NOW + H1}
        other_task = {'task_id': 'TASK-099', 'fencing_token': {'epoch': 'e0', 'counter': 5}, 'expires_at': NOW + H1}
        table, head = line_history(PLAIN, UNFENCED)
        store = Store(log=submitted_line(cid(9)), leases=[other_token, other_task])
        r, _ = run(table, head, store)
        self.assertEqual(r['result'], 'recovered')
        self.assertNotIn('release', store.names())
        self.assertEqual(r['released'], [])
        self.assertEqual(len(store.appends()), 1)

    def test_refused_or_raising_release_goes_on(self):
        """TASK-026 AC6 and TASK-026 AC15: a refused, unreadable or raising release gives a finding naming the task,
        and the recovery goes on to the expiry."""

        class Bad:
            @property
            def result(self):
                raise ValueError('unreadable')
        table, head = line_history(PLAIN, FENCED)
        for kw in ({'release_gives': Refused('token')}, {'release_raises': OSError('locked')},
                   {'release_gives': Bad()}, {'release_gives': object()}):
            with self.subTest(kw=kw):
                store = Store(leases=[LEASE], **kw)
                r, _ = run(table, head, store)
                self.assertEqual(r['result'], 'recovered')
                self.assertEqual(r['released'], [])
                self.assertTrue(any(TASK in f and 'release' in f for f in r['findings']), r['findings'])
                self.assertIn('expire', store.names())


class R7Expiry(unittest.TestCase):
    """TASK-026's R7: AC7."""

    def test_expire_once_after_complete_replay(self):
        """TASK-026 AC7 and TASK-026 AC15: expire is called once, last, and its leases are the result's expired."""
        past = {'task_id': 'TASK-099', 'fencing_token': {'epoch': 'e0', 'counter': 1}, 'expires_at': NOW}
        table, head = line_history(PLAIN, UNFENCED)
        store = Store(leases=[past])
        r, _ = run(table, head, store)
        self.assertEqual((r['result'], r['reason']), ('recovered', None))
        self.assertEqual(store.names().count('expire'), 1)
        self.assertEqual(store.names()[-1], 'expire')
        self.assertEqual(r['expired'], [past])

    def test_no_expiry_after_incomplete_replay_or_raise(self):
        """TASK-026 AC7 and TASK-026 AC15: no expiry when an append fails; an expiry that raises gives partial,
        reason store, and a finding."""
        table, head = line_history(PLAIN, UNFENCED)
        store = Store(stop_after=0)
        r, _ = run(table, head, store)
        self.assertNotIn('expire', store.names())

        class Raise(Store):
            def expire(self, root, now):
                self.calls.append(('expire', now))
                raise OSError('locked')
        store = Raise()
        r, _ = run(table, head, store)
        self.assertEqual((r['result'], r['reason']), ('partial', 'store'))
        self.assertTrue(any('expiry raised OSError' in f for f in r['findings']))


class R8Reruns(unittest.TestCase):
    """TASK-026's R8: AC8."""

    def test_rerun_appends_nothing_new(self):
        """TASK-026 AC8 and TASK-026 AC15: a second recover over the same repository, log and store appends nothing
        new and releases nothing more."""
        table, head = line_history(PLAIN, FENCED, UNFENCED)
        store = Store(leases=[LEASE])
        first, _ = run(table, head, store)
        self.assertEqual(len(first['appended']), 2)
        log = store.log
        second, _ = run(table, head, store)
        self.assertEqual(second['result'], 'recovered')
        self.assertEqual(second['appended'], [])
        self.assertEqual(second['released'], [])
        self.assertEqual(store.log, log)
        self.assertEqual(len(store.appends()), 2)

    def test_run_stopped_after_one_append_completed(self):
        """TASK-026 AC8 and TASK-026 AC15: a run stopped after one of three appends is completed by the next, which
        appends the remaining two and nothing else."""
        table, head = line_history(PLAIN, UNFENCED, UNFENCED, UNFENCED)
        store = Store(stop_after=1)
        first, _ = run(table, head, store)
        self.assertEqual(first['result'], 'partial')
        self.assertEqual(first['appended'], [store.appends()[0][3]])
        store.stop_after = None
        before = len(store.appends())
        second, _ = run(table, head, store)
        self.assertEqual(second['result'], 'recovered')
        self.assertEqual(len(store.appends()) - before, 2)
        self.assertEqual(store.log.count(b'\n'), 3)
        clean = Store()
        run(table, head, clean)
        self.assertEqual(store.log, clean.log)

    def test_run_stopped_before_release_completed(self):
        """TASK-026 AC8 and TASK-026 AC15: a run stopped after a compensating append and before its release is
        completed by the next, which releases that lease by its token."""
        table, head = line_history(PLAIN, FENCED)
        store = Store(leases=[LEASE], release_raises=RuntimeError('stopped'))
        first, _ = run(table, head, store)
        self.assertEqual(first['released'], [])
        self.assertEqual(store.leases, [LEASE])
        store.release_raises = None
        second, _ = run(table, head, store)
        self.assertEqual(second['result'], 'recovered')
        self.assertEqual(second['appended'], [])
        self.assertEqual(second['released'], [LEASE])
        self.assertEqual(store.leases, [])


class R9Defaults(unittest.TestCase):
    """TASK-026's R9: AC9."""

    def test_six_defaults_resolved_at_call_time(self):
        """TASK-026 AC9 and TASK-026 AC15: with no stand-ins given, recover calls gitread.run, writer.read_log,
        writer.append_event, writer.held_leases, writer.release_lease_token and writer.expire_leases, looked up at
        call time (the module attributes are replaced for the test and restored)."""
        table, head = line_history(PLAIN, FENCED)
        store = Store(leases=[LEASE])
        reader = Repo(table, head)
        names = {(gitread, 'run'): reader, (writer, 'read_log'): store.read_log, (writer, 'append_event'): store.append,
                 (writer, 'held_leases'): store.held, (writer, 'release_lease_token'): store.release,
                 (writer, 'expire_leases'): store.expire}
        saved = {key: getattr(*key) for key in names}
        try:
            for (module, name), value in names.items():
                setattr(module, name, value)
            r = startup.recover(FS_ROOT, REPO, REC, NOW)
        finally:
            for (module, name), value in saved.items():
                setattr(module, name, value)
        self.assertEqual(r['result'], 'recovered')
        self.assertTrue(reader.calls)
        self.assertEqual(sorted(set(store.names())), ['append', 'expire', 'leases', 'read_log', 'release'])
        self.assertIs(gitread.run, saved[(gitread, 'run')])

    def test_given_functions_win(self):
        """TASK-026 AC9 and TASK-026 AC15: given stand-ins are used and the defaults are not called."""
        table, head = line_history(PLAIN)
        saved = writer.read_log

        def boom(root):
            raise AssertionError('the default was called')
        writer.read_log = boom
        try:
            r, _ = run(table, head, Store())
        finally:
            writer.read_log = saved
        self.assertEqual(r['result'], 'recovered')


class R10Result(unittest.TestCase):
    """TASK-026's R10: AC10."""

    def test_result_keys(self):
        """TASK-026 AC10 and TASK-026 AC15: the result has exactly the seven keys, for each kind of result."""
        table, head = line_history(PLAIN, UNFENCED)
        for r in (run(table, head, Store())[0], run(table, head, Store(stop_after=0))[0],
                  startup.recover('x', REPO, REC, NOW)):
            self.assertEqual(set(r), startup.RESULT_KEYS)
            self.assertIn(r['result'], ('recovered', 'partial', 'refused'))
            self.assertIsInstance(r['findings'], list)

    def test_exceptions_from_each_function_caught(self):
        """TASK-026 AC10 and TASK-026 AC15: an exception from each injected function, or from reading what it
        returns, becomes a result with a finding naming its type; none escapes."""
        table, head = line_history(PLAIN, FENCED)

        def raising(*args, **kw):
            raise KeyError('x')
        for name in ('read', 'read_log', 'leases', 'append', 'release', 'expire'):
            with self.subTest(name=name):
                store = Store(leases=[LEASE])
                kw = {'read': Repo(table, head), 'read_log': store.read_log, 'append': store.append,
                      'leases': store.held, 'release': store.release, 'expire': store.expire}
                kw[name] = raising
                r = startup.recover(FS_ROOT, REPO, REC, NOW, **kw)
                self.assertEqual(set(r), startup.RESULT_KEYS)
                self.assertTrue(any('KeyError' in f for f in r['findings']), r['findings'])
        for bad in (b'x', 'not bytes', None):
            with self.subTest(log=bad):
                store = Store(leases=[LEASE])
                store.log = bad
                r, _ = run(table, head, store)
                self.assertEqual(r['result'], 'refused')
        store = Store(leases=[LEASE])
        r = startup.recover(FS_ROOT, REPO, REC, NOW, read=Repo(table, head), read_log=store.read_log,
                            append=lambda *a, **k: object(), leases=store.held, release=store.release,
                            expire=lambda root, now: 7)
        self.assertEqual((r['result'], r['reason']), ('partial', 'store'))

    def test_bad_leases_from_the_store_refused(self):
        """TASK-026 AC10 and TASK-026 AC15: leases out of form make reconcile raise; the result is refused, reason
        store, with nothing appended."""
        table, head = line_history(PLAIN, FENCED)
        store = Store(leases=[{'task_id': TASK}])
        r, _ = run(table, head, store)
        self.assertEqual((r['result'], r['reason']), ('refused', 'store'))
        self.assertEqual(store.appends(), [])


class R11ReadLog(unittest.TestCase):
    """TASK-026's R11: AC11, as far as startup uses it (its own test is in tests/unit/test_writer.py)."""

    def test_read_log_is_a_writer_function(self):
        """TASK-026 AC11 and TASK-026 AC15: writer.read_log exists and refuses a root that is not a folder."""
        self.assertTrue(callable(writer.read_log))
        with self.assertRaises(ValueError):
            writer.read_log(FS_ROOT)
        with self.assertRaises(TypeError):
            writer.read_log('')


class R12Purity(unittest.TestCase):
    """TASK-026's R12: AC12, a script check of the module's source."""

    def tree(self):
        return ast.parse(MODULE.read_text(encoding='utf-8'))

    def test_imports(self):
        """TASK-026 AC12 and TASK-026 AC15: only standard-library modules and gitread, recovery and writer are
        imported."""
        names = set()
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.update('%s.%s' % (node.module, a.name) for a in node.names)
        self.assertEqual(names, {'datetime', 'json', 'os', 're', 'aieos_bootstrap.gitread',
                                 'aieos_bootstrap.recovery', 'aieos_bootstrap.writer'})

    def test_no_process_file_clock_environment_or_store_change(self):
        """TASK-026 AC12 and TASK-026 AC15: no open, process, clock, environment, dynamic code or assert; of the
        writer only the five named functions; no string naming the project-state directory."""
        tree = self.tree()
        called = set()
        attrs = set()
        for node in ast.walk(tree):
            self.assertNotIsInstance(node, ast.Assert)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                called.add(node.func.id)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                attrs.add('%s.%s' % (node.value.id, node.attr))
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertNotIn('.aieos', node.value)
        self.assertFalse(called & {'open', 'exec', 'eval', 'compile', '__import__', 'input'})
        writer_used = {a for a in attrs if a.startswith('writer.')}
        self.assertEqual(writer_used, {'writer.read_log', 'writer.append_event', 'writer.held_leases',
                                       'writer.release_lease_token', 'writer.expire_leases'})
        os_used = {a for a in attrs if a.startswith('os.')}
        self.assertEqual(os_used, {'os.path'})
        for bad in ('subprocess', 'importlib', 'environ', 'getenv', 'now', 'utcnow', 'time', 'open_store',
                    'grant_lease', 'start_session', 'end_session', 'release_lease', 'system', 'popen'):
            self.assertNotIn(bad, {a.split('.', 1)[1] for a in attrs}, bad)
        self.assertEqual({a for a in attrs if a.startswith('gitread.')}, {'gitread.run', 'gitread.parse_commit'})

    def test_check_fails_on_a_forbidden_call(self):
        """TASK-026 AC12 and TASK-026 AC15: the same check finds a forbidden call in a sample text (its failing
        case)."""
        sample = ast.parse('import subprocess\nwriter.grant_lease(x)\nopen("f")\n')
        attrs = {'%s.%s' % (n.value.id, n.attr) for n in ast.walk(sample)
                 if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
        called = {n.func.id for n in ast.walk(sample) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertIn('writer.grant_lease', attrs)
        self.assertIn('open', called)


if __name__ == '__main__':
    unittest.main()
