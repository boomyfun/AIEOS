"""The shared resolution of a task contract's path (task TASK-107; specification 7 revision 6, section 6; DEF-0105 link 1).

Every reader of a task contract (base_inputs, task_contract.read_contract and the contract walk of claude_code_shell_allow)
asks this module where the contract may be and how to read the answers, so that the Work Order, the Resume Check, the launcher
and the hook read the same contract.

``candidates(task_id)`` returns the two places in the order they are looked at, each as a tuple of path components:
(the writer's state directory, 'tasks', '<task_id>.yaml') and ('docs', 'tasks', '<task_id>.yaml'). The state directory is
``writer.STATE_DIR``, the only thing this module takes from the writer; it holds no literal of that name (CI's string rule
allows it only in the writer and in the shell allowlist reader). A task id that is not TASK- and digits raises ValueError.

``decide(state, docs)`` takes what a reader found at each place, one of 'present', 'absent' or 'refused', and returns a pair:
- (present, absent) gives ('read', 'state'); (absent, present) gives ('read', 'docs');
- (present, present) gives ('both', None): the contract is in both folders and nothing is read;
- (absent, absent) gives ('absent', None): the reader gives its own absent finding;
- 'refused' on the state side gives ('refused', 'state'), also when the docs side is refused as well; 'refused' on the docs side
  with the state side present or absent gives ('refused', 'docs').
Only a missing entry counts as absent. Any other refusal at the state place (an entry of the wrong kind or mode, a failed or
out-of-form read) is a refusal and never a fallback to docs. The pair (present, refused) giving ('refused', 'docs') is a stated
choice of TASK-107, proposed and fail closed, not the words of the specification: an unreadable docs side cannot be shown absent,
which the both-folders rule needs. Any other argument raises ValueError.

The module does no I/O: it opens no file, starts no process and reads no clock or environment; the walk and the reads stay in
each reader. It makes no Git call, so it adds nothing to any reader's call bounds; the bounds are stated in each reader. Limits:
the resolution reads the committed base only; a task with the same contract in both folders is refused until an approved act
removes one; DEF-0095 (the handoff reader) and DEF-0113 are not done here.
"""

from aieos_bootstrap import writer

DOCS_DIR = 'docs'
TASKS_DIR = 'tasks'
SIDES = ('present', 'absent', 'refused')


def _check_id(task_id):
    if not (type(task_id) is str and task_id.startswith('TASK-') and task_id[5:].isascii() and task_id[5:].isdigit()):
        raise ValueError('candidates: the task id is not TASK- and digits')


def candidates(task_id):
    """The two places of the task's contract, state directory first: ((state, 'tasks', name), ('docs', 'tasks', name))."""
    _check_id(task_id)
    name = task_id + '.yaml'
    return ((writer.STATE_DIR, TASKS_DIR, name), (DOCS_DIR, TASKS_DIR, name))


def decide(state, docs):
    """What to do with the answers at the state place and the docs place: ('read', 'state'), ('read', 'docs'), ('both', None),
    ('absent', None) or ('refused', 'state' or 'docs')."""
    for side in (state, docs):
        if type(side) is not str or side not in SIDES:
            raise ValueError('decide: a side is not present, absent or refused')
    if state == 'refused':
        return ('refused', 'state')
    if docs == 'refused':
        return ('refused', 'docs')
    if state == 'present':
        return ('both', None) if docs == 'present' else ('read', 'state')
    return ('read', 'docs') if docs == 'present' else ('absent', None)
