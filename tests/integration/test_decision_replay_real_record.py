"""Integration test of aieos_bootstrap.decision_replay over the real record (task TASK-139 AC7; erratum E1.5, decision D-6325): line 13 of
the tracked event log, a decision.execution record of the first launch of TASK-136, is read from the repository's own history through
base_files and gitread (the repository root is taken from this file's path), and replayed with the checked tree's engine, whose
SHA-256 must be the pinned one. The command-line entry is run over the same repository with the real reads, except the status read,
which is a stand-in that prints nothing: a CI checkout may hold untracked files that earlier steps made, which the entry's own tree
check would count, and that check has its own unit tests. No test writes a file or starts a process of its own; Git runs only through
gitread. The record needs the repository's history: a shallow clone fails this test, as it should. The whole-repository assertion of the
entry (exit 0) holds only while every decision record of the tree can be replayed: a later decision.acceptance line in the tracked log, or a
decision.execution record written under another engine than the pinned one, makes it fail by design until its replay or its pin exists."""

import hashlib
import pathlib
import unittest

from aieos_bootstrap import base_files, decision_replay, gitread, resume_check

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
PIN = 'b03c0b8a1caaa77c2974da0b512bd38e1f330b5d08dda1bbd85427944eee2e76'
LOG_PATH = '.aieos/events.jsonl'
RECORD_LINE = 13


def head_of_repo():
    r = gitread.run(ROOT, ['rev-parse', '--verify', '--end-of-options', 'HEAD'])
    if r['error'] is not None or r['exit'] != 0:
        raise RuntimeError('rev-parse HEAD gave no answer: %r' % (r['error'],))
    return r['out'].decode('ascii').strip()


def real_log():
    got, found = base_files.read_file(ROOT, head_of_repo(), LOG_PATH)
    if found is not None:
        raise RuntimeError('the log could not be read: %r' % (found,))
    return got['text'].encode('utf-8')


class RealRecordTests(unittest.TestCase):
    def test_the_engine_file_that_runs_is_the_pinned_one(self):
        # replay_execution runs the engine it is given and hashes only git objects, so this test hashes the working-tree file that runs
        # (line endings normalised: a checkout may use CRLF; the CI's POSIX checkout does not)
        data = pathlib.Path(resume_check.__file__).read_bytes().replace(b'\r\n', b'\n')
        self.assertEqual(hashlib.sha256(data).hexdigest(), PIN)

    def test_line_13_is_replayed_with_the_checked_trees_engine(self):
        ok, found = decision_replay.replay_execution(ROOT, real_log(), RECORD_LINE - 1, [PIN], engine=resume_check)
        self.assertEqual((ok, found), (True, []))

    def test_the_replay_refuses_without_the_pin(self):
        ok, found = decision_replay.replay_execution(ROOT, real_log(), RECORD_LINE - 1, [], engine=resume_check)
        self.assertFalse(ok)

    def test_the_replay_refuses_a_wrong_pin(self):
        ok, found = decision_replay.replay_execution(ROOT, real_log(), RECORD_LINE - 1, ['0' * 64], engine=resume_check)
        self.assertFalse(ok)

    def test_the_entry_prints_replayed_for_the_record(self):
        def read(repo, args, timeout=30):
            if args[0] == 'status':
                return {'exit': 0, 'out': b'', 'err': b'', 'error': None}
            return gitread.run(repo, args, timeout)
        lines = []
        rc = decision_replay.main([ROOT, PIN], read=read, out=lines.append)
        self.assertEqual(rc, 0, lines)
        self.assertTrue(any(l.startswith('REPLAYED ') and l.endswith(':13 ok') for l in lines), lines)
        self.assertTrue(lines[-1].startswith('replay: event logs'), lines)

    def test_the_entry_with_no_pin_fails_the_record(self):
        def read(repo, args, timeout=30):
            if args[0] == 'status':
                return {'exit': 0, 'out': b'', 'err': b'', 'error': None}
            return gitread.run(repo, args, timeout)
        lines = []
        rc = decision_replay.main([ROOT], read=read, out=lines.append)
        self.assertEqual(rc, 1, lines)


if __name__ == '__main__':
    unittest.main()
