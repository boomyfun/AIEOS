"""Integration test of aieos_bootstrap.evaluation over this repository's history (task TASK-027, rule R13, AC14): the
real gitread.run reads TASK-026's two task commits and the commit below them, read only; the writer's functions are
stand-ins that keep their log in memory and write nothing, and the root given is never written. It needs the
repository's history down to those commits (a shallow clone may fail it). The decision it builds is data about an
accepted task: it reopens nothing. Each test names its criteria in its own docstring."""

import datetime
import hashlib
import pathlib
import unittest

from aieos_bootstrap import evaluation
from aieos_bootstrap import eventlog
from aieos_bootstrap import gitread

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPO = str(ROOT)
STATE_ROOT = str(ROOT / 'no-such-state-root')
CONTRACT = ROOT / 'docs' / 'tasks' / 'TASK-026.yaml'
CHASH = '3214886e13d348d83ca886d4e53773629879a4b4edf692525ae2da759882f21b'
HEAD = '1f6ff6d8131b5d53a881f895aedb0dd632075ff4'
FIRST = '92e4ab140d2f311d4cb3a188f1b6e496bae5baf4'
BELOW = '8aa9ed91547639d934ab88924123395ca23667da'
WRITE_SET = ['src/aieos_bootstrap/__init__.py', 'src/aieos_bootstrap/startup.py', 'src/aieos_bootstrap/writer.py',
             'tests/integration/test_startup_repo.py', 'tests/property/test_startup_properties.py',
             'tests/unit/test_startup.py', 'tests/unit/test_writer.py']
NOW = datetime.datetime(2026, 10, 12, 10, 0, 0, tzinfo=datetime.timezone.utc)
FENCE = {'epoch': 'e0', 'counter': 1}


def log_bytes():
    """A log with TASK-026's task.approved (the contract's hash) and its task.submitted naming HEAD."""
    log = b''
    r = eventlog.append(log, 'task.approved', {'contract_version': 'v1', 'contract_hash': CHASH,
                                               'approval_record': 'rec-approval'}, 'approved-26', NOW,
                        task_id='TASK-026')
    log += r.line
    lease = {'task_id': 'TASK-026', 'fencing_token': FENCE, 'expires_at': NOW + datetime.timedelta(hours=1)}
    r = eventlog.append(log, 'task.submitted', {'commit': HEAD, 'compensating': False}, 'submitted-26', NOW,
                        task_id='TASK-026', fencing_token=FENCE, lease=lease)
    return log + r.line


def values():
    return {
        'contract': {'traces_to': ['docs/specs/spec-01-state-and-event-model.md#7'], 'risk': 'high',
                     'owner_kept_act': False, 'verification_plan': ['G0', 'G1', 'G2', 'G3']},
        'changed_paths': list(WRITE_SET),
        'risk_rules': [{'id': 'R2', 'match': ['src/**', 'tests/**'], 'class': 'medium'}],
        'owner_kept_rules': [{'id': 'OPS-002', 'match': ['.github/**']}],
        'articles': [{'id': 'INV-001', 'scope': ['src/**'], 'evidence_required': ['deterministic_rule']}],
        'default_profiles': {'high': [{'dimension': 'functional', 'evidence_types': ['unit_test']}]},
        'requirement_profiles': [],
        'delegation': True,
        'evidence_comparison': {'weakens': False},
        'auto_accept': {},
        'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1',
    }


class RepositoryHistory(unittest.TestCase):
    def test_the_evaluation_of_task_026(self):
        """TASK-027 AC14, TASK-027 AC4, TASK-027 AC5, TASK-027 AC8 and TASK-027 AC15: the walk reads TASK-026's two
        task commits and ends at the commit below them; the changed paths are exactly TASK-026's write set; one
        decision.acceptance is appended, bound to HEAD and to the content hash of the contract's bytes."""
        data = CONTRACT.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), CHASH)
        reads, appends = [], []

        def read(repo, args, *rest):
            reads.append(list(args))
            return gitread.run(repo, args, *rest)

        def append(root, event_type, payload, event_id, appended_at, recorder, task_id=None, fencing_token=None):
            appends.append((root, event_type, payload, event_id, task_id, fencing_token))
            return eventlog.append(log_bytes(), event_type, payload, event_id, appended_at, task_id=task_id,
                                   recorder=recorder)

        declared = {'intent_versions': {'docs/specs/spec-01-state-and-event-model.md': 'v1'}, 'retries': 2}
        r = evaluation.evaluate_task(STATE_ROOT, REPO, 'TASK-026', data, declared, values(), [], 'aieos-core', NOW,
                                     read=read, read_log=lambda root: log_bytes(), append=append)
        self.assertEqual(r['result'], 'evaluated', r['findings'])
        self.assertEqual([a[-1] for a in reads if a[0] == 'cat-file'], [HEAD, FIRST, BELOW])
        self.assertEqual([a[-1] for a in reads if a[0] == 'diff-tree'], [HEAD, FIRST])
        self.assertEqual(r['changed_paths'], sorted(WRITE_SET))
        self.assertEqual(len(appends), 1)
        root, kind, payload, event_id, task_id, token = appends[0]
        self.assertEqual((root, kind, task_id, token), (STATE_ROOT, 'decision.acceptance', 'TASK-026', None))
        self.assertEqual(payload['evaluated_commit'], HEAD)
        self.assertEqual(payload['task_content_hash'], hashlib.sha256(data + b'\n' + HEAD.encode('ascii')).hexdigest())
        self.assertFalse(pathlib.Path(STATE_ROOT).exists())


if __name__ == '__main__':
    unittest.main()
