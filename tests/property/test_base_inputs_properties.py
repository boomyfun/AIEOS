"""Property tests of aieos_bootstrap.base_inputs (TASK-082 AC10): over seeded random contracts written in the subset,
the reader gives back the value written; over seeded random byte changes of a contract text it never raises and gives
findings or a value; over seeded random logs the approval and the resume record taken are the last non-duplicate ones
of the task. Each test names its criteria in its own docstring."""

import datetime
import json
import random
import unittest

from aieos_bootstrap import base_inputs, eventlog, records

NOW = datetime.datetime(2026, 10, 24, 12, 0, 0, tzinfo=datetime.timezone.utc)
WORDS = ['alpha', 'beta', 'gamma', 'd-e', 'f_g', 'h.i', 'j/k', 'TASK-7', 'v1', '600k', '2', 'false', 'x#y']
KEYS = ['a', 'b_c', 'd-e', 'f.g', 'h/i', 'k9']


def scalar(rng):
    return ' '.join(rng.choice(WORDS) for _ in range(rng.randint(1, 3)))


def write_value(rng, indent, depth):
    """(the text after "key:", the value) in a form of the subset."""
    pad = ' ' * indent
    kind = rng.randrange(6 if depth < 3 else 3)
    if kind == 0:
        v = scalar(rng)
        return ' ' + v, v
    if kind == 1:
        items = [scalar(rng) for _ in range(rng.randint(0, 3))]
        return ' [' + ', '.join(items) + ']', items
    if kind == 2:
        lines = [scalar(rng) for _ in range(rng.randint(1, 3))]
        return ' >-\n' + ''.join(pad + '  ' + line + '\n' for line in lines)[:-1], ' '.join(lines)
    if kind == 3:
        items = [scalar(rng) for _ in range(rng.randint(1, 3))]
        return '\n' + ''.join(pad + '  - ' + i + '\n' for i in items)[:-1], items
    if kind == 4:
        keys = rng.sample(KEYS, rng.randint(1, 3))
        m = {k: scalar(rng) for k in keys}
        return ' {' + ', '.join('%s: %s' % (k, m[k]) for k in keys) + '}', m
    keys = rng.sample(KEYS, rng.randint(1, 3))
    text, value = '', {}
    for k in keys:
        t, v = write_value(rng, indent + 2, depth + 1)
        text += '\n' + pad + '  ' + k + ':' + t
        value[k] = v
    return text, value


def write_map(rng):
    keys = rng.sample(KEYS, rng.randint(1, len(KEYS)))
    text, value = '', {}
    for k in keys:
        t, v = write_value(rng, 0, 0)
        text += k + ':' + t + '\n'
        value[k] = v
    return text, value


class TASK082AC10Properties(unittest.TestCase):
    def test_round_trip(self):
        """TASK-082 AC10: a random contract written in the subset is read back as written."""
        rng = random.Random(82)
        for _ in range(300):
            text, value = write_map(rng)
            self.assertEqual(base_inputs._parse_contract_text(text), value, text)

    def test_changed_bytes(self):
        """TASK-082 AC10: a random byte change of a contract text never raises; it gives findings or a value."""
        rng = random.Random(8200)
        for _ in range(300):
            text, _ = write_map(rng)
            data = bytearray(text.encode('utf-8'))
            data[rng.randrange(len(data))] = rng.randrange(32, 127)
            try:
                base_inputs._parse_contract_text(data.decode('utf-8', 'replace'))
            except base_inputs._Stop as s:
                self.assertTrue(s.findings)

    def test_last_of_the_task(self):
        """TASK-082 AC10: over random logs, the approval and the record taken are the task's last non-duplicate ones,
        the record after the approval; a duplicate repeats a random earlier line, so it can stand after a later
        approval or record of the task."""
        rng = random.Random(8201)
        moved = 0
        for n in range(100):
            data, lines = b'', []
            for k in range(rng.randint(1, 8)):
                task = rng.choice(['TASK-1', 'TASK-2'])
                if rng.random() < 0.5:
                    kind, payload = 'task.approved', {'contract_version': 'v1', 'contract_hash': '%064x' % k,
                                                      'approval_record': 'a%d' % k}
                else:
                    kind, payload = 'decision.execution', {
                        'record_id': 'r%d' % k, 'fact_kind': 'interpretation', 'source_class': 'deterministic_tool_local',
                        'recorder': 'test', 'subject': task, 'decision': 'CONTINUE', 'uncovered': [], 'state_effect': []}
                r = eventlog.append(data, kind, payload, 'e%d' % k, NOW, task_id=task)
                self.assertEqual(r.result, 'appended', r.findings)
                data += r.line
                lines.append((task, kind, payload, r.line))
                if rng.random() < 0.4:
                    i = rng.randrange(len(lines))
                    moved += i < len(lines) - 1
                    obj = json.loads(lines[i][3])
                    obj['seq'] = data.count(b'\n') + 1
                    data += json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8') + b'\n'
            mine = [(kind, p) for t, kind, p, _ in lines if t == 'TASK-1']
            try:
                approval, record = base_inputs._approval_and_record(base_inputs._log_events(data, 'TASK-1'), 'TASK-1')
            except base_inputs._Stop:
                approved = [i for i, (k, _) in enumerate(mine) if k == 'task.approved']
                execs = [i for i, (k, _) in enumerate(mine) if k == 'decision.execution']
                self.assertTrue(not approved or not execs or execs[-1] < approved[-1])
                continue
            self.assertEqual(approval, [p for k, p in mine if k == 'task.approved'][-1])
            self.assertEqual(record, [p for k, p in mine if k == 'decision.execution'][-1])
            self.assertFalse(records.check_log(data).findings())
        self.assertGreater(moved, 0)

    def test_naming(self):
        """TASK-082 AC11: every test of this module names "TASK-082 ACn" at the start of its docstring."""
        for name in unittest.TestLoader().getTestCaseNames(TASK082AC10Properties):
            self.assertRegex(getattr(TASK082AC10Properties, name).__doc__ or '', r'^TASK-082 AC\d+', name)


if __name__ == '__main__':
    unittest.main()
