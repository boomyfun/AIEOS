"""The bootstrap's command-line entry point and its first command, tasks (task TASK-091; specification 7 revision 2,
section 3 :26, :32, :34; section 10 points 10 and 15).

What it does:
- It is run as ``python -m aieos_bootstrap.cli <command> [flags]``; the installed name is open (specification 7 :26),
  and "aieos <command>" in texts means that run form. ``main(argv, stdout, environ, clock)`` returns 0, 1 or 2 and
  never raises: every Exception is caught; KeyboardInterrupt and SystemExit are not. os.environ is read only in the
  entry line.
- Its own parser, not argparse: argv is exactly a list of str; argv[0] is a command of COMMANDS, whose only entry is
  tasks; the flags are --root <path> (required, once, a non-empty value not beginning "--") and --json (optional,
  once). Anything else gives exit 2 and USAGE, with neither the clock nor list_tasks called.
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
- RUNTIME_VARS and in_runtime(environ): outside any runtime means none of the three names is in the environment.
  in_runtime is true when any of them is present; AIEOS_BASE is counted beside the session id and the root, and a
  name whose value is '' counts as present (two stated choices, both fail-closed); an environment whose membership
  test raises counts as inside. tasks does not call it; the commands that refuse inside a runtime (end, launch)
  come with later tasks.

Limits, stated: a determined agent can start a nested runtime with an environment it chooses (spec 5 :120); a root
value beginning "--" cannot be given; a root that names no folder gives only list_tasks' "a step raised" finding; a
non-ASCII value in the text form on a stdout in a legacy code page raises at the write (exit 1); a stdout in Windows
text mode writes CRLF. __init__.py is not changed, and its module list stays as it was. Nothing runs this module but
its tests.
"""

import datetime
import json
import os
import sys

from aieos_bootstrap import execution

RUNTIME_VARS = ('AIEOS_SESSION_ID', 'AIEOS_ROOT', 'AIEOS_BASE')
COMMANDS = ('tasks',)
USAGE = ('usage: python -m aieos_bootstrap.cli tasks --root <path> [--json]\n'
         '  tasks          the tasks that may be taken\n'
         '  --root <path>  the project root (required)\n'
         '  --json         one JSON line in place of text lines\n')
OUT_OF_FORM = 'tasks: list_tasks gave an answer out of form'
NO_FINDING = 'tasks: list_tasks gave no finding'
_ITEM_KEYS = ('task', 'state', 'contract_hash', 'lease')


def in_runtime(environ):
    """True when any name of RUNTIME_VARS is in environ, '' counting as present; true when the test raises."""
    try:
        return any(name in environ for name in RUNTIME_VARS)
    except Exception:
        return True


def _parse(argv):
    """(root, as_json) for a well-formed argv, else None (a usage error)."""
    if type(argv) is not list or not argv or any(type(a) is not str for a in argv):
        return None
    if argv[0] not in COMMANDS:
        return None
    root, as_json, rest, i = None, False, argv[1:], 0
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
    return root, as_json


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


def _run(argv, clock):
    """(the exit code, the whole output)."""
    try:
        parsed = _parse(argv)
    except Exception as exc:
        return 1, _findings(['cli: a step raised %s' % type(exc).__name__], False)
    if parsed is None:
        return 2, USAGE
    root, as_json = parsed
    code, kind, payload = _tasks(root, clock)
    if kind == 'findings':
        return code, _findings(payload, as_json)
    try:
        return code, _render(payload, as_json)
    except Exception as exc:
        return 1, _findings(['cli: a step raised %s' % type(exc).__name__], as_json)


def main(argv, stdout, environ, clock):
    """Run one command; return 0, 1 or 2; never raise an Exception. environ is taken for the commands that refuse
    inside a runtime; tasks does not read it."""
    try:
        code, text = _run(argv, clock)
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
