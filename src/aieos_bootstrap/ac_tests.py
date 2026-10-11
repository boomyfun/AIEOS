"""The test-to-AC listing of gov-AIEOS (task TASK-022; specification 4 revision 3, section 6 item 2; concept lines 730
and 781: every acceptance criterion maps to evidence, and a test declares the criterion it proves).

``listing`` takes one task id, that task's contract as values (specification 2 section 5.1), the test files as a
mapping from a path to its source text, and every task's write set, and returns, per AC id of the contract, the tests
that name it, the tests whose naming is ambiguous, and one "untested" finding for each AC of the contract's G2 tests
gate that no counting test names. A malformed input gives one "malformed" finding and nothing else (fail closed).

The naming rules are the decision agent's reading (decision D-529 C2), not the specification's words, which say only
that "A test names the ACs it stands for in its name or docstring":
- A test is a function whose name starts with "test", at a module's top level or directly in a top-level class. It
  names ACs only by its own name and its own docstring; module docstrings, class docstrings and comments do not count.
- A qualified mention, "TASK-" with three digits, one space and an AC id, in the docstring counts for that task, in
  any test file; a docstring may name several.
- A bare mention, an AC id in the docstring outside a qualified mention or a name part "ac<digits>", counts only when
  the test's name and docstring name no task id, and then only for a task whose write set lists the test's path; if
  the write sets of more than one task list it, it counts for none and the test is listed as ambiguous.

``listing_record`` returns, when there are findings, the one record of specification 2 section 6.2 in section 6 item
1's form: an observation with outcome blocking and blocking_kind other. It returns the record; it writes and appends
nothing.

Limits (TASK-022 AC6 and AC9):
- "a name-based mapping shows that a test claims an AC, not that it tests it" (specification 4 section 6). The
  listing is evidence of mapping, not of correctness.
- The module decides no acceptance and no execution and refuses no approval. It settles neither how a corrected
  contract or new tests clear such a record nor a record key for the ACs a gate covers (DEF-0042 points 7 and 8).
  There is no caller in the core and no reader of contract or test files.
- It reads no file, no clock and no environment, and makes no process, network or model call (INV-001 to INV-003).
  It builds syntax trees with ast.parse and runs none of the code it reads.
"""

import ast
import hashlib
import re

from aieos_bootstrap import ac_coverage, records

KINDS = ('malformed', 'untested')
SOURCE_CLASSES = ('deterministic_tool_local', 'deterministic_tool_external_ci')
_TASK = re.compile(r'TASK-[0-9]{3}')
_TASK_IN = re.compile(r'\bTASK-[0-9]{3}\b')
_QUALIFIED = re.compile(r'\bTASK-([0-9]{3}) (AC[0-9]+[a-z]?)\b')
_BARE = re.compile(r'\bAC[0-9]+[a-z]?\b')
_NAME_PART = re.compile(r'ac([0-9]+[a-z]?)')
_AC = re.compile(r'AC[0-9]+[a-z]?')
_VERSION = re.compile(r'v[0-9]+')


def _text(value):
    return isinstance(value, str) and value != ''


def _full(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _finding(kind, ref, detail):
    return {'kind': kind, 'ref': ref, 'detail': detail}


def _path_form(path):
    return _text(path) and '\\' not in path and not path.startswith('/')


def _parse(source):
    """The syntax tree of a source text, or None when ast.parse fails on it (TASK-022 AC1; decision D-531 C3)."""
    try:
        return ast.parse(source)
    except Exception:  # only ast.parse's own failures, which make the source malformed (decision D-533 C2)
        return None


def _tests(tree):
    """The tests of one module as (key part, name, docstring): functions named test* at the top level or directly in a
    top-level class (TASK-022 AC2)."""
    out = []
    funcs = (ast.FunctionDef, ast.AsyncFunctionDef)
    for node in tree.body:
        if isinstance(node, funcs) and node.name.startswith('test'):
            out.append((node.name, node.name, ast.get_docstring(node) or ''))
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, funcs) and item.name.startswith('test'):
                    out.append((node.name + '.' + item.name, item.name, ast.get_docstring(item) or ''))
    return out


def _mentions(name, doc):
    """The qualified (task, AC) pairs of a docstring, the bare AC ids of its name and docstring, and whether the name or
    docstring names a task id (TASK-022 AC2)."""
    qualified = {('TASK-' + m.group(1), m.group(2)) for m in _QUALIFIED.finditer(doc)}
    rest = _QUALIFIED.sub(' ', doc)
    bare = set(_BARE.findall(rest))
    for part in name.split('_'):
        m = _NAME_PART.fullmatch(part)
        if m:
            bare.add('AC' + m.group(1))
    names_task = _TASK_IN.search(name + '\n' + doc) is not None
    return qualified, bare, names_task


def _input_form(task_id, contract, tests, write_sets):
    """The first form of AC1 that fails, as a malformed finding, or None; and the parsed trees by path."""
    if not _full(_TASK, task_id):
        return _finding('malformed', 'task_id', 'task_id is not TASK- followed by three digits'), None
    for f in ac_coverage.check(contract):
        if f['kind'] == 'malformed':
            return _finding('malformed', 'contract', 'the contract is malformed: ' + f['detail']), None
    if not isinstance(tests, dict):
        return _finding('malformed', 'tests', 'tests is not a mapping'), None
    for path in tests:
        if not _path_form(path):
            return _finding('malformed', 'tests', 'a test path is not a relative path with / separators'), None
    trees = {}
    for path in sorted(tests):
        source = tests[path]
        if not isinstance(source, str):
            return _finding('malformed', path, 'the source of %s is not a string' % path), None
        tree = _parse(source)
        if tree is None:
            return _finding('malformed', path, 'the source of %s does not parse' % path), None
        trees[path] = tree
    if not isinstance(write_sets, dict):
        return _finding('malformed', 'write_sets', 'write_sets is not a mapping'), None
    for task, paths in write_sets.items():
        if not _full(_TASK, task):
            return _finding('malformed', 'write_sets', 'a write_sets key is not a task id'), None
        if not (isinstance(paths, list) and all(_text(p) for p in paths)):
            return _finding('malformed', task, 'the write set of %s is not a list of non-empty strings' % task), None
    return None, trees


def listing(task_id, contract, tests, write_sets):
    """The test-to-AC listing of specification 4 section 6 item 2 for one task (TASK-022 AC1 to AC4): a mapping with
    the keys named (each AC id of the contract to the sorted keys of the tests that name it for task_id), ambiguous (the
    sorted keys of the tests listed as ambiguous for task_id) and findings (one "untested" finding per AC of the G2
    tests gate that no counting test names, in plan and args order). A malformed input gives named {}, ambiguous []
    and exactly one malformed finding. The input is not changed."""
    bad, trees = _input_form(task_id, contract, tests, write_sets)
    if bad is not None:
        return {'named': {}, 'ambiguous': [], 'findings': [bad]}
    acs = [next(iter(item)) for item in contract['acceptance_criteria']]
    owners = {}
    for task, paths in write_sets.items():
        for p in paths:
            owners.setdefault(p, set()).add(task)
    named = {ac: set() for ac in acs}
    ambiguous = set()
    for path in sorted(trees):
        own = owners.get(path, set())
        for part, name, doc in _tests(trees[path]):
            key = path + '::' + part
            qualified, bare, names_task = _mentions(name, doc)
            counted = {ac for (task, ac) in qualified if task == task_id}
            if bare and not names_task and task_id in own:
                if len(own) == 1:
                    counted |= bare
                else:
                    ambiguous.add(key)
            for ac in counted:
                if ac in named:
                    named[ac].add(key)
    findings = []
    seen = set()
    for gate in contract['verification_plan']:
        if gate['gate'] == 'G2' and gate['check'] == 'tests':
            for ac in gate.get('args', []):
                if ac in seen or not _AC.fullmatch(ac):
                    continue
                seen.add(ac)
                if not named.get(ac):
                    findings.append(_finding('untested', ac, '%s is named by no test of %s under the naming rules'
                                             % (ac, task_id)))
    return {'named': {ac: sorted(named[ac]) for ac in acs}, 'ambiguous': sorted(ambiguous), 'findings': findings}


def listing_record(task_id, contract_version, findings, recorder, source_class):
    """The one blocking record for a contract version's findings, or None when there are none (TASK-022 AC5). It is
    returned, never written. Raises ValueError for an argument out of its form."""
    if not _full(_TASK, task_id):
        raise ValueError('task_id is not TASK- followed by three digits')
    if not _full(_VERSION, contract_version):
        raise ValueError('contract_version is not v followed by digits')
    if not _text(recorder):
        raise ValueError('recorder is not a non-empty string')
    if source_class not in SOURCE_CLASSES:
        raise ValueError('source_class is not deterministic_tool_local or deterministic_tool_external_ci')
    if not isinstance(findings, list):
        raise ValueError('findings is not a list')
    if not findings:
        return None
    record_id = hashlib.sha256('\n'.join(('ac-tests', task_id, contract_version)).encode('utf-8')).hexdigest()
    record = {'record_id': record_id, 'fact_kind': 'observation', 'source_class': source_class, 'recorder': recorder,
              'subject': task_id, 'evidence_type': 'ac_tests', 'outcome': 'blocking', 'blocking_kind': 'other'}
    if records.check_record(record):
        raise ValueError('the record is not in the form of specification 2 section 6.2')
    return record
