"""Property tests of aieos_bootstrap.base_files (TASK-081 AC8): over seeded random trees given by a stand-in read,
list_paths and read_file agree with a reference walk in this module; over seeded random byte changes of a listing
they never raise and give either findings or the reference's value. The reference models the listing form, the name
form, duplicate names, modes and types, caching by tree id (the reads counted), MAX_ENTRIES and MAX_DEPTH (lowered in
one test) and the blob hash (blob bytes changed in that test). Each test names its criteria in its own docstring."""

import collections
import hashlib
import pathlib
import random
import re
import unittest
from unittest import mock

from aieos_bootstrap import base_files

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
NAMES = ['a', 'b', 'c.txt', 'd-e', 'F_9', 'x.y', 'zz']
LINE = re.compile(r'([0-7]+) (blob|tree|commit) ([0-9a-f]{40}|[0-9a-f]{64})\t([^/\x00-\x1f\x7f]+)')
NAME = re.compile(r'[!#-\[\]-~]+')


def gid(kind, data):
    return hashlib.sha1(b'%s %d\x00' % (kind.encode('ascii'), len(data)) + data, usedforsecurity=False).hexdigest()


class Store:
    def __init__(self):
        self.objects = {}

    def put(self, kind, data):
        oid = gid(kind, data)
        self.objects[oid] = (kind, data)
        return oid

    def __call__(self, repo, args, timeout=30):
        oid = args[-1]
        if oid not in self.objects:
            return {'exit': 128, 'out': b'', 'err': b'', 'error': None}
        if args[0] == 'rev-parse':
            out = (oid + '\n').encode('ascii')
        elif args[1] == '-t':
            out = (self.objects[oid][0] + '\n').encode('ascii')
        else:
            out = self.objects[oid][1]
        return {'exit': 0, 'out': out, 'err': b'', 'error': None}


class Counting:
    """A stand-in that passes every call to a Store and counts the cat-file -p reads of each id."""

    def __init__(self, store):
        self.store = store
        self.reads = collections.Counter()

    def __call__(self, repo, args, timeout=30):
        if args[:2] == ['cat-file', '-p']:
            self.reads[args[-1]] += 1
        return self.store(repo, args, timeout)


def make_tree(store, rng, depth):
    entries = []
    for name in rng.sample(NAMES, rng.randint(1, 3)):
        if depth > 0 and rng.random() < 0.4:
            entries.append(('040000', 'tree', make_tree(store, rng, depth - 1), name))
        else:
            mode = rng.choice(['100644', '100755'])
            entries.append((mode, 'blob', store.put('blob', ('text %d\n' % rng.randint(0, 99)).encode('ascii')), name))
    rng.shuffle(entries)
    return store.put('tree', ''.join('%s %s %s\t%s\n' % e for e in entries).encode('ascii'))


def make_commit(store, tree):
    return store.put('commit', ('tree %s\nauthor A B 1 +0000\ncommitter A B 1 +0000\n\nm\n' % tree).encode('ascii'))


def ref_listing(store, tree):
    """The entries of a tree as the reference reads them, or None."""
    if tree not in store.objects or store.objects[tree][0] not in ('tree', 'blob', 'commit'):
        return None
    try:
        text = store.objects[tree][1].decode('utf-8')
    except UnicodeDecodeError:
        return None
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]
    entries = {}
    for line in lines:
        m = LINE.fullmatch(line)
        if m is None:
            return None
        mode, kind, oid, name = m.groups()
        if NAME.fullmatch(name) is None or name in ('.', '..') or name in entries:
            return None
        entries[name] = (mode, kind, oid)
    return entries


def ref_fits(mode, kind):
    return kind == 'tree' and mode == '040000' or kind == 'blob' and mode in ('100644', '100755')


def ref_paths(store, tree, at=''):
    entries = ref_listing(store, tree)
    if entries is None:
        return None
    out = []
    for name, (mode, kind, oid) in entries.items():
        if not ref_fits(mode, kind):
            return None
        here = at + name
        if kind == 'tree':
            below = ref_paths(store, oid, here + '/')
            if below is None:
                return None
            out.extend(below)
        else:
            out.append(here)
    return sorted(out)


def ref_text(store, tree, path):
    names = path.split('/')
    for k, name in enumerate(names):
        entries = ref_listing(store, tree)
        if entries is None or name not in entries:
            return None
        mode, kind, oid = entries[name]
        if not ref_fits(mode, kind):
            return None
        if k < len(names) - 1:
            if kind != 'tree':
                return None
            tree = oid
        elif kind != 'blob' or oid not in store.objects:
            return None
    data = store.objects[oid][1]
    if gid('blob', data) != oid:
        return None
    try:
        return {'blob': oid, 'text': data.decode('utf-8')}
    except UnicodeDecodeError:
        return None


def ref_bounded(store, tree, max_entries, max_depth):
    """The reference's paths under the bounds: None when there are more than max_entries paths or a listed name lies
    more than max_depth names from the root (every tree here holds a blob below it, so the deepest name is a path's)."""
    paths = ref_paths(store, tree)
    if paths is None or len(paths) > max_entries or max(p.count('/') + 1 for p in paths) > max_depth:
        return None
    return paths


class TASK081AC8Properties(unittest.TestCase):
    def test_random_trees(self):
        """TASK-081 AC8: over seeded random trees, list_paths and read_file give the reference walk's values."""
        rng = random.Random(81)
        for _ in range(200):
            store = Store()
            tree = make_tree(store, rng, 3)
            head = make_commit(store, tree)
            expected = ref_paths(store, tree)
            self.assertEqual(base_files.list_paths(ROOT, head, '', store), (expected, None))
            for path in expected:
                self.assertEqual(base_files.read_file(ROOT, head, path, store), (ref_text(store, tree, path), None))

    def test_changed_listings(self):
        """TASK-081 AC8: over seeded random byte changes of a listing, no exception, and findings or the reference's
        value."""
        rng = random.Random(8100)
        for _ in range(300):
            store = Store()
            tree = make_tree(store, rng, 2)
            head = make_commit(store, tree)
            paths = ref_paths(store, tree)
            trees = [oid for oid, (kind, _) in store.objects.items() if kind == 'tree']
            victim = rng.choice(trees)
            data = bytearray(store.objects[victim][1])
            data[rng.randrange(len(data))] = rng.randrange(256)
            store.objects[victim] = ('tree', bytes(data))
            value, findings = base_files.list_paths(ROOT, head, '', store)
            expected = ref_paths(store, tree)
            if value is None:
                self.assertTrue(findings)
            else:
                self.assertEqual(value, expected)
            for path in paths:
                value, findings = base_files.read_file(ROOT, head, path, store)
                if value is None:
                    self.assertTrue(findings)
                else:
                    self.assertEqual(value, ref_text(store, tree, path))

    def test_bounds_and_blobs(self):
        """TASK-081 AC8: with MAX_ENTRIES and MAX_DEPTH lowered, findings exactly when the reference is over a bound;
        each tree id read at most once per call; a changed blob byte gives findings exactly when its hash fails."""
        rng = random.Random(8101)
        for _ in range(200):
            store = Store()
            counted = Counting(store)
            tree = make_tree(store, rng, 3)
            head = make_commit(store, tree)
            max_entries, max_depth = rng.randint(1, 8), rng.randint(1, 4)
            expected = ref_bounded(store, tree, max_entries, max_depth)
            with mock.patch.object(base_files, 'MAX_ENTRIES', max_entries), \
                    mock.patch.object(base_files, 'MAX_DEPTH', max_depth):
                value, findings = base_files.list_paths(ROOT, head, '', counted)
            if expected is None:
                self.assertIsNone(value)
                self.assertTrue(findings)
            else:
                self.assertEqual((value, findings), (expected, None))
            trees = {oid for oid, (kind, _) in store.objects.items() if kind == 'tree'}
            self.assertTrue(all(counted.reads[oid] <= 1 for oid in trees))
            path = rng.choice(ref_paths(store, tree))
            oid = ref_text(store, tree, path)['blob']
            data = bytearray(store.objects[oid][1])
            data[rng.randrange(len(data))] = rng.randrange(256)
            store.objects[oid] = ('blob', bytes(data))
            want = ref_text(store, tree, path)
            value, findings = base_files.read_file(ROOT, head, path, store)
            if want is None:
                self.assertIsNone(value)
                self.assertTrue(findings)
            else:
                self.assertEqual((value, findings), (want, None))

    def test_naming(self):
        """TASK-081 AC9: every test of this module names "TASK-081 ACn" at the start of its docstring."""
        for name in unittest.TestLoader().getTestCaseNames(TASK081AC8Properties):
            self.assertRegex(getattr(TASK081AC8Properties, name).__doc__ or '', r'^TASK-081 AC\d+', name)


if __name__ == '__main__':
    unittest.main()
