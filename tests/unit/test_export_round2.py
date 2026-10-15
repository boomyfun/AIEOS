"""The stack benchmark's round-2 input and reference, and their tests (TASK-047; docs/plan/m4-exit-review.md §6, line 70).

Round 2 is the event log's append and recovery over a generated log (decision D-905): the two pure computations of the
bootstrap, aieos_bootstrap.eventlog.append (TASK-007) and aieos_bootstrap.recovery.reconcile (TASK-009), with the record
forms of aieos_bootstrap.records they use. The writer (files and SQLite) and startup (it starts git) are not in it, since
a port may not write files or start processes (docs/plan/bench-port-brief.md §3): no file behaviour is compared.

The input: run from the repository root as `python tests/unit/test_export_round2.py --input`, it prints the canonical
text (conformance.canonical_text) of one object {"append": [...], "reconcile": [...]}, built by the generator below from
fixed tables and a counter only (no random source, clock, environment, file or network read). The log is generated at
each run and never committed (decision D-794 Q1). Every append call names its event_type, payload, event_id,
appended_at, task_id, fencing_token, corrects, lease, recorder and record_id; every reconcile case its log (the text of a
log the generator builds with eventlog.append), commits, leases, now and recorder. The recorder is "bench-round2"
everywhere and each record_id is formed from its call's index; times are "YYYY-MM-DDTHH:MM:SSZ" text, read as aware UTC
datetimes.

The reference: `--reference <input file>` reads the file, refuses it unless it is an input document of that form, and
prints the canonical text of one object {"append": [...], "reconcile": [...]}: for each append call in order, with the
log carried from call to call (an "appended" result's new log becomes the next call's log; any other result leaves it),
{result, reason, findings, seq, line, record}; for each reconcile case {log, events, expired, findings}; bytes as text and
datetimes in the input's text form. Its form (one object of lists) is the one test_export_reference.py's --compare reads.

Pins: INPUT_SHA256 and REFERENCE2_SHA256; `--check` after either option exits non-zero, printing nothing to standard
output, when the document differs from its pin. A later task that changes eventlog.py, recovery.py, records.py or the
generator changes these pins, pin-only, with one exact new value. Each document is built at most once per test process.

Coverage (AC4): every result of eventlog.RESULTS and the reasons "conflict", "event", "log_after" and "fence" occur among
the append entries. The reason "log" (the given log has a finding) cannot occur: the append calls carry the log from
call to call, starting from the empty log, and eventlog.append never returns a log with a finding (its AC4 refuses one),
so every call is given a log the bootstrap accepts. A damaged log is given to reconcile instead (its case 6).

Limits: the generated sequence is one fixed choice of calls, not a search of all inputs; the trigger paths of the
benchmark workflow do not include this module, so a change to it alone runs its --check at the next triggering push,
while the unit tests assert both pins at every push.
"""

import datetime
import hashlib
import io
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / 'src') not in sys.path:
    sys.path.insert(0, str(REPO / 'src'))

from aieos_bootstrap import conformance, eventlog, recovery  # noqa: E402

RECORDER = 'bench-round2'
N_TASKS = 50
KINDS = 12
N_APPEND = N_TASKS * KINDS
N_RECONCILE = 7
BASE_TIME = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
TIME_FORM = '%Y-%m-%dT%H:%M:%SZ'
CALL_KEYS = ('event_type', 'payload', 'event_id', 'appended_at', 'task_id', 'fencing_token', 'corrects', 'lease',
             'recorder', 'record_id')
CASE_KEYS = ('log', 'commits', 'leases', 'now', 'recorder')
INPUT_SHA256 = '12b9d4652403a74f19aba895a5544e995f6df41105fca7805c5c947718eea5c2'
REFERENCE2_SHA256 = '32f23440e645f50899853fecdee0a40150d7646c768bf48c62237a1abbca2498'
USAGE = ('usage: test_export_round2.py --input [--check]\n'
         '       test_export_round2.py --reference <input file> [--check]')


class Round2Error(Exception):
    """An input that is not a round-2 input document, or a case that cannot be computed."""


def time_text(value):
    return value.strftime(TIME_FORM)


def time_value(text):
    if not isinstance(text, str):
        raise Round2Error('a time is not text')
    try:
        value = datetime.datetime.strptime(text, TIME_FORM).replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        raise Round2Error('a time is not YYYY-MM-DDTHH:MM:SSZ: %r' % text) from None
    if time_text(value) != text:
        raise Round2Error('a time is not YYYY-MM-DDTHH:MM:SSZ: %r' % text)
    return value


def at(seconds):
    return time_text(BASE_TIME + datetime.timedelta(seconds=seconds))


def digest(*parts):
    return hashlib.sha256('\n'.join(parts).encode('utf-8')).hexdigest()


def commit_id(name):
    return digest('commit', name)[:40]


# ---------------------------------------------------------------------------------------------------------------
# The generator

def append_call(i):
    """The append call with index i: kind i % KINDS of task i // KINDS, from the fixed table below."""
    n, kind = divmod(i, KINDS)
    task = 'TASK-%d' % (1000 + n)
    token = {'epoch': 'bench', 'counter': n}
    first = 'e%06d' % (n * KINDS)
    contract = {'contract_version': 'v1', 'contract_hash': digest('contract', task)}
    call = {'event_type': None, 'payload': None, 'event_id': 'e%06d' % i, 'appended_at': at(i), 'task_id': task,
            'fencing_token': None, 'corrects': None, 'lease': None, 'recorder': RECORDER, 'record_id': 'r%06d' % i}
    if kind == 0:      # a draft: appended
        call.update(event_type='task.drafted', payload=dict(contract), event_id=first)
    elif kind == 1:    # its approval: appended
        call.update(event_type='task.approved', payload=dict(contract, approval_record='approval-%d' % n))
    elif kind == 2:    # the draft again, the same event: duplicate
        call.update(event_type='task.drafted', payload=dict(contract), event_id=first)
    elif kind == 3:    # another event under the draft's event_id: refused, conflict
        call.update(event_type='task.drafted', payload=dict(contract, contract_version='v2'), event_id=first)
    elif kind == 4:    # a payload without a key it needs: refused, event
        call.update(event_type='task.blocked', payload={'reason': 'waiting'})
    elif kind == 5:    # a submission with no lease: refused, fence, with its record
        call.update(event_type='task.submitted', payload={'commit': commit_id(task), 'compensating': False},
                    fencing_token=token)
    elif kind == 6:    # the submission under a lease that holds: appended
        call.update(event_type='task.submitted', payload={'commit': commit_id(task), 'compensating': False},
                    fencing_token=token, lease={'task_id': task, 'fencing_token': token, 'expires_at': at(i + 3600)})
    elif kind == 7:    # a task event without task_id: refused, log_after (the whole log's check)
        call.update(event_type='task.drafted', payload=dict(contract), task_id=None)
    elif kind == 8:    # a submission under an expired lease: refused, fence
        call.update(event_type='task.submitted', payload={'commit': commit_id(task + '-late'), 'compensating': False},
                    fencing_token=token, lease={'task_id': task, 'fencing_token': token, 'expires_at': at(i - 1)})
    elif kind == 9:    # an observation about the task
        call.update(event_type='record.added', payload={
            'record_id': 'note-%d' % n, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
            'recorder': RECORDER, 'subject': task, 'evidence_type': 'bench_note', 'outcome': 'pass',
            'refers_to': first})
    elif kind == 10:   # the task done
        call.update(event_type='task.done', payload={'decision_record': 'decision-%d' % n})
    else:              # a submission that names no task: refused, fence, without a record
        call.update(event_type='task.submitted', payload={'commit': commit_id(task + '-none'), 'compensating': False},
                    fencing_token=token, task_id=None)
    return call


def build_log(events):
    """A log built with eventlog.append from (event_type, payload, event_id, seconds, task_id, token) tuples."""
    log = b''
    for event_type, payload, event_id, seconds, task_id, token in events:
        lease = None if token is None else {'task_id': task_id, 'fencing_token': token,
                                            'expires_at': BASE_TIME + datetime.timedelta(seconds=seconds + 3600)}
        r = eventlog.append(log, event_type, payload, event_id, BASE_TIME + datetime.timedelta(seconds=seconds),
                            task_id=task_id, fencing_token=token, lease=lease)
        if r.result != 'appended':
            raise Round2Error('the generator\'s base log could not be built: %r' % r)
        log = r.log
    return log


def message(task, fence):
    lines = ['Work on %s' % task, '', 'AIEOS-Task: %s' % task]
    if fence is not None:
        lines.append('AIEOS-Fence: %s' % fence)
    return '\n'.join(lines)


def reconcile_cases():
    """The seven reconcile cases (AC4's outcomes), each as an input case."""
    c1, c2, c3, c4 = (commit_id('reconcile-%d' % k) for k in (1, 2, 3, 4))
    contract = {'contract_version': 'v1', 'contract_hash': digest('contract', 'reconcile')}
    base = build_log([
        ('task.drafted', dict(contract), 'b1', 1, 'TASK-1', None),
        ('task.approved', dict(contract, approval_record='approval-b1'), 'b2', 2, 'TASK-1', None),
        ('task.submitted', {'commit': c1, 'compensating': False}, 'b3', 3, 'TASK-1', {'epoch': 'bench', 'counter': 1}),
        ('task.drafted', dict(contract), 'b4', 4, 'TASK-2', None),
        ('task.approved', dict(contract, approval_record='approval-b4'), 'b5', 5, 'TASK-2', None),
    ])
    now = at(100)
    first = {'commit': c1, 'message': message('TASK-1', 'bench:1')}
    held = {'task_id': 'TASK-2', 'fencing_token': {'epoch': 'bench', 'counter': 2}, 'expires_at': at(200)}
    expired = {'task_id': 'TASK-2', 'fencing_token': {'epoch': 'bench', 'counter': 9}, 'expires_at': at(50)}
    observed = [first, {'commit': c3, 'message': message('TASK-2', 'bench:3')}]
    after = recovery.reconcile(base, [dict(c) for c in observed], [], time_value(now), RECORDER).log
    cases = [
        (base, [first, {'commit': c2, 'message': message('TASK-2', 'bench:2')}], [held]),    # compensating submission
        (base, observed, []),                                                                  # an unfenced write
        (after, observed, []),                                                                 # its duplicate
        (base, [], []),                                                                        # a commit not given
        (base, [first], [expired]),                                                            # an expired lease
        (base[:-1], [first], []),                                                              # a damaged log
        (base, [first, {'commit': c4, 'message': 'Work\n\naieos-task: TASK-2'}], []),          # a malformed trailer
    ]
    return [{'log': log.decode('ascii'), 'commits': commits, 'leases': leases, 'now': now, 'recorder': RECORDER}
            for log, commits, leases in cases]


def input_document():
    """AC1: the round-2 input document's bytes."""
    doc = {'append': [append_call(i) for i in range(N_APPEND)], 'reconcile': reconcile_cases()}
    if len(doc['reconcile']) != N_RECONCILE:
        raise Round2Error('the number of reconcile cases is not N_RECONCILE')
    return conformance.canonical_text(doc)


# ---------------------------------------------------------------------------------------------------------------
# The reference

def _no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise Round2Error('a duplicate key: %s' % key)
        out[key] = value
    return out


def parse_input(data):
    """The input document read back: refused unless it is canonical text of AC1's form."""
    if not isinstance(data, bytes):
        raise Round2Error('the input is not bytes')
    try:
        doc = json.loads(data.decode('ascii'), object_pairs_hook=_no_duplicates)
    except (UnicodeDecodeError, ValueError) as e:
        raise Round2Error('not a round-2 input document: %s' % e) from None
    if not isinstance(doc, dict) or set(doc) != {'append', 'reconcile'}:
        raise Round2Error('not a round-2 input document: not one object with append and reconcile')
    if conformance.canonical_text(doc) != data:
        raise Round2Error('not a round-2 input document: not its canonical text')
    for call in doc['append'] if isinstance(doc['append'], list) else [None]:
        if not isinstance(call, dict) or set(call) != set(CALL_KEYS):
            raise Round2Error('not a round-2 input document: an append call without exactly its keys')
    for case in doc['reconcile'] if isinstance(doc['reconcile'], list) else [None]:
        if not isinstance(case, dict) or set(case) != set(CASE_KEYS):
            raise Round2Error('not a round-2 input document: a reconcile case without exactly its keys')
    return doc


def _lease_value(lease):
    if lease is None:
        return None
    if not isinstance(lease, dict) or 'expires_at' not in lease:
        raise Round2Error('a lease is not an object with expires_at')
    return dict(lease, expires_at=time_value(lease['expires_at']))


def _lease_text(lease):
    return dict(lease, expires_at=time_text(lease['expires_at']))


def _text(value):
    return None if value is None else value.decode('ascii')


def reference_document(data):
    """AC2: the bootstrap's results over the input document's bytes, as the reference document's bytes."""
    doc = parse_input(data)
    log = b''
    out_append = []
    for call in doc['append']:
        try:
            r = eventlog.append(log, call['event_type'], call['payload'], call['event_id'],
                                time_value(call['appended_at']), task_id=call['task_id'],
                                fencing_token=call['fencing_token'], corrects=call['corrects'],
                                lease=_lease_value(call['lease']), recorder=call['recorder'],
                                record_id=call['record_id'])
        except (TypeError, ValueError) as e:
            raise Round2Error('an append call cannot be computed: %s' % e) from None
        if r.result == 'appended':
            log = r.log
        out_append.append({'result': r.result, 'reason': r.reason, 'findings': list(r.findings), 'seq': r.seq,
                           'line': _text(r.line), 'record': r.record})
    out_reconcile = []
    for case in doc['reconcile']:
        try:
            r = recovery.reconcile(case['log'].encode('ascii'), case['commits'],
                                   [_lease_value(x) for x in case['leases']], time_value(case['now']),
                                   case['recorder'])
        except (AttributeError, TypeError, ValueError, UnicodeEncodeError) as e:
            raise Round2Error('a reconcile case cannot be computed: %s' % e) from None
        out_reconcile.append({'log': _text(r.log), 'events': list(r.events),
                              'expired': [_lease_text(x) for x in r.expired], 'findings': list(r.findings)})
    return conformance.canonical_text({'append': out_append, 'reconcile': out_reconcile})


def main(argv, out=None, err=None, pins=None):
    """The command line: `--input [--check]` or `--reference <file> [--check]`; pins = (input, reference) for tests."""
    out = sys.stdout.buffer if out is None else out
    err = sys.stderr if err is None else err
    pin_input, pin_reference = (INPUT_SHA256, REFERENCE2_SHA256) if pins is None else pins
    if argv[:1] == ['--input'] and argv[1:] in ([], ['--check']):
        check, pin = argv[1:] == ['--check'], pin_input
        try:
            doc = input_document()
        except Round2Error as e:
            print('input failed: %s' % e, file=err)
            return 1
    elif argv[:1] == ['--reference'] and len(argv) in (2, 3) and argv[2:] in ([], ['--check']):
        check, pin = argv[2:] == ['--check'], pin_reference
        try:
            doc = reference_document(Path(argv[1]).read_bytes())
        except (Round2Error, OSError) as e:
            print('reference failed: %s' % e, file=err)
            return 1
    else:
        print(USAGE, file=err)
        return 2
    if check and hashlib.sha256(doc).hexdigest() != pin:
        print('check failed: the document is not the pinned one', file=err)
        return 1
    out.write(doc)
    return 0


# ---------------------------------------------------------------------------------------------------------------
# Tests

_BUILT = {}


def built(kind):
    """Each document built at most once per test process (AC3)."""
    if kind not in _BUILT:
        _BUILT[kind] = input_document() if kind == 'input' else reference_document(built('input'))
    return _BUILT[kind]


def as_object(data):
    return json.loads(data.decode('ascii'))


class InputTests(unittest.TestCase):
    def test_input_document(self):
        """TASK-047 AC1: one object with N_APPEND calls and N_RECONCILE cases, each with exactly its keys; the fixed
        recorder, record ids from the index, times as text; built again in the same process it is the same bytes."""
        doc = as_object(built('input'))
        self.assertEqual(sorted(doc), ['append', 'reconcile'])
        self.assertEqual(len(doc['append']), N_APPEND)
        self.assertEqual(len(doc['reconcile']), N_RECONCILE)
        for i, call in enumerate(doc['append']):
            self.assertEqual(sorted(call), sorted(CALL_KEYS))
            self.assertEqual(call['recorder'], RECORDER)
            self.assertEqual(call['record_id'], 'r%06d' % i)
            self.assertEqual(time_text(time_value(call['appended_at'])), call['appended_at'])
        for case in doc['reconcile']:
            self.assertEqual(sorted(case), sorted(CASE_KEYS))
            self.assertEqual(case['recorder'], RECORDER)
        self.assertEqual(input_document(), built('input'))


class ReferenceTests(unittest.TestCase):
    def test_reference_document(self):
        """TASK-047 AC2: one object of two lists, an entry per call and per case with exactly its keys; an appended
        entry's line is the next log's last line."""
        ref = as_object(built('reference'))
        self.assertEqual(sorted(ref), ['append', 'reconcile'])
        self.assertTrue(all(isinstance(v, list) for v in ref.values()))
        self.assertEqual(len(ref['append']), N_APPEND)
        self.assertEqual(len(ref['reconcile']), N_RECONCILE)
        for e in ref['append']:
            self.assertEqual(sorted(e), ['findings', 'line', 'reason', 'record', 'result', 'seq'])
            self.assertEqual(e['line'] is not None, e['result'] == 'appended')
        for e in ref['reconcile']:
            self.assertEqual(sorted(e), ['events', 'expired', 'findings', 'log'])

    def test_pins_and_form(self):
        """TASK-047 AC3: both documents equal their pins, have no CR byte, are ASCII only and end with one LF; with
        --check a document that differs from its pin exits non-zero and prints nothing to standard output."""
        for kind, pin in (('input', INPUT_SHA256), ('reference', REFERENCE2_SHA256)):
            doc = built(kind)
            self.assertEqual(hashlib.sha256(doc).hexdigest(), pin, kind)
            self.assertNotIn(b'\r', doc)
            doc.decode('ascii')
            self.assertTrue(doc.endswith(b'\n') and not doc.endswith(b'\n\n'))
        out, err = io.BytesIO(), io.StringIO()
        self.assertEqual(main(['--input', '--check'], out, err, pins=('1' * 64, REFERENCE2_SHA256)), 1)
        self.assertEqual(out.getvalue(), b'')
        self.assertIn('check failed', err.getvalue())

    def test_coverage(self):
        """TASK-047 AC4: every result and the reasons conflict, event, log_after and fence occur; the reason log cannot
        (the carried log is always one the bootstrap accepts) and is absent; reconcile shows a compensating
        submission, an observation, a duplicate, a commit not given, an expired lease and a damaged log."""
        ref = as_object(built('reference'))
        results = {e['result'] for e in ref['append']}
        reasons = {e['reason'] for e in ref['append'] if e['reason'] is not None}
        self.assertEqual(results, set(eventlog.RESULTS))
        self.assertEqual(reasons, set(eventlog.REASONS) - {'log'})
        events = [e for case in ref['reconcile'] for e in case['events']]
        self.assertIn(('task.submitted', 'appended'), {(e['type'], e['result']) for e in events})
        self.assertIn(('record.added', 'appended'), {(e['type'], e['result']) for e in events})
        self.assertIn('duplicate', {e['result'] for e in events})
        findings = [f for case in ref['reconcile'] for f in case['findings']]
        self.assertTrue(any(f.startswith('step 2:') for f in findings))
        self.assertTrue(any(f.startswith('log: ') for f in findings))
        self.assertTrue(any(case['expired'] for case in ref['reconcile']))


class FailClosedTests(unittest.TestCase):
    def test_arguments(self):
        """TASK-047 AC5: a missing or extra argument, or an unknown option, exits non-zero and prints nothing to
        standard output; a path that does not exist is refused."""
        for argv in ([], ['--input', '--other'], ['--input', '--check', 'x'], ['--reference'],
                     ['--reference', 'a', '--check', 'b'], ['--other']):
            out, err = io.BytesIO(), io.StringIO()
            self.assertNotEqual(main(argv, out, err), 0, argv)
            self.assertEqual(out.getvalue(), b'', argv)
        out, err = io.BytesIO(), io.StringIO()
        self.assertEqual(main(['--reference', str(REPO / 'no-such-round2-input.json')], out, err), 1)
        self.assertEqual(out.getvalue(), b'')

    def test_not_an_input_document(self):
        """TASK-047 AC5: texts that are not an input document of AC1's form are refused (held in memory)."""
        good = as_object(built('input'))
        bad_call = dict(good, append=[{'event_type': 'task.done'}])
        bad_case = dict(good, reconcile=[{'log': ''}])
        for data in (b'', b'not json', b'[]\n', b'{}\n', b'{"append":[],"reconcile":[],"x":1}\n',
                     json.dumps(good).encode('ascii'), conformance.canonical_text(bad_call),
                     conformance.canonical_text(bad_case), b'{"append":[],"append":[],"reconcile":[]}\n'):
            with self.assertRaises(Round2Error):
                reference_document(data)

    def test_a_case_that_cannot_be_computed(self):
        """TASK-047 AC5: a call whose time is not of the form, or a reconcile case whose commits are not a list, is
        refused, not computed."""
        call = dict(append_call(0), appended_at='2026-01-01 00:00:00')
        case = dict(reconcile_cases()[0], commits='none')
        for doc in ({'append': [call], 'reconcile': []}, {'append': [], 'reconcile': [case]}):
            with self.assertRaises(Round2Error):
                reference_document(conformance.canonical_text(doc))


class SuiteTests(unittest.TestCase):
    def test_workflow_step(self):
        """TASK-047 AC6: in each job the round-2 export is the step right after the reference export, writing both
        documents into the job's temporary folder with their checks."""
        text = (REPO / '.github' / 'workflows' / 'aieos-bench.yml').read_bytes().decode('utf-8')
        jobs = text.split('\n  windows:\n')
        self.assertEqual(len(jobs), 2)
        for job in jobs:
            names = [ln.strip() for ln in job.split('\n') if ln.strip().startswith('- name:')]
            i = names.index('- name: reference export (bootstrap decisions over the frozen fixtures)')
            self.assertEqual(names[i + 1], '- name: round-2 export (the generated log and the bootstrap\'s results)')
        for cmd in ('$PY tests/unit/test_export_round2.py --input --check > "$RUNNER_TEMP/round2-input.json"',
                    '$PY tests/unit/test_export_round2.py --reference "$RUNNER_TEMP/round2-input.json" --check > '
                    '"$RUNNER_TEMP/round2-reference.json"',
                    'wc -c "$RUNNER_TEMP/round2-input.json" "$RUNNER_TEMP/round2-reference.json"'):
            self.assertEqual(text.count(cmd), 2, cmd)

    def test_naming(self):
        """TASK-047 AC9: every test of this module names the AC it stands for in its docstring."""
        loader = unittest.TestLoader()
        for case in (InputTests, ReferenceTests, FailClosedTests, SuiteTests):
            for name in loader.getTestCaseNames(case):
                doc = getattr(case, name).__doc__ or ''
                self.assertRegex(doc, r'^TASK-047 AC\d+', name)


if __name__ == '__main__':
    if sys.argv[1:2] in (['--input'], ['--reference']):
        sys.exit(main(sys.argv[1:]))
    unittest.main()
