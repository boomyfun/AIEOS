"""Unit tests of aieos_bootstrap.evaluation_sources (TASK-158, BT3b-2c-1): the loader of the evaluation sources
(load_sources), the pin of the governor hash (pinned_governor) and the JSON parser (parse_json); the six new entries of
evaluation_policy.EVIDENCE_DEFINING_PATHS and their effect on evaluation_derive.evidence_comparison.

Every Git answer comes from a stand-in read over objects held in memory; the three files of the policy come from this
repository's working tree through pathlib's read_bytes; no test here runs Git, writes a file or makes a temporary folder.
"""

import ast
import hashlib
import json
import pathlib
import sys
import unittest
from unittest import mock

from aieos_bootstrap import (base_files, eval_inputs, evaluation, evaluation_derive, evaluation_policy,
                             evaluation_sources, gitread, scope_reconcile)

HERE = pathlib.Path(__file__).resolve()
ROOT = str(HERE.parents[2])
SRC = HERE.parents[2] / 'src' / 'aieos_bootstrap' / 'evaluation_sources.py'
ES = evaluation_sources
NEW6 = ('src/aieos_bootstrap/evaluation_sources.py', 'src/aieos_bootstrap/scope_reconcile.py',
        'src/aieos_bootstrap/base_inputs.py', 'src/aieos_bootstrap/base_files.py', 'src/aieos_bootstrap/evaluation.py',
        'src/aieos_bootstrap/ci_evidence.py')
POLICY = 'docs/specs/evaluation-policy-gov-aieos.md'
RISK = 'docs/specs/risk-rules-gov-aieos.md'
GOVERNOR = 'src/aieos_bootstrap/governor.py'
STAMP = '2026-01-01T00:00:00.1234567Z'
TASK = 'TASK-158'
KEYS = ('intent_versions', 'owner_kept_rules', 'articles', 'default_profiles', 'requirement_profiles',
        'evidence_comparison', 'delegation', 'auto_accept', 'level_version', 'ruleset_version', 'policy_version',
        'risk_rules')


def file_text(path):
    return (HERE.parents[2] / path).read_bytes().decode('utf-8').replace('\r\n', '\n')


REAL = {POLICY: file_text(POLICY), RISK: file_text(RISK), GOVERNOR: file_text(GOVERNOR)}
PIN = hashlib.sha256(REAL[GOVERNOR].encode('utf-8')).hexdigest()


def gid(kind, data):
    return hashlib.sha1(b'%s %d\x00' % (kind.encode('ascii'), len(data)) + data, usedforsecurity=False).hexdigest()


def ok(out):
    return {'exit': 0, 'out': out, 'err': b'', 'error': None}


def failed(code=128):
    return {'exit': code, 'out': b'', 'err': b'fatal', 'error': None}


class Git:
    """A stand-in for gitread.run over objects held in memory: ids are Git's own hashes of the objects."""

    def __init__(self):
        self.objects = {}
        self.diffs = {}
        self.calls = []
        self.override = {}

    def put(self, kind, data):
        oid = gid(kind, data)
        self.objects[oid] = (kind, data)
        return oid

    def tree_of(self, files):
        top = {}
        for path, text in files.items():
            parts = path.split('/')
            d = top
            for part in parts[:-1]:
                d = d.setdefault(part, {})
            d[parts[-1]] = text

        def make(d):
            entries = []
            for name, value in d.items():
                if isinstance(value, dict):
                    entries.append(('040000', 'tree', make(value), name))
                else:
                    data = value if isinstance(value, bytes) else value.encode('utf-8')
                    entries.append(('100644', 'blob', self.put('blob', data), name))
            return self.put('tree', ''.join('%s %s %s\t%s\n' % e for e in entries).encode('utf-8'))
        return make(top)

    def commit(self, tree, parents=(), message='m\n'):
        head = 'tree %s\n' % tree + ''.join('parent %s\n' % p for p in parents)
        text = head + 'author A B 1 +0000\ncommitter A B 1 +0000\n\n' + message
        return self.put('commit', text.encode('utf-8'))

    def __call__(self, repo, args, timeout=None):
        self.calls.append((repo, list(args), timeout))
        key = tuple(args)
        if key in self.override:
            value = self.override[key]
            if isinstance(value, BaseException):
                raise value
            return value
        oid = args[-1]
        if args[0] == 'rev-parse':
            return ok((oid + '\n').encode('ascii')) if oid in self.objects else failed()
        if args[:2] == ['cat-file', '-t'] and oid in self.objects:
            return ok((self.objects[oid][0] + '\n').encode('ascii'))
        if args[:2] == ['cat-file', '-p'] and oid in self.objects:
            return ok(self.objects[oid][1])
        if args[0] == 'diff-tree' and oid in self.diffs:
            return ok(self.diffs[oid])
        return failed()

    def commands(self, name):
        return [c for c in self.calls if c[1][0] == name]


def message_of(task=TASK, body='work'):
    return '%s\n\nAIEOS-Task: %s\n' % (body, task)


def scenario(files=None, changed=('src/x.py', 'tests/y.py'), parents=1):
    """A stand-in with a policy commit (the three files) and a task commit on it; returns (git, policy_ref, evaluated)."""
    g = Git()
    base = dict(REAL) if files is None else files
    p = g.commit(g.tree_of(base), message='policy\n')
    tip = p
    for n in range(parents):
        c = g.commit(g.tree_of(dict(base, **{'f%d.txt' % n: 'x'})), parents=(tip,), message=message_of(body='work %d' % n))
        g.diffs[c] = b''.join(name.encode('utf-8') + b'\x00' for name in changed)
        tip = c
    return g, p, tip


def pin_line(value=PIN, job='checks', step='Run', stamp=STAMP, name='AIEOS_PINNED_GOVERNOR', lead='  '):
    return '%s\t%s\t%s %s%s: %s' % (job, step, stamp, lead, name, value)


def log_of(*lines):
    return '\n'.join(lines) + '\n'


GOOD_LOG = log_of('checks\tSet up job\t' + STAMP + ' Current runner version', pin_line(),
                  'native\tRun\t' + STAMP + ' something else')


# The partial form of the four whole logs saved from the CI runs of TASK-158 (sizes and sha256 of the whole logs: AC3 (ii)), made by script:
# the first three lines and every line that holds the pin name (22 echo lines and 4 source lines with ANSI escapes), each kept as saved.
SAVED_PIN = '2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f'
PARTIAL_LOGS = (
    ('log_44906005836.txt', [
        "checks\tSet up job\t\ufeff2026-11-21T12:52:01.3572254Z Current runner version: '2.338.2'",
        'checks\tSet up job\t2026-11-21T12:52:01.3591374Z ##[group]Runner Image Provisioner',
        'checks\tSet up job\t2026-11-21T12:52:01.3592055Z Hosted Compute Agent',
        'checks\tFetch the pushed commit, its history and main (no third-party action, no token)\t2026-11-21T12:52:03.3071045Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tG0 task detection (the contract commit on main)\t2026-11-21T12:52:04.8959388Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tCollect the pushed commits and their changed paths\t2026-11-21T12:52:04.9358928Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        "checks\tSEC-001 secret scan (tip tree; every commit's message, file names and added lines)\t2026-11-21T12:52:04.9641666Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f",
        "checks\tSEC-002 pattern rules (every commit's added lines)\t2026-11-21T12:52:05.4049707Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f",
        'checks\tSEC-003 record (changes under .github/)\t2026-11-21T12:52:05.4168799Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tGOV-003 evaluator paths (reports an evaluator change)\t2026-11-21T12:52:05.4291394Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tOPS-002 owner-kept paths\t2026-11-21T12:52:05.4545922Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tINV-010 replay\t2026-11-21T12:52:05.4793178Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tG0 scope (V0)\t2026-11-21T12:52:06.9961711Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        "checks\tconformance base run (V1; the runner, its inputs and any governor from the base)\t2026-11-21T12:52:07.0259824Z \x1b[36;1m#              AIEOS_PINNED_GOVERNOR is empty) the step reports and does not fail on the run's outcome; with one pinned,\x1b[0m",
        "checks\tconformance base run (V1; the runner, its inputs and any governor from the base)\t2026-11-21T12:52:07.0283985Z \x1b[36;1mPINNED = os.environ.get('AIEOS_PINNED_GOVERNOR', '')\x1b[0m",
        'checks\tconformance base run (V1; the runner, its inputs and any governor from the base)\t2026-11-21T12:52:07.0399237Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        "checks\tconformance candidate run (advisory; the base inputs with the head's governor files)\t2026-11-21T12:52:07.0728541Z \x1b[36;1m#              AIEOS_PINNED_GOVERNOR is empty) the step reports and does not fail on the run's outcome; with one pinned,\x1b[0m",
        "checks\tconformance candidate run (advisory; the base inputs with the head's governor files)\t2026-11-21T12:52:07.0753407Z \x1b[36;1mPINNED = os.environ.get('AIEOS_PINNED_GOVERNOR', '')\x1b[0m",
        "checks\tconformance candidate run (advisory; the base inputs with the head's governor files)\t2026-11-21T12:52:07.0871473Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f",
        'checks\tG1 build\t2026-11-21T12:52:07.1210680Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tunit_test\t2026-11-21T12:52:07.1296589Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tintegration_test\t2026-11-21T12:52:07.1380362Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tproperty_test\t2026-11-21T12:52:07.1463412Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tGOV-003 evaluator lists equal\t2026-11-21T12:52:07.1553230Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tdeterministic_rule (INV-001, INV-002, INV-004)\t2026-11-21T12:52:07.2050355Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tOPS-003 pattern rules\t2026-11-21T12:52:07.2596328Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tstatic_security_analysis (bandit, every package pinned by version and hash)\t2026-11-21T12:52:07.2892259Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tlint (pyflakes 4.0.3, pinned by version and hash)\t2026-11-21T12:52:07.2973423Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tGOV-003 base tests (report only)\t2026-11-21T12:52:07.3058706Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f'
    ]),
    ('log_44906763551.txt', [
        "checks\tSet up job\t\ufeff2026-11-21T13:01:31.8375469Z Current runner version: '2.338.2'",
        'checks\tSet up job\t2026-11-21T13:01:31.8402263Z ##[group]Runner Image Provisioner',
        'checks\tSet up job\t2026-11-21T13:01:31.8403199Z Hosted Compute Agent',
        'checks\tFetch the pushed commit, its history and main (no third-party action, no token)\t2026-11-21T13:01:33.1236317Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tG0 task detection (the contract commit on main)\t2026-11-21T13:01:34.8927199Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tCollect the pushed commits and their changed paths\t2026-11-21T13:01:34.9309525Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        "checks\tSEC-001 secret scan (tip tree; every commit's message, file names and added lines)\t2026-11-21T13:01:34.9631909Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f",
        "checks\tSEC-002 pattern rules (every commit's added lines)\t2026-11-21T13:01:35.4139763Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f",
        'checks\tSEC-003 record (changes under .github/)\t2026-11-21T13:01:35.4256471Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tGOV-003 evaluator paths (reports an evaluator change)\t2026-11-21T13:01:35.4380230Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tOPS-002 owner-kept paths\t2026-11-21T13:01:35.4635313Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tINV-010 replay\t2026-11-21T13:01:35.4883747Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tG0 scope (V0)\t2026-11-21T13:01:37.0073812Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        "checks\tconformance base run (V1; the runner, its inputs and any governor from the base)\t2026-11-21T13:01:37.0371877Z \x1b[36;1m#              AIEOS_PINNED_GOVERNOR is empty) the step reports and does not fail on the run's outcome; with one pinned,\x1b[0m",
        "checks\tconformance base run (V1; the runner, its inputs and any governor from the base)\t2026-11-21T13:01:37.0397288Z \x1b[36;1mPINNED = os.environ.get('AIEOS_PINNED_GOVERNOR', '')\x1b[0m",
        'checks\tconformance base run (V1; the runner, its inputs and any governor from the base)\t2026-11-21T13:01:37.0519818Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        "checks\tconformance candidate run (advisory; the base inputs with the head's governor files)\t2026-11-21T13:01:37.0903977Z \x1b[36;1m#              AIEOS_PINNED_GOVERNOR is empty) the step reports and does not fail on the run's outcome; with one pinned,\x1b[0m",
        "checks\tconformance candidate run (advisory; the base inputs with the head's governor files)\t2026-11-21T13:01:37.0930107Z \x1b[36;1mPINNED = os.environ.get('AIEOS_PINNED_GOVERNOR', '')\x1b[0m",
        "checks\tconformance candidate run (advisory; the base inputs with the head's governor files)\t2026-11-21T13:01:37.1051148Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f",
        'checks\tG1 build\t2026-11-21T13:01:37.1379804Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tunit_test\t2026-11-21T13:01:37.1467324Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tintegration_test\t2026-11-21T13:01:37.1550752Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tproperty_test\t2026-11-21T13:01:37.1634219Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tGOV-003 evaluator lists equal\t2026-11-21T13:01:37.1724036Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tdeterministic_rule (INV-001, INV-002, INV-004)\t2026-11-21T13:01:37.2342017Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tOPS-003 pattern rules\t2026-11-21T13:01:37.2745927Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tstatic_security_analysis (bandit, every package pinned by version and hash)\t2026-11-21T13:01:37.3249170Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tlint (pyflakes 4.0.3, pinned by version and hash)\t2026-11-21T13:01:37.3332370Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tGOV-003 base tests (report only)\t2026-11-21T13:01:37.3419737Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f'
    ]),
    ('log_44909901732.txt', [
        "checks\tSet up job\t\ufeff2026-11-21T13:38:57.6001784Z Current runner version: '2.338.2'",
        'checks\tSet up job\t2026-11-21T13:38:57.6020617Z ##[group]Runner Image Provisioner',
        'checks\tSet up job\t2026-11-21T13:38:57.6021329Z Hosted Compute Agent',
        'checks\tFetch the pushed commit, its history and main (no third-party action, no token)\t2026-11-21T13:38:59.4900175Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tG0 task detection (the contract commit on main)\t2026-11-21T13:39:01.3495096Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tCollect the pushed commits and their changed paths\t2026-11-21T13:39:01.4026284Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        "checks\tSEC-001 secret scan (tip tree; every commit's message, file names and added lines)\t2026-11-21T13:39:01.4302147Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f",
        "checks\tSEC-002 pattern rules (every commit's added lines)\t2026-11-21T13:39:01.8557656Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f",
        'checks\tSEC-003 record (changes under .github/)\t2026-11-21T13:39:01.8673623Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tGOV-003 evaluator paths (reports an evaluator change)\t2026-11-21T13:39:01.8794895Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tOPS-002 owner-kept paths\t2026-11-21T13:39:01.9049906Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tINV-010 replay\t2026-11-21T13:39:01.9288712Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tG0 scope (V0)\t2026-11-21T13:39:03.4274327Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        "checks\tconformance base run (V1; the runner, its inputs and any governor from the base)\t2026-11-21T13:39:03.4700245Z \x1b[36;1m#              AIEOS_PINNED_GOVERNOR is empty) the step reports and does not fail on the run's outcome; with one pinned,\x1b[0m",
        "checks\tconformance base run (V1; the runner, its inputs and any governor from the base)\t2026-11-21T13:39:03.4725560Z \x1b[36;1mPINNED = os.environ.get('AIEOS_PINNED_GOVERNOR', '')\x1b[0m",
        'checks\tconformance base run (V1; the runner, its inputs and any governor from the base)\t2026-11-21T13:39:03.4846587Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        "checks\tconformance candidate run (advisory; the base inputs with the head's governor files)\t2026-11-21T13:39:03.8529155Z \x1b[36;1m#              AIEOS_PINNED_GOVERNOR is empty) the step reports and does not fail on the run's outcome; with one pinned,\x1b[0m",
        "checks\tconformance candidate run (advisory; the base inputs with the head's governor files)\t2026-11-21T13:39:03.8554511Z \x1b[36;1mPINNED = os.environ.get('AIEOS_PINNED_GOVERNOR', '')\x1b[0m",
        "checks\tconformance candidate run (advisory; the base inputs with the head's governor files)\t2026-11-21T13:39:03.8681703Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f",
        'checks\tG1 build\t2026-11-21T13:39:03.9111936Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tunit_test\t2026-11-21T13:39:04.6418964Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tintegration_test\t2026-11-21T13:39:46.4586803Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tproperty_test\t2026-11-21T13:40:17.8113088Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tGOV-003 evaluator lists equal\t2026-11-21T13:40:54.2928111Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tdeterministic_rule (INV-001, INV-002, INV-004)\t2026-11-21T13:40:54.3404155Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tOPS-003 pattern rules\t2026-11-21T13:40:56.6661589Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tstatic_security_analysis (bandit, every package pinned by version and hash)\t2026-11-21T13:40:57.2634604Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tlint (pyflakes 4.0.3, pinned by version and hash)\t2026-11-21T13:41:09.7645302Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tGOV-003 base tests (report only)\t2026-11-21T13:41:15.8828526Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f'
    ]),
    ('log_44911201609.txt', [
        "checks\tSet up job\t\ufeff2026-11-21T13:54:45.2594469Z Current runner version: '2.338.2'",
        'checks\tSet up job\t2026-11-21T13:54:45.2613280Z ##[group]Runner Image Provisioner',
        'checks\tSet up job\t2026-11-21T13:54:45.2613976Z Hosted Compute Agent',
        'checks\tFetch the pushed commit, its history and main (no third-party action, no token)\t2026-11-21T13:54:47.0420776Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tG0 task detection (the contract commit on main)\t2026-11-21T13:54:48.9881841Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tCollect the pushed commits and their changed paths\t2026-11-21T13:54:49.0353779Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        "checks\tSEC-001 secret scan (tip tree; every commit's message, file names and added lines)\t2026-11-21T13:54:49.0773455Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f",
        "checks\tSEC-002 pattern rules (every commit's added lines)\t2026-11-21T13:54:49.5174767Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f",
        'checks\tSEC-003 record (changes under .github/)\t2026-11-21T13:54:49.5313077Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tGOV-003 evaluator paths (reports an evaluator change)\t2026-11-21T13:54:49.5456891Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tOPS-002 owner-kept paths\t2026-11-21T13:54:49.5736877Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tINV-010 replay\t2026-11-21T13:54:49.6053935Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tG0 scope (V0)\t2026-11-21T13:54:51.1020001Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        "checks\tconformance base run (V1; the runner, its inputs and any governor from the base)\t2026-11-21T13:54:51.1339665Z \x1b[36;1m#              AIEOS_PINNED_GOVERNOR is empty) the step reports and does not fail on the run's outcome; with one pinned,\x1b[0m",
        "checks\tconformance base run (V1; the runner, its inputs and any governor from the base)\t2026-11-21T13:54:51.1364947Z \x1b[36;1mPINNED = os.environ.get('AIEOS_PINNED_GOVERNOR', '')\x1b[0m",
        'checks\tconformance base run (V1; the runner, its inputs and any governor from the base)\t2026-11-21T13:54:51.1491297Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        "checks\tconformance candidate run (advisory; the base inputs with the head's governor files)\t2026-11-21T13:54:51.5744127Z \x1b[36;1m#              AIEOS_PINNED_GOVERNOR is empty) the step reports and does not fail on the run's outcome; with one pinned,\x1b[0m",
        "checks\tconformance candidate run (advisory; the base inputs with the head's governor files)\t2026-11-21T13:54:51.5770261Z \x1b[36;1mPINNED = os.environ.get('AIEOS_PINNED_GOVERNOR', '')\x1b[0m",
        "checks\tconformance candidate run (advisory; the base inputs with the head's governor files)\t2026-11-21T13:54:51.5901445Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f",
        'checks\tG1 build\t2026-11-21T13:54:51.6263298Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tunit_test\t2026-11-21T13:54:51.6362917Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tintegration_test\t2026-11-21T13:54:51.6455777Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tproperty_test\t2026-11-21T13:54:51.6546784Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tGOV-003 evaluator lists equal\t2026-11-21T13:54:51.6644244Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tdeterministic_rule (INV-001, INV-002, INV-004)\t2026-11-21T13:54:51.7368324Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tOPS-003 pattern rules\t2026-11-21T13:54:51.7752727Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tstatic_security_analysis (bandit, every package pinned by version and hash)\t2026-11-21T13:54:51.8062868Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tlint (pyflakes 4.0.3, pinned by version and hash)\t2026-11-21T13:54:51.8159416Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f',
        'checks\tGOV-003 base tests (report only)\t2026-11-21T13:54:51.8264988Z   AIEOS_PINNED_GOVERNOR: 2f2dcd7525bcc39dcb3539ada93daff428a624cf2c47876c2d17599cf7ec022f'
    ]),
)


def load(g=None, p=None, e=None, **over):
    if g is None:
        g, p, e = scenario()
    args = dict(repo=ROOT, policy_ref=p, evaluated_commit=e, task_id=TASK, ci_logs=[GOOD_LOG], read=g)
    args.update(over)
    return ES.load_sources(**args)


def reason_of(answer):
    return answer['findings'][0]['reason']


class Base(unittest.TestCase):
    def refused(self, answer, reason):
        self.assertEqual(answer['result'], 'refused')
        self.assertIsNone(answer['sources'])
        self.assertIsNone(answer['changed_paths'])
        self.assertEqual(answer['provenance'], [])
        self.assertEqual(len(answer['findings']), 1)
        self.assertEqual(set(answer['findings'][0]), {'reason', 'detail'})
        self.assertEqual(answer['findings'][0]['reason'], reason)
        self.assertIsInstance(answer['findings'][0]['detail'], str)
        self.assertLessEqual(len(answer['findings'][0]['detail']), 200)
        return answer['findings'][0]['detail']


class AC1TheEntries(unittest.TestCase):
    def test_the_six_entries_follow_the_derive_entry_in_this_order(self):
        paths = evaluation_policy.EVIDENCE_DEFINING_PATHS
        self.assertEqual(len(paths), 16)
        self.assertEqual(len(set(paths)), 16)
        self.assertEqual(paths[9], 'src/aieos_bootstrap/evaluation_derive.py')
        self.assertEqual(paths[10:], NEW6)

    def test_each_entry_weakens_the_comparison_and_an_other_source_file_does_not(self):
        for path in NEW6:
            self.assertEqual(evaluation_derive.evidence_comparison([path]), {'weakens': True}, path)
            self.assertEqual(evaluation_derive.evidence_comparison([path.upper()]), {'weakens': True}, path)
        self.assertEqual(evaluation_derive.evidence_comparison(['src/aieos_bootstrap/other_module.py']), {'weakens': False})

    def test_the_public_names_exist(self):
        for name in ('load_sources', 'pinned_governor', 'parse_json'):
            self.assertTrue(callable(getattr(ES, name)), name)
        self.assertEqual(ES.POLICY_PATH, POLICY)
        self.assertEqual(ES.RISK_PATH, RISK)
        self.assertEqual(ES.RISK_PATH, scope_reconcile.POLICY_PATH)
        self.assertEqual(ES.GOVERNOR_PATH, GOVERNOR)
        self.assertEqual(ES.JOB, 'checks')


class AC2TheTwelveSources(Base):
    def test_the_answer_of_a_good_call(self):
        g, p, e = scenario()
        a = load(g, p, e)
        self.assertEqual(a['result'], 'present')
        self.assertEqual(a['findings'], [])
        self.assertEqual(set(a), {'result', 'sources', 'changed_paths', 'provenance', 'findings'})
        self.assertEqual(list(a['sources']), list(KEYS))
        self.assertEqual(list(a['sources']), list(eval_inputs._GAPS))
        self.assertIsNone(a['sources']['intent_versions'])
        for key in KEYS[1:]:
            self.assertIsNotNone(a['sources'][key], key)
        self.assertEqual(a['changed_paths'], ['src/x.py', 'tests/y.py'])
        self.assertEqual(a['sources']['evidence_comparison'], {'weakens': False})

    def test_the_derived_values_have_their_exact_texts(self):
        a = load()
        s = a['sources']
        self.assertEqual(s['ruleset_version'], 'governor-sha256:' + PIN)
        self.assertTrue(s['level_version'].startswith('L1:'))
        self.assertEqual(s['level_version'], 'L1:' + s['policy_version'])
        self.assertEqual(s['level_version'], evaluation_derive.level_version(s['policy_version'])['value'])

    def test_the_policy_sources_are_those_of_the_policy_reader(self):
        a = load()
        parsed = evaluation_policy.read_evaluation_policy(REAL[POLICY])
        self.assertEqual(parsed['result'], 'present')
        for key in ('owner_kept_rules', 'articles', 'default_profiles', 'requirement_profiles', 'delegation', 'auto_accept'):
            self.assertEqual(a['sources'][key], parsed['sources'][key], key)

    def test_the_risk_sources_are_those_of_the_risk_rules_file(self):
        a = load()
        self.assertEqual(a['sources']['risk_rules'], scope_reconcile.rules_from_policy(REAL[RISK]))
        self.assertTrue(a['sources']['risk_rules'])
        for rule in a['sources']['risk_rules']:
            self.assertEqual(set(rule), {'match', 'class'})
            self.assertIn(rule['class'], ('low', 'medium', 'high', 'critical'))
        block = scope_reconcile.policy_block(REAL[RISK])
        versions = [line[len('policy_version: '):] for line in block if line.startswith('policy_version: ')]
        self.assertEqual(len(versions), 1)
        self.assertEqual(a['sources']['policy_version'], versions[0])

    def test_the_provenance(self):
        g, p, e = scenario()
        a = load(g, p, e)
        prov = a['provenance']
        self.assertEqual(len(prov), 5)
        for entry, path in zip(prov[:3], (POLICY, RISK, GOVERNOR)):
            self.assertEqual(set(entry), {'path', 'commit', 'blob', 'sha256'})
            self.assertEqual(entry['path'], path)
            self.assertEqual(entry['commit'], p)
            self.assertEqual(entry['sha256'], hashlib.sha256(REAL[path].encode('utf-8')).hexdigest())
            kind, data = g.objects[entry['blob']]
            self.assertEqual(kind, 'blob')
            self.assertEqual(data, REAL[path].encode('utf-8'))
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry['sha256'])
        self.assertEqual(prov[3], {'pin': 'ci_log', 'value': PIN, 'logs': 1})
        self.assertEqual(prov[4], {'source': 'intent_versions', 'state': 'open gap: no producer'})

    def test_every_read_is_at_the_policy_ref_and_the_walk_at_the_evaluated_commit(self):
        g, p, e = scenario()
        load(g, p, e)
        for repo, args, timeout in g.calls:
            self.assertEqual(repo, ROOT)
            if args[0] == 'cat-file' and args[1] == '-p' and args[2] in g.objects and g.objects[args[2]][0] == 'commit':
                self.assertIn(args[2], (p, e))
        self.assertTrue(g.commands('diff-tree'))
        self.assertEqual([c[1][-1] for c in g.commands('diff-tree')], [e])
        self.assertEqual(g.commands('diff-tree')[0][1][:-1], evaluation.DIFF_FORM)

    def test_the_call_form_with_no_read_uses_gitread_run_for_the_files_and_for_the_walk(self):
        """read=None: gitread.run is replaced (undone at the end) by the recording stand-in; the files are read with the
        timeout of base_files, the walk reads without one, and every rev-parse names policy_ref exactly."""
        g, p, e = scenario()
        original = gitread.run
        with mock.patch.object(gitread, 'run', g):
            self.assertIs(gitread.run, g)
            a = ES.load_sources(ROOT, p, e, TASK, [GOOD_LOG])
        self.assertIs(gitread.run, original)
        self.assertEqual(a['result'], 'present')
        timed = [c for c in g.calls if c[2] == base_files.TIMEOUT]
        self.assertTrue(timed)
        self.assertEqual([c[1][-1] for c in g.commands('rev-parse')], [p, p, p])
        self.assertTrue(all(c[2] == base_files.TIMEOUT for c in g.commands('rev-parse')))
        walk = [c for c in g.calls if c[2] is None]
        self.assertTrue(walk)
        self.assertEqual([c[1][-1] for c in g.commands('diff-tree')], [e])
        self.assertTrue(all(c[2] is None for c in g.commands('diff-tree')))
        self.assertEqual(len(timed) + len(walk), len(g.calls))

    def test_every_rev_parse_of_a_load_with_a_read_names_the_policy_ref(self):
        g, p, e = scenario()
        load(g, p, e)
        for call in g.commands('rev-parse'):
            self.assertEqual(call[1], ['rev-parse', '--verify', '--end-of-options', p])

    def test_the_task_change_is_the_union_of_the_commits_sorted_without_duplicate(self):
        g = Git()
        base = dict(REAL)
        p = g.commit(g.tree_of(base), message='policy\n')
        c1 = g.commit(g.tree_of(dict(base, a='1')), (p,), message_of(body='one'))
        c2 = g.commit(g.tree_of(dict(base, a='2')), (c1,), message_of(body='two'))
        c3 = g.commit(g.tree_of(dict(base, a='3')), (c2,), message_of(body='three'))
        g.diffs[c1] = b'tests/b.py\x00src/a.py\x00'
        g.diffs[c2] = b'src/a.py\x00tests/c.py\x00'
        g.diffs[c3] = b'tests/b.py\x00'
        a = load(g, p, c3)
        self.assertEqual(a['changed_paths'], ['src/a.py', 'tests/b.py', 'tests/c.py'])
        self.assertEqual(len(g.commands('diff-tree')), 3)

    def test_the_change_of_a_policy_path_is_passed_on_and_weakens(self):
        a = load(*scenario(changed=(POLICY,)))
        self.assertEqual(a['changed_paths'], [POLICY])
        self.assertEqual(a['sources']['evidence_comparison'], {'weakens': True})

    def test_an_evidence_defining_change_weakens(self):
        a = load(*scenario(changed=(NEW6[0],)))
        self.assertEqual(a['sources']['evidence_comparison'], {'weakens': True})


class AC2TheNextStep(Base):
    def test_eval_inputs_refuses_the_open_gap_and_names_only_it(self):
        """The contract values here are fixture contract values, labelled as not policy (D-7063 N8): the test checks
        that the one refusal of the next step is the open gap of intent_versions, whatever the contract says."""
        a = load()
        contract = {'traces_to': ['G1'], 'risk': 'low', 'owner_kept_act': 'false', 'verification_plan': [{'gate': 'G1'}],
                    'autonomy': {}}
        made = eval_inputs.eval_inputs(TASK, 'b' * 40, 'a' * 40, contract, 'c' * 64, a['changed_paths'], [], a['sources'],
                                       [], 'recorder')
        self.assertEqual(made['refusal'], {'reason': 'gap', 'detail': 'open gaps: intent_versions'})


class AC3ThePin(Base):
    def test_the_pin_from_one_log(self):
        self.assertEqual(ES.pinned_governor([GOOD_LOG]), {'value': PIN, 'findings': []})

    def test_the_pin_from_several_logs_of_one_value(self):
        self.assertEqual(ES.pinned_governor([GOOD_LOG, GOOD_LOG, log_of(pin_line(), pin_line())])['value'], PIN)

    def test_a_line_of_another_job_is_skipped(self):
        other = log_of('checks\tSet up\t' + STAMP + ' x', pin_line('f' * 64, job='native'), pin_line())
        self.assertEqual(ES.pinned_governor([other])['value'], PIN)

    def test_a_log_with_no_line_of_the_job_is_refused(self):
        r = ES.pinned_governor([log_of(pin_line(job='native'))])
        self.assertIsNone(r['value'])
        self.assertEqual(r['findings'][0]['reason'], 'pin')

    def test_a_log_with_no_pin_line_is_refused(self):
        r = ES.pinned_governor([log_of('checks\tRun\t' + STAMP + ' nothing here')])
        self.assertIsNone(r['value'])

    def test_differing_pins_are_refused(self):
        r = ES.pinned_governor([GOOD_LOG, log_of(pin_line('0' * 64))])
        self.assertIsNone(r['value'])
        self.assertEqual(r['findings'][0]['reason'], 'pin')
        r = ES.pinned_governor([log_of(pin_line(), pin_line('0' * 64))])
        self.assertIsNone(r['value'])

    def test_the_form_of_the_hash_and_of_the_message(self):
        for line in (pin_line(PIN[:63]), pin_line(PIN + '0'), pin_line(PIN.upper()), pin_line(lead=' '),
                     pin_line(lead='   '), pin_line(lead=''), pin_line(name='AIEOS_PINNED_GOVERNORS'),
                     pin_line(name='aieos_pinned_governor')):
            r = ES.pinned_governor([log_of(line)])
            self.assertIsNone(r['value'], line)

    def test_a_line_not_in_the_log_form_refuses_the_log(self):
        for bad in ('checks\tonly two fields', 'no tabs at all', 'checks\tRun\tnot a stamp message',
                    'checks\tRun\t' + STAMP[:-1]):
            r = ES.pinned_governor([log_of(pin_line(), bad)])
            self.assertIsNone(r['value'], bad)

    def test_a_timestamp_only_line_and_a_bom_are_in_form(self):
        log = log_of('checks\tRun\t' + STAMP, '\ufeff'.join(('checks\tRun\t', STAMP + ' text')), pin_line())
        self.assertEqual(ES.pinned_governor([log])['value'], PIN)

    def test_one_trailing_cr_is_taken_off_a_line_and_two_are_not(self):
        one = pin_line() + '\r\n'
        self.assertEqual(ES.pinned_governor([one])['value'], PIN)
        two = pin_line() + '\r\r\n'
        self.assertIsNone(ES.pinned_governor([two])['value'])

    def test_an_empty_list_an_empty_log_and_a_wrong_type_are_refused(self):
        for bad in ([], [''], ['\n'], None, 'text', [None], [b'x'], (GOOD_LOG,), 5, b'x', 1.5, True, {}, [5], [[GOOD_LOG]]):
            r = ES.pinned_governor(bad)
            self.assertIsNone(r['value'], repr(bad))
            self.assertEqual(r['findings'][0]['reason'], 'pin')

    def test_load_sources_with_an_empty_list_of_logs_passes_the_argument_step_and_is_refused_as_pin(self):
        g, p, e = scenario()
        self.refused(load(g, p, e, ci_logs=[]), 'pin')
        self.assertTrue(g.calls)

    def test_the_tab_in_the_message_is_kept_in_the_third_field(self):
        log = log_of('checks\tRun\t' + STAMP + ' a\tb', pin_line())
        self.assertEqual(ES.pinned_governor([log])['value'], PIN)

    def test_the_reasons_and_the_closed_form(self):
        r = ES.pinned_governor([])
        self.assertEqual(set(r), {'value', 'findings'})
        self.assertEqual(set(r['findings'][0]), {'reason', 'detail'})
        self.assertEqual(ES.pinned_governor([GOOD_LOG])['findings'], [])

    def test_the_governor_hash_differing_from_the_pin_is_refused_by_load_sources(self):
        a = load(ci_logs=[log_of(pin_line('1' * 64))])
        self.assertEqual(reason_of(a), 'governor')
        self.refused(a, 'governor')

    def test_a_missing_pin_is_refused_by_load_sources(self):
        self.refused(load(ci_logs=[log_of('checks\tRun\t' + STAMP + ' none')]), 'pin')


class AC3ThePartialSavedLogs(Base):
    """AC3 (i): the partial form of the four whole saved logs (the fixture above, made by script)."""

    @staticmethod
    def text_of(lines):
        return '\n'.join(lines) + '\n'

    def test_the_fixture_has_the_pinned_shape(self):
        self.assertEqual(len(PARTIAL_LOGS), 4)
        for name, lines in PARTIAL_LOGS:
            self.assertEqual(len(lines), 29, name)
            self.assertTrue(all(line.startswith('checks\t') for line in lines), name)
            named = [line for line in lines if 'AIEOS_PINNED_GOVERNOR' in line]
            self.assertEqual(len(named), 26, name)
            self.assertEqual(sum(1 for line in named if line.endswith('  AIEOS_PINNED_GOVERNOR: ' + SAVED_PIN)), 22, name)
            self.assertEqual(sum(1 for line in named if '\x1b[' in line), 4, name)
            self.assertTrue(lines[0].split('\t')[2].startswith('\ufeff'), name)

    def test_each_partial_log_gives_the_pin(self):
        for name, lines in PARTIAL_LOGS:
            self.assertEqual(ES.pinned_governor([self.text_of(lines)]), {'value': SAVED_PIN, 'findings': []}, name)

    def test_the_four_together_give_the_pin(self):
        logs = [self.text_of(lines) for _, lines in PARTIAL_LOGS]
        self.assertEqual(ES.pinned_governor(logs), {'value': SAVED_PIN, 'findings': []})

    def test_the_lines_with_the_name_inside_other_text_give_no_pin_alone(self):
        for name, lines in PARTIAL_LOGS:
            only = [line for line in lines if '\x1b[' in line or 'AIEOS_PINNED_GOVERNOR' not in line]
            r = ES.pinned_governor([self.text_of(only)])
            self.assertIsNone(r['value'], name)
            self.assertEqual(r['findings'][0]['reason'], 'pin', name)

    def test_a_partial_log_with_the_echo_lines_of_another_value_is_refused(self):
        name, lines = PARTIAL_LOGS[0]
        other = [line.replace(SAVED_PIN, '3' * 64) if line.endswith(SAVED_PIN) else line for line in lines]
        self.assertIsNone(ES.pinned_governor([self.text_of(lines), self.text_of(other)])['value'])

    def test_a_tab_lead_is_refused(self):
        self.assertIsNone(ES.pinned_governor([log_of(pin_line(lead='\t'))])['value'])
        self.assertIsNone(ES.pinned_governor([log_of(pin_line(lead=' \t'))])['value'])

    def test_the_name_inside_other_text_only_is_refused(self):
        line = 'checks\tRun\t' + STAMP + " PINNED = os.environ.get('AIEOS_PINNED_GOVERNOR', '')"
        r = ES.pinned_governor([log_of(line)])
        self.assertIsNone(r['value'])
        self.assertEqual(r['findings'][0]['reason'], 'pin')
        line = 'checks\tRun\t' + STAMP + ' text   AIEOS_PINNED_GOVERNOR: ' + SAVED_PIN
        self.assertIsNone(ES.pinned_governor([log_of(line)])['value'])

    def test_several_logs_where_one_has_no_pin_line_are_refused(self):
        none = log_of('checks\tRun\t' + STAMP + ' nothing')
        for logs in ([GOOD_LOG, none], [none, GOOD_LOG], [GOOD_LOG, GOOD_LOG, none]):
            self.assertIsNone(ES.pinned_governor(logs)['value'])

    def test_a_very_long_text_is_refused_without_a_raise(self):
        long_line = 'checks\tRun\t' + STAMP + ' ' + 'x' * 2000000
        r = ES.pinned_governor([log_of(long_line)])
        self.assertIsNone(r['value'])
        self.assertEqual(r['findings'][0]['reason'], 'pin')
        self.assertLessEqual(len(r['findings'][0]['detail']), 200)
        r = ES.pinned_governor([log_of(pin_line(), long_line)])
        self.assertEqual(r['value'], PIN)


class AC4ParseJson(unittest.TestCase):
    def test_plain_values(self):
        for text, value in (('null', None), ('true', True), ('0', 0), ('-1.5', -1.5), ('"s"', 's'), ('[]', []),
                            ('{}', {}), ('{"a": [1, {"b": null}]}', {'a': [1, {'b': None}]})):
            self.assertEqual(ES.parse_json(text), {'value': value, 'findings': []}, text)

    def test_valid_nested_data_equals_json_loads_of_the_same_text(self):
        for text in ('{"a": [1, 2.5, {"b": [true, false, null, "x"]}], "c": {"d": {"e": []}}}', '[[[1], [2, [3]]], {"k": "v"}]',
                     '{"s": "\\u00e9\\n", "n": -0, "m": 1e2}', ' \n[1, 2]\t', '"text"', '12345678901234567890'):
            self.assertEqual(ES.parse_json(text), {'value': json.loads(text), 'findings': []}, text)

    def test_null_gives_none_with_no_finding(self):
        r = ES.parse_json('null')
        self.assertIsNone(r['value'])
        self.assertEqual(r['findings'], [])

    def test_the_constants_are_refused_at_any_depth(self):
        for text in ('NaN', 'Infinity', '-Infinity', '[NaN]', '{"a": [[Infinity]]}', '{"a": {"b": -Infinity}}'):
            r = ES.parse_json(text)
            self.assertIsNone(r['value'], text)
            self.assertEqual(r['findings'][0]['reason'], 'constant', text)

    def test_a_repeated_key_is_refused_at_any_depth(self):
        for text in ('{"a": 1, "a": 2}', '[{"a": 1, "b": 2, "a": 3}]', '{"x": {"y": 1, "y": 1}}'):
            r = ES.parse_json(text)
            self.assertIsNone(r['value'], text)
            self.assertEqual(r['findings'][0]['reason'], 'duplicate', text)

    def test_the_same_key_in_two_objects_is_not_a_repeat(self):
        self.assertEqual(ES.parse_json('[{"a": 1}, {"a": 2}]')['value'], [{'a': 1}, {'a': 2}])

    def test_depth_fifty_is_taken_and_fifty_one_refused(self):
        self.assertEqual(ES.parse_json('[' * 50 + ']' * 50)['findings'], [])
        r = ES.parse_json('[' * 51 + ']' * 51)
        self.assertIsNone(r['value'])
        self.assertEqual(r['findings'][0]['reason'], 'plain')

    def test_a_float_that_is_not_finite_is_refused_as_not_plain(self):
        r = ES.parse_json('1e400')
        self.assertIsNone(r['value'])
        self.assertEqual(r['findings'][0]['reason'], 'plain')

    def test_text_that_is_not_json_or_too_deep_for_the_parser(self):
        for text in ('{', '[1,]', "{'a': 1}", 'tru', '1 2'):
            r = ES.parse_json(text)
            self.assertIsNone(r['value'], text)
            self.assertEqual(r['findings'][0]['reason'], 'json', text)
        r = ES.parse_json('[' * 100000 + ']' * 100000)
        self.assertIsNone(r['value'])
        self.assertEqual(r['findings'][0]['reason'], 'json')

    def test_an_integer_literal_over_the_interpreter_limit_is_refused_as_json(self):
        """The limit of digits is the interpreter's own (sys.get_int_max_str_digits); the run states its Python."""
        if not hasattr(sys, 'get_int_max_str_digits'):
            self.skipTest('this interpreter has no limit of digits for an integer text (Python %s)' % sys.version.split()[0])
        limit = sys.get_int_max_str_digits()
        if limit == 0:
            self.skipTest('this interpreter has no limit of digits for an integer text (Python %s)' % sys.version.split()[0])
        r = ES.parse_json('1' * (limit + 1))
        self.assertIsNone(r['value'])
        self.assertEqual(r['findings'][0]['reason'], 'json')
        self.assertEqual(ES.parse_json('1' * limit)['findings'], [])

    def test_the_finding_of_plain_data_is_passed_on_with_its_detail_unchanged(self):
        r = ES.parse_json('1e400')
        self.assertEqual(r['findings'][0]['detail'], evaluation_derive.plain_data_problem(float('inf'))['detail'])
        deep = []
        for _ in range(50):
            deep = [deep]
        self.assertEqual(ES.parse_json('[' * 51 + ']' * 51)['findings'][0]['detail'],
                         evaluation_derive.plain_data_problem(deep)['detail'])

    def test_an_argument_that_is_not_a_text_is_refused(self):
        for bad in (None, b'{}', 1, [], {}, '\ud800', ''):
            r = ES.parse_json(bad)
            self.assertIsNone(r['value'], repr(bad))
            self.assertEqual(r['findings'][0]['reason'], 'argument', repr(bad))

    def test_the_reasons_are_a_closed_set(self):
        seen = set()
        for text in ('NaN', '{"a":1,"a":2}', '{', '1e400', '[' * 51 + ']' * 51):
            seen.add(ES.parse_json(text)['findings'][0]['reason'])
        seen.add(ES.parse_json(None)['findings'][0]['reason'])
        self.assertEqual(seen, {'argument', 'json', 'constant', 'duplicate', 'plain'})

    def test_a_str_subclass_does_not_matter_for_the_form(self):
        class S(str):
            pass
        self.assertEqual(ES.parse_json(S('[1]'))['findings'][0]['reason'], 'argument')

    def test_the_value_is_a_fresh_one_each_call(self):
        a = ES.parse_json('{"a": [1]}')['value']
        b = ES.parse_json('{"a": [1]}')['value']
        self.assertEqual(a, b)
        self.assertIsNot(a, b)
        self.assertIsNot(a['a'], b['a'])


class AC5TheChangedPaths(Base):
    def test_one_commit(self):
        self.assertEqual(load(*scenario(changed=('src/b.py', 'src/a.py')))['changed_paths'], ['src/a.py', 'src/b.py'])

    def test_three_commits_walk_to_the_first_one_that_is_not_the_tasks(self):
        g, p, e = scenario(parents=3)
        a = load(g, p, e)
        self.assertEqual(a['result'], 'present')
        self.assertEqual(len(g.commands('diff-tree')), 3)

    def test_a_merge_is_refused_as_git(self):
        g = Git()
        p = g.commit(g.tree_of(dict(REAL)), message='policy\n')
        other = g.commit(g.tree_of(dict(REAL, z='1')), (p,), message='side\n')
        merge = g.commit(g.tree_of(dict(REAL, z='2')), (p, other), message_of())
        g.diffs[merge] = b'src/x.py\x00'
        detail = self.refused(load(g, p, merge), 'git')
        self.assertTrue(detail.startswith('merge:'), detail)

    def test_the_bound_and_exactly_the_bound(self):
        g, p, e = scenario(parents=3)
        self.assertEqual(load(g, p, e, max_commits=3)['result'], 'present')
        detail = self.refused(load(g, p, e, max_commits=2), 'git')
        self.assertTrue(detail.startswith('bound:'), detail)

    def test_a_read_that_raises_is_refused_as_git(self):
        g, p, e = scenario()
        g.override[tuple(evaluation.DIFF_FORM + [e])] = RuntimeError('boom')
        detail = self.refused(load(g, p, e), 'git')
        self.assertEqual(detail, 'git: RuntimeError')

    def test_a_failed_diff_is_refused_as_git(self):
        g, p, e = scenario()
        g.override[tuple(evaluation.DIFF_FORM + [e])] = failed(1)
        self.refused(load(g, p, e), 'git')

    def test_a_change_of_no_path_is_refused_as_git(self):
        self.refused(load(*scenario(changed=())), 'git')

    def test_an_evaluated_commit_that_is_not_the_tasks_is_refused_as_git(self):
        g, p, e = scenario()
        self.refused(load(g, p, e, task_id='TASK-999'), 'git')

    def test_the_private_names_of_evaluation_exist(self):
        defined = {node.name for node in ast.parse((HERE.parents[2] / 'src' / 'aieos_bootstrap' / 'evaluation.py')
                                                   .read_bytes().decode('utf-8')).body
                   if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
        for name in ('_task_commits', '_changed_paths', '_Stop'):
            self.assertIn(name, defined)
            self.assertTrue(hasattr(evaluation, name), name)
        self.assertTrue(issubclass(evaluation._Stop, Exception))


class AC6TheRefusals(Base):
    def test_the_arguments(self):
        g, p, e = scenario()
        for key, bad in (('policy_ref', 'A' * 40), ('policy_ref', 'a' * 39), ('policy_ref', None), ('evaluated_commit', 'b' * 41),
                         ('evaluated_commit', 7), ('task_id', 'TASK-'), ('task_id', 'task-1'), ('task_id', None),
                         ('ci_logs', 'text'), ('ci_logs', (GOOD_LOG,)), ('ci_logs', [None]), ('read', 5),
                         ('max_commits', 0), ('max_commits', 10001), ('max_commits', True), ('max_commits', '3'),
                         ('max_commits', 1.0), ('repo', 'relative'), ('repo', ROOT + '/no/such/folder'), ('repo', None)):
            self.refused(load(g, p, e, **{key: bad}), 'argument')
        self.refused(load(g, p, p), 'argument')

    def test_the_argument_limits_are_taken(self):
        g, p, e = scenario()
        for n in (1, 10000):
            self.assertEqual(load(g, p, e, max_commits=n)['result'], 'present')

    def test_no_read_is_made_for_an_argument_refusal(self):
        g, p, e = scenario()
        self.refused(load(g, p, e, task_id='x'), 'argument')
        self.assertEqual(g.calls, [])

    def test_a_missing_file_a_failed_read_and_a_raising_read_are_one_reason(self):
        for path in (POLICY, RISK, GOVERNOR):
            files = dict(REAL)
            del files[path]
            self.refused(load(*scenario(files)), 'read')
        g, p, e = scenario()
        g.override[('cat-file', '-t', p)] = failed(1)
        self.refused(load(g, p, e), 'read')
        g, p, e = scenario()
        g.override[('cat-file', '-t', p)] = OSError('x')
        self.refused(load(g, p, e), 'read')

    def test_a_file_that_is_not_utf8_is_refused_as_read(self):
        for path in (POLICY, RISK, GOVERNOR):
            files = dict(REAL)
            files[path] = b'\xff\xfe\x00'
            self.refused(load(*scenario(files)), 'read')

    def test_a_policy_that_is_refused_by_the_reader(self):
        files = dict(REAL, **{POLICY: 'no block here\n'})
        detail = self.refused(load(*scenario(files)), 'policy')
        self.assertTrue(detail.startswith('policy: '), detail)
        finding = evaluation_policy.read_evaluation_policy(files[POLICY])['findings'][0]
        self.assertEqual(detail, 'policy: %s line %s' % (finding['reason'], 'none' if finding['line'] is None else finding['line']))

    def test_the_policy_detail_is_exactly_reason_and_line_for_several_texts(self):
        numbered = 0
        text = REAL[POLICY]
        for broken in ('no block here\n', text + '\na line after the last key\n', text.replace('articles:', 'articles :', 1),
                       text.replace('\n', '\n\n', 3), text[:len(text) // 2],
                       text.replace('\narticles:', '\njunk line here\narticles:', 1),
                       text.replace('\ndelegation:', '\njunk line here\ndelegation:', 1),
                       text.replace('\nauto_accept:', '\njunk line here\nauto_accept:', 1)):
            parsed = evaluation_policy.read_evaluation_policy(broken)
            if parsed['result'] == 'present':
                continue
            finding = parsed['findings'][0]
            numbered += finding['line'] is not None
            detail = self.refused(load(*scenario(dict(REAL, **{POLICY: broken}))), 'policy')
            self.assertEqual(detail, 'policy: %s line %s' % (finding['reason'], 'none' if finding['line'] is None else finding['line']))
        self.assertGreaterEqual(numbered, 1)

    def test_the_policy_detail_says_line_none_when_the_finding_has_no_line(self):
        made = {'result': 'refused', 'sources': {}, 'findings': [{'reason': 'made', 'line': None, 'detail': 'd'}]}
        with mock.patch.object(evaluation_policy, 'read_evaluation_policy', return_value=made):
            detail = self.refused(load(), 'policy')
        self.assertEqual(detail, 'policy: made line none')
        made = {'result': 'refused', 'sources': {}, 'findings': [{'reason': 'made', 'line': 7, 'detail': 'd'}]}
        with mock.patch.object(evaluation_policy, 'read_evaluation_policy', return_value=made):
            self.assertEqual(self.refused(load(), 'policy'), 'policy: made line 7')

    def test_the_read_detail_is_the_first_finding_of_base_files_unchanged(self):
        for path in (POLICY, RISK, GOVERNOR):
            files = dict(REAL)
            del files[path]
            g, p, e = scenario(files)
            expected = base_files.read_file(ROOT, p, path, g)[1][0]
            self.assertTrue(expected.endswith(' is missing'), expected)
            self.assertEqual(self.refused(load(g, p, e), 'read'), expected)

    def test_the_risk_file_out_of_form(self):
        text = REAL[RISK]
        block = scope_reconcile.policy_block(text)
        version = [line for line in block if line.startswith('policy_version: ')][0]
        for name, files in (
                ('no block', dict(REAL, **{RISK: 'nothing\n'})),
                ('no version', dict(REAL, **{RISK: text.replace(version, '')})),
                ('two versions', dict(REAL, **{RISK: text.replace(version, version + '\n' + version)})),
        ):
            self.refused(load(*scenario(files)), 'rules')

    def test_a_rule_out_of_form_and_an_empty_list_refuse_the_whole_read(self):
        text = REAL[RISK]
        block = scope_reconcile.policy_block(text)
        entry = [line for line in block if line.startswith('    risk: ')][0]
        bad = text.replace(entry, '    risk: unknown', 1)
        self.refused(load(*scenario(dict(REAL, **{RISK: bad}))), 'rules')
        marker = [line for line in block if line.startswith('risk_rules:')][0]
        empty = text[:text.index(marker)] + marker + '\n'
        rest = text[text.index(marker) + len(marker):]
        stop = rest.find('\n```')
        empty += rest[stop + 1:] if stop >= 0 else ''
        self.refused(load(*scenario(dict(REAL, **{RISK: empty}))), 'rules')

    def test_the_order_of_the_checks(self):
        files = dict(REAL, **{POLICY: 'no block here\n'})
        g, p, e = scenario(files)
        a = load(g, p, e, ci_logs=[log_of(pin_line('2' * 64))])
        self.assertEqual(reason_of(a), 'policy')
        a = load(*scenario(dict(REAL, **{RISK: 'nothing\n'})), ci_logs=[log_of('checks\tRun\t' + STAMP + ' none')])
        self.assertEqual(reason_of(a), 'rules')
        a = load(ci_logs=[log_of('checks\tRun\t' + STAMP + ' none')])
        self.assertEqual(reason_of(a), 'pin')
        g, p, e = scenario()
        self.assertEqual(reason_of(load(g, p, e, task_id='TASK-999', ci_logs=[log_of(pin_line('2' * 64))])), 'governor')
        self.assertEqual(reason_of(load(g, p, e, task_id='TASK-999')), 'git')

    def test_a_missing_file_is_found_before_a_later_fault(self):
        files = dict(REAL)
        del files[RISK]
        a = load(*scenario(files), ci_logs=[''])
        self.assertEqual(reason_of(a), 'read')
        g, p, e = scenario()
        self.assertEqual(reason_of(load(g, p, e, max_commits=0)), 'argument')

    def test_a_keyboard_interrupt_passes_and_a_read_that_gives_nothing_is_refused_as_read(self):
        class Bad:
            def __call__(self, repo, args, timeout=30):
                raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            ES.load_sources(ROOT, 'a' * 40, 'b' * 40, TASK, [GOOD_LOG], read=Bad())
        calls = []

        def odd(repo, args, timeout=30):
            calls.append(1)
            return None
        a = ES.load_sources(ROOT, 'a' * 40, 'b' * 40, TASK, [GOOD_LOG], read=odd)
        self.refused(a, 'read')

    def test_the_refusal_is_never_partial(self):
        a = load(ci_logs=[log_of(pin_line('1' * 64))])
        self.assertEqual(set(a), {'result', 'sources', 'changed_paths', 'provenance', 'findings'})
        self.assertIsNone(a['sources'])
        self.assertEqual(a['provenance'], [])

    def test_the_reasons_are_the_closed_set(self):
        allowed = {'argument', 'read', 'policy', 'rules', 'pin', 'governor', 'git', 'plain'}
        g, p, e = scenario()
        seen = set()
        for kw in ({'task_id': 'x'}, {'ci_logs': [log_of(pin_line('1' * 64))]}, {'ci_logs': ['']}, {'max_commits': 1}):
            r = load(g, p, e, **kw)
            if r['result'] == 'refused':
                seen.add(reason_of(r))
        self.assertLessEqual(seen, allowed)
        self.assertEqual(ES.pinned_governor([])['findings'][0]['reason'], 'pin')

    def test_the_detail_is_cut(self):
        g, p, e = scenario()
        long = ('abcdefghij' * 50)
        made = {'value': None, 'findings': [{'reason': 'pin', 'detail': long}]}
        with mock.patch.object(evaluation_derive, 'ruleset_version', return_value=made) as stand_in:
            d = self.refused(load(g, p, e), 'governor')
        self.assertEqual(stand_in.call_count, 1)
        self.assertEqual(len(long), 500)
        self.assertEqual(len(d), 200)
        self.assertEqual(d, long[:200])

    def test_the_helper_refusals_have_a_cut_detail(self):
        r = ES._Refuse('git', 'x' * 500)
        self.assertEqual(len(r.detail), 200)
        self.assertFalse(isinstance(r, ValueError))
        self.assertFalse(isinstance(ES._Reject('json'), ValueError))


class AC6TheGenericPathAndTheRows(Base):
    GOOD = {'match': ['src/**'], 'class': 'low'}

    def test_a_helper_replaced_by_one_that_raises_gives_the_generic_detail_exactly(self):
        for name, error in (('_risk_sources', LookupError), ('_walk', ZeroDivisionError), ('_read', KeyError)):
            with mock.patch.object(ES, name, side_effect=error('a text that must not be in the detail')):
                a = load()
            self.assertEqual(self.refused(a, 'argument'), 'an unexpected error: ' + error.__name__)
        self.assertEqual(load()['result'], 'present')

    def test_a_replaced_helper_is_undone_at_the_end(self):
        original = ES._risk_sources
        with mock.patch.object(ES, '_risk_sources', side_effect=LookupError):
            self.assertIsNot(ES._risk_sources, original)
        self.assertIs(ES._risk_sources, original)

    def test_a_keyboard_interrupt_from_a_read_passes_through(self):
        def stop(repo, args, timeout=None):
            raise KeyboardInterrupt
        g, p, e = scenario()
        with self.assertRaises(KeyboardInterrupt):
            ES.load_sources(ROOT, p, e, TASK, [GOOD_LOG], read=stop)

    def test_no_input_is_changed(self):
        g, p, e = scenario(parents=2)
        logs = [GOOD_LOG, log_of(pin_line())]
        logs_before = list(logs)
        objects_before = dict(g.objects)
        diffs_before = dict(g.diffs)
        a = load(g, p, e, ci_logs=logs)
        self.assertEqual(a['result'], 'present')
        self.assertEqual(logs, logs_before)
        self.assertEqual(g.objects, objects_before)
        self.assertEqual(g.diffs, diffs_before)
        before = json.dumps(a, sort_keys=True)
        load(g, p, e, ci_logs=logs)
        self.assertEqual(json.dumps(a, sort_keys=True), before)

    def test_two_faults_the_first_in_the_order_wins(self):
        broken = dict(REAL, **{POLICY: 'no block here\n'})
        files = dict(broken)
        del files[GOVERNOR]
        self.assertEqual(reason_of(load(*scenario(files))), 'read')
        files = dict(broken)
        del files[RISK]
        self.assertEqual(reason_of(load(*scenario(files))), 'read')
        g, p, e = scenario()
        self.assertEqual(reason_of(load(g, p, e, task_id='TASK-999', ci_logs=[''])), 'pin')
        self.assertEqual(reason_of(load(g, p, e, task_id='TASK-999', ci_logs=[log_of(pin_line(PIN[:60]))])), 'pin')
        self.assertEqual(reason_of(load(g, p, e, task_id='TASK-999', ci_logs=[log_of(pin_line('4' * 64))])), 'governor')

    def refused_rule_row(self, rules, index):
        with mock.patch.object(scope_reconcile, 'rules_from_policy', return_value=rules):
            a = load()
        self.assertEqual(self.refused(a, 'rules'), 'risk rule %d is refused' % index)

    def test_one_row_per_condition_of_a_rule_out_of_form(self):
        good = self.GOOD
        for rule in ({'match': ['a'], 'class': 'low', 'extra': 1}, {'match': ['a']}, {'class': 'low'},
                     {'match': ['a'], 'class': 'urgent'}, {'match': ['a'], 'class': None}, {'match': 'a', 'class': 'low'},
                     {'match': ('a',), 'class': 'low'}, {'match': [], 'class': 'low'}, {'match': [1], 'class': 'low'},
                     {'match': ['a', None], 'class': 'low'}, ['a'], None, 'x', scope_reconcile.REFUSED_RULE):
            self.refused_rule_row([rule], 1)
            self.refused_rule_row([good, rule], 2)

    def test_a_rule_list_that_is_empty_or_not_a_list_is_refused_as_rules(self):
        for rules in ([], None, ()):
            with mock.patch.object(scope_reconcile, 'rules_from_policy', return_value=rules):
                self.refused(load(), 'rules')

    def test_good_rules_are_passed_on_as_given_by_the_producer(self):
        with mock.patch.object(scope_reconcile, 'rules_from_policy', return_value=[self.GOOD, {'match': ['a', 'b'], 'class': 'high'}]):
            a = load()
        self.assertEqual(a['sources']['risk_rules'], [self.GOOD, {'match': ['a', 'b'], 'class': 'high'}])

    def test_the_details_of_the_findings_are_passed_on_unchanged(self):
        bad = hashlib.sha256(b'x').hexdigest()
        a = load(ci_logs=[log_of(pin_line(bad))])
        expected = evaluation_derive.ruleset_version(REAL[GOVERNOR].encode('utf-8'), bad)['findings'][0]['detail']
        self.assertEqual(self.refused(a, 'governor'), expected)
        with mock.patch.object(evaluation_derive, 'plain_data_problem', return_value={'reason': 'type', 'detail': 'a made-up detail'}):
            a = load()
        self.assertEqual(self.refused(a, 'plain'), 'a made-up detail')

    def test_the_helpers_of_evaluation_with_the_same_stand_in_give_the_same_list(self):
        g, p, e = scenario(parents=3)
        commits = evaluation._task_commits(g, ROOT, TASK, e, 1000)
        self.assertEqual(len(commits), 3)
        self.assertEqual(evaluation._changed_paths(g, ROOT, commits), load(g, p, e)['changed_paths'])


class AC6F1NoSharedContainer(Base):
    def test_no_container_of_the_answer_occurs_twice_by_identity(self):
        a = load()
        seen = {}
        stack = [a]
        while stack:
            item = stack.pop()
            if type(item) in (dict, list):
                self.assertNotIn(id(item), seen)
                seen[id(item)] = item
                stack.extend(item.values() if type(item) is dict else item)

    def test_two_calls_share_no_container(self):
        g, p, e = scenario()
        a, b = load(g, p, e), load(g, p, e)
        self.assertEqual(a, b)
        self.assertIsNot(a['sources']['risk_rules'], b['sources']['risk_rules'])
        self.assertIsNot(a['sources']['articles'], b['sources']['articles'])
        self.assertIsNot(a['changed_paths'], b['changed_paths'])

    def test_the_answer_is_plain_data(self):
        self.assertIsNone(evaluation_derive.plain_data_problem(load()))
        self.assertEqual(json.loads(json.dumps(load())), load())


class AC7TheModule(unittest.TestCase):
    def tree(self):
        return ast.parse(SRC.read_bytes().decode('utf-8'))

    def test_the_imports_are_a_subset(self):
        names = set()
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(node.module, 'aieos_bootstrap')
                names.update(a.name for a in node.names)
        self.assertLessEqual(names, {'hashlib', 'json', 're', 'base_files', 'evaluation', 'evaluation_derive',
                                     'evaluation_policy', 'gitread', 'scope_reconcile'})

    def test_no_name_of_a_process_a_file_or_a_dynamic_call(self):
        banned = {'open', 'eval', 'exec', 'compile', 'input', 'breakpoint', '__builtins__', '__import__'}
        modules = {'tempfile', 'shutil', 'subprocess', 'importlib', 'pickle', 'code', 'builtins', 'os', 'sys', 'time',
                   'datetime', 'socket', 'pathlib'}
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.Name):
                self.assertNotIn(node.id, banned)
                self.assertNotIn(node.id, modules)
            if isinstance(node, ast.Attribute):
                self.assertNotEqual(node.attr, 'open')
                self.assertNotIn(node.attr, ('write', 'write_text', 'write_bytes', 'unlink', 'mkdir'))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'replace':
                self.assertGreater(len(node.args), 1)

    def test_no_string_holds_a_dot_before_the_name_of_the_project(self):
        needle = '.' + 'aieos'
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertNotIn(needle, node.value.lower())

    def test_no_string_names_a_measure_folder_or_a_fixture_set(self):
        text = SRC.read_bytes().decode('utf-8')
        for word in ('native' + '/', 'bench' + '/', 'fixtures' + '_rc'):
            self.assertNotIn(word, text)

    def test_the_words_of_the_rules_on_words_are_not_in_the_module(self):
        text = SRC.read_bytes().decode('utf-8')
        for word in ('MEAS' + 'URED', 'ENFOR' + 'CED', 'GUARAN' + 'TEED', 'va' + 'lid', 'acc' + 'epted', 'appr' + 'oved'):
            self.assertNotIn(word, text)

    def test_the_module_has_no_function_that_is_not_listed(self):
        public = sorted(n for n in dir(ES) if not n.startswith('_') and callable(getattr(ES, n))
                        and getattr(getattr(ES, n), '__module__', '') == ES.__name__)
        self.assertEqual(public, ['load_sources', 'parse_json', 'pinned_governor'])

    def test_the_signature_of_load_sources(self):
        code = ES.load_sources.__code__
        self.assertEqual(code.co_varnames[:code.co_argcount],
                         ('repo', 'policy_ref', 'evaluated_commit', 'task_id', 'ci_logs', 'read', 'max_commits'))
        self.assertEqual(ES.load_sources.__defaults__, (None, 1000))

    def test_a_mutation_of_the_standin_changes_the_answer(self):
        g, p, e = scenario()
        before = load(g, p, e)
        g.diffs[e] = b'docs/specs/other.md\x00'
        after = load(g, p, e)
        self.assertNotEqual(before['changed_paths'], after['changed_paths'])


if __name__ == '__main__':
    unittest.main()
