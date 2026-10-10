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


if __name__ == '__main__':
    unittest.main()
