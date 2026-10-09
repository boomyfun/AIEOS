"""Property tests of the Resume Check fixtures of TASK-005 (docs/specs/conformance-files.md revision 4, sections 2 and
9; docs/tasks/TASK-005.yaml AC8). Standard library only, fixed seeds.

Files are read as bytes with pathlib; no fixture module is ever imported or executed.
"""
import hashlib
import json
import pathlib
import random
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE_DIR = 'tests/conformance/fixtures_rc'
FIRST, LAST = b"DATA = r'''", b"'''\n"
EXECUTION = ('CONTINUE', 'CONTINUE_WITH', 'REPLAN', 'BLOCKED', 'ESCALATE', 'STOP: violation', 'STOP: scope invalid',
             'STOP: runtime insufficient')
# The acceptance values of concept lines 299-303; TASK-005's AC8 list is read as these five (decision D-269).
ACCEPTANCE = ('ACCEPT', 'NEEDS_REVIEW', 'INSUFFICIENT_EVIDENCE', 'NEEDS_REWORK', 'REJECT')
SEEDS = (1, 2, 3, 5, 8)


def canon(value, indent=0):
    pad = ' ' * (indent + 2)
    if isinstance(value, dict):
        if not value:
            return '{}'
        return '{\n' + ',\n'.join(pad + canon(k) + ': ' + canon(value[k], indent + 2) for k in sorted(value)) + '\n' + ' ' * indent + '}'
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
    out = []
    for ch in value:
        out.append('\\' + ch if ch in '"\\' else '\\u%04x' % ord(ch) if ord(ch) < 0x20 else ch)
    return '"' + ''.join(out) + '"'


def unwrap(data):
    """The JSON value, only if the file is the two fixed parts around a canonical JSON text (section 2)."""
    if not data.startswith(FIRST) or not data.endswith(LAST):
        raise ValueError('fixed parts')
    text = data[len(FIRST):len(data) - len(LAST)].decode('utf-8')
    value = json.loads(text)
    if canon(value) + '\n' != text:
        raise ValueError('not canonical')
    return value


def files():
    return {p.name: p.read_bytes() for p in sorted((ROOT / FIXTURE_DIR).iterdir()) if p.is_file()}


def keys_anywhere(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from keys_anywhere(v)
    elif isinstance(value, list):
        for v in value:
            yield from keys_anywhere(v)


def noncanonical(value, rng):
    """A JSON text of the same value with the keys of one object in another order."""
    text = json.dumps(value, indent=2, sort_keys=False)
    obj = json.loads(text)
    keys = list(obj)
    rng.shuffle(keys)
    if keys == sorted(keys):
        keys = list(reversed(sorted(keys)))
    return json.dumps({k: obj[k] for k in keys}, indent=2, ensure_ascii=False)


class FileProperties(unittest.TestCase):

    def test_reserialising_is_idempotent(self):
        for name, data in files().items():
            v = unwrap(data)
            once = canon(v)
            self.assertEqual(canon(json.loads(once)), once, name)
            self.assertEqual(FIRST + (once + '\n').encode('utf-8') + LAST, data, name)

    def test_any_one_byte_change_changes_the_hash_and_breaks_the_file(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for name, data in files().items():
                i = rng.randrange(len(data))
                b = bytearray(data)
                b[i] = (b[i] + 1 + rng.randrange(254)) % 256
                altered = bytes(b)
                self.assertNotEqual(hashlib.sha256(altered).hexdigest(), hashlib.sha256(data).hexdigest())
                try:
                    v = unwrap(altered)
                except (ValueError, UnicodeDecodeError):
                    continue
                self.assertNotEqual(v, unwrap(data), (name, seed, i))

    def test_a_reordering_of_keys_is_not_canonical(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for name, data in files().items():
                text = noncanonical(unwrap(data), rng)
                with self.assertRaises(ValueError, msg=(name, seed)):
                    unwrap(FIRST + (text + '\n').encode('utf-8') + LAST)

    def test_the_same_input_gives_the_same_result(self):
        for name, data in files().items():
            self.assertEqual(unwrap(data), unwrap(bytes(data)), name)
            self.assertEqual(canon(unwrap(data)), canon(unwrap(data)), name)


class InvariantProperties(unittest.TestCase):

    def test_inv_005_each_expected_decision_is_exactly_one_a15_value(self):
        for name, data in files().items():
            for case in unwrap(data)['cases']:
                d = case['expected']['decision']
                self.assertEqual(len(d), 1, name)
                self.assertIn(d[0], EXECUTION, name)

    def test_inv_006_no_expected_decision_is_an_acceptance_value(self):
        for name, data in files().items():
            for case in unwrap(data)['cases']:
                self.assertFalse(set(case['expected']['decision']) & set(ACCEPTANCE), name)

    def test_inv_007_inputs_are_bound_to_a_commit_and_intent_versions(self):
        by_id = {}
        for name, data in files().items():
            v = unwrap(data)
            st = v['cases'][0]['inputs']['contract']['input_state']
            self.assertTrue(st['base_commit'] and st['intent_versions'], name)
            by_id[v['scenario']] = v
        rc06 = by_id['RC-06']['cases'][0]
        st = rc06['inputs']['contract']['input_state']
        self.assertNotEqual(rc06['inputs']['intent_current'], st['intent_versions'])
        self.assertEqual(rc06['expected']['decision'], ['REPLAN'])

    def test_inv_008_no_input_holds_a_record_or_a_source_class(self):
        for name, data in files().items():
            keys = set(keys_anywhere(unwrap(data)['cases'][0]['inputs']))
            self.assertFalse(keys & {'records', 'record_id', 'source_class', 'fact_kind'}, name)


if __name__ == '__main__':
    unittest.main()
