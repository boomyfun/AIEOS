"""The scope-drift caller of gov-AIEOS (task TASK-034, hardened by task TASK-035; specification 4 revision 3, section 7
items 2 and 4; the risk rules' revision 4, policy version v3, section 2 point 7; concept lines 745 and 948; DEF-0030,
DEF-0060 and DEF-0061): the core's caller of scope_drift.claims (TASK-033).

``reconcile_scope(root, repo, commit, values, recorder, now, read=None, read_log=None, append=None)`` runs for one base
commit:

1. Arguments (AC1): every argument is checked before anything is read; a wrong one gives a refusal result.
2. The commit (AC2): read once with "cat-file -p" through ``read`` and parsed by gitread.parse_commit; its trailer
   tasks are the values of its "AIEOS-Task" trailers. The parent count is checked first: a commit with other than one
   parent (a merge or a root commit) is named uncovered ("not one parent") with no further read and no call of claims.
   Otherwise its changed paths are read with the pinned gitread.DIFF_TREE form; a commit with no changed path is named
   uncovered ("no changed path") and claims is not called. When an AIEOS-Task trailer value is not a task id, no
   trailer task is passed (so the commit is detected) and the commit is named uncovered ("trailer out of form").
3. The base read (AC3): the policy (docs/specs/risk-rules-gov-aieos.md) and the CI workflow
   (.github/workflows/aieos-checks.yml) are read at the commit's first parent, never at the commit judged, by a walk of
   Git trees with the pinned "cat-file -p <id>" form only (``read_base``). A listing line out of form (a name holding
   "/", NUL or any other control character included; TASK-035 AC2), a name listed twice in one listing (TASK-035 AC1),
   a missing path element, a type other than the one expected, a walked element whose mode does not fit its type
   (040000 for a tree, 100644 or 100755 for the blob; TASK-035 AC3), a failed read or bytes that do not decode stop the
   run. A name beginning with a double quote (Git's C-quoted form) is kept as an entry under its quoted text, so it
   never equals a walked element.
4. The policy's facts (AC4): the list by scope_drift.non_task_list; the rules translated into the governor's form
   {match, class} only (component_tags read as src/** and tests/**, rule R3 by tags; an entry out of form passed on as
   the refused rule {"match": [], "class": None}, so that no path is non-task); the evaluator list from the workflow's
   EVALUATOR literals, used only when every literal gives the same non-empty list (else the empty list, so that no
   path is non-task).
5. The contract (AC5): the log is read once through ``read_log`` and checked by records.check_log; a trailer task's
   write-set is passed to claims only when the SHA-256 of the caller's contract bytes equals the contract_hash of the
   task's last task.approved event in the log; a task with no task.approved event, no value given or another hash gets
   no entry (claims names it "no contract"), and only facts.contracts says which (TASK-035 AC5).
6. The call (AC6): claims once; a result whose error is not None stops the run (never "no claim").
7. The append (AC7): the returned event, if any, once through ``append`` with no task_id and no fencing token; the
   event id is taken inside the append's guard, so a returned event out of form is a refusal "append" with no append
   call (TASK-035 AC4).

The result (AC9) is a mapping with exactly the keys result ("reconciled" or "refused"), reason, findings, appended,
duplicate, detected, exempt, uncovered and facts (AC8 as amended by erratum E1 to AC8, decision D-716: facts is None
when the run makes no base read (an argument or git refusal, a merge, a root or a commit with no changed path) or stops
at the base or log read; otherwise it is the mapping of the facts the run used). An exception raised by a called
function is caught and becomes a result; none escapes.

``read``, ``read_log`` and ``append`` default, at call time, to gitread.run, writer.read_log and writer.append_event;
tests pass stand-ins.

Reading B1 (proposed; decision D-713 P1): "the base" at which the policy and the evaluator list are read, for one base
commit, is that commit's first parent.
Departure D1 (decision D-713 C2): the contract version used is the one the task's last task.approved event in the log
names (its contract_hash), not "the version the task's lease named" (specification 4 line 81): no lease event of
specification 2 carries a contract hash. The facts name the hash used.
Limit L1 (decision D-713 P3): a merge commit is not read against its first parent (gitread pins no diff form for it);
it is named uncovered, with no event.
Limit L2 (TASK-035; DEF-0061 m1): a reader that gives a raw newline inside a name (a stand-in, or a Git that does not
quote) can make a line in form naming a path element no other line names; the parser cannot tell such a line apart.
It is bounded by the refusal of a name listed twice, by reading R1 for the pinned read, and by the parent being
governed history.

Readings (the implementer's, not the contract's own words):
- A literal's item is out of form when it is not a single-quoted text without a quote or a line break; whether an item
  is of the risk rules' point 6 form is left to claims, which then makes no path non-task (the same outcome).
- A tree listing's name is taken as UTF-8.
- Reading R1 (the implementer's, unprobed; TASK-035, decision D-725 C2): "git cat-file -p <tree>" prints a tree as
  ls-tree does, so a name holding a control character, a double quote or a backslash (and, under the default
  core.quotePath, any non-ASCII name) comes C-quoted in double quotes; a raw tab or newline therefore never reaches the
  parser from the pinned read. The refusals of a name listed twice and of a control character hold whether or not R1
  is right.
- An append's result counts by its ``result`` text, as reconcile reads the writer's result.

What it does not do (AC10): it closes no claim, classifies and proposes nothing, changes no task state, grants,
releases or expires no lease, evaluates no task, calls no governor function except through scope_drift, makes no
constitution or stale-evidence finding and walks no range of commits: which commits to run is DEF-0030's caller's.

Limits (AC13):
- The write-set is the caller's data, bound only by the hash of the contract bytes it comes with (evaluation's limit,
  decision D-633 C1). The rules' translation reads R3 by tags as every path under src/** and tests/**.
- One run at a time: the writer reads the log and appends with no check that it is unchanged since this module's read.
- The PATH git is found by is the caller's precondition (DEF-0052 G1).
- The event id depends on the commit only (TASK-033), so a rerun with other facts is refused by the writer as a
  conflict; the facts say which facts a run used.
- It starts no process except through ``read``, opens no file except through ``read_log`` and ``append``, reads no
  clock and no environment, and builds no event-log line itself (INV-001 to INV-004).
"""

import datetime
import hashlib
import re

from aieos_bootstrap import gitread
from aieos_bootstrap import records
from aieos_bootstrap import scope_drift
from aieos_bootstrap import writer

RESULT_KEYS = ('result', 'reason', 'findings', 'appended', 'duplicate', 'detected', 'exempt', 'uncovered', 'facts')
FACT_KEYS = ('commit', 'parent', 'policy_blob', 'workflow_blob', 'non_task', 'rules', 'evaluator', 'contracts')
POLICY_PATH = 'docs/specs/risk-rules-gov-aieos.md'
WORKFLOW_PATH = '.github/workflows/aieos-checks.yml'
CONSTITUTION_PATH = 'docs/pre-genesis/constitution.md'
TAGS_MATCH = ['src/**', 'tests/**']
REFUSED_RULE = {'match': [], 'class': None}
RISKS = ('low', 'medium', 'high', 'critical')
EVENT_TYPE = 'drift.detected'
_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_TASK = re.compile(r'TASK-[0-9]+')
_ENTRY = re.compile(r'  - match: \{ (paths|component_tags): \[(.*)\] \}')
_RISK = re.compile(r'    risk: (\S+)')
_QUOTED = re.compile(r'"[^"\n,\]]+"(?:, "[^"\n,\]]+")*')
_TAGS = re.compile(r'[A-Za-z0-9_-]+(?:, [A-Za-z0-9_-]+)*')
_LITERAL = re.compile(r"'[^'\n]+'(?:,\s*'[^'\n]+')*,?")
_LISTING = re.compile(r'([0-7]+) (blob|tree|commit) ([0-9a-f]{40}|[0-9a-f]{64})\t([^/\x00-\x1f\x7f]+)')
MODES = {'tree': ('040000',), 'blob': ('100644', '100755')}
_ZERO = datetime.timedelta(0)


class _Stop(Exception):
    """A refusal found inside a step: its reason and findings."""

    def __init__(self, reason, findings):
        Exception.__init__(self, reason)
        self.reason = reason
        self.findings = list(findings)


def _text(value):
    return isinstance(value, str) and value != ''


def _result(result, reason=None, findings=(), appended=(), duplicate=(), detected=False, exempt=False, uncovered=(),
            facts=None):
    entries = sorted({(u['ref'], u['detail']) for u in uncovered})
    return {'result': result, 'reason': reason, 'findings': list(findings), 'appended': list(appended),
            'duplicate': list(duplicate), 'detected': detected, 'exempt': exempt,
            'uncovered': [{'ref': r, 'detail': d} for r, d in entries], 'facts': facts}


# ---- AC1 ----

def _argument_findings(root, repo, commit, values, recorder, now):
    """AC1: what is wrong with the arguments, as a list of findings (empty when every argument is in form)."""
    found = []
    for name, value in (('root', root), ('repo', repo)):
        if not _text(value):
            found.append('argument: %s is not a non-empty string' % name)
    if not (isinstance(commit, str) and _COMMIT.fullmatch(commit)):
        found.append('argument: commit is not 40 or 64 lowercase hex characters')
    if not (isinstance(values, dict) and set(values) == {'contracts'}):
        found.append('argument: values is not a mapping with exactly the key contracts')
    elif not isinstance(values['contracts'], dict):
        found.append('argument: values contracts is not a mapping')
    else:
        for task_id in sorted(values['contracts'], key=str):
            entry = values['contracts'][task_id]
            if not (isinstance(task_id, str) and _TASK.fullmatch(task_id)):
                found.append('argument: values contracts has a key that is not a task id: %r' % (task_id,))
            elif not (isinstance(entry, dict) and set(entry) == {'contract_bytes', 'write_set'}
                      and isinstance(entry['contract_bytes'], bytes) and isinstance(entry['write_set'], list)
                      and all(isinstance(p, str) for p in entry['write_set'])):
                found.append('argument: values contracts %s is not a mapping with exactly contract_bytes (bytes) and '
                             'write_set (a list of strings)' % task_id)
    if not _text(recorder):
        found.append('argument: recorder is not a non-empty string')
    if not (isinstance(now, datetime.datetime) and now.tzinfo is not None and now.utcoffset() == _ZERO):
        found.append('argument: now is not a timezone-aware datetime in UTC')
    return found


# ---- AC2 and AC3: Git ----

def _read_failure(name, r):
    """Why a read result does not count, or None when it does."""
    if not isinstance(r, dict) or not {'exit', 'out', 'err', 'error'} <= set(r):
        return '%s gave no result in gitread.run\'s form' % name
    if r['error'] is not None:
        return '%s was not run or did not finish: %s' % (name, r['error'])
    if r['exit'] != 0:
        return '%s exited with %r' % (name, r['exit'])
    if not isinstance(r['out'], bytes):
        return '%s gave no bytes' % name
    return None


def _cat(read, repo, oid, reason):
    r = read(repo, ['cat-file', '-p', oid])
    why = _read_failure('cat-file -p %s' % oid, r)
    if why is not None:
        raise _Stop(reason, ['%s: %s' % (reason, why)])
    return r['out']


def _listing(data, oid):
    """AC3: the entries {name: (mode, type, id)} of a tree's "cat-file -p" output; any line out of form (a control
    character in a name included, TASK-035 AC2) and a name listed twice (TASK-035 AC1) stop."""
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        raise _Stop('base', ['base: the listing of tree %s is not UTF-8' % oid])
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]
    out = {}
    for line in lines:
        m = _LISTING.fullmatch(line)
        if m is None:
            raise _Stop('base', ['base: a line of the listing of tree %s is out of form' % oid])
        if m.group(4) in out:
            raise _Stop('base', ['base: the listing of tree %s names %s twice' % (oid, m.group(4))])
        out[m.group(4)] = (m.group(1), m.group(2), m.group(3))
    return out


def _blob_at(read, repo, tree, path):
    """AC3: (the blob's id, its text) for path in the tree; a missing element, a wrong type or a walked element's mode
    that does not fit its type (TASK-035 AC3) stops."""
    parts = path.split('/')
    current = tree
    for k, name in enumerate(parts):
        entries = _listing(_cat(read, repo, current, 'base'), current)
        if name not in entries:
            raise _Stop('base', ['base: %s: the element %s is missing' % (path, name)])
        mode, kind, oid = entries[name]
        want = 'blob' if k == len(parts) - 1 else 'tree'
        if kind != want:
            raise _Stop('base', ['base: %s: the element %s is a %s, not a %s' % (path, name, kind, want)])
        if mode not in MODES[want]:
            raise _Stop('base', ['base: %s: the element %s has the mode %s, not a %s mode' % (path, name, mode, want)])
        current = oid
    data = _cat(read, repo, current, 'base')
    try:
        return current, data.decode('utf-8')
    except UnicodeDecodeError:
        raise _Stop('base', ['base: %s does not decode as UTF-8' % path])


def read_base(repo, parent, read=None):
    """The base read (TASK-034 AC3): a mapping with exactly the keys policy_blob, policy, workflow_blob and workflow
    (the two files' blob ids and texts at the commit ``parent``, read with the pinned "cat-file -p <id>" form only), or
    a stop. Called by reconcile_scope; any failure is raised to it, which turns it into a refusal "base"."""
    read = gitread.run if read is None else read
    parsed = gitread.parse_commit(_cat(read, repo, parent, 'base'))
    if parsed['error'] is not None or not (isinstance(parsed['tree'], str) and _COMMIT.fullmatch(parsed['tree'])):
        raise _Stop('base', ['base: the parent commit %s is out of form' % parent])
    policy_blob, policy = _blob_at(read, repo, parsed['tree'], POLICY_PATH)
    workflow_blob, workflow = _blob_at(read, repo, parsed['tree'], WORKFLOW_PATH)
    return {'policy_blob': policy_blob, 'policy': policy, 'workflow_blob': workflow_blob, 'workflow': workflow}


# ---- AC4 ----

def _block(text):
    """The lines of the policy's section 3 yaml block, or None (as TASK-033 AC2 finds it)."""
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
    return lines[start + 1:end]


def rules_from_policy(text):
    """AC4: the policy's risk_rules in the governor's form, each exactly {match, class}; an entry out of form is passed
    on as the refused rule, and a block or a risk_rules key that cannot be found gives the single refused rule."""
    block = _block(text)
    if block is None or 'risk_rules:' not in block:
        return [dict(REFUSED_RULE)]
    lines = [x for x in block[block.index('risk_rules:') + 1:] if not x.strip().startswith('#') and x.strip() != '']
    rules = []
    k = 0
    while k < len(lines):
        m = _ENTRY.fullmatch(lines[k])
        r = _RISK.fullmatch(lines[k + 1]) if k + 1 < len(lines) else None
        if m is None or r is None:
            rules.append(dict(REFUSED_RULE))
            k += 1
            continue
        kind, items = m.group(1), m.group(2)
        if kind == 'paths' and _QUOTED.fullmatch(items):
            match = re.findall(r'"([^"]*)"', items)
        elif kind == 'component_tags' and _TAGS.fullmatch(items):
            match = list(TAGS_MATCH)
        else:
            match = None
        cls = r.group(1)
        rules.append({'match': match, 'class': cls} if match is not None and cls in RISKS else dict(REFUSED_RULE))
        k += 2
    return rules


def evaluator_from_workflow(text):
    """AC4: the evaluator list when the workflow holds at least one EVALUATOR literal and every literal gives the same
    non-empty list; otherwise the empty list."""
    lines = text.split('\n')
    found = []
    for i, line in enumerate(lines):
        if not line.strip().startswith('EVALUATOR = ['):
            continue
        end = next((k for k in range(i, len(lines)) if ']' in lines[k]), None)
        if end is None:
            return []
        joined = ' '.join(x.strip() for x in lines[i:end + 1])
        body = joined[len('EVALUATOR = ['):]
        if not body.endswith(']'):
            return []
        body = body[:-1].strip()
        if not _LITERAL.fullmatch(body):
            return []
        found.append(re.findall(r"'([^'\n]*)'", body))
    if not found or any(f != found[0] for f in found) or not found[0]:
        return []
    return found[0]


# ---- AC5 ----

def _log_events(read_log, root):
    data = read_log(root)
    if not isinstance(data, bytes):
        raise _Stop('log', ['log: read_log gave %s, not bytes' % type(data).__name__])
    report = records.check_log(data)
    found = ['log: line %d: %s' % (n, f) for n, f in report.findings()]
    if found:
        raise _Stop('log', found)
    return [line.event for line in report.lines if line.duplicate_of is None]


def _contracts(events, tasks, given):
    """AC5: the contracts for claims and, for each trailer task, the hash matched or why not."""
    contracts, facts = {}, {}
    for task in tasks:
        approved = [e for e in events if e.get('type') == 'task.approved' and e.get('task_id') == task]
        if not approved:
            facts[task] = 'no task.approved event'
            continue
        want = approved[-1]['payload'].get('contract_hash')
        if task not in given:
            facts[task] = 'no value given'
            continue
        if hashlib.sha256(given[task]['contract_bytes']).hexdigest() != want:
            facts[task] = 'hash differs'
            continue
        contracts[task] = list(given[task]['write_set'])
        facts[task] = want
    return contracts, facts


# ---- reconcile_scope ----

def reconcile_scope(root, repo, commit, values, recorder, now, read=None, read_log=None, append=None):
    """Scope drift for one base commit (TASK-034 AC1 to AC9); returns a mapping with RESULT_KEYS."""
    read = gitread.run if read is None else read
    read_log = writer.read_log if read_log is None else read_log
    append = writer.append_event if append is None else append

    try:
        found = _argument_findings(root, repo, commit, values, recorder, now)
    except Exception as exc:  # AC9: an argument whose own methods raise
        found = ['argument: checking the arguments raised %s' % type(exc).__name__]
    if found:
        return _result('refused', 'argument', found)

    uncovered = []
    facts = None
    step = 'git'
    try:
        parsed = gitread.parse_commit(_cat(read, repo, commit, 'git'))
        if parsed['error'] is not None:
            raise _Stop('git', ['git: commit %s is out of form: %s' % (commit, parsed['error'])])
        if len(parsed['parents']) != 1:
            return _result('reconciled', uncovered=[{'ref': commit, 'detail': 'not one parent'}])
        r = read(repo, gitread.DIFF_TREE + [commit])
        why = _read_failure('diff-tree %s' % commit, r)
        if why is not None:
            raise _Stop('git', ['git: ' + why])
        got = gitread.parse_paths(r['out'])
        if got['error'] is not None:
            raise _Stop('git', ['git: the paths of %s are out of form: %s' % (commit, got['error'])])
        paths = list(got['paths'])
        if not paths:
            return _result('reconciled', uncovered=[{'ref': commit, 'detail': 'no changed path'}])
        values_t = [v for k, v in parsed['trailers'] if k == 'AIEOS-Task']
        if all(isinstance(v, str) and _TASK.fullmatch(v) for v in values_t):
            tasks = values_t
        else:
            tasks = []
            uncovered.append({'ref': commit, 'detail': 'trailer out of form'})
        parent = parsed['parents'][0]
        step = 'base'
        base = read_base(repo, parent, read)
        non_task = scope_drift.non_task_list(base['policy'])
        rules = rules_from_policy(base['policy'])
        evaluator = evaluator_from_workflow(base['workflow'])
        step = 'log'
        events = _log_events(read_log, root) if tasks else []
        contracts, contract_facts = _contracts(events, sorted(set(tasks)), values['contracts'])
        facts = {'commit': commit, 'parent': parent, 'policy_blob': base['policy_blob'],
                 'workflow_blob': base['workflow_blob'], 'non_task': non_task, 'rules': len(rules),
                 'evaluator': list(evaluator), 'contracts': contract_facts}
        step = 'scope_drift'
        out = scope_drift.claims({'commit': commit, 'parents': 1, 'trailer_tasks': list(tasks), 'changed_paths': paths,
                                  'contracts': contracts, 'non_task': non_task, 'risk_rules': rules,
                                  'evaluator': list(evaluator), 'constitution_path': CONSTITUTION_PATH,
                                  'policy_path': POLICY_PATH})
        if out['error'] is not None:
            raise _Stop('scope_drift', ['scope_drift: %s' % out['error']])
        uncovered.extend(out['uncovered'])
        detected, exempt, events_out = out['detected'], out['exempt'], out['events']
    except _Stop as stop:
        return _result('refused', stop.reason, stop.findings, uncovered=uncovered, facts=facts)
    except Exception as exc:  # AC9: no exception escapes
        return _result('refused', step, ['%s: a step raised %s' % (step, type(exc).__name__)], uncovered=uncovered,
                       facts=facts)

    appended, duplicate = [], []
    out_of_form = ['append: the returned event is out of form; nothing was appended for it']
    if type(events_out) is not list:  # TASK-035 AC4
        return _result('refused', 'append', out_of_form, appended, duplicate, detected, exempt, uncovered, facts)
    for e in events_out:
        eid = None
        try:
            # TASK-035 AC4: the event id and the payload are taken inside the guard; an event out of form is refused
            # before any append call.
            if type(e) is not dict or 'event_id' not in e or 'payload' not in e:
                return _result('refused', 'append', out_of_form, appended, duplicate, detected, exempt, uncovered,
                               facts)
            eid, payload = e['event_id'], e['payload']
            w = append(root, EVENT_TYPE, payload, eid, now, recorder)
            outcome = getattr(w, 'result', None)
            if type(outcome) is not str:
                raise TypeError('the result is not a string')
        except Exception as exc:  # AC7, AC9
            return _result('refused', 'append', ['append: the append of %s raised or gave no result (%s); whether it '
                                                 'was appended is not known' % (eid, type(exc).__name__)],
                           appended, duplicate, detected, exempt, uncovered, facts)
        if outcome == 'appended':
            appended.append(eid)
        elif outcome == 'duplicate':
            duplicate.append(eid)
        else:
            try:
                extra = [f for f in (getattr(w, 'findings', ()) or ()) if type(f) is str]
            except Exception:  # AC9
                extra = []
            return _result('refused', 'append', ['append: the writer gave %r for %s' % (outcome, eid)] + extra,
                           appended, duplicate, detected, exempt, uncovered, facts)
    return _result('reconciled', None, [], appended, duplicate, detected, exempt, uncovered, facts)
