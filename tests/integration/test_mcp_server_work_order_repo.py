"""Integration tests of the MCP tools get_work_order and query (TASK-083 AC9) over this repository's history: the store
is given as stand-ins (writer.session_leases answers one live lease of TASK-081 for session "s1" in session_leases'
rows form, writer.read_log a log built in the test with eventlog.append), AIEOS_ROOT is this repository's root, where
nothing is written, and read is the default gitread.run. The repository must hold the full history, as
tests/integration/test_gitread_repo.py needs. Each test names its criteria in its own docstring."""

import datetime
import hashlib
import json
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import base_files, eventlog, mcp_server, writer

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
BASE = '4c496d7e406523e495498dd377f3a40587a14ac9'
TASK = 'TASK-081'
DERIVED = 'docs/specs/spec-03-resume-check-and-decision-engine.md'
SPEC7 = 'docs/specs/spec-07-cli-and-zero-friction-path.md'
SPEC7_SHA = '613cbd72dca411586ca03d790cd01bb044d0eb8e9a2885d9c3f8bb25cc9f5efb'
T0 = datetime.datetime(2026, 10, 24, 12, 0, 0, tzinfo=datetime.timezone.utc)
H1 = datetime.timedelta(hours=1)


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
        r = eventlog.append(data, kind, payload, eid, T0, task_id=TASK)
        if r.result != 'appended':
            raise AssertionError(r.findings)
        data += r.line
    return data


class TASK083AC9Repository(unittest.TestCase):
    def setUp(self):
        value, findings = base_files.read_file(ROOT, BASE, 'docs/tasks/%s.yaml' % TASK)
        self.assertIsNone(findings, findings)
        self.log = log_for(value['text'])
        self.calls = []

    def session_leases(self, root, session_id, now):
        self.calls.append(('session_leases', root, session_id))
        lease = {'task_id': TASK, 'expires_at': T0 + H1, 'fencing_token': {'epoch': 1, 'counter': 1}}
        return writer.StoreResult('done', 'rows', value={'ended': False, 'leases': [lease]})

    def read_log(self, root):
        self.calls.append(('read_log', root))
        return self.log

    def append_event(self, *args, **kwargs):
        raise AssertionError('append_event called')

    def test_work_order_and_query_of_task_081(self):
        """TASK-083 AC9: with the store as stand-ins and this repository at base_commit, get_work_order answers
        TASK-081's Work Order at that base, its work_order_hash that of its canonical form without that key, and query
        of spec 7 answers its item with the SHA-256 of the file's text; nothing is appended."""
        env = {'AIEOS_SESSION_ID': 's1', 'AIEOS_ROOT': ROOT, 'AIEOS_BASE': BASE}
        with mock.patch.object(writer, 'session_leases', self.session_leases), \
                mock.patch.object(writer, 'read_log', self.read_log), \
                mock.patch.object(writer, 'append_event', self.append_event):
            work_order, word = mcp_server.get_work_order({}, env, T0)
            item, word2 = mcp_server.query({'ref': SPEC7}, env, T0)
        self.assertIsNone(word, word)
        self.assertEqual((work_order['task'], work_order['base'], work_order['session_id']), (TASK, BASE, 's1'))
        rest = {k: v for k, v in work_order.items() if k != 'work_order_hash'}
        canonical = json.dumps(rest, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        self.assertEqual(work_order['work_order_hash'], hashlib.sha256(canonical.encode('utf-8')).hexdigest())
        self.assertIsNone(word2, word2)
        self.assertEqual((item['ref'], item['hash']), (SPEC7, SPEC7_SHA))
        self.assertEqual(hashlib.sha256(item['content'].encode('utf-8')).hexdigest(), SPEC7_SHA)
        self.assertEqual(self.calls, [('session_leases', ROOT, 's1'), ('read_log', ROOT)] * 2)


if __name__ == '__main__':
    unittest.main()
