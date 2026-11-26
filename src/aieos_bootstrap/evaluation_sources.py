"""The loader of the evaluation sources (task TASK-158; BT3b-2c-1 of DEF-0136 and DEF-0152; decisions D-7059 to D-7078).

Three public functions. The module starts no process of its own, opens no file, reads no clock, no environment and no
network, and writes nothing. It reads the repository only through base_files.read_file, through base_inputs.contract_at
and through the two helpers of evaluation that evaluate_task uses for the task's change (evaluation._task_commits and
evaluation._changed_paths, and evaluation._Stop which they raise); the seam read (default gitread.run) is passed to all
of them.

load_sources(repo, policy_ref, evaluated_commit, task_id, ci_logs, read=None, max_commits=1000) returns a mapping with
exactly the keys result, sources, changed_paths, provenance and findings. result is present or refused. On present:
sources holds exactly the twelve keys of eval_inputs, in the order of eval_inputs._GAPS; changed_paths is the sorted list
without duplicate of the task's change at evaluated_commit; provenance lists the facts that only the loader knows (the
path, the commit, the blob id and the sha256 of the UTF-8 bytes of each of the three files read at policy_ref, then the
pin, then the SHA-256 of the contract with the evaluated commit, then, when the versions are mapped, the same four facts
of the decision matrix and of each traced file in sorted path order, and last the note on intent_versions); findings is
[]. The source intent_versions is the map that intent_map.map_intent_versions gives for the entities of the contract, or
None when the contract names no entity: an open gap that eval_inputs refuses, which a result present does not close
(DEF-0156). On refused: sources and changed_paths are None, provenance is [] and findings is exactly ONE {reason,
detail}; the answer is never partial. The reasons are a closed set: argument, read, policy, rules, pin, governor, git,
contract, intent, plain. The order of the checks is: the arguments; the three reads (the policy file, the risk-rules
file, governor.py); the parse of the policy; policy_version and risk_rules; level_version; the pin; ruleset_version; the
task's change; evidence_comparison; the contract; its intent entities. The first refusal ends these steps. Every answer,
present or refused, is then checked once with evaluation_derive.plain_data_problem; a finding there gives a refusal with
the reason plain (that refusal is not checked again).

The contract is read at evaluated_commit by base_inputs.contract_at (a refusal there: reason contract). Its
input_state.intent_versions names each entity by its file's path with the SHA-256 of its bytes. An absent input_state, or
one without intent_versions, or an empty one, leaves the source None; an input_state or an intent_versions of another
type than a mapping, and more than 100 entities, are refused. Otherwise docs/pre-genesis/decision-matrix.md is read at
policy_ref, intent_map.map_intent_versions gives the versions from its text, and each traced file is then read at
policy_ref and must hash to the value of the contract, else it is stale. Every failure of these steps is a refusal with
the reason intent. The contract's SHA-256 is not compared here with the one that its task approval records.

The three files are read at policy_ref: docs/specs/evaluation-policy-gov-aieos.md gives owner_kept_rules, articles,
default_profiles, requirement_profiles, delegation and auto_accept (requirement_profiles comes from this file only);
the risk-rules file gives policy_version (the one line of the section 3 block) and risk_rules, passed on in the form
scope_reconcile.rules_from_policy gives them, {match, class}; a rule out of form (a refused rule), and an empty list,
refuse the whole read. governor.py gives ruleset_version by evaluation_derive.ruleset_version, checked against the pin.
For these three files a missing file and a refused read are ONE refusal, reason read.

F1, by name: evaluation_derive.plain_data_problem assumes tree-shaped input; it keeps no identity of the containers it
walks. This module meets that by construction: every value it passes on is a fresh result of a text parser, never a
container that a caller gave or that two sources share. One exception: rules_from_policy copies its refused rule with a
shallow copy, so such copies share one list; no such copy is passed on, because a refused rule refuses the read.
F2 is carried, not fixed here: line 4 of the docstring of evaluation_derive.py is false when read literally.

pinned_governor(ci_logs) returns {value, findings}: the pinned hash of governor.py that the CI printed as the echo of the
job environment, in the saved logs of gh run view --log (job TAB step TAB timestamp and message). Every log must be in
that form, must hold a line of the job checks whose message is exactly two spaces, the name, a colon, a space and
64 lowercase hex characters, and every such line of every log must give the same hex. The step is not checked; the
logs of the runs of the evaluated commit are chosen by the caller.

parse_json(text) returns {value, findings}: a pure parser of JSON text that refuses NaN, Infinity, -Infinity, a repeated
key in one object and anything evaluation_derive.plain_data_problem refuses; a decoded key or string that holds a lone
surrogate, which UTF-8 cannot write, is refused with the reason plain.

No function raises an Exception; an Exception inside the walk of the task's change is a refusal with the reason git.
"""
import hashlib
import json
import re

from aieos_bootstrap import base_files
from aieos_bootstrap import base_inputs
from aieos_bootstrap import evaluation
from aieos_bootstrap import evaluation_derive
from aieos_bootstrap import evaluation_policy
from aieos_bootstrap import gitread
from aieos_bootstrap import intent_map
from aieos_bootstrap import scope_reconcile

POLICY_PATH = 'docs/specs/evaluation-policy-gov-aieos.md'
RISK_PATH = scope_reconcile.POLICY_PATH
GOVERNOR_PATH = 'src/aieos_bootstrap/governor.py'
DM_PATH = 'docs/pre-genesis/decision-matrix.md'
JOB = 'checks'
_MAX_ENTITIES = 100
_COMMIT = re.compile(r'[0-9a-f]{40}')
_TASK = re.compile(r'TASK-[0-9]+')
_STAMP = re.compile('\ufeff?[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:[.][0-9]+)?Z(?: (.*))?', re.S)
_PIN_MESSAGE = re.compile(r'  AIEOS_PINNED_GOVERNOR: ([0-9a-f]{64})')
_VERSION_LINE = re.compile(r'policy_version: (\S+)')
_RISKS = ('low', 'medium', 'high', 'critical')
_SOURCES = ('intent_versions', 'owner_kept_rules', 'articles', 'default_profiles', 'requirement_profiles',
            'evidence_comparison', 'delegation', 'auto_accept', 'level_version', 'ruleset_version', 'policy_version',
            'risk_rules')
_POLICY_KEYS = ('owner_kept_rules', 'articles', 'default_profiles', 'requirement_profiles', 'delegation', 'auto_accept')
_MAX_DETAIL = 200


class _Refuse(Exception):
    """A refusal found inside a step: its reason and detail (not a ValueError, so no handler for one takes it)."""

    def __init__(self, reason, detail):
        Exception.__init__(self, reason)
        self.reason = reason
        self.detail = str(detail)[:_MAX_DETAIL]


class _Reject(Exception):
    """A refusal raised by a hook of the JSON parser: its reason (not a ValueError, so json's own handler never takes it)."""

    def __init__(self, reason):
        Exception.__init__(self, reason)
        self.reason = reason


def _refused(reason, detail):
    return {'result': 'refused', 'sources': None, 'changed_paths': None, 'provenance': [],
            'findings': [{'reason': reason, 'detail': str(detail)[:_MAX_DETAIL]}]}


def _argument_error(repo, policy_ref, evaluated_commit, task_id, ci_logs, read, max_commits):
    """The first malformed argument as a short text, or None."""
    if type(policy_ref) is not str or _COMMIT.fullmatch(policy_ref) is None:
        return 'policy_ref is not 40 lowercase hexadecimal characters'
    if type(evaluated_commit) is not str or _COMMIT.fullmatch(evaluated_commit) is None:
        return 'evaluated_commit is not 40 lowercase hexadecimal characters'
    if policy_ref == evaluated_commit:
        return 'policy_ref equals evaluated_commit'
    if type(task_id) is not str or _TASK.fullmatch(task_id) is None:
        return 'task_id is not TASK- and digits'
    if type(ci_logs) is not list or any(type(log) is not str for log in ci_logs):
        return 'ci_logs is not a list of texts'
    if read is not None and not callable(read):
        return 'read is not callable'
    if type(max_commits) is not int or not 1 <= max_commits <= 10000:
        return 'max_commits is not an int from 1 to 10000'
    why = gitread.form_error(repo, ['rev-parse', '--verify', '--end-of-options', policy_ref], base_files.TIMEOUT)
    if why is not None:
        return 'repo: ' + why
    return None


def _read(repo, policy_ref, path, read, provenance):
    """The text of one file at policy_ref, or a refusal; the provenance entry is added."""
    value, findings = base_files.read_file(repo, policy_ref, path, read)
    if value is None:
        raise _Refuse('read', findings[0] if findings else path + ' was not read')
    text = value['text']
    provenance.append({'path': path, 'commit': policy_ref, 'blob': value['blob'],
                       'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest()})
    return text


def _rule_in_form(rule):
    return (type(rule) is dict and set(rule) == {'match', 'class'} and rule['class'] in _RISKS
            and type(rule['match']) is list and bool(rule['match']) and all(type(m) is str for m in rule['match']))


def _risk_sources(text):
    """policy_version and risk_rules from the text of the risk-rules file."""
    block = scope_reconcile.policy_block(text)
    if block is None:
        raise _Refuse('rules', 'the risk-rules file has no section 3 block')
    versions = [m.group(1) for m in (_VERSION_LINE.fullmatch(line) for line in block) if m is not None]
    if len(versions) != 1:
        raise _Refuse('rules', 'the block has %d policy_version lines, not one' % len(versions))
    rules = scope_reconcile.rules_from_policy(text)
    if type(rules) is not list or not rules:
        raise _Refuse('rules', 'the risk rules are an empty list')
    for n, rule in enumerate(rules, 1):
        if not _rule_in_form(rule):
            raise _Refuse('rules', 'risk rule %d is refused' % n)
    return versions[0], rules


def _walk(repo, task_id, evaluated_commit, read, max_commits):
    """The sorted list without duplicate of the task's change, by the helpers that evaluate_task uses."""
    run = gitread.run if read is None else read
    try:
        commits = evaluation._task_commits(run, repo, task_id, evaluated_commit, max_commits)
        return evaluation._changed_paths(run, repo, commits)
    except evaluation._Stop as stop:
        raise _Refuse('git', stop.findings[0] if stop.findings else stop.reason)
    except Exception as exc:
        raise _Refuse('git', 'git: ' + type(exc).__name__)


def _intent_read(repo, policy_ref, path, read, provenance):
    """_read, its refusal given the reason intent."""
    try:
        return _read(repo, policy_ref, path, read, provenance)
    except _Refuse as refusal:
        raise _Refuse('intent', refusal.detail)


def _intent(repo, policy_ref, evaluated_commit, task_id, read, provenance):
    """The source intent_versions and its note: the mapped versions of the contract's entities, or None for a contract that
    names none; the provenance entries of the contract and of every file read are added."""
    value, findings = base_inputs.contract_at(repo, evaluated_commit, task_id, read)
    if value is None:
        raise _Refuse('contract', findings[0])
    contract, digest = value
    provenance.append({'contract': digest, 'commit': evaluated_commit})
    gap = {'source': 'intent_versions', 'state': 'open gap: the contract names no entity'}
    if 'input_state' not in contract:
        return None, gap
    state = contract['input_state']
    if type(state) is not dict:
        raise _Refuse('intent', 'input_state is not a mapping')
    if 'intent_versions' not in state or state['intent_versions'] == {}:
        return None, gap
    entities = state['intent_versions']
    if type(entities) is not dict:
        raise _Refuse('intent', 'intent_versions is not a mapping')
    if len(entities) > _MAX_ENTITIES:
        raise _Refuse('intent', 'intent_versions names over %d entities' % _MAX_ENTITIES)
    dm_text = _intent_read(repo, policy_ref, DM_PATH, read, provenance)
    answer = intent_map.map_intent_versions(entities, dm_text)
    if answer['value'] is None:
        finding = answer['findings'][0]
        raise _Refuse('intent', '%s: %s' % (finding['reason'], finding['detail']))
    for path in sorted(entities):
        text = _intent_read(repo, policy_ref, path, read, provenance)
        if hashlib.sha256(text.encode('utf-8')).hexdigest() != entities[path]:
            raise _Refuse('intent', 'stale: the bytes at policy_ref differ from the contract: ' + path)
    note = {'source': 'intent_versions', 'state': 'mapped', 'versions': dict(answer['value'])}
    return dict(answer['value']), note


def _load(repo, policy_ref, evaluated_commit, task_id, ci_logs, read, max_commits):
    why = _argument_error(repo, policy_ref, evaluated_commit, task_id, ci_logs, read, max_commits)
    if why is not None:
        raise _Refuse('argument', why)
    provenance = []
    policy_text = _read(repo, policy_ref, POLICY_PATH, read, provenance)
    risk_text = _read(repo, policy_ref, RISK_PATH, read, provenance)
    governor_text = _read(repo, policy_ref, GOVERNOR_PATH, read, provenance)
    parsed = evaluation_policy.read_evaluation_policy(policy_text)
    if parsed['result'] != 'present':
        finding = parsed['findings'][0]
        line = 'none' if finding['line'] is None else finding['line']
        raise _Refuse('policy', 'policy: %s line %s' % (finding['reason'], line))
    policy_version, risk_rules = _risk_sources(risk_text)
    level = evaluation_derive.level_version(policy_version)
    if level['value'] is None:
        raise _Refuse('rules', level['findings'][0]['detail'])
    pin = pinned_governor(ci_logs)
    if pin['value'] is None:
        raise _Refuse('pin', pin['findings'][0]['detail'])
    ruleset = evaluation_derive.ruleset_version(governor_text.encode('utf-8'), pin['value'])
    if ruleset['value'] is None:
        finding = ruleset['findings'][0]
        raise _Refuse('governor', finding['detail'])
    paths = _walk(repo, task_id, evaluated_commit, read, max_commits)
    sources = {'intent_versions': None}
    for key in _POLICY_KEYS:
        sources[key] = parsed['sources'][key]
    sources['evidence_comparison'] = evaluation_derive.evidence_comparison(paths)
    sources['level_version'] = level['value']
    sources['ruleset_version'] = ruleset['value']
    sources['policy_version'] = policy_version
    sources['risk_rules'] = risk_rules
    provenance.append({'pin': 'ci_log', 'value': pin['value'], 'logs': len(ci_logs)})
    sources['intent_versions'], note = _intent(repo, policy_ref, evaluated_commit, task_id, read, provenance)
    provenance.append(note)
    ordered = {key: sources[key] for key in _SOURCES}
    return {'result': 'present', 'sources': ordered, 'changed_paths': paths, 'provenance': provenance, 'findings': []}


def load_sources(repo, policy_ref, evaluated_commit, task_id, ci_logs, read=None, max_commits=1000):
    try:
        try:
            answer = _load(repo, policy_ref, evaluated_commit, task_id, ci_logs, read, max_commits)
        except _Refuse as refusal:
            answer = _refused(refusal.reason, refusal.detail)
        except Exception as exc:
            answer = _refused('argument', 'an unexpected error: ' + type(exc).__name__)
        problem = evaluation_derive.plain_data_problem(answer)
        if problem is not None:
            return _refused('plain', problem['detail'])
        return answer
    except Exception as exc:
        return _refused('argument', 'an unexpected error: ' + type(exc).__name__)


def _pin_refused(detail):
    return {'value': None, 'findings': [{'reason': 'pin', 'detail': detail[:_MAX_DETAIL]}]}


def _log_pins(log, number):
    """The pin values of one log (the lines of the job checks whose message is the pin line), or a refusal text."""
    lines = log.split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]
    if not lines:
        return None, 'log %d is empty' % number
    pins = []
    seen_job = False
    for n, raw in enumerate(lines, 1):
        line = raw[:-1] if raw.endswith('\r') else raw
        parts = line.split('\t', 2)
        if len(parts) != 3:
            return None, 'log %d line %d is not job TAB step TAB text' % (number, n)
        stamp = _STAMP.fullmatch(parts[2])
        if stamp is None:
            return None, 'log %d line %d has no timestamp in the pinned form' % (number, n)
        if parts[0] != JOB:
            continue
        seen_job = True
        message = stamp.group(1)
        if message is not None:
            found = _PIN_MESSAGE.fullmatch(message)
            if found is not None:
                pins.append(found.group(1))
    if not seen_job:
        return None, 'log %d has no line of the job %s' % (number, JOB)
    if not pins:
        return None, 'log %d has no pin line' % number
    return pins, None


def pinned_governor(ci_logs):
    try:
        if type(ci_logs) is not list or not ci_logs or any(type(log) is not str for log in ci_logs):
            return _pin_refused('ci_logs is not a non-empty list of texts')
        values = set()
        for number, log in enumerate(ci_logs, 1):
            pins, why = _log_pins(log, number)
            if why is not None:
                return _pin_refused(why)
            values.update(pins)
        if len(values) != 1:
            return _pin_refused('the pin lines give %d different values' % len(values))
        return {'value': next(iter(values)), 'findings': []}
    except Exception:
        return _pin_refused('an unexpected error')


def _constant(name):
    raise _Reject('constant')


def _pairs(pairs):
    seen = set()
    for key, _ in pairs:
        if key in seen:
            raise _Reject('duplicate')
        seen.add(key)
    return dict(pairs)


def _json_refused(reason, detail):
    return {'value': None, 'findings': [{'reason': reason, 'detail': detail[:_MAX_DETAIL]}]}


def _holds_lone_surrogate(value):
    """Whether a key or a string of plain data, at any depth, cannot be written as UTF-8."""
    stack = [value]
    while stack:
        item = stack.pop()
        if type(item) is dict:
            stack.extend(item.keys())
            stack.extend(item.values())
        elif type(item) is list:
            stack.extend(item)
        elif type(item) is str:
            try:
                item.encode('utf-8')
            except UnicodeEncodeError:
                return True
    return False


def parse_json(text):
    try:
        if type(text) is not str:
            return _json_refused('argument', 'text is not a str')
        if text == '':
            return _json_refused('argument', 'text is empty')
        try:
            text.encode('utf-8')
        except UnicodeEncodeError:
            return _json_refused('argument', 'text cannot be encoded as UTF-8')
        try:
            value = json.loads(text, parse_constant=_constant, object_pairs_hook=_pairs)
        except _Reject as rejected:
            return _json_refused(rejected.reason, 'the text holds a ' + rejected.reason)
        except (ValueError, RecursionError) as exc:
            return _json_refused('json', 'json.loads gave ' + type(exc).__name__)
        problem = evaluation_derive.plain_data_problem(value)
        if problem is not None:
            return _json_refused('plain', problem['detail'])
        if _holds_lone_surrogate(value):
            return _json_refused('plain', 'a key or a string holds a lone surrogate')
        return {'value': value, 'findings': []}
    except Exception:
        return _json_refused('json', 'an unexpected error')
