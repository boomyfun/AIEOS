"""Property tests of aieos_bootstrap.claude_code_reads (task TASK-065, AC9's property test), standard library only,
with fixed seeds: over generated hook inputs, the result has exactly the four keys, read_paths is empty unless the
result is "read", a "read" result's list is exactly [file_path], and equal inputs give equal results. No file is
written. Each test names its criteria in its own docstring."""

import json
import random
import unittest

from aieos_bootstrap import claude_code_reads as cr

TOOLS = ['Read', 'Grep', 'Glob', 'Bash', 'PowerShell', 'Write', 'Edit', 'Task', 'Agent', 'mcp__x__y', 'read', 'Other']
CHARS = 'abcXYZ019 _-./\\:é'


def text(rng, n=12):
    return ''.join(rng.choice(CHARS) for _ in range(rng.randint(0, n)))


def gen(rng):
    inp = {}
    if rng.random() < 0.85:
        inp['file_path'] = rng.choice([text(rng), text(rng), 7, None, ''])
    if rng.random() < 0.3:
        inp['offset'] = rng.randint(0, 9)
    if rng.random() < 0.3:
        inp['limit'] = rng.randint(1, 9)
    d = {}
    if rng.random() < 0.95:
        d['tool_name'] = rng.choice(TOOLS + [3])
    if rng.random() < 0.95:
        d['tool_input'] = inp if rng.random() < 0.9 else [inp]
    for k in ('hook_event_name', 'session_id', 'cwd', 'tool_response'):
        if rng.random() < 0.5:
            d[k] = text(rng)
    data = json.dumps(d).encode('utf-8')
    if rng.random() < 0.05:
        data = data[:rng.randint(0, len(data))]
    return d, data


class Properties(unittest.TestCase):
    def test_result_form(self):
        """TASK-065 AC9: the result has exactly the four keys, and read_paths is empty unless the result is "read"."""
        rng = random.Random(6501)
        for _ in range(3000):
            _, data = gen(rng)
            r = cr.read_paths(data)
            self.assertEqual(sorted(r), sorted(cr.RESULT_KEYS))
            self.assertIn(r['result'], ('read', 'uncovered'))
            if r['result'] != 'read':
                self.assertEqual(r['read_paths'], [])

    def test_read_is_exactly_the_path(self):
        """TASK-065 AC9: a "read" result's list is exactly [file_path], for tool_name "Read" and a non-empty string."""
        rng = random.Random(6502)
        for _ in range(3000):
            d, data = gen(rng)
            r = cr.read_paths(data)
            fp = d.get('tool_input', {}).get('file_path') if isinstance(d.get('tool_input'), dict) else None
            good = d.get('tool_name') == 'Read' and isinstance(fp, str) and fp != ''
            if r['result'] == 'read':
                self.assertEqual(r['read_paths'], [fp])
                self.assertTrue(good)
            elif good:
                # only a cut-short input (the generator's truncation) keeps a well-formed Read from "read"
                self.assertIn(r['reason'], ('input_json', 'input_bytes'))

    def test_deterministic(self):
        """TASK-065 AC9: equal inputs give equal results."""
        rng = random.Random(6503)
        for _ in range(1000):
            _, data = gen(rng)
            self.assertEqual(cr.read_paths(data), cr.read_paths(bytes(data)))


if __name__ == '__main__':
    unittest.main()
