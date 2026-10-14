"""Autonomy L1 to L2 as a product feature (task TASK-036; specification 4 section 9; assurance-model.md section 6).

One pure function, ``auto_accept_allowed(levels, allowance, risk, status, touches)``: whether the policy's half of the
governor's row 4 allows auto-accept for a task's risk class. It reads only the values it is given, writes nothing,
reads no file, clock, environment or network, and never raises.

What the result is not:
- ``allowed`` is a necessary condition only: the policy's half of row 4. It is not an acceptance, not a gate result
  and not a ruling on "sufficient assurance" (concept line 622); row 4's other half (every gate passed, the profile
  complete) stays the governor's.
- The caller supplies the levels and the allowance only from an approved, versioned policy, and the statuses only from
  pinned values (assurance-model.md section 6; INV-011). This module defines no level, allowance or status for any
  project, and it does not read gov-AIEOS's.
- Connecting this function to the governor is a separate governor change, not made here; the governor's
  LEVEL_AT_LEAST_L2 stays False and its row 4 stays unreachable.

The rule, fail closed (each reason is added when its condition holds, in this order; ``allowed`` is True only when
no reason is added):
1. "risk": risk is not a str (exactly that type) among low, medium, high and critical.
2. "level": risk is one of them and levels is not a dict (exactly that type), or holds no entry for the class, or the
   entry is neither exactly {"level": "L1"} nor a dict with exactly the keys level, change_request and metrics where
   level is "L2" and change_request and metrics are non-empty str. The level is then "L1". When risk is not one of the
   four, the level is "L1" and "level" is not added.
3. "L1": the level is "L1" (at L1 acceptance ends at NEEDS_REVIEW).
4. "risk above medium": the level is "L2" and risk is high or critical (concept line 622).
5. "policy": unless allowance is a dict and its value for risk is True itself.
6. "C13": unless status is a dict whose value for "C13" is a str equal to "PASS"; a missing value counts as not PASS.
7. "P-CRED": likewise for "P-CRED".
8. "touches policy": unless touches is False itself (a change to the policy, the risk rules, the default profiles,
   the level assignments or the acceptance verifier is never auto-accepted).

Checks are by type and identity, never by truthiness: 1 or "true" is not True, 0 or None is not False, "pass" is not
"PASS"; a dict or str subclass is treated by its type as not a dict or not a str, so no value of unknown type is
hashed or compared.

The L2 entry check is a check of form only: whether the change request is approved and whether the metrics suffice
are the caller's and the approver's. Any bound above L2 is not expressible: a level other than "L1" or "L2" fails
closed.

Reading R1 (the implementer's): the function fails closed when P-CRED is not exactly "PASS", as it does for C13.
This is stricter than specification 4 section 9, which names only C13; whether L2 may be used while P-CRED or C13 is
not PASS is the owner's (master-plan.md section 9 item 5), and only the owner may loosen it.
"""

CLASSES = ('low', 'medium', 'high', 'critical')
_L2_KEYS = ('change_request', 'level', 'metrics')


def _is_str(v):
    return type(v) is str


def _is_dict(v):
    return type(v) is dict


def _class_of(risk):
    """The risk class as one of CLASSES, or None; compares only after checking the exact type."""
    if not _is_str(risk):
        return None
    for c in CLASSES:
        if risk == c:
            return c
    return None


def _get(d, key):
    """The value of a dict (exact type) for a str key, without hashing any key of unknown type; None if absent."""
    for k, v in d.items():
        if _is_str(k) and k == key:
            return v
    return None


def _level(entry):
    """'L1' or 'L2' for an entry in form, None otherwise."""
    if not _is_dict(entry):
        return None
    keys = list(entry)
    if not all(_is_str(k) for k in keys):
        return None
    level = _get(entry, 'level')
    if not _is_str(level):
        return None
    if level == 'L1' and sorted(keys) == ['level']:
        return 'L1'
    if level == 'L2' and sorted(keys) == list(_L2_KEYS):
        cr, metrics = _get(entry, 'change_request'), _get(entry, 'metrics')
        if _is_str(cr) and cr != '' and _is_str(metrics) and metrics != '':
            return 'L2'
    return None


def _passes(status, key):
    if not _is_dict(status):
        return False
    v = _get(status, key)
    return _is_str(v) and v == 'PASS'


def auto_accept_allowed(levels, allowance, risk, status, touches):
    """Return {'allowed': bool, 'level': 'L1' | 'L2', 'reasons': [str, ...]} by the rule of the module docstring."""
    reasons = []
    cls = _class_of(risk)
    level = 'L1'
    if cls is None:
        reasons.append('risk')
    else:
        found = _level(_get(levels, cls)) if _is_dict(levels) else None
        if found is None:
            reasons.append('level')
        else:
            level = found
    if level == 'L1':
        reasons.append('L1')
    elif cls in ('high', 'critical'):
        reasons.append('risk above medium')
    if not (cls is not None and _is_dict(allowance) and _get(allowance, cls) is True):
        reasons.append('policy')
    if not _passes(status, 'C13'):
        reasons.append('C13')
    if not _passes(status, 'P-CRED'):
        reasons.append('P-CRED')
    if touches is not False:
        reasons.append('touches policy')
    return {'allowed': not reasons, 'level': level, 'reasons': reasons}
