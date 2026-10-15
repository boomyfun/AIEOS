"""The stack benchmark's fixture export and its tests (TASK-039; docs/plan/m4-exit-review.md §6).

The export: run from the repository root as `python tests/unit/test_export_fixtures.py --root tests/conformance`, it
reads every file of the three frozen fixture folders (fixtures, fixtures_rc, fixtures_risk; a __pycache__ folder
inside one, which the CI channel's build step makes, is passed over) as text, takes the JSON of
its `DATA = r'''...'''` string, parses it, and prints one JSON document to standard output: an object whose keys are
"<folder>/<file name without .py>" and whose values are the parsed objects, with sorted keys, ASCII only and LF line
ends on every system. It fails closed: on a file not in that exact form, JSON that does not parse, a missing folder,
an entry that is not a .py file, or any other argument, it exits non-zero and prints nothing to standard output, since
the whole document is built before anything is written. It imports no fixture and no module of the repository, runs no
process, reads no network, clock or environment, and writes no file: the benchmark workflow redirects its standard
output into the job's temporary folder.

The export lives in this test module because the CI channel's deterministic_rule lets a module under tests/ import only
the standard library and aieos_bootstrap and refuses every file write, so a separate helper could neither write its
files nor be imported by its tests (decision D-773, erratum E1). It depends on the three frozen fixture folders, and the
two earlier checks that limit which modules name the RC and risk folders (tests/integration/test_conformance_rc_set.py
and test_conformance_risk_set.py) allow it by name (decision D-774, erratum E2). The benchmark's results are advisory
and feed nothing (A29, A31).
"""

import io
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FOLDERS = ('fixtures', 'fixtures_rc', 'fixtures_risk')
HEAD = "DATA = r'''"
QUOTES = "'''"
WORKFLOW = REPO / '.github' / 'workflows' / 'aieos-bench.yml'


class ExportError(Exception):
    """A fixture folder or file is not in the exact form the export reads."""


def parse_fixture(text):
    """Returns the object of one fixture file's text, which must be exactly HEAD, the JSON, QUOTES and at most one LF."""
    if not text.startswith(HEAD):
        raise ExportError('the text does not start with ' + HEAD)
    rest = text[len(HEAD):]
    if HEAD in rest:
        raise ExportError('more than one ' + HEAD)
    if rest.count(QUOTES) != 1:
        raise ExportError('not exactly one closing ' + QUOTES)
    body, tail = rest.split(QUOTES)
    if tail not in ('', '\n'):
        raise ExportError('text after the closing quotes')
    return json.loads(body)


def listing(root):
    """The fixture folders under root as {folder: [(name, kind, bytes or None)]}, kind "dir", "file" or "other";
    a missing folder is left out, so that document() refuses it."""
    out = {}
    for folder in FOLDERS:
        d = Path(root) / folder
        if d.is_dir():
            out[folder] = [(p.name, 'dir' if p.is_dir() else 'file' if p.is_file() else 'other',
                            p.read_bytes() if p.is_file() else None) for p in sorted(d.iterdir())]
    return out


def document(entries):
    """Returns the export document of a listing as an ASCII string ending in LF; refuses any other form."""
    out = {}
    for folder in FOLDERS:
        if folder not in entries:
            raise ExportError('missing fixture folder ' + folder)
        for name, kind, data in entries[folder]:
            if name == '__pycache__' and kind == 'dir':
                continue
            if kind != 'file' or not name.endswith('.py'):
                raise ExportError('not a .py file: %s/%s' % (folder, name))
            out['%s/%s' % (folder, name[:-3])] = parse_fixture(data.decode('utf-8'))
    if not out:
        raise ExportError('no fixture')
    return json.dumps(out, sort_keys=True, indent=2, ensure_ascii=True) + '\n'


def export(root):
    """Returns the export document of the fixture folders under root as an ASCII string ending in LF."""
    return document(listing(root))


def main(argv, out=None):
    """The command line: exactly `--root <folder>`; writes the document to out (standard output's bytes) or nothing."""
    if len(argv) != 2 or argv[0] != '--root':
        print('usage: test_export_fixtures.py --root <folder>', file=sys.stderr)
        return 2
    try:
        doc = export(argv[1])
    except (ExportError, ValueError, OSError) as e:
        print('export failed: %s' % e, file=sys.stderr)
        return 1
    (sys.stdout.buffer if out is None else out).write(doc.encode('ascii'))
    return 0


def fixture(body='{"a": 1}', head=HEAD, tail="'''\n"):
    return head + body + tail


class ParseTests(unittest.TestCase):
    def test_exact_form(self):
        """TASK-039 AC4: a text in the exact form gives its JSON object, with or without the final LF."""
        self.assertEqual(parse_fixture(fixture()), {'a': 1})
        self.assertEqual(parse_fixture(fixture(tail="'''")), {'a': 1})

    def test_fails_closed(self):
        """TASK-039 AC5: no head, text before it, two heads, extra quotes, text after the quotes or bad JSON all raise."""
        bad = (('{"a": 1}' + "'''\n", 'does not start'), ('# x\n' + fixture(), 'does not start'),
               (fixture(body='{"a": 1}' + "'''\n" + HEAD + '{}'), 'more than one'),
               (fixture(body='{"a": "' + "'''" + '"}'), 'not exactly one closing'), (fixture(tail=''), 'not exactly one closing'),
               (fixture(tail="'''\nX = 1\n"), 'text after'), (fixture(tail="'''\n\n"), 'text after'))
        for text, why in bad:
            with self.subTest(text=text):
                with self.assertRaisesRegex(ExportError, why):
                    parse_fixture(text)
        for body in ('{"a": 1,}', ''):
            with self.subTest(body=body):
                with self.assertRaises(ValueError):
                    parse_fixture(fixture(body=body))


def entries(**extra):
    """A listing of the three folders, each with one good fixture, changed by extra (folder: list or None)."""
    out = {f: [('%s_01.py' % f, 'file', fixture().encode('ascii'))] for f in FOLDERS}
    for f, v in extra.items():
        if v is None:
            del out[f]
        else:
            out[f] = v
    return out


class DocumentTests(unittest.TestCase):
    def test_form(self):
        """TASK-039 AC4: keys "<folder>/<stem>", sorted at every level, ASCII only, a __pycache__ folder passed over."""
        e = entries(fixtures=[('z_02.py', 'file', fixture(body='{"b": 1, "a": "é"}').encode('utf-8')),
                              ('__pycache__', 'dir', None), ('a_01.py', 'file', fixture().encode('ascii'))])
        doc = document(e)
        self.assertTrue(doc.isascii())
        self.assertIn('\\u00e9', doc)
        got = json.loads(doc)
        self.assertEqual(list(got), ['fixtures/a_01', 'fixtures/z_02', 'fixtures_rc/fixtures_rc_01',
                                     'fixtures_risk/fixtures_risk_01'])
        self.assertEqual(list(got['fixtures/z_02']), ['a', 'b'])
        self.assertEqual(doc, json.dumps(got, sort_keys=True, indent=2, ensure_ascii=True) + '\n')

    def test_refuses(self):
        """TASK-039 AC5: a missing folder, a non-.py file, another folder, a __pycache__ file or no fixture is refused."""
        cases = ((entries(fixtures_risk=None), 'missing fixture folder'),
                 (entries(fixtures_rc=[('x.txt', 'file', b'')]), 'not a .py file'),
                 (entries(fixtures=[('sub', 'dir', None)]), 'not a .py file'),
                 (entries(fixtures=[('__pycache__', 'file', b'')]), 'not a .py file'),
                 (entries(fixtures=[('odd.py', 'other', None)]), 'not a .py file'),
                 ({f: [] for f in FOLDERS}, 'no fixture'))
        for e, why in cases:
            with self.subTest(why=why):
                with self.assertRaisesRegex(ExportError, why):
                    document(e)


class ExportTests(unittest.TestCase):
    def test_real_fixtures(self):
        """TASK-039 AC4: the export over the frozen fixtures, read only, has one entry per file, each its parsed DATA."""
        root = REPO / 'tests' / 'conformance'
        doc = export(root)
        got = json.loads(doc)
        names = sorted('%s/%s' % (f, p.stem) for f in FOLDERS for p in (root / f).iterdir() if p.name != '__pycache__')
        self.assertEqual(sorted(got), names)
        self.assertEqual([len([n for n in names if n.split('/')[0] == f]) for f in FOLDERS], [19, 11, 1])
        self.assertEqual(len(got), 31)
        for name in names:
            folder, stem = name.split('/')
            text = (root / folder / (stem + '.py')).read_bytes().decode('utf-8')
            self.assertEqual(got[name], json.loads(text[len(HEAD):text.rindex(QUOTES)]))
        self.assertEqual(doc, json.dumps(got, sort_keys=True, indent=2, ensure_ascii=True) + '\n')
        self.assertTrue(doc.isascii())

    def test_main_writes_the_document(self):
        """TASK-039 AC4: main with --root writes the document's ASCII bytes and returns 0."""
        out = io.BytesIO()
        self.assertEqual(main(['--root', str(REPO / 'tests' / 'conformance')], out), 0)
        self.assertEqual(out.getvalue(), export(REPO / 'tests' / 'conformance').encode('ascii'))

    def test_main_fails_closed(self):
        """TASK-039 AC5: a missing folder or any other argument form gives a non-zero exit and nothing written."""
        missing = REPO / 'tests' / 'no-such-folder-task-039'
        self.assertFalse(missing.exists())
        real = str(REPO / 'tests' / 'conformance')
        for argv in (['--root', str(missing)], [], ['--root'], ['--out', 'x'], ['--root', 'a', 'b'], ['x', 'y'],
                     ['--root', real, 'x'], ['--out', real], ['--root', real, '--root', real]):
            with self.subTest(argv=argv):
                out = io.BytesIO()
                self.assertNotEqual(main(argv, out), 0)
                self.assertEqual(out.getvalue(), b'')
        with self.assertRaises(ExportError):
            export(missing)
        with self.assertRaises(ExportError):
            export(REPO / 'tests')

    def test_imports(self):
        """TASK-039 AC4: this module imports only io, json, sys, unittest and pathlib, no fixture or repository module."""
        lines = Path(__file__).read_bytes().decode('utf-8').split('\n')
        imports = [ln for ln in lines if ln.startswith(('import ', 'from '))]
        self.assertFalse([ln for ln in lines if ln.lstrip().startswith(('import ', 'from ')) and not ln.startswith(('import ', 'from '))])
        self.assertEqual(imports, ['import io', 'import json', 'import sys', 'import unittest', 'from pathlib import Path'])


# TASK-043 AC12: the one download the benchmark workflow may make, the pinned type checker (decision D-844).
TSC_URL = 'https://registry.npmjs.org/typescript/-/typescript-6.0.3.tgz'
TSC_INTEGRITY = 'sha512-y2TvuxSZPDyQakkFRPZHKFm+KKVqIisdg9/CZwm9ftvKXLP8NRWj38/ODjNbr43SsoXqNuAisEf1GdCxqWcdBw=='
CURL = ('curl -sS --fail --proto =https --max-time 120 --max-filesize 20000000 ' + TSC_URL
        + ' -o "$RUNNER_TEMP/tsc/typescript-6.0.3.tgz"')


def workflow():
    return WORKFLOW.read_bytes().decode('utf-8')


def top_block(text, key):
    """The lines of one top-level key's block (the key's line and the indented lines after it)."""
    lines = text.split('\n')
    i = lines.index(key + ':')
    out = [lines[i]]
    for ln in lines[i + 1:]:
        if ln and not ln.startswith((' ', '#')):
            break
        out.append(ln)
    return out


class WorkflowTests(unittest.TestCase):
    def test_triggers_and_permissions(self):
        """TASK-039 AC1: push to main with the three paths, workflow_dispatch for the owner only, contents read only."""
        text = workflow()
        on = [ln for ln in top_block(text, 'on') if ln.strip() and not ln.strip().startswith('#')]
        self.assertEqual(on, ['on:', '  push:', '    branches: [main]', '    paths:', "      - 'bench/**'",
                              "      - '.github/workflows/aieos-bench.yml'", "      - 'tests/unit/test_export_fixtures.py'",
                              '  workflow_dispatch:'])
        self.assertIn('for the owner only', '\n'.join(top_block(text, 'on')))
        self.assertEqual([ln for ln in top_block(text, 'permissions') if ln.strip()], ['permissions:', '  contents: read'])
        self.assertEqual(text.count('permissions:'), 1)
        for word in ('pull_request', 'schedule', 'workflow_run', 'repository_dispatch', 'issue', 'release:'):
            self.assertNotIn(word, text)

    def test_jobs_and_checkout(self):
        """TASK-039 AC2: two jobs, Linux and Windows, at most 20 minutes, bash, no action, the checkout of GITHUB_SHA."""
        text = workflow()
        self.assertNotIn('uses:', text)
        self.assertEqual(text.count('runs-on:'), 2)
        self.assertIn('  linux:\n    runs-on: ubuntu-24.04\n', text)
        self.assertIn('  windows:\n    runs-on: windows-latest\n', text)
        mins = [int(ln.split(':')[1]) for ln in text.split('\n') if ln.strip().startswith('timeout-minutes:')]
        self.assertEqual(len(mins), 2)
        self.assertTrue(all(0 < m <= 20 for m in mins))
        self.assertEqual(text.count('      run:\n        shell: bash\n'), 2)
        self.assertEqual(text.count('git fetch -q --depth 1 "${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}.git" "$GITHUB_SHA"'), 2)
        self.assertEqual(text.count('git checkout -q --detach FETCH_HEAD'), 2)
        self.assertEqual(text.count('test "$(git rev-parse HEAD)" = "$GITHUB_SHA"'), 2)
        steps = [ln.strip() for ln in text.split('\n') if ln.strip().startswith('- name:')]
        self.assertEqual(len(steps) % 2, 0)
        half = steps[:len(steps) // 2]
        self.assertEqual(half, steps[len(steps) // 2:])
        self.assertTrue(half[0].startswith('- name: checkout'))
        self.assertTrue(half[1].startswith('- name: checkout check'))

    def test_no_secret_token_or_write(self):
        """TASK-039 AC3: no secret, no token, no push, tag, upload, comment or API call; TASK-043 AC12: curl only as the
        pinned type checker download, exactly twice."""
        text = workflow()
        self.assertEqual(text.count(CURL), 2)
        text = text.replace(CURL, '')
        for word in ('secrets.', 'GITHUB_TOKEN', 'github.token', 'git push', 'git tag', 'upload', 'gh ', 'curl', 'wget',
                     'github.com', 'api.github', 'Invoke-WebRequest', 'write-all', ': write', '${{'):
            self.assertNotIn(word, text)

    def test_steps(self):
        """TASK-039 AC6: the export into the temporary folder, the toolchain versions, and each port only if it exists;
        TASK-043 AC12: the bench/ts guard twice per job (the type check and the port)."""
        text = workflow()
        self.assertEqual(text.count('tests/unit/test_export_fixtures.py --root tests/conformance > "$RUNNER_TEMP/fixtures.json"'), 2)
        for tool in ('node --version', 'go version', 'rustc --version'):
            self.assertEqual(text.count(tool), 2)
        self.assertNotIn('powershell', text.lower())
        for port, count in (('ts', 4), ('go', 2), ('rust', 2)):
            self.assertEqual(text.count('if [ -d bench/%s ]; then' % port), count)


class TypeCheckTests(unittest.TestCase):
    def test_pinned_download(self):
        """TASK-043 AC12: each job fetches only the pinned tarball and checks its integrity before tar and the run."""
        text = workflow()
        jobs = text.split('\n  windows:\n')
        self.assertEqual(len(jobs), 2)
        for job in jobs:
            self.assertEqual(job.count(CURL), 1)
            self.assertEqual(job.count(TSC_URL), 1)
            self.assertEqual(job.count(TSC_INTEGRITY), 1)
            order = [job.index(CURL), job.index('if [ "$got" != "' + TSC_INTEGRITY + '" ]; then'),
                     job.index('tar -xzf typescript-6.0.3.tgz'), job.index('node "$RUNNER_TEMP/tsc/package/bin/tsc" -p bench/ts')]
            self.assertEqual(order, sorted(order))
            self.assertEqual(job.count('exit 1'), 1)

    def test_naming(self):
        """TASK-043 AC12: every test of this class names the AC it stands for in its docstring."""
        for name in unittest.TestLoader().getTestCaseNames(TypeCheckTests):
            self.assertRegex(getattr(TypeCheckTests, name).__doc__ or '', r'^TASK-043 AC\d+', name)


class SuiteTests(unittest.TestCase):
    def test_suite_runs_no_export(self):
        """TASK-039 AC8: run_tests.py keeps its three groups, and this module runs the export only under its main guard."""
        runner = (REPO / 'tests' / 'run_tests.py').read_bytes().decode('utf-8')
        self.assertEqual(runner.count("GROUPS = ('unit', 'integration', 'property')\n"), 1)
        lines = Path(__file__).read_bytes().decode('utf-8').split('\n')
        guard = lines.index("if __name__ == '__main__':")
        self.assertEqual(lines[guard + 1:], ["    if sys.argv[1:2] == ['--root']:", '        sys.exit(main(sys.argv[1:]))',
                                              '    unittest.main()', ''])
        self.assertFalse([ln for ln in lines[:guard] if ln.startswith(('main(', 'export(', 'sys.exit'))])

    def test_naming(self):
        """TASK-039 AC10: every test of this module names the AC it stands for in its docstring."""
        loader = unittest.TestLoader()
        for case in (ParseTests, DocumentTests, ExportTests, WorkflowTests, SuiteTests):
            for name in loader.getTestCaseNames(case):
                doc = getattr(case, name).__doc__ or ''
                self.assertRegex(doc, r'^TASK-039 AC\d+', name)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--root']:
        sys.exit(main(sys.argv[1:]))
    unittest.main()
