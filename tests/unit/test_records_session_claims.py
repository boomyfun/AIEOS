"""Unit tests of the keys session, acs and text of aieos_bootstrap.records (task TASK-077): check_session_claim and its
call from check_record, over records made up for the test. Each test names its criteria in its own docstring."""

import ast
import pathlib
import re
import unittest

from aieos_bootstrap import records

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap' / 'records.py'


def rec(**kw):
    r = {'record_id': 'made-up/claim/1', 'fact_kind': 'claim', 'source_class': 'agent_declared',
         'recorder': 'a made-up recorder', 'subject': 'TASK-100'}
    r.update(kw)
    return r


def rules(record):
    return [f.rule for f in records.check_record(record)]


def names_its_criteria(doc, task='077'):
    """True when ``doc`` names "TASK-<task> ACn" and no other task's AC in qualified form (whitespace collapsed); task
    is '077' but for the tests of the class IntentClaim, added by task TASK-098, which pass '098'."""
    doc = ' '.join((doc or '').split())
    return (bool(re.findall(r'TASK-%s AC[0-9]+' % task, doc))
            and not re.findall(r'TASK-(?!%s )[0-9]+ AC[0-9]+' % task, doc))


class Keys(unittest.TestCase):
    def test_the_three_keys_are_record_keys(self):
        """TASK-077 AC1: RECORD_KEYS holds session, acs and text, and not ci_run."""
        for key in ('session', 'acs', 'text'):
            self.assertIn(key, records.RECORD_KEYS, key)
        self.assertNotIn('ci_run', records.RECORD_KEYS)

    def test_a_session_claim_in_form_has_no_finding(self):
        """TASK-077 AC1: a claim with session, text and acs (one id), each in form, gives no finding at all."""
        r = rec(session='s-1', text='made-up claim text', acs=['AC1'])
        self.assertEqual(records.check_record(r), [])
        self.assertNotIn('6.2:unknown_key', rules(r))

    def test_ci_run_is_still_unknown(self):
        """TASK-077 AC1: a record with ci_run still gets "6.2:unknown_key"."""
        self.assertIn('6.2:unknown_key', rules(rec(ci_run='123')))


class Session(unittest.TestCase):
    def test_session_out_of_form(self):
        """TASK-077 AC2: session None, '', 3, a list or a dict gives "6.2:session"."""
        for value in (None, '', 3, [], ['s-1'], {}, {'a': 's-1'}):
            with self.subTest(value=value):
                self.assertIn('6.2:session', rules(rec(session=value)))

    def test_session_in_form_on_any_fact_kind(self):
        """TASK-077 AC2: session 's-1' on a claim, an observation or an interpretation gives no finding."""
        self.assertEqual(records.check_record(rec(session='s-1')), [])
        self.assertEqual(records.check_record(rec(session='s-1', fact_kind='observation',
                                                  source_class='deterministic_tool_local')), [])
        self.assertEqual(records.check_record(rec(session='s-1', fact_kind='interpretation')), [])


class Text(unittest.TestCase):
    def test_text_out_of_form(self):
        """TASK-077 AC3: text None, '' or 3 on a session claim gives "6.2:text"."""
        for value in (None, '', 3):
            with self.subTest(value=value):
                self.assertIn('6.2:text', rules(rec(session='s-1', text=value)))

    def test_text_on_a_session_claim(self):
        """TASK-077 AC3: a non-empty text on a claim whose session is set gives no finding."""
        self.assertEqual(records.check_record(rec(session='s-1', text='made-up text')), [])

    def test_text_placed_elsewhere(self):
        """TASK-077 AC3: text on an observation with session, on a claim without session, and on a claim whose session
        is '' gives "6.2:text"; the last gives "6.2:session" too."""
        self.assertIn('6.2:text', rules(rec(session='s-1', text='t', fact_kind='observation',
                                            source_class='deterministic_tool_local')))
        self.assertIn('6.2:text', rules(rec(text='t')))
        found = rules(rec(session='', text='t'))
        self.assertIn('6.2:text', found)
        self.assertIn('6.2:session', found)


class Acs(unittest.TestCase):
    def test_acs_out_of_form(self):
        """TASK-077 AC4: acs None, a str, [], an empty string inside, a repeat or a non-str inside gives "6.2:acs", on
        a session claim and on a gate result."""
        for value in (None, 'AC1', [], ['AC1', ''], ['AC1', 'AC1'], ['AC1', 3]):
            with self.subTest(value=value):
                self.assertIn('6.2:acs', rules(rec(session='s-1', acs=value)))
                self.assertIn('6.2:acs', rules(rec(fact_kind='observation', gate='G2', outcome='pass', acs=value)))

    def test_acs_on_a_session_claim(self):
        """TASK-077 AC4: on a claim whose session is set, two ids give "6.2:acs"; one id or no acs gives none."""
        self.assertIn('6.2:acs', rules(rec(session='s-1', acs=['AC1', 'AC2'])))
        self.assertEqual(records.check_record(rec(session='s-1', acs=['AC1'])), [])
        self.assertEqual(records.check_record(rec(session='s-1')), [])

    def test_acs_on_a_gate_result(self):
        """TASK-077 AC4: on a record with gate set, one or more distinct ids give no finding."""
        for value in (['AC1'], ['AC1', 'AC2']):
            with self.subTest(value=value):
                r = rec(fact_kind='observation', source_class='deterministic_tool_external_ci', gate='G2',
                        outcome='pass', acs=value)
                self.assertEqual(records.check_record(r), [])

    def test_acs_placed_elsewhere(self):
        """TASK-077 AC4: acs on an observation with no gate and no session, or on a claim without session, gives
        "6.2:acs"."""
        self.assertIn('6.2:acs', rules(rec(fact_kind='observation', source_class='deterministic_tool_local',
                                           acs=['AC1'])))
        self.assertIn('6.2:acs', rules(rec(acs=['AC1'])))


class ReadSetKept(unittest.TestCase):
    def test_session_still_forbidden_on_a_read_set_record(self):
        """TASK-077 AC5: an observed read-set record with session still gives "6.2:read_set_forbidden"."""
        r = {'record_id': 'observed-read-set/TASK-100/s-1/record', 'fact_kind': 'observation',
             'source_class': 'deterministic_tool_local', 'recorder': 'a made-up adapter', 'subject': 'TASK-100',
             'evidence_type': 'observed_read_set', 'read_paths': ['a.py'], 'session': 's-1'}
        self.assertIn('6.2:read_set_forbidden', rules(r))
        self.assertIn('session', records.READ_SET_FORBIDDEN)

    def test_imports_unchanged(self):
        """TASK-077 AC5: records.py imports only collections, datetime, json and re."""
        tree = ast.parse(SRC.read_text(encoding='utf-8'))
        imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        froms = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertEqual((imports, froms), ({'collections', 'datetime', 'json', 're'}, []))


class Docstring(unittest.TestCase):
    def test_docstring_states_the_rules_and_limits(self):
        """TASK-077 AC7: the module's docstring states the three keys' rules and the limits (its line breaks and indents
        read as single spaces)."""
        doc = ' '.join(ast.get_docstring(ast.parse(SRC.read_text(encoding='utf-8'))).split())
        for words in ('TASK-077 AC2 to AC4', 'the record keys session, acs and text',
                      'on a record of any fact_kind (a reading)',
                      'allowed only on a record whose fact_kind is claim and whose session is set',
                      'allowed only on a record with gate set or on a claim whose session is set, where it holds '
                      'exactly one id', '"6.2:session", "6.2:text" and "6.2:acs"', "the writer's statement",
                      "no check derives standing from these keys' values", 'ci_run is not a record key',
                      'The pinned identities of governor.py and resume_check.py do not see this module'):
            self.assertIn(words, doc, words)


class Naming(unittest.TestCase):
    def test_every_test_names_its_criteria(self):
        """TASK-077 AC8, as task TASK-098 widens it: every test function of this module names "TASK-077 ACn" in its
        own docstring and no other task's AC in qualified form, but the tests of the class IntentClaim, which name
        "TASK-098 ACn" and no other task's AC."""
        tree = ast.parse(pathlib.Path(__file__).resolve().read_bytes().decode('utf-8'))
        added = {n.name for c in ast.walk(tree) if isinstance(c, ast.ClassDef) and c.name == 'IntentClaim'
                 for n in c.body if isinstance(n, ast.FunctionDef)}
        self.assertGreater(len([name for name in added if name.startswith('test')]), 4)
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
            with self.subTest(test=fn.name):
                self.assertTrue(names_its_criteria(ast.get_docstring(fn), '098' if fn.name in added else '077'))

    def test_the_naming_check_refuses(self):
        """TASK-077 AC8: the naming check refuses another task's id and a missing id, and admits this task's."""
        self.assertFalse(names_its_criteria('TASK-076 AC1: made up.'))
        self.assertFalse(names_its_criteria('made up, no id'))
        self.assertFalse(names_its_criteria(None))
        self.assertFalse(names_its_criteria('TASK-077 AC1 and TASK-076 AC2: made up.'))
        self.assertTrue(names_its_criteria('TASK-077 AC1: made up.'))


class IntentClaim(unittest.TestCase):
    def intent(self, **kw):
        r = rec(subject='INT-001', evidence_type='intent', text='made-up intent text')
        r.update(kw)
        return r

    def test_an_intent_claim_may_carry_text(self):
        """TASK-098 AC3: a claim whose evidence_type is intent, whose subject is "INT-" followed by digits and which has
        no session key gives no finding with its text."""
        self.assertEqual(records.check_record(self.intent()), [])
        self.assertEqual(records.check_record(self.intent(subject='INT-12')), [])

    def test_the_intent_claim_test(self):
        """TASK-098 AC3: _is_intent_claim is true for an intent's claim only: not for another fact_kind, another or no
        evidence_type, a subject out of form, or a record with a session key."""
        self.assertTrue(records._is_intent_claim(self.intent()))
        bad = [self.intent(fact_kind='observation'), self.intent(fact_kind='interpretation'),
               self.intent(evidence_type='contract_edit'), self.intent(evidence_type='intents'),
               self.intent(session='s-1')]
        for subject in ('TASK-100', 'INT-', 'INT-1a', 'int-1', ' INT-1', 'INT-1\n', 3, None):
            bad.append(self.intent(subject=subject))
        no_type = self.intent()
        del no_type['evidence_type']
        bad.append(no_type)
        for record in bad:
            with self.subTest(record=record):
                self.assertFalse(records._is_intent_claim(record))

    def test_text_still_refused_off_an_intent_claim(self):
        """TASK-098 AC3: text on an intent-typed claim whose subject is a task id or another subject, on an INT- claim
        of another evidence_type, on one with a session key that is '' or not a str, or on an intent-typed observation
        or interpretation gives "6.2:text"; an empty text on an intent's claim gives it too."""
        for record in (self.intent(subject='TASK-100'), self.intent(subject='made-up'),
                       self.intent(evidence_type='other'), self.intent(session=''), self.intent(session=3),
                       self.intent(fact_kind='observation', source_class='deterministic_tool_local'),
                       self.intent(fact_kind='interpretation'), self.intent(text='')):
            with self.subTest(record=record):
                self.assertIn('6.2:text', rules(record))

    def test_the_session_and_acs_rules_are_unchanged(self):
        """TASK-098 AC3: on an intent's claim, acs gives "6.2:acs" (no session and no gate) and a session of ''
        gives "6.2:session"."""
        self.assertIn('6.2:acs', rules(self.intent(acs=['AC1'])))
        self.assertIn('6.2:session', rules(self.intent(session='')))

    def test_the_widened_naming_check(self):
        """TASK-098 AC3: the naming check, given '098', admits "TASK-098 ACn" alone and refuses this module's other
        id, another task's AC beside it and a missing id; without it, it still reads '077'."""
        self.assertTrue(names_its_criteria('TASK-098 AC3: made up.', '098'))
        self.assertFalse(names_its_criteria('TASK-077 AC3: made up.', '098'))
        self.assertFalse(names_its_criteria('TASK-098 AC3 and TASK-096 AC2: made up.', '098'))
        self.assertFalse(names_its_criteria('made up, no id', '098'))
        self.assertFalse(names_its_criteria('TASK-098 AC3: made up.'))

    def test_the_docstring(self):
        """TASK-098 AC3: the module docstring of records.py holds the intent's claim bullet and keeps the text rule's
        phrase."""
        doc = ' '.join(ast.get_docstring(ast.parse(SRC.read_text(encoding='utf-8'))).split())
        for words in ("An intent's claim", 'TASK-098', '_is_intent_claim', 'whose evidence_type is intent',
                      'allowed only on a record whose fact_kind is claim and whose session is set'):
            self.assertIn(words, doc, words)


if __name__ == '__main__':
    unittest.main()
