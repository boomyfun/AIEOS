"""The task contract reader at a given commit (TASK-071, H2a).

read_contract(root, commit, task_id, run=None) reads a lease task's contract, docs/tasks/<task_id>.yaml, as committed
at an explicit commit, from the repository's object store only (never the working tree), through gitread.run only, and
gives its task, base_commit, write_set and forbidden by G0's layout. parse_contract(text, task_id) is the pure parse of
step (4). The result is a mapping with exactly result, reason, findings, task, base_commit, write_set and forbidden;
result is "read" or "unreadable"; on "unreadable" the last four are None: "unreadable" never carries a partial or
default write-set. Every refusal fails closed.

The flow, in this order, the first step that ends giving the result, one finding per result:
(1) the arguments, by exact types: root a str for which gitread.form_error gives None (an absolute path of an existing
    folder), commit fullmatching gitread.OBJECT_ID, task_id fullmatching "TASK-" and ASCII digits; checked in the order
    root, commit, task_id; reason "argument". run is a test seam: a production caller does not pass it.
(2) the git reads: at most five calls, in the order commit, root tree, docs, tasks, blob, each
    run(root, ["cat-file", "-p", <id>], 10), run taken at call time (gitread.run by default); a try around each run
    call and the checks of its result; reason "git" for the call and the commit, reason "tree" for the three trees.
(3) the contract's bytes: at most 1 MiB, strict UTF-8, no U+FEFF anywhere, none of the controls C0 but the line feed,
    DEL, C1, U+2028 or U+2029; reason "bytes".
(4) the parse, parse_contract: the lines in file order, then the fields, then the task; reason "parse", and "task" for
    a task other than task_id.
(5) "read", reason None, findings [], with task, base_commit, write_set and forbidden (fresh lists of str).
(6) no exception escapes: one outside step (2)'s try gives "unreadable", reason "entry", findings ["entry: <type name>"].

The reason table: "argument" (argument: root, commit, task_id, text); "git" (git: run raised <type name>, result
shape, error, exit <n>, exit not an int, out not bytes, commit text over the cap, commit text not UTF-8, commit out of
form); "tree" (tree: tree text over the cap, tree text not UTF-8, line out of form, repeated name, docs missing, tasks
missing, contract missing, docs not a tree, tasks not a tree, contract not a 100644 blob); "bytes" (bytes: over the cap,
not UTF-8, byte-order mark, control character); "parse" (parse: top-level line out of form, base_commit line out of
form, write_set line out of form, forbidden line out of form, repeated key, item out of form, task missing, base_commit
missing, base_commit out of form, write_set empty, forbidden empty, task value out of form); "task" (task: another
task); "entry". No finding holds any part of git's output, error text or a name from a tree.

Stated limits:
- The commit is the caller's: no base is chosen here. capabilities.shell.allow is not read, and no allowlist source is
  chosen here.
- Its refusals are stricter than G0's, and G0's rules are copied, not shared: a contract G0 accepts can be "unreadable"
  here, which fails closed. Step (3) refuses a U+FEFF anywhere, a carriage return, NUL, tab and the other C0 controls,
  DEL, the C1 controls, U+2028 and U+2029, so a committed CRLF contract that G0 accepts is refused.
- The object store only: a commit that does not exist, a shallow or partial clone without the objects, or another hash
  form gives "unreadable". The commit is not proven a commit object: any object whose text parse_commit accepts is
  followed.
- The five calls of up to 10 seconds each: a caller may wait up to about 50 seconds. The caps of 1 MiB are checked
  after run has returned the whole output; the tree-size bound of the cap: a tree of more than roughly 15,000 entries
  is "tree: tree text over the cap".
- git is trusted as gitread trusts it: replace refs, grafts and alternates can change what a commit reads as (the
  replace-refs limit); an existing folder inside another repository is read as that outer repository (the
  outer-repository limit).
- Nothing hook-side calls it yet.
"""
import re

from aieos_bootstrap import gitread

_RUN_KEYS = frozenset(('exit', 'out', 'err', 'error'))
_CAP = 1 << 20
_TIMEOUT = 10
_TASK = re.compile(r'TASK-[0-9]+', re.ASCII)
_BASE = re.compile(r'[0-9a-f]{40}')
_KEY = re.compile(r'[a-z_]+')
_ITEM = re.compile(r'[A-Za-z0-9_./*-]+')
_LINE = re.compile(r'([0-7]{6}) (blob|tree|commit) ([0-9a-f]{40}|[0-9a-f]{64})\t([^/]+)')
_CONTROL = re.compile('[\\x00-\\x09\\x0b-\\x1f\\x7f-\\x9f\\u2028\\u2029]')


class _Refused(Exception):
    def __init__(self, reason, finding):
        Exception.__init__(self, reason)
        self.reason = reason
        self.finding = finding


def _unreadable(reason, finding):
    return {'result': 'unreadable', 'reason': reason, 'findings': [finding], 'task': None, 'base_commit': None,
            'write_set': None, 'forbidden': None}


def _call(runner, root, oid):
    """Step (2), one call: the output bytes, or _Refused with the "git" finding."""
    try:
        r = runner(root, ['cat-file', '-p', oid], _TIMEOUT)
        if type(r) is not dict or frozenset(r) != _RUN_KEYS:
            finding = 'git: result shape'
        elif r['error'] is not None:
            finding = 'git: error'
        elif type(r['exit']) is not int:
            finding = 'git: exit not an int'
        elif r['exit'] != 0:
            finding = 'git: exit %d' % r['exit']
        elif type(r['out']) is not bytes:
            finding = 'git: out not bytes'
        else:
            return r['out']
    except Exception as e:
        finding = 'git: run raised ' + type(e).__name__
    raise _Refused('git', finding)


def _tree_id(out):
    if len(out) > _CAP:
        raise _Refused('git', 'git: commit text over the cap')
    try:
        out.decode('utf-8')
    except UnicodeDecodeError:
        raise _Refused('git', 'git: commit text not UTF-8')
    c = gitread.parse_commit(out)
    if c['error'] is not None or type(c['tree']) is not str or gitread.OBJECT_ID.fullmatch(c['tree']) is None:
        raise _Refused('git', 'git: commit out of form')
    return c['tree']


def _entry(out, name, mode, kind, what):
    """Step (2), one tree: the id of the sought entry, or _Refused with the "tree" finding."""
    if len(out) > _CAP:
        raise _Refused('tree', 'tree: tree text over the cap')
    try:
        text = out.decode('utf-8')
    except UnicodeDecodeError:
        raise _Refused('tree', 'tree: tree text not UTF-8')
    if text and not text.endswith('\n'):
        raise _Refused('tree', 'tree: line out of form')
    entries = []
    for line in (text[:-1].split('\n') if text else []):
        m = _LINE.fullmatch(line)
        if m is None:
            raise _Refused('tree', 'tree: line out of form')
        entries.append(m.groups())
    names = [e[3] for e in entries]
    if len(set(names)) != len(names):
        raise _Refused('tree', 'tree: repeated name')
    found = [e for e in entries if e[3] == name]
    if not found:
        raise _Refused('tree', 'tree: %s missing' % what)
    if found[0][0] != mode or found[0][1] != kind:
        raise _Refused('tree', 'tree: %s' % ('contract not a 100644 blob' if what == 'contract' else what + ' not a tree'))
    return found[0][2]


def _bytes_text(out):
    """Step (3): the contract's text, or _Refused with the "bytes" finding."""
    if len(out) > _CAP:
        raise _Refused('bytes', 'bytes: over the cap')
    try:
        text = out.decode('utf-8')
    except UnicodeDecodeError:
        raise _Refused('bytes', 'bytes: not UTF-8')
    if '\ufeff' in text:
        raise _Refused('bytes', 'bytes: byte-order mark')
    if _CONTROL.search(text):
        raise _Refused('bytes', 'bytes: control character')
    return text


def _item_ok(item):
    if _ITEM.fullmatch(item) is None or item.startswith('/') or item.startswith('./') or item.endswith('/'):
        return False
    return not any(s in ('', '.', '..') for s in item.split('/'))


def _lines(text):
    """Step (4) (i): the lines in file order; the first broken rule gives the one finding."""
    section, seen = None, set()
    task = base = None
    base_seen = paths_seen = False
    write_set, forbidden = [], []
    for raw in text.split('\n'):
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        if not raw.startswith(' '):
            key, colon, rest = raw.partition(':')
            if not colon or _KEY.fullmatch(key) is None or (rest and not rest.startswith(' ')):
                raise _Refused('parse', 'parse: top-level line out of form')
            if key in ('write_set', 'forbidden') and raw != key + ':':
                raise _Refused('parse', 'parse: top-level line out of form')
            if key in seen:
                raise _Refused('parse', 'parse: repeated key')
            seen.add(key)
            section = key
            if key == 'task':
                task = rest[1:]
            continue
        if section == 'input_state' and raw.startswith('  base_commit:'):
            if raw == '  base_commit:':
                value = ''
            elif raw.startswith('  base_commit: '):
                value = raw[len('  base_commit: '):]
            else:
                raise _Refused('parse', 'parse: base_commit line out of form')
            if base_seen:
                raise _Refused('parse', 'parse: repeated key')
            base_seen, base = True, value
        elif section == 'write_set':
            if raw == '  paths:':
                if paths_seen:
                    raise _Refused('parse', 'parse: repeated key')
                paths_seen = True
            elif paths_seen and raw.startswith('    - ') and len(raw) > len('    - '):
                if not _item_ok(raw[len('    - '):]):
                    raise _Refused('parse', 'parse: item out of form')
                write_set.append(raw[len('    - '):])
            else:
                raise _Refused('parse', 'parse: write_set line out of form')
        elif section == 'forbidden':
            if raw.startswith('  - ') and len(raw) > len('  - '):
                if not _item_ok(raw[len('  - '):]):
                    raise _Refused('parse', 'parse: item out of form')
                forbidden.append(raw[len('  - '):])
            else:
                raise _Refused('parse', 'parse: forbidden line out of form')
    return task, base, write_set, forbidden


def _parse(text, task_id):
    task, base, write_set, forbidden = _lines(text)
    if not task:
        raise _Refused('parse', 'parse: task missing')
    if not base:
        raise _Refused('parse', 'parse: base_commit missing')
    if _BASE.fullmatch(base) is None:
        raise _Refused('parse', 'parse: base_commit out of form')
    if not write_set:
        raise _Refused('parse', 'parse: write_set empty')
    if not forbidden:
        raise _Refused('parse', 'parse: forbidden empty')
    if _TASK.fullmatch(task) is None:
        raise _Refused('parse', 'parse: task value out of form')
    if task != task_id:
        raise _Refused('task', 'task: another task')
    return {'result': 'read', 'reason': None, 'findings': [], 'task': task, 'base_commit': base,
            'write_set': list(write_set), 'forbidden': list(forbidden)}


def parse_contract(text, task_id):
    """Step (4) alone: the same seven-key mapping as read_contract. text is checked first; task_id's form is checked
    only by read_contract's step (1), so a direct call with a malformed task_id ends in "task: another task"."""
    if type(text) is not str:
        return _unreadable('argument', 'argument: text')
    if type(task_id) is not str:
        return _unreadable('argument', 'argument: task_id')
    try:
        return _parse(text, task_id)
    except _Refused as r:
        return _unreadable(r.reason, r.finding)


def read_contract(root, commit, task_id, run=None):
    """Read docs/tasks/<task_id>.yaml at the given commit; see the module docstring for the flow and the limits."""
    try:
        if type(root) is not str or gitread.form_error(root, ['cat-file', '-p', '0' * 40], _TIMEOUT) is not None:
            return _unreadable('argument', 'argument: root')
        if type(commit) is not str or gitread.OBJECT_ID.fullmatch(commit) is None:
            return _unreadable('argument', 'argument: commit')
        if type(task_id) is not str or _TASK.fullmatch(task_id) is None:
            return _unreadable('argument', 'argument: task_id')
        runner = gitread.run if run is None else run
        try:
            tree = _tree_id(_call(runner, root, commit))
            docs = _entry(_call(runner, root, tree), 'docs', '040000', 'tree', 'docs')
            tasks = _entry(_call(runner, root, docs), 'tasks', '040000', 'tree', 'tasks')
            blob = _entry(_call(runner, root, tasks), task_id + '.yaml', '100644', 'blob', 'contract')
            text = _bytes_text(_call(runner, root, blob))
        except _Refused as r:
            return _unreadable(r.reason, r.finding)
        return parse_contract(text, task_id)
    except Exception as e:
        return _unreadable('entry', 'entry: ' + type(e).__name__)
