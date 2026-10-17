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
- Writes made by a shell command (tee, cp, a script; a ">" redirection is refused by the character set below) are
  not judged against the write-set; only Write and Edit calls are. Pushes by other means than git (gh, git send-pack,
  a network call) are not detected. Both are lower bounds, as specification 5 line 73 says of the read-set.
- The tool names are the model-side tool_use names seen in this project's transcripts; that a hook input's tool_name
  carries the same names is supported live only for Bash (D-1202, D-1203), and unmeasured for the other tools.
- The shell checks read the command text only and refuse when unsure, so they over-refuse. First the push checks: any
  text with a git word and "push" in any letter case anywhere once quotes and backslashes are removed (D-1228 F10:
  "git PUSH" is refused too, its effect on Windows being unmeasured), or with a git word and any "$",
  "`" or "%" anywhere, is refused with reason push; a text with an unclosed quote is refused with reason parse (push
  if it has a git word and "push"). Then the character set (D-1223 F9): a text goes to the allowlist only if every
  character is an ASCII letter or digit, a space, a tab, a newline (a carriage return only right before a newline), or
  one of - _ . / : = , + ; & | ( ); any other character refuses with reason parse. So no quote, backslash, "$", "`",
  "%", "#", "<", ">", "{", "}", "@", glob character or non-ASCII character can reach the allowlist, and the split never
  has to agree with a shell on quoting, escapes, comments, here-documents, here-strings, substitutions or line
  continuation. This over-refuses heavily: no quoted argument at all is allowed (git commit -m "x" is refused), nor
  "2>&1". It supersedes the form-by-form rules F5 to F8 of decisions D-1219 and D-1220. With this set the split and
  both shells agree on where commands and words begin and end; their meanings differ (for example of "&", "|", "="
  and ","), and PowerShell's own syntax is not parsed. An allowlist entry holding a character outside the set never
  matches: the contract's own entry "timeout 110 python tests/run_tests.py < /dev/null" included, since "<" is outside.
- A blank command is "uncovered", reason input. A text of separators only, with no simple command (";", "&&", "( )"),
  is refused with reason parse (D-1228 F10), so under an empty allowlist every shell call with a non-blank text is
  refused.
- Pushes the text does not show are not seen: an alias set outside the call, and a push inside a script file or a
  program the command runs (for example "bash run.sh"). The allowlist is the backstop. An allowlist entry for a
  program that runs code (bash, sh, powershell, cmd, python, a script) admits whatever that code does, pushes built
  from parts included (for example a script that builds the word from "gi" and "t"), and an entry for git with any
  arguments admits any git command but a literal push in any letter case (D-1212 F3): for example git -c with
  help.autocorrect, which may run a push from a mistyped word, or with a setting that runs a program. Entries for
  xargs, find with -exec, timeout and other programs that run a command given to them admit that command too.
- The allowlist is matched word by word, case-sensitively, from a simple command's first word as given: leading
  assignments and prefixes are not skipped, so "env X=1 git status" or "GIT status" is refused under an entry
  "git status" (over-refuses).
- Wrong arguments are refused before any concern is sorted, so even a read call then gives "refuse", reason argument.
- Also: a refusal with reason record carries no record (AC7); a tool_input that is not a mapping, or a tool_name that
  is not a string, is "uncovered", reason tool; an exception inside judge gives "uncovered", reason input (AC8); a
  path above the drive root is "outside"; a read call is allowed whatever its path.
- A relative file path is "uncovered": judge relies on no hook-input key other than tool_name and tool_input, so it
  passes no cwd (D-1212 F4). A UNC, device or rooted path without a drive, an alternate data stream, a NUL, a name of
  only dots or spaces, and a trailing space or dot on a name are "uncovered", reason path.
- Links and junctions are not resolved: the lexical form is what is judged. Below the root, a path is compared with
  the write-set case-sensitively, so a path that differs from an allowed one only in case is refused (over-refuses).
  Windows reserved device names (for example NUL or CON, "docs/NUL.md" included) are not treated specially, and 8.3
  short names are judged as written.
- A refusal record's refers_to holds up to 200 characters: the whole command text for a push or parse refusal, the
  failing simple command's words joined by spaces for an allowlist refusal, the normalised path for a write inside the
  root, and the path as given for one outside it. So a credential typed into a command would be copied into the
  record; redaction before a record is written is part CC-2's.
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
_SAFE = re.compile(r'[A-Za-z0-9 \t\n_.,/:=+;&|()-]*')
_STRIP = re.compile(r'''['"\\]''')
_PUSH = re.compile(r'(?<![A-Za-z0-9_-])push(?![A-Za-z0-9_-])', re.I)
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
    return i < len(words) and _is_git(words[i]) and 'push' in [w.lower() for w in words[i + 1:]]


def _text_pushes(text):
    """The whole-text rule (D-1208 M1, D-1212 F1 and F2): with every quote and backslash removed, a git word and a
    bounded "push" anywhere; or a git word and any "$", "`" or "%" (an expansion, so unsure)."""
    stripped = _STRIP.sub('', text)
    if not (any(_is_git(w) for w in _WORD.findall(text)) or _GIT.search(stripped)):
        return False
    return bool(_PUSH.search(stripped)) or any(c in text for c in '$`%')


def _safe(text):
    """D-1223 F9: every character is in the safe set (a carriage return only right before a newline), so that the
    split and both shells agree on where each command and word begins and ends."""
    return bool(_SAFE.fullmatch(text.replace('\r\n', '\n')))


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
        # D-1228 F10: separators only, no simple command, so nothing for the allowlist to admit (AC6)
        if not commands:
            return _refuse('shell', 'parse', _record(record_id, recorder, task_id, 'shell_not_allowed', text))
        if any(_pushes(c) for c in commands) or _text_pushes(text):
            return _refuse('shell', 'push', _record(record_id, recorder, task_id, 'git_push_refused', text))
        # D-1223 F9: only a text of the safe character set reaches the allowlist; it supersedes F5 to F8
        if not _safe(text):
            return _refuse('shell', 'parse', _record(record_id, recorder, task_id, 'shell_not_allowed', text))
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
