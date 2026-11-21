"""The pure derivations of the evaluation sources (TASK-157, BT3b-2b; decisions D-7014 to D-7018).

Four functions and nothing else is public. None does any I/O: no file, no process, no clock, no network, no environment.
The module imports hashlib, math and evaluation_policy only, and none of them raises an Exception for any argument.

ruleset_version(governor_bytes, pinned_sha256) gives {value, findings}: value is the text "governor-sha256:" followed by
the sha256 hex of governor_bytes (the bytes of src/aieos_bootstrap/governor.py that the CALLER read at the pinned
policy_ref), or None with one finding when that hex differs from pinned_sha256 (the value of the CI's AIEOS_PINNED_GOVERNOR
printed by the same run; the caller takes both) or an argument has a wrong form.

level_version(policy_version) gives {value, findings}: value is the text "L1:" followed by policy_version, a non-empty
text that the caller took from the risk-rules file; L1 is the level in force for every class of the self-build.

evidence_comparison(changed_paths) gives the BARE mapping {weakens: bool}, never None (eval_inputs and the governor read
exactly that form: the governor sets weakens_evidence unless the value is exactly {weakens: False}). It answers
{weakens: True} when changed_paths is not a list of non-empty texts; when a path is malformed (a backslash, a leading
"./" or "/", a ".." or an interior "." segment, an empty segment, a trailing "/", a control character, whitespace at an end
of the path or of a segment, a colon, a trailing dot or space in a segment, a character that is not ASCII, or a tilde in a
segment); when a path equals, after str.casefold, an entry of evaluation_policy.EVIDENCE_DEFINING_PATHS (read by name at
each call); and when the FIRST segment of a path begins with a dot (the project-state, CI-channel and agent-settings
directories and the dot files of the root). It answers {weakens: False} otherwise, and for the empty list ("no path
changed"). This is a path-based over-approximation, not the reference comparison of the governor's specification:
{weakens: False} says only that no evidence-defining path and no dot-first path was changed, and it is sound only under the
standing condition that a task which writes, reads or derives requirement entities adds their path to
EVIDENCE_DEFINING_PATHS in the same change. A later narrowing of any rule here is a weakens-evidence change and needs its
own decision. This module is itself an entry of EVIDENCE_DEFINING_PATHS.

plain_data_problem(value) gives None for plain data, or one {reason, detail}. Plain data is dict (every key a text), list,
str, bool, None, int and finite float, nested; anything else is refused (the exact type is tested, so a subclass is
refused), and so is a nest of more than 50 levels of containers (the top container is level 1). detail has at most 40
characters.

Limits: nothing calls this module yet; the loader of the inputs (the git reads at the pinned ref) is BT3b-2c's. Caller obligations: changed_paths is a rename-free
listing of the changed files (a renamed evidence file must have its old path listed too) and is not C-quoted (a quoted spelling would pass as an ordinary path).
"""
import hashlib
import math

from aieos_bootstrap import evaluation_policy

_HEX = frozenset('0123456789abcdef')
_MAX_DEPTH = 50


def _finding(reason, detail):
    return {'reason': reason, 'detail': detail[:40]}


def _refused(reason, detail):
    return {'value': None, 'findings': [_finding(reason, detail)]}


def ruleset_version(governor_bytes, pinned_sha256):
    try:
        if type(governor_bytes) is not bytes:
            return _refused('argument', 'governor_bytes is not bytes')
        if type(pinned_sha256) is not str or len(pinned_sha256) != 64 or not set(pinned_sha256) <= _HEX:
            return _refused('argument', 'pinned_sha256 is not 64 lowercase hex')
        digest = hashlib.sha256(governor_bytes).hexdigest()
        if digest != pinned_sha256:
            return _refused('pin', 'the governor hash differs from the pin')
        return {'value': 'governor-sha256:' + digest, 'findings': []}
    except Exception:
        return _refused('error', 'an unexpected error')


def level_version(policy_version):
    try:
        if type(policy_version) is not str or policy_version == '':
            return _refused('argument', 'policy_version is not a non-empty text')
        return {'value': 'L1:' + policy_version, 'findings': []}
    except Exception:
        return _refused('error', 'an unexpected error')


def _malformed(path):
    if '\\' in path or ':' in path or path.startswith('/') or path.endswith('/'):
        return True
    for ch in path:
        code = ord(ch)
        if code < 32 or code == 127 or code > 127:
            return True
    for seg in path.split('/'):
        if seg in ('', '.', '..'):
            return True
        if seg[0].isspace() or seg[-1].isspace() or seg.endswith('.') or '~' in seg:
            return True
    return False


def evidence_comparison(changed_paths):
    try:
        if type(changed_paths) is not list:
            return {'weakens': True}
        listed = frozenset(entry.casefold() for entry in evaluation_policy.EVIDENCE_DEFINING_PATHS)
        for path in changed_paths:
            if type(path) is not str or path == '' or _malformed(path):
                return {'weakens': True}
            if path.casefold() in listed or path.split('/')[0].startswith('.'):
                return {'weakens': True}
        return {'weakens': False}
    except Exception:
        return {'weakens': True}


def plain_data_problem(value):
    try:
        stack = [(value, 0)]
        while stack:
            item, level = stack.pop()
            kind = type(item)
            if kind in (str, bool, int) or item is None:
                continue
            if kind is float:
                if not math.isfinite(item):
                    return _finding('number', 'a float that is not finite')
                continue
            if kind is dict:
                if level + 1 > _MAX_DEPTH:
                    return _finding('depth', 'more than 50 levels')
                for key, sub in item.items():
                    if type(key) is not str:
                        return _finding('key', 'a key that is not a text')
                    stack.append((sub, level + 1))
                continue
            if kind is list:
                if level + 1 > _MAX_DEPTH:
                    return _finding('depth', 'more than 50 levels')
                for sub in item:
                    stack.append((sub, level + 1))
                continue
            return _finding('type', 'a value that is not plain data')
        return None
    except Exception:
        return _finding('error', 'an unexpected error')
