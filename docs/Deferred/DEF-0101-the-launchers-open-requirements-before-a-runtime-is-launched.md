# DEF-0101: the launcher's open requirements before a runtime is launched

- Status: open
- Opened: 2026-10-24 (session 3797498a; TASK-086's contract, decisions D-2673, D-2681)
- Deferred by: decision agent (A41, A51), D-2681 Q1 and Q3 (TASK-086's launcher writes no observed read-set record
  and leaves max_risk to its caller; these requirements are carried here).
- Decision group: A (later M7 tasks within the self-build; launching with a runtime stays the owner's, DM A51 item (4)).

## What
TASK-086's launcher (src/aieos_bootstrap/launcher.py) runs the core's expiry, the Resume Check and the grant over
adapter.start and adapter.end, and starts no runtime. Before a runtime is launched with it, these stay open:
- closed: the observed read-set record before every lease release (specification 7 :45, specification 5 :112;
  read_set_record.py :19-24) at its three call places: the normal end and the gone session's record at the end after
  a violation or an expiry are written by TASK-089's launcher.end, with the stored reads' removal; the third, the gone
  session's record at the next start (specification 5 :125), with its listing of gone sessions through
  writer.read_sessions, is written by TASK-090's launcher.start before the expiry (decision D-2956);
- the check that HEAD is the base branch's tip, and check 0 of the contract (specification 5 :121; specification 7
  :49); AIEOS_BASE is the head_commit read once;
- launching with a runtime, the owner's act, is not before this item's open points are closed: the base-tip check,
  check 0 and max_risk; this is a statement, not a lock;
- max_risk is the caller's: a caller passing a non-null max_risk declares the runtime's tier, which only the owner's
  measurement can back (C6, P-LOC); the self-build passes null until then, so the launcher never grants (decision
  D-2673 ruling 2);
- closed: a stand-in start giving a non-list truthy findings value would raise past the launcher's step guard; end's
  own findings handling was fixed in TASK-089, and start's two places by TASK-090, which keep only a list's or a
  tuple's str items (DEF-0102, decision D-2956).

## Why deferred
D-2681 Q1: the three record call places and the stored reads' removal were planned as one task after TASK-086, split
by decision D-2771 into TASK-089 (end's two call places and the removal) and TASK-090 (the next start's record); Q3:
max_risk stays the caller's until a tier is measured.

## Resume when
The record's three call places are closed by TASK-089 and TASK-090 (decisions D-2876, D-2956); this item closes when
the base-tip check and check 0 are met or moved by their own decision; max_risk stays the caller's, as its bullet
states.

## Depends on
TASK-086 (the launcher), TASK-089 (end's record and the stored reads' removal), TASK-064 (read_set_record, the
record's core side; read_set_record.py :1), TASK-066 to TASK-068 (the read hook that writes the reads; DEF-0097 :14),
TASK-051 (adapter); specification 5 section 11 points 7 and 10, specification 7 section 5.

## Log
- 2026-10-24: opened with TASK-086's records (session 3797498a; decisions D-2681, D-2758).
- 2026-10-25: TASK-089 accepted (decision D-2876): end writes the record at two of the three call places and removes
  the stored reads; the next start's record and the launch line now name TASK-090 (session 3797498a; decisions D-2771,
  D-2876).
- 2026-10-25: TASK-090 accepted (decision D-2956): start writes the gone sessions' records at the next start and
  removes their stored reads; start's findings handling closed; the launch line now names the base-tip check, check 0
  and max_risk (session ea6ea0a3; decisions D-2910, D-2953, D-2956).
