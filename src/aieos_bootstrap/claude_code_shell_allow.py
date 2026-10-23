"""The shell allowlist reader of the Claude Code adapter's PreToolUse program (task TASK-076; specification 2 revision 8,
section 7.2; specification 5 revision 5, section 11 points 5 and 6).

``read_allowlist(root, base, task_id, run=None)`` reads, at the given base and from Git's object store only (never the
working tree), through gitread.run only, two lists: the policy's ``shell_allow`` in the policy file .aieos/project.yaml
and the lease task's ``capabilities.shell.allow`` in docs/tasks/<task_id>.yaml; it checks each with
claude_code_hook.allowlist_findings, reading a list with any finding as empty, and gives the one list of specification
2 section 7.2 (combine). It gives a mapping with exactly result, policy, contract, allowlist and findings. run is a test
seam: a production caller does not pass it.

The flow, in this order:
(1) the arguments, as task_contract.read_contract checks them, in the order root, base, task_id: one out of form gives
    result "unreadable", every list empty and the one finding "argument: root", "argument: base" or "argument: task_id".
(2) the git reads, each run(root, ["cat-file", "-p", <id>], 10), run taken at call time (gitread.run by default), by a
    walk copied from task_contract's: the commit and the root tree are read once and shared; then the policy's walk
    (the .aieos tree, then the project.yaml blob) and the contract's walk (the docs tree, the tasks tree, then the
    <task_id>.yaml blob): at most seven calls. A refusal at the commit or the root tree empties both lists; one in a
    walk empties that walk's list only. Each blob's bytes are checked as task_contract checks a contract's (at most
    1 MiB, strict UTF-8, no U+FEFF, none of the controls C0 but the line feed, DEL, C1, U+2028 or U+2029).
(3) the grammars: parse_policy for the policy's text and parse_contract_shell for the contract's, each a fixed form,
    narrower than YAML, that gives an empty list for any other shape.
(4) the form check: allowlist_findings over each list; any finding makes that whole list empty.
(5) result "read": policy and contract are the checked lists, allowlist is combine(policy, contract), findings hold
    the steps' findings, each prefixed "policy: " or "contract: " (the walk's fixed words and the form check's words,
    never text from git, a tree or a file).
(6) no exception escapes: one outside the git steps gives "unreadable", every list empty, "entry: <type name>".

combine(policy, contract): for every pair of a policy entry and a contract entry where one's words (split on single
spaces) are a prefix of the other's, the longer of the two, without repeats, in policy order then contract order. A
simple command then matches the one list by the judge's rule exactly when it matches an entry of each list.

Stated limits:
- The tree walk is a copy of task_contract's (its object-store walk), kept in step by hand, as R-4 of DEF-0092 states
  for the hook's other copies; native takeover (A11) retires it. A contract that read_contract refuses only at its parse
  or task step may still give a shell list here; harmless, since the hook stops at its step 3 first.
- Each existing contract's capabilities.shell.allow reads as empty, by no entries or by entries outside the form; only
  a contract written later with entries in the form gains any.
- No policy file exists: the policy list reads as empty, so every leased shell call stays refused, and by
  specification 5 section 8 ends the session, until a policy file with entries exists at the base.
- The entry check accepted with TASK-062 refuses a first word such as timeout or python, so no list can allow the
  project's own command forms (for example "timeout 110 python ..."); under a placed hook those commands stay refused
  whatever the policy holds.
- The grammars are this module's fixed forms, narrower than YAML: any other shape reads as empty.
- The seven calls of up to 10 seconds each: a caller may wait up to about 70 seconds for these git calls alone,
  against Claude Code's own hook timeout (unmeasured).
- git is trusted as gitread trusts it: replace refs, grafts, alternates and an outer repository can change what the
  base reads as.

This module opens no file, starts no process except through gitread.run, and keeps no state between calls. Its one
caller is claude_code_pretool_hook.
"""
import re

from aieos_bootstrap import claude_code_hook
from aieos_bootstrap import gitread

RESULT_KEYS = ('result', 'policy', 'contract', 'allowlist', 'findings')
POLICY_DIR = '.aieos'
POLICY_FILE = 'project.yaml'

_RUN_KEYS = frozenset(('exit', 'out', 'err', 'error'))
_CAP = 1 << 20
_TIMEOUT = 10
_TASK = re.compile(r'TASK-[0-9]+', re.ASCII)
_LINE = re.compile(r'([0-7]{6}) (blob|tree|commit) ([0-9a-f]{40}|[0-9a-f]{64})\t([^/]+)')
_CONTROL = re.compile('[\\x00-\\x09\\x0b-\\x1f\\x7f-\\x9f\\u2028\\u2029]')
_STRING = re.compile(r'"([^"\\]*)"')
_ITEM = '  - '
_SHELL = '  shell: '
_HEAD = '{allow: ['
_TAIL = ']}'


class _Refused(Exception):
    def __init__(self, finding):
        Exception.__init__(self, finding)
        self.finding = finding


def _result(result, policy, contract, allowlist, findings):
    return {'result': result, 'policy': list(policy), 'contract': list(contract), 'allowlist': list(allowlist),
            'findings': list(findings)}


def _call(runner, root, oid):
    """One git call: the output bytes, or _Refused with the "git" finding (task_contract's _call)."""
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
    raise _Refused(finding)


def _tree_id(out):
    """The commit's tree id (task_contract's _tree_id)."""
    if len(out) > _CAP:
        raise _Refused('git: commit text over the cap')
    try:
        out.decode('utf-8')
    except UnicodeDecodeError:
        raise _Refused('git: commit text not UTF-8')
    c = gitread.parse_commit(out)
    if c['error'] is not None or type(c['tree']) is not str or gitread.OBJECT_ID.fullmatch(c['tree']) is None:
        raise _Refused('git: commit out of form')
    return c['tree']


def _entry(out, name, mode, kind, what):
    """One tree: the id of the sought entry, or _Refused with the "tree" finding (task_contract's _entry)."""
    if len(out) > _CAP:
        raise _Refused('tree: tree text over the cap')
    try:
        text = out.decode('utf-8')
    except UnicodeDecodeError:
        raise _Refused('tree: tree text not UTF-8')
    if text and not text.endswith('\n'):
        raise _Refused('tree: line out of form')
    entries = []
    for line in (text[:-1].split('\n') if text else []):
        m = _LINE.fullmatch(line)
        if m is None:
            raise _Refused('tree: line out of form')
        entries.append(m.groups())
    names = [e[3] for e in entries]
    if len(set(names)) != len(names):
        raise _Refused('tree: repeated name')
    found = [e for e in entries if e[3] == name]
    if not found:
        raise _Refused('tree: %s missing' % what)
    if found[0][0] != mode or found[0][1] != kind:
        raise _Refused('tree: %s' % (what + ' not a 100644 blob' if kind == 'blob' else what + ' not a tree'))
    return found[0][2]


def _bytes_text(out):
    """A blob's text, or _Refused with the "bytes" finding (task_contract's _bytes_text)."""
    if len(out) > _CAP:
        raise _Refused('bytes: over the cap')
    try:
        text = out.decode('utf-8')
    except UnicodeDecodeError:
        raise _Refused('bytes: not UTF-8')
    if '﻿' in text:
        raise _Refused('bytes: byte-order mark')
    if _CONTROL.search(text):
        raise _Refused('bytes: control character')
    return text


def _walk(runner, root, out, steps):
    """From the root tree's text along steps (name, kind, what), the last a blob: that blob's checked text."""
    for name, kind, what in steps:
        oid = _entry(out, name, '040000' if kind == 'tree' else '100644', kind, what)
        out = _call(runner, root, oid)
    return _bytes_text(out)


def _skipped(raw):
    return not raw.strip() or raw.lstrip().startswith('#')


def parse_policy(text):
    """The policy's shell_allow list (TASK-076 AC2): the "  - " items after the one top-level line "shell_allow:" up to
    the next top-level line; an empty list for any other shape."""
    if type(text) is not str:
        return []
    out, inside, seen = [], False, False
    for raw in text.split('\n'):
        if _skipped(raw):
            continue
        if not raw.startswith(' '):
            inside = False
            if raw.startswith('shell_allow:'):
                if seen or raw != 'shell_allow:':
                    return []
                seen = inside = True
            continue
        if inside:
            if not raw.startswith(_ITEM) or len(raw) == len(_ITEM):
                return []
            out.append(raw[len(_ITEM):])
    return out


def _strings(value):
    """The strings of "{allow: [" "a", "b" "]}", or None for any other shape."""
    if not value.startswith(_HEAD) or not value.endswith(_TAIL) or len(value) < len(_HEAD) + len(_TAIL):
        return None
    body = value[len(_HEAD):len(value) - len(_TAIL)]
    out, pos = [], 0
    while pos < len(body):
        m = _STRING.match(body, pos)
        if m is None:
            return None
        out.append(m.group(1))
        pos = m.end()
        if pos == len(body):
            break
        if not body.startswith(', ', pos):
            return None
        pos += 2
        if pos == len(body):
            return None
    return out


def parse_contract_shell(text):
    """The contract's capabilities.shell.allow (TASK-076 AC3): the value of the one "  shell: " line of the one top-level
    "capabilities:" section, with its continuation lines, in the form "{allow: [" quoted strings "]}"; an empty list for
    any other shape."""
    if type(text) is not str:
        return []
    lines = text.split('\n')
    section, caps, value, i = None, False, None, 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        if _skipped(raw):
            continue
        if not raw.startswith(' '):
            section = None
            if raw.startswith('capabilities:'):
                if caps or raw != 'capabilities:':
                    return []
                caps, section = True, 'capabilities'
            continue
        if section != 'capabilities' or not raw.startswith(_SHELL):
            continue
        if value is not None:
            return []
        parts, gap = [raw[len(_SHELL):]], False
        while i < len(lines):
            nxt = lines[i]
            if _skipped(nxt):
                gap = True
            elif nxt.startswith('    '):
                if gap:
                    return []
                parts.append(nxt.lstrip(' '))
            else:
                break
            i += 1
        value = ' '.join(parts)
    if value is None:
        return []
    found = _strings(value)
    return [] if found is None else found


def combine(policy, contract):
    """The one list (TASK-076 AC5; specification 2 section 7.2)."""
    out = []
    for p in policy:
        pw = p.split(' ')
        for c in contract:
            cw = c.split(' ')
            if cw[:len(pw)] == pw or pw[:len(cw)] == cw:
                longer = c if len(cw) >= len(pw) else p
                if longer not in out:
                    out.append(longer)
    return out


def _read(root, base, task_id, run):
    if type(root) is not str or gitread.form_error(root, ['cat-file', '-p', '0' * 40], _TIMEOUT) is not None:
        return _result('unreadable', [], [], [], ['argument: root'])
    if type(base) is not str or gitread.OBJECT_ID.fullmatch(base) is None:
        return _result('unreadable', [], [], [], ['argument: base'])
    if type(task_id) is not str or _TASK.fullmatch(task_id) is None:
        return _result('unreadable', [], [], [], ['argument: task_id'])
    runner = gitread.run if run is None else run
    try:
        top = _call(runner, root, _tree_id(_call(runner, root, base)))
    except _Refused as r:
        return _result('read', [], [], [], [r.finding])
    walks = (('policy', ((POLICY_DIR, 'tree', POLICY_DIR), (POLICY_FILE, 'blob', 'policy')), parse_policy),
             ('contract', (('docs', 'tree', 'docs'), ('tasks', 'tree', 'tasks'),
                           (task_id + '.yaml', 'blob', 'contract')), parse_contract_shell))
    lists, findings = [], []
    for side, steps, parse in walks:
        try:
            entries = parse(_walk(runner, root, top, steps))
        except _Refused as r:
            findings.append(side + ': ' + r.finding)
            entries = []
        bad = claude_code_hook.allowlist_findings(entries)
        if bad:
            findings.extend(side + ': ' + f for f in bad)
            entries = []
        lists.append(entries)
    return _result('read', lists[0], lists[1], combine(lists[0], lists[1]), findings)


def read_allowlist(root, base, task_id, run=None):
    """The two lists at base and the one list; see the module docstring for the flow and the limits. Never raises for an
    Exception."""
    try:
        return _read(root, base, task_id, run)
    except Exception as e:
        return _result('unreadable', [], [], [], ['entry: ' + type(e).__name__])
