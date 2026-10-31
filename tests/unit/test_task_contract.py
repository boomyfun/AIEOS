"""Unit tests of aieos_bootstrap.task_contract (task TASK-071, AC1, AC2, AC3, AC5, AC7 and AC8): the reader of a task's
contract at a given commit, driven by a stand-in run that serves fixed objects; no process starts and no file is
written. Each test names its criteria in its own docstring."""

import ast
import pathlib
import re
import unittest
from unittest import mock

from aieos_bootstrap import gitread
from aieos_bootstrap import task_contract as tc

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'
ROOT = str(SRC)
KEYS = ['result', 'reason', 'findings', 'task', 'base_commit', 'write_set', 'forbidden']
COMMIT, TREE, DOCS, TASKS, BLOB = 'a' * 40, 'b' * 40, 'c' * 40, 'd' * 40, 'e' * 40
BASE = 'f' * 40
MARKER = 'MARKER'
VALID = ('task: TASK-071\ninput_state:\n  base_commit: ' + BASE + '\nwrite_set:\n  paths:\n    - src/x.py\n'
         'forbidden:\n  - docs/**\n')
MIB = 1 << 20


def other_task_ids(text):
    """The qualified AC ids of tasks other than TASK-071 in text, with every run of whitespace collapsed (rule (e))."""
    return re.findall(r'TASK-(?!071 )[0-9]+ AC[0-9]+', ' '.join(text.split()))


def commit_text(tree=TREE):
    # "A <a> 1 +0000" is a placeholder author line, not an address
    return ('tree %s\nauthor A <a> 1 +0000\ncommitter A <a> 1 +0000\n\nmessage\n' % tree).encode('utf-8')


def tree_text(*entries):
    return ''.join('%s %s %s\t%s\n' % e for e in entries).encode('utf-8')


def objects(contract=VALID):
    return {COMMIT: commit_text(),
            TREE: tree_text(('100644', 'blob', '1' * 40, 'README.md'), ('040000', 'tree', DOCS, 'docs')),
            DOCS: tree_text(('040000', 'tree', TASKS, 'tasks'), ('100644', 'blob', '2' * 40, 'x.md')),
            TASKS: tree_text(('100644', 'blob', '3' * 40, 'TASK-070.yaml'), ('100644', 'blob', BLOB, 'TASK-071.yaml')),
            BLOB: contract if isinstance(contract, bytes) else contract.encode('utf-8')}


class Stand:
    """A stand-in run serving fixed objects; position n (1 to 5) can be given another result or an exception."""

    def __init__(self, objs=None, at=None, give=None):
        self.objs = objects() if objs is None else objs
        self.at, self.give, self.calls = at, give, []

    def __call__(self, repo, args, timeout):
        self.calls.append((repo, list(args), timeout))
        if len(self.calls) == self.at:
            if isinstance(self.give, Exception):
                raise self.give
            return self.give
        return {'exit': 0, 'out': self.objs[args[2]], 'err': b'', 'error': None}


def ok(out):
    return {'exit': 0, 'out': out, 'err': b'', 'error': None}


def read(contract=VALID, task_id='TASK-071', **kw):
    objs = objects(contract)
    objs.update(kw)
    return tc.read_contract(ROOT, COMMIT, task_id, run=Stand(objs))


class StrSub(str):
    pass


class BytesSub(bytes):
    pass


class DictSub(dict):
    pass


class AC1Arguments(unittest.TestCase):

    def test_a_read_has_the_seven_keys_and_fresh_lists(self):
        """TASK-071 AC1: the result is a mapping with exactly the seven keys; "read" carries findings [] and fresh lists."""
        r1, r2 = read(), read()
        self.assertEqual(list(r1), KEYS)
        self.assertEqual((r1['result'], r1['reason'], r1['findings']), ('read', None, []))
        self.assertEqual((r1['task'], r1['base_commit'], r1['write_set'], r1['forbidden']),
                         ('TASK-071', BASE, ['src/x.py'], ['docs/**']))
        self.assertEqual(r1, r2)
        self.assertIsNot(r1['write_set'], r2['write_set'])

    def test_each_bad_argument_is_refused_before_run(self):
        """TASK-071 AC1: step (1) refuses each bad argument with its exact finding, before run is called."""
        cases = [((None, COMMIT, 'TASK-071'), 'argument: root'), (('src', COMMIT, 'TASK-071'), 'argument: root'),
                 ((ROOT + '/no-such-folder', COMMIT, 'TASK-071'), 'argument: root'),
                 ((StrSub(ROOT), COMMIT, 'TASK-071'), 'argument: root'),
                 ((str(SRC / 'task_contract.py'), COMMIT, 'TASK-071'), 'argument: root'),
                 ((ROOT, None, 'TASK-071'), 'argument: commit'), ((ROOT, 'a' * 39, 'TASK-071'), 'argument: commit'),
                 ((ROOT, 'a' * 41, 'TASK-071'), 'argument: commit'), ((ROOT, 'a' * 63, 'TASK-071'), 'argument: commit'),
                 ((ROOT, 'a' * 40 + '\n', 'TASK-071'), 'argument: commit'),
                 ((ROOT, 'A' * 40, 'TASK-071'), 'argument: commit'),
                 ((ROOT, StrSub(COMMIT), 'TASK-071'), 'argument: commit'),
                 ((ROOT, COMMIT, None), 'argument: task_id'), ((ROOT, COMMIT, 'TASK-07a'), 'argument: task_id'),
                 ((ROOT, COMMIT, 'TASK-٠٧١'), 'argument: task_id'),
                 ((ROOT, COMMIT, 'TASK-071\n'), 'argument: task_id'),
                 ((ROOT, COMMIT, StrSub('TASK-071')), 'argument: task_id'),
                 (('src', 'x', 'y'), 'argument: root'), ((ROOT, 'x', 'y'), 'argument: commit')]
        for args, finding in cases:
            stand = Stand()
            with self.subTest(args=repr(args)):
                r = tc.read_contract(*args, run=stand)
                self.assertEqual((r['result'], r['reason'], r['findings']), ('unreadable', 'argument', [finding]))
                self.assertEqual([r['task'], r['base_commit'], r['write_set'], r['forbidden']], [None] * 4)
                self.assertEqual(stand.calls, [])

    def test_task_contract_never_raises(self):
        """TASK-071 AC1: a patched gitread.parse_commit that raises gives reason "entry", ["entry: <type name>"]."""
        with mock.patch.object(gitread, 'parse_commit', side_effect=KeyError('x')):
            r = read()
        self.assertEqual((r['result'], r['reason'], r['findings']), ('unreadable', 'entry', ['entry: KeyError']))


class AC2GitReads(unittest.TestCase):

    def test_the_calls_their_form_and_order(self):
        """TASK-071 AC2: five calls, each run(root, ["cat-file", "-p", <id>], 10), in the order commit, root tree,
        docs, tasks, blob."""
        stand = Stand()
        tc.read_contract(ROOT, COMMIT, 'TASK-071', run=stand)
        self.assertEqual(stand.calls, [(ROOT, ['cat-file', '-p', i], 10) for i in (COMMIT, TREE, DOCS, TASKS, BLOB)])

    def test_run_is_taken_at_call_time(self):
        """TASK-071 AC2: with no run passed, gitread.run is looked up at call time (a patched one is the one called)."""
        stand = Stand()
        with mock.patch.object(gitread, 'run', stand):
            r = tc.read_contract(ROOT, COMMIT, 'TASK-071')
        self.assertEqual((r['result'], len(stand.calls)), ('read', 5))

    def test_parse_commit_gets_the_original_bytes(self):
        """TASK-071 AC2: parse_commit is given the commit's original bytes."""
        seen = []
        real = gitread.parse_commit

        def spy(data):
            seen.append(data)
            return real(data)
        with mock.patch.object(gitread, 'parse_commit', spy):
            read()
        self.assertEqual(seen, [commit_text()])
        self.assertIs(type(seen[0]), bytes)

    def test_result_faults_at_every_position(self):
        """TASK-071 AC2: each result-check fault, at each of the five call positions, gives its "git" finding."""
        faults = [(ValueError(MARKER), 'git: run raised ValueError'), ([MARKER], 'git: result shape'),
                  (DictSub(ok(b'')), 'git: result shape'), ({'exit': 0, 'out': b''}, 'git: result shape'),
                  (dict(ok(b''), extra=1), 'git: result shape'),
                  ({'exit': 0, 'out': b'', 'err': b'', 'error': MARKER}, 'git: error'),
                  ({'exit': 1, 'out': b'', 'err': MARKER.encode(), 'error': None}, 'git: exit 1'),
                  ({'exit': True, 'out': b'', 'err': b'', 'error': None}, 'git: exit not an int'),
                  ({'exit': None, 'out': b'', 'err': b'', 'error': None}, 'git: exit not an int'),
                  ({'exit': MARKER, 'out': b'', 'err': b'', 'error': None}, 'git: exit not an int'),
                  (ok(MARKER), 'git: out not bytes'), (ok(bytearray(b'x')), 'git: out not bytes'),
                  (ok(BytesSub(b'x')), 'git: out not bytes'),
                  ({'exit': 1, 'out': MARKER, 'err': b'', 'error': None}, 'git: exit 1')]
        for pos in range(1, 6):
            for give, finding in faults:
                with self.subTest(position=pos, finding=finding):
                    r = tc.read_contract(ROOT, COMMIT, 'TASK-071', run=Stand(at=pos, give=give))
                    self.assertEqual((r['result'], r['reason'], r['findings']), ('unreadable', 'git', [finding]))
                    self.assertNotIn(MARKER, repr(r))

    def test_commit_faults(self):
        """TASK-071 AC2: the commit text over the cap or not UTF-8, a parse_commit error and a tree id out of form."""
        big = commit_text() + b'x' * (MIB - len(commit_text()))
        self.assertEqual(len(big), MIB)
        self.assertEqual(read(**{COMMIT: big})['result'], 'read')
        for out, finding in [(big + b'x', 'git: commit text over the cap'), (b'\xff' + commit_text(),
                             'git: commit text not UTF-8'), (b'no tree\n\nm\n', 'git: commit out of form')]:
            with self.subTest(finding=finding):
                self.assertEqual(read(**{COMMIT: out})['findings'], [finding])
        bad = {'tree': 'B' * 40, 'parents': [], 'author': 'A', 'committer': 'A', 'message': '', 'trailers': [],
               'error': None}
        with mock.patch.object(gitread, 'parse_commit', return_value=bad):
            self.assertEqual(read()['findings'], ['git: commit out of form'])

    def test_tree_faults_at_each_tree(self):
        """TASK-071 AC2: each tree-class fault, at each of the three trees, gives its "tree" finding."""
        for tid in (TREE, DOCS, TASKS):
            good = objects()[tid]
            big = good + b'x' * (MIB + 1 - len(good))
            for out, finding in [(big, 'tree: tree text over the cap'), (good + b'\xff', 'tree: tree text not UTF-8'),
                                 (good[:-1], 'tree: line out of form'),
                                 (good + b'100644 blob ' + b'9' * 40 + b' MARKER\n', 'tree: line out of form'),
                                 (good + b'10064 blob ' + b'9' * 40 + b'\tm\n', 'tree: line out of form'),
                                 (good + b'100644 link ' + b'9' * 40 + b'\tm\n', 'tree: line out of form'),
                                 (good + b'100644 blob ' + b'9' * 39 + b'\tm\n', 'tree: line out of form'),
                                 (good + b'100644 blob ' + b'9' * 40 + b'\t\n', 'tree: line out of form'),
                                 (good + b'100644 blob ' + b'9' * 40 + b'\ta/b\n', 'tree: line out of form'),
                                 (good + good, 'tree: repeated name')]:
                with self.subTest(tree=tid[0], finding=finding):
                    r = read(**{tid: out})
                    self.assertEqual((r['reason'], r['findings']), ('tree', [finding]))
                    self.assertNotIn(MARKER, repr(r))

    def test_sought_entries(self):
        """TASK-071 AC2: docs, tasks or the contract missing or of the wrong mode and type; quoted and raw names and a
        name holding U+2028 or U+0085 never match or split a line."""
        e = lambda m, t, i, n: tree_text((m, t, i, n))  # noqa: E731
        cases = [({TREE: e('100644', 'blob', '1' * 40, 'README.md')}, 'tree: docs missing'),
                 ({TREE: e('100644', 'blob', DOCS, 'docs')}, 'tree: docs not a tree'),
                 ({DOCS: e('100644', 'blob', '2' * 40, 'x')}, 'tree: tasks missing'),
                 ({DOCS: e('160000', 'commit', TASKS, 'tasks')}, 'tree: tasks not a tree'),
                 ({TASKS: e('100644', 'blob', '3' * 40, 'TASK-070.yaml')}, 'tree: contract missing'),
                 ({TASKS: e('100755', 'blob', BLOB, 'TASK-071.yaml')}, 'tree: contract not a 100644 blob'),
                 ({TASKS: e('120000', 'blob', BLOB, 'TASK-071.yaml')}, 'tree: contract not a 100644 blob'),
                 ({TASKS: e('100644', 'blob', BLOB, '"TASK-071.yaml"')}, 'tree: contract missing'),
                 ({TASKS: e('100644', 'blob', BLOB, 'TASK-071.yaml\u2028')}, 'tree: contract missing'),
                 ({TASKS: e('100644', 'blob', BLOB, '\u0085TASK-071.yaml')}, 'tree: contract missing'),
                 ({TREE: e('040000', 'tree', DOCS, 'döcs')}, 'tree: docs missing')]
        for over, finding in cases:
            with self.subTest(finding=finding, over=repr(over)[:60]):
                self.assertEqual(read(**over)['findings'], [finding])

    def test_order_cases(self):
        """TASK-071 AC2: exit 1 with an out of type str gives "git: exit 1"; a bad line and no docs entry give "tree:
        line out of form"; at most five calls."""
        r = tc.read_contract(ROOT, COMMIT, 'TASK-071', run=Stand(at=1, give={'exit': 1, 'out': 's', 'err': b'',
                                                                              'error': None}))
        self.assertEqual(r['findings'], ['git: exit 1'])
        r = read(**{TREE: b'bad\n'})
        self.assertEqual(r['findings'], ['tree: line out of form'])
        stand = Stand()
        tc.read_contract(ROOT, COMMIT, 'TASK-071', run=stand)
        self.assertLessEqual(len(stand.calls), 5)


PARSE = [
    ('task:TASK-071\n', 'parse: top-level line out of form'),
    ('Task: TASK-071\n', 'parse: top-level line out of form'),
    ('task1: x\n', 'parse: top-level line out of form'),
    ('write_set: x\n', 'parse: top-level line out of form'),
    ('forbidden: x\n', 'parse: top-level line out of form'),
    (' x: y\n', 'parse: top-level line out of form'),
    ('task: TASK-071\n', 'parse: repeated key'),
    ('write_set:\n', 'parse: repeated key'),
    ('forbidden:\n', 'parse: repeated key'),
]


def mutate(where, line):
    """VALID with line put after the named anchor line."""
    anchors = {'top': 'forbidden:\n  - docs/**\n', 'input': '  base_commit: ' + BASE + '\n',
               'paths': '    - src/x.py\n', 'forb': '  - docs/**\n', 'ws': 'write_set:\n'}
    a = anchors[where]
    return VALID.replace(a, a + line, 1)


class AC2NamesAndOrder(unittest.TestCase):

    def test_no_tree_name_in_any_finding(self):
        """TASK-071 AC2: with "MARKER" as a well-formed tree name, in a repeated name, beside a missing docs entry and
        beside a contract of the wrong mode, "MARKER" is absent from the repr of every result."""
        e = lambda m, t, i, n: tree_text((m, t, i, n))  # noqa: E731
        cases = [({TREE: e('100644', 'blob', '1' * 40, MARKER) + e('100644', 'blob', '2' * 40, MARKER)},
                  'tree: repeated name'),
                 ({TREE: e('100644', 'blob', '1' * 40, MARKER)}, 'tree: docs missing'),
                 ({TASKS: e('100644', 'blob', '3' * 40, MARKER) + e('100755', 'blob', BLOB, 'TASK-071.yaml')},
                  'tree: contract not a 100644 blob')]
        for over, finding in cases:
            with self.subTest(finding=finding):
                r = read(**over)
                self.assertEqual(r['findings'], [finding])
                self.assertNotIn(MARKER, repr(r))

    def test_a_tree_of_exactly_the_cap_reads(self):
        """TASK-071 AC2: a tree text of exactly 1 MiB passes, at each of the three trees."""
        for tid in (TREE, DOCS, TASKS):
            good = objects()[tid]
            name = 'z' * (MIB - len(good) - 54)
            full = good + tree_text(('100644', 'blob', '9' * 40, name))
            with self.subTest(tree=tid[0]):
                self.assertEqual(len(full), MIB)
                self.assertEqual(read(**{tid: full})['result'], 'read')

    def test_the_order_of_each_pair(self):
        """TASK-071 AC2: for adjacent pairs of step (2)'s and step (3)'s order, a text with both faults gives the
        first one's finding. Not every pair is tried here; test_order_cases and test_bytes try others."""
        both = {'exit': 1, 'out': b'', 'err': b'', 'error': MARKER}
        r = tc.read_contract(ROOT, COMMIT, 'TASK-071', run=Stand(at=1, give=dict(both, extra=1)))
        self.assertEqual(r['findings'], ['git: result shape'])
        r = tc.read_contract(ROOT, COMMIT, 'TASK-071', run=Stand(at=1, give=both))
        self.assertEqual(r['findings'], ['git: error'])
        self.assertEqual(read(**{COMMIT: b'\xff' * (MIB + 1)})['findings'], ['git: commit text over the cap'])
        self.assertEqual(read(**{TREE: b'\xff' * (MIB + 1)})['findings'], ['tree: tree text over the cap'])
        self.assertEqual(read(**{TREE: b'\xff bad\n'})['findings'], ['tree: tree text not UTF-8'])
        good = objects()[TREE]
        self.assertEqual(read(**{TREE: good + good + b'bad\n'})['findings'], ['tree: line out of form'])
        dup = tree_text(('100644', 'blob', '1' * 40, 'x'), ('100644', 'blob', '2' * 40, 'x'))
        self.assertEqual(read(**{TREE: dup})['findings'], ['tree: repeated name'])
        self.assertEqual(read(b'\xff' * (MIB + 1))['findings'], ['bytes: over the cap'])
        self.assertEqual(read(b'\xff' + '\ufeff'.encode('utf-8') + VALID.encode())['findings'], ['bytes: not UTF-8'])

    def test_more_parse_cases(self):
        """TASK-071 AC3: a base_commit under another top-level key is missing; the first "  paths:" with a value is a
        write_set line out of form."""
        moved = VALID.replace('  base_commit: ' + BASE + '\n', '') + 'read_set:\n  base_commit: ' + BASE + '\n'
        self.assertEqual(tc.parse_contract(moved, 'TASK-071')['findings'], ['parse: base_commit missing'])
        first = VALID.replace('  paths:\n', '  paths: x\n')
        self.assertEqual(tc.parse_contract(first, 'TASK-071')['findings'], ['parse: write_set line out of form'])

    def test_the_line_id_behaves_as_gitreads(self):
        """TASK-071 AC2: a tree line's id is accepted exactly when gitread.OBJECT_ID fullmatches it."""
        for oid in ('9' * 40, '9' * 64, '9' * 39, '9' * 41, '9' * 63, 'A' * 40, 'g' * 40):
            self.assertEqual(tc._LINE.fullmatch('100644 blob %s\tx' % oid) is not None,
                             gitread.OBJECT_ID.fullmatch(oid) is not None, oid)

    def test_the_line_id_is_gitreads(self):
        """TASK-071 AC2: the tree line's id group is gitread.OBJECT_ID's pattern."""
        self.assertIn('(' + gitread.OBJECT_ID.pattern + ')', tc._LINE.pattern)


class AC3Parse(unittest.TestCase):

    def check(self, text, finding, reason='parse'):
        r = tc.parse_contract(text, 'TASK-071')
        self.assertEqual((r['result'], r['reason'], r['findings']), ('unreadable', reason, [finding]))
        self.assertEqual([r['task'], r['base_commit'], r['write_set'], r['forbidden']], [None] * 4)

    def test_top_level_and_repeated_keys(self):
        """TASK-071 AC3: a top-level line of another form and a repeated top-level key, each its exact finding."""
        for line, finding in PARSE:
            with self.subTest(line=line):
                self.check(VALID + line, finding)

    def test_lines_inside_the_sections(self):
        """TASK-071 AC3: each line rule of step (4) (i), with its exact finding."""
        cases = [('input', '  base_commit:x\n', 'parse: base_commit line out of form'),
                 ('input', '  base_commit: ' + BASE + '\n', 'parse: repeated key'),
                 ('paths', '  paths:\n', 'parse: repeated key'),
                 ('paths', '  paths: x\n', 'parse: write_set line out of form'),
                 ('paths', '    -\n', 'parse: write_set line out of form'),
                 ('paths', '    -x\n', 'parse: write_set line out of form'),
                 ('paths', '    - \n', 'parse: write_set line out of form'),
                 ('paths', '   - a\n', 'parse: write_set line out of form'),
                 ('paths', '      - a\n', 'parse: write_set line out of form'),
                 ('paths', '  other: x\n', 'parse: write_set line out of form'),
                 ('ws', '    - a\n', 'parse: write_set line out of form'),
                 ('paths', '     - x\n', 'parse: write_set line out of form'),
                 ('forb', '  - \n', 'parse: forbidden line out of form'),
                 ('forb', '    - a\n', 'parse: forbidden line out of form'),
                 ('forb', '  key: x\n', 'parse: forbidden line out of form')]
        for where, line, finding in cases:
            with self.subTest(line=line):
                self.check(mutate(where, line), finding)

    def test_items(self):
        """TASK-071 AC3: an item out of form, taken unstripped."""
        for item in ['a ', 'a ', 'a #c', '"a"', "'a'", '{a}', '[a]', '/a', './a', 'a/', 'a//b', 'a/./b', 'a/../b',
                     'a:b', '.', '..']:
            with self.subTest(item=item):
                self.check(mutate('paths', '    - ' + item + '\n'), 'parse: item out of form')
                self.check(mutate('forb', '  - ' + item + '\n'), 'parse: item out of form')

    def test_fields(self):
        """TASK-071 AC3: the field findings of step (4) (ii), in their order."""
        no_task = VALID.replace('task: TASK-071\n', '')
        cases = [(no_task, 'parse: task missing'), (VALID.replace('task: TASK-071', 'task:'), 'parse: task missing'),
                 (VALID.replace('task: TASK-071', 'task: '), 'parse: task missing'),
                 (VALID.replace('task: TASK-071', 'task:  '), 'parse: task value out of form'),
                 (VALID.replace('task: TASK-071', 'task:  TASK-071'), 'parse: task value out of form'),
                 (VALID.replace('task: TASK-071', 'task: TASK-071 '), 'parse: task value out of form'),
                 (VALID.replace('task: TASK-071', 'task: TASK-071 # c'), 'parse: task value out of form'),
                 (VALID.replace('task: TASK-071', 'task: TASK-071 '), 'parse: task value out of form'),
                 (VALID.replace('  base_commit: ' + BASE + '\n', ''), 'parse: base_commit missing'),
                 (VALID.replace('  base_commit: ' + BASE, '  base_commit:'), 'parse: base_commit missing'),
                 (VALID.replace('  base_commit: ' + BASE, '  base_commit: '), 'parse: base_commit missing'),
                 (VALID.replace('  base_commit: ' + BASE, '    base_commit: ' + BASE), 'parse: base_commit missing'),
                 (VALID.replace('  base_commit: ' + BASE, '  base_commit:   '), 'parse: base_commit out of form'),
                 (VALID.replace(BASE, BASE + ' '), 'parse: base_commit out of form'),
                 (VALID.replace(BASE, BASE[:39]), 'parse: base_commit out of form'),
                 (VALID.replace(BASE, BASE.upper()), 'parse: base_commit out of form'),
                 (VALID.replace('    - src/x.py\n', ''), 'parse: write_set empty'),
                 (VALID.replace('  - docs/**\n', ''), 'parse: forbidden empty')]
        for text, finding in cases:
            with self.subTest(finding=finding, text=text[:30]):
                self.check(text, finding)

    def test_order_and_task(self):
        """TASK-071 AC3: two line faults give the earlier line's; a line fault before a field fault; "task" last."""
        self.check(mutate('paths', '    -x\n') + 'Bad\n', 'parse: write_set line out of form')
        self.check(VALID.replace(BASE, 'x') + 'Bad\n', 'parse: top-level line out of form')
        self.check(VALID.replace('TASK-071', 'TASK-070'), 'task: another task', 'task')
        self.check(VALID.replace('TASK-071', 'TASK-070').replace(BASE, 'x'), 'parse: base_commit out of form')

    def test_skipped_lines_and_arguments(self):
        """TASK-071 AC3: comment and whitespace-only lines are skipped; a text or task_id not of type str is
        "argument"."""
        for text in ['# c\n' + VALID, mutate('paths', ' \n'), mutate('paths', '      # c\n')]:
            with self.subTest(text=text[:20]):
                self.assertEqual(tc.parse_contract(text, 'TASK-071')['result'], 'read')
        self.assertEqual(tc.parse_contract(None, None)['findings'], ['argument: text'])
        self.assertEqual(tc.parse_contract(VALID, None)['findings'], ['argument: task_id'])
        self.assertEqual(tc.parse_contract(StrSub(VALID), 'TASK-071')['findings'], ['argument: text'])

    def test_bytes(self):
        """TASK-071 AC3: step (3)'s refusals in their order; a non-ASCII text without controls passes."""
        cases = [(VALID.encode() + b'#' * (MIB + 1 - len(VALID.encode())), 'bytes: over the cap'),
                 (VALID.encode() + b'\xff', 'bytes: not UTF-8'), ('\ufeff' + VALID, 'bytes: byte-order mark'),
                 (VALID + '# \ufeff\n', 'bytes: byte-order mark'), ('\ufeff' + VALID + '\r', 'bytes: byte-order mark')]
        cases += [(VALID + '# ' + c + '\n', 'bytes: control character')
                  for c in ['\r', '\x00', '\t', '\x0c', '\x0b', '\x7f', '\x85', '\x9f', '\u2028', '\u2029']]
        for contract, finding in cases:
            with self.subTest(finding=finding, tail=repr(contract[-3:])):
                r = read(contract)
                self.assertEqual((r['reason'], r['findings']), ('bytes', [finding]))
        exact = VALID.encode() + b'#' * (MIB - len(VALID.encode()) - 1) + b'\n'
        self.assertEqual(len(exact), MIB)
        self.assertEqual(read(exact)['result'], 'read')
        self.assertEqual(read(VALID + '# é€\n')['result'], 'read')


class AC5WhatItImports(unittest.TestCase):

    def test_task_contract_imports_and_names(self):
        """TASK-071 AC5: task_contract.py imports exactly re, aieos_bootstrap.contract_path (the one widening, an amendment
        by TASK-107) and aieos_bootstrap.gitread and uses none of the refused names, attributes or strings."""
        text = (SRC / 'task_contract.py').read_bytes().decode('utf-8')
        tree = ast.parse(text)
        imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        imports |= {n.module + '.' + a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
        self.assertEqual(imports, {'re', 'aieos_bootstrap.contract_path', 'aieos_bootstrap.gitread'})
        deny = {'open', 'exec', 'eval', 'compile', '__import__', 'importlib', 'input', 'breakpoint', '__builtins__'}
        self.assertEqual([n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id in deny], [])
        attrs = {'now', 'utcnow', 'today', 'time', 'environ', 'getenv', 'system', 'popen', 'Popen', 'stdin'}
        self.assertEqual([n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr in attrs], [])
        self.assertEqual([n for n in ast.walk(tree) if isinstance(n, ast.Assert)], [])
        runs = [ast.unparse(n.value) for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == 'run']
        self.assertEqual(set(runs), {'gitread'})
        used = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and ast.unparse(n.value) == 'gitread'}
        self.assertEqual(used, {'run', 'parse_commit', 'OBJECT_ID', 'form_error'})
        consts = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertEqual([c for c in consts if c in ('valid', 'accepted', 'approved')], [])
        self.assertNotIn('.' + 'aieos', text)
        names = [t.id for n in ast.walk(tree) if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)]
        self.assertEqual([x for x in names if any(w in x.lower() for w in ('token', 'pass', 'secret', 'pwd'))], [])

    def test_no_hook_side_module_names_task_contract(self):
        """TASK-071 AC5: no older hook-side module names task_contract."""
        for name in ('claude_code.py', 'claude_code_hook.py', 'claude_code_channel.py', 'claude_code_reads.py',
                     'claude_code_store.py', 'claude_code_read_hook.py'):
            with self.subTest(module=name):
                self.assertNotIn('task_contract', (SRC / name).read_bytes().decode('utf-8'))


class AC7Stated(unittest.TestCase):

    def test_the_docstring_states_the_flow_and_limits(self):
        """TASK-071 AC7: task_contract.py's module docstring states the flow, the reason table and the limits
        (whitespace collapsed)."""
        doc = ' '.join(ast.get_docstring(ast.parse((SRC / 'task_contract.py').read_bytes().decode('utf-8'))).split())
        for words in ('"unreadable" never carries a partial or default write-set', 'The commit is the caller\'s',
                      'no base is chosen here', 'capabilities.shell.allow is not read',
                      'no allowlist source is chosen here', 'stricter than G0\'s', 'G0\'s rules are copied, not shared',
                      'refuses a U+FEFF anywhere, a carriage return, NUL, tab and the other C0 controls, DEL, the C1 '
                      'controls, U+2028 and U+2029', 'a committed CRLF contract that G0 accepts is refused',
                      'The object store only', 'The commit is not proven a commit object', 'The five calls',
                      'about 50 seconds', 'the tree-size bound of the cap', 'the replace-refs limit',
                      'the outer-repository limit', 'run is a test seam: a production caller does not pass it',
                      'Its one hook-side caller is claude_code_pretool_hook (TASK-072)', 'The reason table'):
            with self.subTest(words=words):
                self.assertIn(words, doc)
        self.assertNotIn('.' + 'aieos', doc)


class AC8OwnTests(unittest.TestCase):

    def test_other_task_ids(self):
        """TASK-071 AC8: other_task_ids flags other tasks' qualified AC ids, across a line break, and not TASK-071's."""
        self.assertEqual(other_task_ids('TASK-100 AC1'), ['TASK-100 AC1'])
        self.assertEqual(other_task_ids('TASK-0710 AC1'), ['TASK-0710 AC1'])
        self.assertEqual(other_task_ids('TASK-070\n   AC1'), ['TASK-070 AC1'])
        self.assertEqual(other_task_ids('TASK-071 AC1'), [])

    def test_task_contract_tests_name_their_criteria(self):
        """TASK-071 AC8: every test function of this module names "TASK-071 ACn" in its own docstring and no other
        task's AC in qualified form."""
        tree = ast.parse(pathlib.Path(__file__).read_bytes().decode('utf-8'))
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
            doc = ast.get_docstring(fn) or ''
            with self.subTest(test=fn.name):
                self.assertTrue(re.findall(r'TASK-071 AC[0-9]+', ' '.join(doc.split())))
                self.assertEqual(other_task_ids(doc), [])


if __name__ == '__main__':
    unittest.main()
