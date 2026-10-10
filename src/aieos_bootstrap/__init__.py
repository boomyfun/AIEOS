"""The bootstrap package of gov-AIEOS (tasks TASK-001, TASK-003, TASK-004, TASK-006, TASK-007, TASK-008 and TASK-009).

It holds six modules:
- ``records`` (TASK-001): a checker of the form of event-log lines, records and event payloads of specification 2
  sections 6.1 to 6.4. It reads only the text it is given, writes nothing and decides nothing.
- ``conformance`` (TASK-003, with TASK-006's Resume Check entry): the conformance runner of
  docs/specs/conformance-files.md sections 6 and 9. It reads the frozen set, the fixtures and the bound scenario file
  from the tree it is given, chooses each scenario's entry by its capability, compares a governor's decision records,
  or a Resume Check's execution decisions, with the expected values, and returns the run record; it writes nothing and
  decides no acceptance and no execution.
- ``governor`` (TASK-004): the bootstrap governor of docs/pre-genesis/governor-spec.md, its first version. It reads only
  its arguments and returns one acceptance decision record, which is advisory; it writes nothing.
- ``eventlog`` (TASK-007): the event log's append rules of specifications 1 and 2. Given a log's bytes and one new
  event, it returns the exact bytes to append, or why nothing is appended; it opens and writes no file.
- ``resume_check`` (TASK-008): the Resume Check of specification 3. Given the inputs of its section 1 as values, it
  returns one execution decision record with the events its section 10 gives; it reads, writes and appends nothing.
- ``recovery`` (TASK-009): recovery between Git and the event log at start, specification 1 section 7. Given a log's
  bytes, the commits read from Git, the leases the local store holds and the recovery time, it returns the log after
  the events it appends through ``eventlog``, and the leases whose expiry has passed; it reads and writes no file.
"""

__all__ = ['conformance', 'eventlog', 'governor', 'records', 'recovery', 'resume_check']
