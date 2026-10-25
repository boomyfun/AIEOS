"""The bootstrap's command-line entry point and its commands, tasks, end and status (tasks TASK-091, TASK-092 and
TASK-093; specification 7 revision 2, section 3 :26, :31, :32, :33-34; section 5 :45, :48; section 10 points 5, 10, 11
and 15).

What it does:
- It is run as ``python -m aieos_bootstrap.cli <command> [flags]``; the installed name is open (specification 7 :26),
  and "aieos <command>" in texts means that run form. ``main(argv, stdout, environ, clock)`` returns 0, 1 or 2 and
  never raises: every Exception is caught; KeyboardInterrupt and SystemExit are not. os.environ is read only in the
  entry line.
- Its own parser, not argparse: argv is exactly a list of str; argv[0] is a command of COMMANDS, tasks, end or
  status; end takes its session as argv[1]; the flags are --root <path> (required, once, a non-empty value not
  beginning "--") and --json (optional, once). Anything else gives exit 2 and USAGE, with neither the clock nor a
  command's callee called.
- tasks calls the clock once, then execution.list_tasks(root, now) once, looked up at each call. A list gives exit 0
  and one line "<task> <state> <contract_hash> lease=<lease>" per item (or "no task may be taken"), or under --json
  one JSON line; findings give exit 1 and one "finding: <text>" line each (or one JSON line), list_tasks' str findings
  printed as given, and "tasks: list_tasks gave no finding" when none is left; an answer out of form gives the finding
  "tasks: list_tasks gave an answer out of form"; a raise in the clock or list_tasks gives "tasks: a step raised
  <type>". _render makes the lines of an answer; _findings, a separate fixed function, makes every finding. A raise in
  the parser or in _render gives exit 1 and "cli: a step raised <type>". The whole output is written by one
  stdout.write call, then flush when the sink has one; a write or a flush that raises gives exit 1.
- tasks writes nothing: it reads the log and the store through list_tasks' readers (whose held_leases takes the
  store's write lock for its read, changing no content).
- end <session> (task TASK-092) ends a crashed session from outside the runtime through launcher.end_outside: the
  session must fully match SESSION (mcp_server._SESSION's pattern), not be "." or "..", and not begin with "-". After
  the parse, it is refused inside a runtime: in_runtime(environ) true gives exit 1 and the one finding "end: refused
  inside a runtime (spec 7 :34)", with neither the clock nor end_outside called; else the clock once, then
  launcher.end_outside(root, session, now, RECORDER) once, looked up at each call. "done" gives exit 0 and the lines
  "record: <line>", then "released: <task>" (or "ended, no lease released"), then "finding: <text>", or under --json
  one JSON line of findings, records and released; "refused" gives exit 1 and the findings "end: <reason>", the record
  lines and end_outside's findings; an answer out of form gives "end: end_outside gave an answer out of form"; a raise
  in the clock or end_outside gives "end: a step raised <type>". end writes the core's store and log through the
  writer; it starts no process.
- status (task TASK-093; specification 7 :31), ``aieos status``, gives the project's status through
  execution.status_report: the clock once, then execution.status_report(root, now) once, looked up at each call; it
  does not call in_runtime (spec 7 :34 names only end and launch). An answer gives exit 0 and the lines "progress:
  <task> <state>" per approved task, " stale" added when its stale_evidence is true (or "progress: no approved task"),
  then "drift: not available", "waiting for approval: not available" and "requirements lacking assurance: not
  available", or under --json one JSON line; findings give exit 1 and one "finding: <text>" line each, status_report's
  str findings printed as given, and "status: status_report gave no finding" when none is left; an answer out of form,
  its types checked exactly, gives "status: status_report gave an answer out of form"; a raise in the clock or
  status_report gives "status: a step raised <type>", and a raise in _render_status "cli: a step raised <type>".
  status writes nothing: status_report reads the log once and reads no store.
- RUNTIME_VARS and in_runtime(environ): outside any runtime means none of the three names is in the environment.
  in_runtime is true when any of them is present; AIEOS_BASE is counted beside the session id and the root, and a
  name whose value is '' counts as present (two stated choices, both fail-closed); an environment whose membership
  test raises counts as inside. tasks and status do not call it; end calls it after the parse; launch, which also
  refuses inside a runtime, comes with a later task.

Limits, stated: a determined agent can start a nested runtime with an environment it chooses (spec 5 :120); a root
value beginning "--" cannot be given; a root that names no folder gives only list_tasks' "a step raised" finding; a
non-ASCII value in the text form on a stdout in a legacy code page raises at the write (exit 1); a stdout in Windows
text mode writes CRLF. __init__.py is not changed, and its module list stays as it was. Nothing runs this module but
its tests and the owner's own use.
"""

import datetime
import json
import os
import re
import sys

from aieos_bootstrap import execution
from aieos_bootstrap import launcher

RUNTIME_VARS = ('AIEOS_SESSION_ID', 'AIEOS_ROOT', 'AIEOS_BASE')
COMMANDS = ('tasks', 'end', 'status')
USAGE = ('usage: python -m aieos_bootstrap.cli tasks --root <path> [--json]\n'
         '       python -m aieos_bootstrap.cli end <session> --root <path> [--json]\n'
         '       python -m aieos_bootstrap.cli status --root <path> [--json]\n'
         '  tasks          the tasks that may be taken\n'
         '  end <session>  end a crashed session from outside the runtime\n'
         '  status         the status of the project\n'
         '  --root <path>  the project root (required)\n'
         '  --json         one JSON line in place of text lines\n')
OUT_OF_FORM = 'tasks: list_tasks gave an answer out of form'
NO_FINDING = 'tasks: list_tasks gave no finding'
_ITEM_KEYS = ('task', 'state', 'contract_hash', 'lease')
SESSION = r'[A-Za-z0-9._-]{1,128}'
RECORDER = 'aieos cli end'
RUNTIME_REFUSAL = 'end: refused inside a runtime (spec 7 :34)'
END_OUT_OF_FORM = 'end: end_outside gave an answer out of form'
NO_LEASE = 'ended, no lease released'
_VALUE_OUT_OF_FORM = "end: end_session's value is out of form"
STATUS_OUT_OF_FORM = 'status: status_report gave an answer out of form'
STATUS_NO_FINDING = 'status: status_report gave no finding'
_PROGRESS_KEYS = ('task', 'state', 'stale_evidence')


def in_runtime(environ):
    """True when any name of RUNTIME_VARS is in environ, '' counting as present; true when the test raises."""
    try:
        return any(name in environ for name in RUNTIME_VARS)
    except Exception:
        return True


def _session_in_form(session):
    return (re.fullmatch(SESSION, session) is not None and session not in ('.', '..')
            and not session.startswith('-'))


def _parse(argv):
    """(command, session, root, as_json) for a well-formed argv, else None (a usage error)."""
    if type(argv) is not list or not argv or any(type(a) is not str for a in argv):
        return None
    if argv[0] not in COMMANDS:
        return None
    command, session, rest = argv[0], None, argv[1:]
    if command == 'end':
        if not rest or not _session_in_form(rest[0]):
            return None
        session, rest = rest[0], rest[1:]
    root, as_json, i = None, False, 0
    while i < len(rest):
        flag = rest[i]
        if flag == '--root':
            if root is not None or i + 1 >= len(rest):
                return None
            value = rest[i + 1]
            if not value or value.startswith('--'):
                return None
            root, i = value, i + 2
        elif flag == '--json':
            if as_json:
                return None
            as_json, i = True, i + 1
        else:
            return None
    if root is None:
        return None
    return command, session, root, as_json


def _findings(texts, as_json):
    """The output of findings: one "finding: <text>" line each, or one JSON line."""
    if as_json:
        return json.dumps({'findings': list(texts)}, sort_keys=True) + '\n'
    return ''.join('finding: %s\n' % text for text in texts)


def _render(answer, as_json):
    """The output of tasks' list: one line per item, "no task may be taken" for none, or one JSON line."""
    if as_json:
        return json.dumps({'tasks': answer}, sort_keys=True) + '\n'
    if not answer:
        return 'no task may be taken\n'
    return ''.join('%s %s %s lease=%s\n' % (item['task'], item['state'], item['contract_hash'], item['lease'])
                   for item in answer)


def _item_in_form(item):
    return (type(item) is dict and len(item) == len(_ITEM_KEYS) and all(k in item for k in _ITEM_KEYS)
            and all(type(item[k]) is str for k in _ITEM_KEYS))


def _tasks(root, clock):
    """(0, 'tasks', the list) or (1, 'findings', the texts)."""
    try:
        now = clock()
        answer = execution.list_tasks(root, now)
    except Exception as exc:
        return 1, 'findings', ['tasks: a step raised %s' % type(exc).__name__]
    if type(answer) is not tuple or len(answer) != 2:
        return 1, 'findings', [OUT_OF_FORM]
    value, found = answer
    if value is None:
        texts = [f for f in found if isinstance(f, str)] if isinstance(found, (list, tuple)) else []
        return 1, 'findings', texts or [NO_FINDING]
    if type(value) is not list or found is not None or not all(_item_in_form(item) for item in value):
        return 1, 'findings', [OUT_OF_FORM]
    return 0, 'tasks', value


def _str_list(value):
    return type(value) is list and all(type(v) is str for v in value)


def _end_in_form(answer):
    return (type(answer) is dict and len(answer) == len(launcher.OUTSIDE_KEYS)
            and all(k in answer for k in launcher.OUTSIDE_KEYS) and answer['result'] in ('done', 'refused')
            and (answer['result'] == 'done' or type(answer['reason']) is str)
            and _str_list(answer['records']) and _str_list(answer['released']) and _str_list(answer['findings']))


def _end(session, root, as_json, environ, clock):
    """(the exit code, the whole output) of end."""
    if in_runtime(environ):
        return 1, _findings([RUNTIME_REFUSAL], as_json)
    try:
        now = clock()
        answer = launcher.end_outside(root, session, now, RECORDER)
    except Exception as exc:
        return 1, _findings(['end: a step raised %s' % type(exc).__name__], as_json)
    if not _end_in_form(answer):
        return 1, _findings([END_OUT_OF_FORM], as_json)
    records, released, found = answer['records'], answer['released'], answer['findings']
    if answer['result'] == 'refused':
        return 1, _findings(['end: %s' % answer['reason']] + ['record: %s' % r for r in records] + found, as_json)
    if as_json:
        return 0, json.dumps({'findings': found, 'records': records, 'released': released}, sort_keys=True) + '\n'
    lines = ['record: %s' % r for r in records] + ['released: %s' % t for t in released]
    if not released and _VALUE_OUT_OF_FORM not in found:
        lines.append(NO_LEASE)
    lines += ['finding: %s' % f for f in found]
    return 0, ''.join(line + '\n' for line in lines)


def _progress_in_form(item):
    return (type(item) is dict and len(item) == len(_PROGRESS_KEYS) and all(k in item for k in _PROGRESS_KEYS)
            and type(item['task']) is str and type(item['state']) is str and type(item['stale_evidence']) is bool)


def _status_in_form(value):
    others = [k for k in execution.STATUS_KEYS if k != 'progress']
    return (type(value) is dict and len(value) == len(execution.STATUS_KEYS)
            and all(k in value for k in execution.STATUS_KEYS) and type(value['progress']) is list
            and all(_progress_in_form(item) for item in value['progress'])
            and all(type(value[k]) is str and value[k] == execution.NOT_AVAILABLE for k in others))


def _render_status(answer, as_json):
    """The output of status' answer: the progress lines and the three other items, or one JSON line."""
    if as_json:
        return json.dumps({'drift': answer['drift'], 'progress': answer['progress'],
                           'requirements_lacking_assurance': answer['requirements_lacking_assurance'],
                           'waiting_for_approval': answer['waiting_for_approval']}, sort_keys=True) + '\n'
    lines = ['progress: %s %s%s' % (item['task'], item['state'], ' stale' if item['stale_evidence'] else '')
             for item in answer['progress']] or ['progress: no approved task']
    lines += ['drift: %s' % answer['drift'], 'waiting for approval: %s' % answer['waiting_for_approval'],
              'requirements lacking assurance: %s' % answer['requirements_lacking_assurance']]
    return ''.join(line + '\n' for line in lines)


def _status(root, as_json, clock):
    """(the exit code, the whole output) of status."""
    try:
        now = clock()
        answer = execution.status_report(root, now)
    except Exception as exc:
        return 1, _findings(['status: a step raised %s' % type(exc).__name__], as_json)
    if type(answer) is not tuple or len(answer) != 2:
        return 1, _findings([STATUS_OUT_OF_FORM], as_json)
    value, found = answer
    if value is None:
        texts = [f for f in found if isinstance(f, str)] if isinstance(found, (list, tuple)) else []
        return 1, _findings(texts or [STATUS_NO_FINDING], as_json)
    if found is not None or not _status_in_form(value):
        return 1, _findings([STATUS_OUT_OF_FORM], as_json)
    return 0, _render_status(value, as_json)


def _run(argv, environ, clock):
    """(the exit code, the whole output)."""
    try:
        parsed = _parse(argv)
    except Exception as exc:
        return 1, _findings(['cli: a step raised %s' % type(exc).__name__], False)
    if parsed is None:
        return 2, USAGE
    command, session, root, as_json = parsed
    if command == 'end':
        try:
            return _end(session, root, as_json, environ, clock)
        except Exception as exc:
            return 1, _findings(['cli: a step raised %s' % type(exc).__name__], as_json)
    if command == 'status':
        try:
            return _status(root, as_json, clock)
        except Exception as exc:
            return 1, _findings(['cli: a step raised %s' % type(exc).__name__], as_json)
    code, kind, payload = _tasks(root, clock)
    if kind == 'findings':
        return code, _findings(payload, as_json)
    try:
        return code, _render(payload, as_json)
    except Exception as exc:
        return 1, _findings(['cli: a step raised %s' % type(exc).__name__], as_json)


def main(argv, stdout, environ, clock):
    """Run one command; return 0, 1 or 2; never raise an Exception. environ is read by end, after the parse, through
    in_runtime; tasks and status do not read it."""
    try:
        code, text = _run(argv, environ, clock)
    except Exception:
        return 1
    try:
        stdout.write(text)
        flush = getattr(stdout, 'flush', None)
        if flush is not None:
            flush()
    except Exception:
        return 1
    return code


def _clock():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:], sys.stdout, os.environ, _clock))
