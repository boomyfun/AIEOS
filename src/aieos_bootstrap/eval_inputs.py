"""The inputs of an evaluation (task TASK-152; BT3b-1 of DEF-0136 and DEF-0152; decisions D-6826 to D-6829): a pure
function that assembles, from plain data, every input of evaluation.evaluate_task that a repository file can give, and
refuses when one cannot be given (D-6606 C3: derive every input, nothing hand-typed, refuse a missing input). It starts
no process, opens no file, reads no clock, no environment and no network, holds no credential and writes nothing to the
event log: the caller reads the repository through the existing readers and passes plain data; BT3b-2 appends the
records and wires the command.

``eval_inputs(task_id, evaluated_commit, policy_ref, contract, contract_sha256, changed_paths, runs, sources,
log_payloads, recorder)`` returns a mapping with exactly the keys declared, values, ci_records, evidence and refusal.
On a refusal declared and values are None, ci_records is [], evidence is None and refusal is {reason, detail}; otherwise
refusal is None. The evidence holds policy_ref, evaluated_commit, contract_sha256, ci, uncovered (a fresh copy of the
plan entries that ci_evidence could not cover, so they are not lost; this key is added to the objective's list by
D-6836 to meet AC5), already_in_log and gaps. The reasons are a closed set: argument, gap, retries, plan, risk_rules, policy_path, ci, conflict and
incomplete. It never raises an Exception; a BaseException that is not an Exception passes through.

The checks, in order: (1) the arguments; (2) policy_path: a task whose changed paths include one of the four policy
source files is refused (a task cannot edit the rules that evaluate it); (3) the gaps: ``sources`` is a dict with exactly
the twelve keys intent_versions, owner_kept_rules, articles, default_profiles, requirement_profiles,
evidence_comparison, delegation, auto_accept, level_version, ruleset_version, policy_version and risk_rules; a value
that is None is an OPEN GAP, and any open gap gives ONE refusal, reason gap, whose detail names every open gap in that
order; the answer is never a partial mapping and a fail-closed value is never passed on; no value is typed into the
module, and fixture values in the tests are not policy; (4) retries: the text of contract autonomy budgets retries,
one to three decimal digits with no sign, no space and no leading zero (except 0), 0 to 100; this departs from D-6827
C3 (a), which named the approved contract bytes: the module reads the mapping that base_inputs.contract_at gives, whose
reader already refuses a repeated key (base_inputs.py :362-:363) and returns plain values as text (:380), decided at
D-6828; (5) plan: the gate ids are the verification_plan entries' gate values in order, each G and digits (the run-made
contracts that launcher.py writes carry mappings with gate, check and args); (6) risk_rules: the list that
scope_reconcile.rules_from_policy returns, each rule exactly {match, class}; (7) the CI records through
ci_evidence.ci_evidence, called once; (8) the guard against the records already in the log, in the order check all,
then append; (9) the completeness check: a copy of the values goes to governor.derive_inputs, and a risk, an evidence
profile or a delegation that it cannot derive is a refusal, so the values returned are never turned into no decision.

owner_kept_act reaches the module as the text true or false (the subset reader gives scalars as texts) and is converted
to the bool; evaluation.evaluate_task binds the field to the contract bytes again.

Limits: the module cannot check that the sources are the real policy; until the policy file of BT3c exists ten of the
twelve sources (all but policy_version and risk_rules, which have readers) have no producer, so no real evaluation can
pass the gap check. policy_ref is checked for its form and for being another commit than evaluated_commit; that the
files were read at that ref is the caller's. The policy-path rule is the exact text of four files. The module cannot
check that contract is the contract whose bytes hash to contract_sha256; the caller takes both from one
base_inputs.contract_at call. That reader refuses the self-build contracts of docs/tasks whose intent_versions keys
begin with a dot, so this assembler is for run-made contracts. The arguments are plain data as loaded from JSON; a
crafted subclass whose methods answer differently on each call is outside the guarantee. The CI class of the records is
asserted, not verified (ci_evidence). The run-made review gate G3 stays uncovered (DEF-0153) and is listed in
evidence.uncovered. Five sources (owner_kept_rules, evidence_comparison, auto_accept, level_version and
ruleset_version) are refused with reason argument when their form is wrong, because governor.derive_inputs would turn
such a form into a fail-closed value silently (governor.py :586-:594, :622, :191-:193).
"""
import re

from aieos_bootstrap import ci_evidence
from aieos_bootstrap import governor

_TASK = re.compile(r'TASK-[0-9]+')
_COMMIT = re.compile(r'[0-9a-f]{40}')
_SHA256 = re.compile(r'[0-9a-f]{64}')
_GATE = re.compile(r'G[0-9]+')
_RETRIES = re.compile(r'0|[1-9][0-9]{0,2}')
_RISKS = ('low', 'medium', 'high', 'critical')
_GAPS = ('intent_versions', 'owner_kept_rules', 'articles', 'default_profiles', 'requirement_profiles',
         'evidence_comparison', 'delegation', 'auto_accept', 'level_version', 'ruleset_version', 'policy_version',
         'risk_rules')
_POLICY_PATHS = ('docs/specs/risk-rules-gov-aieos.md', 'docs/pre-genesis/constitution.md',
                 'docs/pre-genesis/assurance-model.md', 'docs/pre-genesis/decision-matrix.md')
_DEPTH = 50


def _answer(declared, values, ci_records, evidence, refusal):
    return {'declared': declared, 'values': values, 'ci_records': ci_records, 'evidence': evidence,
            'refusal': refusal}


def _refuse(reason, detail):
    return _answer(None, None, [], None, {'reason': reason, 'detail': detail})


def _text(value):
    return isinstance(value, str) and value != ''


def _texts(value):
    return isinstance(value, list) and bool(value) and all(_text(v) for v in value)


def _copy(value, depth=0):
    """A fresh copy of plain data (dict with text keys, list, str, int, float, bool, None); ValueError otherwise."""
    if depth > _DEPTH:
        raise ValueError('too deep')
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [_copy(v, depth + 1) for v in value]
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError('a key is not a text')
            out[k] = _copy(v, depth + 1)
        return out
    raise ValueError('not plain data')


def _argument_error(task_id, evaluated_commit, policy_ref, contract, contract_sha256, changed_paths, runs, sources,
                    log_payloads, recorder):
    """The first malformed argument as a short text, or None."""
    if not isinstance(task_id, str) or _TASK.fullmatch(task_id) is None:
        return 'task_id is not TASK- and digits'
    if not isinstance(evaluated_commit, str) or _COMMIT.fullmatch(evaluated_commit) is None:
        return 'evaluated_commit is not 40 lowercase hexadecimal characters'
    if not isinstance(policy_ref, str) or _COMMIT.fullmatch(policy_ref) is None:
        return 'policy_ref is not 40 lowercase hexadecimal characters'
    if policy_ref == evaluated_commit:
        return 'policy_ref equals evaluated_commit'
    if not isinstance(contract, dict):
        return 'contract is not a dict'
    if not _texts(contract.get('traces_to')):
        return 'contract has no traces_to that is a non-empty list of non-empty texts'
    if contract.get('risk') not in _RISKS or not isinstance(contract.get('risk'), str):
        return 'contract has no risk of low, medium, high or critical'
    if contract.get('owner_kept_act') not in ('true', 'false') or not isinstance(contract.get('owner_kept_act'), str):
        return 'contract has no owner_kept_act that is the text true or false'
    plan = contract.get('verification_plan')
    if not isinstance(plan, list) or not plan:
        return 'contract has no verification_plan that is a non-empty list'
    autonomy = contract.get('autonomy')
    if not isinstance(autonomy, dict) or not isinstance(autonomy.get('budgets'), dict):
        return 'contract has no autonomy with a budgets dict'
    if not isinstance(contract_sha256, str) or _SHA256.fullmatch(contract_sha256) is None:
        return 'contract_sha256 is not 64 lowercase hexadecimal characters'
    if not _texts(changed_paths):
        return 'changed_paths is not a non-empty list of non-empty texts'
    if not isinstance(runs, list):
        return 'runs is not a list'
    if not isinstance(sources, dict) or set(sources) != set(_GAPS):
        return 'sources is not a dict with exactly its twelve keys'
    if not isinstance(log_payloads, list) or not all(isinstance(p, dict) for p in log_payloads):
        return 'log_payloads is not a list of dicts'
    if not _text(recorder):
        return 'recorder is not a non-empty text'
    return None


def _retries(budgets):
    """(int, None) or (None, detail)."""
    if 'retries' not in budgets:
        return None, 'budgets has no retries'
    text = budgets['retries']
    if not isinstance(text, str):
        return None, 'retries is not a text'
    if _RETRIES.fullmatch(text) is None:
        return None, 'retries is not one to three decimal digits without sign, space or leading zero'
    if int(text) > 100:
        return None, 'retries is above 100'
    return int(text), None


def _plan(plan):
    """(gate ids, None) or (None, detail)."""
    ids = []
    for entry in plan:
        if not isinstance(entry, dict):
            return None, 'a verification_plan entry is not a dict'
        gate = entry.get('gate')
        if not _text(gate):
            return None, 'a verification_plan entry has no text gate'
        if _GATE.fullmatch(gate) is None:
            return None, 'a verification_plan entry has a gate that is not G and digits'
        ids.append(gate)
    return ids, None


def _rules(rules):
    """(rules in the governor's form as copies, None) or (None, detail)."""
    if not isinstance(rules, list):
        return None, 'risk_rules is not a list'
    out = []
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != {'match', 'class'}:
            return None, 'a risk rule is not a dict with exactly the keys match and class'
        if not _texts(rule['match']):
            return None, 'a risk rule has a match that is not a non-empty list of non-empty texts'
        if not isinstance(rule['class'], str) or rule['class'] not in _RISKS:
            return None, 'a risk rule has a class that is not one of low, medium, high or critical'
        out.append({'match': list(rule['match']), 'class': rule['class']})
    return out, None


def _guard(records, log_payloads):
    """(records to append, record ids already in the log, None) or (None, None, conflicting record id)."""
    fresh, already = [], []
    for record in records:
        same = [p for p in log_payloads if p.get('record_id') == record['record_id']]
        if not same:
            fresh.append(record)
        elif all(p == record for p in same):
            already.append(record['record_id'])
        else:
            return None, None, record['record_id']
    return fresh, already, None


def eval_inputs(task_id, evaluated_commit, policy_ref, contract, contract_sha256, changed_paths, runs, sources,
                log_payloads, recorder):
    """The inputs of evaluation.evaluate_task and the CI records to append, or the refusal."""
    try:
        error = _argument_error(task_id, evaluated_commit, policy_ref, contract, contract_sha256, changed_paths, runs,
                                sources, log_payloads, recorder)
        if error is not None:
            return _refuse('argument', error)
        for path in changed_paths:
            if path in _POLICY_PATHS:
                return _refuse('policy_path', 'a changed path is a policy source: ' + path)
        open_gaps = [name for name in _GAPS if sources[name] is None]
        if open_gaps:
            return _refuse('gap', 'open gaps: ' + ', '.join(open_gaps))
        retries, detail = _retries(contract['autonomy']['budgets'])
        if detail is not None:
            return _refuse('retries', detail)
        gates, detail = _plan(contract['verification_plan'])
        if detail is not None:
            return _refuse('plan', detail)
        rules, detail = _rules(sources['risk_rules'])
        if detail is not None:
            return _refuse('risk_rules', detail)
        if not _text(sources['policy_version']):
            return _refuse('argument', 'policy_version is not a non-empty text')
        for name in ('level_version', 'ruleset_version'):
            if not _text(sources[name]):
                return _refuse('argument', name + ' is not a non-empty text')
        okr = sources['owner_kept_rules']
        if not isinstance(okr, list) or not all(isinstance(r, dict) and _texts(r.get('match')) for r in okr):
            return _refuse('argument', 'owner_kept_rules is not a list of dicts whose match is a non-empty list of '
                                       'non-empty texts')
        comp = sources['evidence_comparison']
        if not isinstance(comp, dict) or set(comp) != {'weakens'} or not isinstance(comp['weakens'], bool):
            return _refuse('argument', 'evidence_comparison is not a dict with exactly the key weakens and a bool value')
        if not isinstance(sources['auto_accept'], dict):
            return _refuse('argument', 'auto_accept is not a dict')
        try:
            copies = {name: _copy(sources[name]) for name in _GAPS}
            plan_entries = [_copy(e) for e in contract['verification_plan']]
            paths = list(changed_paths)
        except ValueError as exc:
            return _refuse('argument', 'a source or a plan entry is not plain data: ' + str(exc))
        made = ci_evidence.ci_evidence(task_id, evaluated_commit, contract_sha256, copies['intent_versions'],
                                       plan_entries, list(paths), runs, recorder)
        if made['refusal'] is not None:
            return _refuse('ci', 'ci_evidence refused: %s: %s' % (made['refusal']['reason'], made['refusal']['detail']))
        fresh, already, clash = _guard(made['records'], log_payloads)
        if clash is not None:
            return _refuse('conflict', 'the log holds another record under the record_id ' + clash)
        values = {
            'contract': {'traces_to': list(contract['traces_to']), 'risk': contract['risk'],
                         'owner_kept_act': contract['owner_kept_act'] == 'true', 'verification_plan': gates},
            'changed_paths': list(paths), 'risk_rules': rules, 'owner_kept_rules': copies['owner_kept_rules'],
            'articles': copies['articles'], 'default_profiles': copies['default_profiles'],
            'requirement_profiles': copies['requirement_profiles'],
            'evidence_comparison': copies['evidence_comparison'], 'delegation': copies['delegation'],
            'auto_accept': copies['auto_accept'], 'policy_version': copies['policy_version'],
            'level_version': copies['level_version'], 'ruleset_version': copies['ruleset_version']}
        try:
            derived = governor.derive_inputs(_copy(values))
        except ValueError as exc:
            return _refuse('incomplete', 'governor.derive_inputs refused the values: ' + str(exc))
        missing = []
        if derived['risk'] is None:
            missing.append('the risk cannot be derived')
        if derived['evidence_profile'] is None:
            missing.append('the evidence profile cannot be derived')
        if derived['delegation_in_force'] is None:
            missing.append('the delegation is not a bool')
        if missing:
            return _refuse('incomplete', 'governor.derive_inputs gives no decision: ' + '; '.join(missing))
        declared = {'intent_versions': _copy(copies['intent_versions']), 'retries': retries}
        evidence = {'policy_ref': policy_ref, 'evaluated_commit': evaluated_commit, 'contract_sha256': contract_sha256,
                    'ci': _copy(made['evidence']), 'uncovered': _copy(made['uncovered']),
                    'already_in_log': list(already), 'gaps': []}
        return _answer(declared, values, [_copy(r) for r in fresh], evidence, None)
    except Exception as exc:
        return _refuse('argument', 'an argument could not be read: ' + type(exc).__name__)
