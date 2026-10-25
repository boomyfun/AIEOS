# DEF-0104: end_outside's two edge limits

- Status: open
- Opened: 2026-10-25 (session ea6ea0a3; TASK-092's records, decision D-3076)
- Deferred by: decision agent (A41, A51), D-3076 (found by TASK-092's acceptance review t92x-S1, findings F1 and
  F2, both non-blocking).
- Decision group: A (a later task that changes launcher.end_outside, within the self-build).

## What
At TASK-092's task head 5f01bb60, launcher.end_outside has two limits that no contract rule forbids:
- F1: a raise after writer.end_session has returned (an answer whose attribute access raises, read by getattr in
  step 4 or in _outside_store) falls to the outer except and gives reason "end" with "end: a step raised <type>",
  without "; the session may be ended", although leases may have been released. The contract names "may be ended"
  only for a raise in end_session itself.
- F2: _outside_store puts the callee's result and reason, by %r, into an own finding, so a callee whose reason held
  the root would put it into an own finding, against "end_outside's own findings never name the root". The writer's
  reasons are fixed words (writer.py :395-397 and the reads' fixed reasons), so no failure is known with the real
  callees.

## Why deferred
D-3076: neither breaks a contract rule; a code commit of its own (X1) would cost a full review cycle for two edge
cases that the real writer does not reach.

## Resume when
At the next task that changes end_outside or _outside_store; this item closes when a raise after end_session's
return also says the session may be ended, and own findings quote no callee text, each with a test.

## Depends on
TASK-092 (end_outside), TASK-089 (_store_findings' form).

## Log
- 2026-10-25: opened with TASK-092's records (session ea6ea0a3; decision D-3076).
