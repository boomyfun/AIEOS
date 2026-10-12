"""Unit tests of the audit-copy rules that TASK-029 adds to aieos_bootstrap.records (specification 2 revision 4, section
6.2). Every case is built in memory; the only files read are the repository's docs/records/*.jsonl, with pathlib's
read_bytes. Each test names the criteria it stands for in its own docstring."""

import json
import pathlib
import unittest

from aieos_bootstrap import records

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMIT = 'a' * 40


def copy_record(kind='risk_class', **changes):
    r = {'record_id': 'r1', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
         'recorder': 'aieos-core', 'subject': 'TASK-029', 'evidence_type': kind,
         kind: 'high' if kind == 'risk_class' else [{'dimension': 'functional', 'evidence_types': ['unit_test']}],
         'commit': COMMIT, 'intent_versions': {'SPEC-001': 'v1'}}
    r.update(changes)
    return {k: v for k, v in r.items() if v is not _ABSENT}


_ABSENT = object()


def rules(record):
    return [f.rule for f in records.check_record(record)]


class WellFormed(unittest.TestCase):

    def test_well_formed_copies_have_no_finding(self):
        """TASK-029 AC7: a risk_class and an evidence_profile copy of the form, with values and with null, pass."""
        for kind in ('risk_class', 'evidence_profile'):
            self.assertEqual(rules(copy_record(kind)), [])
            self.assertEqual(rules(copy_record(kind, **{kind: None})), [])
        for cls in ('low', 'medium', 'high', 'critical'):
            self.assertEqual(rules(copy_record(risk_class=cls)), [])
        self.assertEqual(rules(copy_record(source_class='deterministic_tool_external_ci')), [])
        self.assertEqual(rules(copy_record('evidence_profile', evidence_profile=[])), [])

    def test_the_keys_are_known(self):
        """TASK-029 AC7: RECORD_KEYS gains risk_class and evidence_profile."""
        self.assertIn('risk_class', records.RECORD_KEYS)
        self.assertIn('evidence_profile', records.RECORD_KEYS)


class Malformed(unittest.TestCase):

    def assertFinding(self, record, rule):
        found = rules(record)
        self.assertIn(rule, found)
        self.assertTrue(all(r.startswith('6.2:audit_copy') for r in found if r not in (
            '6.2:outcome', '6.2:blocking_kind', '6.2:gate', '6.2:dimension')), found)

    def test_fact_kind(self):
        """TASK-029 AC7: an audit copy whose fact_kind is not observation."""
        self.assertFinding(copy_record(fact_kind='claim'), '6.2:audit_copy_fact_kind')

    def test_source_class(self):
        """TASK-029 AC7: an audit copy of another source class."""
        self.assertFinding(copy_record(source_class='agent_declared'), '6.2:audit_copy_source_class')

    def test_own_key_missing_or_other_key_present(self):
        """TASK-029 AC7: the own key absent, and the other key carried."""
        self.assertFinding(copy_record(risk_class=_ABSENT), '6.2:audit_copy_key')
        self.assertFinding(copy_record(evidence_profile=None), '6.2:audit_copy_key')
        self.assertFinding(copy_record('evidence_profile', risk_class='low'), '6.2:audit_copy_key')

    def test_values_out_of_form(self):
        """TASK-029 AC7: values that are neither null nor of their form."""
        for bad in ('lowish', 'LOW', '', 3, ['high'], {}):
            self.assertFinding(copy_record(risk_class=bad), '6.2:audit_copy_value')
        for bad in ('x', [{'dimension': 'functional'}], [{'dimension': '', 'evidence_types': []}],
                    [{'dimension': 'f', 'evidence_types': ['']}], [{'dimension': 'f', 'evidence_types': 'unit_test'}],
                    [{'dimension': 'f', 'evidence_types': [], 'x': 1}], [None]):
            self.assertFinding(copy_record('evidence_profile', evidence_profile=bad), '6.2:audit_copy_value')

    def test_binding_missing(self):
        """TASK-029 AC7: an audit copy without commit or intent_versions."""
        self.assertFinding(copy_record(commit=_ABSENT), '6.2:audit_copy_binding')
        self.assertFinding(copy_record(intent_versions=_ABSENT), '6.2:audit_copy_binding')

    def test_forbidden_keys(self):
        """TASK-029 AC7: outcome (each value), gate, blocking_kind and dimension are refused on an audit copy."""
        for outcome in ('pass', 'fail'):
            self.assertFinding(copy_record(outcome=outcome), '6.2:audit_copy_forbidden')
        self.assertFinding(copy_record(outcome='blocking', blocking_kind='other'), '6.2:audit_copy_forbidden')
        self.assertFinding(copy_record(gate='G1'), '6.2:audit_copy_forbidden')
        self.assertFinding(copy_record(dimension='functional'), '6.2:audit_copy_forbidden')

    def test_a_key_on_another_type(self):
        """TASK-029 AC7: risk_class or evidence_profile on a record of another evidence_type, or of none."""
        other = {'record_id': 'g', 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
                 'recorder': 'ci', 'subject': 'TASK-029', 'evidence_type': 'build', 'gate': 'G1', 'outcome': 'pass',
                 'commit': COMMIT, 'intent_versions': {'SPEC-001': 'v1'}}
        self.assertEqual(rules(other), [])
        self.assertIn('6.2:audit_copy_key', rules(dict(other, risk_class='low')))
        self.assertIn('6.2:audit_copy_key', rules(dict(other, evidence_profile=None)))
        no_type = {k: v for k, v in other.items() if k != 'evidence_type'}
        self.assertIn('6.2:audit_copy_key', rules(dict(no_type, risk_class='low')))


class NoEarlierRecordChanges(unittest.TestCase):

    def test_the_helper_finds_nothing_in_the_records_folder(self):
        """TASK-029 AC7: check_audit_copy gives no finding for any record of docs/records/*.jsonl."""
        files = sorted((ROOT / 'docs' / 'records').glob('*.jsonl'))
        self.assertTrue(files)
        count = 0
        for path in files:
            for line in path.read_bytes().decode('utf-8').split('\n'):
                if not line.strip():
                    continue
                rec = json.loads(line)
                self.assertEqual(records.check_audit_copy(rec, path.name), [], path.name)
                count += 1
        self.assertGreater(count, 0)

    def test_records_without_the_names_get_no_audit_finding(self):
        """TASK-029 AC7: a record with neither key and neither name gets no 6.2:audit_copy finding, whatever else."""
        for rec in ({'record_id': 'x'}, {'evidence_type': 'build', 'outcome': 'nonsense'}, {'fact_kind': 'claim'}):
            self.assertEqual(records.check_audit_copy(rec), [])
            self.assertFalse(any(r.startswith('6.2:audit_copy') for r in rules(rec)))


if __name__ == '__main__':
    unittest.main()
