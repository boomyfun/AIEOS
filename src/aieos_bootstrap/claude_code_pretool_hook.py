"""The PreToolUse hook program of the Claude Code adapter (task TASK-072, H2b; specification 5 revision 4, :59-61,
:79-82 and :104-119; specification 3 revision 5, :19, :20, :25 and :177; concept line 945).

A program for a PreToolUse hook: before a tool call it ties the call to the session's one live lease, reads the lease
task's contract at the base the launcher gives, judges the call against that contract's write-set and, for a Bash or
PowerShell call, the shell allowlist read at that base from the policy file and the contract (TASK-076), and records
every refusal on the write-set, git push or the shell allowlist through the core's violation
path. Here no hook is placed: nothing wires this program into Claude Code, no matcher is chosen and no setting
is changed by this task; placing it is the owner's (A51 item (4)), and the launcher that sets AIEOS_SESSION_ID,
AIEOS_ROOT and AIEOS_BASE is specification 7's and not built here.

``run(stdin_bytes, environ, working_folder, now, clock=None)`` judges one hook call, every outside value an argument,
and returns a mapping with exactly exit_code, outcome ("allow" or "refuse"), reason (a word of REASONS) and findings.
clock is a function of no argument that gives the current time in UTC rounded up to the next whole second; when it is
not given, now is used in its place (a stated limit, for tests). Its flow, in this order, the first step that ends
giving the result; the findings hold only this module's fixed words and exception type names, nothing copied from the
store's, the judge's or the core's findings, from standard input, from the environment or from a path:

1. The tie: claude_code_store.judge(the session id, the root, the working folder, now), the two names read only through
   environ.get. "enforce_nothing" gives exit code 0, "allow", reason "enforce_nothing". "refuse" gives exit code 2,
   "refuse", reason "store", the store's reason word as the one finding when it is one of the store lookup's fixed
   reasons, else "store: other"; nothing is recorded. "tied" goes on with the lease's task and the root; any other
   answer (a lease task not of the form TASK-<digits> among them) gives reason "entry". The session id must then be
   a str of [A-Za-z0-9._-]{1,128}; one that is not gives
   reason "store", the finding "store: session id form", and nothing is recorded.
2. The base: AIEOS_BASE, read through environ.get, must be exactly 40 lowercase hexadecimal characters: the tip of the
   base branch (main for the self-build) at the grant, which holds the approved contract from its commit C on; never
   the contract's own input_state.base_commit, at which the contract file does not exist. One absent, empty or out of
   form is read as a contract not readable at the base: reason "base", with the record of step 3.
3. The contract: the contract reader's read of the task's contract at the base (the state directory's tasks folder
   first, then docs/tasks/<task>.yaml, by contract_path's shared resolution), with no runner passed. Any result
   other than "read" is unreadable: a refusal on the write-set concern, recorded, STOP: violation (specification 5
   :113), on every concern alike, a Read call included (a stated choice, fail closed). Its record is built here in the
   judge's record form, evidence type write_outside_write_set and the fixed refers_to "the task contract is not
   readable at the base", checked by claude_code_channel.record_findings and left unchanged by redact; its ids carry
   "/pretool-contract/" in place of "/pretool/". Reason "contract" (or "base"). A "read" whose write_set is not a
   non-empty list of str counts as unreadable too.
4. The judgement: claude_code_hook.entry with the contract's write-set and the shell allowlist: for a call whose
   tool_name, read by a strict parse as strict as the entry's, is exactly Bash or PowerShell, the one list of
   the shell allowlist reader (read_allowlist of claude_code_shell_allow, given the root, the base and the task), read
   only here, on the judged path; for any other tool,
   a parse failure, a reader answer of another shape or an exception from the reader, an empty allowlist (fail
   closed: a shell call is then refused; other tools are unaffected). "allow" (a Read, Grep or
   Glob call, or a write inside the write-set) gives exit code 0, "allow", reason "tied_allow"; "uncovered" gives reason
   "uncovered" and nothing recorded (none of section 8's concerns); "refuse" with a record goes to step 5; "refuse"
   without a record (the entry's or the judge's argument refusals, a malformed allowlist, a record the judge's own check
   refused) gives reason "no_record", nothing recorded; any other answer gives reason "entry".
5. The record: the recorder is "claude_code_pretool_hook, session " followed by the session id, so the record's recorder
   holds the session id. The record must pass claude_code_channel.record_findings, its subject must be the lease's task
   and its recorder the judge's recorder for that text, and redact must give a record; else reason "record_form",
   nothing passed. The redacted record goes to the core's violation path tied by the session id, with no lookup,
   append or release passed (the run seam is closed). The time passed is clock() called once, after every other step
   and just before that call, so a lease that expired while the contract was read reads as expired. "done" gives reason
   "recorded"; a "lease" result (the lease lost between the tie and the record; a repeat after a STOP is refused
   earlier, at step 1) gives "lease_lost", nothing appended; anything else gives "core". The ids: event_id is
   "<session id>/pretool/<tool_use_id>" when the input's tool_use_id, read by the same strict parse the entry uses, is a
   str of [A-Za-z0-9_-]{1,200}, else "<session id>/pretool/sha256-<the SHA-256 of the input bytes>"; record_id is the
   same text with "/record" appended. The input bytes are hashed for any bytes object, a subclass included; an
   input that is not bytes is hashed as no bytes: on the judged path (steps 4 and 5) the entry then refuses it without
   a record, while on the bad-base and contract paths of steps 2 and 3 its record goes to step 5 (the form check,
   redaction, then the core path) with the empty-bytes hash in its ids (main passes bytes only, so main reaches
   neither). The tool_use_id and the hash are read from bytes() of the input while the entry parses the object
   itself, so a bytes subclass whose __bytes__ gives other bytes gets ids from those other bytes (main cannot reach it
   either).
6. No exception escapes run for an Exception: one gives exit code 2, "refuse", reason "entry", the type name only.

``main()`` reads standard input whole as bytes, os.environ, the process's working folder (None when os.getcwd() raises
OSError) and the clock (the process clock rounded up to the next whole second) once for now, and passes the clock
function itself to run. It writes nothing to standard output; on exit code 2 it writes to standard error the one line
"AIEOS: this tool call was refused by the AIEOS hook (<reason>)"; an exception while writing that line keeps run's exit
code; any other exception inside main gives exit code 2, reason "entry", and the line. It never returns 0 or 1 after an
exception, which, as Claude Code's documentation states (unmeasured, C6), would let the call go ahead.

Limits, stated:
- The shell allowlist (TASK-076): no policy file exists, so the policy list reads as empty and, once the owner places
  this hook, every shell call is refused (and ends the session, specification 5 :79-80) while a session holds a live
  lease, until a policy file with entries exists at the base. Each existing contract's capabilities.shell.allow reads as
  empty, by no entries or by entries outside the reader's form; only a contract written later with entries in the form
  gains any. The reader's grammars are fixed forms, narrower than YAML: any other shape reads as empty. The entry check
  accepted with TASK-062 refuses a first word such as timeout or python, so no list can allow the project's own command
  forms (for example "timeout 110 python ..."); under a placed hook those commands stay refused whatever the policy
  holds. The reader's tree walk is a copy of the contract reader's, kept in step by hand; native takeover (A11) retires
  it.
- AIEOS_BASE is a proposal, beyond specification 5 :108: a launcher that sets only the session id and the root makes
  every leased session STOP at its first judged call. And the base is fixed at the grant, so main moving during a
  session is not seen. Specification 5 :115's limit extends to the base: a nested runtime chooses its own session
  id, root and base. The hook cannot show that AIEOS_BASE is the tip of main, nor that the root and its Git state
  are untouched by the change; there is no check 0 of the contract against the approved one (specification 3
  :175). Git is trusted as the contract reader trusts it: replace refs, grafts, alternates and an outer repository
  can change what AIEOS_BASE reads as.
- The contract is read before the judgement on every judged call, reads included: up to five git calls of ten seconds
  each; for a Bash or PowerShell call the shell allowlist's reads come on top, at most seven more git calls of ten
  seconds each, twelve calls, about 120 seconds at worst for the git calls alone (the store lookup's lock wait and the
  core path's own waits come on top), against Claude Code's own hook timeout (unmeasured). Other tools keep the five
  calls. With a state folder in the base (TASK-107) the contract reader makes up to seven calls and the allowlist
  reader up to eight when that folder holds a tasks folder, fifteen calls, about 150 seconds at worst for the git calls
  alone, and thirteen calls (six and seven) when it holds the policy file only.
- The contract's forbidden list: forbidden is not enforced by this hook (specification 5 :109 names only
  write_set.paths); the gates find a forbidden path afterwards.
- Calls refused without a record: after a lease expires, every hook call is refused without a record until the
  launcher ends the session; during a long commit the store lookup is refused without a record too (its lock cost);
  on the judged path (steps 4 and 5) a root that is not a Windows absolute path makes every call a refusal with no
  record and no STOP (the bad-base and contract paths of steps 2 and 3 still pass their record).
- For these, no STOP is recorded by this hook: "record_form", "lease_lost" and "core"; for the first two the record
  is not accepted; "core" may follow a record already appended, a STOP included (the core path's partial outcome or its
  ending after the record); a departure from specification 5 :79 and :104 of the same kind as "no_record".
- A path under the root equal to the fixed refers_to of step 3 reads the same in a record.
- Exit codes and blocking are cited from Claude Code's documentation and are unmeasured (C6); a BaseException that is
  not an Exception is not caught, and a kill (a timeout among them) may leave the call refused or allowed and nothing
  recorded. Standard input is read whole, with no size bound of its own.
- The tie, the contract reader and the judge compose here on a Windows root; CI runs on Linux, so that composition and
  the real-store path of a record and then a repeat are shown only with stand-ins.

This module opens no file, starts no process, keeps no state between calls and reaches the store and the event log
only through the store lookup and the core's violation path. It names the project-state directory only by that phrase.
"""

import datetime
import hashlib
import json
import os
import re
import sys

from aieos_bootstrap import claude_code
from aieos_bootstrap import claude_code_channel
from aieos_bootstrap import claude_code_hook
from aieos_bootstrap import claude_code_shell_allow
from aieos_bootstrap import claude_code_store
from aieos_bootstrap import session_violation
from aieos_bootstrap import task_contract

SESSION_VAR = 'AIEOS_SESSION_ID'
ROOT_VAR = 'AIEOS_ROOT'
BASE_VAR = 'AIEOS_BASE'
SHELL_TOOLS = ('Bash', 'PowerShell')
OUTCOMES = ('allow', 'refuse')
REASONS = ('enforce_nothing', 'tied_allow', 'store', 'base', 'contract', 'uncovered', 'no_record', 'record_form',
           'recorded', 'lease_lost', 'core', 'entry')
RESULT_KEYS = ('exit_code', 'outcome', 'reason', 'findings')
# The store lookup's fixed refusal reasons: claude_code_store's own and the writer's session lookup's.
STORE_REASONS = ('argument', 'root_without_session', 'session_without_root', 'search', 'entry', 'root', 'no_store',
                 'link', 'unreadable', 'tables', 'lease_row_without_session', 'no_lease_row', 'session', 'ended',
                 'leases')
RECORDER_TEXT = 'claude_code_pretool_hook, session '
NOT_READABLE = 'the task contract is not readable at the base'
STDERR_LINE = 'AIEOS: this tool call was refused by the AIEOS hook (%s)\n'

_SESSION = re.compile(r'[A-Za-z0-9._-]{1,128}')
_BASE = re.compile(r'[0-9a-f]{40}')
_TOOL_USE = re.compile(r'[A-Za-z0-9_-]{1,200}')
_TASK = re.compile(r'TASK-[0-9]+')
_FINDING = {
    'uncovered': 'uncovered: the call is none of the judged concerns',
    'no_record': 'no_record: a refusal without a record',
    'record_form': 'record_form: the record is not of the judge\'s form for this session',
    'recorded': 'recorded: the refusal was passed to the core',
    'lease_lost': 'lease_lost: no live tied lease when the record was passed',
    'core': 'core: the core gave another result',
    'base': 'base: AIEOS_BASE is absent or out of form',
    'contract': 'contract: not readable at the base',
}


def _result(reason, findings=()):
    allowed = reason in ('enforce_nothing', 'tied_allow')
    return {'exit_code': 0 if allowed else 2, 'outcome': 'allow' if allowed else 'refuse', 'reason': reason,
            'findings': list(findings)}


def _fixed(reason):
    return _result(reason, [_FINDING[reason]])


def _no_duplicates(pairs):
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError('a duplicate key')
    return dict(pairs)


def _no_constant(name):
    raise ValueError('a refused constant')


def _tool_use_id(stdin_bytes):
    """The input's tool_use_id by the entry's strict parse, or None."""
    if not isinstance(stdin_bytes, bytes):
        return None
    data = bytes(stdin_bytes)
    if data.startswith(b'\xef\xbb\xbf'):
        return None
    try:
        value = json.loads(data.decode('utf-8', 'strict'), object_pairs_hook=_no_duplicates,
                           parse_constant=_no_constant)
    except (ValueError, RecursionError):
        return None
    if not isinstance(value, dict):
        return None
    found = value.get('tool_use_id')
    if type(found) is str and _TOOL_USE.fullmatch(found):
        return found
    return None


def _tool_name(stdin_bytes):
    """The input's tool_name by a strict parse as strict as _tool_use_id's, or None (TASK-076 AC6)."""
    if not isinstance(stdin_bytes, bytes):
        return None
    data = bytes(stdin_bytes)
    if data.startswith(b'\xef\xbb\xbf'):
        return None
    try:
        value = json.loads(data.decode('utf-8', 'strict'), object_pairs_hook=_no_duplicates,
                           parse_constant=_no_constant)
    except (ValueError, RecursionError):
        return None
    if not isinstance(value, dict):
        return None
    found = value.get('tool_name')
    if type(found) is str:
        return found
    return None


def _allowlist(stdin_bytes, root, base, task):
    """Step 4's shell allowlist: the one list read at the base for a Bash or PowerShell call, else [] (any other tool,
    a parse failure, a reader answer of another shape or an exception from the reader)."""
    if _tool_name(stdin_bytes) not in SHELL_TOOLS:
        return []
    try:
        answer = claude_code_shell_allow.read_allowlist(root, base, task)
    except Exception:
        return []
    if not isinstance(answer, dict):
        return []
    found = answer.get('allowlist')
    if type(found) is not list or not all(type(e) is str for e in found):
        return []
    return list(found)


def _ids(session_id, stdin_bytes, segment):
    """(event_id, record_id) of step 5; segment is "pretool" or "pretool-contract"."""
    found = _tool_use_id(stdin_bytes)
    if found is None:
        data = bytes(stdin_bytes) if isinstance(stdin_bytes, bytes) else b''
        found = 'sha256-' + hashlib.sha256(data).hexdigest()
    event_id = session_id + '/' + segment + '/' + found
    return event_id, event_id + '/record'


def _tie(answer, session_id):
    """Step 1: (an ending result, None) or (None, (root, task)) for a live tie."""
    if not isinstance(answer, dict) or set(answer) != set(claude_code_store.KEYS):
        return _result('entry', ['entry: judge']), None
    outcome = answer['outcome']
    if outcome == 'enforce_nothing':
        return _result('enforce_nothing'), None
    if outcome == 'refuse':
        word = answer['reason']
        return _result('store', [word if type(word) is str and word in STORE_REASONS else 'store: other']), None
    lease, root = answer['lease'], answer['root']
    if (outcome != 'tied' or answer['reason'] != 'tied' or type(lease) is not dict or type(root) is not str
            or not root or type(lease.get('task_id')) is not str or not _TASK.fullmatch(lease['task_id'])):
        return _result('entry', ['entry: judge']), None
    if type(session_id) is not str or not _SESSION.fullmatch(session_id):
        return _result('store', ['store: session id form']), None
    return None, (root, lease['task_id'])


def _contract_record(record_id, recorder, task):
    """Step 3's record, in the judge's record form."""
    return {'record_id': record_id, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
            'outcome': 'blocking', 'blocking_kind': 'violation',
            'recorder': claude_code.RECORDER + claude_code_channel.RECORDER_JOIN + recorder, 'subject': task,
            'evidence_type': 'write_outside_write_set', 'refers_to': NOT_READABLE}


def _write_set(read):
    """Step 3: the write-set of a "read" result, or None for any other result."""
    if not isinstance(read, dict) or read.get('result') != 'read':
        return None
    paths = read.get('write_set')
    if type(paths) is not list or not paths or not all(type(p) is str for p in paths):
        return None
    return list(paths)


def _record(root, session_id, task, recorder, record, event_id, now, clock, done):
    """Step 5: check, redact and pass the record; done is the reason a "done" gives."""
    if claude_code_channel.record_findings(record):
        return _fixed('record_form')
    if record['subject'] != task or \
            record['recorder'] != claude_code.RECORDER + claude_code_channel.RECORDER_JOIN + recorder:
        return _fixed('record_form')
    redacted = claude_code_channel.redact(record)
    if not isinstance(redacted, dict):
        return _fixed('record_form')
    at = now if clock is None else clock()
    answer = session_violation.session_violation(root, session_id, redacted, event_id, recorder, at)
    if not isinstance(answer, dict):
        return _fixed('core')
    if answer.get('result') == 'done':
        return _fixed(done)
    if answer.get('result') == 'refused' and answer.get('reason') == 'lease':
        return _fixed('lease_lost')
    return _fixed('core')


def _run(stdin_bytes, environ, working_folder, now, clock):
    session_id = environ.get(SESSION_VAR)
    ended, tie = _tie(claude_code_store.judge(session_id, environ.get(ROOT_VAR), working_folder, now), session_id)
    if ended is not None:
        return ended
    root, task = tie
    recorder = RECORDER_TEXT + session_id
    base = environ.get(BASE_VAR)
    paths = None
    if type(base) is str and _BASE.fullmatch(base):
        paths = _write_set(task_contract.read_contract(root, base, task))
        bad = 'contract'
    else:
        bad = 'base'
    if paths is None:
        event_id, record_id = _ids(session_id, stdin_bytes, 'pretool-contract')
        return _record(root, session_id, task, recorder, _contract_record(record_id, recorder, task), event_id, now,
                       clock, bad)
    event_id, record_id = _ids(session_id, stdin_bytes, 'pretool')
    allowlist = _allowlist(stdin_bytes, root, base, task)
    judged = claude_code_hook.entry(stdin_bytes, root, task, paths, allowlist, record_id, recorder)
    if not isinstance(judged, dict) or set(judged) != set(claude_code_hook.RESULT_KEYS):
        return _result('entry', ['entry: judgement'])
    verdict = judged['verdict']
    if verdict == 'allow':
        return _result('tied_allow')
    if verdict == 'uncovered':
        return _fixed('uncovered')
    if verdict != 'refuse':
        return _result('entry', ['entry: judgement'])
    if judged['record'] is None:
        return _fixed('no_record')
    return _record(root, session_id, task, recorder, judged['record'], event_id, now, clock, 'recorded')


def run(stdin_bytes, environ, working_folder, now, clock=None):
    """The judgement of one PreToolUse hook call (the module docstring states the flow and the limits): a mapping with
    exactly RESULT_KEYS. Never raises for an Exception."""
    try:
        return _run(stdin_bytes, environ, working_folder, now, clock)
    except Exception as e:
        return _result('entry', ['entry: ' + type(e).__name__])


def _raw_clock():
    return datetime.datetime.now(datetime.timezone.utc)


def _whole_second_now():
    now = _raw_clock()
    if now.microsecond:
        now = now.replace(microsecond=0) + datetime.timedelta(seconds=1)
    return now


def _say(reason):
    """Writes the standard-error line; False when the write raised (the exit code is kept either way)."""
    try:
        sys.stderr.write(STDERR_LINE % reason)
    except Exception:
        return False
    return True


def main():
    """The hook's process: standard input, the environment, the working folder and the clock to run; returns run's exit
    code, and 2 after any exception. Writes nothing to standard output."""
    try:
        stdin_bytes = sys.stdin.buffer.read()
        try:
            working_folder = os.getcwd()
        except OSError:
            working_folder = None
        result = run(stdin_bytes, os.environ, working_folder, _whole_second_now(), _whole_second_now)
        code, reason = result['exit_code'], result['reason']
        if code != 0 and reason not in REASONS:
            reason = 'entry'
    except Exception:
        code, reason = 2, 'entry'
    if code != 0:
        code = 2
        _say(reason)
    return code


if __name__ == '__main__':
    sys.exit(main())
