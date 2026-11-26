"""The steps of the command ``aieos evaluate`` (task TASK-162; BT3b-2d-2b of DEF-0136 and DEF-0152; specification 7
revision 14, section 3; decisions D-7276 to D-7298). One submitted task is evaluated from the project's event log, its
contract at the evaluated commit, the saved CI data given as one JSON text and the evaluation sources at the contract's
base commit.

``evaluate(root, repo, task_id, ci_text, recorder, now, read=None, read_log=None, append=None)`` returns a mapping with
exactly the keys result, reason, findings, event_id, decision, next_task_state, manifest_sha256, manifest, appended and
uncovered. result is "evaluated", "duplicate" or "refused". reason is None unless refused, and then one of argument,
log, state, contract, ci, policy_ref, sources, inputs, manifest, append and evaluate. findings is a list of str: a
refusal of a called module is given as "<its reason>: <its detail>" or as its own finding texts; the first refusal ends
the call. appended is the list of the record ids whose appends the writer confirmed, in order.
uncovered is the uncovered list of eval_inputs' evidence, or None before that step succeeded. manifest_sha256 and
manifest are the manifest's SHA-256 and text once the manifest step succeeded, and None before. No Exception
leaves the function (an unexpected one is a refusal
with the reason of the step it happened in, naming its type); a BaseException that is not an Exception passes through.
read_log (default writer.read_log) and append (default writer.append_event) are looked up at each call; read is passed
to every Git reader.

The steps, in order. The arguments: root and repo non-empty absolute paths, task_id TASK- and digits, ci_text a str,
recorder a non-empty str, now a timezone-aware UTC datetime with whole seconds; nothing is read or written before they
pass. (1) The log is read once; the approved contract_hash, the evaluated commit and the task's record payloads come from
evaluation._task_events over those bytes (a private helper, used as evaluation_sources uses evaluation._task_commits).
(2) The contract is read at that commit by base_inputs.contract_at, and the bytes given to the evaluation are read at the
same commit through base_files.read_file at the places of contract_path.candidates; their SHA-256 must be the one
contract_at gave and the approved contract_hash. (3) The CI data is parsed by evaluation_sources.parse_json and read by
evaluation_intake.read_ci_data. (4) policy_ref is the contract's input_state.base_commit, 40 lowercase hexadecimal
characters other than the evaluated commit, and evaluation_sources.load_sources is given the logs of the runs of step 3
and no other. The loader's provenance must then hold exactly one mapping with the key contract, whose keys are
contract and commit and whose values are the SHA-256 of step 2 and the evaluated commit; anything else refuses with
reason sources and nothing is appended (task TASK-163; D-7351). With the real loader it holds by construction.
(5) eval_inputs.eval_inputs assembles the inputs. (6) evaluation_intake.manifest makes the manifest from fresh
copies of what it is given. (7) The records to append are eval_inputs' CI records and then the manifest record,
left out when the log holds an equal payload under its record_id (a different one is a refusal with nothing written);
the event id of a record is the SHA-256 of "evaluation-record", the task id and the record id joined by line feeds. Each
is first decided with eventlog.append over the log and the lines decided so far; only then is each written through append
with expected_log_sha256, the SHA-256 of the log read followed by the lines this call has appended. An exception of
append refuses with a finding that names the record and says that whether it was written is not known: the writer can
raise after the line is on disk, and the log is read once. (8)
evaluation.evaluate_task evaluates and appends the decision; it reads the log again and its append is not guarded.

The module opens no file, starts no process, reads no clock, no environment and no network, and writes only through
append and through evaluate_task's append.

Limits: nothing checks that the base commit is one that the owner or the decision agent trusts; the guard covers only the
appends of step 7, so with no record left to append step 7 calls nothing and a root without a store is not refused
there; a refusal in step 7 or 8 may leave records with no decision; the CI texts are the caller's fetch,
trusted unedited; the sources are those of gov-AIEOS, and with the sources' open gaps a task is refused at step 5.
"""
import datetime
import hashlib
import os
import re

from aieos_bootstrap import base_files
from aieos_bootstrap import base_inputs
from aieos_bootstrap import contract_path
from aieos_bootstrap import eval_inputs
from aieos_bootstrap import evaluation
from aieos_bootstrap import evaluation_intake
from aieos_bootstrap import evaluation_sources
from aieos_bootstrap import eventlog
from aieos_bootstrap import writer

RESULT_KEYS = ('result', 'reason', 'findings', 'event_id', 'decision', 'next_task_state', 'manifest_sha256',
               'manifest', 'appended', 'uncovered')
EVENT_ID_PREFIX = 'evaluation-record'
_RECORD_EVENT = 'record.added'
_OTHER_CONTRACT = "sources: the loader's contract digest or commit differs from the command's"
_TASK = re.compile(r'TASK-[0-9]+')
_COMMIT = re.compile(r'[0-9a-f]{40}')
_ZERO = datetime.timedelta(0)


class _Refuse(Exception):
    """A refusal of a step: its reason and its findings."""

    def __init__(self, reason, findings):
        Exception.__init__(self, reason)
        self.reason = reason
        self.findings = list(findings)


def _texts(findings):
    """The findings of a called module as texts: a str as it is, a mapping as "<reason>: <detail>"."""
    return [f if isinstance(f, str) else '%s: %s' % (f['reason'], f['detail']) for f in findings]


def _argument_findings(root, repo, task_id, ci_text, recorder, now):
    found = []
    for name, value in (('root', root), ('repo', repo)):
        if not (isinstance(value, str) and value and os.path.isabs(value)):
            found.append('argument: %s is not a non-empty absolute path string' % name)
    if not (isinstance(task_id, str) and _TASK.fullmatch(task_id)):
        found.append('argument: task_id is not TASK- followed by digits')
    if not isinstance(ci_text, str):
        found.append('argument: ci_text is not a str')
    if not (isinstance(recorder, str) and recorder):
        found.append('argument: recorder is not a non-empty string')
    if not (isinstance(now, datetime.datetime) and now.tzinfo is not None and now.utcoffset() == _ZERO
            and now.microsecond == 0):
        found.append('argument: now is not a timezone-aware datetime in UTC with whole seconds')
    return found


def _tree(value):
    """A copy of plain data in which every dict and list is new at every place it stands."""
    if isinstance(value, dict):
        return {k: _tree(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_tree(v) for v in value]
    return value


def _contract(repo, commit, task_id, approved_hash, read):
    """Step 2: (the contract, its SHA-256, its bytes)."""
    answer, found = base_inputs.contract_at(repo, commit, task_id, read)
    if answer is None:
        raise _Refuse('contract', _texts(found))
    contract, sha = answer
    data = None
    for place in contract_path.candidates(task_id):
        value, _ = base_files.read_file(repo, commit, '/'.join(place), read)
        if value is None:
            continue
        candidate = value['text'].encode('utf-8')
        if hashlib.sha256(candidate).hexdigest() == sha:
            data = candidate
            break
    if data is None:
        raise _Refuse('contract', ['contract: no file read at the evaluated commit has the SHA-256 contract_at gave'])
    if sha != approved_hash:
        raise _Refuse('contract', ['contract: its SHA-256 is not the approved contract_hash'])
    return contract, sha, data


def _ci(ci_text, task_id, commit):
    """Step 3: (the eligible runs, the file hashes)."""
    parsed = evaluation_sources.parse_json(ci_text)
    if parsed['findings']:
        raise _Refuse('ci', _texts(parsed['findings']))
    if not isinstance(parsed['value'], dict):
        raise _Refuse('ci', ['ci: the CI data is not a JSON object'])
    intake = evaluation_intake.read_ci_data(parsed['value'], task_id, commit)
    if intake['result'] != 'present':
        raise _Refuse('ci', _texts(intake['findings']))
    return intake['runs'], intake['files']


def _policy_ref(contract, commit):
    state = contract.get('input_state')
    ref = state.get('base_commit') if isinstance(state, dict) else None
    if not (isinstance(ref, str) and _COMMIT.fullmatch(ref)):
        raise _Refuse('policy_ref', ['policy_ref: the contract names no input_state.base_commit of 40 lowercase '
                                     'hexadecimal characters'])
    if ref == commit:
        raise _Refuse('policy_ref', ['policy_ref: the base commit of the contract is the evaluated commit'])
    return ref


def _same_contract(provenance, sha, commit):
    """Whether the loader's provenance, a list of mappings, holds exactly one mapping with the key contract, and that
    one is the contract the command read: sha at commit (task TASK-163; D-7351)."""
    if type(provenance) is not list or not all(type(entry) is dict for entry in provenance):
        return False
    found = [entry for entry in provenance if 'contract' in entry]
    return len(found) == 1 and found[0] == {'contract': sha, 'commit': commit}


def _records_to_append(ci_records, manifest_record, payloads):
    """The CI records, then the manifest record unless the log holds it already; a conflicting one refuses."""
    held = [p for p in payloads if p.get('record_id') == manifest_record['record_id']]
    if held and not all(p == manifest_record for p in held):
        raise _Refuse('append', ['append: the log holds another record under the manifest record_id %s'
                                 % manifest_record['record_id']])
    return list(ci_records) + ([] if held else [manifest_record])


def _event_id(task_id, record_id):
    return hashlib.sha256('\n'.join((EVENT_ID_PREFIX, task_id, record_id)).encode('utf-8')).hexdigest()


def _append_all(root, task_id, records, log, recorder, now, append, appended):
    """Step 7: check all, then append, each append guarded by the SHA-256 of the log as this call knows it."""
    events = [(record, _event_id(task_id, record['record_id'])) for record in records]
    pending = log
    for record, event_id in events:
        decided = eventlog.append(pending, _RECORD_EVENT, record, event_id, now, task_id=task_id, recorder=recorder)
        if decided.result != 'appended':
            raise _Refuse('append', ['append: record %s would not be appended (%s, %s); nothing is written'
                                     % (record['record_id'], decided.result, decided.reason)]
                          + _texts(decided.findings))
        pending = pending + decided.line
    current = log
    for record, event_id in events:
        try:
            written = append(root, _RECORD_EVENT, record, event_id, now, recorder, task_id=task_id,
                             expected_log_sha256=hashlib.sha256(current).hexdigest())
        except Exception as exc:
            raise _Refuse('append', ['append: record %s raised %s; whether it was written is not known'
                                     % (record['record_id'], type(exc).__name__)])
        if written.result != 'appended':
            raise _Refuse('append', ['append: record %s was not appended (%s, %s)'
                                     % (record['record_id'], written.result, written.reason)]
                          + _texts(written.findings))
        current = current + written.line
        appended.append(record['record_id'])


def _decide(root, repo, task_id, contract_bytes, made, recorder, now, read):
    """Step 8: evaluate_task's answer, "evaluated" or "duplicate"; any other answer refuses."""
    answer = evaluation.evaluate_task(root, repo, task_id, contract_bytes, made['declared'], made['values'], [],
                                      recorder, now, read=read)
    if not (isinstance(answer, dict) and set(answer) == evaluation.RESULT_KEYS
            and answer['result'] in ('evaluated', 'duplicate', 'refused') and isinstance(answer['findings'], list)
            and all(isinstance(f, str) for f in answer['findings'])):
        raise _Refuse('evaluate', ['evaluate: evaluate_task gave an answer out of form'])
    if answer['result'] == 'refused':
        raise _Refuse('evaluate', ['evaluate: refused %s' % answer['reason']] + answer['findings'])
    return answer


def evaluate(root, repo, task_id, ci_text, recorder, now, read=None, read_log=None, append=None):
    """Evaluate one submitted task; returns a mapping with the keys RESULT_KEYS."""
    out = {'result': 'refused', 'reason': None, 'findings': [], 'event_id': None, 'decision': None,
           'next_task_state': None, 'manifest_sha256': None, 'manifest': None, 'appended': [], 'uncovered': None}
    step = 'argument'
    try:
        read_log = writer.read_log if read_log is None else read_log
        append = writer.append_event if append is None else append
        found = _argument_findings(root, repo, task_id, ci_text, recorder, now)
        if found:
            raise _Refuse('argument', found)
        step = 'log'
        log = read_log(root)
        try:
            events = evaluation._task_events(lambda _root: log, root, task_id)
        except evaluation._Stop as stop:
            raise _Refuse(stop.reason, stop.findings)
        approved_hash, commit, payloads = events[0], events[3], events[5]
        step = 'contract'
        contract, sha, contract_bytes = _contract(repo, commit, task_id, approved_hash, read)
        step = 'ci'
        runs, files = _ci(ci_text, task_id, commit)
        step = 'policy_ref'
        policy_ref = _policy_ref(contract, commit)
        step = 'sources'
        loaded = evaluation_sources.load_sources(repo, policy_ref, commit, task_id, [r['log'] for r in runs], read)
        if loaded['result'] != 'present':
            raise _Refuse('sources', _texts(loaded['findings']))
        if not _same_contract(loaded.get('provenance'), sha, commit):
            raise _Refuse('sources', [_OTHER_CONTRACT])
        step = 'inputs'
        made = eval_inputs.eval_inputs(task_id, commit, policy_ref, contract, sha, loaded['changed_paths'], runs,
                                       loaded['sources'], payloads, recorder)
        if made['refusal'] is not None:
            raise _Refuse('inputs', _texts([made['refusal']]))
        out['uncovered'] = made['evidence']['uncovered']
        step = 'manifest'
        manifest = evaluation_intake.manifest(task_id, commit, policy_ref, sha, _tree(loaded['provenance']),
                                              _tree(made['evidence']['ci']), _tree(files), recorder)
        if manifest['result'] != 'present':
            raise _Refuse('manifest', _texts(manifest['findings']))
        out['manifest_sha256'], out['manifest'] = manifest['sha256'], manifest['text']
        step = 'append'
        records = _records_to_append(made['ci_records'], manifest['record'], payloads)
        _append_all(root, task_id, records, log, recorder, now, append, out['appended'])
        step = 'evaluate'
        answer = _decide(root, repo, task_id, contract_bytes, made, recorder, now, read)
        out['result'], out['findings'] = answer['result'], list(answer['findings'])
        for key in ('event_id', 'decision', 'next_task_state'):
            out[key] = answer[key]
    except _Refuse as refusal:
        out['reason'], out['findings'] = refusal.reason, refusal.findings
    except Exception as exc:
        out['result'] = 'refused'
        out['reason'], out['findings'] = step, ['%s: a step raised %s' % (step, type(exc).__name__)]
    return out
