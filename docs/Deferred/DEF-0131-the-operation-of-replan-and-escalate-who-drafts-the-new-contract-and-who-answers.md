# DEF-0131: the operation of REPLAN and ESCALATE: who drafts the new contract version, who answers an escalation, and with what notice

- Status: open
- Opened: 2026-11-06 (../History/2026-11/2026-11-06-1701-m8-stage-8-the-decision-files-d5198-to-d5236-and-the-coverage-map-ce14b08a.md)
- Deferred by: decision agent (A41, A51), D-5246 (the gaps of the coverage map, D-5245)
- Decision group: A (self-build)
- Blocks v0.1: no (in v0.1 each session needs a launch and no session starts the next one, specification 7 line 51, so a task left blocked by ESCALATE or stopped waits for the next launch, which fails safe; the decisions themselves, concept line 943, are built)
- Scheduled in: M8

## What
The Resume Check's decisions and their state effects are built: REPLAN gives one `task.stale`, and `task.replanned` "is appended later, when a new contract version is drafted; the Resume Check does not append it"; ESCALATE gives `task.blocked` with reason `escalate`, "unblocked only through an authority record that answers the escalation" (specification 3 section 10, lines 149 and 151). Not built or not settled: who drafts the new contract version after a REPLAN and appends `task.replanned`; who answers an escalation and how the person is told (a notice); what a session does after STOP or ESCALATE. The concept's loop (concept section 5.1, lines 255-258) shows CONTINUE, REPLAN and STOP/ESCALATE returning to the start of the loop.

## Why deferred
The coverage map (decisions D-5244 and D-5245) found the decisions built and the operation open; nothing in DEF-0059, DEF-0030 or the milestone reviews covers the drafting step or the notice. It needs a launched session to try, which is an owner act (A51 item (4)).

## Resume when
After the first real run (master-plan section 7) has shown how a REPLAN or an ESCALATE arises in practice, or when a task touches `launcher.py` or `execution.py` for this.

## Depends on
DEF-0059 (the limits of the execution path; its resume-when, the first caller of `execute`, has occurred); DEF-0030 point (i) (the READY to STALE difference, specification 3 line 156).

## Log
- 2026-11-06: opened (session ce14b08a; decisions D-5245, D-5246).
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass F batch 3, decision D-5269): read in full; fields as written at opening (Blocks v0.1: no; Scheduled in: M8); the Resume-when event (after the first real run, or when a task touches launcher.py or execution.py for this) is not met: no first real run yet, and launcher.py was changed by TASK-115, 117 and 118 not for this. State: open; Blocks v0.1: no (in v0.1 each session needs a launch and no session starts the next one, specification 7 line 51, so a task left blocked by ESCALATE or stopped waits for the next launch, which fails safe; the decisions themselves, concept line 943, are built); Scheduled in: M8.
