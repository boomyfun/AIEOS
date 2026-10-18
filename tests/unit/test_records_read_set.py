"""Unit tests of the observed read-set rules of aieos_bootstrap.records (task TASK-064, rule R1): check_read_set and its
call from check_record and check_payload, over records made up for the test. Each test names its criteria in its own
docstring."""

import ast
import pathlib
import unittest

from aieos_bootstrap import records

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap' / 'records.py'


def rec(**kw):
    r = {'record_id': 'observed-read-set/TASK-100/s-1/record', 'fact_kind': 'observation',
         'source_class': 'deterministic_tool_local', 'recorder': 'a made-up adapter, for session s-1',
         'subject': 'TASK-100', 'evidence_type': 'observed_read_set', 'read_paths': ['a/b.py', 'c.md']}
    r.update(kw)
    return r


def rules(record):
    return [f.rule for f in records.check_record(record)]


class ReadSet(unittest.TestCase):
    def test_well_formed(self):
        """TASK-064 AC1: a record of the form gives no finding, an empty read_paths included."""
        self.assertEqual(records.check_record(rec()), [])
        self.assertEqual(records.check_record(rec(read_paths=[])), [])
        self.assertEqual(records.check_payload('record.added', rec()), [])

    def test_read_paths_is_a_known_key(self):
        """TASK-064 AC1: check_record no longer refuses read_paths as an unknown key."""
        self.assertIn('read_paths', records.RECORD_KEYS)
        self.assertNotIn('6.2:unknown_key', rules(rec()))

    def test_fixed_values(self):
        """TASK-064 AC1: a wrong fact_kind, source_class or subject gives its finding."""
        self.assertIn('6.2:read_set_fact_kind', rules(rec(fact_kind='claim')))
        self.assertIn('6.2:read_set_source_class', rules(rec(source_class='agent_declared')))
        self.assertIn('6.2:read_set_subject', rules(rec(subject='INT-1')))
        self.assertIn('6.2:read_set_subject', rules(rec(subject='TASK-')))

    def test_read_paths_form(self):
        """TASK-064 AC1: read_paths missing, not a list, holding an empty string, a non-string or a repeat gives a
        finding."""
        r = rec()
        del r['read_paths']
        self.assertIn('6.2:read_set_key', rules(r))
        for value in ('a.py', None, {'a': 1}, ['a', ''], ['a', 3], ['a', 'a'], ['a', ['b']], ('a',)):
            self.assertIn('6.2:read_set_value', rules(rec(read_paths=value)), value)
        self.assertNotIn('6.2:read_set_value', rules(rec(read_paths=['a', 'A', 'a '])))

    def test_forbidden_keys(self):
        """TASK-064 AC1: each of session, outcome, gate, blocking_kind, dimension, commit and intent_versions gives a
        finding."""
        values = {'session': 's-1', 'outcome': 'pass', 'gate': 'G2', 'blocking_kind': 'violation',
                  'dimension': 'functional', 'commit': 'f' * 40, 'intent_versions': {'x': 'v1'}}
        for key, value in values.items():
            self.assertIn('6.2:read_set_forbidden', rules(rec(**{key: value})), key)

    def test_read_paths_on_another_type(self):
        """TASK-064 AC1: read_paths on a record of another evidence_type, or with none, gives a finding."""
        r = rec(evidence_type='unit_test')
        self.assertIn('6.2:read_set_key', rules(r))
        r = rec()
        del r['evidence_type']
        self.assertIn('6.2:read_set_key', rules(r))

    def test_neither_key_nor_name(self):
        """TASK-064 AC1, AC2: a record with neither read_paths nor the name gets no "6.2:read_set" finding."""
        r = rec(evidence_type='unit_test', outcome='pass', dimension='functional')
        del r['read_paths']
        self.assertEqual(records.check_read_set(r), [])
        self.assertEqual([x for x in rules(r) if x.startswith('6.2:read_set')], [])

    def test_all_rules_prefixed(self):
        """TASK-064 AC1: every finding of check_read_set has a rule beginning "6.2:read_set"."""
        bad = rec(fact_kind='claim', source_class='agent_declared', subject='x', read_paths='p', session='s',
                  outcome='pass', gate='G1', dimension='d', commit='f' * 40, intent_versions={})
        found = records.check_read_set(bad)
        self.assertEqual(len(found), 10)
        self.assertTrue(all(f.rule.startswith('6.2:read_set') for f in found))


class Statements(unittest.TestCase):
    def test_docstring_words(self):
        """TASK-064 AC1: the module's docstring states the rules beside the audit copies' (its line breaks and indents
        read as single spaces)."""
        doc = ' '.join(ast.get_docstring(ast.parse(SRC.read_text(encoding='utf-8'))).split())
        for words in ('TASK-064 AC1', 'no longer refuses it as an unknown key', '"6.2:read_set"',
                      'section 10 point 13', 'how the recorder names the adapter and the session'):
            self.assertIn(words, doc, words)

    def test_no_import_added(self):
        """TASK-064 AC7, AC2: records.py imports only collections, datetime, json and re, as before."""
        tree = ast.parse(SRC.read_text(encoding='utf-8'))
        imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        froms = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertEqual((imports, froms), ({'collections', 'datetime', 'json', 're'}, []))


if __name__ == '__main__':
    unittest.main()
