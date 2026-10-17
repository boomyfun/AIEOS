"""The Claude Code adapter's hooks mapping, part CC-1 (task TASK-061; specification 5 revision 3, section 6's table,
section 8 and section 11 points 7 and 8; specification 2 revision 5, section 6.2).

Two pure functions over one hook-input mapping, the object Claude Code gives a hook:

1. ``normalise_path(root, cwd, path)``: a Windows path, lexically, against the project root (AC3).
2. ``judge(hook_input, root, task_id, write_set, allowlist, record_id, recorder)``: sorts the call into a concern and
   gives a verdict, "allow", "refuse" or "uncovered" (AC2 to AC8):
   - write (tool names Write and Edit): the path of tool_input.file_path against the lease's write-set, matched by
     governor.matches, the matcher the core's write-set scope check uses (scope_drift), so the adapter's allow and
     refuse stay in step with the gate's;
   - shell (Bash and PowerShell): the text of tool_input.command, first for ``git push`` (AC5), then against the
     allowlist (AC6), which is the caller's (specification 5 section 11 point 6), never a default of this module;
   - read (Read, Grep and Glob): nothing is judged; the observed read-set record is part CC-2's;
   - every other tool name, MultiEdit and NotebookEdit (never seen in this project's transcripts) and every name
     beginning "mcp__" included, is "uncovered".
   A refusal on a policy concern carries the observation record the core would write (specification 5 section 8:
   outcome blocking, blocking_kind violation; line 64: deterministic_tool_local), checked by
   records.check_payload('record.added', record).

What these functions show, and what they do not (AC9):
- They judge a given hook-input mapping only. Whether Claude Code runs a hook for a tool, with which input, and whether
  a refusal stops the call are unmeasured (specification 5 lines 65 and 80; C6, the owner's to measure). In session
  1947b313 a hook with matcher "*" was seen not to refuse Read calls it was written to refuse (decisions D-1202 and
  D-1203).
- "uncovered" is never "allow": it says "not judged here". What a caller does with it is part CC-2's, under
  specification 5 section 8 and point 5.
- Writes made by a shell command (">", tee, cp, a script) are not judged against the write-set; only Write and Edit
  calls are. Pushes by other means than git (gh, git send-pack, a network call) are not detected. Both are lower
  bounds, as specification 5 line 73 says of the read-set.
- The tool names are the model-side tool_use names seen in this project's transcripts; that a hook input's tool_name
  carries the same names is supported live only for Bash (D-1202, D-1203), and unmeasured for the other tools.
- The shell checks read the command text only and refuse when unsure, so they over-refuse: any text with a git word
  and "push" anywhere once quotes and backslashes are removed, or with a git word and any "$", "`" or "%", is refused;
  PowerShell's own syntax is not parsed. An alias or a variable set outside the call, and a push inside a script file
  or a program the command runs (for example "bash run.sh"), are not seen: the allowlist is the backstop, and an entry
  that admits an interpreter with any file, or git with any arguments, admits such pushes (D-1212 F3).
- A relative file path is "uncovered": judge relies on no hook-input key other than tool_name and tool_input, so it
  passes no cwd (D-1212 F4). Links and junctions are not resolved: the lexical form is what is judged.
- Open points left as limits: specification 5 section 11 points 4 (the read-set record's evidence_type), 6 (the
  allowlist's content), 10 (an abnormal session end) and 12 (a bound on repeated STOP: violation). A record names the
  session only in the recorder's words (records.py has no ``session`` key). This module is called only by its tests;
  nothing is installed or measured.

Purity: it imports only the standard library and aieos_bootstrap's records and governor; it starts no process, opens
no file, reads no clock or environment, resolves no link and makes no network or model call. The module keeps no state.
"""

import re

from aieos_bootstrap import governor
from aieos_bootstrap import records

RECORDER = 'the Claude Code adapter (aieos_bootstrap.claude_code)'
WRITE_TOOLS = ('Write', 'Edit')
SHELL_TOOLS = ('Bash', 'PowerShell')
READ_TOOLS = ('Read', 'Grep', 'Glob')
VERDICTS = ('allow', 'refuse', 'uncovered')
REASONS = ('argument', 'tool', 'input', 'path', 'write_set', 'parse', 'push', 'allowlist', 'record', 'read')
RESULT_KEYS = ('verdict', 'concern', 'reason', 'findings', 'record')
PREFIXES = ('env', 'command', 'exec', 'nohup', 'time', 'sudo', 'xargs')
REFERS_MAX = 200

_ABS = re.compile(r'[A-Za-z]:[\\/]')
_TASK = re.compile(r'TASK-[0-9]+')
_PATTERN = re.compile(r'[A-Za-z0-9._*/-]+')
_ASSIGN = re.compile(r'[A-Za-z_][A-Za-z0-9_]*=')
_WORD = re.compile(r'''[^\s'"`;&|(){}<>]+''')
_SEPARATORS = '\n;&|(){}`'
_STRIP = re.compile(r'''['"\\]''')
_PUSH = re.compile(r'(?<![A-Za-z0-9_-])push(?![A-Za-z0-9_-])')
_GIT = re.compile(r'(?<![A-Za-z0-9_-])git(?:\.exe)?(?![A-Za-z0-9_-])', re.I)


def _result(verdict, concern, reason, findings=(), record=None):
    return {'verdict': verdict, 'concern': concern, 'reason': reason, 'findings': list(findings), 'record': record}


def _bad_name(name):
    """A name that Windows treats specially or ambiguously: only spaces or dots, or a trailing space or dot."""
    if name in ('.', '..'):
        return False
    return name.strip(' .') == '' or name.endswith(' ') or name.endswith('.')


def _names(text):
    """The names of an absolute Windows path in "/" form, the drive first, or None when its form is uncovered."""
    if '\x00' in text:
        return None
    t = text.replace('\\', '/')
    if t.startswith('//'):
        return None
    if not _ABS.match(t):
        return None
    if ':' in t[2:]:
        return None
    names = [n for n in t[3:].split('/') if n != '']
    if any(_bad_name(n) for n in names):
        return None
    return [t[:2]] + names


def normalise_path(root, cwd, path):
    """(status, value): ("ok", "a/b/c") for a path under root, in its normalised form; ("outside", path) for one that
    is not under root; ("uncovered", a finding) for a form this module does not judge (AC3)."""
    rn = _names(root) if isinstance(root, str) else None
    if rn is None:
        return 'uncovered', 'root is not an absolute Windows path of a judged form'
    if not isinstance(path, str) or path == '':
        return 'uncovered', 'the path is not a non-empty string'
    if '\x00' in path:
        return 'uncovered', 'the path holds a NUL'
    p = path.replace('\\', '/')
    if p.startswith('//') or p.startswith('/'):
        return 'uncovered', 'the path is a UNC, device or rooted path without a drive'
    if _ABS.match(p):
        full = p
    else:
        if ':' in p:
            return 'uncovered', 'a relative path with ":"'
        if not isinstance(cwd, str) or _names(cwd) is None:
            return 'uncovered', 'a relative path with no absolute cwd'
        full = cwd.replace('\\', '/').rstrip('/') + '/' + p
    names = _names(full)
    if names is None:
        return 'uncovered', 'the path has a form that is not judged (an alternate data stream, a trailing space or dot, a name of only dots or spaces)'
    stack = [names[0]]
    for n in names[1:]:
        if n == '.':
            continue
        if n == '..':
            if len(stack) == 1:
                return 'outside', path
            stack.pop()
            continue
        stack.append(n)
    rstack = [rn[0]]
    for n in rn[1:]:
        if n == '.':
            continue
        if n == '..':
            if len(rstack) > 1:
                rstack.pop()
            continue
        rstack.append(n)
    if len(stack) <= len(rstack):
        return 'outside', path
    if [x.lower() for x in stack[:len(rstack)]] != [x.lower() for x in rstack]:
        return 'outside', path
    return 'ok', '/'.join(stack[len(rstack):])


def _split(text):
    """The simple commands of a shell text, each a list of words with quotes removed, or None for an unclosed quote."""
    commands, words, word, inword, q, i = [], [], [], False, None, 0
    while i < len(text):
        c = text[i]
        if q:
            if c == q:
                q = None
            elif c == '\\' and q == '"' and i + 1 < len(text):
                i += 1
                word.append(text[i])
            else:
                word.append(c)
            i += 1
            continue
        if c in '\'"':
            q, inword = c, True
        elif c in _SEPARATORS or (c == '$' and text[i + 1:i + 2] == '('):
            if inword:
                words.append(''.join(word))
            commands.append(words)
            words, word, inword = [], [], False
            if c == '$':
                i += 1
        elif c.isspace():
            if inword:
                words.append(''.join(word))
            word, inword = [], False
        else:
            word.append(c)
            inword = True
        i += 1
    if q:
        return None
    if inword:
        words.append(''.join(word))
    commands.append(words)
    return [w for w in commands if w]


def _is_git(word):
    w = word.lower()
    return w == 'git' or w == 'git.exe' or w.endswith('/git') or w.endswith('\\git') or w.endswith('/git.exe') or w.endswith('\\git.exe')


def _pushes(words):
    i = 0
    while i < len(words) and (_ASSIGN.match(words[i]) or words[i] in PREFIXES):
        i += 1
    return i < len(words) and _is_git(words[i]) and 'push' in words[i + 1:]


def _text_pushes(text):
    """The whole-text rule (D-1208 M1, D-1212 F1 and F2): with every quote and backslash removed, a git word and a
    bounded "push" anywhere; or a git word and any "$", "`" or "%" (an expansion, so unsure)."""
    stripped = _STRIP.sub('', text)
    if not (any(_is_git(w) for w in _WORD.findall(text)) or _GIT.search(stripped)):
        return False
    return bool(_PUSH.search(stripped)) or any(c in text for c in '$`%')


def _record(record_id, recorder, task_id, evidence_type, refers_to):
    return {'record_id': record_id, 'fact_kind': 'observation', 'source_class': 'deterministic_tool_local',
            'outcome': 'blocking', 'blocking_kind': 'violation', 'recorder': RECORDER + ', for ' + recorder,
            'subject': task_id, 'evidence_type': evidence_type, 'refers_to': refers_to[:REFERS_MAX]}


def _refuse(concern, reason, record):
    findings = records.check_payload('record.added', record)
    if findings:
        return _result('refuse', concern, 'record', [str(f) for f in findings])
    return _result('refuse', concern, reason, (), record)


def _argument_findings(hook_input, root, task_id, write_set, allowlist, record_id, recorder):
    f = []
    if not isinstance(hook_input, dict):
        f.append('hook_input is not a mapping')
    if not isinstance(root, str) or not _ABS.match(root):
        f.append('root is not an absolute Windows path')
    if not isinstance(task_id, str) or not _TASK.fullmatch(task_id):
        f.append('task_id is not "TASK-" followed by digits')
    if (not isinstance(write_set, list) or not write_set
            or not all(isinstance(p, str) and _PATTERN.fullmatch(p) and '' not in p.split('/') for p in write_set)):
        f.append('write_set is not a non-empty list of patterns of the risk rules section 2 point 6')
    if not isinstance(allowlist, list) or not all(isinstance(a, str) and a.strip() and '\n' not in a and '\r' not in a for a in allowlist):
        f.append('allowlist is not a list of non-empty strings without a line break')
    for name, v in (('record_id', record_id), ('recorder', recorder)):
        if not isinstance(v, str) or not v:
            f.append('%s is not a non-empty string' % name)
    return f


def _judge(hook_input, root, task_id, write_set, allowlist, record_id, recorder):
    f = _argument_findings(hook_input, root, task_id, write_set, allowlist, record_id, recorder)
    if f:
        return _result('refuse', None, 'argument', f)
    tool = hook_input.get('tool_name')
    inp = hook_input.get('tool_input')
    if not isinstance(tool, str) or not isinstance(inp, dict):
        return _result('uncovered', None, 'tool', ['tool_name is not a string or tool_input is not a mapping'])
    if tool in READ_TOOLS:
        return _result('allow', 'read', 'read')
    if tool in WRITE_TOOLS:
        path = inp.get('file_path')
        if not isinstance(path, str):
            return _result('uncovered', 'write', 'input', ['tool_input.file_path is missing or not a string'])
        # cwd None (D-1212 F4): no hook-input key other than tool_name and tool_input is relied on, so a relative path
        # is uncovered
        status, value = normalise_path(root, None, path)
        if status == 'uncovered':
            return _result('uncovered', 'write', 'path', [value])
        if status == 'ok' and any(governor.matches(p, value) for p in write_set):
            return _result('allow', 'write', 'write_set')
        return _refuse('write', 'write_set', _record(record_id, recorder, task_id, 'write_outside_write_set', value))
    if tool in SHELL_TOOLS:
        text = inp.get('command')
        if not isinstance(text, str) or not text.strip():
            return _result('uncovered', 'shell', 'input', ['tool_input.command is missing, empty or not a string'])
        commands = _split(text)
        if commands is None:
            if _text_pushes(text):
                return _refuse('shell', 'push', _record(record_id, recorder, task_id, 'git_push_refused', text))
            return _refuse('shell', 'parse', _record(record_id, recorder, task_id, 'shell_not_allowed', text))
        if any(_pushes(c) for c in commands) or _text_pushes(text):
            return _refuse('shell', 'push', _record(record_id, recorder, task_id, 'git_push_refused', text))
        entries = [a.split() for a in allowlist]
        for c in commands:
            if not any(c[:len(e)] == e for e in entries):
                return _refuse('shell', 'allowlist', _record(record_id, recorder, task_id, 'shell_not_allowed', ' '.join(c)))
        return _result('allow', 'shell', 'allowlist')
    return _result('uncovered', None, 'tool', ['tool %r is not judged here' % (tool,)])


def judge(hook_input, root, task_id, write_set, allowlist, record_id, recorder):
    """The verdict for one hook-input mapping: a mapping with exactly RESULT_KEYS (AC8). No exception escapes."""
    try:
        return _judge(hook_input, root, task_id, write_set, allowlist, record_id, recorder)
    except Exception as e:  # noqa: BLE001 - AC8: any exception becomes a result
        return _result('uncovered', None, 'input', ['%s raised inside judge' % type(e).__name__])
