"""Integration test of aieos_bootstrap.startup over this repository's history (task TASK-026, rule R13, AC14): the real
gitread.run walks every commit reachable from HEAD, read only; the writer's functions are stand-ins that keep their
log in memory and write nothing, and the root given is never written. It needs the repository's full history (a
shallow clone fails it). The observations it builds are data about accepted commits: they reopen nothing. Each test
names its criteria in its own docstring."""

import datetime
import pathlib
import unittest

from aieos_bootstrap import eventlog
from aieos_bootstrap import gitread
from aieos_bootstrap import startup

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPO = str(ROOT)
STATE_ROOT = str(ROOT / 'no-such-state-root')
FIX = '057cc530e8fa39814eed4431c4de0fd9887014cf'
NOW = datetime.datetime(2026, 10, 12, 10, 0, 0, tzinfo=datetime.timezone.utc)


class Stand:
    """Stand-ins for the writer: read_log gives b"" at first and then the lines append kept (decided by
    eventlog.append, with no lease), leases gives [], append records its calls and gives "appended", release and
    expire record their calls."""

    def __init__(self):
        self.log = b''
        self.appends = []
        self.releases = []
        self.expires = []

    def read_log(self, root):
        return self.log

    def leases(self, root):
        return []

    def append(self, root, event_type, payload, event_id, appended_at, recorder, task_id=None, fencing_token=None):
        self.appends.append((event_type, payload, event_id, task_id, fencing_token))
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id,
                            fencing_token=fencing_token, recorder=recorder)
        self.log += r.line
        return r

    def release(self, *args):
        self.releases.append(args)

    def expire(self, root, now):
        self.expires.append((root, now))
        return []


class RepositoryHistory(unittest.TestCase):
    def test_the_walk_over_this_repository(self):
        """TASK-026 AC14, TASK-026 AC2, TASK-026 AC5, TASK-026 AC7 and TASK-026 AC15: the walk from HEAD reaches a
        commit with no parent; TASK-024's fix commit, whose last paragraph names AIEOS-Task: TASK-024 and no
        AIEOS-Fence, gets exactly one append, a record.added observation of an unfenced write that refers to it; no
        task.submitted is appended (no lease is held), release is not called and expire is called once."""
        seen = []

        def read(repo, args, *rest):
            r = gitread.run(repo, args, *rest)
            if args[:2] == ['cat-file', '-p'] and r['error'] is None and r['exit'] == 0:
                seen.append(gitread.parse_commit(r['out']))
            return r
        stand = Stand()
        r = startup.recover(STATE_ROOT, REPO, 'test', NOW, read=read, read_log=stand.read_log, append=stand.append,
                            leases=stand.leases, release=stand.release, expire=stand.expire)
        self.assertEqual((r['result'], r['reason']), ('recovered', None), r['findings'])
        self.assertTrue(any(p['parents'] == [] for p in seen))
        mine = [a for a in stand.appends if FIX in (a[1].get('refers_to'), a[1].get('commit'))]
        self.assertEqual(len(mine), 1)
        event_type, payload, _, task_id, token = mine[0]
        self.assertEqual((event_type, task_id, token), ('record.added', 'TASK-024', None))
        self.assertEqual((payload['evidence_type'], payload['refers_to']), ('unfenced_write', FIX))
        self.assertNotIn('task.submitted', [a[0] for a in stand.appends])
        self.assertEqual(stand.releases, [])
        self.assertEqual(len(stand.expires), 1)
        self.assertFalse(pathlib.Path(STATE_ROOT).exists())


if __name__ == '__main__':
    unittest.main()
