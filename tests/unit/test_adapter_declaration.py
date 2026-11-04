"""Unit tests of aieos_bootstrap.adapter_declaration and of claude_code_shell_allow.read_policy_text (task TASK-117 AC1
and AC2; specification 2 section 7.1 and section 10 point 12, reading R1 of D-4742). Git is a stand-in `run` passed as
the seam argument (no real Git, no process, no file); the module's source is read with inspect.getsource and parsed
with ast (no file is opened). Each test names its criteria ("TASK-117 AC1" or "TASK-117 AC2") in its own docstring."""

import ast
import inspect
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import adapter_declaration, claude_code_shell_allow as shell_allow

REPO = str(pathlib.Path(__file__).resolve().parents[2])
BASE = '1' * 40
TREE = '2' * 40
ATREE = '3' * 40
BLOB = '4' * 40
OTHER = '5' * 40
CONF = ('{runtime: claude-code, platform: windows-native, version: 2.1.309, settings: '
        'sha256:210052f28a574d4ffdd5ade5b53c4e85f8f10124b24831819523aa1739acc58f}')
ASSUR = '{preventive: none, runtime: none, posthoc: none}'
FIXTURE = ("# unmeasured and advisory: the runtime's tier rests on the owner's decision A74 (decision matrix), not on a "
           "measurement; written by the core's write_policy under task TASK-117\n"
           'adapters:\n'
           '  - adapter: claude-code\n'
           '    tier: T3\n'
           '    configuration: ' + CONF + '\n'
           '    capabilities: {}\n'
           '    assurance: ' + ASSUR + '\n'
           '    max_risk: low\n')
COMMIT = ('tree ' + TREE + '\nauthor a <a@b.c> 1 +0000\ncommitter a <a@b.c> 1 +0000\n\nmessage\n').encode('ascii')
SENTINEL = object()


def ok(out):
    return {'exit': 0, 'out': out, 'err': b'', 'error': None}


class World:
    """A stand-in `run`: a commit whose tree holds (or not) a state folder holding (or not) the policy file."""

    def __init__(self, policy=FIXTURE.encode('utf-8'), aieos=True, entry=True, mode='100644', kind='blob',
                 override=None, commit=COMMIT):
        root = ('040000 tree %s\t.aieos\n' % ATREE) if aieos else ('100644 blob %s\tREADME.md\n' % OTHER)
        state = ('%s %s %s\tproject.yaml\n' % (mode, kind, BLOB)) if entry else ('100644 blob %s\tother.yaml\n' % OTHER)
        self.objects = {BASE: commit, TREE: root.encode('ascii'), ATREE: state.encode('ascii'), BLOB: policy}
        self.override = override
        self.calls = []

    def __call__(self, repo, args, timeout=30):
        self.calls.append((repo, list(args), timeout))
        if self.override is not None:
            given = self.override(repo, args, timeout)
            if given is not None:
                return given
        return ok(self.objects[args[2]])


def item(adapter='claude-code', tier='T3', configuration=CONF, capabilities='{}', assurance=ASSUR, max_risk='low',
         measurement=None):
    lines = ['  - adapter: ' + adapter, '    tier: ' + tier, '    configuration: ' + configuration,
             '    capabilities: ' + capabilities, '    assurance: ' + assurance, '    max_risk: ' + max_risk]
    if measurement is not None:
        lines.append('    measurement: ' + measurement)
    return lines


def block(*items, top=()):
    lines = list(top) + ['adapters:']
    for it in items:
        lines.extend(it)
    return '\n'.join(lines) + '\n'


def declared(text, adapter='claude-code'):
    return adapter_declaration.declared_max_risk(text, adapter)


class TASK117AC1ReadPolicyText(unittest.TestCase):
    def run_read(self, world=None, repo=REPO, base=BASE):
        world = World() if world is None else world
        return shell_allow.read_policy_text(repo, base, world), world

    def assert_shape(self, out):
        self.assertEqual(set(out), {'result', 'text', 'findings'})

    def test_present(self):
        """TASK-117 AC1: a policy blob that passes the checks gives result present, text exactly the blob's text and no
        finding; the reads are git cat-file -p calls on the commit, its tree, the state folder's tree and the blob."""
        out, world = self.run_read()
        self.assert_shape(out)
        self.assertEqual((out['result'], out['text'], list(out['findings'])), ('present', FIXTURE, []))
        self.assertEqual([c[1] for c in world.calls], [['cat-file', '-p', o] for o in (BASE, TREE, ATREE, BLOB)])
        self.assertTrue(all(c[0] == REPO for c in world.calls))

    def test_absent_with_no_state_tree(self):
        """TASK-117 AC1: a root tree with no .aieos entry gives result absent (the base commit and the root tree were
        read, no refusal); it is not a refusal."""
        out, world = self.run_read(World(aieos=False))
        self.assert_shape(out)
        self.assertEqual(out['result'], 'absent')
        self.assertEqual([c[1][2] for c in world.calls], [BASE, TREE])

    def test_absent_with_the_tree_and_no_file(self):
        """TASK-117 AC1: a .aieos tree with no project.yaml entry gives result absent."""
        out, world = self.run_read(World(entry=False))
        self.assert_shape(out)
        self.assertEqual(out['result'], 'absent')
        self.assertEqual([c[1][2] for c in world.calls], [BASE, TREE, ATREE])

    def test_refused_for_a_git_error(self):
        """TASK-117 AC1: each of the git-error findings of the reused call (result shape, error, exit not an int, exit N,
        out not bytes, run raised <type name>) gives result refused, empty text and exactly that finding."""
        cases = (({'exit': 0}, 'git: result shape'),
                 ({'exit': 0, 'out': b'', 'err': b'', 'error': 'boom'}, 'git: error'),
                 ({'exit': '0', 'out': b'', 'err': b'', 'error': None}, 'git: exit not an int'),
                 ({'exit': 1, 'out': b'', 'err': b'', 'error': None}, 'git: exit 1'),
                 ({'exit': 0, 'out': 'text', 'err': b'', 'error': None}, 'git: out not bytes'))
        for answer, finding in cases:
            with self.subTest(finding=finding):
                out, _ = self.run_read(World(override=lambda repo, args, timeout, a=answer: a))
                self.assert_shape(out)
                self.assertEqual((out['result'], out['text'], list(out['findings'])), ('refused', '', [finding]))

        def boom(repo, args, timeout):
            raise RuntimeError('x')

        out, _ = self.run_read(World(override=boom))
        self.assertEqual((out['result'], out['text'], list(out['findings'])),
                         ('refused', '', ['git: run raised RuntimeError']))

    def test_refused_for_a_git_error_at_each_read(self):
        """TASK-117 AC1: a git error at the commit, the root tree, the state folder's tree or the blob read gives
        refused (not absent) with empty text."""
        for oid in (BASE, TREE, ATREE, BLOB):
            with self.subTest(oid=oid):
                world = World(override=lambda repo, args, timeout, o=oid: (
                    {'exit': 1, 'out': b'', 'err': b'', 'error': None} if args[2] == o else None))
                out, _ = self.run_read(world)
                self.assertEqual((out['result'], out['text']), ('refused', ''))
                self.assertEqual(list(out['findings']), ['git: exit 1'])

    def test_refused_for_a_commit_that_is_out_of_form(self):
        """TASK-117 AC1 (reading R1 of D-4742): a refusal at the base commit keeps the module's own fixed finding
        unchanged: a commit text with no tree line gives refused, empty text and "git: commit out of form"."""
        out, _ = self.run_read(World(commit=b'author x\n\nmessage\n'))
        self.assertEqual((out['result'], out['text'], list(out['findings'])),
                         ('refused', '', ['git: commit out of form']))

    def test_refused_for_an_entry_that_is_not_a_regular_blob(self):
        """TASK-117 AC1: a project.yaml entry that is a tree, or a blob of another mode, gives refused with empty text
        and one finding."""
        for mode, kind in (('040000', 'tree'), ('100755', 'blob'), ('120000', 'blob')):
            with self.subTest(mode=mode):
                out, _ = self.run_read(World(mode=mode, kind=kind))
                self.assert_shape(out)
                self.assertEqual((out['result'], out['text']), ('refused', ''))
                self.assertEqual(list(out['findings']), ['tree: policy not a 100644 blob'])

    def test_refused_for_each_byte_check(self):
        """TASK-117 AC1: a blob that is above 1 MiB, not UTF-8, holds U+FEFF, a C0 control but LF (tab and CR among them),
        DEL, a C1 control, U+2028 or U+2029 gives refused, empty text and one finding."""
        control = 'bytes: control character'
        bad = {'over the cap': (b'a' * ((1 << 20) + 1), 'bytes: over the cap'),
               'not UTF-8': (b'a\xff\n', 'bytes: not UTF-8'),
               'BOM': ('a\ufeff\n'.encode('utf-8'), 'bytes: byte-order mark'),
               'NUL': (b'a\x00\n', control), 'tab': (b'a\tb\n', control), 'CR': (b'a\r\n', control),
               'DEL': (b'a\x7f\n', control), 'C1': ('a\u0085\n'.encode('utf-8'), control),
               'U+2028': ('a\u2028\n'.encode('utf-8'), control), 'U+2029': ('a\u2029\n'.encode('utf-8'), control)}
        for name, (blob, finding) in bad.items():
            with self.subTest(name=name):
                out, _ = self.run_read(World(policy=blob))
                self.assert_shape(out)
                self.assertEqual((out['result'], out['text']), ('refused', ''))
                self.assertEqual(list(out['findings']), [finding])

    def test_a_blob_of_exactly_one_mib_passes_the_size_check(self):
        """TASK-117 AC1: a blob of exactly 1 MiB of ASCII is present (at most 1 MiB)."""
        out, _ = self.run_read(World(policy=b'a' * (1 << 20)))
        self.assertEqual(out['result'], 'present')

    def test_refused_for_a_bad_repo(self):
        """TASK-117 AC1: a repo that is not a str, is empty or fails gitread.form_error gives refused, empty text, the
        finding "argument: repo" and no git call."""
        for repo in (None, 3, b'x', ''):
            with self.subTest(repo=repo):
                world = World()
                out = shell_allow.read_policy_text(repo, BASE, world)
                self.assert_shape(out)
                self.assertEqual((out['result'], out['text'], list(out['findings'])),
                                 ('refused', '', ['argument: repo']))
                self.assertEqual(world.calls, [])

    def test_refused_for_a_bad_base(self):
        """TASK-117 AC1: a base that is not a str or is not an object id gives refused, empty text, the finding
        "argument: base" and no git call."""
        for base in (None, 3, b'x', '', 'abc', 'G' * 40, '1' * 41):
            with self.subTest(base=base):
                world = World()
                out = shell_allow.read_policy_text(REPO, base, world)
                self.assertEqual((out['result'], out['text'], list(out['findings'])),
                                 ('refused', '', ['argument: base']))
                self.assertEqual(world.calls, [])

    def test_it_never_raises_for_the_run_seam(self):
        """TASK-117 AC1: whatever the seam answers, read_policy_text returns a mapping and raises nothing."""
        for answer in (None, 3, [], {'exit': 0, 'out': b'', 'err': b'', 'error': None, 'x': 1}):
            with self.subTest(answer=repr(answer)):
                out = shell_allow.read_policy_text(REPO, BASE, lambda repo, args, timeout, a=answer: a)
                self.assertEqual(out['result'], 'refused')

    def test_the_adapters_block_does_not_change_the_shell_allow_list(self):
        """TASK-117 AC1 (D-4737 (d)): a policy text with a top-level adapters: block before the shell_allow items, and
        one after them, gives the same parse_policy list as without it."""
        plain = 'shell_allow:\n  - git status\n  - git log\n'
        self.assertEqual(shell_allow.parse_policy(plain), ['git status', 'git log'])
        adapters = FIXTURE
        self.assertEqual(shell_allow.parse_policy(adapters + plain), ['git status', 'git log'])
        self.assertEqual(shell_allow.parse_policy(plain + adapters), ['git status', 'git log'])

    def test_an_indented_adapters_line_among_the_items_gives_the_empty_list(self):
        """TASK-117 AC1 (D-4737 (d)): a text with an INDENTED line "  adapters:" among the shell_allow items makes
        parse_policy return the empty list."""
        text = 'shell_allow:\n  - git status\n  adapters:\n  - git log\n'
        self.assertEqual(shell_allow.parse_policy(text), [])

    def test_its_docstring_names_the_second_caller(self):
        """TASK-117 AC1: the module docstring of claude_code_shell_allow names adapter_declaration.read_declaration as
        the second caller, and no longer says that its one caller is claude_code_pretool_hook."""
        doc = ' '.join(shell_allow.__doc__.split())
        self.assertIn('adapter_declaration', doc)
        self.assertNotIn('Its one caller is claude_code_pretool_hook', doc)


class TASK117AC2Grammar(unittest.TestCase):
    def check(self, text, result, max_risk=None, adapter='claude-code'):
        out = declared(text, adapter)
        self.assertEqual(set(out), {'result', 'max_risk', 'findings'}, out)
        self.assertEqual((out['result'], out['max_risk']), (result, max_risk), out)
        if result == 'error':
            self.assertTrue(out['findings'], out)
        return out

    def error(self, text, **kw):
        return self.check(text, 'error', **kw)

    def low(self, text, **kw):
        return self.check(text, 'low', 'low', **kw)

    def test_the_fixture_gives_low_for_claude_code_and_none_for_another_id(self):
        """TASK-117 AC2: exactly the fixture text of AC6 gives low for claude-code and none for any other id."""
        self.low(FIXTURE)
        self.check(FIXTURE, 'none', adapter='codex')
        self.check(FIXTURE, 'none', adapter='claude')

    def test_grammar_text_equals_its_quoted_docstring_text(self):
        """TASK-117 AC2: ADAPTERS_GRAMMAR is a non-empty module constant that names the rules g1 to g10, and its text
        occurs, whitespace folded, in the module docstring."""
        grammar = adapter_declaration.ADAPTERS_GRAMMAR
        self.assertIsInstance(grammar, str)
        self.assertGreater(len(grammar), 200)
        for n in range(1, 11):
            self.assertIn('(g%d)' % n, grammar)
        self.assertIn(' '.join(grammar.split()), ' '.join(adapter_declaration.__doc__.split()))
        quoted = adapter_declaration.__doc__.split('GRAMMAR BEGIN\n', 1)[1].split('\nGRAMMAR END', 1)[0]
        self.assertEqual(grammar, quoted)

    def test_g1_blank_and_comment_lines_are_skipped(self):
        """TASK-117 AC2 g1: blank lines, lines of spaces and comment lines (the first non-space character #), indented
        ones among them, are skipped inside the block as outside it."""
        lines = item()
        text = '\n'.join(['# top', '', 'adapters:'] + lines[:2] + ['', '      # indented comment', '   '] + lines[2:]) + '\n'
        self.low(text)

    def test_g1_a_comment_after_a_value_is_part_of_the_value(self):
        """TASK-117 AC2 g1: only a whole line is a comment; "max_risk: low # c" is not "low" and gives error."""
        lines = item()
        lines[-1] = lines[-1] + ' # c'
        self.error(block(lines))

    def test_g2_other_top_level_keys_are_ignored_and_no_block_gives_none(self):
        """TASK-117 AC2 g2: top-level lines of other keys are ignored; no adapters: line gives none; an adapters: line
        followed at once by the next top-level line (an empty block), or by nothing, gives none."""
        self.low(block(item(), top=('shell_allow:', '  - git status', 'policy_version: 1')))
        self.check('shell_allow:\n  - git status\n', 'none')
        self.check('adapters:\nshell_allow:\n  - git status\n', 'none')
        self.check('adapters:\n', 'none')
        self.check('', 'none')

    def test_g2_a_second_or_inexact_adapters_line_gives_error(self):
        """TASK-117 AC2 g2: a second adapters: line, or a top-level line that begins with adapters: and is not exactly
        that, gives error."""
        self.error(block(item()) + 'adapters:\n')
        self.error('adapters: []\n')
        self.error(block(item(), top=('adapters:x',)))

    def test_g2_the_block_ends_at_the_next_top_level_line(self):
        """TASK-117 AC2 g2: items after a following top-level key do not belong to the block; an item before it does."""
        text = block(item(adapter='claude-code')) + 'other:\n' + '\n'.join(item(adapter='second')) + '\n'
        self.low(text)
        self.check(text, 'none', adapter='second')
        self.low(block(item(adapter='claude-code')) + 'other: x\n')

    def test_g3_item_and_key_lines_have_exact_indentation(self):
        """TASK-117 AC2 g3: an item line is two spaces, "- ", "adapter: <id>"; a key line is four spaces, the key, ": " and
        the value; the value may hold ": " (the key is the text before the FIRST ": ")."""
        lines = item(measurement='note: a: b')
        self.low(block(lines))
        for bad in (['   - adapter: claude-code'] + item()[1:], [' - adapter: claude-code'] + item()[1:]):
            self.error(block(bad))
        for i in range(1, 6):
            wrong = item()
            wrong[i] = ' ' + wrong[i]
            self.error(block(wrong))
            wrong[i] = wrong[i][2:]
            self.error(block(wrong))

    def test_g3_a_key_line_before_the_first_item_gives_error(self):
        """TASK-117 AC2 g3: a key line that comes before the first item line of the block gives error; so does any
        other shape (an item whose first key is not adapter, a line with no ": ")."""
        self.error(block(item()[1:], item()))
        self.error(block(['  - tier: T3'] + item()[1:]))
        self.error(block(item() + ['    stray']))
        self.error(block(item() + ['  plain words']))

    def test_g4_the_keys_in_exact_order_and_measurement_optional(self):
        """TASK-117 AC2 g4: the keys are adapter, tier, configuration, capabilities, assurance, max_risk and then
        optionally measurement, in that order; a missing, repeated, unknown or misordered key gives error."""
        self.low(block(item()))
        self.low(block(item(measurement='anything')))
        base = item()
        for i in range(1, 6):
            self.error(block(base[:i] + base[i + 1:]))
        self.error(block(base + [base[3]]))
        self.error(block(base + ['    unknown: x']))
        swapped = list(base)
        swapped[1], swapped[2] = swapped[2], swapped[1]
        self.error(block(swapped))
        self.error(block(item(measurement='m') + ['    measurement: n']))
        misplaced = list(base[:5]) + ['    measurement: m', base[5]]
        self.error(block(misplaced))

    def test_g5_values_are_bare_scalars_in_their_sets(self):
        """TASK-117 AC2 g5: adapter is a lowercase ASCII word or words joined by single hyphens; tier is T0 to T4;
        max_risk is low, medium, high or critical; no quotes; measurement is a non-empty rest of the line."""
        for tier in ('T0', 'T1', 'T2', 'T3', 'T4'):
            self.low(block(item(tier=tier)))
        for risk in ('low', 'medium', 'high', 'critical'):
            self.low(block(item(max_risk=risk)))
        self.low(block(item(adapter='a-b-c')), adapter='a-b-c')
        for tier in ('T5', 't3', '', 'T3 ', '"T3"'):
            self.error(block(item(tier=tier)))
        for risk in ('extreme', 'Low', '', '"low"', "'low'"):
            self.error(block(item(max_risk=risk)))
        for name in ('Claude', 'a--b', '-a', 'a-', 'a_b', 'a b', '', '"x"'):
            self.error(block(item(adapter=name)))
        lines = item()
        self.error(block(lines + ['    measurement: ']))
        self.error(block(lines + ['    measurement:']))

    def test_g6_the_configuration_flow_map(self):
        """TASK-117 AC2 g6: configuration is {runtime: S, platform: S, version: S, settings: S}, written with the exact
        separators, the four keys in that order, S a non-empty string of [A-Za-z0-9._:/+-]."""
        good = '{runtime: r, platform: p, version: 1.0, settings: a/b:c+d-e_f.g}'
        self.low(block(item(configuration=good)))
        for bad in ('{platform: p, runtime: r, version: 1, settings: s}', '{runtime: r, platform: p, version: 1}',
                    '{runtime: r, platform: p, version: 1, settings: s, extra: x}',
                    '{runtime: r,platform: p, version: 1, settings: s}',
                    '{runtime:r, platform: p, version: 1, settings: s}',
                    '{ runtime: r, platform: p, version: 1, settings: s}',
                    '{runtime: r, platform: p, version: 1, settings: s }',
                    '{runtime: r, platform: p, version: 1, settings: }',
                    '{runtime: r, platform: p, version: 1, settings: a b}',
                    '{runtime: r, platform: p, version: 1, settings: a$b}',
                    '{runtime: r, platform: p, version: 1, settings: "s"}',
                    'runtime: r', '{runtime: r, platform: p, version: 1, settings: s', ''):
            with self.subTest(bad=bad):
                self.error(block(item(configuration=bad)))

    def test_g7_the_capabilities_flow_map(self):
        """TASK-117 AC2 g7: capabilities is {} or {name: true, name: false} with the same separators, names
        [a-z][a-z0-9_]* each once, values true or false."""
        for good in ('{}', '{read: true}', '{read_all: true, w2: false}'):
            with self.subTest(good=good):
                self.low(block(item(capabilities=good)))
        for bad in ('{read: true, read: false}', '{Read: true}', '{1a: true}', '{read: yes}', '{read:true}',
                    '{read: true,write: false}', '{ }', '{read: true, }', '[]', '', '{read: True}'):
            with self.subTest(bad=bad):
                self.error(block(item(capabilities=bad)))

    def test_g8_the_assurance_flow_map(self):
        """TASK-117 AC2 g8: assurance is {preventive: X, runtime: X, posthoc: X} in that order, X one of none, weak,
        strong."""
        for x in ('none', 'weak', 'strong'):
            self.low(block(item(assurance='{preventive: %s, runtime: %s, posthoc: %s}' % (x, x, x))))
        for bad in ('{runtime: none, preventive: none, posthoc: none}', '{preventive: high, runtime: none, posthoc: none}',
                    '{preventive: none, runtime: none}', '{preventive: none, runtime: none, posthoc: none, x: none}',
                    '{preventive: None, runtime: none, posthoc: none}', '{}'):
            with self.subTest(bad=bad):
                self.error(block(item(assurance=bad)))

    def test_g9_a_repeated_adapter_id_gives_error_for_the_whole_block(self):
        """TASK-117 AC2 g9: an adapter id that occurs in two items gives error for the whole block, also when another id
        is asked for; two different ids give low and none."""
        text = block(item(adapter='claude-code'), item(adapter='claude-code', tier='T4'))
        self.error(text)
        self.error(text, adapter='codex')
        two = block(item(adapter='claude-code'), item(adapter='codex'))
        self.low(two)
        self.low(two, adapter='codex')
        self.check(two, 'none', adapter='third')

    def test_g10_characters_in_the_block_lines(self):
        """TASK-117 AC2 g10: a CR, a tab or any character outside printable ASCII and LF in the block lines gives
        error; the bytes outside the block are checked on the read path, not by the grammar."""
        for bad in ('\r', '\t', '\u00e9', '\u2028', '\x7f', '\x00'):
            with self.subTest(bad=repr(bad)):
                lines = item(measurement='m' + bad + 'n')
                self.error(block(lines))
        self.low('# caf\u00e9 outside the block\n' + block(item()))

    def test_g2_a_tab_led_item_line_gives_error(self):
        """TASK-117 AC2 g2/g3/g10: a line in the block that starts with a tab is a line of the block (not another
        top-level key that ends it) and, with its tab, gives error."""
        self.error(block(item(), ['\t  - adapter: codex', '    tier: T3']))

    def test_g2_a_tab_led_repeated_id_gives_error(self):
        """TASK-117 AC2 g9/g10: an item led by a tab that repeats an adapter id gives error (it must not be dropped as
        another key and leave the first item to read low)."""
        self.error(block(item(), ['\t  - adapter: claude-code', '    tier: T4']))

    def test_g2_an_nbsp_led_line_in_the_block_gives_error(self):
        """TASK-117 AC2 g2/g10: a line led by U+00A0 is not a line that starts with a non-space: it belongs to the
        block, and its character outside printable ASCII gives error."""
        self.error(block(item(), ['   - adapter: codex', '    tier: T3']))

    def test_g2_an_nbsp_led_repeated_id_after_a_valid_item_gives_error(self):
        """TASK-117 AC2 g9/g10: a U+00A0-led item after a valid item that repeats its id gives error, whichever id is
        asked for."""
        text = block(item(), ['   - adapter: claude-code', '    tier: T4'])
        self.error(text)
        self.error(text, adapter='codex')

    def test_a_well_formed_block_never_reads_above_low(self):
        """TASK-117 AC2: whatever tier and assurance the item states within the sets, and even when its max_risk is
        critical or it has a measurement key, the result is low with max_risk "low" (never above low, no measurement
        resolves); another id gives none."""
        text = block(item(tier='T4', max_risk='critical', assurance='{preventive: strong, runtime: strong, posthoc: '
                                                                    'strong}', measurement='sha256:abc'))
        self.low(text)
        self.check(text, 'none', adapter='other')

    def test_a_bad_adapter_argument_gives_error(self):
        """TASK-117 AC2: an adapter argument that is not a lowercase ASCII word or words joined by single hyphens
        gives error, whatever the text."""
        for adapter in (None, 3, b'x', '', 'Claude', 'a--b', '-a', 'a-', 'a_b', 'a b', 'claude-code\n'):
            with self.subTest(adapter=adapter):
                self.error(FIXTURE, adapter=adapter)

    def test_a_text_that_is_not_a_str_gives_error_or_none_never_a_raise(self):
        """TASK-117 AC2: declared_max_risk raises nothing for any text; a non-str text gives error."""
        for text in (None, 3, b'adapters:\n', []):
            with self.subTest(text=repr(text)):
                self.error(text)


class TASK117AC2ReadDeclaration(unittest.TestCase):
    def read(self, world=None, adapter='claude-code', run=SENTINEL):
        world = World() if world is None else world
        out = adapter_declaration.read_declaration(REPO, BASE, adapter, world if run is SENTINEL else run)
        self.assertEqual(set(out), {'result', 'max_risk', 'findings'}, out)
        return out, world

    def test_its_signature(self):
        """TASK-117 AC2: read_declaration(repo, base, adapter, run=None)."""
        sig = inspect.signature(adapter_declaration.read_declaration)
        self.assertEqual(list(sig.parameters), ['repo', 'base', 'adapter', 'run'])
        self.assertIsNone(sig.parameters['run'].default)

    def test_present_with_an_item_gives_low(self):
        """TASK-117 AC2: a present policy with an item for the adapter gives result low, max_risk "low" and no
        finding."""
        out, _ = self.read()
        self.assertEqual((out['result'], out['max_risk'], list(out['findings'])), ('low', 'low', []))

    def test_present_with_no_adapters_line_gives_absent(self):
        """TASK-117 AC2: a present policy with no adapters: line gives result absent and max_risk None."""
        out, _ = self.read(World(policy=b'shell_allow:\n  - git status\n'))
        self.assertEqual((out['result'], out['max_risk']), ('absent', None))

    def test_present_with_no_item_for_the_adapter_gives_absent(self):
        """TASK-117 AC2: a present policy whose items are for other adapters gives result absent and max_risk None."""
        out, _ = self.read(adapter='codex')
        self.assertEqual((out['result'], out['max_risk']), ('absent', None))

    def test_an_absent_file_gives_absent(self):
        """TASK-117 AC2: no .aieos tree, or no project.yaml, at the base gives result absent and max_risk None (the
        existing path to check 7)."""
        for world in (World(aieos=False), World(entry=False)):
            with self.subTest(world=world.objects[TREE]):
                out, _ = self.read(world)
                self.assertEqual((out['result'], out['max_risk']), ('absent', None))

    def test_a_refusal_of_the_base_read_passes_through(self):
        """TASK-117 AC2: a refused base read gives result refused, max_risk None and the base read's own findings."""
        world = World(override=lambda repo, args, timeout: {'exit': 1, 'out': b'', 'err': b'', 'error': None})
        out, _ = self.read(world)
        self.assertEqual((out['result'], out['max_risk'], list(out['findings'])), ('refused', None, ['git: exit 1']))

    def test_a_malformed_block_gives_error(self):
        """TASK-117 AC2: a malformed block, or a repeated adapter id, gives result error and max_risk None, with
        findings."""
        for policy in (block(item(tier='T9')).encode('ascii'),
                       block(item(), item(tier='T4')).encode('ascii')):
            with self.subTest(policy=policy[:30]):
                out, _ = self.read(World(policy=policy))
                self.assertEqual((out['result'], out['max_risk']), ('error', None))
                self.assertTrue(out['findings'])

    def test_an_nbsp_led_line_in_the_block_gives_error_through_read_declaration(self):
        """TASK-117 AC2 g2/g9/g10: through the real read path (a stand-in run serving the text as present), a block
        with a U+00A0-led item that repeats the adapter id gives result error, max_risk None and findings, never low."""
        policy = block(item(), ['   - adapter: claude-code', '    tier: T4']).encode('utf-8')
        out, _ = self.read(World(policy=policy))
        self.assertEqual((out['result'], out['max_risk']), ('error', None))
        self.assertTrue(out['findings'])

    def test_repo_base_and_run_reach_read_policy_text_unchanged(self):
        """TASK-117 AC2: read_declaration passes repo, base and run to claude_code_shell_allow.read_policy_text
        unchanged (the same objects), once."""
        seen = []
        sig = inspect.signature(shell_allow.read_policy_text)

        def fake(*args, **kwargs):
            seen.append(sig.bind(*args, **kwargs).arguments)
            return {'result': 'present', 'text': FIXTURE, 'findings': []}

        run = object()
        repo, base = 'C:/another-repo', '6' * 40
        with mock.patch.object(shell_allow, 'read_policy_text', fake):
            out = adapter_declaration.read_declaration(repo, base, 'claude-code', run)
        self.assertEqual(out['result'], 'low')
        self.assertEqual(len(seen), 1)
        self.assertEqual(dict(seen[0]), {'repo': repo, 'base': base, 'run': run})
        self.assertIs(seen[0]['run'], run)

    def test_the_default_run_is_none(self):
        """TASK-117 AC2: with no run given, read_policy_text is called with run None (the real Git reader is its
        default)."""
        seen = []
        sig = inspect.signature(shell_allow.read_policy_text)

        def fake(*args, **kwargs):
            seen.append(dict(sig.bind(*args, **kwargs).arguments))
            return {'result': 'absent', 'text': '', 'findings': []}

        with mock.patch.object(shell_allow, 'read_policy_text', fake):
            out = adapter_declaration.read_declaration(REPO, BASE, 'claude-code')
        self.assertEqual(out['result'], 'absent')
        self.assertIsNone(seen[0].get('run'))

    def test_a_bad_adapter_gives_error_with_no_git_call(self):
        """TASK-117 AC2: the adapter argument is checked first, before any read: a bad one gives result error, max_risk
        None and no git call, also when the repo and the base are bad too."""
        for adapter in (None, 'Claude', 'a--b', ''):
            with self.subTest(adapter=adapter):
                world = World()
                out = adapter_declaration.read_declaration(REPO, BASE, adapter, world)
                self.assertEqual((out['result'], out['max_risk']), ('error', None))
                self.assertEqual(world.calls, [])
                world = World()
                out = adapter_declaration.read_declaration(None, 'x', adapter, world)
                self.assertEqual((out['result'], out['max_risk']), ('error', None))
                self.assertEqual(world.calls, [])


class TASK117AC2TheModule(unittest.TestCase):
    def tree(self):
        return ast.parse(inspect.getsource(adapter_declaration))

    def test_it_names_no_state_folder_anywhere(self):
        """TASK-117 AC2: no string constant of adapter_declaration.py, its docstrings included, holds the name of the
        project-state directory (the CI string rule), and no comment does."""
        source = inspect.getsource(adapter_declaration)
        state = '.' + 'aieos'
        self.assertNotIn(state, source)
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertNotIn(state, node.value)

    def test_it_imports_nothing_that_opens_or_runs(self):
        """TASK-117 AC2: adapter_declaration imports claude_code_shell_allow and nothing that opens a file or starts a
        process (no os, io, pathlib, subprocess, tempfile, shutil, sqlite3, importlib, builtins or gitread import),
        calls no open and uses no open name."""
        imported = set()
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or '')
                imported.update((node.module or '') + '.' + a.name for a in node.names)
        self.assertTrue(any(name.endswith('claude_code_shell_allow') for name in imported), imported)
        for denied in ('os', 'io', 'pathlib', 'subprocess', 'tempfile', 'shutil', 'sqlite3', 'importlib', 'builtins',
                       'aieos_bootstrap.gitread'):
            self.assertNotIn(denied, imported)
        names = {n.id for n in ast.walk(self.tree()) if isinstance(n, ast.Name)}
        self.assertNotIn('open', names)
        attrs = {n.func.attr for n in ast.walk(self.tree()) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute)}
        for denied in ('open', 'write_text', 'write_bytes', 'mkdir', 'touch'):
            self.assertNotIn(denied, attrs)

    def test_its_public_names(self):
        """TASK-117 AC2: the module defines ADAPTERS_GRAMMAR, declared_max_risk and read_declaration."""
        for name in ('ADAPTERS_GRAMMAR', 'declared_max_risk', 'read_declaration'):
            self.assertTrue(hasattr(adapter_declaration, name), name)

    def test_every_test_of_this_module_names_its_criteria(self):
        """TASK-117 AC2: every test of this module names "TASK-117 AC1" or "TASK-117 AC2" in its own docstring."""
        tree = ast.parse(inspect.getsource(inspect.getmodule(type(self))))
        tests = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        self.assertGreater(len(tests), 40)
        for node in tests:
            doc = ast.get_docstring(node) or ''
            self.assertTrue('TASK-117 AC1' in doc or 'TASK-117 AC2' in doc, node.name)


if __name__ == '__main__':
    unittest.main()
