"""Unit tests of aieos_bootstrap.claude_code_shell_allow (TASK-076 AC1 to AC5, AC7 and AC8): read_allowlist over
in-memory object stores of task_contract's shape, extended with a capabilities line and a policy tree, served by a
stand-in run; the two grammars; the form check; combine; the module's imports and names. No test writes a file, makes
a folder or opens a store; every fixture is an in-memory Git object stand-in, and every list entry is made up."""

import ast
import pathlib
import re
import unittest
from unittest import mock

from aieos_bootstrap import claude_code_hook, claude_code_shell_allow as sa, task_contract

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'
REPO = str(pathlib.Path(__file__).resolve().parents[2])
TEXT = (SRC / 'claude_code_shell_allow.py').read_bytes().decode('utf-8')
BASE = '0123456789abcdef0123456789abcdef01234567'
TASK = 'TASK-001'
POLICY = b'version: 1\n# made-up policy\nshell_allow:\n  - ls\n  - git status\n  - cat\nother: x\n'
CONTRACT = ('task: TASK-001\ninput_state:\n  base_commit: %s\nwrite_set:\n  paths:\n    - src/a.py\nforbidden:\n'
            '  - docs/**\ncapabilities:\n  filesystem: {read: [x]}\n  shell: {allow: ["ls -la", "git status"]}\n'
            '  network: {allow: []}\n' % BASE).encode()
KEYS = ('result', 'policy', 'contract', 'allowlist', 'findings')
I = {k: k * 40 for k in 'abcdef123'}


def tree(*lines):
    return ''.join('%s %s %s\t%s\n' % line for line in lines).encode()


def store(policy=POLICY, contract=CONTRACT, aieos=('040000', 'tree'), project=('100644', 'blob'),
          docs=('040000', 'tree'), entry=('100644', 'blob'), with_aieos=True, with_project=True,
          with_contract=True):
    """An in-memory object store at BASE: the commit, the root tree, the policy tree and file, docs, tasks and the
    contract; each part may be left out or given another mode."""
    objects = {BASE: ('tree %s\nauthor A <a> 1 +0000\ncommitter A <a> 1 +0000\n\nm\n' % I['a']).encode()}
    root = [(docs[0], docs[1], I['d'], 'docs')]
    if with_aieos:
        root.insert(0, (aieos[0], aieos[1], I['b'], '.aieos'))
    objects[I['a']] = tree(*root)
    objects[I['b']] = tree((project[0], project[1], I['c'], 'project.yaml')) if with_project else tree(
        ('100644', 'blob', I['1'], 'other.yaml'))
    objects[I['c']] = policy
    objects[I['d']] = tree(('040000', 'tree', I['e'], 'tasks'))
    objects[I['e']] = tree((entry[0], entry[1], I['f'], TASK + '.yaml')) if with_contract else tree(
        ('100644', 'blob', I['1'], 'TASK-002.yaml'))
    objects[I['f']] = contract
    objects[I['1']] = b'x\n'
    return objects


class Runner:
    """A stand-in gitread.run serving an object store; failing ids answer exit 128, raising ids raise."""

    def __init__(self, objects, failing=(), raising=False):
        self.objects, self.failing, self.raising, self.asked = objects, set(failing), raising, []

    def __call__(self, root, args, timeout):
        self.asked.append((args[0], args[1], args[2], timeout))
        if self.raising:
            raise RuntimeError('made-up')
        if args[2] in self.failing or args[2] not in self.objects:
            return {'exit': 128, 'out': b'', 'err': b'', 'error': None}
        return {'exit': 0, 'out': self.objects[args[2]], 'err': b'', 'error': None}


def read(objects=None, **kwargs):
    run = Runner(store() if objects is None else objects, **kwargs)
    return sa.read_allowlist(REPO, BASE, TASK, run), run


WRITING = {'open', 'write_' + 'bytes', 'write_' + 'text', 'mk' + 'dir', 'make' + 'dirs'}


def writing_calls(text):
    """The calls of a module text whose function is the name open, or an attribute named open or one of the
    file-writing and folder-making methods (TASK-076 AC8, D-1974 C2)."""
    found = []
    for n in ast.walk(ast.parse(text)):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Name) and f.id == 'open':
            found.append('open')
        elif isinstance(f, ast.Attribute) and f.attr in WRITING:
            found.append(f.attr)
    return found


class AC1TheReader(unittest.TestCase):

    def test_both_lists_are_read_and_combined(self):
        """TASK-076 AC1: both lists are read at the base through run only, "cat-file -p <id>" with 10 s each, at most
        seven calls, the commit and the root tree once each; the result has exactly its five keys."""
        out, run = read()
        self.assertEqual(tuple(out), KEYS)
        self.assertEqual(out, {'result': 'read', 'policy': ['ls', 'git status', 'cat'],
                               'contract': ['ls -la', 'git status'], 'allowlist': ['ls -la', 'git status'],
                               'findings': []})
        ids = [a[2] for a in run.asked]
        self.assertLessEqual(len(ids), 7)
        self.assertEqual(ids[:2], [BASE, I['a']])
        self.assertEqual(ids.count(BASE), 1)
        self.assertEqual(ids.count(I['a']), 1)
        self.assertTrue(all(a[:2] == ('cat-file', '-p') and a[3] == 10 for a in run.asked))

    def test_each_policy_failure_empties_the_policy_list_only(self):
        """TASK-076 AC1: an absent .aieos tree, an absent project.yaml, a project.yaml that is not a blob, a .aieos
        that is not a tree, an unreadable blob and an over-cap or non-UTF-8 blob each give the policy list empty, the
        contract list still read, and one fixed finding."""
        cases = ((store(with_aieos=False), 'policy: tree: .aieos missing'),
                 (store(with_project=False), 'policy: tree: policy missing'),
                 (store(project=('040000', 'tree')), 'policy: tree: policy not a 100644 blob'),
                 (store(aieos=('100644', 'blob')), 'policy: tree: .aieos not a tree'),
                 (store(policy=b'x' * ((1 << 20) + 1)), 'policy: bytes: over the cap'),
                 (store(policy=b'\xff'), 'policy: bytes: not UTF-8'),
                 (store(policy=b'shell_allow:\n  - ls\t\n'), 'policy: bytes: control character'))
        for objects, finding in cases:
            with self.subTest(finding=finding):
                out, _ = read(objects)
                self.assertEqual((out['result'], out['policy'], out['allowlist']), ('read', [], []))
                self.assertEqual(out['contract'], ['ls -la', 'git status'])
                self.assertEqual(out['findings'], [finding])
        out, _ = read(failing=(I['c'],))
        self.assertEqual((out['policy'], out['findings']), ([], ['policy: git: exit 128']))

    def test_each_contract_failure_empties_the_contract_list_only(self):
        """TASK-076 AC1: a contract missing at the base, not a blob, unreadable or over the cap gives the contract list
        empty, the policy list still read."""
        cases = ((store(with_contract=False), 'contract: tree: contract missing'),
                 (store(entry=('040000', 'tree')), 'contract: tree: contract not a 100644 blob'),
                 (store(docs=('100644', 'blob')), 'contract: tree: docs not a tree'),
                 (store(contract=b'x' * ((1 << 20) + 1)), 'contract: bytes: over the cap'))
        for objects, finding in cases:
            with self.subTest(finding=finding):
                out, _ = read(objects)
                self.assertEqual((out['contract'], out['allowlist']), ([], []))
                self.assertEqual(out['policy'], ['ls', 'git status', 'cat'])
                self.assertEqual(out['findings'], [finding])
        out, _ = read(failing=(I['f'],))
        self.assertEqual((out['contract'], out['findings']), ([], ['contract: git: exit 128']))

    def test_a_raising_run_or_a_bad_commit_empties_both(self):
        """TASK-076 AC1: a stand-in run that raises, a commit that cannot be read and a root tree out of form give both
        lists empty."""
        out, run = read(raising=True)
        self.assertEqual(out, {'result': 'read', 'policy': [], 'contract': [], 'allowlist': [],
                               'findings': ['git: run raised RuntimeError']})
        self.assertEqual(len(run.asked), 1)
        out, _ = read(failing=(BASE,))
        self.assertEqual((out['policy'], out['contract'], out['findings']), ([], [], ['git: exit 128']))
        bad = store()
        bad[I['a']] = b'not a tree line\n'
        out, _ = read(bad)
        self.assertEqual((out['policy'], out['contract']), ([], []))

    def test_arguments_out_of_form(self):
        """TASK-076 AC1: a root, a base or a task id out of form, as read_contract checks them, gives "unreadable",
        every list empty and one finding, with no git call."""
        cases = ((7, BASE, TASK, 'argument: root'), ('made-up-relative', BASE, TASK, 'argument: root'),
                 (REPO, BASE.upper(), TASK, 'argument: base'), (REPO, 7, TASK, 'argument: base'),
                 (REPO, BASE, 'TASK-x', 'argument: task_id'), (REPO, BASE, None, 'argument: task_id'))
        for root, base, task, finding in cases:
            with self.subTest(finding=finding, root=root, base=base, task=task):
                run = Runner(store())
                out = sa.read_allowlist(root, base, task, run)
                self.assertEqual(out, {'result': 'unreadable', 'policy': [], 'contract': [], 'allowlist': [],
                                       'findings': [finding]})
                self.assertEqual(run.asked, [])
                self.assertEqual(task_contract.read_contract(root, base, task, run)['findings'],
                                 [finding.replace('base', 'commit')])

    def test_the_walk_is_held_equal_to_task_contracts(self):
        """TASK-076 AC1: over the same stand-in stores, the new walk reaches the same contract blob as read_contract,
        and in every case read_contract refuses at its git, tree or bytes step the contract list is empty."""
        out, run = read()
        rc = Runner(store())
        self.assertEqual(task_contract.read_contract(REPO, BASE, TASK, rc)['result'], 'read')
        self.assertEqual(rc.asked[-1][2], I['f'])
        self.assertIn(I['f'], [a[2] for a in run.asked])
        self.assertEqual(out['contract'], ['ls -la', 'git status'])
        broken = [store(with_contract=False), store(entry=('040000', 'tree')), store(docs=('100644', 'blob')),
                  store(contract=b'x' * ((1 << 20) + 1)), store(contract=b'\xff'), store(contract=b'\xef\xbb\xbfa'),
                  store(contract=CONTRACT.replace(b'\n', b'\r\n'))]
        tasks_missing = store()
        tasks_missing[I['d']] = tree(('040000', 'tree', I['e'], 'other'))
        repeated = store()
        repeated[I['a']] = repeated[I['a']] + repeated[I['a']]
        broken += [tasks_missing, repeated]
        for i, objects in enumerate(broken):
            with self.subTest(i=i):
                refused = task_contract.read_contract(REPO, BASE, TASK, Runner(objects))
                self.assertIn(refused['reason'], ('git', 'tree', 'bytes'))
                self.assertEqual(read(objects)[0]['contract'], [])
        for failing in ((BASE,), (I['a'],), (I['d'],), (I['e'],), (I['f'],)):
            with self.subTest(failing=failing):
                self.assertEqual(task_contract.read_contract(REPO, BASE, TASK, Runner(store(), failing))['reason'],
                                 'git')
                self.assertEqual(read(failing=failing)[0]['contract'], [])

    def test_no_file_is_opened(self):
        """TASK-076 AC1: reading opens no file (open replaced by one that raises gives the same result)."""
        want, _ = read()

        def refuse(*args, **kwargs):
            raise AssertionError('a file was opened')
        with mock.patch('builtins.open', refuse):
            got = sa.read_allowlist(REPO, BASE, TASK, Runner(store()))
        self.assertEqual(got, want)

    def test_an_exception_gives_entry_with_its_type_only(self):
        """TASK-076 AC1: an exception outside the git steps gives "unreadable", every list empty, "entry: <type>"."""
        with mock.patch.object(sa, 'combine', mock.Mock(side_effect=KeyError('made-up'))):
            out, _ = read()
        self.assertEqual(out, {'result': 'unreadable', 'policy': [], 'contract': [], 'allowlist': [],
                               'findings': ['entry: KeyError']})


class AC2ThePolicyGrammar(unittest.TestCase):

    def test_a_valid_list_is_read_in_order(self):
        """TASK-076 AC2: a valid list of three made-up entries is read in order; blank and "#" lines are skipped."""
        text = '# made-up\nname: x\n\nshell_allow:\n  - ls\n\n  # a comment\n  - git status\n  - cat\nnext: y\n'
        self.assertEqual(sa.parse_policy(text), ['ls', 'git status', 'cat'])
        self.assertEqual(sa.parse_policy('name: x\n'), [])

    def test_every_other_shape_gives_an_empty_list(self):
        """TASK-076 AC2: a second top-level "shell_allow:" line, an item line of another form, an empty section, a value
        on the "shell_allow:" line, and a text that is not a str each give an empty list."""
        texts = ['shell_allow:\n  - ls\nshell_allow:\n  - cat\n', 'shell_allow:\n  - ls\nshell_allow: x\n',
                 'shell_allow:\n  - ls\n    - cat\n', 'shell_allow:\n  -ls\n', 'shell_allow:\n  - \n',
                 'shell_allow:\n   - ls\n', 'shell_allow:\n  ls\n', 'shell_allow:\nnext: x\n', 'shell_allow:\n',
                 'shell_allow: [ls]\n', 'shell_allow: \n  - ls\n', None, b'shell_allow:\n  - ls\n']
        for text in texts:
            with self.subTest(text=text):
                self.assertEqual(sa.parse_policy(text), [])


class AC3TheContractGrammar(unittest.TestCase):

    def test_a_well_formed_list_over_two_lines_is_read(self):
        """TASK-076 AC3: a well-formed list of two made-up entries over two lines is read; one line; an empty list; a
        string holding ", "."""
        two = 'task: TASK-001\ncapabilities:\n  shell: {allow: ["ls -la",\n    "git status"]}\n  network: {}\n'
        self.assertEqual(sa.parse_contract_shell(two), ['ls -la', 'git status'])
        self.assertEqual(sa.parse_contract_shell(CONTRACT.decode()), ['ls -la', 'git status'])
        self.assertEqual(sa.parse_contract_shell('capabilities:\n  shell: {allow: []}\n'), [])
        self.assertEqual(sa.parse_contract_shell('capabilities:\n  shell: {allow: ["a, b"]}\n'), ['a, b'])

    def test_every_other_shape_gives_an_empty_list(self):
        """TASK-076 AC3: a backslash or a quote inside a string, another shape, a second "  shell: " line, a second
        top-level "capabilities:", a blank or comment line inside the continuation, no shell line, and a text that is
        not a str each give an empty list."""
        head = 'task: TASK-001\ncapabilities:\n'
        texts = [head + '  shell: {allow: ["a\\\\b"]}\n', head + '  shell: {allow: ["a"b"]}\n',
                 head + '  shell: {allow: ["a",]}\n', head + '  shell: {allow: ["a", ]}\n',
                 head + '  shell: {allow: ["a"]} x\n', head + '  shell: {allow: [a]}\n',
                 head + '  shell: {allow: ["a"],}\n', head + '  shell: [a]\n', head + '  shell: {allow: ["a","b"]}\n',
                 head + '  shell: {allow: ["a"]}\n  shell: {allow: ["b"]}\n',
                 head + '  shell: {allow: ["a"]}\ncapabilities:\n',
                 'capabilities: x\n  shell: {allow: ["a"]}\n',
                 head + '  shell: {allow: ["a",\n\n    "b"]}\n', head + '  shell: {allow: ["a",\n    # c\n    "b"]}\n',
                 head + '  network: {allow: []}\n', 'other:\n  shell: {allow: ["a"]}\n', head + '  shell:\n',
                 None, b'capabilities:\n  shell: {allow: ["a"]}\n']
        for text in texts:
            with self.subTest(text=text):
                self.assertEqual(sa.parse_contract_shell(text), [])

    def test_a_text_of_task_074s_shape_reads_empty(self):
        """TASK-076 AC3: a made-up text of TASK-074.yaml's shape (an entry with "<", a first word "timeout", a line
        wrap inside a string) parses, but reads empty after allowlist_findings."""
        text = ('capabilities:\n  filesystem: {read: [x]}\n  shell: {allow: ["timeout 110 python t.py < /dev/null", '
                '"timeout 110 python <a made-up\n    script> < /dev/null"]}\n  network: {allow: []}\n')
        parsed = sa.parse_contract_shell(text)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[1], 'timeout 110 python <a made-up script> < /dev/null')
        self.assertTrue(claude_code_hook.allowlist_findings(parsed))
        out, _ = read(store(contract=CONTRACT.split(b'capabilities:')[0] + text.encode()))
        self.assertEqual((out['contract'], out['allowlist']), ([], []))
        self.assertTrue(out['findings'] and all(f.startswith('contract: entry ') for f in out['findings']))


class AC4TheFormCheck(unittest.TestCase):

    def test_one_malformed_entry_voids_its_list(self):
        """TASK-076 AC4: one malformed entry among good ones makes that whole list empty, the finding words kept; a list
        of only good entries stays."""
        out, _ = read(store(policy=b'shell_allow:\n  - ls\n  - python x\n'))
        self.assertEqual((out['policy'], out['allowlist']), ([], []))
        self.assertEqual(out['contract'], ['ls -la', 'git status'])
        self.assertEqual(out['findings'], ['policy: entry 1 starts with a program that runs code or commands'])
        out, _ = read(store(policy=b'shell_allow:\n  - ls\n  - git status\n'))
        self.assertEqual((out['policy'], out['findings']), (['ls', 'git status'], []))


class AC5TheOneList(unittest.TestCase):

    def test_combine(self):
        """TASK-076 AC5: the longer entry of each prefix pair, without repeats, in policy order then contract order;
        either list empty gives an empty list."""
        self.assertEqual(sa.combine(['ls'], ['ls -la']), ['ls -la'])
        self.assertEqual(sa.combine(['git status -s'], ['git']), ['git status -s'])
        self.assertEqual(sa.combine(['ls', 'git status'], ['git', 'ls -la', 'ls']), ['ls -la', 'ls', 'git status'])
        self.assertEqual(sa.combine(['ls', 'ls'], ['ls']), ['ls'])
        self.assertEqual(sa.combine(['ls'], ['lsx']), [])
        self.assertEqual(sa.combine([], ['ls']), [])
        self.assertEqual(sa.combine(['ls'], []), [])


class AC8NoEntryAndNoFile(unittest.TestCase):

    def test_the_module_imports_and_names(self):
        """TASK-076 AC8: the module imports only re and, as "from aieos_bootstrap import X", claude_code_hook and
        gitread; it uses no open, no os, no process call of its own, no assert; RESULT_KEYS and the policy names."""
        tree = ast.parse(TEXT)
        imports = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imports.update(('import', a.name) for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imports.update((n.module, a.name) for a in n.names)
        self.assertEqual(imports, {('import', 're'), ('aieos_bootstrap', 'claude_code_hook'),
                                   ('aieos_bootstrap', 'gitread')})
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertFalse((names | attrs) & {'open', 'os', 'print', 'exec', 'eval', '__import__', 'subprocess',
                                            'importlib', 'sqlite3', 'writer', 'adapter'})
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Assert)])
        self.assertEqual(sa.RESULT_KEYS, KEYS)
        self.assertEqual((sa.POLICY_DIR, sa.POLICY_FILE), ('.' + 'aieos', 'project.yaml'))

    def test_no_test_writes_a_file(self):
        """TASK-076 AC8: the two test modules of the new module hold no file-writing call and no folder making."""
        here = pathlib.Path(__file__).resolve()
        words = ('write_' + 'bytes', 'write_' + 'text', 'mk' + 'dir', 'make' + 'dirs', 'temp' + 'file')
        for path in (here, here.parents[1] / 'property' / 'test_claude_code_shell_allow_properties.py'):
            text = path.read_bytes().decode('utf-8')
            for word in words:
                with self.subTest(path=path.name, word=word):
                    self.assertNotIn(word, text)
            with self.subTest(path=path.name):
                self.assertEqual(writing_calls(text), [])
        self.assertTrue(writing_calls('open("f", "a")\n'))
        self.assertTrue(writing_calls('import pathlib\npathlib.Path("f").' + 'write_' + 'text("x")\n'))
        self.assertTrue(writing_calls('import os\nos.' + 'make' + 'dirs("d")\n'))
        self.assertEqual(writing_calls('mock.patch("builtins.open", f)\n'), [])


class AC7Naming(unittest.TestCase):

    def test_every_test_names_its_criteria(self):
        """TASK-076 AC7: every test function of this module and of the property module names "TASK-076 ACn" in its own
        docstring and no other task's AC in qualified form."""
        here = pathlib.Path(__file__).resolve()
        for path in (here, here.parents[1] / 'property' / 'test_claude_code_shell_allow_properties.py'):
            tree = ast.parse(path.read_bytes().decode('utf-8'))
            for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
                doc = ' '.join((ast.get_docstring(fn) or '').split())
                with self.subTest(test=fn.name):
                    self.assertTrue(re.findall(r'TASK-076 AC[0-9]+', doc))
                    self.assertEqual(re.findall(r'TASK-(?!076 )[0-9]+ AC[0-9]+', doc), [])
        self.assertEqual(re.findall(r'TASK-(?!076 )[0-9]+ AC[0-9]+', 'TASK-074 AC1'), ['TASK-074 AC1'])


if __name__ == '__main__':
    unittest.main()
