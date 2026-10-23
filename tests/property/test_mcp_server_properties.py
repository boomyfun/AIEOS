"""Property tests of aieos_bootstrap.mcp_server (task TASK-078): arbitrary input lines never make main raise and get one
answer line at most each; status's answer over arbitrary lease rows follows the mapping. Seeded random cases over a
stand-in for writer.session_leases; no real store, no temporary folder, no file write."""

import datetime
import io
import json
import os
import random
import unittest
from unittest import mock

from aieos_bootstrap import mcp_server, writer

UTC = datetime.timezone.utc
T0 = datetime.datetime(2026, 10, 23, 12, 0, 0, tzinfo=UTC)
ENV = {'AIEOS_SESSION_ID': 's-1', 'AIEOS_ROOT': os.path.join(os.path.abspath(os.sep), 'made-up-root')}
PARTS = ['{', '}', '[', ']', '"', ':', ',', ' ', '\t', 'null', 'true', '1', '-1', '1.5', '"jsonrpc"', '"2.0"', '"id"',
         '"method"', '"params"', '"name"', '"status"', '"initialize"', '"tools/list"', '"tools/call"',
         '"notifications/initialized"', 'é', '\\u0000', 'x']
MESSAGES = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'}, {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 'a', 'method': 'tools/list'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'status'}},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'ask'}},
            {'jsonrpc': '2.0', 'id': None, 'method': 'other'}, {'jsonrpc': '2.0', 'id': True, 'method': 'initialize'}]


def lease(task, until, counter):
    return {'task_id': task, 'fencing_token': {'epoch': 'e', 'counter': counter}, 'expires_at': until}


class AC3AnyLines(unittest.TestCase):
    def test_main_never_raises_and_answers_once_at_most(self):
        """TASK-078 AC3: over 300 seeded cases of arbitrary lines (fragments, valid messages and their mixtures), main
        returns 0, writes only JSON-RPC 2.0 answer lines, and writes no more answer lines than input lines."""
        rng = random.Random(78)
        answer = writer.StoreResult('done', 'rows', value={'ended': False, 'leases': []})
        for case in range(300):
            lines = []
            for _ in range(rng.randint(0, 6)):
                if rng.random() < 0.4:
                    lines.append(json.dumps(rng.choice(MESSAGES)))
                else:
                    lines.append(''.join(rng.choice(PARTS) for _ in range(rng.randint(0, 12))))
            out = io.StringIO()
            with mock.patch.object(writer, 'session_leases', return_value=answer):
                rc = mcp_server.main(io.StringIO(''.join(x.replace('\n', ' ') + '\n' for x in lines)), out, ENV,
                                     lambda: T0)
            with self.subTest(case=case):
                got = out.getvalue().splitlines()
                self.assertEqual(rc, 0)
                self.assertLessEqual(len(got), len(lines))
                for g in got:
                    a = json.loads(g)
                    self.assertEqual(a['jsonrpc'], '2.0')
                    self.assertEqual(len([k for k in ('result', 'error') if k in a]), 1)


class AC5AnyRows(unittest.TestCase):
    def test_the_mapping_over_arbitrary_rows(self):
        """TASK-078 AC5: over 300 seeded sets of lease rows, status gives core_error for more than one unexpired row,
        live for exactly one, expired with the highest counter's task when rows exist and none is unexpired, and none
        for no row or an ended session."""
        rng = random.Random(780)
        for case in range(300):
            ended = rng.random() < 0.2
            rows = [lease('TASK-%d' % rng.randint(1, 99), T0 + datetime.timedelta(minutes=rng.randint(-120, 120)), c)
                    for c in rng.sample(range(1, 1000), rng.randint(0, 4))]
            if ended:
                rows = []
            value = {'ended': ended, 'leases': sorted(rows, key=lambda x: x['fencing_token']['counter'])}
            with mock.patch.object(writer, 'session_leases',
                                   return_value=writer.StoreResult('done', 'rows', value=value)):
                got = mcp_server.status(ENV, T0)
            live = [x for x in rows if x['expires_at'] > T0]
            with self.subTest(case=case):
                if ended or not rows:
                    self.assertEqual(got, ({'task': None, 'lease': 'none'}, None))
                elif len(live) > 1:
                    self.assertEqual(got, (None, 'core_error'))
                elif len(live) == 1:
                    self.assertEqual(got[0]['lease'], 'live')
                    self.assertEqual(got[0]['task'], live[0]['task_id'])
                else:
                    top = max(rows, key=lambda x: x['fencing_token']['counter'])
                    self.assertEqual(got, ({'task': top['task_id'], 'lease': 'expired'}, None))


if __name__ == '__main__':
    unittest.main()
