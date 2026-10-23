"""Property tests of aieos_bootstrap.context_compiler (TASK-080 AC8): over seeded random inputs of the contract header's
form, build_work_order returns a Work Order whose hash matches its canonical form, whose every layer fits its budget
or holds only references, whose references keep the hash of the content they replace and were taken largest first,
and whose kept contents are whole. Standard library only; no file is read or written."""

import hashlib
import json
import random
import unittest

from aieos_bootstrap import context_compiler

LAYERS = ['constitution', 'components', 'traced', 'files', 'handoff']
CASES = 300
POOL = ['src/a/x.py', 'src/a/y.py', 'src/b/z.py', 'lib/api/order.json', 'lib/api/c.py', 'docs/d.md', 'docs/e/f.md',
        'tests/t.py', 'tests/u/v.py', 'other/w.py', 'é/ü.py']
COMPONENT_PATHS = ['src', 'src/a', 'lib/api/**', 'docs/*.md', 'tests', 'other', 'src/b/*.py', 'é']
PATTERNS = ['src/a/x.py', 'src/**', 'docs/*.md', 'tests/**', 'lib/api/c.py', 'nothing/**', 'é/ü.py']
ARTICLES = ['INV-001', 'INV-002', 'GOV-002', 'SEC-001']
CHARS = 'abcé€ '


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def text(rng):
    return ''.join(rng.choice(CHARS) for _ in range(rng.randint(0, 30)))


def random_inputs(rng):
    """Well-formed inputs: unique refs, every interface naming a given component, no schema entry."""
    components = [{'id': 'c%d' % i, 'paths': rng.sample(COMPONENT_PATHS, rng.randint(1, 3)), 'tags': []}
                  for i in range(rng.randint(0, 4))]
    interfaces = [{'id': 'i%d' % i, 'component': c['id']} for i, c in enumerate(components) if rng.random() < 0.6]
    traces = ['spec#%d' % i for i in range(rng.randint(0, 3))] + ['ADR-%03d' % i for i in range(rng.randint(0, 2))]
    adrs = {t: text(rng) for t in traces if t.startswith('ADR-')}
    applicable = rng.sample(ARTICLES, rng.randint(0, len(ARTICLES)))
    contract = {'task': 'TASK-900', 'contract_version': 'v3', 'traces_to': traces,
                'write_set': {'paths': rng.sample(PATTERNS, rng.randint(0, 3))},
                'read_set': {'paths': rng.sample(PATTERNS, rng.randint(0, 3)),
                             'interfaces': [i['id'] for i in interfaces if rng.random() < 0.5]},
                'acceptance_criteria': [{'AC%d' % n: text(rng)} for n in range(1, rng.randint(1, 4))]}
    small = rng.random() < 0.7
    return {
        'task': 'TASK-900', 'session_id': 's.%d' % rng.randint(0, 99), 'base': '%040x' % rng.getrandbits(160),
        'contract': contract, 'contract_hash': 'f' * 64,
        'resume_record': {'decision': rng.choice(['CONTINUE', 'CONTINUE_WITH']), 'subject': 'TASK-900',
                          'contract_hash': 'f' * 64, 'contract_version': 'v3',
                          'constitution': {'applicable': applicable, 'violated': [], 'no_result': []}},
        'articles': {a: text(rng) for a in applicable},
        'components': components, 'interfaces': interfaces,
        'adrs': adrs, 'traced': {t: text(rng) for t in traces if t not in adrs},
        'files': {p: text(rng) for p in POOL if rng.random() < 0.7},
        'derived_read_set': rng.sample(POOL + ['missing/m.py'], rng.randint(0, 3)),
        'last_handoff': {'ref': 'handoffs/h.md', 'text': text(rng)} if rng.random() < 0.5 else None,
        'budgets': {n: rng.randint(1, 40) if small else 10 ** 6 for n in LAYERS}}


def originals(inp):
    """Every content the inputs can give, by layer name and ref, in the module's stated forms."""
    owner = {i['id']: i['component'] for i in inp['interfaces']}
    c = inp['contract']
    traced = dict(inp['traced'])
    traced.update({k: v for a in c['acceptance_criteria'] for k, v in a.items()})
    traced.update({'adr:' + k: v for k, v in inp['adrs'].items()})
    components = {'component:' + x['id']: json.dumps({'component': x, 'interfaces': sorted(
        i for i, o in owner.items() if o == x['id'])}, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        for x in inp['components']}
    handoff = {inp['last_handoff']['ref']: inp['last_handoff']['text']} if inp['last_handoff'] else {}
    return {'constitution': inp['articles'], 'components': components, 'traced': traced, 'files': inp['files'],
            'handoff': handoff}


class TASK080AC8Properties(unittest.TestCase):
    def test_hash_budget_and_references(self):
        """TASK-080 AC8: over seeded random inputs, the hash matches the canonical form, every layer fits its budget
        or holds only references, references keep the replaced content's hash and were the largest, kept contents are
        whole; some cases make references and some keep everything."""
        rng = random.Random(80)
        with_refs = kept_all = 0
        for _ in range(CASES):
            inp = random_inputs(rng)
            wo, findings = context_compiler.build_work_order(inp)
            self.assertIsNone(findings, findings)
            rest = {k: v for k, v in wo.items() if k != 'work_order_hash'}
            self.assertEqual(wo['work_order_hash'], hashlib.sha256(canonical(rest)).hexdigest())
            source = originals(inp)
            any_ref = False
            for x in wo['layers']:
                items = x['items']
                kept = [i for i in items if 'content' in i]
                dropped = [i for i in items if 'content' not in i]
                used = sum(len(i['content'].encode('utf-8')) for i in kept)
                self.assertTrue(used <= inp['budgets'][x['name']] or not kept)
                for i in items:
                    full = source[x['name']][i['ref']]
                    self.assertEqual(i['hash'], sha(full))
                    if 'content' in i:
                        self.assertEqual(i['content'], full)
                    else:
                        self.assertEqual(set(i), {'ref', 'hash'})
                if kept and dropped:
                    smallest_dropped = min(len(source[x['name']][i['ref']].encode('utf-8')) for i in dropped)
                    largest_kept = max(len(i['content'].encode('utf-8')) for i in kept)
                    self.assertGreaterEqual(smallest_dropped, largest_kept)
                any_ref = any_ref or bool(dropped)
            with_refs += any_ref
            kept_all += not any_ref
        self.assertGreater(with_refs, 0)
        self.assertGreater(kept_all, 0)

    def test_same_inputs_same_bytes(self):
        """TASK-080 AC8: over seeded random inputs, the same inputs give the same bytes and the inputs are unchanged."""
        rng = random.Random(81)
        for _ in range(CASES // 3):
            inp = random_inputs(rng)
            before = json.dumps(inp, sort_keys=True)
            a = context_compiler.build_work_order(inp)[0]
            b = context_compiler.build_work_order(json.loads(before))[0]
            self.assertEqual(canonical(a), canonical(b))
            self.assertEqual(json.dumps(inp, sort_keys=True), before)


if __name__ == '__main__':
    unittest.main()
