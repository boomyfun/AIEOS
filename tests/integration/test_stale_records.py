"""Integration test of aieos_bootstrap.stale over TASK-022's records on main (task TASK-023; decisions D-544 C1 and
D-545 Q2): read only, with pathlib's read_bytes; the contract's read-set is taken by this test's own line-based reader,
and the base commits after TASK-022's acceptance, with their changed paths against their first parent, are fixed
inputs here, not read from Git. The result is data about an accepted task: it reopens no acceptance and schedules
nothing, since no caller exists."""

import hashlib
import json
import pathlib
import re
import unittest

from aieos_bootstrap import records, stale

ROOT = pathlib.Path(__file__).resolve().parents[2]
ACCEPTED = '4ef7dfa91df7eed00e7c3d5180d3aac12e94f768'
TRIGGER = 'a4c2255be6e29b5e020018b6f32943787129aa50'
# The two commits on main after TASK-022's acceptance, in order, with their changed paths (fixed inputs).
LATER = [
    {'commit': '92da3802e54722b9232507ceac402052916e6bd7', 'paths': ['docs/records/TASK-022.jsonl'],
     'submitted_by_task': False},
    {'commit': TRIGGER, 'paths': [
        'docs/Deferred/DEF-0042-specification-4-open-points-and-the-risk-01-route.md',
        'docs/Deferred/DEF-0049-carried-findings-of-the-test-listing-and-the-untested-criteria.md',
        'docs/History/2026-10/2026-10-11-2112-test-to-ac-listing-accepted-and-on-main.md',
        'docs/Lessons/L-0007-evidence-proves-the-proposition.md',
        'docs/Lessons/L-0015-write-every-text-for-the-owner-in-vietnamese.md',
        'docs/Progress/2026-10.md'], 'submitted_by_task': False},
]
EVENT_ID = '1ab38fa6a7637d1260e4f614b350097322a774f1656e56b8261ba7aaa88a19b4'
_LIST = re.compile(r'^  (interfaces|schemas): \[(.*)\]$')


def read_set(text):
    """The read_set of a contract's text: path entries with their own text as the pattern, interface and schema entries
    with patterns None (the caller has not resolved them)."""
    lines = text.split('\n')
    start = lines.index('read_set:')
    out = []
    for line in lines[start + 1:]:
        if not line.startswith('  '):
            break
        if line.startswith('    - '):
            out.append({'entry': line[6:], 'kind': 'path', 'patterns': [line[6:]]})
        m = _LIST.match(line)
        if m:
            kind = 'interface' if m.group(1) == 'interfaces' else 'schema'
            out += [{'entry': x.strip(), 'kind': kind, 'patterns': None} for x in m.group(2).split(',')]
    return out


def the_inputs():
    recs = [json.loads(line) for line in
            (ROOT / 'docs' / 'records' / 'TASK-022.jsonl').read_bytes().decode('utf-8').split('\n') if line.strip()]
    contract = (ROOT / 'docs' / 'tasks' / 'TASK-022.yaml').read_bytes().decode('utf-8')
    return {'task_id': 'TASK-022', 'accepted_commit': ACCEPTED, 'trigger_commit': TRIGGER, 'records': recs,
            'intent_current': {}, 'read_set': read_set(contract), 'read_set_estimate': True, 'base_commits': LATER,
            'earlier_events': []}


class Task022Records(unittest.TestCase):

    def test_inputs_as_read(self):
        """TASK-023 AC10: 25 records, 15 path entries and five unresolved interface and schema entries."""
        x = the_inputs()
        self.assertEqual(len(x['records']), 25)
        self.assertEqual(sum(1 for e in x['read_set'] if e['kind'] == 'path'), 15)
        self.assertEqual(sum(1 for e in x['read_set'] if e['patterns'] is None), 5)

    def test_result_as_data(self):
        """TASK-023 AC10, TASK-023 AC3, TASK-023 AC4 and TASK-023 AC5: all 25 records stale by commit, none by
        intent_version, and 32 uncovered entries, as the scratch prescan found (decision D-545 Q2)."""
        x = the_inputs()
        r = stale.stale(x)
        self.assertIsNone(r['error'])
        self.assertEqual(r['stale']['commit'], sorted(rec['record_id'] for rec in x['records']))
        self.assertEqual(r['stale']['intent_version'], [])
        details = {}
        for u in r['uncovered']:
            details[u['detail']] = details.get(u['detail'], 0) + 1
        self.assertEqual(details, {'no intent_versions': 25, 'commit order not known': 1,
                                   'not resolved by the caller': 5, 'the read-set is an estimate': 1})
        bad = [u['ref'] for u in r['uncovered'] if u['detail'] == 'commit order not known']
        self.assertEqual([rec['commit'] for rec in x['records'] if rec['record_id'] in bad],
                         ['e71f7bb36fe04000082982e59583f1faee8b2edf'])

    def test_the_one_event(self):
        """TASK-023 AC10 and TASK-023 AC6: one event, reason commit, with the 25 ids and the prescan's event id."""
        r = stale.stale(the_inputs())
        self.assertEqual(len(r['events']), 1)
        e = r['events'][0]
        self.assertEqual(e['event_id'], EVENT_ID)
        self.assertEqual(e['event_id'], hashlib.sha256(
            ('evidence.stale\nTASK-022\n%s\ncommit' % TRIGGER).encode('utf-8')).hexdigest())
        self.assertEqual(e['payload'], {'records': r['stale']['commit'], 'reason': 'commit'})
        self.assertEqual(records.check_payload('evidence.stale', e['payload']), [])

    def test_second_run_adds_nothing(self):
        """TASK-023 AC10 and TASK-023 AC6: with the first run's event as an earlier event, a second run gives no
        event."""
        x = the_inputs()
        first = stale.stale(x)['events'][0]['payload']
        x['earlier_events'] = [first]
        self.assertEqual(stale.stale(x)['events'], [])


if __name__ == '__main__':
    unittest.main()
