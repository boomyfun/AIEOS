"""The stale-evidence computation of gov-AIEOS (task TASK-023; specification 4 revision 3, section 3 rules 2 and 3 and
section 7 item 3; concept lines 728 and 746: evidence is bound to a commit and an intent version, and code that changes
makes old evidence stale).

``stale`` takes one task's reconciliation facts as values: its accepted commit, its records, the current intent
versions at the base's head, its effective read-set with each entry resolved by the caller, the base commits after the
accepted commit with their changed paths, the triggering base commit and the task's earlier evidence.stale events. It
returns the stale record ids by reason, at most one evidence.stale event per reason with only the ids that no earlier
event of the same reason listed, and the list of what it could not check. A malformed input gives an error and no
event (fail closed).

- Rule 2 (reason intent_version): a record with intent_versions is stale when, for an id it names, the current
  version differs. An id with no current version is uncovered only (a reading of the task contract, AC2).
- Rule 3 (reason commit), reconciliation only: a base commit meets the read-set when the task's own submission did not
  make it and one of its paths matches an entry; a record is stale when such a commit comes later, in the given order,
  than the record's commit. A path entry is matched by its own text; an interface or schema entry by the patterns
  the caller resolved it to; any entry whose patterns the caller gives as None is uncovered and meets nothing (the
  implementer's reading, approved in decision D-548 Q2), and so is one whose patterns are an empty list, which names
  no path (the decision agent's reading, decision D-551 Q2, proposed). Path matching is aieos_bootstrap.resume_check's
  (specification 3 section 3), called, not copied.

The readings of the decision agent (decision D-544 Q2, points 1 to 4, proposed, not the specification's own words):
- An interface or schema entry is met when a changed path matches one of the patterns the caller resolved it to; an
  entry the caller could not resolve is uncovered, not stale.
- The accepted commit comes before every base commit. A record whose commit is neither the accepted commit nor a base
  commit is treated as earlier than every base commit (fail closed), and is named as uncovered: "commit order not
  known".
- A record with no intent_versions, or no commit, is uncovered for rule 2, or rule 3: never stale by that rule and
  never reported as passed. A read-set that is an estimate is uncovered. An empty intent_versions names no artefact,
  so it counts as no intent_versions (decision D-548 Q3, proposed).
- An event's id is the SHA-256 hex digest of "evidence.stale", the task id, the triggering commit and the reason
  joined by LF, as the writer joins the parts of its refusal ids.

Limits (TASK-023 AC7 and AC11):
- It runs neither rule 1 (the governor's rule 2, at an evaluation) nor any governor rule; it changes no task state,
  blocks nothing and appends nothing. An evidence.stale event schedules a re-verify and a DONE task stays DONE, by the
  event's effect in specification 1, not by this module. Whether the governor should also use rule 3 is DEF-0042 point
  10, not settled here.
- The facts are the caller's: reading Git and the event log, the derived and observed read-sets, resolving interfaces
  and schemas to paths, and appending the events through the core's single writer belong to the caller carried in
  DEF-0030, which does not exist yet. The facts are not checked against Git or the log here.
- It reads no file, no clock and no environment, and makes no process, network or model call (INV-001 to INV-003).
"""

import hashlib
import re

from aieos_bootstrap import resume_check

EVENT_TYPE = 'evidence.stale'
REASONS = ('commit', 'intent_version')
KINDS = ('path', 'interface', 'schema')
INPUT_KEYS = ('task_id', 'accepted_commit', 'trigger_commit', 'records', 'intent_current', 'read_set',
              'read_set_estimate', 'base_commits', 'earlier_events')
_TASK = re.compile(r'TASK-[0-9]{3}')
_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_VERSION = re.compile(r'v[0-9]+')


def _text(value):
    return isinstance(value, str) and value != ''


def _full(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _versions(value):
    """The record form of intent_versions (specification 2 section 6.2): ids to "v" followed by digits."""
    return isinstance(value, dict) and all(_text(k) and _full(_VERSION, v) for k, v in value.items())


def _strings(value, non_empty=False):
    return isinstance(value, list) and all(isinstance(v, str) and (v != '' or not non_empty) for v in value)


def _record_ok(r):
    if not (isinstance(r, dict) and _text(r.get('record_id'))):
        return False
    if 'commit' in r and not _full(_COMMIT, r['commit']):
        return False
    return 'intent_versions' not in r or _versions(r['intent_versions'])


def _entry_ok(e):
    return (isinstance(e, dict) and set(e) == {'entry', 'kind', 'patterns'} and _text(e['entry'])
            and e['kind'] in KINDS and (e['patterns'] is None or _strings(e['patterns'], True)))


def _input_error(inputs):
    """The first form of AC1 that fails, as a short text, or None."""
    if not isinstance(inputs, dict):
        return 'inputs is not a mapping'
    checks = (
        ('task_id', lambda v: _full(_TASK, v), 'is not TASK- followed by three digits'),
        ('accepted_commit', lambda v: _full(_COMMIT, v), 'is not 40 or 64 lowercase hex characters'),
        ('trigger_commit', lambda v: _full(_COMMIT, v), 'is not 40 or 64 lowercase hex characters'),
        ('records', lambda v: isinstance(v, list) and all(_record_ok(r) for r in v)
         and len({r['record_id'] for r in v}) == len(v),
         'is not a list of records with unique ids, commits and intent_versions in their forms'),
        ('intent_current', _versions, 'is not a mapping from ids to versions v<digits>'),
        ('read_set', lambda v: isinstance(v, list) and all(_entry_ok(e) for e in v),
         'is not a list of {entry, kind, patterns}'),
        ('read_set_estimate', lambda v: isinstance(v, bool), 'is not a bool'),
        ('base_commits', lambda v: _base_ok(v, inputs.get('accepted_commit')),
         'is not a list of {commit, paths, submitted_by_task} with distinct commits other than the accepted one'),
        ('earlier_events', lambda v: isinstance(v, list) and all(
            isinstance(e, dict) and set(e) == {'reason', 'records'} and e['reason'] in REASONS and _strings(e['records'])
            for e in v), 'is not a list of {reason, records}'),
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


def _base_ok(value, accepted):
    if not isinstance(value, list):
        return False
    seen = set()
    for c in value:
        if not (isinstance(c, dict) and set(c) == {'commit', 'paths', 'submitted_by_task'}
                and _full(_COMMIT, c['commit']) and _strings(c['paths'])
                and isinstance(c['submitted_by_task'], bool)):
            return False
        if c['commit'] in seen or c['commit'] == accepted:
            return False
        seen.add(c['commit'])
    return True


def _event_id(task_id, trigger_commit, reason):
    return hashlib.sha256('\n'.join((EVENT_TYPE, task_id, trigger_commit, reason)).encode('utf-8')).hexdigest()


def _meets(entry, path):
    if entry['kind'] == 'path':
        return resume_check.matches(entry['entry'], path)
    return any(resume_check.matches(p, path) for p in entry['patterns'])


def stale(inputs):
    """The stale-evidence computation for one task (TASK-023 AC1 to AC8): a mapping with the keys stale (each reason to
    the sorted stale record ids), events (at most one evidence.stale event per reason, commit first), uncovered
    (sorted {rule, ref, detail} entries, without duplicates) and error (None, or a short text for a malformed input,
    which gives no stale id, no event and no uncovered entry). The input is not changed."""
    error = _input_error(inputs)
    if error is not None:
        return {'stale': {r: [] for r in REASONS}, 'events': [], 'uncovered': [], 'error': error}
    uncovered = set()
    found = {r: set() for r in REASONS}
    current = inputs['intent_current']
    # Rule 2 (AC2, AC5).
    for r in inputs['records']:
        rid = r['record_id']
        if not r.get('intent_versions'):
            uncovered.add(('rule 2', rid, 'no intent_versions'))
            continue
        for ident, version in sorted(r['intent_versions'].items()):
            if ident not in current:
                uncovered.add(('rule 2', rid, 'no current version of ' + ident))
            elif current[ident] != version:
                found['intent_version'].add(rid)
    # Rule 3 (AC3 to AC5).
    entries = []
    for e in inputs['read_set']:
        if not e['patterns']:
            uncovered.add(('rule 3', e['entry'], 'not resolved by the caller'))
        else:
            entries.append(e)
    if inputs['read_set_estimate']:
        uncovered.add(('rule 3', 'read_set', 'the read-set is an estimate'))
    position = {inputs['accepted_commit']: -1}
    meeting = []
    for k, c in enumerate(inputs['base_commits']):
        position[c['commit']] = k
        if not c['submitted_by_task'] and any(_meets(e, p) for p in c['paths'] for e in entries):
            meeting.append(k)
    last = max(meeting) if meeting else None
    for r in inputs['records']:
        rid = r['record_id']
        if 'commit' not in r:
            uncovered.add(('rule 3', rid, 'no commit'))
            continue
        at = position.get(r['commit'])
        if at is None:
            uncovered.add(('rule 3', rid, 'commit order not known'))
            at = -2
        if last is not None and last > at:
            found['commit'].add(rid)
    # The events (AC6).
    events = []
    for reason in REASONS:
        listed = set()
        for e in inputs['earlier_events']:
            if e['reason'] == reason:
                listed.update(e['records'])
        new = sorted(found[reason] - listed)
        if new:
            events.append({'event_id': _event_id(inputs['task_id'], inputs['trigger_commit'], reason),
                           'event_type': EVENT_TYPE, 'task_id': inputs['task_id'],
                           'payload': {'records': new, 'reason': reason}})
    return {'stale': {r: sorted(found[r]) for r in REASONS}, 'events': events,
            'uncovered': [{'rule': a, 'ref': b, 'detail': c} for a, b, c in sorted(uncovered)], 'error': None}
