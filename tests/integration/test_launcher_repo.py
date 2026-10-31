"""Integration tests of aieos_bootstrap.launcher over this repository's history (TASK-086 AC11): start for TASK-088
with HEAD fixed at f216376e by a stand-in read that answers only the exact HEAD form and the exact base form
(refs/heads/main) and forwards every other call to gitread.run unchanged; the log is a stand-in holding TASK-088's task.approved; every store function is a stand-in
bound to the real function's signature, so no file is written. The repository must hold the full history, as
tests/integration/test_resume_log_inputs_repo.py needs. Each test names its criteria in its own docstring."""

import datetime
import inspect
import pathlib
import types
import unittest

from aieos_bootstrap import adapter, eventlog, gitread, launcher, resume_check, resume_inputs, writer

REPO = str(pathlib.Path(__file__).resolve().parents[2])
ROOT = str(pathlib.Path(__file__).resolve().parents[2] / 'no-such-launcher-root')
COMMIT = 'f216376e75a25945d9056d195e7282b589457a0b'
TASK = 'TASK-088'
PINNED = 'e1578939404da0b61d56d9187521b92c923e7cb841acdf15d0afb7155605a135'
HEAD_ARGS = ['rev-parse', '--verify', '--end-of-options', 'HEAD']
BASE_ARGS = ['rev-parse', '--verify', '--end-of-options', 'refs/heads/main']
NOW = datetime.datetime(2026, 10, 24, 12, 0, 0, tzinfo=datetime.timezone.utc)
LATER = NOW + datetime.timedelta(hours=1)
REC = 'aieos-launcher (integration)'


class Calls:
    """Stand-ins that record each call, bound to the real function's signature, and give a set answer."""

    def __init__(self, answers):
        self.calls = []
        self.answers = dict(answers)

    def make(self, name, real):
        def stand_in(*args, **kwargs):
            inspect.signature(real).bind(*args, **kwargs)
            self.calls.append((name, args, kwargs))
            a = self.answers.get(name)
            return a(*args, **kwargs) if callable(a) else a
        return stand_in

    def of(self, name):
        return [c for c in self.calls if c[0] == name]


class Intercept:
    """A read that answers only the exact HEAD form and the exact base form (refs/heads/main) with COMMIT and forwards
    every other call to gitread.run unchanged, recording the forwarded calls."""

    def __init__(self):
        self.forwarded = []

    def __call__(self, repo, args, timeout=30):
        if list(args) == HEAD_ARGS or list(args) == BASE_ARGS:
            return {'exit': 0, 'out': (COMMIT + '\n').encode('ascii'), 'err': b'', 'error': None}
        self.forwarded.append((repo, list(args), timeout))
        return gitread.run(repo, args, timeout)


def written(*args, **kwargs):
    return writer.WriteResult(types.SimpleNamespace(result='appended', reason=None, seq=1, line=b'', findings=()))


def ended(*args, **kwargs):
    out = dict.fromkeys(adapter.RESULT_KEYS)
    out.update({'result': 'done', 'findings': []})
    return out


class TASK086AC11Repository(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        given, found = resume_inputs.git_inputs(REPO, COMMIT, TASK, b'')
        if found is not None:
            raise AssertionError(found)
        r = eventlog.append(b'', 'task.approved', {'contract_version': 'v1', 'contract_hash': given['contract_hash'],
                                                   'approval_record': 'r'}, 'appr-088', NOW, task_id=TASK)
        if r.result != 'appended':
            raise AssertionError(r.findings)
        log = r.line
        cls.read = Intercept()
        cls.c = Calls({'read_log': lambda root: log, 'expire': [], 'held': None,
                       'start_session': writer.StoreResult('done'), 'append': written,
                       'grant': writer.StoreResult('done'), 'release': writer.StoreResult('done'),
                       'start': adapter.start, 'end': ended})
        kw = {name: cls.c.make(name, real) for name, real in (
            ('read_log', writer.read_log), ('expire', writer.expire_leases), ('held', writer.held_lease),
            ('start_session', writer.start_session), ('append', writer.append_event), ('grant', writer.grant_lease),
            ('release', writer.release_lease_token), ('start', adapter.start), ('end', adapter.end))}
        cls.result = launcher.start(ROOT, REPO, TASK, 'integration', None, 'agent-1', REC, NOW, LATER, read=cls.read,
                                    **kw)

    def record(self):
        return next(call[1][2] for call in self.c.of('append') if call[1][1] == 'decision.execution')

    def test_the_reads(self):
        """TASK-086 AC11: HEAD is f216376e; every other read is forwarded to gitread.run unchanged, rev-list,
        diff-tree and cat-file calls among them, and each passes gitread.form_error."""
        self.assertEqual(self.result['head_commit'], COMMIT, self.result['findings'])
        subs = {args[0] for _, args, _ in self.read.forwarded}
        for sub in ('rev-list', 'diff-tree', 'cat-file'):
            self.assertIn(sub, subs)
        self.assertNotIn(HEAD_ARGS, [args for _, args, _ in self.read.forwarded])
        for call in self.read.forwarded:
            self.assertIsNone(gitread.form_error(*call), call)

    def test_the_inputs_and_the_engine(self):
        """TASK-086 AC11: code_sha256 equals the CI's pinned Resume Check e1578939… (aieos-checks.yml :153); the
        inputs' keys equal resume_check.INPUT_KEYS."""
        args = self.c.of('start')[0][1]
        self.assertEqual(set(args[4]), set(resume_check.INPUT_KEYS))
        self.assertEqual(args[5], PINNED)

    def test_a_contract_that_is_not_the_approved_one_gives_check_0(self):
        """TASK-086 AC11: with a task.approved naming a contract hash other than the contract at COMMIT, the real Resume
        Check answers with its check 0 error (decision None and the error "check 0: the contract at HEAD is not the
        approved contract"); start gives "not granted" with reason "decision" and no fencing token, and no lease is
        granted. The error text is in the decision record passed to the append stand-in, not in start's answer."""
        r = eventlog.append(b'', 'task.approved', {'contract_version': 'v1', 'contract_hash': 'f' * 64,
                                                   'approval_record': 'r'}, 'appr-088', NOW, task_id=TASK)
        self.assertEqual(r.result, 'appended')
        c = Calls({'read_log': lambda root: r.line, 'expire': [], 'held': None,
                   'start_session': writer.StoreResult('done'), 'append': written,
                   'grant': writer.StoreResult('done'), 'release': writer.StoreResult('done'),
                   'start': adapter.start, 'end': ended})
        kw = {name: c.make(name, real) for name, real in (
            ('read_log', writer.read_log), ('expire', writer.expire_leases), ('held', writer.held_lease),
            ('start_session', writer.start_session), ('append', writer.append_event), ('grant', writer.grant_lease),
            ('release', writer.release_lease_token), ('start', adapter.start), ('end', adapter.end))}
        out = launcher.start(ROOT, REPO, TASK, 'integration', None, 'agent-1', REC, NOW, LATER, read=Intercept(), **kw)
        record = next(call[1][2] for call in c.of('append') if call[1][1] == 'decision.execution')
        self.assertIsNone(record['decision'])
        self.assertEqual(record['error'], 'check 0: the contract at HEAD is not the approved contract')
        self.assertEqual((out['result'], out['reason']), ('not granted', 'decision'), out['findings'])
        self.assertIsNone(out['fencing_token'])
        self.assertIsNone(out['environment'])
        self.assertEqual(c.of('grant'), [])

    def test_the_decision(self):
        """TASK-086 AC11: the decision record's check 7 fired with "the runtime has no declaration"; its decision
        equals "STOP: scope invalid" (check 2); no lease is granted and adapter.end's stand-in is called once."""
        record = self.record()
        seven = next(c for c in record['checks'] if c['check'] == 7)
        self.assertEqual((seven['status'], seven['detail']), ('fired', 'the runtime has no declaration'))
        self.assertEqual(record['decision'], 'STOP: scope invalid')
        self.assertEqual(self.result['decision'], 'STOP: scope invalid')
        self.assertEqual(self.result['result'], 'not granted')
        self.assertIsNone(self.result['environment'])
        self.assertEqual(self.c.of('grant'), [])
        self.assertEqual(len(self.c.of('end')), 1)
        self.assertIsNone(self.c.of('end')[0][1][3])


if __name__ == '__main__':
    unittest.main()
