"""Integration tests of aieos_bootstrap.read_set_record (task TASK-064, rule R5's store half): observe through the real
writer in a temporary folder that the test creates and removes, with a granted lease: the record appended once and read
back, a repeat "duplicate", another list "conflict", and a token that is not the held lease's refused by the fence.
The context's root must have judge's absolute Windows form (TASK-063 AC1), which a temporary folder of the CI's Linux
runner does not have; so the context names a made-up Windows root and append is writer.append_event with the
temporary folder put in place of the root it is given, every other argument passed unchanged (a reading). Each test
names its criteria in its own docstring."""

import datetime
import tempfile
import unittest

from aieos_bootstrap import read_set_record as rs
from aieos_bootstrap import records
from aieos_bootstrap import writer

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
SID = 'made-up-session-8'
ROOT = 'C:\\proj\\repo'


def setup(root):
    writer.open_store(root)
    writer.start_session(root, SID, 'agent-1', T0)
    lease = writer.grant_lease(root, 'TASK-100', 'READY', 'agent-1', SID, T0, T0 + datetime.timedelta(hours=1)).value
    ctx = {'root': ROOT, 'task_id': 'TASK-100', 'session_id': SID, 'fencing_token': lease['fencing_token'],
           'write_set': ['docs/notes/**'], 'allowlist': ['git status'], 'recorder': 'a test session ' + SID}
    seen = []

    def append(given_root, *args, **kw):
        seen.append(given_root)
        return writer.append_event(root, *args, **kw)

    return ctx, append, seen


def at(minutes):
    return T0 + datetime.timedelta(minutes=minutes)


class Store(unittest.TestCase):
    def test_appended_once_and_read_back(self):
        """TASK-064 AC5, AC3, AC1: the record is appended once under the lease and the log reads back with no finding."""
        with tempfile.TemporaryDirectory() as root:
            ctx, append, seen = setup(root)
            r = rs.observe(ctx, ['a/b.py', 'c.md', 'a/b.py'], at(1), append=append)
            self.assertEqual((r['result'], r['core']['result']), ('written', 'appended'))
            self.assertEqual(seen, [ROOT])
            report = records.check_log(writer.read_log(root))
            self.assertEqual(report.findings(), [])
            events = [x.event for x in report.lines]
            self.assertEqual(len(events), 1)
            e = events[0]
            self.assertEqual((e['type'], e['event_id'], e['task_id'], e['fencing_token']),
                             ('record.added', 'observed-read-set/TASK-100/' + SID, 'TASK-100', ctx['fencing_token']))
            self.assertEqual(e['payload']['read_paths'], ['a/b.py', 'c.md'])
            self.assertEqual(e['payload']['evidence_type'], 'observed_read_set')

    def test_repeat_duplicate_and_another_list_conflict(self):
        """TASK-064 AC3, AC5: the same list again gives "duplicate"; another list for the same session is refused
        "conflict"; the log holds one record."""
        with tempfile.TemporaryDirectory() as root:
            ctx, append, _ = setup(root)
            self.assertEqual(rs.observe(ctx, ['a.py'], at(1), append=append)['result'], 'written')
            again = rs.observe(ctx, ['a.py'], at(2), append=append)
            self.assertEqual((again['result'], again['core']['result']), ('duplicate', 'duplicate'))
            other = rs.observe(ctx, ['b.py'], at(3), append=append)
            self.assertEqual((other['result'], other['reason'], other['core']['reason']), ('refused', 'core', 'conflict'))
            self.assertEqual(len(records.check_log(writer.read_log(root)).lines), 1)

    def test_token_not_held_refused_by_the_fence(self):
        """TASK-064 AC5: a token that is not the held lease's is refused by the writer's fence, whose own refusal record
        is in the log; no read-set record is added."""
        with tempfile.TemporaryDirectory() as root:
            ctx, append, _ = setup(root)
            ctx['fencing_token'] = dict(ctx['fencing_token'], counter=ctx['fencing_token']['counter'] + 5)
            r = rs.observe(ctx, ['a.py'], at(1), append=append)
            self.assertEqual((r['result'], r['reason'], r['core']['reason']), ('refused', 'core', 'fence'))
            lines = records.check_log(writer.read_log(root)).lines
            self.assertEqual(len(lines), 1)
            self.assertEqual(lines[0].event['type'], 'record.added')
            self.assertNotEqual(lines[0].event['payload'].get('evidence_type'), 'observed_read_set')

    def test_after_release_refused_by_the_fence(self):
        """TASK-064 AC5: after the lease is released, the read-set is refused by the fence (the caller passes it before
        the release)."""
        with tempfile.TemporaryDirectory() as root:
            ctx, append, _ = setup(root)
            self.assertEqual(writer.release_lease_token(root, 'TASK-100', ctx['fencing_token']).result, 'done')
            r = rs.observe(ctx, ['a.py'], at(1), append=append)
            self.assertEqual((r['result'], r['core']['reason']), ('refused', 'fence'))


if __name__ == '__main__':
    unittest.main()
