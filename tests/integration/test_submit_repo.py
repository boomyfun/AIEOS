"""Integration test of aieos_bootstrap.submit over this repository's history (task TASK-025, rule R9, AC9): the real
gitread.run reads fixed objects of main, read only; the writer's functions are stand-ins that record their calls and
write nothing, and the root given is never written. It needs the repository's full history (a shallow clone fails
it). The results are data about accepted commits: they reopen nothing. Each test names its criteria in its own
docstring."""

import datetime
import pathlib
import unittest

from aieos_bootstrap import submit

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPO = str(ROOT)
STATE_ROOT = str(ROOT / 'no-such-state-root')
FIX = '057cc530e8fa39814eed4431c4de0fd9887014cf'
FIX_TREE = 'c7b8728f2d0a4bb0efec66076fe3ad0b4f2da441'
NOW = datetime.datetime(2026, 10, 12, 9, 30, 0, tzinfo=datetime.timezone.utc)


class Refusal:
    result = 'refused'
    reason = 'fence'
    findings = ('fence: the event carries no fencing_token',)
    refusal = None


class Recorder:
    def __init__(self):
        self.append_calls = []
        self.release_calls = []
        self.held_calls = []

    def append(self, *args, **kwargs):
        self.append_calls.append((args, kwargs))
        return Refusal()

    def release(self, *args):
        self.release_calls.append(args)

    def held(self, *args):
        self.held_calls.append(args)


def run(commit_id, task_id):
    rec = Recorder()
    r = submit.submit(STATE_ROOT, REPO, commit_id, task_id, 'ev-integration', 'test', NOW, append=rec.append,
                      release=rec.release, held=rec.held)
    return r, rec


class RepositoryHistory(unittest.TestCase):
    def test_a_commit_of_the_task_without_a_fence_reaches_the_writer_with_no_token(self):
        """TASK-025 AC9, TASK-025 AC2, TASK-025 AC3 and TASK-025 AC13: TASK-024's fix commit names AIEOS-Task:
        TASK-024 and no AIEOS-Fence; as a submission of TASK-024 it reaches append once with fencing_token None, release
        and held are not called, and the stand-in's refusal is returned with a finding of the missing fence."""
        r, rec = run(FIX, 'TASK-024')
        self.assertEqual((r['result'], r['reason']), ('refused', 'fence'))
        self.assertEqual(len(rec.append_calls), 1)
        args, kwargs = rec.append_calls[0]
        self.assertEqual(args[1:3], ('task.submitted', {'commit': FIX, 'compensating': False}))
        self.assertEqual(kwargs, {'task_id': 'TASK-024', 'fencing_token': None})
        self.assertIn('no usable AIEOS-Fence', ' '.join(r['findings']))
        self.assertEqual((rec.release_calls, rec.held_calls), ([], []))

    def test_a_commit_of_another_task_is_refused_before_the_writer(self):
        """TASK-025 AC9, TASK-025 AC3 and TASK-025 AC13: the same commit as a submission of TASK-025 is refused with
        reason trailer and a finding of the different task; nothing is called."""
        r, rec = run(FIX, 'TASK-025')
        self.assertEqual((r['result'], r['reason']), ('refused', 'trailer'))
        self.assertIn('TASK-024', ' '.join(r['findings']))
        self.assertEqual((rec.append_calls, rec.release_calls, rec.held_calls), ([], [], []))

    def test_a_tree_is_refused_as_not_a_commit(self):
        """TASK-025 AC9, TASK-025 AC2 and TASK-025 AC13: that commit's tree is refused with reason git; nothing is
        called."""
        r, rec = run(FIX_TREE, 'TASK-024')
        self.assertEqual((r['result'], r['reason']), ('refused', 'git'))
        self.assertIn('not a commit', ' '.join(r['findings']))
        self.assertEqual((rec.append_calls, rec.release_calls, rec.held_calls), ([], [], []))

    def test_the_root_is_not_written(self):
        """TASK-025 AC9 and TASK-025 AC8: after the runs, the root given still does not exist."""
        run(FIX, 'TASK-024')
        self.assertFalse(pathlib.Path(STATE_ROOT).exists())


if __name__ == '__main__':
    unittest.main()
