# DEF-0067: the review findings and limits carried from TASK-052 (the violation path)

- Status: open
- Opened: 2026-10-16 (decision D-1010)
- Deferred by: decision agent (A41), D-1010 (TASK-052's acceptance), with the dispositions D1 and D3 to D16 of D-1009.
- Decision group: A (limits of an accepted task, carried for later tasks).

## What
- **The contract's AC8 limits:** a STOP: violation did not make acceptance reject (evaluation.py passed the governor only record.added payloads; TASK-053 takes this on); violation.record called only by adapter.violation, and that only by replay and the tests, until that later task is accepted (E4 of D-1000); no task.* event follows STOP: violation, so the task stays READY with no lease and the next Resume Check may CONTINUE again; no bound on repeated STOP: violation (specification 5 §11 point 12); a fence refusal's record labelled refused_submission (eventlog.py); F-a kept; a passing replay with a violation shows no hook observing anything (C6 unmeasured); no observed read-set call; a run against the real writer's files not tested.
- **Readings** (D-1003): c1, a replay with a violation and no granted lease gives "violation" and still calls end; c2, adapter.violation's decision from record's appended and duplicate lists; c3, the fence result names the writer's refusal record's result.
- **D11, the quotation** (D-1009, D-1010): violation.py lines 5 to 7 quote specification 3 line 106 in quotation marks, abridged (stopping after "the lease is released") and altered (the section sign written "section", the backticks dropped), not marked so in the code; the next task that touches violation.py marks it "(abridged, not verbatim)" or paraphrases it.
- **Test gaps:** D3 (a repeat of a completed call with a stale token, "done" with nothing appended, has no named test); D5 (N1: test_replay R10's first case keeps a submission); D6 (N2, widened: a refused WriteResult other than the fence at either append, and a fence refusal at the decision append, untested); D7 (N3: the property test varies only the event_id); D8 (the end-to-end replay does not assert end's "none" nor record's released); D9 (reading c1 has no test); D10 (the stale token covered only by a foreign token with a higher counter); D12 (R6Adapter's "calls record once" not asserted); D15 (no case for a non-UTC offset, a token with an extra key or a negative counter); D16 (a weak assertIn of record.added).
- **Readings and limits:** D3 (a caller must read "done" with an empty appended list as "not a fresh stop"); D4 (str and dict subclasses pass the argument check; the writer re-checks the form and the fence); D13 (reads of the writer's result outside a try, unreachable with the real writer); D14 (replay.py says "task TASK-051" for limits TASK-052 shares); D1 (NO_ERROR_RELEASE would become a B105 candidate if renamed to a token-like name).

## Resume when
- A hardening task after M5's violation path (as TASK-046 after the ports), or any task that touches violation.py, adapter.py or replay.py (D11 first).

## Log
- 2026-10-16: opened (D-1010).
- 2026-10-30: TASK-102 (accepted by decision D-3707 at f25b4576; range fb90baaf..f25b4576; records d3a328bd; the map is docs/records/TASK-102.jsonl :44): settled D3's test gap (tests/unit/test_violation.py:251), D5, D8, D16 (tests/unit/test_replay.py:433, :456-458, :496), D10 (test_violation.py:286), D12 (:330), D15 (:122), D14 (src/aieos_bootstrap/replay.py:56-60); D11 was done earlier; open D6, D7, D9 and, with no change shown, the AC8 limits, readings c1 to c3, D3's reading, D1, D4 and D13 (the map's "settled except D6, D7, D9" takes these in too). Status stays open.
