"""The constitution-drift computation of gov-AIEOS (task TASK-030; specification 4 revision 3, section 7 item 1; concept
lines 744 and 948: constitution drift is found deterministically).

``violations`` takes one base commit's facts as values: the commit, its changed paths, the constitution's articles at
the base, the rule results recorded for that commit, the records of a task whose evaluated commit is that commit, and
the recorder. It returns one violation.detected event per article whose scope meets a changed path and whose rule
failed on that commit, unless that task's own records already hold the same failure (one finding, not two); the
articles found already; and what it could not check. A malformed input gives an error and no event (fail closed).

- The articles that apply (AC2): an article applies when its scope is a non-empty list of non-empty strings and
  aieos_bootstrap.governor.matches(pattern, path) is true for some pattern and changed path; a scope in any other form
  cannot be evaluated, so the article applies and is named as uncovered (as the governor's derive_inputs reads such a
  scope). An article's other keys are not read: a base commit has no task type.
- Rule results (AC3, AC4): a rule result counts for an article only in specification 2's form for a check observation
  of a constitution article: records.check_record finds nothing, fact_kind "observation", gate "G3", commit equal to
  the base commit, outcome "pass" or "fail", and refers_to equal to the article's id. An applicable article fails
  when a usable result for it fails; one with no usable result is uncovered, never passed. An entry that is not usable
  by that form (refers_to aside), a well-formed result of another commit or gate included, is named as uncovered and
  counts as no result. An entry usable by that form whose refers_to names no article (a CI step text, for example) is
  counted for no article and not named; each applicable article it leaves without a result is named instead.
- One finding, not two (AC5): a failing article gives no event when a well-formed observation among the task records
  has gate "G3", refers_to the article's id, commit equal to the base commit and outcome "fail"; a malformed record
  never suppresses a finding.
- The events (AC6): payload {record_id, fact_kind "observation", source_class "deterministic_tool_local", recorder,
  subject the base commit, commit the base commit, outcome "blocking", blocking_kind "violation", refers_to the article
  id}; record_id is the SHA-256 hex digest of "violation", the commit and the article id joined by LF, and the event
  id that of "violation.detected", the commit and the article id, as the writer joins the parts of its refusal ids. An
  event carries no task_id: its subject is a commit and no task's state changes.

Limits (TASK-030 AC7 and AC11):
- It runs no rule (the CI's G3 steps run them), changes no task state, blocks no task and appends nothing; it makes no
  scope-drift or stale-evidence finding. Reading the facts and appending the events through the core's single writer
  are the caller's, TASK-031 (decision D-663), which also maps the CI's steps to article ids: the CI's G3 records name
  a step in refers_to, not an article id, so they count as no result here until the caller maps them.
- The facts are not checked against Git, the CI or the log. The one-finding rule holds only when the base commit is
  the task's evaluated commit; after a landing that is not a fast-forward the findings are two.
- The provenance of a rule result or a task record is not judged: its source_class is checked for form only (by
  records.check_record), so a well-formed observation of any source class counts; which channel a record came
  through is the caller's to establish (DEF-0051).
- The scopes come from the constitution at the base; governor.matches is recursive over a pattern's "/" parts, so a
  pathological scope (about a thousand parts) may raise instead of giving a result.
- It reads no file, no clock and no environment, and makes no process, network or model call (INV-001 to INV-003).
"""

import hashlib
import re

from aieos_bootstrap import governor
from aieos_bootstrap import records

EVENT_TYPE = 'violation.detected'
INPUT_KEYS = ('base_commit', 'changed_paths', 'articles', 'rule_results', 'task_records', 'recorder')
SOURCE_CLASS = 'deterministic_tool_local'
_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')


def _text(value):
    return isinstance(value, str) and value != ''


def _list_of(value, kind):
    return isinstance(value, list) and all(isinstance(v, kind) for v in value)


def _articles_ok(value):
    if not isinstance(value, list):
        return False
    seen = set()
    for a in value:
        if not (isinstance(a, dict) and _text(a.get('id')) and 'scope' in a) or a['id'] in seen:
            return False
        seen.add(a['id'])
    return True


def _input_error(inputs):
    """The first form of AC1 that fails, as a short text, or None."""
    if not isinstance(inputs, dict):
        return 'inputs is not a mapping'
    checks = (
        ('base_commit', lambda v: isinstance(v, str) and _COMMIT.fullmatch(v) is not None,
         'is not 40 or 64 lowercase hex characters'),
        ('changed_paths', lambda v: _list_of(v, str), 'is not a list of strings'),
        ('articles', _articles_ok, 'is not a list of mappings with unique non-empty string ids and a scope'),
        ('rule_results', lambda v: _list_of(v, dict), 'is not a list of mappings'),
        ('task_records', lambda v: _list_of(v, dict), 'is not a list of mappings'),
        ('recorder', _text, 'is not a non-empty string'),
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


def _evaluable(scope):
    return isinstance(scope, list) and len(scope) > 0 and all(_text(p) for p in scope)


def _observation(r):
    """A record that records.check_record finds nothing in, with fact_kind observation."""
    return not records.check_record(r) and r.get('fact_kind') == 'observation'


def _usable(r, commit):
    """AC3's form, refers_to aside: a well-formed G3 observation of this commit with outcome pass or fail."""
    return (_observation(r) and r.get('gate') == 'G3' and r.get('commit') == commit
            and r.get('outcome') in ('pass', 'fail'))


def violations(inputs):
    """The constitution-drift computation for one base commit (TASK-030 AC1 to AC8): a mapping with the keys events
    (one violation.detected event per new failing article, sorted by article id), already (the sorted ids that the
    task records already hold as the same failure), uncovered (sorted {ref, detail} entries, without duplicates) and
    error (None, or a short text for a malformed input, which gives no event and no entry). The input is not
    changed."""
    error = _input_error(inputs)
    if error is not None:
        return {'events': [], 'already': [], 'uncovered': [], 'error': error}
    commit = inputs['base_commit']
    paths = inputs['changed_paths']
    uncovered = set()
    applicable = []
    for a in inputs['articles']:
        scope = a['scope']
        if not _evaluable(scope):
            uncovered.add((a['id'], 'scope cannot be evaluated'))
            applicable.append(a['id'])
        elif any(governor.matches(p, path) for p in scope for path in paths):
            applicable.append(a['id'])
    # Rule results (AC3, AC4).
    results = {}
    for i, r in enumerate(inputs['rule_results']):
        if not _usable(r, commit):
            rid = r.get('record_id')
            uncovered.add((rid if _text(rid) else 'rule_results[%d]' % i, 'not a usable rule result'))
            continue
        if isinstance(r.get('refers_to'), str):
            results.setdefault(r['refers_to'], []).append(r['outcome'])
    failing = []
    for art in applicable:
        outcomes = results.get(art)
        if not outcomes:
            uncovered.add((art, 'no rule result'))
        elif 'fail' in outcomes:
            failing.append(art)
    # One finding, not two (AC5).
    found = set()
    for r in inputs['task_records']:
        if (_observation(r) and r.get('gate') == 'G3' and r.get('commit') == commit and r.get('outcome') == 'fail'
                and isinstance(r.get('refers_to'), str)):
            found.add(r['refers_to'])
    already = sorted(set(failing) & found)
    # The events (AC6).
    events = []
    for art in sorted(set(failing) - found):
        payload = {'record_id': _digest('violation', commit, art), 'fact_kind': 'observation',
                   'source_class': SOURCE_CLASS, 'recorder': inputs['recorder'], 'subject': commit, 'commit': commit,
                   'outcome': 'blocking', 'blocking_kind': 'violation', 'refers_to': art}
        events.append({'event_id': _digest(EVENT_TYPE, commit, art), 'event_type': EVENT_TYPE, 'payload': payload})
    return {'events': events, 'already': already,
            'uncovered': [{'ref': a, 'detail': b} for a, b in sorted(uncovered)], 'error': None}
