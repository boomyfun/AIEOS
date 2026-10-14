"""The reconciliation caller of gov-AIEOS (task TASK-031; specification 4 revision 3, section 7 items 1, 3 and 4; concept
lines 744 and 948; DEF-0030): the core's caller of the two pure reconciliation computations, stale.stale (TASK-023)
and drift.violations (TASK-030).

``reconcile(root, repo, trigger_commit, values, rule_results, recorder, now)`` runs at one base commit, the trigger:

1. Arguments (AC1): every argument is checked before anything is read; a wrong one gives a refusal result.
2. The log (AC2): read once through writer.read_log and checked by records.check_log. A task is DONE when the log
   holds a task.done event for it; its accepted commit is the evaluated_commit of the decision.acceptance whose
   record_id is that task.done's decision_record. A decision record that is absent, not an ACCEPT decision or without
   an evaluated_commit leaves the task uncovered (fail closed). The task's records are its record.added payloads, its
   earlier events its evidence.stale payloads, its submitted commits those of its task.submitted events.
3. The walk (AC3): from the trigger back along first parents, each commit read once with "cat-file -p" through
   gitread.run and parsed by gitread.parse_commit, its changed paths read with the pinned diff-tree form
   (gitread.DIFF_TREE, the form evaluation reads) and parsed by gitread.parse_paths. It stops once every DONE task's
   accepted commit is reached, at a root, or at max_commits commits read. A task whose accepted commit is not reached
   is uncovered, never fresh. A merge is followed by its first parent and its paths are not read: a task whose base
   commits hold a merge is uncovered, and a merge trigger is not given to drift.
4. Stale evidence (AC4): stale.stale once per DONE task with the facts the caller gives in values["tasks"].
5. The source-class filter (AC5) and constitution drift (AC6): only deterministic_tool_external_ci and
   deterministic_tool_local rule results and task records reach drift.violations, which is called once for the
   trigger with the records of every task whose last decision.acceptance evaluated the trigger.
6. The appends (AC8): every returned event through writer.append_event, with no fencing token, in a fixed order (the
   evidence.stale events by task id, then the violation.detected events), under the ids those functions derive, so a
   rerun gives "duplicate". The first other result stops the appends; the log is append-only, so nothing is undone.

The result (AC10) is a mapping with exactly the keys result ("reconciled" or "refused"), reason, findings, appended,
duplicate, already and uncovered. An exception raised by a called function is caught and becomes a result; none
escapes.

``rule_results_from_steps(steps, step_articles, commit, recorder)`` (AC7) is pure: it turns the CI's step results for
one commit into article-form G3 observations by a mapping the caller gives (decision D-664 C4). A step's success
counts as the article's deterministic rule passing, not as the article being satisfied (a reading). Its records are
reconcile's caller's inputs and are not appended.

``read``, ``read_log`` and ``append`` default, at call time, to gitread.run, writer.read_log and writer.append_event;
tests pass stand-ins.

Readings (the implementer's, not the contract's own words):
- A task's decision record is looked up among the log's decision.acceptance events of that task; when several carry
  the same record_id, the last one counts. When a task has several task.done events, the last one counts.
- stale.stale's own uncovered entries are passed on as {ref the task id, detail "<rule>, <its ref>: <its detail>"}.
- A left-out task record is named by its record_id, or by "task_records[i]", its index in the list given to drift.

What it does not do (AC9): it calls no governor function, evaluates no task, grants, releases or expires no lease,
creates no store, changes no task state (an evidence.stale event schedules a re-verify and a DONE task stays DONE, by
specification 1; DEF-0030's state effect and the lease on CONTINUE stay open), makes no scope-drift finding and reads
no network: the CI's step results are the caller's values.

Limits (AC12):
- The DONE tasks' facts other than the log and Git (intent_current, the resolved read-set and its estimate flag, the
  articles and the rule results) are the caller's and not checked against anything.
- The source class is the writer's statement, not checked against the channel a record came through (DEF-0051).
- The task's kept G3 records name a CI step in refers_to, not an article, so they match no article: a G3 failure at a
  task's evaluation and the same failure on the base may be two findings (DEF-0057).
- One run at a time: the writer reads the log and appends with no check that it is unchanged since this module's read.
- The walk has a bound. A merge's changed paths are not read (gitread's one pinned form gives none for a merge), so
  the tasks whose range holds one, and a merge trigger, are uncovered.
- The PATH git is found by is the caller's precondition (DEF-0052 G1).
- It starts no process except through ``read``, opens no file except through ``read_log`` and ``append``, reads no
  clock and no environment, and builds no event-log line itself (INV-001 to INV-004).
"""

import datetime
import hashlib
import re

from aieos_bootstrap import drift
from aieos_bootstrap import gitread
from aieos_bootstrap import records
from aieos_bootstrap import stale
from aieos_bootstrap import writer

RESULT_KEYS = ('result', 'reason', 'findings', 'appended', 'duplicate', 'already', 'uncovered')
COUNTED = ('deterministic_tool_external_ci', 'deterministic_tool_local')
TASK_FACT_KEYS = frozenset({'intent_current', 'read_set', 'read_set_estimate'})
STEP_CONCLUSIONS = {'success': 'pass', 'failure': 'fail'}
RECORD_PREFIX = 'ci-rule'
_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_TASK = re.compile(r'TASK-[0-9]+')
_VERSION = re.compile(r'v[0-9]+')
_ZERO = datetime.timedelta(0)


class _Stop(Exception):
    """A refusal found inside a step: its reason and findings."""

    def __init__(self, reason, findings):
        Exception.__init__(self, reason)
        self.reason = reason
        self.findings = list(findings)


def _text(value):
    return isinstance(value, str) and value != ''


def _commit(value):
    return isinstance(value, str) and _COMMIT.fullmatch(value) is not None


def _result(result, reason=None, findings=(), appended=(), duplicate=(), already=(), uncovered=()):
    entries = sorted({(u['ref'], u['detail']) for u in uncovered})
    return {'result': result, 'reason': reason, 'findings': list(findings), 'appended': list(appended),
            'duplicate': list(duplicate), 'already': list(already),
            'uncovered': [{'ref': r, 'detail': d} for r, d in entries]}


# ---- AC1 ----

def _facts_error(facts):
    """The form of one task's facts in values["tasks"] (stale.stale's forms), as a short text, or None."""
    if not (isinstance(facts, dict) and set(facts) == TASK_FACT_KEYS):
        return 'is not a mapping with exactly the keys intent_current, read_set and read_set_estimate'
    iv = facts['intent_current']
    if not (isinstance(iv, dict) and all(_text(k) and isinstance(v, str) and _VERSION.fullmatch(v) is not None
                                         for k, v in iv.items())):
        return 'intent_current is not a mapping from ids to versions v<digits>'
    rs = facts['read_set']
    if not (isinstance(rs, list) and all(
            isinstance(e, dict) and set(e) == {'entry', 'kind', 'patterns'} and _text(e['entry'])
            and e['kind'] in stale.KINDS
            and (e['patterns'] is None or (isinstance(e['patterns'], list) and all(_text(p) for p in e['patterns'])))
            for e in rs)):
        return 'read_set is not a list of {entry, kind, patterns}'
    if not isinstance(facts['read_set_estimate'], bool):
        return 'read_set_estimate is not a bool'
    return None


def _argument_findings(root, repo, trigger_commit, values, rule_results, recorder, now, max_commits):
    """AC1: what is wrong with the arguments, as a list of findings (empty when every argument is in form)."""
    found = []
    for name, value in (('root', root), ('repo', repo)):
        if not _text(value):
            found.append('argument: %s is not a non-empty string' % name)
    if not _commit(trigger_commit):
        found.append('argument: trigger_commit is not 40 or 64 lowercase hex characters')
    if not (isinstance(values, dict) and set(values) == {'articles', 'tasks'}):
        found.append('argument: values is not a mapping with exactly the keys articles and tasks')
    else:
        if not isinstance(values['articles'], list):
            found.append('argument: values articles is not a list')
        tasks = values['tasks']
        if not isinstance(tasks, dict):
            found.append('argument: values tasks is not a mapping')
        else:
            for task_id in sorted(tasks, key=str):
                if not (isinstance(task_id, str) and _TASK.fullmatch(task_id)):
                    found.append('argument: values tasks has a key that is not a task id: %r' % (task_id,))
                    continue
                why = _facts_error(tasks[task_id])
                if why is not None:
                    found.append('argument: values tasks %s %s' % (task_id, why))
    if not (isinstance(rule_results, list) and all(isinstance(r, dict) for r in rule_results)):
        found.append('argument: rule_results is not a list of mappings')
    if not _text(recorder):
        found.append('argument: recorder is not a non-empty string')
    if not (isinstance(now, datetime.datetime) and now.tzinfo is not None and now.utcoffset() == _ZERO):
        found.append('argument: now is not a timezone-aware datetime in UTC')
    if not (isinstance(max_commits, int) and not isinstance(max_commits, bool) and 1 <= max_commits <= 10000):
        found.append('argument: max_commits is not an int from 1 to 10000')
    return found


# ---- AC2 ----

def _log_events(read_log, root):
    """AC2: the log's events in order (ignored duplicates left out), after records.check_log finds nothing."""
    data = read_log(root)
    if not isinstance(data, bytes):
        raise _Stop('log', ['log: read_log gave %s, not bytes' % type(data).__name__])
    report = records.check_log(data)
    found = ['log: line %d: %s' % (n, f) for n, f in report.findings()]
    if found:
        raise _Stop('log', found)
    return [line.event for line in report.lines if line.duplicate_of is None]


def _done_tasks(events, uncovered):
    """AC2: {task id: accepted commit} of the DONE tasks whose decision record has no gap; each gap is uncovered."""
    done = {}
    for e in events:
        if e['type'] == 'task.done':
            done[e['task_id']] = e['payload']['decision_record']
    accepted = {}
    for task_id in sorted(done):
        record = None
        for e in events:
            if (e['type'] == 'decision.acceptance' and e.get('task_id') == task_id
                    and e['payload'].get('record_id') == done[task_id]):
                record = e['payload']
        if record is None:
            uncovered.append({'ref': task_id, 'detail': 'decision record %s not in the log' % done[task_id]})
        elif record.get('decision') != 'ACCEPT':
            uncovered.append({'ref': task_id, 'detail': 'decision record %s is not an ACCEPT decision' % done[task_id]})
        elif not _commit(record.get('evaluated_commit')):
            uncovered.append({'ref': task_id, 'detail': 'decision record %s has no evaluated_commit' % done[task_id]})
        else:
            accepted[task_id] = record['evaluated_commit']
    return accepted


def _task_facts(events, task_id):
    """AC2: the task's record payloads, earlier evidence.stale payloads and submitted commits, in log order."""
    recs, earlier, submitted = [], [], set()
    for e in events:
        if e.get('task_id') != task_id:
            continue
        if e['type'] == 'record.added':
            recs.append(e['payload'])
        elif e['type'] == 'evidence.stale':
            earlier.append({'reason': e['payload']['reason'], 'records': list(e['payload']['records'])})
        elif e['type'] == 'task.submitted':
            submitted.add(e['payload']['commit'])
    return recs, earlier, submitted


def _last_evaluated(events):
    """AC6: {task id: the evaluated_commit of its last decision.acceptance}."""
    out = {}
    for e in events:
        if e['type'] == 'decision.acceptance' and _text(e.get('task_id')):
            out[e['task_id']] = e['payload'].get('evaluated_commit')
    return out


# ---- AC3 ----

def _read_failure(name, r):
    """Why a read result does not count, or None when it does."""
    if not isinstance(r, dict) or not {'exit', 'out', 'err', 'error'} <= set(r):
        return 'git: %s gave no result in gitread.run\'s form' % name
    if r['error'] is not None:
        return 'git: %s was not run or did not finish: %s' % (name, r['error'])
    if r['exit'] != 0:
        return 'git: %s exited with %r' % (name, r['exit'])
    return None


def _walk(read, repo, trigger, wanted, max_commits):
    """AC3: the walked commits, newest first, each {commit, merge, paths} (paths None for a merge)."""
    walked = []
    left = set(wanted)
    current = trigger
    while current is not None and len(walked) < max_commits:
        r = read(repo, ['cat-file', '-p', current])
        why = _read_failure('cat-file -p %s' % current, r)
        if why is not None:
            raise _Stop('git', [why])
        parsed = gitread.parse_commit(r['out'])
        if parsed['error'] is not None:
            raise _Stop('git', ['git: commit %s is out of form: %s' % (current, parsed['error'])])
        merge = len(parsed['parents']) > 1
        paths = None
        if not merge:
            r = read(repo, gitread.DIFF_TREE + [current])
            why = _read_failure('diff-tree %s' % current, r)
            if why is not None:
                raise _Stop('git', [why])
            got = gitread.parse_paths(r['out'])
            if got['error'] is not None:
                raise _Stop('git', ['git: the paths of %s are out of form: %s' % (current, got['error'])])
            paths = list(got['paths'])
        walked.append({'commit': current, 'merge': merge, 'paths': paths})
        left.discard(current)
        if not left:
            break
        current = parsed['parents'][0] if parsed['parents'] else None
    return walked


# ---- AC5 ----

def _counted(entries, name, uncovered):
    """AC5: the entries whose source_class is counted; each other one is uncovered."""
    kept = []
    for i, r in enumerate(entries):
        if isinstance(r, dict) and r.get('source_class') in COUNTED:
            kept.append(r)
        else:
            rid = r.get('record_id') if isinstance(r, dict) else None
            uncovered.append({'ref': rid if _text(rid) else '%s[%d]' % (name, i), 'detail': 'source class not counted'})
    return kept


# ---- AC7 ----

def _step_error(steps, step_articles, commit, recorder):
    if not (isinstance(steps, list) and all(isinstance(s, dict) and _text(s.get('name')) and 'conclusion' in s
                                            for s in steps)):
        return 'steps is not a list of {name, conclusion} with non-empty string names'
    if not (isinstance(step_articles, dict) and all(
            _text(k) and isinstance(v, list) and v and all(_text(a) for a in v) for k, v in step_articles.items())):
        return 'step_articles is not a mapping from step names to non-empty lists of article ids'
    if not _commit(commit):
        return 'commit is not 40 or 64 lowercase hex characters'
    if not _text(recorder):
        return 'recorder is not a non-empty string'
    return None


def rule_result_id(commit, step, article):
    """AC7: the SHA-256 hex digest of "ci-rule", the commit, the step name and the article id joined by LF."""
    return hashlib.sha256('\n'.join((RECORD_PREFIX, commit, step, article)).encode('utf-8')).hexdigest()


def rule_results_from_steps(steps, step_articles, commit, recorder):
    """The mapping helper (TASK-031 AC7): a mapping with the keys records (article-form G3 observations), uncovered
    ({ref, detail} entries) and error (None, or a short text for a malformed argument, which gives no record). The
    arguments are not changed."""
    try:
        error = _step_error(steps, step_articles, commit, recorder)
    except Exception as exc:  # an argument whose own methods raise
        error = 'checking the arguments raised %s' % type(exc).__name__
    if error is not None:
        return {'records': [], 'uncovered': [], 'error': error}
    out, uncovered = [], []
    for s in steps:
        name = s['name']
        outcome = STEP_CONCLUSIONS.get(s['conclusion']) if isinstance(s['conclusion'], str) else None
        if name not in step_articles:
            uncovered.append({'ref': name, 'detail': 'step not named by the mapping'})
            continue
        if outcome is None:
            uncovered.append({'ref': name, 'detail': 'conclusion %r is neither success nor failure' % (s['conclusion'],)})
            continue
        for art in step_articles[name]:
            out.append({'record_id': rule_result_id(commit, name, art), 'fact_kind': 'observation',
                        'source_class': 'deterministic_tool_external_ci', 'recorder': recorder, 'subject': commit,
                        'commit': commit, 'gate': 'G3', 'outcome': outcome, 'refers_to': art})
    return {'records': out, 'uncovered': uncovered, 'error': None}


# ---- reconcile ----

def _compute(events, walked, trigger, accepted, values, rule_results, recorder, uncovered):
    """AC3 to AC6: the stale events in append order, drift's events and its already list."""
    position = {w['commit']: k for k, w in enumerate(walked)}
    stale_events = []
    for task_id in sorted(accepted):
        acc = accepted[task_id]
        if acc not in position:
            uncovered.append({'ref': task_id, 'detail': 'accepted commit not reached'})
            continue
        newer = walked[:position[acc]]
        if any(w['merge'] for w in newer):
            uncovered.append({'ref': task_id, 'detail': 'merge commit on the walk'})
            continue
        facts = values['tasks'].get(task_id)
        if facts is None:
            uncovered.append({'ref': task_id, 'detail': 'no facts given'})
            continue
        recs, earlier, submitted = _task_facts(events, task_id)
        inputs = {'task_id': task_id, 'accepted_commit': acc, 'trigger_commit': trigger, 'records': recs,
                  'intent_current': facts['intent_current'], 'read_set': facts['read_set'],
                  'read_set_estimate': facts['read_set_estimate'],
                  'base_commits': [{'commit': w['commit'], 'paths': list(w['paths']),
                                    'submitted_by_task': w['commit'] in submitted} for w in reversed(newer)],
                  'earlier_events': earlier}
        out = stale.stale(inputs)
        if out['error'] is not None:
            raise _Stop('stale', ['stale: %s: %s' % (task_id, out['error'])])
        for u in out['uncovered']:
            uncovered.append({'ref': task_id, 'detail': '%s, %s: %s' % (u['rule'], u['ref'], u['detail'])})
        stale_events.extend(out['events'])
    if walked[0]['merge']:
        uncovered.append({'ref': trigger, 'detail': 'trigger is a merge'})
        return stale_events, [], []
    last = _last_evaluated(events)
    task_records = []
    for task_id in sorted(t for t, c in last.items() if c == trigger):
        task_records.extend(_task_facts(events, task_id)[0])
    kept_results = _counted(rule_results, 'rule_results', uncovered)
    kept_records = _counted(task_records, 'task_records', uncovered)
    return stale_events, kept_results, kept_records


def reconcile(root, repo, trigger_commit, values, rule_results, recorder, now, max_commits=1000, read=None,
              read_log=None, append=None):
    """Reconcile at one base commit (TASK-031 AC1 to AC10); returns a mapping with RESULT_KEYS."""
    read = gitread.run if read is None else read
    read_log = writer.read_log if read_log is None else read_log
    append = writer.append_event if append is None else append

    try:
        found = _argument_findings(root, repo, trigger_commit, values, rule_results, recorder, now, max_commits)
    except Exception as exc:  # AC10: an argument whose own methods raise
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    if found:
        return _result('refused', 'argument', found)

    uncovered = []
    already = []
    step = 'log'
    try:
        events = _log_events(read_log, root)
        accepted = _done_tasks(events, uncovered)
        step = 'git'
        walked = _walk(read, repo, trigger_commit, accepted.values(), max_commits)
        step = 'stale'
        stale_events, kept_results, kept_records = _compute(events, walked, trigger_commit, accepted, values,
                                                            rule_results, recorder, uncovered)
        drift_events = []
        if not walked[0]['merge']:
            step = 'drift'
            out = drift.violations({'base_commit': trigger_commit, 'changed_paths': list(walked[0]['paths']),
                                    'articles': values['articles'], 'rule_results': kept_results,
                                    'task_records': kept_records, 'recorder': recorder})
            if out['error'] is not None:
                raise _Stop('drift', ['drift: %s' % out['error']])
            uncovered.extend(out['uncovered'])
            already = list(out['already'])
            drift_events = out['events']
    except _Stop as stop:
        return _result('refused', stop.reason, stop.findings, uncovered=uncovered)
    except Exception as exc:  # AC10: no exception escapes
        return _result('refused', step, ['%s: a step raised %s' % (step, type(exc).__name__)], uncovered=uncovered)

    appended, duplicate = [], []
    plan = [(e, e['task_id']) for e in stale_events] + [(e, None) for e in drift_events]
    for e, task_id in plan:
        eid = e['event_id']
        try:
            w = append(root, e['event_type'], e['payload'], eid, now, recorder, task_id=task_id)
            outcome = getattr(w, 'result', None)
            if type(outcome) is not str:
                raise TypeError('the result is not a string')
        except Exception as exc:  # AC8, AC10
            return _result('refused', 'append', ['append: the append of %s raised or gave no result (%s); whether it '
                                                 'was appended is not known' % (eid, type(exc).__name__)],
                           appended, duplicate, already, uncovered)
        if outcome == 'appended':
            appended.append(eid)
        elif outcome == 'duplicate':
            duplicate.append(eid)
        else:
            try:
                extra = [f for f in (getattr(w, 'findings', ()) or ()) if type(f) is str]
            except Exception:  # AC10
                extra = []
            return _result('refused', 'append', ['append: the writer gave %r for %s' % (outcome, eid)] + extra,
                           appended, duplicate, already, uncovered)
    return _result('reconciled', None, [], appended, duplicate, already, uncovered)
