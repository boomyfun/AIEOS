"""The replay of logged decision.execution records (task TASK-139; constitution INV-010; specification 3 section 11 (a decision is
recomputable from its record, the repository and the event log); decisions D-6310, D-6312, D-6314, D-6315, D-6316 and, for the
erratum E1 to the contract, D-6325 and D-6327): it recomputes one logged decision.execution record with the Resume Check and reports
every difference, and it fails closed on everything else.

``replay_execution(repo, log_bytes, record_index, accepted_engines, checked_commit=None, read=None, engine=None, engine_text=None,
build_inputs=None)`` returns (True, []) or (False, findings), findings being non-empty strs, and never raises; with no ``engine`` given it
refuses and imports nothing (erratum E1.7). ``record_index`` is the 0-based position of the record among the lines of the log
(``log_bytes`` is the whole log). ``main(argv, read=None, out=print, engine=None)``
is the command-line entry (run as ``PYTHONPATH=src python -B -P -m aieos_bootstrap.decision_replay <repo> [--governor-pin <sha256>] [<accepted engine sha256> ...]``, erratum E1.7)
and returns the exit code, 0 only when every decision record of the checked tree was replayed and passed, a recognised record of the violation path excepted (task TASK-141).

What a replay does, in order (each step a failure with its finding when it does not hold):
1. The log is checked by records.check_log; the record is the line ``record_index``: a decision.execution event with a task_id and a payload
   holding head_commit (a commit id), log_seq (an int), engine_identity (code_sha256) and runtime (adapter, max_risk); its own
   seq is log_seq + 1 (erratum E1.1: the record is not one of its own inputs).
2. The log is cut at the lines with seq <= log_seq; they must be exactly the lines before ``record_index`` (a log with a line out of order
   fails). The cut log is the log of the recomputation, as the launcher read it when it granted the start.
3. The engine (erratum E1.1, decision D-6325). The Resume Check is the checked tree's src/aieos_bootstrap/resume_check.py, reached
   by a plain import statement (no exec, no compile, no importlib: the deterministic_rule step of the CI refuses them). The replay
   calls its check only when all four values are equal: (a) the SHA-256 of the engine text at head_commit, (b) the record's
   engine_identity.code_sha256, (c) the SHA-256 of the same file at the checked commit, and (d) one of ``accepted_engines``; each text
   is read through base_files.read_file and hashed as launcher.py hashes it (raw git bytes are not used: the hash is of the text
   as base_files.read_file returns it, encoded as UTF-8). With no accepted engine every
   record fails. A head_commit engine that differs from the checked tree's fails with "no historical-engine loader (erratum E1)".
4. The 22 inputs of the Resume Check are built as launcher._inputs builds them (resume_inputs.git_inputs, resume_log_inputs.log_inputs,
   execution.task_view over the cut log with no held lease, and the runtime taken from the record) and the engine's check is called
   with the record's code_sha256.
5. Every key of the recomputed record and of the logged payload is compared. engine_identity is compared, without its python value, by canonical JSON text like every other key: its
   python value is reported in the notes of the command-line entry and never fails a replay (the interpreter of the CI runner may differ).

``main`` (erratum E1.2 to E1.4): it refuses, with exit 1, unless the configuration read of gitread (CONFIG_LIST) shows no key that
begins with "filter." (ASCII-lowercased) or equals "core.worktree" (the refusal of the launcher's root check, TASK-110) and the status
read (gitread.STATUS_HEAD with one exclusion) prints nothing; the engine file that a plain import would load (computed from the package's own file, before the engine is imported) must be the
repository's own src/aieos_bootstrap/resume_check.py (a path comparison through os.path.normcase and os.path.abspath on both sides, no file read).
The one name that the status form needs is ".git": it is the one name the form needs, chosen because the project-state folder may
not be named in src (INV-004); git status never reports .git, so the exclusion hides nothing. HEAD comes from gitread's rev-parse form
and every tracked file named events.jsonl (its last path component, at any depth) comes from base_files.list_paths(repo, HEAD, "")
and base_files.read_file; a refused listing or read is a failure, never a skip. Each decision.execution line is replayed and each
decision.acceptance line is replayed as the next paragraph says, or fails; no record is
skipped or counted as passing without a replay, with ONE exception (task TASK-141): a record of the violation path, recognised by violation_path_record
(the form that violation.py writes and the earlier violation.detected line that it names), is reported "NOT REPLAYED: violation-path record (no Resume Check ran)"
and counted apart; it is neither replayed nor counted as passed or as failed, because no Resume Check ran for it (violation.py UNCOVERED). The engine gate comes first: when the engine is not an accepted one, every decision.execution line fails, a recognised record included.

The replay of a decision.acceptance line (task TASK-167; DEF-0137 task B; decisions D-7557 and D-7558). The entry takes
--governor-pin <sha256> after the repository, at most once; it is never an accepted engine, and an engine pin is never read as
it. Without it every such line is counted failed and printed "NOT REPLAYED: decision.acceptance" with its place. With it, the
replay of an acceptance line imports no module that imports the governor, directly or through its own imports
(evaluation_sources through evaluation and scope_reconcile, eval_inputs, evaluate_command, evaluation, evaluation_intake),
unless the engine gate passes (the reader of contracts imports the Resume Check), the governor file that a plain import
would load is the
repository's own src/aieos_bootstrap/governor.py, the governor at the checked commit has the pin's SHA-256 and the record's
ruleset_version is "governor-sha256:" and the pin; the fourth equal value, the governor at the record's policy_ref, is
checked by evaluation_sources.load_sources with the pin. This holds for the acceptance replay only: the replay of a
decision.execution line imports the governor with no governor gate, through resume_log_inputs, scope_reconcile and
scope_drift, as before this task; so when an execution line that reached its inputs was replayed before an acceptance
line, the governor is already imported when that line's governor gate runs, and the gate still checks the governor file
and its SHA-256 before the acceptance replay uses it. Before the recomputation a line fails when the log does not end with
LF, when the line or any line before it is an ignored duplicate of an earlier one or is not in the form the writer writes,
or when the line holds fencing_token or corrects (the evaluation writes neither). The log of the recomputation is the
lines before the record (the record holds no log position). The evaluated commit and the approved contract hash come from those lines; the contract, its bytes and
policy_ref from the commit (the helpers of the command aieos evaluate); the sources and the changed paths from load_sources
with the pin and no CI log; the argument checks of eval_inputs are made over them by eval_inputs._argument_error, with
the CI runs and the log payloads passed as empty lists; the values come from eval_inputs._assemble and are then derived and
refused as eval_inputs does by its own function, so a governor error record that aieos evaluate would not write fails.
Before the evaluation, the manifest (task TASK-168): among the task's record.added payloads on the earlier lines at
least one evaluation_manifest of the evaluated commit must be remade equal by evaluation_intake.manifest from its one basis
text, name the task, commit, policy_ref and contract SHA-256 of the replay, hold the replay's provenance with the pin
mapping as the command writes it from the CI logs (logs equal to the number of its runs), hold a ci mapping of the form
ci_evidence gives, and stand on a line with the event id that evaluate_command gives it; and no other earlier payload of
the task may share its record_id with different content. Nothing of the manifest is an input of the recomputation.
Then evaluation.evaluate_task is called over the cut log with no extra record, with the recorder of the payload and the
append time of the line, and with an append that writes nothing; the captured event type, event_id and task_id must equal
the line's, and every key of the record the payload's, by canonical JSON text. An evaluated commit that the checkout cannot
read fails with its own finding. Every line of a log must be in the form the writer writes (no ignored duplicate,
canonical bytes, a final LF): in the entry a file with such a finding fails and none of its decision records is counted as
passed, and replay_execution refuses such a log.
Accepted limits: the CI and review records in the log are trusted as logged and nothing reads GitHub or a reviews file
again; a manifest record is trusted as logged beyond what is compared above (the runs and their log hashes, the contract
commit and base of the detect line, files and reviews_sha256), so whoever writes the log can write a matching manifest;
appended_at is taken from the line and not otherwise checked; the readers, the evaluation modules and the governor run
from the tree under check (GOV-003 is not met by them); a line appended between an evaluation's read and its own append can
make its replay differ (when it changes the recomputed record); no logged acceptance record of the self-build exists, so
no real record has been replayed. Open items, not accepted limits (DEF-0137): the refusals of aieos evaluate that need the
saved CI data or the reviews text are not repeated (read_ci_data, ci_evidence, the record-id guard over the CI records,
the reviews maker and its guard); after a change of the governor or of the governor pin, or of a reader in a way that
changes a result, older records fail closed, with no loader of the old code. A record whose evaluated commit the checkout
does not hold fails, and which of fetching it, keeping such a record out of main's log, or another course is taken is the
decision of the later workflow step.

The module violation is imported when this module is loaded, so before the gates of the entry.

Limits, stated (erratum E1; D-6314 C2 and C3; D-6313 C5):
- The reader modules (resume_inputs, resume_log_inputs, execution, base_files, gitread and records, whose check_log is used) are those of
  the commit that the CI checks out, never of a local working tree, and only the engine is tied to head_commit by its hash. A pass shows
  that the record is reproducible by the checked tree's readers and the pinned engine, NOT that it is what head_commit's readers computed.
- Any difference, including one that a later reader change causes, fails closed, with no skip list. The named remedy for a historical
  record that a reader change makes differ is to load the readers from head_commit, to be ruled on by the decision agent.
- This module, the module violation (whose DECISION and RECORDER decide which record is recognised, task TASK-141) and the reader modules run from the tree under check, not from a base or a pinned ref, so GOV-003 is not met by them: a change that
  alters them can change what passes. Only the engine is pinned (decision D-6332).
- After a pinned engine upgrade, records written under the old engine fail closed ("no historical-engine loader") until such a loader
  exists; it is a later task, not this one.
- runtime.max_risk is taken from the record: the launcher reads it from the adapter declaration (launcher.py), which the replay does not
  repeat. The held lease is None and ``now`` is a fixed constant, which only the argument checks of task_view use.
- The workflow of the CI passes no governor pin until its own step is decided, so there a decision.acceptance record fails.
- A record of the violation path is recognised by its form and by the violation.detected line that it names, and nothing recomputes it (task TASK-141): a forged
  pair of such lines would be reported "NOT REPLAYED: violation-path record" and would not fail the replay; the state-commit gate of the worker names the lines it accepts.
- The interpreter of the CI runner may differ from the recorded python; it is reported, not failed.
- The limits of the configuration and status reads are those of gitread (its docstring, "Limits", the sixth and fifth forms; TASK-109 and
  TASK-110), cited here and not repeated as new claims: (1) the configuration and the status are two reads made one after the other, not
  atomically; (2) a key is matched by its text, never by whether a file uses the driver, so a clone that names a driver and uses none is
  refused; (3) other keys change what the status read counts and are not refused (an ignore, sparse-checkout, line-ending or attributes key
  among them; core.checkStat, core.trustctime and core.ignoreStat are not refused either); (4) the user's own global ignore file is meant not to be read, and whether git on a machine finds a home directory is not
  checked; (5) if a later git removes the ``--list`` spelling the read fails and the entry refuses; (6) a bare clone is not refused by the
  configuration read, since the status read refuses it; (7) a partial clone can make a git before 2.44 start a lazy fetch (per git's
  documentation, not run here). The status read counts untracked files that are not ignored, so the entry must run where the checkout is
  clean (the A66 step of the CI is to say where; decision D-6328 C3).
- The status read does not see index flags (assume-unchanged, skip-worktree), so a working-tree file flagged so can differ from the git
  object whose hash was checked (the launcher states the same limit in its root check); the engine and the readers that run are the
  working-tree files of the checkout.
- ``python -m`` without -P puts the current directory first on the import path. The invocation of erratum E1.7 is ``-B -P``, and a guard
  (placed after ``import sys`` and its helper, before this module's other imports) exits 1 when it runs as __main__ without safe_path; the guard only detects a missing -P (a module that
  shadows a library module and is imported before it is not caught), so the defence is the invocation of the A66 step, which must run in a
  fresh checkout. The engine is imported only after the argument checks, the engine-file path check (computed from the package's own file),
  the configuration and status reads, and the check that the engine's SHA-256 at the checked HEAD is one of the pins; the readers that import
  the engine are imported at the same point. Python may write bytecode before the status read when it imports the package; -B prevents it.
- git's refs/replace is not disabled by gitread, so a replaced tree could change the readers' inputs; blobs (the engine) are hashed.
- The command line is the only path that the CI step is to call: replay_execution and replay_detail are for tests and refuse with no engine.
- head_commit is any commit of the repository that the record names; it need not be HEAD or an ancestor of it. The record cannot choose the
  engine (the engine is the plain import, tied to the record by the four equal values), but it chooses the commit at which the inputs are read.
- ``replay_execution`` runs none of the tree, configuration or engine-file checks (only ``main`` does) and accepts injected engine,
  engine_text and build_inputs, which the tests use; ``main`` calls it with the engine that it imported after its gates.
- With no tracked file named events.jsonl the entry replays nothing and exits 0, as the CI step that it is to replace did; every tracked
  events.jsonl is checked with records.check_log, and a finding fails the entry.
- Values are compared by their canonical JSON text, so 1, 1.0 and true differ; engine_identity is compared without its python value only.
- One record was recomputed by a read-only probe before this module (decision D-6313), with the engine loaded from head_commit's text;
  the tests of this task are the evidence for the others.
The module opens and writes no file of its own (Python itself may write bytecode under the source folder when it imports the module), reads
no clock and no environment variable, starts no process but through gitread, makes no network call of its own (a git before 2.44 on a partial clone may start a lazy fetch) and no model call.
"""

import sys


def _safe_path_ok(flags):
    """Whether the interpreter flags show the -P option (safe_path, Python 3.11 and later); False when the flag does not exist."""
    return bool(getattr(flags, 'safe_path', False))


# erratum E1.7 (decision D-6333): a guard placed before this module's other imports. It detects a run without -P only; a module that
# shadows a library module and is imported before this guard is not caught: the defence is the invocation of the A66 step.
if __name__ == '__main__' and not _safe_path_ok(sys.flags):
    sys.stdout.write('FAIL: this entry must be run with -P (and -B), as erratum E1.7 sets: the current directory must not be on the import path\n')
    sys.exit(1)

import datetime
import hashlib
import json
import os
import re

import aieos_bootstrap
from aieos_bootstrap import base_files, eventlog, gitread, records, violation

ENGINE_PATH = 'src/aieos_bootstrap/resume_check.py'
GOVERNOR_PATH = 'src/aieos_bootstrap/governor.py'
GOVERNOR_FLAG = '--governor-pin'
RULESET_PREFIX = 'governor-sha256:'
ACCEPTANCE = 'decision.acceptance'
EVENTS_NAME = 'events.jsonl'
TIMEOUT = 60
# the one name the status form needs (see the docstring): git status never reports it
STATE_EXCLUDE = '.git'
NOW = datetime.datetime(2026, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_HEX64 = re.compile(r'[0-9a-f]{64}')
_TASK = re.compile(r'TASK-[0-9]+')
_SHOWN = 300
_ABSENT = object()
# the limits that the command-line entry prints (erratum E1.1, contract AC3): short forms of the docstring's limits
LIMITS = (
    'the reader modules are those of the checked commit and only the engine is tied to head_commit by its hash: a pass shows reproducibility by those readers, NOT what head_commit\'s readers computed',
    'any difference fails closed, with no skip list; the remedy for a historical record that a reader change makes differ is to load the readers from head_commit (a decision of the decision agent)',
    'after a pinned engine upgrade, records written under the old engine fail closed until a historical-engine loader exists (erratum E1)',
    'runtime.max_risk is taken from the record; the held lease is None and the clock is a fixed constant',
    'a decision.acceptance record is replayed only with --governor-pin and fails without it; the python value of engine_identity is reported, not compared',
    'a decision.acceptance replay trusts the CI and review records as logged and reads nothing from GitHub or a reviews file; it uses the readers, the evaluation modules and the governor of the tree under check (GOV-003 is not met by them); a record whose evaluated commit this checkout does not hold fails, and the course for such a record is the decision of the later workflow step',
    'a decision.acceptance replay trusts a manifest record as logged beyond what it compares (its runs and log hashes, the contract commit and base of its detect line, files and reviews_sha256); appended_at is not otherwise checked; no logged acceptance record of the self-build exists, so no real record has been replayed',
    'open (DEF-0137), not accepted limits: the refusals of aieos evaluate that need the saved CI data or the reviews text are not repeated; after a change of the governor or of its pin older acceptance records fail closed',
    'a record of the violation path is recognised by its form and by the violation.detected line that it names, and nothing recomputes it (task TASK-141): a forged pair of such lines is reported NOT REPLAYED: violation-path record and does not fail this entry; the module violation, read from the tree under check, decides what is recognised',
    'the status read does not see assume-unchanged or skip-worktree flags and counts untracked files that are not ignored: run in a clean checkout where no file shadows a library module',
    'this entry and its reader modules run from the tree under check, not from a base or a pinned ref: GOV-003 is not met by them, and a change to them can change what passes; only the engine is pinned (decision D-6332)',
    'the guard against a run without -P only detects a missing -P: a module that shadows a library module and is imported before the guard is not caught; the defence is the invocation with -P and -B (erratum E1.7)',
    'the limits of the configuration and status reads apply (two separate reads; keys matched by text; ignore, attributes, core.checkStat-type keys not refused; a git before 2.44 on a partial clone may lazy-fetch): see the module docstring',
)


def _safe(value):
    """A value as one printable line fragment: a str is JSON-escaped (so a newline in a record cannot forge a line), anything else is str()."""
    return json.dumps(value)[1:-1] if isinstance(value, str) else str(value)


def _canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def _cut(text):
    text = str(text)
    return text if len(text) <= _SHOWN else text[:_SHOWN] + '...'


def _sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _no_held(root, task_id):
    return None


def _default_engine_text(repo, commit, read):
    got, found = base_files.read_file(repo, commit, ENGINE_PATH, read)
    if found is not None:
        return None, found
    return got['text'], None


def _engine_module():
    """The checked tree's Resume Check by a plain import statement; it runs the engine's top-level code, so it is called only after the gates."""
    from aieos_bootstrap import resume_check
    return resume_check


def _default_build_inputs(repo, head, task_id, cut_log, runtime, read):
    """(the 22 inputs, None) or (None, findings), as launcher._inputs joins them (the log read, the runtime from the record). The readers
    import the engine themselves, so they are imported here by plain import statements, not at load (erratum E1.7)."""
    from aieos_bootstrap import execution, resume_inputs, resume_log_inputs
    given, found = resume_inputs.git_inputs(repo, head, task_id, cut_log, read)
    if found is not None:
        return None, ['git_inputs: %s' % f for f in found]
    logged, found = resume_log_inputs.log_inputs(repo, head, task_id, cut_log, read)
    if found is not None:
        return None, ['log_inputs: %s' % f for f in found]
    view, found = execution.task_view(cut_log, repo, task_id, NOW, held=_no_held)
    if found is not None:
        return None, ['task_view: %s' % f for f in found]
    inputs = dict(given)
    inputs.update(logged)
    inputs.update({'task_id': task_id, 'runtime': {'adapter': runtime['adapter'], 'max_risk': runtime['max_risk']},
                   'log_seq': view['log_seq'], 'task_state': view['task_state'],
                   'approved_contract_hash': view['approved_contract_hash']})
    return inputs, None


def _record(lines, index):
    """(the record's fields as a dict, None) or (None, a finding)."""
    try:
        event = json.loads(lines[index].decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return None, 'record: line %d is not JSON' % (index + 1)
    if not isinstance(event, dict) or event.get('type') != 'decision.execution':
        return None, 'record: line %d is not a decision.execution event' % (index + 1)
    payload = event.get('payload')
    task_id = event.get('task_id')
    seq = event.get('seq')
    if not isinstance(payload, dict) or not isinstance(task_id, str) or _TASK.fullmatch(task_id) is None:
        return None, 'record: line %d has no payload or no task_id in form' % (index + 1)
    head = payload.get('head_commit')
    log_seq = payload.get('log_seq')
    ident = payload.get('engine_identity')
    runtime = payload.get('runtime')
    if not (isinstance(head, str) and _COMMIT.fullmatch(head)):
        return None, 'record: head_commit is not a commit id'
    if type(log_seq) is not int or type(seq) is not int or log_seq < 0:
        return None, 'record: log_seq or seq is not an int'
    if not (isinstance(ident, dict) and isinstance(ident.get('code_sha256'), str) and _HEX64.fullmatch(ident['code_sha256'])):
        return None, 'record: engine_identity.code_sha256 is not 64 lowercase hex characters'
    if not (isinstance(runtime, dict) and isinstance(runtime.get('adapter'), str) and isinstance(runtime.get('max_risk'), str)):
        return None, 'record: runtime has no adapter or max_risk'
    if seq != log_seq + 1:
        return None, 'record: seq %d is not log_seq + 1 (%d)' % (seq, log_seq + 1)
    return {'task_id': task_id, 'head': head, 'log_seq': log_seq, 'code_sha256': ident['code_sha256'], 'runtime': runtime,
            'payload': payload, 'seq': seq, 'record_id': payload.get('record_id')}, None


def violation_path_record(lines, index):
    """True only for the record that the violation path writes (violation.py; task TASK-141): a decision.execution event whose decision is
    violation.DECISION and whose recorder is violation.RECORDER, with no head_commit (the path has none by design), whose event_id is its
    refers_to followed by "/decision", and whose refers_to is the event_id of an EARLIER line of the same log whose type is violation.detected
    and whose task_id is the same. Every other line is not one. It checks the FORM only: nothing recomputes the record. ``lines`` is the log split at newlines, ``index`` the 0-based position of the
    line. Never raises."""
    try:
        if type(index) is not int or index < 0:
            return False
        event = json.loads(lines[index].decode('utf-8'))
        if not isinstance(event, dict) or event.get('type') != 'decision.execution':
            return False
        payload = event.get('payload')
        task = event.get('task_id')
        refers = payload.get('refers_to') if isinstance(payload, dict) else None
        if not (isinstance(payload, dict) and isinstance(task, str) and isinstance(refers, str)):
            return False
        if payload.get('decision') != violation.DECISION or payload.get('recorder') != violation.RECORDER or 'head_commit' in payload:
            return False
        if event.get('event_id') != refers + '/decision':
            return False
        for line in lines[:index]:
            try:
                earlier = json.loads(line.decode('utf-8'))
            except (ValueError, UnicodeDecodeError, RecursionError):
                continue
            if isinstance(earlier, dict) and earlier.get('type') == 'violation.detected' and earlier.get('event_id') == refers and earlier.get('task_id') == task:
                return True
        return False
    except Exception:  # every failure is "not a violation-path record", and the line is then replayed as before
        return False


def _form_findings(log_bytes, report):
    """The findings of a form that the writer never writes, over the bytes of an event log and the report of
    records.check_log over them; an empty log has none."""
    if not log_bytes:
        return []
    found = []
    if not log_bytes.endswith(b'\n'):
        found.append('log: the log does not end with LF')
    lines = log_bytes.split(b'\n')
    if lines[-1] == b'':
        lines = lines[:-1]
    for number, line in enumerate(lines, 1):
        first = report.lines[number - 1].duplicate_of if number <= len(report.lines) else None
        if first is not None:
            found.append('log: line %d is an ignored duplicate of line %d, which the writer never writes' % (number, first))
        try:
            written = eventlog._canonical(json.loads(line.decode('utf-8'))).encode('ascii')
        except (ValueError, TypeError, UnicodeDecodeError, RecursionError):
            written = None
        if line != written:
            found.append('log: line %d is not in the form the writer writes' % number)
    return found


def _replay(repo, log_bytes, record_index, accepted_engines, checked_commit, read, engine, engine_text, build_inputs):
    """(the findings, the notes); an empty findings list is a pass."""
    index = record_index
    if engine is None:
        return ['engine: no engine was given; the entry runs the gates, imports the engine and passes it (erratum E1.7)'], []
    if not isinstance(log_bytes, bytes) or type(index) is not int or index < 0:
        return ['argument: log_bytes is not bytes or index is not a non-negative int'], []
    if not (isinstance(accepted_engines, (list, tuple)) and all(isinstance(a, str) and _HEX64.fullmatch(a) for a in accepted_engines)):
        return ['argument: accepted_engines is not a list of 64-hex strings'], []
    report = records.check_log(log_bytes)
    found = ['log: line %d: %s' % (n, f) for n, f in report.findings()]
    if found:
        return found, []
    found = _form_findings(log_bytes, report)
    if found:
        return found, []
    lines = log_bytes.split(b'\n')
    if lines and lines[-1] == b'':
        lines = lines[:-1]
    if index >= len(lines):
        return ['record: index %d is past the %d lines of the log' % (index, len(lines))], []
    rec, finding = _record(lines, index)
    if finding is not None:
        return [finding], []
    seqs = []
    for k, line in enumerate(lines):
        try:
            seqs.append(json.loads(line.decode('utf-8'))['seq'])
        except (ValueError, UnicodeDecodeError, KeyError, TypeError):
            return ['log: line %d has no seq' % (k + 1)], []
    cut = [line for line, s in zip(lines, seqs) if type(s) is int and s <= rec['log_seq']]
    if index == 0:
        return ['log: a record on the first line has no earlier line to recompute from'], []
    if cut != lines[:index]:
        return ['log: the lines with seq <= log_seq (%d) are not exactly the %d lines before the record' % (rec['log_seq'], index)], []
    cut_log = b'\n'.join(cut) + b'\n'
    findings = []
    if rec['code_sha256'] not in accepted_engines:
        findings.append('engine: the record\'s code_sha256 is not an accepted engine (%d accepted)' % len(accepted_engines))
    getter = engine_text if engine_text is not None else _default_engine_text
    at_head, why = getter(repo, rec['head'], read)
    if why is not None:
        findings.extend('engine at head_commit: %s' % w for w in why)
    elif _sha(at_head) != rec['code_sha256']:
        findings.append('engine: the SHA-256 of the engine at head_commit is not the record\'s code_sha256')
    if checked_commit is None:
        r = (read or gitread.run)(repo, ['rev-parse', '--verify', '--end-of-options', 'HEAD'], TIMEOUT)
        out = r.get('out') if isinstance(r, dict) else None
        checked_commit = out.decode('ascii', 'replace').strip() if isinstance(out, bytes) else None
    if not (isinstance(checked_commit, str) and _COMMIT.fullmatch(checked_commit)):
        findings.append('engine: the checked commit is not a commit id')
    else:
        at_tree, why = getter(repo, checked_commit, read)
        if why is not None:
            findings.extend('engine at the checked commit: %s' % w for w in why)
        elif at_head is not None and _sha(at_tree) != _sha(at_head):
            findings.append('engine at head_commit differs from the checked tree\'s engine; no historical-engine loader (erratum E1)')
        elif _sha(at_tree) != rec['code_sha256']:
            findings.append('engine: the SHA-256 of the engine at the checked commit is not the record\'s code_sha256')
    if findings:
        return findings, []
    builder = build_inputs if build_inputs is not None else _default_build_inputs
    inputs, why = builder(repo, rec['head'], rec['task_id'], cut_log, rec['runtime'], read)
    if why is not None:
        return ['inputs: %s' % w for w in why], []
    eng = engine
    if not isinstance(inputs, dict) or set(inputs) != set(eng.INPUT_KEYS):
        return ['inputs: the keys are not exactly the engine\'s INPUT_KEYS'], []
    out = eng.check(inputs, rec['code_sha256'])
    if not isinstance(out, dict):
        return ['engine: check did not return a mapping'], []
    notes = []
    differing = []
    for key in sorted(set(out) | set(rec['payload'])):
        a = out.get(key, _ABSENT)
        b = rec['payload'].get(key, _ABSENT)
        if key == 'engine_identity':
            if not (isinstance(a, dict) and isinstance(b, dict)):
                differing.append('engine_identity')
                continue
            notes.append('engine_identity.python recorded %s, recomputed %s (reported only)' % (b.get('python'), a.get('python')))
            if _canon({k: v for k, v in a.items() if k != 'python'}) != _canon({k: v for k, v in b.items() if k != 'python'}):
                differing.append('engine_identity.code_sha256')
            continue
        if a is _ABSENT or b is _ABSENT or _canon(a) != _canon(b):
            differing.append(key)
    if differing:
        return ['record: the recomputed record differs from the logged one at: %s' % ', '.join(differing)], notes
    return [], notes


def replay_detail(repo, log_bytes, record_index, accepted_engines, checked_commit=None, read=None, engine=None, engine_text=None,
                  build_inputs=None):
    """(findings, notes), as _replay gives them, never raising."""
    try:
        return _replay(repo, log_bytes, record_index, accepted_engines, checked_commit, read, engine, engine_text, build_inputs)
    except Exception as exc:  # every failure is a finding
        return ['replay: a step raised %s' % type(exc).__name__], []


def replay_execution(repo, log_bytes, record_index, accepted_engines, checked_commit=None, read=None, engine=None, engine_text=None,
                     build_inputs=None):
    """(True, []) when the record at ``record_index`` is recomputed equal, else (False, findings). Never raises. With no engine given it
    refuses and imports nothing."""
    findings, notes = replay_detail(repo, log_bytes, record_index, accepted_engines, checked_commit, read, engine, engine_text, build_inputs)
    return (not findings), [_cut(f) for f in findings]


class _Captured:
    """What the capturing append answers: the evaluation reads the attribute result."""

    result = 'appended'


def _acceptance_record(lines, index):
    """(the line's event, None) or (None, a finding)."""
    try:
        event = json.loads(lines[index].decode('utf-8'))
    except (ValueError, UnicodeDecodeError, RecursionError):
        return None, 'record: line %d is not JSON' % (index + 1)
    if not isinstance(event, dict) or event.get('type') != ACCEPTANCE:
        return None, 'record: line %d is not a decision.acceptance event' % (index + 1)
    task_id = event.get('task_id')
    event_id = event.get('event_id')
    if not (isinstance(event.get('payload'), dict) and isinstance(task_id, str) and _TASK.fullmatch(task_id)
            and isinstance(event_id, str) and event_id):
        return None, 'record: line %d has no payload, task_id or event_id in form' % (index + 1)
    for key in ('fencing_token', 'corrects'):
        if key in event:
            return None, 'record: line %d holds %s, which the evaluation does not write' % (index + 1, key)
    return event, None


def _governor_gate(repo, checked_commit, governor_pin, read):
    """A finding, or None when the governor that a plain import would load is the repository's file and the governor at the
    checked commit has the pin's SHA-256. Nothing that imports the governor is imported here."""
    governor_file = os.path.join(os.path.dirname(os.path.abspath(aieos_bootstrap.__file__)), 'governor.py')
    if not _own_file(governor_file, repo, GOVERNOR_PATH):
        return 'governor: the governor file is not the repository\'s %s' % GOVERNOR_PATH
    got, found = base_files.read_file(repo, checked_commit, GOVERNOR_PATH, read)
    if found is not None:
        return 'governor at the checked commit: %s' % '; '.join(found)
    if _sha(got['text']) != governor_pin:
        return 'governor: the governor at the checked commit is not the pinned one; it is not imported'
    return None


def _manifest_finding(lines, index, task_id, commit, policy_ref, sha, provenance, governor_pin, read_json, make,
                      ci_module, event_id_of):
    """None when a manifest record of the log before the line matches the replay (task TASK-168 AC5), else one finding.
    The values of a matching manifest are compared and never used as inputs of the recomputation."""
    events = [json.loads(line.decode('utf-8')) for line in lines[:index]]
    added = [(e, e['payload']) for e in events
             if e.get('type') == 'record.added' and e.get('task_id') == task_id and isinstance(e.get('payload'), dict)]
    matched = []
    for event, payload in added:
        basis = payload.get('basis')
        if not (payload.get('evidence_type') == 'evaluation_manifest' and payload.get('commit') == commit
                and isinstance(basis, list) and len(basis) == 1 and isinstance(basis[0], str)):
            continue
        text = basis[0]
        parsed = read_json(text)
        held = parsed['value']
        keys = {'task_id', 'evaluated_commit', 'policy_ref', 'contract_sha256', 'provenance', 'ci', 'files'}
        if parsed['findings'] or not isinstance(held, dict) or set(held) - {'reviews_sha256'} != keys:
            continue
        more = {'reviews_sha256': held['reviews_sha256']} if 'reviews_sha256' in held else {}
        made = make(held['task_id'], held['evaluated_commit'], held['policy_ref'], held['contract_sha256'],
                    held['provenance'], held['ci'], held['files'], payload.get('recorder'), **more)
        if not (made['result'] == 'present' and made['text'] == text and _canon(made['record']) == _canon(payload)):
            continue
        if [held['task_id'], held['evaluated_commit'], held['policy_ref'], held['contract_sha256']] != [
                task_id, commit, policy_ref, sha]:
            continue
        ci = held['ci']
        if not _ci_matches(ci, task_id, commit, sha, ci_module):
            continue
        given = {'pin': 'given', 'value': governor_pin}
        logged = {'pin': 'ci_log', 'value': governor_pin, 'logs': len(ci['runs'])}
        wanted = [logged if entry == given else entry for entry in provenance]
        if _canon(held['provenance']) != _canon(wanted):
            continue
        if event.get('event_id') != event_id_of(task_id, made['record']['record_id']):
            continue
        matched.append(payload)
    if not matched:
        return 'manifest: no manifest record of the log before the line matches'
    for record in matched:
        ident = record['record_id']
        if any(other.get('record_id') == ident and _canon(other) != _canon(record) for _, other in added):
            return 'manifest: the log holds another record under the record_id %s' % ident
    return None


def _ci_matches(ci, task_id, commit, sha, ci_module):
    """Whether the ci mapping of a manifest has the form ci_evidence gives for this task, commit and contract."""
    if not (isinstance(ci, dict) and set(ci) == {'head_sha', 'workflow_path', 'detect_line', 'contract_sha256', 'runs'}):
        return False
    line = ci['detect_line']
    detect = ci_module._DETECT.fullmatch(line) if isinstance(line, str) else None
    if not (ci['head_sha'] == commit and ci['contract_sha256'] == sha and ci['workflow_path'] == ci_module._WORKFLOW
            and detect is not None and detect.group(1) == task_id):
        return False
    runs = ci['runs']
    if not (isinstance(runs, list) and runs):
        return False
    order = []
    for run in runs:
        if not (isinstance(run, dict) and set(run) == {'run_id', 'attempt', 'log_sha256'}
                and all(type(run[k]) is int and run[k] > 0 for k in ('run_id', 'attempt'))
                and isinstance(run['log_sha256'], str) and _HEX64.fullmatch(run['log_sha256'])):
            return False
        order.append((run['run_id'], run['attempt']))
    return all(a < b for a, b in zip(order, order[1:]))


def _replay_acceptance(repo, log_bytes, index, governor_pin, checked_commit, read):
    """The findings of the replay of one decision.acceptance line; an empty list is a pass. The caller has passed the
    engine gate, because the reader of contracts imports the Resume Check."""
    def git(where, args, timeout=TIMEOUT):
        return read(where, args, timeout)

    try:
        report = records.check_log(log_bytes)
        found = ['log: line %d: %s' % (n, f) for n, f in report.findings()]
        if found:
            return found
        if not log_bytes.endswith(b'\n'):
            return ['log: the log does not end with LF']
        lines = log_bytes.split(b'\n')[:-1]
        if index >= len(lines):
            return ['record: index %d is past the %d lines of the log' % (index, len(lines))]
        event, finding = _acceptance_record(lines, index)
        if finding is not None:
            return [finding]
        first = report.lines[index].duplicate_of
        if first is not None:
            return ['record: line %d is an ignored duplicate of line %d, which the writer never writes' % (index + 1, first)]
        if lines[index] != eventlog._canonical(event).encode('ascii'):
            return ['record: line %d is not in the form the writer writes' % (index + 1)]
        if index == 0:
            return ['log: a record on the first line has no earlier line to recompute from']
        earlier = _form_findings(b'\n'.join(lines[:index]) + b'\n', report)
        if earlier:
            return earlier
        task_id, payload = event['task_id'], event['payload']
        if payload.get('ruleset_version') != RULESET_PREFIX + governor_pin:
            return ['record: ruleset_version is not "%s" and the governor pin' % RULESET_PREFIX]
        finding = _governor_gate(repo, checked_commit, governor_pin, read)
        if finding is not None:
            return [finding]
        cut_log = b'\n'.join(lines[:index]) + b'\n'
        # every module below is the governor or imports it, directly or through its own imports: only after the gate
        from aieos_bootstrap import (ci_evidence, eval_inputs, evaluate_command, evaluation, evaluation_intake,
                                     evaluation_sources, governor)
        state = evaluation._task_events(lambda _root: cut_log, repo, task_id)
        approved_hash, commit = state[0], state[3]
        answer = git(repo, ['cat-file', '-p', commit])
        if not (isinstance(answer, dict) and answer.get('error') is None and answer.get('exit') == 0):
            return ['record: the evaluated commit %s cannot be read in this checkout' % commit]
        contract, sha, contract_bytes = evaluate_command._contract(repo, commit, task_id, approved_hash, git)
        policy_ref = evaluate_command._policy_ref(contract, commit)
        loaded = evaluation_sources.load_sources(repo, policy_ref, commit, task_id, None, git, pin=governor_pin)
        if loaded['result'] != 'present':
            return ['sources: %s: %s' % (f['reason'], f['detail']) for f in loaded['findings']]
        if not evaluate_command._same_contract(loaded.get('provenance'), sha, commit):
            return ['sources: the loader\'s contract digest or commit differs from the replay\'s']
        # the argument checks of eval_inputs over the same values; the runs and the log payloads are passed empty
        wrong = eval_inputs._argument_error(task_id, commit, policy_ref, contract, sha, loaded['changed_paths'], [],
                                            loaded['sources'], [], payload.get('recorder'))
        if wrong is not None:
            return ['inputs: argument: %s' % wrong]
        declared, values, _, refusal = eval_inputs._assemble(contract, loaded['changed_paths'], loaded['sources'])
        if refusal is not None:
            return ['inputs: %s: %s' % refusal]
        derived, held = None, None
        try:
            derived = governor.derive_inputs(eval_inputs._copy(values))
        except Exception as exc:
            held = exc
        detail = eval_inputs._incomplete(derived, held)
        if detail is not None:
            return ['inputs: incomplete: %s' % detail]
        finding = _manifest_finding(lines, index, task_id, commit, policy_ref, sha, loaded['provenance'], governor_pin,
                                    evaluation_sources.parse_json, evaluation_intake.manifest, ci_evidence,
                                    evaluate_command._event_id)
        if finding is not None:
            return [finding]
        calls = []

        def capture(root, event_type, record, event_id, appended_at, recorder, task_id=None):
            calls.append((event_type, record, event_id, task_id))
            return _Captured()

        now = datetime.datetime.strptime(event['appended_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)
        out = evaluation.evaluate_task(repo, repo, task_id, contract_bytes, declared, values, [], payload.get('recorder'),
                                       now, read=git, read_log=lambda _root: cut_log, append=capture)
        if out['result'] != 'evaluated' or len(calls) != 1:
            return ['evaluate: the evaluation gave %s (%s) with %d appends: %s'
                    % (out['result'], out['reason'], len(calls), '; '.join(out['findings']))]
        event_type, record, event_id, recomputed_task = calls[0]
        differing = [name for name, a, b in (('type', event_type, event['type']), ('event_id', event_id, event['event_id']),
                                             ('task_id', recomputed_task, task_id)) if a != b]
        for key in sorted(set(record) | set(payload)):
            a = record.get(key, _ABSENT)
            b = payload.get(key, _ABSENT)
            if a is _ABSENT or b is _ABSENT or _canon(a) != _canon(b):
                differing.append(key)
        if differing:
            return ['record: the recomputed record differs from the logged one at: %s' % ', '.join(differing)]
        return []
    except Exception as exc:  # every refusal of a called function and every exception is a finding
        told = getattr(exc, 'findings', None)
        told = [f for f in told if isinstance(f, str)] if isinstance(told, list) else []
        return told or ['acceptance: the replay raised %s' % type(exc).__name__]


def config_refused(output):
    """(the refused keys of ``git config --list -z`` output, None) or (None, a finding). A key is refused when, ASCII-lowercased,
    it begins with b'filter.' or equals b'core.worktree'; the output must be bytes ending in NUL and hold no empty key."""
    if not isinstance(output, bytes):
        return None, 'tree: the configuration answer is not bytes'
    parts = output.split(b'\0')
    if parts[-1] != b'':
        return None, 'tree: the configuration answer does not end in NUL'
    refused = []
    for part in parts[:-1]:
        key = part.split(b'\n', 1)[0]
        if key == b'':
            return None, 'tree: the configuration answer has an empty key'
        low = key.lower()
        if low.startswith(b'filter.') or low == b'core.worktree':
            refused.append(key)
    return refused, None


def engine_file_matches(engine_file, repo):
    """Whether ``engine_file`` is the repository's own engine path (a path comparison; no file is read)."""
    return _own_file(engine_file, repo, ENGINE_PATH)


def _own_file(file, repo, path):
    """Whether ``file`` is the repository's own file at ``path`` (a path comparison; no file is read)."""
    if not (isinstance(file, str) and isinstance(repo, str)):
        return False
    want = os.path.normcase(os.path.abspath(repo + '/' + path))
    return os.path.normcase(os.path.abspath(file)) == want


def _tree_findings(repo, read):
    """(the checked HEAD, findings): the configuration read first, then the status read; any refusal is a finding."""
    c = read(repo, list(gitread.CONFIG_LIST), TIMEOUT)
    if not (isinstance(c, dict) and c.get('error') is None and c.get('exit') == 0):
        return None, ['tree: git config gave no answer']
    refused, found = config_refused(c.get('out'))
    if found is not None:
        return None, [found]
    if refused:
        return None, ['tree: the configuration names %d filter driver or work tree keys' % len(refused)]
    s = read(repo, list(gitread.STATUS_HEAD) + [gitread.EXCLUDE_MAGIC + STATE_EXCLUDE], TIMEOUT)
    if not (isinstance(s, dict) and s.get('error') is None and s.get('exit') == 0 and isinstance(s.get('out'), bytes)):
        return None, ['tree: git status gave no answer']
    if s['out'] != b'':
        return None, ['tree: the working tree has changes against HEAD (%d bytes of git status)' % len(s['out'])]
    r = read(repo, ['rev-parse', '--verify', '--end-of-options', 'HEAD'], TIMEOUT)
    out = r.get('out') if isinstance(r, dict) else None
    head = out.decode('ascii', 'replace').strip() if isinstance(out, bytes) else ''
    if not (isinstance(r, dict) and r.get('exit') == 0 and _COMMIT.fullmatch(head)):
        return None, ['tree: rev-parse HEAD gave no commit id']
    return head, []


def _main(argv, read, out, engine):
    """The body of the command-line entry (see main)."""
    read = read if read is not None else gitread.run
    eng = engine
    args = list(argv)
    if not args:
        out('usage: decision_replay <repo> [%s <sha256>] [<accepted engine sha256> ...]' % GOVERNOR_FLAG)
        return 1
    repo, pins = args[0], args[1:]
    governor_pin = None
    if GOVERNOR_FLAG in pins:
        at = pins.index(GOVERNOR_FLAG)
        if pins.count(GOVERNOR_FLAG) != 1 or at + 1 >= len(pins) or _HEX64.fullmatch(pins[at + 1]) is None:
            out('FAIL: %s is given once, followed by 64 lowercase hex characters' % GOVERNOR_FLAG)
            return 1
        governor_pin = pins[at + 1]
        pins = pins[:at] + pins[at + 2:]
    bad = [p for p in pins if _HEX64.fullmatch(p) is None]
    if bad:
        out('FAIL: an accepted engine argument is not 64 lowercase hex characters')
        return 1
    why = gitread.form_error(repo, ['rev-parse', '--verify', '--end-of-options', 'HEAD'], TIMEOUT)
    if why is not None:
        out('FAIL: %s' % why)
        return 1
    # the engine file that a plain import would load, from the package's own file (the engine is not imported yet), or the injected engine's file
    engine_file = (getattr(eng, '__file__', None) if eng is not None
                   else os.path.join(os.path.dirname(os.path.abspath(aieos_bootstrap.__file__)), 'resume_check.py'))
    if not engine_file_matches(engine_file, repo):
        out('FAIL: the engine file is not the repository\'s %s' % ENGINE_PATH)
        return 1
    head, found = _tree_findings(repo, read)
    if found:
        for f in found:
            out('FAIL: %s' % f)
        return 1
    paths, found = base_files.list_paths(repo, head, '', read)
    if found is not None:
        for f in found:
            out('FAIL: tree listing: %s' % _cut(f))
        return 1
    files = [p for p in paths if p == EVENTS_NAME or p.endswith('/' + EVENTS_NAME)]
    # the engine gate (erratum E1.7): the engine is imported only when its SHA-256 at the checked HEAD is one of the pins
    engine_gate = None
    at_head, why = _default_engine_text(repo, head, read)
    if why is not None:
        engine_gate = 'engine at the checked commit: %s' % _cut('; '.join(why))
    elif _sha(at_head) not in pins:
        engine_gate = 'engine: the engine at the checked commit is not an accepted engine (%d accepted); it is not imported' % len(pins)
    total = replayed = failed = skipped = 0
    for path in files:
        got, found = base_files.read_file(repo, head, path, read)
        if found is not None:
            failed += 1
            out('FAIL: %s: %s' % (_safe(path), _cut('; '.join(found))))
            continue
        log_bytes = got['text'].encode('utf-8')
        report = records.check_log(log_bytes)
        for n, f in report.findings():
            failed += 1
            out('FAIL: %s: log: line %s: %s' % (_safe(path), n, _cut(f)))
        form = _form_findings(log_bytes, report)
        for f in form:
            failed += 1
            out('FAIL: %s: %s' % (_safe(path), f))
        lines = log_bytes.split(b'\n')
        for index, line in enumerate(lines):
            names = b'decision.acceptance' in line or b'decision.execution' in line
            try:
                event = json.loads(line.decode('utf-8'))
            except (ValueError, UnicodeDecodeError, RecursionError):
                if names:
                    total += 1
                    failed += 1
                    out('FAIL: %s:%d: an unparsable line names a decision record' % (_safe(path), index + 1))
                continue
            if not isinstance(event, dict):
                if names:
                    total += 1
                    failed += 1
                    out('FAIL: %s:%d: a line that is not an object names a decision record' % (_safe(path), index + 1))
                continue
            kind = event.get('type')
            if kind not in ('decision.execution', 'decision.acceptance'):
                continue
            total += 1
            rid = _safe(event.get('payload', {}).get('record_id') if isinstance(event.get('payload'), dict) else None)
            seq = _safe(event.get('seq'))
            where = '%s %s:%s' % (rid, _safe(path), seq)
            if form:
                failed += 1
                out('FAIL %s: log: the file is not in the form the writer writes' % where)
                continue
            if kind == ACCEPTANCE and governor_pin is None:
                failed += 1
                out('NOT REPLAYED: decision.acceptance %s: no governor pin was given' % where)
                continue
            if engine_gate is not None:
                failed += 1
                out('FAIL %s: %s' % (where, engine_gate))
                continue
            if kind != ACCEPTANCE and violation_path_record(lines, index):
                skipped += 1
                out('NOT REPLAYED: violation-path record (no Resume Check ran) %s' % where)
                continue
            if kind == ACCEPTANCE:
                findings, notes = _replay_acceptance(repo, log_bytes, index, governor_pin, head, read), []
            else:
                if eng is None:
                    eng = _engine_module()
                findings, notes = replay_detail(repo, log_bytes, index, pins, head, read, eng)
            if findings:
                failed += 1
                out('FAIL %s: %s' % (where, _safe(_cut('; '.join(findings)))))
            else:
                replayed += 1
                out('REPLAYED %s ok' % where)
            for note in notes:
                out('NOTE %s' % _safe(note))
    if not files:
        out('NOTE: no tracked file is named %s' % EVENTS_NAME)
    for limit in LIMITS:
        out('LIMIT: %s' % limit)
    out('replay: event logs %d, decision records: %d, replayed and passed: %d, failed: %d, not replayed (violation path): %d' % (len(files), total, replayed, failed, skipped))
    return 0 if failed == 0 else 1


def main(argv, read=None, out=print, engine=None):
    """The command-line entry: 0 only when every decision record of the tree was replayed and passed, a recognised record of the violation path excepted (task TASK-141); any exception is a failure line
    and the exit code 1."""
    try:
        return _main(argv, read, out, engine)
    except Exception as exc:  # the entry never raises: an exception is a failure
        try:
            out('FAIL: the entry stopped: %s' % type(exc).__name__)
        except Exception:  # a failing output function cannot be reported through itself
            return 1
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
