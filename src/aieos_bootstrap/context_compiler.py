"""The Context Compiler v1 (TASK-080): build_work_order(inputs) returns the Work Order of specification 6 revision 7,
sections 5 and 6, from values given.

This is a pure module, in resume_check.check's form: build_work_order reads no file, no clock and no environment,
starts no process, writes and appends nothing, mutates no input and never raises. It returns (work_order, None), or
(None, findings) with a non-empty list of strs and no partial Work Order. It imports only the standard library and
aieos_bootstrap.resume_check, of which it uses only meet and matches (specification 3's pattern rules); it never calls
resume_check.check, so layer 1 is not recomputed: it is taken from the Resume Check record that made the grant.

The inputs are a dict with exactly the keys task, session_id, base, contract, contract_hash, resume_record, articles,
components, interfaces, adrs, traced, files, derived_read_set, last_handoff and budgets, in the forms the task contract
states; every value is JSON (a float finite, every str encodable as UTF-8). The resume record must be CONTINUE or
CONTINUE_WITH and name the same task, contract hash and contract version; budgets are required: one int above 0 per
layer, in bytes, with no default.

The Work Order has the keys task, contract_version, contract_hash, base, session_id, decision, contract, layers and
work_order_hash, the SHA-256 of the canonical form (UTF-8, keys sorted, no insignificant whitespace) of the object
without that key. Its five layers, in the concept's order:
(1) constitution: the articles of the record's constitution.applicable;
(2) components: the components one of whose paths meets a write-set or read_set.paths pattern (a path with no
    wildcard read as "<it>/**"), and those a read_set.interfaces entry names, each with the interfaces that name it;
(3) traced: the traces_to entries that are not ADRs, the acceptance criteria, and the ADRs that traces_to names;
(4) files: the files a write-set or read_set.paths pattern matches, the files under a component a read_set.interfaces
    entry names, the file each read_set.schemas entry resolves to (exactly one, else findings), and the derived paths
    present in files;
(5) handoff: the last handoff, or no item.
An item is {ref, hash, content}, or {ref, hash} when given as a reference; items are ordered by ref. While a layer's
content bytes are over its budget, items become references: the largest content first, ties by ref. A reference keeps
the hash of the content it replaces; never a summary and never a shortened content.

Stated choices, each this task's choice (specification 6 section 11 stays open for its next revision): the order of
turning items into references; the item refs (an article's id, "component:<id>", a traces_to entry as written, an AC
id, "adr:<id>", a repository path, the handoff's own ref); the layer and item shapes; the findings form.

Limits: the inputs' truth is the caller's; this module checks their form and their ties, not that they are what the
base holds, and "the last" handoff is the caller's choice. No reader of the inputs and no MCP tool are here: S3b waits
for M7. Nothing calls build_work_order but its tests.
"""
import hashlib
import json
import math
import re

from aieos_bootstrap import resume_check

INPUT_KEYS = frozenset({
    'task', 'session_id', 'base', 'contract', 'contract_hash', 'resume_record', 'articles', 'components',
    'interfaces', 'adrs', 'traced', 'files', 'derived_read_set', 'last_handoff', 'budgets'})
LAYERS = ('constitution', 'components', 'traced', 'files', 'handoff')
DECISIONS = ('CONTINUE', 'CONTINUE_WITH')
READ_SET_KEYS = ('paths', 'interfaces', 'schemas')
CONSTITUTION_KEYS = frozenset({'applicable', 'violated', 'no_result'})
COMPONENT_KEYS = frozenset({'id', 'paths', 'tags'})
INTERFACE_KEYS = frozenset({'id', 'component'})
HANDOFF_KEYS = frozenset({'ref', 'text'})
# The depth beyond which a value is refused rather than walked (a cycle among the inputs ends here too).
MAX_DEPTH = 200

_TASK = re.compile(r'TASK-[0-9]+')
_SESSION = re.compile(r'[A-Za-z0-9._-]{1,128}')
_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_HEX64 = re.compile(r'[0-9a-f]{64}')
_VERSION = re.compile(r'v[0-9]+')


def build_work_order(inputs):
    """The Work Order of the given inputs: (work_order, None), or (None, findings). Never raises."""
    try:
        return _build(inputs)
    except Exception as e:  # any failure is a finding, never an exception
        return None, ['the inputs could not be compiled: ' + type(e).__name__]


def _build(inputs):
    if not isinstance(inputs, dict):
        return None, ['inputs is not an object']
    findings = []
    _json_value(inputs, 'inputs', findings, 0)
    if findings:
        return None, findings
    missing = sorted(INPUT_KEYS - set(inputs))
    if missing:
        findings.append('inputs lacks ' + ', '.join(missing))
    extra = sorted(set(inputs) - INPUT_KEYS)
    if extra:
        findings.append('inputs has keys this task does not name: ' + ', '.join(extra))
    if findings:
        return None, findings
    inp = json.loads(_dumps(inputs))
    _check(inp, findings)
    if findings:
        return None, findings
    layers = _layers(inp, findings)
    if findings:
        return None, findings
    contract = inp['contract']
    work_order = {'task': inp['task'], 'contract_version': contract['contract_version'],
                  'contract_hash': inp['contract_hash'], 'base': inp['base'], 'session_id': inp['session_id'],
                  'decision': inp['resume_record']['decision'], 'contract': contract, 'layers': layers}
    work_order['work_order_hash'] = _sha256(_dumps(work_order))
    return work_order, None


# ---------------------------------------------------------------------------------------------------------------
# Value forms

def _dumps(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _utf8(text):
    try:
        text.encode('utf-8')
    except UnicodeEncodeError:
        return False
    return True


def _json_value(value, where, findings, depth):
    """Appends a finding for each part of value that is not JSON: a float that is not finite, a str or key UTF-8
    cannot encode, a key that is not a str, any other type, or nesting deeper than MAX_DEPTH."""
    if depth > MAX_DEPTH:
        findings.append('%s is nested more than %d deep' % (where, MAX_DEPTH))
    elif value is None or isinstance(value, (bool, int)):
        return
    elif isinstance(value, float):
        if not math.isfinite(value):
            findings.append(where + ' is a float that is not finite')
    elif isinstance(value, str):
        if not _utf8(value):
            findings.append(where + ' is a str UTF-8 cannot encode')
    elif isinstance(value, list):
        for i, x in enumerate(value):
            _json_value(x, '%s[%d]' % (where, i), findings, depth + 1)
    elif isinstance(value, dict):
        for k, x in value.items():
            if not isinstance(k, str):
                findings.append(where + ' has a key that is not a str')
            elif not _utf8(k):
                findings.append(where + ' has a key UTF-8 cannot encode')
            else:
                _json_value(x, where + '.' + k, findings, depth + 1)
    else:
        findings.append('%s is not a JSON value (%s)' % (where, type(value).__name__))


def _str(v):
    return isinstance(v, str) and v != ''


def _strs(v):
    return isinstance(v, list) and all(_str(x) for x in v)


def _text_map(v):
    return isinstance(v, dict) and all(_str(k) and isinstance(x, str) for k, x in v.items())


def _positive_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def _need(findings, ok, what):
    if not ok:
        findings.append(what)


# ---------------------------------------------------------------------------------------------------------------
# The inputs (the task contract's header)

def _check(inp, findings):
    task = inp['task']
    _need(findings, isinstance(task, str) and _TASK.fullmatch(task) is not None, 'task is not TASK-<digits>')
    sid = inp['session_id']
    _need(findings, isinstance(sid, str) and _SESSION.fullmatch(sid) is not None,
          'session_id is not 1 to 128 of [A-Za-z0-9._-]')
    _need(findings, isinstance(inp['base'], str) and _COMMIT.fullmatch(inp['base']) is not None,
          'base is not 40 or 64 lowercase hex digits')
    _need(findings, isinstance(inp['contract_hash'], str) and _HEX64.fullmatch(inp['contract_hash']) is not None,
          'contract_hash is not 64 lowercase hex digits')
    _check_contract(inp, findings)
    if findings:
        return
    _check_record(inp, findings)
    if findings:
        return
    _check_sources(inp, findings)


def _check_contract(inp, findings):
    c = inp['contract']
    if not isinstance(c, dict):
        findings.append('contract is not an object')
        return
    _need(findings, c.get('task') == inp['task'], 'contract task differs from task')
    v = c.get('contract_version')
    _need(findings, isinstance(v, str) and _VERSION.fullmatch(v) is not None, 'contract contract_version is not v<digits>')
    _need(findings, _strs(c.get('traces_to')), 'contract traces_to is not a list of strs')
    ws = c.get('write_set')
    _need(findings, isinstance(ws, dict) and _strs(ws.get('paths')), 'contract write_set.paths is not a list of strs')
    rs = c.get('read_set')
    _need(findings, isinstance(rs, dict) and all(_strs(rs.get(k, [])) for k in READ_SET_KEYS),
          'contract read_set is not {paths, interfaces, schemas} of strs')
    acs = c.get('acceptance_criteria')
    _need(findings, isinstance(acs, list) and all(
        isinstance(a, dict) and len(a) == 1 and all(_str(k) and isinstance(t, str) for k, t in a.items()) for a in acs),
        'contract acceptance_criteria is not a list of one-entry maps from an AC id to its text')


def _check_record(inp, findings):
    r = inp['resume_record']
    if not isinstance(r, dict):
        findings.append('resume_record is not an object')
        return
    _need(findings, r.get('decision') in DECISIONS, 'resume_record decision is not CONTINUE or CONTINUE_WITH')
    _need(findings, r.get('subject') == inp['task'], 'resume_record subject differs from task')
    _need(findings, r.get('contract_hash') == inp['contract_hash'], 'resume_record contract_hash differs')
    _need(findings, r.get('contract_version') == inp['contract']['contract_version'],
          'resume_record contract_version differs from the contract')
    con = r.get('constitution')
    _need(findings, isinstance(con, dict) and set(con) == CONSTITUTION_KEYS and all(_strs(con[k]) for k in con),
          'resume_record constitution is not {applicable, violated, no_result} of article ids')


def _check_sources(inp, findings):
    contract = inp['contract']
    applicable = inp['resume_record']['constitution']['applicable']
    articles = inp['articles']
    _need(findings, _text_map(articles) and set(articles) == set(applicable),
          'articles is not {article id: text} keyed exactly by constitution.applicable')
    components = inp['components']
    comps_ok = isinstance(components, list) and all(
        isinstance(x, dict) and set(x) == COMPONENT_KEYS and _str(x['id']) and _strs(x['paths'])
        and _strs(x['tags']) for x in components)
    _need(findings, comps_ok, 'components is not a list of {id, paths, tags}')
    if comps_ok:
        ids = [x['id'] for x in components]
        _need(findings, len(ids) == len(set(ids)), 'a component id is given more than once')
    interfaces = inp['interfaces']
    ifaces_ok = isinstance(interfaces, list) and all(
        isinstance(i, dict) and set(i) == INTERFACE_KEYS and _str(i['id']) and _str(i['component']) for i in interfaces)
    _need(findings, ifaces_ok, 'interfaces is not a list of {id, component}')
    if ifaces_ok:
        ids = [i['id'] for i in interfaces]
        _need(findings, len(ids) == len(set(ids)), 'an interface id is given more than once')
        if comps_ok:
            known = {x['id'] for x in components}
            for i in interfaces:
                _need(findings, i['component'] in known, 'interface %s names no given component' % i['id'])
        for e in contract['read_set'].get('interfaces', []):
            _need(findings, e in ids, 'read_set.interfaces entry %s names no given interface' % e)
    traces = contract['traces_to']
    adrs = inp['adrs']
    adrs_ok = _text_map(adrs) and set(adrs) <= set(traces)
    _need(findings, adrs_ok, 'adrs is not {ADR id: text} of traces_to entries')
    if adrs_ok:
        traced = inp['traced']
        _need(findings, _text_map(traced) and set(traced) == {t for t in traces if t not in adrs},
              'traced is not {entry: text} keyed exactly by the traces_to entries that are not ADRs')
    _need(findings, _text_map(inp['files']), 'files is not {repository path: text}')
    _need(findings, _strs(inp['derived_read_set']), 'derived_read_set is not a list of repository paths')
    h = inp['last_handoff']
    _need(findings, h is None or (isinstance(h, dict) and set(h) == HANDOFF_KEYS and _str(h['ref'])
                                  and isinstance(h['text'], str)), 'last_handoff is not null or {ref, text}')
    b = inp['budgets']
    _need(findings, isinstance(b, dict) and set(b) == set(LAYERS) and all(_positive_int(v) for v in b.values()),
          'budgets is not {layer name: an int above 0} for the five layers')


# ---------------------------------------------------------------------------------------------------------------
# The layers (specification 6 section 6)

def _folder(path):
    """A component path: a path with no wildcard is read as the folder it may name, <it>/**."""
    if '*' in path:
        return path
    return path.rstrip('/') + '/**'


def _stem(path):
    """The last name of a path without its extension."""
    name = path.rsplit('/', 1)[-1]
    return name.rsplit('.', 1)[0] if '.' in name else name


def _layers(inp, findings):
    contract = inp['contract']
    rs = contract['read_set']
    declared = contract['write_set']['paths'] + rs.get('paths', [])
    components = inp['components']
    owner = {i['id']: i['component'] for i in inp['interfaces']}
    named = {owner[e] for e in rs.get('interfaces', [])}
    selected = [x for x in components if x['id'] in named
                or any(resume_check.meet(_folder(p), d) for p in x['paths'] for d in declared)]
    named_paths = [_folder(p) for x in components if x['id'] in named for p in x['paths']]
    selected_paths = [_folder(p) for x in selected for p in x['paths']]
    files = inp['files']

    schema_files = set()
    for s in rs.get('schemas', []):
        found = sorted(p for p in files if _stem(p) == s and any(resume_check.matches(q, p) for q in selected_paths))
        if len(found) == 1:
            schema_files.add(found[0])
        else:
            findings.append('read_set.schemas entry %s resolves to %d files under the selected components, not one'
                            % (s, len(found)))
    if findings:
        return None

    derived = set(inp['derived_read_set'])
    chosen = [p for p in files if p in schema_files or p in derived
              or any(resume_check.matches(d, p) for d in declared)
              or any(resume_check.matches(q, p) for q in named_paths)]

    articles = inp['articles']
    traced = inp['traced']
    adrs = inp['adrs']
    handoff = inp['last_handoff']
    sources = [
        [(a, articles[a]) for a in inp['resume_record']['constitution']['applicable']],
        [('component:' + x['id'], _dumps({'component': x, 'interfaces': sorted(i for i, c in owner.items()
                                                                              if c == x['id'])}))
         for x in selected],
        [(t, traced[t]) for t in contract['traces_to'] if t not in adrs]
        + [(k, text) for a in contract['acceptance_criteria'] for k, text in a.items()]
        + [('adr:' + t, adrs[t]) for t in contract['traces_to'] if t in adrs],
        [(p, files[p]) for p in chosen],
        [(handoff['ref'], handoff['text'])] if handoff is not None else [],
    ]
    layers = []
    for n, (name, pairs) in enumerate(zip(LAYERS, sources), 1):
        refs = [r for r, _ in pairs]
        if len(refs) != len(set(refs)):
            findings.append('layer %d (%s) has a ref more than once' % (n, name))
        items = [{'ref': r, 'hash': _sha256(text), 'content': text} for r, text in sorted(pairs)]
        layers.append({'layer': n, 'name': name, 'items': _fit(items, inp['budgets'][name])})
    return layers


def _fit(items, budget):
    """Turns items into references, the largest content first, ties by ref, until the layer's content bytes are within
    its budget. A reference keeps its ref and hash; a content is never shortened."""
    size = {i['ref']: len(i['content'].encode('utf-8')) for i in items}
    total = sum(size.values())
    dropped = set()
    for ref in sorted(size, key=lambda r: (-size[r], r)):
        if total <= budget:
            break
        dropped.add(ref)
        total -= size[ref]
    return [{'ref': i['ref'], 'hash': i['hash']} if i['ref'] in dropped else i for i in items]
