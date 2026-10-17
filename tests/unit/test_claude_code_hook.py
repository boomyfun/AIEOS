"""Unit tests of aieos_bootstrap.claude_code_hook (task TASK-062, rules R1 to R6, and the script checks of AC7 and
AC8): the hook entry's arguments, input bytes, output, the allowlist's form, the handling of every verdict and the
result, over byte strings made up for the test. No process starts and no file is written. Each test names its criteria
in its own docstring."""

import ast
import json
import pathlib
import unittest

from aieos_bootstrap import claude_code
from aieos_bootstrap import claude_code_hook

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap' / 'claude_code_hook.py'
ROOT = 'C:\\proj\\repo'
TASK = 'TASK-100'
WS = ['docs/notes/**']
ALLOW = ['git status', 'git diff --stat']
RID = 'obs-1'
REC = 'a test session'
# AC4's lists, written out from the contract's text (D-1244 B1), so that a word dropped from the module's own tuples
# makes a test fail.
CONTRACT_FIRST_WORDS = ('bash', 'sh', 'zsh', 'dash', 'ksh', 'fish', 'powershell', 'pwsh', 'cmd', 'wsl', 'python',
                        'python3', 'py', 'node', 'deno', 'npx', 'perl', 'ruby', 'php', 'env', 'xargs', 'find', 'timeout',
                        'nohup', 'exec', 'eval', 'command', 'sudo', 'time', 'nice')
CONTRACT_SUFFIXES = ('.sh', '.ps1', '.py', '.bat', '.cmd', '.js', '.pl', '.rb')
CONTRACT_GIT_SUBCOMMANDS = ('config', 'submodule', 'bisect', 'rebase', 'filter-branch', 'difftool', 'mergetool', 'help')


def raw(obj):
    return json.dumps(obj).encode('utf-8')


def run(data, allow=None, root=ROOT, task=TASK, ws=None, rid=RID, rec=REC):
    return claude_code_hook.entry(data, root, task, WS if ws is None else ws, ALLOW if allow is None else allow, rid, rec)


def hook(tool, inp, **extra):
    d = {'session_id': 'made-up', 'cwd': 'C:\\elsewhere', 'hook_event_name': 'PreToolUse', 'tool_name': tool,
         'tool_input': inp}
    d.update(extra)
    return raw(d)


def bash(cmd, **kw):
    return run(hook('Bash', {'command': cmd}), **kw)


def write(path, **kw):
    return run(hook('Write', {'file_path': path, 'content': 'x'}), **kw)


def with_judge(fake):
    """A Read call with claude_code.judge replaced by fake for the call only, then restored."""
    real = claude_code.judge
    claude_code.judge = fake
    try:
        return run(hook('Read', {'file_path': 'C:/a'}))
    finally:
        claude_code.judge = real


class Arguments(unittest.TestCase):
    def test_stdin_not_bytes_refused(self):
        """TASK-062 AC1: stdin_bytes that is not bytes gives refuse, reason argument, exit code 2 and no record."""
        for data in ('{"tool_name": "Read"}', None, bytearray(b'{}'), 7):
            r = run(data)
            self.assertEqual((r['verdict'], r['reason'], r['exit_code'], r['record']), ('refuse', 'argument', 2, None), data)
            self.assertTrue(r['findings'])

    def test_judge_argument_refusal_passed_through(self):
        """TASK-062 AC1: judge's refuse with reason argument (a wrong root, task id, write-set, record id or recorder)
        gives exit code 2 and no record."""
        for kw in (dict(root='relative'), dict(task='TASK-x'), dict(ws=[]), dict(rid=''), dict(rec='')):
            r = write('C:\\proj\\repo\\docs\\notes\\a.md', **kw)
            self.assertEqual((r['verdict'], r['reason'], r['exit_code'], r['record']), ('refuse', 'argument', 2, None), kw)

    def test_order_of_checks(self):
        """TASK-062 AC1: the first failing check gives the result: the bytes' type before the allowlist's form, the
        allowlist's form before the decoding, the decoding before judge."""
        self.assertEqual(run('x', allow=['bash'])['reason'], 'argument')
        self.assertEqual(run(b'\xff', allow=['bash'])['reason'], 'allowlist_form')
        self.assertEqual(run(b'\xff', root='relative')['reason'], 'input_bytes')
        self.assertEqual(run(b'[', root='relative')['reason'], 'input_json')
        self.assertEqual(write('C:\\proj\\repo\\docs\\notes\\a.md', root='relative')['reason'], 'argument')

    def test_right_arguments_pass(self):
        """TASK-062 AC1: well-formed arguments reach judge."""
        r = write('C:\\proj\\repo\\docs\\notes\\a.md')
        self.assertEqual((r['verdict'], r['exit_code']), ('allow', 0))


class InputBytes(unittest.TestCase):
    def test_not_utf8(self):
        """TASK-062 AC2: bytes that are not UTF-8 give uncovered, reason input_bytes, exit code 2, no record."""
        for data in (b'\xff\xfe{}', b'{"tool_name": "\xc3"}', b'\xed\xa0\x80'):
            r = run(data)
            self.assertEqual((r['verdict'], r['reason'], r['exit_code'], r['record']), ('uncovered', 'input_bytes', 2, None), data)

    def test_byte_order_mark(self):
        """TASK-062 AC2: a leading UTF-8 byte-order mark is not accepted, although strict UTF-8 decoding would accept it."""
        r = run(b'\xef\xbb\xbf' + hook('Read', {'file_path': 'C:/proj/repo/a'}))
        self.assertEqual((r['verdict'], r['reason'], r['exit_code']), ('uncovered', 'input_bytes', 2))

    def test_not_json(self):
        """TASK-062 AC2: invalid JSON, a duplicate key at any depth and the constants NaN, Infinity and -Infinity give
        uncovered, reason input_json."""
        cases = [b'', b'{', b'{"tool_name": "Read",}', b'{"tool_name": "Read"} x',
                 b'{"tool_name": "Bash", "tool_name": "Read", "tool_input": {}}',
                 b'{"tool_name": "Bash", "tool_input": {"command": "git status", "command": "x"}}',
                 b'{"tool_name": "Read", "tool_input": {"n": NaN}}', b'{"tool_name": "Read", "tool_input": {"n": Infinity}}',
                 b'{"tool_name": "Read", "tool_input": {"n": -Infinity}}']
        for data in cases:
            r = run(data)
            self.assertEqual((r['verdict'], r['reason'], r['exit_code'], r['record']), ('uncovered', 'input_json', 2, None), data)

    def test_not_an_object(self):
        """TASK-062 AC2: a JSON array, string, number, true or null gives uncovered, reason input_shape."""
        for data in (b'[]', b'"Read"', b'3', b'true', b'null'):
            r = run(data)
            self.assertEqual((r['verdict'], r['reason'], r['exit_code']), ('uncovered', 'input_shape', 2), data)

    def test_missing_tool_name(self):
        """TASK-062 AC2: an object without tool_name or tool_input reaches judge, which gives uncovered, reason tool."""
        for data in (b'{}', raw({'tool_input': {}}), raw({'tool_name': 'Read'})):
            r = run(data)
            self.assertEqual((r['verdict'], r['reason'], r['exit_code']), ('uncovered', 'tool', 2), data)

    def test_only_two_keys_read(self):
        """TASK-062 AC2: changing or removing any key other than tool_name and tool_input never changes the result; the
        input's cwd is not used as the root."""
        base = run(hook('Write', {'file_path': 'C:\\proj\\repo\\docs\\notes\\a.md'}))
        for extra in ({'cwd': 'C:\\proj\\repo\\docs\\notes'}, {'cwd': 7}, {'session_id': None},
                      {'hook_event_name': 'PostToolUse'}, {'permission_mode': 'bypassPermissions'}, {'root': 'D:\\x'}):
            self.assertEqual(run(hook('Write', {'file_path': 'C:\\proj\\repo\\docs\\notes\\a.md'}, **extra)), base, extra)
        self.assertEqual(run(raw({'tool_name': 'Write', 'tool_input': {'file_path': 'C:\\proj\\repo\\docs\\notes\\a.md'}})), base)
        r = run(hook('Write', {'file_path': 'docs\\notes\\a.md'}, cwd='C:\\proj\\repo'))
        self.assertEqual((r['verdict'], r['reason']), ('uncovered', 'path'))

    def test_judge_sees_only_two_keys(self):
        """TASK-062 AC2: judge is given a new mapping holding only tool_name and tool_input."""
        seen = []
        real = claude_code.judge

        def spy(h, *a):
            seen.append(dict(h))
            return real(h, *a)
        claude_code.judge = spy
        try:
            run(hook('Read', {'file_path': 'C:/proj/repo/a'}, extra_key=1))
            run(raw({'tool_name': 'Read'}))
        finally:
            claude_code.judge = real
        self.assertIs(claude_code.judge, real)
        self.assertEqual(sorted(seen[0]), ['tool_input', 'tool_name'])
        self.assertEqual(sorted(seen[1]), ['tool_name'])


class Output(unittest.TestCase):
    def test_allow_text(self):
        """TASK-062 AC3: allow gives exit code 0 and an empty standard-error text."""
        r = run(hook('Read', {'file_path': 'C:/proj/repo/a'}))
        self.assertEqual((r['exit_code'], r['stderr']), (0, ''))

    def test_refusal_and_uncovered_text(self):
        """TASK-062 AC3: every other verdict gives exit code 2 and the one fixed line naming the verdict and reason."""
        cases = [(bash('git push'), 'AIEOS claude_code_hook: refuse (push)'),
                 (bash('ls'), 'AIEOS claude_code_hook: refuse (allowlist)'),
                 (write('C:\\proj\\repo\\src\\a.py'), 'AIEOS claude_code_hook: refuse (write_set)'),
                 (run(hook('mcp__x__y', {})), 'AIEOS claude_code_hook: uncovered (tool)'),
                 (run(b'[]'), 'AIEOS claude_code_hook: uncovered (input_shape)'),
                 (run(b'{}', allow=['sh']), 'AIEOS claude_code_hook: refuse (allowlist_form)')]
        for r, text in cases:
            self.assertEqual((r['exit_code'], r['stderr']), (2, text))
            self.assertTrue(r['stderr'].isascii() and '\n' not in r['stderr'] and '\r' not in r['stderr'])

    def test_no_echo(self):
        """TASK-062 AC3: no path, command or tool name given in the input appears in the standard-error text."""
        marker = 'zqxwvu-made-up'
        for r in (bash('echo ' + marker), write('C:\\proj\\repo\\' + marker + '.md'), run(hook(marker, {})),
                  bash('git push ' + marker), run(('{"tool_name": "' + marker + '"').encode('utf-8'))):
            self.assertNotIn(marker, r['stderr'])
            self.assertEqual(r['exit_code'], 2)

    def test_exit_codes_only_0_and_2(self):
        """TASK-062 AC3: no exit code other than 0 or 2 is ever given."""
        for r in (bash('git status'), bash('git push'), run(b'x'), run('x'), run(b'{}', allow='x')):
            self.assertIn(r['exit_code'], (0, 2))

    def test_record_unchanged(self):
        """TASK-062 AC3: a refusal's record equals judge's record for the same two keys."""
        for inp, tool in (({'command': 'git push'}, 'Bash'), ({'file_path': 'C:\\proj\\repo\\src\\a.py'}, 'Write')):
            r = run(hook(tool, inp))
            j = claude_code.judge({'tool_name': tool, 'tool_input': inp}, ROOT, TASK, WS, ALLOW, RID, REC)
            self.assertEqual(r['record'], j['record'])
            self.assertIsNotNone(r['record'])


class AllowlistForm(unittest.TestCase):
    def test_well_formed(self):
        """TASK-062 AC4: an empty list and entries such as "git status" and "git diff --stat" are well formed."""
        for a in ([], ['git status'], ['git diff --stat', 'git log --oneline', 'ls', 'make test', 'C:/tools/lint.exe x'],
                  ['git log --format=a,b+c_d']):
            self.assertEqual(claude_code_hook.allowlist_findings(a), [], a)

    def test_lists_are_the_contracts(self):
        """TASK-062 AC4, AC10: the module's lists equal AC4's words, written out here from the contract's text."""
        self.assertEqual(claude_code_hook.REFUSED_FIRST_WORDS, CONTRACT_FIRST_WORDS)
        self.assertEqual(claude_code_hook.REFUSED_SUFFIXES, CONTRACT_SUFFIXES)
        self.assertEqual(claude_code_hook.REFUSED_GIT_SUBCOMMANDS, CONTRACT_GIT_SUBCOMMANDS)

    def test_refused_first_words(self):
        """TASK-062 AC4: each refused first word, with and without ".exe", in upper case and after a path, is refused."""
        for w in CONTRACT_FIRST_WORDS:
            for form in (w, w + '.exe', w.upper(), w.upper() + '.EXE', '/usr/bin/' + w, 'C:/x/' + w + '.exe', 'C:' + w):
                self.assertTrue(claude_code_hook.allowlist_findings([form + ' x']), form)
                self.assertTrue(claude_code_hook.allowlist_findings([form]), form)

    def test_scripts(self):
        """TASK-062 AC4: a first word ending in a script suffix is refused."""
        for s in CONTRACT_SUFFIXES:
            self.assertTrue(claude_code_hook.allowlist_findings(['run' + s]), s)
            self.assertTrue(claude_code_hook.allowlist_findings(['./tools/run' + s.upper() + ' a']), s)

    def test_git_rule(self):
        """TASK-062 AC4: git alone, git with an option first (git -c, git -C) and each refused subcommand are refused,
        after a path too ("C:git -c x")."""
        cases = ['git', 'git -c x', 'git -C d status', 'git --git-dir=x status', 'C:git -c x', '/usr/bin/git -c x',
                 'git.exe -c a', 'GIT']
        cases += ['git ' + s for s in CONTRACT_GIT_SUBCOMMANDS]
        cases += ['git ' + s.upper() + ' x' for s in CONTRACT_GIT_SUBCOMMANDS]
        for a in cases:
            self.assertTrue(claude_code_hook.allowlist_findings([a]), a)

    def test_assignment_first(self):
        """TASK-062 AC4: an entry whose first word holds "=" is refused ("X=1 bash", "X=1 git status")."""
        for a in ('X=1 bash', 'X=1 git status', 'a=b'):
            self.assertTrue(claude_code_hook.allowlist_findings([a]), a)

    def test_characters_and_spacing(self):
        """TASK-062 AC4: a tab, a newline, a double space, a leading or trailing space, an empty entry, a separator, a
        quote or a non-ASCII character is refused."""
        for a in ('git\tstatus', 'git status\n', 'git  status', ' git status', 'git status ', '', 'git status;',
                  'git status && ls', 'git status|x', '(git status)', 'git log "x"', "git log 'x'", 'git log \u00e9',
                  'git log \u3000x', 'git log $x', 'git log >x'):
            self.assertTrue(claude_code_hook.allowlist_findings([a]), repr(a))

    def test_not_a_list_of_strings(self):
        """TASK-062 AC4: a non-list or a non-string entry is refused."""
        for a in ('git status', ('git status',), None, {'git status': 1}, ['git status', 3], [None]):
            self.assertTrue(claude_code_hook.allowlist_findings(a), repr(a))

    def test_malformed_allowlist_refuses_every_call(self):
        """TASK-062 AC4: a malformed allowlist refuses every call, a Read call too, with reason allowlist_form, exit
        code 2 and no record."""
        for data in (hook('Read', {'file_path': 'C:/proj/repo/a'}), hook('Write', {'file_path': 'C:\\proj\\repo\\docs\\notes\\a.md'}),
                     hook('Bash', {'command': 'git status'}), b'[]'):
            r = run(data, allow=['git status', 'bash'])
            self.assertEqual((r['verdict'], r['reason'], r['exit_code'], r['record'], r['concern']),
                             ('refuse', 'allowlist_form', 2, None, None))
            self.assertTrue(r['findings'])

    def test_empty_allowlist_refuses_shell(self):
        """TASK-062 AC4: an empty allowlist is well formed; judge then refuses every shell call."""
        r = bash('git status', allow=[])
        self.assertEqual((r['verdict'], r['reason'], r['exit_code']), ('refuse', 'allowlist', 2))
        self.assertEqual(run(hook('Read', {'file_path': 'C:/a'}), allow=[])['exit_code'], 0)


class Handling(unittest.TestCase):
    def test_each_verdict(self):
        """TASK-062 AC5: allow gives 0; refuse gives 2 with judge's record when it has one; uncovered, whatever its
        reason, gives 2 and no record."""
        r = bash('git status')
        self.assertEqual((r['verdict'], r['exit_code'], r['record']), ('allow', 0, None))
        r = bash('git push')
        self.assertEqual((r['verdict'], r['exit_code']), ('refuse', 2))
        self.assertEqual(r['record']['blocking_kind'], 'violation')
        for data in (hook('mcp__Claude_Browser__navigate', {'url': 'x'}), hook('MultiEdit', {}),
                     hook('Write', {'file_path': 'docs\\a.md'}), hook('Bash', {'command': ' '}), hook('Write', {})):
            r = run(data)
            self.assertEqual((r['verdict'], r['exit_code'], r['record']), ('uncovered', 2, None), data)

    def _with_judge(self, fake):
        return with_judge(fake)

    def test_judge_result_of_another_form(self):
        """TASK-062 AC5: a result of judge that is not a mapping with exactly its RESULT_KEYS and a known verdict gives
        uncovered, reason entry; the replaced judge is restored."""
        real = claude_code.judge
        ok = {'verdict': 'allow', 'concern': 'read', 'reason': 'read', 'findings': [], 'record': None}
        for bad in (None, [], {}, dict(ok, verdict='yes'), dict(ok, extra=1), {k: ok[k] for k in list(ok)[:-1]}):
            r = self._with_judge(lambda *a, b=bad: b)
            self.assertEqual((r['verdict'], r['reason'], r['exit_code'], r['record']), ('uncovered', 'entry', 2, None), bad)
        self.assertEqual(self._with_judge(lambda *a: dict(ok))['exit_code'], 0)
        self.assertIs(claude_code.judge, real)

    def test_exception_in_judge(self):
        """TASK-062 AC5: an exception inside entry gives uncovered, reason entry, its type's name only, exit code 2,
        no record; the replaced judge is restored."""
        real = claude_code.judge

        def boom(*a):
            raise KeyError('zqxwvu-made-up')
        r = self._with_judge(boom)
        self.assertEqual((r['verdict'], r['reason'], r['exit_code'], r['record']), ('uncovered', 'entry', 2, None))
        self.assertEqual(r['findings'], ['KeyError raised inside entry'])
        self.assertIs(claude_code.judge, real)

    def test_deep_input(self):
        """TASK-062 AC2, AC5: an input nested too deeply for the parser, as arrays or as objects, is a parse error:
        uncovered, reason input_json, exit code 2, never an exception."""
        for data in (b'[' * 200000 + b']' * 200000, b'{"a":' * 200000 + b'1' + b'}' * 200000):
            r = run(data)
            self.assertEqual((r['verdict'], r['reason'], r['exit_code']), ('uncovered', 'input_json', 2))

    def test_judge_reason_outside_its_set(self):
        """TASK-062 AC3, AC5, AC6: a reason of judge's outside claude_code.REASONS gives uncovered, reason entry, exit
        code 2 and the fixed line; the replaced judge is restored."""
        real = claude_code.judge
        for reason in ('x\n', 'read ', 'zqxwvu-made-up', 7, None):
            r = self._with_judge(lambda *a, b=reason: {'verdict': 'allow', 'concern': 'read', 'reason': b,
                                                       'findings': [], 'record': None})
            self.assertEqual((r['verdict'], r['reason'], r['exit_code'], r['stderr']),
                             ('uncovered', 'entry', 2, 'AIEOS claude_code_hook: uncovered (entry)'), reason)
        self.assertIs(claude_code.judge, real)

    def test_exception_in_allowlist_findings(self):
        """TASK-062 AC5: an exception inside allowlist_findings becomes a finding with its type's name only."""
        class Odd(list):
            def __iter__(self):
                raise RuntimeError('zqxwvu-made-up')
        f = claude_code_hook.allowlist_findings(Odd(['git status']))
        self.assertEqual(f, ['RuntimeError raised inside allowlist_findings'])
        r = run(hook('Read', {'file_path': 'C:/a'}), allow=Odd(['git status']))
        self.assertEqual((r['verdict'], r['reason'], r['exit_code']), ('refuse', 'allowlist_form', 2))


class Result(unittest.TestCase):
    CASES = [lambda: run('x'), lambda: run(b'\xff'), lambda: run(b'{'), lambda: run(b'[]'),
             lambda: run(b'{}', allow=['sh']), lambda: bash('git status'), lambda: bash('git push'),
             lambda: write('C:\\proj\\repo\\src\\a.py'), lambda: run(hook('Read', {})), lambda: run(hook('mcp__a', {})),
             lambda: with_judge(lambda *a: None), lambda: with_judge(lambda *a: 1 // 0)]

    def test_keys_and_values(self):
        """TASK-062 AC6: exactly RESULT_KEYS; exit code 0 exactly for allow; a reason of claude_code.REASONS or of the
        module's own REASONS; the module's REASONS are not in claude_code.REASONS."""
        self.assertFalse(set(claude_code_hook.REASONS) & set(claude_code.REASONS))
        for c in self.CASES:
            r = c()
            self.assertEqual(tuple(r), claude_code_hook.RESULT_KEYS)
            self.assertEqual(r['exit_code'] == 0, r['verdict'] == 'allow')
            self.assertIn(r['verdict'], ('allow', 'refuse', 'uncovered'))
            self.assertIn(r['concern'], ('write', 'shell', 'read', None))
            self.assertIn(r['reason'], claude_code.REASONS + claude_code_hook.REASONS)
            self.assertIsInstance(r['findings'], list)
            self.assertTrue(all(isinstance(f, str) for f in r['findings']))

    def test_record_only_on_policy_refusal(self):
        """TASK-062 AC6: only refuse from judge with a reason other than argument and record carries a record."""
        for c in self.CASES:
            r = c()
            has = r['record'] is not None
            self.assertEqual(has, r['verdict'] == 'refuse' and r['reason'] not in ('argument', 'record', 'allowlist_form'))

    def test_judge_record_reason_has_no_record(self):
        """TASK-062 AC6: judge's refuse with reason record (check_payload failed) carries no record here either."""
        r = with_judge(lambda *a: {'verdict': 'refuse', 'concern': 'shell', 'reason': 'record',
                                                         'findings': ['x'], 'record': None})
        self.assertEqual((r['verdict'], r['reason'], r['record'], r['exit_code']), ('refuse', 'record', None, 2))


class ScriptChecks(unittest.TestCase):
    def test_imports_and_absent_names(self):
        """TASK-062 AC8: only json and aieos_bootstrap's claude_code are imported; no process, file, standard input,
        print, exit, clock, environment, network, model, exec, eval, compile, __import__, importlib or assert."""
        tree = ast.parse(SRC.read_text(encoding='utf-8'))
        imports = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imports |= {a.name for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                imports |= {n.module + '.' + a.name for a in n.names}
        self.assertEqual(imports, {'json', 'aieos_bootstrap.claude_code'})
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for bad in ('open', 'print', 'exit', 'stdin', 'stdout', 'environ', 'getenv', 'time', 'subprocess',
                    'socket', 'exec', 'eval', 'compile', '__import__', 'importlib', 'input', 'system', 'popen'):
            self.assertNotIn(bad, names, bad)
        self.assertFalse(any(isinstance(n, ast.Assert) for n in ast.walk(tree)))
        self.assertNotIn('.aie' + 'os', SRC.read_text(encoding='utf-8'))

    def test_judge_called_through_the_module(self):
        """TASK-062 AC5, AC8: judge is called as claude_code.judge, so a test double reaches it."""
        text = SRC.read_text(encoding='utf-8')
        self.assertIn('claude_code.judge(', text)
        self.assertNotIn('import judge', text)

    def test_own_tests_named(self):
        """TASK-062 AC9: every test function of the three new test modules names "TASK-062 ACn" in its own docstring
        and no other task's AC in qualified form."""
        tests = pathlib.Path(__file__).resolve().parents[1]
        for rel in ('unit/test_claude_code_hook.py', 'integration/test_claude_code_hook_inputs.py',
                    'property/test_claude_code_hook_properties.py'):
            tree = ast.parse((tests / rel).read_text(encoding='utf-8'))
            fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]
            self.assertTrue(fns, rel)
            for fn in fns:
                doc = ast.get_docstring(fn) or ''
                self.assertRegex(doc, r'TASK-062 AC[0-9]+', (rel, fn.name))
                self.assertNotRegex(doc, r'TASK-(?!062 )[0-9]+ AC[0-9]+', (rel, fn.name))

    def test_docstring_words(self):
        """TASK-062 AC7: the docstring states what is unmeasured, the documentation source, the fail-open case, the
        matcher, the two keys, that uncovered is never allow, and the redaction limit."""
        doc = ast.get_docstring(ast.parse(SRC.read_text(encoding='utf-8')))
        for words in ('unmeasured', 'C6', 'https://code.claude.com/docs/en/hooks', 'not measured', 'fails',
                      'open outside these functions', 'matcher', 'owner', 'only tool_name and tool_input are read',
                      '"uncovered" is never "allow"', 'redaction', 'D-1202', 'D-1203', 'Nothing is installed or measured'):
            self.assertIn(words, doc, words)


if __name__ == '__main__':
    unittest.main()
