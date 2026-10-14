"""The scope-drift computation of gov-AIEOS (task TASK-033; specification 4 revision 3, section 7 item 2; the risk
rules' revision 4, policy version v3, section 2 point 7; concept lines 745 and 948: scope drift is found
deterministically).

``non_task_list(policy_text)`` reads the risk rules' list of non-task paths from the policy's text, fail closed.
``claims(inputs)`` takes one base commit's facts as values: the commit, its parent count, its AIEOS-Task trailer task
ids, its changed paths, the write-sets of the named tasks' contracts, the non-task list, the policy's rules in the
governor's form, the evaluator list and the constitution's and the policy's paths. It returns the drift.detected event
of a commit that is a scope-drift claim, whether the commit was detected and exempt, and what it could not check. A
malformed input gives an error and no event (fail closed).

- The list (AC2): exactly one line ``non_task_paths: ["p1", "p2", ...]`` in section 3's yaml block, after its
  ``policy_version:`` line, each item a pattern of the risk rules' section 2 point 6 holding no '"', ',' or ']'.
  Anything else (no block, no line, a repeated line, a line out of form, an item out of form, the line before
  ``policy_version:``) gives None: no path is non-task.
- Detection (AC3; specification 4 line 81): a commit with a parent count other than one gives no event and is named
  as uncovered (a merge's paths are the caller's to read against its first parent, TASK-034). Otherwise it is
  detected when it carries no trailer task, or one trailer task whose contract's write-set does not hold a changed
  path (aieos_bootstrap.governor.matches). Several trailer tasks, a trailer task with no contract given and a
  write-set that cannot be evaluated each make the commit detected and are named as uncovered.
- Non-task paths (AC4; policy point 7): a changed path is non-task only when the list is given and one of its
  patterns matches the path, its class under the rules is exactly low, no pattern of the evaluator list matches it,
  and it is not the constitution, the policy or a path under ".github/". The class is computed by ``_path_class``, a
  copy of the per-path derivation in governor.derive_inputs (the highest class of the rules whose match holds the
  path; a rule whose match cannot be evaluated matches every path, one whose class cannot be read gives critical; a
  path no rule matches has no class); a rule out of the form {match, class}, an evaluator list out of form or a list
  item out of form makes no path non-task (fail closed).
- Claim or exempt (AC5; reading R1, proposed, decision D-702): specification 4 line 81's sentence "A commit that
  touches the constitution, the policy, the evaluator paths or `.github/` is always a claim" is read, by its place
  between "A detected commit is not a claim when ..." and "Every other detected commit ...", as a limit on the
  exemption of a detected commit, not as the specification's own words for every commit. A detected commit is exempt
  when every changed path is non-task; otherwise it is a claim. A detected commit that touches such a path is never
  exempt; a commit that is not detected is no claim, whatever its paths.
- The event (AC6; reading R2, proposed, decision D-702): payload {paths: the sorted changed paths that are not
  non-task, entities: the sorted trailer task ids}; the event id is the SHA-256 hex digest of "drift.detected",
  "scope" and the commit joined by LF (as drift joins the parts of its ids), so it depends on the commit only. An
  event carries no task_id: its subject is a commit and no task's state changes (specification 1, drift.detected).

Limits (TASK-033 AC7 and AC11):
- It classifies and proposes nothing (CLASSIFY and PROPOSE are an authority's records), closes no claim, changes no
  task state, blocks no task, appends nothing, and makes no constitution or stale-evidence finding. Reading the facts
  at the base and appending the event through the core's single writer are the caller's, TASK-034 (decision D-702),
  which also translates the policy's rules (R3 by tags, read as every path under src/** and tests/**) into the
  governor's form.
- The facts are not checked against Git, the contracts or the policy at the base; the write-sets are the caller's
  (the version the task's last task.approved names). Several equal trailer task ids count as one.
- governor.matches is recursive over a pattern's "/" parts, so a pathological pattern may raise; claims and
  non_task_list catch any exception and return it as an error, and no exception escapes.
- It reads no file, no clock and no environment, and makes no process, network or model call (INV-001 to INV-003).
"""

import hashlib
import re

from aieos_bootstrap import governor
from aieos_bootstrap import records

EVENT_TYPE = 'drift.detected'
INPUT_KEYS = ('commit', 'parents', 'trailer_tasks', 'changed_paths', 'contracts', 'non_task', 'risk_rules',
              'evaluator', 'constitution_path', 'policy_path')
RESULT_KEYS = ('events', 'detected', 'exempt', 'uncovered', 'error')
RISKS = ('low', 'medium', 'high', 'critical')
_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_TASK = re.compile(r'TASK-[0-9]+')
_NAME = re.compile(r'[A-Za-z0-9._*-]+')
_LIST_LINE = re.compile(r'non_task_paths: \[("[^"\n,\]]+"(?:, "[^"\n,\]]+")*)\]')


def _text(value):
    return isinstance(value, str) and value != ''


def _texts(value):
    return isinstance(value, list) and all(_text(v) for v in value)


def _pattern_ok(p):
    """A pattern of the risk rules' section 2 point 6: names of letters, digits, ".", "_", "-" and "*"; "**" only as a
    whole name; no empty, "." or ".." name."""
    if not _text(p):
        return False
    for name in p.split('/'):
        if _NAME.fullmatch(name) is None or name in ('.', '..') or ('**' in name and name != '**'):
            return False
    return True


def _patterns_ok(value):
    return isinstance(value, list) and len(value) > 0 and all(_pattern_ok(p) for p in value)


def _list_from(text):
    lines = text.split('\n')
    if '## 3. The rules' not in lines:
        return None
    i = lines.index('## 3. The rules')
    start = next((k for k in range(i + 1, len(lines)) if lines[k] == '```yaml'), None)
    if start is None:
        return None
    end = next((k for k in range(start + 1, len(lines)) if lines[k] == '```'), None)
    if end is None:
        return None
    block = lines[start + 1:end]
    at = [k for k, line in enumerate(block) if line.startswith('non_task_paths:')]
    versions = [k for k, line in enumerate(block) if line.startswith('policy_version:')]
    if len(at) != 1 or not versions or min(versions) > at[0]:
        return None
    m = _LIST_LINE.fullmatch(block[at[0]])
    if m is None:
        return None
    items = re.findall(r'"([^"]*)"', m.group(1))
    if not items or not all(_pattern_ok(p) for p in items):
        return None
    return items


def non_task_list(policy_text):
    """The risk rules' non-task list (TASK-033 AC2): the list's patterns in order, or None for any text out of policy
    point 7's form (no path is then non-task). No exception escapes."""
    try:
        if not isinstance(policy_text, str):
            return None
        return _list_from(policy_text)
    except Exception:  # noqa: BLE001 - fail closed (AC8)
        return None


def _input_error(inputs):
    """The first form of AC1 that fails, as a short text, or None."""
    if not isinstance(inputs, dict):
        return 'inputs is not a mapping'
    checks = (
        ('commit', lambda v: isinstance(v, str) and _COMMIT.fullmatch(v) is not None,
         'is not 40 or 64 lowercase hex characters'),
        ('parents', lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0, 'is not an int of 0 or more'),
        ('trailer_tasks', lambda v: isinstance(v, list) and all(isinstance(t, str) and _TASK.fullmatch(t) for t in v),
         'is not a list of task ids'),
        ('changed_paths', lambda v: _texts(v) and len(v) > 0, 'is not a non-empty list of non-empty strings'),
        ('contracts', lambda v: isinstance(v, dict), 'is not a mapping'),
        ('non_task', lambda v: v is None or (isinstance(v, list) and all(isinstance(p, str) for p in v)),
         'is not a list of strings or None'),
        ('risk_rules', lambda v: isinstance(v, list), 'is not a list'),
        ('evaluator', lambda v: isinstance(v, list) and all(isinstance(p, str) for p in v), 'is not a list of strings'),
        ('constitution_path', _text, 'is not a non-empty string'),
        ('policy_path', _text, 'is not a non-empty string'),
    )
    for key, ok, what in checks:
        if key not in inputs:
            return 'inputs lacks ' + key
        if not ok(inputs[key]):
            return key + ' ' + what
    extra = sorted(str(k) for k in inputs if k not in INPUT_KEYS)
    if extra:
        return 'inputs has an unknown key: ' + extra[0]
    return None


def _digest(*parts):
    return hashlib.sha256('\n'.join(parts).encode('utf-8')).hexdigest()


def _rule_ok(rule):
    return (isinstance(rule, dict) and set(rule) == {'match', 'class'} and _texts(rule['match'])
            and len(rule['match']) > 0 and rule['class'] in RISKS)


def _path_class(rules, path):
    """The per-path class of governor.derive_inputs (its risk loop), for one path: the highest class among the rules
    whose match holds the path; a rule whose match cannot be evaluated matches every path, one whose class cannot be
    read gives critical; None when no rule matches."""
    best = None
    for rule in rules:
        ok = isinstance(rule, dict) and _texts(rule.get('match')) and len(rule.get('match')) > 0
        if ok and not any(governor.matches(p, path) for p in rule['match']):
            continue
        cls = rule.get('class') if isinstance(rule, dict) and rule.get('class') in RISKS else 'critical'
        best = cls if best is None or RISKS.index(cls) > RISKS.index(best) else best
    return best


def _detect(inputs, uncovered):
    """AC3: whether a one-parent commit is detected; names the uncovered cases."""
    commit, paths = inputs['commit'], inputs['changed_paths']
    tasks = sorted(set(inputs['trailer_tasks']))
    if not tasks:
        return True
    if len(tasks) > 1:
        uncovered.add((commit, 'several trailers'))
        return True
    task = tasks[0]
    if task not in inputs['contracts']:
        uncovered.add((task, 'no contract'))
        return True
    write_set = inputs['contracts'][task]
    if not _patterns_ok(write_set):
        uncovered.add((task, 'write set cannot be evaluated'))
        return True
    return any(not any(governor.matches(p, path) for p in write_set) for path in paths)


def _non_task_paths(inputs):
    """AC4: the set of changed paths that are non-task (empty when the list, a rule or the evaluator list is out of
    form)."""
    listed, rules, evaluator = inputs['non_task'], inputs['risk_rules'], inputs['evaluator']
    if not (isinstance(listed, list) and all(_pattern_ok(p) for p in listed)):
        return set()
    if not all(_rule_ok(r) for r in rules):
        return set()
    if not _patterns_ok(evaluator):
        return set()
    out = set()
    for path in inputs['changed_paths']:
        if (any(governor.matches(p, path) for p in listed) and _path_class(rules, path) == 'low'
                and not any(governor.matches(e, path) for e in evaluator)
                and path not in (inputs['constitution_path'], inputs['policy_path'])
                and not path.startswith('.github/')):
            out.add(path)
    return out


def _result(events, detected, exempt, uncovered, error):
    return {'events': events, 'detected': detected, 'exempt': exempt,
            'uncovered': [{'ref': a, 'detail': b} for a, b in sorted(uncovered)], 'error': error}


def _claims(inputs):
    error = _input_error(inputs)
    if error is not None:
        return _result([], False, False, set(), error)
    commit = inputs['commit']
    uncovered = set()
    if inputs['parents'] != 1:
        uncovered.add((commit, 'not one parent'))
        return _result([], False, False, uncovered, None)
    if not _detect(inputs, uncovered):
        return _result([], False, False, uncovered, None)
    free = _non_task_paths(inputs)
    rest = sorted(set(inputs['changed_paths']) - free)
    if not rest:
        return _result([], True, True, uncovered, None)
    payload = {'paths': rest, 'entities': sorted(set(inputs['trailer_tasks']))}
    if records.check_payload(EVENT_TYPE, payload):
        return _result([], True, False, uncovered, 'the payload is not of specification 2\'s drift.detected form')
    event = {'event_id': _digest(EVENT_TYPE, 'scope', commit), 'event_type': EVENT_TYPE, 'payload': payload}
    return _result([event], True, False, uncovered, None)


def claims(inputs):
    """The scope-drift computation for one base commit (TASK-033 AC1 to AC8): a mapping with exactly the keys events
    (one drift.detected event when the commit is a claim, else none), detected and exempt (exempt only when
    detected), uncovered (sorted {ref, detail} entries, without duplicates) and error (None, or a short text for a
    malformed input, which gives no event, detected and exempt false and no entry). The input is not changed and no
    exception escapes."""
    try:
        return _claims(inputs)
    except Exception as exc:  # noqa: BLE001 - fail closed (AC8)
        return _result([], False, False, set(), 'an exception: ' + type(exc).__name__)
