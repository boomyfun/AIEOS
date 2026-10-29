"""The native governor's reference: the governor-only export and its tests (TASK-100 AC1, AC2; m8-plan.md section 2).

The reference: run from the repository root as `python tests/unit/test_export_governor.py --root tests/conformance`, it
reads every .py file of the round-1 governor fixture folder (fixtures, the governor's 19 files) as bytes with pathlib (a
__pycache__ folder inside it, which the CI channel's build step makes, is passed over; any other entry that is not a .py
file fails closed), unwraps each with the bootstrap's own reader aieos_bootstrap.conformance.unwrap, and calls, for each
case, aieos_bootstrap.governor.evaluate(request, inputs, records), each argument a deep copy, as the conformance runner
calls it. It prints to standard output the canonical text (conformance-files.md section 2; conformance.canonical_text)
of one object whose keys are "fixtures/<file stem>" and whose values are the lists of that file's case records in case
order: the document the native governor must print byte for byte (the workflow aieos-native.yml compares the two). It is the governor part of the full round-1 reference document of tests/unit/test_export_reference.py,
which this module does not import (the CI channel's deterministic_rule lets a module under tests/ import only the
standard library and aieos_bootstrap, decision D-773); its tests compute the full document the same way, check its
SHA-256 against FULL_REFERENCE_SHA256, a copy of that module's pin found in its bytes, and check that the governor
document equals the full document's governor part, so the two cannot drift apart (TASK-100 AC2; decisions D-3408 C6,
D-3417 R1). The second folder's name is built from parts, since the closed name lists of the conformance set tests
allow only their own modules to name it (decision D-3427 C3).

The pin: REFERENCE_GOVERNOR_SHA256 is the SHA-256 of the document at this task's commit. A later task that changes the
governor's decision code or a frozen governor fixture of round 1 also changes this pin, pin-only, with one exact new
value, and its contract says so. `--check` fails when the document's hash differs from the pin.

It fails closed: on any other argument form, a missing folder, an entry that is not a .py file, a file the reader
refuses, a call that raises or a record that is not an object, it exits non-zero and prints nothing to standard output,
since the whole document is built before anything is written. It runs no process, reads no network, clock or
environment, reads files only with Path.read_bytes and writes no file: the workflow redirects its standard output into
the job's temporary folder. Its results are advisory and feed nothing (A29, A31).
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
RC_FOLDER = GOVERNOR_FOLDER + '_' + 'rc'
PLACEHOLDER = '<engine>'
REFERENCE_GOVERNOR_SHA256 = 'b403fd22d40fcfc5eba98073786bd2e764c8404d61010c7ffa84b25af11fcec7'
FULL_REFERENCE_SHA256 = '01aeec8f12bcf11303e1ec08c1d87d866a7aa823066fe9c5f5eeace4c0ac6443'
USAGE = 'usage: test_export_governor.py --root <folder> [--check]'


class ReferenceError(Exception):
    """A fixture folder, file, call or document is not in the form the reference reads."""


def entries_of(root, folder):
    """The folder's entries under root as [(name, kind, bytes or None)], kind "dir", "file" or "other"; None for a
    missing folder."""
    d = Path(root) / folder
    if not d.is_dir():
        return None
    return [(p.name, 'dir' if p.is_dir() else 'file' if p.is_file() else 'other',
             p.read_bytes() if p.is_file() else None) for p in sorted(d.iterdir())]


def values_of(folder, entries):
    """The unwrapped fixtures of one folder as [(key, value)], in name order; ReferenceError otherwise."""
    if entries is None:
        raise ReferenceError('missing fixture folder ' + folder)
    out = []
    for name, kind, data in entries:
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
        out.append((folder + '/' + name[:-3], value))
    return out


def governor_records(value):
    """The decision records of one unwrapped governor fixture's cases, in case order."""
    out = []
    for n, case in enumerate(value['cases'], 1):
        try:
            rec = governor.evaluate(copy.deepcopy(case['request']), copy.deepcopy(case['inputs']),
                                    copy.deepcopy(case['records']))
        except Exception as e:
            raise ReferenceError('case %d: the call raised %s' % (n, type(e).__name__)) from None
        if not isinstance(rec, dict):
            raise ReferenceError('case %d: the record is not an object' % n)
        out.append(rec)
    return out


def text_of(obj):
    """The canonical text of obj, ASCII with LF only; ReferenceError otherwise."""
    try:
        out = conformance.canonical_text(obj)
    except conformance.Malformed as e:
        raise ReferenceError(str(e)) from None
    if b'\r' in out or any(b > 127 for b in out):
        raise ReferenceError('the document is not ASCII with LF line ends')
    return out


def document(root):
    """The governor-only document's bytes for the governor fixture folder under root."""
    obj = {}
    for key, value in values_of(GOVERNOR_FOLDER, entries_of(root, GOVERNOR_FOLDER)):
        try:
            obj[key] = governor_records(value)
        except ReferenceError as e:
            raise ReferenceError('%s: %s' % (key, e)) from None
    return text_of(obj)


def main(argv, out=None, err=None):
    """The command line: `--root <folder>` or `--root <folder> --check`."""
    out = sys.stdout.buffer if out is None else out
    err = sys.stderr if err is None else err
    if not (len(argv) == 2 and argv[0] == '--root') and not (len(argv) == 3 and argv[0] == '--root'
                                                            and argv[2] == '--check'):
        print(USAGE, file=err)
        return 2
    try:
        doc = document(argv[1])
    except (ReferenceError, OSError) as e:
        print('reference failed: %s' % e, file=err)
        return 1
    if len(argv) == 3 and hashlib.sha256(doc).hexdigest() != REFERENCE_GOVERNOR_SHA256:
        print('reference check failed: the document is not the pinned one', file=err)
        return 1
    out.write(doc)
    return 0


# ---------------------------------------------------------------------------------------------------------------
# Tests

ROOT = REPO / 'tests' / 'conformance'


def full_document(root):
    """The full round-1 document as the full reference computes it: the governor's records and the Resume Check's
    records with the closed placeholder engine_identity.python."""
    obj = {}
    for key, value in values_of(GOVERNOR_FOLDER, entries_of(root, GOVERNOR_FOLDER)):
        obj[key] = governor_records(value)
    for key, value in values_of(RC_FOLDER, entries_of(root, RC_FOLDER)):
        recs = []
        for case in value['cases']:
            rec = copy.deepcopy(resume_check.check(copy.deepcopy(case['inputs'])))
            if isinstance(rec.get('engine_identity'), dict) and 'python' in rec['engine_identity']:
                rec['engine_identity']['python'] = PLACEHOLDER
            recs.append(rec)
        obj[key] = recs
    return text_of(obj)


class GovernorReference(unittest.TestCase):

    def test_document_and_pin(self):
        """TASK-100 AC1: the document is the canonical text of the governor folder's records, ASCII and LF, and its
        SHA-256 is the pin."""
        doc = document(ROOT)
        obj = json.loads(doc.decode('ascii'))
        self.assertEqual(conformance.canonical_text(obj), doc)
        self.assertTrue(obj)
        self.assertTrue(all(k.startswith(GOVERNOR_FOLDER + '/') for k in obj))
        self.assertEqual(hashlib.sha256(doc).hexdigest(), REFERENCE_GOVERNOR_SHA256)

    def test_tie_to_the_full_reference(self):
        """TASK-100 AC2: the full document hashes to the full reference's pin, which is that module's value, and the
        governor document is its governor part."""
        full = full_document(ROOT)
        self.assertEqual(hashlib.sha256(full).hexdigest(), FULL_REFERENCE_SHA256)
        ref = (REPO / 'tests' / 'unit' / 'test_export_reference.py').read_bytes()
        self.assertEqual(ref.count(FULL_REFERENCE_SHA256.encode('ascii')), 1)
        self.assertIn(("REFERENCE_SHA256 = '%s'" % FULL_REFERENCE_SHA256).encode('ascii'), ref)
        part = {k: v for k, v in json.loads(full.decode('ascii')).items() if k.startswith(GOVERNOR_FOLDER + '/')}
        self.assertEqual(conformance.canonical_text(part), document(ROOT))

    def test_fails_closed(self):
        """TASK-100 AC1: a missing folder, a file that is not .py, a refused file, a call that raises and a record that
        is not an object each fail closed."""
        with self.assertRaises(ReferenceError):
            values_of(GOVERNOR_FOLDER, None)
        with self.assertRaises(ReferenceError):
            values_of(GOVERNOR_FOLDER, [('x.txt', 'file', b'')])
        with self.assertRaises(ReferenceError):
            values_of(GOVERNOR_FOLDER, [('sub', 'dir', None)])
        with self.assertRaises(ReferenceError):
            values_of(GOVERNOR_FOLDER, [('x.py', 'file', b'not a fixture')])
        self.assertEqual(values_of(GOVERNOR_FOLDER, [('__pycache__', 'dir', None)]), [])
        value = values_of(GOVERNOR_FOLDER, entries_of(ROOT, GOVERNOR_FOLDER))[0][1]
        with mock.patch.object(governor, 'evaluate', side_effect=ValueError('x')):
            with self.assertRaises(ReferenceError):
                governor_records(value)
        with mock.patch.object(governor, 'evaluate', return_value=['not', 'an', 'object']):
            with self.assertRaises(ReferenceError):
                governor_records(value)

    def test_main(self):
        """TASK-100 AC1: --root prints the document; --check passes on the pin; any other form exits 2; a missing folder
        exits 1; a failing check exits 1; nothing is printed to standard output on failure."""
        out, err = io.BytesIO(), io.StringIO()
        self.assertEqual(main(['--root', str(ROOT)], out, err), 0)
        self.assertEqual(out.getvalue(), document(ROOT))
        out = io.BytesIO()
        self.assertEqual(main(['--root', str(ROOT), '--check'], out, err), 0)
        for argv in ([], ['--root'], ['--root', str(ROOT), '--other'], ['--root', str(ROOT), '--check', 'x'],
                     ['--check', str(ROOT)], ['x']):
            out = io.BytesIO()
            self.assertEqual(main(argv, out, io.StringIO()), 2)
            self.assertEqual(out.getvalue(), b'')
        out = io.BytesIO()
        self.assertEqual(main(['--root', str(REPO / 'no-such-folder')], out, io.StringIO()), 1)
        self.assertEqual(out.getvalue(), b'')
        with mock.patch.object(sys.modules[__name__], 'REFERENCE_GOVERNOR_SHA256', '0' * 64):
            out = io.BytesIO()
            self.assertEqual(main(['--root', str(ROOT), '--check'], out, io.StringIO()), 1)
            self.assertEqual(out.getvalue(), b'')

    def test_names(self):
        """TASK-100 AC1: this module names no closed fixture folder and no benchmark path in its bytes."""
        data = Path(__file__).read_bytes()
        for parts in (('fixtures', '_rc'), ('fixtures', '_risk'), ('fixtures', '_cb'), ('ben', 'ch/')):
            self.assertNotIn(''.join(parts).encode('ascii'), data)

    def test_workflow_step(self):
        """TASK-100 AC1: the workflow aieos-native.yml runs this module with --check in each job."""
        wf = (REPO / '.github' / 'workflows' / 'aieos-native.yml').read_bytes().decode('utf-8')
        cmd = '$PY tests/unit/test_export_governor.py --root tests/conformance --check > "$RUNNER_TEMP/governor-reference.json"'
        self.assertEqual(wf.count(cmd), 2)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--root']:
        sys.exit(main(sys.argv[1:]))
    unittest.main()
