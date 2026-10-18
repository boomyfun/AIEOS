"""Integration tests of aieos_bootstrap.read_set_record (task TASK-064, rule R5's store half), in the form of erratum E1
of decision D-1291: observe through the real eventlog.append and the real records.check_log, with no file, folder or
store. The append stand-in keeps the log bytes in memory, passes a lease of writer.held_lease's form (task_id,
fencing_token, expires_at), or None after a release, appends the new line on "appended", and on a fence refusal whose
record is not None appends that record as one record.added event, as writer.append_event does. The writer's file and
store code (open_store, grant_lease, the file write) is tested by the writer's own tests, not here (D-1291 E1).
Checked: the record appended once and read back, a repeat "duplicate", another list "conflict", a token that is not the
lease's refused by the fence, and the read-set refused after the release; and observe's call binds to
writer.append_event's own signature. Each test names its criteria in its own docstring."""

import datetime
import inspect
import unittest

from aieos_bootstrap import eventlog
from aieos_bootstrap import read_set_record as rs
from aieos_bootstrap import records
from aieos_bootstrap import writer

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
SID = 'made-up-session-8'
ROOT = 'C:\\proj\\repo'
TOKEN = {'epoch': 'made-up-epoch', 'counter': 1}


class Log:
    """An in-memory stand-in for writer.append_event over the real eventlog.append (D-1291 E1a)."""

    def __init__(self):
        self.bytes = b''
        self.lease = {'task_id': 'TASK-100', 'fencing_token': dict(TOKEN), 'expires_at': T0 + datetime.timedelta(hours=1)}
        self.roots = []

    def append(self, root, event_type, payload, event_id, appended_at, recorder, task_id=None, fencing_token=None):
        self.roots.append(root)
        r = eventlog.append(self.bytes, event_type, payload, event_id, appended_at, task_id=task_id,
                            fencing_token=fencing_token, lease=self.lease, recorder=recorder,
                            record_id=event_id + '/refusal-record')
        if r.result == 'appended':
            self.bytes += r.line
        elif r.result == 'refused' and r.reason == 'fence' and r.record is not None:
            rec = eventlog.append(self.bytes, 'record.added', r.record, event_id + '/refusal', appended_at,
                                  task_id=task_id, recorder=recorder)
            if rec.result == 'appended':
                self.bytes += rec.line
        return r


def context():
    return {'root': ROOT, 'task_id': 'TASK-100', 'session_id': SID, 'fencing_token': dict(TOKEN),
            'write_set': ['docs/notes/**'], 'allowlist': ['git status'], 'recorder': 'a test session ' + SID}


def at(minutes):
    return T0 + datetime.timedelta(minutes=minutes)


class Store(unittest.TestCase):
    def test_appended_once_and_read_back(self):
        """TASK-064 AC5, AC3, AC1: the record is appended once under the lease and the log reads back with no finding."""
        log, ctx = Log(), context()
        r = rs.observe(ctx, ['a/b.py', 'c.md', 'a/b.py'], at(1), append=log.append)
        self.assertEqual((r['result'], r['core']['result']), ('written', 'appended'))
        self.assertEqual(log.roots, [ROOT])
        report = records.check_log(log.bytes)
        self.assertEqual(report.findings(), [])
        events = [x.event for x in report.lines]
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertEqual((e['type'], e['event_id'], e['task_id'], e['fencing_token']),
                         ('record.added', 'observed-read-set/TASK-100/' + SID, 'TASK-100', TOKEN))
        self.assertEqual(e['payload']['read_paths'], ['a/b.py', 'c.md'])
        self.assertEqual(e['payload']['evidence_type'], 'observed_read_set')

    def test_repeat_duplicate_and_another_list_conflict(self):
        """TASK-064 AC3, AC5: the same list again gives "duplicate"; another list for the same session is refused
        "conflict"; the log holds one record."""
        log, ctx = Log(), context()
        self.assertEqual(rs.observe(ctx, ['a.py'], at(1), append=log.append)['result'], 'written')
        again = rs.observe(ctx, ['a.py'], at(2), append=log.append)
        self.assertEqual((again['result'], again['core']['result']), ('duplicate', 'duplicate'))
        other = rs.observe(ctx, ['b.py'], at(3), append=log.append)
        self.assertEqual((other['result'], other['reason'], other['core']['reason']), ('refused', 'core', 'conflict'))
        self.assertEqual(len(records.check_log(log.bytes).lines), 1)

    def test_token_not_held_refused_by_the_fence(self):
        """TASK-064 AC5: a token that is not the lease's is refused by the fence, whose own refusal record is in the
        log; no read-set record is added."""
        log, ctx = Log(), context()
        ctx['fencing_token'] = dict(TOKEN, counter=6)
        r = rs.observe(ctx, ['a.py'], at(1), append=log.append)
        self.assertEqual((r['result'], r['reason'], r['core']['reason']), ('refused', 'core', 'fence'))
        lines = records.check_log(log.bytes).lines
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].event['type'], 'record.added')
        self.assertEqual(lines[0].event['payload']['evidence_type'], 'refused_submission')

    def test_after_release_refused_by_the_fence(self):
        """TASK-064 AC5: after the lease is released (no lease held), the read-set is refused by the fence (the caller
        passes it before the release)."""
        log, ctx = Log(), context()
        log.lease = None
        r = rs.observe(ctx, ['a.py'], at(1), append=log.append)
        self.assertEqual((r['result'], r['core']['reason']), ('refused', 'fence'))
        self.assertNotIn(b'observed_read_set', log.bytes)

    def test_call_binds_to_the_writers_signature(self):
        """TASK-064 AC5, AC7: observe's call of append binds to writer.append_event's own signature (D-1291 C2)."""
        calls = []

        def capture(*args, **kwargs):
            calls.append((args, kwargs))
            return Log().append(*args, **kwargs)

        rs.observe(context(), ['a.py'], at(1), append=capture)
        self.assertEqual(len(calls), 1)
        bound = inspect.signature(writer.append_event).bind(*calls[0][0], **calls[0][1])
        self.assertEqual(bound.arguments['event_type'], 'record.added')
        self.assertEqual(bound.arguments['fencing_token'], TOKEN)


if __name__ == '__main__':
    unittest.main()
