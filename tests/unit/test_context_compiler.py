"""Unit tests of aieos_bootstrap.context_compiler (TASK-080): the inputs and their findings, the Work Order's keys and
hash, the five layers, the schemas, the items and budgets, purity, what the module may touch, its docstring and this
module's own naming rule. No test here reads or writes a store or a temporary folder; the source is read with
pathlib's read_bytes."""

import ast
import copy
import hashlib
import json
import pathlib
import sys
import unittest
from unittest import mock

from aieos_bootstrap import conformance, context_compiler

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap' / 'context_compiler.py'
build = context_compiler.build_work_order
LAYERS = ['constitution', 'components', 'traced', 'files', 'handoff']
WO_KEYS = {'task', 'contract_version', 'contract_hash', 'base', 'session_id', 'decision', 'contract', 'layers',
           'work_order_hash'}
API = {'id': 'api', 'paths': ['lib/api/**'], 'tags': ['x']}
CORE = {'id': 'core', 'paths': ['src/pkg'], 'tags': []}
OTHER = {'id': 'other', 'paths': ['other'], 'tags': []}


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def inputs():
    """A fresh set of well-formed inputs: core is met by the write-set (a bare path read as a folder), api is named by
    an interface only, other is neither."""
    contract = {
        'task': 'TASK-900', 'contract_version': 'v1', 'objective': 'an objective',
        'traces_to': ['docs/specs/x.md#1', 'ADR-001'],
        'write_set': {'paths': ['src/pkg/mod.py']},
        'read_set': {'paths': ['docs/specs/x.md'], 'interfaces': ['pkg.api'], 'schemas': ['order']},
        'acceptance_criteria': [{'AC1': 'first'}, {'AC2': 'second'}],
        'constitution': ['INV-001', 'INV-002'], 'risk': 'low'}
    return {
        'task': 'TASK-900', 'session_id': 's-1', 'base': 'a' * 40, 'contract': contract, 'contract_hash': 'b' * 64,
        'resume_record': {'decision': 'CONTINUE', 'subject': 'TASK-900', 'contract_hash': 'b' * 64,
                          'contract_version': 'v1',
                          'constitution': {'applicable': ['INV-001'], 'violated': [], 'no_result': []}},
        'articles': {'INV-001': 'article one'},
        'components': [copy.deepcopy(CORE), copy.deepcopy(API), copy.deepcopy(OTHER)],
        'interfaces': [{'id': 'pkg.api', 'component': 'api'}],
        'adrs': {'ADR-001': 'adr text'},
        'traced': {'docs/specs/x.md#1': 'section one'},
        'files': {'src/pkg/mod.py': 'code', 'src/pkg/util.py': 'util', 'docs/specs/x.md': 'spec',
                  'lib/api/order.json': 'schema', 'lib/api/client.py': 'client', 'other/z.py': 'z',
                  'derived/d.py': 'd'},
        'derived_read_set': ['derived/d.py', 'missing/m.py'],
        'last_handoff': {'ref': 'handoffs/TASK-900-s-0.md', 'text': 'handoff'},
        'budgets': {name: 100000 for name in LAYERS}}


def layer(wo, name):
    return [x for x in wo['layers'] if x['name'] == name][0]


def refs(wo, name):
    return [i['ref'] for i in layer(wo, name)['items']]


class Base(unittest.TestCase):
    def built(self, inp):
        wo, findings = build(inp)
        self.assertIsNone(findings)
        self.assertIsInstance(wo, dict)
        return wo

    def refused(self, inp):
        result = build(inp)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsNone(result[0])
        self.assertIsInstance(result[1], list)
        self.assertTrue(result[1])
        self.assertTrue(all(isinstance(f, str) for f in result[1]))
        return result[1]


class TASK080AC1Inputs(Base):
    def test_well_formed_inputs_give_a_work_order(self):
        """TASK-080 AC1: well-formed inputs give a Work Order and no findings."""
        self.built(inputs())

    def test_not_an_object(self):
        """TASK-080 AC1: inputs that are not a dict give findings, never an exception."""
        for v in (None, [], 'x', 3):
            self.refused(v)

    def test_missing_and_extra_keys(self):
        """TASK-080 AC1: a missing key and an extra key each give findings."""
        for key in sorted(inputs()):
            inp = inputs()
            del inp[key]
            self.refused(inp)
        inp = inputs()
        inp['more'] = 1
        self.refused(inp)

    def test_task_session_base_and_hash_forms(self):
        """TASK-080 AC1: task, session_id, base and contract_hash outside their forms give findings."""
        for key, value in (('task', 'TASK-x'), ('session_id', ''), ('session_id', 'a b'), ('session_id', 'a' * 129),
                           ('base', 'A' * 40), ('base', 'a' * 39), ('contract_hash', 'b' * 63)):
            inp = inputs()
            inp[key] = value
            self.refused(inp)

    def test_decision_other_than_continue(self):
        """TASK-080 AC1: a record decision other than CONTINUE or CONTINUE_WITH gives findings; both are taken."""
        for d in ('REPLAN', 'BLOCKED', 'STOP: violation', None):
            inp = inputs()
            inp['resume_record']['decision'] = d
            self.refused(inp)
        inp = inputs()
        inp['resume_record']['decision'] = 'CONTINUE_WITH'
        self.assertEqual(self.built(inp)['decision'], 'CONTINUE_WITH')

    def test_record_ties(self):
        """TASK-080 AC1: a record whose subject, contract_hash or contract_version differs gives findings."""
        for key, value in (('subject', 'TASK-901'), ('contract_hash', 'c' * 64), ('contract_version', 'v2')):
            inp = inputs()
            inp['resume_record'][key] = value
            self.refused(inp)

    def test_record_constitution_form(self):
        """TASK-080 AC1: a record constitution that is not {applicable, violated, no_result} of ids gives findings."""
        for con in (None, {'applicable': ['INV-001']}, {'applicable': 'INV-001', 'violated': [], 'no_result': []}):
            inp = inputs()
            inp['resume_record']['constitution'] = con
            self.refused(inp)

    def test_articles_keys(self):
        """TASK-080 AC1: articles keyed other than constitution.applicable give findings."""
        for articles in ({}, {'INV-001': 'a', 'INV-002': 'b'}, {'INV-002': 'b'}, {'INV-001': 1}):
            inp = inputs()
            inp['articles'] = articles
            self.refused(inp)

    def test_traced_and_adrs_keys(self):
        """TASK-080 AC1: traced or adrs keyed other than the header states give findings."""
        inp = inputs()
        inp['traced']['other'] = 'x'
        self.refused(inp)
        inp = inputs()
        inp['traced'] = {}
        self.refused(inp)
        inp = inputs()
        inp['adrs']['ADR-002'] = 'not traced'
        self.refused(inp)
        inp = inputs()
        inp['traced']['ADR-001'] = 'both'
        self.refused(inp)

    def test_contract_task_differs(self):
        """TASK-080 AC1: a contract whose task differs gives findings."""
        inp = inputs()
        inp['contract']['task'] = 'TASK-901'
        self.refused(inp)

    def test_contract_forms(self):
        """TASK-080 AC1: contract keys outside their forms give findings."""
        cases = [('contract_version', '1'), ('traces_to', 'x'), ('write_set', {'paths': 'src'}),
                 ('read_set', {'paths': [1]}), ('acceptance_criteria', [{'AC1': 'a', 'AC2': 'b'}]),
                 ('acceptance_criteria', [{'AC1': 1}])]
        for key, value in cases:
            inp = inputs()
            inp['contract'][key] = value
            self.refused(inp)
        inp = inputs()
        inp['contract'] = []
        self.refused(inp)

    def test_budgets(self):
        """TASK-080 AC1: a missing, non-int, bool or non-positive budget gives findings; budgets have no default."""
        for value in ('5', True, 0, -1, 1.5, None):
            inp = inputs()
            inp['budgets']['files'] = value
            self.refused(inp)
        inp = inputs()
        del inp['budgets']['handoff']
        self.refused(inp)
        inp = inputs()
        inp['budgets']['extra'] = 5
        self.refused(inp)

    def test_duplicate_ref(self):
        """TASK-080 AC1: a ref given twice within a layer gives findings."""
        inp = inputs()
        inp['contract']['acceptance_criteria'] = [{'AC1': 'first'}, {'AC1': 'again'}]
        self.refused(inp)
        inp = inputs()
        inp['contract']['traces_to'] = ['docs/specs/x.md#1', 'docs/specs/x.md#1', 'ADR-001']
        self.refused(inp)
        inp = inputs()
        inp['contract']['acceptance_criteria'] = [{'docs/specs/x.md#1': 'an AC id equal to a traced entry'}]
        self.refused(inp)

    def test_non_json_values(self):
        """TASK-080 AC1: a float NaN or infinity, a set, a tuple, a non-str key, or a str UTF-8 cannot encode gives
        findings."""
        for value in (float('nan'), float('inf'), float('-inf'), {1, 2}, (1, 2), {1: 'x'}, '\ud800', {'\udc00': 1},
                      object(), b'bytes'):
            inp = inputs()
            inp['contract']['extra'] = value
            self.refused(inp)
        inp = inputs()
        inp['files']['lib/api/client.py'] = '\ud800'
        self.refused(inp)

    def test_nested_too_deep_and_a_cycle(self):
        """TASK-080 AC1: a value nested beyond the bound, or a cycle, gives findings, never an exception."""
        deep = []
        for _ in range(context_compiler.MAX_DEPTH + 5):
            deep = [deep]
        inp = inputs()
        inp['contract']['extra'] = deep
        self.refused(inp)
        loop = []
        loop.append(loop)
        inp = inputs()
        inp['contract']['extra'] = loop
        self.refused(inp)

    def test_wide_cycle_and_doubling_value(self):
        """TASK-080 AC1: a list holding itself twice, and an acyclic value doubling at each level, give findings (the
        bound on the values walked) instead of a walk without end; an input of 1,000 values is taken."""
        wide = []
        wide.append(wide)
        wide.append(wide)
        inp = inputs()
        inp['contract']['extra'] = wide
        self.refused(inp)
        doubling = 'leaf'
        for _ in range(60):
            doubling = [doubling, doubling]
        inp = inputs()
        inp['contract']['extra'] = doubling
        findings = self.refused(inp)
        self.assertEqual(len(findings), 1)
        self.assertIn(str(context_compiler.MAX_NODES), findings[0])
        inp = inputs()
        inp['contract']['extra'] = list(range(1000))
        self.built(inp)

    def test_interface_entry_naming_nothing(self):
        """TASK-080 AC1: a read_set.interfaces entry naming no given interface gives findings, as does an interface
        naming no given component."""
        inp = inputs()
        inp['contract']['read_set']['interfaces'] = ['pkg.none']
        self.refused(inp)
        inp = inputs()
        inp['interfaces'] = [{'id': 'pkg.api', 'component': 'none'}]
        self.refused(inp)

    def test_malformed_sources(self):
        """TASK-080 AC1: malformed files, derived_read_set, components, interfaces or last_handoff give findings."""
        cases = [('files', {'a': 1}), ('files', []), ('derived_read_set', 'derived/d.py'), ('derived_read_set', [1]),
                 ('components', [{'id': 'a', 'paths': ['x']}]), ('components', [API, API]),
                 ('interfaces', [{'id': 'pkg.api'}]),
                 ('interfaces', [{'id': 'pkg.api', 'component': 'api'}, {'id': 'pkg.api', 'component': 'core'}]),
                 ('last_handoff', {'ref': 'h'}), ('last_handoff', {'ref': '', 'text': 't'}), ('last_handoff', 'h')]
        for key, value in cases:
            inp = inputs()
            inp[key] = copy.deepcopy(value)
            self.refused(inp)

    def test_no_partial_work_order(self):
        """TASK-080 AC1: on findings the first element is None, never a partial Work Order."""
        inp = inputs()
        inp['budgets']['files'] = 0
        result = build(inp)
        self.assertIsNone(result[0])

    def test_taken_without_schemas_and_with_a_finite_float(self):
        """TASK-080 AC1: a read_set without schemas, and a finite float in the contract, are taken."""
        inp = inputs()
        del inp['contract']['read_set']['schemas']
        self.built(inp)
        inp = inputs()
        inp['contract']['weight'] = 0.5
        inp['contract']['large'] = 1e300
        wo = self.built(inp)
        self.assertEqual(wo['contract']['weight'], 0.5)
        self.assertEqual(wo['contract']['large'], 1e300)


class TASK080AC2KeysAndHash(Base):
    def test_nine_keys(self):
        """TASK-080 AC2: the Work Order has exactly the nine keys of specification 6 section 5."""
        wo = self.built(inputs())
        self.assertEqual(set(wo), WO_KEYS)
        self.assertEqual((wo['task'], wo['contract_version'], wo['contract_hash'], wo['base'], wo['session_id']),
                         ('TASK-900', 'v1', 'b' * 64, 'a' * 40, 's-1'))

    def test_contract_and_decision(self):
        """TASK-080 AC2: contract is the contract as given and decision is the record's."""
        inp = inputs()
        wo = self.built(inp)
        self.assertEqual(wo['contract'], inp['contract'])
        self.assertEqual(wo['decision'], 'CONTINUE')

    def test_hash_recomputed_from_the_object(self):
        """TASK-080 AC2: work_order_hash is the SHA-256 of the canonical form of the object without it."""
        wo = self.built(inputs())
        rest = {k: v for k, v in wo.items() if k != 'work_order_hash'}
        self.assertEqual(wo['work_order_hash'], hashlib.sha256(canonical(rest)).hexdigest())

    def test_canonical_form_uses_sorted_keys_and_utf8(self):
        """TASK-080 AC2: the canonical form sorts keys, has no insignificant whitespace and keeps non-ASCII text."""
        inp = inputs()
        inp['contract']['objective'] = 'ổn định'
        wo = self.built(inp)
        rest = {k: v for k, v in wo.items() if k != 'work_order_hash'}
        unsorted = json.dumps(rest, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        ascii_form = json.dumps(rest, sort_keys=True, separators=(',', ':')).encode('utf-8')
        spaced = json.dumps(rest, sort_keys=True, ensure_ascii=False).encode('utf-8')
        for other in (unsorted, ascii_form, spaced):
            self.assertNotEqual(wo['work_order_hash'], hashlib.sha256(other).hexdigest())

    def test_same_inputs_same_bytes(self):
        """TASK-080 AC2: the same inputs give the same bytes."""
        self.assertEqual(canonical(self.built(inputs())), canonical(self.built(inputs())))

    def test_any_change_changes_the_hash(self):
        """TASK-080 AC2: a change of any included value changes the hash."""
        h = self.built(inputs())['work_order_hash']
        changes = [lambda i: i.__setitem__('session_id', 's-2'), lambda i: i.__setitem__('base', 'c' * 40),
                   lambda i: i['files'].__setitem__('src/pkg/mod.py', 'code2'),
                   lambda i: i['articles'].__setitem__('INV-001', 'changed'),
                   lambda i: i['contract'].__setitem__('objective', 'other'),
                   lambda i: i['last_handoff'].__setitem__('text', 'other'),
                   lambda i: i['resume_record'].__setitem__('decision', 'CONTINUE_WITH')]
        for change in changes:
            inp = inputs()
            change(inp)
            self.assertNotEqual(self.built(inp)['work_order_hash'], h)

    def test_an_unselected_value_leaves_the_hash(self):
        """TASK-080 AC2: a change of a value the Work Order does not include leaves the hash as it is."""
        h = self.built(inputs())['work_order_hash']
        inp = inputs()
        inp['files']['other/z.py'] = 'changed'
        self.assertEqual(self.built(inp)['work_order_hash'], h)


class TASK080AC3Layers(Base):
    def test_five_layers_in_order(self):
        """TASK-080 AC3: five layers, numbered 1 to 5, with the header's names."""
        wo = self.built(inputs())
        self.assertEqual([(x['layer'], x['name']) for x in wo['layers']], list(enumerate(LAYERS, 1)))
        self.assertTrue(all(set(x) == {'layer', 'name', 'items'} for x in wo['layers']))

    def test_layer_1_from_the_record(self):
        """TASK-080 AC3: layer 1 holds constitution.applicable only; a contract article not applicable is absent."""
        wo = self.built(inputs())
        self.assertEqual(refs(wo, 'constitution'), ['INV-001'])
        self.assertEqual(layer(wo, 'constitution')['items'][0]['content'], 'article one')
        inp = inputs()
        inp['resume_record']['constitution']['applicable'] = ['SEC-001', 'INV-001']
        inp['articles'] = {'SEC-001': 's', 'INV-001': 'a'}
        self.assertEqual(refs(self.built(inp), 'constitution'), ['INV-001', 'SEC-001'])

    def test_layer_2_met_and_named_components(self):
        """TASK-080 AC3: layer 2 holds the component met by the write-set, its bare path read as a folder, and the one
        an interface entry names; the other is absent."""
        self.assertEqual(refs(self.built(inputs()), 'components'), ['component:api', 'component:core'])

    def test_layer_2_met_by_read_set_paths(self):
        """TASK-080 AC3: a component met only by a read_set.paths pattern is in layer 2."""
        inp = inputs()
        inp['components'].append({'id': 'docs', 'paths': ['docs'], 'tags': []})
        self.assertIn('component:docs', refs(self.built(inp), 'components'))

    def test_layer_2_bare_path_is_a_folder(self):
        """TASK-080 AC3: a bare component path is read as "<it>/**", so a file under it meets it."""
        inp = inputs()
        inp['contract']['read_set']['interfaces'] = []
        inp['contract']['read_set']['schemas'] = []
        self.assertEqual(refs(self.built(inp), 'components'), ['component:core'])

    def test_layer_2_content(self):
        """TASK-080 AC3: a component item's content is the canonical JSON of its declaration and naming interfaces."""
        inp = inputs()
        inp['interfaces'].append({'id': 'pkg.api2', 'component': 'api'})
        wo = self.built(inp)
        items = {i['ref']: i for i in layer(wo, 'components')['items']}
        expected = json.dumps({'component': API, 'interfaces': ['pkg.api', 'pkg.api2']}, sort_keys=True,
                              separators=(',', ':'), ensure_ascii=False)
        self.assertEqual(items['component:api']['content'], expected)
        self.assertEqual(json.loads(items['component:core']['content']), {'component': CORE, 'interfaces': []})

    def test_layer_3(self):
        """TASK-080 AC3: layer 3 holds the non-ADR traces_to entries, the ACs and the ADRs, each once."""
        wo = self.built(inputs())
        self.assertEqual(refs(wo, 'traced'), ['AC1', 'AC2', 'adr:ADR-001', 'docs/specs/x.md#1'])
        contents = {i['ref']: i['content'] for i in layer(wo, 'traced')['items']}
        self.assertEqual(contents, {'AC1': 'first', 'AC2': 'second', 'adr:ADR-001': 'adr text',
                                    'docs/specs/x.md#1': 'section one'})

    def test_layer_4(self):
        """TASK-080 AC3: layer 4 holds the write-set and read_set.paths matches, the files under the interface's
        component, the schema's file and the derived paths present in files; unselected entries are absent."""
        wo = self.built(inputs())
        self.assertEqual(refs(wo, 'files'), ['derived/d.py', 'docs/specs/x.md', 'lib/api/client.py',
                                             'lib/api/order.json', 'src/pkg/mod.py'])
        for absent in ('src/pkg/util.py', 'other/z.py', 'missing/m.py'):
            self.assertNotIn(absent, refs(wo, 'files'))

    def test_layer_4_double_star_entry(self):
        """TASK-080 AC3: a "**" entry of read_set.paths selects the files under it."""
        inp = inputs()
        inp['contract']['read_set']['paths'].append('tests/**')
        inp['files']['tests/unit/a/b.py'] = 't'
        inp['files']['testsx/c.py'] = 'u'
        got = refs(self.built(inp), 'files')
        self.assertIn('tests/unit/a/b.py', got)
        self.assertNotIn('testsx/c.py', got)

    def test_layer_4_pattern_matching_no_file(self):
        """TASK-080 AC3: a pattern matching no file gives no item and no finding."""
        inp = inputs()
        inp['contract']['write_set']['paths'].append('src/new/none.py')
        self.assertNotIn('src/new/none.py', refs(self.built(inp), 'files'))

    def test_layer_4_without_the_interface(self):
        """TASK-080 AC3: without the read_set.interfaces entry, the interface component's files are absent."""
        inp = inputs()
        inp['contract']['read_set']['interfaces'] = []
        inp['contract']['read_set']['schemas'] = []
        got = refs(self.built(inp), 'files')
        self.assertNotIn('lib/api/client.py', got)
        self.assertNotIn('lib/api/order.json', got)

    def test_layer_5(self):
        """TASK-080 AC3: layer 5 holds the last handoff, or no item."""
        wo = self.built(inputs())
        self.assertEqual(layer(wo, 'handoff')['items'], [{'ref': 'handoffs/TASK-900-s-0.md', 'hash': sha('handoff'),
                                                          'content': 'handoff'}])
        inp = inputs()
        inp['last_handoff'] = None
        self.assertEqual(layer(self.built(inp), 'handoff')['items'], [])


class TASK080AC4Schemas(Base):
    def test_schema_resolves_under_an_interface_component(self):
        """TASK-080 AC4: a schema under a component named only by an interface resolves and is in layer 4."""
        inp = inputs()
        inp['components'][1]['paths'] = ['lib/api/**']
        inp['contract']['read_set']['interfaces'] = ['pkg.api']
        self.assertIn('lib/api/order.json', refs(self.built(inp), 'files'))

    def test_schema_resolves_under_a_met_component(self):
        """TASK-080 AC4: a schema under a component the write-set meets resolves; its file is in layer 4 by the schema
        alone."""
        inp = inputs()
        inp['contract']['read_set']['schemas'] = ['events']
        inp['files']['src/pkg/events.json'] = 'events schema'
        self.assertIn('src/pkg/events.json', refs(self.built(inp), 'files'))
        inp['contract']['read_set']['schemas'] = []
        self.assertNotIn('src/pkg/events.json', refs(self.built(inp), 'files'))

    def test_no_file_gives_findings(self):
        """TASK-080 AC4: a schema entry no file resolves gives findings."""
        inp = inputs()
        inp['contract']['read_set']['schemas'] = ['nothing']
        self.refused(inp)

    def test_a_file_outside_the_components_does_not_resolve(self):
        """TASK-080 AC4: a file of the schema's name under no selected component does not resolve."""
        inp = inputs()
        inp['contract']['read_set']['schemas'] = ['zeta']
        inp['files']['other/zeta.json'] = 'z'
        self.refused(inp)

    def test_two_files_give_findings(self):
        """TASK-080 AC4: a schema entry two files resolve gives findings."""
        inp = inputs()
        inp['files']['lib/api/sub/order.yaml'] = 'again'
        self.refused(inp)


class TASK080AC5ItemsAndBudgets(Base):
    def sized(self, budget):
        inp = inputs()
        inp['files'].update({'src/pkg/mod.py': 'x' * 10, 'docs/specs/x.md': 'y' * 5, 'lib/api/order.json': 'z' * 7,
                             'lib/api/client.py': 'w' * 7, 'derived/d.py': 'v'})
        inp['budgets']['files'] = budget
        return {i['ref']: i for i in layer(self.built(inp), 'files')['items']}

    def test_item_form(self):
        """TASK-080 AC5: every item is {ref, hash, content} with content a str and hash its SHA-256, ordered by ref."""
        wo = self.built(inputs())
        for x in wo['layers']:
            self.assertEqual([i['ref'] for i in x['items']], sorted(i['ref'] for i in x['items']))
            for i in x['items']:
                self.assertEqual(set(i), {'ref', 'hash', 'content'})
                self.assertIsInstance(i['content'], str)
                self.assertEqual(i['hash'], sha(i['content']))

    def test_code_point_order(self):
        """TASK-080 AC5: refs are ordered by code point, upper case before lower case."""
        inp = inputs()
        inp['derived_read_set'] = ['B.py', 'a.py', 'é.py']
        inp['files'].update({'B.py': '1', 'a.py': '2', 'é.py': '3'})
        got = [r for r in refs(self.built(inp), 'files') if r in ('B.py', 'a.py', 'é.py')]
        self.assertEqual(got, ['B.py', 'a.py', 'é.py'])

    def test_largest_first(self):
        """TASK-080 AC5: over the budget, the largest content becomes a reference first."""
        items = self.sized(20)
        self.assertEqual(sorted(r for r, i in items.items() if 'content' not in i), ['src/pkg/mod.py'])

    def test_ties_by_ref(self):
        """TASK-080 AC5: between two contents of one size, the first ref becomes a reference first."""
        items = self.sized(13)
        self.assertEqual(sorted(r for r, i in items.items() if 'content' not in i),
                         ['lib/api/client.py', 'src/pkg/mod.py'])
        self.assertEqual(items['lib/api/order.json']['content'], 'z' * 7)

    def test_exact_budget_keeps_every_content(self):
        """TASK-080 AC5: a budget equal to the layer's bytes keeps every content; one byte less does not."""
        self.assertTrue(all('content' in i for i in self.sized(30).values()))
        self.assertFalse(all('content' in i for i in self.sized(29).values()))

    def test_references_keep_the_hash_and_never_shorten(self):
        """TASK-080 AC5: a reference is {ref, hash} with the replaced content's hash; a kept content is whole."""
        items = self.sized(1)
        full = {'src/pkg/mod.py': 'x' * 10, 'docs/specs/x.md': 'y' * 5, 'lib/api/order.json': 'z' * 7,
                'lib/api/client.py': 'w' * 7, 'derived/d.py': 'v'}
        for r, i in items.items():
            self.assertEqual(i['hash'], sha(full[r]))
            if 'content' in i:
                self.assertEqual(i['content'], full[r])
            else:
                self.assertEqual(set(i), {'ref', 'hash'})
        self.assertEqual(sum(len(i.get('content', '').encode('utf-8')) for i in items.values()), 1)

    def test_budget_counts_utf8_bytes(self):
        """TASK-080 AC5: the budget counts UTF-8 bytes, not characters."""
        inp = inputs()
        inp['last_handoff']['text'] = 'é' * 5
        inp['budgets']['handoff'] = 9
        self.assertNotIn('content', layer(self.built(inp), 'handoff')['items'][0])
        inp['budgets']['handoff'] = 10
        self.assertIn('content', layer(self.built(inp), 'handoff')['items'][0])

    def test_large_budget_keeps_everything(self):
        """TASK-080 AC5: a budget large enough keeps every content of every layer."""
        wo = self.built(inputs())
        self.assertTrue(all('content' in i for x in wo['layers'] for i in x['items']))


class NoEnviron(dict):
    """A stand-in for os.environ that counts every read."""
    reads = 0

    def _read(self, *a, **k):
        NoEnviron.reads += 1
        raise AssertionError('the environment was read')

    __getitem__ = __contains__ = __iter__ = __len__ = get = keys = items = values = copy = _read


class TASK080AC6Purity(Base):
    def test_no_file_clock_environment_or_process(self):
        """TASK-080 AC6: with stand-ins installed after the import, build_work_order makes no open, time, environment
        or process call."""
        NoEnviron.reads = 0
        targets = ['builtins.open', 'io.open', 'time.time', 'time.time_ns', 'time.monotonic', 'time.perf_counter',
                   'time.localtime', 'time.gmtime', 'os.getenv', 'os.system', 'os.popen', 'subprocess.Popen',
                   'subprocess.run']
        patches = [mock.patch(t, side_effect=AssertionError(t)) for t in targets]
        mocks = [p.start() for p in patches]
        env = mock.patch('os.environ', new=NoEnviron())
        env.start()
        try:
            wo, findings = build(inputs())
        finally:
            env.stop()
            for p in patches:
                p.stop()
        self.assertIsNone(findings)
        self.assertIsNotNone(wo)
        self.assertEqual([m.call_count for m in mocks], [0] * len(mocks))
        self.assertEqual(NoEnviron.reads, 0)

    def test_inputs_not_mutated(self):
        """TASK-080 AC6: build_work_order mutates no input (deep-equal before and after), and the Work Order shares no
        object with the inputs."""
        inp = inputs()
        before = copy.deepcopy(inp)
        wo = self.built(inp)
        self.assertEqual(inp, before)
        wo['contract']['objective'] = 'changed'
        wo['layers'][3]['items'][0]['content'] = 'changed'
        self.assertEqual(inp, before)
        bad = inputs()
        bad['budgets']['files'] = 0
        before = copy.deepcopy(bad)
        self.refused(bad)
        self.assertEqual(bad, before)

    def test_imports_by_ast(self):
        """TASK-080 AC6: by ast, the module imports no module that reads a clock, the environment or a process."""
        tree = ast.parse(SRC.read_bytes().decode('utf-8'))
        imported = {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        imported |= {(n.module or '').split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        self.assertEqual(imported, {'hashlib', 'json', 'math', 're', 'aieos_bootstrap'})
        for name in ('os', 'time', 'datetime', 'subprocess', 'io', 'pathlib', 'random', 'socket'):
            self.assertNotIn(name, imported)


class TASK080AC7Touch(Base):
    def tree(self):
        return ast.parse(SRC.read_bytes().decode('utf-8'))

    def test_imports(self):
        """TASK-080 AC7: the module imports only the standard library and aieos_bootstrap.resume_check."""
        tree = self.tree()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    self.assertIn(a.name.split('.')[0], sys.stdlib_module_names)
            if isinstance(n, ast.ImportFrom):
                if n.module == 'aieos_bootstrap':
                    self.assertEqual([a.name for a in n.names], ['resume_check'])
                else:
                    self.assertIn((n.module or '').split('.')[0], sys.stdlib_module_names)

    def test_resume_check_attributes(self):
        """TASK-080 AC7: the attributes used on resume_check are exactly meet and matches; check is never named."""
        used = {n.attr for n in ast.walk(self.tree()) if isinstance(n, ast.Attribute)
                and isinstance(n.value, ast.Name) and n.value.id == 'resume_check'}
        self.assertEqual(used, {'meet', 'matches'})
        names = {n.id for n in ast.walk(self.tree()) if isinstance(n, ast.Name)}
        self.assertNotIn('check', names)

    def test_no_refused_names_or_calls(self):
        """TASK-080 AC7: no name compile or open, and no .open or .connect call."""
        tree = self.tree()
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertFalse(names & {'compile', 'open', 'exec', 'eval', '__import__', '__builtins__'})
        attrs = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertFalse(attrs & {'open', 'connect'})

    def test_no_refused_strings(self):
        """TASK-080 AC7: no ".aieos" string, no name of the benchmark folder with its slash, and no name of a conformance fixture folder."""
        raw = SRC.read_bytes()
        strings = [n.value for n in ast.walk(self.tree()) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertFalse(any('.aieos' in s for s in strings))
        self.assertNotIn(b'bench' + b'/', raw)
        dirs = (conformance.FIXTURE_DIR, conformance.RC_FIXTURE_DIR, conformance.RISK_FIXTURE_DIR,
                conformance.CB_FIXTURE_DIR)
        for d in dirs:
            self.assertNotIn(d.rsplit('/', 1)[1].encode('ascii'), raw)

    def test_no_pass_or_continue_handlers(self):
        """TASK-080 AC7: no try/except/pass and no try/except/continue."""
        for n in ast.walk(self.tree()):
            if isinstance(n, ast.ExceptHandler):
                self.assertFalse(any(isinstance(s, (ast.Pass, ast.Continue)) for s in n.body))

    def test_never_raises(self):
        """TASK-080 AC7: a failure inside the module is returned as findings, never raised."""
        with mock.patch.object(context_compiler, '_layers', side_effect=RuntimeError('made up')):
            findings = self.refused(inputs())
        self.assertIn('RuntimeError', findings[0])


PHRASES = ['a pure module', 'reads no file, no clock and no environment', 'never calls resume_check.check',
           'layer 1 is not recomputed', 'budgets are required', 'the largest content first, ties by ref',
           'never a summary', "this task's choice", 'S3b waits for M7', "the inputs' truth is the caller's"]


class TASK080AC9Docstring(Base):
    def test_docstring_phrases(self):
        """TASK-080 AC9: the module docstring holds AC9's phrases, whitespace read as single spaces."""
        doc = ' '.join(ast.get_docstring(ast.parse(SRC.read_bytes().decode('utf-8'))).split())
        for phrase in PHRASES:
            self.assertIn(phrase, doc)

    def test_naming(self):
        """TASK-080 AC9: every test of this module names "TASK-080 ACn" at the start of its docstring."""
        classes = [v for v in globals().values() if isinstance(v, type) and issubclass(v, unittest.TestCase)
                   and v.__module__ == __name__]
        self.assertGreater(len(classes), 5)
        for cls in classes:
            for name in unittest.TestLoader().getTestCaseNames(cls):
                self.assertRegex(getattr(cls, name).__doc__ or '', r'^TASK-080 AC\d+', name)


if __name__ == '__main__':
    unittest.main()
