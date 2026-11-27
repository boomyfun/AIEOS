"""The gate maker (task TASK-150; BT2 of DEF-0136, option (A) of D-6770): a pure function that turns the step
conclusions of ONE CI run on ONE commit into gate-result records that the governor counts for a task, honestly. A gate
gets a "pass" record only when every check that the plan names for that gate is covered by CI evidence that is present
and concluded and passed, and a "fail" record when a covered check failed (the rules below); an entry that is not
covered is never turned into a record and is reported as uncovered.

``gate_records(task_id, commit, intent_versions, plan, steps, check_map, recorder)`` returns a mapping with exactly the
keys records (a list of mappings), uncovered (a list of mappings with the keys gate, check and detail) and error (None,
or a short text for a malformed argument or for an internal fault, which this function reports with the same kind of
text, in which case records and uncovered are both empty). It starts no process,
opens no file, reads no clock and no network; it imports the standard library only (hashlib and re). It never raises an
Exception; a BaseException that is not an Exception passes through.

The arguments are checked first, each failure is an error and no record: task_id is TASK- and digits; commit is 40
lowercase hexadecimal characters; intent_versions is a non-empty dict from a non-empty str to v and digits; plan is a
non-empty list of dicts with exactly the keys gate (G and digits) and check (a non-empty str); steps is a list of dicts
with exactly the keys name (a non-empty str) and conclusion (a str or None), the step conclusions of the CI run as
data; check_map is a dict from a non-empty str to a non-empty list of non-empty str (the exact step names that are
evidence of that check); recorder is a non-empty str.

The matching is by CHECK, not only by gate. The plan's entries are grouped by gate in the order of the plan and every
entry is evaluated. An entry whose check has no entry in check_map is uncovered ("no CI step is evidence of this
check"), so a caller cannot turn the steps of another check into a pass for a check the map does not name. Otherwise
every step name the map gives for the check must occur in steps exactly once (absent: uncovered, "step not present";
twice or more: uncovered, "step named more than once"); when each is present once, a conclusion other than "success"
and "failure" makes the entry uncovered ("conclusion is neither success nor failure"); otherwise the entry is covered,
"fail" when a step concluded "failure" and "pass" when all concluded "success". A gate gets at most one record: "fail"
when at least one of its entries is covered and failed (an uncovered entry of it is still listed), "pass" only when
every entry of it is covered and passed, otherwise none. A "fail" therefore comes only from a check whose mapped steps
are all present exactly once and concluded, never from a missing, duplicated or skipped step.

The record of a gate has exactly the keys record_id, fact_kind, source_class, recorder, subject, commit,
intent_versions, gate and outcome. Its record_id is the SHA-256 of the four texts "ci-gate", the task, the commit and
the gate joined by LF (a form different from reconcile's "ci-rule" id, so the two cannot collide); it has no ci_run key
because the records module has none.

DEFAULT_CHECK_MAP names the CI steps of the workflow at the base for the checks scope, build, lint and constitution. The
entry constitution holds seven steps of the constitution gate (spec-04 section 2), in the workflow's order (decision-matrix
row A82). Three other steps are left out: "SEC-003 record (changes under .github/)" and "GOV-003 evaluator paths (reports
an evaluator change)" only report and never fail, so counting them as passed would be false, and "GOV-003 evaluator lists
equal" is not among the steps that spec-04 section 2 gives to the gate. The map has no entry for review or tests: a plan
entry with either check stays uncovered. The maker reads no CI run and appends nothing: the caller gives the steps and
takes the records.

The limit of the constitution gate: its CI steps do not check the run-made contract's AC1 (the change does what the intent
states), nor the path part of its AC2 (no other path is changed; G0 scope checks that). Each of the seven steps checks only
what its own workflow text says, with the limits that text states (SEC-002 does not check account names; INV-010 replay
does not replay decision.acceptance records; deterministic_rule is an accident filter; OPS-003 pattern rules checks only
effect labels and three named words; bandit skips named rules for named files and for tests). The run-made AC1 is judged by
the decision agent's review while the task is in review (decision-matrix row A82). Passing gates alone do not meet the
evidence profile of a run-made low task, so the governor still answers INSUFFICIENT_EVIDENCE for it (the contract of
TASK-164, AC7).

type_records(task_id, commit, intent_versions, wanted, steps, recorder) (task TASK-165; DEF-0159 part A) makes the
evidence records of the types build and lint for the wanted (dimension, evidence type) pairs from the same step
conclusions. wanted is a list of dicts with exactly the keys dimension (a non-empty text that UTF-8 can encode) and
evidence_type (build or lint); the other arguments are checked as for gate_records. It returns a mapping with exactly the
keys records and error. For each pair, in order, a repeated pair once, one record is made when every step that
DEFAULT_CHECK_MAP names for the check of the type's name occurs exactly once and concluded success or failure (outcome
fail when one failed), and none otherwise. The record has no gate key; it has evidence_type and dimension, and its
record_id is the SHA-256 of "ci-type", the task, the commit, the type and the dimension joined by LF, the dimension last
because it alone may hold a LF. Limits: a build record is the conclusion of the step "G1 build" (compileall -q over src
and tests: the files compile, and nothing more) and a lint record that of the lint step (pyflakes with its default checks
over src and tests), so neither checks a change outside src and tests, such as a docs change; both steps conclude success
in a run that has no task; the CI class rests on the steps the caller gives; only build and lint are made, so an entry of
another CI type stays unmet; the record_id binds neither the outcome nor the intent versions; the governor counts every
record in the log of the CI source class with that type under that dimension, so whoever writes the log is trusted; this
module is not on EVIDENCE_DEFINING_PATHS (evaluation_policy.py), an open part of DEF-0154. A gate record satisfies no
build or lint entry, since it carries no evidence_type and no dimension.

What the caller owes (the limits of this function): (1) the arguments are plain data, as loaded from JSON; an object of
a subclass whose methods lie or change between two reads is outside the guarantee. (2) The plan entries are given
without their optional args key: an entry with any key other than gate and check makes the whole call an error. (3) The
steps are those of the CI run on the given commit; the function cannot check that, and it stamps the CI source class on
what it is given. (4) The mapped steps of the default map for scope, build and lint (the task detection and scope
steps, the build step and the lint step) and three of its constitution steps (deterministic_rule, OPS-003 pattern rules,
static_security_analysis) also conclude as success in a run that has NO task, where each prints a note and exits 0; the
other four constitution steps run their checks on every push (ci_evidence refuses a run whose detect step says no task).
The caller must give steps only of a run whose detect step names this task. (5) The record_id binds the task, the commit and the gate,
not the outcome or the intent versions: a rerun gives the same id, which the governor refuses within one request.
(6) DEFAULT_CHECK_MAP is one shared module dict, not copied by the function; callers do not change it.
"""
import hashlib
import re

_TASK = re.compile(r'TASK-[0-9]+')
_COMMIT = re.compile(r'[0-9a-f]{40}')
_VERSION = re.compile(r'v[0-9]+')
_GATE = re.compile(r'G[0-9]+')

DEFAULT_CHECK_MAP = {
    'scope': ['G0 task detection (the contract commit on main)', 'G0 scope (V0)'],
    'build': ['G1 build'],
    'lint': ['lint (pyflakes 4.0.3, pinned by version and hash)'],
    'constitution': [
        "SEC-001 secret scan (tip tree; every commit's message, file names and added lines)",
        "SEC-002 pattern rules (every commit's added lines)",
        'OPS-002 owner-kept paths',
        'INV-010 replay',
        'deterministic_rule (INV-001, INV-002, INV-004)',
        'OPS-003 pattern rules',
        'static_security_analysis (bandit, every package pinned by version and hash)',
    ],
}

_NO_STEP_FOR_CHECK = 'no CI step is evidence of this check'
_ABSENT = 'step not present'
_REPEATED = 'step named more than once'
_NOT_CONCLUDED = 'conclusion is neither success nor failure'

_PLAN_KEYS = frozenset({'gate', 'check'})
_STEP_KEYS = frozenset({'name', 'conclusion'})


def _result(records, uncovered, error):
    return {'records': records, 'uncovered': uncovered, 'error': error}


def _text(value):
    return isinstance(value, str) and value != ''


def _argument_error(task_id, commit, intent_versions, plan, steps, check_map, recorder):
    """The first malformed argument as a short text, or None."""
    if not isinstance(task_id, str) or _TASK.fullmatch(task_id) is None:
        return 'task_id is not TASK- and digits'
    if not isinstance(commit, str) or _COMMIT.fullmatch(commit) is None:
        return 'commit is not 40 lowercase hexadecimal characters'
    if not isinstance(intent_versions, dict) or not intent_versions:
        return 'intent_versions is not a non-empty mapping'
    for key, value in intent_versions.items():
        if not _text(key) or not isinstance(value, str) or _VERSION.fullmatch(value) is None:
            return 'intent_versions holds an entry that is not a non-empty name and v and digits'
    if not isinstance(plan, list) or not plan:
        return 'plan is not a non-empty list'
    for entry in plan:
        if not isinstance(entry, dict) or set(entry) != _PLAN_KEYS:
            return 'a plan entry is not a mapping with exactly the keys gate and check'
        if not isinstance(entry['gate'], str) or _GATE.fullmatch(entry['gate']) is None:
            return 'a plan entry has a gate that is not G and digits'
        if not _text(entry['check']):
            return 'a plan entry has a check that is not a non-empty text'
    if not isinstance(steps, list):
        return 'steps is not a list'
    for step in steps:
        if not isinstance(step, dict) or set(step) != _STEP_KEYS:
            return 'a step is not a mapping with exactly the keys name and conclusion'
        if not _text(step['name']):
            return 'a step has a name that is not a non-empty text'
        if step['conclusion'] is not None and not isinstance(step['conclusion'], str):
            return 'a step has a conclusion that is neither a text nor None'
    if not isinstance(check_map, dict):
        return 'check_map is not a mapping'
    for check, names in check_map.items():
        if not _text(check) or not isinstance(names, list) or not names or not all(_text(n) for n in names):
            return 'check_map holds an entry that is not a non-empty check and a non-empty list of step names'
    if not _text(recorder):
        return 'recorder is not a non-empty text'
    return None


def _entry(check, check_map, seen):
    """One plan entry: ('uncovered', detail) or ('covered', 'pass' or 'fail'). ``seen`` maps a step name to the list
    of its conclusions."""
    names = check_map.get(check)
    if names is None:
        return 'uncovered', _NO_STEP_FOR_CHECK
    for name in names:
        found = len(seen.get(name, ()))
        if found == 0:
            return 'uncovered', _ABSENT
        if found > 1:
            return 'uncovered', _REPEATED
    conclusions = [seen[name][0] for name in names]
    if any(c not in ('success', 'failure') for c in conclusions):
        return 'uncovered', _NOT_CONCLUDED
    return 'covered', 'fail' if 'failure' in conclusions else 'pass'


_TYPES = ('build', 'lint')
_WANTED_KEYS = frozenset({'dimension', 'evidence_type'})


def _wanted_error(wanted):
    """The first malformed entry of wanted as a short text, or None."""
    if not isinstance(wanted, list):
        return 'wanted is not a list'
    for item in wanted:
        if not isinstance(item, dict) or set(item) != _WANTED_KEYS:
            return 'a wanted entry is not a mapping with exactly the keys dimension and evidence_type'
        if not _text(item['dimension']):
            return 'a wanted entry has a dimension that is not a non-empty text'
        try:
            item['dimension'].encode('utf-8')
        except UnicodeEncodeError:
            return 'a wanted entry has a dimension that UTF-8 cannot encode'
        if not isinstance(item['evidence_type'], str) or item['evidence_type'] not in _TYPES:
            return 'a wanted entry has an evidence_type that is not build or lint'
    return None


def type_records(task_id, commit, intent_versions, wanted, steps, recorder):
    """The build and lint evidence records of one CI run for the wanted (dimension, evidence type) pairs."""
    try:
        error = _argument_error(task_id, commit, intent_versions, [{'gate': 'G0', 'check': 'scope'}], steps,
                                DEFAULT_CHECK_MAP, recorder)
        if error is None:
            error = _wanted_error(wanted)
        if error is not None:
            return {'records': [], 'error': error}
        seen = {}
        for step in steps:
            seen.setdefault(step['name'], []).append(step['conclusion'])
        records, done = [], set()
        for item in wanted:
            kind, dimension = item['evidence_type'], item['dimension']
            if (kind, dimension) in done:
                continue
            done.add((kind, dimension))
            state, outcome = _entry(kind, DEFAULT_CHECK_MAP, seen)
            if state != 'covered':
                continue
            ident = hashlib.sha256('\n'.join(('ci-type', task_id, commit, kind, dimension)).encode('utf-8')).hexdigest()
            records.append({
                'record_id': ident, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
                'recorder': recorder, 'subject': task_id, 'commit': commit,
                'intent_versions': dict(intent_versions), 'evidence_type': kind, 'dimension': dimension,
                'outcome': outcome})
        return {'records': records, 'error': None}
    except Exception as exc:
        return {'records': [], 'error': 'an argument could not be read: ' + type(exc).__name__}


def gate_records(task_id, commit, intent_versions, plan, steps, check_map, recorder):
    """The gate-result records of one CI run for one task and commit, and the entries that stay uncovered."""
    try:
        error = _argument_error(task_id, commit, intent_versions, plan, steps, check_map, recorder)
        if error is not None:
            return _result([], [], error)
        seen = {}
        for step in steps:
            seen.setdefault(step['name'], []).append(step['conclusion'])
        order, by_gate = [], {}
        for item in plan:
            if item['gate'] not in by_gate:
                order.append(item['gate'])
                by_gate[item['gate']] = []
            by_gate[item['gate']].append(item['check'])
        records, uncovered = [], []
        for gate in order:
            outcomes, open_entries = [], 0
            for check in by_gate[gate]:
                state, value = _entry(check, check_map, seen)
                if state == 'uncovered':
                    open_entries += 1
                    uncovered.append({'gate': gate, 'check': check, 'detail': value})
                else:
                    outcomes.append(value)
            if 'fail' in outcomes:
                outcome = 'fail'
            elif open_entries == 0:
                outcome = 'pass'
            else:
                continue
            ident = hashlib.sha256('\n'.join(('ci-gate', task_id, commit, gate)).encode('utf-8')).hexdigest()
            records.append({
                'record_id': ident, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_external_ci',
                'recorder': recorder, 'subject': task_id, 'commit': commit,
                'intent_versions': dict(intent_versions), 'gate': gate, 'outcome': outcome})
        return _result(records, uncovered, None)
    except Exception as exc:
        return _result([], [], 'an argument could not be read: ' + type(exc).__name__)
