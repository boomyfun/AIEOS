"""The readers of the Work Order's inputs at a commit (task TASK-082; specification 6 revision 7, sections 5 and 6;
specification 7 revision 2, section 6).

``work_order_inputs(repo, commit, task_id, session_id, log, read=None)`` returns (inputs, None), inputs being the dict
that context_compiler.build_work_order takes, or (None, findings), a non-empty list of strs, and no partial value.

The module reads through base_files only: every file is read at the commit with base_files.read_file and
base_files.list_paths, and the commit is an argument: TASK-083 passes the session's base, and TASK-085 is to pass HEAD;
nothing here reads AIEOS_BASE. read is injectable: it is passed through to base_files, gitread.run being the default,
taken at call time, and within one call the read in use is wrapped by a cache keyed by its arguments. As for the log,
the log is a value: the bytes writer.read_log returns, checked by records.check_log. The module never raises: every
failure, a RecursionError or MemoryError among them, is given as findings. It writes nothing, opens no file, reads no
clock and no environment, and starts no process but through read. Each reader fails closed.

The readers, each this task's choice where TASK-082's contract says so:
- contract: tasks/<task>.yaml, found by contract_path's shared resolution (specification 7 revision 6, TASK-107): the writer's
  state directory first and docs/tasks/<task>.yaml as the self-build's fallback; the contract in both folders is a finding
  and nothing is read; a refusal on either side is a refusal and never a fallback (a stated choice of TASK-107: a refused
  docs side with a present state side is a refusal); only a missing entry is absent. The git calls are today's with the
  docs folder only (a name that the root listing does not hold makes no call, and identical calls are cached). The text is
  parsed by a fixed subset of YAML (the contract's header lists its forms and its refusals); values are kept as strs; its
  SHA-256 must equal the contract_hash of the task's last task.approved, whose contract_version must equal the contract's.
- resume_record: the payload of the task's last decision.execution, after that approval, CONTINUE or CONTINUE_WITH,
  naming the task, the contract_hash and the contract_version.
- articles: each applicable article's block in docs/pre-genesis/constitution.md.
- components and interfaces: read from the read_set.interfaces entries "aieos_bootstrap.<module>.<name> ..." (one
  component per module, tags []), a departure from specification 6 :65 for the self-build; no schemas.
- traced: each traces_to entry's file read whole; an ADR id gives findings; adrs is {}.
- files: the paths the write_set and read_set patterns match, found by listing each pattern's literal prefix, and the
  derived paths present at the commit.
- derived_read_set: the path entries of the resume record's read_set whose sources include "derived", not recomputed.
- last_handoff: the task's handoff files at the base, in the writer's state directory (its handoffs folder) and in docs/handoffs, each named <task>-<session>.md
  (a session part out of form, or one name in both folders, is a finding): none gives None, exactly one gives {ref, text}; two or more give the one whose session has the
  newest handoff claim record in the log's order (the position among the task's events; a stated choice of TASK-108, proposed and fail closed, not the specification's
  words: a file whose session has no claim cannot be ordered and is a finding).
- budgets: BUDGETS.

Limits, stated: the commit and the log are the caller's; the resume record is the task's last decision.execution, not
one bound to the session; the task's later state events are not projected; a listing fails whole on a symbolic link, a
submodule or an out-of-form name under its prefix (base_files' rules); a line's corrects field is not read. TASK-107's
limits: the contract is read from the committed base only, never the working tree; the call bounds: the state candidate
adds one base_files read to the docs-only calls (identical calls are cached, so the root listing is not repeated); DEF-0113 is not
done by TASK-107. TASK-108's limits: the handoff reader is done (DEF-0095's reader half) and reads the committed base only, never the
working tree; its call bound: the state folder's handoffs folder adds one base_files listing to the docs-only calls (cached by
prefix, so no identical call repeats; no added call when the root listing does not hold the state directory); a handoff file of one
task and session in both folders refuses the task's handoff until an approved act removes one; with two or more files, a file whose
session has no handoff claim in the log cannot be ordered and is refused; a handoff made in a session that ended abnormally writes no
file and is never the last handoff; the core does not commit the state files: the user, or on the self-build the owner or an
approved executor script, commits them, and they stay out of an agent's commit because the work tree is cut after the state commit
and CI refuses any changed path under the state folder; the rule that a contract's write set does not list the state directory is
stated and read by no check. The write of a handoff file after a submission, the launcher's wiring, DEF-0113 and DEF-0101's
untouched-root check are not done by TASK-108.

TASK-085 adds four public wrappers over these helpers, by added lines only, for its module resume_inputs: contract_at
(the contract at a commit through _read and _parse_contract_text, CONTRACT_NEEDS and its task checked, with the
SHA-256 of the file's bytes; no log, approval or resume record is read), components_of (_components), paths_under
(_listing, an absent prefix giving []) and submitted_commits (the commit of each task.submitted of a task that
_log_events gives). Each gives (value, None) or (None, findings) and never raises. Where the second paragraph says that
TASK-085 is to pass HEAD, read: TASK-085 takes the commit as an argument, which the launcher reads and passes.
"""

import hashlib
import re

from aieos_bootstrap import base_files, contract_path, gitread, records, resume_check

MAX_FILES = 2000
MAX_FILE_BYTES = 16777216
MAX_PATTERNS = 1000
MAX_CONTRACT_BYTES = 1048576
MAX_DEPTH = 200
BUDGETS = {'constitution': 65536, 'components': 32768, 'traced': 262144, 'files': 524288, 'handoff': 32768}

CONSTITUTION_PATH = 'docs/pre-genesis/constitution.md'
HANDOFF_PREFIX = 'docs'
DECISIONS = ('CONTINUE', 'CONTINUE_WITH')
CONTRACT_NEEDS = ('task', 'contract_version', 'traces_to', 'write_set', 'read_set', 'acceptance_criteria')
READ_SET_ENTRY_KEYS = frozenset({'entry', 'kind', 'sources'})

_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_TASK = re.compile(r'TASK-[0-9]+')
_SESSION = re.compile(r'[A-Za-z0-9._-]{1,128}')
_ADR = re.compile(r'ADR-[0-9]+')
_INTERFACE = re.compile(r'aieos_bootstrap\.([a-z_][a-z0-9_]*)\.[A-Za-z_][A-Za-z0-9_]*')
_KEY = re.compile(r'([A-Za-z0-9_][A-Za-z0-9_./\-]*):(?: (.*))?')
_FLOW_KEY = re.compile(r'([A-Za-z0-9_][A-Za-z0-9_./\-]*): ')
_REFUSED_CHARS = re.compile('[﻿\r\x00-\x09\x0b-\x1f\x7f\x80-\x9f  ]')
_LEADING = '@`%?|>!&*\',[]{}#'


class _Stop(Exception):
    """A refusal: its findings."""

    def __init__(self, findings):
        Exception.__init__(self, findings[0])
        self.findings = list(findings)


# ---------------------------------------------------------------------------------------------------------------
# The contract's subset of YAML

def _indent(line):
    return len(line) - len(line.lstrip(' '))


def _skip(line):
    s = line.strip()
    return s == '' or s.startswith('#')


def _check_plain(text, where):
    """A plain scalar's text after its line breaks are folded, or a _Stop."""
    if text == '' or text[0] in _LEADING or text == '-' or text.startswith('- '):
        raise _Stop(['contract: %s: a plain scalar is empty or starts with an indicator' % where])
    if ' #' in text or ': ' in text or text.endswith(':'):
        raise _Stop(['contract: %s: a plain scalar holds " #" or ": " or ends with ":"' % where])
    return text


def _fold(lines):
    """The value of a ">-" folded scalar's lines, its block indentation removed, as YAML folds them: between two
    non-empty lines with k empty lines between, " " (k = 0) or k line breaks, and one more line break when either line
    is more indented."""
    out, prev, empty = lines[0], lines[0], 0
    for line in lines[1:]:
        if line == '':
            empty += 1
            continue
        kept = line.startswith(' ') or prev.startswith(' ')
        if empty:
            out += '\n' * (empty + kept)
        else:
            out += '\n' if kept else ' '
        out += line
        prev, empty = line, 0
    return out


class _Parser:
    def __init__(self, lines):
        self.lines = lines
        self.i = 0

    def where(self):
        return 'line %d' % self.i

    def next_content(self):
        j = self.i
        while j < len(self.lines) and _skip(self.lines[j]):
            j += 1
        return j

    def block(self, indent, depth):
        if depth > MAX_DEPTH:
            raise _Stop(['contract: nesting deeper than MAX_DEPTH (%d)' % MAX_DEPTH])
        j = self.next_content()
        if j >= len(self.lines) or _indent(self.lines[j]) != indent:
            raise _Stop(['contract: line %d: a block is not at its indentation' % (j + 1)])
        content = self.lines[j][indent:]
        if content == '-' or content.startswith('- '):
            return self.seq(indent, depth)
        return self.mapping(indent, depth)

    def mapping(self, indent, depth):
        result = {}
        while True:
            j = self.next_content()
            if j >= len(self.lines):
                return result
            ind = _indent(self.lines[j])
            if ind < indent:
                return result
            if ind > indent:
                raise _Stop(['contract: line %d: an indentation out of form' % (j + 1)])
            content = self.lines[j][ind:].rstrip(' ')
            m = _KEY.fullmatch(content)
            if m is None:
                raise _Stop(['contract: line %d: a line out of the subset' % (j + 1)])
            key = m.group(1)
            if key in result:
                raise _Stop(['contract: line %d: the key %s is repeated' % (j + 1, key)])
            self.i = j + 1
            result[key] = self.after_key(indent, m.group(2), depth, j + 1)

    def after_key(self, indent, rest, depth, number):
        rest = (rest or '').strip(' ')
        if rest == '':
            j = self.next_content()
            if j < len(self.lines):
                nind = _indent(self.lines[j])
                content = self.lines[j][nind:]
                if nind == indent + 2:
                    return self.block(nind, depth + 1)
                if nind == indent and (content == '-' or content.startswith('- ')):
                    return self.seq(indent, depth + 1)
            raise _Stop(['contract: line %d: an empty value' % number])
        if rest == '>-':
            return self.folded(indent, number)
        if rest[0] in '[{':
            return self.flow(rest, indent, depth, number)
        if rest[0] == '"':
            value, k = _dq(rest, 0, number)
            if rest[k:].strip(' '):
                raise _Stop(['contract: line %d: text after a double-quoted scalar' % number])
            return value
        return self.plain(rest, indent, number)

    def folded(self, indent, number):
        got = []
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if line.strip() == '':
                got.append('')
                self.i += 1
                continue
            if _indent(line) <= indent:
                break
            got.append(line)
            self.i += 1
        while got and got[-1] == '':
            got.pop()
        if not got:
            raise _Stop(['contract: line %d: a folded scalar with no line' % number])
        base = _indent(got[0])
        for line in got:
            if line != '' and _indent(line) < base:
                raise _Stop(['contract: line %d: a folded scalar line less indented than its first' % number])
        return _fold([line[base:] if line != '' else '' for line in got])

    def plain(self, first, indent, number):
        parts = [first.strip(' ')]
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if line.strip() == '' or _indent(line) <= indent:
                break
            if line.strip().startswith('#'):
                raise _Stop(['contract: line %d: a comment inside a plain scalar' % (self.i + 1)])
            parts.append(line.strip(' '))
            self.i += 1
        return _check_plain(' '.join(parts), 'line %d' % number)

    def flow(self, first, indent, depth, number):
        text = first.rstrip(' ')
        while not _closed(text):
            if self.i >= len(self.lines):
                raise _Stop(['contract: line %d: an unclosed flow collection' % number])
            line = self.lines[self.i]
            if line.strip() == '' or _indent(line) <= indent:
                raise _Stop(['contract: line %d: an unclosed flow collection' % number])
            text += ' ' + line.strip(' ')
            self.i += 1
        value, k = _flow_value(text, 0, depth + 1, number)
        if text[k:].strip(' '):
            raise _Stop(['contract: line %d: text after a flow collection closes' % number])
        return value

    def seq(self, indent, depth):
        if depth > MAX_DEPTH:
            raise _Stop(['contract: nesting deeper than MAX_DEPTH (%d)' % MAX_DEPTH])
        result = []
        while True:
            j = self.next_content()
            if j >= len(self.lines):
                return result
            ind = _indent(self.lines[j])
            if ind < indent:
                return result
            if ind > indent:
                raise _Stop(['contract: line %d: an indentation out of form' % (j + 1)])
            content = self.lines[j][ind:].rstrip(' ')
            if not (content == '-' or content.startswith('- ')):
                return result
            item = content[2:].strip(' ')
            self.i = j + 1
            if item == '':
                raise _Stop(['contract: line %d: an empty sequence item' % (j + 1)])
            if item == '>-':
                result.append(self.folded(indent, j + 1))
            elif item[0] in '[{':
                result.append(self.flow(item, indent, depth, j + 1))
            elif item[0] == '"':
                value, k = _dq(item, 0, j + 1)
                if item[k:].strip(' '):
                    raise _Stop(['contract: line %d: text after a double-quoted scalar' % (j + 1)])
                result.append(value)
            elif _KEY.fullmatch(item):
                m = _KEY.fullmatch(item)
                value = self.after_key(indent + 2, m.group(2), depth + 1, j + 1)
                k = self.next_content()
                if k < len(self.lines) and _indent(self.lines[k]) == indent + 2:
                    raise _Stop(['contract: line %d: a sequence item with more than one key' % (k + 1)])
                result.append({m.group(1): value})
            else:
                result.append(self.plain(item, indent, j + 1))


def _closed(text):
    depth, quoted = 0, False
    for ch in text:
        if quoted:
            if ch == '"':
                quoted = False
        elif ch == '"':
            quoted = True
        elif ch in '[{':
            depth += 1
        elif ch in ']}':
            depth -= 1
    return depth <= 0 and not quoted


def _dq(text, k, number):
    """A double-quoted scalar starting at text[k]: (its value, the index after it)."""
    end = text.find('"', k + 1)
    if end < 0:
        raise _Stop(['contract: line %d: an unclosed double-quoted scalar' % number])
    value = text[k + 1:end]
    if '\\' in value:
        raise _Stop(['contract: line %d: a "\\" inside a double-quoted scalar' % number])
    return value, end + 1


def _spaces(text, k):
    while k < len(text) and text[k] == ' ':
        k += 1
    return k


def _flow_value(text, k, depth, number):
    if depth > MAX_DEPTH:
        raise _Stop(['contract: nesting deeper than MAX_DEPTH (%d)' % MAX_DEPTH])
    k = _spaces(text, k)
    if k >= len(text):
        raise _Stop(['contract: line %d: a flow collection ends early' % number])
    ch = text[k]
    if ch == '[':
        result = []
        k = _spaces(text, k + 1)
        if k < len(text) and text[k] == ']':
            return result, k + 1
        while True:
            value, k = _flow_value(text, k, depth + 1, number)
            result.append(value)
            k = _spaces(text, k)
            if k < len(text) and text[k] == ',':
                k += 1
                continue
            if k < len(text) and text[k] == ']':
                return result, k + 1
            raise _Stop(['contract: line %d: a flow list out of form' % number])
    if ch == '{':
        result = {}
        k = _spaces(text, k + 1)
        if k < len(text) and text[k] == '}':
            return result, k + 1
        while True:
            k = _spaces(text, k)
            m = _FLOW_KEY.match(text, k)
            if m is None:
                raise _Stop(['contract: line %d: a flow map key out of form' % number])
            key = m.group(1)
            if key in result:
                raise _Stop(['contract: line %d: the key %s is repeated' % (number, key)])
            value, k = _flow_value(text, m.end(), depth + 1, number)
            result[key] = value
            k = _spaces(text, k)
            if k < len(text) and text[k] == ',':
                k += 1
                continue
            if k < len(text) and text[k] == '}':
                return result, k + 1
            raise _Stop(['contract: line %d: a flow map out of form' % number])
    if ch == '"':
        return _dq(text, k, number)
    end = k
    while end < len(text) and text[end] not in ',]}':
        if text[end] in '[{':
            raise _Stop(['contract: line %d: a "[" or "{" inside a plain scalar of a flow collection' % number])
        end += 1
    return _check_plain(text[k:end].strip(' '), 'line %d' % number), end


def _parse_contract_text(text):
    """The contract's map, read by the subset; a _Stop otherwise."""
    if len(text.encode('utf-8')) > MAX_CONTRACT_BYTES:
        raise _Stop(['contract: over MAX_CONTRACT_BYTES (%d)' % MAX_CONTRACT_BYTES])
    if _REFUSED_CHARS.search(text):
        raise _Stop(['contract: a byte-order mark, CR, tab or control character'])
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    for n, line in enumerate(lines, 1):
        if line.rstrip(' ') in ('---', '...'):
            raise _Stop(['contract: line %d: a document marker' % n])
    p = _Parser(lines)
    value = p.block(0, 0)
    if p.next_content() < len(lines):
        raise _Stop(['contract: line %d: a line out of the subset' % (p.next_content() + 1)])
    if not isinstance(value, dict):
        raise _Stop(['contract: the top level is not a map'])
    return value


# ---------------------------------------------------------------------------------------------------------------
# The readers

def _absent(findings, path):
    """Whether base_files' findings say exactly that the path or one of its ancestors is missing."""
    names = path.split('/') if path else []
    missing = {'%s is missing' % '/'.join(names[:k]) for k in range(1, len(names) + 1)}
    return len(findings) == 1 and findings[0] in missing


def _read(state, path):
    value, found = base_files.read_file(state['repo'], state['commit'], path, state['read'])
    if found:
        raise _Stop(['%s: %s' % (path, f) for f in found])
    return value['text']


def _side(state, path):
    """What the read of one candidate place gives: ('present', text), ('absent', findings) when exactly the path or an
    ancestor is missing (the rule of _absent), or ('refused', findings); the findings are prefixed by the path as _read does."""
    value, found = base_files.read_file(state['repo'], state['commit'], path, state['read'])
    if not found:
        return 'present', value['text']
    prefixed = ['%s: %s' % (path, f) for f in found]
    return ('absent' if _absent(found, path) else 'refused'), prefixed


def _contract_text(state, task_id):
    """The text of the task's contract through contract_path's shared resolution, or a _Stop for a contract in both
    folders, in neither, or a refusal on either side."""
    paths = ['/'.join(place) for place in contract_path.candidates(task_id)]
    got = [_side(state, p) for p in paths]
    what, side = contract_path.decide(got[0][0], got[1][0])
    if what == 'read':
        return got[0 if side == 'state' else 1][1]
    if what == 'both':
        raise _Stop(['contract: %s is in both folders' % task_id])
    if what == 'absent':
        raise _Stop(got[1][1])
    raise _Stop([f for kind, found in got if kind == 'refused' for f in found])


def _listing(state, prefix):
    """The paths under prefix, or [] when base_files says it is missing."""
    if prefix in state['listings']:
        return state['listings'][prefix]
    value, found = base_files.list_paths(state['repo'], state['commit'], prefix, state['read'])
    if found:
        if not _absent(found, prefix):
            raise _Stop(['listing of %r: %s' % (prefix, f) for f in found])
        value = []
    state['listings'][prefix] = value
    return value


def _prefix(pattern):
    """The literal prefix to list for a pattern."""
    if '/' not in pattern:
        return ''
    names = pattern.split('/')
    head = []
    for name in names:
        if '*' in name:
            return '/'.join(head)
        head.append(name)
    return '/'.join(head[:-1])


def _log_events(log, task_id):
    report = records.check_log(log)
    found = ['log: line %d: %s' % (n, f) for n, f in report.findings()]
    if found:
        raise _Stop(found)
    return [line.event for line in report.lines if line.duplicate_of is None and line.event.get('task_id') == task_id]


def _approval_and_record(events, task_id):
    approved = [k for k, e in enumerate(events) if e.get('type') == 'task.approved']
    if not approved:
        raise _Stop(['log: no task.approved of %s' % task_id])
    last = approved[-1]
    approval = events[last].get('payload')
    executions = [k for k, e in enumerate(events) if e.get('type') == 'decision.execution']
    if not executions or executions[-1] < last:
        raise _Stop(['log: no decision.execution of %s after its last task.approved' % task_id])
    record = events[executions[-1]].get('payload')
    if not (isinstance(approval, dict) and isinstance(record, dict)):
        raise _Stop(['log: an approval or a record that is not an object'])
    return approval, record


def _contract(state, task_id, approval, record):
    text = _contract_text(state, task_id)
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
    contract = _parse_contract_text(text)
    found = []
    for key in CONTRACT_NEEDS:
        if key not in contract:
            found.append('contract: no key %s' % key)
    if found:
        raise _Stop(found)
    if digest != approval.get('contract_hash'):
        found.append('contract: its SHA-256 differs from the last task.approved contract_hash')
    if contract.get('contract_version') != approval.get('contract_version'):
        found.append('contract: its contract_version differs from the last task.approved')
    if contract.get('task') != task_id:
        found.append('contract: its task differs from %s' % task_id)
    if record.get('decision') not in DECISIONS:
        found.append('resume record: the decision is not CONTINUE or CONTINUE_WITH')
    if record.get('subject') != task_id:
        found.append('resume record: the subject differs from %s' % task_id)
    if record.get('contract_hash') != digest:
        found.append('resume record: the contract_hash differs from the contract')
    if record.get('contract_version') != contract.get('contract_version'):
        found.append('resume record: the contract_version differs from the contract')
    if found:
        raise _Stop(found)
    return contract, digest


def _articles(state, record):
    con = record.get('constitution')
    if not (isinstance(con, dict) and isinstance(con.get('applicable'), list)
            and all(isinstance(a, str) for a in con['applicable'])):
        raise _Stop(['resume record: constitution.applicable is not a list of article ids'])
    lines = _read(state, CONSTITUTION_PATH).split('\n')
    out = {}
    for a in con['applicable']:
        head = '### ' + a + ' · '
        starts = [k for k, line in enumerate(lines) if line.startswith(head)]
        if len(starts) != 1:
            raise _Stop(['articles: %s has %d blocks in %s, not one' % (a, len(starts), CONSTITUTION_PATH)])
        k = starts[0] + 1
        while k < len(lines) and not (lines[k].startswith('### ') or lines[k].startswith('## ')):
            k += 1
        block = lines[starts[0]:k]
        while block and block[-1].strip() == '':
            block.pop()
        out[a] = '\n'.join(block)
    return out


def _components(contract):
    rs = contract.get('read_set')
    if not isinstance(rs, dict):
        raise _Stop(['contract: read_set is not a map'])
    if rs.get('schemas', []):
        raise _Stop(['contract: read_set.schemas is not supported for the self-build'])
    entries = rs.get('interfaces', [])
    if not (isinstance(entries, list) and all(isinstance(e, str) for e in entries)):
        raise _Stop(['contract: read_set.interfaces is not a list of strs'])
    if len(entries) != len(set(entries)):
        raise _Stop(['contract: a read_set.interfaces entry is listed twice'])
    components, interfaces, seen = [], [], set()
    for e in entries:
        m = _INTERFACE.fullmatch(e.split(' ', 1)[0])
        if m is None:
            raise _Stop(['contract: the read_set.interfaces entry %r is out of the form aieos_bootstrap.<module>.<name>'
                         % e])
        cid = 'aieos_bootstrap.' + m.group(1)
        interfaces.append({'id': e, 'component': cid})
        if cid not in seen:
            seen.add(cid)
            components.append({'id': cid, 'paths': ['src/aieos_bootstrap/%s.py' % m.group(1)], 'tags': []})
    return components, interfaces


def _traced(state, contract):
    traces = contract.get('traces_to')
    if not (isinstance(traces, list) and all(isinstance(t, str) for t in traces)):
        raise _Stop(['contract: traces_to is not a list of strs'])
    out = {}
    for t in traces:
        if _ADR.fullmatch(t):
            raise _Stop(['traced: the ADR id %s cannot be read: the self-build has no ADR folder' % t])
        out[t] = _read(state, t.split('#', 1)[0])
    return out


def _derived(state, record):
    rs = record.get('read_set')
    entries = rs.get('entries') if isinstance(rs, dict) else None
    if not (isinstance(entries, list) and all(
            isinstance(e, dict) and set(e) == READ_SET_ENTRY_KEYS and isinstance(e['entry'], str)
            and isinstance(e['sources'], list) and all(isinstance(s, str) for s in e['sources']) for e in entries)):
        raise _Stop(['resume record: read_set is not an object whose entries are {entry, kind, sources}'])
    out = []
    for e in entries:
        if e['kind'] != 'path' or 'derived' not in e['sources']:
            continue
        path = e['entry']
        parent = path.rsplit('/', 1)[0] if '/' in path else ''
        if path in _listing(state, parent) and path not in out:
            out.append(path)
    return out


def _files(state, contract, derived):
    ws = contract.get('write_set')
    rs = contract.get('read_set')
    patterns = (ws.get('paths', []) if isinstance(ws, dict) else []) + rs.get('paths', [])
    if not all(isinstance(p, str) for p in patterns):
        raise _Stop(['contract: a write_set or read_set path is not a str'])
    if len(patterns) > MAX_PATTERNS:
        raise _Stop(['contract: more than MAX_PATTERNS (%d) patterns' % MAX_PATTERNS])
    chosen = []
    for pattern in patterns:
        for path in _listing(state, _prefix(pattern)):
            if path not in chosen and resume_check.matches(pattern, path):
                chosen.append(path)
    for path in derived:
        if path not in chosen:
            chosen.append(path)
    files, total = {}, 0
    for path in chosen:
        if len(files) >= MAX_FILES:
            raise _Stop(['files: more than MAX_FILES (%d)' % MAX_FILES])
        text = _read(state, path)
        size = len(text.encode('utf-8'))
        if size > base_files.MAX_BYTES:
            raise _Stop(['files: %s is over base_files.MAX_BYTES' % path])
        total += size
        if total > MAX_FILE_BYTES:
            raise _Stop(['files: more than MAX_FILE_BYTES (%d) in all' % MAX_FILE_BYTES])
        files[path] = text
    return files


def _handoff_files(state, task_id):
    """The task's handoff files at the base, by session: the state directory's handoffs folder, then docs/handoffs; a session part out of form
    or a name in both folders is a _Stop (TASK-108)."""
    state_dir = contract_path.candidates(task_id)[0][0]
    names = {}
    for prefix, listed in ((state_dir, state_dir + '/handoffs'), (HANDOFF_PREFIX, HANDOFF_PREFIX)):
        head = '%s/handoffs/%s-' % (prefix, task_id)
        for p in _listing(state, listed):
            if p.startswith(head) and p.endswith('.md') and '/' not in p[len(head):]:
                session = p[len(head):-len('.md')]
                if _SESSION.fullmatch(session) is None or session in ('.', '..'):
                    raise _Stop(['last_handoff: %s: the session part is out of form' % p])
                if session in names:
                    raise _Stop(['last_handoff: %s-%s.md is in both folders' % (task_id, session)])
                names[session] = p
    return names


def _handoff_rank(events, task_id, sessions):
    """The largest position in events of a handoff claim of each session (the log's order; no clock): a record.added event whose payload is
    an object with fact_kind 'claim', subject the task, the session and a refers_to that starts 'handoffs/<task>-<session>.md#'."""
    rank = {}
    for k, event in enumerate(events):
        payload = event.get('payload')
        if event.get('type') != 'record.added' or not isinstance(payload, dict):
            continue
        session, ref = payload.get('session'), payload.get('refers_to')
        if payload.get('fact_kind') == 'claim' and payload.get('subject') == task_id and isinstance(session, str) and session in sessions \
                and isinstance(ref, str) and ref.startswith('handoffs/%s-%s.md#' % (task_id, session)):
            rank[session] = k
    return rank


def _handoff(state, task_id, events):
    names = _handoff_files(state, task_id)
    if not names:
        return None
    if len(names) == 1:
        path = next(iter(names.values()))
        return {'ref': path, 'text': _read(state, path)}
    rank = _handoff_rank(events, task_id, names)
    lacking = [names[s] for s in sorted(names) if s not in rank]
    if lacking:
        raise _Stop(['last_handoff: %d handoffs of %s; which is the last cannot be told: %s has no handoff claim in the log'
                     % (len(names), task_id, lacking[0])])
    if len(set(rank.values())) != len(rank):
        raise _Stop(['last_handoff: two handoffs share a rank'])
    path = names[max(rank, key=rank.get)]
    return {'ref': path, 'text': _read(state, path)}


def _arguments(repo, commit, task_id, session_id, log, read):
    found = []
    if type(repo) is not str:
        found.append('argument: repo is not a str')
    if type(commit) is not str or _COMMIT.fullmatch(commit) is None:
        found.append('argument: commit is not 40 or 64 lowercase hexadecimal characters')
    if type(task_id) is not str or _TASK.fullmatch(task_id) is None:
        found.append('argument: task_id is not TASK-<digits>')
    if type(session_id) is not str or _SESSION.fullmatch(session_id) is None:
        found.append('argument: session_id is not 1 to 128 of [A-Za-z0-9._-]')
    if type(log) is not bytes:
        found.append('argument: log is not bytes')
    if read is not None and not callable(read):
        found.append('argument: read is not callable')
    if found:
        raise _Stop(found)


def _cached(read):
    memo = {}

    def run(repo, args, timeout=30):
        key = (repo, tuple(args), timeout)
        if key not in memo:
            memo[key] = read(repo, args, timeout)
        return memo[key]
    return run


def _inputs(repo, commit, task_id, session_id, log, read):
    _arguments(repo, commit, task_id, session_id, log, read)
    state = {'repo': repo, 'commit': commit, 'read': _cached(gitread.run if read is None else read), 'listings': {}}
    events = _log_events(log, task_id)
    approval, record = _approval_and_record(events, task_id)
    contract, digest = _contract(state, task_id, approval, record)
    articles = _articles(state, record)
    components, interfaces = _components(contract)
    traced = _traced(state, contract)
    derived = _derived(state, record)
    files = _files(state, contract, derived)
    return {'task': task_id, 'session_id': session_id, 'base': commit, 'contract': contract, 'contract_hash': digest,
            'resume_record': record, 'articles': articles, 'components': components, 'interfaces': interfaces,
            'adrs': {}, 'traced': traced, 'files': files, 'derived_read_set': derived,
            'last_handoff': _handoff(state, task_id, events), 'budgets': dict(BUDGETS)}


def work_order_inputs(repo, commit, task_id, session_id, log, read=None):
    """The inputs of context_compiler.build_work_order read at commit: (inputs, None), or (None, findings)."""
    try:
        return _inputs(repo, commit, task_id, session_id, log, read), None
    except _Stop as s:
        return None, s.findings
    except Exception as e:
        return None, ['work_order_inputs: an unexpected %s' % type(e).__name__]


# ---------------------------------------------------------------------------------------------------------------
# The wrappers of TASK-085

def _plain_state(repo, commit, read):
    """The state _inputs builds, after the checks of repo, commit and read only."""
    found = []
    if type(repo) is not str:
        found.append('argument: repo is not a str')
    if type(commit) is not str or _COMMIT.fullmatch(commit) is None:
        found.append('argument: commit is not 40 or 64 lowercase hexadecimal characters')
    if read is not None and not callable(read):
        found.append('argument: read is not callable')
    if found:
        raise _Stop(found)
    return {'repo': repo, 'commit': commit, 'read': _cached(gitread.run if read is None else read), 'listings': {}}


def _contract_at(repo, commit, task_id, read):
    if type(task_id) is not str or _TASK.fullmatch(task_id) is None:
        raise _Stop(['argument: task_id is not TASK-<digits>'])
    state = _plain_state(repo, commit, read)
    text = _contract_text(state, task_id)
    contract = _parse_contract_text(text)
    found = ['contract: no key %s' % key for key in CONTRACT_NEEDS if key not in contract]
    if found:
        raise _Stop(found)
    if contract.get('task') != task_id:
        raise _Stop(['contract: its task differs from %s' % task_id])
    return contract, hashlib.sha256(text.encode('utf-8')).hexdigest()


def contract_at(repo, commit, task_id, read=None):
    """The contract of task_id at commit and the SHA-256 of its file: ((contract, sha256), None), or (None, findings)."""
    try:
        return _contract_at(repo, commit, task_id, read), None
    except _Stop as s:
        return None, s.findings
    except Exception as e:
        return None, ['contract_at: an unexpected %s' % type(e).__name__]


def components_of(contract):
    """The components and interfaces of a contract's read_set: ((components, interfaces), None), or (None, findings)."""
    try:
        if not isinstance(contract, dict):
            raise _Stop(['contract: not a map'])
        return _components(contract), None
    except _Stop as s:
        return None, s.findings
    except Exception as e:
        return None, ['components_of: an unexpected %s' % type(e).__name__]


def _paths_under(repo, commit, prefix, read):
    if type(prefix) is not str:
        raise _Stop(['argument: prefix is not a str'])
    return _listing(_plain_state(repo, commit, read), prefix)


def paths_under(repo, commit, prefix, read=None):
    """The blob paths under prefix at commit, [] when it is absent: (paths, None), or (None, findings)."""
    try:
        return _paths_under(repo, commit, prefix, read), None
    except _Stop as s:
        return None, s.findings
    except Exception as e:
        return None, ['paths_under: an unexpected %s' % type(e).__name__]


def _submitted_commits(log, task_id):
    if type(log) is not bytes:
        raise _Stop(['argument: log is not bytes'])
    if type(task_id) is not str or _TASK.fullmatch(task_id) is None:
        raise _Stop(['argument: task_id is not TASK-<digits>'])
    out = []
    for e in _log_events(log, task_id):
        if e.get('type') != 'task.submitted':
            continue
        payload = e.get('payload')
        commit = payload.get('commit') if isinstance(payload, dict) else None
        if type(commit) is not str or _COMMIT.fullmatch(commit) is None:
            raise _Stop(['log: a task.submitted of %s names no commit id' % task_id])
        out.append(commit)
    return out


def submitted_commits(log, task_id):
    """The commit of every task.submitted of task_id in the log: (a list, None), or (None, findings)."""
    try:
        return _submitted_commits(log, task_id), None
    except _Stop as s:
        return None, s.findings
    except Exception as e:
        return None, ['submitted_commits: an unexpected %s' % type(e).__name__]
