"""The CI intake and the manifest of an evaluation (task TASK-159; BT3b-2d-1 of DEF-0136 and DEF-0152; decisions D-7117
to D-7127): two pure functions. read_ci_data turns the saved texts of the CI runs of a task commit, given by the caller
as a mapping from file name to text, into the run mappings that ci_evidence takes, after binding each run attempt to its
own files. manifest turns what an evaluation read into one canonical JSON text, its SHA-256 and the record.added payload
that carries them. Nothing here fetches, reads or writes a file, starts a process, reads a clock, an environment or a
network, or appends to the event log: the command does that.

read_ci_data(files, task_id, evaluated_commit) returns exactly the keys result, runs, files and findings. For each run
attempt there are three names, run-<id>-<attempt>.api.json (the answer of the GitHub API for that attempt),
run-<id>-<attempt>.view.json (gh run view --attempt <attempt> --json) and run-<id>-<attempt>.log (gh run view
--attempt <attempt> --log). The checks, in order, the first refusal ending the call: the arguments (argument); the names
(files); every text can be written as UTF-8 (plain); per attempt in numeric order, both JSON texts parse with
evaluation_sources.parse_json (json); the binding of the three files of an attempt (binding); the choice of the eligible
runs by ci_evidence.eligible_run (run); for each run with an eligible attempt, its attempts are exactly 1 to the highest
given and each is eligible (attempts); and each eligible log holds the line of the checkout step that prints the
evaluated commit (binding). result is "present" or "refused". On "present" runs holds only the eligible mappings sorted
by run id and attempt, and files holds {name, sha256} of every text given, sorted by name. On "refused" runs and files
are None and findings holds exactly one {reason, detail}. An unexpected Exception is a refusal with reason argument and a
detail that names its type.

manifest(task_id, evaluated_commit, policy_ref, contract_sha256, provenance, ci, files, recorder) returns exactly the
keys result, text, sha256, record and findings. The arguments are checked first (argument), then that provenance, ci and
files are plain data and that the text can be written (plain). The record has no outcome, gate, dimension or intent
versions, so it satisfies no evidence entry.

Limits: a log cannot be shown to be that run's from its bytes (the saved log holds no run id), so the line of the commit
and ci_evidence's detect line are content checks only; the highest attempt that exists is not knowable from the texts
given, so an omitted later attempt is not seen; the texts are the caller's fetch, trusted unedited.
"""
import hashlib
import json
import re

from aieos_bootstrap import ci_evidence
from aieos_bootstrap import evaluation_derive
from aieos_bootstrap import evaluation_sources

_TASK = re.compile(r'TASK-[0-9]+')
_COMMIT = re.compile(r'[0-9a-f]{40}')
_SHA256 = re.compile(r'[0-9a-f]{64}')
_NAME = re.compile(r'run-([1-9][0-9]{0,18})-([1-9][0-9]{0,18})\.(api\.json|view\.json|log)')
_KINDS = ('api.json', 'view.json', 'log')
_LINE = re.compile('\ufeff?[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:[.][0-9]+)?Z(?: (.*))?', re.S)
_JOB = 'checks'
_STEP = 'Fetch the pushed commit, its history and main (no third-party action, no token)'
_API_KEYS = ('id', 'run_attempt', 'head_sha', 'event', 'head_branch', 'status', 'conclusion', 'path')
_VIEW_KEYS = ('databaseId', 'attempt', 'headSha', 'event', 'headBranch', 'status', 'conclusion', 'jobs')
_PAIRS = (('head_sha', 'headSha'), ('event', 'event'), ('head_branch', 'headBranch'), ('status', 'status'),
          ('conclusion', 'conclusion'))
_MAX_DETAIL = 200


class _Refuse(Exception):
    def __init__(self, reason, detail):
        Exception.__init__(self, reason)
        self.reason = reason
        self.detail = detail


def _finding(reason, detail):
    return [{'reason': reason, 'detail': detail[:_MAX_DETAIL]}]


def _intake_refused(reason, detail):
    return {'result': 'refused', 'runs': None, 'files': None, 'findings': _finding(reason, detail)}


def _can_encode(text):
    try:
        text.encode('utf-8')
    except UnicodeEncodeError:
        return False
    return True


def _matches(pattern, value):
    return type(value) is str and pattern.fullmatch(value) is not None


def _argument_error(files, task_id, evaluated_commit):
    if type(files) is not dict or any(type(k) is not str or type(v) is not str for k, v in files.items()):
        return 'files is not a dict from a text to a text'
    if not _matches(_TASK, task_id):
        return 'task_id is not TASK- and digits'
    if not _matches(_COMMIT, evaluated_commit):
        return 'evaluated_commit is not 40 lowercase hexadecimal characters'
    return None


def _attempts(files):
    """{(id, attempt): {kind: text}} for the given names, or a refusal."""
    found = {}
    for name, text in files.items():
        m = _NAME.fullmatch(name)
        if m is None:
            raise _Refuse('files', 'a name is not one of the three forms: ' + repr(name))
        found.setdefault((int(m.group(1)), int(m.group(2))), {})[m.group(3)] = text
    if not found:
        raise _Refuse('files', 'no file is given')
    for key in sorted(found):
        if set(found[key]) != set(_KINDS):
            raise _Refuse('files', 'run %d attempt %d does not have its three files' % key)
    return found


def _parsed(text, key, kind):
    answer = evaluation_sources.parse_json(text)
    if answer['findings']:
        raise _Refuse('json', 'run %d attempt %d %s: %s' % (key[0], key[1], kind, answer['findings'][0]['detail']))
    return answer['value']


def _need(value, keys, where):
    if type(value) is not dict:
        raise _Refuse('binding', where + ' is not a JSON object')
    for name in keys:
        if name not in value:
            raise _Refuse('binding', where + ' lacks the key ' + name)


def _steps(view, where):
    jobs = view['jobs']
    if type(jobs) is not list:
        raise _Refuse('binding', where + ' jobs is not a list')
    steps = []
    for job in jobs:
        _need(job, ('steps',), where + ' a job')
        if type(job['steps']) is not list:
            raise _Refuse('binding', where + ' steps is not a list')
        for step in job['steps']:
            _need(step, ('name', 'conclusion'), where + ' a step')
            name, conclusion = step['name'], step['conclusion']
            if type(name) is not str or name == '':
                raise _Refuse('binding', where + ' a step has a name that is not a non-empty text')
            if conclusion is not None and type(conclusion) is not str:
                raise _Refuse('binding', where + ' a step has a conclusion that is neither a text nor null')
            steps.append({'name': name, 'conclusion': conclusion})
    return steps


def _bound(key, api, view, log):
    """The run mapping of one attempt, after every pair of its two JSON objects and its names agrees."""
    where = 'run %d attempt %d' % key
    _need(api, _API_KEYS, where + ' api')
    _need(view, _VIEW_KEYS, where + ' view')
    for number, mine, theirs in ((key[0], 'id', 'databaseId'), (key[1], 'run_attempt', 'attempt')):
        if type(api[mine]) is not int or type(view[theirs]) is not int or not api[mine] == number == view[theirs]:
            raise _Refuse('binding', '%s: %s, the name and the view %s differ' % (where, mine, theirs))
    for mine, theirs in _PAIRS:
        left, right = api[mine], view[theirs]
        allowed = (str, type(None)) if mine == 'conclusion' else (str,)
        if type(left) not in allowed or type(right) not in allowed or left != right:
            raise _Refuse('binding', '%s: %s and the view %s differ or are not texts' % (where, mine, theirs))
    if type(api['path']) is not str:
        raise _Refuse('binding', where + ' path is not a text')
    return {'run_id': key[0], 'attempt': key[1], 'head_sha': api['head_sha'], 'event': api['event'],
            'head_branch': api['head_branch'], 'workflow_path': api['path'], 'status': api['status'],
            'conclusion': api['conclusion'], 'steps': _steps(view, where + ' view'), 'log': log}


def _names_the_commit(log, commit):
    wanted = '  SHA: ' + commit
    for line in log.split('\n'):
        if line.endswith('\r'):
            line = line[:-1]
        parts = line.split('\t', 2)
        if len(parts) != 3 or parts[0] != _JOB or parts[1] != _STEP:
            continue
        m = _LINE.fullmatch(parts[2])
        if m is not None and m.group(1) == wanted:
            return True
    return False


def _intake(files, task_id, evaluated_commit):
    found = _attempts(files)
    for name in sorted(files):
        if not _can_encode(files[name]):
            raise _Refuse('plain', 'a text cannot be written as UTF-8: ' + name)
    runs = []
    for key in sorted(found):
        api = _parsed(found[key]['api.json'], key, 'api.json')
        view = _parsed(found[key]['view.json'], key, 'view.json')
        runs.append((key, api, view))
    mappings = [_bound(key, api, view, found[key]['log']) for key, api, view in runs]
    chosen = [r for r in mappings if ci_evidence.eligible_run(r, task_id, evaluated_commit)]
    if not chosen:
        raise _Refuse('run', 'no eligible run')
    eligible = {(r['run_id'], r['attempt']) for r in chosen}
    for run_id in sorted({r['run_id'] for r in chosen}):
        given = sorted(attempt for number, attempt in found if number == run_id)
        if given != list(range(1, len(given) + 1)) or any((run_id, attempt) not in eligible for attempt in given):
            raise _Refuse('attempts', 'run %d does not give every attempt from 1 as an eligible one' % run_id)
    for r in chosen:
        if not _names_the_commit(r['log'], evaluated_commit):
            raise _Refuse('binding', 'run %d attempt %d: no line of the checkout step names the commit'
                          % (r['run_id'], r['attempt']))
    listed = [{'name': name, 'sha256': hashlib.sha256(files[name].encode('utf-8')).hexdigest()} for name in sorted(files)]
    return {'result': 'present', 'runs': chosen, 'files': listed, 'findings': []}


def read_ci_data(files, task_id, evaluated_commit):
    """The eligible run mappings and the file hashes of the saved CI data, or the refusal."""
    try:
        error = _argument_error(files, task_id, evaluated_commit)
        if error is not None:
            return _intake_refused('argument', error)
        return _intake(files, task_id, evaluated_commit)
    except _Refuse as refused:
        return _intake_refused(refused.reason, refused.detail)
    except Exception as exc:
        return _intake_refused('argument', 'an unexpected error: ' + type(exc).__name__)


def _manifest_refused(reason, detail):
    return {'result': 'refused', 'text': None, 'sha256': None, 'record': None, 'findings': _finding(reason, detail)}


def _manifest_argument_error(task_id, evaluated_commit, policy_ref, contract_sha256, provenance, ci, files, recorder):
    if not _matches(_TASK, task_id):
        return 'task_id is not TASK- and digits'
    if not _matches(_COMMIT, evaluated_commit):
        return 'evaluated_commit is not 40 lowercase hexadecimal characters'
    if not _matches(_COMMIT, policy_ref):
        return 'policy_ref is not 40 lowercase hexadecimal characters'
    if not _matches(_SHA256, contract_sha256):
        return 'contract_sha256 is not 64 lowercase hexadecimal characters'
    if type(provenance) is not list:
        return 'provenance is not a list'
    if type(ci) is not dict:
        return 'ci is not a dict'
    if type(files) is not list:
        return 'files is not a list'
    if type(recorder) is not str or recorder == '' or not _can_encode(recorder):
        return 'recorder is not a non-empty text that UTF-8 can write'
    return None


def manifest(task_id, evaluated_commit, policy_ref, contract_sha256, provenance, ci, files, recorder):
    """The manifest text, its SHA-256 and its record, or the refusal."""
    try:
        error = _manifest_argument_error(task_id, evaluated_commit, policy_ref, contract_sha256, provenance, ci, files,
                                         recorder)
        if error is not None:
            return _manifest_refused('argument', error)
        for name, value in (('provenance', provenance), ('ci', ci), ('files', files)):
            problem = evaluation_derive.plain_data_problem(value)
            if problem is not None:
                return _manifest_refused('plain', name + ': ' + problem['detail'])
        try:
            text = json.dumps({'task_id': task_id, 'evaluated_commit': evaluated_commit, 'policy_ref': policy_ref,
                               'contract_sha256': contract_sha256, 'provenance': provenance, 'ci': ci, 'files': files},
                              sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
        except ValueError as exc:
            return _manifest_refused('plain', 'the text cannot be made: ' + type(exc).__name__)
        if not _can_encode(text):
            return _manifest_refused('plain', 'the text cannot be written as UTF-8')
        digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
        record_id = hashlib.sha256('\n'.join(('evaluation-manifest', task_id, evaluated_commit, digest))
                                   .encode('utf-8')).hexdigest()
        record = {'record_id': record_id, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
                  'recorder': recorder, 'subject': task_id, 'evidence_type': 'evaluation_manifest',
                  'commit': evaluated_commit, 'refers_to': digest, 'basis': [text]}
        return {'result': 'present', 'text': text, 'sha256': digest, 'record': record, 'findings': []}
    except Exception as exc:
        return _manifest_refused('argument', 'an unexpected error: ' + type(exc).__name__)
