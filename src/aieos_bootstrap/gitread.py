"""The Git reader of gov-AIEOS (task TASK-024; constitution INV-001; specification 4 revision 3, section 7 item 4 and
section 12 point 4; DEF-0030): the first piece of the core's caller, and INV-001's single process wrapper.

INV-001 allows a process only "through one wrapper with a pinned list of allowed executables". This module is that
wrapper. Its pinned list is [git], and git runs only with one of four read-only subcommands, each in one fixed form:

- rev-parse: ["rev-parse", "--verify", "--end-of-options", <name>], the name an object id, HEAD, or "refs/heads/" followed by
  one branch name that is_base_name accepts (specification 7 revision 5, section 5: the launcher's base-tip check; TASK-106);
- cat-file: ["cat-file", "-p", <id>] or ["cat-file", "-t", <id>];
- rev-list: ["rev-list", "--parents", "-n", "1", <id>];
- diff-tree: ["diff-tree", "--no-commit-id", "--name-only", "-r", "--no-renames", "--no-ext-diff", "--no-textconv",
  "-z", "--root", <id>];

where an object id is 40 or 64 lowercase hexadecimal characters. Anything else is refused before any process starts
(fail closed). A further executable or subcommand is a change to this module and to the workflow's pattern rule for
it (the CI workflow's revision 8), each under its own decision.

``run(repo, args, timeout)`` starts git with no shell, the standard input closed, a pinned working directory (the
repository given) and a timeout, and closes git's own ways of starting other programs by fixed options: no pager,
core.fsmonitor off, core.hooksPath the null device, diff.external empty, and an environment built from nothing but
PATH, SYSTEMROOT (only when present, for Windows), GIT_CONFIG_NOSYSTEM, GIT_CONFIG_GLOBAL (the null device),
GIT_TERMINAL_PROMPT, GIT_OPTIONAL_LOCKS ("0", so git refreshes no index), GIT_NO_LAZY_FETCH ("1", so a partial clone
starts no fetch) and LC_ALL. It refuses, before any process starts, when the PATH it would pass is empty or, split by
os.pathsep, has an entry that is empty or not an absolute path, since on POSIX git would then be looked up relative
to the repository (erratum E1 of the contract, decision D-580). It returns the exit code and the output as bytes,
and raises nothing for a refused form, a timeout or a git that cannot be started.

``parse_commit(data)`` and ``parse_paths(data)`` are pure: they turn the bytes of "cat-file -p" of a commit and of the
diff-tree form into values, and give an error, never an exception, for bytes out of form.

Readings (the implementer's, for the decision agent's ruling, not the contract's own words):
- A commit's header lines are, in order, one tree line, any parent lines, one author line and one committer line,
  then any further header lines of the form "<key> <value>" (the key lowercase letters and hyphens, as git's encoding,
  gpgsig and mergetag), each optionally followed by continuation lines that begin with a space; such further lines
  are accepted and not returned. Anything else is a header line out of form.
- The trailers are taken from the message's last paragraph as the contract states it, including when that paragraph
  is the message's only one. git's own rule differs: it treats a message's first paragraph as the subject, so a
  one-line message "Key: value" has no trailer for git but one here. A caller that relies on a trailer must check
  that the message has a body (carried to DEF-0030).
- Bytes of the paths form that do not end with NUL keep their last name, so truncated output parses without error; a
  caller checks run's exit and error before parsing.

Limits (TASK-024 AC10): git is trusted as the operating system finds it, by its name, not by a pinned path or hash
(on Windows a git program placed in a place that process creation searches before PATH, such as the directory of the
Python program or the current directory of the calling process, would be found first), with the caller's PATH taken
as given once every entry of it is absolute; on Windows the program search does not use the PATH passed to git, so
the refusal of an empty or relative PATH entry closes that route on POSIX only; the repository's own configuration
is still read by git, and the fixed options override only the keys named above; GIT_NO_LAZY_FETCH is ignored by a
git older than 2.44, and GIT_CONFIG_GLOBAL by one older than 2.32; core.hooksPath has no test of effect, since none
of the four subcommands runs a hook; output is not capped in size, and cat-file reads whatever object an id names;
the repository path is the caller's; the parsers check form, not that a commit exists or is reachable;
no caller exists yet. The module opens, writes and removes no file, reads no clock, and reads the environment only
for PATH and SYSTEMROOT.
"""

import os
import re
import subprocess

SUBCOMMANDS = ('cat-file', 'diff-tree', 'rev-list', 'rev-parse')
MAX_TIMEOUT = 120
OBJECT_ID = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
DIFF_TREE = ['diff-tree', '--no-commit-id', '--name-only', '-r', '--no-renames', '--no-ext-diff', '--no-textconv', '-z',
             '--root']
FIXED_OPTIONS = ['--no-pager', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=' + os.devnull, '-c',
                 'diff.external=', '-c', 'core.pager=cat']
HEADER_KEY = re.compile(r'[a-z][a-z-]*')
TRAILER = re.compile(r'([A-Za-z0-9-]+): (.*)')


def _result(exit_code, out, err, error):
    return {'exit': exit_code, 'out': out, 'err': err, 'error': error}


def _is_id(s):
    return OBJECT_ID.fullmatch(s) is not None


BASE_NAME_CHARS = re.compile(r'[A-Za-z0-9._/-]{1,100}')
BRANCH_PREFIX = 'refs/heads/'


def is_base_name(name):
    """Whether name is one base branch name of specification 7 revision 5 (section 5): a str of 1 to 100 ASCII letters,
    digits, ".", "_", "-" and "/"; split on "/", every part is non-empty, begins with a letter or a digit and does not end
    in "." or ".lock"; and ".." occurs nowhere. The rule is stricter than git's own (TASK-106 AC3). Pure: it starts no
    process and reads nothing."""
    if type(name) is not str or BASE_NAME_CHARS.fullmatch(name) is None or '..' in name:
        return False
    for part in name.split('/'):
        if not part or not part[0].isalnum() or part.endswith('.') or part.endswith('.lock'):
            return False
    return True


def _is_branch_ref(s):
    return s.startswith(BRANCH_PREFIX) and is_base_name(s[len(BRANCH_PREFIX):])


def form_error(repo, args, timeout):
    """Why repo, args and timeout are not a pinned form, or None when they are one (TASK-024 AC1)."""
    # exact types, not subclasses: a subclass of list or str could compare or iterate otherwise than it indexes
    if type(repo) is not str or not os.path.isabs(repo):
        return 'repo is not an absolute path'
    if not os.path.isdir(repo):
        return 'repo is not an existing directory'
    if type(timeout) not in (int, float) or not 0 < timeout <= MAX_TIMEOUT:
        return 'timeout is not a number of seconds greater than 0 and at most %d' % MAX_TIMEOUT
    if type(args) is not list or not args or not all(type(a) is str for a in args):
        return 'args is not a non-empty list of strings'
    sub = args[0]
    if sub not in SUBCOMMANDS:
        return 'subcommand not in the pinned list'
    if sub == 'rev-parse':
        ok = len(args) == 4 and args[1:3] == ['--verify', '--end-of-options'] and (args[3] == 'HEAD' or _is_id(args[3]) or _is_branch_ref(args[3]))
    elif sub == 'cat-file':
        ok = len(args) == 3 and args[1] in ('-p', '-t') and _is_id(args[2])
    elif sub == 'rev-list':
        ok = len(args) == 5 and args[1:4] == ['--parents', '-n', '1'] and _is_id(args[4])
    else:
        ok = len(args) == len(DIFF_TREE) + 1 and args[:-1] == DIFF_TREE and _is_id(args[-1])
    if not ok:
        return 'args are not the fixed form of %s' % sub
    return None


def environment():
    """The environment git runs with: built from nothing but the keys TASK-024 AC2 names."""
    env = {'PATH': os.environ.get('PATH', '')}
    if 'SYSTEMROOT' in os.environ:
        env['SYSTEMROOT'] = os.environ['SYSTEMROOT']
    env['GIT_CONFIG_NOSYSTEM'] = '1'
    env['GIT_CONFIG_GLOBAL'] = os.devnull
    env['GIT_TERMINAL_PROMPT'] = '0'
    env['GIT_OPTIONAL_LOCKS'] = '0'
    env['GIT_NO_LAZY_FETCH'] = '1'
    env['LC_ALL'] = 'C'
    return env


def path_error(path):
    """Why the PATH git would get is refused, or None (erratum E1): it must be non-empty and every entry absolute."""
    entries = path.split(os.pathsep)
    if not path or any(not e or not os.path.isabs(e) for e in entries):
        return 'PATH has an empty or relative entry'
    return None


def run(repo, args, timeout=30):
    """Run git with one pinned form (TASK-024 AC1 to AC3): a mapping with exactly the keys exit, out, err and error."""
    why = form_error(repo, args, timeout)
    env = environment()
    if why is None:
        why = path_error(env['PATH'])
    if why is not None:
        return _result(None, b'', b'', why)
    try:
        p = subprocess.run(['git'] + FIXED_OPTIONS + ['-C', repo] + list(args), shell=False, stdin=subprocess.DEVNULL,
                           capture_output=True, cwd=repo, timeout=timeout, check=False, env=env)
    except subprocess.TimeoutExpired:
        return _result(None, b'', b'', 'timeout')
    except OSError as e:
        return _result(None, b'', b'', 'git could not be started (%s)' % type(e).__name__)
    return _result(p.returncode, p.stdout, p.stderr, None)


def _commit_error(why):
    return {'tree': None, 'parents': [], 'author': None, 'committer': None, 'message': '', 'trailers': [], 'error': why}


def trailers(message):
    """The [key, value] pairs of the message's last paragraph when every line of it is "<key>: <value>", else []."""
    paragraphs = [p for p in message.strip('\n').split('\n\n') if p.strip('\n')]
    if not paragraphs:
        return []
    out = []
    for line in paragraphs[-1].strip('\n').split('\n'):
        m = TRAILER.fullmatch(line)
        if m is None:
            return []
        out.append([m.group(1), m.group(2)])
    return out


def parse_commit(data):
    """The values of a commit object's bytes, as "git cat-file -p" prints them (TASK-024 AC4)."""
    if not isinstance(data, bytes):
        return _commit_error('data is not bytes')
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return _commit_error('data is not UTF-8')
    head, sep, message = text.partition('\n\n')
    if not sep:
        return _commit_error('no empty line after the header')
    lines = head.split('\n')
    i = 0
    if i >= len(lines) or not lines[i].startswith('tree ') or not _is_id(lines[i][5:]):
        return _commit_error('no tree line, or a tree line out of form')
    tree = lines[i][5:]
    i += 1
    parents = []
    while i < len(lines) and lines[i].startswith('parent '):
        if not _is_id(lines[i][7:]):
            return _commit_error('a parent line out of form')
        parents.append(lines[i][7:])
        i += 1
    values = {}
    for key in ('author', 'committer'):
        if i >= len(lines) or not lines[i].startswith(key + ' ') or not lines[i][len(key) + 1:]:
            return _commit_error('no %s line, or a %s line out of form' % (key, key))
        values[key] = lines[i][len(key) + 1:]
        i += 1
    while i < len(lines):
        key, space, value = lines[i].partition(' ')
        if not space or HEADER_KEY.fullmatch(key) is None or key in ('tree', 'parent', 'author', 'committer'):
            return _commit_error('a header line out of form')
        i += 1
        while i < len(lines) and lines[i].startswith(' '):
            i += 1
    return {'tree': tree, 'parents': parents, 'author': values['author'], 'committer': values['committer'],
            'message': message, 'trailers': trailers(message), 'error': None}


def parse_paths(data):
    """The changed paths in the bytes of the diff-tree form, NUL-separated (TASK-024 AC5)."""
    if not isinstance(data, bytes):
        return {'paths': [], 'error': 'data is not bytes'}
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return {'paths': [], 'error': 'data is not UTF-8'}
    names = text.split('\0')
    if names and names[-1] == '':
        names = names[:-1]
    if any(n == '' for n in names):
        return {'paths': [], 'error': 'an empty name before the last NUL'}
    return {'paths': names, 'error': None}
