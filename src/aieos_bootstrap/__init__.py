"""The bootstrap package of gov-AIEOS (tasks TASK-001, TASK-003 and TASK-004).

It holds three modules:
- ``records`` (TASK-001): a checker of the form of event-log lines, records and event payloads of specification 2
  sections 6.1 to 6.4. It reads only the text it is given, writes nothing and decides nothing.
- ``conformance`` (TASK-003): the conformance runner of docs/specs/conformance-files.md section 6. It reads the frozen
  set, the fixtures and the bound scenario file from the tree it is given, compares a governor's decision records with
  the expected values, and returns the run record; it writes nothing and decides no acceptance.
- ``governor`` (TASK-004): the bootstrap governor of docs/pre-genesis/governor-spec.md, its first version. It reads only
  its arguments and returns one acceptance decision record, which is advisory; it writes nothing.
"""

__all__ = ['conformance', 'governor', 'records']
