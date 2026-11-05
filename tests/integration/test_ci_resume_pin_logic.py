"""Integration tests of the text of the workflow's Resume Check pin (task TASK-121, AC1 to AC6). They compare text only.
The workflow .github/workflows/aieos-checks.yml holds the job value AIEOS_PINNED_RESUME_CHECK_PREVIOUS (empty = off)
and, in each of its two conformance steps, the exact new lines of AC2 (a) to (d); the old base-run condition is gone;
the governor lines and the pushed-file check are as before. The file also holds a pure-Python reference function
base_run_accepts(P, Q, b, n, h) of the rule of AC3 with a truth table. Plainly: the truth table checks a model of the
rule, not the workflow; the workflow's logic is tied to the model only by the literal line pins of AC2 and by the
decision agent's reading of the exact diff (DM A66); that nothing else in the workflow changed is checked by that
reading, not by these tests. Nothing here runs the workflow code. Each test names its criteria in its own docstring."""

import pathlib
import re
import unittest

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
HEXRE = r'[0-9a-f]{64}'
OLD_PIN = 'e1578939404da0b61d56d9187521b92c923e7cb841acdf15d0afb7155605a135'
NEW_PIN = 'b03c0b8a1caaa77c2974da0b512bd38e1f330b5d08dda1bbd85427944eee2e76'
PIN_LINE = ' ' * 10 + "PINNED_RC = os.environ.get('AIEOS_PINNED_RESUME_CHECK', '')"
NEW_LINES = {
    'a': [' ' * 10 + "PREV_RC = os.environ.get('AIEOS_PINNED_RESUME_CHECK_PREVIOUS', '')"],
    'b': [' ' * 14 + "head_rc = blob(head, RESUME_CHECK_FILE)",
          ' ' * 14 + "head_rc_sha = hashlib.sha256(head_rc).hexdigest() if head_rc is not None else 'absent'"],
    'c': [' ' * 14 + "rc_ok = {PINNED_RC}",
          ' ' * 14 + "if HEX.fullmatch(PREV_RC) and rc_sha == PREV_RC and head_rc_sha == PINNED_RC:",
          ' ' * 18 + "rc_ok.add(PREV_RC)"],
    'd': [' ' * 14 + "if mode == 'base' and PINNED_RC and (rc_sha not in rc_ok or rc_named not in rc_ok):",
          ' ' * 18 + "return fail(title, 'the base Resume Check (file %s, run %s) is not an accepted version (%s)' % (",
          ' ' * 22 + "rc_sha, rc_named, ', '.join(sorted(rc_ok))))"],
}
OLD_CONDITION = ' ' * 14 + "if mode == 'base' and PINNED_RC and (rc_sha != PINNED_RC or rc_named != PINNED_RC):"
GOVERNOR_LINES = [
    ' ' * 18 + 'if PINNED and GOVERNOR_FILES[0] in touched and pushed_sha != PINNED:',
    ' ' * 14 + "if gov_sha != PINNED or value['governor_identity'] != PINNED:",
]
PUSHED_FILE_LINE = ' ' * 18 + 'if PINNED_RC and RESUME_CHECK_FILE in touched and pushed_rc_sha != PINNED_RC:'
ENV_PIN_LINE = ' ' * 6 + "AIEOS_PINNED_RESUME_CHECK: '" + NEW_PIN + "'"
ENV_PREVIOUS_LINE = ' ' * 6 + "AIEOS_PINNED_RESUME_CHECK_PREVIOUS: ''"
COMMENT_FIRST = ' ' * 6 + '# AIEOS_PINNED_RESUME_CHECK_PREVIOUS qualifies the "Pinned:" sentence above. Empty means off.'
# Words that must not appear in an added line (AC1, AC6); written in pieces so that this file does not hold them whole.
FORBIDDEN = ['permis' + 'sions:', 'secr' + 'ets.', 'GITHUB_' + 'TOKEN', 'us' + 'es:', 'continue-on-' + 'error',
             'cu' + 'rl', 'w' + 'get', 'ben' + 'ch/', 'nat' + 'ive/']


def workflow_lines():
    return (pathlib.Path(ROOT) / '.github' / 'workflows' / 'aieos-checks.yml').read_bytes().decode('utf-8').split('\n')


def steps(lines):
    """The text of the two conformance steps: from the first PINNED_RC line to the second, and from the second on."""
    at = [i for i, ln in enumerate(lines) if ln == PIN_LINE]
    assert len(at) == 2, len(at)
    return [lines[at[0]:at[1]], lines[at[1]:]]


def base_run_accepts(P, Q, b, n, h):
    """The rule of TASK-121 AC3: P the pin, Q the previous version, b the hash of the base's Resume Check file, n the
    hash that the run record names, h the hash of the head's file."""
    if not P:
        return True
    ok = {P}
    if re.fullmatch(HEXRE, Q) and b == Q and h == P:
        ok.add(Q)
    return b in ok and n in ok


def base_rule(P, b, n):
    """The rule at base_commit: accept iff P is empty or both b and n equal P."""
    return (not P) or (b == P and n == P)


def wrong_rule(P, Q, b, n, h):
    """A wrong model: accepts Q whenever Q is non-empty. The table below must tell it from base_run_accepts."""
    if not P:
        return True
    return (b in (P, Q) if Q else b == P) and (n in (P, Q) if Q else n == P)


A, B, C, D = 'a' * 64, 'b' * 64, 'c' * 64, 'd' * 64


class AC1TheEnvValue(unittest.TestCase):

    def test_the_env_line_and_its_comment(self):
        """TASK-121 AC1 and AC6: the pin line is as before; right after it come the comment block, which begins by
        saying it qualifies the Pinned sentence, and the previous-value line; no forbidden word is in the added block."""
        lines = workflow_lines()
        self.assertEqual(lines.count(ENV_PIN_LINE), 1)
        self.assertEqual(lines.count(ENV_PREVIOUS_LINE), 1)
        i = lines.index(ENV_PIN_LINE)
        j = lines.index(ENV_PREVIOUS_LINE)
        self.assertEqual(j, i + 8)
        self.assertTrue(lines[i + 1].startswith(COMMENT_FIRST))
        block = lines[i + 1:j + 1]
        for ln in block[:-1]:
            self.assertTrue(ln.startswith(' ' * 6 + '# '), ln)
        for ln in block:
            self.assertEqual(ln, ln.rstrip(), ln)
            for word in FORBIDDEN:
                self.assertNotIn(word, ln)

    def test_the_lines_before_the_pin_are_in_form_as_before(self):
        """TASK-121 AC1: the comment of the Resume Check pin (the lines before the pin value line) begins as at
        base_commit and the governor pin line is unchanged in form."""
        lines = workflow_lines()
        i = lines.index(ENV_PIN_LINE)
        self.assertTrue(lines[i - 8].startswith(' ' * 6 + "# The pinned Resume Check version's content hash"))
        self.assertTrue(lines[i - 9].startswith(' ' * 6 + "AIEOS_PINNED_GOVERNOR: '"))

    def test_the_previous_value_line_and_the_two_pins(self):
        """TASK-122 AC2(c) and AC4: the one line of AIEOS_PINNED_RESUME_CHECK_PREVIOUS equals ENV_PREVIOUS_LINE; the
        pin P and the previous value Q are each 64 lowercase hex digits and P differs from Q."""
        hits = [ln for ln in workflow_lines() if ln.strip().startswith('AIEOS_PINNED_RESUME_CHECK_PREVIOUS:')]
        self.assertEqual(hits, [ENV_PREVIOUS_LINE])
        self.assertRegex(NEW_PIN, '^' + HEXRE + '$')
        self.assertRegex(OLD_PIN, '^' + HEXRE + '$')
        self.assertNotEqual(NEW_PIN, OLD_PIN)


class AC2TheCode(unittest.TestCase):

    def test_each_new_line_is_in_each_step_exactly_once(self):
        """TASK-121 AC2 and AC5: in each of the two conformance steps each exact new line of AC2 (a) to (d), whole
        line with its indentation and no trailing space, appears exactly once."""
        for k, step in enumerate(steps(workflow_lines())):
            for part, new in NEW_LINES.items():
                for line in new:
                    with self.subTest(step=k, part=part, line=line):
                        self.assertEqual(step.count(line), 1)

    def test_the_new_lines_follow_their_anchors_in_order(self):
        """TASK-121 AC2: (a) follows the PINNED_RC line; (b) and (c) follow the rc_sha line in order; (d) is the
        condition, the failure line and its last line in a row."""
        for k, step in enumerate(steps(workflow_lines())):
            with self.subTest(step=k):
                self.assertEqual(step[1], NEW_LINES['a'][0])
                at = step.index(' ' * 14 + "rc_sha = hashlib.sha256(rc_file).hexdigest() if rc_file is not None else 'absent'")
                self.assertEqual(step[at + 1:at + 6], NEW_LINES['b'] + NEW_LINES['c'])
                at = step.index(NEW_LINES['d'][0])
                self.assertEqual(step[at:at + 3], NEW_LINES['d'])

    def test_the_old_condition_is_gone(self):
        """TASK-121 AC2 and AC5: the old base-run condition line appears zero times in each step."""
        for k, step in enumerate(steps(workflow_lines())):
            with self.subTest(step=k):
                self.assertEqual(step.count(OLD_CONDITION), 0)

    def test_no_added_line_holds_a_forbidden_word(self):
        """TASK-121 AC6: none of the new code lines holds a word of the forbidden list."""
        for part, new in NEW_LINES.items():
            for line in new:
                for word in FORBIDDEN:
                    with self.subTest(part=part, word=word):
                        self.assertNotIn(word, line)


class AC4TheGovernorAndThePushedFile(unittest.TestCase):

    def test_the_governor_lines_and_the_pushed_file_line_are_unchanged(self):
        """TASK-121 AC4: the governor lines of the push check and of the base check, and the pushed-file check of the
        Resume Check, appear once in each of the two steps as at base_commit."""
        for k, step in enumerate(steps(workflow_lines())):
            for line in GOVERNOR_LINES + [PUSHED_FILE_LINE]:
                with self.subTest(step=k, line=line.strip()):
                    self.assertEqual(step.count(line), 1)


class AC3AC5TheRule(unittest.TestCase):

    def test_the_landing_passes(self):
        """TASK-121 AC3 and AC5: a landing that moves the file from the previous version Q to the pinned version P
        passes (b == Q, n == Q, h == P), as a main push and as a task-branch run (base = origin/main = Q)."""
        self.assertTrue(base_run_accepts(A, B, B, B, A))
        self.assertTrue(base_run_accepts(A, B, B, B, A))

    def test_a_head_file_other_than_p_fails(self):
        """TASK-121 AC3 and AC5: with b == Q and a head file other than P the base run fails."""
        self.assertFalse(base_run_accepts(A, B, B, B, C))
        self.assertFalse(base_run_accepts(A, B, B, B, 'absent'))

    def test_a_base_or_a_record_outside_p_and_q_fails(self):
        """TASK-121 AC3 and AC5: a base equal to neither P nor Q fails; a record n equal to neither P nor the
        accepted Q fails."""
        self.assertFalse(base_run_accepts(A, B, D, D, A))
        self.assertFalse(base_run_accepts(A, B, B, D, A))
        self.assertFalse(base_run_accepts(A, B, B, 'none', A))
        self.assertFalse(base_run_accepts(A, B, B, 'not used', A))
        self.assertFalse(base_run_accepts(A, B, D, B, A))

    def test_a_non_hex_previous_version_is_never_accepted(self):
        """TASK-121 AC3 and AC5: a Q that is not 64 lowercase hex digits is never accepted."""
        for q in ('x' * 64, B.upper(), B[:63], B + 'b', ' ' + B[1:], 'none', 'absent'):
            with self.subTest(q=q):
                self.assertFalse(base_run_accepts(A, q, q, q, A))

    def test_an_empty_previous_version_is_the_base_rule(self):
        """TASK-121 AC3 and AC5: with Q empty the rule equals the rule at base_commit for every input."""
        for p in ('', A):
            for b in (A, B, 'absent', ''):
                for n in (A, B, 'none', 'not used', ''):
                    for h in (A, B, 'absent'):
                        with self.subTest(p=p, b=b, n=n, h=h):
                            self.assertEqual(base_run_accepts(p, '', b, n, h), base_rule(p, b, n))

    def test_an_empty_pin_accepts(self):
        """TASK-121 AC3 and AC5: with P empty the base run accepts (as at base_commit)."""
        self.assertTrue(base_run_accepts('', B, D, D, C))

    def test_q_equal_to_p_is_the_base_rule(self):
        """TASK-121 AC3 and AC5: with Q == P the accepted set is {P}; the rule equals the rule at base_commit."""
        for b in (A, B, 'absent'):
            for n in (A, B, 'none'):
                for h in (A, B):
                    with self.subTest(b=b, n=n, h=h):
                        self.assertEqual(base_run_accepts(A, A, b, n, h), base_rule(A, b, n))

    def test_q_is_not_accepted_when_the_head_is_not_p(self):
        """TASK-121 AC3 and AC5: Q as the base is accepted only with a head file equal to P."""
        for h in (B, C, D, 'absent', ''):
            with self.subTest(h=h):
                self.assertFalse(base_run_accepts(A, B, B, B, h))

    def test_the_table_tells_a_wrong_rule_from_the_right_one(self):
        """TASK-121 AC5: the table can fail: a rule that accepts Q whenever Q is non-empty differs from the right
        rule on the row with a head file other than P and on the row with a non-hex Q."""
        self.assertTrue(wrong_rule(A, B, B, B, C))
        self.assertFalse(base_run_accepts(A, B, B, B, C))
        self.assertTrue(wrong_rule(A, 'zz', 'zz', 'zz', A))
        self.assertFalse(base_run_accepts(A, 'zz', 'zz', 'zz', A))


if __name__ == '__main__':
    unittest.main()
