"""The rest of the Resume Check's inputs, read at a given commit and from the log (task TASK-088; specification 3
revision 5, sections 1 and 2; conformance-files.md section 9; DEF-0097; DEF-0100).

``log_inputs(repo, commit, task_id, log, read=None)`` returns (inputs, None), inputs being exactly seven of the 22
inputs of resume_check.INPUT_KEYS in section 9's forms: dependencies, observed_read_set, budget_use, intent_current,
articles, risk_rules and policy_version; or (None, findings), a non-empty list of strs, and no partial value. With
TASK-085's ten (resume_inputs.git_inputs) the 22 are covered once TASK-086 adds task_id and runtime and derives
log_seq, task_state and approved_contract_hash from the log; the call that joins them is TASK-086's.

As in resume_inputs, the commit is an argument: nothing here reads HEAD. read is injectable: gitread.run is the
default, taken at call time, and within one call the read in use is wrapped by one memo keyed by its arguments and
passed to every base_files and base_inputs call. The log is a value, given as bytes and read through
execution.task_states and execution.rework_count. The module never raises: every failure, a RecursionError or
MemoryError among them, is given as findings. It writes nothing, opens no file, reads no clock and no environment,
and starts no process but through read. Each reader fails closed.

The readers, each this task's choice where TASK-088's contract says so:
- The contract: base_inputs.contract_at at the commit; a contract whose input_state.depends_on is not a list of strs,
  whose input_state.intent_versions is not a mapping or whose autonomy.budgets is not a mapping fails closed.
- dependencies: execution.task_states over the contract's depends_on: {state, stale_evidence} for each, state null
  when the log holds no task.approved of the task (the Resume Check's check 5 then gives BLOCKED), stale_evidence
  true when an evidence.stale of the task follows its last task.done (a reading; one with no task_id is not counted).
- observed_read_set is null, by rule: no runtime's tier is measured (read_set_record.py; C6, P-LOC).
- budget_use: for each budget of autonomy.budgets, retries {used: execution.rework_count, reported: true}, every
  other {used: 0, reported: false}, since no source reads a runtime's reports.
- intent_current: for each entity of input_state.intent_versions, read as a repository path at the commit, the
  SHA-256 hex of the file's bytes (base_files.read_file's text encoded as UTF-8), or null when the path is not in its
  folder's listing (base_inputs.paths_under); an entity that is not a path in base_files' name form fails closed.
- articles: the constitution at the commit, one entry per heading "### <ID> · " in file order, {id, scope,
  applicability, violated: null}; scope the article's "Scope: " prose as a str, to the first ". " or the line's end
  ("" when there is none), which the Resume Check reads as a scope that cannot be evaluated, so every article whose
  applicability is null or names the contract's task_type counts as applicable (a stated departure from section 9's
  {paths, components} form); applicability {task_types: [...]} when the "Applicability: " prose is a list of
  lowercase words joined by ", ", else null. A constitution with no such heading, or an id twice, fails closed.
- risk_rules: scope_reconcile.rules_from_policy at the commit, each {match, class} given as {match: {paths: match},
  risk: class}; a component_tags rule thus comes as its TAGS_MATCH paths (src/** and tests/**), the risk rules' point
  3 reading; a refused rule (class null) fails closed.
- policy_version: the value of the one "policy_version: <v>" line of scope_reconcile.policy_block's lines, or fail
  closed.

Limits, stated (DEF-0100 carries those for specification 3's next revision): seven of the 22 inputs; observed_read_set
is null; three budgets unreported and the retries limit a str the Resume Check's check 8 does not parse, so check 8
is inert for every budget of the self-build; stale_evidence a reading; every article's scope its prose and violated
null; component_tags rules read as point 3's paths until the architecture names components; intent_current as file
hashes, a non-UTF-8 or over-size file failing the call; the repository read at one moment; a symbolic link, a
submodule or an out-of-form name under a listed folder fails the call (base_files' rules), and an intent entity at
the repository root lists the whole tree, so one such entry anywhere fails it.
"""

import hashlib
import re

from aieos_bootstrap import base_files, base_inputs, execution, gitread, resume_check, scope_reconcile

TIMEOUT = 30
KEYS = ('dependencies', 'observed_read_set', 'budget_use', 'intent_current', 'articles', 'risk_rules',
        'policy_version')

_COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
_TASK = re.compile(r'TASK-[0-9]+')
_HEADING = re.compile(r'### ([A-Z]+-[0-9]+) · ')
_WORDS = re.compile(r'[a-z][a-z_-]*(?:, [a-z][a-z_-]*)*')
_VERSION = re.compile(r'policy_version: (\S+)')


class _Stop(Exception):
    """A refusal: its findings."""

    def __init__(self, findings):
        Exception.__init__(self, findings[0])
        self.findings = list(findings)


def _memo(read):
    """read wrapped by a memo keyed by its arguments."""
    seen = {}

    def run(repo, args, timeout=TIMEOUT):
        key = (repo, tuple(args), timeout)
        if key not in seen:
            seen[key] = read(repo, args, timeout)
        return seen[key]
    return run


def _value(result, what):
    value, found = result
    if found is not None:
        raise _Stop(['%s: %s' % (what, f) for f in found])
    return value


def _check(repo, commit, task_id, log, read):
    found = []
    if type(repo) is not str:
        found.append('argument: repo is not a str')
    if type(commit) is not str or _COMMIT.fullmatch(commit) is None:
        found.append('argument: commit is not 40 or 64 lowercase hexadecimal characters')
    if type(task_id) is not str or _TASK.fullmatch(task_id) is None:
        found.append('argument: task_id is not TASK-<digits>')
    if type(log) is not bytes:
        found.append('argument: log is not bytes')
    if read is not None and not callable(read):
        found.append('argument: read is not callable')
    if found:
        raise _Stop(found)


def _needs(contract):
    """The contract's depends_on, intent_versions and budgets, or a refusal."""
    s = contract.get('input_state')
    a = contract.get('autonomy')
    deps = s.get('depends_on') if isinstance(s, dict) else None
    iv = s.get('intent_versions') if isinstance(s, dict) else None
    budgets = a.get('budgets') if isinstance(a, dict) else None
    found = []
    if not (isinstance(deps, list) and all(type(d) is str for d in deps)):
        found.append('contract: input_state.depends_on is not a list of strs')
    if not isinstance(iv, dict):
        found.append('contract: input_state.intent_versions is not a mapping')
    if not isinstance(budgets, dict):
        found.append('contract: autonomy.budgets is not a mapping')
    if found:
        raise _Stop(found)
    return deps, iv, budgets


def _budget_use(log, task_id, budgets):
    out = {}
    for name in budgets:
        if name == 'retries':
            out[name] = {'used': _value(execution.rework_count(log, task_id), 'log'), 'reported': True}
        else:
            out[name] = {'used': 0, 'reported': False}
    return out


def _path_form(path):
    names = path.split('/') if type(path) is str else []
    return (0 < len(path) <= base_files.MAX_PATH if names else False) and all(
        base_files._NAME.fullmatch(n) is not None and n not in ('.', '..') for n in names)


def _intent_current(repo, commit, read, entities):
    out = {}
    for path in entities:
        if not _path_form(path):
            raise _Stop(['intent_versions: the entity %r is not a path in base_files\' form' % (path,)])
        folder = path.rsplit('/', 1)[0] if '/' in path else ''
        listing = _value(base_inputs.paths_under(repo, commit, folder, read), 'listing of %r' % folder)
        if path not in listing:
            out[path] = None
            continue
        text = _value(base_files.read_file(repo, commit, path, read), path)['text']
        out[path] = hashlib.sha256(text.encode('utf-8')).hexdigest()
    return out


def _prose(lines, label):
    """The text after the first "<label>: " in lines, to the first ". " or the line's end, or None."""
    for line in lines:
        k = line.find(label + ': ')
        if k >= 0:
            rest = line[k + len(label) + 2:]
            end = rest.find('. ')
            text = rest if end < 0 else rest[:end]
            return text[:-1] if end < 0 and text.endswith('.') else text
    return None


def _articles(text):
    lines = text.split('\n')
    starts = [(k, m.group(1)) for k, m in ((k, _HEADING.match(x)) for k, x in enumerate(lines)) if m is not None]
    if not starts:
        raise _Stop(['constitution: no heading "### <ID> · "'])
    ids = [i for _, i in starts]
    twice = sorted(set(i for i in ids if ids.count(i) > 1))
    if twice:
        raise _Stop(['constitution: the id %s is there twice' % i for i in twice])
    out = []
    for n, (k, article) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        body = []
        for line in lines[k + 1:end]:
            if line.startswith('#'):
                break
            body.append(line)
        scope = _prose(body, 'Scope')
        words = _prose(body, 'Applicability')
        applicability = ({'task_types': words.split(', ')} if words is not None and _WORDS.fullmatch(words)
                         else None)
        out.append({'id': article, 'scope': '' if scope is None else scope, 'applicability': applicability,
                    'violated': None})
    return out


def _risk_rules(text):
    out = []
    for n, rule in enumerate(scope_reconcile.rules_from_policy(text)):
        if rule.get('class') is None or not isinstance(rule.get('match'), list):
            raise _Stop(['risk rules: rule %d is refused by rules_from_policy' % (n + 1)])
        out.append({'match': {'paths': list(rule['match'])}, 'risk': rule['class']})
    return out


def _policy_version(text):
    block = scope_reconcile.policy_block(text)
    if block is None:
        raise _Stop(['risk rules: no section 3 yaml block'])
    found = [m.group(1) for m in (_VERSION.fullmatch(x) for x in block) if m is not None]
    if len(found) != 1:
        raise _Stop(['risk rules: %d policy_version lines in the block, not one' % len(found)])
    return found[0]


def _log_inputs(repo, commit, task_id, log, read):
    _check(repo, commit, task_id, log, read)
    run = _memo(gitread.run if read is None else read)
    contract, _ = _value(base_inputs.contract_at(repo, commit, task_id, run), 'contract')
    deps, iv, budgets = _needs(contract)
    policy = _value(base_files.read_file(repo, commit, scope_reconcile.POLICY_PATH, run),
                    scope_reconcile.POLICY_PATH)['text']
    constitution = _value(base_files.read_file(repo, commit, scope_reconcile.CONSTITUTION_PATH, run),
                          scope_reconcile.CONSTITUTION_PATH)['text']
    out = {'dependencies': _value(execution.task_states(log, deps), 'log'),
           'observed_read_set': None,
           'budget_use': _budget_use(log, task_id, budgets),
           'intent_current': _intent_current(repo, commit, run, list(iv)),
           'articles': _articles(constitution),
           'risk_rules': _risk_rules(policy),
           'policy_version': _policy_version(policy)}
    if not set(out) <= resume_check.INPUT_KEYS:
        raise _Stop(['log_inputs: a key resume_check.INPUT_KEYS does not name'])
    return out


def log_inputs(repo, commit, task_id, log, read=None):
    """Seven of the Resume Check's inputs read at commit and from the log: (inputs, None), or (None, findings)."""
    try:
        return _log_inputs(repo, commit, task_id, log, read), None
    except _Stop as s:
        return None, s.findings
    except Exception as e:
        return None, ['log_inputs: an unexpected %s' % type(e).__name__]
