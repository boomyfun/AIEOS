"""Integration tests of aieos_bootstrap.base_inputs over this repository's history (TASK-082 AC9): fixed commits,
read only, gitread.run as read; the log is built in the test with eventlog.append. The repository must hold the full
history, as tests/integration/test_gitread_repo.py needs. Each test names its criteria in its own docstring."""

import datetime
import hashlib
import pathlib
import unittest

from aieos_bootstrap import base_files, base_inputs, context_compiler, eventlog, gitread

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
BASE = '4c496d7e406523e495498dd377f3a40587a14ac9'
OLDER = 'af834d5d4e1e85657bb6c08c823fd16c1b106682'
TASK = 'TASK-081'
DERIVED = 'docs/specs/spec-03-resume-check-and-decision-engine.md'
SPEC7 = 'docs/specs/spec-07-cli-and-zero-friction-path.md'
SPEC7_SHA = '613cbd72dca411586ca03d790cd01bb044d0eb8e9a2885d9c3f8bb25cc9f5efb'
EXCUSED = {'docs/tasks/TASK-028.yaml', 'docs/tasks/TASK-036.yaml'}
NOW = datetime.datetime(2026, 10, 24, 12, 0, 0, tzinfo=datetime.timezone.utc)


def contract_text(commit):
    value, findings = base_files.read_file(ROOT, commit, 'docs/tasks/%s.yaml' % TASK)
    if findings:
        return None
    return value['text']


def log_for(text):
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
    record = {'record_id': 'rec-1', 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local',
              'recorder': 'the Resume Check (test)', 'subject': TASK, 'decision': 'CONTINUE', 'uncovered': [],
              'state_effect': [], 'contract_hash': digest, 'contract_version': 'v1',
              'constitution': {'applicable': ['INV-001', 'INV-002', 'OPS-003'], 'violated': [], 'no_result': []},
              'read_set': {'entries': [{'entry': DERIVED, 'kind': 'path', 'sources': ['derived']}],
                           'estimate': True, 'unresolved': [], 'unanalysed': []}}
    data = b''
    for kind, payload, eid in (('task.approved', {'contract_version': 'v1', 'contract_hash': digest,
                                                  'approval_record': 'a1'}, 'approved-1'),
                               ('decision.execution', record, 'exec-1')):
        r = eventlog.append(data, kind, payload, eid, NOW, task_id=TASK)
        if r.result != 'appended':
            raise AssertionError(r.findings)
        data += r.line
    return data


class TASK082AC9Repository(unittest.TestCase):
    def test_work_order_of_task_081(self):
        """TASK-082 AC9: at base_commit, TASK-081's inputs are read and build_work_order accepts them; spec 7 has its
        intent hash; the derived path outside TASK-081's patterns is in files and derived_read_set."""
        text = contract_text(BASE)
        value, findings = base_inputs.work_order_inputs(ROOT, BASE, TASK, 's1', log_for(text), gitread.run)
        self.assertIsNone(findings, findings)
        self.assertEqual(value['contract']['task'], TASK)
        self.assertEqual(hashlib.sha256(value['files'][SPEC7].encode('utf-8')).hexdigest(), SPEC7_SHA)
        self.assertIn(DERIVED, value['files'])
        self.assertEqual(value['derived_read_set'], [DERIVED])
        work_order, problems = context_compiler.build_work_order(value)
        self.assertIsNone(problems, problems)

    def test_older_commit(self):
        """TASK-082 AC9: at an older commit, where docs/tasks/TASK-081.yaml is absent, the same call gives findings."""
        self.assertIsNone(contract_text(OLDER))
        value, findings = base_inputs.work_order_inputs(ROOT, OLDER, TASK, 's1', log_for(contract_text(BASE)),
                                                        gitread.run)
        self.assertIsNone(value)
        self.assertTrue(findings)

    def test_every_contract_parses(self):
        """TASK-082 AC9: every docs/tasks/*.yaml at base_commit parses with the subset reader except exactly the two
        of the closed excused list, both refused."""
        paths, found = base_files.list_paths(ROOT, BASE, 'docs/tasks')
        self.assertIsNone(found, found)
        refused = set()
        for path in paths:
            if not path.endswith('.yaml'):
                continue
            value, found = base_files.read_file(ROOT, BASE, path)
            self.assertIsNone(found, found)
            try:
                base_inputs._parse_contract_text(value['text'])
            except base_inputs._Stop:
                refused.add(path)
        self.assertEqual(refused, EXCUSED)


if __name__ == '__main__':
    unittest.main()
