"""Unit tests of aieos_bootstrap.base_files (TASK-081): the inputs, read_file's commit checks and walk, list_paths, the
read calls, purity, what the module may touch, its docstring and this module's own naming rule. Every Git answer
comes from a stand-in read; no test here runs Git, reads or writes a store or a temporary folder; the source is read
with pathlib's read_bytes."""

import ast
import hashlib
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import base_files, conformance, gitread

HERE = pathlib.Path(__file__).resolve()
ROOT = str(HERE.parents[2])
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap' / 'base_files.py'


def gid(kind, data, long=False):
    full = b'%s %d\x00' % (kind.encode('ascii'), len(data)) + data
    if long:
        return hashlib.sha256(full).hexdigest()
    return hashlib.sha1(full, usedforsecurity=False).hexdigest()


def ok(out):
    return {'exit': 0, 'out': out, 'err': b'', 'error': None}


def failed(code):
    return {'exit': code, 'out': b'', 'err': b'fatal', 'error': None}


class Git:
    """A stand-in for gitread.run over objects held in memory: ids are Git's own hashes of the objects."""

    def __init__(self, long=False):
        self.long = long
        self.objects = {}
        self.calls = []
        self.override = {}

    def put(self, kind, data):
        oid = gid(kind, data, self.long)
        self.objects[oid] = (kind, data)
        return oid

    def blob(self, data):
        return self.put('blob', data.encode('utf-8') if isinstance(data, str) else data)

    def tree(self, entries):
        return self.put('tree', ''.join('%s %s %s\t%s\n' % e for e in entries).encode('utf-8'))

    def raw_tree(self, data):
        oid = gid('tree', data, self.long)
        self.objects[oid] = ('tree', data)
        return oid

    def commit(self, tree):
        text = 'tree %s\nauthor A B 1 +0000\ncommitter A B 1 +0000\n\nm\n' % tree
        return self.put('commit', text.encode('ascii'))

    def __call__(self, repo, args, timeout=30):
        self.calls.append((repo, list(args), timeout))
        key = tuple(args)
        if key in self.override:
            return self.override[key]
        oid = args[-1]
        if args[0] == 'rev-parse':
            return ok((oid + '\n').encode('ascii')) if oid in self.objects else failed(128)
        if args[:2] == ['cat-file', '-t'] and oid in self.objects:
            return ok((self.objects[oid][0] + '\n').encode('ascii'))
        if args[:2] == ['cat-file', '-p'] and oid in self.objects:
            return ok(self.objects[oid][1])
        return failed(128)

    def reads_of(self, oid):
        return sum(1 for _, a, _ in self.calls if a == ['cat-file', '-p', oid])


def sample(long=False):
    """A commit whose root lists a.txt, dir and b.sh, in that (unsorted) order, and dir lists c.txt."""
    g = Git(long)
    a, b, c = g.blob('alpha\n'), g.blob('beta\n'), g.blob('gamma\n')
    sub = g.tree([('100644', 'blob', c, 'c.txt')])
    root = g.tree([('100644', 'blob', a, 'a.txt'), ('040000', 'tree', sub, 'dir'), ('100755', 'blob', b, 'b.sh')])
    g.ids = {'a': a, 'b': b, 'c': c, 'sub': sub, 'root': root}
    return g, g.commit(root)


def with_root(entries, long=False):
    """A commit whose root holds the given entries plus a.txt, and the stand-in."""
    g = Git(long)
    a = g.blob('alpha\n')
    root = g.tree([('100644', 'blob', a, 'a.txt')] + entries(g))
    return g, g.commit(root)


class Base(unittest.TestCase):
    def refused(self, result):
        value, findings = result
        self.assertIsNone(value)
        self.assertIsInstance(findings, list)
        self.assertTrue(findings)
        self.assertTrue(all(isinstance(f, str) for f in findings))
        return findings


class TASK081AC1Inputs(Base):
    def test_commit_forms(self):
        """TASK-081 AC1: a commit not 40 or 64 lowercase hex characters gives findings with zero read calls."""
        for commit in ['', 'x', 'a' * 39, 'A' * 40, 'a' * 41, 'g' * 40, 'a' * 63, 5, None, b'a' * 40]:
            g, _ = sample()
            self.refused(base_files.read_file(ROOT, commit, 'a.txt', g))
            self.refused(base_files.list_paths(ROOT, commit, '', g))
            self.assertEqual(g.calls, [], commit)

    def test_path_forms(self):
        """TASK-081 AC1: a path or prefix out of form gives findings with zero read calls."""
        bad = ['a//b', './a', 'a/.', '..', 'a/../b', 'a\\b', 'a"b', '"a"', 'a b', 'a\x01', 'a\x7f', 'a\tb', 'é',
               '/a', 'a/', '/', 'x' * 4097, '/'.join(['a'] * 65)]
        for path in bad + ['']:
            g, head = sample()
            self.refused(base_files.read_file(ROOT, head, path, g))
            self.assertEqual(g.calls, [], path)
        for prefix in bad:
            g, head = sample()
            self.refused(base_files.list_paths(ROOT, head, prefix, g))
            self.assertEqual(g.calls, [], prefix)

    def test_non_str_and_subclass(self):
        """TASK-081 AC1: a non-str argument or a str subclass gives findings with zero read calls."""
        class S(str):
            pass
        g, head = sample()
        for args in [(5, head, 'a.txt'), (S(ROOT), head, 'a.txt'), (ROOT, S(head), 'a.txt'), (ROOT, head, S('a.txt')),
                     (ROOT, head, 5), (ROOT, head, None), (None, head, 'a.txt')]:
            self.refused(base_files.read_file(*args, read=g))
        self.refused(base_files.list_paths(ROOT, head, S(''), g))
        self.assertEqual(g.calls, [])

    def test_non_callable_read(self):
        """TASK-081 AC1: a non-callable read gives findings."""
        _, head = sample()
        self.refused(base_files.read_file(ROOT, head, 'a.txt', read=5))
        self.refused(base_files.list_paths(ROOT, head, '', read='run'))

    def test_repo_refused_by_form_error(self):
        """TASK-081 AC1: a relative or missing repo is refused by gitread.form_error before any read call."""
        for repo in ['relative', ROOT + '/no-such-folder-081']:
            g, head = sample()
            findings = self.refused(base_files.read_file(repo, head, 'a.txt', g))
            self.assertIn('repo', findings[0])
            self.refused(base_files.list_paths(repo, head, '', g))
            self.assertEqual(g.calls, [])

    def test_depth_limit_counts_names(self):
        """TASK-081 AC1: a path of MAX_DEPTH names is taken, one more is refused with zero calls."""
        g, head = sample()
        self.refused(base_files.read_file(ROOT, head, '/'.join(['a'] * 64), g))
        self.assertTrue(g.calls)
        g.calls.clear()
        self.refused(base_files.read_file(ROOT, head, '/'.join(['a'] * 65), g))
        self.assertEqual(g.calls, [])


class TASK081AC2ReadFile(Base):
    def test_reads_a_file(self):
        """TASK-081 AC2: the blob id and text of a file at the commit, with SHA-1 ids."""
        g, head = sample()
        self.assertEqual(base_files.read_file(ROOT, head, 'dir/c.txt', g), ({'blob': g.ids['c'], 'text': 'gamma\n'},
                                                                           None))
        self.assertEqual(base_files.read_file(ROOT, head, 'b.sh', g)[0]['text'], 'beta\n')

    def test_reads_a_file_with_sha256_ids(self):
        """TASK-081 AC2: the same with 64-character ids, hashed with SHA-256."""
        g, head = sample(long=True)
        self.assertEqual(len(head), 64)
        self.assertEqual(base_files.read_file(ROOT, head, 'dir/c.txt', g)[0], {'blob': g.ids['c'], 'text': 'gamma\n'})

    def test_rev_parse_other_output(self):
        """TASK-081 AC2: rev-parse output other than the commit gives findings."""
        g, head = sample()
        g.override[('rev-parse', '--verify', '--end-of-options', head)] = ok(b'0' * 40 + b'\n')
        self.refused(base_files.read_file(ROOT, head, 'a.txt', g))

    def test_cat_file_t_other_than_commit(self):
        """TASK-081 AC2: cat-file -t other than commit gives findings, though cat-file -p parses as a commit."""
        for kind in [b'tag\n', b'tree\n', b'blob\n', b'commit \n']:
            g, head = sample()
            g.override[('cat-file', '-t', head)] = ok(kind)
            self.refused(base_files.read_file(ROOT, head, 'a.txt', g))

    def test_commit_out_of_form(self):
        """TASK-081 AC2: a commit object parse_commit refuses (non-UTF-8 among them) gives findings."""
        for data in [b'junk', b'tree zz\n\nm', b'\xff\xfe']:
            g, head = sample()
            g.override[('cat-file', '-p', head)] = ok(data)
            self.assertIn('out of form', self.refused(base_files.read_file(ROOT, head, 'a.txt', g))[0])

    def test_walk_refusals(self):
        """TASK-081 AC2: a missing name, a blob where a tree is due, a tree where a blob is due."""
        g, head = sample()
        for path, reason in [('none.txt', 'is missing'), ('a.txt/x', 'not a tree'), ('dir', 'not a blob'),
                             ('dir/none', 'is missing')]:
            self.assertIn(reason, self.refused(base_files.read_file(ROOT, head, path, g))[0], path)

    def test_modes_links_and_submodules(self):
        """TASK-081 AC2: a mode that does not fit its type, a symbolic link and a submodule give findings."""
        cases = [lambda g: [('100600', 'blob', g.blob('x'), 'f')], lambda g: [('120000', 'blob', g.blob('a.txt'), 'f')],
                 lambda g: [('160000', 'commit', 'c' * 40, 'f')], lambda g: [('100644', 'tree', g.tree([]), 'f')]]
        for case in cases:
            g, head = with_root(case)
            self.refused(base_files.read_file(ROOT, head, 'f', g))
        g, head = with_root(lambda g: [('100644', 'tree', g.tree([('100644', 'blob', g.blob('y'), 'y')]), 'd')])
        self.refused(base_files.read_file(ROOT, head, 'd/y', g))

    def test_listing_lines(self):
        """TASK-081 AC2: a listing line out of form and a name listed twice give findings."""
        for data in [b'garbage\n', b'100644 blob ' + b'1' * 40 + b' a.txt\n', b'100644 blob ' + b'1' * 39 + b'\ta.txt\n']:
            g = Git()
            head = g.commit(g.raw_tree(data))
            self.refused(base_files.read_file(ROOT, head, 'a.txt', g))
        g, head = with_root(lambda g: [('100644', 'blob', g.blob('other'), 'a.txt')])
        self.refused(base_files.read_file(ROOT, head, 'a.txt', g))

    def test_sibling_names_out_of_form(self):
        """TASK-081 AC2: a sibling of the walked element named out of the path-name form gives findings."""
        for name in ['"q"', 'a b', 'é', '.', '..', 'a\\b']:
            g, head = with_root(lambda g: [('100644', 'blob', g.blob('z'), name)])
            self.refused(base_files.read_file(ROOT, head, 'a.txt', g))

    def test_sizes(self):
        """TASK-081 AC2: a listing or a blob over MAX_BYTES gives findings."""
        g, head = sample()
        with mock.patch.object(base_files, 'MAX_BYTES', 5):
            self.refused(base_files.read_file(ROOT, head, 'a.txt', g))
        g = Git()
        big = g.blob('x' * 100)
        head = g.commit(g.tree([('100644', 'blob', big, 'f')]))
        with mock.patch.object(base_files, 'MAX_BYTES', 80):
            findings = self.refused(base_files.read_file(ROOT, head, 'f', g))
        self.assertIn('blob', findings[0])

    def test_blob_hash(self):
        """TASK-081 AC2: a blob whose bytes do not hash to its id gives findings, for SHA-1 and SHA-256 ids."""
        for long in (False, True):
            g, head = sample(long)
            g.override[('cat-file', '-p', g.ids['a'])] = ok(b'other\n')
            findings = self.refused(base_files.read_file(ROOT, head, 'a.txt', g))
            self.assertIn('hash', findings[0])

    def test_not_utf8(self):
        """TASK-081 AC2: a blob that is not UTF-8 gives findings."""
        g = Git()
        head = g.commit(g.tree([('100644', 'blob', g.blob(b'\xff\xfe'), 'f')]))
        self.refused(base_files.read_file(ROOT, head, 'f', g))


class TASK081AC3ListPaths(Base):
    def test_lists_sorted(self):
        """TASK-081 AC3: every blob path under the prefix, sorted though the listing is not."""
        g, head = sample()
        self.assertEqual(base_files.list_paths(ROOT, head, '', g), (['a.txt', 'b.sh', 'dir/c.txt'], None))
        self.assertEqual(base_files.list_paths(ROOT, head, 'dir', g), (['dir/c.txt'], None))
        g = Git()
        sub = g.tree([('100644', 'blob', g.blob('z'), 'z')])
        head = g.commit(g.tree([('040000', 'tree', sub, 'b'), ('100644', 'blob', g.blob('a'), 'a.txt'),
                                ('100644', 'blob', g.blob('c'), 'c')]))
        self.assertEqual(base_files.list_paths(ROOT, head, '', g), (['a.txt', 'b/z', 'c'], None))

    def test_shared_tree_read_once(self):
        """TASK-081 AC3: a tree id at two places is read once and gives its paths at both."""
        g = Git()
        sub = g.tree([('100644', 'blob', g.blob('s'), 's')])
        head = g.commit(g.tree([('040000', 'tree', sub, 'x'), ('040000', 'tree', sub, 'y')]))
        self.assertEqual(base_files.list_paths(ROOT, head, '', g), (['x/s', 'y/s'], None))
        self.assertEqual(g.reads_of(sub), 1)

    def test_prefix_refusals(self):
        """TASK-081 AC3: a prefix naming a blob or missing gives findings."""
        g, head = sample()
        for prefix in ['a.txt', 'none', 'dir/c.txt']:
            self.refused(base_files.list_paths(ROOT, head, prefix, g))

    def test_links_submodules_and_names_below(self):
        """TASK-081 AC3: a symbolic link, a submodule or a name out of form anywhere under the prefix gives findings."""
        cases = [lambda g: [('120000', 'blob', g.blob('t'), 'l')], lambda g: [('160000', 'commit', 'c' * 40, 's')],
                 lambda g: [('100644', 'blob', g.blob('q'), '"q"')], lambda g: [('100644', 'blob', g.blob('q'), 'a b')],
                 lambda g: [('040000', 'tree', g.tree([('120000', 'blob', g.blob('t'), 'deep')]), 'd')]]
        for case in cases:
            g, head = with_root(case)
            self.refused(base_files.list_paths(ROOT, head, '', g))

    def test_bounds(self):
        """TASK-081 AC3: a listing over MAX_BYTES, MAX_TOTAL_BYTES, MAX_ENTRIES and MAX_TREES give findings."""
        for name, value in [('MAX_BYTES', 10), ('MAX_TOTAL_BYTES', 100), ('MAX_ENTRIES', 2), ('MAX_TREES', 1)]:
            g, head = sample()
            with mock.patch.object(base_files, name, value):
                self.refused(base_files.list_paths(ROOT, head, '', g))
            self.assertEqual(base_files.list_paths(ROOT, head, '', g)[0], ['a.txt', 'b.sh', 'dir/c.txt'], name)

    def test_walk_stops_at_the_bound(self):
        """TASK-081 AC3: the walk stops at MAX_TREES and at MAX_ENTRIES, the reads counted."""
        g, head = sample()
        with mock.patch.object(base_files, 'MAX_TREES', 1):
            self.assertIn('MAX_TREES', self.refused(base_files.list_paths(ROOT, head, '', g))[0])
        self.assertEqual((g.reads_of(g.ids['root']), g.reads_of(g.ids['sub'])), (1, 0))
        g = Git()
        blobs = [g.blob(t) for t in ('p', 'q', 'r')]
        root = g.tree([('100644', 'blob', b, n) for b, n in zip(blobs, ('p', 'q', 'r'))])
        head = g.commit(root)
        with mock.patch.object(base_files, 'MAX_ENTRIES', 1):
            self.assertIn('MAX_ENTRIES', self.refused(base_files.list_paths(ROOT, head, '', g))[0])
        self.assertEqual(g.reads_of(root), 1)
        self.assertEqual(sum(g.reads_of(b) for b in blobs), 0)

    def test_places_bound_on_repeated_subtrees(self):
        """TASK-081 AC3: a tree of repeated subtrees with no blob stops at MAX_PLACES, each tree read once."""
        g = Git()
        t = g.tree([])
        for _ in range(30):
            t = g.tree([('040000', 'tree', t, 'a'), ('040000', 'tree', t, 'b')])
        head = g.commit(t)
        with mock.patch.object(base_files, 'MAX_PLACES', 1000):
            findings = self.refused(base_files.list_paths(ROOT, head, '', g))
        self.assertIn('MAX_PLACES', findings[0])
        self.assertLessEqual(sum(1 for _, a, _ in g.calls if a[:2] == ['cat-file', '-p']), 32)

    def test_depth_bound(self):
        """TASK-081 AC3: a path deeper than MAX_DEPTH names from the root gives findings; one of exactly MAX_DEPTH
        names is listed."""
        g = Git()
        t = g.tree([('100644', 'blob', g.blob('x'), 'f')])
        for name in ['c', 'b', 'a']:
            t = g.tree([('040000', 'tree', t, name)])
        head = g.commit(t)
        with mock.patch.object(base_files, 'MAX_DEPTH', 3):
            self.refused(base_files.list_paths(ROOT, head, '', g))
            self.refused(base_files.list_paths(ROOT, head, 'a', g))
        with mock.patch.object(base_files, 'MAX_DEPTH', 4):
            self.assertEqual(base_files.list_paths(ROOT, head, '', g), (['a/b/c/f'], None))
        self.assertEqual(base_files.list_paths(ROOT, head, 'a', g)[0], ['a/b/c/f'])


class TASK081AC4Calls(Base):
    def test_fixed_forms_and_timeout(self):
        """TASK-081 AC4: only gitread's fixed forms, each with TIMEOUT, the commit checks first."""
        g, head = sample()
        base_files.read_file(ROOT, head, 'dir/c.txt', g)
        base_files.list_paths(ROOT, head, '', g)
        for repo, args, timeout in g.calls:
            self.assertEqual(repo, ROOT)
            self.assertEqual(timeout, base_files.TIMEOUT)
            self.assertIsNone(gitread.form_error(ROOT, args, timeout), args)
            self.assertIn(args[:2], (['rev-parse', '--verify'], ['cat-file', '-t'], ['cat-file', '-p']))
        self.assertEqual([a[:2] for _, a, _ in g.calls[:3]],
                         [['rev-parse', '--verify'], ['cat-file', '-t'], ['cat-file', '-p']])

    def test_failed_reads(self):
        """TASK-081 AC4: a raising read, a non-dict, a missing key, an error, a nonzero exit, a timeout or non-bytes out
        gives findings naming the subcommand."""
        def raising(repo, args, timeout):
            raise RuntimeError('made up')
        answers = [(lambda *a: None, 'gave no result'), (lambda *a: {'exit': 0, 'out': b''}, 'gave no result'),
                   (lambda *a: {**ok(b''), 'error': 'timeout'}, 'was not run'), (lambda *a: failed(1), 'exited with'),
                   (lambda *a: {**ok(b''), 'out': 'text'}, 'gave no bytes'), (raising, 'raised')]
        _, head = sample()
        for answer, text in answers:
            findings = self.refused(base_files.read_file(ROOT, head, 'a.txt', answer))
            self.assertIn('rev-parse --verify', findings[0])
            self.assertIn(text, findings[0])

    def test_default_read_is_gitread_run(self):
        """TASK-081 AC4: read defaults to gitread.run, taken at call time."""
        g, head = sample()
        with mock.patch.object(gitread, 'run', g):
            self.assertEqual(base_files.read_file(ROOT, head, 'a.txt')[0]['text'], 'alpha\n')
        self.assertTrue(g.calls)


class TASK081AC6Purity(Base):
    def test_no_open_clock_or_environment(self):
        """TASK-081 AC6: no open, no clock and no environment read; every Git call goes through read."""
        g, head = sample()
        with mock.patch('builtins.open', side_effect=AssertionError('open')), \
                mock.patch('time.time', side_effect=AssertionError('time')), \
                mock.patch('time.monotonic', side_effect=AssertionError('monotonic')), \
                mock.patch('os.getenv', side_effect=AssertionError('getenv')), \
                mock.patch.object(gitread, 'run', side_effect=AssertionError('run')):
            self.assertEqual(base_files.read_file(ROOT, head, 'a.txt', g)[0]['text'], 'alpha\n')
            self.assertEqual(base_files.list_paths(ROOT, head, '', g)[0], ['a.txt', 'b.sh', 'dir/c.txt'])


class Source(Base):
    def tree(self):
        return ast.parse(SRC.read_bytes().decode('utf-8'))


class TASK081AC7Touch(Source):
    def test_import_set(self):
        """TASK-081 AC7: the module imports exactly hashlib, re and aieos_bootstrap.gitread."""
        names = set()
        for n in ast.walk(self.tree()):
            if isinstance(n, ast.Import):
                names |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                names |= {'%s.%s' % (n.module, a.name) for a in n.names}
        self.assertEqual(names, {'hashlib', 're', 'aieos_bootstrap.gitread'})

    def test_gitread_attributes(self):
        """TASK-081 AC7: on gitread exactly run, parse_commit and form_error are used."""
        attrs = {n.attr for n in ast.walk(self.tree()) if isinstance(n, ast.Attribute)
                 and isinstance(n.value, ast.Name) and n.value.id == 'gitread'}
        self.assertEqual(attrs, {'run', 'parse_commit', 'form_error'})

    def test_sha1_keyword(self):
        """TASK-081 AC7: every hashlib.sha1 call passes usedforsecurity=False, in the module and the tests."""
        files = [SRC, HERE, HERE.parents[1] / 'integration' / 'test_base_files_repo.py',
                 HERE.parents[1] / 'property' / 'test_base_files_properties.py']
        for f in files:
            calls = [n for n in ast.walk(ast.parse(f.read_bytes().decode('utf-8'))) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Attribute) and n.func.attr == 'sha1']
            self.assertTrue(calls, f.name)
            for c in calls:
                kw = [k for k in c.keywords if k.arg == 'usedforsecurity']
                self.assertEqual(len(kw), 1, f.name)
                self.assertIs(kw[0].value.value, False, f.name)

    def test_no_refused_names_or_calls(self):
        """TASK-081 AC7: no name compile, open, exec or eval, no subprocess, and no refused attribute call."""
        tree = self.tree()
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertFalse(names & {'compile', 'open', 'exec', 'eval', '__import__', '__builtins__', 'subprocess'})
        attrs = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertFalse(attrs & {'open', 'connect', 'read_text', 'read_bytes', 'listdir', 'scandir', 'stat', 'walk'})

    def test_no_refused_strings(self):
        """TASK-081 AC7: no ".aieos" string, no benchmark folder name with its slash, no conformance fixture folder
        name, and no string constant exactly valid, accepted or approved."""
        raw = SRC.read_bytes()
        strings = [n.value for n in ast.walk(self.tree()) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertFalse(any('.aieos' in s for s in strings))
        self.assertFalse(set(strings) & {'valid', 'accepted', 'approved'})
        self.assertNotIn(b'bench' + b'/', raw)
        for d in (conformance.FIXTURE_DIR, conformance.RC_FIXTURE_DIR, conformance.RISK_FIXTURE_DIR,
                  conformance.CB_FIXTURE_DIR):
            self.assertNotIn(d.rsplit('/', 1)[1].encode('ascii'), raw)

    def test_no_pass_or_continue_handlers(self):
        """TASK-081 AC7: no try/except/pass and no try/except/continue."""
        for n in ast.walk(self.tree()):
            if isinstance(n, ast.ExceptHandler):
                self.assertFalse(any(isinstance(s, (ast.Pass, ast.Continue)) for s in n.body))

    def test_never_raises(self):
        """TASK-081 AC7: a failure inside the module is returned as findings, never raised."""
        g, head = sample()
        with mock.patch.object(base_files, '_root', side_effect=RuntimeError('made up')):
            findings = self.refused(base_files.read_file(ROOT, head, 'a.txt', g))
            self.assertIn('RuntimeError', findings[0])
            self.refused(base_files.list_paths(ROOT, head, '', g))


PHRASES = ['reads through gitread.run only', 'read is injectable', 'never raises', 'writes nothing',
           'modelled on scope_reconcile._blob_at', 'cached by tree id', 'fails closed', "this task's choice"]


class TASK081AC9Docstring(Source):
    def test_docstring_phrases(self):
        """TASK-081 AC9: the module docstring holds AC9's phrases, whitespace read as single spaces."""
        doc = ' '.join(ast.get_docstring(self.tree()).split())
        for phrase in PHRASES:
            self.assertIn(phrase, doc)

    def test_naming(self):
        """TASK-081 AC9: every test of this module names "TASK-081 ACn" at the start of its docstring."""
        classes = [v for v in globals().values() if isinstance(v, type) and issubclass(v, unittest.TestCase)
                   and v.__module__ == __name__]
        self.assertGreater(len(classes), 5)
        for cls in classes:
            for name in unittest.TestLoader().getTestCaseNames(cls):
                self.assertRegex(getattr(cls, name).__doc__ or '', r'^TASK-081 AC\d+', name)


if __name__ == '__main__':
    unittest.main()
