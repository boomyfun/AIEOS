"""Property tests of aieos_bootstrap.mcp_server (tasks TASK-078 and TASK-079): arbitrary input lines never make main
raise and get one answer line at most each; status's answer over arbitrary lease rows follows the mapping; the claim
tools over arbitrary arguments answer within their forms. Seeded random cases over stand-ins for the writer's
functions; no real store, no temporary folder, no file write."""

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


VALUES = [None, True, 0, 1, -1, 1.5, '', 'x', 'AC1', 'AC', 'é', [], [''], ['a'], ['a', 'b'], [1], {}, {'ac': 'AC2'},
          {'ac': 'AC2', 'text': 't'}, [{'ac': 'AC2', 'text': 't'}], [{'ac': 'B2', 'text': 't'}]]
KEYS = ['assumptions', 'question', 'criteria', 'notes', 'done', 'not_done', 'discoveries', 'risks', 'proposals',
        'fencing_token', 'x']


WORDS = ['w', 'x y', 'é', 'AC1 met', '{"a": 1}']
LISTS = ['done', 'not_done', 'assumptions', 'discoveries', 'risks', 'proposals']


def valid_call(rng, tool):
    """An input of the header's shape for ``tool``, from small random lists of made-up strings; one ask in two also
    carries a made-up fencing_token key, which the tool must refuse as input."""
    def texts(least):
        return ['%s %d' % (rng.choice(WORDS), i) for i in range(rng.randint(least, 3))]
    if tool == 'acknowledge':
        return {'assumptions': texts(1)}
    if tool == 'ask':
        args = {'question': rng.choice(WORDS)}
        if rng.random() < 0.5:
            args['fencing_token'] = {'epoch': 'made-up', 'counter': 99}
        return args
    if tool == 'report':
        return {'criteria': [{'ac': 'AC%d' % rng.randint(1, 20), 'text': rng.choice(WORDS)}
                             for _ in range(rng.randint(1, 3))], 'notes': rng.choice(['', 'n'])}
    args = {k: texts(0) for k in LISTS}
    args['done'] = texts(1)
    return args


class TASK079AnyArguments(unittest.TestCase):
    def test_the_claim_tools_over_arbitrary_arguments(self):
        """TASK-079 AC1 and TASK-079 AC3: over 400 seeded inputs to the four claim tools, one case in three of the
        header's shape and the others arbitrary, the answer is a records object or an error word of section 8; an
        invalid_input answer calls no writer function; every append carries the store's token and the record's
        recorder, never a value of the input; appends happen over the run (the property is not empty)."""
        rng = random.Random(79)
        live = writer.StoreResult('done', 'rows', value={'ended': False, 'leases': [
            lease('TASK-9', T0 + datetime.timedelta(hours=1), 5)]})
        appended = writer.WriteResult(type('A', (), {'result': 'appended', 'reason': None, 'seq': 1, 'line': None,
                                                     'findings': ()})())
        appends = 0
        for case in range(400):
            tool = rng.choice(['acknowledge', 'ask', 'report', 'handoff'])
            if case % 3 == 0:
                args = valid_call(rng, tool)
            elif rng.random() < 0.1:
                args = rng.choice(VALUES)
            else:
                args = {k: rng.choice(VALUES) for k in rng.sample(KEYS, rng.randint(0, 4))}
            calls = []
            with mock.patch.object(writer, 'session_leases', side_effect=lambda *a: calls.append('l') or live), \
                    mock.patch.object(writer, 'read_log', side_effect=lambda *a: calls.append('r') or b''), \
                    mock.patch.object(writer, 'append_event',
                                      side_effect=lambda *a, **k: calls.append(('a', a, k)) or appended):
                obj, word = mcp_server.claim(tool, args, ENV, T0)
            appends += len([c for c in calls if isinstance(c, tuple)])
            with self.subTest(case=case, tool=tool, args=args):
                if word is None:
                    self.assertEqual(set(obj), {'records'})
                    self.assertTrue(obj['records'])
                else:
                    self.assertIn(word, mcp_server.ERRORS)
                if word == 'invalid_input':
                    self.assertEqual(calls, [])
                for c in calls:
                    if isinstance(c, tuple):
                        self.assertEqual(c[2], {'task_id': 'TASK-9', 'fencing_token': {'epoch': 'e', 'counter': 5}})
                        self.assertEqual(c[1][5], c[1][2]['recorder'])
        self.assertGreater(appends, 0)


if __name__ == '__main__':
    unittest.main()
