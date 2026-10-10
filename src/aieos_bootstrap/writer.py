"""The core's single writer of the project-state directory (task TASK-016): specification 1 sections 4, 5.2 and 8,
specification 2 sections 3 and 6.1; constitution INV-004 and INV-009.

This is the only module of the core that opens files in the project-state directory for writing. Under a root folder
the caller gives, it touches exactly two files (AC1):

- ``<root>/.aieos/events.jsonl``, the event log: ``append_event`` reads its bytes, lets ``eventlog.append`` (TASK-007,
  as TASK-015 left it) decide the one line to append, appends exactly that line, flushes and syncs it, and reads the
  file back (AC2); a fence refusal is recorded as its own ``record.added`` event (AC3);
- ``<root>/.aieos/local/state.sqlite``, the local store of the fence's epoch and counter, the leases and the sessions
  (AC4 to AC7), with SQLite's own rollback journal ``state.sqlite-journal`` beside it, which SQLite creates and removes
  during a transaction (the default rollback journal mode; no WAL).

Every time is an argument, a timezone-aware datetime in UTC with whole seconds; the clock is read nowhere. The store's
times are ISO 8601 text with "Z" as specification 2 section 6.1 writes them.

Limits (AC10):
- A damaged or cut last line of the log is refused by ``eventlog.append`` and never extended or repaired; a failed
  read-back after an append raises and repairs nothing.
- No lock beyond SQLite's own transaction (v0.1 runs one task at a time, concept line 951).
- The caller runs the Resume Check before a grant and gives the task's state; the store projects no state from the log.
- No caller in the core yet; ``.gitignore`` is not changed here (carried to the task that first creates a real
  project-state directory).

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
}
_SCHEMA = (
    'CREATE TABLE store (epoch TEXT NOT NULL, counter INTEGER NOT NULL)',
    'CREATE TABLE leases (task_id TEXT PRIMARY KEY, holder TEXT NOT NULL, session_id TEXT NOT NULL, '
    'fencing_epoch TEXT NOT NULL, fencing_counter INTEGER NOT NULL, granted_at TEXT NOT NULL, '
    'expires_at TEXT NOT NULL)',
    'CREATE TABLE sessions (session_id TEXT PRIMARY KEY, holder TEXT NOT NULL, started_at TEXT NOT NULL, '
    'ended_at TEXT)',
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
        raise ValueError('the store does not hold exactly the tables store, leases and sessions of specification 2 '
                         'section 3')
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
