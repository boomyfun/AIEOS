"""Unit tests of aieos_bootstrap.writer (TASK-016 AC12, rules R1 to R8); every rule has at least one passing case and
one failing case, and each test works in its own temporary folder, removed by tempfile's own cleanup."""

import ast
import datetime
import os
import sqlite3
import tempfile
import unittest

from aieos_bootstrap import eventlog, records, writer

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
H1 = datetime.timedelta(hours=1)
H64 = '0123456789abcdef' * 4
C40 = 'fedcba9876543210fedcba9876543210fedcba98'
TASK = 'TASK-016'
DRAFTED = {'contract_version': 'v1', 'contract_hash': H64}
SUBMITTED = {'commit': C40, 'compensating': False}
REC = 'aieos-core'
SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src',
                   'aieos_bootstrap')


def files_under(root):
    """Every file under the root, as paths relative to it with "/"."""
    out = []
    for here, _, names in os.walk(root):
        for name in names:
            out.append(os.path.relpath(os.path.join(here, name), root).replace(os.sep, '/'))
    return sorted(out)


def read(path):
    with open(path, 'rb') as f:
        return f.read()


class Case(unittest.TestCase):
    """Each test in its own temporary folder (AC12)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def store(self, epoch='epoch-1'):
        return writer.open_store(self.root, epoch)

    def session(self, sid='s-1', holder='agent-1', at=T0):
        r = writer.start_session(self.root, sid, holder, at)
        self.assertEqual(r.result, 'done', r)

    def grant(self, task=TASK, state='READY', holder='agent-1', sid='s-1', at=T0, until=None):
        return writer.grant_lease(self.root, task, state, holder, sid, at, at + H1 if until is None else until)

    def draft(self, event_id='ev-d', task=TASK):
        return writer.append_event(self.root, 'task.drafted', DRAFTED, event_id, T0, REC, task_id=task)


class R1Paths(Case):

    def test_only_the_two_paths_after_each_transaction(self):
        self.assertEqual(files_under(self.root), [])
        self.store()
        self.assertEqual(files_under(self.root), ['.aieos/local/state.sqlite'])
        self.session()
        self.assertEqual(self.grant().result, 'done')
        self.assertEqual(files_under(self.root), ['.aieos/local/state.sqlite'])
        self.draft()
        self.assertEqual(files_under(self.root), ['.aieos/events.jsonl', '.aieos/local/state.sqlite'])
        writer.release_lease(self.root, TASK)
        writer.expire_leases(self.root, T0)
        writer.end_session(self.root, 's-1', T0)
        self.assertEqual(files_under(self.root), ['.aieos/events.jsonl', '.aieos/local/state.sqlite'])

    def test_paths_created_on_first_use(self):
        self.draft()
        self.assertEqual(files_under(self.root), ['.aieos/events.jsonl'])
        self.assertEqual(writer.log_path(self.root), os.path.join(self.root, '.aieos', 'events.jsonl'))
        self.assertEqual(writer.store_path(self.root), os.path.join(self.root, '.aieos', 'local', 'state.sqlite'))

    def test_a_root_that_is_not_a_folder_raises(self):
        missing = os.path.join(self.root, 'absent')
        with self.assertRaises(ValueError):
            writer.append_event(missing, 'task.drafted', DRAFTED, 'ev-1', T0, REC, task_id=TASK)
        with self.assertRaises(ValueError):
            writer.open_store(missing)
        self.draft()
        with self.assertRaises(ValueError):
            writer.open_store(writer.log_path(self.root))
        with self.assertRaises(TypeError):
            writer.held_leases(None)
        self.assertFalse(os.path.exists(missing))


class R2AppendEvent(Case):

    def test_an_append_is_the_given_bytes_plus_the_line(self):
        r1 = self.draft('ev-1')
        self.assertEqual((r1.result, r1.seq), ('appended', 1))
        before = read(writer.log_path(self.root))
        r2 = self.draft('ev-2')
        self.assertEqual((r2.result, r2.seq), ('appended', 2))
        self.assertEqual(read(writer.log_path(self.root)), before + r2.line)
        self.assertEqual(records.check_log(read(writer.log_path(self.root))).findings(), [])

    def test_a_duplicate_writes_nothing(self):
        self.draft('ev-1')
        before = read(writer.log_path(self.root))
        r = self.draft('ev-1')
        self.assertEqual((r.result, r.seq, r.refusal), ('duplicate', 1, None))
        self.assertEqual(read(writer.log_path(self.root)), before)

    def test_a_refusal_writes_nothing(self):
        self.draft('ev-1')
        before = read(writer.log_path(self.root))
        r = writer.append_event(self.root, 'task.drafted', {'contract_version': 'x'}, 'ev-2', T0, REC, task_id=TASK)
        self.assertEqual((r.result, r.reason), ('refused', 'event'))
        self.assertEqual(read(writer.log_path(self.root)), before)
        r = writer.append_event(self.root, 'task.drafted', DRAFTED, 'ev-1', T0, REC, task_id='TASK-099')
        self.assertEqual((r.result, r.reason), ('refused', 'conflict'))
        self.assertEqual(read(writer.log_path(self.root)), before)

    def test_a_cut_last_line_is_never_extended(self):
        self.draft('ev-1')
        with open(writer.log_path(self.root), 'ab') as f:
            f.write(b'{"event_id":"ev-cut"')
        damaged = read(writer.log_path(self.root))
        r = self.draft('ev-2')
        self.assertEqual((r.result, r.reason), ('refused', 'log'))
        self.assertEqual(read(writer.log_path(self.root)), damaged)

    def test_recorder_is_required(self):
        for bad in (None, '', 7):
            with self.assertRaises(ValueError):
                writer.append_event(self.root, 'task.drafted', DRAFTED, 'ev-1', T0, bad, task_id=TASK)
        self.assertEqual(files_under(self.root), [])

    def test_a_failed_read_back_raises(self):
        path = writer.log_path(self.root)
        self.draft('ev-1')
        log = read(path)
        with self.assertRaises(RuntimeError):
            writer._append_line(path, log + b'x', b'{}\n')

    def test_a_lease_holding_submission_is_appended(self):
        self.store()
        self.session()
        lease = self.grant().value
        r = writer.append_event(self.root, 'task.submitted', SUBMITTED, 'ev-s', T0, REC, task_id=TASK,
                                fencing_token=lease['fencing_token'])
        self.assertEqual((r.result, r.refusal), ('appended', None))


class R3Refusals(Case):

    def submit(self, event_id='ev-s', token=None, task=TASK):
        return writer.append_event(self.root, 'task.submitted', SUBMITTED, event_id, T0, REC, task_id=task,
                                   fencing_token={'epoch': 'epoch-1', 'counter': 9} if token is None else token)

    def test_a_fence_refusal_is_recorded_once(self):
        r = self.submit()
        self.assertEqual((r.result, r.reason), ('refused', 'fence'))
        self.assertEqual((r.refusal.result, r.refusal.seq), ('appended', 1))
        log = read(writer.log_path(self.root))
        lines = records.check_log(log).lines
        self.assertEqual(len(lines), 1)
        event = lines[0].event
        self.assertEqual((event['type'], event['task_id']), ('record.added', TASK))
        self.assertEqual(event['event_id'], writer._digest('refusal', 'ev-s'))
        self.assertEqual(event['payload']['record_id'], writer._digest('refusal-record', 'ev-s'))
        self.assertEqual(event['payload']['refers_to'], 'ev-s')
        self.assertEqual(event['payload']['recorder'], REC)
        again = self.submit()
        self.assertEqual((again.result, again.reason, again.refusal.result), ('refused', 'fence', 'duplicate'))
        self.assertEqual(read(writer.log_path(self.root)), log)

    def test_the_ids_are_the_digests_of_the_contract(self):
        import hashlib
        self.assertEqual(writer._digest('refusal', 'ev-s'), hashlib.sha256(b'refusal\nev-s').hexdigest())
        self.assertEqual(writer._digest('refusal-record', 'ev-s'), hashlib.sha256(b'refusal-record\nev-s').hexdigest())

    def test_no_record_for_no_task_id(self):
        r = writer.append_event(self.root, 'task.submitted', SUBMITTED, 'ev-s', T0, REC,
                                fencing_token={'epoch': 'e', 'counter': 1})
        self.assertEqual((r.result, r.reason, r.refusal), ('refused', 'fence', None))
        self.assertIn('fence: no refusal record, the event names no task_id', r.findings)
        self.assertFalse(os.path.exists(writer.log_path(self.root)))

    def test_a_held_lease_with_another_token_is_refused_and_recorded(self):
        self.store()
        self.session()
        lease = self.grant().value
        token = dict(lease['fencing_token'], counter=lease['fencing_token']['counter'] + 1)
        r = self.submit(token=token)
        self.assertEqual((r.reason, r.refusal.result), ('fence', 'appended'))


class R4Store(Case):

    def test_the_tables_and_the_given_epoch(self):
        self.assertEqual(self.store('epoch-1'), {'epoch': 'epoch-1', 'counter': 0})
        con = sqlite3.connect(writer.store_path(self.root))
        try:
            self.assertEqual(writer._tables(con), writer.TABLES)
            self.assertEqual(con.execute('SELECT epoch, counter FROM store').fetchall(), [('epoch-1', 0)])
        finally:
            con.close()

    def test_a_random_epoch(self):
        epoch = writer.open_store(self.root)['epoch']
        self.assertEqual(len(epoch), 32)
        int(epoch, 16)

    def test_an_existing_store_is_opened_unchanged(self):
        self.store()
        self.session()
        self.grant()
        before = read(writer.store_path(self.root))
        self.assertEqual(writer.open_store(self.root), {'epoch': 'epoch-1', 'counter': 1})
        self.assertEqual(writer.open_store(self.root, 'epoch-1')['counter'], 1)
        self.assertEqual(read(writer.store_path(self.root)), before)

    def test_a_differing_epoch_is_refused(self):
        self.store()
        with self.assertRaises(ValueError):
            writer.open_store(self.root, 'epoch-2')
        with self.assertRaises(ValueError):
            writer.open_store(self.root, '')

    def test_a_store_that_is_not_ours_is_refused(self):
        self.store()
        con = sqlite3.connect(writer.store_path(self.root))
        try:
            con.execute('DROP TABLE sessions')
            con.commit()
        finally:
            con.close()
        with self.assertRaises(ValueError):
            writer.open_store(self.root)
        with self.assertRaises(ValueError):
            writer.held_leases(self.root)

    def test_a_new_store_gives_tokens_unequal_to_a_lost_one(self):
        self.store(None)
        self.session()
        first = self.grant().value['fencing_token']
        with tempfile.TemporaryDirectory() as other:
            writer.open_store(other)
            writer.start_session(other, 's-1', 'agent-1', T0)
            second = writer.grant_lease(other, TASK, 'READY', 'agent-1', 's-1', T0, T0 + H1).value['fencing_token']
        self.assertEqual((first['counter'], second['counter']), (1, 1))
        self.assertNotEqual(first, second)


class R5Grants(Case):

    def setUp(self):
        super().setUp()
        self.store()
        self.session()

    def test_a_grant_in_ready_and_in_rework(self):
        r = self.grant()
        self.assertEqual(r.result, 'done')
        self.assertEqual(r.value, {'task_id': TASK, 'fencing_token': {'epoch': 'epoch-1', 'counter': 1},
                                   'expires_at': T0 + H1})
        self.assertEqual(set(r.value), eventlog.LEASE_KEYS)
        self.assertEqual(self.grant(task='TASK-017', state='REWORK').value['fencing_token']['counter'], 2)

    def test_each_refusal_reason_changes_nothing(self):
        self.grant()
        before = read(writer.store_path(self.root))
        cases = [(dict(task='TASK-017', state='IN_PROGRESS'), 'state'),
                 (dict(), 'held'),
                 (dict(task='TASK-017', until=T0), 'expiry'),
                 (dict(task='TASK-017', sid='s-9'), 'session'),
                 (dict(task='TASK-017', holder='agent-2'), 'session')]
        for kw, reason in cases:
            r = self.grant(**kw)
            self.assertEqual((r.result, r.reason), ('refused', reason), kw)
            self.assertTrue(r.findings)
        self.assertEqual(read(writer.store_path(self.root)), before)
        writer.end_session(self.root, 's-1', T0)
        self.assertEqual(self.grant(task='TASK-017').reason, 'session')
        self.assertEqual(writer.open_store(self.root)['counter'], 1)

    def test_the_counter_only_increases(self):
        counters = []
        for i in range(5):
            lease = self.grant().value
            counters.append(lease['fencing_token']['counter'])
            writer.release_lease(self.root, TASK)
        self.assertEqual(counters, [1, 2, 3, 4, 5])

    def test_bad_arguments_raise(self):
        with self.assertRaises(ValueError):
            self.grant(task='task-1')
        with self.assertRaises(ValueError):
            writer.grant_lease(self.root, TASK, 'READY', 'agent-1', 's-1', T0.replace(tzinfo=None), T0 + H1)
        with self.assertRaises(ValueError):
            writer.grant_lease(self.root, TASK, 'READY', 'agent-1', 's-1', T0, T0 + H1 + datetime.timedelta(
                microseconds=5))
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(ValueError):
                writer.grant_lease(empty, TASK, 'READY', 'agent-1', 's-1', T0, T0 + H1)
            self.assertEqual(files_under(empty), [])


class R6ReleaseExpiryLookup(Case):

    def setUp(self):
        super().setUp()
        self.store()
        self.session()

    def test_release(self):
        lease = self.grant().value
        self.assertEqual(writer.release_lease(self.root, TASK), lease)
        self.assertIsNone(writer.release_lease(self.root, TASK))
        self.assertIsNone(writer.held_lease(self.root, TASK))

    def test_expiry_at_and_before_now(self):
        a = self.grant(task='TASK-001', until=T0 + datetime.timedelta(minutes=10)).value
        b = self.grant(task='TASK-002', until=T0 + datetime.timedelta(minutes=5)).value
        c = self.grant(task='TASK-003', until=T0 + datetime.timedelta(minutes=20)).value
        self.assertEqual(writer.expire_leases(self.root, T0 + datetime.timedelta(minutes=4)), [])
        self.assertEqual(writer.expire_leases(self.root, T0 + datetime.timedelta(minutes=10)), [b, a])
        self.assertEqual(writer.held_leases(self.root), [c])

    def test_lookups_in_lease_keys_form(self):
        a = self.grant(task='TASK-001').value
        b = self.grant(task='TASK-002').value
        self.assertEqual(writer.held_lease(self.root, 'TASK-002'), b)
        self.assertEqual(writer.held_leases(self.root), [a, b])
        for lease in writer.held_leases(self.root):
            self.assertEqual(set(lease), eventlog.LEASE_KEYS)
            self.assertEqual(lease['expires_at'].tzinfo, UTC)

    def test_a_missing_store_is_not_created(self):
        with tempfile.TemporaryDirectory() as empty:
            self.assertIsNone(writer.held_lease(empty, TASK))
            self.assertEqual(writer.held_leases(empty), [])
            self.assertEqual(writer.expire_leases(empty, T0), [])
            self.assertIsNone(writer.release_lease(empty, TASK))
            self.assertEqual(files_under(empty), [])


class R7Sessions(Case):

    def setUp(self):
        super().setUp()
        self.store()

    def test_start_once(self):
        self.session()
        r = writer.start_session(self.root, 's-1', 'agent-1', T0)
        self.assertEqual((r.result, r.reason), ('refused', 'started'))

    def test_end_once_releases_the_sessions_leases(self):
        self.session()
        self.session('s-2', 'agent-2')
        a = self.grant(task='TASK-001').value
        b = self.grant(task='TASK-002', holder='agent-2', sid='s-2').value
        r = writer.end_session(self.root, 's-1', T0 + H1)
        self.assertEqual((r.result, r.value), ('done', [a]))
        self.assertEqual(writer.held_leases(self.root), [b])
        again = writer.end_session(self.root, 's-1', T0 + H1)
        self.assertEqual((again.result, again.reason), ('refused', 'ended'))
        unknown = writer.end_session(self.root, 's-9', T0)
        self.assertEqual((unknown.result, unknown.reason), ('refused', 'session'))


def opens_and_strings(path):
    """The calls of open, the strings naming the project-state directory and the imports of one source file."""
    tree = ast.parse(read(path).decode('utf-8'))
    opens, strings, imports = [], [], set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'open':
            opens.append(node.lineno)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ('open', 'connect'):
            opens.append(node.lineno)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and '.aieos' in node.value:
            strings.append(node.lineno)
        elif isinstance(node, ast.Import):
            imports.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module if not node.level else '.')
    return opens, strings, imports


class R8SingleWriter(unittest.TestCase):

    def test_only_the_writer_opens_files_or_names_the_directory(self):
        names = sorted(n for n in os.listdir(SRC) if n.endswith('.py'))
        self.assertIn('writer.py', names)
        for name in names:
            opens, strings, _ = opens_and_strings(os.path.join(SRC, name))
            if name == 'writer.py':
                self.assertTrue(opens and strings)
            else:
                self.assertEqual((name, opens, strings), (name, [], []))

    def test_the_writers_imports(self):
        _, _, imports = opens_and_strings(os.path.join(SRC, 'writer.py'))
        allowed = {'datetime', 'hashlib', 'json', 'os', 're', 'secrets', 'sqlite3', 'aieos_bootstrap'}
        self.assertLessEqual(imports, allowed)
        self.assertIn('sqlite3', imports)

    def test_the_check_finds_an_open_elsewhere(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'other.py')
            with open(path, 'ab') as f:
                f.write(b"x = open('a', 'rb')\ny = '.aieos/x'\n")
            opens, strings, _ = opens_and_strings(path)
            self.assertEqual((opens, strings), ([1], [2]))

    def test_the_writer_reads_no_clock(self):
        tree = ast.parse(read(os.path.join(SRC, 'writer.py')).decode('utf-8'))
        calls = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertFalse(calls & {'now', 'utcnow', 'today', 'time', 'monotonic', 'perf_counter'})
        self.assertNotIn('time', imports)


class R9ReleaseByToken(Case):
    """TASK-028's rules R1 to R3 on the store: release_lease_token."""

    def setUp(self):
        super().setUp()
        self.store()
        self.session()

    def test_the_held_token_releases_the_lease(self):
        """TASK-028 AC1 and TASK-028 AC11: the held lease's own token removes it and returns it; the store then holds
        none."""
        lease = self.grant().value
        r = writer.release_lease_token(self.root, TASK, dict(lease['fencing_token']))
        self.assertEqual((r.result, r.reason, r.value), ('done', None, lease))
        self.assertIsNone(writer.held_lease(self.root, TASK))

    def test_another_token_changes_nothing(self):
        """TASK-028 AC1 and TASK-028 AC11: another epoch or another counter is refused with reason "token" and one
        finding, and the lease is still held."""
        lease = self.grant().value
        token = lease['fencing_token']
        for other in (dict(token, epoch='epoch-2'), dict(token, counter=token['counter'] + 1), dict(token, counter=0)):
            with self.subTest(other=other):
                r = writer.release_lease_token(self.root, TASK, other)
                self.assertEqual((r.result, r.reason, r.value, len(r.findings)), ('refused', 'token', None, 1))
                for part in (repr(token['epoch']), repr(token['counter']), repr(other['epoch']), repr(other['counter'])):
                    self.assertIn(part, r.findings[0])
                self.assertEqual(writer.held_lease(self.root, TASK), lease)

    def test_no_lease_or_no_store_changes_nothing(self):
        """TASK-028 AC1 and TASK-028 AC11: with no lease held, or no store under the root, the result is refused with
        reason "none", and no store is created."""
        r = writer.release_lease_token(self.root, TASK, {'epoch': 'epoch-1', 'counter': 1})
        self.assertEqual((r.result, r.reason, r.value, len(r.findings)), ('refused', 'none', None, 1))
        with tempfile.TemporaryDirectory() as empty:
            r = writer.release_lease_token(empty, TASK, {'epoch': 'epoch-1', 'counter': 1})
            self.assertEqual((r.result, r.reason, len(r.findings)), ('refused', 'none', 1))
            self.assertEqual(files_under(empty), [])

    def test_a_malformed_token_raises_before_the_store_is_looked_at(self):
        """TASK-028 AC2 and TASK-028 AC11: with no store under the root, a malformed token still raises ValueError (it
        is checked before the store is looked for), and nothing is created."""
        with tempfile.TemporaryDirectory() as empty:
            for bad in (None, {'epoch': 'epoch-1', 'counter': True}, {'epoch': 1, 'counter': 1}):
                with self.subTest(bad=bad):
                    with self.assertRaises(ValueError):
                        writer.release_lease_token(empty, TASK, bad)
            self.assertEqual(files_under(empty), [])

    def test_a_malformed_token_raises_and_changes_nothing(self):
        """TASK-028 AC2 and TASK-028 AC11: a token out of the store's form raises ValueError, a bool counter and an
        integer epoch among them, and the store is unchanged."""
        lease = self.grant().value
        good = lease['fencing_token']
        for bad in (None, [], 'epoch-1:1', {'epoch': 'epoch-1'}, dict(good, extra=1), dict(good, epoch=1),
                    dict(good, epoch=''), dict(good, epoch=None), dict(good, counter=True), dict(good, counter=False),
                    dict(good, counter=1.0), dict(good, counter='1'), dict(good, counter=-1)):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    writer.release_lease_token(self.root, TASK, bad)
                self.assertEqual(writer.held_lease(self.root, TASK), lease)
        with self.assertRaises(ValueError):
            writer.release_lease_token(self.root, 'task-1', good)

    def test_the_removal_is_keyed_on_task_epoch_and_counter(self):
        """TASK-028 AC3 and TASK-028 AC11: the one DELETE of release_lease_token names the task, the epoch and the
        counter as parameters, in one transaction with the read."""
        source = read(os.path.join(SRC, 'writer.py')).decode('utf-8')
        body = source.split('def release_lease_token(', 1)[1].split('\ndef ', 1)[0]
        self.assertIn("'DELETE FROM leases WHERE task_id = ? AND fencing_epoch = ? AND fencing_counter = ?'", body)
        self.assertEqual(body.count('DELETE'), 1)
        self.assertEqual(body.count('_transaction('), 1)

    def test_a_lease_granted_since_is_not_released_by_the_old_token(self):
        """TASK-028 AC3 and TASK-028 AC11 (DEF-0053 F3): a lease expires, the task is granted again to another holder,
        and the first lease's token releases nothing; the old token's release_lease would have removed the new lease."""
        first = self.grant(until=T0 + datetime.timedelta(minutes=5)).value
        self.assertEqual(writer.expire_leases(self.root, T0 + datetime.timedelta(minutes=5)), [first])
        self.session(sid='s-2', holder='agent-2')
        second = self.grant(holder='agent-2', sid='s-2', at=T0 + datetime.timedelta(minutes=6)).value
        r = writer.release_lease_token(self.root, TASK, first['fencing_token'])
        self.assertEqual((r.result, r.reason), ('refused', 'token'))
        self.assertEqual(writer.held_lease(self.root, TASK), second)


class R10ReadLog(Case):
    """TASK-026's R11 on the writer: read_log."""

    def test_an_absent_log_is_empty_bytes_and_nothing_is_created(self):
        """TASK-026 AC11 and TASK-026 AC15: with no log under the root, read_log gives b"" and creates nothing."""
        self.assertEqual(writer.read_log(self.root), b'')
        self.assertEqual(files_under(self.root), [])

    def test_a_log_with_lines_is_its_bytes(self):
        """TASK-026 AC11 and TASK-026 AC15: with a log of two lines, read_log gives its bytes and changes nothing."""
        self.draft('ev-1')
        self.draft('ev-2')
        before = files_under(self.root)
        data = read(writer.log_path(self.root))
        self.assertEqual(data.count(b'\n'), 2)
        self.assertEqual(writer.read_log(self.root), data)
        self.assertEqual(files_under(self.root), before)
        self.assertEqual(read(writer.log_path(self.root)), data)

    def test_a_root_out_of_form_raises(self):
        """TASK-026 AC11 and TASK-026 AC15: the root is checked as the writer's other functions check it."""
        with self.assertRaises(TypeError):
            writer.read_log('')
        with self.assertRaises(ValueError):
            writer.read_log(os.path.join(self.root, 'missing'))


class R11SessionLease(Case):
    """TASK-066's rule R1 over real stores: session_lease's arguments, order and cases."""

    def lookup(self, sid='s-1', now=T0, root=None, timeout=5.0):
        return writer.session_lease(self.root if root is None else root, sid, now, timeout)

    def refused(self, r, reason):
        self.assertEqual((r.result, r.reason, r.value, len(r.findings)), ('refused', reason, None, 1), r)
        self.assertTrue(r.findings[0].startswith(reason + ': '), r.findings)

    def sql(self, *statements):
        con = sqlite3.connect(writer.store_path(self.root), isolation_level=None)
        try:
            for s in statements:
                con.execute(s)
        finally:
            con.close()

    def test_the_tied_lease(self):
        """TASK-066 AC1, TASK-066 AC2 and TASK-066 AC9: one unexpired lease of a started session gives "done", reason
        "tied", value the lease as held_lease gives it; judge gives "tied" too."""
        from aieos_bootstrap import claude_code_store
        self.store()
        self.session()
        lease = self.grant().value
        r = self.lookup()
        self.assertEqual((r.result, r.reason, r.findings, r.value), ('done', 'tied', (), lease))
        self.assertEqual(r.value, writer.held_lease(self.root, TASK))
        self.assertEqual(set(r.value), eventlog.LEASE_KEYS)
        out = claude_code_store.judge('s-1', self.root, None, T0)
        self.assertEqual((out['outcome'], out['root'], out['lease']), ('tied', self.root, lease))

    def test_each_bad_argument(self):
        """TASK-066 AC1 and TASK-066 AC9: each bad session id, now and timeout gives "argument", checked before the
        root (here a missing one); a raising tzinfo and a lone surrogate among them; no exception escapes."""

        class Raising(datetime.tzinfo):
            def utcoffset(self, dt):
                raise RuntimeError('made-up')
        missing = os.path.join(self.root, 'absent')
        cases = [dict(sid=''), dict(sid=0), dict(sid=b's-1'), dict(sid=['s']), dict(sid='s-\ud800'),
                 dict(now=None), dict(now=T0.replace(tzinfo=None)), dict(now=T0.replace(microsecond=1)),
                 dict(now=T0.astimezone(datetime.timezone(H1))), dict(now=T0.date()),
                 dict(now=T0.replace(tzinfo=Raising())), dict(timeout=0), dict(timeout=-1), dict(timeout=61),
                 dict(timeout=float('inf')), dict(timeout=float('nan')), dict(timeout=True), dict(timeout='5'),
                 dict(timeout=None)]
        for kw in cases:
            with self.subTest(kw=kw):
                self.refused(self.lookup(root=missing, **kw), 'argument')
        self.assertEqual(self.lookup(root=missing, timeout=60).reason, 'root')
        self.assertEqual(self.lookup(root=missing, timeout=0.5).reason, 'root')

    def test_the_root(self):
        """TASK-066 AC1, TASK-066 AC2 and TASK-066 AC9: a missing root, a root that is a file and a relative root,
        with a session id set, give "root" through session_lease; through judge the missing and the file root give
        "root" and the relative root judge's own "argument"; nothing is created."""
        from aieos_bootstrap import claude_code_store
        self.draft()
        missing = os.path.join(self.root, 'absent')
        a_file = writer.log_path(self.root)
        for bad in (missing, a_file, 'relative-folder', os.curdir, '', None, 7):
            with self.subTest(bad=bad):
                self.refused(writer.session_lease(bad, 's-1', T0), 'root')
        for bad, reason in ((missing, 'root'), (a_file, 'root'), ('relative-folder', 'argument'),
                            (os.curdir, 'argument')):
            with self.subTest(bad=bad):
                out = claude_code_store.judge('s-1', bad, None, T0)
                self.assertEqual((out['outcome'], out['reason']), ('refuse', reason))
        self.assertEqual(files_under(self.root), ['.aieos/events.jsonl'])

    def test_no_store(self):
        """TASK-066 AC2 and TASK-066 AC9: no store under an existing root gives "no_store" and creates nothing."""
        self.refused(self.lookup(), 'no_store')
        self.refused(self.lookup(sid=None), 'no_store')
        self.assertEqual(files_under(self.root), [])

    def test_tables_of_another_form(self):
        """TASK-066 AC2 and TASK-066 AC9: a missing table, a fourth table and two store rows give "tables"."""
        self.store()
        self.session()
        self.grant()
        self.sql('CREATE TABLE extra (task_id TEXT)')
        self.refused(self.lookup(), 'tables')
        self.sql('DROP TABLE extra', "INSERT INTO store (epoch, counter) VALUES ('x', 0)")
        self.refused(self.lookup(), 'tables')
        self.sql("DELETE FROM store WHERE epoch = 'x'")
        self.assertEqual(self.lookup().reason, 'tied')
        self.sql('DROP TABLE sessions')
        self.refused(self.lookup(), 'tables')

    def test_no_session_id(self):
        """TASK-066 AC2 and TASK-066 AC9: with no session id, no lease row gives "done", reason "no_lease_row", value
        None; an unexpired or an expired lease row gives "lease_row_without_session"."""
        self.store()
        self.session()
        r = self.lookup(sid=None)
        self.assertEqual((r.result, r.reason, r.value, r.findings), ('done', 'no_lease_row', None, ()))
        self.grant(until=T0 + datetime.timedelta(minutes=5))
        self.refused(self.lookup(sid=None), 'lease_row_without_session')
        self.refused(self.lookup(sid=None, now=T0 + H1), 'lease_row_without_session')

    def test_a_session_id_with_no_lease_row(self):
        """TASK-066 AC2 and TASK-066 AC9: with a session id set, a store with no lease row refuses "no_lease_row"."""
        self.store()
        self.session()
        self.refused(self.lookup(), 'no_lease_row')

    def test_the_session_cases(self):
        """TASK-066 AC2 and TASK-066 AC9: no such session gives "session"; an ended session (two sessions, a lease
        granted to the second, the first ended) gives "ended", and so does ended_at ""."""
        self.store()
        self.session()
        self.session('s-2', 'agent-2')
        self.grant(holder='agent-2', sid='s-2')
        self.refused(self.lookup(sid='s-9'), 'session')
        writer.end_session(self.root, 's-1', T0)
        self.refused(self.lookup(sid='s-1'), 'ended')
        self.sql("UPDATE sessions SET ended_at = '' WHERE session_id = 's-2'")
        self.refused(self.lookup(sid='s-2'), 'ended')

    def test_the_count_of_unexpired_leases(self):
        """TASK-066 AC2 and TASK-066 AC9: zero and two unexpired leases of the session give "leases"; one unexpired
        and one expired give "tied"; a lease expiring exactly at now is expired (expires_at > now)."""
        self.store()
        self.session()
        a = self.grant(task='TASK-001', until=T0 + datetime.timedelta(minutes=5)).value
        self.assertEqual(self.lookup().value, a)
        self.refused(self.lookup(now=T0 + datetime.timedelta(minutes=5)), 'leases')
        b = self.grant(task='TASK-002', until=T0 + H1).value
        self.refused(self.lookup(), 'leases')
        r = self.lookup(now=T0 + datetime.timedelta(minutes=5))
        self.assertEqual((r.reason, r.value), ('tied', b))
        self.refused(self.lookup(now=T0 + H1), 'leases')

    def test_a_malformed_stored_time(self):
        """TASK-066 AC2 and TASK-066 AC9: a malformed time on the session's own lease row gives "unreadable"; one on
        another session's lease row is not parsed."""
        self.store()
        self.session()
        self.session('s-2', 'agent-2')
        lease = self.grant().value
        self.grant(task='TASK-002', holder='agent-2', sid='s-2')
        self.sql("UPDATE leases SET expires_at = 'soon' WHERE session_id = 's-2'")
        self.assertEqual(self.lookup().value, lease)
        self.refused(self.lookup(sid='s-2'), 'unreadable')

    def test_a_zero_byte_and_a_garbage_store(self):
        """TASK-066 AC2 and TASK-066 AC9: a 0-byte store file gives "tables" and a garbage file of at least 100 bytes
        "unreadable"; both are built by open_store with a failing statement, which leaves the folders and an empty
        store file after its rollback, and the garbage is written with open "ab"."""
        from unittest import mock
        with mock.patch.object(writer, '_SCHEMA', ('CREATE TABLE broken (',)):
            with self.assertRaises(sqlite3.Error):
                writer.open_store(self.root, 'epoch-1')
        path = writer.store_path(self.root)
        self.assertEqual(read(path), b'')
        self.refused(self.lookup(), 'tables')
        self.assertEqual(read(path), b'')
        with open(path, 'ab') as f:
            f.write(b'made-up bytes, not a store. ' * 5)
        self.assertGreaterEqual(len(read(path)), 100)
        self.refused(self.lookup(), 'unreadable')
        self.assertEqual(files_under(self.root), ['.aieos/local/state.sqlite'])


class R12StoreUri(unittest.TestCase):
    """TASK-066's rule R2 on _store_uri: fixed strings on every platform, its separators given by the test."""

    def test_fixed_strings(self):
        """TASK-066 AC3 and TASK-066 AC9: a POSIX path, a Windows-form path, a backslash in a POSIX name, a space, "#",
        "%", "?", a colon outside a drive and a non-ASCII name."""
        cases = [(('/home/u/p/.aieos/local/state.sqlite', '/', None), 'file:///home/u/p/.aieos/local/state.sqlite?mode=ro'),
                 (('C:\\Users\\u\\p\\state.sqlite', '\\', '/'), 'file:///C:/Users/u/p/state.sqlite?mode=ro'),
                 (('c:/u\\p', '\\', '/'), 'file:///c:/u/p?mode=ro'),
                 (('/a/b\\c', '/', None), 'file:///a/b%5Cc?mode=ro'),
                 (('/a b/c#d/e%f/g?h', '/', None), 'file:///a%20b/c%23d/e%25f/g%3Fh?mode=ro'),
                 (('/a:b/C:', '/', None), 'file:///a%3Ab/C%3A?mode=ro'),
                 (('/caf\u00e9/\u65e5', '/', None), 'file:///caf%C3%A9/%E6%97%A5?mode=ro'),
                 (('D:\\x y', '\\', '/'), 'file:///D:/x%20y?mode=ro')]
        for args, want in cases:
            with self.subTest(args=args):
                self.assertEqual(writer._store_uri(*args), want)

    def test_unc_and_surrogates_are_refused(self):
        """TASK-066 AC3 and TASK-066 AC9: a path starting with two separators (a UNC path) and a path not encodable as
        UTF-8 raise ValueError."""
        for args in (('\\\\server\\share\\x', '\\', '/'), ('//server/share/x', '\\', '/'), ('//x', '/', None),
                     ('/a/\udcff', '/', None)):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    writer._store_uri(*args)


class R13PresenceAndLink(Case):
    """TASK-066's rule R3: the presence step and the link check through stand-ins for os.lstat, os.path.realpath and
    os.path.normcase, each patched on writer's os functions for one call and passing every other path to the real
    function. No link or folder is created."""

    def setUp(self):
        super().setUp()
        self.store()
        self.session()
        self.lease = self.grant().value
        self.path = writer.store_path(self.root)

    def lookup(self):
        return writer.session_lease(self.root, 's-1', T0)

    def with_lstat(self, effect):
        import types
        from unittest import mock
        real = writer.os.lstat

        def fake(p, *a, **k):
            if p == self.path:
                if isinstance(effect, BaseException):
                    raise effect
                return types.SimpleNamespace(st_mode=effect)
            return real(p, *a, **k)
        with mock.patch.object(writer.os, 'lstat', fake):
            return self.lookup()

    def with_realpath(self, mapping, normcase=None):
        from unittest import mock
        real = writer.os.path.realpath

        def fake(p, *a, **k):
            if p in mapping:
                if isinstance(mapping[p], BaseException):
                    raise mapping[p]
                return mapping[p]
            return real(p, *a, **k)
        with mock.patch.object(writer.os.path, 'realpath', fake):
            if normcase is None:
                return self.lookup()
            with mock.patch.object(writer.os.path, 'normcase', normcase):
                return self.lookup()

    def test_the_presence_step(self):
        """TASK-066 AC2 and TASK-066 AC9: FileNotFoundError and NotADirectoryError give "no_store"; another OSError
        and a ValueError "unreadable"; a directory, a link and another kind at the store path give "link"; a regular
        file goes on to "tied"."""
        for effect, reason in ((FileNotFoundError('x'), 'no_store'), (NotADirectoryError('x'), 'no_store'),
                               (PermissionError('x'), 'unreadable'), (OSError('x'), 'unreadable'),
                               (ValueError('x'), 'unreadable'), (0o040755, 'link'), (0o120777, 'link'),
                               (0o010644, 'link'), (0o140755, 'link')):
            with self.subTest(effect=effect):
                r = self.with_lstat(effect)
                self.assertEqual((r.result, r.reason), ('refused', reason))
        self.assertEqual(self.with_lstat(0o100600).value, self.lease)

    def test_a_path_resolving_elsewhere_is_a_link(self):
        """TASK-066 AC2 and TASK-066 AC9: the store file, the local folder or the project-state folder resolving
        elsewhere gives "link"."""
        rroot = os.path.realpath(self.root)
        for there in (os.path.join(rroot, '.aieos', 'local', 'other.sqlite'),
                      os.path.join(rroot, '.aieos', 'elsewhere', 'state.sqlite'),
                      os.path.join(rroot, 'elsewhere', 'local', 'state.sqlite'),
                      os.path.join(os.path.dirname(rroot), 'other-root', '.aieos', 'local', 'state.sqlite')):
            with self.subTest(there=there):
                r = self.with_realpath({self.path: there})
                self.assertEqual((r.result, r.reason), ('refused', 'link'))

    def test_case_and_separator_differences_are_not_links(self):
        """TASK-066 AC2 and TASK-066 AC9: with ntpath.normcase standing in for os.path.normcase, a root whose
        realpath differs only in case or in separators gives no "link"; nor does a short name whose realpath is the
        same expanded form on both sides."""
        import ntpath
        rroot = os.path.realpath(self.root)
        for other in (rroot.upper(), rroot.lower(), rroot.replace(os.sep, '/')):
            with self.subTest(other=other):
                r = self.with_realpath({self.root: other}, normcase=ntpath.normcase)
                self.assertEqual((r.reason, r.value), ('tied', self.lease))
        from unittest import mock
        short = os.path.join(self.root, '.')
        keyed = {writer.store_path(short): os.path.join(rroot, '.aieos', 'local', 'state.sqlite'), short: rroot}
        hits = dict.fromkeys(keyed, 0)
        real = writer.os.path.realpath

        def counting(p, *a, **k):
            if p in keyed:
                hits[p] += 1
                return keyed[p]
            return real(p, *a, **k)
        with mock.patch.object(writer.os.path, 'realpath', counting):
            r = writer.session_lease(short, 's-1', T0)
        for p in keyed:
            with self.subTest(keyed=p):
                self.assertGreaterEqual(hits[p], 1)
        self.assertNotEqual(r.reason, 'link')
        self.assertEqual((r.reason, r.value), ('tied', self.lease))
        self.assertEqual(writer.session_lease(short, 's-1', T0).reason, 'tied')

    def test_a_raising_check_or_uri(self):
        """TASK-066 AC1 and TASK-066 AC9: a raising realpath gives "link", a raising _store_uri "unreadable"; the
        finding names the type only."""
        from unittest import mock
        r = self.with_realpath({self.path: RuntimeError('made-up message')})
        self.assertEqual((r.reason, r.findings), ('link', ('link: RuntimeError',)))

        def boom(*a):
            raise ValueError('made-up message')
        with mock.patch.object(writer, '_store_uri', boom):
            r = self.lookup()
        self.assertEqual((r.reason, r.findings), ('unreadable', ('unreadable: ValueError',)))


class R14WhatTheWriterSays(unittest.TestCase):
    """TASK-066's rules R5 and R6 on writer.py: the current text's calls and the docstrings' words."""

    def source(self):
        return read(os.path.join(SRC, 'writer.py')).decode('utf-8')

    def test_the_lookup_connects_read_only(self):
        """TASK-066 AC3 and TASK-066 AC6: the lookup's one connect passes the URI, uri=True, the timeout and
        isolation_level None, runs a deferred BEGIN, ends the transaction and closes in finally blocks; no PRAGMA; no
        one-argument replace."""
        text = self.source()
        part = text.split('# ---- the read-only lookup of the store (task TASK-066) ----', 1)[1]
        self.assertIn("sqlite3.connect(uri, uri=True, timeout=timeout, isolation_level=None)", part)
        self.assertIn("'?mode=ro'", part)
        self.assertIn("con.execute('BEGIN DEFERRED')", part)
        self.assertIn("con.execute('ROLLBACK')", part)
        self.assertIn('con.close()', part)
        self.assertEqual(part.count('finally:'), 2)
        self.assertNotIn('PRAGMA', part)
        self.assertNotIn('INSERT', part)
        self.assertNotIn('UPDATE', part)
        self.assertNotIn('DELETE', part)
        self.assertNotIn('makedirs', part)
        tree = ast.parse(part)
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'replace':
                self.assertEqual(len(n.args), 2)

    def test_the_docstrings_state_what_the_contract_names(self):
        """TASK-066 AC7: the module docstring names session_lease and TASK-066 and its limits the read-only and lock
        text; session_lease's docstring states the outcomes, read-only and the lock, the URI rule, the table form,
        the presence step and the link check with their limits, the arguments and the fail-open direction of now, and
        that nothing is placed or measured (whitespace collapsed)."""
        tree = ast.parse(self.source())
        mod = ' '.join(ast.get_docstring(tree).split())
        for words in ('``session_lease`` (task TASK-066', 'reads the store only', 'takes only a shared lock',
                      'refused without a record'):
            with self.subTest(words=words):
                self.assertIn(words, mod)
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'session_lease')
        doc = ' '.join(ast.get_docstring(fn).split())
        for words in ('bullets 3 to 6', '"tied"', 'enforce nothing', 'refuse without a record', 'empty-as-absent rule',
                      'expires_at > now', 'read-only mode', 'deferred BEGIN', 'shared lock', 'long commit',
                      'hot rollback journal', 'WAL state', 'link check\'s verified left-hand string', 'UNC path',
                      'not encodable as UTF-8', 'four-table form', 'K1', 'Specification 2 revision 7 section 3',
                      'os.lstat of the store path first', 'never exercised in CI, which runs on Linux',
                      'short (8.3) names', 'hard links and bind mounts', 'two steps', 'a later contract\'s',
                      'fail-open direction', 'process clock', 'No hook is placed', 'nothing measured', 'CC-3', 'C6'):
            with self.subTest(words=words):
                self.assertIn(words, doc)


# ---- task TASK-067: the reads table and the read-set accumulation ----

class ReadsCase(Case):
    """A store with session s-1 and one live lease of it on TASK-067, and helpers over a test connection."""

    def tied(self, task='TASK-067', until=None):
        self.store()
        self.session()
        return self.grant(task=task, until=until).value

    def sql(self, *statements):
        con = sqlite3.connect(writer.store_path(self.root), isolation_level=None)
        try:
            out = None
            for s in statements:
                out = con.execute(s).fetchall()
            return out
        finally:
            con.close()

    def rows(self):
        return self.sql('SELECT session_id, task_id, seq, path FROM reads ORDER BY rowid')

    def dump(self):
        con = sqlite3.connect(writer.store_path(self.root), isolation_level=None)
        try:
            out = {}
            for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"):
                out[name] = con.execute('SELECT * FROM "%s" ORDER BY rowid' % name).fetchall()
            return out
        finally:
            con.close()

    def refused(self, r, reason):
        self.assertEqual((r.result, r.reason, r.value, len(r.findings)), ('refused', reason, None, 1), r)
        self.assertTrue(r.findings[0].startswith(reason + ': '), r.findings)

    def add(self, paths, sid='s-1', now=T0, timeout=5.0, root=None):
        return writer.add_reads(self.root if root is None else root, sid, paths, now, timeout)


class R15ReadsTable(ReadsCase):
    """TASK-067's rule R1: the four-table form and its constraints."""

    def test_the_four_table_form_is_created(self):
        """TASK-067 AC1 and TASK-067 AC9: open_store creates the four tables, sqlite_master holds exactly them and their
        automatic indexes and no sqlite_sequence, and reads is an ordinary rowid table."""
        self.store()
        names = self.sql("SELECT type, name FROM sqlite_master ORDER BY name")
        tables = sorted(n for t, n in names if t == 'table')
        self.assertEqual(tables, ['leases', 'reads', 'sessions', 'store'])
        self.assertEqual(sorted(t for t, n in names), ['index'] * (len(names) - 4) + ['table'] * 4)
        self.assertTrue(all(n.startswith('sqlite_autoindex_') for t, n in names if t == 'index'))
        self.assertNotIn('sqlite_sequence', [n for _, n in names])
        self.assertEqual(writer.TABLES['reads'], ('session_id', 'task_id', 'seq', 'path'))
        self.sql("INSERT INTO reads (session_id, task_id, seq, path) VALUES ('s', 'TASK-1', 0, 'a')")
        self.assertEqual(self.sql('SELECT rowid FROM reads'), [(1,)])
        self.assertEqual(writer.open_store(self.root, 'epoch-1')['epoch'], 'epoch-1')

    def test_the_constraints_hold(self):
        """TASK-067 AC1 and TASK-067 AC9: a duplicate (session, task, path), a duplicate (session, task, seq) and a
        NULL in each column raise sqlite3.IntegrityError through a test connection."""
        self.store()
        self.sql("INSERT INTO reads (session_id, task_id, seq, path) VALUES ('s', 'TASK-1', 0, 'a')")
        bad = ["INSERT INTO reads (session_id, task_id, seq, path) VALUES ('s', 'TASK-1', 1, 'a')",
               "INSERT INTO reads (session_id, task_id, seq, path) VALUES ('s', 'TASK-1', 0, 'b')",
               "INSERT INTO reads (session_id, task_id, seq, path) VALUES (NULL, 'TASK-1', 2, 'c')",
               "INSERT INTO reads (session_id, task_id, seq, path) VALUES ('s', NULL, 3, 'd')",
               "INSERT INTO reads (session_id, task_id, seq, path) VALUES ('s', 'TASK-1', NULL, 'e')",
               "INSERT INTO reads (session_id, task_id, seq, path) VALUES ('s', 'TASK-1', 4, NULL)"]
        for s in bad:
            with self.subTest(s=s):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.sql(s)

    def test_a_three_table_store_is_refused(self):
        """TASK-067 AC1 and TASK-067 AC9: on a store whose reads table a test connection dropped, open_store and every
        existing writer function raise, session_lease gives "tables", and add_reads, stored_reads and remove_reads
        give "tables"; _check_schema's message names reads."""
        self.tied()
        self.sql('DROP TABLE reads')
        with self.assertRaises(ValueError) as cm:
            writer.open_store(self.root)
        self.assertIn('reads', str(cm.exception))
        for call in (lambda: writer.start_session(self.root, 's-2', 'agent-2', T0),
                     lambda: writer.end_session(self.root, 's-1', T0),
                     lambda: writer.grant_lease(self.root, 'TASK-002', 'READY', 'agent-1', 's-1', T0, T0 + H1),
                     lambda: writer.release_lease(self.root, 'TASK-067'), lambda: writer.expire_leases(self.root, T0),
                     lambda: writer.held_lease(self.root, 'TASK-067'), lambda: writer.held_leases(self.root)):
            with self.subTest(call=call):
                with self.assertRaises(ValueError):
                    call()
        self.refused(writer.session_lease(self.root, 's-1', T0), 'tables')
        self.refused(self.add(['a']), 'tables')
        self.refused(writer.stored_reads(self.root, 's-1', 'TASK-067'), 'tables')
        self.refused(writer.remove_reads(self.root, 's-1', 'TASK-067'), 'tables')

    def test_a_reads_table_without_the_constraints_passes_the_check(self):
        """TASK-067 AC1 and TASK-067 AC9: a reads table whose columns match but whose constraints are missing passes
        _check_schema (a stated limit)."""
        self.tied()
        self.sql('DROP TABLE reads', 'CREATE TABLE reads (session_id, task_id, seq, path)')
        self.assertEqual(self.add(['a']).value, 1)


class R16AddReads(ReadsCase):
    """TASK-067's rule R2: add_reads' arguments, order, bounds, seq and cases over real stores."""

    def test_paths_are_added_once_in_first_seen_order(self):
        """TASK-067 AC2 and TASK-067 AC9: an added path, a path repeated in one call and a path stored before are
        each kept once; the seq values read through a test connection are 0, 1, 2 across calls; a tuple is accepted;
        numeric-looking and whitespace paths come back unchanged as text."""
        self.tied()
        self.assertEqual(self.add(['a', 'b', 'a']).value, 2)
        self.assertEqual(self.add(('b', '007', '1e3', ' ')).value, 3)
        self.assertEqual(self.rows(), [('s-1', 'TASK-067', 0, 'a'), ('s-1', 'TASK-067', 1, 'b'), ('s-1', 'TASK-067', 2, '007'),
                                       ('s-1', 'TASK-067', 3, '1e3'), ('s-1', 'TASK-067', 4, ' ')])
        self.assertEqual(writer.stored_reads(self.root, 's-1', 'TASK-067').value, ['a', 'b', '007', '1e3', ' '])

    def test_the_next_seq_is_the_largest_plus_one(self):
        """TASK-067 AC2 and TASK-067 AC9: after a gap made by a test connection, the next seq is the largest stored
        plus one, not the count."""
        self.tied()
        self.add(['a', 'b', 'c'])
        self.sql("DELETE FROM reads WHERE path = 'b'")
        self.add(['d'])
        self.assertEqual([r[2:] for r in self.rows()], [(0, 'a'), (2, 'c'), (3, 'd')])

    def test_two_tasks_of_one_session_are_kept_apart(self):
        """TASK-067 AC2 and TASK-067 AC9: the task is the lease's; a lease released and another granted keeps the
        reads of each task apart."""
        self.tied()
        self.add(['a'])
        writer.release_lease(self.root, 'TASK-067')
        self.grant(task='TASK-068')
        self.add(['a', 'b'])
        self.assertEqual(writer.stored_reads(self.root, 's-1', 'TASK-067').value, ['a'])
        self.assertEqual(writer.stored_reads(self.root, 's-1', 'TASK-068').value, ['a', 'b'])

    def test_an_empty_list(self):
        """TASK-067 AC2 and TASK-067 AC9: an empty list gives "done" 0 with a live lease and is refused without one."""
        self.store()
        self.session()
        self.refused(self.add([]), 'no_lease_row')
        self.grant(task='TASK-067')
        self.assertEqual((self.add([]).result, self.add([]).value), ('done', 0))

    def test_each_bad_argument(self):
        """TASK-067 AC2 and TASK-067 AC9: each bad session id, paths, now and timeout gives "argument", before the root
        (a missing one); a str subclass session id and a list subclass are refused; a raising tzinfo too."""

        class S(str):
            pass

        class L(list):
            pass

        class Raising(datetime.tzinfo):
            def utcoffset(self, dt):
                raise RuntimeError('made-up')
        missing = os.path.join(self.root, 'absent')
        cases = [dict(sid=''), dict(sid=None), dict(sid=7), dict(sid=S('s-1')), dict(sid='s-\ud800'),
                 dict(paths='a'), dict(paths=None), dict(paths=L(['a'])), dict(paths={'a'}),
                 dict(now=T0.replace(tzinfo=None)), dict(now=T0.replace(microsecond=1)),
                 dict(now=T0.astimezone(datetime.timezone(H1))), dict(now=T0.date()),
                 dict(now=T0.replace(tzinfo=Raising())), dict(timeout=True), dict(timeout=0), dict(timeout=61),
                 dict(timeout=float('inf')), dict(timeout=float('nan')), dict(timeout='5'), dict(timeout=None)]
        for kw in cases:
            paths = kw.pop('paths', ['a'])
            with self.subTest(kw=kw, paths=paths):
                self.refused(self.add(paths, root=missing, **kw), 'argument')
        self.refused(self.add(['a'], root=missing), 'root')

    def test_each_bad_path(self):
        """TASK-067 AC2 and TASK-067 AC9: a path not exactly a str (a str subclass among them), empty, holding NUL,
        longer than 4096 characters or holding a lone surrogate gives "path", before any store read; 4096 passes."""

        class S(str):
            pass
        self.tied()
        for bad in (S('a'), 7, None, '', 'a\x00b', 'x' * 4097, 'a\ud800'):
            with self.subTest(bad=bad):
                self.refused(self.add(['ok', bad]), 'path')
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.add(['x' * 4096]).value, 1)

    def test_the_earlier_reason_wins(self):
        """TASK-067 AC2 and TASK-067 AC9: an argument and a path error give "argument"; an early bound and a path error
        "bound"; a path error on a store with no lease row "path"; a bad path on a missing root "path"."""
        self.store()
        self.refused(self.add(['']), 'path')
        self.refused(self.add([''], timeout=0), 'argument')
        self.refused(self.add(['a'] * 10000 + ['']), 'bound')
        self.refused(self.add([''], root=os.path.join(self.root, 'absent')), 'path')

    def test_the_bounds(self):
        """TASK-067 AC2 and TASK-067 AC9: 10000 paths in one call pass and 10001 are refused early; with 9999 stored
        one new and one duplicate pass and two new are refused; with exactly 10000 stored a duplicate and an empty list
        pass with 0 and a new path is refused; nothing changes on a refusal."""
        self.tied()
        self.refused(self.add(['p%d' % i for i in range(10001)]), 'bound')
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.add(['p%d' % i for i in range(10000)]).value, 10000)
        self.assertEqual(writer.remove_reads(self.root, 's-1', 'TASK-067').value, 10000)
        self.assertEqual(self.add(['p%d' % i for i in range(9999)]).value, 9999)
        before = self.dump()
        self.refused(self.add(['n1', 'n2']), 'bound')
        self.assertEqual(self.dump(), before)
        self.assertEqual(self.add(['n1', 'p0']).value, 1)
        self.assertEqual(self.add(['n1', 'p0']).value, 0)
        self.assertEqual(self.add([]).value, 0)
        self.refused(self.add(['n2']), 'bound')

    def test_a_stored_count_above_the_bound(self):
        """TASK-067 AC2 and TASK-067 AC9: more than 10000 stored rows (written by a test connection) refuse "bound"
        before any path is read."""
        self.tied()
        con = sqlite3.connect(writer.store_path(self.root), isolation_level=None)
        try:
            con.executemany('INSERT INTO reads (session_id, task_id, seq, path) VALUES (?, ?, ?, ?)',
                            [('s-1', 'TASK-067', i, 'p%d' % i) for i in range(10001)])
        finally:
            con.close()
        self.refused(self.add(['p0']), 'bound')

    def test_the_live_lease_reasons(self):
        """TASK-067 AC2 and TASK-067 AC9: no lease row, no such session, an ended session, zero and two live leases,
        and a malformed stored time give the helper's reasons; nothing is stored."""
        self.store()
        self.session()
        self.refused(self.add(['a']), 'no_lease_row')
        self.session('s-2', 'agent-2')
        self.grant(task='TASK-002', holder='agent-2', sid='s-2')
        self.refused(self.add(['a'], sid='s-9'), 'session')
        self.refused(self.add(['a']), 'leases')
        self.grant(task='TASK-003', until=T0 + datetime.timedelta(minutes=5))
        self.grant(task='TASK-004')
        self.refused(self.add(['a']), 'leases')
        self.assertEqual(self.add(['a'], now=T0 + datetime.timedelta(minutes=5)).value, 1)
        writer.end_session(self.root, 's-2', T0)
        self.refused(self.add(['a'], sid='s-2'), 'ended')
        self.sql("UPDATE leases SET expires_at = 'soon' WHERE task_id = 'TASK-004'")
        r = self.add(['b'])
        self.assertEqual((r.reason, r.findings), ('unreadable', ('unreadable: ValueError',)))

    def test_a_lease_whose_task_id_is_out_of_form(self):
        """TASK-067 AC2, TASK-067 AC4 and TASK-067 AC9: a lease row whose task_id fails the writer's form (a number, a
        blob) gives "unreadable" with the fixed finding, while session_lease gives "tied"."""
        self.tied()
        for value in ('7', "x'00'", "'task-1'"):
            with self.subTest(value=value):
                self.sql('UPDATE leases SET task_id = %s' % value)
                r = self.add(['a'])
                self.assertEqual((r.reason, r.findings),
                                 ('unreadable', ("unreadable: the lease's task id is not in the writer's form",)))
                self.assertEqual(writer.session_lease(self.root, 's-1', T0).reason, 'tied')
        self.assertEqual(self.rows(), [])

    def test_a_malformed_stored_seq(self):
        """TASK-067 AC2 and TASK-067 AC9: a stored seq that is not a number (a test connection, on a table without the
        constraints) gives "unreadable" and stores nothing."""
        self.tied()
        self.sql('DROP TABLE reads', 'CREATE TABLE reads (session_id, task_id, seq, path)',
                 "INSERT INTO reads VALUES ('s-1', 'TASK-067', 'x', 'a')")
        r = self.add(['b'])
        self.assertEqual((r.reason, r.findings), ('unreadable', ('unreadable: TypeError',)))
        self.assertEqual(len(self.rows()), 1)

    def test_a_held_write_lock_and_the_timeout(self):
        """TASK-067 AC2 and TASK-067 AC9: while another connection holds BEGIN IMMEDIATE, add_reads with a timeout of
        about 0.2 gives "unreadable"; the timeout is passed to connect (a recording stand-in)."""
        from unittest import mock
        self.tied()
        con = sqlite3.connect(writer.store_path(self.root), isolation_level=None)
        try:
            con.execute('BEGIN IMMEDIATE')
            self.refused(self.add(['a'], timeout=0.2), 'unreadable')
        finally:
            con.close()
        seen = []
        real = sqlite3.connect

        def recording(*a, **k):
            seen.append(k.get('timeout'))
            return real(*a, **k)
        with mock.patch.object(writer.sqlite3, 'connect', recording):
            self.assertEqual(self.add(['a'], timeout=7).value, 1)
        self.assertEqual(seen, [7])

    def test_a_garbage_and_a_zero_byte_store(self):
        """TASK-067 AC2 and TASK-067 AC9: a 0-byte store file gives "tables" and a garbage file "unreadable", for
        add_reads, stored_reads and remove_reads."""
        from unittest import mock
        with mock.patch.object(writer, '_SCHEMA', ('CREATE TABLE broken (',)):
            with self.assertRaises(sqlite3.Error):
                writer.open_store(self.root, 'epoch-1')
        calls = (lambda: self.add(['a']), lambda: writer.stored_reads(self.root, 's-1', 'TASK-067'),
                 lambda: writer.remove_reads(self.root, 's-1', 'TASK-067'))
        for call in calls:
            self.refused(call(), 'tables')
        with open(writer.store_path(self.root), 'ab') as f:
            f.write(b'made-up bytes, not a store. ' * 5)
        for call in calls:
            self.refused(call(), 'unreadable')


class R17StoredAndRemoved(ReadsCase):
    """TASK-067's rule R3: stored_reads and remove_reads, and the presence step of the four functions."""

    def test_order_count_and_scope(self):
        """TASK-067 AC3 and TASK-067 AC9: stored_reads gives the paths in seq order (empty when none) and changes no
        byte; remove_reads removes only that session's and task's rows and gives the DELETE's count."""
        self.tied()
        self.add(['b', 'a'])
        self.sql("INSERT INTO reads VALUES ('s-2', 'TASK-067', 0, 'x')", "INSERT INTO reads VALUES ('s-1', 'TASK-1', 0, 'y')")
        before = read(writer.store_path(self.root))
        self.assertEqual(writer.stored_reads(self.root, 's-1', 'TASK-067').value, ['b', 'a'])
        self.assertEqual(writer.stored_reads(self.root, 's-9', 'TASK-067').value, [])
        self.assertEqual(read(writer.store_path(self.root)), before)
        r = writer.remove_reads(self.root, 's-1', 'TASK-067')
        self.assertEqual((r.result, r.value), ('done', 2))
        self.assertEqual(sorted(x[:2] for x in self.rows()), [('s-1', 'TASK-1'), ('s-2', 'TASK-067')])
        self.assertEqual(writer.remove_reads(self.root, 's-1', 'TASK-067').value, 0)

    def test_a_seq_tie_is_ordered_by_rowid(self):
        """TASK-067 AC3 and TASK-067 AC9: on a reads table without the constraints, two rows with one seq come back in
        rowid order."""
        self.tied()
        self.sql('DROP TABLE reads', 'CREATE TABLE reads (session_id, task_id, seq, path)',
                 "INSERT INTO reads VALUES ('s-1', 'TASK-067', 1, 'b')", "INSERT INTO reads VALUES ('s-1', 'TASK-067', 1, 'a')",
                 "INSERT INTO reads VALUES ('s-1', 'TASK-067', 0, 'c')")
        self.assertEqual(writer.stored_reads(self.root, 's-1', 'TASK-067').value, ['c', 'b', 'a'])

    def test_a_stored_path_that_is_not_text(self):
        """TASK-067 AC3 and TASK-067 AC9: a stored path that is not a str gives "unreadable" with the fixed finding."""
        self.tied()
        self.sql('DROP TABLE reads', 'CREATE TABLE reads (session_id, task_id, seq, path)',
                 "INSERT INTO reads VALUES ('s-1', 'TASK-067', 0, 7)")
        r = writer.stored_reads(self.root, 's-1', 'TASK-067')
        self.assertEqual((r.reason, r.findings), ('unreadable', ('unreadable: a stored path is not text',)))

    def test_no_lease_is_checked(self):
        """TASK-067 AC3 and TASK-067 AC9 (D-1395 M2): both work for a session with no lease, an expired lease, an ended
        session and an unknown session id."""
        self.tied(until=T0 + datetime.timedelta(minutes=5))
        self.add(['a'])
        self.sql("INSERT INTO reads VALUES ('s-9', 'TASK-067', 0, 'z')")
        writer.expire_leases(self.root, T0 + H1)
        self.assertEqual(writer.stored_reads(self.root, 's-1', 'TASK-067').value, ['a'])
        writer.end_session(self.root, 's-1', T0 + H1)
        self.assertEqual(writer.stored_reads(self.root, 's-1', 'TASK-067').value, ['a'])
        self.assertEqual(writer.stored_reads(self.root, 's-9', 'TASK-067').value, ['z'])
        self.assertEqual(writer.remove_reads(self.root, 's-1', 'TASK-067').value, 1)
        self.assertEqual(writer.remove_reads(self.root, 's-9', 'TASK-067').value, 1)

    def test_each_bad_argument_and_root(self):
        """TASK-067 AC3 and TASK-067 AC9: bad session ids, task ids and timeouts give "argument", a bad root "root"."""

        class S(str):
            pass
        self.tied()
        missing = os.path.join(self.root, 'absent')
        for fn in (writer.stored_reads, writer.remove_reads):
            for sid, task, timeout in (('', 'TASK-067', 5), (S('s-1'), 'TASK-067', 5), ('s-1', 'task-1', 5), ('s-1', S('TASK-067'), 5),
                                       ('s-1', None, 5), ('s-1', 'TASK-067', 0), ('s-1', 'TASK-067', True)):
                with self.subTest(fn=fn, sid=sid, task=task, timeout=timeout):
                    self.refused(fn(missing, sid, task, timeout), 'argument')
            for bad in (missing, 'relative', '', None, writer.store_path(self.root)):
                with self.subTest(fn=fn, bad=bad):
                    self.refused(fn(bad, 's-1', 'TASK-067'), 'root')

    def test_the_read_helper_fails_closed(self):
        """TASK-067 AC3 and TASK-067 AC9: stored_reads gives "unreadable" when ROLLBACK or close fails (a connect
        stand-in), and a failed BEGIN DEFERRED skips ROLLBACK; the timeout is passed to connect (a recording
        stand-in)."""
        from unittest import mock
        self.tied()
        real = sqlite3.connect

        class Wrap:
            def __init__(self, con, fail):
                self.con, self.fail, self.ran = con, fail, []

            @property
            def in_transaction(self):
                return self.con.in_transaction

            def execute(self, s, *a):
                self.ran.append(s)
                if s == self.fail:
                    raise sqlite3.OperationalError('made-up')
                return self.con.execute(s, *a)

            def close(self):
                self.con.close()
                if self.fail == 'close':
                    raise sqlite3.OperationalError('made-up')
        for fail in ('ROLLBACK', 'close', 'BEGIN DEFERRED'):
            made = []

            def connect(*a, **k):
                made.append(Wrap(real(*a, **k), fail))
                return made[-1]
            with self.subTest(fail=fail):
                with mock.patch.object(writer.sqlite3, 'connect', connect):
                    r = writer.stored_reads(self.root, 's-1', 'TASK-067')
                self.assertEqual((r.result, r.reason), ('refused', 'unreadable'))
                if fail == 'BEGIN DEFERRED':
                    self.assertNotIn('ROLLBACK', made[0].ran)
        seen = []

        def recording(*a, **k):
            seen.append(k.get('timeout'))
            return real(*a, **k)
        with mock.patch.object(writer.sqlite3, 'connect', recording):
            self.assertEqual(writer.stored_reads(self.root, 's-1', 'TASK-067', timeout=7).result, 'done')
        self.assertEqual(seen, [7])

    def test_the_presence_step_of_the_four_functions(self):
        """TASK-067 AC3 and TASK-067 AC9: through the stand-ins of R13's form, each of the four functions gives
        "no_store", "unreadable" (an lstat OSError, a ValueError) and "link" (a directory, a raising realpath, a
        realpath elsewhere), each with the same reason and finding as session_lease."""
        import types
        from unittest import mock
        self.tied()
        path = writer.store_path(self.root)
        rroot = os.path.realpath(self.root)
        calls = {'add_reads': lambda: self.add(['a']), 'stored_reads': lambda: writer.stored_reads(self.root, 's-1', 'TASK-067'),
                 'remove_reads': lambda: writer.remove_reads(self.root, 's-1', 'TASK-067'),
                 'migrate_store': lambda: writer.migrate_store(self.root),
                 'session_lease': lambda: writer.session_lease(self.root, 's-1', T0)}
        lstat, realpath = writer.os.lstat, writer.os.path.realpath

        def with_lstat(effect):
            def fake(p, *a, **k):
                if p == path:
                    if isinstance(effect, BaseException):
                        raise effect
                    return types.SimpleNamespace(st_mode=effect)
                return lstat(p, *a, **k)
            return mock.patch.object(writer.os, 'lstat', fake)

        def with_realpath(effect):
            def fake(p, *a, **k):
                if p == path:
                    if isinstance(effect, BaseException):
                        raise effect
                    return effect
                return realpath(p, *a, **k)
            return mock.patch.object(writer.os.path, 'realpath', fake)
        stands = [(with_lstat(FileNotFoundError('x')), 'no_store'), (with_lstat(PermissionError('x')), 'unreadable'),
                  (with_lstat(ValueError('x')), 'unreadable'), (with_lstat(0o040755), 'link'),
                  (with_realpath(RuntimeError('x')), 'link'),
                  (with_realpath(os.path.join(rroot, '.aieos', 'local', 'other.sqlite')), 'link')]
        for patcher, reason in stands:
            got = {}
            for name, call in calls.items():
                with patcher:
                    got[name] = call()
            with self.subTest(reason=reason):
                for name, r in got.items():
                    self.assertEqual((name, r.result, r.reason, r.findings),
                                     (name, 'refused', reason, got['session_lease'].findings))


class R18TheSharedRule(ReadsCase):
    """TASK-067's rule R4: the live-lease helper through both callers, and session_lease's exact findings."""

    def test_session_lease_findings_are_unchanged(self):
        """TASK-067 AC4 and TASK-067 AC9 (D-1395 M3): session_lease's exact finding for each refusal reason with fixed
        text, the strings copied by hand from the base text of writer.py, never imported."""
        self.store()
        self.session()
        self.assertEqual(writer.session_lease(self.root, 's-1', T0).findings,
                         ('no_lease_row: the store holds no lease row',))
        self.session('s-2', 'agent-2')
        self.grant(task='TASK-002', holder='agent-2', sid='s-2')
        self.assertEqual(writer.session_lease(self.root, None, T0).findings,
                         ('lease_row_without_session: the store holds a lease row',))
        self.assertEqual(writer.session_lease(self.root, 's-9', T0).findings, ('session: no session with this id',))
        self.assertEqual(writer.session_lease(self.root, 's-1', T0).findings,
                         ('leases: not exactly one unexpired lease of the session (0)',))
        writer.end_session(self.root, 's-1', T0)
        self.assertEqual(writer.session_lease(self.root, 's-1', T0).findings, ('ended: the session is ended',))
        self.sql("UPDATE leases SET expires_at = 'soon'")
        self.assertEqual(writer.session_lease(self.root, 's-2', T0).findings, ('unreadable: ValueError',))

    def test_both_callers_agree(self):
        """TASK-067 AC4 and TASK-067 AC9: over the helper's cases, in order, session_lease and add_reads give the same
        reason and finding, an unknown session on a store with no lease row among them; "tied" exactly when add_reads
        accepts."""
        self.store()
        self.session()
        self.session('s-2', 'agent-2')

        def both(sid, now=T0):
            a = writer.session_lease(self.root, sid, now)
            b = self.add(['p'], sid=sid, now=now)
            return a, b
        a, b = both('s-9')
        self.assertEqual((a.reason, a.findings), (b.reason, b.findings))
        self.assertEqual(a.reason, 'no_lease_row')
        self.grant(task='TASK-002', holder='agent-2', sid='s-2', until=T0 + datetime.timedelta(minutes=5))
        for sid, now in (('s-9', T0), ('s-1', T0), ('s-2', T0 + datetime.timedelta(minutes=5))):
            a, b = both(sid, now)
            with self.subTest(sid=sid, now=now):
                self.assertEqual((a.reason, a.findings), (b.reason, b.findings))
        a, b = both('s-2')
        self.assertEqual((a.reason, b.result), ('tied', 'done'))
        self.grant(task='TASK-003')
        writer.end_session(self.root, 's-2', T0)
        a, b = both('s-2')
        self.assertEqual((a.reason, a.findings), (b.reason, b.findings))
        self.assertEqual(a.reason, 'ended')


class R19MigrateAndTheWriteHelper(ReadsCase):
    """TASK-067's rule R5: migrate_store's table of outcomes, the write helper's ending, the "?mode=rw" reading and
    the catch-all."""

    def three_tables(self, rows=1):
        self.tied()
        self.sql('DROP TABLE reads')
        if rows != 1:
            self.sql("INSERT INTO store (epoch, counter) VALUES ('x', 0)")

    def test_migrated_and_current(self):
        """TASK-067 AC5 and TASK-067 AC9: a three-table store is "migrated", the other rows unchanged by a dump, and
        then every writer function reads it as a four-table store; a four-table store is "current", bytes unchanged."""
        self.three_tables()
        self.add(['ignored'])
        before = self.dump()
        r = writer.migrate_store(self.root)
        self.assertEqual((r.result, r.value), ('done', 'migrated'))
        after = self.dump()
        self.assertEqual(after.pop('reads'), [])
        self.assertEqual(after, before)
        self.assertEqual(writer.held_lease(self.root, 'TASK-067')['task_id'], 'TASK-067')
        self.assertEqual(self.add(['a']).value, 1)
        self.assertEqual(writer.session_lease(self.root, 's-1', T0).reason, 'tied')
        data = read(writer.store_path(self.root))
        self.assertEqual(writer.migrate_store(self.root).value, 'current')
        self.assertEqual(read(writer.store_path(self.root)), data)

    def test_other_forms_give_tables(self):
        """TASK-067 AC5 and TASK-067 AC9: a leftover reads table of other columns, an extra table, a missing table and
        two store rows give "tables", the store unchanged; a pre-task form with two store rows runs the CREATE and is
        refused at the second check, rolled back."""
        for setup in (lambda: self.sql('DROP TABLE reads', 'CREATE TABLE reads (x)'),
                      lambda: self.sql('CREATE TABLE extra (x)'), lambda: self.sql('DROP TABLE reads', 'DROP TABLE sessions'),
                      lambda: self.sql("INSERT INTO store (epoch, counter) VALUES ('x', 0)"),
                      lambda: self.sql('DROP TABLE reads', "INSERT INTO store (epoch, counter) VALUES ('x', 0)")):
            with self.subTest(setup=setup):
                self.tearDown()
                self.setUp()
                self.tied()
                setup()
                before = self.dump()
                self.refused(writer.migrate_store(self.root), 'tables')
                self.assertEqual(self.dump(), before)

    def test_arguments_root_store_link_and_lock(self):
        """TASK-067 AC5 and TASK-067 AC9: its "argument", "root", "no_store" (nothing created), "link" and held-lock
        "unreadable" cases."""
        import types
        from unittest import mock
        for bad in (0, 61, True, 'x', None):
            self.refused(writer.migrate_store(self.root, bad), 'argument')
        self.refused(writer.migrate_store(os.path.join(self.root, 'absent')), 'root')
        self.refused(writer.migrate_store(self.root), 'no_store')
        self.assertEqual(files_under(self.root), [])
        self.three_tables()
        with mock.patch.object(writer.os, 'lstat', lambda p, *a, **k: types.SimpleNamespace(st_mode=0o040755)):
            self.refused(writer.migrate_store(self.root), 'link')
        con = sqlite3.connect(writer.store_path(self.root), isolation_level=None)
        try:
            con.execute('BEGIN IMMEDIATE')
            self.refused(writer.migrate_store(self.root, 0.2), 'unreadable')
        finally:
            con.close()
        self.assertNotIn('reads', self.dump())

    def test_every_cell_of_the_table(self):
        """TASK-067 AC5 and TASK-067 AC9 (D-1395 M5): the probe's and the second check's ValueError and sqlite3.Error
        by a stand-in for _check_schema keyed on its call count, and the CREATE's sqlite3.Error and another exception
        by a connect stand-in whose execute raises for the CREATE TABLE reads text; the store unchanged after each
        refusal."""
        from unittest import mock
        real_check, real_connect = writer._check_schema, sqlite3.connect

        def keyed(effects):
            calls = []

            def check(con):
                calls.append(1)
                e = effects.get(len(calls))
                if e is not None:
                    raise e
                return real_check(con)
            return check
        cells = [({1: sqlite3.OperationalError('x')}, 'unreadable'), ({2: ValueError('x')}, 'tables'),
                 ({2: sqlite3.OperationalError('x')}, 'unreadable')]
        for effects, reason in cells:
            with self.subTest(effects=effects):
                self.tearDown()
                self.setUp()
                self.three_tables()
                before = self.dump()
                with mock.patch.object(writer, '_check_schema', keyed(effects)):
                    self.refused(writer.migrate_store(self.root), reason)
                self.assertEqual(self.dump(), before)

        class Wrap:
            def __init__(self, con, error):
                self.con, self.error = con, error

            @property
            def in_transaction(self):
                return self.con.in_transaction

            def execute(self, s, *a):
                if s.startswith('CREATE TABLE reads'):
                    raise self.error
                return self.con.execute(s, *a)

            def close(self):
                self.con.close()
        for error, finding in ((sqlite3.OperationalError('x'), 'unreadable: OperationalError'),
                               (RuntimeError('x'), 'unreadable: RuntimeError')):
            with self.subTest(error=error):
                self.tearDown()
                self.setUp()
                self.three_tables()
                before = self.dump()
                with mock.patch.object(writer.sqlite3, 'connect', lambda *a, **k: Wrap(real_connect(*a, **k), error)):
                    r = writer.migrate_store(self.root)
                self.assertEqual((r.reason, r.findings), ('unreadable', (finding,)))
                self.assertEqual(self.dump(), before)

    def test_the_write_helpers_ending(self):
        """TASK-067 AC9 (D-1393 K1): normal calls return "done" with their change; a refusal from the work leaves the
        store unchanged; a failing close after a successful COMMIT still gives "done"; a failing COMMIT and a work
        result that is not a StoreResult give "unreadable" with the store unchanged; a failing ROLLBACK after a refusal
        from the work gives "unreadable" from the write helper itself, no exception escaping it."""
        from unittest import mock
        self.tied()
        self.assertEqual(self.add(['a']).value, 1)
        self.assertEqual(writer.remove_reads(self.root, 's-1', 'TASK-067').value, 1)
        real = sqlite3.connect

        class Wrap:
            def __init__(self, con, fail):
                self.con, self.fail = con, fail

            @property
            def in_transaction(self):
                return self.con.in_transaction

            def execute(self, s, *a):
                if s == self.fail:
                    raise sqlite3.OperationalError('made-up')
                return self.con.execute(s, *a)

            def close(self):
                self.con.close()
                if self.fail == 'close':
                    raise sqlite3.OperationalError('made-up')
        with mock.patch.object(writer.sqlite3, 'connect', lambda *a, **k: Wrap(real(*a, **k), 'close')):
            self.assertEqual(self.add(['b']).value, 1)
        self.assertEqual(writer.stored_reads(self.root, 's-1', 'TASK-067').value, ['b'])
        before = self.dump()
        with mock.patch.object(writer.sqlite3, 'connect', lambda *a, **k: Wrap(real(*a, **k), 'COMMIT')):
            self.refused(self.add(['c']), 'unreadable')
        self.assertEqual(self.dump(), before)
        self.refused(self.add(['c'], sid='s-9'), 'session')
        self.assertEqual(self.dump(), before)
        real_store = writer._store_present(self.root)[1]
        r = writer._write_store(real_store, 5.0, lambda con: (con.execute(
            "INSERT INTO reads VALUES ('s-1', 'TASK-067', 9, 'z')"), None)[1])
        self.assertEqual(r.reason, 'unreadable')
        self.assertEqual(self.dump(), before)
        with mock.patch.object(writer.sqlite3, 'connect', lambda *a, **k: Wrap(real(*a, **k), 'ROLLBACK')):
            r = writer._write_store(real_store, 5.0, lambda con: writer._refused('session', 'session: made-up'))
        self.assertEqual((r.result, r.reason, r.findings), ('refused', 'unreadable', ('unreadable: OperationalError',)))
        self.assertEqual(self.dump(), before)

    def test_the_rw_open_never_creates_a_store(self):
        """TASK-067 AC9 (D-1393 K7, C1 (d)): a stand-in for _store_present returns a missing file in an existing folder;
        a connect recorder shows the open was reached with a URI ending "?mode=rw"; the three write functions give
        "unreadable" and no file is created; the suffix change touches only the final suffix."""
        from unittest import mock
        self.tied()
        missing = os.path.join(self.root, 'made-up.sqlite')
        before = files_under(self.root)
        seen = []
        real = sqlite3.connect

        def recording(target, *a, **k):
            seen.append(target)
            return real(target, *a, **k)
        calls = (lambda: self.add(['a']), lambda: writer.remove_reads(self.root, 's-1', 'TASK-067'),
                 lambda: writer.migrate_store(self.root))
        for call in calls:
            with mock.patch.object(writer, '_store_present', lambda root: (None, missing)), \
                    mock.patch.object(writer.sqlite3, 'connect', recording):
                self.refused(call(), 'unreadable')
        self.assertEqual(len(seen), 3)
        self.assertTrue(all(u.endswith('made-up.sqlite?mode=rw') for u in seen), seen)
        self.assertEqual(files_under(self.root), before)
        seen.clear()
        odd = os.path.join(self.root, 'a?mode=ro')
        with mock.patch.object(writer, '_store_present', lambda root: (None, odd)), \
                mock.patch.object(writer.sqlite3, 'connect', recording):
            self.add(['a'])
        self.assertTrue(seen[0].endswith('a%3Fmode%3Dro?mode=rw'), seen)

    def test_the_catch_all(self):
        """TASK-067 AC9 (D-1395 M1, C1 (b); D-1397 C1): a UNC-form path and a path not encodable as UTF-8 from a
        _store_present stand-in reach _store_uri (a recorder) and give, for all four functions, "unreadable:
        ValueError" (the UNC path) and "unreadable: UnicodeEncodeError" (the path not encodable as UTF-8; a subclass
        of ValueError; D-1421 E1); a URI without the "?mode=ro" suffix gives "unreadable" for the three write functions; a stand-in
        for a named helper raising RuntimeError gives "unreadable: RuntimeError", the store unchanged."""
        from unittest import mock
        self.tied()
        before = self.dump()
        calls = {'add_reads': lambda: self.add(['a']), 'stored_reads': lambda: writer.stored_reads(self.root, 's-1', 'TASK-067'),
                 'remove_reads': lambda: writer.remove_reads(self.root, 's-1', 'TASK-067'),
                 'migrate_store': lambda: writer.migrate_store(self.root)}
        real_uri = writer._store_uri
        # The surrogate case raises UnicodeEncodeError, a subclass of ValueError, inside _store_uri; the finding names
        # the exception's own type, under the contract's type rule (D-1421 E1; AC9's text says "unreadable: ValueError").
        self.assertTrue(issubclass(UnicodeEncodeError, ValueError))
        for odd, kind in (('//server/share/state.sqlite', 'ValueError'),
                          (os.path.join(self.root, 'x\udcff'), 'UnicodeEncodeError')):
            for name, call in calls.items():
                reached = []

                def uri(*a):
                    reached.append(a)
                    return real_uri(*a)
                with self.subTest(odd=odd, name=name):
                    with mock.patch.object(writer, '_store_present', lambda root: (None, odd)), \
                            mock.patch.object(writer, '_store_uri', uri):
                        r = call()
                    self.assertEqual((r.reason, r.findings), ('unreadable', ('unreadable: ' + kind,)))
                    self.assertEqual(len(reached), 1)
        for name in ('add_reads', 'remove_reads', 'migrate_store'):
            with self.subTest(name=name):
                with mock.patch.object(writer, '_store_uri', lambda *a: 'file:///x'):
                    self.refused(calls[name](), 'unreadable')

        def boom(*a, **k):
            raise RuntimeError('made-up')
        helpers = {'add_reads': ('_store_present', '_write_store'), 'remove_reads': ('_store_present', '_write_store'),
                   'migrate_store': ('_store_present', '_write_store'), 'stored_reads': ('_store_present', '_read_reads')}
        for name, names in helpers.items():
            for helper in names:
                with self.subTest(name=name, helper=helper):
                    with mock.patch.object(writer, helper, boom):
                        r = calls[name]()
                    self.assertEqual((r.reason, r.findings), ('unreadable', ('unreadable: RuntimeError',)))
                    self.assertEqual(self.dump(), before)

    def test_no_finding_holds_the_callers_text(self):
        """TASK-067 AC9 (D-1393 K3): for every refusal reason of the four functions, with a made-up hostile session
        id, task id, root and path, none of their text appears in the finding."""
        from unittest import mock
        hostile = 'zz-HOSTILE-zz'
        root = os.path.join(self.root, hostile)
        self.store()
        self.session(hostile)
        out = [self.add(['a'], sid=hostile), self.add([hostile + '\x00']), self.add(['a'], sid=hostile, root=root),
               writer.stored_reads(root, hostile, 'TASK-1'), writer.remove_reads(root, hostile, 'TASK-1'),
               writer.stored_reads(self.root, hostile, hostile), writer.migrate_store(root),
               self.add(['a'] * 10001, sid=hostile)]
        with mock.patch.object(writer, '_store_present', lambda r: (None, '//' + hostile)):
            out += [self.add(['a'], sid=hostile), writer.stored_reads(self.root, hostile, 'TASK-1')]
        for r in out:
            with self.subTest(r=r):
                self.assertEqual(r.result, 'refused')
                self.assertNotIn(hostile, ' '.join(r.findings))


class R20TheQueries(unittest.TestCase):
    """TASK-067's rule R6: every execute call of writer.py takes a constant query."""

    @staticmethod
    def bad_queries(source):
        """The line numbers of execute calls whose query is not a str constant (implicit concatenation included), a
        module-level name bound to a str constant, or a name bound by a for loop over _SCHEMA."""
        tree = ast.parse(source)
        consts = {t.id for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                  and isinstance(n.value.value, str) for t in n.targets if isinstance(t, ast.Name)}
        loops = {n.target.id for n in ast.walk(tree) if isinstance(n, ast.For) and isinstance(n.target, ast.Name)
                 and isinstance(n.iter, ast.Name) and n.iter.id == '_SCHEMA'}
        bad = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ('execute', 'executemany'):
                q = n.args[0] if n.args else None
                ok = (isinstance(q, ast.Constant) and isinstance(q.value, str)) or (
                    isinstance(q, ast.Name) and (q.id in consts or q.id in loops))
                if not ok:
                    bad.append(n.lineno)
        return bad

    def test_every_query_is_a_constant(self):
        """TASK-067 AC6 and TASK-067 AC9: no execute call of writer.py builds its query; the check finds each of an
        f-string, "%", "+", a call and a subscript in a hostile sample."""
        self.assertEqual(self.bad_queries(read(os.path.join(SRC, 'writer.py')).decode('utf-8')), [])
        sample = ("Q = 'SELECT 1'\nN = 1\ncon.execute(Q)\ncon.execute('SELECT ' 'x')\ncon.execute(f'SELECT {x}')\n"
                  "con.execute('SELECT %s' % x)\ncon.execute('SELECT ' + x)\ncon.execute(q())\ncon.execute(A[0])\n"
                  "con.execute(N)\n")
        self.assertEqual(self.bad_queries(sample), [5, 6, 7, 8, 9, 10])

    def test_the_lookup_test_still_passes_with_the_new_code_above_the_marker(self):
        """TASK-067 AC9: every new definition stands above the marker of TASK-066's lookup, whose text keeps no
        INSERT, UPDATE, DELETE or PRAGMA and two "finally:"."""
        text = read(os.path.join(SRC, 'writer.py')).decode('utf-8')
        head, part = text.split('# ---- the read-only lookup of the store (task TASK-066) ----', 1)
        for name in ('def add_reads(', 'def stored_reads(', 'def remove_reads(', 'def migrate_store(',
                     'def _live_lease(', 'def _store_present(', 'def _write_store(', 'def _read_reads('):
            with self.subTest(name=name):
                self.assertIn(name, head)
                self.assertNotIn(name, part)
        for word in ('INSERT', 'UPDATE', 'DELETE', 'PRAGMA'):
            self.assertNotIn(word, part)
        self.assertEqual(part.count('finally:'), 2)


if __name__ == '__main__':
    unittest.main()
