"""The mapper of the self-build's intent versions (task TASK-160; BT3b-2d-3 of DEF-0156 and DEF-0152).

The port of the self-build's mapping script (revision r2, D-1131; its three fixed forms of D-1130) for specification 2
section 6.2 (:175-:176): the version of an entity that a task contract names by its file's path with the SHA-256 of its
bytes is v<N>, N being the revision number that a decision-matrix row names with that exact SHA-256. It adds no new rule
and never guesses a version.

map_intent_versions(entities, dm_text) returns exactly the keys value and findings. value is a dict from each path of
entities to "v" and decimal digits, with findings []; or value None with exactly one finding {reason, detail}, the detail
cut to its first 200 characters. The answer is never partial. The module starts no process, opens no file, reads no
clock, no environment and no network, writes nothing, changes no argument and raises no Exception (an unexpected one
is refused with the reason argument and a detail naming its type).

The order of the checks. (1) entities is a dict with 1 to 100 items (a resource bound) and dm_text a str, else reason
argument. (2) Every key and every value is a str, checked before any sorting; then, over the entities in sorted key
order, each key is a file path in the form of base_files' path rule (base_files._names, a private name, used as
evaluation_sources uses evaluation._task_commits) and each value is exactly 64 lowercase hexadecimal characters, else
reason entity; all entities are checked before any row is read. base_files' rule takes a name with a leading dot, so
such a key is taken here; the contract reader of the loader refuses such a contract earlier. (3) The rows are the lines
of dm_text split at the line feed that start with "| ". For each entity in sorted key order the naming rows are those
that hold the value as a substring: none, reason no_row; a naming row that binds the value in none of the forms, or
whose number cannot be converted to an integer, reason form; two different numbers over the naming rows, reason
revisions. The first entity that fails ends the call. The closed set of reasons: argument, entity, no_row, form,
revisions.

The forms, with the path matched literally and N made of the digits 0 to 9: (a) "`path` revision N (value)";
(b) "revision N (SHA-256 value)"; (c) a row that starts "| F" and digits and " | ", holds "SHA-256 value" exactly once
and holds exactly one match of "`path`", an optional ",", a space, an optional "still ", "revision N" ending at a word
boundary, that match starting before the "SHA-256 value".

The differences from the script: the answer is all or nothing; the bound of 1 to 100 entities; the key and value form
checks of all entities before any row is read, a trailing line feed of a value refused; digits 0 to 9 only, also in the
row id of form (c); other reason names and detail texts, in a closed set.

Limits, carried from the script: L1, form (b) binds by the value alone, not by the path (the value is the file's own
bytes); L2, a row that names the value in a form and also elsewhere is not refused; L3, a row's status is not read. The
text of the decision matrix is read only; whether a row is in force is not read.
"""
import re

from aieos_bootstrap import base_files

_VALUE = re.compile(r'[0-9a-f]{64}')
_F_ROW = re.compile(r'\| F[0-9]+ \| ')
_MAX_ENTITIES = 100
_MAX_DETAIL = 200


class _Refuse(Exception):
    """A refusal found inside a step: its reason and detail."""

    def __init__(self, reason, detail):
        Exception.__init__(self, reason)
        self.reason = reason
        self.detail = detail


def _refused(reason, detail):
    return {'value': None, 'findings': [{'reason': reason, 'detail': detail[:_MAX_DETAIL]}]}


def _checked(entities):
    """The keys of entities in sorted order, every key and value in form, or a refusal with the reason entity."""
    for key, value in entities.items():
        if type(key) is not str or type(value) is not str:
            raise _Refuse('entity', 'an entity key or value is not a str')
    keys = sorted(entities)
    for position, key in enumerate(keys, 1):
        try:
            base_files._names(key, 'path', False)
        except Exception:
            raise _Refuse('entity', 'the key at position %d is not a file path in form' % position)
        if _VALUE.fullmatch(entities[key]) is None:
            raise _Refuse('entity', 'the value at position %d is not 64 lowercase hexadecimal characters' % position)
    return keys


def _numbers(row, path, value):
    """The revision numbers, as texts, that the row binds to the path and the value in the forms (a), (b) and (c)."""
    quoted = '`' + re.escape(path) + '`'
    found = re.findall(quoted + r' revision ([0-9]+) \(' + value + r'\)', row)
    found += re.findall(r'revision ([0-9]+) \(SHA-256 ' + value + r'\)', row)
    if _F_ROW.match(row) is not None and row.count('SHA-256 ' + value) == 1:
        marks = list(re.finditer(quoted + r',? (?:still )?revision ([0-9]+)\b', row))
        if len(marks) == 1 and marks[0].start() < row.index('SHA-256 ' + value):
            found.append(marks[0].group(1))
    return found


def _version(rows, path, value):
    """The version of one entity from the rows, or a refusal with the reason no_row, form or revisions."""
    naming = [(number, row) for number, row in rows if value in row]
    if not naming:
        raise _Refuse('no_row', 'no decision-matrix row names the SHA-256 of ' + path)
    versions = set()
    for number, row in naming:
        found = _numbers(row, path, value)
        try:
            read = [int(text) for text in found]
        except ValueError:
            read = []
        if not read:
            raise _Refuse('form', 'row %s at line %d binds the SHA-256 in no form'
                          % (row.split('|')[1].strip(), number))
        versions.update(read)
    if len(versions) != 1:
        raise _Refuse('revisions', 'the SHA-256 of %s is named with %d revisions' % (path, len(versions)))
    return 'v%d' % versions.pop()


def map_intent_versions(entities, dm_text):
    """The version of every entity from the decision-matrix text, or one refusal."""
    try:
        if type(entities) is not dict or not 1 <= len(entities) <= _MAX_ENTITIES:
            return _refused('argument', 'entities is not a dict of 1 to %d items' % _MAX_ENTITIES)
        if type(dm_text) is not str:
            return _refused('argument', 'dm_text is not a str')
        keys = _checked(entities)
        rows = [(number, line) for number, line in enumerate(dm_text.split('\n'), 1) if line.startswith('| ')]
        mapped = {}
        for key in keys:
            mapped[key] = _version(rows, key, entities[key])
        return {'value': mapped, 'findings': []}
    except _Refuse as refusal:
        return _refused(refusal.reason, refusal.detail)
    except Exception as exc:
        return _refused('argument', 'an unexpected error: ' + type(exc).__name__)
