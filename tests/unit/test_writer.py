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
        self.sql('CREATE TABLE reads (task_id TEXT)')
        self.refused(self.lookup(), 'tables')
        self.sql('DROP TABLE reads', "INSERT INTO store (epoch, counter) VALUES ('x', 0)")
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
        short = os.path.join(self.root, '.')
        r = self.with_realpath({short: rroot})
        self.assertNotEqual(r.reason, 'link')
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


if __name__ == '__main__':
    unittest.main()
