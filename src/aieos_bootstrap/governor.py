"""The bootstrap governor of gov-AIEOS, its first version (task TASK-004; governor-spec.md revision 5).

``evaluate(request, inputs, records)`` takes an evaluation request (specification 2 section 6.5), the inputs of
governor-spec.md section 3.2 as values (conformance-files.md section 4) and the records it reads (specification 2
section 6.2), and returns one acceptance decision record (specification 2 section 6.4) by the rules of governor-spec.md
section 4 and the table of section 5. ``derive_inputs(values)`` derives those inputs from values: the contract's
declared fields, the changed paths, the policy's rules, the owner-kept path rules, the articles, the default and the
requirements' profiles and the pinned delegation value.

Limits (TASK-004 AC12):
- Its decisions are advisory (governor-spec.md section 10); A29 cannot hold, because the CI channel runs agent-written
  code. It emits no execution decision.
- Row 4 of the table (ACCEPT) cannot apply to gov-AIEOS now: the self-build is at L1 (A35; A54 point 2), and no input
  gives a risk class's level, so this module reads every class as L1.
- evaluate takes the section 3.2 inputs as values and derive_inputs takes values: reading the policy, the
  constitution, the requirements and the task contracts from the repository is not covered (conformance-files.md
  section 1; governor-spec.md section 6.2).
- governor_identity and scenario_set_hash are null, for the caller to give; the record's source_class
  (deterministic_tool_local) and recorder (this module's path) are defaults, not the channel or the identity that
  specification 2 section 6.4 names: evaluate reads no file and knows neither where it runs nor its own content hash.
- A candidate run of this module in the CI channel runs inside the runner's process, so it can be forged from inside
  that process; no acceptance rests on it alone. The pin is a later workflow revision, the owner's, computed from the
  accepted file's bytes.
- The open points of governor-spec.md section 11 stay open; where the module needs one, it applies the proposed
  reading and marks it "(reading)".
- It reads only its arguments: no file, environment variable, clock, random source, network or process. It does not
  change its arguments, and the same arguments always give the same record (constitution INV-010).
"""

import hashlib
import re

from aieos_bootstrap import records as record_forms

MODULE_PATH = 'src/aieos_bootstrap/governor.py'
SOURCE_CLASS = 'deterministic_tool_local'
CI = 'deterministic_tool_external_ci'
RISKS = ('low', 'medium', 'high', 'critical')
EVALUATED_STATES = ('VERIFYING', 'IN_REVIEW')
HUMAN_TYPES = ('human_review', 'human_security_review')
AI_REVIEW = 'ai_review'
CROSS_MODEL = 'ai_review (cross-model)'
REVIEW_RECORD_TYPES = ('other_model_review', 'decision_agent_review')
ROW_1_KINDS = ('out_of_scope', 'forbidden_path', 'violation')
REQUEST_KEYS = frozenset({'task_id', 'task_content_hash', 'evaluated_commit', 'intent_versions', 'task_state',
                          'changed_paths', 'retry_count'})
INPUT_KEYS = frozenset({'traces_to', 'risk', 'owner_kept_act', 'weakens_evidence', 'delegation_in_force',
                        'auto_accept', 'verification_plan', 'evidence_profile', 'applicable_articles',
                        'policy_version', 'level_version', 'ruleset_version'})
VALUE_KEYS = frozenset({'contract', 'changed_paths', 'risk_rules', 'owner_kept_rules', 'articles', 'default_profiles',
                        'requirement_profiles', 'delegation', 'evidence_comparison', 'auto_accept', 'policy_version',
                        'level_version', 'ruleset_version'})
CONTRACT_KEYS = frozenset({'traces_to', 'risk', 'owner_kept_act', 'verification_plan'})
# The self-build runs at L1 (A35); row 4 needs L2 or above (governor-spec.md section 5), so it never applies (AC12).
LEVEL_AT_LEAST_L2 = False
NOTES = (
    'advisory: decisions of this governor are advisory (governor-spec.md section 10)',
    'inputs: the inputs of governor-spec.md section 3.2 are values given to evaluate, not read from the repository',
    'identity: governor_identity and scenario_set_hash are for the caller; source_class and recorder are this '
    'module\'s defaults, not the channel or the identity that specification 2 section 6.4 names',
)

_HEX64 = re.compile(r'[0-9a-f]{64}')
_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_TASK = re.compile(r'TASK-[0-9]+')
_VERSION = re.compile(r'v[0-9]+')
_GATE = re.compile(r'G[0-9]+')


def _text(value):
    """A non-empty string that UTF-8 can encode (a lone surrogate cannot), so that it can enter the record."""
    if not isinstance(value, str) or value == '':
        return False
    try:
        value.encode('utf-8')
    except UnicodeEncodeError:
        return False
    return True


def _texts(value):
    return isinstance(value, list) and all(_text(v) for v in value)


def _full(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def canon(value, indent=0):
    """The canonical JSON text of one value (conformance-files.md section 2), without the final LF."""
    pad = ' ' * (indent + 2)
    if isinstance(value, dict):
        if not value:
            return '{}'
        items = (pad + canon(k) + ': ' + canon(value[k], indent + 2) for k in sorted(value))
        return '{\n' + ',\n'.join(items) + '\n' + ' ' * indent + '}'
    if isinstance(value, list):
        if not value:
            return '[]'
        return '[\n' + ',\n'.join(pad + canon(x, indent + 2) for x in value) + '\n' + ' ' * indent + ']'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if value is None:
        return 'null'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        out = []
        for ch in value:
            if ch in '"\\':
                out.append('\\' + ch)
            elif ord(ch) < 0x20:
                out.append('\\u%04x' % ord(ch))
            else:
                out.append(ch)
        return '"' + ''.join(out) + '"'
    raise ValueError('a value of type %s has no canonical form' % type(value).__name__)


def _record_id(record):
    """"decision-" and the SHA-256 of the canonical form of the record without record_id (AC8; decision D-221 E1)."""
    text = canon({k: v for k, v in record.items() if k != 'record_id'}) + '\n'
    return 'decision-' + hashlib.sha256(text.encode('utf-8')).hexdigest()


# ---------------------------------------------------------------------------------------------------------------
# Input checks (governor-spec.md section 4 rules 6 and 7; AC2)

def _request_errors(req):
    if not isinstance(req, dict) or set(req) != REQUEST_KEYS:
        return ['the request is not exactly the keys of specification 2 section 6.5']
    errors = []
    if not _full(_HEX64, req['task_content_hash']):
        errors.append('task_content_hash')
    if not _full(_COMMIT, req['evaluated_commit']):
        errors.append('evaluated_commit')
    if not _intent_versions(req['intent_versions']):
        errors.append('intent_versions')
    if req['task_state'] not in EVALUATED_STATES:
        # governor-spec.md section 3.1: VERIFYING, or IN_REVIEW for re-evaluation (reading: any other state is
        # malformed).
        errors.append('task_state')
    if not _texts(req['changed_paths']):
        errors.append('changed_paths')
    rc = req['retry_count']
    if not (isinstance(rc, dict) and set(rc) == {'used', 'limit'} and _count(rc['used']) and _count(rc['limit'])):
        errors.append('retry_count')
    return ['the request\'s %s is malformed' % e for e in errors]


def _intent_versions(value):
    return isinstance(value, dict) and all(_text(k) and _full(_VERSION, v) for k, v in value.items())


def _profile_form(value):
    return isinstance(value, list) and all(
        isinstance(e, dict) and set(e) == {'dimension', 'evidence_types'} and _text(e['dimension'])
        and _texts(e['evidence_types']) for e in value)


def _articles_form(value):
    return isinstance(value, list) and all(
        isinstance(a, dict) and set(a) == {'id', 'evidence_required'} and _text(a['id'])
        and _texts(a['evidence_required']) for a in value)


def _inputs_errors(inp):
    if not isinstance(inp, dict) or set(inp) != INPUT_KEYS:
        return ['the inputs are not exactly the keys of conformance-files.md section 4']
    errors = []
    if not _texts(inp['traces_to']):
        errors.append('traces_to')
    if inp['risk'] not in RISKS:
        # A change that matches no risk rule gets no decision value (governor-spec.md section 4 rule 8).
        errors.append('risk')
    for key in ('owner_kept_act', 'weakens_evidence', 'delegation_in_force', 'auto_accept'):
        if not isinstance(inp[key], bool):
            # A missing delegation value gives no decision (section 3.2; section 4 rule 7).
            errors.append(key)
    if not (_texts(inp['verification_plan']) and all(_full(_GATE, g) for g in inp['verification_plan'])):
        errors.append('verification_plan')
    if not _profile_form(inp['evidence_profile']):
        errors.append('evidence_profile')
    if not _articles_form(inp['applicable_articles']):
        errors.append('applicable_articles')
    for key in ('policy_version', 'level_version', 'ruleset_version'):
        if not _text(inp[key]):
            errors.append(key)
    return ['the inputs\' %s is malformed' % e for e in errors]


def _records_errors(recs):
    if not isinstance(recs, list):
        return ['the records are not a list']
    seen, errors = set(), []
    for r in recs:
        rid = r.get('record_id') if isinstance(r, dict) else None
        if _text(rid):
            if rid in seen:
                # Reading (AC2): a record id used twice makes the request malformed.
                errors.append('the record id %s is used twice' % rid)
            seen.add(rid)
    return errors


# ---------------------------------------------------------------------------------------------------------------
# The decision record (governor-spec.md section 6.1; specification 2 section 6.4; AC8)

def _base(task, request, inputs):
    rec = {
        'fact_kind': 'interpretation',
        'source_class': SOURCE_CLASS,
        'recorder': MODULE_PATH,
        'subject': task,
        'governor_identity': None,
        'scenario_set_hash': None,
    }
    for key in ('policy_version', 'level_version', 'ruleset_version'):
        rec[key] = inputs[key] if isinstance(inputs, dict) and _text(inputs.get(key)) else None
    return rec


def _error_record(task, request, inputs, error):
    """A record with no decision value (rule 7): the error, the task's state as the next state when it is a state name,
    no table row, and AC8's keys (reading: a key whose value would give a check_decision finding is left out)."""
    rec = _base(task, request, inputs)
    rec.update({'decision': None, 'error': error, 'table_row': None, 'profile_used': [], 'missing_gates': [],
                'blocking': [], 'failed_gates': [], 'reverify': [], 'approval_record': None,
                'uncovered': list(NOTES), 'rests_on_ai': {'entries': [], 'approval': False}})
    if _full(_HEX64, request.get('task_content_hash')):
        rec['task_content_hash'] = request['task_content_hash']
    if _full(_COMMIT, request.get('evaluated_commit')):
        rec['evaluated_commit'] = request['evaluated_commit']
    if _intent_versions(request.get('intent_versions')):
        rec['intent_versions'] = dict(request['intent_versions'])
    if request.get('task_state') in record_forms.STATE_NAMES:
        rec['next_task_state'] = request['task_state']
    rec['record_id'] = _record_id(rec)
    return rec


# ---------------------------------------------------------------------------------------------------------------
# The profile (governor-spec.md section 3.2: the evidence profile and the applicable articles)

def _join(profile, articles):
    """The profile as (dimension, types) pairs in first-seen order: entries of one dimension are joined, and each
    applicable article's evidence_required joins under a dimension named by the article's id (reading: an article
    names no dimension, so a record satisfies its entry only when its dimension is the article's id)."""
    out = {}
    for entry in profile:
        types = out.setdefault(entry['dimension'], [])
        types.extend(t for t in entry['evidence_types'] if t not in types)
    for article in articles:
        types = out.setdefault(article['id'], [])
        types.extend(t for t in article['evidence_required'] if t not in types)
    return list(out.items())


def _review_like(kind):
    """An entry type that names a review but is not one of the table's review types: no record satisfies it (fail
    closed; reading of governor-spec.md section 4 rule 3, "if it lists none, no record satisfies the entry")."""
    return kind.endswith('review') or kind.startswith(AI_REVIEW)


def _is_way2(r):
    """An other_model_review that qualifies (section 4 rule 3, the ai_review row): same_lineage_review, two models that
    differ, and a decision of the decision agent (decision_ref, required by check_record for this type)."""
    m = r.get('models')
    return (r['source_class'] == 'same_lineage_review' and r.get('evidence_type') == 'other_model_review'
            and isinstance(m, dict) and m.get('reviewer') != m.get('implementer') and _text(r.get('decision_ref')))


def _is_da_review(r, stands_for):
    """A decision_agent_review that stands for the entry: recorded by the decision agent (reading: its source class
    decision_agent), with a basis and a decision_ref (both required by check_record for it)."""
    return (r['source_class'] == 'decision_agent' and r.get('evidence_type') == 'decision_agent_review'
            and r.get('stands_for') == stands_for and 'basis' in r and _text(r.get('decision_ref')))


def _candidate(r, kind, inputs):
    """Whether the record is of a kind that the table lets satisfy an entry of this type, apart from its outcome
    (governor-spec.md section 4 rule 3). Not used for the cross-model entry, which only a pair satisfies."""
    cls, et = r['source_class'], r.get('evidence_type')
    delegated = inputs['delegation_in_force']
    if kind in HUMAN_TYPES:
        if cls == 'human_authority' and et == kind:
            return True
        return delegated and not inputs['owner_kept_act'] and _is_da_review(r, kind)
    if kind == AI_REVIEW:
        return delegated and _is_way2(r)
    if _review_like(kind):
        return False
    return cls == CI and et == kind


def _entry(dimension, kind, current, inputs, reserved):
    """The satisfying record ids and the failed candidate ids of one entry."""
    rs = [r for r in current if r.get('dimension') == dimension]
    if kind == CROSS_MODEL:
        if not (inputs['delegation_in_force'] and inputs['risk'] in ('high', 'critical')):
            return [], []
        way2 = [r for r in rs if _is_way2(r)]
        da = [r for r in rs if _is_da_review(r, CROSS_MODEL)]
        failed = [r['record_id'] for r in way2 + da if r.get('outcome') == 'fail']
        w = sorted(r['record_id'] for r in way2 if r.get('outcome') == 'pass')
        d = sorted(r['record_id'] for r in da if r.get('outcome') == 'pass')
        if w and d:
            reserved.add(w[0])
            return [w[0], d[0]], failed
        return [], failed
    cands = [r for r in rs if _candidate(r, kind, inputs) and r['record_id'] not in reserved]
    sat = sorted(r['record_id'] for r in cands if r.get('outcome') == 'pass')
    failed = sorted(r['record_id'] for r in cands if r.get('outcome') == 'fail')
    return sat, failed


# ---------------------------------------------------------------------------------------------------------------
# Records: subject, use, binding, blocking (governor-spec.md section 4 rules 2, 4, 5 and 6)

def _sort_records(task, request, recs):
    """Splits the records: blocking ones (any class, also unused or stale ones, rule 4), approvals (authority
    records), current observations, stale ids, and the uncovered notes. A record of another task is left out
    (reading); a record whose subject cannot be read still blocks (fail closed)."""
    blocking, approvals, current, stale, notes = [], [], [], [], []
    commit, versions = request['evaluated_commit'], request['intent_versions']
    for n, r in enumerate(recs, 1):
        rid = r.get('record_id') if isinstance(r, dict) else None
        label = rid if _text(rid) else 'record %d' % n
        if isinstance(r, dict) and isinstance(r.get('subject'), str) and r['subject'] != '' and r['subject'] != task:
            notes.append('%s: about another subject, not read' % label)
            continue
        findings = record_forms.check_record(r)
        if isinstance(r, dict) and r.get('outcome') == 'blocking':
            kind = r.get('blocking_kind')
            blocking.append((label, kind if kind in record_forms.BLOCKING_KINDS else 'other'))
            if findings:
                notes.append('%s: blocking, and not otherwise used: %s' % (label, findings[0].rule))
            continue
        if findings:
            notes.append('%s: not used: %s' % (label, findings[0].rule))
            continue
        if not _text(rid):
            # A record id that UTF-8 cannot encode cannot be written into the decision record (reading).
            notes.append('%s: not used: its record_id cannot be written' % label)
            continue
        if r['fact_kind'] == 'authority':
            approvals.append(r)
            continue
        if 'evidence_type' not in r and 'gate' not in r:
            notes.append('%s: not used: no evidence type or gate' % label)
            continue
        if 'commit' not in r or 'intent_versions' not in r:
            notes.append('%s: not used: no commit binding' % label)
            continue
        # Rule 2 (AC3): bound to the evaluated commit and to the request's version of every entity it names; an
        # entity the request does not name has no current version here, so the record is stale (reading).
        if r['commit'] != commit or any(versions.get(k) != v for k, v in r['intent_versions'].items()):
            stale.append(rid)
            continue
        if r['fact_kind'] != 'observation':
            # Only an observation proves an evidence type (governor-spec.md section 3.3; reading).
            notes.append('%s: not used: a %s, not an observation' % (label, r['fact_kind']))
            continue
        current.append(r)
    return blocking, approvals, current, sorted(set(stale)), notes


def _approval(task, request, inputs, approvals, notes):
    """The approval record that counts (rule 5), or None: an authority record bound to the task's current content
    hash, from human_authority, or from decision_agent with a decision_ref while the delegation is in force and neither
    the owner-kept act nor weakens-evidence is set (reading of "recorded decided by: decision agent (A41, A51)").
    The owner's own approval is cited before the decision agent's."""
    counted = []
    for r in approvals:
        b = r.get('approval_binding')
        if not (isinstance(b, dict) and b.get('kind') == 'acceptance' and b.get('hash') == request['task_content_hash']):
            notes.append('%s: an approval not bound to this task\'s content hash' % r['record_id'])
            continue
        if r['source_class'] == 'human_authority':
            counted.append((0, r['record_id']))
        elif r['source_class'] == 'decision_agent':
            if not inputs['delegation_in_force']:
                notes.append('%s: a delegated approval while the delegation is not in force' % r['record_id'])
            elif inputs['owner_kept_act'] or inputs['weakens_evidence']:
                notes.append('%s: a delegated approval where only the owner\'s counts' % r['record_id'])
            elif _text(r.get('decision_ref')):
                counted.append((1, r['record_id']))
        else:
            notes.append('%s: an approval from a class that cannot approve' % r['record_id'])
    if not counted:
        return None, False
    first = sorted(counted)[0]
    return first[1], first[0] == 1


# ---------------------------------------------------------------------------------------------------------------
# Evaluation (governor-spec.md section 5; AC7)

def _next_after_rework(request):
    rc = request['retry_count']
    return 'ESCALATED' if rc['used'] >= rc['limit'] else 'REWORK'


def evaluate(request, inputs, records):
    """One acceptance decision record for the request, the inputs and the records (AC1 to AC8). Raises ValueError for
    a request that is not an object or has no task id of the form TASK-<digits>, because no record can name its
    subject (reading; decision D-221 E2)."""
    if not isinstance(request, dict) or not _full(_TASK, request.get('task_id')):
        raise ValueError('the request has no task id of the form TASK-<digits>')
    task = request['task_id']
    errors = _request_errors(request) + _inputs_errors(inputs) + _records_errors(records)
    if errors:
        return _error_record(task, request, inputs, '; '.join(errors))

    blocking, approvals, current, stale, notes = _sort_records(task, request, records)

    plan = ['G0'] + [g for g in inputs['verification_plan'] if g != 'G0']  # G0 is always a gate (section 3.2)
    plan = [g for i, g in enumerate(plan) if g not in plan[:i]]
    gate_results = [r for r in current if 'gate' in r and r['source_class'] == CI]  # (reading: CI results only)
    passed = {r['gate'] for r in gate_results if r.get('outcome') == 'pass'}
    failed_gates = sorted({r['gate'] for r in gate_results if r.get('outcome') == 'fail'})
    missing_gates = [g for g in plan if g not in passed]

    profile_used, failed_records, rests = [], [], []
    by_id = {r['record_id']: r for r in current}
    for dimension, kinds in _join(inputs['evidence_profile'], inputs['applicable_articles']):
        reserved = set()
        order = [k for k in kinds if k == CROSS_MODEL] + [k for k in kinds if k != CROSS_MODEL]
        sat, missing = {}, []
        for kind in order:
            ids, failed = _entry(dimension, kind, current, inputs, reserved)
            failed_records.extend(failed)
            if ids:
                sat[kind] = ids
            else:
                missing.append(kind)
        for kind in kinds:
            if kind in sat:
                if all(by_id[i].get('evidence_type') in REVIEW_RECORD_TYPES for i in sat[kind]):
                    rests.append({'dimension': dimension, 'evidence_type': kind})
        profile_used.append({
            'dimension': dimension,
            'required': list(kinds),
            'satisfied_by': sorted({i for ids in sat.values() for i in ids}),
            'missing_types': [k for k in kinds if k in missing],
        })

    row_1 = [label for label, kind in blocking if kind in ROW_1_KINDS]
    other_blocking = [label for label, kind in blocking if kind not in ROW_1_KINDS]
    missing_any = any(item['missing_types'] for item in profile_used)
    re_evaluating = request['task_state'] == 'IN_REVIEW'

    approval_record, ai_approval = None, False
    if row_1:
        decision, state, row = 'REJECT', 'REJECTED', 1
    elif other_blocking or failed_gates or failed_records:
        decision, state, row = 'NEEDS_REWORK', _next_after_rework(request), 2
    elif missing_gates or missing_any:
        decision, row = 'INSUFFICIENT_EVIDENCE', 3
        missing_kinds = [k for item in profile_used for k in item['missing_types']]
        human_only = not missing_gates and all(k in HUMAN_TYPES for k in missing_kinds)
        state = 'IN_REVIEW' if human_only else _next_after_rework(request)
    elif inputs['auto_accept'] and LEVEL_AT_LEAST_L2 and not re_evaluating:
        decision, state, row = 'ACCEPT', 'ACCEPTED', 4  # never reached now (AC12)
    else:
        decision, state, row = 'NEEDS_REVIEW', 'IN_REVIEW', 5
        if re_evaluating:
            # Leaving IN_REVIEW: rows 1 to 3 did not apply; an approval that counts makes the next state ACCEPTED.
            approval_record, ai_approval = _approval(task, request, inputs, approvals, notes)
            if approval_record is not None:
                state = 'ACCEPTED'

    rec = _base(task, request, inputs)
    rec.update({
        'decision': decision,
        'next_task_state': state,
        'table_row': row,
        'task_content_hash': request['task_content_hash'],
        'evaluated_commit': request['evaluated_commit'],
        'intent_versions': dict(request['intent_versions']),
        'profile_used': profile_used,
        'missing_gates': missing_gates,
        'blocking': sorted(label for label, kind in blocking),
        'failed_gates': failed_gates,
        'reverify': stale,
        'approval_record': approval_record,
        'uncovered': list(NOTES) + notes,
        'rests_on_ai': {'entries': rests, 'approval': ai_approval},
    })
    rec['record_id'] = _record_id(rec)
    return rec


# ---------------------------------------------------------------------------------------------------------------
# Deriving the inputs of governor-spec.md section 3.2 from values (AC9)

def _segment(pattern, name):
    """One path name against one pattern name: "*" matches any part of one name; nothing else is special."""
    regex = ''.join('[^/]*' if ch == '*' else re.escape(ch) for ch in pattern)
    return re.fullmatch(regex, name) is not None


def matches(pattern, path):
    """A path against a pattern of the risk rules' section 2 point 6: "*" never crosses "/", "**" matches any sequence
    of names, and a pattern without "/" matches a file name in any folder."""
    names = path.split('/')
    if '/' not in pattern:
        return _segment(pattern, names[-1])
    parts = pattern.split('/')
    memo = {}

    def go(i, j):
        if (i, j) in memo:
            return memo[(i, j)]
        if i == len(parts):
            ok = j == len(names)
        elif parts[i] == '**':
            ok = any(go(i + 1, k) for k in range(j, len(names) + 1))
        else:
            ok = j < len(names) and _segment(parts[i], names[j]) and go(i + 1, j + 1)
        memo[(i, j)] = ok
        return ok
    return go(0, 0)


def _evaluable(patterns):
    return _texts(patterns) and len(patterns) > 0


def _hits(patterns, paths):
    """Whether any path matches; a pattern list that cannot be evaluated matches every path (fail closed)."""
    if not _evaluable(patterns):
        return True
    return any(matches(p, path) for p in patterns for path in paths)


def derive_inputs(values):
    """The inputs object of conformance-files.md section 4, derived from values only (AC9). Raises ValueError when
    ``values`` is not exactly its keys or the contract's fields or the changed paths are not in their forms. A value
    that cannot be derived is None, so that evaluate gives no decision (rules 7 and 8): the risk when a changed path
    matches no rule, the delegation when its pinned value is missing, and the profile when the risk has no default."""
    if not isinstance(values, dict) or set(values) != VALUE_KEYS:
        raise ValueError('the values are not exactly the keys of derive_inputs')
    contract, paths = values['contract'], values['changed_paths']
    if not isinstance(contract, dict) or set(contract) != CONTRACT_KEYS:
        raise ValueError('the contract is not exactly its declared fields')
    if not (_texts(paths) and paths):
        raise ValueError('the changed paths are not a non-empty list of paths')
    if not (_texts(contract['traces_to']) and _texts(contract['verification_plan'])):
        raise ValueError('the contract\'s traces_to or verification_plan is malformed')

    # Risk (rule 8; risk rules section 2): the highest class a matching rule gives; a path that no rule matches
    # gives no class; a rule that cannot be evaluated matches every path, and one whose class cannot be read gives
    # critical (fail closed; reading); a higher declared risk is used, a lower one never.
    rules = values['risk_rules'] if isinstance(values['risk_rules'], list) else [None]
    risk = None
    per_path = []
    for path in paths:
        best = None
        for rule in rules:
            ok = isinstance(rule, dict) and _evaluable(rule.get('match'))
            if ok and not any(matches(p, path) for p in rule['match']):
                continue
            cls = rule.get('class') if isinstance(rule, dict) and rule.get('class') in RISKS else 'critical'
            best = cls if best is None or RISKS.index(cls) > RISKS.index(best) else best
        per_path.append(best)
    if all(c is not None for c in per_path):
        risk = max(per_path, key=RISKS.index)
        declared = contract['risk']
        if declared in RISKS and RISKS.index(declared) > RISKS.index(risk):
            risk = declared

    # The owner-kept act (section 3.2): declared, or a path rule matches, or a rule cannot be evaluated.
    kept = contract['owner_kept_act'] is not False
    okr = values['owner_kept_rules'] if isinstance(values['owner_kept_rules'], list) else [None]
    for rule in okr:
        if not isinstance(rule, dict) or _hits(rule.get('match'), paths):
            kept = True

    # Weakens evidence (section 3.2): set unless a comparison is given and says it weakens nothing.
    comp = values['evidence_comparison']
    weakens = not (isinstance(comp, dict) and set(comp) == {'weakens'} and comp['weakens'] is False)

    delegation = values['delegation'] if isinstance(values['delegation'], bool) else None

    # The applicable articles: those whose scope meets a changed path; a scope that cannot be evaluated applies.
    applicable = []
    arts = values['articles'] if isinstance(values['articles'], list) else []
    for art in arts:
        if not (isinstance(art, dict) and _text(art.get('id')) and _texts(art.get('evidence_required'))):
            raise ValueError('an article is not {id, scope, evidence_required}')
        if _hits(art.get('scope'), paths):
            applicable.append({'id': art['id'], 'evidence_required': list(art['evidence_required'])})

    # The evidence profile: the risk's default, with each traced requirement's added entries; the articles join it.
    profile = None
    defaults = values['default_profiles'] if isinstance(values['default_profiles'], dict) else {}
    if risk is not None and _profile_form(defaults.get(risk)):
        entries = [dict(e, evidence_types=list(e['evidence_types'])) for e in defaults[risk]]
        reqs = values['requirement_profiles'] if isinstance(values['requirement_profiles'], list) else []
        for req in reqs:
            if not (isinstance(req, dict) and set(req) == {'id', 'add'} and _profile_form(req['add'])):
                raise ValueError('a requirement profile is not {id, add}')
            if req['id'] in contract['traces_to']:
                entries.extend(dict(e, evidence_types=list(e['evidence_types'])) for e in req['add'])
        profile = [{'dimension': d, 'evidence_types': t} for d, t in _join(entries, applicable)]

    plan = ['G0'] + [g for g in contract['verification_plan'] if g != 'G0']
    allow = values['auto_accept'] if isinstance(values['auto_accept'], dict) else {}
    return {
        'traces_to': list(contract['traces_to']),
        'risk': risk,
        'owner_kept_act': kept,
        'weakens_evidence': weakens,
        'delegation_in_force': delegation,
        'auto_accept': risk is not None and allow.get(risk) is True,
        'verification_plan': [g for i, g in enumerate(plan) if g not in plan[:i]],
        'evidence_profile': profile,
        'applicable_articles': applicable,
        'policy_version': values['policy_version'],
        'level_version': values['level_version'],
        'ruleset_version': values['ruleset_version'],
    }
