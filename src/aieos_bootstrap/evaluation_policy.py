"""The reader of the evaluation policy file (task TASK-153; BT3c-1 of DEF-0152 item 1; decisions D-6873 to D-6877): a pure
function that reads the TEXT of docs/specs/evaluation-policy-gov-aieos.md (the caller reads it at the pinned policy_ref
through the Git object store, as claude_code_shell_allow.read_policy_text does) and returns the six sources that the file
gives, in the governor's form, for eval_inputs. It opens no file, starts no process, reads no clock, no environment and no
network, and never raises an Exception. It does not check that the values are the decided policy (the content of the file
is BT3c-2's, and for owner_kept_rules, delegation and auto_accept the owner's): it checks the FORM.

``read_evaluation_policy(text)`` returns a mapping with exactly the keys result, sources and findings. The text must hold
the heading line "## 3. The sources" followed by one fenced block that starts with the line "```yaml" and ends with the
line "```" (the convention of scope_reconcile._block); only that block is read. Inside the block every line is blank, a
comment (its first non-space character is #) or part of one of six keys, exactly once each, in this order:
owner_kept_rules, articles, default_profiles, requirement_profiles, delegation, auto_accept. A key line is "<key>: gap"
(the open-gap marker: the source is None), or "<key>: []" (the empty list, for owner_kept_rules, articles and
requirement_profiles), or "delegation: true" / "delegation: false", or "<key>:" followed by lines of the forms below, two
spaces of indent per level, one or more of them:
  owner_kept_rules:     "  - match: [<item>, ...]"
  articles:             "  - id: <scalar>", "    scope: [<item>, ...]", "    evidence_required: [<item>, ...]" ("[]" allowed)
  default_profiles:     per risk (low, medium, high, critical: a subset, in that order) "  <risk>:" then lines
                        "    - {dimension: <scalar>, evidence_types: [<item>, ...]}"
  requirement_profiles: "  - id: <scalar>", "    add:" then lines "      - {dimension: <scalar>, evidence_types: [<item>, ...]}"
  auto_accept:          per risk, in the same order, "  <risk>: true" or "  <risk>: false"
Here "[<item>, ...]" is the notation of a flow list: "[" scalars separated by ", " "]" (the dots are notation, not file text).
Values are texts only: a scalar is a bare word that matches [A-Za-z0-9_.:/*-]+ in full, or a single-quoted text of one or
more characters with no quote, no backslash and no line break (the quotes are not part of the value). A bare word is
refused (reason scalar) when it is number-like or YAML-special: its first character is a digit; or float(word) or
int(word, 0) accepts it; or word.lower() is one of nan, .nan, inf, .inf, -inf, -.inf, infinity, -infinity, true, false,
yes, no, on, off, null. A quoted text is always a text. The booleans of delegation and auto_accept are the bare texts true
and false; there a number-like token is reason scalar and any other value is reason value. The reader never reads a number.

On present: result "present", sources a dict with exactly the six keys (each in the governor's form or None for a key marked
gap), findings []. Governor forms: owner_kept_rules a list of {match: [texts]}; articles a list of {id, scope,
evidence_required}; default_profiles a dict from risk to a list of {dimension, evidence_types}; requirement_profiles a list
of {id, add: [{dimension, evidence_types}]}; delegation a bool; auto_accept a dict from risk to bool. On any departure:
result "refused", sources all six keys None (never a partial answer) and findings exactly one {reason, line, detail}: the
first departure in the order argument (the text is not a str), encoding (a text that UTF-8 cannot encode: the line of the
first lone surrogate; the whole text is checked, comments included), block (the heading or the fence not found, or the
heading found twice), then the lines of the block from the top: line (a line not of the grammar: a tab, a CR, trailing
spaces, a comment after a value, a list without the ", " separator), key (an unknown, repeated, missing or out-of-order
key), value (a value outside the form of its key, an empty list where an item is needed, an empty block, a risk class not
in the closed set or out of order), scalar (a number-like or non-text scalar), duplicate (a repeated id, a repeated risk or
a repeated item in one list). line is the 1-based line number in the whole text, or None for argument and block. Among
the departures inside the block the finding is the one on the lowest line of the text (D-6884 M1), and on the same line a
line departure comes first; each names the line where it is (a repeated id, rule, risk or requirement: the line of the
second occurrence; a risk with no entry: its risk line; an id with no "add:", or an "add:" with no entry: the id line or
the add line; an empty key block: the key line; a missing key: the line of the closing fence). A "```yaml" line anywhere
other than the one that opens the block, before the heading too, is a block departure; a quoted text may not hold any
character at which str.splitlines splits (reason scalar). Two readings that the contract leaves open are declared: an
unexpected internal exception is reported as reason argument (line None), because the closed set has no internal-error
reason; and a repeated whole owner rule is refused as a duplicate (stricter than the contract's list). A "no entry" or
"no add:" finding names the earlier line only when the line that follows is itself of a form of that block, or the block
ends; a line of no form of the block is reported on its own line (D-6885 N1).

EVIDENCE_DEFINING_PATHS is the list of repository paths whose change may weaken an evidence requirement (governor-spec :44),
for the producer of evidence_comparison in BT3b-2 (D-6874 (e)): docs/pre-genesis/constitution.md (an evidence_required entry
of the constitution, or the scope, applicability or severity of an article: governor-spec :44), docs/pre-genesis/
assurance-model.md (the default profiles: :76-:84, :95-:96), docs/specs/risk-rules-gov-aieos.md (the policy's risk rules:
governor-spec :44), docs/pre-genesis/decision-matrix.md (the pinned delegation and the approvals the policy mirrors; the
policy paths of eval_inputs), docs/specs/evaluation-policy-gov-aieos.md (this policy file), src/aieos_bootstrap/governor.py
(this governor's rules on which records satisfy an entry: governor-spec :44), docs/pre-genesis/governor-spec.md (the
definitions of the inputs: :43-:44, :196), src/aieos_bootstrap/evaluation_policy.py and src/aieos_bootstrap/
eval_inputs.py (the modules that give the sources). The list is INCOMPLETE against governor-spec :44 ("an evidence entry
of a requirement"): where a requirement's evidence entries live is not established, so BT3b-2 may not give
evidence_comparison {weakens: false} for any task until the requirement entities' paths are added by a decided change, or a
decision records, with a Grep over every requirement entity, that none holds an evidence entry. Shrinking the list later is
itself a weakens-evidence change. It names the derivations that BT3b-2 computes (not coded here): ruleset_version, the text
"governor-sha256:" and the sha256 of src/aieos_bootstrap/governor.py at the pinned policy_ref (refused if it differs from
the CI's AIEOS_PINNED_GOVERNOR value printed by the same run); level_version, the text "L1:" and policy_version (L1 is the
level in force for every risk class of the self-build, assurance-model :90, spec-04 :93, and is not a value of the file).

Limits: the module checks form, not the decided policy; spec-02 section 7 :228 describes the product's project.yaml
(autonomy with a level_version per class; default_profiles for v0.1 low and medium only), whereas this file is the
self-build's own policy file, as risk-rules-gov-aieos.md is, its reader is not the project.yaml reader, level_version is
derived as named above and the grammar accepts all four risks in default_profiles (a departure from that description,
stated and not hidden); until the GOV-003 evaluator-list decision this module is not an evaluator path of GOV-003.
"""
import re

_HEADING = '## 3. The sources'
_FENCE_OPEN = '```yaml'
_FENCE_CLOSE = '```'
_KEYS = ('owner_kept_rules', 'articles', 'default_profiles', 'requirement_profiles', 'delegation', 'auto_accept')
_RISKS = ('low', 'medium', 'high', 'critical')
_BARE = re.compile(r'[A-Za-z0-9_.:/*-]+')
_QUOTED = re.compile(r"'[^'\\\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029]+'")
_SPECIAL = frozenset(('nan', '.nan', 'inf', '.inf', '-inf', '-.inf', 'infinity', '-infinity', 'true', 'false', 'yes', 'no',
                      'on', 'off', 'null'))
_KEYLINE = re.compile(r'([a-z_]+):(?: (.*))?')
EVIDENCE_DEFINING_PATHS = (
    'docs/pre-genesis/constitution.md',
    'docs/pre-genesis/assurance-model.md',
    'docs/specs/risk-rules-gov-aieos.md',
    'docs/pre-genesis/decision-matrix.md',
    'docs/specs/evaluation-policy-gov-aieos.md',
    'src/aieos_bootstrap/governor.py',
    'docs/pre-genesis/governor-spec.md',
    'src/aieos_bootstrap/evaluation_policy.py',
    'src/aieos_bootstrap/eval_inputs.py',
)


class _Departure(Exception):
    def __init__(self, reason, line, detail):
        Exception.__init__(self, reason)
        self.reason = reason
        self.line = line
        self.detail = detail


def _refused(reason, line, detail):
    return {'result': 'refused', 'sources': dict.fromkeys(_KEYS), 'findings': [{'reason': reason, 'line': line, 'detail': detail}]}


_NANINF = frozenset(('nan', '.nan', 'inf', '.inf', '-inf', '-.inf', 'infinity', '-infinity'))


def _numeric(word):
    """A number-like token (any characters): its first character is a digit, or float(word) or int(word, 0) accepts it, or
    it is a nan or infinity spelling. In a boolean position this is reason scalar; yes, no, on, off, null and the case
    variants of true and false are reason value there."""
    if word == '':
        return False
    if word[0].isdigit() or word.lower() in _NANINF:
        return True
    for conv in (float, lambda w: int(w, 0)):
        try:
            conv(word)
            return True
        except (ValueError, OverflowError):
            pass
    return False


def _numberlike(word):
    """A bare word that is not a text scalar: number-like or YAML-special."""
    return _numeric(word) or word.lower() in _SPECIAL


def _scalar(token, n):
    """One scalar in a scalar position: a bare word or a single-quoted text; anything else is reason scalar."""
    if _QUOTED.fullmatch(token):
        return token[1:-1]
    if _BARE.fullmatch(token) and not _numberlike(token):
        return token
    raise _Departure('scalar', n, 'not a text scalar: %r' % token[:40])


def _flow(token, n, empty_ok):
    """A flow list "[a, b]" of scalars (or "[]" when empty_ok); the separator is exactly ", "."""
    if not (token.startswith('[') and token.endswith(']')):
        raise _Departure('value', n, 'not a flow list: %r' % token[:40])
    inner = token[1:-1]
    if inner == '':
        if empty_ok:
            return []
        raise _Departure('value', n, 'an empty list where an item is needed')
    # split on ", " outside single quotes; a comma without the space, or a space without the comma, is a line departure
    parts, cur, quoted, i = [], '', False, 0
    while i < len(inner):
        ch = inner[i]
        if ch == "'":
            quoted = not quoted
            cur += ch
        elif not quoted and inner.startswith(', ', i):
            parts.append(cur)
            cur = ''
            i += 1
        else:
            cur += ch
        i += 1
    parts.append(cur)
    if quoted:
        raise _Departure('scalar', n, 'an unterminated quote')
    for p in parts:
        if p == '' or ',' in _quoteless(p):
            raise _Departure('line', n, 'a flow list not written with ", " separators')
    out = [_scalar(p, n) for p in parts]
    if len(set(out)) != len(out):
        raise _Departure('duplicate', n, 'a repeated item in one list')
    return out


def _quoteless(text):
    """The text of a line with the single-quoted spans blanked, for the comment-after-value check."""
    return re.sub(r"'[^']*'", "''", text)


def _entry(text, n):
    """A profile entry line (after the dash): "{dimension: <scalar>, evidence_types: [<item>, ...]}"."""
    m = re.fullmatch(r'\{dimension: (.+), evidence_types: (\[.*\])\}', text)
    if m is None:
        raise _Departure('line', n, 'not a profile entry {dimension: X, evidence_types: [..]}')
    return {'dimension': _scalar(m.group(1), n), 'evidence_types': _flow(m.group(2), n, False)}


def _block(lines):
    """The lines of the block as (number, text) and the number of the closing fence, or a block departure. A "```yaml" line
    anywhere other than the one that opens the block (before the heading too) is a block departure (D-6884 M3)."""
    heads = [i for i, l in enumerate(lines) if l == _HEADING]
    if len(heads) != 1:
        raise _Departure('block', None, 'the heading line "%s" is found %d times' % (_HEADING, len(heads)))
    opens = [i for i, l in enumerate(lines) if l == _FENCE_OPEN]
    if len(opens) > 1:
        raise _Departure('block', None, 'a second "```yaml" line')
    start = opens[0] if opens and opens[0] > heads[0] else None
    if start is None:
        raise _Departure('block', None, 'no "```yaml" line after the heading')
    end = next((k for k in range(start + 1, len(lines)) if lines[k] == _FENCE_CLOSE), None)
    if end is None:
        raise _Departure('block', None, 'the fenced block is never closed')
    return [(k + 1, lines[k]) for k in range(start + 1, end)], end + 1


def _lexical(body):
    """The first lexical departure of the block, (line, detail), or None: a tab, a CR or trailing spaces (comment lines and
    lines of spaces included), or a comment after a value. It raises nothing: the caller compares its line with the first
    structural departure (D-6884 M1)."""
    for n, l in body:
        if '\t' in l or '\r' in l or l != l.rstrip(' '):
            return n, 'a tab, a CR or trailing spaces'
        s = l.strip()
        if s == '' or s.startswith('#'):
            continue
        if re.search(r'\s#', _quoteless(l)):
            return n, 'a comment after a value'
    return None


def _parse(lines):
    """The first departure is the one on the lowest line of the text; on the same line a line departure comes first."""
    body, close_no = _block(lines)
    lex = _lexical(body)
    items = [(n, l) for n, l in body if l.strip() != '' and not l.strip().startswith('#')]
    sources, st = None, None
    try:
        sources = _structure(items, close_no)
    except _Departure as d:
        st = d
    if lex is not None and (st is None or st.line is None or lex[0] <= st.line):
        raise _Departure('line', lex[0], lex[1])
    if st is not None:
        raise st
    return sources


def _structure(items, close_no):
    sources, pos = {}, 0
    for key in _KEYS:
        if pos >= len(items):
            raise _Departure('key', close_no, 'the key %s is missing' % key)
        n, l = items[pos]
        m = _KEYLINE.fullmatch(l)
        if l.startswith(' ') or m is None:
            raise _Departure('line', n, 'not a key line: %r' % l[:40])
        name, rest = m.group(1), m.group(2)
        if name != key:
            if name in sources or name in _KEYS:
                raise _Departure('key', n, 'the key %s is repeated or out of order (expected %s)' % (name, key))
            raise _Departure('key', n, 'an unknown key %s (expected %s)' % (name, key))
        pos += 1
        sub = []
        while pos < len(items) and items[pos][1].startswith(' '):
            sub.append(items[pos])
            pos += 1
        if rest == 'gap':
            if sub:
                raise _Departure('value', sub[0][0], 'lines under a key marked gap')
            sources[key] = None
        elif key == 'delegation':
            if sub or rest is None:
                raise _Departure('value', n, 'delegation takes true, false or gap')
            if rest in ('true', 'false'):
                sources[key] = rest == 'true'
            elif _numeric(rest):
                raise _Departure('scalar', n, 'a number-like token in a boolean position: %r' % rest[:40])
            else:
                raise _Departure('value', n, 'delegation takes true, false or gap, not %r' % rest[:40])
        elif rest == '[]':
            if key not in ('owner_kept_rules', 'articles', 'requirement_profiles'):
                raise _Departure('value', n, '"[]" is not allowed for %s' % key)
            if sub:
                raise _Departure('value', sub[0][0], 'lines under an empty list')
            sources[key] = []
        elif rest is not None:
            raise _Departure('value', n, 'a value on the key line of %s' % key)
        else:
            sources[key] = _body(key, sub, n)
    if pos != len(items):
        n, l = items[pos]
        raise _Departure('line', n, 'a line after the last key: %r' % l[:40])
    return sources


def _body(key, sub, n0):
    """The lines under one key; every departure names the line where it is (D-6884 M1)."""
    if not sub:
        raise _Departure('value', n0, 'an empty block for %s' % key)
    if key == 'owner_kept_rules':
        out, seen = [], set()
        for n, l in sub:
            m = re.fullmatch(r'  - match: (\[.*\])', l)
            if m is None:
                raise _Departure('line', n, 'not "  - match: [..]"')
            match = _flow(m.group(1), n, False)
            if tuple(match) in seen:
                raise _Departure('duplicate', n, 'a repeated rule')
            seen.add(tuple(match))
            out.append({'match': match})
        return out
    if key == 'articles':
        out, seen = [], set()
        for i in range(0, len(sub), 3):
            tri = sub[i:i + 3]
            (n0_, l0) = tri[0]
            m0 = re.fullmatch(r'  - id: (.+)', l0)
            if m0 is None:
                raise _Departure('line', n0_, 'not the id line of an article')
            art_id = _scalar(m0.group(1), n0_)
            if art_id in seen:
                raise _Departure('duplicate', n0_, 'a repeated article id')
            seen.add(art_id)
            scope = required = None
            if len(tri) >= 2:
                m1 = re.fullmatch(r'    scope: (\[.*\])', tri[1][1])
                if m1 is None:
                    raise _Departure('line', tri[1][0], 'not the scope line of an article')
                scope = _flow(m1.group(1), tri[1][0], False)
            if len(tri) == 3:
                m2 = re.fullmatch(r'    evidence_required: (\[.*\])', tri[2][1])
                if m2 is None:
                    raise _Departure('line', tri[2][0], 'not the evidence_required line of an article')
                required = _flow(m2.group(1), tri[2][0], True)
            if len(tri) != 3:
                raise _Departure('line', n0_, 'an article is three lines: id, scope, evidence_required')
            out.append({'id': art_id, 'scope': scope, 'evidence_required': required})
        return out
    if key == 'default_profiles':
        out, last, cur, cur_n = {}, -1, None, None
        for n, l in sub:
            entry = re.fullmatch(r'    - (\{.*\})', l)
            m = re.fullmatch(r'  ([a-z]+):', l)
            if cur is not None and not out[cur] and m is not None:
                raise _Departure('value', cur_n, 'the risk %s has no profile entry' % cur)
            if m is not None:
                if m.group(1) not in _RISKS:
                    raise _Departure('value', n, 'a risk class not in low, medium, high, critical: %r' % m.group(1))
                if m.group(1) in out:
                    raise _Departure('duplicate', n, 'a repeated risk %s' % m.group(1))
                if _RISKS.index(m.group(1)) < last:
                    raise _Departure('value', n, 'the risks are out of order')
                last, cur, cur_n = _RISKS.index(m.group(1)), m.group(1), n
                out[cur] = []
                continue
            if entry is None or cur is None:
                raise _Departure('line', n, 'not a risk line or a profile entry')
            out[cur].append(_entry(entry.group(1), n))
        if cur is not None and not out[cur]:
            raise _Departure('value', cur_n, 'the risk %s has no profile entry' % cur)
        return out
    if key == 'requirement_profiles':
        out, cur, cur_n, add_n, seen = [], None, None, None, set()
        for n, l in sub:
            entry = re.fullmatch(r'      - (\{.*\})', l)
            m = re.fullmatch(r'  - id: (.+)', l)
            if cur is not None and (m is not None or entry is not None or l == '    add:'):
                if cur['add'] is None and l != '    add:':
                    raise _Departure('value', cur_n, 'a requirement profile with no add: line')
                if cur['add'] is not None and not cur['add'] and entry is None:
                    raise _Departure('value', add_n, 'an add: with no entry')
            if m is not None:
                rid = _scalar(m.group(1), n)
                if rid in seen:
                    raise _Departure('duplicate', n, 'a repeated requirement id')
                seen.add(rid)
                out.append({'id': rid, 'add': None})
                cur, cur_n = out[-1], n
                continue
            if l == '    add:':
                if cur is None or cur['add'] is not None:
                    raise _Departure('line', n, '"add:" without its id line or twice')
                cur['add'], add_n = [], n
                continue
            if entry is None or cur is None or cur['add'] is None:
                raise _Departure('line', n, 'not an id line, an add line or a profile entry')
            cur['add'].append(_entry(entry.group(1), n))
        if cur is not None and cur['add'] is None:
            raise _Departure('value', cur_n, 'a requirement profile with no add: line')
        if cur is not None and not cur['add']:
            raise _Departure('value', add_n, 'an add: with no entry')
        return out
    out, last = {}, -1
    for n, l in sub:
        m = re.fullmatch(r'  ([a-z]+): (.+)', l)
        if m is None:
            raise _Departure('line', n, 'not "  <risk>: true|false"')
        risk, val = m.group(1), m.group(2)
        if risk not in _RISKS:
            raise _Departure('value', n, 'a risk class not in low, medium, high, critical: %r' % risk)
        if risk in out:
            raise _Departure('duplicate', n, 'a repeated risk %s' % risk)
        if _RISKS.index(risk) < last:
            raise _Departure('value', n, 'the risks are out of order')
        last = _RISKS.index(risk)
        if val not in ('true', 'false'):
            if _numeric(val):
                raise _Departure('scalar', n, 'a number-like token in a boolean position: %r' % val[:40])
            raise _Departure('value', n, 'a boolean is true or false, not %r' % val[:40])
        out[risk] = val == 'true'
    return out


def read_evaluation_policy(text):
    """The sources of the policy file in the text, or a refusal that gives none (the module docstring is the grammar)."""
    try:
        if not isinstance(text, str):
            return _refused('argument', None, 'the text is not a str')
        try:
            text.encode('utf-8')
        except UnicodeEncodeError:
            for n, l in enumerate(text.split('\n'), 1):
                try:
                    l.encode('utf-8')
                except UnicodeEncodeError:
                    return _refused('encoding', n, 'a text that UTF-8 cannot encode (a lone surrogate)')
            return _refused('encoding', None, 'a text that UTF-8 cannot encode')
        try:
            sources = _parse(text.split('\n'))
        except _Departure as d:
            return _refused(d.reason, d.line, d.detail)
        return {'result': 'present', 'sources': sources, 'findings': []}
    except Exception:
        return _refused('argument', None, 'an unexpected exception inside the reader')
