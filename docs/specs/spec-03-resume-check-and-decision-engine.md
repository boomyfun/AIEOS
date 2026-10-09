# Specification 3: Resume Check & Decision Engine

> - **Status:** revision 4, a draft until approved. Whether it is approved and baselined is recorded in DM section F, not in this file. It decides nothing that a decision matrix (DM) row or a bound document decides.
> - **Drafted under:** decision agent decision D-243 (the drafting plan for specification 3, approved with its condition C2; Master Plan §4 M3). Decision files are kept outside the repository (`docs/WORKING-RECORDS.md`).
> - **Path:** `docs/specs/spec-03-resume-check-and-decision-engine.md` is interim, like specifications 1 and 2: the layout is settled (DM F16), but files move only when a core writes the project-state directory (spec 2 §10 point 2).
> - **Sources:** "concept line N" is a line of `AIEOS-concept.md` (v0.5, unchanged, A22). "DM A15" is a row of `docs/pre-genesis/decision-matrix.md`. "Spec 1" and "spec 2" are `docs/specs/spec-01-state-and-event-model.md` and `docs/specs/spec-02-aieos-file-format.md`; "the risk rules" is `docs/specs/risk-rules-gov-aieos.md`. "(proposed)" marks a choice of this specification where the concept is silent or says less; each one is also listed in section 12.

This is the third of the seven technical specifications of concept §18 (line 993): "Thuật toán 8 kiểm tra, tính `Δ`, phát hiện thay đổi chữ ký interface, bảng quyết định". It defines when the Resume Check runs and what it reads, its eight checks, how they combine into one execution decision, the decisions taken while a session runs, the record of an execution decision, and the task state each decision causes. Its limits are in section 11.

## 1. When the Resume Check runs and what it reads

- The Resume Check runs before a Work Order is issued (concept lines 485-489), at the start of every session (line 487, "một session mới"; line 535): before the local store grants a lease on a task in READY or REWORK (spec 1 §5.2), and again at the start of each new session on a task that stays IN_PROGRESS under a lease it still holds. On IN_PROGRESS, any decision other than CONTINUE or CONTINUE_WITH releases the lease (proposed). A lease is granted under the HEAD its decision records; a later move of HEAD is seen by the next session's Resume Check (proposed). It is deterministic, cheap and always run (line 489): the same inputs give the same decision; it calls no model (constitution INV-001; concept line 162) and reads only the inputs below (proposed); no earlier result is reused (proposed).
- Only CONTINUE and CONTINUE_WITH let the lease be granted and the Context Compiler run (line 506). Every other decision grants no lease.
- When a writer's commit reaches the base branch, a task whose effective read-set meets it is checked again before its next lease (line 542). v0.1 runs one task at a time (line 951), so no other task holds a lease meanwhile; the rule needs nothing beyond running the Resume Check at every lease.
- Its inputs:

| Input | Source |
|---|---|
| The task contract: `input_state.base_commit`, `input_state.depends_on`, `input_state.intent_versions`, `write_set`, `read_set`, `constitution`, `task_type`, `risk`, `autonomy.budgets`; its `contract_hash` | the contract file at HEAD (spec 2 §5.1, §2) |
| HEAD | the tip of the base branch on which the task's work lands, never the task's own branch (proposed) |
| The commits of `base_commit..HEAD`, their parents and changed paths, and the file contents at `base_commit` and HEAD | Git |
| The task's `task.approved` and `task.submitted` events | the event log (spec 2 §6.3) |
| The architecture entities: components and interfaces | their files at HEAD (spec 2 §4.2) |
| The observed read-set | the runtime's records of the task's earlier sessions (section 4; specification 5) |
| The base branch's name and the module roots of section 4 | the project's declaration; spec 2 §7 has no key for them yet (section 12); for the self-build the base branch is `main` when the project declares none (proposed); module roots that are not declared leave imports `unresolved` (section 4) |
| The current version of each intent artefact | its file at HEAD (spec 1 §3) |
| The state of each task in `depends_on` | the projection of the event log (spec 1 §6) |
| The constitution's articles and their latest check results | the constitution at HEAD (spec 2 §4.1) and its check records (spec 2 §6.2) |
| The runtime's `max_risk` | the adapter declaration of the runtime that would take the lease (concept lines 636-645; its form is specification 5's) |
| The policy's risk rules | the policy at the base or a pinned ref (the risk rules §2 point 3) |
| Budget use: retries | the retry counter (spec 1 §5.1) |
| Budget use: tokens, wall time, human attention | Execution State: runtime telemetry (spec 1 §2), as the runtime reports it |

## 2. The eight checks

A precondition comes first, as DM A15 allows ("A precondition layer ("check 0") may exist without changing §5.3 semantics"): the contract file at HEAD must have the `contract_hash` that the task's latest `task.approved` event carries (spec 2 §6.3); otherwise the Resume Check gives no decision value (section 7) (proposed). Then the eight checks run in the concept's order (lines 493-502). Each ends as `passed`, `fired` (with its outcome), `skipped` or `not_run`; every result is kept in the decision record (section 9).

| # | Check | Rule | When it fires |
|---|---|---|---|
| 1 | Base freshness (line 495) | Compare `base_commit` with HEAD. Equal: checks 2 and 3 are `skipped`. Different: compute `Δ`, the union of the paths that each commit of `base_commit..HEAD` changes against its first parent, leaving out only the commits that a `task.submitted` event of this task names (a trailer alone is not enough, since any writer can write one), without rename detection, so a renamed file counts under its old and its new path, as the risk rules §2 point 5 counts it (proposed) | ESCALATE when `base_commit` is not a commit of the repository or not an ancestor of HEAD; checks 2 and 3 are then `not_run` (proposed) |
| 2 | Write-set conflict (line 496) | `Δ ∩ write-set` (section 3) | not empty: STOP: scope invalid (section 6) |
| 3 | Read-set freshness (line 497) | `Δ ∩ effective read-set` (sections 3 and 4) | not empty and every met entry non-breaking: CONTINUE_WITH; not empty and any met entry breaking (section 5): REPLAN |
| 4 | Intent freshness (line 498) | each entry of `intent_versions` against the artefact's current version | any version differs, or the artefact is missing at HEAD: REPLAN |
| 5 | Dependency freshness (line 499) | each task of `depends_on` is DONE and not STALE | any is not DONE, or is STALE, or is unknown to the log: BLOCKED. A DONE task with stale evidence stays DONE (lines 504, 530) and passes |
| 6 | Constitution (line 500) | the articles that apply to the task: those whose `scope` meets `write-set ∪ effective read-set` (the task-time set, line 393; "meets" as section 3 defines it for two patterns, a `scope.components` entry standing for its component's paths, an article with no `scope` being project-wide and not in the task-time set (spec 2 §4.1), and an article whose scope cannot be evaluated counting as applicable) and whose `applicability`, if present, names the task's `task_type` (spec 2 §4.1), with the articles the contract lists | an applicable article has an `observation` record of its check bound to HEAD whose `refers_to` is the article's id (proposed; a widening of spec 2 §6.2's `refers_to`), with outcome `fail`, or `blocking` with `blocking_kind` `constitution`: ESCALATE. An applicable article with no result at HEAD is not a reason to stop (line 280) and is listed as uncovered (proposed) |
| 7 | Runtime (line 501) | the runtime's `max_risk` against the task's risk: the higher of the contract's `risk` and the highest class of every risk rule whose pattern meets a `write_set.paths` pattern, "meets" as section 3 defines it for two patterns, so that files the task will create count; a rule that cannot be evaluated meets every pattern it could cover (the risk rules §2 point 3) (proposed) | `max_risk` lower, or no declaration for the runtime: STOP: runtime insufficient. A write-set pattern that no risk rule meets (the risk rules §2 point 2): ESCALATE (proposed) |
| 8 | Budget (line 502) | each budget of `autonomy.budgets` against its use | retries used up: the count of spec 1 §5.1 over the contract's retries limit ("Retry quá giới hạn", line 293); the k-th decision that sends the task to REWORK opens its k-th retry, so a count equal to the limit still allows the last retry, and scenario RC-10's "the task's retries are used up" is a count over the limit; or a reported use over its budget, uses counted from the task's latest `task.approved`: ESCALATE. Spec 1 §5.1 sends a task to ESCALATED instead of REWORK once its retries are used up, so in the normal flow the governor stops the task first, and the retry branch is a fail-closed backstop for a log whose count is over the limit (section 12; `governor-spec.md` §5 leaves the counting outside the governor). A use the runtime does not report, or whose telemetry was lost with the local store, is not counted and is listed as uncovered (line 280; proposed) |

- Stale evidence is not a check (line 504): it belongs to acceptance, and never stops execution (line 280).
- Impact analysis after an intent change (line 498) is reconciliation's work (concept §10, line 734), not the Resume Check's; check 4 only finds that the version moved.

## 3. Path matching

- Paths and patterns follow the risk rules §2 point 6 exactly, so that every check matches a path as check 7's rules do (proposed).
- Two patterns meet when some path could match both. This is decided on the patterns alone, without listing files: compare them name by name from the root; `**` may stand for any number of names; two literal names must be equal; a name with `*` meets a literal name it matches and any other name with `*`; a pattern without `/` is first read as `**/` followed by it, as the risk rules read it. When this cannot decide, the patterns meet (fail closed; proposed).
- `Δ ∩ write-set` is the set of paths of `Δ` that a `write_set.paths` pattern matches.
- `Δ ∩ effective read-set` is the set of entries of the effective read-set (section 4) that `Δ` meets: a path entry when a path of `Δ` matches it; an interface entry when a path of `Δ` lies under the component it names (spec 2 §4.2: an interface is `{id, component}`, a component `{id, paths, tags}`), a component path with no wildcard that names a folder standing for `<it>/**` (proposed; the same reading for check 6's `scope.components`); a schema entry when a path of `Δ` matches the file it resolves to (section 5).

## 4. The effective read-set

The read-set comes from three sources (lines 475-483); the effective read-set is their union, and each entry keeps its sources.
- **Declared:** `read_set.paths`, `read_set.interfaces` and `read_set.schemas` of the contract (spec 2 §5.1; line 443).
- **Derived** (line 941, "read-set declared + derived"): a deterministic static analysis of the write-set's files as they are at `base_commit`. For the self-build, every Python file of the write-set that exists at `base_commit` is read with Python's own parser (standard library only, constitution INV-002), and every module it imports directly that resolves to a file of the repository, searched under the module roots the project names (for the self-build, `src/` and the repository root; proposed), is added as a path entry. Imports outside the repository are left out; imports that do not resolve, files that cannot be parsed and files of other languages add nothing and are listed in the record as `unresolved` or `unanalysed` (proposed: direct imports only, one level).
- **Observed:** the files the agent read in the task's earlier sessions, as a runtime of tier T3 or above records them (line 481); their capture is specification 5's.
- When the observed source is absent, as on runtimes T0 to T2, the record marks the effective read-set as an estimate (line 483).

## 5. Interface and schema signatures

A met entry is breaking or non-breaking (line 497):
- **An interface entry** (line 443): its signature is computed in each Python file of its component at `base_commit` and at HEAD. The symbol is the top-level class or function named by the interface's `id`. A function's signature is its name, its parameters (names, kinds, which have defaults, annotations), its return annotation and its decorators; a class's is its name, its bases and the signatures of its methods and class-level names that do not start with `_`. Each part is compared in one fixed form, the parser's dump of its syntax tree without positions, so that layout and comments never count, and the record names the interpreter's version (proposed). Equal at both commits: non-breaking. Different, or removed: breaking.
- **A schema entry** is a name, as in line 444 (`schemas: [reset_tokens]`): it resolves, at `base_commit` and at HEAD separately, to the one file whose name without its extension equals it, under the paths of the components the read-set's interfaces name and of the components whose paths meet the write-set or the read-set's paths (section 3) (proposed). A schema that resolves at both commits to the same single path is compared by its content. Its signature is that file's content hash (spec 2 §2), so any change is breaking (proposed: no schema format is parsed in v0.1).
- **A path entry**, declared or derived, has no signature in the concept (line 497 speaks of interfaces and schemas): its change is non-breaking and gives CONTINUE_WITH, and so does a removed path entry (proposed). What a task depends on as an interface or schema is declared as one.
- **Fail closed:** an interface whose component cannot be resolved, a symbol defined in no file or in more than one file of its component, a schema name that resolves to no file or to more than one, or a file that cannot be parsed at either commit gives a breaking verdict, never a non-breaking one. An unresolvable interface or schema entry counts as met whenever `Δ` is not empty (proposed).
- Each met entry's verdict and its reason are kept in the record (section 9).

## 6. Check 2's rebase branch

- The concept offers an alternative to STOP: scope invalid when a write-set conflict "tự giải được" (line 496): a rebase. This specification defers that branch; it does not drop it. Until a later revision defines a deterministic condition under which a rebase is safe, every non-empty `Δ ∩ write-set` gives STOP: scope invalid, the stricter outcome (proposed).
- The scenario set leaves the branch uncovered (`conformance-scenarios-initial.md` §6); a scenario for it is proposed in section 12, not added (scenarios change only by their own approval, CR-002 part 6).

## 7. The decision table

- Every check that applies runs, even after one has fired, so that the record shows every result (proposed). Checks 2 and 3 are `skipped` when HEAD equals `base_commit` and `not_run` when check 1 cannot compute `Δ`.
- The decision is one A15 value (DM A15; constitution INV-005). When more than one check fires, the outcome is the first fired outcome in this order (proposed; the concept gives no order): STOP: violation; STOP: scope invalid; STOP: runtime insufficient; ESCALATE; BLOCKED; REPLAN; CONTINUE_WITH. When none fires, CONTINUE. So no fired STOP, ESCALATE or BLOCKED is ever hidden behind a milder outcome, and every fired outcome is also listed in the record's `outcomes_fired`.
- Missing evidence is never a reason to stop execution (line 280): the Resume Check stops only on what a check finds, and lists what it could not see as `uncovered` (concept line 65).
- A Resume Check that cannot read an input it needs gives no decision value: its record carries `error`, `decision` is `null`, and no lease is granted (as `governor-spec.md` §4 rule 7 does for acceptance; proposed). The inputs whose absence or malformed form gives `error`: the contract and the check 0 precondition, Git (HEAD, `base_commit`'s lookup apart, which check 1 handles), the event log, the policy, the architecture entities, the constitution, a malformed base-branch declaration and a malformed adapter declaration. A runtime with no declaration gives STOP: runtime insufficient (check 7); an unreported budget use and an article with no result are uncovered (checks 6 and 8).
- Against the scenario set (`conformance-scenarios-initial.md` §4, with its Resume Check defaults); the scenarios name the declared read-set, so their fixtures keep the derived and observed sources from meeting `Δ`:

| Scenario | Given | The rule that gives the expected decision |
|---|---|---|
| RC-01 | defaults | check 1: HEAD equals `base_commit`, checks 2-3 skipped; checks 4-8 pass: CONTINUE |
| RC-02 | `Δ` meets neither set | checks 2 and 3 pass: CONTINUE |
| RC-03 | `Δ` meets the write-set; not self-resolving | check 2: STOP: scope invalid (section 6) |
| RC-04 | `Δ` meets the declared read-set; no signature changed | check 3, every met entry non-breaking: CONTINUE_WITH |
| RC-05 | as RC-04, an interface signature changed | check 3, a breaking entry: REPLAN |
| RC-06 | only a newer version of a spec in `intent_versions` | check 4: REPLAN; checks 2 and 3 pass |
| RC-07 | a dependency is STALE | check 5: BLOCKED |
| RC-08 | the current code violates an applicable article | check 6: ESCALATE |
| RC-09 | `max_risk` below the task's risk | check 7: STOP: runtime insufficient |
| RC-10 | retries used up | check 8: ESCALATE |
| RC-11 | a dependency DONE with stale evidence | check 5 passes (section 2): CONTINUE |

## 8. Decisions during the run

Execution decisions are also taken while a session runs (line 277):
- **STOP: violation** (line 291): when the runtime observes a write outside the write-set or another broken policy (scenario ADV-02). The core appends `violation.detected` (spec 1 §5.3) and a `decision.execution` with this value; the session stops and the lease is released; the change is rejected at acceptance (`governor-spec.md` §5 row 1, whose reach is open there, §11 point 5). Observing it needs a runtime of tier T3 or above (lines 649-652; specification 5); below T3 the G0 scope gate finds it after the fact (specification 4).
- **ESCALATE**: when the runtime reports that a budget of section 2 check 8 is used up while the session runs; the session stops, the lease is released, and section 10's effect follows (proposed).
- An intent change while a session runs is reconciliation's (`task.stale`, spec 1 §5.3); the next Resume Check gives REPLAN. No other decision is taken while a session runs in v0.1 (proposed).

## 9. The execution decision record

- It is the payload of `decision.execution` (spec 1 §5.1; spec 2 §6.3), the decision contract of spec 2 §6.4, which bootstrap and native write alike (A15).
- Its `fact_kind` is `interpretation`, the kind B5 gives an acceptance decision, "an `interpretation` record that cites the records it used"; this settles spec 1 §10 point 9 (proposed). Its `source_class` is the class of where it ran; its `recorder` is the core's identity; its `subject` is the task id.
- Its other keys (proposed names), which settle spec 2 §10 point 6:

| Key | Value |
|---|---|
| `decision` | one A15 value, or `null` exactly when `error` is present |
| `contract_hash`, `contract_version` | the contract checked (spec 2 §2) |
| `base_commit`, `head_commit` | the two commits compared, in full |
| `log_seq` | the sequence number of the last event of the log the check read (spec 2 §6.1) |
| `delta` | the paths of `Δ`, each with its change: added, modified or deleted |
| `checks` | eight entries `{check, status, outcome, detail}`, `status` one of `passed`, `fired`, `skipped`, `not_run` |
| `outcomes_fired` | every fired outcome, in the order of section 7 |
| `read_set` | the effective entries with their sources; `estimate`; `unresolved`; `unanalysed` |
| `signatures` | for each met entry: `{entry, kind, verdict, reason}`, `verdict` `breaking` or `non_breaking` |
| `intent_versions` | for each entry: the contract's version and the current one |
| `dependencies` | for each task of `depends_on`: its state |
| `constitution` | the applicable articles, those violated at HEAD, and those with no result |
| `runtime` | the adapter, its `max_risk` and the task's risk as section 2 check 7 computes it |
| `budgets` | for each budget: its limit, its use, and whether the use was reported |
| `policy_version` | the policy read for check 7 |
| `engine_identity` | the content hash of the code that decided, as `governor_identity` is for acceptance; with the interpreter's version (section 5) |
| `uncovered` | what the decision could not see (concept line 65) |
| `state_effect` | the events section 10 appends with it |
| `error` | present only when no decision value is given |

- A decision is recomputable from its record, the repository and the event log: the same inputs give the same decision (as constitution INV-010 asks of acceptance; proposed).
- Ids (concept line 856; spec 2 §6.1 and §6.2): every Resume Check is a fact of its own. Its record carries `log_seq`, the sequence number of the last event of the log it read; its `record_id`, and the `event_id` of every event section 10 appends with it, are the SHA-256 of the task id, `log_seq`, `head_commit`, the `engine_identity` and the event's type (`decision.execution` for the record itself), computed once when the check runs and stored in the record. A retried append of the same record reuses the stored ids and has no effect; a later check reads a later `log_seq` and so gets new ids. A decision taken while a session runs (section 8) uses as `log_seq` the last event of the log the core read when it decided (proposed). A READY task that stays stuck (section 10) gets a new `conflict.detected` with each later check, as intended.

## 10. The task state each decision causes

This settles spec 1 §10 point 7, with spec 1's events only and no new state (proposed):

| Decision | Effect |
|---|---|
| CONTINUE | the lease is granted: READY or REWORK becomes IN_PROGRESS through the local store (spec 1 §5.1) |
| CONTINUE_WITH | as CONTINUE; the Work Order is compiled again (line 287); the contract is not changed |
| REPLAN | one `task.stale` (spec 2 §6.3), for the lowest-numbered check that gave REPLAN; any other is kept in the record: for check 3, `cause` `conflict`, referring to a `conflict.detected` appended first with the tasks named by the trailers of the commits that changed the met entries (the list may be empty) and the `interfaces` or `paths` met; for check 4, `cause` `intent_change`, referring to the `intent.changed` event of the current version. `task.replanned` (STALE → DRAFT, spec 1 §5.1) is appended later, when a new contract version is drafted; the Resume Check does not append it, and it is not part of `state_effect` |
| BLOCKED | `task.blocked`, `reason` `dependency`, `blocked_by` the tasks of check 5; the core appends `task.unblocked` when check 5 passes again, run each time a task it waits for changes state |
| ESCALATE | `task.blocked`, `reason` `escalate`, `blocked_by` the decision's `record_id`; it is unblocked only through an authority record that answers the escalation |
| STOP: scope invalid | `conflict.detected` with the tasks named by the trailers of the commits that changed the write-set's paths (the list may be empty) and those `paths`; then `task.blocked`, `reason` `scope_invalid`, `blocked_by` that event; it is unblocked only through an authority record that settles the conflict, since section 6's rebase is deferred. A write-set collision is not an interface-breaking CONFLICT, so spec 1 gives it no `task.stale` (spec 1 §5.1; concept line 289) |
| STOP: runtime insufficient | no task event: the task stays in READY or REWORK, and only a runtime whose `max_risk` is enough may take it (line 645) |
| STOP: violation | `violation.detected`; the lease is released; the change is rejected at acceptance (section 8) |

- The Resume Check runs on a task in READY or REWORK, or IN_PROGRESS under a held lease (section 1). On a held lease, REPLAN gives `task.stale` from IN_PROGRESS, which spec 1 allows, and the lease is released (spec 1 §5.1). Spec 1 lets `task.stale` start from REWORK but does not list READY (spec 1 §5.1, and §10 point 8, which leaves open whether READY is among the states "sau READY" of line 529). Until spec 1's next revision settles it, a READY task given REPLAN gets the `conflict.detected` of that row, if any, but no `task.stale`: it stays in READY with no lease; each later Resume Check appends its own record, and none grants a lease; an authority record or that revision moves it on (proposed; section 12).
- Overlapping write-sets never run in parallel in v0.1 (spec 1 §5.2; lines 541, 951): one lease at a time.
- A CONFLICT found by reconciliation (`conflict.detected`, spec 1 §5.3; line 271) leads to the task's next Resume Check, whose check 3 gives CONTINUE_WITH or REPLAN.

## 11. Boundaries

- The acceptance decision is the governor's (`governor-spec.md`); the governor never emits an execution decision (its §1). The two decisions are never merged (concept line 943; A15).
- Evidence profiles, gates and stale evidence are specification 4's; the adapter declaration, its `max_risk`, observed read-sets and the detection of violations while running are specification 5's; the protocol and the CLI are specifications 6 and 7's; the Context Compiler, which runs after CONTINUE or CONTINUE_WITH, is not specified here (its milestone is open, Master Plan §10).
- Which milestones are built as the bootstrap and when the native stack is chosen is open (Master Plan §10); it does not change this specification, whose rules and decision contract are the same for bootstrap and native (A15).
- Records that the bootstrap writes before AIEOS governs its own build carry their recorder and are not authoritative (CR-001 E3; constitution INV-004).

## 12. Open points and proposed choices

1. Check 2's rebase branch (section 6): deferred, not dropped. Proposed scenario: `Δ` meets the write-set, and the conflict resolves by a deterministic rebase → the decision the rebase rule gives.
2. Proposed scenarios that the set does not cover (`conformance-scenarios-initial.md` §6): check 5's "chưa DONE" branch (a dependency not yet DONE → BLOCKED); budgets other than retries (a reported token or wall-time use at its budget → ESCALATE); two checks firing at once (the order of section 7); an unresolvable interface entry (section 5); `base_commit` not an ancestor of HEAD (section 2 check 1).
3. Settled here, given to this specification by spec 1 and spec 2: spec 1 §10 point 7 (section 10) and point 9 (section 9); spec 2 §10 point 6 (section 9). Spec 1 and spec 2 are not changed by this text; their open-point lists are updated at their next revisions.
4. The payload of `task.stale` (spec 2 §6.3) has the causes `intent_change` and `conflict` only: a check-4 REPLAN where the log holds no `intent.changed` event for the current version (an intent file changed outside a change request) has no event to refer to; whether that is DRIFT (spec 1 §5.3) and how it is referred to is open, for spec 2's next revision.
5. The `task.blocked` reasons `dependency`, `escalate` and `scope_invalid` (section 10) are values of spec 2's `reason`, whose vocabulary spec 2 does not fix.
6. A READY task given REPLAN (section 10): spec 1 §10 point 8 leaves open whether `task.stale` may start from READY; proposed for spec 1's next revision: yes, when the Resume Check finds it, since the check runs at the step from READY to IN_PROGRESS. Until then the task stays in READY, as section 10 says.
7. The precondition of section 2 (check 0, DM A15): the contract at HEAD must equal the approved one.
8. A check record names the constitution article it checks by `refers_to` (section 2 check 6): a widening of spec 2 §6.2, for spec 2's next revision; how the check that writes it runs is specification 4's.
9. HEAD as the tip of the base branch, and `Δ` as the union of the changes of each commit, leaving out only the commits the task's own `task.submitted` events name (section 1; section 2 check 1).
10. Where a project declares its base branch and its module roots: spec 2 §7 has no key for them; for spec 2's next revision (section 1).
11. Check 8's retry branch is a backstop behind the governor's routing to ESCALATED (spec 1 §5.1; `governor-spec.md` §5 leaves the counting outside the governor); RC-10's fixture gives a count over the limit and states it.
12. The other choices marked "(proposed)": the inputs as the only reads; the runs at each new session under a held lease, and HEAD moving after the decision (section 1); no reuse of an earlier result; ESCALATE when `base_commit` is not an ancestor; `Δ` without rename detection; check 6's uncovered articles and its scope rule; check 7's task risk by pattern overlap and its ESCALATE for an unclassified pattern; check 8's "over the limit", its count from the latest approval and its unreported uses; the two-pattern rule of section 3; the derived read-set's one level of direct imports; the signature rules and their fixed form, schema names and their resolution, path entries as non-breaking, and the fail-closed verdicts (section 5); running every check and the order of section 7; `error` with `null` and its list of inputs; ESCALATE while running; `fact_kind` `interpretation`; the record's key names and `engine_identity`; recomputability and the ids from `log_seq`, stored in the record (section 9); the self-build's base branch `main`; the effects of section 10, among them one `task.stale` for the lowest-numbered REPLAN check and STOP: scope invalid as `task.blocked`.

## 13. Revisions

- Revision 0: first draft (D-243).
- Revision 1: applies the sixteen findings of one read-only reviewer round (sonnet), each verified against its source lines (fifteen applied, one left as is: the section "Revisions", which specifications 1 and 2 also have): schema entries as names with a fail-closed resolution; path entries non-breaking; check 7 by pattern overlap; check 6's article named by `refers_to`; retries over the limit; the full input list; the risk rules' pattern text; `Δ` without trailer-based exclusion; the scenario fixtures' read-set sources; runs on IN_PROGRESS; one cause per `task.stale` and idempotent ids; STOP: scope invalid as `task.blocked`; the two-pattern rule; a fixed signature form; the inputs that give `error`.
- Revision 2: three corrections of decision D-244 (D1 to D3): the ids of a Resume Check's record and events come from `log_seq` and are stored once, so two checks are always distinct facts and a retried append has no effect; `task.replanned` is appended when a new contract version is drafted, not by the Resume Check; the self-build's base branch is `main`, and its declaration is among the inputs that give `error`.
- Revision 3: the findings of a second read-only review round (sonnet) on the fixes: check 8's retry branch fires at the limit, as scenario RC-10 says, with its boundary to the governor's routing listed as open; a component path naming a folder stands for everything under it; the schema-name resolution names its components and runs at both commits; `main` applies when nothing is declared, and undeclared module roots leave imports unresolved; REPLAN on a held lease gives `task.stale` from IN_PROGRESS; the ids name `decision.execution` and the in-run `log_seq`; an article with no scope is not in the task-time set.
- Revision 4: decision D-245: check 8's retry branch fires over the limit, as in revision 2, since the k-th decision that sends a task to REWORK opens its k-th retry; RC-10's "used up" is read as a count over the limit, and the branch is a backstop behind the governor's routing (section 12 point 11).
