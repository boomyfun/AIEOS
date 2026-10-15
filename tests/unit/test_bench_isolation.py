"""No part of AIEOS names or runs the stack benchmark's ports (TASK-043 AC7; decision D-800 C3; the risk rules policy
revision 6, rule R12).

The ports under bench/ are disposable benchmark code whose results are advisory and feed nothing (A29, A31). This test
reads, with read_bytes, every file under src/ and tests/ (a __pycache__ folder is passed over) and the CI workflow
.github/workflows/aieos-checks.yml, and fails if any of them names "bench/" or imports a module named bench, except the
files of a closed allow-list, each with its reason below. It also checks that the benchmark workflow
.github/workflows/aieos-bench.yml is the only workflow that names "bench/". It runs no process and writes no file.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NAME = b'bench/'
IMPORT = re.compile(rb'(?m)^\s*(?:import|from)\s+bench\b')
# The closed allow-list: a repository path, or a folder prefix ending in "/", with its reason.
ALLOWED = {
    'tests/unit/test_export_fixtures.py': 'the benchmark workflow\'s trigger pins name its paths (TASK-039 AC1)',
    'tests/conformance/': 'the frozen fixtures (R11, critical): RISK-01\'s fixture carries rule R12\'s pattern as a value',
    'tests/unit/test_bench_isolation.py': 'this test names what it looks for',
}


def allowed(path):
    return any(path == a or (a.endswith('/') and path.startswith(a)) for a in ALLOWED)


def offenders(files):
    """The paths, outside the allow-list, whose bytes name bench/ or import a module named bench."""
    return sorted(p for p, b in files.items() if not allowed(p) and (NAME in b or IMPORT.search(b)))


def repository_files():
    files = {}
    for top in ('src', 'tests'):
        for f in sorted((REPO / top).rglob('*')):
            if f.is_file() and '__pycache__' not in f.relative_to(REPO).parts:
                files[f.relative_to(REPO).as_posix()] = f.read_bytes()
    checks = REPO / '.github' / 'workflows' / 'aieos-checks.yml'
    files['.github/workflows/aieos-checks.yml'] = checks.read_bytes()
    return files


class IsolationTests(unittest.TestCase):
    def test_no_aieos_file_names_bench(self):
        """TASK-043 AC7: no file under src/ or tests/, nor aieos-checks.yml, names bench/ outside the allow-list."""
        files = repository_files()
        self.assertIn('src/aieos_bootstrap/governor.py', files)
        self.assertIn('.github/workflows/aieos-checks.yml', files)
        self.assertEqual(offenders(files), [])

    def test_a_name_outside_the_list_fails(self):
        """TASK-043 AC7: a file outside the allow-list that names bench/ or imports bench is caught."""
        files = {'src/aieos_bootstrap/x.py': b'path = "bench/ts/main.ts"\n',
                 'tests/unit/y.py': b'def f():\n    import bench.ts\n',
                 'tests/unit/z.py': b'from bench import ts\n',
                 'tests/unit/test_export_fixtures.py': b"'bench/**'\n",
                 'tests/conformance/fixtures/r.py': b'bench/\n',
                 'tests/unit/ok.py': b'benchmark = 1\nbenchmarks\n'}
        self.assertEqual(offenders(files), ['src/aieos_bootstrap/x.py', 'tests/unit/y.py', 'tests/unit/z.py'])

    def test_only_the_benchmark_workflow_names_bench(self):
        """TASK-043 AC7: .github/workflows/aieos-bench.yml is the only workflow that names bench/."""
        folder = REPO / '.github' / 'workflows'
        naming = sorted(f.name for f in folder.iterdir() if f.is_file() and NAME in f.read_bytes())
        self.assertEqual(naming, ['aieos-bench.yml'])

    def test_allow_list_is_closed(self):
        """TASK-043 AC7: the allow-list holds exactly its three entries, each with a reason."""
        self.assertEqual(sorted(ALLOWED), ['tests/conformance/', 'tests/unit/test_bench_isolation.py',
                                           'tests/unit/test_export_fixtures.py'])
        self.assertTrue(all(reason for reason in ALLOWED.values()))

    def test_naming(self):
        """TASK-043 AC10: every test of this module names the AC it stands for in its docstring."""
        for name in unittest.TestLoader().getTestCaseNames(IsolationTests):
            self.assertRegex(getattr(IsolationTests, name).__doc__ or '', r'^TASK-043 AC\d+', name)


if __name__ == '__main__':
    unittest.main()
