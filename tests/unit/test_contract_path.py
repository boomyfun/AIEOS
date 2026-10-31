"""Unit tests of aieos_bootstrap.contract_path (task TASK-107, AC1 and AC6): the shared resolution of a task contract's path, a
pure module that imports only the writer and does no I/O. Each test names its criteria in its own docstring."""

import ast
import itertools
import pathlib
import re
import unittest

from aieos_bootstrap import claude_code_shell_allow as sa
from aieos_bootstrap import contract_path as cp
from aieos_bootstrap import writer

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'
STATE_NAME = '.' + 'aieos'
SIDES = ('present', 'absent', 'refused')
TABLE = {
    ('present', 'absent'): ('read', 'state'),
    ('absent', 'present'): ('read', 'docs'),
    ('present', 'present'): ('both', None),
    ('absent', 'absent'): ('absent', None),
    ('present', 'refused'): ('refused', 'docs'),
    ('absent', 'refused'): ('refused', 'docs'),
    ('refused', 'present'): ('refused', 'state'),
    ('refused', 'absent'): ('refused', 'state'),
    ('refused', 'refused'): ('refused', 'state'),
}


def purity_findings(text):
    """What is wrong with the text of contract_path.py by the pins of TASK-107 AC1: its imports, refused names and
    attributes, asserts, writer attributes, and the state directory's name in any string or in the text."""
    tree = ast.parse(text)
    found = []
    imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imports |= {n.module + '.' + a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    if imports != {'aieos_bootstrap.writer'}:
        found.append('imports: ' + ', '.join(sorted(imports)))
    deny = {'open', 'exec', 'eval', 'compile', '__import__', 'importlib', 'input', 'breakpoint', '__builtins__', 'os',
            'subprocess', 'gitread', 'time', 'sys', 'pathlib', 'io', 'socket'}
    found += ['name: ' + n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id in deny]
    attrs = {'now', 'utcnow', 'today', 'time', 'environ', 'getenv', 'system', 'popen', 'Popen', 'stdin', 'run'}
    found += ['attribute: ' + n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr in attrs]
    found += ['assert' for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    used = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and ast.unparse(n.value) == 'writer'}
    if used != {'STATE_DIR'}:
        found.append('writer attributes: ' + ', '.join(sorted(used)))
    consts = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    found += ['constant with the state name' for c in consts if STATE_NAME in c]
    if STATE_NAME in text:
        found.append('the state name in the text')
    return found


def other_task_ids(text):
    """The qualified AC ids of tasks other than TASK-107 in text, with every run of whitespace collapsed."""
    return re.findall(r'TASK-(?!107 )[0-9]+ AC[0-9]+', ' '.join(text.split()))


class AC1Candidates(unittest.TestCase):

    def test_the_two_places_in_order(self):
        """TASK-107 AC1: candidates returns the ordered pair of component tuples, the writer's state directory first and docs
        second, and nothing else."""
        got = cp.candidates('TASK-107')
        self.assertEqual(got, ((writer.STATE_DIR, 'tasks', 'TASK-107.yaml'), ('docs', 'tasks', 'TASK-107.yaml')))
        self.assertIsInstance(got, tuple)
        self.assertTrue(all(isinstance(x, tuple) and len(x) == 3 for x in got))
        self.assertEqual(cp.candidates('TASK-7')[0][2], 'TASK-7.yaml')

    def test_a_bad_id_raises_value_error(self):
        """TASK-107 AC1: an id that is not TASK- and digits raises ValueError, whatever the type."""
        bad = ['', 'TASK-', 'TASK-x', 'TASK-1x', 'task-1', 'TASK--1', 'TASK-1\n', ' TASK-1', 'TASK-1 ', 'TASK-١',
               'TASK-²', 'TASK-１', 'XTASK-1', 'TASK-1/../x', 3, None, b'TASK-1', ['TASK-1'], ('TASK-1',)]
        for task_id in bad:
            with self.subTest(task_id=task_id):
                with self.assertRaises(ValueError):
                    cp.candidates(task_id)


class AC1Decide(unittest.TestCase):

    def test_the_nine_rows(self):
        """TASK-107 AC1: decide gives the table of its docstring for each of the nine pairs, and nothing else."""
        self.assertEqual(set(TABLE), set(itertools.product(SIDES, SIDES)))
        for (state, docs), want in TABLE.items():
            with self.subTest(state=state, docs=docs):
                self.assertEqual(cp.decide(state, docs), want)

    def test_a_refusal_never_falls_back(self):
        """TASK-107 AC1: a refused state side is never read as absent: it gives ('refused', 'state') whatever the docs side
        is, and a refused docs side is a refusal whatever the state side is."""
        for docs in SIDES:
            self.assertEqual(cp.decide('refused', docs), ('refused', 'state'))
        for state in ('present', 'absent'):
            self.assertEqual(cp.decide(state, 'refused'), ('refused', 'docs'))

    def test_any_other_argument_raises_value_error(self):
        """TASK-107 AC1: an argument that is not one of the three words, of any type, raises ValueError on either side."""
        bad = ['', 'Present', 'PRESENT', 'present ', 'read', 'both', None, 1, True, b'present', ['present'], ('present',),
               {'present'}, 3.5]
        for x in bad:
            with self.subTest(x=x):
                with self.assertRaises(ValueError):
                    cp.decide(x, 'absent')
                with self.assertRaises(ValueError):
                    cp.decide('absent', x)

    def test_the_answers_are_pairs_of_the_four_words(self):
        """TASK-107 AC1: every answer is a pair whose first element is read, both, absent or refused."""
        for state, docs in itertools.product(SIDES, SIDES):
            answer = cp.decide(state, docs)
            self.assertIsInstance(answer, tuple)
            self.assertEqual(len(answer), 2)
            self.assertIn(answer[0], ('read', 'both', 'absent', 'refused'))
            self.assertIn(answer[1], ('state', 'docs', None))


class AC1Purity(unittest.TestCase):

    def test_what_contract_path_imports_and_uses(self):
        """TASK-107 AC1: contract_path.py imports exactly aieos_bootstrap.writer, reads no attribute of it but STATE_DIR, uses
        none of the refused names or attributes, holds no assert, and no text of it (code, docstring or comment) holds the
        state directory's name: purity_findings gives nothing for the real text."""
        text = (SRC / 'contract_path.py').read_bytes().decode('utf-8')
        self.assertEqual(purity_findings(text), [])

    def test_the_purity_check_fails_on_broken_copies(self):
        """TASK-107 AC1 and AC6: the purity check is a pin: each stated mutation of the real text (an added import of os, an open
        call, a second writer attribute, a constant holding the state directory's name, the state directory's name in a comment,
        an assert) gives a finding, and the unchanged text gives none."""
        text = (SRC / 'contract_path.py').read_bytes().decode('utf-8')
        self.assertEqual(purity_findings(text), [])
        mutations = {
            'an import of os': 'import os\n' + text,
            'an open call': text + "\n\ndef _leak():\n    return open('x')\n",
            'a second writer attribute': text + '\n\n_STORE = writer.STORE\n',
            'a constant with the state name': text + "\n\n_NAME = '" + STATE_NAME + "'\n",
            'the state name in a comment': text + '\n# ' + STATE_NAME + '\n',
            'an assert': text + '\n\nassert SIDES\n',
        }
        for label, broken in mutations.items():
            with self.subTest(mutation=label):
                self.assertNotEqual(purity_findings(broken), [])

    def test_the_state_directory_is_the_writers_and_the_hook_readers(self):
        """TASK-107 AC1: the state directory that contract_path returns equals writer.STATE_DIR and the shell allowlist
        reader's POLICY_DIR, and docs is the second place."""
        self.assertEqual(cp.candidates('TASK-107')[0][0], writer.STATE_DIR)
        self.assertEqual(writer.STATE_DIR, sa.POLICY_DIR)
        self.assertEqual(writer.STATE_DIR, STATE_NAME)
        self.assertEqual(cp.candidates('TASK-107')[1][0], 'docs')

    def test_the_docstring_states_the_order_the_rule_and_the_choice(self):
        """TASK-107 AC1 and AC8: the module docstring states the order, the rule for each pair, the refusal without fallback,
        the stated choice for a refused docs side and the limits (whitespace collapsed)."""
        doc = ' '.join(ast.get_docstring(ast.parse((SRC / 'contract_path.py').read_bytes().decode('utf-8'))).split())
        for words in ('in the order they are looked at', "('both', None): the contract is in both folders and nothing is read",
                      "('absent', None): the reader gives its own absent finding",
                      "never a fallback to docs", "a stated choice of TASK-107, proposed and fail closed, not the words of the "
                      "specification", 'The module does no I/O', 'the committed base only',
                      'DEF-0095 (the handoff reader) and DEF-0113 are not done here',
                      "It makes no Git call, so it adds nothing to any reader's call bounds; the bounds are stated in each reader"):
            with self.subTest(words=words):
                self.assertIn(words, doc)


def tree_text(*entries):
    return ''.join('%s %s %s\t%s\n' % e for e in entries).encode('utf-8')


def contract(path):
    return ('task: TASK-107\ninput_state:\n  base_commit: ' + 'f' * 40 + '\nwrite_set:\n  paths:\n    - ' + path
            + '\nforbidden:\n  - docs/**\n').encode('utf-8')


class Stand:
    """A stand-in run over objects held in memory, one answer per object id; it counts its calls."""

    def __init__(self, objs):
        self.objs, self.calls = objs, []

    def __call__(self, repo, args, timeout):
        self.calls.append((list(args), timeout))
        if args[2] not in self.objs:
            return {'exit': 128, 'out': b'', 'err': b'', 'error': None}
        return {'exit': 0, 'out': self.objs[args[2]], 'err': b'', 'error': None}


def shell_contract(entry):
    return ('task: TASK-107\ncapabilities:\n  shell: {allow: ["' + entry + '"]}\n').encode('utf-8')


def world(state='none', docs='none', task='TASK-107', texts=None, policy=False):
    """Objects of a commit whose root holds the state folder and docs as asked: 'none' (not in the root), 'ok' (a tasks
    folder holding the contract), 'nocontract' (a tasks folder without the contract), 'blob' (the folder is a plain
    file), 'tasksblob' (its tasks entry is a plain file), 'contractdir' (the contract entry is a tree); policy=True adds
    the policy file to the state folder."""
    c, r, st, stt, dt, dtt, bs, bd = (ch * 40 for ch in 'abcdef56')
    objs = {c: ('tree %s\nauthor A <a> 1 +0000\ncommitter A <a> 1 +0000\n\nm\n' % r).encode('utf-8'),
            bs: texts[0] if texts else contract('src/s.py'), bd: texts[1] if texts else contract('src/d.py')}
    entries = [('100644', 'blob', '1' * 40, 'README.md')]
    for name, kind, top, mid, blob in ((STATE_NAME, state, st, stt, bs), ('docs', docs, dt, dtt, bd)):
        if kind == 'none':
            continue
        if kind == 'blob':
            entries.append(('100644', 'blob', top, name))
            continue
        entries.append(('040000', 'tree', top, name))
        inside = [('100644', 'blob', '2' * 40, 'x.md'), ('100644' if kind == 'tasksblob' else '040000',
                                                         'blob' if kind == 'tasksblob' else 'tree', mid, 'tasks')]
        if policy and name == STATE_NAME:
            inside.append(('100644', 'blob', '3' * 40, 'project.yaml'))
            objs['3' * 40] = b'shell_allow:\n'
        objs[top] = tree_text(*inside)
        objs[mid] = tree_text() if kind == 'nocontract' else tree_text(
            ('040000' if kind == 'contractdir' else '100644', 'tree' if kind == 'contractdir' else 'blob', blob, task + '.yaml'))
    objs[r] = tree_text(*entries)
    return c, objs


class AC3TaskContract(unittest.TestCase):

    def read(self, state='none', docs='none'):
        from aieos_bootstrap import task_contract
        commit, objs = world(state, docs)
        stand = Stand(objs)
        return task_contract.read_contract(str(SRC), commit, 'TASK-107', run=stand), stand

    def test_docs_only_makes_todays_five_calls(self):
        """TASK-107 AC3: the contract only in docs is read with today's five calls and its write set."""
        result, stand = self.read(docs='ok')
        self.assertEqual((result['result'], result['write_set']), ('read', ['src/d.py']))
        self.assertEqual(len(stand.calls), 5)
        self.assertTrue(all(a[0][:2] == ['cat-file', '-p'] and a[1] == 10 for a in stand.calls))

    def test_state_only_reads_the_state_contract(self):
        """TASK-107 AC3: the contract only in the state folder is read, with at most seven calls."""
        result, stand = self.read(state='ok')
        self.assertEqual((result['result'], result['write_set']), ('read', ['src/s.py']))
        self.assertLessEqual(len(stand.calls), 7)

    def test_both_is_refused_and_no_blob_is_read(self):
        """TASK-107 AC3: the contract in both folders gives the reason tree and the finding "contract in both folders", and
        neither blob is read."""
        result, stand = self.read(state='ok', docs='ok')
        self.assertEqual((result['result'], result['reason'], result['findings']),
                         ('unreadable', 'tree', ['tree: contract in both folders']))
        self.assertIsNone(result['write_set'])
        self.assertEqual(len(stand.calls), 6)
        self.assertLessEqual(len(stand.calls), 7)

    def test_neither_gives_the_docs_finding(self):
        """TASK-107 AC3: the contract in neither place gives the docs finding as before."""
        result, stand = self.read()
        self.assertEqual((result['reason'], result['findings']), ('tree', ['tree: docs missing']))
        self.assertEqual(len(stand.calls), 2)

    def test_a_refused_state_side_never_falls_back(self):
        """TASK-107 AC3: a state folder, its tasks entry or its contract entry of the wrong kind is a refusal with its own
        finding, whether docs holds the contract or not, and docs is not read."""
        cases = (('blob', 'tree: state not a tree', 2), ('tasksblob', 'tree: state tasks not a tree', 3),
                 ('contractdir', 'tree: state contract not a blob', 4))
        for kind, finding, calls in cases:
            for docs in ('none', 'ok'):
                with self.subTest(kind=kind, docs=docs):
                    result, stand = self.read(state=kind, docs=docs)
                    self.assertEqual((result['result'], result['reason'], result['findings']),
                                     ('unreadable', 'tree', [finding]))
                    self.assertEqual(len(stand.calls), calls)

    def test_a_refused_docs_side_is_a_refusal(self):
        """TASK-107 AC3: a docs folder of the wrong kind is a refusal with the docs finding, also when the state side holds
        the contract (the stated choice of TASK-107)."""
        for state in ('none', 'ok'):
            with self.subTest(state=state):
                result, _ = self.read(state=state, docs='blob')
                self.assertEqual((result['reason'], result['findings']), ('tree', ['tree: docs not a tree']))

    def test_the_most_calls_are_seven(self):
        """TASK-107 AC3: with a state folder holding the contract and a docs tasks folder without it, the reader makes
        exactly seven calls (commit, root tree, the state folder, its tasks, docs, its tasks, the state blob)."""
        from aieos_bootstrap import task_contract
        commit, objs = world('ok', 'nocontract')
        stand = Stand(objs)
        result = task_contract.read_contract(str(SRC), commit, 'TASK-107', run=stand)
        self.assertEqual((result['result'], result['write_set']), ('read', ['src/s.py']))
        self.assertEqual(len(stand.calls), 7)

    def test_a_failed_call_on_the_state_tasks_tree_is_a_refusal(self):
        """TASK-107 AC3: a failed read of the state folder's tasks tree is the git refusal, not a fallback to docs."""
        from aieos_bootstrap import task_contract
        commit, objs = world('ok', 'ok')
        stand = Stand({k: v for k, v in objs.items() if k != 'd' * 40})
        result = task_contract.read_contract(str(SRC), commit, 'TASK-107', run=stand)
        self.assertEqual((result['result'], result['reason']), ('unreadable', 'git'))
        self.assertEqual(len(result['findings']), 1)
        self.assertIsNone(result['write_set'])

    def test_a_failed_call_on_the_state_side_is_a_refusal(self):
        """TASK-107 AC3: a failed read of the state folder's tree is the git refusal, not a fallback to docs."""
        from aieos_bootstrap import task_contract
        commit, objs = world('ok', 'ok')
        stand = Stand({k: v for k, v in objs.items() if k != 'c' * 40})
        result = task_contract.read_contract(str(SRC), commit, 'TASK-107', run=stand)
        self.assertEqual((result['result'], result['reason']), ('unreadable', 'git'))
        self.assertEqual(len(result['findings']), 1)


class AC4ShellAllow(unittest.TestCase):

    def read(self, state='none', docs='none'):
        commit, objs = world(state, docs, texts=(shell_contract('ls -la'), shell_contract('git status')))
        stand = Stand(objs)
        return sa.read_allowlist(str(SRC), commit, 'TASK-107', run=stand), stand

    def test_the_six_cases(self):
        """TASK-107 AC4: the contract only in docs, only in the state folder, in both, in neither, with the state side
        refused and with the docs side refused gives its contract list and fixed findings, the policy list empty (the stand-in
        holds no policy file)."""
        cases = [
            (('none', 'ok'), ['git status'], ['policy: tree: ' + STATE_NAME + ' missing']),
            (('ok', 'none'), ['ls -la'], ['policy: tree: policy missing']),
            (('ok', 'ok'), [], ['policy: tree: policy missing', 'contract: tree: contract in both folders']),
            (('none', 'none'), [], ['policy: tree: ' + STATE_NAME + ' missing', 'contract: tree: docs missing']),
            (('blob', 'ok'), [], ['policy: tree: ' + STATE_NAME + ' not a tree', 'contract: tree: state not a tree']),
            (('ok', 'blob'), [], ['policy: tree: policy missing', 'contract: tree: docs not a tree']),
            (('tasksblob', 'ok'), [], ['policy: tree: policy missing', 'contract: tree: state tasks not a tree']),
            (('contractdir', 'ok'), [], ['policy: tree: policy missing', 'contract: tree: state contract not a blob']),
        ]
        for (state, docs), want, findings in cases:
            with self.subTest(state=state, docs=docs):
                out, _ = self.read(state, docs)
                self.assertEqual(out['result'], 'read')
                self.assertEqual((out['policy'], out['contract']), ([], want))
                self.assertEqual(out['findings'], findings)

    def test_the_state_tree_is_read_once_and_the_calls_are_bounded(self):
        """TASK-107 AC4: the state folder's tree is read once for both walks, the commit and the root once each, and the
        calls are at most eight, all cat-file -p with the timeout of today."""
        out, stand = self.read('ok', 'ok')
        ids = [a[0][2] for a in stand.calls]
        self.assertEqual(ids.count('a' * 40), 1)
        self.assertEqual(ids.count('b' * 40), 1)
        self.assertEqual(ids.count('c' * 40), 1)
        self.assertLessEqual(len(ids), 8)
        self.assertTrue(all(a[0][:2] == ['cat-file', '-p'] and a[1] == 10 for a in stand.calls))
        out, stand = self.read('none', 'ok')
        self.assertLessEqual(len(stand.calls), 7)

    def test_the_most_calls_are_eight(self):
        """TASK-107 AC4: with the policy file and a state folder holding the contract and a docs tasks folder without it,
        the reader makes exactly eight calls (commit, root tree, the state folder, the policy blob, the state tasks, docs,
        its tasks, the state blob)."""
        commit, objs = world('ok', 'nocontract', texts=(shell_contract('ls -la'), shell_contract('git status')), policy=True)
        stand = Stand(objs)
        out = sa.read_allowlist(str(SRC), commit, 'TASK-107', run=stand)
        self.assertEqual(out['result'], 'read')
        self.assertEqual(out['contract'], ['ls -la'])
        self.assertEqual(len(stand.calls), 8)

    def test_a_failed_state_tasks_tree_read_gives_the_contract_walk_its_own_finding(self):
        """TASK-107 AC4: a failed read of the state folder's tasks tree empties the contract list with its own finding, the
        policy walk keeps its finding, and docs is not used as a fallback."""
        commit, objs = world('ok', 'ok', texts=(shell_contract('ls -la'), shell_contract('git status')))
        stand = Stand({k: v for k, v in objs.items() if k != 'd' * 40})
        out = sa.read_allowlist(str(SRC), commit, 'TASK-107', run=stand)
        self.assertEqual((out['policy'], out['contract']), ([], []))
        self.assertEqual(out['findings'], ['policy: tree: policy missing', 'contract: git: exit 128'])

    def test_a_failed_state_tree_read_gives_each_walk_its_own_finding(self):
        """TASK-107 AC4: a failed read of the state folder's tree gives the policy walk its git finding first and the contract
        walk its own, and no fallback to docs."""
        commit, objs = world('ok', 'ok', texts=(shell_contract('ls -la'), shell_contract('git status')))
        stand = Stand({k: v for k, v in objs.items() if k != 'c' * 40})
        out = sa.read_allowlist(str(SRC), commit, 'TASK-107', run=stand)
        self.assertEqual((out['policy'], out['contract']), ([], []))
        self.assertEqual(out['findings'], ['policy: git: exit 128', 'contract: git: exit 128'])


class AC6Parity(unittest.TestCase):

    def test_a_reader_gives_the_same_answer_for_the_same_bytes_in_either_place(self):
        """TASK-107 AC6: on one stand-in each reader's public answer for a contract held only in the state folder equals the
        same reader's answer for the same bytes held only in docs (task_contract in full; the shell allowlist reader in its
        contract list, its policy findings differing by the missing folder); no bytes are compared across readers."""
        from aieos_bootstrap import task_contract
        same = contract('src/same.py')
        got = []
        for state, docs in (('ok', 'none'), ('none', 'ok')):
            commit, objs = world(state, docs, texts=(same, same))
            got.append(task_contract.read_contract(str(SRC), commit, 'TASK-107', run=Stand(objs)))
        self.assertEqual(got[0], got[1])
        self.assertEqual(got[0]['write_set'], ['src/same.py'])
        allow = shell_contract('ls -la')
        lists = []
        for state, docs in (('ok', 'none'), ('none', 'ok')):
            commit, objs = world(state, docs, texts=(allow, allow))
            out = sa.read_allowlist(str(SRC), commit, 'TASK-107', run=Stand(objs))
            self.assertEqual(out['result'], 'read')
            lists.append(out['contract'])
        self.assertEqual(lists[0], lists[1])
        self.assertEqual(lists[0], ['ls -la'])


class AC6OwnTests(unittest.TestCase):

    def test_other_task_ids(self):
        """TASK-107 AC6: other_task_ids flags other tasks' qualified AC ids, across a line break, and not TASK-107's."""
        self.assertEqual(other_task_ids('TASK-100 AC1'), ['TASK-100 AC1'])
        self.assertEqual(other_task_ids('TASK-1070 AC1'), ['TASK-1070 AC1'])
        self.assertEqual(other_task_ids('TASK-104\n   AC1'), ['TASK-104 AC1'])
        self.assertEqual(other_task_ids('TASK-107 AC1'), [])

    def test_contract_path_tests_name_their_criteria(self):
        """TASK-107 AC6: every test function of this module names "TASK-107 ACn" in its own docstring and no other task's AC
        in qualified form."""
        tree = ast.parse(pathlib.Path(__file__).read_bytes().decode('utf-8'))
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
            doc = ast.get_docstring(fn) or ''
            with self.subTest(test=fn.name):
                self.assertTrue(re.findall(r'TASK-107 AC[0-9]+', ' '.join(doc.split())))
                self.assertEqual(other_task_ids(doc), [])


if __name__ == '__main__':
    unittest.main()
