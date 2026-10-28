"""The bootstrap's command-line entry point and its commands, tasks, end, status, init, launch, approve, edit, reject
and import (tasks TASK-091, TASK-092, TASK-093, TASK-095, TASK-094, TASK-096 and TASK-097; specification 7 revision
2, section 3 :26, :28, :29, :31, :32, :33-35; section 4; section 5 :45, :48; section 10 points 4, 5, 6, 10, 11 and
15).

What it does:
- It is run as ``python -m aieos_bootstrap.cli <command> [flags]``; the installed name is open (specification 7 :26),
  and "aieos <command>" in texts means that run form. ``main(argv, stdout, environ, clock, starter=None)`` returns 0,
  1 or 2 and never raises: every Exception is caught; KeyboardInterrupt and SystemExit are not. os.environ is read only
  in the entry line, which passes no starter.
- Its own parser, not argparse: argv is exactly a list of str; argv[0] is a command of COMMANDS, tasks, end, status,
  init, launch, approve, edit, reject or import; end takes its session as argv[1], and launch, approve, edit, reject
  and import their task as argv[1]; the flags are --root <path> (required, once, a non-empty value not beginning "--")
  and --json (optional, once); approve, edit and reject also take --class and --by (each required, once) and edit
  --note (required, once, edit only). Anything else gives exit 2 and USAGE, with neither the clock nor a command's
  callee called.
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
- init (task TASK-095; specification 7 :28), ``aieos init``, creates the folders of the project-state layout the
  owner settled, through launcher.init_project, which calls the writer. After the parse it is refused inside a
  runtime: in_runtime(environ) true gives exit 1 and the one finding INIT_RUNTIME_REFUSAL, with init_project not
  called (stricter than spec 7 :34, since init writes); else launcher.init_project(root) once, looked up at each call;
  it calls no clock. "done" gives exit 0 and one line "created: <path>" per folder, or under --json one JSON line of
  created and findings; "refused" gives exit 1 and the findings "init: <reason>" then init_project's findings; an
  answer out of form, its types checked exactly, gives "init: init_project gave an answer out of form"; a raise in
  init_project gives "init: a step raised <type>", and a raise in _render_init "cli: a step raised <type>". init
  creates folders only, through the writer, and is refused where a project-state directory exists.
- launch <task> (task TASK-094; specification 7 :34-35), ``aieos launch``, launches a session for the task from
  outside the runtime through launcher.launch_outside; the task must fully match TASK. After the parse it is refused
  inside a runtime: in_runtime(environ) true gives exit 1 and the one finding LAUNCH_RUNTIME_REFUSAL; else, with no
  starter (main's starter is None, and the entry line passes none), it gives exit 1 and the one finding NO_STARTER, no
  runtime starter being shipped, with neither the clock nor launch_outside called; else
  launcher.launch_outside(root, task, clock, starter) once, looked up at each call. "done" gives exit 0 and the lines
  "session: <id>", "run: returned", "end: done" and "handoff: <written or none>", then "finding: <text>" per finding,
  or under --json one JSON line of session_id and findings; "not granted" and "refused" give exit 1 and the findings
  "launch: <result> <reason>" then the answer's findings; an answer out of form, its types checked exactly, gives
  LAUNCH_OUT_OF_FORM; a raise in launch_outside gives "launch: a step raised <type>", and a raise in _render_launch
  "cli: a step raised <type>". As shipped, launch starts no runtime: starting one stays the owner's (spec 7 :35).
- approve <task>, edit <task> and reject <task> (task TASK-096; specification 7 section 4, specification 1 section
  12), ``aieos approve``, ``aieos edit`` and ``aieos reject``, record an approval, an edit note or a rejection of the
  task's drafted contract version through launcher.approval_act, which writes through the writer. --class is
  decision_agent or human_authority, with no default, and --by the decision id or the person's name; the class and the
  name are the caller's statement, not checked. After the parse each is refused inside a runtime: in_runtime(environ)
  true gives exit 1 and the one finding APPROVAL_RUNTIME_REFUSAL filled with the command; else
  launcher.approval_act(root, task, act, class, by, note, clock) once, looked up at each call. "done" gives exit 0 and
  the lines "record: <id>" and "event: <id> <appended or duplicate>" per event, then "finding: <text>" per finding, or
  under --json one JSON line of record_id, event_ids, appends and findings; "refused" gives exit 1 and the findings
  "<command>: refused <reason>" then the answer's findings, its record_id and event ids not printed; an answer out of
  form, its types checked exactly, gives "<command>: approval_act gave an answer out of form"; a raise in approval_act
  gives "<command>: a step raised <type>", and a raise in _render_approval "cli: a step raised <type>". approve writes a
  contract-kind approval and task.approved; it writes nothing the governor counts at acceptance.
- import <task> (task TASK-097; specification 7 section 3 :29), ``aieos import``, makes and records a drafting task
  through launcher.import_task, which fills a fixed template with the task and HEAD, writes the contract through the
  writer and appends task.drafted; it drafts nothing: reading the repository and drafting the proposals are a
  launched session's, the owner's. After the parse it is refused inside a runtime: in_runtime(environ) true gives exit
  1 and the one finding IMPORT_RUNTIME_REFUSAL; else launcher.import_task(root, task, clock) once, looked up at each
  call. "done" gives exit 0 and the lines "contract: <path> <hash>" and "event: <id> <appended or duplicate>", then
  "finding: <text>" per finding, or under --json one JSON line of path, contract_hash, event_id, append and findings;
  "refused" gives exit 1 and the findings "import: refused <reason>" then the answer's findings; an answer out of form,
  its types checked exactly, gives IMPORT_OUT_OF_FORM; a raise in import_task gives "import: a step raised <type>",
  and a raise in _render_import "cli: a step raised <type>". It is not run on any real project: its real use is the
  owner's, asked separately.
- RUNTIME_VARS and in_runtime(environ): outside any runtime means none of the three names is in the environment.
  in_runtime is true when any of them is present; AIEOS_BASE is counted beside the session id and the root, and a
  name whose value is '' counts as present (two stated choices, both fail-closed); an environment whose membership
  test raises counts as inside. tasks and status do not call it; end and init call it after the parse; launch also
  calls it after the parse, then refuses with no starter; approve, edit and reject also call it after the parse; import
  also calls it after the parse.

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
COMMANDS = ('tasks', 'end', 'status', 'init', 'launch', 'approve', 'edit', 'reject', 'import')
USAGE = ('usage: python -m aieos_bootstrap.cli tasks --root <path> [--json]\n'
         '       python -m aieos_bootstrap.cli end <session> --root <path> [--json]\n'
         '       python -m aieos_bootstrap.cli status --root <path> [--json]\n'
         '       python -m aieos_bootstrap.cli init --root <path> [--json]\n'
         '       python -m aieos_bootstrap.cli launch <task> --root <path> [--json]\n'
         '       python -m aieos_bootstrap.cli approve <task> --root <path> --class <decision_agent|human_authority> '
         '--by <decision id or name> [--json]\n'
         '       python -m aieos_bootstrap.cli edit <task> --root <path> --class <decision_agent|human_authority> '
         '--by <decision id or name> --note <text> [--json]\n'
         '       python -m aieos_bootstrap.cli reject <task> --root <path> --class <decision_agent|human_authority> '
         '--by <decision id or name> [--json]\n'
         '       python -m aieos_bootstrap.cli import <task> --root <path> [--json]\n'
         '  tasks          the tasks that may be taken\n'
         '  end <session>  end a crashed session from outside the runtime\n'
         '  status         the status of the project\n'
         '  init           create the project-state layout in a folder that has none\n'
         '  launch <task>  launch a session for a task (no runtime starter is shipped)\n'
         '  approve <task> approve the task\'s drafted contract version\n'
         '  edit <task>    record an edit note on the task\'s drafted contract version\n'
         '  reject <task>  reject the task\'s drafted contract version\n'
         '  import <task>  make and record a drafting task for a repository\'s proposals\n'
         '  --root <path>  the project root (required)\n'
         '  --class <c>    who acts, decision_agent or human_authority, as the caller states it (not checked)\n'
         '  --by <who>     the decision id (decision_agent) or the name (human_authority)\n'
         '  --note <text>  the edit note (edit only)\n'
         '  --json         one JSON line in place of text lines\n')
OUT_OF_FORM = 'tasks: list_tasks gave an answer out of form'
NO_FINDING = 'tasks: list_tasks gave no finding'
_ITEM_KEYS = ('task', 'state', 'contract_hash', 'lease')
SESSION = r'[A-Za-z0-9._-]{1,128}'
TASK = r'TASK-[0-9]+'
RECORDER = 'aieos cli end'
RUNTIME_REFUSAL = 'end: refused inside a runtime (spec 7 :34)'
END_OUT_OF_FORM = 'end: end_outside gave an answer out of form'
NO_LEASE = 'ended, no lease released'
_VALUE_OUT_OF_FORM = "end: end_session's value is out of form"
STATUS_OUT_OF_FORM = 'status: status_report gave an answer out of form'
STATUS_NO_FINDING = 'status: status_report gave no finding'
_PROGRESS_KEYS = ('task', 'state', 'stale_evidence')
INIT_RUNTIME_REFUSAL = ('init: refused inside a runtime (it writes; specification 7 :34 names end and launch, and init '
                        'is refused for the same reason)')
INIT_OUT_OF_FORM = 'init: init_project gave an answer out of form'
LAUNCH_RUNTIME_REFUSAL = 'launch: refused inside a runtime (spec 7 :34)'
NO_STARTER = 'launch: no runtime starter (a runtime is started by the owner; specification 7 :35, DEF-0101)'
LAUNCH_OUT_OF_FORM = 'launch: launch_outside gave an answer out of form'
APPROVAL_COMMANDS = ('approve', 'edit', 'reject')
APPROVAL_RUNTIME_REFUSAL = ('%s: refused inside a runtime (it writes; specification 7 :34 names end and launch, and %s '
                            'is refused for the same reason)')
APPROVAL_OUT_OF_FORM = '%s: approval_act gave an answer out of form'
_APPROVAL_FLAGS = ('--class', '--by', '--note')
_APPROVAL_EVENTS = {'approve': 2, 'edit': 1, 'reject': 1}
IMPORT_RUNTIME_REFUSAL = ('import: refused inside a runtime (it writes; specification 7 :34 names end and launch, and '
                          'import is refused for the same reason)')
IMPORT_OUT_OF_FORM = 'import: import_task gave an answer out of form'


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
    """(command, session or task, root, as_json, source_class, who, note) for a well-formed argv, else None (a usage
    error); source_class, who and note are None except for approve, edit and reject."""
    if type(argv) is not list or not argv or any(type(a) is not str for a in argv):
        return None
    if argv[0] not in COMMANDS:
        return None
    command, session, rest = argv[0], None, argv[1:]
    if command == 'end':
        if not rest or not _session_in_form(rest[0]):
            return None
        session, rest = rest[0], rest[1:]
    elif command in ('launch', 'import') or command in APPROVAL_COMMANDS:
        if not rest or re.fullmatch(TASK, rest[0]) is None:
            return None
        session, rest = rest[0], rest[1:]
    allowed = ()
    if command in APPROVAL_COMMANDS:
        allowed = _APPROVAL_FLAGS if command == 'edit' else _APPROVAL_FLAGS[:2]
    root, as_json, values, i = None, False, {}, 0
    while i < len(rest):
        flag = rest[i]
        if flag == '--root' or flag in allowed:
            if (flag == '--root' and root is not None) or flag in values or i + 1 >= len(rest):
                return None
            value = rest[i + 1]
            if not value or value.startswith('--'):
                return None
            if flag == '--root':
                root = value
            else:
                values[flag] = value
            i += 2
        elif flag == '--json':
            if as_json:
                return None
            as_json, i = True, i + 1
        else:
            return None
    if root is None or set(values) != set(allowed):
        return None
    if command in APPROVAL_COMMANDS and values['--class'] not in launcher.APPROVAL_CLASSES:
        return None
    return (command, session, root, as_json, values.get('--class'), values.get('--by'), values.get('--note'))


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


def _init_in_form(answer):
    """True for init_project's mapping in form: exactly launcher.INIT_KEYS, "done" with reason None, findings [] and a
    non-empty list of str created, or "refused" with a str reason, a list of str findings and created []."""
    if type(answer) is not dict or len(answer) != len(launcher.INIT_KEYS):
        return False
    if not all(k in answer for k in launcher.INIT_KEYS):
        return False
    if type(answer['result']) is not str:
        return False
    if answer['result'] == 'done':
        return (answer['reason'] is None and type(answer['findings']) is list and answer['findings'] == []
                and _str_list(answer['created']) and len(answer['created']) > 0)
    if answer['result'] == 'refused':
        return (type(answer['reason']) is str and _str_list(answer['findings'])
                and type(answer['created']) is list and answer['created'] == [])
    return False


def _render_init(created, as_json):
    """The output of init's "done": one "created: <path>" line per folder, or one JSON line."""
    if as_json:
        return json.dumps({'findings': [], 'created': created}, sort_keys=True) + '\n'
    return ''.join('created: %s\n' % path for path in created)


def _init(root, as_json, environ):
    """(the exit code, the whole output) of init."""
    if in_runtime(environ):
        return 1, _findings([INIT_RUNTIME_REFUSAL], as_json)
    try:
        answer = launcher.init_project(root)
    except Exception as exc:
        return 1, _findings(['init: a step raised %s' % type(exc).__name__], as_json)
    try:
        in_form = _init_in_form(answer)
    except Exception:
        in_form = False
    if not in_form:
        return 1, _findings([INIT_OUT_OF_FORM], as_json)
    if answer['result'] == 'refused':
        return 1, _findings(['init: %s' % answer['reason']] + answer['findings'], as_json)
    return 0, _render_init(answer['created'], as_json)


def _launch_run_in_form(value):
    return value is None or (type(value) is str and (value == 'returned' or value.startswith('raised ')))


def _launch_in_form(answer):
    """True for launch_outside's mapping in form, its types checked exactly: exactly launcher.LAUNCH_KEYS; result
    "done", "not granted" or "refused"; findings a list of str; session_id None or a str; start, end and handoff each
    None or a dict; run None, "returned" or "raised <type>"; "done" with reason None, a str session_id, a granted start,
    run "returned", a done end and a written or empty handoff; the others with a reason of launcher.LAUNCH_REASONS."""
    if type(answer) is not dict or len(answer) != len(launcher.LAUNCH_KEYS):
        return False
    if not all(k in answer for k in launcher.LAUNCH_KEYS):
        return False
    if not (type(answer['result']) is str and answer['result'] in ('done', 'not granted', 'refused')):
        return False
    if not (_str_list(answer['findings']) and (answer['session_id'] is None or type(answer['session_id']) is str)
            and all(answer[k] is None or type(answer[k]) is dict for k in ('start', 'end', 'handoff'))
            and _launch_run_in_form(answer['run'])):
        return False
    if answer['result'] == 'done':
        return (answer['reason'] is None and type(answer['session_id']) is str and answer['run'] == 'returned'
                and answer['start'] is not None and answer['start'].get('result') == 'granted'
                and answer['end'] is not None and answer['end'].get('result') == 'done'
                and answer['handoff'] is not None and answer['handoff'].get('result') in ('written', 'none'))
    return type(answer['reason']) is str and answer['reason'] in launcher.LAUNCH_REASONS


def _render_launch(answer, as_json):
    """The output of launch's "done": the four lines, then the findings, or one JSON line."""
    if as_json:
        return json.dumps({'session_id': answer['session_id'], 'findings': answer['findings']}, sort_keys=True) + '\n'
    lines = ['session: %s' % answer['session_id'], 'run: returned', 'end: done',
             'handoff: %s' % answer['handoff']['result']]
    lines += ['finding: %s' % f for f in answer['findings']]
    return ''.join(line + '\n' for line in lines)


def _launch(task, root, as_json, environ, clock, starter):
    """(the exit code, the whole output) of launch."""
    if in_runtime(environ):
        return 1, _findings([LAUNCH_RUNTIME_REFUSAL], as_json)
    if starter is None:
        return 1, _findings([NO_STARTER], as_json)
    try:
        answer = launcher.launch_outside(root, task, clock, starter)
    except Exception as exc:
        return 1, _findings(['launch: a step raised %s' % type(exc).__name__], as_json)
    try:
        in_form = _launch_in_form(answer)
    except Exception:
        in_form = False
    if not in_form:
        return 1, _findings([LAUNCH_OUT_OF_FORM], as_json)
    if answer['result'] != 'done':
        return 1, _findings(['launch: %s %s' % (answer['result'], answer['reason'])] + answer['findings'], as_json)
    return 0, _render_launch(answer, as_json)


def _approval_in_form(answer, act):
    """True for approval_act's mapping in form, its types checked exactly: exactly launcher.APPROVAL_KEYS; result
    "done" or "refused"; findings a list of str; event_ids and appends lists of str of equal length, each append
    "appended" or "duplicate"; "done" with reason None, a str record_id and two event ids for approve, one for edit and
    reject; "refused" with a reason of launcher.APPROVAL_REASONS and a record_id None or a str."""
    if type(answer) is not dict or len(answer) != len(launcher.APPROVAL_KEYS):
        return False
    if not all(k in answer for k in launcher.APPROVAL_KEYS):
        return False
    if not (type(answer['result']) is str and answer['result'] in ('done', 'refused')):
        return False
    if not (_str_list(answer['findings']) and _str_list(answer['event_ids']) and _str_list(answer['appends'])
            and len(answer['event_ids']) == len(answer['appends'])
            and all(a in ('appended', 'duplicate') for a in answer['appends'])):
        return False
    if answer['result'] == 'done':
        return (answer['reason'] is None and type(answer['record_id']) is str
                and len(answer['event_ids']) == _APPROVAL_EVENTS[act])
    return (type(answer['reason']) is str and answer['reason'] in launcher.APPROVAL_REASONS
            and (answer['record_id'] is None or type(answer['record_id']) is str))


def _render_approval(answer, as_json):
    """The output of approve's, edit's or reject's "done": the record line and one event line per event, then the
    findings, or one JSON line."""
    if as_json:
        return json.dumps({'record_id': answer['record_id'], 'event_ids': answer['event_ids'],
                           'appends': answer['appends'], 'findings': answer['findings']}, sort_keys=True) + '\n'
    lines = ['record: %s' % answer['record_id']]
    lines += ['event: %s %s' % pair for pair in zip(answer['event_ids'], answer['appends'])]
    lines += ['finding: %s' % f for f in answer['findings']]
    return ''.join(line + '\n' for line in lines)


def _approval(act, task, root, source_class, who, note, as_json, environ, clock):
    """(the exit code, the whole output) of approve, edit or reject."""
    if in_runtime(environ):
        return 1, _findings([APPROVAL_RUNTIME_REFUSAL % (act, act)], as_json)
    try:
        answer = launcher.approval_act(root, task, act, source_class, who, note, clock)
    except Exception as exc:
        return 1, _findings(['%s: a step raised %s' % (act, type(exc).__name__)], as_json)
    try:
        in_form = _approval_in_form(answer, act)
    except Exception:
        in_form = False
    if not in_form:
        return 1, _findings([APPROVAL_OUT_OF_FORM % act], as_json)
    if answer['result'] != 'done':
        return 1, _findings(['%s: refused %s' % (act, answer['reason'])] + answer['findings'], as_json)
    return 0, _render_approval(answer, as_json)


def _none_or_str(value):
    return value is None or type(value) is str


def _import_in_form(answer):
    """True for import_task's mapping in form, its types checked exactly: exactly launcher.IMPORT_KEYS; result "done"
    or "refused"; findings a list of str; "done" with reason None, path, contract_hash and event_id each a str and
    append "appended" or "duplicate"; "refused" with a reason of launcher.IMPORT_REASONS, path, contract_hash and
    event_id each None or a str, and append None or a str."""
    if type(answer) is not dict or len(answer) != len(launcher.IMPORT_KEYS):
        return False
    if not all(k in answer for k in launcher.IMPORT_KEYS):
        return False
    if not (type(answer['result']) is str and answer['result'] in ('done', 'refused')
            and _str_list(answer['findings'])):
        return False
    if answer['result'] == 'done':
        return (answer['reason'] is None
                and all(type(answer[k]) is str for k in ('path', 'contract_hash', 'event_id'))
                and type(answer['append']) is str and answer['append'] in ('appended', 'duplicate'))
    return (type(answer['reason']) is str and answer['reason'] in launcher.IMPORT_REASONS
            and all(_none_or_str(answer[k]) for k in ('path', 'contract_hash', 'event_id', 'append')))


def _render_import(answer, as_json):
    """The output of import's "done": the contract line and the event line, then the findings, or one JSON line."""
    if as_json:
        return json.dumps({'path': answer['path'], 'contract_hash': answer['contract_hash'],
                           'event_id': answer['event_id'], 'append': answer['append'],
                           'findings': answer['findings']}, sort_keys=True) + '\n'
    lines = ['contract: %s %s' % (answer['path'], answer['contract_hash']),
             'event: %s %s' % (answer['event_id'], answer['append'])]
    lines += ['finding: %s' % f for f in answer['findings']]
    return ''.join(line + '\n' for line in lines)


def _import(task, root, as_json, environ, clock):
    """(the exit code, the whole output) of import."""
    if in_runtime(environ):
        return 1, _findings([IMPORT_RUNTIME_REFUSAL], as_json)
    try:
        answer = launcher.import_task(root, task, clock)
    except Exception as exc:
        return 1, _findings(['import: a step raised %s' % type(exc).__name__], as_json)
    try:
        in_form = _import_in_form(answer)
    except Exception:
        in_form = False
    if not in_form:
        return 1, _findings([IMPORT_OUT_OF_FORM], as_json)
    if answer['result'] != 'done':
        return 1, _findings(['import: refused %s' % answer['reason']] + answer['findings'], as_json)
    return 0, _render_import(answer, as_json)


def _run(argv, environ, clock, starter=None):
    """(the exit code, the whole output)."""
    try:
        parsed = _parse(argv)
    except Exception as exc:
        return 1, _findings(['cli: a step raised %s' % type(exc).__name__], False)
    if parsed is None:
        return 2, USAGE
    command, session, root, as_json, source_class, who, note = parsed
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
    if command == 'init':
        try:
            return _init(root, as_json, environ)
        except Exception as exc:
            return 1, _findings(['cli: a step raised %s' % type(exc).__name__], as_json)
    if command == 'launch':
        try:
            return _launch(session, root, as_json, environ, clock, starter)
        except Exception as exc:
            return 1, _findings(['cli: a step raised %s' % type(exc).__name__], as_json)
    if command in APPROVAL_COMMANDS:
        try:
            return _approval(command, session, root, source_class, who, note, as_json, environ, clock)
        except Exception as exc:
            return 1, _findings(['cli: a step raised %s' % type(exc).__name__], as_json)
    if command == 'import':
        try:
            return _import(session, root, as_json, environ, clock)
        except Exception as exc:
            return 1, _findings(['cli: a step raised %s' % type(exc).__name__], as_json)
    code, kind, payload = _tasks(root, clock)
    if kind == 'findings':
        return code, _findings(payload, as_json)
    try:
        return code, _render(payload, as_json)
    except Exception as exc:
        return 1, _findings(['cli: a step raised %s' % type(exc).__name__], as_json)


def main(argv, stdout, environ, clock, starter=None):
    """Run one command; return 0, 1 or 2; never raise an Exception. environ is read by end, init, launch, approve,
    edit, reject and import, after the parse, through in_runtime; tasks and status do not read it. starter is None
    unless a caller passes one; the entry line passes none."""
    try:
        code, text = _run(argv, environ, clock, starter)
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
