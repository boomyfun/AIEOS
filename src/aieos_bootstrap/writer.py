"""The core's single writer of the project-state directory (task TASK-016): specification 1 sections 4, 5.2 and 8,
specification 2 sections 3 and 6.1; constitution INV-004 and INV-009.

This is the only module of the core that opens files in the project-state directory for writing. Under a root folder
the caller gives, it touches exactly two files (AC1):

- ``<root>/.aieos/events.jsonl``, the event log: ``append_event`` reads its bytes, lets ``eventlog.append`` (TASK-007,
  as TASK-015 left it) decide the one line to append, appends exactly that line, flushes and syncs it, and reads the
  file back (AC2); a fence refusal is recorded as its own ``record.added`` event (AC3); ``read_log`` returns the
  log's bytes, or empty bytes when it is absent, and creates nothing (TASK-026);
- ``<root>/.aieos/local/state.sqlite``, the local store of the fence's epoch and counter, the leases, the sessions
  (AC4 to AC7) and, from task TASK-067, the reads kept for a session's observed read-set record, with SQLite's own rollback journal ``state.sqlite-journal`` beside it, which SQLite creates and removes
  during a transaction (the default rollback journal mode; no WAL); ``release_lease_token`` releases a lease only for
  its own fencing token (TASK-028).

Every time is an argument, a timezone-aware datetime in UTC with whole seconds; the clock is read nowhere. The store's
times are ISO 8601 text with "Z" as specification 2 section 6.1 writes them.

Limits (AC10):
- A damaged or cut last line of the log is refused by ``eventlog.append`` and never extended or repaired; a failed
  read-back after an append raises and repairs nothing.
- No lock beyond SQLite's own transaction (v0.1 runs one task at a time, concept line 951).
- The caller runs the Resume Check before a grant and gives the task's state; the store projects no state from the log.
- No caller in the core yet; ``.gitignore`` is not changed here (carried to the task that first creates a real
  project-state directory).
- ``session_lease`` (task TASK-066) reads the store only, through SQLite's read-only mode and a deferred transaction:
  it writes, creates and removes nothing, takes only a shared lock at its first read, and refuses ("unreadable") when
  a writer holds an exclusive or pending lock longer than its timeout, or when a hot journal or a journal or WAL state
  that a read-only connection cannot use is present; a hook call during a long commit is refused without a record.

``session_lease`` (task TASK-066; specification 5 section 11 point 7, bullets 3 to 6) is the read-only lookup of the
store for the Claude Code adapter's hook process: the store's answer for a session, or for no session.

Task TASK-067 (specification 2 revision 7 section 3; specification 5 sections 7 and 11 point 7) adds the fourth table
reads (session_id, task_id, seq, path) and four functions: ``add_reads``, the read-set accumulation under the session's
one live lease (the only one meant for a later hook-side caller); ``stored_reads`` and ``remove_reads``, core-only, for
the launcher's record and its clean-up; ``migrate_store``, core-only, which adds the table to a store of the earlier
form. From this task on ``open_store`` creates the four-table form, and every existing function refuses or raises on a
three-table store until ``migrate_store`` has run (no store exists in this repository and no hook is placed).
Limits of task TASK-067:
- The table check compares table and column names only: a reads table without its UNIQUE constraints passes it; "each
  once" and the next seq are held by add_reads' own reads inside its transaction.
- At most 10000 stored paths per session and task and 4096 characters per path; a call that would exceed either is
  refused whole, so a long session's later reads are refused and the record stays a lower bound; the table's total size
  stays unbounded across sessions and tasks; stored_reads has no row cap.
- The presence step, the link check and the open are separate steps for the write path too: a component replaced by a
  link between the check and the "?mode=rw" open would let a write reach another existing store of the four-table
  form; the existing writer functions make no link check at all.
- stored_reads and remove_reads check no lease; a late add_reads between remove_reads and the lease's release is
  accepted and stores reads that no record uses and nothing removes; a store migrated while a hook process reads it is
  a race; the writer never makes a WAL-mode store, and the existing functions' behaviour on one is not tested; now is
  trusted from the caller.
- A read-only open of a store in WAL mode, which the writer never makes, may create its -shm and -wal files beside it
  when the folder is writable and leave them there; in AC7 (a)'s test the store's own bytes were unchanged (D-1421).
- For a store path not encodable as UTF-8, _store_uri raises UnicodeEncodeError (a subclass of ValueError), and the
  finding names that type, "unreadable: UnicodeEncodeError", under the contract's type rule (D-1421 E1).
- session_lease's docstring is kept byte-identical, so its sentences on the three tables before K1 are stale by design.

Readings of the specifications that the contract marks "(reading)" are noted where they are applied.
"""

import datetime
import hashlib
import os
import re
import secrets
import sqlite3

from aieos_bootstrap import eventlog

STATE_DIR = '.aieos'
LOG_NAME = 'events.jsonl'
LOCAL_DIR = 'local'
STORE_NAME = 'state.sqlite'
GRANT_STATES = ('READY', 'REWORK')
TABLES = {
    'store': ('epoch', 'counter'),
    'leases': ('task_id', 'holder', 'session_id', 'fencing_epoch', 'fencing_counter', 'granted_at', 'expires_at'),
    'sessions': ('session_id', 'holder', 'started_at', 'ended_at'),
    'reads': ('session_id', 'task_id', 'seq', 'path'),
}
# The tables of the store before task TASK-067 (TABLES without reads), which migrate_store migrates from.
_PRE_READS_TABLES = {name: columns for name, columns in TABLES.items() if name != 'reads'}
# Task TASK-067: the reads table of specification 2 revision 7 section 3, an ordinary rowid table; the UNIQUE
# constraints are a second guard to add_reads' own reads (the table check compares names only).
_CREATE_READS = ('CREATE TABLE reads (session_id TEXT NOT NULL, task_id TEXT NOT NULL, seq INTEGER NOT NULL, '
                 'path TEXT NOT NULL, UNIQUE (session_id, task_id, path), UNIQUE (session_id, task_id, seq))')
_SCHEMA = (
    'CREATE TABLE store (epoch TEXT NOT NULL, counter INTEGER NOT NULL)',
    'CREATE TABLE leases (task_id TEXT PRIMARY KEY, holder TEXT NOT NULL, session_id TEXT NOT NULL, '
    'fencing_epoch TEXT NOT NULL, fencing_counter INTEGER NOT NULL, granted_at TEXT NOT NULL, '
    'expires_at TEXT NOT NULL)',
    'CREATE TABLE sessions (session_id TEXT PRIMARY KEY, holder TEXT NOT NULL, started_at TEXT NOT NULL, '
    'ended_at TEXT)',
    _CREATE_READS,
)
# Every query is a constant text with ? parameters; no query is built from values.
_LEASES = 'SELECT task_id, fencing_epoch, fencing_counter, expires_at FROM leases ORDER BY fencing_counter'
_LEASE_OF_TASK = 'SELECT task_id, fencing_epoch, fencing_counter, expires_at FROM leases WHERE task_id = ?'
_LEASES_OF_SESSION = ('SELECT task_id, fencing_epoch, fencing_counter, expires_at FROM leases WHERE session_id = ? '
                      'ORDER BY fencing_counter')
_TASK = re.compile(r'TASK-[0-9]+')
_TIME = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z')
_ZERO = datetime.timedelta(0)
_UTC = datetime.timezone.utc


class WriteResult:
    """The result of one ``append_event``.

    - ``result``, ``reason``, ``seq`` and ``findings``: those of ``eventlog.append`` for the event (``line`` is the
      appended line when appended, else None).
    - ``refusal``: for a ``fence`` refusal whose record ``eventlog.append`` built, the AppendResult of appending that
      record as a ``record.added`` event (``appended``, or ``duplicate`` on a retry); else None, and the findings say
      why no record exists (AC3).
    """

    __slots__ = ('result', 'reason', 'seq', 'line', 'findings', 'refusal')

    def __init__(self, appended, refusal=None):
        self.result = appended.result
        self.reason = appended.reason
        self.seq = appended.seq
        self.line = appended.line
        self.findings = appended.findings
        self.refusal = refusal

    def __repr__(self):
        return 'WriteResult(%r, reason=%r, seq=%r, refusal=%r)' % (self.result, self.reason, self.seq, self.refusal)


class StoreResult:
    """The result of one change of the store: ``result`` is ``done`` or ``refused``; ``reason`` and ``findings`` say
    why a change was refused; ``value`` is what was done (a lease, a list of leases, or None)."""

    __slots__ = ('result', 'reason', 'findings', 'value')

    def __init__(self, result, reason=None, findings=(), value=None):
        self.result = result
        self.reason = reason
        self.findings = tuple(findings)
        self.value = value

    def __repr__(self):
        return 'StoreResult(%r, reason=%r, findings=%r)' % (self.result, self.reason, self.findings)


def _refused(reason, finding):
    return StoreResult('refused', reason, [finding])


# ---- arguments ----

def _check_root(root):
    """AC1: the root is an existing folder; checked before anything is opened."""
    if not isinstance(root, str) or not root:
        raise TypeError('the root is given as a non-empty string')
    if not os.path.isdir(root):
        raise ValueError('the root is not an existing folder: %r' % root)


def _is_str(value):
    return isinstance(value, str) and value != ''


def _check_time(value, what):
    if not (isinstance(value, datetime.datetime) and value.tzinfo is not None and value.utcoffset() == _ZERO):
        raise ValueError('%s is not a timezone-aware datetime in UTC' % what)
    if value.microsecond:
        raise ValueError('%s has a fraction of a second; times are whole seconds (specification 2 section 6.1)' % what)


def _check_task(task_id):
    if not (isinstance(task_id, str) and _TASK.fullmatch(task_id)):
        raise ValueError('task_id is not TASK- followed by digits')


def _time_text(value):
    return '%04d-%02d-%02dT%02d:%02d:%02dZ' % (value.year, value.month, value.day, value.hour, value.minute,
                                                value.second)


def _time_value(text):
    if not (isinstance(text, str) and _TIME.fullmatch(text)):
        raise ValueError('a stored time is not ISO 8601 text with "Z": %r' % (text,))
    return datetime.datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=_UTC)


def _digest(kind, event_id):
    """AC3: the SHA-256 hex digest of the UTF-8 text of ``kind`` and the refused event's event_id joined by LF."""
    return hashlib.sha256(('%s\n%s' % (kind, event_id)).encode('utf-8')).hexdigest()


# ---- paths (AC1) ----

def log_path(root):
    """The event log's path under the root."""
    return os.path.join(root, STATE_DIR, LOG_NAME)


def read_log(root):
    """The bytes of the root's event log, or b"" when it does not exist (TASK-026 AC11). It creates and writes
    nothing."""
    _check_root(root)
    return _read_log(log_path(root))


def store_path(root):
    """The local store's path under the root."""
    return os.path.join(root, STATE_DIR, LOCAL_DIR, STORE_NAME)


# ---- the event log (AC2, AC3) ----

def _read_log(path):
    if not os.path.exists(path):
        return b''
    with open(path, 'rb') as f:
        return f.read()


def _append_line(path, log, line):
    """Append exactly ``line`` to the file whose bytes were ``log``, flush and sync it, and read it back (INV-009).
    A read-back that differs raises; nothing more is written and nothing is repaired (fail closed)."""
    with open(path, 'ab') as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())
    after = _read_log(path)
    if after != log + line:
        raise RuntimeError('the log read back after the append is not the given bytes followed by the new line '
                           '(INV-009); nothing more is written and nothing is repaired')


def append_event(root, event_type, payload, event_id, appended_at, recorder, task_id=None, fencing_token=None,
                 corrects=None):
    """Append one event to the root's event log through ``eventlog.append``. Returns a WriteResult (AC2, AC3).

    The lease ``eventlog.append`` needs is the store's held lease on ``task_id`` (None when the store or the lease is
    absent). ``recorder`` is required, so that a fence refusal's record can always be built for an event that names a
    task (DEF-0030; decision D-405, disposition (h)).
    """
    _check_root(root)
    if not _is_str(recorder):
        raise ValueError('the recorder is not a non-empty string')
    os.makedirs(os.path.join(root, STATE_DIR), exist_ok=True)
    path = log_path(root)
    log = _read_log(path)
    lease = held_lease(root, task_id) if isinstance(task_id, str) and _TASK.fullmatch(task_id) else None
    record_id = _digest('refusal-record', event_id) if isinstance(event_id, str) else None
    r = eventlog.append(log, event_type, payload, event_id, appended_at, task_id=task_id, fencing_token=fencing_token,
                        corrects=corrects, lease=lease, recorder=recorder, record_id=record_id)
    if r.result == 'appended':
        _append_line(path, log, r.line)
        return WriteResult(r)
    if r.result == 'refused' and r.reason == 'fence' and r.record is not None:
        # AC3: the refusal recorded as its own record.added event; it carries no fencing_token, so it needs no lease,
        # and a retry gives "duplicate" by its derived event_id (idempotency, concept line 856).
        rec = eventlog.append(log, 'record.added', r.record, _digest('refusal', event_id), appended_at,
                              task_id=task_id, recorder=recorder)
        if rec.result == 'appended':
            _append_line(path, log, rec.line)
        return WriteResult(r, refusal=rec)
    return WriteResult(r)


# ---- the store (AC4 to AC7) ----

def _connect(path):
    return sqlite3.connect(path, isolation_level=None)


def _tables(con):
    names = [row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
    found = {}
    for name in names:
        found[name] = tuple(row[1] for row in con.execute('SELECT * FROM pragma_table_info(?)', (name,)))
    return found


def _check_schema(con):
    if _tables(con) != TABLES:
        raise ValueError('the store does not hold exactly the tables store, leases, sessions and reads of '
                         'specification 2 section 3')
    rows = con.execute('SELECT epoch, counter FROM store').fetchall()
    if len(rows) != 1 or not _is_str(rows[0][0]) or not (isinstance(rows[0][1], int) and rows[0][1] >= 0):
        raise ValueError('the store does not hold exactly one row with an epoch and a counter of 0 or more')
    return rows[0]


def _transaction(path, work):
    """Run ``work(con)`` in one SQLite transaction on the existing store; the connection is closed afterwards, so
    the journal is gone when this returns (AC1)."""
    con = _connect(path)
    try:
        con.execute('BEGIN IMMEDIATE')
        try:
            _check_schema(con)
            out = work(con)
        except BaseException:
            con.execute('ROLLBACK')
            raise
        con.execute('COMMIT')
        return out
    finally:
        con.close()


def _existing_store(root):
    """The store's path when the store exists; None when it does not (nothing is created)."""
    _check_root(root)
    path = store_path(root)
    return path if os.path.exists(path) else None


def _lease(row):
    """A lease in eventlog.LEASE_KEYS' form, as eventlog.append and recovery.reconcile take it (AC5, AC6)."""
    task_id, epoch, counter, expires_at = row
    return {'task_id': task_id, 'fencing_token': {'epoch': epoch, 'counter': counter},
            'expires_at': _time_value(expires_at)}


def open_store(root, epoch=None):
    """Create the store when it does not exist, with its tables and one store row (the given epoch, or a new random
    one, and counter 0); open an existing store unchanged, and raise if a given epoch differs from its own (AC4).
    Returns the store's epoch and counter as a mapping."""
    _check_root(root)
    if epoch is not None and not _is_str(epoch):
        raise ValueError('the epoch is not a non-empty string')
    path = store_path(root)
    if os.path.exists(path):
        con = _connect(path)
        try:
            own, counter = _check_schema(con)
        finally:
            con.close()
        if epoch is not None and epoch != own:
            raise ValueError('the given epoch differs from the store\'s own epoch')
        return {'epoch': own, 'counter': counter}
    os.makedirs(os.path.join(root, STATE_DIR, LOCAL_DIR), exist_ok=True)
    new_epoch = secrets.token_hex(16) if epoch is None else epoch
    con = _connect(path)
    try:
        con.execute('BEGIN IMMEDIATE')
        try:
            for statement in _SCHEMA:
                con.execute(statement)
            con.execute('INSERT INTO store (epoch, counter) VALUES (?, 0)', (new_epoch,))
        except BaseException:
            con.execute('ROLLBACK')
            raise
        con.execute('COMMIT')
    finally:
        con.close()
    return {'epoch': new_epoch, 'counter': 0}


def start_session(root, session_id, holder, now):
    """Start a session once; a second start of the same id is refused (AC7)."""
    if not _is_str(session_id) or not _is_str(holder):
        raise ValueError('session_id and holder are not both non-empty strings')
    _check_time(now, 'now')
    path = _existing_store(root)
    if path is None:
        raise ValueError('no store exists under the root; open_store creates it')

    def work(con):
        if con.execute('SELECT 1 FROM sessions WHERE session_id = ?', (session_id,)).fetchone():
            return _refused('started', 'the session %r was already started' % session_id)
        con.execute('INSERT INTO sessions (session_id, holder, started_at, ended_at) VALUES (?, ?, ?, NULL)',
                    (session_id, holder, _time_text(now)))
        return StoreResult('done')
    return _transaction(path, work)


def end_session(root, session_id, now):
    """End a started session once and release its leases; returns the released leases, oldest grant first (AC7)."""
    if not _is_str(session_id):
        raise ValueError('session_id is not a non-empty string')
    _check_time(now, 'now')
    path = _existing_store(root)
    if path is None:
        raise ValueError('no store exists under the root; open_store creates it')

    def work(con):
        row = con.execute('SELECT ended_at FROM sessions WHERE session_id = ?', (session_id,)).fetchone()
        if row is None:
            return _refused('session', 'the session %r was never started' % session_id)
        if row[0] is not None:
            return _refused('ended', 'the session %r was already ended' % session_id)
        con.execute('UPDATE sessions SET ended_at = ? WHERE session_id = ?', (_time_text(now), session_id))
        released = [_lease(r) for r in con.execute(_LEASES_OF_SESSION,
                                                   (session_id,))]
        con.execute('DELETE FROM leases WHERE session_id = ?', (session_id,))
        return StoreResult('done', value=released)
    return _transaction(path, work)


def grant_lease(root, task_id, task_state, holder, session_id, now, expires_at):
    """Grant one lease on ``task_id`` (AC5): only for a task in READY or REWORK (the caller's reading of the log; the
    store does not project it), when no lease on the task is held, ``expires_at`` is after ``now``, and the session is
    the holder's, started and not ended. The counter increases by one and the lease is inserted in one transaction;
    the lease is returned in eventlog.LEASE_KEYS' form. Any other case is refused and changes nothing. The caller runs
    the Resume Check first (specification 3 section 1); the store does not."""
    _check_task(task_id)
    if not _is_str(holder) or not _is_str(session_id):
        raise ValueError('holder and session_id are not both non-empty strings')
    _check_time(now, 'now')
    _check_time(expires_at, 'expires_at')
    path = _existing_store(root)
    if path is None:
        raise ValueError('no store exists under the root; open_store creates it')
    if task_state not in GRANT_STATES:
        return _refused('state', 'a lease is granted only on a task in READY or REWORK, not %r' % (task_state,))
    if not expires_at > now:
        return _refused('expiry', 'expires_at is not after now')

    def work(con):
        if con.execute('SELECT 1 FROM leases WHERE task_id = ?', (task_id,)).fetchone():
            return _refused('held', 'a lease on %s is held; it is released or expired first' % task_id)
        session = con.execute('SELECT holder, ended_at FROM sessions WHERE session_id = ?', (session_id,)).fetchone()
        if session is None or session[1] is not None or session[0] != holder:
            return _refused('session', 'the session %r is not a started, not ended session of %r'
                            % (session_id, holder))
        epoch, counter = con.execute('SELECT epoch, counter FROM store').fetchone()
        counter += 1
        con.execute('UPDATE store SET counter = ?', (counter,))
        con.execute('INSERT INTO leases (task_id, holder, session_id, fencing_epoch, fencing_counter, granted_at, '
                    'expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (task_id, holder, session_id, epoch, counter, _time_text(now), _time_text(expires_at)))
        return StoreResult('done', value=_lease((task_id, epoch, counter, _time_text(expires_at))))
    return _transaction(path, work)


def release_lease(root, task_id):
    """Remove the held lease on ``task_id`` and return it, or None when none is held (AC6)."""
    _check_task(task_id)
    path = _existing_store(root)
    if path is None:
        return None

    def work(con):
        row = con.execute(_LEASE_OF_TASK, (task_id,)).fetchone()
        if row is None:
            return None
        con.execute('DELETE FROM leases WHERE task_id = ?', (task_id,))
        return _lease(row)
    return _transaction(path, work)


def _check_token(token):
    """TASK-028 AC2: a fencing token in the store's own form, {epoch: a non-empty str, counter: an int, not a bool, at
    least 0}; anything else raises ValueError."""
    if (not isinstance(token, dict) or set(token) != {'epoch', 'counter'} or not _is_str(token['epoch'])
            or type(token['counter']) is not int or token['counter'] < 0):
        raise ValueError('the fencing token is not {epoch: a non-empty string, counter: an int at least 0}')


def release_lease_token(root, task_id, fencing_token):
    """Remove the held lease on ``task_id`` only when its fencing token equals ``fencing_token`` (TASK-028 AC1 to AC3;
    DEF-0053 F3). The comparison and the removal run in one transaction, and the removal is keyed on the task, the
    epoch and the counter, so a lease granted to another holder since, which has a new counter, is never removed.
    Returns StoreResult('done', value=the removed lease); else nothing changes and the result is refused with reason
    ``none`` (no lease on the task is held, or no store exists; none is created) or ``token`` (another token is held)."""
    _check_task(task_id)
    _check_token(fencing_token)
    epoch, counter = fencing_token['epoch'], fencing_token['counter']
    path = _existing_store(root)
    if path is None:
        return _refused('none', 'no store exists under the root, so no lease on %s is held' % task_id)

    def work(con):
        row = con.execute(_LEASE_OF_TASK, (task_id,)).fetchone()
        if row is None:
            return _refused('none', 'no lease on %s is held' % task_id)
        if (row[1], row[2]) != (epoch, counter):
            return _refused('token', 'the lease on %s is held with epoch %r and counter %r, not epoch %r and counter %r'
                            % (task_id, row[1], row[2], epoch, counter))
        removed = con.execute('DELETE FROM leases WHERE task_id = ? AND fencing_epoch = ? AND fencing_counter = ?',
                              (task_id, epoch, counter)).rowcount
        if removed != 1:
            raise sqlite3.DatabaseError('the release removed %d rows, not 1' % removed)
        return StoreResult('done', value=_lease(row))
    return _transaction(path, work)


def expire_leases(root, now):
    """Remove every lease whose expires_at is at or before ``now`` and return them, oldest expiry first (AC6;
    specification 1 section 8: "An expired lease is expired, whatever its holder believes")."""
    _check_time(now, 'now')
    path = _existing_store(root)
    if path is None:
        return []

    def work(con):
        leases = [_lease(r) for r in con.execute(_LEASES)]
        gone = sorted((x for x in leases if not x['expires_at'] > now),
                      key=lambda x: (x['expires_at'], x['fencing_token']['counter']))
        for x in gone:
            con.execute('DELETE FROM leases WHERE task_id = ?', (x['task_id'],))
        return gone
    return _transaction(path, work)


def held_lease(root, task_id):
    """The held lease on ``task_id`` in eventlog.LEASE_KEYS' form, or None (AC6). It reads only; a missing store is
    not created."""
    _check_task(task_id)
    path = _existing_store(root)
    if path is None:
        return None
    return _transaction(path, lambda con: next(
        (_lease(r) for r in con.execute(_LEASE_OF_TASK, (task_id,))), None))


def held_leases(root):
    """Every held lease in eventlog.LEASE_KEYS' form, by fencing counter, as ``recovery.reconcile`` takes them (AC6)."""
    path = _existing_store(root)
    if path is None:
        return []
    return _transaction(path, lambda con: [_lease(r) for r in con.execute(_LEASES)])


# ---- the reads table and the read-set accumulation (task TASK-067) ----
#
# Everything of task TASK-067 stands above the marker of task TASK-066's lookup, so that the text below that marker
# keeps no INSERT, UPDATE, DELETE or PRAGMA. It uses names defined below the marker (_store_uri, _KIND_BITS,
# _REGULAR_FILE, _LOOKUP_TIMEOUT_MAX, _check_lookup_root, _named), which Python resolves at call time.

_READS_MAX = 10000
_READ_PATH_MAX = 4096
_RO_SUFFIX = '?mode=ro'
_RW_SUFFIX = '?mode=rw'
_READS_COUNT = 'SELECT COUNT(*) FROM reads WHERE session_id = ? AND task_id = ?'
_READS_PATHS = 'SELECT path FROM reads WHERE session_id = ? AND task_id = ?'
_READS_TOP = 'SELECT MAX(seq) FROM reads WHERE session_id = ? AND task_id = ?'
_READS_INSERT = 'INSERT INTO reads (session_id, task_id, seq, path) VALUES (?, ?, ?, ?)'
_READS_IN_ORDER = 'SELECT path FROM reads WHERE session_id = ? AND task_id = ? ORDER BY seq, rowid'
_READS_REMOVE = 'DELETE FROM reads WHERE session_id = ? AND task_id = ?'
_TABLES_FINDING = 'tables: the store does not hold exactly the writer\'s tables and one store row'


def _live_lease(con, session_id, now, any_lease):
    """The live lease of a session, inside the caller's transaction (TASK-067 AC4; TASK-066 AC2's order): no lease
    row at all in the store ("no_lease_row"), no such session ("session"), an ended session ("ended"), then the stored
    times of that session's lease rows only are parsed (a malformed one raises ValueError, which each caller turns into
    "unreadable"), and not exactly one of them with expires_at > now ("leases"). ``any_lease`` is the caller's own
    answer to whether the store holds any lease row, so no second such query is run here. Returns a refused
    StoreResult, or StoreResult("done", "tied", value=the lease in eventlog.LEASE_KEYS' form)."""
    if not any_lease:
        return _refused('no_lease_row', 'no_lease_row: the store holds no lease row')
    row = con.execute('SELECT ended_at FROM sessions WHERE session_id = ?', (session_id,)).fetchone()
    if row is None:
        return _refused('session', 'session: no session with this id')
    if row[0] is not None:
        return _refused('ended', 'ended: the session is ended')
    leases = [_lease(r) for r in con.execute(_LEASES_OF_SESSION, (session_id,))]
    live = [x for x in leases if x['expires_at'] > now]
    if len(live) != 1:
        return _refused('leases', 'leases: not exactly one unexpired lease of the session (%d)' % len(live))
    return StoreResult('done', 'tied', value=live[0])


def _store_present(root):
    """The presence step and the link check of session_lease, for the four functions of task TASK-067 (session_lease
    keeps its own): os.lstat of the store path ("no_store" for a missing entry, "unreadable" for another OSError or a
    ValueError, "link" for an entry that is not a regular file), then the realpath comparison ("link", a raising step
    included). Returns (a refused StoreResult, None), or (None, the checked realpath of the store)."""
    path = store_path(root)
    try:
        kind = os.lstat(path).st_mode & _KIND_BITS
    except (FileNotFoundError, NotADirectoryError):
        return _refused('no_store', 'no_store: no store file under the root'), None
    except (OSError, ValueError) as e:
        return _named('unreadable', e), None
    if kind != _REGULAR_FILE:
        return _refused('link', 'link: the store path is not a regular file'), None
    try:
        real = os.path.realpath(path)
        same = os.path.normcase(real) == os.path.normcase(
            os.path.join(os.path.realpath(root), STATE_DIR, LOCAL_DIR, STORE_NAME))
    except Exception as e:
        return _named('link', e), None
    if not same:
        return _refused('link', 'link: the store or a folder above it resolves elsewhere'), None
    return None, real


def _write_steps(con, work, check):
    """Inside _write_store's open transaction: the table check when ``check`` is True, then the work. A result that is
    not a "done" or a "refused" StoreResult is "unreadable"."""
    if check:
        try:
            _check_schema(con)
        except ValueError:
            return _refused('tables', _TABLES_FINDING)
    out = work(con)
    if isinstance(out, StoreResult) and out.result in ('done', 'refused'):
        return out
    return _refused('unreadable', 'unreadable: the work gave no store result')


def _write_store(real, timeout, work, check=True):
    """One write transaction on the existing store at the checked realpath ``real`` (task TASK-067; _transaction is
    unchanged). The URI is _store_uri's, checked to end in exactly "?mode=ro" before only that suffix becomes
    "?mode=rw" (SQLite's rw mode opens an existing file only, so a store removed after the check is never created);
    the connection takes the given timeout and no implicit transaction; BEGIN IMMEDIATE; the table check when ``check``
    is True ("tables"); the work. A "done" result is committed; a refused result is rolled back and returned; any other
    result, any exception (inside the work too), a lock held past the timeout, a damaged file, any sqlite error and a
    failing COMMIT give "unreadable: <exception type name>" after a rollback. ROLLBACK runs only while a transaction is
    open; a failing ROLLBACK, or a failing close before a successful COMMIT, gives "unreadable"; after a successful
    COMMIT a failing close changes nothing. No exception escapes."""
    con = None
    committed = False
    result = None
    try:
        try:
            uri = _store_uri(real, os.sep, os.altsep)
            if not uri.endswith(_RO_SUFFIX):
                raise ValueError('the store URI does not end in the read-only mode')
            con = sqlite3.connect(uri[:-len(_RO_SUFFIX)] + _RW_SUFFIX, uri=True, timeout=timeout,
                                  isolation_level=None)
            con.execute('BEGIN IMMEDIATE')
            result = _write_steps(con, work, check)
            if result.result == 'done':
                con.execute('COMMIT')
                committed = True
        except Exception as e:
            result = _named('unreadable', e)
        finally:
            if con is not None and not committed:
                try:
                    if con.in_transaction:
                        con.execute('ROLLBACK')
                except Exception as e:
                    result = _named('unreadable', e)
    finally:
        if con is not None:
            try:
                con.close()
            except Exception as e:
                if not committed:
                    result = _named('unreadable', e)
    return result


def _reads_answer(con, session_id, task_id):
    """Inside _read_reads' deferred transaction: the table check, then the stored paths in seq order."""
    try:
        _check_schema(con)
    except ValueError:
        return _refused('tables', _TABLES_FINDING)
    paths = [row[0] for row in con.execute(_READS_IN_ORDER, (session_id, task_id))]
    if any(type(p) is not str for p in paths):
        return _refused('unreadable', 'unreadable: a stored path is not text')
    return StoreResult('done', value=paths)


def _read_reads(real, timeout, session_id, task_id):
    """stored_reads' read: _store_uri's "?mode=ro" URI for the checked realpath, the timeout, no implicit transaction,
    BEGIN DEFERRED, the reads, then ROLLBACK (only while a transaction is open, so a failed BEGIN skips it) and close in
    finally blocks, whose failure gives "unreadable". It writes and creates nothing."""
    con = None
    result = None
    try:
        try:
            con = sqlite3.connect(_store_uri(real, os.sep, os.altsep), uri=True, timeout=timeout,
                                  isolation_level=None)
            con.execute('BEGIN DEFERRED')
            result = _reads_answer(con, session_id, task_id)
        except Exception as e:
            result = _named('unreadable', e)
        finally:
            if con is not None:
                try:
                    if con.in_transaction:
                        con.execute('ROLLBACK')
                except Exception as e:
                    result = _named('unreadable', e)
    finally:
        if con is not None:
            try:
                con.close()
            except Exception as e:
                result = _named('unreadable', e)
    return result


def _check_reads_session(session_id):
    if type(session_id) is not str or not session_id:
        raise ValueError('session_id is not a non-empty str')
    session_id.encode('utf-8')


def _check_reads_timeout(timeout):
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= _LOOKUP_TIMEOUT_MAX:
        raise ValueError('timeout is not a number of seconds above 0 and at most 60')


def _check_read_path(path):
    if type(path) is not str or not path or '\x00' in path or len(path) > _READ_PATH_MAX:
        raise ValueError('a path is not a non-empty str of at most 4096 characters without NUL')
    path.encode('utf-8')


def _add_work(con, session_id, items, now):
    """add_reads' work inside its one BEGIN IMMEDIATE transaction (AC2 steps 8 and 9, then the inserts)."""
    any_lease = con.execute('SELECT 1 FROM leases LIMIT 1').fetchone() is not None
    live = _live_lease(con, session_id, now, any_lease)
    if live.result != 'done':
        return live
    task_id = live.value['task_id']
    if not (isinstance(task_id, str) and _TASK.fullmatch(task_id)):
        return _refused('unreadable', 'unreadable: the lease\'s task id is not in the writer\'s form')
    count = con.execute(_READS_COUNT, (session_id, task_id)).fetchone()[0]
    if count > _READS_MAX:
        return _refused('bound', 'bound: more than 10000 paths are stored for the session and its task')
    stored = {row[0] for row in con.execute(_READS_PATHS, (session_id, task_id))}
    new = []
    for p in items:
        if p not in stored:
            stored.add(p)
            new.append(p)
    if count + len(new) > _READS_MAX:
        return _refused('bound', 'bound: the stored and the new paths would exceed 10000')
    top = con.execute(_READS_TOP, (session_id, task_id)).fetchone()[0]
    seq = 0 if top is None else top + 1
    for p in new:
        con.execute(_READS_INSERT, (session_id, task_id, seq, p))
        seq += 1
    return StoreResult('done', value=len(new))


def add_reads(root, session_id, paths, now, timeout=5.0):
    """Add the paths a hook call passed for a session to the reads table, under the session's one live lease (task
    TASK-067; specification 5 sections 7 and 11 point 7, bullet 3; specification 2 revision 7 section 3): in one
    BEGIN IMMEDIATE transaction, refused unless the session holds a live lease (a check of the store's lease, not of a
    token the caller carries), then each given path not yet stored for the session and the lease's task is added in the
    given order with the next seq (one more than the largest stored, 0 for the first). The task is the lease's task,
    never an argument. The only function of task TASK-067 meant for a later hook-side caller; nothing calls it yet but
    the tests, and claude_code_store's check of its calls is not widened here.

    Arguments: ``root``, the project root (non-empty, absolute, an existing folder); ``session_id``, a non-empty str of
    exactly type str; ``paths``, exactly a list or a tuple of paths, each a non-empty str of exactly type str, encodable
    as UTF-8, without NUL, of at most 4096 characters, kept as given (whitespace-only included; no normalisation);
    ``now``, a timezone-aware datetime in UTC with whole seconds; ``timeout``, above 0 and at most 60. Now is trusted
    from the caller: a now earlier than the real time would make an expired lease read as live (the fail-open
    direction), so the later hook-side caller must take now from the process clock.

    The result is a StoreResult: "done" with value the number of paths added (0 or more), or "refused" with one finding
    and the reason of the first step that applies: "argument", "bound" (more than 10000 paths in the call), "path",
    "root", "no_store", "unreadable" or "link" (the presence step and the link check), "unreadable" (the open, a lock
    held past the timeout, a damaged file, any sqlite error), "tables", the live-lease reasons "no_lease_row",
    "session", "ended", "unreadable" (a malformed stored time of the session's lease rows), "leases", then
    "unreadable" for a lease whose task id is not in the writer's form, then "bound" (more than 10000 stored for the
    session and its task, or the stored and the new together would exceed 10000). A refusal changes nothing. A finding
    is fixed words and, where an exception is named, its type, or the lease count; never a message, a root, a path, a
    session id or a task id. No exception escapes: any other exception gives "unreadable: <type name>". A COMMIT that
    fails, or a process that dies after it, may have applied the change although "unreadable" is returned; "each
    once" makes a retry safe."""
    try:
        _check_reads_session(session_id)
        if type(paths) not in (list, tuple):
            raise ValueError('paths is not a list or a tuple')
        _check_time(now, 'now')
        _check_reads_timeout(timeout)
        items = tuple(paths)
    except Exception as e:
        return _named('argument', e)
    if len(items) > _READS_MAX:
        return _refused('bound', 'bound: more than 10000 paths in one call')
    try:
        for p in items:
            _check_read_path(p)
    except Exception as e:
        return _named('path', e)
    try:
        _check_lookup_root(root)
    except Exception as e:
        return _named('root', e)
    try:
        refusal, real = _store_present(root)
        if refusal is not None:
            return refusal
        return _write_store(real, timeout, lambda con: _add_work(con, session_id, items, now))
    except Exception as e:
        return _named('unreadable', e)


def _check_reads_task(task_id):
    if type(task_id) is not str or not _TASK.fullmatch(task_id):
        raise ValueError('task_id is not TASK- followed by digits')


def stored_reads(root, session_id, task_id, timeout=5.0):
    """The stored paths of a session and a task, in the order of seq, then rowid (task TASK-067), read only, for the
    launcher's observed read-set record before the release (specification 5 section 11 point 7, bullet 2). Core-only.
    It checks no lease, so it works for a session with no lease, an expired lease, an ended or an unknown session.

    The result is a StoreResult: "done" with value the list of paths (empty when none), or "refused" with one finding,
    in the order "argument" (session_id as add_reads'; task_id exactly a str in the writer's form; timeout), "root",
    "no_store", "unreadable" or "link", "unreadable" (the open or a read, a lock past the timeout included), "tables";
    a stored path that is not text gives "unreadable". It connects through SQLite's read-only mode, runs one BEGIN
    DEFERRED, and ends the transaction and closes the connection on every path; it writes and creates nothing. It has
    no row cap: a store written outside the writer can hold more than 10000 rows of a session and task. No exception
    escapes."""
    try:
        _check_reads_session(session_id)
        _check_reads_task(task_id)
        _check_reads_timeout(timeout)
    except Exception as e:
        return _named('argument', e)
    try:
        _check_lookup_root(root)
    except Exception as e:
        return _named('root', e)
    try:
        refusal, real = _store_present(root)
        if refusal is not None:
            return refusal
        return _read_reads(real, timeout, session_id, task_id)
    except Exception as e:
        return _named('unreadable', e)


_SESSION_LEASES_ENDED = 'SELECT ended_at FROM sessions WHERE session_id = ?'


def _session_leases_answer(con, session_id):
    """Inside _session_leases_read's deferred transaction (task TASK-078): the table check, the session's row, then
    the session's lease rows in fencing-counter order."""
    try:
        _check_schema(con)
    except ValueError:
        return _refused('tables', _TABLES_FINDING)
    row = con.execute(_SESSION_LEASES_ENDED, (session_id,)).fetchone()
    if row is None:
        return _refused('session', 'session: no session with this id')
    leases = [_lease(r) for r in con.execute(_LEASES_OF_SESSION, (session_id,))]
    return StoreResult('done', 'rows', value={'ended': row[0] is not None, 'leases': leases})


def _session_leases_read(real, timeout, session_id):
    """session_leases' read (task TASK-078), in the form of _read_reads: _store_uri's "?mode=ro" URI for the checked
    realpath, the timeout, no implicit transaction, BEGIN DEFERRED, the reads, then ROLLBACK (only while a transaction
    is open) and close in finally blocks, whose failure gives "unreadable". It writes and creates nothing."""
    con = None
    result = None
    try:
        try:
            con = sqlite3.connect(_store_uri(real, os.sep, os.altsep), uri=True, timeout=timeout,
                                  isolation_level=None)
            con.execute('BEGIN DEFERRED')
            result = _session_leases_answer(con, session_id)
        except Exception as e:
            result = _named('unreadable', e)
        finally:
            if con is not None:
                try:
                    if con.in_transaction:
                        con.execute('ROLLBACK')
                except Exception as e:
                    result = _named('unreadable', e)
    finally:
        if con is not None:
            try:
                con.close()
            except Exception as e:
                result = _named('unreadable', e)
    return result


def session_leases(root, session_id, now, timeout=5.0):
    """A session's lease rows, each with its expiry, and whether the session has ended (task TASK-078; specification
    6 section 4, the status tool's reading), read only. Core-only.

    The result is a StoreResult: "done" with reason "rows" and value {"ended": a bool, "leases": the session's lease
    rows in eventlog.LEASE_KEYS' form, in fencing-counter order}; or "refused" with one finding, in the order
    "argument" (session_id as add_reads'; now a timezone-aware UTC datetime with whole seconds; timeout above 0 and at
    most 60), "root", "no_store", "unreadable" or "link" (_store_present's steps), "unreadable" (the open or a read, a
    lock past the timeout included), "tables", "session" (no session with this id). The value is a stated choice. No
    exception escapes.

    Limits, stated: ``now`` is checked for its form only; comparing each expiry with the time is the caller's. An
    "expired" row exists only between a lease's expiry and the next expire_leases, which removes it; end_session
    removes an ended session's rows, so an ended session has none. More than one unexpired row of one session breaks
    the one-lease rule as this task reads it; this function reports the rows as they are. The read is a hand-kept copy
    of session_lease's and _read_reads' transaction steps, kept in step by hand; the presence step and the link check
    are _store_present's, unchanged. It connects through SQLite's read-only mode, runs one BEGIN DEFERRED, and ends the
    transaction and closes the connection on every path; it writes and creates nothing."""
    try:
        _check_reads_session(session_id)
        _check_time(now, 'now')
        _check_reads_timeout(timeout)
    except Exception as e:
        return _named('argument', e)
    try:
        _check_lookup_root(root)
    except Exception as e:
        return _named('root', e)
    try:
        refusal, real = _store_present(root)
        if refusal is not None:
            return refusal
        return _session_leases_read(real, timeout, session_id)
    except Exception as e:
        return _named('unreadable', e)


def remove_reads(root, session_id, task_id, timeout=5.0):
    """Remove every stored path of a session and a task in one write transaction (task TASK-067; specification 2
    revision 7 section 3: the reads are removed once the session's observed read-set record is appended or found
    present). Core-only; the caller (the launcher, specification 7) decides when; it reads no event log and checks no
    lease, so it can remove the reads of a session whose lease is live.

    The result is a StoreResult: "done" with value the number removed (the DELETE's row count), or "refused" with one
    finding, in the order "argument", "root", "no_store", "unreadable" or "link", "unreadable", "tables". It removes
    nothing else. No exception escapes."""
    try:
        _check_reads_session(session_id)
        _check_reads_task(task_id)
        _check_reads_timeout(timeout)
    except Exception as e:
        return _named('argument', e)
    try:
        _check_lookup_root(root)
    except Exception as e:
        return _named('root', e)

    def work(con):
        return StoreResult('done', value=con.execute(_READS_REMOVE, (session_id, task_id)).rowcount)
    try:
        refusal, real = _store_present(root)
        if refusal is not None:
            return refusal
        return _write_store(real, timeout, work)
    except Exception as e:
        return _named('unreadable', e)


def _migrate_work(con):
    """migrate_store's work inside its one BEGIN IMMEDIATE transaction (AC5's table): P1 the unchanged table check
    ("current" when it passes); P2 the tables compared with the pre-task form ("tables" when they differ); P3 the
    CREATE TABLE reads; P4 the unchanged table check again ("migrated", or "tables" when it raises ValueError). An
    sqlite3.Error at P1, P3 or P4 reaches _write_store's handler ("unreadable"), and every refusal is rolled back."""
    try:
        _check_schema(con)
        current = True
    except ValueError:
        current = False
    if current:
        return StoreResult('done', value='current')
    if _tables(con) != _PRE_READS_TABLES:
        return _refused('tables', _TABLES_FINDING)
    con.execute(_CREATE_READS)
    try:
        _check_schema(con)
    except ValueError:
        return _refused('tables', _TABLES_FINDING)
    return StoreResult('done', value='migrated')


def migrate_store(root, timeout=5.0):
    """Add the reads table to a store in exactly the form before task TASK-067, in one write transaction, changing
    nothing else; a store already in the four-table form is left unchanged (task TASK-067; specification 5 section 11
    point 7, bullet 6: a store of the old form is refused until its migration). Core-only; nothing calls it yet but
    the tests. open_store keeps its meaning (create, or open unchanged).

    The result is a StoreResult: "done" with value "migrated" or "current", or "refused" with one finding, in the
    order "argument" (timeout), "root", "no_store", "unreadable" or "link", "unreadable" (the open, a lock past the
    timeout, any sqlite error), "tables" (another form, or a pre-task form whose store row is not exactly one). It
    never creates a store. No exception escapes."""
    try:
        _check_reads_timeout(timeout)
    except Exception as e:
        return _named('argument', e)
    try:
        _check_lookup_root(root)
    except Exception as e:
        return _named('root', e)
    try:
        refusal, real = _store_present(root)
        if refusal is not None:
            return refusal
        return _write_store(real, timeout, _migrate_work, check=False)
    except Exception as e:
        return _named('unreadable', e)


# ---- the read-only lookup of the store (task TASK-066) ----

# The bytes a file URI keeps as they are: RFC 3986's unreserved characters and "/" (the drive's ":" is kept apart).
_URI_KEEP = frozenset(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~/')
_DRIVE_LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
# The kind bits of st_mode and the kind of a regular file, read without the stat module (no import is added).
_KIND_BITS = 0o170000
_REGULAR_FILE = 0o100000
_LOOKUP_TIMEOUT_MAX = 60


def _store_uri(path, sep, altsep):
    """The read-only SQLite URI of the store at ``path`` (TASK-066; D-1362 C1). Only ``sep`` and ``altsep`` become "/"
    (a "\\" where it is neither is an ordinary byte and is encoded as %5C); a "/" goes before a drive (an ASCII letter
    and ":" at the start); every UTF-8 byte outside A-Z, a-z, 0-9, "-", ".", "_", "~", "/" and the drive's ":" becomes
    %XX in uppercase hex; the result is "file:" + "//" + that path + "?mode=ro". A path that starts with two separators
    (a UNC path) is refused, and so is a path not encodable as UTF-8 (a surrogate-escaped byte): both raise
    ValueError."""
    text = path
    for s in (sep, altsep):
        if s and s != '/':
            text = text.replace(s, '/')
    if text.startswith('//'):
        raise ValueError('a path that starts with two separators (a UNC path) is not made into a URI')
    drive = len(text) >= 2 and text[0] in _DRIVE_LETTERS and text[1] == ':'
    if drive:
        text = '/' + text
    data = text.encode('utf-8')
    out = []
    for i, b in enumerate(data):
        if b in _URI_KEEP or (drive and i == 2):
            out.append(chr(b))
        else:
            out.append('%%%02X' % b)
    return 'file:' + '//' + ''.join(out) + '?mode=ro'


def _check_lookup(session_id, now, timeout):
    """session_lease's arguments (AC1); raises on any that is out of form."""
    if session_id is not None:
        if not _is_str(session_id):
            raise ValueError('session_id is neither None nor a non-empty string')
        session_id.encode('utf-8')
    _check_time(now, 'now')
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= _LOOKUP_TIMEOUT_MAX:
        raise ValueError('timeout is not a number of seconds above 0 and at most 60')


def _check_lookup_root(root):
    """session_lease's root (AC1): a non-empty string, absolute, naming an existing folder; raises otherwise."""
    _check_root(root)
    if not os.path.isabs(root):
        raise ValueError('the root is not an absolute path')


def _named(reason, error):
    """A refusal whose one finding names the exception's type, never its message (AC1)."""
    return _refused(reason, '%s: %s' % (reason, type(error).__name__))


def _store_answer(con, session_id, now):
    """The store's answer inside the lookup's one deferred transaction (AC2)."""
    try:
        _check_schema(con)
    except ValueError:
        return _refused('tables', 'tables: the store does not hold exactly the writer\'s tables and one store row')
    any_lease = con.execute('SELECT 1 FROM leases LIMIT 1').fetchone() is not None
    if session_id is None:
        if any_lease:
            return _refused('lease_row_without_session', 'lease_row_without_session: the store holds a lease row')
        return StoreResult('done', 'no_lease_row')
    return _live_lease(con, session_id, now, any_lease)


def _read_store(uri, timeout, session_id, now):
    """Open the store read-only, run one deferred transaction, end it and close the connection on every path."""
    con = None
    try:
        con = sqlite3.connect(uri, uri=True, timeout=timeout, isolation_level=None)
        con.execute('BEGIN DEFERRED')
        try:
            answer = _store_answer(con, session_id, now)
        finally:
            con.execute('ROLLBACK')
        return answer
    finally:
        if con is not None:
            con.close()


def session_lease(root, session_id, now, timeout=5.0):
    """The store's answer for a session, or for no session, read only (task TASK-066; specification 5 section 11
    point 7, bullets 3 to 6: the hook program reaches the store only through the writer module's functions, a
    read-only lookup of the store among them).

    Arguments: ``root``, the project root (a non-empty, absolute path of an existing folder); ``session_id``, None or a
    non-empty str (the empty-as-absent rule is ``claude_code_store.judge``'s, not this function's); ``now``, a
    timezone-aware datetime in UTC with whole seconds; ``timeout``, the seconds SQLite waits for a lock (above 0, at
    most 60). The session id, the root and now are arguments: where the hook entry takes them from is a later
    contract's. A now earlier than the real time would make an expired lease read as unexpired (the fail-open
    direction), so that contract must take now from the process clock.

    The result is a StoreResult: "done" with reason "tied" (value the one unexpired lease of the session, in
    eventlog.LEASE_KEYS' form) or reason "no_lease_row" (only with no session id and no lease row at all; value None);
    else "refused" with one finding and one of the reasons "argument", "root", "no_store", "link", "unreadable",
    "tables", "lease_row_without_session", "no_lease_row", "session", "ended", "leases", in that order of checking.
    These map to the hook's three outcomes (specification 5 section 11 point 7, bullets 3, 5 and 6): tied,
    enforce nothing (no session id, no root, and no lease row at all) and refuse without a record. No exception
    escapes; a finding names an exception's type, never its message. "Unexpired" is expires_at > now, the comparison of
    expire_leases.

    Read-only and the lock: the store is opened through SQLite's read-only mode (a file URI ending "?mode=ro") with the
    given timeout and no implicit transaction; one deferred BEGIN holds every read, the table check included; the
    transaction is ended and the connection closed on every path. So no row is inserted, changed or removed, no table
    is created, no expiry is run (the launcher's), and the store file, its journal and its folders are never created.
    The deferred BEGIN takes only a shared lock, at its first read, and a writer's commit waits for it while it reads.
    A writer that holds, or waits at, an exclusive or pending lock longer than the timeout makes the lookup refuse
    ("unreadable"): a hook call during a long commit is refused without a record. A hot rollback journal left by a
    crash cannot be rolled back by a read-only connection, and a journal or WAL state a read-only connection cannot use
    is refused too ("unreadable"). Claude Code's own hook timeouts are unmeasured (C6).

    The URI is built by ``_store_uri`` from the link check's verified left-hand string, the realpath of the store path,
    so the store opened is the store checked; a UNC path and a path not encodable as UTF-8 are refused ("unreadable").

    The table form: the store is checked against TABLES, the writer's three tables, before K1 (the contract that adds
    the reads table). Specification 2 revision 7 section 3 already lists four tables, reads among them; a store in that
    four-table form is refused ("tables") until K1; when K1 adds reads, TABLES gains it, this lookup follows without a
    change of its own, and a store of the old form is refused until K1's migration.

    The presence step and the link check: os.lstat of the store path first; a missing entry (FileNotFoundError or
    NotADirectoryError) gives "no_store", any other OSError or a ValueError "unreadable", an entry that is not a
    regular file (a directory, a link, any other kind) "link". Just before the store is opened, os.path.normcase of
    the realpath of the store path must equal os.path.normcase of the root's realpath joined with the project-state
    directory, its local folder and the store's name; else "link". Limits: real links and junctions are never
    exercised in CI, which runs on Linux; a junction or link that realpath does not resolve on the running Python is
    not seen; short (8.3) names that realpath does not resolve give a false refusal (fail closed); hard links and bind
    mounts are not seen; the check and the open are two steps, and a change between them is not seen.

    No hook is placed, no matcher chosen, no setting changed and nothing measured here (CC-3, the owner's; C6).
    """
    try:
        _check_lookup(session_id, now, timeout)
    except Exception as e:
        return _named('argument', e)
    try:
        _check_lookup_root(root)
    except Exception as e:
        return _named('root', e)
    try:
        path = store_path(root)
        try:
            kind = os.lstat(path).st_mode & _KIND_BITS
        except (FileNotFoundError, NotADirectoryError):
            return _refused('no_store', 'no_store: no store file under the root')
        except (OSError, ValueError) as e:
            return _named('unreadable', e)
        if kind != _REGULAR_FILE:
            return _refused('link', 'link: the store path is not a regular file')
        try:
            real = os.path.realpath(path)
            same = os.path.normcase(real) == os.path.normcase(
                os.path.join(os.path.realpath(root), STATE_DIR, LOCAL_DIR, STORE_NAME))
        except Exception as e:
            return _named('link', e)
        if not same:
            return _refused('link', 'link: the store or a folder above it resolves elsewhere')
        return _read_store(_store_uri(real, os.sep, os.altsep), timeout, session_id, now)
    except Exception as e:
        return _named('unreadable', e)
