"""Integration tests of aieos_bootstrap.writer (TASK-016 AC12): a full flow on real files in a temporary folder: a
store, a session, a grant, appends under the lease, a refused submission recorded, recovery's reconcile over the file's
bytes and the store's held leases, and expiry."""

import datetime
import os
import tempfile
import unittest

from aieos_bootstrap import records, recovery, writer

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
H64 = '0123456789abcdef' * 4
C40 = 'fedcba9876543210fedcba9876543210fedcba98'
REC = 'aieos-core'


def read(path):
    with open(path, 'rb') as f:
        return f.read()


class FullFlow(unittest.TestCase):

    def test_a_task_from_grant_to_recovery(self):
        with tempfile.TemporaryDirectory() as root:
            store = writer.open_store(root)
            self.assertEqual(store['counter'], 0)
            self.assertEqual(writer.start_session(root, 's-1', 'agent-1', T0).result, 'done')
            r = writer.append_event(root, 'task.drafted', {'contract_version': 'v1', 'contract_hash': H64}, 'ev-1',
                                    T0, REC, task_id='TASK-016')
            self.assertEqual(r.result, 'appended')
            lease = writer.grant_lease(root, 'TASK-016', 'READY', 'agent-1', 's-1', T0,
                                       T0 + datetime.timedelta(hours=1)).value
            self.assertEqual(lease['fencing_token'], {'epoch': store['epoch'], 'counter': 1})

            # a submission under another token is refused by the fence and recorded once
            wrong = dict(lease['fencing_token'], counter=7)
            refused = writer.append_event(root, 'task.submitted', {'commit': C40, 'compensating': False}, 'ev-bad',
                                          T0 + datetime.timedelta(minutes=1), REC, task_id='TASK-016',
                                          fencing_token=wrong)
            self.assertEqual((refused.reason, refused.refusal.result), ('fence', 'appended'))

            # the submission under the lease is appended
            ok = writer.append_event(root, 'task.submitted', {'commit': C40, 'compensating': False}, 'ev-s',
                                     T0 + datetime.timedelta(minutes=2), REC, task_id='TASK-016',
                                     fencing_token=lease['fencing_token'])
            self.assertEqual((ok.result, ok.seq), ('appended', 3))
            log = read(writer.log_path(root))
            self.assertEqual(records.check_log(log).findings(), [])
            self.assertEqual([x.event['type'] for x in records.check_log(log).lines],
                             ['task.drafted', 'record.added', 'task.submitted'])

            # recovery over the file's bytes and the store's held leases
            message = 'Work\n\nAIEOS-Task: TASK-016\nAIEOS-Fence: %s:1\n' % store['epoch']
            result = recovery.reconcile(log, [{'commit': C40, 'message': message}], writer.held_leases(root),
                                        T0 + datetime.timedelta(minutes=3), REC)
            self.assertEqual(result.expired, ())
            self.assertEqual((result.log, result.events, result.findings), (log, (), ()))
            self.assertEqual(writer.held_leases(root), [lease])
            late = recovery.reconcile(log, [{'commit': C40, 'message': message}], writer.held_leases(root),
                                      T0 + datetime.timedelta(hours=1), REC)
            self.assertEqual(late.expired, (lease,))

            # expiry, then the files are still exactly the two
            gone = writer.expire_leases(root, T0 + datetime.timedelta(hours=1))
            self.assertEqual(gone, [lease])
            self.assertEqual(writer.end_session(root, 's-1', T0 + datetime.timedelta(hours=2)).value, [])
            found = sorted(os.path.relpath(os.path.join(h, n), root).replace(os.sep, '/')
                           for h, _, ns in os.walk(root) for n in ns)
            self.assertEqual(found, ['.aieos/events.jsonl', '.aieos/local/state.sqlite'])
            self.assertEqual(read(writer.log_path(root)), log)


class ReleaseByToken(unittest.TestCase):

    def test_the_old_token_never_releases_a_lease_granted_since(self):
        """TASK-028 AC3 and TASK-028 AC11 (DEF-0053 F3), on real files: a lease expires and is granted again to another
        holder; the first token is refused and the second lease stays; the second token then releases it, and the store
        file is the only file under .aieos/local/."""
        with tempfile.TemporaryDirectory() as root:
            writer.open_store(root)
            for sid, holder in (('s-1', 'agent-1'), ('s-2', 'agent-2')):
                self.assertEqual(writer.start_session(root, sid, holder, T0).result, 'done')
            first = writer.grant_lease(root, 'TASK-028', 'READY', 'agent-1', 's-1', T0,
                                       T0 + datetime.timedelta(minutes=5)).value
            self.assertEqual(writer.expire_leases(root, T0 + datetime.timedelta(minutes=5)), [first])
            later = T0 + datetime.timedelta(minutes=6)
            second = writer.grant_lease(root, 'TASK-028', 'READY', 'agent-2', 's-2', later,
                                        later + datetime.timedelta(hours=1)).value
            r = writer.release_lease_token(root, 'TASK-028', first['fencing_token'])
            self.assertEqual((r.result, r.reason), ('refused', 'token'))
            self.assertEqual(writer.held_lease(root, 'TASK-028'), second)
            r = writer.release_lease_token(root, 'TASK-028', second['fencing_token'])
            self.assertEqual((r.result, r.value), ('done', second))
            self.assertEqual(writer.held_leases(root), [])
            self.assertEqual(sorted(os.listdir(os.path.dirname(writer.store_path(root)))), ['state.sqlite'])


def tied_store(root, sid='s-1'):
    """A store with one session and one unexpired lease of it; returns the lease."""
    writer.open_store(root, 'epoch-1')
    writer.start_session(root, sid, 'agent-1', T0)
    return writer.grant_lease(root, 'TASK-001', 'READY', 'agent-1', sid, T0, T0 + datetime.timedelta(hours=1)).value


def snapshot(root):
    """The store file's bytes and the list of files under the root's project-state directory."""
    files = []
    for here, _, names in os.walk(os.path.join(root, '.aieos')):
        files.extend(os.path.relpath(os.path.join(here, n), root) for n in names)
    path = writer.store_path(root)
    return (read(path) if os.path.isfile(path) else None), sorted(files)


class StoreLookupFiles(unittest.TestCase):
    """TASK-066's rule R2 on real files: read-only, the special-character root, the locks and the hot journal."""

    def test_no_case_changes_the_store_or_its_folder(self):
        """TASK-066 AC3 and TASK-066 AC9: over the cases of AC2 the store file's bytes and the files under the
        project-state directory are the same before and after the lookup; no journal is left."""
        import sqlite3
        steps = [lambda r: None,
                 lambda r: writer.open_store(r, 'epoch-1'),
                 lambda r: writer.start_session(r, 's-1', 'agent-1', T0),
                 lambda r: writer.start_session(r, 's-2', 'agent-2', T0),
                 lambda r: writer.grant_lease(r, 'TASK-001', 'READY', 'agent-1', 's-1', T0, T0 + datetime.timedelta(hours=1)),
                 lambda r: writer.grant_lease(r, 'TASK-002', 'READY', 'agent-1', 's-1', T0,
                                              T0 + datetime.timedelta(minutes=5)),
                 lambda r: writer.end_session(r, 's-2', T0)]
        reasons = set()
        with tempfile.TemporaryDirectory() as root:
            for step in steps:
                step(root)
                for sid in (None, 's-1', 's-2', 's-9'):
                    for now in (T0, T0 + datetime.timedelta(minutes=5), T0 + datetime.timedelta(hours=2)):
                        before = snapshot(root)
                        r = writer.session_lease(root, sid, now)
                        reasons.add(r.reason)
                        self.assertEqual(snapshot(root), before, (sid, now, r))
            con = sqlite3.connect(writer.store_path(root), isolation_level=None)
            try:
                con.execute('CREATE TABLE extra (task_id TEXT)')
            finally:
                con.close()
            before = snapshot(root)
            reasons.add(writer.session_lease(root, 's-1', T0).reason)
            self.assertEqual(snapshot(root), before)
        self.assertEqual(reasons, {'no_store', 'no_lease_row', 'lease_row_without_session', 'session', 'ended',
                                   'leases', 'tied', 'tables'})

    def lookup_in(self, prefix, suffix):
        with tempfile.TemporaryDirectory(prefix=prefix, suffix=suffix) as root:
            lease = tied_store(root)
            before = snapshot(root)
            r = writer.session_lease(root, 's-1', T0)
            self.assertEqual((r.result, r.reason, r.value), ('done', 'tied', lease))
            self.assertEqual(snapshot(root), before)

    def test_a_root_with_special_characters(self):
        """TASK-066 AC3 and TASK-066 AC9: a root whose path holds a space, "#" and "%" is looked up correctly."""
        self.lookup_in('a #%b ', ' c%20')

    @unittest.skipIf(os.sep != '/', 'Windows file names cannot hold "?"')
    def test_a_root_with_a_question_mark(self):
        """TASK-066 AC3 and TASK-066 AC9: where os.sep is "/", a root holding "?" too is looked up correctly."""
        self.lookup_in('a ?#%b ', '?x=1')

    def test_the_locks(self):
        """TASK-066 AC3 and TASK-066 AC9: while another connection holds a write transaction that has not reached its
        commit (BEGIN IMMEDIATE) the lookup still reads; while another holds an exclusive lock (BEGIN EXCLUSIVE) the
        lookup with a short timeout gives "unreadable"."""
        import sqlite3
        with tempfile.TemporaryDirectory() as root:
            lease = tied_store(root)
            con = sqlite3.connect(writer.store_path(root), isolation_level=None)
            try:
                con.execute('BEGIN IMMEDIATE')
                con.execute('UPDATE store SET counter = counter')
                r = writer.session_lease(root, 's-1', T0, 0.2)
                self.assertEqual((r.reason, r.value), ('tied', lease))
                con.execute('ROLLBACK')
                con.execute('BEGIN EXCLUSIVE')
                r = writer.session_lease(root, 's-1', T0, 0.2)
                self.assertEqual((r.result, r.reason, r.findings), ('refused', 'unreadable',
                                                                    ('unreadable: OperationalError',)))
                con.execute('ROLLBACK')
            finally:
                con.close()
            self.assertEqual(writer.session_lease(root, 's-1', T0).reason, 'tied')

    def test_a_hot_journal_is_refused(self):
        """TASK-066 AC3 and TASK-066 AC9 (D-1362 C6): a second store is made by open_store (tests may not make
        folders); on a first store a write transaction is held open after it has written pages (a cache of one page
        makes SQLite spill them, so its journal holds records), and that journal's bytes, read with open "rb", are
        written with open "ab" to the journal path beside the second store; the lookup on the second store then gives
        "unreadable", where it gave "tied" before."""
        import sqlite3
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            tied_store(first)
            lease = tied_store(second)
            self.assertEqual(writer.session_lease(second, 's-1', T0).value, lease)
            con = sqlite3.connect(writer.store_path(first), isolation_level=None)
            try:
                con.execute('PRAGMA cache_size = 1')
                con.execute('BEGIN IMMEDIATE')
                con.execute('UPDATE store SET counter = 7')
                con.execute('CREATE TABLE pad (v TEXT)')
                for _ in range(200):
                    con.execute('INSERT INTO pad VALUES (?)', ('y' * 500,))
                journal = read(writer.store_path(first) + '-journal')
                con.execute('ROLLBACK')
            finally:
                con.close()
            self.assertEqual(journal[:8], b'\xd9\xd5\x05\xf9\x20\xa1\x63\xd7')
            self.assertNotEqual(journal[8:12], b'\x00\x00\x00\x00')
            with open(writer.store_path(second) + '-journal', 'ab') as f:
                f.write(journal)
            r = writer.session_lease(second, 's-1', T0)
            self.assertEqual((r.result, r.reason, r.value), ('refused', 'unreadable', None))

    def test_judge_searches_real_folders(self):
        """TASK-066 AC4, TASK-066 AC5 and TASK-066 AC9: judge with neither value searches up from a real working
        folder, passes over a folder whose project-state directory holds no store file, and judges the outer store:
        "enforce_nothing" with no lease row, "refuse" with one; with both values it gives "tied"."""
        from aieos_bootstrap import claude_code_store
        with tempfile.TemporaryDirectory() as outer:
            writer.open_store(outer, 'epoch-1')
            with tempfile.TemporaryDirectory(dir=outer) as inner:
                writer.append_event(inner, 'task.drafted', {'contract_version': 'v1', 'contract_hash': H64}, 'ev-1',
                                    T0, REC, task_id='TASK-001')
                out = claude_code_store.judge(None, '', inner, T0)
                self.assertEqual((out['outcome'], out['reason'], out['root']),
                                 ('enforce_nothing', 'no_lease_row', outer))
                writer.start_session(outer, 's-1', 'agent-1', T0)
                lease = writer.grant_lease(outer, 'TASK-001', 'READY', 'agent-1', 's-1', T0, T0 + datetime.timedelta(hours=1)).value
                out = claude_code_store.judge(None, None, inner, T0)
                self.assertEqual((out['outcome'], out['reason']), ('refuse', 'lease_row_without_session'))
                out = claude_code_store.judge('s-1', outer, inner, T0)
                self.assertEqual((out['outcome'], out['lease'], out['root']), ('tied', lease, outer))


class ReadsFiles(unittest.TestCase):
    """TASK-067's rule R7 on real files: DEF-0085's writer-side points (AC7 (a) and (b))."""

    def test_a_wal_mode_store(self):
        """TASK-067 AC7 and TASK-067 AC9: a store set to WAL mode by a test connection; session_lease and stored_reads
        each give "unreadable" or the right answer, and the store's bytes are unchanged; whether a file appears beside
        the store is printed as an observation, not asserted (a limit: the disjunction cannot fail for code that always
        refuses)."""
        import sqlite3
        with tempfile.TemporaryDirectory() as root:
            lease = tied_store(root)
            writer.add_reads(root, 's-1', ['a', 'b'], T0)
            con = sqlite3.connect(writer.store_path(root), isolation_level=None)
            try:
                self.assertEqual(con.execute('PRAGMA journal_mode=WAL').fetchone()[0], 'wal')
            finally:
                con.close()
            data, files = snapshot(root)
            r = writer.session_lease(root, 's-1', T0)
            self.assertIn((r.result, r.reason, r.value), (('refused', 'unreadable', None), ('done', 'tied', lease)))
            s = writer.stored_reads(root, 's-1', 'TASK-001')
            self.assertIn((s.result, s.reason, s.value), (('refused', 'unreadable', None), ('done', None, ['a', 'b'])))
            after = snapshot(root)
            self.assertEqual(after[0], data)
            print('\nTASK-067 AC7 (a) observation: lookup %s, stored_reads %s, files before %s, after %s'
                  % (r.reason, s.result, files, after[1]))

    def test_the_read_paths_run_only_deferred_reads(self):
        """TASK-067 AC7 and TASK-067 AC9: by set_trace_callback on the real connection (a stand-in for writer's
        sqlite3.connect for one call), session_lease and stored_reads run only BEGIN DEFERRED, SELECT and ROLLBACK, by
        each statement's leading keyword, case-insensitively; never BEGIN IMMEDIATE; the trace's own comment lines are
        allowed only in the form "-- PRAGMA table_info=" (D-1421 E2)."""
        import sqlite3
        from unittest import mock
        real = sqlite3.connect
        with tempfile.TemporaryDirectory() as root:
            tied_store(root)
            writer.add_reads(root, 's-1', ['a'], T0)
            for call in (lambda: writer.session_lease(root, 's-1', T0),
                         lambda: writer.stored_reads(root, 's-1', 'TASK-001')):
                ran = []

                def traced(*a, **k):
                    con = real(*a, **k)
                    con.set_trace_callback(ran.append)
                    return con
                with mock.patch.object(writer.sqlite3, 'connect', traced):
                    self.assertEqual(call().result, 'done')
                # SQLite's trace also reports "-- PRAGMA table_info=..." comment lines for the table-valued function
                # pragma_table_info that the table check's SELECT reads; exactly that form is allowed, and any other
                # line starting "--" fails (D-1421 E2).
                notes = [s for s in ran if s.lstrip().startswith('--')]
                words = [' '.join(s.split()[:2]).upper() if s.split()[0].upper() == 'BEGIN' else s.split()[0].upper()
                         for s in ran if not s.lstrip().startswith('--')]
                with self.subTest(call=call):
                    for s in notes:
                        self.assertTrue(s.lstrip().startswith('-- PRAGMA table_info='), s)
                    self.assertTrue(words)
                    self.assertLessEqual(set(words), {'BEGIN DEFERRED', 'SELECT', 'ROLLBACK'}, ran)
                    self.assertEqual(words[0], 'BEGIN DEFERRED')


def read_input(path, tool='Read'):
    """The bytes of a PostToolUse input for a tool call, with a made-up path (json escapes a NUL)."""
    import json
    return json.dumps({'session_id': 'made-up-input-session', 'cwd': 'made-up-input-cwd', 'tool_name': tool,
                       'tool_input': {'file_path': path}}).encode('utf-8')


def dump(root):
    """The store's tables, reads included, as SQL text (None when there is no store file)."""
    import sqlite3
    path = writer.store_path(root)
    if not os.path.isfile(path):
        return None
    con = sqlite3.connect(path)
    try:
        return list(con.iterdump())
    finally:
        con.close()


class ReadHookFiles(unittest.TestCase):
    """TASK-068's rule R4 on real files: run end to end over real stores."""

    def hook(self, root, data, env, folder=None, now=T0):
        from aieos_bootstrap import claude_code_read_hook as hook
        names = {}
        if env[0] is not None:
            names[hook.SESSION_VAR] = env[0]
        if env[1] is not None:
            names[hook.ROOT_VAR] = env[1]
        return hook.run(data, names, folder, now)

    def assert_refused(self, out, reason):
        self.assertEqual((out['outcome'], out['reason']), ('skip', 'refuse'))
        self.assertTrue(out['findings'][0].startswith(reason + ':'), out)

    def test_a_read_is_recorded_once(self):
        """TASK-068 AC4 and TASK-068 AC9: a Read input under a live tied lease gives "recorded" and stored_reads
        shows the path; the same call again gives "recorded" and the path is stored once."""
        with tempfile.TemporaryDirectory() as root:
            tied_store(root)
            for _ in range(2):
                out = self.hook(root, read_input('made-up/a.txt'), ('s-1', root))
                self.assertEqual(out, {'exit_code': 0, 'outcome': 'recorded', 'reason': None, 'findings': []})
                self.assertEqual(writer.stored_reads(root, 's-1', 'TASK-001').value, ['made-up/a.txt'])

    def test_nothing_is_stored_without_a_live_tie(self):
        """TASK-068 AC4 and TASK-068 AC9: an expired lease, an ended session, an unknown session id, a session id
        without a root, a root without a session id, a root whose store holds no lease row, a root with no store, two
        unexpired leases of the session and a store of the three-table form each give "skip", "refuse" with judge's
        own reason, and the store's tables are unchanged."""
        import sqlite3

        def other_lease(root):
            tied_store(root)
            writer.start_session(root, 's-2', 'agent-2', T0)
            writer.grant_lease(root, 'TASK-002', 'READY', 'agent-2', 's-2', T0, T0 + datetime.timedelta(hours=1))

        def ended(root):
            other_lease(root)
            writer.end_session(root, 's-1', T0)

        def two_leases(root):
            tied_store(root)
            writer.grant_lease(root, 'TASK-002', 'READY', 'agent-1', 's-1', T0, T0 + datetime.timedelta(hours=1))

        def three_tables(root):
            tied_store(root)
            con = sqlite3.connect(writer.store_path(root), isolation_level=None)
            try:
                con.execute('DROP TABLE reads')
            finally:
                con.close()
        cases = [('leases', tied_store, ('s-1', 'R'), T0 + datetime.timedelta(hours=2)),
                 ('ended', ended, ('s-1', 'R'), T0),
                 ('session', other_lease, ('s-9', 'R'), T0),
                 ('session_without_root', tied_store, ('s-1', None), T0),
                 ('root_without_session', tied_store, (None, 'R'), T0),
                 ('no_lease_row', lambda r: writer.open_store(r, 'epoch-1'), ('s-1', 'R'), T0),
                 ('no_store', lambda r: None, ('s-1', 'R'), T0),
                 ('leases', two_leases, ('s-1', 'R'), T0),
                 ('tables', three_tables, ('s-1', 'R'), T0)]
        for reason, setup, env, now in cases:
            with self.subTest(reason=reason, setup=setup):
                with tempfile.TemporaryDirectory() as root:
                    setup(root)
                    before = dump(root)
                    out = self.hook(root, read_input('made-up/a.txt'), tuple(root if v == 'R' else v for v in env),
                                    now=now)
                    self.assert_refused(out, reason)
                    self.assertEqual(dump(root), before)

    def test_neither_name_set(self):
        """TASK-068 AC4 and TASK-068 AC9: with neither name set and the working folder the store's root, a store with
        no lease row gives "skip", "enforce_nothing", and one with a lease row "skip", "refuse"; nothing is stored."""
        with tempfile.TemporaryDirectory() as root:
            writer.open_store(root, 'epoch-1')
            before = dump(root)
            out = self.hook(root, read_input('made-up/a.txt'), (None, None), folder=root)
            self.assertEqual((out['outcome'], out['reason'], out['findings']), ('skip', 'enforce_nothing', []))
            self.assertEqual(dump(root), before)
        with tempfile.TemporaryDirectory() as root:
            tied_store(root)
            before = dump(root)
            out = self.hook(root, read_input('made-up/a.txt'), (None, None), folder=root)
            self.assert_refused(out, 'lease_row_without_session')
            self.assertEqual(dump(root), before)

    def test_uncovered_and_refused_paths(self):
        """TASK-068 AC4 and TASK-068 AC9: an input for Grep gives "skip", "uncovered"; a file_path holding NUL and one
        of 4097 characters give "lost", reason "path"; nothing is stored."""
        with tempfile.TemporaryDirectory() as root:
            tied_store(root)
            before = dump(root)
            out = self.hook(root, read_input('made-up/a.txt', tool='Grep'), ('s-1', root))
            self.assertEqual((out['outcome'], out['reason'], out['findings']), ('skip', 'uncovered', []))
            for path in ('made-up\x00a', 'x' * 4097):
                with self.subTest(path=len(path)):
                    out = self.hook(root, read_input(path), ('s-1', root))
                    self.assertEqual((out['outcome'], out['reason']), ('lost', 'path'))
                    self.assertTrue(out['findings'][0].startswith('path:'))
            self.assertEqual(dump(root), before)

    def test_a_held_write_lock_loses_the_read(self):
        """TASK-068 AC4 and TASK-068 AC9: while another connection holds BEGIN IMMEDIATE, judge's read-only lookup
        still reads, and add_reads, reached through a stand-in of writer.add_reads that forwards with a timeout of 0.2
        seconds, gives "lost", reason "unreadable"; after the holder's ROLLBACK the store's tables are unchanged."""
        import sqlite3
        from unittest import mock
        real = writer.add_reads
        with tempfile.TemporaryDirectory() as root:
            tied_store(root)
            before = dump(root)
            con = sqlite3.connect(writer.store_path(root), isolation_level=None)
            try:
                con.execute('BEGIN IMMEDIATE')
                con.execute('UPDATE store SET counter = counter')
                with mock.patch.object(writer, 'add_reads', lambda r, s, p, n: real(r, s, p, n, timeout=0.2)):
                    out = self.hook(root, read_input('made-up/a.txt'), ('s-1', root))
                con.execute('ROLLBACK')
            finally:
                con.close()
            self.assertEqual((out['outcome'], out['reason']), ('lost', 'unreadable'))
            self.assertTrue(out['findings'][0].startswith('unreadable:'))
            self.assertEqual(dump(root), before)


if __name__ == '__main__':
    unittest.main()
