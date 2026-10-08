"""Local test runner of TASK-001 (AC9): runs the unit, integration and property tests with the standard library's
unittest and exits non-zero if any test fails. It is for local runs only; the CI channel runs its own discovery from
the workflow (GOV-003). Run from the repository root: python tests/run_tests.py
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GROUPS = ('unit', 'integration', 'property')


def main():
    sys.path.insert(0, os.path.join(ROOT, 'src'))
    suite = unittest.TestSuite()
    for group in GROUPS:
        start = os.path.join(HERE, group)
        suite.addTests(unittest.TestLoader().discover(start, pattern='test_*.py', top_level_dir=start))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if result.wasSuccessful() and result.testsRun > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
