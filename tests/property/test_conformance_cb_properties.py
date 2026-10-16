"""Property tests of the Capability Boundaries fixture of TASK-057 (docs/specs/conformance-files.md revision 10, sections
2 and 11; docs/tasks/TASK-057.yaml AC10): the canonical form, the hash, the tests' matcher against point 6, and the
properties of the invariants the task relates to (INV-005 to INV-008). Standard library only, fixed seeds.

Files are read as bytes with pathlib's read_bytes; the fixture module is never imported or executed, and the core is
never run (decision D-1086).
"""
import hashlib
import json
import pathlib
import random
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = 'tests/conformance/fixtures_cb/adv_02.py'
FIRST, LAST = b"DATA = r'''", b"'''\n"
ACCEPTANCE = ('ACCEPT', 'NEEDS_REVIEW', 'INSUFFICIENT_EVIDENCE', 'NEEDS_REWORK', 'REJECT')
STATES = ('DRAFT', 'READY', 'IN_PROGRESS', 'VERIFYING', 'ACCEPTED', 'DONE', 'IN_REVIEW', 'REWORK', 'ESCALATED',
          'REJECTED', 'BLOCKED', 'STALE')
ROUNDS = 300


def read(path):
    return (ROOT / path).read_bytes()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canon(value, indent=0):
    """The canonical JSON text of one value (section 2), without the final LF."""
    pad = ' ' * (indent + 2)
    if isinstance(value, dict):
        if not value:
            return '{}'
        items = (pad + canon(k) + ': ' + canon(value[k], indent + 2) for k in sorted(value))
        return '{\n' + ',\n'.join(items) + '\n' + ' ' * indent + '}'
    if isinstance(value, list):
        if not value:
            return '[]'
        return '[\n' + ',\n'.join(pad + canon(x, indent + 2) for x in value) + '\n' + ' ' * indent + ']'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if value is None:
        return 'null'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        out = []
        for ch in value:
            if ch in '"\\':
                out.append('\\' + ch)
            elif ord(ch) < 0x20:
                out.append('\\u%04x' % ord(ch))
            else:
                out.append(ch)
        return '"' + ''.join(out) + '"'
    raise ValueError('a value of type %s has no canonical form' % type(value).__name__)


def text_of(data):
    return data[len(FIRST):len(data) - len(LAST)].decode('utf-8')


def is_canonical(data):
    if not data.startswith(FIRST) or not data.endswith(LAST):
        return False
    try:
        value = json.loads(text_of(data))
    except ValueError:
        return False
    return canon(value) + '\n' == text_of(data)


def matches(pattern, path):
    """The tests' own matcher of point 6's forms, as in the unit module."""
    if '/' not in pattern:
        pattern = '**/' + pattern
    parts = pattern.split('/')
    rx = ''
    for i, part in enumerate(parts):
        last = i == len(parts) - 1
        if part == '**':
            rx += '[^/]+(?:/[^/]+)*' if last else '(?:[^/]+/)*'
        else:
            rx += ''.join('[^/]*' if c == '*' else re.escape(c) for c in part) + ('' if last else '/')
    return re.fullmatch(rx, path) is not None


def reference(pattern, path):
    """A second reading of point 6, by names and not by one regular expression, to check the tests' matcher."""
    if '/' not in pattern:
        pattern = '**/' + pattern
    parts, names = pattern.split('/'), path.split('/')

    def name_ok(p, n):
        if not p:
            return not n
        if p[0] == '*':
            return any(name_ok(p[1:], n[k:]) for k in range(len(n) + 1))
        return bool(n) and p[0] == n[0] and name_ok(p[1:], n[1:])

    def step(i, j):
        if i == len(parts):
            return j == len(names)
        if parts[i] == '**':
            if i == len(parts) - 1:
                return j < len(names)
            return any(step(i + 1, k) for k in range(j, len(names) + 1))
        return j < len(names) and name_ok(parts[i], names[j]) and step(i + 1, j + 1)

    return step(0, 0)


def keys_reordered(value, rng):
    """The value's JSON text with the keys of one object in another order."""
    objs = []

    def walk(v):
        if isinstance(v, dict):
            if len(v) > 1:
                objs.append(v)
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(value)
    target = rng.choice(objs)
    keys = sorted(target)
    while keys == sorted(target):
        rng.shuffle(keys)

    def dump(v, indent=0):
        pad = ' ' * (indent + 2)
        if isinstance(v, dict):
            if not v:
                return '{}'
            order = keys if v is target else sorted(v)
            return '{\n' + ',\n'.join(pad + json.dumps(k) + ': ' + dump(v[k], indent + 2) for k in order) + '\n' + ' ' * indent + '}'
        if isinstance(v, list):
            if not v:
                return '[]'
            return '[\n' + ',\n'.join(pad + dump(x, indent + 2) for x in v) + '\n' + ' ' * indent + ']'
        return canon(v)
    return FIRST + (dump(value) + '\n').encode('utf-8') + LAST


def strings(v):
    if isinstance(v, dict):
        for k, x in v.items():
            yield k
            yield from strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from strings(x)
    elif isinstance(v, str):
        yield v


class CanonicalFormProperties(unittest.TestCase):

    def setUp(self):
        self.data = read(FIXTURE)
        self.value = json.loads(text_of(self.data))

    def test_reserialising_is_idempotent(self):
        once = FIRST + (canon(self.value) + '\n').encode('utf-8') + LAST
        twice = FIRST + (canon(json.loads(text_of(once))) + '\n').encode('utf-8') + LAST
        self.assertEqual(once, self.data)
        self.assertEqual(twice, once)

    def test_any_one_byte_change_changes_the_hash(self):
        rng = random.Random(57001)
        base = sha256(self.data)
        for _ in range(ROUNDS):
            i = rng.randrange(len(self.data))
            b = bytearray(self.data)
            b[i] = (b[i] + rng.randrange(1, 256)) % 256
            self.assertNotEqual(sha256(bytes(b)), base)

    def test_any_reordering_of_keys_is_not_canonical(self):
        rng = random.Random(57002)
        self.assertTrue(is_canonical(self.data))
        for _ in range(60):
            self.assertFalse(is_canonical(keys_reordered(self.value, rng)))


class MatcherProperties(unittest.TestCase):

    NAMES = ('a', 'b', 'docs', 'notes', 'src', 'x.md', 'outside.py', 'a.py', '.github', 'file.txt')
    PARTS = ('a', 'b', 'docs', 'notes', 'src', '*', '*.md', '*.py', 'x*', '**', 'outside.py', '.github')

    def test_the_matcher_follows_point_6_for_random_paths_and_patterns(self):
        rng = random.Random(57003)
        hits = 0
        for _ in range(ROUNDS * 4):
            path = '/'.join(rng.choice(self.NAMES) for _ in range(rng.randint(1, 4)))
            pattern = '/'.join(rng.choice(self.PARTS) for _ in range(rng.randint(1, 4)))
            want = reference(pattern, path)
            hits += want
            self.assertEqual(matches(pattern, path), want, (pattern, path))
        self.assertGreater(hits, 50)

    def test_the_fixture_patterns_against_random_paths(self):
        rng = random.Random(57004)
        case = json.loads(text_of(read(FIXTURE)))['cases'][0]
        patterns = list(case['given']['write_set']) + [p for r in case['evaluation']['values']['risk_rules'] for p in r['match']]
        for p in patterns:
            for _ in range(20):
                path = '/'.join(rng.choice(self.NAMES) for _ in range(rng.randint(1, 3)))
                self.assertEqual(matches(p, path), reference(p, path), (p, path))
        for p in case['given']['write_set']:
            self.assertFalse(reference(p, case['given']['outside_path']), p)


class InvariantProperties(unittest.TestCase):

    def setUp(self):
        self.value = json.loads(text_of(read(FIXTURE)))
        self.case = self.value['cases'][0]

    def test_inv_005_expected_fixes_only_reject_and_rejected(self):
        exp = self.case['expected']
        self.assertEqual(exp['decision'], ['REJECT'])
        self.assertEqual(exp['next_state'], ['REJECTED'])
        self.assertEqual([s for s in strings(exp) if s in STATES], ['REJECTED'])

    def test_inv_006_no_expected_element_is_another_acceptance_value(self):
        self.assertEqual([s for s in strings(self.case['expected']) if s in ACCEPTANCE], ['REJECT'])

    def test_inv_007_the_submitted_commit_is_every_extra_record_s_commit(self):
        cid = self.case['continuation']['submission']['commit_id']
        recs = self.case['evaluation']['extra_records']
        self.assertTrue(recs)
        self.assertEqual({r['commit'] for r in recs}, {cid})

    def test_inv_008_no_extra_record_is_an_agent_s_own_declaration(self):
        for r in self.case['evaluation']['extra_records']:
            self.assertNotEqual(r['source_class'], 'agent_declared')
            self.assertNotEqual(r['fact_kind'], 'claim')
        self.assertNotEqual(self.case['document']['violation']['observation']['source_class'], 'agent_declared')


if __name__ == '__main__':
    unittest.main()
