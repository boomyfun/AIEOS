# Specification 1: State & Event Model

> - **Status:** revision 2. Whether it is approved and baselined is recorded in DM section F, not in this file. It decides nothing that a decision matrix (DM) row or a bound document decides.
> - **Drafted under:** decision agent decision D-146 (the M1 drafting plan, item 1; Master Plan §4 M1). Decision files are kept outside the repository (`docs/WORKING-RECORDS.md`).
> - **Path:** `docs/specs/spec-01-state-and-event-model.md` is interim, like `docs/plan/`. The layout (DM B7, proposed) and CR-001 E4 (working record DEF-0018) are open; specification 2 proposes them.
> - **Sources:** "concept line N" is a line of `AIEOS-concept.md` (v0.5, unchanged, A22). "DM B5" is a row of `docs/pre-genesis/decision-matrix.md`. Statuses are those the DM rows record: B3, B5, B7 and B9 are rows of DM section B, "Proposed architecture (not ratified)"; `governor-spec.md` revision 3 is approved in the owner's place (DM F3) and keeps its own "proposed" marks. "(proposed)" in this text marks a choice of this specification where the concept is silent or says less; each one is also listed in section 10.

## 1. Purpose and scope

- This is the first of the seven technical specifications of concept §18 (line 991): "Schema các thực thể, danh sách event, projection, recovery, fencing".
- It defines what AIEOS keeps as state, which entities exist, which events change them, how derived views are rebuilt, and how the state recovers from crashes and stale writers.
- Not in scope: the file syntax of any entity (specification 2, line 992); the Resume Check algorithm and the execution decision table (specification 3, line 993); evidence profiles and gates (specification 4, line 994); adapters, the MCP tools and the CLI (specifications 5 to 7). Where this text names a field, specification 2 fixes its spelling and type.

## 2. Two kinds of state, three trust classes

- **Project State** is long-lived and authoritative: intent, the constitution, accepted changes, current evidence and architecture reality. **Execution State** is temporary and recoverable: sessions, leases, task progress, checkpoints, retry counters and runtime telemetry (concept §13.1, lines 827-836). Losing Project State is not acceptable; losing Execution State is: it is recovered or redone (line 834).
- Every stored item belongs to one trust class (concept §13.2, lines 838-849):
  - **authoritative:** code in Git, intent and constitution files, the event log; never lost;
  - **derived:** projections, the traceability index, the impact graph, derived read-sets; rebuilt from authoritative items;
  - **ephemeral:** leases, sessions, telemetry, unsubmitted checkpoints; dropped or redone.
- When they disagree (concept lines 845-849): on what changed in code, Git wins and the event log is patched from commit trailers `AIEOS-Task:`; between intent files and a projection, the file wins and the projection is rebuilt; a lease that has expired has expired, whatever its holder believes (section 8).

## 3. Entities

| Entity | Trust class | Kept in | Identity and version |
|---|---|---|---|
| Intent artefact: requirement, specification, architecture, ADR, convention (concept §6.2, lines 401-409) | authoritative | Git, as files (format: specification 2) | an id and a version (line 409); a specification also has a lifecycle status, draft → baselined → superseded (B9, proposed); a change is an INTENT_CHANGE (section 5.3) |
| Change request (concept line 409) | authoritative | Git, as a file (proposed) | an id; intent changes only through an approved change request (line 409) |
| Constitution (concept §6.1) | authoritative | Git, as a file | its version; articles keep their ids |
| Policy: risk rules, autonomy, adapters (concept line 868) | authoritative | Git, as a file | its version; the governor reads the policy version and the level version in force (A35; `governor-spec.md` §3.2) |
| Task contract (concept §7.1, lines 425-484) | authoritative | Git, as a file | a task id and the content hash of the contract (A42) |
| Task state | derived | projection of the event log, with IN_PROGRESS read from the local store (sections 5.1 and 6) | the task id |
| Record (B5: claim, observation, interpretation, authority) | authoritative | the event log | an idempotent record id (concept line 856); fields as `governor-spec.md` §3.3. Evidence items, gate results and verification runs are `observation` records; approvals are `authority` records (B5) |
| Acceptance decision (A15; concept §5.3, lines 273-311) | authoritative | the event log, as an `interpretation` record (B5) | its record id; fields as `governor-spec.md` §6.1 |
| Execution decision (A15; concept §5.3) | authoritative | the event log | its record id; its record type is open (section 10): B5 names only the acceptance decision |
| Handoff (concept §7.5: done, not_done, assumptions, discoveries, risks, proposals) | authoritative | Git, as a file | the task id and session |
| Proposal: a discovery or proposal of a handoff (concept line 537) | authoritative | the event log, as a `claim` record in a queue (proposed) | its record id; it becomes a fact only when approved (line 537) |
| Commit | authoritative | Git | the commit id; its trailer names the task and, proposed, the fencing token (section 8) |
| Lease | ephemeral | local store, not committed (concept line 876); not in the event log (section 5.2) | task id, holder, fencing token, expiry |
| Session | ephemeral | local store | a session id; never a source of Project State |
| Checkpoint not yet submitted, runtime telemetry (concept lines 833, 844) | ephemeral | local store | dropped or redone (line 844) |

- A record carries `fact_kind`, `source_class` (B3) and `recorder` as separate fields (B5); an agent's claim is a `claim` from `agent_declared`, valid only as an observation that the claim was made (B5).
- Projections and indexes are not entities of their own: they are views over the entities above (section 6). The retry counter is one of them (section 5.1).

## 4. The event log

- One append-only log of events for the project (concept line 874, "append-only event log"; its file name and place are specification 2's).
- Every event has an envelope with: an idempotent `event_id`; a `type` (section 5); the UTC time it was appended; a per-log sequence number assigned by the writer; the `task_id` where the event concerns a task; the `fencing_token` where the event results from a lease holder's action; for a correction, `corrects`, the `event_id` it corrects (proposed); and a payload. Events that carry a record also carry the record's B5 fields.
- Appending an event whose `event_id` is already in the log has no effect (concept line 856).
- Only the AIEOS core writes the project-state directory (`.aieos/` in the concept, lines 858 and 879; its layout is open: B7, E4), the event log included, through one writer (constitution INV-004). Agents act through the protocol (specification 6) or the CLI (specification 7), never by writing that directory.
- Events are never edited or removed. A correction is a new event whose `corrects` names the one it corrects.

## 5. Event list

The names are proposed; specification 2 fixes their spelling. Each event names the state change it causes, if any. One fact is appended by one event only.

### 5.1 Task lifecycle (concept §7.4, lines 518-531)

Task progress is Execution State (line 833), and leases are kept in the local store, not committed (line 876; section 5.2). So the event log records the task states that Project State needs, and IN_PROGRESS is read from the local store: a task that the log has in READY or REWORK is IN_PROGRESS while the local store holds an unexpired lease on it (proposed). When the lease is released or expires, or the local store is lost, the task is back in READY or REWORK without any event, so that it can be leased again (line 857), and its work is redone (line 834); a session that crashes or is killed (line 836) ends this way.

| Event | Effect on the task state |
|---|---|
| `task.drafted` | → DRAFT |
| `task.approved` | DRAFT → READY; only when every dependency is DONE (concept line 543) |
| `task.blocked`, `task.unblocked` | READY or REWORK → BLOCKED, and BLOCKED → READY (lines 521-523, whose diagram shows IN_PROGRESS → BLOCKED → READY); a lease on the task is released first (proposed) |
| `task.submitted` | READY or REWORK while leased, that is IN_PROGRESS, → VERIFYING; carries the commit id and the fencing token; appended only as section 8 allows; the lease is released (proposed) |
| `decision.acceptance` | appends the governor's decision record (section 5.4) and moves the task to the record's next state (`governor-spec.md` §5). From VERIFYING: ACCEPTED (ACCEPT); IN_REVIEW (NEEDS_REVIEW, or INSUFFICIENT_EVIDENCE when only human-only evidence types are missing: CR-001 E8); REWORK (NEEDS_REWORK, or INSUFFICIENT_EVIDENCE otherwise); ESCALATED instead of REWORK once the retries the contract allows are used up; REJECTED (REJECT). From IN_REVIEW, on re-evaluation when a record of the task is added (`governor-spec.md` §5, "Leaving IN_REVIEW"): the same next states, ACCEPTED only through an approval that counts and that the decision record cites; a decision that keeps the task IN_REVIEW changes nothing |
| `task.done` | ACCEPTED → DONE |
| `task.stale` | IN_PROGRESS, BLOCKED, VERIFYING, IN_REVIEW, REWORK or ACCEPTED → STALE, on INTENT_CHANGE or an interface-breaking CONFLICT (line 529, "từ bất kỳ trạng thái sau READY"; this list is a proposed reading, section 10); also READY → STALE, only when the Resume Check gives REPLAN on a READY task, since it runs at the step from READY to IN_PROGRESS (specification 3 §1; set by this revision, as specification 3 §12 point 6 proposes; proposed); the lease of a task in IN_PROGRESS is released |
| `task.replanned` | STALE → DRAFT, a new contract version (proposed reading of "STALE ─► REPLAN", line 529) |

- The retry counter is Execution State (line 833). It is derived from the log (proposed): the number of the task's `decision.acceptance` events that sent it to REWORK since its contract was last approved (`task.approved`), so that a rework is counted also when the task was blocked and unblocked before it was submitted again. The governor reads the count and compares it with the contract's retries budget (line 463; `governor-spec.md` §5, which leaves the counting outside the governor).
- `decision.execution` appends an execution decision (CONTINUE, CONTINUE_WITH, REPLAN, the three STOPs, BLOCKED, ESCALATE; A15). Which task state each outcome causes, for example BLOCKED through `task.blocked`, is specification 3's (line 993), and its section 10 settles it with this section's events only and no new state. The execution decision and the acceptance decision are never merged (concept lines 275-278; A15).

### 5.2 Leases and sessions

- Leases and sessions are kept in the local store, not committed (concept line 876), and are not events of the log. The local store grants, releases and expires leases. A lease is exclusive on the task and its write-set (line 541): one lease per task at a time, granted only on a task in READY or REWORK (proposed); how tasks whose write-sets overlap are kept apart (not run in parallel, or each in its own worktree and merged in order, line 541) is specification 3's.
- They are Execution State (line 833): if the local store is lost, every lease is gone, leased tasks are back in READY or REWORK, and their work is redone (line 834); no Project State is lost. Fencing stays safe because a new store never hands out an old token (section 8).

### 5.3 Reconciliation (concept §5.2, lines 261-271)

| Event | Meaning (concept) | Effect |
|---|---|---|
| `intent.changed` | INTENT_CHANGE: intent changed by an approved change request | impact analysis; dependent artefacts and tasks → STALE (line 267); for tasks, `task.stale` |
| `drift.detected` | DRIFT: reality differs from intent, side unknown | no state change; the classification and the proposal (fix the code or fix the intent) are `claim` records, and the human's choice is an `authority` record (line 268; the record kinds are proposed) |
| `violation.detected` | VIOLATION: a known policy is broken | an `observation` record (proposed), counted in the metric of the runtime and of the agent (line 269); the session stops; the change is rejected: `governor-spec.md` §5 row 1 gives REJECT, and whether that holds for every such change is open there (§11 point 5) |
| `evidence.stale` | STALE_EVIDENCE: evidence no longer matches the commit or intent version | re-verify is scheduled; execution is not blocked; a DONE task stays DONE with stale evidence |
| `conflict.detected` | CONFLICT: two lines of work collide | CONTINUE_WITH or REPLAN (specification 3) |

### 5.4 Records

- `record.added` appends one record (B5) other than an acceptance decision: claims, observations (evidence items, gate results, verification runs) and authority records, such as approvals, one per task, bound to the contract hash (A42). It changes no task state. When the record concerns a task in IN_REVIEW, the governor re-evaluates the task (`governor-spec.md` §5), and only the resulting `decision.acceptance` can change its state.
- `decision.acceptance` appends the governor's decision record, an `interpretation` record (B5; `governor-spec.md` §6.1). No record is appended twice under two event types.

## 6. Projections

- A projection is a derived view computed by replaying the event log in sequence order (concept §13.2). The same log always gives the same projection.
- The projections v0.1 needs: the state of each task (section 5.1; IN_PROGRESS is read from the local store); the records of each task, by evidence type and dimension, which the governor reads; the retry counter (section 5.1); and the traceability index from tasks to intent artefacts.
- A damaged or missing projection is deleted and rebuilt by replay (concept line 859). No projection is ever a source for another authoritative item.

## 7. Recovery

At start, before any new event, the core reconciles Git and the event log (concept line 855), in this order:
1. For every commit whose trailer names a task and that no `task.submitted` event names: if the trailer's fencing token is that of a lease on that task which the local store still holds (this step runs before step 5), the core appends a compensating `task.submitted` event that says it is compensating, and the task goes to VERIFYING (line 855). Otherwise, also when the local store was lost, it records an `observation` of an unfenced write, and the task state is unchanged (line 857; proposed). Either way the commit stands as the fact of what changed in code (line 847). The commit's own date is not used (proposed).
2. Where Git and the log disagree on what changed in code, Git wins (concept line 847).
3. Where an intent file and a projection disagree, the file wins and the projection is rebuilt (concept line 848).
4. Duplicate `event_id`s are ignored (concept line 856).
5. Leases whose expiry has passed are expired in the local store.

## 8. Fencing

- Each lease grant increases a number that only increases, and the lease carries it as its fencing token (concept line 857). Proposed: the number is a counter that the local store increases by one at each grant, and the token pairs it with the store's epoch, a new random id each time the store is created; so a lost store can never hand out a token again, and the log needs no lease events.
- Every submission carries the token of the lease it was made under, and so does the commit's trailer (proposed; spelling: specification 2). The core refuses a submission whose token is not that of the lease the local store holds on the task, or whose lease has passed its expiry time even if the store has not yet expired it (line 849). The refusal is recorded as an `observation`, and the submission changes nothing.
- An expired lease is expired, whatever its holder believes (concept line 849).

## 9. Before AIEOS governs its own build

- Records written before AIEOS governs its own build carry their recorder and are not authoritative (CR-001 E3; constitution INV-004). Master Plan §5 point 4 applies this to the bootstrap; that point is a reading, not bound text (Master Plan §5, last point).
- The rule of B5 applies to them meanwhile: "a locally written record counts at most as a claim unless it can be re-derived from Git or re-fetched from an external channel".
- Where the governor's records are kept until the event log of milestone M3 exists, and how they move into it, are open (Master Plan §4 M2 and §10).

## 10. Open points

1. The spelling of event names and fields (specification 2).
2. The file name and place of the event log and of the local store (specification 2; B7 and E4 open).
3. Whether the log carries a hash chain between events. The concept does not ask for one; not proposed here.
4. How long ephemeral items are kept.
5. The M2 record store and its move into the event log (Master Plan §10).
6. A commit found at recovery whose lease the local store no longer holds, for example after the store was lost: recorded as an unfenced write, not as a submission (section 7); whether its work can be submitted again under a new lease.
7. Settled by specification 3 §10 (proposed there): the task state each execution decision causes (section 5.1).
8. Whether DONE, REJECTED and ESCALATED are among the states "sau READY" that INTENT_CHANGE or CONFLICT makes STALE (line 529); STALE → DRAFT as the reading of REPLAN; READY or REWORK → BLOCKED. READY → STALE for the Resume Check's REPLAN only is set by this revision (section 5.1; proposed, as specification 3 §12 point 6 proposes).
9. Settled by specification 3 §9 (proposed there): an execution decision is an `interpretation` record, the kind B5 gives an acceptance decision.
10. The other choices marked "(proposed)": IN_PROGRESS read from the local store, and what release, expiry and a lost store do (sections 5.1 and 5.2); one lease per task, only on READY or REWORK; releasing a lease on submission, blocking or staleness; the retry counter; the token's form, the token in the commit trailer, its use at recovery and the expiry check at submission (sections 7 and 8); the `corrects` field (section 4); where change requests and proposals are kept (section 3); the record kinds of DRIFT and VIOLATION (section 5.3); READY → STALE for the Resume Check's REPLAN (section 5.1; revision 2).

## 11. Revisions

- Revision 0: first draft (D-146).
- Revision 1: applies the fourteen findings of one read-only checker round (claude-sonnet-5-5), each verified against its source lines: acceptance routing as CR-001 E8 and `governor-spec.md` §5 give it, including leaving IN_REVIEW and ESCALATED; one event per fact; leases kept in the local store only, as concept line 876 says, with IN_PROGRESS read from it, and what release, expiry, rework and blocking do; fencing at recovery and at submission, with a token a lost store cannot repeat; the entities that were missing; the reconciliation effects; the single writer for the whole directory; proposed choices marked and listed in section 10; section 9 aligned with the Master Plan's open points.
- Revision 2 (decisions D-254 and D-255; DEF-0025): records what specification 3 settles and uses: `task.stale` from READY for the Resume Check's REPLAN, set by this revision as specification 3 §12 point 6 proposes (section 5.1; section 10 point 8 narrowed, and the choice listed in point 10), and section 10 points 7 and 9 settled by specification 3 §10 and §9.
