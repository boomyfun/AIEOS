"""The AC coverage check of gov-AIEOS (task TASK-021; specification 4 revision 3, section 6 item 1; concept line 730:
every acceptance criterion maps to evidence).

``check`` takes one task contract as values (specification 2 section 5.1: its ``acceptance_criteria``,
``verification_plan`` and ``constitution``) and returns the findings of section 6 item 1: each AC id that no gate's
``args`` names ("uncovered"), an empty ``acceptance_criteria`` list ("no_acceptance_criteria"), and each ``args``
entry that is neither an AC id of the contract nor an article id of its own ``constitution`` list ("stray_arg"; the
article allowance is a reading of the specification's proposed text, TASK-021 R1). A contract whose three fields are
not in their forms gives one "malformed" finding and nothing else (fail closed).

``coverage_record`` returns, when there are findings, the one record of specification 2 section 6.2 that section 6
item 1 names: an observation with outcome blocking and blocking_kind other, one per contract version (specification 4
section 10). It returns the record; it writes and appends nothing.

Limits (TASK-021 AC7 and AC9):
- The module decides no acceptance and no execution and refuses no approval. It settles neither how a corrected
  contract clears such a record nor whether the governor should name an uncovered AC as a missing gate result
  (DEF-0042 point 7; specification 4 section 12 item 7).
- The mapping is by AC id at gate level only; test-to-AC (section 6 item 2) and a record key for the ACs a gate
  covers (item 3; DEF-0042 point 8) are not here. There is no caller in the core and no reader of contract files.
- It reads no file, no clock and no environment, and makes no process, network or model call (INV-001 to INV-003).
"""

import hashlib
import re

from aieos_bootstrap import records

KINDS = ('malformed', 'no_acceptance_criteria', 'uncovered', 'stray_arg')
SOURCE_CLASSES = ('deterministic_tool_local', 'deterministic_tool_external_ci')
_AC = re.compile(r'AC[0-9]+[a-z]?')
_GATE = re.compile(r'G[0-9]+')
_TASK = re.compile(r'TASK-[0-9]+')
_VERSION = re.compile(r'v[0-9]+')


def _text(value):
    return isinstance(value, str) and value != ''


def _full(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _finding(kind, ref, detail):
    return {'kind': kind, 'ref': ref, 'detail': detail}


def _form(contract):
    """The first form of AC1 that fails, as a malformed finding, or None."""
    if not isinstance(contract, dict):
        return _finding('malformed', 'contract', 'the contract is not a mapping')
    for key in ('acceptance_criteria', 'verification_plan', 'constitution'):
        if key not in contract:
            return _finding('malformed', key, 'the contract lacks %s' % key)
    acs = contract['acceptance_criteria']
    if not isinstance(acs, list):
        return _finding('malformed', 'acceptance_criteria', 'acceptance_criteria is not a list')
    seen = set()
    for item in acs:
        if not (isinstance(item, dict) and len(item) == 1):
            return _finding('malformed', 'acceptance_criteria', 'an entry is not a one-entry mapping')
        (ac, text), = item.items()
        if not _full(_AC, ac) or not _text(text):
            return _finding('malformed', 'acceptance_criteria', 'an entry is not an AC id with a non-empty text')
        if ac in seen:
            return _finding('malformed', ac, 'the AC id %s is repeated' % ac)
        seen.add(ac)
    plan = contract['verification_plan']
    if not isinstance(plan, list):
        return _finding('malformed', 'verification_plan', 'verification_plan is not a list')
    for gate in plan:
        if not (isinstance(gate, dict) and set(gate) in ({'gate', 'check'}, {'gate', 'check', 'args'})):
            return _finding('malformed', 'verification_plan', 'a gate is not a mapping of gate, check and optional args')
        if not _full(_GATE, gate['gate']) or not _text(gate['check']):
            return _finding('malformed', 'verification_plan', 'a gate has no gate id G<digits> or no check')
        if 'args' in gate and not (isinstance(gate['args'], list) and all(_text(a) for a in gate['args'])):
            return _finding('malformed', 'verification_plan', 'a gate\'s args is not a list of non-empty strings')
    const = contract['constitution']
    if not (isinstance(const, list) and all(_text(a) for a in const)):
        return _finding('malformed', 'constitution', 'constitution is not a list of non-empty strings')
    return None


def check(contract):
    """The findings of specification 4 section 6 item 1 for one contract (TASK-021 AC1 to AC5), in a fixed order:
    no_acceptance_criteria, then uncovered in the order of acceptance_criteria, then stray_arg in plan and args order.
    A malformed contract gives exactly one malformed finding. The input is not changed."""
    bad = _form(contract)
    if bad is not None:
        return [bad]
    acs = [next(iter(item)) for item in contract['acceptance_criteria']]
    plan = contract['verification_plan']
    const = set(contract['constitution'])
    findings = []
    if not acs:
        findings.append(_finding('no_acceptance_criteria', 'acceptance_criteria', 'the contract has no acceptance criteria'))
    named = {a for gate in plan for a in gate.get('args', [])}
    for ac in acs:
        if ac not in named:
            findings.append(_finding('uncovered', ac, '%s is named by no gate of the verification plan' % ac))
    known = set(acs) | const
    reported = set()
    for gate in plan:
        for a in gate.get('args', []):
            if a not in known and a not in reported:
                reported.add(a)
                findings.append(_finding('stray_arg', a, '%s in the args of %s is neither an AC of the contract nor an '
                                                           'article of its constitution list' % (a, gate['gate'])))
    return findings


def coverage_record(task_id, contract_version, findings, recorder, source_class):
    """The one blocking record for a contract version's findings, or None when there are none (TASK-021 AC6). It is
    returned, never written. Raises ValueError for an argument out of its form."""
    if not _full(_TASK, task_id):
        raise ValueError('task_id is not TASK- followed by digits')
    if not _full(_VERSION, contract_version):
        raise ValueError('contract_version is not v followed by digits')
    if not _text(recorder):
        raise ValueError('recorder is not a non-empty string')
    if source_class not in SOURCE_CLASSES:
        raise ValueError('source_class is not deterministic_tool_local or deterministic_tool_external_ci')
    if not isinstance(findings, list):
        raise ValueError('findings is not a list')
    if not findings:
        return None
    record_id = hashlib.sha256('\n'.join(('ac-coverage', task_id, contract_version)).encode('utf-8')).hexdigest()
    record = {'record_id': record_id, 'fact_kind': 'observation', 'source_class': source_class, 'recorder': recorder,
              'subject': task_id, 'evidence_type': 'ac_coverage', 'outcome': 'blocking', 'blocking_kind': 'other'}
    if records.check_record(record):
        raise ValueError('the record is not in the form of specification 2 section 6.2')
    return record
