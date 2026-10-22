"""The store lookup of the Claude Code adapter's hook process (task TASK-066; specification 5 section 11 point 7,
bullets 3 to 6; concept line 945).

``judge(session_id, root, working_folder, now)`` gives the read-only judgement every hook call needs before any
concern: a mapping with exactly the keys outcome, reason, findings, root and lease. The three outcomes and their
sources (specification 5 section 11 point 7):

- "tied" (bullet 3): the one unexpired lease the store holds for the session, in eventlog.LEASE_KEYS' form, and the
  root it was found at;
- "enforce_nothing" (bullet 5): neither a session id nor a root, and no store found upward ("no_store_found"), or the
  store found holds no lease row at all, expired or not ("no_lease_row"); only with both absent;
- "refuse" (bullet 6, no record): every other case with no live tied lease, with one fixed reason.

The values rule (bullet 4): a session id or a root is absent when it is None or the empty str; any other str is
present, whitespace-only included (a whitespace root is not absolute and refuses: fail closed); any other type, and a
present root that is not absolute, refuses ("argument"). A root without a session id refuses
("root_without_session"), a session id without a root refuses ("session_without_root"). With both, the store is
looked up only at the given root, through ``writer.session_lease``; no search is made and the working folder is not
used. The empty-as-absent rule is this module's; ``writer.session_lease`` takes None or a non-empty str only.

The upward search, with neither: the working folder must be an absolute path of an existing folder ("argument"
otherwise), so no result depends on the process's current folder. The search starts at its absolute form and goes to
each parent in turn, until the parent no longer changes (the drive or share root), taking os.lstat of
``writer.store_path`` of each folder: a missing entry (FileNotFoundError or NotADirectoryError) passes the folder over
(a folder whose project-state directory has no store file); a regular file, read from st_mode's kind bits with no stat
import, stops the search there; any other OSError, a ValueError or an entry that is not a regular file (a dangling
link among them) refuses ("search"; a fail-closed reading of bullet 6's "every other case", since bullet 5 names only a
store not found). The store found is then looked up with no session id. The search climbs the lexical parents of
os.path.abspath of the working folder, with no link resolved: a working folder reached through a link from outside a
project's tree finds no store there and gives "enforce_nothing" (fail-open for that case; task TASK-068 states it and
leaves the search unchanged). Limits: a store found first inside an inner
project is judged alone, even while an outer store holds a lease row; a hook call outside every project's folder tree
is not judged; a store created, removed or swapped between this search and the lookup's open is a race (refused if
gone, judged if it appears).

Read-only and the lock: this module never opens the store, the event log or any file; ``writer.session_lease`` opens
the store read-only, takes only a shared lock, and refuses ("unreadable") a lock held past its timeout, a hot journal
or a journal or WAL state a read-only connection cannot use: a hook call during a long commit is refused without a
record. Its URI rule, its UNC and non-UTF-8 refusals, its table form before and after K1 (specification 2 revision 7
section 3 already lists four tables) and its presence step and link check, with their limits (untested in CI on Linux;
junctions and unresolved links; hard links and bind mounts; check and use apart), are stated in that function's own
docstring.

The mapping of the lookup's answer: "done" with reason "tied" and a lease gives "tied" only when the lookup was made
with a session id; on the search path, where no session id is given, it gives "refuse" with reason "entry" (task
TASK-068; the real lookup gives "tied" only with a session id, so this guard changes no real result); "done" with reason
"no_lease_row" gives "enforce_nothing" only on the search path; every "refused" gives "refuse" with the same reason
and findings; any other shape of answer gives "refuse" with reason "entry". No exception escapes: an exception while
now is checked gives "refuse", reason "argument", with the finding "argument: now (<type name>)"; any other exception
inside gives "refuse", reason "entry", the exception's type name in findings. Equal arguments over an unchanged disk
give equal results; nothing is kept between calls.

Now is checked here by its type's MRO (a class named datetime in module datetime), with no import of datetime, while
the writer checks it with isinstance; the two checks of now differ and both fail closed (each refuses what it does not
accept, and the writer checks again).

The session id, the root, the working folder and now are arguments: this module's two hook-side callers,
claude_code_read_hook (task TASK-068) and claude_code_pretool_hook (task TASK-072), take them from the environment,
the process's own working folder and the process clock. A now earlier than the real time would make an expired lease
read as unexpired (the fail-open direction), so every caller must take now from the process clock. This module reads
no clock, no environment and no standard input, starts no process and prints nothing. No hook is placed, no matcher
chosen, no setting changed and nothing is measured (CC-3, the owner's; C6).
"""

import os

from aieos_bootstrap import writer

KEYS = ('outcome', 'reason', 'findings', 'root', 'lease')
_KIND_BITS = 0o170000
_REGULAR_FILE = 0o100000


def _result(outcome, reason, findings, root=None, lease=None):
    return {'outcome': outcome, 'reason': reason, 'findings': list(findings), 'root': root, 'lease': lease}


def _refuse(reason, finding, root=None):
    return _result('refuse', reason, [finding], root)


def _absent(value):
    """None and the empty str are absent; anything else is present."""
    return value is None or (isinstance(value, str) and value == '')


def _is_now(now):
    """A timezone-aware datetime in UTC with whole seconds, checked without importing datetime."""
    if not any(c.__module__ == 'datetime' and c.__name__ == 'datetime' for c in type(now).__mro__):
        return False
    offset = now.utcoffset()
    return now.tzinfo is not None and offset is not None and not offset and now.microsecond == 0


def _probe(folder):
    """One folder of the upward search: "absent", "found" or "refuse"."""
    try:
        kind = os.lstat(writer.store_path(folder)).st_mode & _KIND_BITS
    except (FileNotFoundError, NotADirectoryError):
        return 'absent'
    except (OSError, ValueError):
        return 'refuse'
    return 'found' if kind == _REGULAR_FILE else 'refuse'


def _search(working_folder):
    """The folder whose store is found nearest upward, None when none is, or "refuse"."""
    folder = os.path.abspath(working_folder)
    while True:
        seen = _probe(folder)
        if seen == 'found':
            return folder
        if seen == 'refuse':
            return seen
        parent = os.path.dirname(folder)
        if parent == folder:
            return None
        folder = parent


def _map(answer, searched, root):
    """The lookup's answer as judge's result (AC5)."""
    if not isinstance(answer, writer.StoreResult):
        return _refuse('entry', 'entry: the lookup gave no store result', root)
    if answer.result == 'done' and answer.reason == 'tied' and searched:
        return _refuse('entry', 'entry: the lookup gave "tied" without a session id', root)
    if answer.result == 'done' and answer.reason == 'tied' and answer.value is not None:
        return _result('tied', 'tied', [], root, answer.value)
    if answer.result == 'done' and answer.reason == 'no_lease_row' and searched:
        return _result('enforce_nothing', 'no_lease_row', [], root)
    if answer.result == 'refused':
        return _result('refuse', answer.reason, answer.findings, root)
    return _refuse('entry', 'entry: the lookup gave an answer of another shape', root)


def _judge(session_id, root, working_folder, now):
    try:
        ok = _is_now(now)
    except Exception as e:
        return _refuse('argument', 'argument: now (%s)' % type(e).__name__)
    if not ok:
        return _refuse('argument', 'argument: now is not a timezone-aware datetime in UTC with whole seconds')
    has_session, has_root = not _absent(session_id), not _absent(root)
    if (has_session and not isinstance(session_id, str)) or (has_root and not isinstance(root, str)):
        return _refuse('argument', 'argument: a session id or a root that is not a string')
    if has_root and not os.path.isabs(root):
        return _refuse('argument', 'argument: the root is not an absolute path')
    if has_root and not has_session:
        return _refuse('root_without_session', 'root_without_session: a root is set without a session id')
    if has_session and not has_root:
        return _refuse('session_without_root', 'session_without_root: a session id is set without a root')
    if has_session:
        return _map(writer.session_lease(root, session_id, now), False, root)
    if not (isinstance(working_folder, str) and os.path.isabs(working_folder) and os.path.isdir(working_folder)):
        return _refuse('argument', 'argument: the working folder is not an absolute path of an existing folder')
    found = _search(working_folder)
    if found == 'refuse':
        return _refuse('search', 'search: an entry on the way up could not be examined or is not a regular file')
    if found is None:
        return _result('enforce_nothing', 'no_store_found', [])
    return _map(writer.session_lease(found, None, now), True, found)


def judge(session_id, root, working_folder, now):
    """The hook's judgement of one call: outcome "tied", "enforce_nothing" or "refuse" (the module docstring states
    the rules, the mapping and the limits). Never raises."""
    try:
        return _judge(session_id, root, working_folder, now)
    except Exception as e:
        return _refuse('entry', 'entry: %s' % type(e).__name__)
