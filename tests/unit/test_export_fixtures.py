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


# TASK-044 AC8: the Go port's step (decision D-855 B3, B4), its module file, and the checks carried from TASK-043
# (decision D-849; D-855 B5 (i)): the guard count per job and the whole TypeScript type-check step. TASK-049 AC8:
# GO_STEP updated in place with round 2's six lines (decisions D-938 B4, D-943).
GO_STEP = ('          if [ -d bench/go ]; then\n'
           '            export GOTOOLCHAIN=local GOPROXY=off CGO_ENABLED=0\n'
           '            mkdir "$RUNNER_TEMP/go"\n'
           '            (cd bench/go && go vet . && out="$(gofmt -l .)" && test -z "$out"'
           ' && go build -trimpath -o "$RUNNER_TEMP/go/port.exe" .)\n'
           '            "$RUNNER_TEMP/go/port.exe" "$RUNNER_TEMP/fixtures.json" > "$RUNNER_TEMP/go.json"\n'
           '            $PY tests/unit/test_export_reference.py --compare "$RUNNER_TEMP/reference.json" "$RUNNER_TEMP/go.json"\n'
           '            if "$RUNNER_TEMP/go/port.exe" > "$RUNNER_TEMP/go-noarg.txt"; then'
           ' echo "go: the port exits 0 with no argument"; false; fi\n'
           '            test ! -s "$RUNNER_TEMP/go-noarg.txt"\n'
           '            (cd bench/go && go test -count=1 . -args "$RUNNER_TEMP/fixtures.json" "$RUNNER_TEMP/reference.json")\n'
           '            (cd bench/go && go vet ./round2 && go build -trimpath -o "$RUNNER_TEMP/go/port2.exe" ./round2)\n'
           '            "$RUNNER_TEMP/go/port2.exe" "$RUNNER_TEMP/round2-input.json" > "$RUNNER_TEMP/go2.json"\n'
           '            $PY tests/unit/test_export_reference.py --compare "$RUNNER_TEMP/round2-reference.json"'
           ' "$RUNNER_TEMP/go2.json"\n'
           '            if "$RUNNER_TEMP/go/port2.exe" > "$RUNNER_TEMP/go2-noarg.txt"; then'
           ' echo "go: port2 exits 0 with no argument"; false; fi\n'
           '            test ! -s "$RUNNER_TEMP/go2-noarg.txt"\n'
           '            (cd bench/go && go test -count=1 ./round2 -args "$RUNNER_TEMP/round2-input.json"'
           ' "$RUNNER_TEMP/round2-reference.json")\n'
           '          else\n'
           '            echo "no port in bench/go"\n'
           '          fi\n')
TS_CHECK_STEP = ('      - name: type-check ts (only if bench/ts exists)\n'
                 '        run: |\n'
                 '          if [ -d bench/ts ]; then\n'
                 '            mkdir "$RUNNER_TEMP/tsc"\n'
                 '            ' + CURL + '\n'
                 '            got="sha512-$(openssl dgst -sha512 -binary "$RUNNER_TEMP/tsc/typescript-6.0.3.tgz" | base64 -w0)"\n'
                 '            if [ "$got" != "' + TSC_INTEGRITY + '" ]; then\n'
                 '              echo "the type checker\'s integrity differs: $got"\n'
                 '              exit 1\n'
                 '            fi\n'
                 '            (cd "$RUNNER_TEMP/tsc" && tar -xzf typescript-6.0.3.tgz)\n'
                 '            node "$RUNNER_TEMP/tsc/package/bin/tsc" -p bench/ts\n'
                 '          else\n'
                 '            echo "no port in bench/ts"\n'
                 '          fi\n')
GO_MOD = b'module aieosbench\n\ngo 1.24\n'
BENCH_GO = REPO / 'bench' / 'go'


def jobs():
    parts = workflow().split('\n  windows:\n')
    if len(parts) != 2:
        raise AssertionError('not exactly two jobs')
    return parts


class GoStepTests(unittest.TestCase):
    def test_go_step(self):
        """TASK-044 AC8: in each job the go step runs exactly the pinned commands under its one guard, with the toolchain
        switch and the module proxy off before the first go command; no go get, install, mod download or env -w."""
        for job in jobs():
            name = '      - name: port go (only if bench/go exists)\n        run: |\n'
            self.assertEqual(job.count(name), 1)
            self.assertEqual(job.count(name + GO_STEP), 1)
            self.assertLess(job.index('export GOTOOLCHAIN=local GOPROXY=off'), job.index('go vet .'))
        text = workflow()
        for word in ('go get', 'go install', 'go mod', 'go env', 'GOFLAGS', 'GONOSUMDB', 'GOPRIVATE'):
            self.assertNotIn(word, text)

    def test_guards_per_job(self):
        """TASK-044 AC8: in each job, the bench/ts guard twice (the type check and the port), bench/go and bench/rust
        once."""
        for job in jobs():
            for port, count in (('ts', 2), ('go', 1), ('rust', 1)):
                self.assertEqual(job.count('if [ -d bench/%s ]; then' % port), count, port)

    def test_ts_type_check_step(self):
        """TASK-044 AC8: the whole TypeScript type-check step of each job, its got= line included, is TASK-043's."""
        for job in jobs():
            self.assertEqual(job.count(TS_CHECK_STEP), 1)

    def test_go_module(self):
        """TASK-044 AC8: when bench/go exists, its go.mod is exactly the module line and go 1.24 (no require, replace
        or toolchain line), and it has no go.sum and no vendor folder."""
        if not BENCH_GO.is_dir():
            return
        self.assertEqual((BENCH_GO / 'go.mod').read_bytes(), GO_MOD)
        self.assertFalse((BENCH_GO / 'go.sum').exists())
        self.assertFalse((BENCH_GO / 'vendor').exists())

    def test_naming(self):
        """TASK-044 AC10: every test of this class names the AC it stands for in its docstring."""
        for name in unittest.TestLoader().getTestCaseNames(GoStepTests):
            self.assertRegex(getattr(GoStepTests, name).__doc__ or '', r'^TASK-044 AC\d+', name)


# TASK-045 AC8: the Rust port's step (decisions D-871 B1, B3, C1), its Cargo files (D-871 B4, C2; D-872 M1) and the
# TypeScript and Go steps kept as they were.
RUST_STEP = ('          if [ -d bench/rust ]; then\n'
             '            export CARGO_NET_OFFLINE=true CARGO_TARGET_DIR="$RUNNER_TEMP/rust"\n'
             '            cargo --version\n'
             '            cargo fmt --version\n'
             '            cargo clippy --version\n'
             '            (cd bench/rust && cargo fmt --check && cargo clippy --locked --offline --release -- -D warnings'
             ' && cargo build --locked --offline --release)\n'
             '            (cd bench/rust && cargo run --locked --offline --release --quiet --bin port -- "$RUNNER_TEMP/fixtures.json")'
             ' > "$RUNNER_TEMP/rust.json"\n'
             '            $PY tests/unit/test_export_reference.py --compare "$RUNNER_TEMP/reference.json" "$RUNNER_TEMP/rust.json"\n'
             '            p="$RUNNER_TEMP/rust/release/port"; if [ -f "$p.exe" ]; then p="$p.exe"; fi\n'
             '            if "$p" > "$RUNNER_TEMP/rust-noarg.txt"; then echo "rust: the port exits 0 with no argument"; false; fi\n'
             '            test ! -s "$RUNNER_TEMP/rust-noarg.txt"\n'
             '            (cd bench/rust && cargo test --locked --offline --release --test port_test -- "$RUNNER_TEMP/fixtures.json"'
             ' "$RUNNER_TEMP/reference.json")\n'
             '            (cd bench/rust && cargo run --locked --offline --release --quiet --bin port2 --'
             ' "$RUNNER_TEMP/round2-input.json") > "$RUNNER_TEMP/rust2.json"\n'
             '            $PY tests/unit/test_export_reference.py --compare "$RUNNER_TEMP/round2-reference.json"'
             ' "$RUNNER_TEMP/rust2.json"\n'
             '            (cd bench/rust && cargo test --locked --offline --release --test port2_test --'
             ' "$RUNNER_TEMP/round2-input.json" "$RUNNER_TEMP/round2-reference.json")\n'
             '            p2="$RUNNER_TEMP/rust/release/port2"; if [ -f "$p2.exe" ]; then p2="$p2.exe"; fi\n'
             '            if "$p2" > "$RUNNER_TEMP/rust2-noarg.txt"; then echo "rust: port2 exits 0 with no argument";'
             ' false; fi\n'
             '            test ! -s "$RUNNER_TEMP/rust2-noarg.txt"\n'
             '          else\n'
             '            echo "no port in bench/rust"\n'
             '          fi\n')
TS_PORT_STEP = ('      - name: port ts (only if bench/ts exists)\n'
                '        run: |\n'
                '          if [ -d bench/ts ]; then\n'
                '            (cd bench/ts && node main.ts "$RUNNER_TEMP/fixtures.json") > "$RUNNER_TEMP/ts.json"\n'
                '            $PY tests/unit/test_export_reference.py --compare "$RUNNER_TEMP/reference.json" "$RUNNER_TEMP/ts.json"\n'
                '            if (cd bench/ts && node main.ts) > "$RUNNER_TEMP/ts-noarg.txt"; then'
                ' echo "ts: the port exits 0 with no argument"; false; fi\n'
                '            test ! -s "$RUNNER_TEMP/ts-noarg.txt"\n'
                '            (cd bench/ts && node test.ts "$RUNNER_TEMP/fixtures.json" "$RUNNER_TEMP/reference.json")\n'
                '          else\n'
                '            echo "no port in bench/ts"\n'
                '          fi\n')
CARGO_TOML = (b'[package]\nname = "aieos-bench-port"\nversion = "0.1.0"\nedition = "2021"\npublish = false\n'
              b'autobins = false\nautoexamples = false\nautotests = false\nautobenches = false\n\n'
              b'[lib]\npath = "src/lib.rs"\ntest = false\ndoctest = false\n\n'
              b'[[bin]]\nname = "port"\npath = "src/main.rs"\ntest = false\n\n'
              b'[[bin]]\nname = "port2"\npath = "src/round2_main.rs"\ntest = false\n\n'
              b'[[test]]\nname = "port_test"\npath = "tests/port_test.rs"\nharness = false\n\n'
              b'[[test]]\nname = "port2_test"\npath = "tests/port2_test.rs"\nharness = false\n')
BENCH_RUST = REPO / 'bench' / 'rust'
# TASK-048 AC8: each cargo verb's count per job after round 2's lines (one clippy and one build; two runs and two
# tests, one per round).
RUST_VERB_COUNT = {'clippy': 1, 'build': 1, 'run': 2, 'test': 2}


class RustStepTests(unittest.TestCase):
    def test_rust_step(self):
        """TASK-045 AC8: in each job the rust step runs exactly the pinned lines under its one guard, with
        CARGO_NET_OFFLINE and CARGO_TARGET_DIR set before the first cargo command, and every build, lint, run and test
        command locked and offline; no cargo install, add, update or fetch and no rustup."""
        for job in jobs():
            name = '      - name: port rust (only if bench/rust exists)\n        run: |\n'
            self.assertEqual(job.count(name), 1)
            self.assertEqual(job.count(name + RUST_STEP), 1)
            self.assertLess(job.index('export CARGO_NET_OFFLINE=true CARGO_TARGET_DIR='), job.index('cargo --version'))
            for verb in ('clippy', 'build', 'run', 'test'):
                self.assertEqual(job.count('cargo %s --locked --offline --release' % verb), RUST_VERB_COUNT[verb], verb)
                self.assertEqual(job.count('cargo %s ' % verb) - job.count('cargo %s --version' % verb),
                                 RUST_VERB_COUNT[verb], verb)
        text = workflow()
        for word in ('cargo install', 'cargo add', 'cargo update', 'cargo fetch', 'cargo generate-lockfile', 'rustup',
                     'RUSTFLAGS', 'RUSTC_WRAPPER', '--target-dir', '--config'):
            self.assertNotIn(word, text)

    def test_ts_and_go_steps_kept(self):
        """TASK-045 AC8: in each job the TypeScript type-check and port steps and the Go step are the bytes of
        base_commit."""
        for job in jobs():
            self.assertEqual(job.count(TS_CHECK_STEP), 1)
            self.assertEqual(job.count(TS_PORT_STEP), 1)
            self.assertEqual(job.count('      - name: port go (only if bench/go exists)\n        run: |\n' + GO_STEP), 1)

    def test_cargo_files(self):
        """TASK-045 AC8: when bench/rust exists, Cargo.toml is exactly AC3's bytes, Cargo.lock is lock version 4 with
        the one package and no source, checksum or dependencies line, and the file set is AC3's: no build.rs, no .cargo
        folder, only src/*.rs, tests/port_test.rs and at most one README.md beside the two Cargo files."""
        if not BENCH_RUST.is_dir():
            return
        self.assertEqual((BENCH_RUST / 'Cargo.toml').read_bytes(), CARGO_TOML)
        lock = (BENCH_RUST / 'Cargo.lock').read_bytes().decode('ascii').split('\n')
        self.assertIn('version = 4', lock)
        self.assertEqual(lock.count('[[package]]'), 1)
        self.assertIn('name = "aieos-bench-port"', lock)
        self.assertIn('version = "0.1.0"', lock)
        self.assertFalse([ln for ln in lock if ln.startswith(('source', 'checksum', 'dependencies'))])
        files = sorted(p.relative_to(BENCH_RUST).as_posix() for p in BENCH_RUST.rglob('*') if p.is_file())
        allowed = [f for f in files if f in ('Cargo.toml', 'Cargo.lock', 'tests/port_test.rs', 'tests/port2_test.rs',
                                             'README.md')
                   or (f.startswith('src/') and f.endswith('.rs') and f.count('/') == 1)]
        self.assertEqual(files, allowed)
        self.assertIn('src/lib.rs', files)
        self.assertIn('src/main.rs', files)
        self.assertIn('tests/port_test.rs', files)

    def test_naming(self):
        """TASK-045 AC10: every test of this class names the AC it stands for in its docstring."""
        for name in unittest.TestLoader().getTestCaseNames(RustStepTests):
            self.assertRegex(getattr(RustStepTests, name).__doc__ or '', r'^TASK-045 AC\d+', name)


# TASK-046 AC6: the hardening pins (decisions D-890, D-891): the three port folders required, the TypeScript and Go
# file sets, tsconfig.json's and Cargo.lock's bytes, and TASK-045 AC3's forbidden source forms over bench/rust.
BENCH_TS = REPO / 'bench' / 'ts'
TS_FILES = ['bytes.ts', 'export.ts', 'governor.ts', 'json.ts', 'main.ts', 'node.d.ts', 'records.ts', 'resume_check.ts',
            'test.ts', 'tsconfig.json']
GO_FILES = ['export.go', 'go.mod', 'governor.go', 'json.go', 'main.go', 'port_test.go', 'records.go', 'resume.go',
            'round2', 'round2/document.go', 'round2/eventlog.go', 'round2/json.go', 'round2/logcheck.go',
            'round2/port2.go', 'round2/pytext.go', 'round2/records.go', 'round2/recovery.go', 'round2/round2_test.go']
TSCONFIG = (b'{\n  "compilerOptions": {\n    "noEmit": true,\n    "strict": true,\n    "erasableSyntaxOnly": true,\n'
            b'    "allowImportingTsExtensions": true,\n    "module": "preserve",\n    "moduleResolution": "bundler",\n'
            b'    "moduleDetection": "force",\n    "target": "es2022",\n    "lib": ["es2022"],\n    "types": [],\n'
            b'    "verbatimModuleSyntax": true\n  },\n  "include": ["*.ts"]\n}\n')
CARGO_LOCK = (b'# This file is automatically @generated by Cargo.\n# It is not intended for manual editing.\nversion = 4\n\n'
              b'[[package]]\nname = "aieos-bench-port"\nversion = "0.1.0"\n')
RUST_FORBIDDEN = ('unsafe', 'extern', '#![feature', '#[path', 'include!', 'include_str!', 'include_bytes!', 'env!',
                  'option_env!', 'std::process', 'std::net')
RUST_ALLOWED_ITEM = {'std::env': '::args', 'std::fs': '::read'}


def _word_char(ch):
    return ch.isalnum() or ch == '_'


def forbidden_forms(text):
    """Returns the forms of TASK-045 AC3 found in the text as whole words: each of RUST_FORBIDDEN not preceded (and,
    when it ends in a letter, not followed) by a word character, and any std::env or std::fs not preceded by a word
    character unless it is followed by exactly the item of RUST_ALLOWED_ITEM and then a non-word character (so
    `use std::env;` is a hit; a grouped import such as `use std::{env, fs}` is not caught, a limit). The module
    imports no re, so the match is written out (TASK-039 AC4)."""
    found = []
    for form in RUST_FORBIDDEN + tuple(RUST_ALLOWED_ITEM):
        start = text.find(form)
        while start != -1:
            end = start + len(form)
            before = text[start - 1] if start else ''
            after = text[end] if end < len(text) else ''
            if form in RUST_ALLOWED_ITEM:
                tail = end + len(RUST_ALLOWED_ITEM[form])
                allowed = (text.startswith(RUST_ALLOWED_ITEM[form], end)
                           and not (tail < len(text) and _word_char(text[tail])))
                hit = not _word_char(before) and not allowed
            else:
                hit = not _word_char(before) and not (_word_char(form[-1]) and _word_char(after))
            if hit:
                found.append(form)
                break
            start = text.find(form, start + 1)
    return found


def file_set(folder):
    return sorted(p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() or p.is_dir())


class HardeningTests(unittest.TestCase):
    def test_port_folders_exist(self):
        """TASK-046 AC6: bench/ts, bench/go and bench/rust each exist as a folder, so no port pin passes vacuously."""
        for folder in (BENCH_TS, BENCH_GO, BENCH_RUST):
            self.assertTrue(folder.is_dir(), folder.name)

    def test_ts_and_go_file_sets(self):
        """TASK-046 AC6: bench/ts holds exactly its ten files and bench/go exactly its eight round-1 files and its one
        subfolder round2 with round 2's nine files."""
        self.assertEqual(file_set(BENCH_TS), TS_FILES)
        self.assertEqual(file_set(BENCH_GO), GO_FILES)

    def test_pinned_bytes(self):
        """TASK-046 AC6: bench/ts/tsconfig.json and bench/rust/Cargo.lock are exactly their accepted bytes."""
        self.assertEqual((BENCH_TS / 'tsconfig.json').read_bytes(), TSCONFIG)
        self.assertEqual((BENCH_RUST / 'Cargo.lock').read_bytes(), CARGO_LOCK)

    def test_rust_forbidden_forms(self):
        """TASK-046 AC6: no .rs file of bench/rust holds a forbidden form of TASK-045 AC3, and the scan finds each
        form in a sample that holds it."""
        files = sorted(BENCH_RUST.rglob('*.rs'))
        self.assertTrue(files)
        for path in files:
            self.assertEqual(forbidden_forms(path.read_bytes().decode('utf-8')), [], path.name)
        for sample in ('unsafe { }', 'extern "C" {}', 'extern crate x;', '#![feature(x)]', '#[path = "x.rs"]',
                       'include!("x")', 'include_str!("x")', 'include_bytes!("x")', 'env!("X")', 'option_env!("X")',
                       'std::process::exit(0)', 'std::net::TcpStream', 'std::env::var("X")', 'std::fs::write(p, b)',
                       'use std::env;', 'use std::fs;', 'std::env::args_os()', 'std::fs::read_to_string(p)'):
            self.assertTrue(forbidden_forms(sample), sample)
        self.assertEqual(forbidden_forms('std::env::args() std::fs::read(p)'), [])

    def test_naming(self):
        """TASK-046 AC10: every test of this class names the AC it stands for in its docstring."""
        for name in unittest.TestLoader().getTestCaseNames(HardeningTests):
            self.assertRegex(getattr(HardeningTests, name).__doc__ or '', r'^TASK-046 AC\d+', name)


# TASK-048 AC8: round 2's pins (decisions D-921 B3, B4; D-926 C2): bench/rust's exact file set after round 2, and in
# each job the rust step's lines in their order, each binary and test target named once.
RUST_FILES = ['Cargo.lock', 'Cargo.toml', 'src', 'src/document.rs', 'src/eventlog.rs', 'src/governor.rs', 'src/json.rs',
              'src/lib.rs', 'src/main.rs', 'src/pyval.rs', 'src/records.rs', 'src/records2.rs', 'src/recovery.rs',
              'src/resume_check.rs', 'src/round2.rs', 'src/round2_main.rs', 'src/sha256.rs', 'tests', 'tests/port2_test.rs',
              'tests/port_test.rs']


class Round2RustTests(unittest.TestCase):
    def test_rust_file_set(self):
        """TASK-048 AC8: bench/rust holds exactly its round-1 files and round 2's six new modules and test file, with
        no other file or folder."""
        self.assertEqual(file_set(BENCH_RUST), RUST_FILES)

    def test_rust_step_order(self):
        """TASK-048 AC8: in each job the round-1 run, compare, probe and test lines come before round 2's run, compare,
        test and probe lines; each binary (--bin port, --bin port2) and test target (--test port_test, --test
        port2_test) is named once, and no cargo run or test line names neither."""
        for job in jobs():
            marks = ['--bin port --', 'rust.json"\n', 'rust-noarg.txt"\n', '--test port_test --', '--bin port2 --',
                     'rust2.json"\n', '--test port2_test --', 'rust2-noarg.txt"\n']
            order = [job.index(m) for m in marks]
            self.assertEqual(order, sorted(order))
            for name in ('--bin port --', '--bin port2 --', '--test port_test --', '--test port2_test --'):
                self.assertEqual(job.count(name), 1, name)
            self.assertNotIn('--quiet -- "', job)
            self.assertNotIn('--release -- "', job)

    def test_cargo_toml(self):
        """TASK-048 AC8: Cargo.toml is exactly the round-1 bytes with one [[bin]] block (port2) and one [[test]] block
        (port2_test) added, and Cargo.lock keeps TASK-046's bytes."""
        self.assertEqual((BENCH_RUST / 'Cargo.toml').read_bytes(), CARGO_TOML)
        self.assertEqual(CARGO_TOML.count(b'[[bin]]'), 2)
        self.assertEqual(CARGO_TOML.count(b'[[test]]'), 2)
        self.assertEqual((BENCH_RUST / 'Cargo.lock').read_bytes(), CARGO_LOCK)

    def test_naming(self):
        """TASK-048 AC10: every test of this class names the AC it stands for in its docstring."""
        for name in unittest.TestLoader().getTestCaseNames(Round2RustTests):
            self.assertRegex(getattr(Round2RustTests, name).__doc__ or '', r'^TASK-048 AC\d+', name)


# TASK-049 AC8: round 2's Go pins (decisions D-938 B2, B4, M1; D-943; D-947): bench/go/round2's exact file set, the
# round-1 files' bytes at base_commit, the two whole-file copies of round-1 files, and in each job the go step's
# round-1 lines before its round-2 lines.
BENCH_GO2 = BENCH_GO / 'round2'
GO2_FILES = ['document.go', 'eventlog.go', 'json.go', 'logcheck.go', 'port2.go',
             'pytext.go', 'records.go', 'recovery.go', 'round2_test.go']
GO_ROUND1_SHA256 = {
    'export.go': '66f72d6655ac8b1a5bfa6f58ae8bff2998b8ffb98dde3f69600e34bc9b91fb6b',
    'go.mod': 'c4e8c0e48ccfd033e30a86af3643489c18371768efd3182739fef34b98a8d808',
    'governor.go': 'e5e1eeb49932d519f0777650cb9c9fb736362782dea38f906199ad160e0d7fd0',
    'json.go': '001eaa6b68efb291152d50014190df0d8fbcadbe9c9a3bd8c150d5f42a7b1429',
    'main.go': '67c2377dd041dc209a427cff8706199d0cb00f10934c1782cfc23de7751d7627',
    'port_test.go': '1449f90c899bd745f5ec4303002e48cf17b65dfbb88a36cf9697ff68044212e7',
    'records.go': '26ff9da5e0adf4bc5128c48ec73f1d65d84923fd10c0cd7b6253d2cf900d42c6',
    'resume.go': '89da51ba9865cbafec5005a7d4329c1d6d0f8b3a5ea5562a09573527b652e02e',
}
GO_COPIES = ('json.go', 'records.go')


_K = [int(x, 16) for x in (
    '428a2f98 71374491 b5c0fbcf e9b5dba5 3956c25b 59f111f1 923f82a4 ab1c5ed5 d807aa98 12835b01 243185be 550c7dc3 '
    '72be5d74 80deb1fe 9bdc06a7 c19bf174 e49b69c1 efbe4786 0fc19dc6 240ca1cc 2de92c6f 4a7484aa 5cb0a9dc 76f988da '
    '983e5152 a831c66d b00327c8 bf597fc7 c6e00bf3 d5a79147 06ca6351 14292967 27b70a85 2e1b2138 4d2c6dfc 53380d13 '
    '650a7354 766a0abb 81c2c92e 92722c85 a2bfe8a1 a81a664b c24b8b70 c76c51a3 d192e819 d6990624 f40e3585 106aa070 '
    '19a4c116 1e376c08 2748774c 34b0bcb5 391c0cb3 4ed8aa4a 5b9cca4f 682e6ff3 748f82ee 78a5636f 84c87814 8cc70208 '
    '90befffa a4506ceb bef9a3f7 c67178f2').split()]


def sha256_hex(path):
    """FIPS 180-4 SHA-256 of a file's bytes, written out because TASK-039 AC4 pins this module's imports (no
    hashlib); checked against known digests by test_sha256_known_values."""
    return _sha256(path.read_bytes())


def _sha256(data):
    def rot(x, n):
        return ((x >> n) | (x << (32 - n))) & 0xffffffff
    h = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]
    m = data + b'\x80' + b'\x00' * ((55 - len(data)) % 64) + (len(data) * 8).to_bytes(8, 'big')
    for i in range(0, len(m), 64):
        w = [int.from_bytes(m[i + 4 * j:i + 4 * j + 4], 'big') for j in range(16)]
        for j in range(16, 64):
            s0 = rot(w[j - 15], 7) ^ rot(w[j - 15], 18) ^ (w[j - 15] >> 3)
            s1 = rot(w[j - 2], 17) ^ rot(w[j - 2], 19) ^ (w[j - 2] >> 10)
            w.append((w[j - 16] + s0 + w[j - 7] + s1) & 0xffffffff)
        a, b, c, d, e, f, g, k = h
        for j in range(64):
            t1 = (k + (rot(e, 6) ^ rot(e, 11) ^ rot(e, 25)) + ((e & f) ^ (~e & g)) + _K[j] + w[j]) & 0xffffffff
            t2 = ((rot(a, 2) ^ rot(a, 13) ^ rot(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) & 0xffffffff
            a, b, c, d, e, f, g, k = (t1 + t2) & 0xffffffff, a, b, c, (d + t1) & 0xffffffff, e, f, g
        h = [(x + y) & 0xffffffff for x, y in zip(h, (a, b, c, d, e, f, g, k))]
    return ''.join('%08x' % x for x in h)


class Round2GoTests(unittest.TestCase):
    def test_go_round2_file_set(self):
        """TASK-049 AC8: bench/go/round2 holds exactly round 2's nine .go files, with no go.mod, go.sum, vendor
        folder or other file or folder."""
        self.assertEqual(file_set(BENCH_GO2), GO2_FILES)
        for name in ('go.mod', 'go.sum', 'vendor'):
            self.assertFalse((BENCH_GO2 / name).exists(), name)

    def test_go_round1_files_unchanged(self):
        """TASK-049 AC8: each of bench/go's eight round-1 files is exactly its bytes at base_commit."""
        for name, digest in GO_ROUND1_SHA256.items():
            self.assertEqual(sha256_hex(BENCH_GO / name), digest, name)

    def test_sha256_known_values(self):
        """TASK-049 AC8: the written-out SHA-256 gives the FIPS 180-4 digests of the empty input, 'abc' and the
        two-block 'abcdbcde...' message, and of a 64-byte and a 1000-byte input across the padding boundaries."""
        self.assertEqual(_sha256(b''), 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
        self.assertEqual(_sha256(b'abc'), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
        self.assertEqual(_sha256(b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq'),
                         '248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1')
        self.assertEqual(_sha256(b'a' * 64), 'ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb')
        self.assertEqual(_sha256(b'a' * 1000), '41edece42d63e8d9bf515a9ba6932e1c20cbc9f5a5d134645adb5db1b9737ea3')

    def test_go_whole_file_copies(self):
        """TASK-049 AC8: each whole-file copy under bench/go/round2 is byte-equal to its round-1 file (D-938 M1)."""
        for name in GO_COPIES:
            self.assertEqual((BENCH_GO2 / name).read_bytes(), (BENCH_GO / name).read_bytes(), name)

    def test_go_step_order(self):
        """TASK-049 AC8: in each job the go step's round-1 build, run, compare, probe and test lines come before
        round 2's vet and build, run, compare, probe and test lines, and each round-2 command appears once."""
        for job in jobs():
            marks = ['go/port.exe" .)', 'go.json"\n', 'go-noarg.txt"\n', 'go test -count=1 . -args',
                     'go vet ./round2', 'go2.json"\n', 'go2-noarg.txt"\n', 'go test -count=1 ./round2 -args']
            order = [job.index(m) for m in marks]
            self.assertEqual(order, sorted(order))
            for line in ('go vet ./round2', 'go build -trimpath -o "$RUNNER_TEMP/go/port2.exe" ./round2',
                         'go test -count=1 ./round2 -args'):
                self.assertEqual(job.count(line), 1, line)

    def test_naming(self):
        """TASK-049 AC10: every test of this class names the AC it stands for in its docstring."""
        for name in unittest.TestLoader().getTestCaseNames(Round2GoTests):
            self.assertRegex(getattr(Round2GoTests, name).__doc__ or '', r'^TASK-049 AC\d+', name)


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
