"""The replay of logged decision.execution records (task TASK-139; constitution INV-010; specification 3 section 11 (a decision is
recomputable from its record, the repository and the event log); decisions D-6310, D-6312, D-6314, D-6315, D-6316 and, for the
erratum E1 to the contract, D-6325 and D-6327): it recomputes one logged decision.execution record with the Resume Check and reports
every difference, and it fails closed on everything else.

``replay_execution(repo, log_bytes, record_index, accepted_engines, checked_commit=None, read=None, engine=None, engine_text=None,
build_inputs=None)`` returns (True, []) or (False, findings), findings being non-empty strs, and never raises; with no ``engine`` given it
refuses and imports nothing (erratum E1.7). ``record_index`` is the 0-based position of the record among the lines of the log
(``log_bytes`` is the whole log). ``main(argv, read=None, out=print)``
is the command-line entry (run as ``PYTHONPATH=src python -B -P -m aieos_bootstrap.decision_replay <repo> [<accepted engine sha256> ...]``, erratum E1.7)
and returns the exit code, 0 only when every decision record of the checked tree was replayed and passed, a recognised record of the violation path excepted (task TASK-141).

What a replay does, in order (each step a failure with its finding when it does not hold):
1. The log is checked by records.check_log; the record is the line ``record_index``: a decision.execution event with a task_id and a payload
   holding head_commit (a commit id), log_seq (an int), engine_identity (code_sha256, python) and runtime (adapter, max_risk); its own
   seq is log_seq + 1 (erratum E1.1: the record is not one of its own inputs).
2. The log is cut at the lines with seq <= log_seq; they must be exactly the lines before ``record_index`` (a log with a line out of order
   fails). The cut log is the log of the recomputation, as the launcher read it when it granted the start.
3. The engine (erratum E1.1, decision D-6325). The Resume Check is the checked tree's src/aieos_bootstrap/resume_check.py, reached
   by a plain import statement (no exec, no compile, no importlib: the deterministic_rule step of the CI refuses them). The replay
   calls its check only when all four values are equal: (a) the SHA-256 of the engine text at head_commit, (b) the record's
   engine_identity.code_sha256, (c) the SHA-256 of the same file at the checked commit, and (d) one of ``accepted_engines``; each text
   is read through base_files.read_file and hashed as launcher.py hashes it (the text encoded as UTF-8; raw git bytes are not used: the hash is of the text
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
decision.acceptance line is reported "NOT REPLAYED: decision.acceptance" and fails (their replay is a separate task); no record is
skipped or counted as passing without a replay, with ONE exception (task TASK-141): a record of the violation path, recognised by violation_path_record
(the form that violation.py writes and the earlier violation.detected line that it names), is reported "NOT REPLAYED: violation-path record (no Resume Check ran)"
and counted apart; it is neither replayed nor counted as passed or as failed, because no Resume Check ran for it (violation.py UNCOVERED).

Limits, stated (erratum E1; D-6314 C2 and C3; D-6313 C5):
- The reader modules (resume_inputs, resume_log_inputs, execution, base_files, gitread and records, whose check_log is used) are those of
  the commit that the CI checks out, never of a local working tree, and only the engine is tied to head_commit by its hash. A pass shows
  that the record is reproducible by the checked tree's readers and the pinned engine, NOT that it is what head_commit's readers computed.
- Any difference, including one that a later reader change causes, fails closed, with no skip list. The named remedy for a historical
  record that a reader change makes differ is to load the readers from head_commit, to be ruled on by the decision agent.
- This module and the reader modules run from the tree under check, not from a base or a pinned ref, so GOV-003 is not met by them: a change that
  alters them can change what passes. Only the engine is pinned (decision D-6332).
- After a pinned engine upgrade, records written under the old engine fail closed ("no historical-engine loader") until such a loader
  exists; it is a later task, not this one.
- runtime.max_risk is taken from the record: the launcher reads it from the adapter declaration (launcher.py), which the replay does not
  repeat. The held lease is None and ``now`` is a fixed constant, which only the argument checks of task_view use.
- The replay of decision.acceptance records is not done here: their inputs (evaluation.py's declared and values) have no assembler in src.
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


# erratum E1.7 (decision D-6333): a guard placed before every other import of this module. It detects a run without -P only; a module that
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
from aieos_bootstrap import base_files, gitread, records, violation

ENGINE_PATH = 'src/aieos_bootstrap/resume_check.py'
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
    'decision.acceptance records are not replayed and fail this entry; the python value of engine_identity is reported, not compared',
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
    and whose task_id is the same. Every other line is not one. ``lines`` is the log split at newlines, ``index`` the 0-based position of the
    line. Never raises."""
    try:
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
    if not (isinstance(engine_file, str) and isinstance(repo, str)):
        return False
    want = os.path.normcase(os.path.abspath(repo + '/' + ENGINE_PATH))
    return os.path.normcase(os.path.abspath(engine_file)) == want


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
        out('usage: decision_replay <repo> [<accepted engine sha256> ...]')
        return 1
    repo, pins = args[0], args[1:]
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
            if kind == 'decision.acceptance':
                failed += 1
                out('NOT REPLAYED: decision.acceptance %s' % where)
                continue
            if violation_path_record(lines, index):
                skipped += 1
                out('NOT REPLAYED: violation-path record (no Resume Check ran) %s' % where)
                continue
            if engine_gate is not None:
                failed += 1
                out('FAIL %s: %s' % (where, engine_gate))
                continue
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
    """The command-line entry: 0 only when every decision record of the tree was replayed and passed; any exception is a failure line
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
