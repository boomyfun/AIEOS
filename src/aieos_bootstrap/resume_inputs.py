"""The Git side of the Resume Check's inputs, read at a given commit (task TASK-085; specification 3 revision 5,
sections 1 and 4; conformance-files.md section 9; specification 7 revision 2, section 5; DEF-0097).

``git_inputs(repo, commit, task_id, log, read=None)`` returns (inputs, None), inputs being exactly ten of the 22 inputs
of resume_check.INPUT_KEYS in section 9's forms: head_commit, base_is_ancestor, commits, contract, contract_hash,
components, interfaces, symbols, schemas and derived_read_set; or (None, findings), a non-empty list of strs, and no
partial value. ``is_ancestor(repo, commit, base, read=None)`` returns (True or False, None) or (None, findings): the
walk git_inputs uses for base_is_ancestor.

As for HEAD, the commit is an argument: the launcher reads HEAD once and passes it; nothing here reads HEAD. read is injectable:
gitread.run is the default, taken at call time, and within one call the read in use is wrapped by a memo keyed by its
arguments and passed to every base_files and base_inputs call, so each (commit, folder) is listed once. Every Git read
is one of gitread's four fixed forms; there is no new form. The log is a value, read only for task.submitted through
base_inputs.submitted_commits. The module never raises: every failure, a RecursionError or MemoryError among them, is
given as findings. It writes nothing, opens no file, reads no clock and no environment, and starts no process but
through read. Each reader fails closed.

The readers, each this task's choice where TASK-085's contract says so:
- head_commit: the commit, which rev-parse --verify must give back and cat-file -t must call a commit.
- contract and contract_hash: base_inputs.contract_at at the commit; the contract's input_state.base_commit must be a
  commit id. base_commit is then read by cat-file -t alone: an answer with no error and a non-zero exit, or a type
  other than commit, means it is not a commit of the repository, and then base_is_ancestor is false, commits [],
  derived_read_set [] and each symbol's base null, so that the Resume Check's check 1 decides.
- base_is_ancestor: is_ancestor's breadth-first walk by rev-list --parents -n 1, every parent followed, each commit
  visited once, at most MAX_WALK commits visited.
- commits: when base_is_ancestor is true, the first-parent chain from the commit back to base_commit, base_commit left
  out, oldest first, at most MAX_COMMITS; a merge commit on the chain fails closed. Each commit's paths come from
  diff-tree; a path is modified when the listing of its folder holds it at the commit and at its parent, added when
  only at the commit, deleted when only at the parent, and a path in neither fails closed; at most MAX_PATHS paths a
  commit. submitted is true when a task.submitted of the task names the commit.
- components and interfaces: base_inputs.components_of. schemas: [] for the self-build (a non-empty read_set.schemas
  fails closed, as components_of refuses it).
- symbols: for each read_set.interfaces entry, its whole text as interface, its first word naming the module and the
  name; base and head the fixed form of resume_check.signature_form at base_commit and at the commit, null when the
  module's file is not in src/aieos_bootstrap's listing, and null when the text is unparsable, which the Resume Check
  reads as breaking.
- derived_read_set: the write set's .py paths in the listing at base_commit (a "*" entry matched by
  resume_check.matches over that whole listing), each read at base_commit and given to resume_check.direct_imports
  with the roots "src/" and ""; the sorted union of the paths it returns.

Limits, stated: ten of the 22 inputs; the other twelve are the launcher's, execution's or TASK-085b's, and every input
stays the caller's to join (R5 F4: derived_read_set is computed from the write set at base_commit, and the imports
direct_imports leaves unresolved and the files it cannot parse are not returned, so the record's unresolved and
unanalysed stay []); schemas always []; a merge on the chain fails closed; renames are not detected; one component per
module (TASK-082's reading); a shallow clone's cut reads as a root; a symbolic link, a submodule or an out-of-form name
under a listed folder fails the call (base_files' rules); the repository is read at one moment.
"""

import re

from aieos_bootstrap import base_files, base_inputs, gitread, resume_check

MAX_WALK = 20000
MAX_COMMITS = 1000
MAX_PATHS = 5000
TIMEOUT = 30
ROOTS = ['src/', '']
INTERFACE_FOLDER = 'src/aieos_bootstrap'
KEYS = ('head_commit', 'base_is_ancestor', 'commits', 'contract', 'contract_hash', 'components', 'interfaces',
        'symbols', 'schemas', 'derived_read_set')

_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_TASK = re.compile(r'TASK-[0-9]+')
_INTERFACE = re.compile(r'aieos_bootstrap\.([a-z_][a-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)')


class _Stop(Exception):
    """A refusal: its findings."""

    def __init__(self, findings):
        Exception.__init__(self, findings[0])
        self.findings = list(findings)


def _memo(read):
    """read wrapped by a memo keyed by its arguments."""
    seen = {}

    def run(repo, args, timeout=TIMEOUT):
        key = (repo, tuple(args), timeout)
        if key not in seen:
            seen[key] = read(repo, args, timeout)
        return seen[key]
    return run


def _state(repo, read):
    return {'repo': repo, 'read': _memo(gitread.run if read is None else read), 'listings': {}}


def _answer(state, args):
    """One guarded read: its answer in gitread.run's form, with no error and bytes out, or a _Stop."""
    name = ' '.join(args[:2])
    try:
        r = state['read'](state['repo'], list(args), TIMEOUT)
    except Exception as e:
        raise _Stop(['%s raised %s' % (name, type(e).__name__)])
    if not isinstance(r, dict) or not {'exit', 'out', 'err', 'error'} <= set(r):
        raise _Stop(['%s gave no result in gitread.run\'s form' % name])
    if r['error'] is not None:
        raise _Stop(['%s was not run or did not finish: %s' % (name, r['error'])])
    if not isinstance(r['out'], bytes):
        raise _Stop(['%s gave no bytes' % name])
    return r


def _out(state, args):
    r = _answer(state, args)
    if r['exit'] != 0:
        raise _Stop(['%s exited with %r' % (' '.join(args[:2]), r['exit'])])
    return r['out']


def _text(out, what):
    try:
        return out.decode('ascii')
    except UnicodeDecodeError:
        raise _Stop(['%s is not ASCII' % what])


def _kind(state, oid):
    """cat-file -t's type of oid, or None when cat-file exits non-zero with no error."""
    r = _answer(state, ['cat-file', '-t', oid])
    if r['exit'] != 0:
        return None
    return _text(r['out'], 'cat-file -t of %s' % oid).strip()


def _head(state, commit):
    if _text(_out(state, ['rev-parse', '--verify', '--end-of-options', commit]), 'rev-parse').strip() != commit:
        raise _Stop(['rev-parse --verify did not give back the commit %s' % commit])
    if _kind(state, commit) != 'commit':
        raise _Stop(['cat-file -t: %s is not a commit' % commit])


def _parents(state, oid):
    tokens = _text(_out(state, ['rev-list', '--parents', '-n', '1', oid]), 'rev-list of %s' % oid).split()
    if not tokens or tokens[0] != oid or not all(_COMMIT.fullmatch(t) for t in tokens[1:]):
        raise _Stop(['rev-list --parents of %s is out of form' % oid])
    return tokens[1:]


def _walk(state, commit, base):
    seen, queue, k = {commit}, [commit], 0
    while k < len(queue):
        here = queue[k]
        k += 1
        if here == base:
            return True
        if k > MAX_WALK:
            raise _Stop(['the walk from %s visited more than MAX_WALK (%d) commits' % (commit, MAX_WALK)])
        for p in _parents(state, here):
            if p not in seen:
                seen.add(p)
                queue.append(p)
    return False


def _check(repo, commit, read, more):
    found = []
    if type(repo) is not str:
        found.append('argument: repo is not a str')
    if type(commit) is not str or _COMMIT.fullmatch(commit) is None:
        found.append('argument: commit is not 40 or 64 lowercase hexadecimal characters')
    found.extend(more)
    if read is not None and not callable(read):
        found.append('argument: read is not callable')
    if found:
        raise _Stop(found)


def _is_ancestor(repo, commit, base, read):
    _check(repo, commit, read, [] if type(base) is str and _COMMIT.fullmatch(base) else
           ['argument: base is not 40 or 64 lowercase hexadecimal characters'])
    return _walk(_state(repo, read), commit, base)


def is_ancestor(repo, commit, base, read=None):
    """Whether base is commit or one of its ancestors: (True or False, None), or (None, findings)."""
    try:
        return _is_ancestor(repo, commit, base, read), None
    except _Stop as s:
        return None, s.findings
    except Exception as e:
        return None, ['is_ancestor: an unexpected %s' % type(e).__name__]


def _value(result, what):
    value, found = result
    if found is not None:
        raise _Stop(['%s: %s' % (what, f) for f in found])
    return value


def _listed(state, commit, folder):
    key = (commit, folder)
    if key not in state['listings']:
        paths = _value(base_inputs.paths_under(state['repo'], commit, folder, state['read']),
                       'listing of %r at %s' % (folder, commit))
        state['listings'][key] = set(paths)
    return state['listings'][key]


def _commits(state, commit, base, submitted):
    chain, here = [], commit
    while here != base:
        if len(chain) >= MAX_COMMITS:
            raise _Stop(['the chain from %s holds more than MAX_COMMITS (%d) commits' % (commit, MAX_COMMITS)])
        parents = _parents(state, here)
        if len(parents) != 1:
            raise _Stop(['the commit %s on the chain has %d parents, not one' % (here, len(parents))])
        chain.append((here, parents[0]))
        here = parents[0]
    out = []
    for c, parent in reversed(chain):
        parsed = gitread.parse_paths(_out(state, gitread.DIFF_TREE + [c]))
        if parsed['error'] is not None:
            raise _Stop(['diff-tree of %s is out of form: %s' % (c, parsed['error'])])
        if len(parsed['paths']) > MAX_PATHS:
            raise _Stop(['the commit %s changes more than MAX_PATHS (%d) paths' % (c, MAX_PATHS)])
        paths = []
        for path in parsed['paths']:
            folder = path.rsplit('/', 1)[0] if '/' in path else ''
            here_in, parent_in = path in _listed(state, c, folder), path in _listed(state, parent, folder)
            if here_in and parent_in:
                change = 'modified'
            elif here_in:
                change = 'added'
            elif parent_in:
                change = 'deleted'
            else:
                raise _Stop(['%s, changed by %s, is in neither its listing nor its parent\'s' % (path, c)])
            paths.append({'path': path, 'change': change})
        out.append({'id': c, 'paths': paths, 'submitted': c in submitted})
    return out


def _form(state, commit, module, name):
    path = '%s/%s.py' % (INTERFACE_FOLDER, module)
    if path not in _listed(state, commit, INTERFACE_FOLDER):
        return None
    text = _value(base_files.read_file(state['repo'], commit, path, state['read']), path)['text']
    form = resume_check.signature_form(text, name)
    return None if form == resume_check.UNPARSABLE else form


def _symbols(state, commit, base, entries):
    out = []
    for entry in entries:
        m = _INTERFACE.fullmatch(entry.split(' ', 1)[0])
        if m is None:
            raise _Stop(['the read_set.interfaces entry %r is out of the form aieos_bootstrap.<module>.<name>' % entry])
        module, name = m.groups()
        out.append({'interface': entry, 'base': None if base is None else _form(state, base, module, name),
                    'head': _form(state, commit, module, name)})
    return out


def _derived(state, base, contract):
    ws = contract.get('write_set')
    patterns = ws.get('paths', []) if isinstance(ws, dict) else None
    if not (isinstance(patterns, list) and all(isinstance(p, str) for p in patterns)):
        raise _Stop(['contract: write_set.paths is not a list of strs'])
    listing = _listed(state, base, '')
    chosen = sorted(p for p in listing if p.endswith('.py') and any(
        p == pat if '*' not in pat else resume_check.matches(pat, p) for pat in patterns))
    found = set()
    for path in chosen:
        text = _value(base_files.read_file(state['repo'], base, path, state['read']), path)['text']
        imports = resume_check.direct_imports(text, ROOTS, sorted(listing))
        if imports == resume_check.UNANALYSED:
            continue
        found.update(imports['paths'])
    return sorted(found)


def _git_inputs(repo, commit, task_id, log, read):
    more = []
    if type(task_id) is not str or _TASK.fullmatch(task_id) is None:
        more.append('argument: task_id is not TASK-<digits>')
    if type(log) is not bytes:
        more.append('argument: log is not bytes')
    _check(repo, commit, read, more)
    state = _state(repo, read)
    _head(state, commit)
    submitted = set(_value(base_inputs.submitted_commits(log, task_id), 'log'))
    contract, digest = _value(base_inputs.contract_at(repo, commit, task_id, state['read']), 'contract')
    s = contract.get('input_state')
    base = s.get('base_commit') if isinstance(s, dict) else None
    if type(base) is not str or _COMMIT.fullmatch(base) is None:
        raise _Stop(['contract: input_state.base_commit is not a commit id'])
    components, interfaces = _value(base_inputs.components_of(contract), 'contract')
    rs = contract['read_set']
    is_commit = _kind(state, base) == 'commit'
    ancestor = _walk(state, commit, base) if is_commit else False
    return {'head_commit': commit, 'base_is_ancestor': ancestor,
            'commits': _commits(state, commit, base, submitted) if ancestor else [],
            'contract': contract, 'contract_hash': digest, 'components': components, 'interfaces': interfaces,
            'symbols': _symbols(state, commit, base if is_commit else None, rs.get('interfaces', [])),
            'schemas': [], 'derived_read_set': _derived(state, base, contract) if is_commit else []}


def git_inputs(repo, commit, task_id, log, read=None):
    """Ten of the Resume Check's inputs read at commit: (inputs, None), or (None, findings)."""
    try:
        return _git_inputs(repo, commit, task_id, log, read), None
    except _Stop as s:
        return None, s.findings
    except Exception as e:
        return None, ['git_inputs: an unexpected %s' % type(e).__name__]
