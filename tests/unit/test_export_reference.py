"""The stack benchmark's reference export and its tests (TASK-041; docs/plan/m4-exit-review.md §6, line 70).

The reference: run from the repository root as `python tests/unit/test_export_reference.py --root tests/conformance`,
it reads every .py file of the two frozen fixture folders of round 1, fixtures (the governor's 19 files) and fixtures_rc
(the Resume Check's 11 files), as bytes with pathlib (a __pycache__ folder inside one, which the CI channel's build step
makes, is passed over; any other entry that is not a .py file fails closed), unwraps each with the bootstrap's own
reader aieos_bootstrap.conformance.unwrap, and calls, for each case, aieos_bootstrap.governor.evaluate(request, inputs,
records) or aieos_bootstrap.resume_check.check(inputs), each argument a deep copy, as the conformance runner calls them.
It prints to standard output the canonical text (conformance-files.md section 2; conformance.canonical_text) of one
object whose keys are "<folder>/<file stem>" and whose values are the lists of that file's case records in case order:
the decision records every language port of the benchmark must print byte for byte. RISK-01 (the risk folder) is not in
it: the derivation derive_inputs is not ported in round 1 (decision D-794).

The closed placeholder list (decision D-794 C2): exactly one value path, engine_identity.python in the Resume Check's
records, is written as the text "<engine>" by the reference and by every port; nothing else is replaced.

The pin: REFERENCE_SHA256 is the SHA-256 of the document at this task's commit. A later task that changes the
governor's or the Resume Check's decision code, or a frozen fixture of round 1, also changes this pin, pin-only, with
one exact new value (conformance-files.md section 8 (i) reading), and its contract says so. `--check` fails when the
document's hash differs from the pin; the benchmark workflow runs it on Linux and Windows, and the unit tests check
the pin at every push on Linux. The benchmark workflow (.github/workflows/aieos-bench.yml) is where this module runs as
a script, by design: each job runs the reference export right after the fixture export, and its first run with that
step was the workflow's run 2, at TASK-041's landing (TASK-043 AC8).

`--compare <a> <b>` compares two documents byte for byte and names the first key (and case) that differs.

It fails closed: on any other argument form, a missing folder, an entry that is not a .py file, a file the reader
refuses, a call that raises or a record that is not an object, it exits non-zero and prints nothing to standard
output, since the whole document is built before anything is written. It runs no process, reads no network, clock or
environment, and writes no file: the benchmark workflow redirects its standard output into the job's temporary folder.
It lives in this test module because the CI channel's deterministic_rule lets a module under tests/ import only the
standard library and aieos_bootstrap and refuses every file write (decision D-773). It names the Resume Check fixture
folder, so tests/integration/test_conformance_rc_set.py allows it by name. Its results are advisory and feed nothing
(A29, A31).
"""

import copy
import hashlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
if str(REPO / 'src') not in sys.path:
    sys.path.insert(0, str(REPO / 'src'))

from aieos_bootstrap import conformance, governor, resume_check  # noqa: E402

GOVERNOR_FOLDER = 'fixtures'
RC_FOLDER = 'fixtures_rc'
FOLDERS = (GOVERNOR_FOLDER, RC_FOLDER)
PLACEHOLDER = '<engine>'
PLACEHOLDER_PATHS = ((RC_FOLDER, ('engine_identity', 'python')),)
REFERENCE_SHA256 = '01aeec8f12bcf11303e1ec08c1d87d866a7aa823066fe9c5f5eeace4c0ac6443'
USAGE = ('usage: test_export_reference.py --root <folder> [--check]\n'
         '       test_export_reference.py --compare <reference file> <port file>')


class ReferenceError(Exception):
    """A fixture folder, file, call or document is not in the form the reference reads."""


def listing(root):
    """The round-1 fixture folders under root as {folder: [(name, kind, bytes or None)]}, kind "dir", "file" or
    "other"; a missing folder is left out, so that document() refuses it."""
    out = {}
    for folder in FOLDERS:
        d = Path(root) / folder
        if d.is_dir():
            out[folder] = [(p.name, 'dir' if p.is_dir() else 'file' if p.is_file() else 'other',
                            p.read_bytes() if p.is_file() else None) for p in sorted(d.iterdir())]
    return out


def placeholder(folder, record):
    """The record with the closed placeholder list applied (a copy)."""
    rec = copy.deepcopy(record)
    for f, path in PLACEHOLDER_PATHS:
        if f != folder:
            continue
        node = rec
        for key in path[:-1]:
            node = node.get(key) if isinstance(node, dict) else None
        if isinstance(node, dict) and path[-1] in node:
            node[path[-1]] = PLACEHOLDER
    return rec


def case_records(folder, value):
    """The decision records of one unwrapped fixture's cases, in case order."""
    out = []
    for n, case in enumerate(value['cases'], 1):
        try:
            if folder == GOVERNOR_FOLDER:
                rec = governor.evaluate(copy.deepcopy(case['request']), copy.deepcopy(case['inputs']),
                                        copy.deepcopy(case['records']))
            else:
                rec = resume_check.check(copy.deepcopy(case['inputs']))
        except Exception as e:
            raise ReferenceError('case %d: the call raised %s' % (n, type(e).__name__)) from None
        if not isinstance(rec, dict):
            raise ReferenceError('case %d: the record is not an object' % n)
        out.append(placeholder(folder, rec))
    return out


def document(entries):
    """The reference document's bytes (canonical text, ASCII, LF) for a listing() result; ReferenceError otherwise."""
    obj = {}
    for folder in FOLDERS:
        if folder not in entries:
            raise ReferenceError('missing fixture folder ' + folder)
        for name, kind, data in entries[folder]:
            if kind == 'dir' and name == '__pycache__':
                continue
            if kind != 'file' or not name.endswith('.py') or name == '.py':
                raise ReferenceError('not a .py file: %s/%s' % (folder, name))
            try:
                value = conformance.unwrap(data)
            except conformance.Malformed as e:
                raise ReferenceError('%s/%s: %s' % (folder, name, e)) from None
            if not isinstance(value, dict) or not isinstance(value.get('cases'), list) or not value['cases']:
                raise ReferenceError('%s/%s: no cases' % (folder, name))
            try:
                obj[folder + '/' + name[:-3]] = case_records(folder, value)
            except ReferenceError as e:
                raise ReferenceError('%s/%s: %s' % (folder, name, e)) from None
    try:
        out = conformance.canonical_text(obj)
    except conformance.Malformed as e:
        raise ReferenceError(str(e)) from None
    if b'\r' in out or any(b > 127 for b in out):
        raise ReferenceError('the document is not ASCII with LF line ends')
    return out


def reference(root):
    """The reference document's bytes for the fixture folders under root."""
    return document(listing(root))


def first_difference(a, b):
    """None when the two documents are byte-equal; otherwise the first key (and case) whose text differs, or "not a
    reference document" when either is not one object of lists in the canonical form."""
    if a == b:
        return None
    try:
        da, db = json.loads(a.decode('ascii')), json.loads(b.decode('ascii'))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return 'not a reference document'
    for d, raw in ((da, a), (db, b)):
        if not isinstance(d, dict) or not all(isinstance(v, list) for v in d.values()):
            return 'not a reference document'
        try:
            if conformance.canonical_text(d) != raw:
                return 'not a reference document'
        except conformance.Malformed:
            return 'not a reference document'
    for key in sorted(set(da) | set(db)):
        if key not in da or key not in db:
            return 'key %s: present in one document only' % key
        for i in range(max(len(da[key]), len(db[key]))):
            if i >= len(da[key]) or i >= len(db[key]):
                return 'key %s: case %d: present in one document only' % (key, i + 1)
            if conformance.canonical_text(da[key][i]) != conformance.canonical_text(db[key][i]):
                return 'key %s: case %d: differs' % (key, i + 1)
    return 'the documents differ'


def main(argv, out=None, err=None):
    """The command line: `--root <folder>` or `--root <folder> --check`, or `--compare <a> <b>`."""
    out = sys.stdout.buffer if out is None else out
    err = sys.stderr if err is None else err
    if len(argv) == 3 and argv[0] == '--compare':
        try:
            a, b = Path(argv[1]).read_bytes(), Path(argv[2]).read_bytes()
        except OSError as e:
            print('compare failed: %s' % e, file=err)
            return 2
        diff = first_difference(a, b)
        if diff is None:
            return 0
        print(diff, file=err)
        return 1
    if not (len(argv) == 2 and argv[0] == '--root') and not (len(argv) == 3 and argv[0] == '--root'
                                                            and argv[2] == '--check'):
        print(USAGE, file=err)
        return 2
    try:
        doc = reference(argv[1])
    except (ReferenceError, OSError) as e:
        print('reference failed: %s' % e, file=err)
        return 1
    if len(argv) == 3 and hashlib.sha256(doc).hexdigest() != REFERENCE_SHA256:
        print('reference check failed: the document is not the pinned one', file=err)
        return 1
    out.write(doc)
    return 0


# ---------------------------------------------------------------------------------------------------------------
# Tests

ROOT = REPO / 'tests' / 'conformance'


def fixture_bytes(value):
    return b"DATA = r'''" + conformance.canonical_text(value) + b"'''\n"


def real_entries():
    return listing(ROOT)


class ReferenceTests(unittest.TestCase):
    def test_document(self):
        """TASK-041 AC1, AC5: the real folders give 30 keys and 32 case records, in case order, ASCII and LF."""
        doc = reference(ROOT)
        value = json.loads(doc.decode('ascii'))
        self.assertEqual(len(value), 30)
        self.assertEqual(sorted(k.split('/')[0] for k in value), [GOVERNOR_FOLDER] * 19 + [RC_FOLDER] * 11)
        self.assertEqual(sum(len(v) for v in value.values()), 32)
        self.assertEqual(len(value['fixtures/acc_13']), 3)
        self.assertEqual({k.split('/')[0] for k in value}, set(FOLDERS))
        self.assertTrue(doc.endswith(b'\n'))
        self.assertNotIn(b'\r', doc)

    def test_calls_as_the_runner(self):
        """TASK-041 AC1: each record equals the call the runner makes for that case, with the placeholder."""
        entries = real_entries()
        value = json.loads(reference(ROOT).decode('ascii'))
        for folder in FOLDERS:
            for name, kind, data in entries[folder]:
                if kind != 'file':
                    continue
                fx = conformance.unwrap(data)
                for n, case in enumerate(fx['cases']):
                    if folder == GOVERNOR_FOLDER:
                        want = governor.evaluate(copy.deepcopy(case['request']), copy.deepcopy(case['inputs']),
                                                 copy.deepcopy(case['records']))
                    else:
                        want = resume_check.check(copy.deepcopy(case['inputs']))
                        want['engine_identity']['python'] = PLACEHOLDER
                    self.assertEqual(value[folder + '/' + name[:-3]][n], want, (folder, name, n))

    def test_placeholder_list_is_closed(self):
        """TASK-041 AC2: only engine_identity.python of the Resume Check records depends on the interpreter's version."""
        def flat(v, prefix=()):
            if isinstance(v, dict):
                for k in v:
                    yield from flat(v[k], prefix + (k,))
            elif isinstance(v, list):
                for i, x in enumerate(v):
                    yield from flat(x, prefix + (i,))
            else:
                yield prefix, v

        def raw(entries):
            obj = {}
            for folder in FOLDERS:
                for name, kind, data in entries[folder]:
                    if kind != 'file':
                        continue
                    fx = conformance.unwrap(data)
                    recs = []
                    for case in fx['cases']:
                        if folder == GOVERNOR_FOLDER:
                            recs.append(governor.evaluate(copy.deepcopy(case['request']),
                                                          copy.deepcopy(case['inputs']), copy.deepcopy(case['records'])))
                        else:
                            recs.append(resume_check.check(copy.deepcopy(case['inputs'])))
                    obj[folder + '/' + name[:-3]] = recs
            return obj

        entries = real_entries()
        first = dict(flat(raw(entries)))
        with mock.patch.object(resume_check, '_python_version', return_value='0.0.0'):
            second = dict(flat(raw(entries)))
            doc2 = reference(ROOT)
        self.assertEqual(set(first), set(second))
        changed = {(k[0].split('/')[0],) + tuple(x for x in k[2:]) for k in first if first[k] != second[k]}
        self.assertEqual(changed, {(RC_FOLDER,) + path for f, path in PLACEHOLDER_PATHS})
        self.assertEqual(doc2, reference(ROOT))

    def test_byte_identity_and_pin(self):
        """TASK-041 AC3: two builds are byte-equal, ASCII, LF only, end in LF, and match REFERENCE_SHA256."""
        a, b = reference(ROOT), reference(ROOT)
        self.assertEqual(a, b)
        self.assertTrue(all(x < 128 for x in a))
        self.assertNotIn(b'\r', a)
        self.assertTrue(a.endswith(b'\n'))
        self.assertEqual(hashlib.sha256(a).hexdigest(), REFERENCE_SHA256)

    def test_fails_closed(self):
        """TASK-041 AC5: a missing folder, a non-.py entry, a bad file, a raising call and a non-object record."""
        good = real_entries()
        cases = []
        missing = dict(good)
        del missing[RC_FOLDER]
        cases.append((missing, 'missing fixture folder'))
        extra = dict(good)
        extra[RC_FOLDER] = good[RC_FOLDER] + [('notes.txt', 'file', b'x')]
        cases.append((extra, 'not a .py file'))
        other = dict(good)
        other[RC_FOLDER] = good[RC_FOLDER] + [('sub', 'dir', None)]
        cases.append((other, 'not a .py file'))
        bad = dict(good)
        bad[RC_FOLDER] = [('rc_99.py', 'file', b'x = 1\n')]
        cases.append((bad, 'rc_99.py'))
        nocase = dict(good)
        nocase[RC_FOLDER] = [('rc_98.py', 'file', fixture_bytes({'cases': []}))]
        cases.append((nocase, 'no cases'))
        for entries, text in cases:
            with self.assertRaises(ReferenceError) as cm:
                document(entries)
            self.assertIn(text, str(cm.exception))
        with mock.patch.object(resume_check, 'check', side_effect=ValueError('x')):
            with self.assertRaises(ReferenceError) as cm:
                document(good)
            self.assertIn('the call raised ValueError', str(cm.exception))
        with mock.patch.object(governor, 'evaluate', return_value=['not', 'an', 'object']):
            with self.assertRaises(ReferenceError) as cm:
                document(good)
            self.assertIn('not an object', str(cm.exception))
        pyc = dict(good)
        pyc[RC_FOLDER] = good[RC_FOLDER] + [('__pycache__', 'dir', None)]
        self.assertEqual(document(pyc), document(good))

    def test_main(self):
        """TASK-041 AC3, AC5: the command line prints the document, checks the pin, and refuses other forms."""
        out, err = io.BytesIO(), io.StringIO()
        self.assertEqual(main(['--root', str(ROOT)], out, err), 0)
        self.assertEqual(out.getvalue(), reference(ROOT))
        out, err = io.BytesIO(), io.StringIO()
        self.assertEqual(main(['--root', str(ROOT), '--check'], out, err), 0)
        self.assertEqual(out.getvalue(), reference(ROOT))
        for argv in ([], ['--root'], ['--root', str(ROOT), '--other'], ['--root', str(ROOT), '--check', 'x'],
                     ['--check', str(ROOT)], ['--compare', 'a'], ['x']):
            out, err = io.BytesIO(), io.StringIO()
            self.assertEqual(main(argv, out, err), 2, argv)
            self.assertEqual(out.getvalue(), b'', argv)
        out, err = io.BytesIO(), io.StringIO()
        self.assertEqual(main(['--root', str(REPO / 'no-such-folder')], out, err), 1)
        self.assertEqual(out.getvalue(), b'')
        with mock.patch.object(sys.modules[__name__], 'REFERENCE_SHA256', '0' * 64):
            out, err = io.BytesIO(), io.StringIO()
            self.assertEqual(main(['--root', str(ROOT), '--check'], out, err), 1)
            self.assertEqual(out.getvalue(), b'')
            self.assertIn('not the pinned one', err.getvalue())


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.doc = conformance.canonical_text({'fixtures/a': [{'x': 1}, {'x': 2}], 'fixtures_rc/b': [{'y': 'z'}]})

    def test_equal(self):
        """TASK-041 AC4: byte-equal documents give no difference."""
        self.assertIsNone(first_difference(self.doc, self.doc))

    def test_one_byte(self):
        """TASK-041 AC4: a one-byte difference names the key and the case."""
        other = conformance.canonical_text({'fixtures/a': [{'x': 1}, {'x': 3}], 'fixtures_rc/b': [{'y': 'z'}]})
        self.assertEqual(len(other), len(self.doc))
        self.assertEqual(first_difference(self.doc, other), 'key fixtures/a: case 2: differs')

    def test_missing_and_extra(self):
        """TASK-041 AC4: a missing key, an extra key and a missing case are named."""
        missing = conformance.canonical_text({'fixtures/a': [{'x': 1}, {'x': 2}]})
        self.assertEqual(first_difference(self.doc, missing), 'key fixtures_rc/b: present in one document only')
        extra = conformance.canonical_text({'fixtures/a': [{'x': 1}, {'x': 2}], 'fixtures/c': [],
                                            'fixtures_rc/b': [{'y': 'z'}]})
        self.assertEqual(first_difference(self.doc, extra), 'key fixtures/c: present in one document only')
        short = conformance.canonical_text({'fixtures/a': [{'x': 1}], 'fixtures_rc/b': [{'y': 'z'}]})
        self.assertEqual(first_difference(self.doc, short), 'key fixtures/a: case 2: present in one document only')

    def test_malformed(self):
        """TASK-041 AC4: input that is not a canonical object of lists is "not a reference document"."""
        for bad in (b'', b'{', b'[]\n', b'{"a": 1}\n', self.doc.rstrip(b'\n'), b'\xff\n',
                    json.dumps({'fixtures/a': []}).encode('ascii')):
            self.assertEqual(first_difference(self.doc, bad), 'not a reference document', bad)

    def test_deep_nesting(self):
        """TASK-041 AC4; TASK-043 AC8 (d): a document nested too deep to read is "not a reference document"."""
        deep = b'{"fixtures/a": ' + b'[' * 200000 + b']' * 200000 + b'}\n'
        self.assertEqual(first_difference(self.doc, deep), 'not a reference document')
        self.assertEqual(first_difference(deep, self.doc), 'not a reference document')

    def test_compare_main(self):
        """TASK-041 AC4: --compare exits 0 on equal files, 1 with a message on a difference, 2 on a missing path;
        TASK-043 AC8 (b): a malformed first document is refused as well."""
        out, err = io.BytesIO(), io.StringIO()
        with mock.patch.object(Path, 'read_bytes', side_effect=[self.doc, self.doc]):
            self.assertEqual(main(['--compare', 'a', 'b'], out, err), 0)
        self.assertEqual((out.getvalue(), err.getvalue()), (b'', ''))
        out, err = io.BytesIO(), io.StringIO()
        with mock.patch.object(Path, 'read_bytes', side_effect=[self.doc, b'{']):
            self.assertEqual(main(['--compare', 'a', 'b'], out, err), 1)
        self.assertEqual(out.getvalue(), b'')
        self.assertIn('not a reference document', err.getvalue())
        out, err = io.BytesIO(), io.StringIO()
        with mock.patch.object(Path, 'read_bytes', side_effect=[b'{', self.doc]):
            self.assertEqual(main(['--compare', 'a', 'b'], out, err), 1)
        self.assertEqual(out.getvalue(), b'')
        self.assertIn('not a reference document', err.getvalue())
        out, err = io.BytesIO(), io.StringIO()
        self.assertEqual(main(['--compare', str(REPO / 'no-such-file'), str(REPO / 'no-such-file')], out, err), 2)
        self.assertEqual(out.getvalue(), b'')


class SuiteTests(unittest.TestCase):
    def test_imports(self):
        """TASK-041 AC9: the module imports only the standard library names listed and aieos_bootstrap; TASK-043 AC8
        (a): indented import lines count too, and the built-in import function is not named."""
        text = Path(__file__).read_bytes().decode('utf-8')
        self.assertNotIn('_' + '_import_' + '_', text)
        lines = text.split('\n')
        imports = [ln.strip() for ln in lines if ln.lstrip().startswith(('import ', 'from '))]
        self.assertEqual(imports, ['import copy', 'import hashlib', 'import io', 'import json', 'import sys',
                                   'import unittest', 'from pathlib import Path', 'from unittest import mock',
                                   'from aieos_bootstrap import conformance, governor, resume_check  # noqa: E402'])

    def test_suite_runs_no_export(self):
        """TASK-041 AC10: run_tests.py keeps its three groups, and this module runs the export only under its guard."""
        runner = (REPO / 'tests' / 'run_tests.py').read_bytes().decode('utf-8')
        self.assertEqual(runner.count("GROUPS = ('unit', 'integration', 'property')\n"), 1)
        lines = Path(__file__).read_bytes().decode('utf-8').split('\n')
        guard = lines.index("if __name__ == '__main__':")
        self.assertEqual(lines[guard + 1:], ["    if sys.argv[1:2] in (['--root'], ['--compare']):",
                                              '        sys.exit(main(sys.argv[1:]))', '    unittest.main()', ''])

    def test_workflow_step(self):
        """TASK-041 AC6: each job runs the reference export with --check into the temporary folder, once; TASK-043 AC8
        (c): in each job it is the step right after the fixture export."""
        text = (REPO / '.github' / 'workflows' / 'aieos-bench.yml').read_bytes().decode('utf-8')
        for job in text.split('\n  windows:\n'):
            names = [ln.strip() for ln in job.split('\n') if ln.strip().startswith('- name:')]
            i = names.index('- name: export the frozen fixtures into the temporary folder')
            self.assertEqual(names[i + 1], '- name: reference export (bootstrap decisions over the frozen fixtures)')
        cmd = ('$PY tests/unit/test_export_reference.py --root tests/conformance --check > '
               '"$RUNNER_TEMP/reference.json"')
        self.assertEqual(text.count(cmd), 2)
        self.assertEqual(text.count('- name: reference export (bootstrap decisions over the frozen fixtures)'), 2)
        self.assertEqual(text.count('wc -c "$RUNNER_TEMP/reference.json"'), 2)

    def test_naming(self):
        """TASK-041 AC10: every test of this module names the AC it stands for in its docstring."""
        loader = unittest.TestLoader()
        for case in (ReferenceTests, CompareTests, SuiteTests):
            for name in loader.getTestCaseNames(case):
                doc = getattr(case, name).__doc__ or ''
                self.assertRegex(doc, r'^TASK-041 AC\d+', name)


if __name__ == '__main__':
    if sys.argv[1:2] in (['--root'], ['--compare']):
        sys.exit(main(sys.argv[1:]))
    unittest.main()
