"""Integration test of aieos_bootstrap.scope_drift with aieos_bootstrap.eventlog (task TASK-033 AC10): the list is read
from a policy text in policy v3's form, and the event claims returns is appended to an in-memory event log by the
append rules; a second append is a duplicate. No file is opened. Each test names its criteria in its own docstring."""

import datetime
import unittest

from aieos_bootstrap import eventlog, records, scope_drift

AT = datetime.datetime(2026, 10, 15, 0, 0, 0, tzinfo=datetime.timezone.utc)
POLICY_TEXT = '\n'.join([
    '# The self-build\'s risk rules (gov-AIEOS), policy version v3', '', '## 3. The rules', '', '```yaml',
    'policy_version: v3',
    'non_task_paths: ["docs/History/**", "docs/Progress/**", "docs/Deferred/**", "docs/Lessons/**"]', 'risk_rules:',
    '  # R1, low: concept line 597.', '  - match: { paths: ["docs/**", "*.md"] }', '    risk: low',
    '  # R2, medium.', '  - match: { paths: ["src/**", "tests/**"] }', '    risk: medium', '```', ''])
RULES = [{'match': ['docs/**', '*.md'], 'class': 'low'}, {'match': ['src/**', 'tests/**'], 'class': 'medium'},
         {'match': ['src/**', 'tests/**'], 'class': 'high'}, {'match': ['.github/**'], 'class': 'critical'}]
EVALUATOR = ['.github/**', 'src/aieos_bootstrap/**', 'docs/records/**', 'tests/unit/**']


def facts(commit, paths, trailers=(), contracts=None):
    return {'commit': commit, 'parents': 1, 'trailer_tasks': list(trailers), 'changed_paths': paths,
            'contracts': contracts or {}, 'non_task': scope_drift.non_task_list(POLICY_TEXT), 'risk_rules': RULES,
            'evaluator': EVALUATOR, 'constitution_path': 'docs/pre-genesis/constitution.md',
            'policy_path': 'docs/specs/risk-rules-gov-aieos.md'}


class EventsInALog(unittest.TestCase):

    def test_claim_exempt_and_not_detected_into_a_log(self):
        """TASK-033 AC10 and TASK-033 AC2 and TASK-033 AC6: a claim commit gives one event, an exempt commit and a
        commit that is not detected give none; the event appended to an empty log leaves no finding under check_log,
        and a second append of it is a duplicate."""
        self.assertEqual(scope_drift.non_task_list(POLICY_TEXT),
                         ['docs/History/**', 'docs/Progress/**', 'docs/Deferred/**', 'docs/Lessons/**'])
        claim = scope_drift.claims(facts('1' * 40, ['src/aieos_bootstrap/x.py', 'docs/History/a.md']))
        exempt = scope_drift.claims(facts('2' * 40, ['docs/History/a.md', 'docs/Lessons/L-0001-x.md']))
        task = scope_drift.claims(facts('3' * 40, ['src/aieos_bootstrap/x.py'], ['TASK-033'],
                                        {'TASK-033': ['src/aieos_bootstrap/x.py']}))
        self.assertEqual((len(claim['events']), claim['detected'], claim['exempt']), (1, True, False))
        self.assertEqual((exempt['events'], exempt['detected'], exempt['exempt']), ([], True, True))
        self.assertEqual((task['events'], task['detected'], task['exempt']), ([], False, False))
        log = b''
        for e in claim['events'] + exempt['events'] + task['events']:
            out = eventlog.append(log, e['event_type'], e['payload'], e['event_id'], AT)
            self.assertEqual(out.result, 'appended', out)
            log = out.log
        self.assertEqual(log.count(b'\n'), 1)
        self.assertEqual(records.check_log(log).findings(), [])
        again = eventlog.append(log, claim['events'][0]['event_type'], claim['events'][0]['payload'],
                                claim['events'][0]['event_id'], AT)
        self.assertEqual(again.result, 'duplicate', again)

    def test_a_rerun_appends_nothing_new(self):
        """TASK-033 AC10 and TASK-033 AC6: a rerun of claims for the same commit gives the same event, a duplicate."""
        f = facts('4' * 40, ['.github/workflows/x.yml'])
        first = scope_drift.claims(f)['events'][0]
        log = eventlog.append(b'', first['event_type'], first['payload'], first['event_id'], AT).log
        rerun = scope_drift.claims(f)['events'][0]
        self.assertEqual(rerun, first)
        self.assertEqual(eventlog.append(log, rerun['event_type'], rerun['payload'], rerun['event_id'], AT).result,
                         'duplicate')


if __name__ == '__main__':
    unittest.main()
