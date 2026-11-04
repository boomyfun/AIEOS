"""The runtime's declaration, read at the base (task TASK-117; specification 2 section 7.1 and section 10 point 12;
specification 5 section 11 point 14): the core reads the ``adapters`` list of the policy file at a base commit, in a
fixed form, and gives the Resume Check's runtime tier for one adapter id.

``declared_max_risk(text, adapter)`` PARSES a policy text and returns a mapping with exactly result, max_risk and
findings: result "none" (max_risk None; the text has no adapters block, an empty one, or no item for the adapter), "low"
(max_risk "low"; the adapter has an item in a well-formed block) or "error" (max_risk None; a malformed block, a
repeated adapter id, a text that is not a str or an adapter argument out of form: no decision). No measurement
resolves through the core because point 12 is open (R-b of D-4737): a ``measurement`` key is read as unresolved, so
every declaration is read at its weakest, max_risk "low", whatever tier, assurance or max_risk the item states.

``read_declaration(repo, base, adapter, run=None)`` composes the base read of claude_code_shell_allow.read_policy_text
with that parse and returns a mapping with exactly result, max_risk and findings: "absent" (max_risk None; there is no
declaration for the adapter: no policy file at the base, no adapters block, or no item for the adapter; the existing
path to check 7), "refused" (the base read was refused; max_risk None; its findings are passed through), "error" (as
declared_max_risk) or "low". The adapter argument is checked first, before any read. It is the default of the
launcher's seam read_declaration. This module opens no file and starts no process except through
claude_code_shell_allow.read_policy_text (which runs git through gitread.run); declared_max_risk starts none.

The grammar of the adapters block, quoted as ADAPTERS_GRAMMAR:
GRAMMAR BEGIN
(g1) the text is split on LF; a line is SKIPPED when it is blank (its strip is empty) or its lstrip starts with #;
(g2) the block is the lines after the one top-level line whose whole text is exactly ``adapters:`` up to the next
top-level line (a line that starts with a non-space); top-level lines of any other key are ignored; no ``adapters:``
line gives none; a block with no item lines gives none; a second ``adapters:`` line, or a top-level line that begins
with ``adapters:`` and is not exactly that, gives error;
(g3) inside the block each non-skipped line is either an ITEM line, exactly two spaces, ``- ``, then ``adapter: <id>``,
or a KEY line, exactly four spaces, then the key (the text before the FIRST ``: ``), ``: `` and the value (the rest of
the line); a KEY line that comes before the first ITEM line of the block gives error; any other shape gives error;
(g4) each item has exactly these keys, in exactly this order: adapter, tier, configuration, capabilities, assurance,
max_risk, and then optionally measurement; a missing, repeated, unknown or misordered key gives error;
(g5) values are bare scalars with no quotes: adapter is a lowercase ASCII word or several joined by single hyphens;
tier is one of T0 T1 T2 T3 T4; max_risk is one of low medium high critical (any other value gives error); measurement
is any non-empty rest of the line and is read as UNRESOLVED (no measurement resolves through the core);
(g6) configuration is the flow map ``{runtime: S, platform: S, version: S, settings: S}``, written with ``{``, the four
pairs separated by ``, ``, ``: `` between key and value, and ``}``, no other space, exactly those four keys in that
order, S a non-empty string of [A-Za-z0-9._:/+-];
(g7) capabilities is ``{}`` or a flow map in the same separators ``{name: true, name: false}`` with names
[a-z][a-z0-9_]* each once;
(g8) assurance is the flow map ``{preventive: X, runtime: X, posthoc: X}`` in the same separators and that order with
X one of none weak strong;
(g9) an adapter id that occurs in two items gives error for the whole block;
(g10) a CR, a tab or any character outside printable ASCII and LF in the block lines gives error (the bytes outside
the block are checked on the read path, by claude_code_shell_allow.read_policy_text, not by the grammar).
GRAMMAR END
A well-formed block gives low for an adapter that has an item and none for any other id, whatever tier and assurance
the item states within the sets above, and even when its max_risk is critical or it has a measurement key; the result
is never above low.
"""

import re

from aieos_bootstrap import claude_code_shell_allow

# A literal, not derived from __doc__ (python -OO drops docstrings); the tests compare it with the docstring's own text.
ADAPTERS_GRAMMAR = """(g1) the text is split on LF; a line is SKIPPED when it is blank (its strip is empty) or its lstrip starts with #;
(g2) the block is the lines after the one top-level line whose whole text is exactly ``adapters:`` up to the next
top-level line (a line that starts with a non-space); top-level lines of any other key are ignored; no ``adapters:``
line gives none; a block with no item lines gives none; a second ``adapters:`` line, or a top-level line that begins
with ``adapters:`` and is not exactly that, gives error;
(g3) inside the block each non-skipped line is either an ITEM line, exactly two spaces, ``- ``, then ``adapter: <id>``,
or a KEY line, exactly four spaces, then the key (the text before the FIRST ``: ``), ``: `` and the value (the rest of
the line); a KEY line that comes before the first ITEM line of the block gives error; any other shape gives error;
(g4) each item has exactly these keys, in exactly this order: adapter, tier, configuration, capabilities, assurance,
max_risk, and then optionally measurement; a missing, repeated, unknown or misordered key gives error;
(g5) values are bare scalars with no quotes: adapter is a lowercase ASCII word or several joined by single hyphens;
tier is one of T0 T1 T2 T3 T4; max_risk is one of low medium high critical (any other value gives error); measurement
is any non-empty rest of the line and is read as UNRESOLVED (no measurement resolves through the core);
(g6) configuration is the flow map ``{runtime: S, platform: S, version: S, settings: S}``, written with ``{``, the four
pairs separated by ``, ``, ``: `` between key and value, and ``}``, no other space, exactly those four keys in that
order, S a non-empty string of [A-Za-z0-9._:/+-];
(g7) capabilities is ``{}`` or a flow map in the same separators ``{name: true, name: false}`` with names
[a-z][a-z0-9_]* each once;
(g8) assurance is the flow map ``{preventive: X, runtime: X, posthoc: X}`` in the same separators and that order with
X one of none weak strong;
(g9) an adapter id that occurs in two items gives error for the whole block;
(g10) a CR, a tab or any character outside printable ASCII and LF in the block lines gives error (the bytes outside
the block are checked on the read path, by claude_code_shell_allow.read_policy_text, not by the grammar)."""

_ADAPTER = re.compile('[a-z0-9]+(?:-[a-z0-9]+)*')
_ITEM = re.compile('  - adapter: (.*)')
_KEY = re.compile(' {4}(?! )(.*)')
_KEYS = ('adapter', 'tier', 'configuration', 'capabilities', 'assurance', 'max_risk')
_TIERS = ('T0', 'T1', 'T2', 'T3', 'T4')
_RISKS = ('low', 'medium', 'high', 'critical')
_S = '[A-Za-z0-9._:/+-]+'
_CONFIGURATION = re.compile('\\{runtime: %s, platform: %s, version: %s, settings: %s\\}' % (_S, _S, _S, _S))
_ASSURANCE = re.compile('\\{preventive: (?:none|weak|strong), runtime: (?:none|weak|strong), '
                        'posthoc: (?:none|weak|strong)\\}')
_CAPABILITY = re.compile('([a-z][a-z0-9_]*): (?:true|false)')
_PRINTABLE = re.compile('[ -~]*')


class _Bad(Exception):
    def __init__(self, finding):
        Exception.__init__(self, finding)
        self.finding = finding


def _result(result, max_risk, findings):
    return {'result': result, 'max_risk': max_risk, 'findings': list(findings)}


def _skipped(raw):
    return not raw.strip() or raw.lstrip().startswith('#')


def _adapter_ok(value):
    return type(value) is str and _ADAPTER.fullmatch(value) is not None


def _capabilities_ok(value):
    if value == '{}':
        return True
    if not (value.startswith('{') and value.endswith('}')):
        return False
    names = []
    for pair in value[1:-1].split(', '):
        m = _CAPABILITY.fullmatch(pair)
        if m is None:
            return False
        names.append(m.group(1))
    return len(set(names)) == len(names)


def _value_ok(key, value):
    if key == 'adapter':
        return _adapter_ok(value)
    if key == 'tier':
        return value in _TIERS
    if key == 'configuration':
        return _CONFIGURATION.fullmatch(value) is not None
    if key == 'capabilities':
        return _capabilities_ok(value)
    if key == 'assurance':
        return _ASSURANCE.fullmatch(value) is not None
    if key == 'max_risk':
        return value in _RISKS
    return value != ''


# g2's "a line that starts with a non-space" is read as: a line whose first character is not whitespace (str.isspace()
# is false for it); so a line led by a tab, U+00A0 or another whitespace character belongs to the block, where g10
# checks its characters (D-4767 C2, D-4768).
def _block(text):
    """The raw lines of the adapters block, or None when the text has no adapters line (g1, g2); _Bad for a repeated or
    inexact adapters line."""
    lines = text.split('\n')
    start = None
    for i, raw in enumerate(lines):
        if _skipped(raw) or raw[:1].isspace():
            continue
        if raw.startswith('adapters:'):
            if raw != 'adapters:':
                raise _Bad('adapters: a top-level line begins with adapters: and is not exactly that')
            if start is not None:
                raise _Bad('adapters: a second adapters: line')
            start = i
    if start is None:
        return None
    block = []
    for raw in lines[start + 1:]:
        if not _skipped(raw) and not raw[:1].isspace():
            break
        block.append(raw)
    return block


def _items(block):
    """The items of a block as lists of (key, value) pairs (g3, g4, g5, g9, g10), or _Bad."""
    for raw in block:
        if _PRINTABLE.fullmatch(raw) is None:
            raise _Bad('adapters: a character outside printable ASCII, or a CR or a tab, in the block')
    items = []
    for raw in block:
        if _skipped(raw):
            continue
        m = _ITEM.fullmatch(raw)
        if m is not None:
            items.append([('adapter', m.group(1))])
            continue
        k = _KEY.fullmatch(raw)
        if k is None or not items:
            raise _Bad('adapters: a line out of the item and key forms, or a key line before the first item')
        key, sep, value = k.group(1).partition(': ')
        if not sep:
            raise _Bad('adapters: a key line with no ": "')
        items[-1].append((key, value))
    for item in items:
        keys = [k for k, _ in item]
        if keys != list(_KEYS) and keys != list(_KEYS) + ['measurement']:
            raise _Bad('adapters: the keys of an item are not adapter, tier, configuration, capabilities, assurance, '
                       'max_risk and optionally measurement, in that order')
        for key, value in item:
            if not _value_ok(key, value):
                raise _Bad('adapters: the value of %s is out of form' % key)
    ids = [item[0][1] for item in items]
    if len(set(ids)) != len(ids):
        raise _Bad('adapters: an adapter id occurs in two items')
    return items


def declared_max_risk(text, adapter):
    """The runtime tier a policy text declares for an adapter (TASK-117 AC2): a mapping with exactly result, max_risk and
    findings; see the module docstring. Never raises an Exception."""
    try:
        if not _adapter_ok(adapter):
            return _result('error', None, ['argument: adapter is not a lowercase word or words joined by hyphens'])
        if type(text) is not str:
            return _result('error', None, ['argument: text is not a str'])
        block = _block(text)
        if block is None:
            return _result('none', None, [])
        items = _items(block)
        if any(item[0][1] == adapter for item in items):
            return _result('low', 'low', [])
        return _result('none', None, [])
    except _Bad as bad:
        return _result('error', None, [bad.finding])
    except Exception as exc:
        return _result('error', None, ['entry: ' + type(exc).__name__])


def read_declaration(repo, base, adapter, run=None):
    """The Resume Check's runtime.max_risk for an adapter, from the policy file at the base commit (TASK-117 AC2): a
    mapping with exactly result, max_risk and findings; see the module docstring. Never raises an Exception."""
    try:
        if not _adapter_ok(adapter):
            return _result('error', None, ['argument: adapter is not a lowercase word or words joined by hyphens'])
        got = claude_code_shell_allow.read_policy_text(repo, base, run)
        if type(got) is not dict or got.get('result') not in ('present', 'absent', 'refused'):
            return _result('error', None, ['declaration: the base read gave an answer out of form'])
        if got['result'] == 'refused':
            given = got.get('findings')
            return _result('refused', None, [f for f in given if isinstance(f, str)] if isinstance(given, list) else [])
        if got['result'] == 'absent':
            return _result('absent', None, [])
        parsed = declared_max_risk(got.get('text'), adapter)
        if parsed['result'] == 'none':
            return _result('absent', None, [])
        return parsed
    except Exception as exc:
        return _result('error', None, ['entry: ' + type(exc).__name__])
