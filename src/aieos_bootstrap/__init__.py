"""The bootstrap package of gov-AIEOS (tasks TASK-001, TASK-003, TASK-004, TASK-006, TASK-007, TASK-008, TASK-009,
TASK-016, TASK-021, TASK-022, TASK-023, TASK-024, TASK-025 and TASK-026).

It holds thirteen modules:
- ``records`` (TASK-001): a checker of the form of event-log lines, records and event payloads of specification 2
  sections 6.1 to 6.4. It reads only the text it is given, writes nothing and decides nothing.
- ``conformance`` (TASK-003, with TASK-006's Resume Check entry and TASK-017's Risk Engine entry): the conformance runner of
  docs/specs/conformance-files.md sections 6, 9 and 10. It reads the frozen set, the fixtures and the bound scenario file
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
- ``writer`` (TASK-016): the core's single writer of the project-state directory, specifications 1 and 2: it appends
  the lines ``eventlog`` decides to the event log file, records every fence refusal, and keeps the local store of the
  fence's epoch and counter, the leases and the sessions; it opens no other file, and every time is an argument.
- ``ac_coverage`` (TASK-021): the AC coverage check of specification 4 section 6 item 1. Given a task contract's
  values, it returns the acceptance criteria that no gate of its verification plan names, an empty list of criteria
  and the stray args entries, and the one blocking record for them; it reads and writes no file.
- ``ac_tests`` (TASK-022): the test-to-AC listing of specification 4 section 6 item 2. Given a task id, its contract's
  values, the test files' source texts and every task's write set, it returns per acceptance criterion the tests
  that name it in their own name or docstring, and the criteria of the G2 tests gate that no test names, and the one
  blocking record for them; it reads and writes no file.
- ``stale`` (TASK-023): the stale-evidence computation of specification 4 section 3 rules 2 and 3 and section 7 item
  3. Given one task's reconciliation facts as values, it returns the stale record ids by reason, at most one
  evidence.stale event per reason with only the new ids, and what it could not check; it reads and writes no file and
  appends nothing.
- ``gitread`` (TASK-024): the Git reader, constitution INV-001's single process wrapper and the first piece of the
  core's caller. It starts only git, with one of four pinned read-only subcommands in fixed forms, no shell, a
  controlled environment, a pinned working directory and a timeout, and returns the exit code and the output as bytes;
  its parsers turn a commit object and a list of changed paths into values. It writes nothing; submit calls it.
- ``submit`` (TASK-025): the submission path of the core's caller. It reads one commit through gitread, takes its
  AIEOS-Task and AIEOS-Fence trailers with recovery's rules, appends the task.submitted event through the writer, whose
  fence check decides and records any refusal, and releases the lease; it opens no file itself and reads no clock.
- ``startup`` (TASK-026): recovery at start, the third piece of the core's caller. It walks the commits reachable from
  HEAD through gitread within a bound, lets ``recovery`` decide every event, appends those events through the writer,
  releases by token the leases that logged submissions name, and then expires the leases past their expiry; it opens
  no file itself and reads no clock.
"""

__all__ = ['ac_coverage', 'ac_tests', 'conformance', 'eventlog', 'gitread', 'governor', 'records', 'recovery',
           'resume_check', 'stale', 'startup', 'submit', 'writer']
