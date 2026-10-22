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


SV_TASK = 'TASK-070'
SV_EPOCH = 'epoch-of-the-tied-store-69'
SV_EV = 'ev-violation-1'
SV_HIDDEN = 'release: the lease is held with another token (not shown)'


def sv_observation(subject=SV_TASK):
    return {'record_id': 'obs-1', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
            'recorder': REC, 'subject': subject, 'evidence_type': 'write_outside_write_set', 'outcome': 'blocking',
            'blocking_kind': 'violation', 'refers_to': 'src/outside.py'}


def sv_store(root):
    """A store with session s-1 holding one unexpired lease on SV_TASK; returns the lease."""
    writer.open_store(root, SV_EPOCH)
    writer.start_session(root, 's-1', 'agent-1', T0)
    return writer.grant_lease(root, SV_TASK, 'READY', 'agent-1', 's-1', T0, T0 + datetime.timedelta(hours=1)).value


def sv_events(root):
    """The log's events, after checking that records.check_log gives no finding."""
    path = writer.log_path(root)
    if not os.path.isfile(path):
        return []
    log = records.check_log(read(path))
    assert log.findings() == [], log.findings()
    return [x.event for x in log.lines]


def sv_holds_token(value, epochs):
    if isinstance(value, dict):
        if 'epoch' in value and 'counter' in value:
            return True
        return any(sv_holds_token(k, epochs) or sv_holds_token(v, epochs) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(sv_holds_token(v, epochs) for v in value)
    if isinstance(value, str):
        return ('epoch' in value and 'counter' in value) or any(e in value for e in epochs)
    return False


def sv_files(root):
    return sorted(os.path.relpath(os.path.join(h, n), root).replace(os.sep, '/') for h, _, ns in os.walk(root)
                  for n in ns)


class SessionViolationFiles(unittest.TestCase):
    """TASK-070's rule R4 on real files: the violation path tied by the live lease, end to end."""

    NOW = T0 + datetime.timedelta(minutes=1)

    def call(self, root, sid='s-1', subject=SV_TASK, now=None, **kw):
        from aieos_bootstrap import session_violation
        return session_violation.session_violation(root, sid, sv_observation(subject), SV_EV, REC, now or self.NOW, **kw)

    def test_the_tied_call_and_its_repeat(self):
        """TASK-070 AC4: the tied call gives "done" and 'STOP: violation'; the log ends with violation.detected and
        decision.execution under the lease's task and token; no lease is held; the result holds no token; the same call
        again gives "lease" with "no_lease_row:" and leaves the log unchanged."""
        with tempfile.TemporaryDirectory() as root:
            lease = sv_store(root)
            r = self.call(root)
            self.assertEqual((r['result'], r['decision']), ('done', 'STOP: violation'))
            self.assertEqual(r['released'], {'task_id': SV_TASK, 'expires_at': lease['expires_at']})
            events = sv_events(root)
            self.assertEqual([e['type'] for e in events], ['violation.detected', 'decision.execution'])
            for e in events:
                self.assertEqual((e['task_id'], e['fencing_token']), (SV_TASK, lease['fencing_token']))
            self.assertEqual((events[1]['payload']['decision'], events[1]['payload']['refers_to']),
                             ('STOP: violation', SV_EV))
            self.assertEqual(writer.held_leases(root), [])
            self.assertFalse(sv_holds_token(r, (SV_EPOCH,)))
            log = read(writer.log_path(root))
            again = self.call(root)
            self.assertEqual((again['result'], again['reason']), ('refused', 'lease'))
            self.assertTrue(again['findings'][0].startswith('no_lease_row:'), again['findings'])
            self.assertEqual(read(writer.log_path(root)), log)
            self.assertEqual(sv_files(root), ['.aieos/events.jsonl', '.aieos/local/state.sqlite'])

    def test_the_lookups_refusals(self):
        """TASK-070 AC4: a now at or after expires_at gives "leases:"; an ended session s-2 gives "ended:" while s-1
        holds its lease; an unknown session id gives "session:"; each leaves the log empty and the lease kept."""
        with tempfile.TemporaryDirectory() as root:
            lease = sv_store(root)
            writer.start_session(root, 's-2', 'agent-2', T0)
            writer.end_session(root, 's-2', T0)
            for kw, prefix in (({'now': lease['expires_at']}, 'leases:'), ({'sid': 's-2'}, 'ended:'),
                               ({'sid': 's-9'}, 'session:')):
                with self.subTest(case=prefix):
                    r = self.call(root, **kw)
                    self.assertEqual((r['result'], r['reason']), ('refused', 'lease'))
                    self.assertTrue(r['findings'][0].startswith(prefix), r['findings'])
                    self.assertEqual(sv_events(root), [])
                    self.assertEqual(writer.held_leases(root), [lease])

    def test_another_tasks_observation(self):
        """TASK-070 AC4: an observation for another task gives "argument"; the log is unchanged and the lease kept."""
        with tempfile.TemporaryDirectory() as root:
            lease = sv_store(root)
            r = self.call(root, subject='TASK-071')
            self.assertEqual((r['result'], r['reason']), ('refused', 'argument'))
            self.assertEqual(sv_events(root), [])
            self.assertEqual(writer.held_leases(root), [lease])

    def test_the_race_with_a_new_holder(self):
        """TASK-070 AC4: a lookup stand-in giving a lease read before it was released and granted again to s-2 gives
        "core" with core's reason "fence"; one record.added is appended, no violation.detected; the second lease is
        kept."""
        with tempfile.TemporaryDirectory() as root:
            sv_store(root)
            old = writer.session_lease(root, 's-1', self.NOW)
            self.assertEqual(writer.release_lease_token(root, SV_TASK, old.value['fencing_token']).result, 'done')
            writer.start_session(root, 's-2', 'agent-2', T0)
            second = writer.grant_lease(root, SV_TASK, 'READY', 'agent-2', 's-2', T0,
                                        T0 + datetime.timedelta(hours=1)).value
            r = self.call(root, lookup=lambda root_, sid, now: old)
            self.assertEqual((r['result'], r['reason'], r['core']['reason']), ('refused', 'core', 'fence'))
            events = sv_events(root)
            self.assertEqual([e['type'] for e in events], ['record.added'])
            self.assertEqual(events[0]['payload']['evidence_type'], 'refused_submission')
            self.assertEqual(writer.held_leases(root), [second])
            self.assertFalse(sv_holds_token(r, (SV_EPOCH,)))

    def test_the_partial_outcome(self):
        """TASK-070 AC4: an append stand-in that releases the lease after the first append gives "core", decision None;
        the log holds violation.detected and the fence's record.added and no decision.execution."""
        with tempfile.TemporaryDirectory() as root:
            lease = sv_store(root)
            count = []

            def append(*args, **kwargs):
                w = writer.append_event(*args, **kwargs)
                if not count:
                    writer.release_lease_token(root, SV_TASK, lease['fencing_token'])
                count.append(1)
                return w
            r = self.call(root, append=append)
            self.assertEqual((r['result'], r['reason'], r['decision']), ('refused', 'core', None))
            self.assertEqual(r['core']['appended'], [SV_EV])
            self.assertEqual([e['type'] for e in sv_events(root)], ['violation.detected', 'record.added'])
            self.assertEqual(writer.held_leases(root), [])

    def test_the_release_token_race(self):
        """TASK-070 AC4: a release stand-in that releases the lease and grants the task again to s-2 before the release
        gives "done", 'STOP: violation', released None, the second lease kept, and the fixed finding in core's
        findings; the result holds no token."""
        with tempfile.TemporaryDirectory() as root:
            lease = sv_store(root)
            second = []

            def release(root_, task_id, token):
                writer.release_lease_token(root_, task_id, token)
                writer.start_session(root_, 's-2', 'agent-2', T0)
                second.append(writer.grant_lease(root_, task_id, 'READY', 'agent-2', 's-2', T0,
                                                 T0 + datetime.timedelta(hours=1)).value)
                return writer.release_lease_token(root_, task_id, token)
            r = self.call(root, release=release)
            self.assertEqual((r['result'], r['decision'], r['released']), ('done', 'STOP: violation', None))
            self.assertIn(SV_HIDDEN, r['core']['findings'])
            self.assertEqual(writer.held_leases(root), second)
            self.assertNotEqual(second[0]['fencing_token'], lease['fencing_token'])
            self.assertFalse(sv_holds_token(r, (SV_EPOCH,)))
            self.assertEqual([e['type'] for e in sv_events(root)], ['violation.detected', 'decision.execution'])


def pretool_input():
    """The bytes of a PreToolUse input for a Write call, with a made-up path."""
    import json
    return json.dumps({'session_id': 'made-up-input-session', 'tool_name': 'Write', 'tool_use_id': 'toolu_made-up',
                       'tool_input': {'file_path': 'C:\\made-up\\a.py', 'content': 'x'}}).encode('utf-8')


class PretoolHookFiles(unittest.TestCase):
    """TASK-072's step 1 on real files: the tie through real stores made by writer functions, ending before the
    contract is read; nothing is appended or released."""

    def run_hook(self, root, env, folder=None, now=T0, leases=True):
        from aieos_bootstrap import claude_code_pretool_hook as hook
        names = {}
        for name, value in zip((hook.SESSION_VAR, hook.ROOT_VAR), env):
            if value is not None:
                names[name] = value
        names[hook.BASE_VAR] = C40
        before = (writer.held_leases(root) if leases and os.path.isfile(writer.store_path(root)) else None, dump(root),
                  sv_events(root))
        out = hook.run(pretool_input(), names, folder, now)
        after = (writer.held_leases(root) if leases and os.path.isfile(writer.store_path(root)) else None, dump(root),
                 sv_events(root))
        self.assertEqual(after, before)
        return out

    def test_enforce_nothing_on_real_folders(self):
        """TASK-072 AC1: with neither name set, an empty folder with no store upward and a store with no lease row
        each give exit 0, "allow", reason "enforce_nothing"; nothing is appended."""
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(self.run_hook(root, (None, None), folder=root),
                             {'exit_code': 0, 'outcome': 'allow', 'reason': 'enforce_nothing', 'findings': []})
        with tempfile.TemporaryDirectory() as root:
            writer.open_store(root, 'epoch-1')
            self.assertEqual(self.run_hook(root, (None, None), folder=root),
                             {'exit_code': 0, 'outcome': 'allow', 'reason': 'enforce_nothing', 'findings': []})

    def test_each_reachable_store_refusal(self):
        """TASK-072 AC1: each store refusal reachable with a real store (argument, root_without_session,
        session_without_root, root, no_store, session, ended, leases twice, no_lease_row, lease_row_without_session,
        tables, unreadable) gives exit 2, "refuse", reason "store" and that word as the one finding; nothing is
        appended or released. search, link and entry are left to stand-ins (tests here make no folder or link)."""
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
        missing = os.path.join(os.path.abspath(os.sep), 'made-up-missing-root-72')
        cases = [('argument', tied_store, ('s-1', 'made-up-relative-root'), None, T0),
                 ('root_without_session', tied_store, (None, 'R'), None, T0),
                 ('session_without_root', tied_store, ('s-1', None), None, T0),
                 ('root', tied_store, ('s-1', missing), None, T0),
                 ('no_store', lambda r: None, ('s-1', 'R'), None, T0),
                 ('session', other_lease, ('s-9', 'R'), None, T0),
                 ('ended', ended, ('s-1', 'R'), None, T0),
                 ('leases', tied_store, ('s-1', 'R'), None, T0 + datetime.timedelta(hours=2)),
                 ('leases', two_leases, ('s-1', 'R'), None, T0),
                 ('no_lease_row', lambda r: writer.open_store(r, 'epoch-1'), ('s-1', 'R'), None, T0),
                 ('lease_row_without_session', tied_store, (None, None), 'R', T0),
                 ('tables', three_tables, ('s-1', 'R'), None, T0)]
        for reason, setup, env, folder, now in cases:
            with self.subTest(reason=reason, setup=setup):
                with tempfile.TemporaryDirectory() as root:
                    setup(root)
                    out = self.run_hook(root, tuple(root if v == 'R' else v for v in env),
                                        folder=root if folder == 'R' else folder, now=now,
                                        leases=reason != 'tables')
                    self.assertEqual(out, {'exit_code': 2, 'outcome': 'refuse', 'reason': 'store',
                                           'findings': [reason]})

    def test_a_locked_store_is_refused(self):
        """TASK-072 AC1: while another connection holds an exclusive lock the store lookup gives "unreadable" after its
        wait, and run gives reason "store" with that word; nothing is appended or released."""
        import sqlite3
        with tempfile.TemporaryDirectory() as root:
            tied_store(root)
            con = sqlite3.connect(writer.store_path(root), isolation_level=None)
            try:
                con.execute('BEGIN EXCLUSIVE')
                from aieos_bootstrap import claude_code_pretool_hook as hook
                out = hook.run(pretool_input(), {hook.SESSION_VAR: 's-1', hook.ROOT_VAR: root, hook.BASE_VAR: C40},
                               None, T0)
                con.execute('ROLLBACK')
            finally:
                con.close()
            self.assertEqual(out, {'exit_code': 2, 'outcome': 'refuse', 'reason': 'store', 'findings': ['unreadable']})
            self.assertEqual(len(writer.held_leases(root)), 1)
            self.assertEqual(sv_events(root), [])

    def test_a_session_id_out_of_form_on_a_real_tie(self):
        """TASK-072 AC1: a real live tie whose session id is out of form ("a b") gives "store: session id form";
        nothing is appended or released."""
        with tempfile.TemporaryDirectory() as root:
            tied_store(root, sid='a b')
            out = self.run_hook(root, ('a b', root))
            self.assertEqual(out, {'exit_code': 2, 'outcome': 'refuse', 'reason': 'store',
                                   'findings': ['store: session id form']})


if __name__ == '__main__':
    unittest.main()
