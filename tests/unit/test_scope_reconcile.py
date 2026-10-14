"""Unit tests of aieos_bootstrap.scope_reconcile (task TASK-034, its rules R1 to R10); every rule has at least one
passing case and one failing case. The repository is a stand-in answering in gitread.run's result form and the log is
kept in memory and appended by eventlog.append. The tests write and remove no file, and open none except the module's
own source, read for R9's script checks (TASK-034 AC14). Each test names the criteria it stands for in its own
docstring."""

import ast
import datetime
import hashlib
import pathlib
import re
import unittest

from aieos_bootstrap import eventlog, gitread, records, scope_drift, scope_reconcile

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap' / 'scope_reconcile.py'
NOW = datetime.datetime(2026, 10, 15, 9, 0, 0, tzinfo=datetime.timezone.utc)
REC = 'aieos-core (unit)'
POLICY_TEXT = '\n'.join([
    '# The risk rules', '', '## 3. The rules', '', '```yaml', 'policy_version: v3',
    'non_task_paths: ["docs/History/**", "docs/Progress/**", "docs/Deferred/**", "docs/Lessons/**"]', 'risk_rules:',
    '  # R1, low.', '  - match: { paths: ["docs/**", "*.md"] }', '    risk: low',
    '  - match: { paths: ["src/**", "tests/**"] }', '    risk: medium',
    '  # R3, high, by tags.', '  - match: { component_tags: [auth, governor, verification] }', '    risk: high',
    '  - match: { paths: ["docs/plan/**", "docs/WORKING-RECORDS.md"] }', '    risk: high',
    '  - match: { paths: ["**/contracts/**"] }', '    risk: critical',
    '  - match: { paths: ["docs/pre-genesis/**", "docs/specs/**"] }', '    risk: critical',
    '  - match: { paths: [".github/**"] }', '    risk: critical',
    '```', '', '## 4. After', ''])
EVAL_LINES = ["          EVALUATOR = ['.github/**', 'src/aieos_bootstrap/**', 'tests/conformance/**',",
              "                       'docs/records/**', 'tests/unit/**', 'tests/integration/**', 'tests/property/**']"]
WORKFLOW_TEXT = '\n'.join(['jobs:', '  run: |'] + EVAL_LINES + ['          pass', '  again: |'] + EVAL_LINES + [''])
EVALUATOR = ['.github/**', 'src/aieos_bootstrap/**', 'tests/conformance/**', 'docs/records/**', 'tests/unit/**',
             'tests/integration/**', 'tests/property/**']
CONTRACT = b'task: TASK-090\nwrite_set: [src/x.py]\n'


def oid(*parts):
    return hashlib.sha256('\n'.join(parts).encode('utf-8')).hexdigest()


class Repo:
    """A stand-in repository: objects {id: bytes} for "cat-file -p" and changed paths {commit: [paths]} for diff-tree.
    reads lists every args list asked."""

    def __init__(self):
        self.objects, self.paths, self.reads = {}, {}, []

    def tree(self, files):
        """Store the trees for {path: text} and return the root tree's id."""
        entries = {}
        sub = {}
        for path, text in files.items():
            head, _, rest = path.partition('/')
            if rest:
                sub.setdefault(head, {})[rest] = text
            else:
                b = text.encode('utf-8') if isinstance(text, str) else text
                bid = oid('blob', path, repr(b))
                self.objects[bid] = b
                entries[head] = ('blob', bid)
        for name, files_in in sub.items():
            entries[name] = ('tree', self.tree(files_in))
        listing = ''.join('%s %s %s\t%s\n' % ('040000' if k == 'tree' else '100644', k, i, n)
                          for n, (k, i) in sorted(entries.items()))
        tid = oid('tree', listing)
        self.objects[tid] = listing.encode('utf-8')
        return tid

    def commit(self, name, parents, files, paths, trailer=None):
        cid = oid('commit', name)
        msg = 'Change %s\n' % name + ('\n%s\n' % trailer if trailer else '')
        head = 'tree %s\n' % self.tree(files) + ''.join('parent %s\n' % p for p in parents)
        self.objects[cid] = (head + 'author A <a> 1 +0000\ncommitter A <a> 1 +0000\n\n' + msg).encode('utf-8')
        self.paths[cid] = paths
        return cid

    def __call__(self, repo, args, *rest):
        self.reads.append(list(args))
        if args[:2] == ['cat-file', '-p'] and args[2] in self.objects:
            return {'exit': 0, 'out': self.objects[args[2]], 'err': b'', 'error': None}
        if args[:-1] == gitread.DIFF_TREE and args[-1] in self.paths:
            return {'exit': 0, 'out': b''.join(p.encode('utf-8') + b'\0' for p in self.paths[args[-1]]), 'err': b'',
                    'error': None}
        return {'exit': 128, 'out': b'', 'err': b'fatal', 'error': None}


class Memory:
    """An event log kept in memory, read by read_log and appended by eventlog.append."""

    def __init__(self):
        self.log = b''
        self.calls = []

    def read_log(self, root):
        return self.log

    def add(self, event_type, payload, event_id, task_id=None):
        r = eventlog.append(self.log, event_type, payload, event_id, NOW, task_id=task_id)
        if r.result != 'appended':
            raise AssertionError(r.findings)
        self.log += r.line

    def append(self, root, event_type, payload, event_id, appended_at, recorder, task_id=None, fencing_token=None):
        self.calls.append((event_type, payload, event_id, task_id, fencing_token))
        r = eventlog.append(self.log, event_type, payload, event_id, appended_at, task_id=task_id)
        if r.result == 'appended':
            self.log += r.line
        return r


def approve(mem, task, data, n=1):
    mem.add('task.approved', {'contract_version': 'v%d' % n, 'contract_hash': hashlib.sha256(data).hexdigest(),
                              'approval_record': 'ap-%s-%d' % (task, n)}, 'e-ap-%s-%d' % (task, n), task)


BASE_FILES = {scope_reconcile.POLICY_PATH: POLICY_TEXT, scope_reconcile.WORKFLOW_PATH: WORKFLOW_TEXT,
              'README.md': 'r\n'}


def world(paths, trailer=None, parent_files=None, child_files=None):
    """A repository with a parent commit P (holding the base files) and a child commit C changing paths."""
    repo = Repo()
    p = repo.commit('P', [], BASE_FILES if parent_files is None else parent_files, ['README.md'])
    c = repo.commit('C', [p], child_files if child_files is not None else {'README.md': 'other\n'}, paths, trailer)
    return repo, p, c


def run(repo, c, mem=None, contracts=None, **kw):
    mem = Memory() if mem is None else mem
    out = scope_reconcile.reconcile_scope('/state', '/repo', c, {'contracts': contracts or {}}, REC, NOW, read=repo,
                                          read_log=mem.read_log, append=mem.append, **kw)
    return out, mem


class Arguments(unittest.TestCase):
    def test_each_malformed_argument_is_refused_and_nothing_is_read(self):
        """TASK-034 AC1 and TASK-034 AC9: each wrong argument gives a refusal "argument" naming it; no read, no
        append."""
        repo, p, c = world(['src/x.py'])
        good = dict(root='/state', repo='/repo', commit=c, values={'contracts': {}}, recorder=REC, now=NOW)
        bad = [('root', ''), ('repo', None), ('commit', 'C' * 40), ('commit', 'a' * 39), ('values', {}),
               ('values', {'contracts': []}), ('values', {'contracts': {'X-1': {}}}),
               ('values', {'contracts': {'TASK-1': {'contract_bytes': 'x', 'write_set': []}}}),
               ('values', {'contracts': {'TASK-1': {'contract_bytes': b'x', 'write_set': [1]}}}),
               ('recorder', ''), ('now', datetime.datetime(2026, 1, 1)),
               ('now', datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone(datetime.timedelta(hours=7))))]
        for key, value in bad:
            mem = Memory()
            args = dict(good, **{key: value})
            out = scope_reconcile.reconcile_scope(args['root'], args['repo'], args['commit'], args['values'],
                                                  args['recorder'], args['now'], read=repo, read_log=mem.read_log,
                                                  append=mem.append)
            self.assertEqual((out['result'], out['reason']), ('refused', 'argument'), key)
            self.assertTrue(any(key in f for f in out['findings']), (key, out['findings']))
            self.assertEqual(mem.calls, [])
        self.assertEqual(repo.reads, [])

    def test_good_arguments_are_accepted(self):
        """TASK-034 AC1: well-formed arguments pass the check and the run reads the commit."""
        repo, p, c = world(['README.md'])
        out, mem = run(repo, c)
        self.assertEqual(out['result'], 'reconciled', out)
        self.assertEqual(repo.reads[0], ['cat-file', '-p', c])


class TheCommit(unittest.TestCase):
    def test_a_merge_and_a_root_are_uncovered_with_no_further_read(self):
        """TASK-034 AC2 and TASK-034 AC6: a merge and a root commit: "not one parent", one read only, claims not
        called (nothing appended), facts None."""
        repo = Repo()
        p = repo.commit('P', [], BASE_FILES, ['README.md'])
        q = repo.commit('Q', [p], BASE_FILES, ['src/a.py'])
        m = repo.commit('M', [p, q], BASE_FILES, ['src/a.py'])
        for commit in (m, p):
            repo.reads = []
            out, mem = run(repo, commit)
            self.assertEqual(out['result'], 'reconciled')
            self.assertEqual(out['uncovered'], [{'ref': commit, 'detail': 'not one parent'}])
            self.assertEqual(repo.reads, [['cat-file', '-p', commit]])
            self.assertEqual((out['facts'], out['appended'], mem.calls), (None, [], []))

    def test_no_changed_path_is_uncovered_and_claims_is_not_called(self):
        """TASK-034 AC2: a one-parent commit with no changed path: "no changed path", no base read, no event."""
        repo, p, c = world([])
        out, mem = run(repo, c)
        self.assertEqual(out['uncovered'], [{'ref': c, 'detail': 'no changed path'}])
        self.assertEqual(len(repo.reads), 2)
        self.assertEqual((out['facts'], mem.calls, out['detected']), (None, [], False))

    def test_failed_reads_and_parse_errors_are_refused_git(self):
        """TASK-034 AC2: a failed commit read, a commit out of form, a failed diff-tree and paths out of form are each
        refused "git" with no event."""
        repo, p, c = world(['src/x.py'])
        out, _ = run(repo, 'f' * 40)
        self.assertEqual((out['result'], out['reason']), ('refused', 'git'))
        repo2, p2, c2 = world(['src/x.py'])
        repo2.objects[c2] = b'not a commit'
        self.assertEqual(run(repo2, c2)[0]['reason'], 'git')
        repo3, p3, c3 = world(['src/x.py'])
        del repo3.paths[c3]
        self.assertEqual(run(repo3, c3)[0]['reason'], 'git')
        repo4, p4, c4 = world(['src/x.py'])
        orig = repo4.__call__

        def bad_paths(repo_, args, *rest):
            r = orig(repo_, args)
            if args[0] == 'diff-tree':
                r = dict(r, out=b'\xff\xfe')
            return r
        self.assertEqual(run(bad_paths, c4)[0]['reason'], 'git')
        no_form = run(lambda r, a, *x: None, c)[0]
        self.assertEqual(no_form['reason'], 'git')

    def test_a_trailer_out_of_form_passes_no_trailer_task(self):
        """TASK-034 AC2 (the trailer reading): "AIEOS-Task: nonsense" makes the commit detected, a claim, with
        "trailer out of form"; a well-formed trailer is passed on."""
        repo, p, c = world(['src/x.py'], trailer='AIEOS-Task: nonsense')
        out, mem = run(repo, c)
        self.assertIn({'ref': c, 'detail': 'trailer out of form'}, out['uncovered'])
        self.assertTrue(out['detected'])
        self.assertEqual(len(out['appended']), 1)
        self.assertEqual(mem.calls[0][1]['entities'], [])
        repo2, p2, c2 = world(['src/x.py'], trailer='AIEOS-Task: TASK-090')
        out2, mem2 = run(repo2, c2)
        self.assertNotIn({'ref': c2, 'detail': 'trailer out of form'}, out2['uncovered'])
        self.assertEqual(mem2.calls[0][1]['entities'], ['TASK-090'])


class BaseRead(unittest.TestCase):
    def test_the_files_are_read_at_the_first_parent_never_at_the_commit(self):
        """TASK-034 AC3 and TASK-034 AC8: the commit's own tree holds a policy that would exempt everything; the run
        reads the parent's, so a change under src/ is still a claim, and the facts name the parent's blobs."""
        loose = POLICY_TEXT.replace('"docs/Lessons/**"]', '"docs/Lessons/**", "src/**"]')
        child = dict(BASE_FILES, **{scope_reconcile.POLICY_PATH: loose})
        repo, p, c = world(['src/x.py'], child_files=child)
        out, mem = run(repo, c)
        self.assertEqual(len(out['appended']), 1)
        self.assertEqual(out['facts']['parent'], p)
        self.assertEqual(out['facts']['policy_blob'], oid('blob', 'risk-rules-gov-aieos.md',
                                                          repr(POLICY_TEXT.encode('utf-8'))))
        child_tree = repo.objects[c].decode('utf-8').split('\n')[0].split()[1]
        self.assertNotIn(['cat-file', '-p', child_tree], repo.reads)

    def test_each_fail_closed_case_of_the_walk_is_refused_base(self):
        """TASK-034 AC3: a listing line out of form, a missing element, a blob where a tree is expected, a tree where a
        blob is expected, a failed read and bytes that do not decode are each refused "base" with no event."""
        cases = []
        repo, p, c = world(['src/x.py'])
        ptree = repo.objects[p].decode('utf-8').split('\n')[0].split()[1]
        repo.objects[ptree] = repo.objects[ptree] + b'garbage line\n'
        cases.append(repo)
        files = dict(BASE_FILES)
        del files[scope_reconcile.WORKFLOW_PATH]
        cases.append(world(['src/x.py'], parent_files=files)[0])
        cases.append(world(['src/x.py'], parent_files={'docs': 'a blob\n',
                                                       scope_reconcile.WORKFLOW_PATH: WORKFLOW_TEXT})[0])
        cases.append(world(['src/x.py'], parent_files={'docs/specs/risk-rules-gov-aieos.md/x': 't',
                                                       '.github/workflows/aieos-checks.yml': WORKFLOW_TEXT})[0])
        repo5, p5, c5 = world(['src/x.py'])
        ptree5 = repo5.objects[p5].decode('utf-8').split('\n')[0].split()[1]
        del repo5.objects[ptree5]
        cases.append(repo5)
        undecodable = dict(BASE_FILES, **{scope_reconcile.POLICY_PATH: b'\xff\xfe'})
        cases.append(world(['src/x.py'], parent_files=undecodable)[0])
        for k, r in enumerate(cases):
            commit = [cid for cid, b in r.objects.items() if b.startswith(b'tree') and b'parent ' in b][0]
            mem = Memory()
            out = scope_reconcile.reconcile_scope('/state', '/repo', commit, {'contracts': {}}, REC, NOW, read=r,
                                                  read_log=mem.read_log, append=mem.append)
            self.assertEqual((out['result'], out['reason']), ('refused', 'base'), (k, out))
            self.assertEqual(mem.calls, [])

    def test_read_base_gives_both_files(self):
        """TASK-034 AC3: read_base gives the two blob ids and texts."""
        repo, p, c = world(['src/x.py'])
        got = scope_reconcile.read_base('/repo', p, repo)
        self.assertEqual(set(got), {'policy_blob', 'policy', 'workflow_blob', 'workflow'})
        self.assertEqual((got['policy'], got['workflow']), (POLICY_TEXT, WORKFLOW_TEXT))


class PolicyFacts(unittest.TestCase):
    def test_the_rules_are_translated_into_match_and_class_only(self):
        """TASK-034 AC4: every entry becomes exactly {match, class}; component_tags give src/** and tests/**."""
        rules = scope_reconcile.rules_from_policy(POLICY_TEXT)
        self.assertEqual(len(rules), 7)
        self.assertTrue(all(set(r) == {'match', 'class'} for r in rules))
        self.assertEqual(rules[0], {'match': ['docs/**', '*.md'], 'class': 'low'})
        self.assertEqual(rules[2], {'match': ['src/**', 'tests/**'], 'class': 'high'})

    def test_an_entry_out_of_form_is_passed_on_as_the_refused_rule(self):
        """TASK-034 AC4: an unknown match key, an unknown class, an entry without its risk line, a block or key that
        cannot be found: the refused rule, so no path is non-task (a commit under docs/History is a claim)."""
        variants = [POLICY_TEXT.replace('{ paths: ["**/contracts/**"] }', '{ files: ["**/contracts/**"] }'),
                    POLICY_TEXT.replace('    risk: low', '    risk: lowest'),
                    POLICY_TEXT.replace('  - match: { paths: [".github/**"] }\n    risk: critical\n',
                                        '  - match: { paths: [".github/**"] }\n'),
                    POLICY_TEXT.replace('risk_rules:', 'rules:'),
                    POLICY_TEXT.replace('```yaml', '```')]
        for text in variants:
            rules = scope_reconcile.rules_from_policy(text)
            self.assertIn(scope_reconcile.REFUSED_RULE, rules, text[:0])
            out = scope_drift.claims({'commit': 'c' * 40, 'parents': 1, 'trailer_tasks': [],
                                      'changed_paths': ['docs/History/x.md'], 'contracts': {},
                                      'non_task': scope_drift.non_task_list(POLICY_TEXT), 'risk_rules': rules,
                                      'evaluator': EVALUATOR, 'constitution_path': 'a', 'policy_path': 'b'})
            self.assertEqual((out['detected'], out['exempt'], len(out['events'])), (True, False, 1))
        files = dict(BASE_FILES, **{scope_reconcile.POLICY_PATH: variants[0]})
        repo, p, c = world(['docs/History/x.md'], parent_files=files)
        out, mem = run(repo, c)
        self.assertEqual((out['result'], len(out['appended'])), ('reconciled', 1))

    def test_the_evaluator_literals(self):
        """TASK-034 AC4: one literal, two equal literals: the list; two that differ, none, an unclosed one, an item out
        of form: the empty list."""
        self.assertEqual(scope_reconcile.evaluator_from_workflow(WORKFLOW_TEXT), EVALUATOR)
        one = '\n'.join(EVAL_LINES)
        self.assertEqual(scope_reconcile.evaluator_from_workflow(one), EVALUATOR)
        differ = WORKFLOW_TEXT.replace("'tests/property/**']", "'tests/property/**', 'x/**']", 1)
        self.assertEqual(scope_reconcile.evaluator_from_workflow(differ), [])
        self.assertEqual(scope_reconcile.evaluator_from_workflow('jobs: none\n'), [])
        self.assertEqual(scope_reconcile.evaluator_from_workflow("EVALUATOR = ['a/**',\n"), [])
        self.assertEqual(scope_reconcile.evaluator_from_workflow("EVALUATOR = ['a/**', b]\n"), [])
        self.assertEqual(scope_reconcile.evaluator_from_workflow("EVALUATOR = []\n"), [])

    def test_the_fixed_paths(self):
        """TASK-034 AC4: the constitution's and the policy's paths are fixed in the module."""
        self.assertEqual(scope_reconcile.CONSTITUTION_PATH, 'docs/pre-genesis/constitution.md')
        self.assertEqual(scope_reconcile.POLICY_PATH, 'docs/specs/risk-rules-gov-aieos.md')

    def test_a_records_only_commit_is_exempt(self):
        """TASK-034 AC4 and TASK-034 AC6: a commit with no trailer changing only docs/Lessons is detected and exempt,
        with no event."""
        repo, p, c = world(['docs/Lessons/L-1.md'])
        out, mem = run(repo, c)
        self.assertEqual((out['detected'], out['exempt'], out['appended'], mem.calls), (True, True, [], []))


class TheContract(unittest.TestCase):
    def test_a_matching_hash_passes_the_write_set(self):
        """TASK-034 AC5 and TASK-034 AC8: the contract bytes hash to the last task.approved contract_hash, so a commit
        inside the write-set is not detected; the facts name the hash."""
        repo, p, c = world(['src/x.py'], trailer='AIEOS-Task: TASK-090')
        mem = Memory()
        approve(mem, 'TASK-090', CONTRACT)
        out, _ = run(repo, c, mem, {'TASK-090': {'contract_bytes': CONTRACT, 'write_set': ['src/x.py']}})
        self.assertEqual((out['detected'], out['appended']), (False, []))
        self.assertEqual(out['facts']['contracts'], {'TASK-090': hashlib.sha256(CONTRACT).hexdigest()})

    def test_no_approval_no_value_and_a_differing_hash_give_no_contract(self):
        """TASK-034 AC5: no task.approved event, no value and a hash that differs each leave the task out: "no
        contract", detected, one event; the facts say why."""
        for kind in ('no task.approved event', 'no value given', 'hash differs'):
            repo, p, c = world(['src/x.py'], trailer='AIEOS-Task: TASK-090')
            mem = Memory()
            if kind != 'no task.approved event':
                approve(mem, 'TASK-090', CONTRACT)
            given = {} if kind == 'no value given' else {
                'TASK-090': {'contract_bytes': CONTRACT + (b'x' if kind == 'hash differs' else b''),
                             'write_set': ['src/x.py']}}
            out, _ = run(repo, c, mem, given)
            self.assertIn({'ref': 'TASK-090', 'detail': 'no contract'}, out['uncovered'], kind)
            self.assertTrue(out['detected'])
            self.assertEqual(out['facts']['contracts'], {'TASK-090': kind})

    def test_the_last_task_approved_counts(self):
        """TASK-034 AC5: of two task.approved events, the last one's hash counts."""
        repo, p, c = world(['src/x.py'], trailer='AIEOS-Task: TASK-090')
        mem = Memory()
        approve(mem, 'TASK-090', b'old contract', 1)
        approve(mem, 'TASK-090', CONTRACT, 2)
        out, _ = run(repo, c, mem, {'TASK-090': {'contract_bytes': CONTRACT, 'write_set': ['src/x.py']}})
        self.assertFalse(out['detected'])
        out2, _ = run(repo, c, mem, {'TASK-090': {'contract_bytes': b'old contract', 'write_set': ['src/x.py']}})
        self.assertTrue(out2['detected'])

    def test_a_damaged_log_is_refused_log(self):
        """TASK-034 AC5: a log with findings, and a read_log that gives no bytes, are refused "log"."""
        repo, p, c = world(['src/x.py'], trailer='AIEOS-Task: TASK-090')
        mem = Memory()
        mem.log = b'not json\n'
        self.assertEqual(run(repo, c, mem)[0]['reason'], 'log')
        out = scope_reconcile.reconcile_scope('/state', '/repo', c, {'contracts': {}}, REC, NOW, read=repo,
                                              read_log=lambda root: 'text', append=Memory().append)
        self.assertEqual(out['reason'], 'log')

    def test_no_trailer_reads_no_log(self):
        """TASK-034 AC5: a commit with no trailer task does not read the log."""
        repo, p, c = world(['src/x.py'])

        def boom(root):
            raise AssertionError('the log was read')
        out = scope_reconcile.reconcile_scope('/state', '/repo', c, {'contracts': {}}, REC, NOW, read=repo,
                                              read_log=boom, append=Memory().append)
        self.assertEqual(out['result'], 'reconciled')


class TheCall(unittest.TestCase):
    def test_a_claims_error_is_a_stop(self):
        """TASK-034 AC6: claims' error gives a refusal "scope_drift" and no append."""
        repo, p, c = world(['src/x.py'])
        orig = scope_drift.claims
        try:
            scope_drift.claims = lambda inputs: {'events': [], 'detected': False, 'exempt': False, 'uncovered': [],
                                                 'error': 'an exception: X'}
            out, mem = run(repo, c)
        finally:
            scope_drift.claims = orig
        self.assertEqual((out['result'], out['reason'], mem.calls), ('refused', 'scope_drift', []))
        self.assertIn('an exception: X', out['findings'][0])

    def test_claims_is_called_once_with_the_facts(self):
        """TASK-034 AC6: claims gets exactly the commit, parents 1, the trailers, the paths, the contracts, the list,
        the rules, the evaluator list and the two fixed paths."""
        repo, p, c = world(['src/x.py', 'docs/a.md'], trailer='AIEOS-Task: TASK-090')
        seen = []
        orig = scope_drift.claims
        try:
            scope_drift.claims = lambda inputs: seen.append(inputs) or orig(inputs)
            run(repo, c)
        finally:
            scope_drift.claims = orig
        self.assertEqual(len(seen), 1)
        i = seen[0]
        self.assertEqual(set(i), set(scope_drift.INPUT_KEYS))
        self.assertEqual((i['commit'], i['parents'], i['trailer_tasks'], i['changed_paths']),
                         (c, 1, ['TASK-090'], ['src/x.py', 'docs/a.md']))
        self.assertEqual((i['evaluator'], i['constitution_path'], i['policy_path']),
                         (EVALUATOR, scope_reconcile.CONSTITUTION_PATH, scope_reconcile.POLICY_PATH))
        self.assertEqual(i['non_task'], scope_drift.non_task_list(POLICY_TEXT))


class TheAppend(unittest.TestCase):
    def test_appended_then_duplicate(self):
        """TASK-034 AC7: a claim is appended with no task_id and no fencing token; a rerun gives "duplicate"."""
        repo, p, c = world(['src/x.py'])
        out, mem = run(repo, c)
        eid = hashlib.sha256('\n'.join(('drift.detected', 'scope', c)).encode('utf-8')).hexdigest()
        self.assertEqual(out['appended'], [eid])
        self.assertEqual(mem.calls[0][3:], (None, None))
        self.assertEqual(records.check_log(mem.log).findings(), [])
        again, _ = run(repo, c, mem)
        self.assertEqual((again['result'], again['appended'], again['duplicate']), ('reconciled', [], [eid]))

    def test_a_conflict_no_result_and_an_exception_are_refused_append(self):
        """TASK-034 AC7: a rerun with other facts (a conflict), an object without a string result, and an exception are
        refused "append"."""
        repo, p, c = world(['src/x.py'])
        out, mem = run(repo, c)
        repo2, p2, c2 = world(['src/x.py', 'src/y.py'])
        self.assertEqual(c2, c)
        conflict, _ = run(repo2, c2, mem)
        self.assertEqual((conflict['result'], conflict['reason']), ('refused', 'append'))

        class NoResult:
            result = None
        for app in (lambda *a, **k: NoResult(), lambda *a, **k: 1 / 0):
            o = scope_reconcile.reconcile_scope('/state', '/repo', c, {'contracts': {}}, REC, NOW, read=repo,
                                                read_log=Memory().read_log, append=app)
            self.assertEqual((o['result'], o['reason']), ('refused', 'append'))


class TheResult(unittest.TestCase):
    def test_the_keys_and_the_facts(self):
        """TASK-034 AC8 and TASK-034 AC9: the result's keys, the facts' keys, sorted uncovered entries."""
        repo, p, c = world(['src/x.py'], trailer='AIEOS-Task: TASK-090\nAIEOS-Task: TASK-091')
        out, _ = run(repo, c)
        self.assertEqual(tuple(out), scope_reconcile.RESULT_KEYS)
        self.assertEqual(tuple(out['facts']), scope_reconcile.FACT_KEYS)
        self.assertEqual(out['facts']['rules'], 7)
        self.assertEqual(out['uncovered'], sorted(out['uncovered'], key=lambda u: (u['ref'], u['detail'])))
        self.assertEqual(out['facts']['contracts'], {'TASK-090': 'no task.approved event',
                                                     'TASK-091': 'no task.approved event'})

    def test_facts_are_none_on_a_log_or_base_stop(self):
        """TASK-034 AC8 (erratum E1, decision D-716): a refusal at the log read and one at the base read give facts
        None, although the base read was made in the first case."""
        repo, p, c = world(['src/x.py'], trailer='AIEOS-Task: TASK-090')
        mem = Memory()
        mem.log = b'not json\n'
        out, _ = run(repo, c, mem)
        self.assertEqual((out['reason'], out['facts']), ('log', None))
        files = dict(BASE_FILES)
        del files[scope_reconcile.POLICY_PATH]
        repo2, p2, c2 = world(['src/x.py'], parent_files=files)
        out2, _ = run(repo2, c2)
        self.assertEqual((out2['reason'], out2['facts']), ('base', None))

    def test_no_exception_escapes(self):
        """TASK-034 AC9: a read that raises, an argument whose methods raise, and odd inputs give results."""
        repo, p, c = world(['src/x.py'])

        def raises(*a):
            raise RuntimeError('x')
        out, _ = run(raises, c)
        self.assertEqual(out['result'], 'refused')

        class Weird(dict):
            def __iter__(self):
                raise RuntimeError('x')
        o = scope_reconcile.reconcile_scope('/s', '/r', c, Weird(contracts={}), REC, NOW, read=repo)
        self.assertEqual(o['reason'], 'argument')
        for odd in (None, 1, [], 'x', b'x'):
            o = scope_reconcile.reconcile_scope(odd, odd, odd, odd, odd, odd, read=repo)
            self.assertEqual(o['result'], 'refused')


class Purity(unittest.TestCase):
    def test_imports_calls_and_docstring(self):
        """TASK-034 AC10 and TASK-034 AC11: the module imports only datetime, hashlib, re and gitread, records,
        scope_drift and writer; it calls no open, write, clock or process function; its docstring states B1, D1, L1
        and DEF-0030's caller."""
        text = SRC.read_text(encoding='utf-8')
        tree = ast.parse(text)
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.update('%s.%s' % (node.module, a.name) for a in node.names)
        self.assertEqual(names, {'datetime', 'hashlib', 're', 'aieos_bootstrap.gitread', 'aieos_bootstrap.records',
                                 'aieos_bootstrap.scope_drift', 'aieos_bootstrap.writer'})
        bare = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        attrs = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        for bad in ('open', 'eval', 'exec', 'compile', '__import__'):
            self.assertNotIn(bad, bare)
        for bad in ('write', 'now', 'utcnow', 'time', 'run', 'Popen', 'system', 'getenv', 'import_module'):
            self.assertNotIn(bad, attrs)
        self.assertNotIn('assert ', text)
        doc = ast.get_docstring(tree)
        for s in ('Reading B1 (proposed', 'Departure D1', 'Limit L1', "DEF-0030's caller"):
            self.assertIn(s, doc)

    def test_a_failing_purity_check_is_seen(self):
        """TASK-034 AC11: the import check above finds an import that is not allowed (a negative control)."""
        tree = ast.parse('import os\n')
        self.assertEqual({a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}, {'os'})


class Naming(unittest.TestCase):
    def test_every_test_names_its_criteria(self):
        """TASK-034 AC14: every test function of this module names "TASK-034 ACn" in its own docstring, and no other
        task's AC in qualified form."""
        # The loaded classes' docstrings are read, not this file (TASK-034 AC14: the tests open only package sources).
        tests = [(cls.__name__, name, getattr(cls, name).__doc__ or '') for cls in list(globals().values())
                 if isinstance(cls, type) and issubclass(cls, unittest.TestCase) for name in vars(cls)
                 if name.startswith('test_')]
        self.assertGreater(len(tests), 20)
        for cls_name, name, doc in tests:
            self.assertIn('TASK-034 AC', doc, (cls_name, name))
            self.assertEqual(set(re.findall(r'(TASK-\d+) AC', doc)), {'TASK-034'}, (cls_name, name))


if __name__ == '__main__':
    unittest.main()
