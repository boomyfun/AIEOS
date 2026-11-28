"""Integration tests of the text of the workflow's governor pin transition (task TASK-177, AC1, AC2, AC4 and AC5). They
compare text only. The workflow .github/workflows/aieos-checks.yml holds the job value AIEOS_PINNED_GOVERNOR_PREVIOUS
(empty = off) and, in each of its two conformance steps, the exact new lines of AC2; the governor lines of the push check
and of the base check are as before. The file also holds a pure-Python reference function
base_run_accepts_governor(P, Q, b, n, h, outcome) of the rule of AC3 with a truth table. Plainly: the truth table checks
a model of the rule, not the workflow; the workflow's logic is tied to the model only by the literal line pins and by the
decision agent's reading of the exact diff (DM A66); that nothing else in the workflow changed is checked by that
reading, not by these tests. Nothing here runs the workflow code. Each test names its criterion in its own
docstring."""

import pathlib
import re
import unittest

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
HEXRE = r'[0-9a-f]{64}'
PINNED_LINE = ' ' * 10 + "PINNED = os.environ.get('AIEOS_PINNED_GOVERNOR', '')"
ENV_BEFORE = ' ' * 6 + "AIEOS_PINNED_RESUME_CHECK_PREVIOUS: ''"
ENV_LINE = ' ' * 6 + "AIEOS_PINNED_GOVERNOR_PREVIOUS: ''"
COMMENT_FIRST = (' ' * 6 + '# AIEOS_PINNED_GOVERNOR_PREVIOUS qualifies the "Pinned:" sentence of AIEOS_PINNED_GOVERNOR'
                 ' above. Empty means off.')
REVISION = 'revision 34 (TASK-177)'
NEW_A = ' ' * 10 + "PREV_GOV = os.environ.get('AIEOS_PINNED_GOVERNOR_PREVIOUS', '')"
ANCHOR_B = ' ' * 18 + 'rc_ok.add(PREV_RC)'
NEW_B = [' ' * 14 + 'head_pin = blob(head, GOVERNOR_FILES[0])',
         ' ' * 14 + "head_pin_sha = hashlib.sha256(head_pin).hexdigest() if head_pin is not None else 'absent'"]
REPORT_ONLY = [' ' * 14 + 'if report_only:', ' ' * 18 + 'return 0']
NEW_C = [(' ' * 14 + 'if HEX.fullmatch(PREV_GOV) and gov_sha == PREV_GOV and head_pin_sha == PINNED and '
          "value['governor_identity'] == PREV_GOV:"),
         ' ' * 18 + "if record['outcome'] != 'pass':",
         ' ' * 22 + "return fail(title, 'outcome %s with the previous pinned governor' % record['outcome'])",
         ' ' * 18 + "print('%s: pass with the previous pinned governor %s' % (title, PREV_GOV))",
         ' ' * 18 + 'return 0']
ANCHOR_D = ' ' * 10 + '#              pass. This step runs before any step that runs code from the pushed commits.'
NEW_D = (' ' * 10 + '#              From revision 34, with AIEOS_PINNED_GOVERNOR_PREVIOUS set, the base run also accepts '
         "that version under the rule of the job's comment.")
PUSH_LINE = ' ' * 18 + 'if PINNED and GOVERNOR_FILES[0] in touched and pushed_sha != PINNED:'
BASE_LINE = ' ' * 14 + "if gov_sha != PINNED or value['governor_identity'] != PINNED:"
# Words that must not appear in an added line (AC5 (iv)); written in pieces so that this file does not hold them whole.
FORBIDDEN = ['permis' + 'sions:', 'secr' + 'ets.', 'GITHUB_' + 'TOKEN', 'us' + 'es:', 'continue-on-' + 'error',
             'cu' + 'rl', 'w' + 'get', 'ben' + 'ch/', 'nat' + 'ive/']


def workflow_lines():
    return (pathlib.Path(ROOT) / '.github' / 'workflows' / 'aieos-checks.yml').read_bytes().decode('utf-8').split('\n')


def pinned_places(lines):
    at = [i for i, ln in enumerate(lines) if ln == PINNED_LINE]
    assert len(at) == 2, len(at)
    return at


def steps(lines):
    """The text of the two conformance steps: from the first PINNED line to the second, and from the second on."""
    at = pinned_places(lines)
    return [lines[at[0]:at[1]], lines[at[1]:]]


def comment_block(lines):
    """The lines after the Resume Check's previous value up to the governor's previous value line."""
    i = lines.index(ENV_BEFORE)
    j = lines.index(ENV_LINE)
    return lines[i + 1:j]


def base_run_accepts_governor(P, Q, b, n, h, outcome):
    """The rule of TASK-177 AC3: P the pin, Q the previous version, b the hash of the base's governor file, n the run's
    governor identity, h the hash of the head's governor file, outcome the run record's outcome."""
    if not P:
        return True
    if outcome != 'pass':
        return False
    if b == P and n == P:
        return True
    return bool(re.fullmatch(HEXRE, Q)) and b == Q and n == Q and h == P


def base_rule(P, b, n, outcome):
    """The rule at base_commit: accept iff P is empty, or the outcome is pass and both b and n equal P."""
    return (not P) or (outcome == 'pass' and b == P and n == P)


def wrong_rule(P, Q, b, n, h, outcome):
    """A wrong model: accepts Q whenever Q is non-empty. The table below must tell it from the right rule."""
    if not P:
        return True
    ok = (P, Q) if Q else (P,)
    return outcome == 'pass' and b in ok and n in ok


A, B, C, D = 'a' * 64, 'b' * 64, 'c' * 64, 'd' * 64


class TheEnvValue(unittest.TestCase):

    def test_the_value_line_is_empty_and_follows_the_resume_checks(self):
        """TASK-177 AC1: the line of the governor's previous value appears once, is empty, and comes after the Resume
        Check's previous value line with only comment lines between them."""
        lines = workflow_lines()
        hits = [ln for ln in lines if ln.strip().startswith('AIEOS_PINNED_GOVERNOR_PREVIOUS:')]
        self.assertEqual(hits, [ENV_LINE])
        self.assertLess(lines.index(ENV_BEFORE), lines.index(ENV_LINE))
        block = comment_block(lines)
        self.assertTrue(block)
        for ln in block:
            self.assertTrue(ln.startswith(' ' * 6 + '# '), ln)
            self.assertEqual(ln, ln.rstrip(), ln)

    def test_the_comment_begins_as_required_and_names_its_revision(self):
        """TASK-177 AC1: the comment block begins with the required line and names its revision."""
        block = comment_block(workflow_lines())
        self.assertEqual(block[0], COMMENT_FIRST)
        self.assertIn(REVISION, ' '.join(ln.strip().lstrip('# ') for ln in block))


class TheCode(unittest.TestCase):

    def test_the_previous_value_is_read_right_after_the_pin(self):
        """TASK-177 AC2: in each step line (a) appears once, directly after the PINNED line."""
        for k, step in enumerate(steps(workflow_lines())):
            with self.subTest(step=k):
                self.assertEqual(step.count(NEW_A), 1)
                self.assertEqual(step[1], NEW_A)

    def test_the_head_governor_is_read_after_the_resume_check_set(self):
        """TASK-177 AC2: in each step the two lines (b) appear once, directly after rc_ok.add(PREV_RC)."""
        for k, step in enumerate(steps(workflow_lines())):
            with self.subTest(step=k):
                for line in NEW_B:
                    self.assertEqual(step.count(line), 1)
                at = step.index(ANCHOR_B)
                self.assertEqual(step[at + 1:at + 3], NEW_B)

    def test_the_accept_branch_stands_between_report_only_and_the_pinned_check(self):
        """TASK-177 AC2: in each step the block (c) is contiguous, once, after the report_only return and before the
        unchanged governor condition."""
        for k, step in enumerate(steps(workflow_lines())):
            with self.subTest(step=k):
                self.assertEqual(step.count(NEW_C[0]), 1)
                at = step.index(BASE_LINE)
                self.assertEqual(step[at - len(NEW_C):at], NEW_C)
                self.assertEqual(step[at - len(NEW_C) - 2:at - len(NEW_C)], REPORT_ONLY)

    def test_each_step_comment_names_the_previous_value(self):
        """TASK-177 AC2: the comment line (d) appears once for each step, directly after that step's anchor line."""
        lines = workflow_lines()
        first, second = pinned_places(lines)
        self.assertEqual(lines.count(NEW_D), 2)
        for k, part in enumerate([lines[:first], lines[first:second]]):
            with self.subTest(step=k):
                self.assertEqual(part.count(NEW_D), 1)
                self.assertEqual(part[part.index(NEW_D) - 1], ANCHOR_D)

    def test_no_added_line_holds_a_forbidden_word(self):
        """TASK-177 AC5: no added line of the workflow holds a word of the forbidden list."""
        lines = workflow_lines()
        added = comment_block(lines) + [ENV_LINE, NEW_A, NEW_D] + NEW_B + NEW_C
        for line in added:
            for word in FORBIDDEN:
                with self.subTest(line=line.strip(), word=word):
                    self.assertNotIn(word, line)


class TheGovernorLines(unittest.TestCase):

    def test_the_push_check_and_the_pinned_check_are_unchanged(self):
        """TASK-177 AC4: the governor lines of the push check and of the base check appear once in each step."""
        for k, step in enumerate(steps(workflow_lines())):
            for line in (PUSH_LINE, BASE_LINE):
                with self.subTest(step=k, line=line.strip()):
                    self.assertEqual(step.count(line), 1)


class TheRule(unittest.TestCase):

    def test_the_landing_passes(self):
        """TASK-177 AC5: a landing that moves the governor from the previous version Q to the pinned version P passes
        (b == Q, n == Q, h == P), as a main push (base = the tip before it) and as a branch run (base = origin/main)."""
        for run in ('main push', 'task branch'):
            with self.subTest(run=run):
                self.assertTrue(base_run_accepts_governor(A, B, B, B, A, 'pass'))

    def test_a_head_file_other_than_p_fails(self):
        """TASK-177 AC5: with b == Q a head file other than P fails."""
        for h in (B, C, D, 'absent', ''):
            with self.subTest(h=h):
                self.assertFalse(base_run_accepts_governor(A, B, B, B, h, 'pass'))

    def test_a_base_outside_p_and_q_fails(self):
        """TASK-177 AC5: a base equal to neither P nor Q fails."""
        for b in (C, D, 'absent', ''):
            with self.subTest(b=b):
                self.assertFalse(base_run_accepts_governor(A, B, b, b, A, 'pass'))

    def test_an_identity_other_than_the_accepted_value_fails(self):
        """TASK-177 AC5: a run identity other than the accepted value fails, a mixed pair included."""
        for b, n in ((B, A), (A, B), (B, C), (A, C), (B, None), (B, 'none'), (B, 'not used'), (B, ''), (A, '')):
            with self.subTest(b=b, n=n):
                self.assertFalse(base_run_accepts_governor(A, B, b, n, A, 'pass'))

    def test_a_non_hex_previous_version_is_never_accepted(self):
        """TASK-177 AC5: a Q that is not 64 lowercase hex digits is never accepted."""
        for q in ('x' * 64, B.upper(), B[:63], B + 'b', ' ' + B[1:], 'none', 'absent'):
            with self.subTest(q=q):
                self.assertFalse(base_run_accepts_governor(A, q, q, q, A, 'pass'))

    def test_an_empty_previous_version_is_the_base_rule(self):
        """TASK-177 AC5: with Q empty the rule equals the rule at base_commit for every input."""
        for p in ('', A):
            for b in (A, B, 'absent', ''):
                for n in (A, B, None, ''):
                    for h in (A, B, 'absent'):
                        for outcome in ('pass', 'fail'):
                            with self.subTest(p=p, b=b, n=n, h=h, outcome=outcome):
                                self.assertEqual(base_run_accepts_governor(p, '', b, n, h, outcome),
                                                 base_rule(p, b, n, outcome))

    def test_an_empty_pin_accepts(self):
        """TASK-177 AC5: with P empty the base run accepts, as at base_commit."""
        for outcome in ('pass', 'fail'):
            with self.subTest(outcome=outcome):
                self.assertTrue(base_run_accepts_governor('', B, D, D, C, outcome))

    def test_q_equal_to_p_is_the_base_rule(self):
        """TASK-177 AC5: with Q == P the rule equals the rule at base_commit."""
        for b in (A, B, 'absent'):
            for n in (A, B, None):
                for h in (A, B):
                    for outcome in ('pass', 'fail'):
                        with self.subTest(b=b, n=n, h=h, outcome=outcome):
                            self.assertEqual(base_run_accepts_governor(A, A, b, n, h, outcome),
                                             base_rule(A, b, n, outcome))

    def test_an_outcome_other_than_pass_is_refused_when_the_pin_is_set(self):
        """TASK-177 AC5: with P set an outcome that is not pass is refused, on the landing and on the pinned base."""
        for outcome in ('fail', 'not run', '', None):
            for b in (A, B):
                with self.subTest(outcome=outcome, b=b):
                    self.assertFalse(base_run_accepts_governor(A, B, b, b, A, outcome))

    def test_the_table_tells_a_wrong_rule_from_the_right_one(self):
        """TASK-177 AC5: the table can fail: a rule that accepts Q whenever Q is non-empty differs from the right rule
        on a head file other than P and on a non-hex Q."""
        self.assertTrue(wrong_rule(A, B, B, B, C, 'pass'))
        self.assertFalse(base_run_accepts_governor(A, B, B, B, C, 'pass'))
        self.assertTrue(wrong_rule(A, 'zz', 'zz', 'zz', A, 'pass'))
        self.assertFalse(base_run_accepts_governor(A, 'zz', 'zz', 'zz', A, 'pass'))


if __name__ == '__main__':
    unittest.main()
