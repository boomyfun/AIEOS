# DEF-0101: the launcher's open requirements before a runtime is launched

- Status: open
- Opened: 2026-10-24 (session 3797498a; TASK-086's contract, decisions D-2673, D-2681)
- Deferred by: decision agent (A41, A51), D-2681 Q1 and Q3 (TASK-086's launcher writes no observed read-set record
  and leaves max_risk to its caller; these requirements are carried here).
- Decision group: A (later M7 tasks within the self-build; launching with a runtime stays the owner's, DM A51 item (4)).

## What
TASK-086's launcher (src/aieos_bootstrap/launcher.py) runs the core's expiry, the Resume Check and the grant over
adapter.start and adapter.end, and starts no runtime. Before a runtime is launched with it, these stay open:
- the observed read-set record before every lease release (specification 7 :45, specification 5 :112;
  read_set_record.py :19-24) at its three call places: the normal end (read_set_record.observe before adapter.end),
  the gone session's record at the end after a violation or an expiry, and the gone session's record at the next
  start (specification 5 :125); and the removal of the session's stored reads;
- the check that HEAD is the base branch's tip, and check 0 of the contract (specification 5 :121; specification 7
  :49); AIEOS_BASE is the head_commit read once;
- launching with a runtime, the owner's act, is not to happen before TASK-089 lands; this is a statement, not a lock;
- max_risk is the caller's: a caller passing a non-null max_risk declares the runtime's tier, which only the owner's
  measurement can back (C6, P-LOC); the self-build passes null until then, so the launcher never grants (decision
  D-2673 ruling 2);
- a stand-in start or end giving a non-list truthy findings value would raise past the launcher's step guard; the
  real adapter.start and adapter.end always give a list (TASK-086's acceptance, decision D-2758).

## Why deferred
D-2681 Q1: the three record call places and the stored reads' removal are one task, TASK-089, after TASK-086; Q3:
max_risk stays the caller's until a tier is measured.

## Resume when
At TASK-089, not yet contracted (planned by decisions D-2673 and D-2681); this item closes when the observed
read-set record is written at its three call places and the stored reads are removed, each by an accepted task, and
the base-tip check and check 0 are met or moved by their own decision.

## Depends on
TASK-086 (the launcher), TASK-064 (read_set_record, the record's core side; read_set_record.py :1), TASK-066 to
TASK-068 (the read hook that writes the reads; DEF-0097 :14), TASK-051 (adapter); specification 5 section 11 points 7
and 10, specification 7 section 5.

## Log
- 2026-10-24: opened with TASK-086's records (session 3797498a; decisions D-2681, D-2758).
