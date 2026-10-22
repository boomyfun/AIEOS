"""Property tests of aieos_bootstrap.task_contract (task TASK-071, AC8): contract and tree texts generated from a
template with fixed seeds, at most 50 cases each; standard library only. Each test names its criteria in its own
docstring."""

import ast
import pathlib
import random
import re
import unittest

from aieos_bootstrap import task_contract as tc

BASE = 'f' * 40
COMMIT, TREE, DOCS, TASKS, BLOB = 'a' * 40, 'b' * 40, 'c' * 40, 'd' * 40, 'e' * 40
SEGMENTS = ['src', 'tests', 'docs', 'a', 'b_c', 'x.py', 'y-z', '**', '*.md']
CASES = 50


def other_task_ids(text):
    """The qualified AC ids of tasks other than TASK-071 in text, with every run of whitespace collapsed (rule (e))."""
    return re.findall(r'TASK-(?!071 )[0-9]+ AC[0-9]+', ' '.join(text.split()))


def items(rng):
    return ['/'.join(rng.choice(SEGMENTS) for _ in range(rng.randint(1, 3))) for _ in range(rng.randint(1, 5))]


def template(ws, fb, extra=''):
    return ('task: TASK-071\ninput_state:\n  base_commit: ' + BASE + '\nwrite_set:\n  paths:\n' +
            ''.join('    - %s\n' % i for i in ws) + 'forbidden:\n' + ''.join('  - %s\n' % i for i in fb) + extra)


PARSE_MUTATIONS = [lambda t: t + 'Bad line\n', lambda t: t + 'task: TASK-071\n',
                   lambda t: t.replace('  paths:\n', '  paths: x\n'), lambda t: t.replace('forbidden:\n', 'forbidden:\n  -\n'),
                   lambda t: t.replace('  base_commit: ' + BASE, '  base_commit:x'),
                   lambda t: t.replace(BASE, BASE[:20]), lambda t: t.replace('task: TASK-071', 'task: TASK-071 '),
                   lambda t: t.replace('    - ', '    - /', 1)]
SKIP_MUTATIONS = [lambda t: '# a comment\n' + t, lambda t: t.replace('forbidden:\n', ' \nforbidden:\n'),
                  lambda t: t + '\n\n']
BYTES_MUTATIONS = [lambda t: t + '# \r\n', lambda t: '﻿' + t, lambda t: t + '#  \n', lambda t: t + '#\t\n',
                   lambda t: t + '# \x85\n']


def objects(contract):
    tree = lambda *es: ''.join('%s %s %s\t%s\n' % e for e in es).encode('utf-8')  # noqa: E731
    return {COMMIT: ('tree %s\nauthor A <a> 1 +0000\ncommitter A <a> 1 +0000\n\nm\n' % TREE).encode('utf-8'),
            TREE: tree(('040000', 'tree', DOCS, 'docs')), DOCS: tree(('040000', 'tree', TASKS, 'tasks')),
            TASKS: tree(('100644', 'blob', BLOB, 'TASK-071.yaml')), BLOB: contract.encode('utf-8')}


def stand(objs):
    return lambda repo, args, timeout: {'exit': 0, 'out': objs[args[2]], 'err': b'', 'error': None}


class AC8Properties(unittest.TestCase):

    def test_read_gives_the_template_lists(self):
        """TASK-071 AC8: "read" implies write_set and forbidden equal to the template's lists; "unreadable" implies the
        four fields None."""
        rng = random.Random(71)
        for _ in range(CASES):
            ws, fb = items(rng), items(rng)
            r = tc.parse_contract(template(ws, fb), 'TASK-071')
            if r['result'] == 'read':
                self.assertEqual((r['write_set'], r['forbidden']), (ws, fb))
            else:
                self.assertEqual([r['task'], r['base_commit'], r['write_set'], r['forbidden']], [None] * 4)

    def test_mutation_classes(self):
        """TASK-071 AC8: every parse-class mutation gives "parse", every task-class mutation "task", every
        skipped-class mutation leaves the result unchanged, every bytes-class mutation gives "bytes"."""
        rng = random.Random(710)
        for _ in range(CASES):
            ws, fb = items(rng), items(rng)
            t = template(ws, fb)
            base = tc.parse_contract(t, 'TASK-071')
            self.assertEqual(base['result'], 'read')
            m = rng.choice(PARSE_MUTATIONS)
            self.assertEqual(tc.parse_contract(m(t), 'TASK-071')['reason'], 'parse')
            self.assertEqual(tc.parse_contract(t.replace('TASK-071', 'TASK-%d' % rng.randint(100, 999)),
                                               'TASK-071')['reason'], 'task')
            self.assertEqual(tc.parse_contract(rng.choice(SKIP_MUTATIONS)(t), 'TASK-071'), base)
            r = tc.read_contract(str(pathlib.Path(__file__).resolve().parent), COMMIT, 'TASK-071',
                                 run=stand(objects(rng.choice(BYTES_MUTATIONS)(t))))
            self.assertEqual(r['reason'], 'bytes')

    def test_generated_trees(self):
        """TASK-071 AC8: over generated tree texts, unrelated well-formed entries leave "read"; a bad line gives
        "tree: line out of form"."""
        rng = random.Random(7100)
        root = str(pathlib.Path(__file__).resolve().parent)
        t = template(['src/x.py'], ['docs/**'])
        for _ in range(CASES):
            objs = objects(t)
            names = {'n%d.md' % rng.randint(0, 10 ** 6) for _ in range(rng.randint(0, 6))}
            extra = ''.join('100644 blob %s\t%s\n' % ('9' * 40, n) for n in sorted(names)).encode('utf-8')
            where = rng.choice([TREE, DOCS, TASKS])
            objs[where] = objs[where] + extra
            self.assertEqual(tc.read_contract(root, COMMIT, 'TASK-071', run=stand(objs))['result'], 'read')
            objs[where] = objs[where] + b'100644 blob short\tz\n'
            r = tc.read_contract(root, COMMIT, 'TASK-071', run=stand(objs))
            self.assertEqual(r['findings'], ['tree: line out of form'])

    def test_task_contract_properties_name_their_criteria(self):
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
