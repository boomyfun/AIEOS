"""Unit tests of aieos_bootstrap.claude_code (task TASK-061, rules R1 to R8): the hooks mapping's arguments, concerns,
Windows paths, write-set, git push, allowlist, refusal records and results, over hook-input mappings made up for the
test. No process starts and no file is written. Each test names its criteria in its own docstring."""

import ast
import pathlib
import unittest

from aieos_bootstrap import claude_code
from aieos_bootstrap import records

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap' / 'claude_code.py'
ROOT = 'C:\\proj\\repo'
TASK = 'TASK-100'
WS = ['docs/notes/**', 'src/app/*.py']
ALLOW = ['git status', 'python tests/run_tests.py', 'bash', 'sh', 'powershell']
RID = 'obs-1'
REC = 'a test session'


def call(tool, inp, cwd=None, root=ROOT, task=TASK, ws=None, allow=None, rid=RID, rec=REC):
    hook = {'tool_name': tool, 'tool_input': inp}
    if cwd is not None:
        hook['cwd'] = cwd
    return claude_code.judge(hook, root, task, WS if ws is None else ws, ALLOW if allow is None else allow, rid, rec)


def write(path, cwd=None, **kw):
    return call('Write', {'file_path': path, 'content': 'x'}, cwd=cwd, **kw)


def bash(cmd, **kw):
    return call('Bash', {'command': cmd}, **kw)


class Arguments(unittest.TestCase):
    def test_wrong_arguments_refused_without_record(self):
        """TASK-061 AC1: each wrong argument gives refuse, reason argument, a finding and no record."""
        cases = [dict(root='relative\\root'), dict(root=''), dict(task='TASK-x'), dict(ws=[]), dict(ws=['a//b']),
                 dict(ws=['a b']), dict(ws='docs/**'), dict(allow=['']), dict(allow=['a\nb']), dict(allow='git'),
                 dict(rid=''), dict(rec='')]
        for kw in cases:
            r = write('C:\\proj\\repo\\docs\\notes\\a.md', **kw)
            self.assertEqual((r['verdict'], r['reason'], r['record']), ('refuse', 'argument', None), kw)
            self.assertTrue(r['findings'], kw)
        r = claude_code.judge('not a mapping', ROOT, TASK, WS, ALLOW, RID, REC)
        self.assertEqual((r['verdict'], r['reason'], r['record']), ('refuse', 'argument', None))

    def test_right_arguments_pass(self):
        """TASK-061 AC1: well-formed arguments reach the concern."""
        r = write('C:\\proj\\repo\\docs\\notes\\a.md')
        self.assertEqual(r['verdict'], 'allow')


class Concerns(unittest.TestCase):
    def test_named_tools(self):
        """TASK-061 AC2: Write and Edit are write, Bash and PowerShell shell, Read, Grep and Glob read (allow, no
        record)."""
        self.assertEqual(call('Edit', {'file_path': 'C:/proj/repo/docs/notes/a.md', 'old_string': 'a', 'new_string': 'b'})['concern'], 'write')
        self.assertEqual(call('PowerShell', {'command': 'git status'})['concern'], 'shell')
        for tool in ('Read', 'Grep', 'Glob'):
            r = call(tool, {'file_path': 'C:/elsewhere/x'})
            self.assertEqual((r['verdict'], r['concern'], r['reason'], r['record']), ('allow', 'read', 'read', None))

    def test_other_tools_uncovered(self):
        """TASK-061 AC2: MultiEdit, NotebookEdit, an mcp__ name, Agent, WebFetch, a missing or non-string name and a
        non-mapping tool_input are uncovered, reason tool, never allow."""
        for tool in ('MultiEdit', 'NotebookEdit', 'mcp__Claude_Browser__navigate', 'Agent', 'WebFetch', None, 7):
            r = call(tool, {'file_path': 'C:/proj/repo/docs/notes/a.md'})
            self.assertEqual((r['verdict'], r['reason'], r['record']), ('uncovered', 'tool', None), tool)
        r = claude_code.judge({'tool_name': 'Write', 'tool_input': 'x'}, ROOT, TASK, WS, ALLOW, RID, REC)
        self.assertEqual((r['verdict'], r['reason']), ('uncovered', 'tool'))
        r = claude_code.judge({}, ROOT, TASK, WS, ALLOW, RID, REC)
        self.assertEqual(r['verdict'], 'uncovered')

    def test_missing_input_uncovered(self):
        """TASK-061 AC2: a write without a string path, a shell call without a string command, uncovered, input."""
        self.assertEqual((call('Write', {})['verdict'], call('Write', {})['reason']), ('uncovered', 'input'))
        self.assertEqual(call('Write', {'file_path': 3})['reason'], 'input')
        self.assertEqual((bash(None)['verdict'], bash(None)['reason']), ('uncovered', 'input'))
        self.assertEqual(call('Bash', {})['verdict'], 'uncovered')


class Paths(unittest.TestCase):
    def test_normal_forms(self):
        """TASK-061 AC3: separators, ".", "..", case of the root, and the normalised form."""
        n = claude_code.normalise_path
        self.assertEqual(n(ROOT, None, 'C:\\proj\\repo\\docs\\notes\\a.md'), ('ok', 'docs/notes/a.md'))
        self.assertEqual(n(ROOT, None, 'c:/PROJ/Repo/docs/./x/../notes/a.md'), ('ok', 'docs/notes/a.md'))
        self.assertEqual(n(ROOT, 'C:\\proj\\repo\\docs', 'notes\\a.md'), ('ok', 'docs/notes/a.md'))
        self.assertEqual(n(ROOT, None, 'C:/proj/repo/Docs/notes/a.md'), ('ok', 'Docs/notes/a.md'))

    def test_outside_and_uncovered(self):
        """TASK-061 AC3: outside root, a relative path with no cwd, and the uncovered forms."""
        n = claude_code.normalise_path
        self.assertEqual(n(ROOT, None, 'C:/proj/other/a.md')[0], 'outside')
        self.assertEqual(n(ROOT, None, 'C:/proj/repo/../other/a.md')[0], 'outside')
        self.assertEqual(n(ROOT, None, 'D:/proj/repo/a.md')[0], 'outside')
        self.assertEqual(n(ROOT, None, 'C:/proj/repo')[0], 'outside')
        self.assertEqual(n(ROOT, None, 'C:/proj/repo-x/a.md')[0], 'outside')
        self.assertEqual(n(ROOT, None, 'C:/../../a.md')[0], 'outside')
        for p in ('docs/a.md', 'C:/proj/repo/a.md:stream', '\\\\?\\C:\\proj\\repo\\a.md', '\\\\.\\C:\\a',
                  '\\\\server\\share\\a', '/proj/repo/a', 'C:/proj/repo/a.md.', 'C:/proj/repo/a.md ',
                  'C:/proj/repo/.../a', 'C:/proj/repo/   /a', 'C:/proj/repo/a\x00b', 'x:y', ''):
            self.assertEqual(n(ROOT, None, p)[0], 'uncovered', p)
        self.assertEqual(n('relative', None, 'C:/a')[0], 'uncovered')
        self.assertEqual(n(ROOT, 'rel', 'docs/a.md')[0], 'uncovered')


class WriteSet(unittest.TestCase):
    def test_inside_allowed(self):
        """TASK-061 AC4: a path matching a write-set pattern by governor.matches is allowed."""
        for p in ('C:/proj/repo/docs/notes/a.md', 'C:/proj/repo/docs/notes/x/y.md', 'C:/proj/repo/src/app/m.py'):
            r = write(p)
            self.assertEqual((r['verdict'], r['reason'], r['record']), ('allow', 'write_set', None), p)

    def test_outside_refused_with_record(self):
        """TASK-061 AC4, TASK-061 AC7: outside the write-set, outside root, and a case difference are refused with the record."""
        r = write('C:/proj/repo/src/app/sub/m.py')
        self.assertEqual((r['verdict'], r['reason']), ('refuse', 'write_set'))
        self.assertEqual(r['record']['refers_to'], 'src/app/sub/m.py')
        self.assertEqual(r['record']['evidence_type'], 'write_outside_write_set')
        r = write('C:/elsewhere/a.md')
        self.assertEqual((r['verdict'], r['record']['refers_to']), ('refuse', 'C:/elsewhere/a.md'))
        r = write('C:/proj/repo/Docs/notes/a.md')
        self.assertEqual(r['verdict'], 'refuse')
        r = write('C:/proj/repo/a.md:s')
        self.assertEqual((r['verdict'], r['reason'], r['record']), ('uncovered', 'path', None))


class Push(unittest.TestCase):
    CASES = ['git push', 'git -C d push', 'git -c a=b push', '/usr/bin/git push', 'git.exe push',
             'echo a && git push', '(git push)', '$(git push)', '`git push`', 'env X=1 git push',
             'bash -c "git push"', "sh -c 'git push'", 'powershell -Command "git push"',
             'git --git-dir=x push origin', 'C:\\Git\\bin\\git.exe push', 'X=1 git push']

    def test_pushes_refused(self):
        """TASK-061 AC5: every listed push form is refused, reason push, even with bash, sh and powershell allowed."""
        for c in self.CASES:
            r = bash(c, allow=ALLOW + ['git', 'echo', 'env', '/usr/bin/git', 'git.exe', 'X=1', 'C:\\Git\\bin\\git.exe'])
            self.assertEqual((r['verdict'], r['reason']), ('refuse', 'push'), c)
            self.assertEqual(r['record']['evidence_type'], 'git_push_refused', c)

    def test_quoted_and_assigned_push(self):
        """TASK-061 AC5 (D-1212 F1): quotes or a backslash inside a nested shell, and "push" inside an option value,
        are refused, reason push, even with bash, sh and git allowed."""
        allow = ['bash', 'sh', 'git']
        for c in ('bash -c "git pu\'\'sh"', "sh -c 'git p\\ush'", 'git -c alias.x=push x', 'git config alias.x push',
                  'bash -c "g\\it push"', 'P=push && git $P'):
            r = bash(c, allow=allow + ['P=push'])
            self.assertEqual((r['verdict'], r['reason']), ('refuse', 'push'), c)

    def test_expansions_with_git(self):
        """TASK-061 AC5 (D-1212 F2): a git word with any "$", "`" or "%" is refused, reason push (unsure)."""
        for c in ('git $P', 'P=pu && git ${P}sh', 'git %CMD%', 'git `echo x`', 'git status $X'):
            r = bash(c, allow=['git', 'P=pu'])
            self.assertEqual((r['verdict'], r['reason']), ('refuse', 'push'), c)
        self.assertEqual(bash('echo $HOME', allow=['echo'])['reason'], 'parse')

    def test_unclosed_quote(self):
        """TASK-061 AC5: an unclosed quote gives parse; with git and push in it, push."""
        r = bash('echo "a')
        self.assertEqual((r['verdict'], r['reason'], r['record']['evidence_type']), ('refuse', 'parse', 'shell_not_allowed'))
        r = bash('git push "a')
        self.assertEqual((r['verdict'], r['reason']), ('refuse', 'push'))

    def test_no_push_passes(self):
        """TASK-061 AC5, TASK-061 AC6: git status with an allowlist entry "git status" is allowed."""
        r = bash('git status')
        self.assertEqual((r['verdict'], r['reason'], r['record']), ('allow', 'allowlist', None))
        r = call('PowerShell', {'command': 'git status'})
        self.assertEqual(r['verdict'], 'allow')


class Unsure(unittest.TestCase):
    def test_substitutions_refused(self):
        """TASK-061 AC5, TASK-061 AC6 (D-1223 F9; the form B1 of D-1219): a substitution or an expansion, with no
        literal git word, is refused, reason parse, under the entry its first word needs."""
        for c, allow in (('python -m pytest "$(G=gi;${G}t push)"', ['python -m pytest']),
                         ('python -m pytest "$($(printf gi)t push)"', ['python -m pytest']),
                         ('python -m pytest "`G=gi;H=t;$G$H push`"', ['python -m pytest']),
                         ('bash -c "G=gi;\\${G}t push"', ['bash']),
                         ('echo "$(rm x)"', ['echo']),
                         ('echo "$X"', ['echo']),
                         ('echo ${X}', ['echo'])):
            r = bash(c, allow=allow)
            self.assertEqual((r['verdict'], r['reason'], r['record']['evidence_type']),
                             ('refuse', 'parse', 'shell_not_allowed'), c)
        self.assertEqual(bash("echo '$X'", allow=['echo'])['reason'], 'parse')

    def test_escaped_quote_refused(self):
        """TASK-061 AC5, TASK-061 AC6 (D-1223 F9; the form B2 of D-1219): a backslash before a quote, in bash and in
        PowerShell, is refused, reason parse."""
        r = bash('git status \\"; rm x # "', allow=['git status'])
        self.assertEqual((r['verdict'], r['reason']), ('refuse', 'parse'))
        r = call('PowerShell', {'command': 'echo "a\\" ; rm x ; echo \\"b"'}, allow=['echo'])
        self.assertEqual((r['verdict'], r['reason']), ('refuse', 'parse'))
        r = bash("echo it\\'s", allow=['echo'])
        self.assertEqual((r['verdict'], r['reason']), ('refuse', 'parse'))

    def test_comments_refused(self):
        """TASK-061 AC5, TASK-061 AC6 (D-1223 F9; the form N1 of D-1220): a "#" outside quotes, "<#" included, is
        refused, reason parse, in bash and in PowerShell, and so is a "#" inside quotes."""
        for tool, c in (('Bash', 'echo hi # "\nrm x\n# "'), ('PowerShell', 'echo hi # "\nrm x\n# "'),
                        ('PowerShell', 'echo <# " #> ; rm x ; echo <# " #>'), ('Bash', 'echo a#b')):
            r = call(tool, {'command': c}, allow=['echo'])
            self.assertEqual((r['verdict'], r['reason']), ('refuse', 'parse'), c)
        self.assertEqual(bash('echo "a#b"', allow=['echo'])['reason'], 'parse')

    def test_typographic_quotes_refused(self):
        """TASK-061 AC5, TASK-061 AC6 (D-1223 F9; the form N2 of D-1220): a typographic quote mark anywhere is
        refused, reason parse."""
        for q in '\u2018\u2019\u201a\u201b\u201c\u201d\u201e':
            r = call('PowerShell', {'command': 'echo "a' + q + ' ; rm x ; echo ' + q + 'b"'}, allow=['echo'])
            self.assertEqual((r['verdict'], r['reason']), ('refuse', 'parse'), ascii(q))

    def test_lone_line_breaks_refused(self):
        """TASK-061 AC5, TASK-061 AC6 (D-1223 F9): a lone carriage return, a vertical tab, a form feed and the Unicode
        line breaks are refused, reason parse; a carriage return right before a newline is not."""
        for sep in ('\r', '\v', '\f', '\u2028', '\u2029', '\u0085'):
            r = call('PowerShell', {'command': 'git status' + sep + 'rm x'}, allow=['git status'])
            self.assertEqual((r['verdict'], r['reason']), ('refuse', 'parse'), ascii(sep))
        self.assertEqual(bash('git status\r\n')['verdict'], 'allow')

    def test_safe_set(self):
        """TASK-061 AC5, TASK-061 AC6 (D-1223 F9): each character outside the safe set refuses, reason parse, even under
        an entry that admits the words; texts of the safe set reach the allowlist."""
        for ch in '\'"\\$`%#<>{}@*?!~^[]\u00a0\u00e9':
            r = bash('echo hi ' + ch, allow=['echo'])
            self.assertEqual((r['verdict'], r['reason'], r['record']['evidence_type']),
                             ('refuse', 'parse', 'shell_not_allowed'), ascii(ch))
        for c in ('git status', 'git log -n 3 --format=oneline', 'python tests/run_tests.py && git status',
                  'git diff a/b.py,c.py x:y +z', '(git status) | git status ; git status & git status'):
            self.assertEqual(bash(c, allow=['git', 'python tests/run_tests.py'])['verdict'], 'allow', c)

    def test_here_documents_and_continuations_refused(self):
        """TASK-061 AC5, TASK-061 AC6 (D-1223 F9; the form H1 of D-1223): here-documents, here-strings, the stop-parsing
        token and a backslash before a line break are refused, reason parse."""
        for tool, c, allow in (('Bash', "echo <<EOF\necho it's\nEOF\nrm x\necho 'z", ['echo']),
                               ('Bash', 'echo <<\'EOF\'\necho "\nEOF\nrm x\necho "', ['echo']),
                               ('Bash', 'git pu\\\nsh origin', ['git', 'sh']),
                               ('PowerShell', 'python -m pytest --% "; rm x; "', ['python -m pytest']),
                               ('PowerShell', "echo @'\nx\n'@ ; echo ok", ['echo']),
                               ('PowerShell', 'git @a', ['git'])):
            r = call(tool, {'command': c}, allow=allow)
            self.assertEqual((r['verdict'], r['reason']), ('refuse', 'parse'), c)


class Allowlist(unittest.TestCase):
    def test_entries(self):
        """TASK-061 AC6: each simple command must start with an entry's words; an empty allowlist refuses every call."""
        self.assertEqual(bash('python tests/run_tests.py && git status')['verdict'], 'allow')
        r = bash('git status && rm -rf x')
        self.assertEqual((r['verdict'], r['reason'], r['record']['refers_to']), ('refuse', 'allowlist', 'rm -rf x'))
        self.assertEqual(bash('git')['verdict'], 'refuse')
        r = bash('git status', allow=[])
        self.assertEqual((r['verdict'], r['reason']), ('refuse', 'allowlist'))
        r = bash('echo ' + 'a' * 500)
        self.assertEqual(len(r['record']['refers_to']), claude_code.REFERS_MAX)

    def test_empty_command_uncovered(self):
        """TASK-061 AC2, TASK-061 AC6: an empty or blank command is uncovered, input (a blank command is read as one
        that is missing)."""
        self.assertEqual(bash('   ')['verdict'], 'uncovered')


class Record(unittest.TestCase):
    def test_record_form(self):
        """TASK-061 AC7: exactly the record keys, passing check_payload, and the recorder's words."""
        r = write('C:/elsewhere/a.md')
        rec = r['record']
        self.assertEqual(set(rec), {'record_id', 'fact_kind', 'source_class', 'outcome', 'blocking_kind', 'recorder',
                                    'subject', 'evidence_type', 'refers_to'})
        self.assertEqual((rec['fact_kind'], rec['source_class'], rec['outcome'], rec['blocking_kind']),
                         ('observation', 'deterministic_tool_local', 'blocking', 'violation'))
        self.assertEqual(rec['recorder'], claude_code.RECORDER + ', for ' + REC)
        self.assertEqual(rec['subject'], TASK)
        self.assertEqual(records.check_payload('record.added', rec), [])

    def test_record_findings_refuse(self):
        """TASK-061 AC7: a record that check_payload refuses gives refuse, reason record, no record."""
        r = claude_code._refuse('write', 'write_set', {'record_id': 'x'})
        self.assertEqual((r['verdict'], r['reason'], r['record']), ('refuse', 'record', None))
        self.assertTrue(r['findings'])


class Results(unittest.TestCase):
    def test_keys_and_values(self):
        """TASK-061 AC8: exactly the result keys, with values from the named sets."""
        for r in (write('C:/proj/repo/docs/notes/a.md'), write('C:/x'), bash('git push'), call('Read', {}),
                  call('Agent', {}), write('x', root='')):
            self.assertEqual(tuple(sorted(r)), tuple(sorted(claude_code.RESULT_KEYS)))
            self.assertIn(r['verdict'], claude_code.VERDICTS)
            self.assertIn(r['reason'], claude_code.REASONS)
            self.assertEqual(r['record'] is not None, r['verdict'] == 'refuse' and r['reason'] not in ('argument', 'record'))

    def test_no_exception_escapes(self):
        """TASK-061 AC8: an exception inside judge becomes uncovered, input, with its type."""
        class Bad(dict):
            def get(self, key, default=None):
                raise RuntimeError('boom')
        r = claude_code.judge(Bad(), ROOT, TASK, WS, ALLOW, RID, REC)
        self.assertEqual((r['verdict'], r['reason']), ('uncovered', 'input'))
        self.assertIn('RuntimeError', r['findings'][0])


class Purity(unittest.TestCase):
    def test_imports_calls_and_docstring(self):
        """TASK-061 AC9, TASK-061 AC10: only the standard library and records and governor; no open, process, clock,
        environment, link resolution, exec or eval; no assert; the docstring's statements."""
        text = SRC.read_text(encoding='utf-8')
        tree = ast.parse(text)
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                mods.add(node.module + ':' + ','.join(a.name for a in node.names))
            self.assertNotIsInstance(node, ast.Assert)
        self.assertEqual(mods, {'re', 'aieos_bootstrap:governor', 'aieos_bootstrap:records'})
        ids = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for bad in ('open', 'exec', 'eval', 'compile', '__import__', 'subprocess', 'os', 'time', 'datetime',
                    'importlib', 'pathlib', 'socket', 'urllib'):
            self.assertNotIn(bad, ids, bad)
        for bad in ('system', 'popen', 'environ', 'getenv', 'realpath', 'readlink', 'resolve', 'urlopen', 'now',
                    'run', 'Popen'):
            self.assertNotIn(bad, attrs, bad)
        doc = ast.get_docstring(tree)
        for words in ('unmeasured', 'D-1202', 'D-1203', '"uncovered" is never "allow"', 'not judged against the write-set',
                      'Pushes by other means', 'supported live only for Bash', 'Links and junctions are not resolved',
                      'matcher "*"', 'passes no cwd', 'admits whatever that code does', 'D-1223 F9',
                      'supersedes the form-by-form rules F5 to F8', 'no quoted argument at all', 'case-sensitively',
                      'reserved device names', 'redaction', 'A blank command is "uncovered"', 'an alternate data stream'):
            self.assertIn(words, doc, words)
        self.assertNotIn('.aieos', text)

    def test_own_text(self):
        """TASK-061 AC11: every test function of the three modules names a TASK-061 AC in its docstring, and no test
        value is a path of a user folder or a command of this project's own hooks."""
        tests = pathlib.Path(__file__).resolve().parents[1]
        for rel in ('unit/test_claude_code.py', 'integration/test_claude_code_inputs.py',
                    'property/test_claude_code_properties.py'):
            text = (tests / rel).read_text(encoding='utf-8')
            tree = ast.parse(text)
            for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test')]:
                self.assertRegex(ast.get_docstring(fn) or '', r'TASK-061 AC[0-9]+', fn.name)
                self.assertNotRegex(ast.get_docstring(fn) or '', r'TASK-(?!061 )[0-9]+ AC[0-9]+', fn.name)
            # the words are built from parts, so that this module's own text does not hold them
            for bad in ('Us' + 'ers', 'App' + 'Data', '.cla' + 'ude/', '.cla' + 'ude\\','aieos_' + 'bash_guard', 'aieos_' + 'callform_guard',
                        'aieos_' + 'textblock_guard'):
                self.assertNotIn(bad, text, (rel, bad))


if __name__ == '__main__':
    unittest.main()
