"""Unit tests of the command evaluate of cli.py (task TASK-162; specification 7 revision 14, section 3 :37-:46).
evaluate_command.evaluate is replaced by a stand-in through mock.patch.object, restored after each test; standard input,
standard output and the clock are stand-ins; no test writes a file, runs Git or starts a process; the only file read is
cli.py; the roots are literal paths that name no folder. Each test names its criteria in its own docstring."""

import ast
import datetime
import pathlib
import unittest
from unittest import mock

from aieos_bootstrap import cli, evaluate_command

SRC = pathlib.Path(__file__).resolve().parents[2] / 'src' / 'aieos_bootstrap'
ROOT = 'C:/cli-root-162'
REPO = 'C:/cli-repo-162'
TASK = 'TASK-7'
NOW = datetime.datetime(2026, 11, 26, 12, 0, 0, tzinfo=datetime.timezone.utc)
BODY = '{"é": "x"}'
ARGV = ['evaluate', TASK, '--root', ROOT, '--repo', REPO]


def answer(**changes):
    a = {'result': 'evaluated', 'reason': None, 'findings': ['left out'], 'event_id': 'e1', 'decision': 'REJECT',
         'next_task_state': 'REJECTED', 'manifest_sha256': 'f' * 64, 'manifest': '{"m":1}', 'appended': ['r1', 'r2'],
         'uncovered': [{'gate': 'G3', 'check': 'review'}]}
    a.update(changes)
    return a


class Sink:
    def __init__(self):
        self.writes = []

    def write(self, text):
        self.writes.append(text)


class Buffer:
    def __init__(self, data=BODY.encode('utf-8'), raises=None):
        self.data = data
        self.raises = raises
        self.calls = []

    def read(self, *args):
        self.calls.append(args)
        if self.raises is not None:
            raise self.raises
        return self.data


class Stdin:
    def __init__(self, buffer):
        self.buffer = buffer


class Clock:
    def __init__(self, raises=None):
        self.calls = 0
        self.raises = raises

    def __call__(self):
        self.calls += 1
        if self.raises is not None:
            raise self.raises
        return NOW


class Stand:
    def __init__(self, value=None, raises=None):
        self.calls = []
        self.value = answer() if value is None else value
        self.raises = raises

    def __call__(self, *args):
        self.calls.append(args)
        if self.raises is not None:
            raise self.raises
        return self.value


def run(argv=ARGV, stdin=None, clock=None, stand=None, environ=None, no_stdin=False):
    sink = Sink()
    buffer = Buffer()
    stdin = Stdin(buffer) if stdin is None and not no_stdin else stdin
    clock = Clock() if clock is None else clock
    stand = Stand() if stand is None else stand
    with mock.patch.object(evaluate_command, 'evaluate', stand):
        rc = cli.main(argv, sink, {} if environ is None else environ, clock, stdin=stdin)
    return rc, ''.join(sink.writes), stand, clock, stdin


class TASK162AC11Parser(unittest.TestCase):
    def test_the_accepted_form(self):
        """TASK-162 AC11: the form reads stdin once with STDIN_CAP + 1, then calls evaluate once with the root, the
        repository, the task, the decoded text, the recorder and the clock's time."""
        for argv in (ARGV, ['evaluate', TASK, '--repo', REPO, '--root', ROOT, '--json']):
            rc, _, stand, clock, stdin = run(argv)
            self.assertEqual(rc, 0, argv)
            self.assertEqual(stand.calls, [(ROOT, REPO, TASK, BODY, 'aieos cli evaluate', NOW)])
            self.assertEqual((clock.calls, stdin.buffer.calls), (1, [(cli.STDIN_CAP + 1,)]))
        self.assertEqual(cli.STDIN_CAP, 67108864)

    def test_usage_errors(self):
        """TASK-162 AC11: any other argv gives exit 2 and USAGE with nothing read or called."""
        bad = (['evaluate'], ['evaluate', TASK], ['evaluate', TASK, '--root', ROOT],
               ['evaluate', TASK, '--repo', REPO], ['evaluate', 'T-1', '--root', ROOT, '--repo', REPO],
               ARGV + ['--repo', REPO], ARGV + ['--root', ROOT], ARGV + ['--class', 'decision_agent'],
               ['evaluate', TASK, '--root', ROOT, '--repo', '--json'],
               ['evaluate', TASK, '--root', ROOT, '--repo', ''], ARGV + ['extra'],
               ['status', '--root', ROOT, '--repo', REPO], ARGV + ['--json', '--json'])
        for argv in bad:
            rc, out, stand, clock, stdin = run(argv)
            self.assertEqual((rc, out, stand.calls, clock.calls, stdin.buffer.calls), (2, cli.USAGE, [], 0, []), argv)

    def test_the_runtime_refusal_comes_before_stdin_and_the_clock(self):
        """TASK-162 AC11: inside a runtime, exit 1 with the one refusal, standard input not read and the clock not
        called."""
        for name in cli.RUNTIME_VARS:
            rc, out, stand, clock, stdin = run(environ={name: ''})
            self.assertEqual((rc, out), (1, 'finding: %s\n' % cli.EVALUATE_RUNTIME_REFUSAL))
            self.assertEqual((stand.calls, clock.calls, stdin.buffer.calls), ([], 0, []))


class TASK162AC11Stdin(unittest.TestCase):
    def test_the_other_commands_never_touch_stdin(self):
        """TASK-162 AC11: only evaluate reads standard input."""
        touched = []

        class Watch:
            def __getattr__(self, name):
                touched.append(name)
                raise AssertionError(name)

        inside = {cli.RUNTIME_VARS[0]: ''}
        by = ['--class', 'decision_agent', '--by', 'D-1']
        with mock.patch.object(cli, '_status', Stand((0, 'x'))):
            for argv, code in ((['status', '--root', ROOT], 0), (['end', 's1', '--root', ROOT], 1),
                               (['init', '--root', ROOT], 1), (['launch', TASK, '--root', ROOT], 1),
                               (['approve', TASK, '--root', ROOT] + by, 1)):
                rc = cli.main(argv, Sink(), inside, Clock(), stdin=Watch())
                self.assertEqual(rc, code, argv)
        self.assertEqual(touched, [])

    def test_the_refusals_of_standard_input(self):
        """TASK-162 AC11: no stdin, no buffer, a raising access or read, a value that is not bytes, more than the cap
        or bytes that are not UTF-8 give exit 1 with STDIN_REFUSAL and evaluate not called."""
        class NoBuffer:
            pass

        class Raising:
            @property
            def buffer(self):
                raise OSError('x')

        cases = (None, NoBuffer(), Raising(), Stdin(Buffer(raises=OSError('r'))), Stdin(Buffer(data='text')),
                 Stdin(Buffer(data=b'\xff')), Stdin(Buffer(data=bytearray(b'{}'))))
        for stdin in cases:
            rc, out, stand, clock, _ = run(stdin=stdin, no_stdin=stdin is None)
            self.assertEqual((rc, out, stand.calls, clock.calls),
                             (1, 'finding: %s\n' % cli.STDIN_REFUSAL, [], 0), stdin)
        with mock.patch.object(cli, 'STDIN_CAP', 3):
            rc, out, stand, _, _ = run(stdin=Stdin(Buffer(data=b'1234')))
            self.assertEqual((rc, stand.calls), (1, []))
            rc, _, stand, _, _ = run(stdin=Stdin(Buffer(data=b'123')))
            self.assertEqual((rc, stand.calls[0][3]), (0, '123'))


class TASK162AC11Output(unittest.TestCase):
    def test_the_exit_codes(self):
        """TASK-162 AC11: evaluated and duplicate with a decision give 0; a decision of None and a refusal give 1."""
        for changes, code in (({}, 0), ({'result': 'duplicate'}, 0), ({'decision': None}, 1),
                              ({'result': 'duplicate', 'decision': None}, 1),
                              ({'result': 'refused', 'reason': 'ci'}, 1)):
            rc = run(stand=Stand(answer(**changes)))[0]
            self.assertEqual(rc, code, changes)

    def test_the_text_lines(self):
        """TASK-162 AC11: the result, the manifest, the appended ids, the uncovered entries and the findings, one per
        line; no line says that the task was accepted."""
        rc, out, _, _, _ = run()
        self.assertEqual((rc, out), (0, 'evaluate: evaluated REJECT REJECTED e1\n'
                                        'manifest-sha256: ' + 'f' * 64 + '\n'
                                        'manifest: {"m":1}\n'
                                        'appended: r1\n'
                                        'appended: r2\n'
                                        'uncovered: {"check": "review", "gate": "G3"}\n'
                                        'finding: left out\n'))
        value = answer(result='refused', reason='inputs', decision=None, next_task_state=None, event_id=None,
                       manifest=None, manifest_sha256=None, appended=[], uncovered=None, findings=['gap: x'])
        rc, out, _, _, _ = run(stand=Stand(value))
        self.assertEqual((rc, out), (1, 'evaluate: refused inputs\nfinding: gap: x\n'))
        rc, out, _, _, _ = run(stand=Stand(answer(decision=None, next_task_state=None, uncovered=[], appended=[],
                                                  findings=[])))
        self.assertEqual((rc, out), (1, 'evaluate: evaluated none none e1\n'
                                        'manifest-sha256: ' + 'f' * 64 + '\nmanifest: {"m":1}\n'))

    def test_the_json_line(self):
        """TASK-162 AC11: --json gives one sorted JSON line of the whole answer."""
        rc, out, _, _, _ = run(ARGV + ['--json'])
        self.assertEqual(rc, 0)
        self.assertEqual(out.count('\n'), 1)
        self.assertTrue(out.startswith('{"appended": ["r1", "r2"], "decision": "REJECT", "event_id": "e1"'), out)

    def test_answers_out_of_form_and_raises(self):
        """TASK-162 AC11: an answer out of form gives the out-of-form finding and exit 1; a raise in the clock or in
        evaluate gives exit 1 naming the type."""
        for value in (5, {}, answer(extra=1), answer(result='done'), answer(reason='ci'),
                      answer(result='refused'), answer(findings='x'), answer(appended=[1]), answer(uncovered={}),
                      answer(decision=1), answer(manifest=b'x')):
            rc, out, _, _, _ = run(stand=Stand(value))
            self.assertEqual((rc, out), (1, 'finding: %s\n' % cli.EVALUATE_OUT_OF_FORM), value)
        rc, out, _, _, _ = run(stand=Stand(raises=ValueError('v')))
        self.assertEqual((rc, out), (1, 'finding: evaluate: a step raised ValueError\n'))
        rc, out, stand, _, _ = run(clock=Clock(raises=KeyError('k')))
        self.assertEqual((rc, out, stand.calls), (1, 'finding: evaluate: a step raised KeyError\n', []))


class TASK162AC11Docs(unittest.TestCase):
    def test_the_usage_docstring_and_commands(self):
        """TASK-162 AC11: USAGE names evaluate with its flags; the docstring names the command and its stdin; COMMANDS
        ends with import, run, evaluate; the recorder of end is unchanged."""
        self.assertIn('python -m aieos_bootstrap.cli evaluate <task> --root <path> --repo <path> [--reviews <path>] '
                      '[--json]', cli.USAGE)
        text = ' '.join(ast.get_docstring(ast.parse((SRC / 'cli.py').read_bytes().decode('utf-8'))).split())
        for phrase in ('aieos evaluate', 'TASK-162', 'stdin.buffer.read(STDIN_CAP + 1)',
                       'evaluate also calls it after the parse'):
            self.assertIn(phrase, text)
        self.assertEqual(cli.COMMANDS[-3:], ('import', 'run', 'evaluate'))
        self.assertEqual((cli.RECORDER, cli.EVALUATE_RECORDER), ('aieos cli end', 'aieos cli evaluate'))


# TASK-166: the flag --reviews of evaluate.
REVIEWS = 'C:/cli-reviews-166.json'
REVIEWS_BODY = '[{"é": 1}]'


class KeywordStand(Stand):
    def __init__(self):
        Stand.__init__(self)
        self.keywords = []

    def __call__(self, *args, **keywords):
        self.keywords.append(keywords)
        return Stand.__call__(self, *args)


class Reads:
    """A stand-in for pathlib's read_bytes: it keeps each path asked for and gives the data or raises."""

    def __init__(self, data=REVIEWS_BODY.encode('utf-8'), raises=None):
        self.data = data
        self.raises = raises
        self.paths = []

    def go(self, argv, environ=None):
        def read_bytes(path):
            self.paths.append(path.as_posix())
            if self.raises is not None:
                raise self.raises
            return self.data

        stand = KeywordStand()
        with mock.patch.object(pathlib.Path, 'read_bytes', read_bytes):
            rc, out, _, clock, stdin = run(argv, stand=stand, environ=environ)
        return rc, out, stand, clock, stdin


WITH = ARGV + ['--reviews', REVIEWS]


class TASK166Parser(unittest.TestCase):
    def test_the_flag_in_any_place_once(self):
        """TASK-166 AC5: --reviews is accepted once, wherever it stands among the flags."""
        for argv in (WITH, ['evaluate', TASK, '--reviews', REVIEWS, '--json', '--repo', REPO, '--root', ROOT]):
            reads = Reads()
            rc, _, stand, clock, stdin = reads.go(argv)
            self.assertEqual((rc, reads.paths, len(stand.calls), clock.calls), (0, [REVIEWS], 1, 1), argv)

    def test_usage_errors(self):
        """TASK-166 AC5: a second --reviews, one without a value, one without --repo and one on another command give the
        usage, with nothing read or called."""
        bad = (WITH + ['--reviews', REVIEWS], ARGV + ['--reviews'], ARGV + ['--reviews', '--json'],
               ARGV + ['--reviews', ''], ['evaluate', TASK, '--root', ROOT, '--reviews', REVIEWS],
               ['status', '--root', ROOT, '--reviews', REVIEWS],
               ['import', TASK, '--root', ROOT, '--reviews', REVIEWS])
        for argv in bad:
            reads = Reads()
            rc, out, stand, clock, stdin = reads.go(argv)
            self.assertEqual((rc, out, reads.paths, stand.calls, clock.calls, stdin.buffer.calls),
                             (2, cli.USAGE, [], [], 0, []), argv)

    def test_the_usage_names_the_flag(self):
        """TASK-166 AC5: the flag has its own help line."""
        self.assertIn('  --reviews <path> the reviews file (evaluate only; at most once)\n', cli.USAGE)


class TASK166Reading(unittest.TestCase):
    def test_the_text_reaches_evaluate_as_reviews_text(self):
        """TASK-166 AC5: the decoded text is passed as the one keyword reviews_text, a byte-order mark kept."""
        for body in (REVIEWS_BODY, '\ufeff[]'):
            reads = Reads(body.encode('utf-8'))
            rc, _, stand, _, _ = reads.go(WITH)
            self.assertEqual((rc, stand.keywords), (0, [{'reviews_text': body}]))
            self.assertEqual(stand.calls, [(ROOT, REPO, TASK, BODY, 'aieos cli evaluate', NOW)])

    def test_without_the_flag_nothing_is_read_and_no_keyword_is_given(self):
        """TASK-166 AC5: without the flag the call is the one of before."""
        reads = Reads()
        rc, _, stand, _, _ = reads.go(ARGV)
        self.assertEqual((rc, reads.paths, stand.keywords), (0, [], [{}]))

    def test_the_cap(self):
        """TASK-166 AC5: 1048576 bytes pass and one byte more refuses."""
        self.assertEqual(cli.REVIEWS_CAP, 1048576)
        rc, _, stand, _, _ = Reads(b' ' * 1048576).go(WITH)
        self.assertEqual((rc, len(stand.keywords[0]['reviews_text'])), (0, 1048576))
        rc, out, stand, clock, _ = Reads(b' ' * 1048577).go(WITH)
        self.assertEqual((rc, out, stand.calls, clock.calls), (1, 'finding: %s\n' % cli.REVIEWS_REFUSAL, [], 0))

    def test_a_file_that_gives_no_text_refuses(self):
        """TASK-166 AC5: a raising read, a value that is not bytes and bytes that are not UTF-8 give the one finding,
        with neither the clock nor evaluate called; standard input was read before."""
        self.assertEqual(cli.REVIEWS_REFUSAL, 'evaluate: the reviews file gave no UTF-8 bytes within the cap')
        for reads in (Reads(raises=OSError('x')), Reads(raises=ValueError('v')), Reads(raises=MemoryError()),
                      Reads('text'), Reads(bytearray(b'[]')), Reads(b'\xff')):
            rc, out, stand, clock, stdin = reads.go(WITH)
            self.assertEqual((rc, out, stand.calls, clock.calls, stdin.buffer.calls),
                             (1, 'finding: evaluate: the reviews file gave no UTF-8 bytes within the cap\n', [], 0,
                              [(cli.STDIN_CAP + 1,)]), reads.data)

    def test_inside_a_runtime_the_file_is_not_read(self):
        """TASK-166 AC5: the refusal inside a runtime comes before the file is read."""
        for name in cli.RUNTIME_VARS:
            reads = Reads()
            rc, out, stand, clock, stdin = reads.go(WITH, environ={name: ''})
            self.assertEqual((rc, out, reads.paths, stand.calls, clock.calls, stdin.buffer.calls),
                             (1, 'finding: %s\n' % cli.EVALUATE_RUNTIME_REFUSAL, [], [], 0, []))

    def test_a_refused_standard_input_leaves_the_file_unread(self):
        """TASK-166 AC5: the file is read after standard input."""
        reads = Reads()

        def read_bytes(path):
            reads.paths.append(path.as_posix())
            return b'[]'

        with mock.patch.object(pathlib.Path, 'read_bytes', read_bytes):
            rc, out, stand, _, _ = run(WITH, stdin=Stdin(Buffer(raises=OSError('x'))), stand=KeywordStand())
        self.assertEqual((rc, out, reads.paths, stand.calls),
                         (1, 'finding: %s\n' % cli.STDIN_REFUSAL, [], []))


if __name__ == '__main__':
    unittest.main()
