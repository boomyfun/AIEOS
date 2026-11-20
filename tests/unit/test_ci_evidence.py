"""Unit tests of the CI evidence module of TASK-151 (BT3a, AC1 to AC8). Every case is built in memory; the log fixtures below
are cut by script, byte for byte, from the saved logs of two CI runs of the TASK-150 push (the line ranges are named in
the comment at the fixtures) and are embedded as constants, so no test reads a log file; the only files read are the
module's own source and, for the step names, none.
"""
import ast
import copy
import hashlib
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import ci_evidence
from aieos_bootstrap import gate_records
from aieos_bootstrap import governor
from aieos_bootstrap import records

ROOT = pathlib.Path(__file__).resolve().parents[2]
# The fixtures: byte-for-byte cuts of the saved logs of `gh run view <id> --log` (each line: job TAB step TAB text), written as ASCII
# string literals (ESC as \x1b, the byte-order mark as \ufeff); cut by script from the sources named here, line numbers of the full logs.
# BRANCH_LOG: aieos-checks run 44780942904 (the task branch push), lines 30, 143-144, 229-233.
BRANCH_LOG = (
    'checks\tSet up job\t2026-11-20T17:11:58.6217825Z Complete job name: checks\n'
    "checks\tG0 task detection (the contract commit on main)\t2026-11-20T17:12:03.0320708Z \x1b[36;1m        open('../range-base.txt', 'w').write('')\x1b[0m\n"
    "checks\tG0 task detection (the contract commit on main)\t2026-11-20T17:12:03.0321134Z \x1b[36;1m        print('G0 detect: no task (no pushed commit outside main carries an AIEOS-Task trailer; commits outside main: %d)' % len(ahead))\x1b[0m\n"
    'checks\tG0 task detection (the contract commit on main)\t2026-11-20T17:12:03.3557860Z   AIEOS_ARGS: detect\n'
    'checks\tG0 task detection (the contract commit on main)\t2026-11-20T17:12:03.3558218Z ##[endgroup]\n'
    'checks\tG0 task detection (the contract commit on main)\t2026-11-20T17:12:03.4046970Z G0 detect: task TASK-150 contract commit 3572f9585da94f9ec2fb749a25e46a9e040f0033 base f48804f6e3001a3c9dd070437e7ce339d7881150\n'
    'checks\tG0 task detection (the contract commit on main)\t2026-11-20T17:12:03.4068619Z G0 contract sha256 7c45fd60c17666c085b2c5d6583a01e70988e2fcf3c0fad1117a8f673eb504ff\n'
    'checks\tCollect the pushed commits and their changed paths\t\ufeff2026-11-20T17:12:03.4097193Z ##[group]Run set -euo pipefail\n'
)
# MAIN_LOG: aieos-checks run 44777971143 (the push of main at the contract commit), lines 143-144, 229-232.
MAIN_LOG = (
    "checks\tG0 task detection (the contract commit on main)\t2026-11-20T16:54:18.0041934Z \x1b[36;1m        open('../range-base.txt', 'w').write('')\x1b[0m\n"
    "checks\tG0 task detection (the contract commit on main)\t2026-11-20T16:54:18.0044129Z \x1b[36;1m        print('G0 detect: no task (no pushed commit outside main carries an AIEOS-Task trailer; commits outside main: %d)' % len(ahead))\x1b[0m\n"
    'checks\tG0 task detection (the contract commit on main)\t2026-11-20T16:54:18.0468999Z   AIEOS_ARGS: detect\n'
    'checks\tG0 task detection (the contract commit on main)\t2026-11-20T16:54:18.0470099Z ##[endgroup]\n'
    'checks\tG0 task detection (the contract commit on main)\t2026-11-20T16:54:18.0825689Z G0 detect: no task (no pushed commit outside main carries an AIEOS-Task trailer; commits outside main: 0)\n'
    'checks\tCollect the pushed commits and their changed paths\t\ufeff2026-11-20T16:54:18.0924408Z ##[group]Run set -euo pipefail\n'
)

TASK = 'TASK-150'
COMMIT = '06880dd8d00b69fa2a9f25fc4036a635bdd31fc0'
SHA = '7c45fd60c17666c085b2c5d6583a01e70988e2fcf3c0fad1117a8f673eb504ff'
IV = {'SPEC-001': 'v2'}
WORKFLOW = '.github/workflows/aieos-checks.yml'
MAP = gate_records.DEFAULT_CHECK_MAP
MAPPED = ['G0 task detection (the contract commit on main)', 'G0 scope (V0)', 'G1 build',
          'lint (pyflakes 4.0.3, pinned by version and hash)']
PLAN4 = [{'gate': 'G0', 'check': 'scope'}, {'gate': 'G1', 'check': 'build'}, {'gate': 'G2', 'check': 'lint'},
         {'gate': 'G3', 'check': 'review', 'args': ['AC1', 'AC2']}]
DEFAULT = object()  # "not given", so that None can be passed as an argument


def step(name, conclusion='success'):
    return {'name': name, 'conclusion': conclusion}


def all_steps(conclusion='success'):
    return [step(n, conclusion) for n in MAPPED]


def run(**changes):
    r = {'run_id': 100, 'attempt': 1, 'head_sha': COMMIT, 'event': 'push', 'head_branch': 'task/' + TASK,
         'workflow_path': WORKFLOW, 'status': 'completed', 'conclusion': 'success', 'steps': all_steps(),
         'log': BRANCH_LOG}
    r.update(changes)
    return r


def call(**kw):
    a = {'task_id': TASK, 'commit': COMMIT, 'contract_sha256': SHA, 'intent_versions': dict(IV),
         'plan': copy.deepcopy(PLAN4), 'changed_paths': ['src/aieos_bootstrap/gate_records.py'], 'runs': [run()],
         'recorder': 'external CI'}
    a.update(kw)
    return ci_evidence.ci_evidence(a['task_id'], a['commit'], a['contract_sha256'], a['intent_versions'], a['plan'],
                                   a['changed_paths'], a['runs'], a['recorder'])


def refusal(out):
    return (out['refusal']['reason'], out['refusal']['detail']) if out['refusal'] else None


def gates(out):
    return {r['gate']: r['outcome'] for r in out['records']}


def with_log(*mods, base=BRANCH_LOG):
    """The branch log with exact line edits: each mod is (old, new) and must occur exactly once."""
    t = base
    for old, new in mods:
        assert t.count(old) == 1, old
        t = t.replace(old, new)
    return t


class Boom(BaseException):
    """A BaseException that is not an Exception (AC1, AC5)."""


class AC1TheModule(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / 'src/aieos_bootstrap/ci_evidence.py').read_bytes().decode('utf-8')

    def test_public_names_are_exactly_one(self):
        tree = ast.parse(self.source)
        public = set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith('_'):
                public.add(node.name)
            elif isinstance(node, ast.Assign):
                public.update(t.id for t in node.targets if isinstance(t, ast.Name) and not t.id.startswith('_'))
        self.assertEqual(public, {'ci_evidence'})

    def test_the_public_attributes_of_the_module_are_the_function_and_the_three_imports(self):
        # the imported modules are attributes of the module object; AC1 names them as the import list, not as public names
        attrs = {n for n in dir(ci_evidence) if not n.startswith('_')}
        self.assertEqual(attrs, {'ci_evidence', 'hashlib', 're', 'gate_records'})

    def test_imports_and_forbidden_names(self):
        tree = ast.parse(self.source)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.update(node.module + '.' + a.name for a in node.names)
        self.assertEqual(imports, {'hashlib', 're', 'aieos_bootstrap.gate_records'})
        calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertFalse(calls & {'open', 'exec', 'eval', 'compile', '__import__'})
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for bad in ('subprocess', 'system', 'environ', 'time', 'now'):
            self.assertNotIn(bad, names)

    def test_the_return_form(self):
        ok, bad = call(), call(task_id='x')
        self.assertEqual(set(ok), {'records', 'uncovered', 'evidence', 'refusal'})
        self.assertEqual(set(bad), {'records', 'uncovered', 'evidence', 'refusal'})
        self.assertIsNone(ok['refusal'])
        self.assertEqual((bad['records'], bad['uncovered'], bad['evidence']), ([], [], None))

    def test_every_argument_check_names_its_exact_detail(self):
        sha_e = 'contract_sha256 is not 64 lowercase hexadecimal characters'
        iv_e = 'intent_versions holds an entry that is not a non-empty name and v and digits'
        plan_e = 'a plan entry is not a mapping with the keys gate and check and at most args'
        gate_e = 'a plan entry has a gate that is not G and digits'
        check_e = 'a plan entry has a check that is not a non-empty text'
        paths_e = 'changed_paths is not a list of non-empty texts'
        run_e = 'a run is not a mapping with exactly the run keys'
        id_e = 'a run has a run_id or an attempt that is not an integer above zero'
        text_e = 'a run has a head_sha, event, head_branch, workflow_path, status or log that is not a text'
        concl_e = 'a run has a conclusion that is neither a text nor None'
        steps_e = 'a run has steps that are not a list'
        step_keys_e = 'a step is not a mapping with exactly the keys name and conclusion'
        step_name_e = 'a step has a name that is not a non-empty text'
        step_concl_e = 'a step has a conclusion that is neither a text nor None'
        bad = [
            ('task_id is not TASK- and digits', dict(task_id='TASK-')), ('task_id is not TASK- and digits', dict(task_id=5)),
            ('commit is not 40 lowercase hexadecimal characters', dict(commit='A' * 40)),
            ('commit is not 40 lowercase hexadecimal characters', dict(commit='a' * 39)),
            (sha_e, dict(contract_sha256='A' * 64)), (sha_e, dict(contract_sha256='a' * 63)), (sha_e, dict(contract_sha256=None)),
            ('intent_versions is not a non-empty mapping', dict(intent_versions={})),
            ('intent_versions is not a non-empty mapping', dict(intent_versions=[('a', 'v1')])),
            (iv_e, dict(intent_versions={'': 'v1'})), (iv_e, dict(intent_versions={'a': 'v'})), (iv_e, dict(intent_versions={'a': 1})),
            ('plan is not a non-empty list', dict(plan=[])), ('plan is not a non-empty list', dict(plan='G0')),
            (plan_e, dict(plan=['G0'])), (plan_e, dict(plan=[{'gate': 'G0'}])),
            (plan_e, dict(plan=[{'gate': 'G0', 'check': 'scope', 'x': 1}])),
            (gate_e, dict(plan=[{'gate': 'g0', 'check': 'scope'}])), (gate_e, dict(plan=[{'gate': 3, 'check': 'scope'}])),
            (check_e, dict(plan=[{'gate': 'G0', 'check': ''}])), (check_e, dict(plan=[{'gate': 'G0', 'check': 3}])),
            (paths_e, dict(changed_paths='a')), (paths_e, dict(changed_paths=[''])), (paths_e, dict(changed_paths=[3])),
            ('runs is not a list', dict(runs=None)),
            (run_e, dict(runs=['x'])), (run_e, dict(runs=[{'run_id': 1}])),
            (id_e, dict(runs=[run(run_id=True)])), (id_e, dict(runs=[run(run_id=1.0)])), (id_e, dict(runs=[run(run_id=0)])),
            (id_e, dict(runs=[run(attempt=False)])), (id_e, dict(runs=[run(attempt=-1)])),
            (text_e, dict(runs=[run(head_sha=3)])), (text_e, dict(runs=[run(event=None)])), (text_e, dict(runs=[run(log=b'x')])),
            (concl_e, dict(runs=[run(conclusion=1)])), (steps_e, dict(runs=[run(steps=None)])),
            (step_keys_e, dict(runs=[run(steps=['x'])])), (step_keys_e, dict(runs=[run(steps=[{'name': 'a'}])])),
            (step_name_e, dict(runs=[run(steps=[step('')])])), (step_name_e, dict(runs=[run(steps=[step(3)])])),
            (step_concl_e, dict(runs=[run(steps=[step('a', 1)])])),
            ('recorder is not a non-empty text', dict(recorder='')), ('recorder is not a non-empty text', dict(recorder=None)),
        ]
        for want, kw in bad:
            out = call(**kw)
            self.assertEqual(refusal(out), ('argument', want), kw)
            self.assertEqual((out['records'], out['uncovered'], out['evidence']), ([], [], None), kw)

    def test_a_plan_entry_may_carry_args(self):
        self.assertIn('args', PLAN4[3])  # the default call passes the review entry with its args key
        self.assertIsNone(call()['refusal'])

    def test_no_exception_escapes(self):
        class Bad(dict):
            def __len__(self):
                raise RuntimeError('own method')

        out = call(intent_versions=Bad(IV))
        self.assertEqual(refusal(out), ('argument', 'an argument could not be read: RuntimeError'))
        self.assertEqual((out['records'], out['uncovered'], out['evidence']), ([], [], None))

    def test_a_base_exception_passes_through(self):
        class Worse(dict):
            def __len__(self):
                raise Boom()

        with self.assertRaises(Boom):
            call(intent_versions=Worse(IV))


class AC2TheLog(unittest.TestCase):
    def test_the_branch_fixture_is_accepted_and_the_echoed_no_task_text_is_not_read(self):
        self.assertIn('G0 detect: no task', BRANCH_LOG)  # in the echoed source, before the endgroup
        out = call()
        self.assertIsNone(out['refusal'])
        self.assertIn('G0 detect: task TASK-150 contract commit 3572f9585da94f9ec2fb749a25e46a9e040f0033 base f48804f6e3001a3c9dd070437e7ce339d7881150',
                      out['evidence']['detect_line'])

    def test_the_main_fixture_says_no_task_and_is_refused(self):
        self.assertEqual(refusal(call(runs=[run(log=MAIN_LOG)])), ('detect', 'the detect step says no task'))

    def test_task_text_only_in_the_echoed_source_names_no_task(self):
        # before the endgroup, two lines whose messages are exactly a valid detect line and a valid contract line
        echoed = ('checks\tG0 task detection (the contract commit on main)\t2026-11-20T16:54:18.0000000Z G0 detect: task TASK-150 contract commit '
                  + 'a' * 40 + ' base ' + 'b' * 40 + '\n'
                  + 'checks\tG0 task detection (the contract commit on main)\t2026-11-20T16:54:18.0000001Z G0 contract sha256 ' + SHA + '\n')
        marker = 'checks\tG0 task detection (the contract commit on main)\t2026-11-20T16:54:18.0470099Z ##[endgroup]\n'
        log = with_log((marker, echoed + marker), base=MAIN_LOG)
        self.assertEqual(refusal(call(runs=[run(log=log)])), ('detect', 'the detect step says no task'))
        log2 = with_log(('G0 detect: no task (no pushed commit outside main carries an AIEOS-Task trailer; commits outside main: 0)', 'G0 detect: nothing'), base=log)
        self.assertEqual(refusal(call(runs=[run(log=log2)])), ('detect', 'the detect step output has 0 detect lines (exactly one is expected)'))

    def test_endgroup_count(self):
        no_end = with_log(('##[endgroup]', '##[endxroup]'))
        self.assertEqual(refusal(call(runs=[run(log=no_end)])), ('detect', 'the detect step has 0 endgroup lines (exactly one is expected)'))
        line = [ln for ln in BRANCH_LOG.split('\n') if ln.endswith('##[endgroup]') and ln.startswith('checks\tG0 task detection')][0]
        two = with_log((line + '\n', line + '\n' + line + '\n'))
        self.assertEqual(refusal(call(runs=[run(log=two)])), ('detect', 'the detect step has 2 endgroup lines (exactly one is expected)'))

    def test_detect_and_contract_lines(self):
        det = [ln for ln in BRANCH_LOG.split('\n') if 'G0 detect: task' in ln][0]
        con = [ln for ln in BRANCH_LOG.split('\n') if 'G0 contract sha256' in ln][0]
        two = with_log((det + '\n', det + '\n' + det + '\n'))
        self.assertEqual(refusal(call(runs=[run(log=two)])), ('detect', 'the detect step output has 2 detect lines (exactly one is expected)'))
        self.assertEqual(refusal(call(runs=[run(log=with_log((con + '\n', '')))])),
                         ('detect', 'the detect step output has 0 contract sha256 lines (exactly one is expected)'))
        self.assertEqual(refusal(call(runs=[run(log=with_log((con + '\n', con + '\n' + con + '\n')))])),
                         ('detect', 'the detect step output has 2 contract sha256 lines (exactly one is expected)'))
        self.assertEqual(refusal(call(contract_sha256='0' * 64)), ('detect', 'the contract sha256 of the log differs from the expected one'))
        self.assertEqual(refusal(call(task_id='TASK-151')), ('run', 'no eligible run'))  # another task: the branch differs
        other = with_log(('G0 detect: task TASK-150 contract', 'G0 detect: task TASK-151 contract'))
        self.assertEqual(refusal(call(runs=[run(log=other)])), ('detect', 'the detect line names another task'))

    def test_a_line_out_of_the_pinned_form(self):
        first = BRANCH_LOG.split('\n')[0]
        for mod, want in ((('\n', '\nno tabs here\n', 1), 'line 2 is not job TAB step TAB text'),
                          ((first, 'checks\tSet up job\t2026-13-xx', 1), 'line 1 has no timestamp in the pinned form')):
            old, new, _ = mod
            log = BRANCH_LOG.replace(old, new, 1)
            self.assertEqual(refusal(call(runs=[run(log=log)])), ('log_format', want))
        self.assertEqual(refusal(call(runs=[run(log='')])), ('log_format', 'the log is empty'))
        self.assertEqual(refusal(call(runs=[run(log='\n')])), ('log_format', 'line 1 is not job TAB step TAB text'))

    def test_a_log_without_the_job_checks_or_the_detect_step(self):
        other_job = BRANCH_LOG.replace('checks\t', 'other\t')
        self.assertEqual(refusal(call(runs=[run(log=other_job)])), ('log_format', 'the log has no line of the job checks'))
        other_step = BRANCH_LOG.replace('checks\tG0 task detection (the contract commit on main)\t', 'checks\tAnother step\t')
        self.assertEqual(refusal(call(runs=[run(log=other_step)])), ('detect', 'the log has no line of the detect step'))

    def test_lines_of_other_jobs_and_steps_never_count(self):
        det = [ln for ln in BRANCH_LOG.split('\n') if 'G0 detect: task' in ln][0]
        extra = det.replace('checks\tG0 task detection (the contract commit on main)\t', 'other\tG0 task detection (the contract commit on main)\t') + '\n'
        self.assertIsNone(call(runs=[run(log=BRANCH_LOG + extra)])['refusal'])
        extra2 = det.replace('G0 task detection (the contract commit on main)', 'G0 scope (V0)') + '\n'
        self.assertIsNone(call(runs=[run(log=BRANCH_LOG + extra2)])['refusal'])

    def test_crlf_is_read_in_the_pinned_form(self):
        crlf = BRANCH_LOG.replace('\n', '\r\n')
        self.assertIsNone(call(runs=[run(log=crlf)])['refusal'])

    def test_the_byte_order_mark_is_allowed_at_the_start_of_the_text_only(self):
        bom = chr(0xFEFF)
        self.assertIn(bom, BRANCH_LOG)  # the fixture has it on the first line of a later step
        det = [ln for ln in BRANCH_LOG.split('\n') if 'G0 detect: task' in ln][0]
        job, name, text = det.split('\t', 2)
        self.assertFalse(text.startswith(bom))
        # at the start of the text of the detect line itself: accepted, and the detect line of the evidence is unchanged
        out = call(runs=[run(log=with_log((det, job + '\t' + name + '\t' + bom + text)))])
        self.assertIsNone(out['refusal'])
        self.assertEqual(out['evidence']['detect_line'], call()['evidence']['detect_line'])
        # in the job field of every line: no line of the job checks
        self.assertEqual(refusal(call(runs=[run(log=BRANCH_LOG.replace('checks\t', bom + 'checks\t'))])),
                         ('log_format', 'the log has no line of the job checks'))
        # in the job field of the lines of the detect step only: no line of the detect step
        step_lines = 'checks\tG0 task detection (the contract commit on main)\t'
        self.assertEqual(refusal(call(runs=[run(log=BRANCH_LOG.replace(step_lines, bom + step_lines))])),
                         ('detect', 'the log has no line of the detect step'))

    def test_detect_and_contract_lines_that_only_start_like_the_pinned_form_are_not_read(self):
        commit_e = 'contract commit 3572f9585da94f9ec2fb749a25e46a9e040f0033 base'
        zero_detect = ('detect', 'the detect step output has 0 detect lines (exactly one is expected)')
        # a task id with more digits is a well-formed detect line of ANOTHER task (TASK-1500 is not TASK-150)
        self.assertEqual(refusal(call(runs=[run(log=with_log(('G0 detect: task TASK-150 contract', 'G0 detect: task TASK-1500 contract')))])),
                         ('detect', 'the detect line names another task'))
        # a commit of 41 characters is not a detect line of the pinned form
        self.assertEqual(refusal(call(runs=[run(log=with_log((commit_e, commit_e.replace(' base', 'a base'))))])), zero_detect)
        # text after the second sha of the detect line: not the pinned form
        base_e = ' base f48804f6e3001a3c9dd070437e7ce339d7881150'
        self.assertEqual(refusal(call(runs=[run(log=with_log((base_e, base_e + ' and more')))])), zero_detect)
        zero_sum = ('detect', 'the detect step output has 0 contract sha256 lines (exactly one is expected)')
        upper = with_log(('G0 contract sha256 ' + SHA, 'G0 contract sha256 ' + SHA.upper()))
        self.assertEqual(refusal(call(runs=[run(log=upper)])), zero_sum)
        # a contract line with 65 hexadecimal characters, or with text after the sha: not the pinned form
        self.assertEqual(refusal(call(runs=[run(log=with_log(('G0 contract sha256 ' + SHA, 'G0 contract sha256 ' + SHA + 'a')))])), zero_sum)
        self.assertEqual(refusal(call(runs=[run(log=with_log(('G0 contract sha256 ' + SHA, 'G0 contract sha256 ' + SHA + ' x')))])), zero_sum)

    def test_a_log_that_is_not_utf_8_text_is_refused_as_a_log_format(self):
        surrogate = BRANCH_LOG + 'checks\tSet up job\t2026-11-20T17:12:03.0000000Z a' + chr(0xD800) + 'b\n'
        self.assertEqual(refusal(call(runs=[run(log=surrogate)])),
                         ('log_format', 'run 100 attempt 1: the log is not UTF-8 text'))
        out = call(runs=[run(log=surrogate)])
        self.assertEqual((out['records'], out['uncovered'], out['evidence']), ([], [], None))
        # the second attempt carries it; the first is a good log
        self.assertEqual(refusal(call(runs=[run(), run(attempt=2, log=surrogate)])),
                         ('log_format', 'run 100 attempt 2: the log is not UTF-8 text'))
        # a log that has the surrogate and also no detect line is refused for the encoding first
        self.assertEqual(refusal(call(runs=[run(log=MAIN_LOG + 'checks\tSet up job\t2026-11-20T17:12:03.0000000Z' + ' ' + chr(0xD800) + '\n')])),
                         ('log_format', 'run 100 attempt 1: the log is not UTF-8 text'))


class AC3TheRuns(unittest.TestCase):
    def test_other_runs_of_the_same_sha_are_ignored(self):
        runs = [run(), run(run_id=7, head_branch='main', log=MAIN_LOG), run(run_id=8, event='pull_request', log=MAIN_LOG),
                run(run_id=9, workflow_path='.github/workflows/aieos-native.yml', log=MAIN_LOG),
                run(run_id=10, head_sha='b' * 40, log=MAIN_LOG), run(run_id=11, head_branch='task/TASK-1500', log=MAIN_LOG)]
        out = call(runs=runs)
        self.assertIsNone(out['refusal'])
        self.assertEqual([r['run_id'] for r in out['evidence']['runs']], [100])

    def test_refusals(self):
        self.assertEqual(refusal(call(runs=[])), ('run', 'no eligible run'))
        self.assertEqual(refusal(call(runs=[run(head_branch='main')])), ('run', 'no eligible run'))
        self.assertEqual(refusal(call(runs=[run(head_branch='task/TASK-1500')])), ('run', 'no eligible run'))
        self.assertEqual(refusal(call(runs=[run(status='in_progress', conclusion=None)])),
                         ('run', 'run 100 attempt 1 is not completed with success or failure'))
        for c in ('cancelled', 'skipped', None, 'neutral'):
            self.assertEqual(refusal(call(runs=[run(conclusion=c)])), ('run', 'run 100 attempt 1 is not completed with success or failure'), c)
        self.assertEqual(refusal(call(runs=[run(), run()])), ('run', 'run 100 attempt 1 is given twice'))

    def test_a_failed_run_with_the_detect_line_is_evidence_for_a_fail(self):
        steps = [step(n) for n in MAPPED[:2]] + [step('G1 build', 'failure'), step(MAPPED[3])]
        out = call(runs=[run(conclusion='failure', steps=steps)])
        self.assertIsNone(out['refusal'])
        self.assertEqual(gates(out), {'G0': 'pass', 'G1': 'fail', 'G2': 'pass'})


class AC4TheRerunRule(unittest.TestCase):
    def test_two_agreeing_attempts_give_the_records_of_one(self):
        one = call()
        two = call(runs=[run(), run(attempt=2)])
        self.assertEqual(two['records'], one['records'])
        self.assertEqual([(r['run_id'], r['attempt']) for r in two['evidence']['runs']], [(100, 1), (100, 2)])

    def test_a_flaky_failure_then_a_pass_refuses_in_both_orders(self):
        failed = [step(n) for n in MAPPED[:2]] + [step('G1 build', 'failure'), step(MAPPED[3])]
        for runs in ([run(conclusion='failure', steps=failed), run(attempt=2)], [run(), run(attempt=2, conclusion='failure', steps=failed)]):
            self.assertEqual(refusal(call(runs=runs)), ('rerun', 'the attempts disagree on the step G1 build'))

    def test_a_different_detect_line_refuses(self):
        other = with_log(('base f48804f6', 'base f48804f7'))
        self.assertEqual(refusal(call(runs=[run(), run(attempt=2, log=other)])), ('rerun', 'the attempts disagree on the detect line'))

    def test_a_mapped_step_absent_in_one_attempt_or_present_twice_refuses(self):
        fewer = [s for s in all_steps() if s['name'] != 'G1 build']
        self.assertEqual(refusal(call(runs=[run(), run(attempt=2, steps=fewer)])), ('rerun', 'the attempts disagree on the step G1 build'))
        twice = all_steps() + [step('G1 build')]
        self.assertEqual(refusal(call(runs=[run(), run(attempt=2, steps=twice)])), ('rerun', 'the attempts disagree on the step G1 build'))

    def test_a_single_run_with_an_absent_or_repeated_mapped_step_is_not_refused(self):
        fewer = [s for s in all_steps() if s['name'] != 'G1 build']
        out = call(runs=[run(steps=fewer)])
        self.assertIsNone(out['refusal'])
        self.assertIn({'gate': 'G1', 'check': 'build', 'detail': 'step not present'}, out['uncovered'])
        out = call(runs=[run(steps=all_steps() + [step('G1 build')])])
        self.assertIsNone(out['refusal'])
        self.assertIn({'gate': 'G1', 'check': 'build', 'detail': 'step named more than once'}, out['uncovered'])

    def test_the_steps_given_to_the_maker_are_those_of_the_highest_attempt(self):
        first = all_steps() + [step('unit_test', 'success')]
        second = all_steps() + [step('unit_test', 'failure')]
        seen = []

        def capture(task_id, commit, intent_versions, plan, steps, check_map, recorder):
            seen.append(copy.deepcopy(steps))
            return {'records': [], 'uncovered': [], 'error': None}

        with mock.patch.object(ci_evidence.gate_records, 'gate_records', capture):
            self.assertIsNone(call(runs=[run(attempt=2, steps=second), run(attempt=1, steps=first)])['refusal'])
        self.assertEqual(seen, [second])

    def _chosen_steps(self, runs):
        seen = []

        def capture(task_id, commit, intent_versions, plan, steps, check_map, recorder):
            seen.append(copy.deepcopy(steps))
            return {'records': [], 'uncovered': [], 'error': None}

        with mock.patch.object(ci_evidence.gate_records, 'gate_records', capture):
            out = call(runs=runs)
        self.assertIsNone(out['refusal'])
        return seen, out

    def test_the_highest_pair_is_chosen_by_run_id_first_and_by_numbers(self):
        s99 = all_steps() + [step('unit_test', 'failure')]
        s100 = all_steps() + [step('unit_test', 'success')]
        for runs in ([run(run_id=99, attempt=3, steps=s99), run(run_id=100, attempt=1, steps=s100)],
                     [run(run_id=100, attempt=1, steps=s100), run(run_id=99, attempt=3, steps=s99)]):
            seen, out = self._chosen_steps(runs)
            self.assertEqual(seen, [s100])  # run 100 attempt 1 is higher than run 99 attempt 3
            self.assertEqual([(r['run_id'], r['attempt']) for r in out['evidence']['runs']], [(99, 3), (100, 1)])
        s9 = all_steps() + [step('unit_test', 'failure')]
        s10 = all_steps() + [step('unit_test', 'success')]
        for runs in ([run(run_id=9, steps=s9), run(run_id=10, steps=s10)], [run(run_id=10, steps=s10), run(run_id=9, steps=s9)]):
            seen, out = self._chosen_steps(runs)
            self.assertEqual(seen, [s10])  # numbers, not texts: 10 is higher than 9
            self.assertEqual([r['run_id'] for r in out['evidence']['runs']], [9, 10])

    def test_every_attempt_keeps_the_hash_of_its_own_log(self):
        other = BRANCH_LOG + 'other\tSet up job\t2026-11-20T17:12:03.0000000Z another job line\n'
        out = call(runs=[run(), run(attempt=2, log=other)])
        self.assertIsNone(out['refusal'])
        want = [hashlib.sha256(BRANCH_LOG.encode('utf-8')).hexdigest(), hashlib.sha256(other.encode('utf-8')).hexdigest()]
        self.assertNotEqual(want[0], want[1])
        self.assertEqual([r['log_sha256'] for r in out['evidence']['runs']], want)

    def test_the_cost_is_stated_in_the_docstring(self):
        self.assertIn('a new commit', ci_evidence.__doc__)


class AC5TheMakerAndTheDuties(unittest.TestCase):
    def test_the_records_equal_the_makers_for_the_same_arguments(self):
        out = call()
        made = gate_records.gate_records(TASK, COMMIT, dict(IV), [{'gate': e['gate'], 'check': e['check']} for e in PLAN4],
                                         all_steps(), copy.deepcopy(MAP), 'external CI')
        self.assertEqual(out['records'], made['records'])
        self.assertEqual(out['uncovered'], made['uncovered'])
        self.assertEqual(gates(out), {'G0': 'pass', 'G1': 'pass', 'G2': 'pass'})

    def test_the_review_gate_with_args_is_uncovered(self):
        out = call()
        self.assertEqual(out['uncovered'], [{'gate': 'G3', 'check': 'review', 'detail': 'no CI step is evidence of this check'}])

    def test_intent_versions_are_a_copy_and_the_arguments_are_not_changed(self):
        args = {'task_id': TASK, 'commit': COMMIT, 'contract_sha256': SHA, 'intent_versions': dict(IV),
                'plan': copy.deepcopy(PLAN4), 'changed_paths': ['a'], 'runs': [run(), run(attempt=2)], 'recorder': 'external CI'}
        before = copy.deepcopy(args)
        out = call(**args)
        self.assertEqual(args, before)
        for r in out['records']:
            self.assertEqual(r['intent_versions'], IV)
            self.assertIsNot(r['intent_versions'], args['intent_versions'])
        out['records'][0]['intent_versions']['SPEC-001'] = 'v9'
        self.assertEqual(args['intent_versions'], IV)

    def test_the_default_map_is_never_passed_and_never_changed(self):
        before = copy.deepcopy(MAP)
        seen = []

        def capture(task_id, commit, intent_versions, plan, steps, check_map, recorder):
            seen.append(check_map)
            check_map['scope'].append('mutated by the stand-in')
            return {'records': [], 'uncovered': [], 'error': None}

        with mock.patch.object(ci_evidence.gate_records, 'gate_records', capture):
            call()
        self.assertEqual(MAP, before)
        self.assertIsNot(seen[0], MAP)

    def test_the_same_arguments_give_equal_results(self):
        self.assertEqual(call(), call())

    def test_a_maker_error_text_is_a_maker_refusal(self):
        stand_in = mock.Mock(return_value={'records': [], 'uncovered': [], 'error': 'an error text of the maker'})
        with mock.patch.object(ci_evidence.gate_records, 'gate_records', stand_in):
            out = call()
        self.assertEqual(refusal(out), ('maker', 'an error text of the maker'))
        self.assertEqual((out['records'], out['uncovered'], out['evidence']), ([], [], None))

    def test_a_maker_exception_and_a_base_exception(self):
        with mock.patch.object(ci_evidence.gate_records, 'gate_records', mock.Mock(side_effect=RuntimeError('x'))):
            self.assertEqual(refusal(call()), ('maker', 'the maker raised RuntimeError'))
        with mock.patch.object(ci_evidence.gate_records, 'gate_records', mock.Mock(side_effect=Boom())):
            with self.assertRaises(Boom):
                call()


class AC6ThePathRule(unittest.TestCase):
    def test_a_path_under_github_is_refused_before_any_run_is_read(self):
        for p in ('.github/workflows/aieos-checks.yml', '.github/x', '.github'):
            out = call(changed_paths=['src/a.py', p], runs=[run(log='')])
            self.assertEqual(refusal(out), ('path', 'a changed path is under .github: ' + p))

    def test_similar_paths_are_not_refused(self):
        for p in ('.githubx/y', 'docs/.github/z', 'github/a'):
            self.assertIsNone(call(changed_paths=[p])['refusal'], p)
        self.assertIsNone(call(changed_paths=[])['refusal'])


class AC7TheEvidence(unittest.TestCase):
    def test_the_evidence_mapping(self):
        out = call(runs=[run(attempt=2), run(run_id=99, attempt=3, log=BRANCH_LOG), run()])
        ev = out['evidence']
        self.assertEqual(set(ev), {'head_sha', 'workflow_path', 'detect_line', 'contract_sha256', 'runs'})
        self.assertEqual((ev['head_sha'], ev['workflow_path'], ev['contract_sha256']), (COMMIT, WORKFLOW, SHA))
        self.assertTrue(ev['detect_line'].startswith('G0 detect: task TASK-150 contract commit '))
        self.assertEqual([(r['run_id'], r['attempt']) for r in ev['runs']], [(99, 3), (100, 1), (100, 2)])
        for r in ev['runs']:
            self.assertEqual(set(r), {'run_id', 'attempt', 'log_sha256'})
            self.assertEqual(r['log_sha256'], hashlib.sha256(BRANCH_LOG.encode('utf-8')).hexdigest())
        self.assertTrue(all(type(r['run_id']) is int and type(r['attempt']) is int for r in ev['runs']))

    def test_a_refusal_has_no_evidence(self):
        self.assertIsNone(call(runs=[])['evidence'])


class AC8TheG3ResultAndTheGovernor(unittest.TestCase):
    def _request(self):
        return {'task_id': TASK, 'task_content_hash': 'c' * 64, 'evaluated_commit': COMMIT, 'intent_versions': dict(IV),
                'task_state': 'VERIFYING', 'changed_paths': ['src/x.py'], 'retry_count': {'used': 0, 'limit': 2}}

    def _inputs(self, plan):
        return {'traces_to': ['SPEC-001'], 'risk': 'low', 'owner_kept_act': False, 'weakens_evidence': False,
                'delegation_in_force': True, 'auto_accept': False, 'verification_plan': plan,
                'evidence_profile': [{'dimension': 'functional', 'evidence_types': ['build']}],
                'applicable_articles': [], 'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1'}

    def test_the_records_cover_g0_to_g2_and_the_governor_names_g3_missing(self):
        out = call()
        self.assertEqual(gates(out), {'G0': 'pass', 'G1': 'pass', 'G2': 'pass'})
        for r in out['records']:
            self.assertEqual(records.check_record(r), [])
        decision = governor.evaluate(self._request(), self._inputs([e['gate'] for e in PLAN4]), out['records'])
        # missing_gates is the assertion that shows the records are counted; the decision alone would also follow from the profile.
        self.assertEqual(decision['missing_gates'], ['G3'])
        self.assertEqual(decision['failed_gates'], [])
        self.assertEqual(decision['decision'], 'INSUFFICIENT_EVIDENCE')

    def test_a_failed_mapped_step_gives_a_failed_gate(self):
        steps = [step(n) for n in MAPPED[:2]] + [step('G1 build', 'failure'), step(MAPPED[3])]
        out = call(runs=[run(conclusion='failure', steps=steps)])
        decision = governor.evaluate(self._request(), self._inputs([e['gate'] for e in PLAN4]), out['records'])
        self.assertEqual(decision['failed_gates'], ['G1'])
        self.assertEqual(decision['decision'], 'NEEDS_REWORK')


if __name__ == '__main__':
    unittest.main()
