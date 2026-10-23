"""The reader of files at the base (task TASK-081; specification 7 revision 2, section 6): it reads one file's text, or
the paths under a tree, at a commit of the repository.

``read_file(repo, commit, path, read=None)`` returns ({"blob": <blob id>, "text": <the text>}, None) or (None,
findings); ``list_paths(repo, commit, prefix, read=None)`` returns (<the sorted list of blob paths under prefix>, None)
or (None, findings). Findings are a non-empty list of strs; on findings there is no value.

The module reads through gitread.run only, with gitread's fixed forms: rev-parse --verify --end-of-options of the
commit, cat-file -t of the commit, and cat-file -p of the commit, of each tree and of the blob. read is injectable: it
defaults, at call time, to gitread.run, and tests pass a stand-in with the same signature and result. Before any read,
every argument is checked, and gitread.form_error checks the repository path; a refused input makes no read call. The
module never raises: every failure, a raising read among them, gives findings. It writes nothing, opens no file, reads
no clock and no environment, and starts no process but through read.

The walk is modelled on scope_reconcile._blob_at (TASK-035), not imported from it: this task's choice (option (a) of
TASK-081's contract), a departure from specification 7's "reuse that walk", listed for its next revision. It differs
from _blob_at in: the commit's rev-parse and cat-file -t checks; gitread.form_error first; the name form of every
listed name; the bounds; the refusal of symbolic links, submodules and quoted names; the blob hash check; TIMEOUT; and
findings in place of a raised stop.

Listings are cached by tree id: each distinct tree id is read once, and every place it appears gives its paths. The
walk fails closed: a listed name outside the path-name form (unquoted printable ASCII, no "." or ".."), a symbolic
link or a submodule anywhere under a listed prefix, a mode that does not fit its type, or a crossed bound gives
findings, never a partial value. The bounds are module constants, read at call time: MAX_BYTES per blob and per
listing, MAX_TOTAL_BYTES per call, MAX_ENTRIES paths, MAX_TREES distinct trees (the root counted), MAX_PLACES tree
places, MAX_DEPTH names counted from the root, and TIMEOUT seconds per read.

Limits: Git is trusted as the contract reader trusts it (specification 5 :121); gitread's output is not capped, so a
size bound is checked after a read returns; a path with a non-ASCII or other quoted name cannot be read or listed; a
raw newline inside a name, from a stand-in or a Git that does not quote, can make a listing line that is in form and
wrong (scope_reconcile's limit L2); cat-file honours refs/replace, so a tree read may not be the commit's own, while a
blob is checked by its hash; and that the commit is the base the launcher passed is the caller's.
"""

import hashlib
import re

from aieos_bootstrap import gitread

MAX_BYTES = 4194304
MAX_TOTAL_BYTES = 67108864
MAX_ENTRIES = 100000
MAX_TREES = 20000
MAX_PLACES = 200000
MAX_DEPTH = 64
TIMEOUT = 60
MAX_PATH = 4096

_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_NAME = re.compile(r'[!#-\[\]-~]+')
_LISTING = re.compile(r'([0-7]+) (blob|tree|commit) ([0-9a-f]{40}|[0-9a-f]{64})\t([^/\x00-\x1f\x7f]+)')
_TREE_MODE = '040000'
_BLOB_MODES = ('100644', '100755')
_LINK_MODE = '120000'


class _Stop(Exception):
    """A refusal found inside a step: its findings."""

    def __init__(self, findings):
        Exception.__init__(self, findings[0])
        self.findings = list(findings)


def _names(value, what, root_ok):
    """The names of a repository path, or a _Stop with the finding."""
    if type(value) is not str:
        raise _Stop(['argument: %s is not a str' % what])
    if value == '':
        if root_ok:
            return []
        raise _Stop(['argument: %s is empty' % what])
    if len(value) > MAX_PATH:
        raise _Stop(['argument: %s is over %d characters' % (what, MAX_PATH)])
    names = value.split('/')
    if len(names) > MAX_DEPTH:
        raise _Stop(['argument: %s has more than MAX_DEPTH (%d) names' % (what, MAX_DEPTH)])
    for name in names:
        if _NAME.fullmatch(name) is None or name in ('.', '..'):
            raise _Stop(['argument: %s has a name out of form: %r' % (what, name)])
    return names


def _start(repo, commit, read):
    """The call's state after the argument checks, or a _Stop; no read call is made here."""
    if type(repo) is not str:
        raise _Stop(['argument: repo is not a str'])
    if type(commit) is not str or _COMMIT.fullmatch(commit) is None:
        raise _Stop(['argument: commit is not 40 or 64 lowercase hexadecimal characters'])
    if read is not None and not callable(read):
        raise _Stop(['argument: read is not callable'])
    why = gitread.form_error(repo, ['rev-parse', '--verify', '--end-of-options', commit], TIMEOUT)
    if why is not None:
        raise _Stop(['argument: %s' % why])
    return {'repo': repo, 'read': gitread.run if read is None else read, 'trees': {}, 'total': 0}


def _call(state, args):
    """The out bytes of one guarded read call, or a _Stop naming the subcommand."""
    name = ' '.join(args[:2])
    try:
        r = state['read'](state['repo'], list(args), TIMEOUT)
    except Exception as e:
        raise _Stop(['%s raised %s' % (name, type(e).__name__)])
    if not isinstance(r, dict) or not {'exit', 'out', 'err', 'error'} <= set(r):
        raise _Stop(['%s gave no result in gitread.run\'s form' % name])
    if r['error'] is not None:
        raise _Stop(['%s was not run or did not finish: %s' % (name, r['error'])])
    if r['exit'] != 0:
        raise _Stop(['%s exited with %r' % (name, r['exit'])])
    if not isinstance(r['out'], bytes):
        raise _Stop(['%s gave no bytes' % name])
    return r['out']


def _strip(out):
    return out[:-1] if out.endswith(b'\n') else out


def _counted(state, out, what):
    """Counts out's bytes against MAX_BYTES and MAX_TOTAL_BYTES."""
    if len(out) > MAX_BYTES:
        raise _Stop(['%s is over MAX_BYTES (%d)' % (what, MAX_BYTES)])
    state['total'] += len(out)
    if state['total'] > MAX_TOTAL_BYTES:
        raise _Stop(['the call read over MAX_TOTAL_BYTES (%d)' % MAX_TOTAL_BYTES])


def _root(state, commit):
    """The commit's tree id after its checks."""
    if _strip(_call(state, ['rev-parse', '--verify', '--end-of-options', commit])) != commit.encode('ascii'):
        raise _Stop(['rev-parse --verify did not give back the commit %s' % commit])
    if _strip(_call(state, ['cat-file', '-t', commit])) != b'commit':
        raise _Stop(['cat-file -t: %s is not a commit' % commit])
    parsed = gitread.parse_commit(_call(state, ['cat-file', '-p', commit]))
    if parsed['error'] is not None:
        raise _Stop(['cat-file -p: the commit %s is out of form: %s' % (commit, parsed['error'])])
    tree = parsed['tree']
    if not (isinstance(tree, str) and _COMMIT.fullmatch(tree)):
        raise _Stop(['cat-file -p: the commit %s names no tree id in form' % commit])
    return tree


def _listing(state, tree):
    """{name: (mode, kind, id)} of a tree, read once per tree id."""
    if tree in state['trees']:
        return state['trees'][tree]
    if len(state['trees']) >= MAX_TREES:
        raise _Stop(['more than MAX_TREES (%d) distinct trees' % MAX_TREES])
    out = _call(state, ['cat-file', '-p', tree])
    _counted(state, out, 'the listing of tree %s' % tree)
    try:
        text = out.decode('utf-8')
    except UnicodeDecodeError:
        raise _Stop(['the listing of tree %s is not UTF-8' % tree])
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]
    entries = {}
    for line in lines:
        m = _LISTING.fullmatch(line)
        if m is None:
            raise _Stop(['the listing of tree %s has a line out of form' % tree])
        mode, kind, oid, name = m.groups()
        if _NAME.fullmatch(name) is None or name in ('.', '..'):
            raise _Stop(['the listing of tree %s has a name out of the path-name form: %r' % (tree, name)])
        if name in entries:
            raise _Stop(['the listing of tree %s names %r twice' % (tree, name)])
        entries[name] = (mode, kind, oid)
    state['trees'][tree] = entries
    return entries


def _kind_check(path, mode, kind):
    """A _Stop for a submodule, a symbolic link or a mode that does not fit its type."""
    if kind == 'commit':
        raise _Stop(['%s is a submodule' % path])
    if kind == 'blob' and mode == _LINK_MODE:
        raise _Stop(['%s is a symbolic link' % path])
    if kind == 'tree' and mode != _TREE_MODE or kind == 'blob' and mode not in _BLOB_MODES:
        raise _Stop(['%s has the mode %s, which does not fit a %s' % (path, mode, kind)])


def _walk_trees(state, tree, names):
    """The tree id at names below tree, each element a tree."""
    current = tree
    for k, name in enumerate(names):
        here = '/'.join(names[:k + 1])
        entries = _listing(state, current)
        if name not in entries:
            raise _Stop(['%s is missing' % here])
        mode, kind, oid = entries[name]
        _kind_check(here, mode, kind)
        if kind != 'tree':
            raise _Stop(['%s is a %s, not a tree' % (here, kind)])
        current = oid
    return current


def _blob_text(state, path, oid):
    """The blob's text after its size, hash and UTF-8 checks."""
    data = _call(state, ['cat-file', '-p', oid])
    _counted(state, data, 'the blob %s' % path)
    header = b'blob %d\x00' % len(data)
    if len(oid) == 40:
        digest = hashlib.sha1(header + data, usedforsecurity=False).hexdigest()
    else:
        digest = hashlib.sha256(header + data).hexdigest()
    if digest != oid:
        raise _Stop(['the bytes of %s do not hash to its id %s' % (path, oid)])
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        raise _Stop(['%s does not decode as UTF-8' % path])


def _read_file(repo, commit, path, read):
    names = _names(path, 'path', False)
    state = _start(repo, commit, read)
    parent = _walk_trees(state, _root(state, commit), names[:-1])
    entries = _listing(state, parent)
    if names[-1] not in entries:
        raise _Stop(['%s is missing' % path])
    mode, kind, oid = entries[names[-1]]
    _kind_check(path, mode, kind)
    if kind != 'blob':
        raise _Stop(['%s is a %s, not a blob' % (path, kind)])
    return {'blob': oid, 'text': _blob_text(state, path, oid)}


def _list_paths(repo, commit, prefix, read):
    names = _names(prefix, 'prefix', True)
    state = _start(repo, commit, read)
    top = _walk_trees(state, _root(state, commit), names)
    paths = []
    places = 0
    stack = [(top, names)]
    while stack:
        tree, at = stack.pop()
        places += 1
        if places > MAX_PLACES:
            raise _Stop(['more than MAX_PLACES (%d) tree places' % MAX_PLACES])
        for name, (mode, kind, oid) in _listing(state, tree).items():
            below = at + [name]
            here = '/'.join(below)
            if len(below) > MAX_DEPTH:
                raise _Stop(['%s is deeper than MAX_DEPTH (%d)' % (here, MAX_DEPTH)])
            _kind_check(here, mode, kind)
            if kind == 'tree':
                stack.append((oid, below))
            else:
                paths.append(here)
                if len(paths) > MAX_ENTRIES:
                    raise _Stop(['more than MAX_ENTRIES (%d) paths' % MAX_ENTRIES])
    return sorted(paths)


def read_file(repo, commit, path, read=None):
    """The blob id and UTF-8 text of path at commit, or findings."""
    try:
        return _read_file(repo, commit, path, read), None
    except _Stop as s:
        return None, s.findings
    except Exception as e:
        return None, ['read_file: an unexpected %s' % type(e).__name__]


def list_paths(repo, commit, prefix, read=None):
    """The sorted blob paths under prefix at commit ("" for the root), or findings."""
    try:
        return _list_paths(repo, commit, prefix, read), None
    except _Stop as s:
        return None, s.findings
    except Exception as e:
        return None, ['list_paths: an unexpected %s' % type(e).__name__]
