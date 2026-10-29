"""Property tests of the Risk Engine fixture of TASK-018 (docs/specs/conformance-files.md revision 7, sections 2 and 10;
docs/tasks/TASK-018.yaml AC9): the canonical form, the hash, the tests' matcher against point 6, and the properties of
the invariants the task relates to (INV-005 to INV-008). Standard library only, fixed seeds.

Files are read as bytes with pathlib's read_bytes; the fixture module is never imported or executed.
"""
import hashlib
import json
import pathlib
import random
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = 'tests/conformance/fixtures_risk/risk_01.py'
FIRST, LAST = b"DATA = r'''", b"'''\n"
ACCEPTANCE = ('ACCEPT', 'NEEDS_REVIEW', 'INSUFFICIENT_EVIDENCE', 'NEEDS_REWORK', 'REJECT')
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
    """The tests' own matcher of point 6's forms, as in the unit and integration modules."""
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
    """A second reading of point 6, by names and not by one regular expression, to check the tests' matcher. It shares three
    readings with matches (an empty '*', a zero-name middle '**', a one-name trailing '**'), which the unit module pins by cases."""
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
    """The value's JSON text with the keys of one object in another order (or None if no object has two keys)."""
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
        rng = random.Random(18001)
        base = sha256(self.data)
        for _ in range(ROUNDS):
            i = rng.randrange(len(self.data))
            b = bytearray(self.data)
            b[i] = (b[i] + rng.randrange(1, 256)) % 256
            self.assertNotEqual(sha256(bytes(b)), base)

    def test_any_one_byte_change_breaks_the_form_or_the_value(self):
        """A one-byte change either leaves the canonical form or changes the value, so the hash property is not trivial."""
        rng = random.Random(18003)
        value = json.loads(text_of(self.data))
        for _ in range(ROUNDS):
            i = rng.randrange(len(self.data))
            b = bytearray(self.data)
            b[i] = (b[i] + rng.randrange(1, 256)) % 256
            altered = bytes(b)
            self.assertTrue(not is_canonical(altered) or json.loads(text_of(altered)) != value, i)

    def test_any_reordering_of_keys_is_not_canonical(self):
        rng = random.Random(18002)
        self.assertTrue(is_canonical(self.data))
        for _ in range(60):
            self.assertFalse(is_canonical(keys_reordered(self.value, rng)))


class MatcherProperties(unittest.TestCase):

    NAMES = ('a', 'b', 'docs', 'src', 'x.md', 'a.py', 'contracts', 'CLAUDE.md', '.github', 'file.txt')
    PARTS = ('a', 'b', 'docs', 'src', '*', '*.md', '*.py', 'x*', '**', 'contracts', '.github', 'file.txt')

    def test_the_matcher_follows_point_6_for_random_paths_and_patterns(self):
        rng = random.Random(18003)
        hits = 0
        for _ in range(ROUNDS * 4):
            path = '/'.join(rng.choice(self.NAMES) for _ in range(rng.randint(1, 4)))
            parts = [rng.choice(self.PARTS) for _ in range(rng.randint(1, 4))]
            pattern = '/'.join(parts)
            want = reference(pattern, path)
            hits += want
            self.assertEqual(matches(pattern, path), want, (pattern, path))
        self.assertGreater(hits, 50)

    def test_the_fixture_path_against_random_patterns_of_the_policy_forms(self):
        rng = random.Random(18004)
        value = json.loads(text_of(read(FIXTURE)))
        for case in value['cases']:
            for rule in case['values']['risk_rules']:
                for p in rule['match']:
                    for _ in range(5):
                        path = '/'.join(rng.choice(self.NAMES) for _ in range(rng.randint(1, 3)))
                        self.assertEqual(matches(p, path), reference(p, path), (p, path))
                    for path in case['values']['changed_paths']:
                        self.assertFalse(reference(p, path), (p, path))


class InvariantProperties(unittest.TestCase):

    def setUp(self):
        self.value = json.loads(text_of(read(FIXTURE)))

    def test_inv_005_expected_fixes_no_decision_value(self):
        for case in self.value['cases']:
            self.assertIn('decision', case['expected']['not_fixed'])
            self.assertNotIn('decision', case['expected'])

    def test_inv_005_006_expected_has_only_the_risk_keys(self):
        """The expected element holds exactly risk_not, profile_excludes and not_fixed, and not_fixed names exactly the
        decision and the next state."""
        for case in self.value['cases']:
            self.assertEqual(set(case['expected']), {'risk_not', 'profile_excludes', 'not_fixed'})
            self.assertEqual(sorted(case['expected']['not_fixed']), ['decision', 'next_state'])

    def test_inv_006_no_expected_element_is_an_acceptance_value(self):
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
        for case in self.value['cases']:
            self.assertEqual([s for s in strings(case['expected']) if s in ACCEPTANCE], [])

    def test_inv_007_the_evaluated_commit_is_every_record_s_commit(self):
        for case in self.value['cases']:
            c = case['request']['evaluated_commit']
            self.assertTrue(case['records'])
            self.assertEqual({r['commit'] for r in case['records']}, {c})

    def test_inv_008_no_record_is_an_agent_s_own_declaration(self):
        for case in self.value['cases']:
            for r in case['records']:
                self.assertNotEqual(r['source_class'], 'agent_declared')
                self.assertNotEqual(r['fact_kind'], 'claim')


if __name__ == '__main__':
    unittest.main()
