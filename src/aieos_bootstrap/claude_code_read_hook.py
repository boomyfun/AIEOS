"""The read hook program of the Claude Code adapter (task TASK-068; specification 5 revision 4, section 7 and section
11 point 7, bullets 2 to 6; specification 2 revision 7, section 3; concept line 945, "record the observed read-set").

A program for a PostToolUse hook on the file-reading tool: after a Read call it stores the paths that call read under
the session's live tied lease, and does nothing else; nothing wires this program into Claude Code: no setting, no
matcher and no hook entry is made by this task; placing it and choosing its matcher are the owner's (CC-3; A51 item
(4)), and whether Claude Code calls it, with which input and in which folder, is unmeasured (C6).

``run(stdin_bytes, environ, working_folder, now)`` judges one hook call, every outside value an argument, and returns
a mapping with exactly exit_code, outcome ("skip", "recorded" or "lost"), reason and findings. Its flow, in this order,
the first step that ends giving the result:

1. the arguments: stdin_bytes of exactly type bytes, environ a Mapping, working_folder a str or None, now a
   timezone-aware datetime in UTC with whole seconds; else "skip", reason "argument";
2. the two names AIEOS_SESSION_ID and AIEOS_ROOT, read only through environ.get and passed unchanged (absent is None,
   empty is ""); no other name is read, and the empty-or-absent rule is judge's;
3. claude_code_store.judge(session id, root, working folder, now): "enforce_nothing" gives "skip" and stores nothing;
   "refuse" gives "skip" with judge's own findings; only "tied", with judge's reason "tied", a lease, a session id
   and judge's root, goes on; any other answer gives "skip", reason "entry";
4. claude_code_reads.read_paths(stdin_bytes): "uncovered" gives "skip" (its finding, which may name the tool, is not
   copied); a non-empty list of paths goes on;
5. writer.add_reads(judge's root, the session id, the paths, now): "done" gives "recorded"; "refused" gives "lost"
   with the writer's reason and findings;
6. no exception escapes: one gives "skip" or, once add_reads was reached, "lost", reason "entry", with only the
   exception's type name.

RESULT_KEYS, the four keys of run's result in that order, is a public constant of this module, as SESSION_VAR and
ROOT_VAR (the two names step 2 reads) are.

The working folder is the process's own working folder (os.getcwd()), never the input's cwd, and no key of the hook
input is read but through read_paths, which reads only tool_name and tool_input: the input's session_id, cwd and
transcript_path are never read. This program writes no record: the observed read-set record is the launcher's
(specification 5 section 7 and section 11 point 7; specification 7). read_set_record.observe is core-side: no
hook-side module calls it.

``main()`` reads standard input once, takes os.environ (passed to run unread), the process's working folder (None when
os.getcwd() raises OSError) and the clock once, calls run and returns its exit code. The clock is the process clock
rounded up to the next whole second when it has a fraction (the writer takes whole seconds): rounding up is the
fail-closed direction, since a now earlier than the real time would make an expired lease read as live, so rounding
never makes a lease that has expired at the clock's reading read as live. The same now goes to judge and add_reads.

Exit code 0 on every outcome, and the program prints nothing, for every exception inheriting Exception (a
BaseException that is not an Exception, or a failure before main runs, can give a non-zero exit code and text): a
PostToolUse hook runs after the read (as documented, unmeasured: C6), so a refusal
would block nothing; it never asks for an approval and never shows a stop (decision D-1469 ruling 1). An error
inheriting Exception while reading standard input, the environment or the clock gives exit code 0 too, with nothing
written.

Limits: a read may be lost silently, and nothing records the loss: on "lost" (a lock held past add_reads' timeout,
the bound, a path refused, a damaged store, an exception) and on every "skip" other than "enforce_nothing" while the
session holds a lease (a Read input read_paths cannot parse, judge refusing "unreadable" during a long commit); the
read-set stays a lower bound and an estimate. The clock window: now is fixed before the lookups, before judge's
lookup and before add_reads' lock waits (up to about 5 seconds each), so a lease that expires during the call, up to
about 10 seconds, may still be judged live and a read stored for it; a limit in the fail-open direction,
kept (decision D-1484 C2): a second clock reading before add_reads would not close it, since add_reads checks the
lease against the now it is given only after its own lock wait of up to about 5 seconds. One hook call may wait up to
about 10 seconds, beside Claude Code's own hook timeout (unmeasured); a hook killed by that timeout may store nothing,
and a kill after add_reads' COMMIT may have stored the read. Judge's limits hold here: a hook call outside every
project's folder tree is not judged; an
inner project's store judges alone; a removed or emptied store turns the hook off when no session id is set; a run
outside the launcher while no task is leased is not judged. With neither name set, a hook inside a project whose
store holds a lease row stores nothing (in the desktop app's sessions the tie is covered by no measurement). Reads
through Grep, Glob, a shell or an MCP tool are not seen. Whether a PostToolUse hook inherits the runtime's
environment, in subagents and across a resume or a compaction, and the folder it runs in are unmeasured. The machine's
clock is trusted; standard input is read whole, with no size bound of its own.

What a hook-side caller of add_reads meets (task TASK-067): with exactly 10000 stored, a duplicate or an empty call
returns "done" 0 at the bound; its "?mode=rw" open may roll back a hot journal and so change the store's bytes; a
failed COMMIT may have applied the change, and "each once" makes a later call safe.

This module reaches the store only through writer.add_reads; it opens no file, starts no process, makes no network or
model call and keeps no state between calls. It names the project-state directory only by that phrase.
"""

import collections.abc
import datetime
import os
import sys

from aieos_bootstrap import claude_code_reads, claude_code_store, writer

SESSION_VAR = 'AIEOS_SESSION_ID'
ROOT_VAR = 'AIEOS_ROOT'
RESULT_KEYS = ('exit_code', 'outcome', 'reason', 'findings')


def _result(outcome, reason, findings):
    return {'exit_code': 0, 'outcome': outcome, 'reason': reason, 'findings': list(findings)}


def _is_str_list(value):
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


def _filled(value):
    return isinstance(value, str) and value != ''


def _check_arguments(stdin_bytes, environ, working_folder, now):
    """Step (1): the name of the first argument of a wrong kind, or None."""
    if type(stdin_bytes) is not bytes:
        return 'stdin_bytes'
    if not isinstance(environ, collections.abc.Mapping):
        return 'environ'
    if working_folder is not None and not isinstance(working_folder, str):
        return 'working_folder'
    if not (isinstance(now, datetime.datetime) and now.tzinfo is not None
            and now.utcoffset() == datetime.timedelta(0) and now.microsecond == 0):
        return 'now'
    return None


def _judged(answer, session_id):
    """Step (3): judge's answer as an ending result, or None when it is a live tie to go on with."""
    if not isinstance(answer, dict) or set(answer) != set(claude_code_store.KEYS) \
            or not _is_str_list(answer['findings']):
        return _result('skip', 'entry', ['entry: judge'])
    outcome = answer['outcome']
    if outcome == 'enforce_nothing':
        return _result('skip', 'enforce_nothing', [])
    if outcome == 'refuse' and isinstance(answer['reason'], str):
        return _result('skip', 'refuse', list(answer['findings']))
    if outcome == 'tied' and answer['reason'] == 'tied' and isinstance(answer['lease'], dict) \
            and _filled(session_id) and _filled(answer['root']):
        return None
    return _result('skip', 'entry', ['entry: judge'])


def _paths(answer):
    """Step (4): (an ending result, None) or (None, the paths to store)."""
    if not isinstance(answer, dict) or set(answer) != set(claude_code_reads.RESULT_KEYS):
        return _result('skip', 'entry', ['entry: read_paths']), None
    if answer['result'] == 'uncovered':
        return _result('skip', 'uncovered', []), None
    paths = answer['read_paths']
    if answer['result'] == 'read' and _is_str_list(paths) and paths:
        return None, list(paths)
    return _result('skip', 'entry', ['entry: read_paths']), None


def _stored(answer):
    """Step (5): the writer's answer as the result."""
    if not isinstance(answer, writer.StoreResult):
        return _result('lost', 'entry', ['entry: add_reads'])
    if answer.result == 'done':
        return _result('recorded', None, [])
    if answer.result == 'refused' and isinstance(answer.reason, str):
        findings = list(answer.findings)
        if all(isinstance(f, str) for f in findings):
            return _result('lost', answer.reason, findings)
    return _result('lost', 'entry', ['entry: add_reads'])


def run(stdin_bytes, environ, working_folder, now):
    """The judgement of one PostToolUse hook call (the module docstring states the flow and the limits). Exit code 0
    always; never raises an exception inheriting Exception."""
    try:
        wrong = _check_arguments(stdin_bytes, environ, working_folder, now)
    except Exception as e:
        return _result('skip', 'argument', ['argument: %s' % type(e).__name__])
    if wrong is not None:
        return _result('skip', 'argument', ['argument: %s' % wrong])
    reached = False
    try:
        session_id = environ.get(SESSION_VAR)
        root = environ.get(ROOT_VAR)
        answer = claude_code_store.judge(session_id, root, working_folder, now)
        ended = _judged(answer, session_id)
        if ended is not None:
            return ended
        ended, paths = _paths(claude_code_reads.read_paths(stdin_bytes))
        if ended is not None:
            return ended
        reached = True
        return _stored(writer.add_reads(answer['root'], session_id, paths, now))
    except Exception as e:
        return _result('lost' if reached else 'skip', 'entry', ['entry: %s' % type(e).__name__])


def _raw_clock():
    return datetime.datetime.now(datetime.timezone.utc)


def _whole_second_now():
    now = _raw_clock()
    if now.microsecond:
        now = now.replace(microsecond=0) + datetime.timedelta(seconds=1)
    return now


def main():
    """The hook's process: standard input, the environment, the working folder and the clock to run; returns run's
    exit code, 0. Prints nothing; never raises an exception inheriting Exception."""
    try:
        stdin_bytes = sys.stdin.buffer.read()
        try:
            working_folder = os.getcwd()
        except OSError:
            working_folder = None
        now = _whole_second_now()
        return run(stdin_bytes, os.environ, working_folder, now)['exit_code']
    except Exception:
        return 0


if __name__ == '__main__':
    sys.exit(main())
