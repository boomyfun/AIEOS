"""The capture step of a launched session (task TASK-147; DEF-0149 route (c); DEF-0147).

Two public functions, capture and restore. capture writes the change of one working tree as ONE commit on one new
reference, refs/heads/task/TASK-<digits>, without touching the real index, the checked-out branch or the working tree.
restore puts the working tree back to HEAD on exactly the listed paths. The caller decides everything about scope: every
argument is given, the module re-derives nothing, and it never reads the status. It starts git through ONE process call
of one form, and only with one of the ten argument forms of CAPTURE_FORMS; the CI pattern rule of revision 28 judges this
file (aieos-checks.yml, check_capture).

Both functions return a mapping and never raise an Exception. capture gives {'result': 'done', 'commit': <40 hex>} or
{'result': 'refused', 'reason': <word>, 'findings': [...]}; restore gives {'result': 'done'} or the same refused form.
The reason words are the closed set REASONS. A finding holds the step's name, an exit code or a rule, and no output of
git. A forced stop between the steps, or a refused step, leaves what exists as it is: the module never undoes.

The index of the capture is the file aieos-capture-index in the repository's git directory. It is overwritten by
read-tree and never deleted. Two captures at once in one clone are not supported.

Limits, in plain words. (1) The classes of restore are the caller's and are trusted. (2) A path that git ignores is not
seen by the caller's status read and so is not captured. (3) Directories that a clean leaves empty stay. (4) A filter
driver named in the clone's own configuration runs under update-index and restore; the options close it only in part, and
the caller's configuration read is the other half. (5) git is found by its name, as gitread does. (6) The state name rule
accepts any name that begins with a dot. (7) restore discards uncaptured changes on the listed paths and does not check
that a capture came first; the order of the calls is the caller's. (8) A listed path that names a directory would make
restore and clean act on everything below it; capture refuses it, because update-index fails on a directory, and the
caller lists files only. (9) The stored content is git's form under the clone's attributes (eol and text conversion).
(10) The text that tells an existing reference from another failure is git's English message under LC_ALL=C and can change
between git versions; a changed text makes an existing reference read as git-failed, and the reference is left alone
either way. (11) Nothing calls this module until the core part of the next task is built.
"""

import os
import re
import subprocess

CAPTURE_FORMS = (('read-tree', 'HEAD'),
                 ('update-index', '--add', '--remove', '--', '<paths>'),
                 ('write-tree',),
                 ('commit-tree', '--no-gpg-sign', '<tree>', '-p', '<id>', '-F', '-'),
                 ('update-ref', '<taskref>', '<id>', '<zero>'),
                 ('rev-parse', '--absolute-git-dir'),
                 ('rev-parse', '--verify', 'HEAD'),
                 ('diff', '--no-ext-diff', '--no-textconv', '--name-only', '<id>', '<id>'),
                 ('restore', '--source=HEAD', '--worktree', '--', '<paths>'),
                 ('clean', '-f', '--', '<paths>'))
CAPTURE_OPTIONS = ('--no-pager', '-c', 'core.fsmonitor=false', '-c', 'diff.external=', '-c', 'commit.gpgsign=false')
CAPTURE_ENV_FIXED = (('GIT_CONFIG_NOSYSTEM', '1'), ('GIT_CONFIG_GLOBAL', '<null>'), ('GIT_TERMINAL_PROMPT', '0'),
                     ('GIT_OPTIONAL_LOCKS', '0'), ('GIT_NO_LAZY_FETCH', '1'), ('LC_ALL', 'C'))

REASONS = ('invalid-argument', 'head-moved', 'ref-exists', 'name-list-mismatch', 'git-failed', 'timeout')
CLASSES = ('modified', 'added', 'deleted')
INDEX_NAME = 'aieos-capture-index'
EXISTS_TEXT = b'already exists'
ZERO = '0' * 40

_READ_TREE, _UPDATE_INDEX, _WRITE_TREE, _COMMIT_TREE, _UPDATE_REF = 0, 1, 2, 3, 4
_GIT_DIR, _HEAD, _DIFF, _RESTORE, _CLEAN = 5, 6, 7, 8, 9

_REF = re.compile(r'refs/heads/task/TASK-[0-9]+')
_ID = re.compile(r'[0-9a-f]{40}')
_NOT_IN_A_PATH = frozenset('\\:"*?[]')
_NOT_IN_A_NAME = frozenset('<>\n\0')


def _refused(reason, findings):
    return {'result': 'refused', 'reason': reason, 'findings': list(findings)}


def _one_path(path, state_name):
    """The findings of one path (none when it passes); none holds the path's text."""
    if not path or any(ord(c) < 0x20 or ord(c) > 0x7e for c in path):
        return ['paths: a path is empty or holds a character outside 0x20 to 0x7e']
    if any(c in _NOT_IN_A_PATH for c in path):
        return ['paths: a path holds a backslash, a colon, a quote, a star, a question mark or a bracket']
    if path.startswith(('-', '/')):
        return ['paths: a path begins with a dash or a slash']
    names = path.split('/')
    if any(n in ('', '.', '..') or n.endswith(('.', ' ')) for n in names):
        return ['paths: a path has a name that is empty, a dot, two dots, or ends in a dot or a space']
    if names[0].lower() == state_name.lower():
        return ['paths: a path is under the project-state directory']
    if any(n.lower() == '.git' for n in names):
        return ['paths: a path holds a .git name']
    return []


def _state_findings(state_name):
    if not (isinstance(state_name, str) and len(state_name) > 1 and state_name.startswith('.')
            and '/' not in state_name and '\\' not in state_name):
        return ['state_name: not a name that begins with a dot']
    return []


def _paths_findings(paths, state_name):
    """The findings of the path list; the state name must already have passed."""
    if not (isinstance(paths, list) and paths and all(type(p) is str for p in paths)):
        return ['paths: not a non-empty list of str']
    found, seen = [], set()
    for p in paths:
        if p.lower() in seen:
            found.append('paths: a path is listed twice (letter case ignored)')
        seen.add(p.lower())
        found.extend(_one_path(p, state_name))
    return found


def _common_findings(repo, paths, state_name):
    found = []
    if not (isinstance(repo, str) and os.path.isabs(repo)):
        found.append('repo: not an absolute path')
    state = _state_findings(state_name)
    found.extend(state)
    if not state:
        found.extend(_paths_findings(paths, state_name))
    return found


def _capture_findings(repo, ref, old_head, paths, message, identity, state_name):
    found = _common_findings(repo, paths, state_name)
    if not (isinstance(ref, str) and _REF.fullmatch(ref)):
        found.append('ref: not refs/heads/task/TASK- followed by digits')
    if not (isinstance(old_head, str) and _ID.fullmatch(old_head)):
        found.append('old_head: not 40 lowercase hexadecimal characters')
    if not (isinstance(message, str) and message and '\0' not in message):
        found.append('message: not a non-empty string without NUL')
    else:
        try:
            message.encode('utf-8')
        except UnicodeError:
            found.append('message: not encodable as UTF-8')
    ok = (isinstance(identity, dict) and set(identity) == {'name', 'email'}
          and all(type(v) is str and v and not any(c in _NOT_IN_A_NAME for c in v) for v in identity.values()))
    if not ok:
        found.append('identity: not a mapping of a name and an e-mail, each non-empty without <, >, LF or NUL')
    return found


def _restore_findings(repo, paths, classes, state_name):
    found = _common_findings(repo, paths, state_name)
    if not (isinstance(classes, dict) and all(type(k) is str and v in CLASSES for k, v in classes.items())):
        found.append('classes: not a mapping of each path to modified, added or deleted')
    elif isinstance(paths, list) and set(classes) != set(p for p in paths if type(p) is str):
        found.append('classes: the keys are not exactly the listed paths')
    return found


def _build(form_tuple, values):
    """(the argument vector, None) or (None, findings): the form must be one of CAPTURE_FORMS and every placeholder
    must be filled by a value of its own form."""
    if form_tuple not in CAPTURE_FORMS:
        return None, ['form: not one of CAPTURE_FORMS']
    ids = list(values.get('ids', ()))
    allowed = values.get('allowed', ())
    out = []
    for token in form_tuple:
        if token == '<paths>':
            listed = values.get('paths')
            if not (isinstance(listed, list) and listed and all(p in allowed for p in listed)):
                return None, ['form: the paths are not a non-empty part of the listed paths']
            out.extend(listed)
        elif token in ('<tree>', '<id>'):
            if not (ids and isinstance(ids[0], str) and _ID.fullmatch(ids[0])):
                return None, ['form: an id is missing or not 40 lowercase hexadecimal characters']
            out.append(ids.pop(0))
        elif token == '<taskref>':
            ref = values.get('ref')
            if not (isinstance(ref, str) and _REF.fullmatch(ref)):
                return None, ['form: the reference is not a task reference']
            out.append(ref)
        elif token == '<zero>':
            out.append(ZERO)
        else:
            out.append(token)
    if ids:
        return None, ['form: an id was given that the form does not take']
    return out, None


def _env(index, identity):
    """(the environment built from nothing, None) or (None, findings)."""
    path = os.environ.get('PATH')
    if not path or any(not e or not os.path.isabs(e) for e in path.split(os.pathsep)):
        return None, ['environment: PATH is empty or has an entry that is not an absolute path']
    env = {'PATH': path}
    root = os.environ.get('SYSTEMROOT')
    if root is not None:
        env['SYSTEMROOT'] = root
    for key, value in CAPTURE_ENV_FIXED:
        env[key] = os.devnull if value == '<null>' else value
    if index is not None:
        env['GIT_INDEX_FILE'] = index
    if identity is not None:
        env['GIT_AUTHOR_NAME'] = env['GIT_COMMITTER_NAME'] = identity['name']
        env['GIT_AUTHOR_EMAIL'] = env['GIT_COMMITTER_EMAIL'] = identity['email']
    return env, None


def _step(repo, form_tuple, values, index=None, identity=None, data=None):
    """Run one form. (the answer {'exit', 'out', 'err'}, None), or (None, a refused mapping)."""
    form, found = _build(form_tuple, values)
    if found:
        return None, _refused('invalid-argument', found)
    env, found = _env(index, identity)
    if found:
        return None, _refused('git-failed', found)
    name = form_tuple[0]
    try:
        done = subprocess.run(['git'] + list(CAPTURE_OPTIONS) + ['-c', 'core.hooksPath=' + os.devnull] + form,
                              shell=False, timeout=60, env=env, input=data, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, cwd=repo, check=False)
        answer = {'exit': done.returncode, 'out': done.stdout, 'err': done.stderr}
    except subprocess.TimeoutExpired:
        return None, _refused('timeout', ['%s: the call did not finish in time' % name])
    except Exception as exc:
        return None, _refused('git-failed', ['%s: the call raised %s' % (name, type(exc).__name__)])
    if type(answer['exit']) is not int or not isinstance(answer['out'], bytes) or not isinstance(answer['err'], bytes):
        return None, _refused('git-failed', ['%s: the answer is out of form' % name])
    return answer, None


def _ok_step(repo, form_tuple, values, index=None, identity=None, data=None):
    """Like _step, and an exit other than 0 is a refusal 'git-failed'."""
    answer, refused = _step(repo, form_tuple, values, index, identity, data)
    if refused is not None:
        return None, refused
    if answer['exit'] != 0:
        return None, _refused('git-failed', ['%s: exit %d' % (form_tuple[0], answer['exit'])])
    return answer, None


def _text(answer):
    return answer['out'].decode('ascii').strip()


def _head_is(repo, old_head):
    """None when HEAD is old_head, else a refused mapping."""
    answer, refused = _ok_step(repo, CAPTURE_FORMS[_HEAD], {})
    if refused is not None:
        return refused
    if _text(answer) != old_head:
        return _refused('head-moved', ['HEAD is not the commit the caller read'])
    return None


def _capture(repo, ref, old_head, paths, message, identity, state_name):
    found = _capture_findings(repo, ref, old_head, paths, message, identity, state_name)
    if found:
        return _refused('invalid-argument', found)
    listed = list(paths)
    base = {'allowed': listed}
    answer, refused = _ok_step(repo, CAPTURE_FORMS[_GIT_DIR], base)
    if refused is not None:
        return refused
    git_dir = _text(answer)
    if not git_dir or not os.path.isabs(git_dir):
        return _refused('git-failed', ['rev-parse: the git directory is not an absolute path'])
    index = os.path.join(git_dir, INDEX_NAME)
    refused = _head_is(repo, old_head)
    if refused is not None:
        return refused
    answer, refused = _ok_step(repo, CAPTURE_FORMS[_READ_TREE], base, index)
    if refused is not None:
        return refused
    answer, refused = _ok_step(repo, CAPTURE_FORMS[_UPDATE_INDEX], {'allowed': listed, 'paths': listed}, index)
    if refused is not None:
        return refused
    answer, refused = _ok_step(repo, CAPTURE_FORMS[_WRITE_TREE], base, index)
    if refused is not None:
        return refused
    tree = _text(answer)
    answer, refused = _ok_step(repo, CAPTURE_FORMS[_COMMIT_TREE], {'ids': [tree, old_head]}, None, identity,
                               message.encode('utf-8'))
    if refused is not None:
        return refused
    commit = _text(answer)
    answer, refused = _step(repo, CAPTURE_FORMS[_UPDATE_REF], {'ref': ref, 'ids': [commit]})
    if refused is not None:
        return refused
    if answer['exit'] != 0:
        if EXISTS_TEXT in answer['err']:
            return _refused('ref-exists', ['update-ref: the reference exists'])
        return _refused('git-failed', ['update-ref: exit %d' % answer['exit']])
    refused = _head_is(repo, old_head)
    if refused is not None:
        return refused
    answer, refused = _ok_step(repo, CAPTURE_FORMS[_DIFF], {'ids': [old_head, commit]})
    if refused is not None:
        return refused
    names = [n for n in answer['out'].decode('utf-8').split('\n') if n]
    if sorted(names) != sorted(listed):
        return _refused('name-list-mismatch', ['diff: the commit changes other paths than the listed ones'])
    return {'result': 'done', 'commit': commit}


def capture(repo, ref, old_head, paths, message, identity, state_name):
    """Write the listed paths of the working tree as one commit on the new reference ref, whose parent is old_head.

    repo: an absolute path. ref: refs/heads/task/TASK- and digits. old_head: the 40 hexadecimal characters of HEAD that
    the caller read. paths: a non-empty list of file paths in git form. message: the commit message. identity: a mapping
    with the keys name and email. state_name: the name of the project-state directory, which begins with a dot."""
    try:
        return _capture(repo, ref, old_head, paths, message, identity, state_name)
    except Exception as exc:
        return _refused('git-failed', ['capture: a step raised %s' % type(exc).__name__])


def _restore(repo, paths, classes, state_name):
    found = _restore_findings(repo, paths, classes, state_name)
    if found:
        return _refused('invalid-argument', found)
    listed = list(paths)
    back = [p for p in listed if classes[p] in ('modified', 'deleted')]
    added = [p for p in listed if classes[p] == 'added']
    if back:
        answer, refused = _ok_step(repo, CAPTURE_FORMS[_RESTORE], {'allowed': listed, 'paths': back})
        if refused is not None:
            return refused
    if added:
        answer, refused = _ok_step(repo, CAPTURE_FORMS[_CLEAN], {'allowed': listed, 'paths': added})
        if refused is not None:
            return refused
    return {'result': 'done'}


def restore(repo, paths, classes, state_name):
    """Put the listed paths back to HEAD: a modified or a deleted path is restored from HEAD, an added path (one that
    HEAD does not have) is removed by clean, never with -d or -x. classes maps each listed path to modified, added or
    deleted. The module does not read the status; the caller checks the tree afterwards."""
    try:
        return _restore(repo, paths, classes, state_name)
    except Exception as exc:
        return _refused('git-failed', ['restore: a step raised %s' % type(exc).__name__])
