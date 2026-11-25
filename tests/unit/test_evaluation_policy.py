"""Unit tests of the reader of the evaluation policy file of TASK-153 (BT3c-1, AC1 to AC4 and AC6). Every case is built in
memory; the only file read is the module's own source. The values of the policy texts below are FIXTURES, not policy: no
test asserts that they are the repository's policy.
"""
import ast
import pathlib
import unittest

from aieos_bootstrap import eval_inputs
from aieos_bootstrap import evaluation_policy
from aieos_bootstrap import governor

ROOT = pathlib.Path(__file__).resolve().parents[2]
KEYS = ('owner_kept_rules', 'articles', 'default_profiles', 'requirement_profiles', 'delegation', 'auto_accept')
FENCE = '`' * 3
GOOD_LINES = [
    "owner_kept_rules:",
    "  - match: ['docs/a.md', docs/b/**]",
    "articles:",
    "  - id: INV-002",
    "    scope: [src/**]",
    "    evidence_required: [ai_review]",
    "default_profiles:",
    "  low:",
    "    - {dimension: functional, evidence_types: [build, lint]}",
    "  medium:",
    "    - {dimension: functional, evidence_types: [unit_test]}",
    "    - {dimension: architecture, evidence_types: [deterministic_rule]}",
    "requirement_profiles: []",
    "delegation: true",
    "auto_accept:",
    "  low: false",
    "  medium: false",
]


def make(lines=None, head='## 3. The sources', before='Prose before the block.', after='Prose after the block.'):
    body = GOOD_LINES if lines is None else lines
    return '\n'.join([before, '', head, '', FENCE + 'yaml'] + list(body) + [FENCE, '', after, ''])


def read(text):
    return evaluation_policy.read_evaluation_policy(text)


def reason(text):
    out = read(text)
    assert out['result'] == 'refused', out
    assert len(out['findings']) == 1
    assert out['sources'] == dict.fromkeys(KEYS), out
    return out['findings'][0]['reason']


def replace_line(old, new):
    return [new if x == old else x for x in GOOD_LINES]


class AC1TheModule(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / 'src/aieos_bootstrap/evaluation_policy.py').read_bytes().decode('utf-8')

    def test_public_names_and_imports(self):
        tree = ast.parse(self.source)
        public, imports = set(), set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith('_'):
                public.add(node.name)
            elif isinstance(node, ast.Assign):
                public.update(t.id for t in node.targets if isinstance(t, ast.Name) and not t.id.startswith('_'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module)
        self.assertEqual(public, {'read_evaluation_policy', 'EVIDENCE_DEFINING_PATHS'})
        self.assertEqual(imports, {'re'})
        attrs = {n for n in dir(evaluation_policy) if not n.startswith('_')}
        self.assertEqual(attrs, {'read_evaluation_policy', 'EVIDENCE_DEFINING_PATHS', 're'})

    def test_no_io_process_clock_or_environment_name_is_used(self):
        tree = ast.parse(self.source)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for forbidden in ('open', 'subprocess', 'os', 'time', 'environ', 'getenv', 'popen', 'system', 'read_text', 'read_bytes', 'sys'):
            self.assertNotIn(forbidden, names, forbidden)

    def test_the_answer_has_exactly_three_keys_and_six_sources(self):
        for text in (make(), make([]), 'x', ''):
            out = read(text)
            self.assertEqual(set(out), {'result', 'sources', 'findings'})
            self.assertEqual(set(out['sources']), set(KEYS))

    def test_never_raises_and_gives_a_result_for_odd_arguments(self):
        for arg in (None, 3, b'x', ['a'], {'a': 1}, object(), 'x' * 2000000, '\n' * 10000, ('## 3. The sources\n' + FENCE + 'yaml\n') * 5000):
            out = read(arg)
            self.assertIn(out['result'], ('present', 'refused'))
        big = make(GOOD_LINES + ['# ' + 'c' * 50] * 10000)
        self.assertEqual(read(big)['result'], 'present')
        self.assertEqual(reason(None), 'argument')
        self.assertEqual(read(None)['findings'][0]['line'], None)

    def test_the_text_is_not_changed_and_the_answer_is_fresh(self):
        text = make()
        a, b = read(text), read(text)
        self.assertEqual(a, b)
        a['sources']['articles'].append('x')
        self.assertNotIn('x', read(text)['sources']['articles'])


class AC2TheGrammar(unittest.TestCase):
    def test_the_good_block_is_read_as_a_whole_value(self):
        out = read(make())
        self.assertEqual(out['result'], 'present')
        self.assertEqual(out['findings'], [])
        self.assertEqual(out['sources'], {
            'owner_kept_rules': [{'match': ['docs/a.md', 'docs/b/**']}],
            'articles': [{'id': 'INV-002', 'scope': ['src/**'], 'evidence_required': ['ai_review']}],
            'default_profiles': {'low': [{'dimension': 'functional', 'evidence_types': ['build', 'lint']}],
                                 'medium': [{'dimension': 'functional', 'evidence_types': ['unit_test']},
                                            {'dimension': 'architecture', 'evidence_types': ['deterministic_rule']}]},
            'requirement_profiles': [],
            'delegation': True,
            'auto_accept': {'low': False, 'medium': False},
        })

    def test_the_text_outside_the_block_is_ignored(self):
        out = read(make(before='\t trailing   \r\n a tab', after='\u2603 anything # here\t'))
        self.assertEqual(out['result'], 'present')

    def test_blank_lines_and_comments_may_stand_between_any_two_lines(self):
        lines = []
        for x in GOOD_LINES:
            lines += ['', '# a comment', '   # an indented comment', x]
        self.assertEqual(read(make(lines)), read(make()))

    def test_requirement_profiles_with_entries(self):
        lines = replace_line('requirement_profiles: []', 'requirement_profiles:')
        i = lines.index('requirement_profiles:') + 1
        lines[i:i] = ['  - id: SPEC-001', '    add:', '      - {dimension: security, evidence_types: [static_security_analysis]}',
                      '  - id: SPEC-002', '    add:', '      - {dimension: functional, evidence_types: [a, b]}',
                      '      - {dimension: security, evidence_types: [c]}']
        out = read(make(lines))
        self.assertEqual(out['sources']['requirement_profiles'], [
            {'id': 'SPEC-001', 'add': [{'dimension': 'security', 'evidence_types': ['static_security_analysis']}]},
            {'id': 'SPEC-002', 'add': [{'dimension': 'functional', 'evidence_types': ['a', 'b']},
                                       {'dimension': 'security', 'evidence_types': ['c']}]}])

    def test_an_empty_evidence_required_list_is_accepted_and_gives_an_empty_list(self):
        out = read(make(replace_line('    evidence_required: [ai_review]', '    evidence_required: []')))
        self.assertEqual(out['result'], 'present', out)
        self.assertEqual(out['sources']['articles'], [{'id': 'INV-002', 'scope': ['src/**'], 'evidence_required': []}])

    def test_the_empty_list_gives_an_empty_list_for_the_three_list_keys(self):
        lines = replace_line('owner_kept_rules:', 'owner_kept_rules: []')
        lines = [x for x in lines if x != "  - match: ['docs/a.md', docs/b/**]"]
        lines = [('articles: []' if x == 'articles:' else x) for x in lines]
        lines = [x for x in lines if not x.startswith('  - id: INV') and not x.startswith('    scope') and not x.startswith('    evidence_required')]
        out = read(make(lines))
        self.assertEqual(out['result'], 'present', out)
        self.assertEqual(out['sources']['owner_kept_rules'], [])
        self.assertEqual(out['sources']['articles'], [])
        self.assertEqual(out['sources']['requirement_profiles'], [])

    def test_the_gap_marker_gives_none_for_exactly_that_key(self):
        for key in KEYS:
            lines = list(GOOD_LINES)
            i = next(k for k, x in enumerate(lines) if x.startswith(key + ':'))
            j = i + 1
            while j < len(lines) and lines[j].startswith(' '):
                j += 1
            lines[i:j] = [key + ': gap']
            out = read(make(lines))
            self.assertEqual(out['result'], 'present', (key, out))
            self.assertIsNone(out['sources'][key], key)
            good = read(make())['sources']
            for other in KEYS:
                if other != key:
                    self.assertEqual(out['sources'][other], good[other], (key, other))

    def test_delegation_values(self):
        self.assertIs(read(make(replace_line('delegation: true', 'delegation: false')))['sources']['delegation'], False)
        self.assertIs(read(make())['sources']['delegation'], True)
        self.assertIsNone(read(make(replace_line('delegation: true', 'delegation: gap')))['sources']['delegation'])

    def test_all_four_risks_are_accepted_in_order_and_a_subset_is_accepted(self):
        lines = replace_line('  medium: false', '  medium: false')
        lines += ['  high: true', '  critical: false']
        self.assertEqual(read(make(lines))['sources']['auto_accept'], {'low': False, 'medium': False, 'high': True, 'critical': False})
        sub = [x for x in GOOD_LINES if x not in ('  low: false',)]
        self.assertEqual(read(make(sub))['sources']['auto_accept'], {'medium': False})

    def test_a_quoted_text_may_hold_spaces_and_is_always_a_text(self):
        lines = replace_line('    scope: [src/**]', "    scope: ['a b', '123', 'true']")
        self.assertEqual(read(make(lines))['sources']['articles'][0]['scope'], ['a b', '123', 'true'])

    def test_the_heading_and_the_fence_are_exact_lines(self):
        for head in ('## 3. The sources ', '### 3. The sources', '## 3. the sources'):
            self.assertEqual(reason(make(head=head)), 'block', head)


class AC3TheRefusals(unittest.TestCase):
    def test_block_refusals(self):
        self.assertEqual(reason('no heading here'), 'block')
        self.assertEqual(reason('## 3. The sources\n\nno fence\n'), 'block')
        self.assertEqual(reason('## 3. The sources\n' + FENCE + 'yaml\n' + '\n'.join(GOOD_LINES) + '\n'), 'block')
        self.assertEqual(reason(make() + '\n## 3. The sources\n'), 'block')
        self.assertEqual(reason(make() + '\n' + FENCE + 'yaml\nx\n' + FENCE + '\n'), 'block')
        self.assertIsNone(read('no heading')['findings'][0]['line'])

    def test_line_refusals(self):
        cases = [
            replace_line('delegation: true', 'delegation:\ttrue'),
            replace_line('delegation: true', 'delegation: true '),
            replace_line('delegation: true', 'delegation: true\r'),
            replace_line('delegation: true', 'Delegation: true'),
            replace_line('delegation: true', 'delegation: true # a comment'),
            replace_line("    scope: [src/**]", "    scope: [a,b]"),
            replace_line("    scope: [src/**]", "    scope: [a ,b]"),
            replace_line("    scope: [src/**]", "    scope:  [src/**]"),
            replace_line("  - id: INV-002", " - id: INV-002"),
            replace_line("  low:", "   low:"),
            GOOD_LINES + ['Trailing: stuff'],
            replace_line('requirement_profiles: []', '   '),
        ]
        for lines in cases:
            self.assertEqual(reason(make(lines)), 'line', lines)

    def test_key_refusals(self):
        self.assertEqual(reason(make(GOOD_LINES + ['delegation: true'])), 'key')
        self.assertEqual(reason(make(GOOD_LINES + ['trailing: stuff'])), 'key')
        no_auto = GOOD_LINES[:-3]
        self.assertEqual(reason(make(no_auto)), 'key')
        unknown = replace_line('delegation: true', 'delegations: true')
        self.assertEqual(reason(make(unknown)), 'key')
        swapped = list(GOOD_LINES)
        i, j = swapped.index('delegation: true'), swapped.index('requirement_profiles: []')
        swapped[i], swapped[j] = swapped[j], swapped[i]
        self.assertEqual(reason(make(swapped)), 'key')
        repeated = swapped = GOOD_LINES[:12] + ['requirement_profiles: []'] + GOOD_LINES[12:]
        self.assertEqual(reason(make(repeated)), 'key')
        self.assertEqual(reason(make([])), 'key')

    def test_value_refusals(self):
        cases = [
            replace_line('  medium: false', '  extreme: false'),
            replace_line('  medium: false', '  medium: False'),
            replace_line('  medium: false', '  medium: yes'),
            replace_line('delegation: true', 'delegation: True'),
            replace_line('delegation: true', 'delegation: maybe'),
            replace_line('delegation: true', 'delegation:'),
            replace_line('requirement_profiles: []', 'requirement_profiles:'),
            replace_line('  - match: [\'docs/a.md\', docs/b/**]', '  - match: []'),
            replace_line('    scope: [src/**]', '    scope: []'),
            replace_line('    - {dimension: functional, evidence_types: [build, lint]}', '    - {dimension: functional, evidence_types: []}'),
            replace_line('articles:', 'articles: gap\n'.strip()),
            replace_line('default_profiles:', 'default_profiles: []'),
            replace_line('auto_accept:', 'auto_accept: []'),
            replace_line('delegation: true', 'delegation: gap now'),
            GOOD_LINES[:GOOD_LINES.index('  medium:')] + ['  high:', '    - {dimension: a, evidence_types: [b]}', '  medium:',
                                                          '    - {dimension: a, evidence_types: [b]}'] + GOOD_LINES[GOOD_LINES.index('requirement_profiles: []'):],
        ]
        for lines in cases:
            self.assertEqual(reason(make(lines)), 'value', lines)
        empty_dp = [x for x in GOOD_LINES if not x.startswith('  ') or not any(k in x for k in ('low', 'medium', 'functional', 'architecture'))]
        self.assertEqual(reason(make(empty_dp)), 'value')
        empty_aa = GOOD_LINES[:-2]
        self.assertEqual(reason(make(empty_aa)), 'value')

    def test_scalar_refusals_in_item_and_in_boolean_positions(self):
        for token in ('0', '12', '3.5', '1e3', 'NaN', 'nan', 'Infinity', '-Infinity', 'inf', '+1', '0x1F', '1abc', 'True', 'null',
                      'a b', "''", '.nan', '-.inf', 'YES', 'off', '"q"'):
            item = replace_line("    scope: [src/**]", '    scope: [%s]' % token)
            self.assertEqual(reason(make(item)), 'scalar', token)
            ident = replace_line("  - id: INV-002", '  - id: %s' % token)
            self.assertEqual(reason(make(ident)), 'scalar', token)
        for token in ('0', '12', '3.5', '1e3', 'NaN', 'nan', 'Infinity', '-Infinity', 'inf', '+1', '0x1F', '1abc', '.nan', '-.inf'):
            self.assertEqual(reason(make(replace_line('delegation: true', 'delegation: ' + token))), 'scalar', token)
            self.assertEqual(reason(make(replace_line('  medium: false', '  medium: ' + token))), 'scalar', token)
        self.assertEqual(reason(make(replace_line('delegation: true', 'delegation: a b'))), 'value')

    def test_encoding_refusals_are_checked_on_the_whole_text_first(self):
        lone = '\ud800'
        in_item = replace_line("    scope: [src/**]", "    scope: ['a%s']" % lone)
        self.assertEqual(reason(make(in_item)), 'encoding')
        in_comment = list(GOOD_LINES)
        in_comment.insert(3, '# a comment with a lone surrogate %s' % lone)
        out = read(make(in_comment))
        self.assertEqual(out['result'], 'refused')
        self.assertEqual(out['findings'][0]['reason'], 'encoding')
        self.assertEqual(out['findings'][0]['line'], make(in_comment).split('\n').index('# a comment with a lone surrogate %s' % lone) + 1)
        outside = read(make(after='x %s y' % lone))
        self.assertEqual(outside['findings'][0]['reason'], 'encoding')
        # encoding comes before every other departure, block included
        self.assertEqual(reason('no heading ' + lone), 'encoding')

    def test_duplicate_refusals(self):
        art = GOOD_LINES.index('articles:') + 1
        twice = GOOD_LINES[:art] + GOOD_LINES[art:art + 3] + GOOD_LINES[art:]
        self.assertEqual(reason(make(twice)), 'duplicate')
        risk = GOOD_LINES[:GOOD_LINES.index('  medium:')] + ['  low:', '    - {dimension: a, evidence_types: [b]}'] + GOOD_LINES[GOOD_LINES.index('  medium:'):]
        self.assertEqual(reason(make(risk)), 'duplicate')
        self.assertEqual(reason(make(replace_line("  - match: ['docs/a.md', docs/b/**]", "  - match: [x, x]"))), 'duplicate')
        auto = GOOD_LINES + ['  low: true']
        self.assertEqual(reason(make(auto)), 'duplicate')
        req = replace_line('requirement_profiles: []', 'requirement_profiles:')
        i = req.index('requirement_profiles:') + 1
        e = ['  - id: S', '    add:', '      - {dimension: a, evidence_types: [b]}']
        req[i:i] = e + e
        self.assertEqual(reason(make(req)), 'duplicate')

    def test_the_first_departure_in_the_order_of_the_contract_is_the_only_finding(self):
        lines = ['delegation: maybe', 'owner_kept_rules: gap']
        out = read(make(lines))
        self.assertEqual(len(out['findings']), 1)
        self.assertEqual(out['findings'][0]['reason'], 'key')
        self.assertEqual(set(out['findings'][0]), {'reason', 'line', 'detail'})
        self.assertIsInstance(out['findings'][0]['detail'], str)

    def test_a_refusal_gives_no_partial_mapping(self):
        bad = [replace_line('delegation: true', 'delegation: maybe'), replace_line('  medium: false', '  medium: 1'),
               replace_line('requirement_profiles: []', 'requirement_profiles: [x]')]
        for lines in bad + [None, 'x']:
            out = read(make(lines) if isinstance(lines, list) else lines)
            self.assertEqual(out['result'], 'refused')
            self.assertEqual(out['sources'], dict.fromkeys(KEYS))
            self.assertEqual(len(out['findings']), 1)

    def test_the_line_of_a_finding_is_the_one_based_line_of_the_whole_text(self):
        text = make(replace_line('delegation: true', 'delegation: maybe'))
        n = text.split('\n').index('delegation: maybe') + 1
        self.assertEqual(read(text)['findings'][0]['line'], n)


def finding(lines, marker=None, **kw):
    """The refusal of make(lines, **kw): (reason, line) and, with marker, the 1-based line of the marker in the text."""
    text = make(lines, **kw)
    out = read(text)
    assert out['result'] == 'refused', out
    f = out['findings'][0]
    n = None
    if marker is not None:
        n = [i for i, x in enumerate(text.split('\n'), 1) if x == marker]
    return f['reason'], f['line'], n


class AC3bTheFirstDepartureIsTheOneOnTheLowestLine(unittest.TestCase):
    """D-6884 M1: the single finding is the departure on the lowest line of the text; on the same line a line departure
    comes first; every finding names the line where its departure is."""

    def check(self, lines, reason_, marker, nth=0):
        r, line, n = finding(lines, marker)
        self.assertEqual(r, reason_, lines)
        self.assertEqual(line, n[nth], (lines, line, n))

    def test_a_repeated_article_id_is_reported_on_the_line_of_the_second_id(self):
        art = GOOD_LINES.index('articles:') + 1
        lines = GOOD_LINES[:art] + GOOD_LINES[art:art + 3] + GOOD_LINES[art:]
        self.check(lines, 'duplicate', '  - id: INV-002', 1)

    def test_a_repeated_owner_rule_is_reported_on_the_second_rule(self):
        rule = "  - match: ['docs/a.md', docs/b/**]"
        lines = GOOD_LINES[:2] + [rule] + GOOD_LINES[2:]
        self.check(lines, 'duplicate', rule, 1)

    def test_a_repeated_risk_is_reported_on_the_line_of_the_second_risk(self):
        i = GOOD_LINES.index('  medium:')
        lines = GOOD_LINES[:i] + ['  low:', '    - {dimension: a, evidence_types: [b]}'] + GOOD_LINES[i:]
        self.check(lines, 'duplicate', '  low:', 1)
        self.check(GOOD_LINES + ['  low: true'], 'duplicate', '  low: true')

    def test_a_repeated_requirement_id_is_reported_on_the_second_id_line(self):
        req = replace_line('requirement_profiles: []', 'requirement_profiles:')
        i = req.index('requirement_profiles:') + 1
        e = ['  - id: S', '    add:', '      - {dimension: a, evidence_types: [b]}']
        req[i:i] = e + e
        self.check(req, 'duplicate', '  - id: S', 1)

    def test_a_risk_with_no_entry_is_reported_on_that_risk_line(self):
        i = GOOD_LINES.index('  low:')
        lines = GOOD_LINES[:i + 1] + GOOD_LINES[i + 2:]
        self.check(lines, 'value', '  low:')
        # the last risk of the block with no entry: reported on its own line, not at the end of the block
        last = [x for x in GOOD_LINES if x not in ('    - {dimension: functional, evidence_types: [unit_test]}',
                                                    '    - {dimension: architecture, evidence_types: [deterministic_rule]}')]
        self.check(last, 'value', '  medium:')
        # an empty risk followed by a line that is itself wrong: the empty risk is on the lower line
        i = lines.index('  medium:')
        self.check(lines[:i] + ['not a line at all'] + lines[i:], 'value', '  low:')

    def test_an_id_with_no_add_and_an_add_with_no_entry_are_reported_on_the_id_and_the_add_lines(self):
        req = replace_line('requirement_profiles: []', 'requirement_profiles:')
        i = req.index('requirement_profiles:') + 1
        self.check(req[:i] + ['  - id: S'] + req[i:], 'value', '  - id: S')
        self.check(req[:i] + ['  - id: S', '    add:'] + req[i:], 'value', '    add:')

    def test_an_empty_key_block_is_reported_on_the_key_line(self):
        self.check(replace_line('requirement_profiles: []', 'requirement_profiles:'), 'value', 'requirement_profiles:')
        no_profiles = GOOD_LINES[:GOOD_LINES.index('default_profiles:') + 1] + GOOD_LINES[GOOD_LINES.index('requirement_profiles: []'):]
        self.check(no_profiles, 'value', 'default_profiles:')

    def test_a_missing_key_is_reported_on_the_closing_fence_line(self):
        text = make(GOOD_LINES[:-3])
        out = read(text)
        self.assertEqual((out['findings'][0]['reason'], out['findings'][0]['line']), ('key', text.split('\n').index(FENCE) + 1))

    def test_a_structural_departure_above_a_lexical_one_is_reported_first(self):
        lines = [('    scope: []' if x == '    scope: [src/**]' else x) for x in GOOD_LINES]
        lines = [('delegation: true ' if x == 'delegation: true' else x) for x in lines]
        self.check(lines, 'value', '    scope: []')

    def test_a_lexical_departure_above_a_structural_one_is_reported_first(self):
        lines = [('    scope: [src/**] ' if x == '    scope: [src/**]' else x) for x in GOOD_LINES]
        lines = [('delegation: maybe' if x == 'delegation: true' else x) for x in lines]
        self.check(lines, 'line', '    scope: [src/**] ')

    def test_on_the_same_line_a_line_departure_comes_first(self):
        lines = replace_line('delegation: true', 'delegation: maybe ')
        self.check(lines, 'line', 'delegation: maybe ')
        lines = replace_line('delegation: true', 'delegation: 12\t')
        self.check(lines, 'line', 'delegation: 12\t')

    def test_the_line_of_a_finding_is_exact_for_every_reason(self):
        for lines, marker, why in (
                (replace_line('  medium: false', '  medium: 12'), '  medium: 12', 'scalar'),
                (replace_line('  medium: false', '  extreme: false'), '  extreme: false', 'value'),
                (replace_line('delegation: true', 'Delegation: true'), 'Delegation: true', 'line'),
                (replace_line('delegation: true', 'delegations: true'), 'delegations: true', 'key')):
            self.check(lines, why, marker)


    def test_n1_a_wrong_line_under_an_empty_risk_is_reported_on_its_own_line(self):
        entry = '    - {dimension: functional, evidence_types: [unit_test]}'
        one = [x for x in GOOD_LINES if x != '    - {dimension: architecture, evidence_types: [deterministic_rule]}']
        self.check([(entry + ' ' if x == entry else x) for x in one], 'line', entry + ' ')
        self.check([('    - {dimension: functional, evidence_types: []}' if x == entry else x) for x in one], 'value',
                   '    - {dimension: functional, evidence_types: []}')
        i = one.index('  medium:')
        self.check(one[:i + 1] + ['    - not an entry'] + one[i + 2:], 'line', '    - not an entry')

    def test_n1_a_wrong_add_line_is_reported_on_its_own_line(self):
        req = replace_line('requirement_profiles: []', 'requirement_profiles:')
        i = req.index('requirement_profiles:') + 1
        self.check(req[:i] + ['  - id: S', '    add: '] + req[i:], 'line', '    add: ')
        self.check(req[:i] + ['  - id: S', '    adds:'] + req[i:], 'line', '    adds:')

    def test_n1_a_last_article_with_a_wrong_second_line_is_reported_on_that_line(self):
        i = GOOD_LINES.index('articles:')
        lines = GOOD_LINES[:i + 1] + ['  - id: A', '    scope bad'] + GOOD_LINES[GOOD_LINES.index('default_profiles:'):]
        self.check(lines, 'line', '    scope bad')
        lines = GOOD_LINES[:i + 1] + ['  - id: A'] + GOOD_LINES[GOOD_LINES.index('default_profiles:'):]
        self.check(lines, 'line', '  - id: A')

    def test_n1_an_id_followed_directly_by_an_entry_line_is_reported_on_the_id_line(self):
        req = replace_line('requirement_profiles: []', 'requirement_profiles:')
        i = req.index('requirement_profiles:') + 1
        self.check(req[:i] + ['  - id: S', '      - {dimension: a, evidence_types: [b]}'] + req[i:], 'value', '  - id: S')

    def test_n1_an_add_followed_directly_by_an_id_line_is_reported_on_the_add_line(self):
        req = replace_line('requirement_profiles: []', 'requirement_profiles:')
        i = req.index('requirement_profiles:') + 1
        self.check(req[:i] + ['  - id: S', '    add:', '  - id: T', '    add:', '      - {dimension: a, evidence_types: [b]}'] + req[i:],
                   'value', '    add:')


class AC3dSurvivorsOfTheFirstMutationRun(unittest.TestCase):
    """D-6886 C1: tests for the survivors A11, A26, A33, A34, A47 and A51 of the first mutation run."""

    def test_a_single_yaml_fence_line_before_the_heading_and_none_after_it_is_a_block(self):
        text = 'intro\n' + FENCE + 'yaml\n' + '\n'.join(GOOD_LINES) + '\n' + FENCE + '\n\n## 3. The sources\n\nnothing here\n'
        out = read(text)
        self.assertEqual(out['result'], 'refused')
        self.assertEqual((out['findings'][0]['reason'], out['findings'][0]['line']), ('block', None))
        self.assertEqual(out['sources'], dict.fromkeys(KEYS))

    def test_the_empty_list_is_refused_for_default_profiles_and_auto_accept_with_the_key_line_alone(self):
        dp = GOOD_LINES[:GOOD_LINES.index('default_profiles:')] + ['default_profiles: []'] + GOOD_LINES[GOOD_LINES.index('requirement_profiles: []'):]
        r, line, n = finding(dp, 'default_profiles: []')
        self.assertEqual((r, line), ('value', n[0]))
        aa = GOOD_LINES[:GOOD_LINES.index('auto_accept:')] + ['auto_accept: []']
        r, line, n = finding(aa, 'auto_accept: []')
        self.assertEqual((r, line), ('value', n[0]))

    def test_tokens_that_only_float_or_only_int_accept_are_scalars_in_both_positions(self):
        for token in ('+1.5', '-1e3', '+0x1F', '-0b11'):
            for lines in (replace_line('delegation: true', 'delegation: ' + token), replace_line('  medium: false', '  medium: ' + token)):
                self.assertEqual(reason(make(lines)), 'scalar', token)
        for token in ('-1e3', '-0b11'):
            lines = replace_line("    scope: [src/**]", '    scope: [%s]' % token)
            self.assertEqual(reason(make(lines)), 'scalar', token)

    def test_auto_accept_risks_out_of_order_are_refused_on_the_line_of_the_first_one_out_of_order(self):
        lines = [x for x in GOOD_LINES if x not in ('  low: false', '  medium: false')] + ['  low: false', '  high: true', '  medium: false']
        r, line, n = finding(lines, '  medium: false')
        self.assertEqual((r, line), ('value', n[-1]))

    def test_an_unexpected_internal_exception_is_reported_as_an_argument_finding(self):
        from unittest import mock
        with mock.patch.object(evaluation_policy, '_parse', side_effect=ValueError('boom')):
            out = read(make())
        self.assertEqual(out['result'], 'refused')
        self.assertEqual((out['findings'][0]['reason'], out['findings'][0]['line']), ('argument', None))
        self.assertEqual(out['sources'], dict.fromkeys(KEYS))


PINNED_REASON = {'\n': 'line', '\r': 'line', '\x0b': 'scalar', '\x0c': 'scalar', '\x1c': 'scalar', '\x1d': 'scalar', '\x1e': 'scalar', '\x85': 'scalar', '\u2028': 'scalar', '\u2029': 'scalar'}


class AC3cQuotedTextsAndFences(unittest.TestCase):
    def test_a_quoted_text_refuses_every_line_boundary_character(self):
        for ch in ('\n', '\r', '\x0b', '\x0c', '\x1c', '\x1d', '\x1e', '\x85', '\u2028', '\u2029'):
            lines = replace_line("    scope: [src/**]", "    scope: ['a%sb']" % ch)
            out = read(make(lines))
            self.assertEqual(out['result'], 'refused', repr(ch))
            self.assertEqual(out['findings'][0]['reason'], PINNED_REASON[ch], repr(ch))
        for ch in ('\u2028', '\x0c'):
            self.assertEqual(reason(make(replace_line("    scope: [src/**]", "    scope: ['a%sb']" % ch))), 'scalar', repr(ch))
        self.assertEqual(read(make(replace_line("    scope: [src/**]", "    scope: ['a\u00e9b']")))['result'], 'present')

    def test_a_yaml_fence_line_before_the_heading_is_refused_as_a_block(self):
        text = make(before='intro\n' + FENCE + 'yaml\nsomething\n' + FENCE)
        self.assertEqual(reason(text), 'block')
        self.assertEqual(reason(make(after=FENCE + 'yaml')), 'block')


class AC4TheFormsMeetTheGovernor(unittest.TestCase):
    def test_the_six_sources_are_accepted_by_derive_inputs_and_an_article_applies(self):
        src = read(make())['sources']
        values = {
            'contract': {'traces_to': ['SPEC-001'], 'risk': 'low', 'owner_kept_act': False, 'verification_plan': ['G1']},
            'changed_paths': ['src/x.py'],
            'risk_rules': [{'match': ['src/**'], 'class': 'medium'}],
            'owner_kept_rules': src['owner_kept_rules'], 'articles': src['articles'], 'default_profiles': src['default_profiles'],
            'requirement_profiles': src['requirement_profiles'], 'delegation': src['delegation'], 'evidence_comparison': {'weakens': False},
            'auto_accept': src['auto_accept'], 'policy_version': 'v2', 'level_version': 'v1', 'ruleset_version': 'v1'}
        self.assertEqual(set(values), governor.VALUE_KEYS)
        out = governor.derive_inputs(values)
        self.assertEqual(out['risk'], 'medium')
        self.assertEqual(out['applicable_articles'], [{'id': 'INV-002', 'evidence_required': ['ai_review']}])
        self.assertIs(out['delegation_in_force'], True)
        self.assertIs(out['auto_accept'], False)
        self.assertEqual(out['evidence_profile'][0]['dimension'], 'functional')

    def test_a_gap_in_the_policy_is_refused_by_eval_inputs_as_a_gap_naming_exactly_that_key(self):
        src = read(make(replace_line('articles:', 'articles: gap')[:3] + GOOD_LINES[6:]))
        self.assertEqual(src['result'], 'present', src)
        self.assertIsNone(src['sources']['articles'])
        # the other six sources are FIXTURES, not policy
        sources = {'intent_versions': {'SPEC-001': 'v2'}, 'evidence_comparison': {'weakens': False}, 'level_version': 'v1',
                   'ruleset_version': 'v1', 'policy_version': 'v2', 'risk_rules': [{'match': ['src/**'], 'class': 'medium'}]}
        sources.update(src['sources'])
        contract = {'task': 'TASK-150', 'traces_to': ['SPEC-001'], 'risk': 'low', 'owner_kept_act': 'false',
                    'verification_plan': [{'gate': 'G0', 'check': 'scope'}],
                    'autonomy': {'max_level': 'L1', 'budgets': {'tokens': '400k', 'wall_time': '2h', 'retries': '1', 'human_attention': '0m'}}}
        out = eval_inputs.eval_inputs(task_id='TASK-150', evaluated_commit='a' * 40, policy_ref='b' * 40, contract=contract,
                                      contract_sha256='c' * 64, changed_paths=['src/x.py'], runs=[], sources=sources,
                                      log_payloads=[], recorder='external CI')
        self.assertEqual((out['refusal']['reason'], out['refusal']['detail']), ('gap', 'open gaps: articles'))


class AC6TheEvidenceDefiningPaths(unittest.TestCase):
    EXPECTED = ('docs/pre-genesis/constitution.md', 'docs/pre-genesis/assurance-model.md', 'docs/specs/risk-rules-gov-aieos.md',
                'docs/pre-genesis/decision-matrix.md', 'docs/specs/evaluation-policy-gov-aieos.md',
                'src/aieos_bootstrap/governor.py', 'docs/pre-genesis/governor-spec.md', 'src/aieos_bootstrap/evaluation_policy.py',
                'src/aieos_bootstrap/eval_inputs.py', 'src/aieos_bootstrap/evaluation_derive.py',
                'src/aieos_bootstrap/evaluation_sources.py', 'src/aieos_bootstrap/scope_reconcile.py', 'src/aieos_bootstrap/base_inputs.py',
                'src/aieos_bootstrap/base_files.py', 'src/aieos_bootstrap/evaluation.py', 'src/aieos_bootstrap/ci_evidence.py')

    def test_the_list_is_a_tuple_of_the_paths_of_the_contract(self):
        paths = evaluation_policy.EVIDENCE_DEFINING_PATHS
        self.assertIsInstance(paths, tuple)
        self.assertEqual(paths, self.EXPECTED)
        self.assertEqual(len(set(paths)), len(paths))

    def test_every_path_is_a_relative_repository_path(self):
        for p in evaluation_policy.EVIDENCE_DEFINING_PATHS:
            self.assertIsInstance(p, str)
            self.assertTrue(p and not p.startswith('/') and '..' not in p and '\\' not in p, p)

    def test_it_holds_the_five_policy_paths_of_eval_inputs(self):
        policy = set(eval_inputs._POLICY_PATHS)
        self.assertEqual(len(policy), 5)
        self.assertIn('docs/specs/evaluation-policy-gov-aieos.md', policy)
        self.assertTrue(policy <= set(evaluation_policy.EVIDENCE_DEFINING_PATHS))

    def test_the_paths_that_exist_in_the_repository_exist(self):
        for p in self.EXPECTED:
            if p != 'docs/specs/evaluation-policy-gov-aieos.md':
                self.assertTrue((ROOT / p).is_file(), p)


if __name__ == '__main__':
    unittest.main()
