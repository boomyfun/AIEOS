"""The Claude Code adapter's hook entry, part CC-2 (task TASK-062; specification 5 revision 3, sections 6 and 8 and
section 11 points 5, 6 and 7; specification 2 revision 5, section 6.2).

Two pure functions, called only by their tests:

1. ``allowlist_findings(allowlist)``: the allowlist's form, checked before judge is called (AC4). An empty list of
   findings means the allowlist is well formed.
2. ``entry(stdin_bytes, root, task_id, write_set, allowlist, record_id, recorder)``: from the bytes Claude Code would
   write to a PreToolUse hook's standard input to what the hook would return (AC1 to AC6). The checks run in this
   order, and the first that fails gives the result: the type of stdin_bytes (AC1), the allowlist's form (AC4), the
   decoding and parsing (AC2), then aieos_bootstrap.claude_code.judge on a new mapping that holds only the input's
   tool_name and tool_input. Exit code 0 is given only for judge's "allow"; every refusal and every "uncovered" gives
   exit code 2 (fail closed; specification 5 section 11 point 5; decision D-1236 Q4). A refusal's observation record is
   returned unchanged from judge, as a value for the core: no file is written and no channel is opened.

What these functions show, and what they do not (AC7):
- They judge given bytes only. Whether Claude Code runs the hook, with which input, and whether exit code 2 blocks the
  call are unmeasured (specification 5 lines 65 and 80; C6, the owner's to measure). In session 1947b313 a hook with
  matcher "*" was seen not to refuse Read calls it was written to refuse (decisions D-1202 and D-1203).
- The exit-code form is cited from Claude Code's documentation, not measured: the hooks reference
  (https://code.claude.com/docs/en/hooks, as summarised by a web-reading tool on 2026-10-18: a summary, not the page)
  says that exit code 0 is success and that Claude never
  sees standard error then; that exit code 2 on PreToolUse blocks the tool call, with the hook's standard error as the
  message unless JSON printed on standard output makes a blocking decision; and that any other exit code, a hook that
  does not start, or invalid JSON output is a non-blocking error and the action goes ahead. So the protection fails
  open outside these functions when the hook program does not start, is killed or exits otherwise (unmeasured). The
  entry gives only exit codes 0 and 2 and no standard-output text.
- The entry is meant for a hook whose matcher names only the judged tools (Write, Edit, Bash, PowerShell, Read, Grep,
  Glob); under a matcher "*" it would block every other tool's call. The matcher is the owner's to choose when the hook
  is placed (part CC-3; A51 item (4)); nothing here places a hook or chooses a matcher.
- Of the hook input only tool_name and tool_input are read (D-1236 Q2). The root is the caller's argument, never the
  input's cwd (D-1212 F4); session_id, cwd, hook_event_name and every other key are not read, so placed on another hook
  event the entry would judge in the same way. The ids that tie an observation to a session and a lease, and how a
  record reaches the core, are point 7's rest.
- "uncovered" is never "allow", and it carries no record (no new record key is made; a marked observation waits for a
  revision of specification 2).
- The standard-error line is fixed text, the verdict and the reason only: no path, command or tool name from the input
  is echoed, and an exception gives only its type's name. A reason of judge's outside claude_code.REASONS gives
  "uncovered", reason "entry", so the line holds fixed words whatever judge returns. The result's findings and record
  may hold input text (judge names an unjudged tool in a finding, and a record's refers_to holds the path or command);
  only the standard-error line is fixed.
- A refusal record is returned unchanged, so a credential typed into a command stays in its refers_to
  (aieos_bootstrap.claude_code's docstring; D-1219 R2-2); redaction before any record is written is not done here.
- The allowlist's form check refuses the first words below, a first word with "=", any character outside its set, and
  any spacing other than single spaces. Its lists are this module's minimum and not complete (D-1236): an entry not on
  them for a program that runs code (a build tool, a package runner, a script) still admits whatever that code does,
  as aieos_bootstrap.claude_code's docstring states. Names outside the lists pass even when they run code, for
  example python3.12, pythonw, iex, Invoke-Expression, source, ".", wscript, cscript, mshta, bun, a ".vbs" or ".jar"
  script, a name with a trailing dot such as "bash.", and git options after the subcommand such as "git log
  --output=x"; matching them would change the name rule of the contract's AC4. A malformed allowlist refuses every call, whatever its tool, as a
  caller's error with no record. The allowlist's content stays the caller's policy (point 6), never a default here.
- Every limit of aieos_bootstrap.claude_code holds here too, and specification 5 section 11 points 3, 4, 10 and 12 stay
  open. Nothing is installed or measured.

Purity: it imports only the standard library's json module and aieos_bootstrap's claude_code; it starts no process,
opens no file, reads no standard input, prints nothing, reads no clock or environment and makes no network or model
call. The module keeps no state.
"""

import json

from aieos_bootstrap import claude_code

REASONS = ('allowlist_form', 'input_bytes', 'input_json', 'input_shape', 'entry')
RESULT_KEYS = ('exit_code', 'stderr', 'verdict', 'concern', 'reason', 'findings', 'record')
STDERR_PREFIX = 'AIEOS claude_code_hook: '
ENTRY_CHARACTERS = frozenset('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 -_./:=,+')
REFUSED_FIRST_WORDS = ('bash', 'sh', 'zsh', 'dash', 'ksh', 'fish', 'powershell', 'pwsh', 'cmd', 'wsl', 'python',
                       'python3', 'py', 'node', 'deno', 'npx', 'perl', 'ruby', 'php', 'env', 'xargs', 'find', 'timeout',
                       'nohup', 'exec', 'eval', 'command', 'sudo', 'time', 'nice')
REFUSED_SUFFIXES = ('.sh', '.ps1', '.py', '.bat', '.cmd', '.js', '.pl', '.rb')
REFUSED_GIT_SUBCOMMANDS = ('config', 'submodule', 'bisect', 'rebase', 'filter-branch', 'difftool', 'mergetool', 'help')


def _result(verdict, concern, reason, findings=(), record=None):
    return {'exit_code': 0 if verdict == 'allow' else 2,
            'stderr': '' if verdict == 'allow' else STDERR_PREFIX + verdict + ' (' + reason + ')',
            'verdict': verdict, 'concern': concern, 'reason': reason, 'findings': list(findings), 'record': record}


def _name(word):
    """A first word's name: the part after its last "/" or ":", in lower case, a final ".exe" removed."""
    name = word.replace(':', '/').rsplit('/', 1)[-1].lower()
    if name.endswith('.exe'):
        name = name[:-4]
    return name


def _entry_findings(i, entry):
    if not isinstance(entry, str):
        return ['entry %d is not a string' % i]
    if not entry:
        return ['entry %d is empty' % i]
    if any(c not in ENTRY_CHARACTERS for c in entry):
        return ['entry %d holds a character outside the set' % i]
    if entry != entry.strip(' ') or '  ' in entry:
        return ['entry %d is not words separated by single spaces' % i]
    words = entry.split(' ')
    if '=' in words[0]:
        return ['entry %d has "=" in its first word' % i]
    name = _name(words[0])
    if name in REFUSED_FIRST_WORDS:
        return ['entry %d starts with a program that runs code or commands' % i]
    if name.endswith(REFUSED_SUFFIXES):
        return ['entry %d starts with a script' % i]
    if name == 'git' and (len(words) < 2 or words[1].startswith('-') or words[1].lower() in REFUSED_GIT_SUBCOMMANDS):
        return ['entry %d is git without a subcommand, with an option first or with a refused subcommand' % i]
    return []


def allowlist_findings(allowlist):
    """The findings of the allowlist's form (AC4); empty only when it is well formed. No exception escapes (AC5)."""
    try:
        if not isinstance(allowlist, list):
            return ['allowlist is not a list']
        findings = []
        for i, entry in enumerate(allowlist):
            findings += _entry_findings(i, entry)
        return findings
    except Exception as e:  # noqa: BLE001 - AC5: any exception becomes a finding, its type only
        return ['%s raised inside allowlist_findings' % type(e).__name__]


def _no_duplicates(pairs):
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError('a duplicate key')
    return dict(pairs)


def _no_constant(name):
    raise ValueError('a refused constant')


def _entry(stdin_bytes, root, task_id, write_set, allowlist, record_id, recorder):
    if not isinstance(stdin_bytes, bytes):
        return _result('refuse', None, 'argument', ['stdin_bytes is not a bytes object'])
    f = allowlist_findings(allowlist)
    if f:
        return _result('refuse', None, 'allowlist_form', f)
    if stdin_bytes.startswith(b'\xef\xbb\xbf'):
        return _result('uncovered', None, 'input_bytes', ['the input starts with a byte-order mark'])
    try:
        text = stdin_bytes.decode('utf-8', 'strict')
    except UnicodeDecodeError:
        return _result('uncovered', None, 'input_bytes', ['the input is not UTF-8'])
    try:
        value = json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_no_constant)
    except (ValueError, RecursionError):
        return _result('uncovered', None, 'input_json', ['the input is not one JSON value without duplicate keys or constants'])
    if not isinstance(value, dict):
        return _result('uncovered', None, 'input_shape', ['the input is not a JSON object'])
    hook = {k: value[k] for k in ('tool_name', 'tool_input') if k in value}
    r = claude_code.judge(hook, root, task_id, write_set, allowlist, record_id, recorder)
    if (not isinstance(r, dict) or tuple(sorted(r)) != tuple(sorted(claude_code.RESULT_KEYS))
            or r['verdict'] not in claude_code.VERDICTS or r['reason'] not in claude_code.REASONS):
        return _result('uncovered', None, 'entry', ['judge gave a result of another form'])
    record = r['record'] if r['verdict'] == 'refuse' else None
    return _result(r['verdict'], r['concern'], r['reason'], r['findings'], record)


def entry(stdin_bytes, root, task_id, write_set, allowlist, record_id, recorder):
    """What the hook would return for these bytes: a mapping with exactly RESULT_KEYS (AC6). No exception escapes."""
    try:
        return _entry(stdin_bytes, root, task_id, write_set, allowlist, record_id, recorder)
    except Exception as e:  # noqa: BLE001 - AC5: any exception becomes a result, its type only
        return _result('uncovered', None, 'entry', ['%s raised inside entry' % type(e).__name__])
