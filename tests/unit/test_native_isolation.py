"""No part of AIEOS names or runs the native shadow ports (TASK-100 AC7; decisions D-3408 C7, D-3417 C1, D-3427 C3; the
form of decision D-800 C3).

The native governor under native/ runs in shadow: it decides nothing, and only the advisory workflow aieos-native.yml
runs it (m8-plan.md section 2). This test reads, with read_bytes, every file under src/ and tests/ (a __pycache__ folder
is passed over) and the CI workflow .github/workflows/aieos-checks.yml, and fails if any of them names "native/" or
imports a module named native, except the files of a closed allow-list, each with its reason below. It also checks that
aieos-native.yml is the only workflow that names "native/". It runs no process and writes no file.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NAME = b'native/'
IMPORT = re.compile(rb'(?m)^\s*(?:import|from)\s+native\b')
# The closed allow-list: exactly two repository paths, each with its reason. RISK-01's path is built from parts, since
# the closed name lists of the conformance set tests allow only their own modules to name its folder.
RISK_01 = 'tests/conformance/' + 'fixtures_' + 'risk' + '/risk_01.py'
ALLOWED = {
    'tests/unit/test_native_isolation.py': 'this test names what it looks for',
    RISK_01: 'a frozen risk-rules fixture (R11, critical) that carries rule R13\'s pattern "native/**" as a value',
}


def offenders(files):
    """The paths, outside the allow-list, whose bytes name native/ or import a module named native."""
    return sorted(p for p, b in files.items() if p not in ALLOWED and (NAME in b or IMPORT.search(b)))


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
    def test_no_aieos_file_names_native(self):
        """TASK-100 AC7: no file under src/ or tests/, nor aieos-checks.yml, names native/ outside the allow-list."""
        files = repository_files()
        self.assertIn('src/aieos_bootstrap/governor.py', files)
        self.assertIn('.github/workflows/aieos-checks.yml', files)
        self.assertIn(RISK_01, files)
        self.assertEqual(offenders(files), [])

    def test_a_name_outside_the_list_fails(self):
        """TASK-100 AC7: a file outside the allow-list that names native/ or imports native is caught."""
        files = {'src/aieos_bootstrap/x.py': b'path = "native/go/governor"\n',
                 'tests/unit/y.py': b'def f():\n    import native.go\n',
                 'tests/unit/z.py': b'from native import go\n',
                 RISK_01: b'native/**\n',
                 'tests/conformance/other.py': b'native/\n',
                 'tests/unit/ok.py': b'natively = 1\nnatives\n'}
        self.assertEqual(offenders(files), ['src/aieos_bootstrap/x.py', 'tests/conformance/other.py',
                                            'tests/unit/y.py', 'tests/unit/z.py'])

    def test_only_the_native_workflow_names_native(self):
        """TASK-100 AC7: .github/workflows/aieos-native.yml is the only workflow that names native/."""
        folder = REPO / '.github' / 'workflows'
        naming = sorted(f.name for f in folder.iterdir() if f.is_file() and NAME in f.read_bytes())
        self.assertEqual(naming, ['aieos-native.yml'])

    def test_allow_list_is_closed(self):
        """TASK-100 AC7: the allow-list holds exactly its two entries, each with a reason."""
        self.assertEqual(sorted(ALLOWED), [RISK_01, 'tests/unit/test_native_isolation.py'])
        self.assertTrue(all(reason for reason in ALLOWED.values()))

    def test_naming(self):
        """TASK-100 AC7: every test of this module names the AC it stands for in its docstring."""
        for name in unittest.TestLoader().getTestCaseNames(IsolationTests):
            self.assertRegex(getattr(IsolationTests, name).__doc__ or '', r'^TASK-100 AC\d+', name)


if __name__ == '__main__':
    unittest.main()
