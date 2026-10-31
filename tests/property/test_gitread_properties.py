"""Property tests of aieos_bootstrap.gitread (task TASK-024, rule R1 and the parsers), standard library only, with
fixed seeds. Argument lists made out of the pinned forms by an insertion, a removal or a replacement are always refused
without a call to the process function; random well-formed commit and path bytes round-trip through the parsers. Each
test names its criteria in its own docstring."""

import pathlib
import random
import unittest
from unittest import mock

from aieos_bootstrap import gitread

REPO = str(pathlib.Path(__file__).resolve().parents[2])
SEEDS = (1, 2, 3, 5, 8, 13, 21, 34)
ROUNDS = 40
HEXD = '0123456789abcdef'
TOKENS = ['--all', '-p', '-t', '--', 'HEAD', 'main', '-n', '2', '--exec', '!sh', '--output=x', 'x', '', 'A' * 40]
NAME_CHARS = 'abcxyz019_-./ é'


def oid(rng):
    return ''.join(rng.choice(HEXD) for _ in range(rng.choice((40, 64))))


def pinned(rng):
    k = rng.randrange(5)
    if k == 0:
        return ['rev-parse', '--verify', '--end-of-options', rng.choice(['HEAD', oid(rng)])]
    if k == 1:
        return ['cat-file', rng.choice(['-p', '-t']), oid(rng)]
    if k == 2:
        return ['rev-list', '--parents', '-n', '1', oid(rng)]
    return ['diff-tree', '--no-commit-id', '--name-only', '-r', '--no-renames', '--no-ext-diff', '--no-textconv', '-z',
            '--root', oid(rng)]


def broken(rng):
    """A pinned form made invalid by construction: a token inserted or removed (the length is fixed per subcommand),
    a fixed token replaced by another, or the object name replaced by a non-id token."""
    a = pinned(rng)
    k = rng.randrange(4)
    if k == 0:
        a.insert(rng.randrange(1, len(a) + 1), rng.choice(TOKENS + [oid(rng)]))
    elif k == 1:
        del a[rng.randrange(len(a))]
    elif k == 2:
        i = rng.randrange(len(a) - 1)
        a[i] = rng.choice([t for t in TOKENS
                           if t != a[i] and not (i == 1 and a[0] == 'cat-file' and t in ('-p', '-t'))])
    else:
        a[-1] = rng.choice([t for t in TOKENS if t != 'HEAD'])
    return a


class Calls:
    def __init__(self):
        self.n = 0

    def __call__(self, *args, **kwargs):
        self.n += 1
        raise AssertionError('no process may start here')


class BranchRefProperties(unittest.TestCase):
    def test_the_base_name_rule_and_the_form_agree(self):
        """TASK-024 AC1: for random names over letters, digits, ".", "_", "-", "/", a space and a non-ASCII letter, the
        pinned rev-parse form with refs/heads/ and the name has no form error exactly when is_base_name accepts the name,
        and every accepted name is 1 to 100 ASCII characters whose parts are non-empty, begin with a letter or a digit,
        do not end in "." or ".lock" and hold no "..", with none of the refused characters."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS * 5):
                name = ''.join(rng.choice(NAME_CHARS) for _ in range(rng.randrange(0, 14)))
                ok = gitread.is_base_name(name)
                err = gitread.form_error(REPO, ['rev-parse', '--verify', '--end-of-options', 'refs/heads/' + name], 30)
                self.assertEqual(err is None, ok, name)
                if ok:
                    self.assertTrue(1 <= len(name) <= 100 and name.isascii(), name)
                    self.assertNotIn('..', name)
                    for part in name.split('/'):
                        self.assertTrue(part and part[0].isalnum(), name)
                        self.assertFalse(part.endswith('.') or part.endswith('.lock'), name)
                    self.assertFalse(set(name) & set(' é'), name)

    def test_a_name_that_is_not_a_base_name_is_never_a_branch_ref_form(self):
        """TASK-024 AC1 and TASK-024 AC12: a broken ref name (a prefix other than refs/heads/, or the prefix with a
        character from an unsafe set) is refused by the form check and never starts a process."""
        c = Calls()
        with mock.patch.object(gitread.subprocess, 'run', c):
            for seed in SEEDS:
                rng = random.Random(seed)
                for _ in range(ROUNDS):
                    bad = rng.choice(['refs/tags/', 'refs/remotes/', 'heads/', 'refs/heads//', 'refs/head/']) + 'main'
                    r = gitread.run(REPO, ['rev-parse', '--verify', '--end-of-options', bad])
                    self.assertTrue(r['error'], bad)
                    bad2 = 'refs/heads/' + rng.choice(['a', 'b/c']) + rng.choice(['..', ' ', '\n', ':', '~', '^', '?', '*', '[', '\\', '@{'])
                    r2 = gitread.run(REPO, ['rev-parse', '--verify', '--end-of-options', bad2])
                    self.assertTrue(r2['error'], bad2)
        self.assertEqual(c.n, 0)


class Forms(unittest.TestCase):
    def test_broken_forms_are_refused_without_a_call(self):
        """TASK-024 AC1 and TASK-024 AC12: every argument list made out of a pinned form by an insertion, a removal or a
        replacement is refused, and the process function is never called."""
        c = Calls()
        with mock.patch.object(gitread.subprocess, 'run', c):
            for seed in SEEDS:
                rng = random.Random(seed)
                for _ in range(ROUNDS):
                    a = broken(rng)
                    r = gitread.run(REPO, a)
                    self.assertTrue(r['error'], a)
                    self.assertEqual((r['exit'], r['out'], r['err']), (None, b'', b''))
        self.assertEqual(c.n, 0)

    def test_random_pinned_forms_are_accepted(self):
        """TASK-024 AC1 and TASK-024 AC12: every random pinned form is accepted (no form error)."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                a = pinned(rng)
                self.assertIsNone(gitread.form_error(REPO, a, rng.choice((1, 30, 120))), a)


def name(rng):
    return ''.join(rng.choice(NAME_CHARS) for _ in range(rng.randint(1, 12)))


class Parsers(unittest.TestCase):
    def test_commit_round_trip(self):
        """TASK-024 AC4 and TASK-024 AC12: random well-formed commit bytes parse back to their values, trailers
        included."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                tree = oid(rng)
                parents = [oid(rng) for _ in range(rng.randint(0, 3))]
                author = 'A%d <a%d> %d +0700' % (rng.randint(0, 9), rng.randint(0, 9), rng.randint(0, 10 ** 9))
                committer = 'C%d <c> %d -0100' % (rng.randint(0, 9), rng.randint(0, 10 ** 9))
                pairs = [['K%s-%d' % (rng.choice('abc'), i), 'value %d' % rng.randint(0, 99)]
                         for i in range(rng.randint(0, 3))]
                message = 'Subject %d\n\nBody text, line one.\n' % rng.randint(0, 99)
                if pairs:
                    message += '\n' + ''.join('%s: %s\n' % (k, v) for k, v in pairs)
                data = ('tree %s\n' % tree + ''.join('parent %s\n' % p for p in parents)
                        + 'author %s\ncommitter %s\n\n' % (author, committer) + message).encode('utf-8')
                p = gitread.parse_commit(data)
                self.assertEqual(p, {'tree': tree, 'parents': parents, 'author': author, 'committer': committer,
                                     'message': message, 'trailers': pairs, 'error': None})

    def test_paths_round_trip(self):
        """TASK-024 AC5 and TASK-024 AC12: random lists of non-empty names joined with NUL, with a final NUL, parse back
        in order."""
        for seed in SEEDS:
            rng = random.Random(seed)
            for _ in range(ROUNDS):
                names = [name(rng) for _ in range(rng.randint(0, 6))]
                data = b''.join(n.encode('utf-8') + b'\0' for n in names)
                self.assertEqual(gitread.parse_paths(data), {'paths': names, 'error': None})


if __name__ == '__main__':
    unittest.main()
