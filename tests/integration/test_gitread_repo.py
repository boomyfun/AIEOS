"""Integration test of aieos_bootstrap.gitread over this repository's history (task TASK-024, rule R7, AC8): read
only, with the four pinned forms, on fixed commits of main; it needs the repository's full history (a shallow clone
fails it). The results are data about accepted commits: they reopen nothing. Each test names its criteria in its own
docstring."""

import pathlib
import unittest

from aieos_bootstrap import gitread

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
FIX = '2b7bf15269c57484e3306c6a6532d4cea6b5d3e2'
FIRST = '8cc5af058c1acd37b729ae7e44b6a2367a851043'
CONTRACT = 'badd0c97ffb1f35b37d78bebf4167e05b6207304'
DIFF = ['diff-tree', '--no-commit-id', '--name-only', '-r', '--no-renames', '--no-ext-diff', '--no-textconv', '-z',
        '--root']


class RepositoryHistory(unittest.TestCase):
    def test_commit_object_parses(self):
        """TASK-024 AC8, TASK-024 AC4 and TASK-024 AC12: cat-file -p of TASK-023's fix commit parses with its one parent
        and the trailer AIEOS-Task: TASK-023."""
        r = gitread.run(ROOT, ['cat-file', '-p', FIX])
        self.assertIsNone(r['error'])
        self.assertEqual(r['exit'], 0)
        p = gitread.parse_commit(r['out'])
        self.assertIsNone(p['error'])
        self.assertEqual(p['parents'], [FIRST])
        self.assertIn(['AIEOS-Task', 'TASK-023'], p['trailers'])

    def test_changed_paths(self):
        """TASK-024 AC8, TASK-024 AC5 and TASK-024 AC12: diff-tree of the fix commit gives exactly its four paths."""
        r = gitread.run(ROOT, DIFF + [FIX])
        self.assertEqual((r['exit'], r['error']), (0, None))
        self.assertEqual(gitread.parse_paths(r['out']), {'paths': [
            'src/aieos_bootstrap/stale.py', 'tests/integration/test_stale_records.py',
            'tests/property/test_stale_properties.py', 'tests/unit/test_stale.py'], 'error': None})

    def test_parents_and_type(self):
        """TASK-024 AC8, TASK-024 AC1 and TASK-024 AC12: rev-list --parents of TASK-023's first commit names commit C as
        its parent, and cat-file -t of it gives "commit"; rev-parse of HEAD gives one object id."""
        r = gitread.run(ROOT, ['rev-list', '--parents', '-n', '1', FIRST])
        self.assertEqual(r['exit'], 0)
        self.assertEqual(r['out'].decode('utf-8').split(), [FIRST, CONTRACT])
        r = gitread.run(ROOT, ['cat-file', '-t', FIRST])
        self.assertEqual((r['exit'], r['out']), (0, b'commit\n'))
        r = gitread.run(ROOT, ['rev-parse', '--verify', '--end-of-options', 'HEAD'])
        self.assertEqual(r['exit'], 0)
        self.assertIsNotNone(gitread.OBJECT_ID.fullmatch(r['out'].decode('utf-8').strip()))

    def test_refused_forms_start_nothing(self):
        """TASK-024 AC8, TASK-024 AC1, TASK-024 AC3 and TASK-024 AC12: a write form and a fifth subcommand return the
        refusal result."""
        for args in (['commit', '-m', 'x'], ['log']):
            r = gitread.run(ROOT, args)
            self.assertEqual((r['exit'], r['out'], r['err']), (None, b'', b''))
            self.assertIn('subcommand', r['error'])


if __name__ == '__main__':
    unittest.main()
