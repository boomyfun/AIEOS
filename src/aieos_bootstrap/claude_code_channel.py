"""The Claude Code adapter's channel to the core, part CC-2 part 2 (task TASK-063; specification 5 revision 3, sections 6
and 8 and section 11 points 5 and 7; specification 2 revision 6, section 6.2; working record DEF-0079).

Four functions, called only by their tests:

1. ``context_findings(context)``: the form of the per-session context a hook call needs (AC1). An empty list of
   findings means the context is well formed.
2. ``record_findings(record)``: whether a record has the exact form that aieos_bootstrap.claude_code.judge gives a
   refusal (AC2). A record of any other form is never passed to the core.
3. ``redact(record)``: the record with its refers_to redacted (AC3, AC4), or None for a record of another form.
4. ``deliver(context, hook_result, event_id, now, append=None, release=None)``: for a refusal of
   aieos_bootstrap.claude_code_hook.entry that carries a record of judge's form belonging to the context, the record is
   redacted and passed once to the core through aieos_bootstrap.adapter.violation (AC5).

The context (AC1, AC7): exactly root, task_id, session_id, fencing_token, write_set, allowlist and recorder.
- root is one root, for judging and for the core's writer, which keeps its store under the root (writer.py:11).
- The lease is tied by fencing_token, the token that adapter.start's grant returns.
- The session is tied in words only, by a recorder that holds session_id verbatim: records.py accepts a session key on
  a record since specification 2 revision 10 (TASK-077), but the record judge gives has none, this module writes none,
  and adapter.violation takes no session id. The core does not check it.
  The tie is a substring test, so a very short session_id ties weakly.
- The write-set (proposed): the caller takes it from the lease's task contract at the base, the contract's
  write_set.paths, the same key the Resume Check reads from the contract it is given (resume_check.py:290, :405).
  This module reads no file; it checks only the form, as judge does.
- The allowlist is the caller's policy (specification 5 section 11 point 6); only its form is checked, by
  claude_code_hook.allowlist_findings.
- The root and write-set forms are copies of judge's own argument check (claude_code.py:99, :101, :273-279), not
  calls of it, so the two could drift apart; no test ties them.

Redaction (DEF-0079; AC3, AC4):
- A record of evidence_type git_push_refused or shell_not_allowed gets a fixed refers_to for its type: no part of the
  command text, no first word and no hash of it is kept. Judge cut the text to 200 characters, so a hash would be of
  the cut text, and a hash of a short text holding a short secret can be found by guessing. Keeping a first word or a
  hash is a later choice, not taken. So the shell command is recorded redacted, not as typed: a departure from
  specification 5 section 6's table, whose row for the shell allowlist records "the command" (its git push row records
  only "a refusal"; the command text of a git push refusal comes from judge's record).
- A record of evidence_type write_outside_write_set keeps refers_to only in judge's root-relative form: non-empty, no
  ":", no "\\", no leading "/", and no empty, "." or ".." segment; otherwise a fixed text. Why this catches every path
  outside the root (claude_code.py:61-66, :169, :183-186): judge gives a path inside the root in the "/"-joined
  root-relative form with no drive, and a path outside it as given, which is always absolute with a drive, since
  relative and driveless rooted paths are "uncovered" there; so every path outside the root holds a ":". Limit,
  stated: a file or folder name under the root can itself hold a secret; segments are not hashed, since the path under
  the root is the evidence that scenario ADV-02 and the gates need.
- The test is chosen by the record's evidence_type, which is trusted: judge gives write_outside_write_set only for a
  path (claude_code.py:309), so a forged record of that type whose refers_to holds other text with no ":", no "\\" and
  no leading "/" would be kept. The record is the caller's input; this is a stated limit.

deliver (AC5, AC7):
- entry's exit code and standard-error text are never changed: hook_result is not changed, and the caller keeps
  entry's exit code.
- hook_result is checked only for its key set, its verdict, its exit code for that verdict (0 for "allow", else 2) and
  that a record goes with "refuse" alone; its standard-error text, concern, reason and findings are not checked, nor the
  record's evidence_type against the concern; the record inside it is checked further in _deliver (record_findings, its
  subject against the task_id, its recorder against the context's). now, append and release are not checked here: a fault in them surfaces
  only through adapter.violation, as a "core" refusal, or as "deliver" when an exception escapes it.
- Nothing is written for "allow", for "uncovered", or for a "refuse" without a record. The last (entry's reasons
  argument, allowlist_form and record) is a caller's error; it is a departure from specification 5 section 8, which
  records every refusal by a hook.
- The result's findings hold only this module's own fixed words, an exception's type, and adapter.violation's findings
  for the redacted record; no text of hook_result's findings or of the original refers_to is copied into the result.
  The original refers_to's text is read as the text that redaction removes: a root-relative path that AC4 keeps is part
  of the redacted record, and so is in the result's record.
- The result "written" means adapter.violation gave "done", which includes its "duplicate" for a repeated event_id:
  nothing new is appended then. After an exception, the result's record is the redacted record when adapter.violation
  was already called with it, and None otherwise; when adapter.violation itself raised, whether anything was written
  is then not known.
- The module writes only through adapter.violation, which writes through the core's writer (INV-004); append and
  release are passed on, so tests pass stand-ins. It opens no file itself, starts no process, reads no clock or
  environment and makes no network or model call; it is not pure, since adapter.violation writes.

The ids (AC6): event_id and the record's record_id are the caller's, and only their form is checked. A repeated
event_id gives adapter.violation's "duplicate": nothing is appended and it is no error. A repeated record_id of a kept
blocking record can make a later evaluation of the task refuse (violation.py:35-38), unless it repeats a kept blocking
record's record_id with the same blocking_kind and subject. record_id is form-checked only and is not redacted, so text
in a forged record's record_id would reach the core and deliver's result; it is the caller's input, a stated limit.
How a hook process makes the
ids is left to the task that starts the hook process; the candidates are named, not decided: the hook input's
tool_use_id (entry does not read it today) and a counter per session (which needs state across hook processes).

What is not covered (AC7):
- A hook that does not fire neither refuses nor records (specification 5 section 8), and a refusal that the hook
  process never delivers (a crash, a timeout, a missing context) is lost; the gates find a violation afterwards. Both
  are unmeasured (C6, the owner's).
- How a hook process obtains the context and how it is started are out of this task: they belong with placing the
  hook (part CC-3, the owner's act, A51 item (4)) and with INV-004.
- No observed read-set record is made (specification 5 section 11 point 4's record needs state across hook calls).
- Mapping or string subclasses that override their methods are outside the trusted-caller model: the checks read them as
  their methods answer.
- Every limit of aieos_bootstrap.claude_code and aieos_bootstrap.claude_code_hook holds here too; specification 5
  section 11 points 10 (an abnormal session end) and 12 (a bound on repeated STOP: violation) stay open. Nothing is
  installed or measured, and no test asserts anything about a running Claude Code.
"""

import re

from aieos_bootstrap import adapter
from aieos_bootstrap import claude_code
from aieos_bootstrap import claude_code_hook

CONTEXT_KEYS = ('root', 'task_id', 'session_id', 'fencing_token', 'write_set', 'allowlist', 'recorder')
RECORD_KEYS = ('record_id', 'fact_kind', 'source_class', 'outcome', 'blocking_kind', 'recorder', 'subject',
               'evidence_type', 'refers_to')
EVIDENCE_TYPES = ('write_outside_write_set', 'git_push_refused', 'shell_not_allowed')
FIXED = {'fact_kind': 'observation', 'source_class': 'deterministic_tool_local', 'outcome': 'blocking',
         'blocking_kind': 'violation'}
REDACTED = {
    'git_push_refused': 'a git push command; its text is not kept (D-1262 M2)',
    'shell_not_allowed': 'a shell command; its text is not kept (D-1262 M2)',
    'write_outside_write_set': 'a path outside the root; it is not kept (D-1262 M3)',
}
RESULT_KEYS = ('result', 'reason', 'findings', 'record', 'core')
REASONS = ('context', 'hook_result', 'event_id', 'allow', 'uncovered', 'no_record', 'record', 'core', 'deliver')
RECORDER_JOIN = ', for '

# The same forms judge's argument check uses for root and for write-set patterns (claude_code.py:99, :101).
_ABS = re.compile(r'[A-Za-z]:[\\/]')
_PATTERN = re.compile(r'[A-Za-z0-9._*/-]+')
_TASK = re.compile(r'TASK-[0-9]+')
_NO_SPACE = re.compile(r'\S+')


def _result(result, reason, findings=(), record=None, core=None):
    return {'result': result, 'reason': reason, 'findings': list(findings), 'record': record, 'core': core}


def _text(value):
    return isinstance(value, str) and value != ''


def _token_form(token):
    return (isinstance(token, dict) and set(token) == {'epoch', 'counter'} and _text(token['epoch'])
            and type(token['counter']) is int and token['counter'] >= 0)


def _context_findings(context):
    if not isinstance(context, dict):
        return ['context is not a mapping']
    f = []
    if set(context) != set(CONTEXT_KEYS):
        f.append('context does not have exactly the keys ' + ', '.join(CONTEXT_KEYS))
        return f
    root = context['root']
    if not isinstance(root, str) or not _ABS.match(root):
        f.append('root is not an absolute Windows path')
    task_id = context['task_id']
    if not isinstance(task_id, str) or not _TASK.fullmatch(task_id):
        f.append('task_id is not "TASK-" followed by digits')
    session_id = context['session_id']
    session_ok = isinstance(session_id, str) and _NO_SPACE.fullmatch(session_id) is not None
    if not session_ok:
        f.append('session_id is not a non-empty string with no whitespace')
    if not _token_form(context['fencing_token']):
        f.append('fencing_token is not {epoch: a non-empty string, counter: an int at least 0}')
    ws = context['write_set']
    if (not isinstance(ws, list) or not ws
            or not all(isinstance(p, str) and _PATTERN.fullmatch(p) and '' not in p.split('/') for p in ws)):
        f.append('write_set is not a non-empty list of patterns of the risk rules section 2 point 6')
    if claude_code_hook.allowlist_findings(context['allowlist']):
        f.append('allowlist is not well formed by claude_code_hook.allowlist_findings')
    recorder = context['recorder']
    if not _text(recorder):
        f.append('recorder is not a non-empty string')
    elif session_ok and session_id not in recorder:
        f.append('recorder does not hold session_id')
    return f


def context_findings(context):
    """The findings of the context's form (AC1); empty only when it is well formed. No exception escapes."""
    try:
        return _context_findings(context)
    except Exception as e:  # noqa: BLE001 - any exception becomes a finding, its type only
        return ['%s raised inside context_findings' % type(e).__name__]


def _record_findings(record):
    if not isinstance(record, dict):
        return ['record is not a mapping']
    if set(record) != set(RECORD_KEYS):
        return ['record does not have exactly the keys of judge\'s records']
    f = []
    for key, value in FIXED.items():
        if record[key] != value:
            f.append('record %s is not %s' % (key, value))
    for key in ('record_id', 'subject', 'refers_to'):
        if not _text(record[key]):
            f.append('record %s is not a non-empty string' % key)
    if not (isinstance(record['recorder'], str) and record['recorder'].startswith(claude_code.RECORDER + RECORDER_JOIN)):
        f.append('record recorder does not begin with judge\'s recorder')
    if record['evidence_type'] not in EVIDENCE_TYPES:
        f.append('record evidence_type is not one of ' + ', '.join(EVIDENCE_TYPES))
    return f


def record_findings(record):
    """The findings of the record's form (AC2); empty only when it has judge's exact form. No exception escapes."""
    try:
        return _record_findings(record)
    except Exception as e:  # noqa: BLE001 - any exception becomes a finding, its type only
        return ['%s raised inside record_findings' % type(e).__name__]


def _root_relative(text):
    # the leading "/" and empty-text tests are also caught by the empty-segment test below; kept as explicit forms
    if not text or ':' in text or '\\' in text or text.startswith('/'):
        return False
    return all(segment not in ('', '.', '..') for segment in text.split('/'))


def redact(record):
    """A new record equal to record except refers_to, redacted (AC3, AC4); None for a record with a finding under
    record_findings. The given record is never changed."""
    if record_findings(record):
        return None
    out = dict(record)
    kind = record['evidence_type']
    if kind == 'write_outside_write_set':
        if not _root_relative(record['refers_to']):
            out['refers_to'] = REDACTED[kind]
    else:
        out['refers_to'] = REDACTED[kind]
    return out


def _hook_result_ok(hook_result):
    if not isinstance(hook_result, dict) or set(hook_result) != set(claude_code_hook.RESULT_KEYS):
        return False
    verdict = hook_result['verdict']
    if verdict not in claude_code.VERDICTS:
        return False
    code = hook_result['exit_code']
    if type(code) is not int or code != (0 if verdict == 'allow' else 2):
        return False
    return verdict == 'refuse' or hook_result['record'] is None


def _deliver(context, hook_result, event_id, now, append, release, state):
    found = context_findings(context)
    if found:
        return _result('refused', 'context', found)
    if not _hook_result_ok(hook_result):
        return _result('refused', 'hook_result', ['hook_result is not a result of claude_code_hook.entry\'s form'])
    if not (isinstance(event_id, str) and _NO_SPACE.fullmatch(event_id)):
        return _result('refused', 'event_id', ['event_id is not a non-empty string with no whitespace'])
    verdict = hook_result['verdict']
    if verdict == 'allow':
        return _result('nothing', 'allow')
    if verdict == 'uncovered':
        return _result('nothing', 'uncovered')
    record = hook_result['record']
    if record is None:
        return _result('nothing', 'no_record')
    found = list(record_findings(record))
    if not found:
        if record['subject'] != context['task_id']:
            found.append('record subject is not the context\'s task_id')
        if record['recorder'] != claude_code.RECORDER + RECORDER_JOIN + context['recorder']:
            found.append('record recorder is not judge\'s recorder for the context\'s recorder')
    if found:
        return _result('refused', 'record', found)
    passed = redact(record)
    state['passed'] = passed
    core = adapter.violation(context['root'], context['task_id'], context['fencing_token'], passed, event_id,
                             context['recorder'], now, append=append, release=release)
    if isinstance(core, dict) and core.get('result') == 'done':
        return _result('written', None, [], passed, core)
    core_found = core.get('findings') if isinstance(core, dict) else None
    findings = ['adapter.violation did not give "done"'] + [str(x) for x in (core_found or [])]
    return _result('refused', 'core', findings, passed, core)


def deliver(context, hook_result, event_id, now, append=None, release=None):
    """Pass a refusal's redacted record to the core once, through adapter.violation (AC5): a mapping with exactly
    RESULT_KEYS. No exception escapes."""
    state = {}
    try:
        return _deliver(context, hook_result, event_id, now, append, release, state)
    except Exception as e:  # noqa: BLE001 - any exception becomes a result, its type only
        # AC5: the record passed, when adapter.violation was already called with it, else None
        return _result('refused', 'deliver', ['%s raised inside deliver' % type(e).__name__], state.get('passed'))
