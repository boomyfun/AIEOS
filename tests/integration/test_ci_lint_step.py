"""Integration tests of the text of the workflow's lint step (task TASK-119, AC1 to AC3). They compare text only: the step
"lint (pyflakes 4.0.3, pinned by version and hash)" of .github/workflows/aieos-checks.yml stands directly after the bandit
step and before the last step, has the fixed form of AC1 (the exact requirements line, the install flags, the exact last
line, no working-directory), holds none of the tokens that AC1 and AC3 forbid, and the header paragraph of revision 19 is
written without the words of AC3's list. The tests show the text, not that a line is reached and not that the job fails
when pyflakes fails, which follows from the form of the step. Each test names its criteria in its own docstring."""

import pathlib
import re
import unittest

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
STEP_NAME = 'lint (pyflakes 4.0.3, pinned by version and hash)'
BANDIT_NAME = 'static_security_analysis (bandit, every package pinned by version and hash)'
LAST_NAME = 'GOV-003 base tests (report only)'
REQ_LINE = 'pyflakes==4.0.3 --hash=sha256:330ba92b8c1db2eb0b8f4068f6c58674e2649a99e334769aa50e3e9c5b11c23a'
INSTALL_LINE = ('"$A/venv/bin/pip" install --quiet --no-deps --require-hashes --only-binary :all: '
                '-r "$A/requirements.txt"')
LAST_LINE = '"$A/venv/bin/pyflakes" "$GITHUB_WORKSPACE/work/src" "$GITHUB_WORKSPACE/work/tests"'
NO_TASK_LINE = 'if grep -q \'"task": null\' task.json; then echo "lint: no task"; exit 0; fi'
AC1_FORBIDDEN = ['continue-on-error', '||', 'set +e', 'set +o', 'true', 'trap', 'python3 -m pyflakes']
AC3_FORBIDDEN = ['permissions', 'secrets', 'GITHUB_TOKEN', 'uses:', 'continue-on-error', 'env:', 'PIP_',
                 'index-url', 'find-links', 'trusted-host', 'curl', 'wget']


def workflow():
    return (pathlib.Path(ROOT) / '.github' / 'workflows' / 'aieos-checks.yml').read_bytes().decode('utf-8')


def steps(wf):
    """The steps of the job as (name, text) in file order: each starts at a line `      - name: ` of the job's steps."""
    parts = re.split(r'(?m)^      - name: ', wf)
    out = []
    for p in parts[1:]:
        name, _, rest = p.partition('\n')
        out.append((name, rest))
    return out


def lint_step(wf):
    found = [(i, t) for i, (n, t) in enumerate(steps(wf)) if n == STEP_NAME]
    return found


def run_lines(text):
    """The lines of the step's run block with their indentation removed."""
    m = re.search(r'(?m)^        run: \|\n((?:          .*\n|\n)*)', text)
    if m is None:
        return None
    return [ln[10:] if ln.startswith('          ') else ln for ln in m.group(1).split('\n')]


class AC1Form(unittest.TestCase):

    def test_the_step_stands_once_between_the_bandit_step_and_the_last_step(self):
        """TASK-119 AC1 and TASK-119 AC2: the lint step exists exactly once, directly after the bandit step, and the
        step that follows it is the last step of the job."""
        wf = workflow()
        all_steps = steps(wf)
        found = lint_step(wf)
        self.assertEqual(len(found), 1)
        i = found[0][0]
        self.assertEqual(all_steps[i - 1][0], BANDIT_NAME)
        self.assertEqual(all_steps[i + 1][0], LAST_NAME)
        self.assertEqual(i + 2, len(all_steps))

    def test_the_step_has_the_condition_no_working_directory_and_the_fixed_lines(self):
        """TASK-119 AC1: the step has the key `if: ${{ !cancelled() }}`, no `working-directory`, begins its run text
        with `set -euo pipefail`, holds the no-task line, the folder line, the venv line, the exact requirements line,
        the exact install line and, as its last line, the exact pyflakes line."""
        step = lint_step(workflow())[0][1]
        self.assertIn('        if: ${{ !cancelled() }}\n', step)
        self.assertNotIn('working-directory', step)
        lines = run_lines(step)
        self.assertIsNotNone(lines)
        body = [ln for ln in lines if ln.strip()]
        self.assertEqual(body[0], 'set -euo pipefail')
        self.assertEqual(body[1], NO_TASK_LINE)
        self.assertIn('A="$RUNNER_TEMP/aieos-lint"', body)
        self.assertIn('python3 -m venv "$A/venv"', body)
        self.assertEqual(body.count(REQ_LINE), 1)
        self.assertEqual(body.count(INSTALL_LINE), 1)
        self.assertEqual(body[-1], LAST_LINE)
        self.assertEqual(body[-2], 'cd "$A"')

    def test_the_run_text_names_pyflakes_only_in_two_lines_and_has_one_exit_and_one_if(self):
        """TASK-119 AC1: in the run text no line names pyflakes other than the requirements line and the last line;
        the only `exit` is the one of the no-task line and the only shell `if` is that line's."""
        lines = [ln for ln in run_lines(lint_step(workflow())[0][1]) if ln.strip()]
        self.assertEqual([ln for ln in lines if 'pyflakes' in ln], [REQ_LINE, LAST_LINE])
        self.assertEqual([ln for ln in lines if re.search(r'\bexit\b', ln)], [NO_TASK_LINE])
        self.assertEqual([ln for ln in lines if re.search(r'(^|[;\s])if\s', ln)], [NO_TASK_LINE])

    def test_the_step_holds_none_of_the_forbidden_tokens_of_this_criterion(self):
        """TASK-119 AC1: the text of the step contains none of the tokens that make a step non-blocking or that read
        a tool from a name the change can shadow."""
        step = lint_step(workflow())[0][1].split('\n      - name: ')[0]
        for tok in AC1_FORBIDDEN:
            with self.subTest(token=tok):
                self.assertNotIn(tok, step)


class AC3Limits(unittest.TestCase):

    def test_the_step_holds_none_of_the_tokens_of_the_limits(self):
        """TASK-119 AC3: the text of the step contains none of the tokens that grant write access, use a secret or
        a token, add an action, read an environment or an index setting, or fetch by another tool."""
        step = lint_step(workflow())[0][1]
        for tok in AC3_FORBIDDEN:
            with self.subTest(token=tok):
                self.assertNotIn(tok, step)

    def test_the_revision_19_paragraph_is_written_without_the_tokens_of_the_limits(self):
        """TASK-119 AC2 and TASK-119 AC3: the header holds a paragraph that begins `# Revision 19 (TASK-119;` and it
        holds none of the tokens of AC3's list."""
        wf = workflow()
        m = re.search(r'(?m)^# Revision 19 \(TASK-119;.*\n(?:# .*\n)*', wf)
        self.assertIsNotNone(m)
        para = m.group(0)
        self.assertIn('TASK-119', para)
        for tok in AC3_FORBIDDEN:
            with self.subTest(token=tok):
                self.assertNotIn(tok, para)

    def test_the_job_timeout_is_unchanged(self):
        """TASK-119 AC2: the job's timeout stays 15 minutes and the base-tests step keeps its own timeout of 4."""
        wf = workflow()
        self.assertEqual(len(re.findall(r'(?m)^    timeout-minutes: 15$', wf)), 1)
        self.assertEqual(len(re.findall(r'(?m)^        timeout-minutes: 4$', wf)), 1)


if __name__ == '__main__':
    unittest.main()
