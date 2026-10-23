"""Integration test of aieos_bootstrap.base_files (TASK-081 AC5) over this repository's history, as
tests/integration/test_gitread_repo.py reads it: read only, gitread.run as read, on fixed commits of main; it needs the
repository's full history (a shallow clone fails it). It also holds the conformance with scope_reconcile._blob_at,
used here as a test-only oracle. Each test names its criteria in its own docstring."""

import hashlib
import pathlib
import unittest

from aieos_bootstrap import base_files, gitread, scope_reconcile

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
BASE = 'af834d5d4e1e85657bb6c08c823fd16c1b106682'
OLDER = 'e0378695ff7c251d65049f2e20cf6986bae412f6'
SPEC7 = 'docs/specs/spec-07-cli-and-zero-friction-path.md'
DM = 'docs/pre-genesis/decision-matrix.md'
SPECS = ['docs/specs/conformance-files.md', 'docs/specs/risk-rules-gov-aieos.md',
         'docs/specs/spec-01-state-and-event-model.md', 'docs/specs/spec-02-aieos-file-format.md',
         'docs/specs/spec-03-resume-check-and-decision-engine.md', 'docs/specs/spec-04-verification-and-evidence.md',
         'docs/specs/spec-05-adapter-contract.md', 'docs/specs/spec-06-mcp-protocol-and-work-orders.md']


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def gid(kind, data):
    return hashlib.sha1(b'%s %d\x00' % (kind.encode('ascii'), len(data)) + data, usedforsecurity=False).hexdigest()


class Hostile:
    """A stand-in read over a root listing given as bytes, for both walks."""

    def __init__(self, listing):
        self.blob = b'alpha\n'
        self.blob_id = gid('blob', self.blob)
        self.listing = listing.replace(b'@BLOB@', self.blob_id.encode('ascii'))
        self.tree = gid('tree', self.listing)
        self.commit_data = ('tree %s\nauthor A B 1 +0000\ncommitter A B 1 +0000\n\nm\n' % self.tree).encode('ascii')
        self.commit = gid('commit', self.commit_data)
        self.objects = {self.blob_id: ('blob', self.blob), self.tree: ('tree', self.listing),
                        self.commit: ('commit', self.commit_data)}

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


class TASK081AC5History(unittest.TestCase):
    def test_base_commit(self):
        """TASK-081 AC5: at base_commit, specification 7's text has its intent_versions hash and docs/specs nine
        paths."""
        value, findings = base_files.read_file(ROOT, BASE, SPEC7)
        self.assertIsNone(findings)
        self.assertEqual(sha(value['text']), '613cbd72dca411586ca03d790cd01bb044d0eb8e9a2885d9c3f8bb25cc9f5efb')
        self.assertEqual(base_files.list_paths(ROOT, BASE, 'docs/specs'), (sorted(SPECS + [SPEC7]), None))

    def test_older_commit(self):
        """TASK-081 AC5: at e0378695 the decision matrix has its older hash, specification 7 is missing and docs/specs
        holds eight paths, whatever the working tree holds."""
        value, findings = base_files.read_file(ROOT, OLDER, DM)
        self.assertIsNone(findings)
        self.assertEqual(sha(value['text']), 'ac8a611640714aa282bf311197a9fe2d64b303e82ba46bcc193aa38a64252577')
        self.assertIsNone(base_files.read_file(ROOT, OLDER, SPEC7)[0])
        self.assertEqual(base_files.list_paths(ROOT, OLDER, 'docs/specs'), (SPECS, None))

    def test_conformance_with_blob_at(self):
        """TASK-081 AC5: on the fixed set of paths at base_commit, read_file gives the blob id and text that
        scope_reconcile._blob_at gives."""
        tree = gitread.parse_commit(gitread.run(ROOT, ['cat-file', '-p', BASE])['out'])['tree']
        paths = SPECS + [SPEC7, scope_reconcile.POLICY_PATH, scope_reconcile.WORKFLOW_PATH]
        for path in paths:
            oid, text = scope_reconcile._blob_at(gitread.run, ROOT, tree, path)
            self.assertEqual(base_files.read_file(ROOT, BASE, path), ({'blob': oid, 'text': text}, None), path)

    def test_conformance_on_hostile_listings(self):
        """TASK-081 AC5: on hostile listings both walks refuse: read_file gives findings where _blob_at stops."""
        line = b'100644 blob @BLOB@\ta.txt\n'
        listings = [line + line, b'100600 blob @BLOB@\ta.txt\n', line + b'100644 blob @BLOB@\tb\x01c\n',
                    line + b'100644 blob @BLOB@\t\xff\xfe\n']
        for listing in listings:
            g = Hostile(listing)
            value, findings = base_files.read_file(ROOT, g.commit, 'a.txt', g)
            self.assertIsNone(value, listing)
            self.assertTrue(findings, listing)
            with self.assertRaises(scope_reconcile._Stop, msg=listing):
                scope_reconcile._blob_at(g, ROOT, g.tree, 'a.txt')

    def test_naming(self):
        """TASK-081 AC9: every test of this module names "TASK-081 ACn" at the start of its docstring."""
        for name in unittest.TestLoader().getTestCaseNames(TASK081AC5History):
            self.assertRegex(getattr(TASK081AC5History, name).__doc__ or '', r'^TASK-081 AC\d+', name)


if __name__ == '__main__':
    unittest.main()
