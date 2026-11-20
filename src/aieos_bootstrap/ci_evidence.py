"""The CI evidence of a task commit (task TASK-151; BT3a of DEF-0136 and DEF-0152; decisions D-6795 to D-6798): a pure
function that decides whether the saved CI data of ONE task commit may be used as gate evidence, and if so turns it into
the gate-result records of the gate maker (gate_records). It starts no process, opens no file, reads no clock, no
environment and no network, and holds no credential: the CI data enters as plain data that an EXECUTOR step outside this
package has fetched (the saved, unedited output of ``gh run view <id> --attempt <n> --log`` and the run metadata of every
attempt).

``ci_evidence(task_id, commit, contract_sha256, intent_versions, plan, changed_paths, runs, recorder)`` returns a mapping
with exactly the keys records, uncovered, evidence and refusal. On a refusal records and uncovered are empty lists,
evidence is None and refusal is {reason, detail}; otherwise refusal is None. The reasons are a closed set: argument,
log_format, detect, run, rerun, path and maker. It never raises an Exception; a BaseException that is not an Exception
passes through.

The checks, in order, after the arguments: (1) path: a task that changes anything under .github is refused, because the
workflow that made the evidence comes from the pushed commit itself and could print anything (the stated limit: such a
task is refused, not evaluated). (2) The eligible runs: a run of this sha, the event push, the workflow file
.github/workflows/aieos-checks.yml and the branch task/<task_id>; every other run of the sha (the run on main after a
fast-forward, a pull request run, another workflow) is ignored; with none the answer is refusal run; every eligible run
must be completed with the conclusion success or failure. (3) The log of each eligible run, in the pinned form of
``gh run view --log`` (job TAB step TAB timestamp message): from the job checks, the output lines of the detect step
after its single ##[endgroup] must hold exactly one line "G0 detect: task <task_id> contract commit <sha> base <sha>"
and exactly one line "G0 contract sha256 <sha>" equal to the expected contract sha256; the lines before the endgroup
echo the script's source: every line of the log must still be in the pinned form, but the message text of those lines is
never read. A log that is not UTF-8 text (a lone surrogate) is refused with log_format. (4) The rerun agreement: ALL eligible runs and attempts must agree on the
detect line and, for every step name of DEFAULT_CHECK_MAP, on the list of the conclusions of the steps of that name; a
flaky failure followed by a pass is therefore refused and the remedy is a new commit (the cost of this rule). (5) The
maker: gate_records.gate_records is called once with the steps of the run with the highest (run_id, attempt), the plan
entries rebuilt with exactly gate and check (the optional args key of a contract's entry is dropped), a fresh copy of
the intent versions and a fresh copy of DEFAULT_CHECK_MAP (the constant is never passed and never changed).

The evidence mapping, for the caller that keeps the provenance: head_sha, workflow_path, detect_line, contract_sha256 and
runs (a list of run_id, attempt and the SHA-256 of the UTF-8 bytes of that attempt's log).

Limits: the log is trusted as the executor's unedited fetch, which this function cannot check (the evidence mapping
names it); the step conclusions that become records come from the run metadata (the steps lists), which is trusted in the
same way and is not tied to the log, so the caller keeps the hash of the metadata as well; the default map covers scope,
build and lint only, so the run-made plan's review gate stays uncovered (the owner's question of DEF-0153); the module
cannot see the mapping that evaluation.evaluate_task declares, so passing the same copy of the intent versions is the
caller's duty; a change of the detect step's output wording or of the log form makes the answer a refusal (fail closed).
The caller's duties: pass EVERY attempt of every run of the task branch (the module cannot know how many attempts there
are, so an omitted earlier attempt is invisible and the highest attempt given decides); pass EVERY path the commit changes,
including the old side of a rename (a diff without rename detection), because the .github rule sees only the list given
and tests the exact text '.github' or a text that starts with '.github/'. The CI class of the records is asserted, not
verified: the records carry no run id or log hash (the evidence mapping does), and gate_records stays callable directly.
The arguments are plain data as loaded from JSON; a crafted subclass of dict, list or str whose methods answer differently
on each call is outside the guarantee (the same reading as gate_records).
"""
import hashlib
import re

from aieos_bootstrap import gate_records

_TASK = re.compile(r'TASK-[0-9]+')
_COMMIT = re.compile(r'[0-9a-f]{40}')
_SHA256 = re.compile(r'[0-9a-f]{64}')
_GATE = re.compile(r'G[0-9]+')
_VERSION = re.compile(r'v[0-9]+')
_TEXT = re.compile('\ufeff?[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:[.][0-9]+)?Z(?: (.*))?', re.S)
_DETECT = re.compile(r'G0 detect: task (TASK-[0-9]+) contract commit ([0-9a-f]{40}) base ([0-9a-f]{40})')
_CONTRACT = re.compile(r'G0 contract sha256 ([0-9a-f]{64})')

_WORKFLOW = '.github/workflows/aieos-checks.yml'
_JOB = 'checks'
_DETECT_STEP = 'G0 task detection (the contract commit on main)'
_ENDGROUP = '##[endgroup]'
_RUN_KEYS = frozenset({'run_id', 'attempt', 'head_sha', 'event', 'head_branch', 'workflow_path', 'status', 'conclusion',
                       'steps', 'log'})
_STEP_KEYS = frozenset({'name', 'conclusion'})


def _answer(records, uncovered, evidence, refusal):
    return {'records': records, 'uncovered': uncovered, 'evidence': evidence, 'refusal': refusal}


def _refuse(reason, detail):
    return _answer([], [], None, {'reason': reason, 'detail': detail})


def _text(value):
    return isinstance(value, str) and value != ''


def _int(value):
    return type(value) is int and value > 0


def _argument_error(task_id, commit, contract_sha256, intent_versions, plan, changed_paths, runs, recorder):
    """The first malformed argument as a short text, or None."""
    if not isinstance(task_id, str) or _TASK.fullmatch(task_id) is None:
        return 'task_id is not TASK- and digits'
    if not isinstance(commit, str) or _COMMIT.fullmatch(commit) is None:
        return 'commit is not 40 lowercase hexadecimal characters'
    if not isinstance(contract_sha256, str) or _SHA256.fullmatch(contract_sha256) is None:
        return 'contract_sha256 is not 64 lowercase hexadecimal characters'
    if not isinstance(intent_versions, dict) or not intent_versions:
        return 'intent_versions is not a non-empty mapping'
    for key, value in intent_versions.items():
        if not _text(key) or not isinstance(value, str) or _VERSION.fullmatch(value) is None:
            return 'intent_versions holds an entry that is not a non-empty name and v and digits'
    if not isinstance(plan, list) or not plan:
        return 'plan is not a non-empty list'
    for entry in plan:
        if not isinstance(entry, dict) or set(entry) - {'args'} != {'gate', 'check'}:
            return 'a plan entry is not a mapping with the keys gate and check and at most args'
        if not isinstance(entry['gate'], str) or _GATE.fullmatch(entry['gate']) is None:
            return 'a plan entry has a gate that is not G and digits'
        if not _text(entry['check']):
            return 'a plan entry has a check that is not a non-empty text'
    if not isinstance(changed_paths, list) or not all(_text(p) for p in changed_paths):
        return 'changed_paths is not a list of non-empty texts'
    if not isinstance(runs, list):
        return 'runs is not a list'
    for run in runs:
        if not isinstance(run, dict) or set(run) != _RUN_KEYS:
            return 'a run is not a mapping with exactly the run keys'
        if not _int(run['run_id']) or not _int(run['attempt']):
            return 'a run has a run_id or an attempt that is not an integer above zero'
        if not all(isinstance(run[k], str) for k in ('head_sha', 'event', 'head_branch', 'workflow_path', 'status', 'log')):
            return 'a run has a head_sha, event, head_branch, workflow_path, status or log that is not a text'
        if run['conclusion'] is not None and not isinstance(run['conclusion'], str):
            return 'a run has a conclusion that is neither a text nor None'
        if not isinstance(run['steps'], list):
            return 'a run has steps that are not a list'
        for step in run['steps']:
            if not isinstance(step, dict) or set(step) != _STEP_KEYS:
                return 'a step is not a mapping with exactly the keys name and conclusion'
            if not _text(step['name']):
                return 'a step has a name that is not a non-empty text'
            if step['conclusion'] is not None and not isinstance(step['conclusion'], str):
                return 'a step has a conclusion that is neither a text nor None'
    if not _text(recorder):
        return 'recorder is not a non-empty text'
    return None


def _detect_line(log, task_id, contract_sha256):
    """The detect line of one saved log, or (reason, detail) when the log may not be used."""
    lines = log.split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]
    if not lines:
        return None, ('log_format', 'the log is empty')
    kept = []
    for n, raw in enumerate(lines, 1):
        line = raw[:-1] if raw.endswith('\r') else raw
        parts = line.split('\t', 2)
        if len(parts) != 3:
            return None, ('log_format', 'line %d is not job TAB step TAB text' % n)
        match = _TEXT.fullmatch(parts[2])
        if match is None:
            return None, ('log_format', 'line %d has no timestamp in the pinned form' % n)
        if parts[0] == _JOB and parts[1] == _DETECT_STEP:
            kept.append(match.group(1) or '')
    if not any(raw.split('\t', 2)[0] == _JOB for raw in lines):
        return None, ('log_format', 'the log has no line of the job checks')
    if not kept:
        return None, ('detect', 'the log has no line of the detect step')
    ends = [i for i, message in enumerate(kept) if message == _ENDGROUP]
    if len(ends) != 1:
        return None, ('detect', 'the detect step has %d endgroup lines (exactly one is expected)' % len(ends))
    output = kept[ends[0] + 1:]
    if any(message.startswith('G0 detect: no task') for message in output):
        return None, ('detect', 'the detect step says no task')
    found = [message for message in output if _DETECT.fullmatch(message) is not None]
    if len(found) != 1:
        return None, ('detect', 'the detect step output has %d detect lines (exactly one is expected)' % len(found))
    if _DETECT.fullmatch(found[0]).group(1) != task_id:
        return None, ('detect', 'the detect line names another task')
    sums = [_CONTRACT.fullmatch(message).group(1) for message in output if _CONTRACT.fullmatch(message) is not None]
    if len(sums) != 1:
        return None, ('detect', 'the detect step output has %d contract sha256 lines (exactly one is expected)' % len(sums))
    if sums[0] != contract_sha256:
        return None, ('detect', 'the contract sha256 of the log differs from the expected one')
    return found[0], None


def _mapped_names():
    names = []
    for steps in gate_records.DEFAULT_CHECK_MAP.values():
        for name in steps:
            if name not in names:
                names.append(name)
    return names


def ci_evidence(task_id, commit, contract_sha256, intent_versions, plan, changed_paths, runs, recorder):
    """The gate-result records of one task commit from its saved CI data, or the refusal."""
    try:
        error = _argument_error(task_id, commit, contract_sha256, intent_versions, plan, changed_paths, runs, recorder)
        if error is not None:
            return _refuse('argument', error)
        for path in changed_paths:
            if path == '.github' or path.startswith('.github/'):
                return _refuse('path', 'a changed path is under .github: ' + path)
        branch = 'task/' + task_id
        eligible = [r for r in runs if r['head_sha'] == commit and r['event'] == 'push'
                    and r['workflow_path'] == _WORKFLOW and r['head_branch'] == branch]
        if not eligible:
            return _refuse('run', 'no eligible run')
        seen = set()
        for run in eligible:
            key = (run['run_id'], run['attempt'])
            if key in seen:
                return _refuse('run', 'run %d attempt %d is given twice' % key)
            seen.add(key)
            if run['status'] != 'completed' or run['conclusion'] not in ('success', 'failure'):
                return _refuse('run', 'run %d attempt %d is not completed with success or failure' % key)
        eligible.sort(key=lambda r: (r['run_id'], r['attempt']))
        lines = []
        digests = []
        for run in eligible:
            try:
                digests.append(hashlib.sha256(run['log'].encode('utf-8')).hexdigest())
            except UnicodeEncodeError:
                return _refuse('log_format', 'run %d attempt %d: the log is not UTF-8 text' % (run['run_id'], run['attempt']))
            line, problem = _detect_line(run['log'], task_id, contract_sha256)
            if problem is not None:
                return _refuse(problem[0], problem[1])
            lines.append(line)
        if any(line != lines[0] for line in lines):
            return _refuse('rerun', 'the attempts disagree on the detect line')
        for name in _mapped_names():
            seen_lists = [tuple(s['conclusion'] for s in run['steps'] if s['name'] == name) for run in eligible]
            if any(item != seen_lists[0] for item in seen_lists):
                return _refuse('rerun', 'the attempts disagree on the step ' + name)
        chosen = eligible[-1]
        steps = [{'name': s['name'], 'conclusion': s['conclusion']} for s in chosen['steps']]
        entries = [{'gate': e['gate'], 'check': e['check']} for e in plan]
        check_map = {k: list(v) for k, v in gate_records.DEFAULT_CHECK_MAP.items()}
        try:
            made = gate_records.gate_records(task_id, commit, dict(intent_versions), entries, steps, check_map, recorder)
        except Exception as exc:
            return _refuse('maker', 'the maker raised ' + type(exc).__name__)
        if made['error'] is not None:
            return _refuse('maker', made['error'])
        evidence = {
            'head_sha': commit, 'workflow_path': _WORKFLOW, 'detect_line': lines[0], 'contract_sha256': contract_sha256,
            'runs': [{'run_id': r['run_id'], 'attempt': r['attempt'], 'log_sha256': d} for r, d in zip(eligible, digests)]}
        return _answer(made['records'], made['uncovered'], evidence, None)
    except Exception as exc:
        return _refuse('argument', 'an argument could not be read: ' + type(exc).__name__)
