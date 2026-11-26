# DEF-0158: the product's controls against deferred-work growth

- Status: open
- Opened: 2026-11-27 (session 228f426b; D-7444)
- Deferred by: decision agent D-7444 (the order: after TASK-164 and the second real run); the requirement is the owner's (DM A83), quoted: "Không, vào bản đầu" (session 228f426b, transcript :37288)
- Decision group: A for the content and design under A51 and the specifications (docs/specs is risk rule R6); B for a concept erratum
- Blocks v0.1: yes (the owner's answer puts it in the first release, DM A83)
- Scheduled in: M8, the deferred-work controls task, its specification revision first, after TASK-164 and the second real run

## What

The owner's requirement and answer (DM A83): the product must have controls against deferred-work growth, and they are part of v0.1. At main 8fc9c16f a search of AIEOS-concept.md for deferred, backlog, technical debt and the Vietnamese word for put off found only line 999 (a feature put off); the hits in docs/specs are the records folder docs/Deferred and single deferred features. Other wordings are not excluded. No concept erratum is made; whether a concept erratum lists this item is the owner's, asked at the M8 exit review at the latest (DM A83).

## Options (Claude's proposal, not a design)

1. A deferred item is a record of the core in the event log: what, the event that makes it due, the task or milestone that resolves it, whether it blocks the release, state.
2. Intake: an item is accepted only with those fields; a finding may instead be recorded as an accepted limit of its task, counted and listed.
3. Touch: when a task's write set meets a path an open item names, the core puts the item into the Work Order and asks for its state at acceptance.
4. Closing needs evidence bound to a commit; an agent's claim does not close an item.
5. Flow limit: a configurable limit on the rise of open items over a batch of accepted tasks, with a default.
6. Release gate: no release is reported done while a blocking item is open.
7. `aieos status` shows opened, closed, open and blocking.

## Why deferred

The specification does not exist, and TASK-164 and the second real run, which are on the path of the v0.1 exit criterion, come first; the self-build uses the rule of master plan section 6 point (6) before the design is fixed.

## Resume when

The second real run is closed.

## Depends on

DM A83; master plan section 6 point (6) (revision 10); TASK-164.

## Log

- 2026-11-27: opened (session 228f426b; D-7443, D-7444).
