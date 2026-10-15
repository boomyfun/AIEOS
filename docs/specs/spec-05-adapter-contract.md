# Specification 5: Adapter Contract + Claude Code adapter

> - **Status:** revision 3, a draft until approved. Whether it is approved and baselined is recorded in DM section F, not in this file. It decides nothing that a decision matrix (DM) row or a bound document decides.
> - **Drafted under:** decision agent decisions D-758 (the drafting plan; Master Plan revision 4 §4 M5), D-759 (revision 1) and D-763 (revision 2). Decision files are kept outside the repository (`docs/WORKING-RECORDS.md`).
> - **Path:** `docs/specs/spec-05-adapter-contract.md` is interim, like specifications 1 to 4: files move only when a core writes the project-state directory (spec 2 §10 point 2).
> - **Citation form:** as specification 4: a reference is `[file:line]` or `[file:first-last]`; "concept" is `AIEOS-concept.md` (v0.5, unchanged, A22). Every choice that no source fixes is marked "(proposed)".
> - **What this text is not:** it installs, configures and measures nothing. A hooks mapping here is text only; putting any hook or setting into force is the owner's act (section 10).

## 1. Scope and reading order

- Specification 5 is the fifth of the seven technical specifications of concept §18: "Interface adapter, khai báo assurance, hooks mapping" [AIEOS-concept.md:995]. Its v0.1 item is the Claude Code adapter, with T3 as its target tier (section 6): hooks that enforce the write-set and a shell allowlist, block `git push`, and record the observed read-set [AIEOS-concept.md:945]. The second vendor adapter of line 946 is out of v0.1 [docs/pre-genesis/CR-001-concept-errata.md:11].
- Runtime neutrality for v0.1 is shown by "`adapter contract + T0 manual adapter + replay adapter + conformance`" [docs/pre-genesis/decision-matrix.md:68] (A12).
- What earlier specifications left to this one: the observed read-set and its capture [docs/specs/spec-03-resume-check-and-decision-engine.md:24] [docs/specs/spec-03-resume-check-and-decision-engine.md:64]; the runtime's `max_risk` and the adapter declaration's form [docs/specs/spec-03-resume-check-and-decision-engine.md:29]; the detection of violations while running [docs/specs/spec-03-resume-check-and-decision-engine.md:106] [docs/specs/spec-03-resume-check-and-decision-engine.md:163]; and the runtime hooks that specification 4 leaves out [docs/specs/spec-04-verification-and-evidence.md:105].
- Built in the bootstrap: Python 3, standard library only, disposable (Master Plan revision 4, §4 M5 to M7 constraints; A9).
- Reading order: the assurance model, specifications 1 to 4, then this one (proposed).

## 2. The adapter contract

- An adapter connects one agent runtime to the core. The core stays the single writer of the project-state directory [docs/pre-genesis/constitution.md:42-43] (INV-004); an adapter never writes it, and reaches the core only through the core's paths (proposed).
- What an adapter does (proposed):
  1. **Session start:** asks the core for a session on a task; the core runs the Resume Check and, on CONTINUE or CONTINUE_WITH, grants the lease (specification 3; specification 1's lease and fencing token [docs/specs/spec-01-state-and-event-model.md:39]); the adapter carries the fencing token for the session.
  2. **Work Order:** receives the Work Order (specification 6's form; named here only as an input).
  3. **Observations:** passes to the core what the runtime observed (section 7) and any violation (section 8), as records the core writes.
  4. **Submission:** submits the session's commit through the core's submission path (TASK-025's). The commit carries the session's fencing token in its `AIEOS-Fence` trailer; the submission path passes it to the core's writer, and the writer passes the store's held lease to the append, which refuses a token that is not the held lease's or a lease that has expired [src/aieos_bootstrap/submit.py:13-18] (TASK-025; the writer, TASK-016). A commit with no usable fence goes to the writer with no token and is refused; such a refusal is the core's observation `refused_submission` with `outcome` `fail` [docs/specs/spec-02-aieos-file-format.md:173], not a violation. The adapter makes no fence comparison of its own. (Task ids name accepted tasks; their decisions are kept outside the repository, `docs/WORKING-RECORDS.md`.)
  5. **Session end:** a session that ends without a submission and without a release by the core asks the core to release the lease by its token (TASK-028); a release whose token no longer matches the held lease has no effect. After a submission the submission path releases the lease [src/aieos_bootstrap/submit.py:19-21]; on STOP: violation the core releases it [docs/specs/spec-03-resume-check-and-decision-engine.md:154]; if the adapter or the runtime stops without either, the lease's expiry is the fallback (specification 1) (proposed).
- An adapter makes no acceptance and no execution decision; those stay the governor's and the Resume Check's [docs/specs/spec-03-resume-check-and-decision-engine.md:163].

## 3. The adapter declaration

- The concept's form: capabilities, assurance and `max_risk` [AIEOS-concept.md:630-643]; the scheduler uses `max_risk` "để **từ chối giao** task vượt mức cho runtime yếu" [AIEOS-concept.md:645]; tiers T0 to T4 [AIEOS-concept.md:649-653].
- **Never self-declared.** By CR-001 E1, an adapter's assurance is not self-declared; it counts only as measured, for each runtime × platform × version × configuration [docs/pre-genesis/CR-001-concept-errata.md:10]. So (proposed):
  1. a declaration names its capabilities and the configuration it was measured in, and points to the measurement record;
  2. an assurance field without such a record is read at its weakest value (`none`), and `max_risk` is then read as `low` (fail closed);
  3. a declaration is data the core reads at the base, never from the change it judges.
- **STOP: runtime insufficient** [AIEOS-concept.md:290]: a task whose risk is above the runtime's `max_risk` is not leased to it; the Resume Check returns that value (specification 3's check 7 and RC-09 [docs/specs/spec-03-resume-check-and-decision-engine.md:46] [docs/specs/spec-03-resume-check-and-decision-engine.md:99]).
- Three cases, kept apart (specification 3 [docs/specs/spec-03-resume-check-and-decision-engine.md:86]): a runtime with **no declaration** gets STOP: runtime insufficient for every task; a **malformed** declaration gives `error` and no decision; a well-formed declaration **without a measurement record** reads `max_risk` as `low` by item 2 above, so any task above low risk gets STOP: runtime insufficient (proposed).
- This specification sets no tier, no assurance value and no `max_risk` for gov-AIEOS's runtime. No declaration of it exists, so until one is made and measured, check 7 gives STOP: runtime insufficient for its tasks (the first case above); item 2's reading rule is a default for any declaration, not a value set for this runtime (proposed; section 10).

## 4. The T0 manual adapter

- Tier T0, "Chat", "Chỉ post-hoc" [AIEOS-concept.md:649]: a human or a chat session does the work; nothing is observed while running.
- Its records are claims of `agent_declared` [docs/pre-genesis/assurance-model.md:22] for what the agent says it did; the read-set is an estimate [AIEOS-concept.md:483]; the evidence that counts comes after, from the gates (specification 4) (proposed).

## 5. The replay adapter

- It replays a recorded session against the core, for conformance (A12): a fixed sequence of session start, observations, submission and end, read from a fixture (proposed).
- Deterministic, no model call (INV-001 [docs/pre-genesis/constitution.md:27]); its records carry a recorder that names the replay, so they are never mistaken for a live session's (proposed).
- Replayed records exist only in a conformance run, never in a project's event log, and claim no class above `deterministic_tool_local`; a passing replayed scenario shows how the core handles a recorded observation, never that any hook observes anything (C6 stays unmeasured) (proposed).
- Every value a replayed session needs (times, ids, the fencing token) comes from the fixture, so two runs give equal records; the fixture's form is an open point (section 11) (proposed).

## 6. The Claude Code adapter

- **Target configuration in v0.1:** Claude Code running natively on Windows in the desktop app's sessions, the runtime C6's note names [docs/pre-genesis/decision-matrix.md:178] (A38 [docs/pre-genesis/decision-matrix.md:99]). Other platforms are open points (section 11).
- **Target tier:** T3, "Hooks / permissions / sandbox", "Preventive + runtime + post-hoc" [AIEOS-concept.md:652]; as a target only: its assurance counts only when measured (section 3).
- **The hooks mapping (text only; proposed):**

| Concern | Line 945 asks | Hook point (proposed) | What it would record |
|---|---|---|---|
| Write-set | enforce the write-set | before a file-writing tool call | the path; a refusal when outside the lease's write-set |
| Shell allowlist | enforce an allowlist | before a shell tool call | the command; a refusal when not allowed |
| `git push` | block it | before a shell tool call | a refusal |
| Observed read-set | record it | after a file-reading tool call | the path read |

- **What a hook can and cannot show** (A25 [docs/pre-genesis/decision-matrix.md:86]): a hook is an enforcement mechanism whose strength depends on the boundary around it; at best preventive for cooperative or accidental actions; against a determined agent at most detective, and only through a channel outside the agent's reach; it cannot prove its own integrity. So (proposed): every record a hook makes on the agent's machine is at most `deterministic_tool_local` [docs/pre-genesis/assurance-model.md:24], which may block and never satisfies an evidence entry; a refusal by a hook is a block, not a proof that nothing else happened.
- **Unmeasured, not assumed** (C6 [docs/pre-genesis/decision-matrix.md:178]): whether hooks fire and block as configured; fail-open behaviour and timeouts; session start sources, including after compaction; tool coverage, including PowerShell, MCP tools and subagents; and whether the agent can edit the hook configuration. Until measured, the adapter's assurance fields read at their weakest (section 3).
- **An existing example:** the owner answered yes to an automatic block for forbidden command forms (DM A57 [docs/pre-genesis/decision-matrix.md:118]). It is advisory and unmeasured: refusals seen in Claude's own sessions are agent observations, not a measurement of C6, and this specification does not rely on the guard as a control (proposed).

## 7. Observed read-set records

- The concept's source "Observed": "File agent thực sự đọc trong session (hooks của runtime T3+)" [AIEOS-concept.md:481]; below T3 the read-set is an estimate [AIEOS-concept.md:483].
- Form (proposed): one record per session in specification 2 §6.2's form [docs/specs/spec-02-aieos-file-format.md:139], its `subject` the task id (so the envelope's `task_id` is that id [docs/specs/spec-02-aieos-file-format.md:137]), `source_class` `deterministic_tool_local`, a `recorder` naming the adapter and the session, listing the paths read; written by the core from what the adapter passes. The key that holds the paths is an open point (section 11).
- Use: specification 3 takes the observed source only from a runtime of tier T3 or above [docs/specs/spec-03-resume-check-and-decision-engine.md:64]. Since no runtime's tier counts until measured (section 3), the observed source stays absent, and the read-set an estimate, until a measurement record exists; until then such records are kept and not used (proposed).
- Even when used, a hook-based capture is a lower bound: reads made through a shell command, or through a tool no hook covers, are not seen, and a hook cannot show its own completeness (A25); so the read-set stays marked as an estimate where any such path exists, and an uncovered check is listed as uncovered (proposed).

## 8. Violations seen while running

- STOP: violation, "Session vừa vi phạm policy", for example "Ghi ngoài write-set" [AIEOS-concept.md:291]; the core appends `violation.detected` and the execution decision [docs/specs/spec-03-resume-check-and-decision-engine.md:106]; its record is "one `observation` record with `outcome` `blocking` and `blocking_kind` `violation`" [docs/specs/spec-02-aieos-file-format.md:191].
- A refusal by a hook (proposed, fail closed): every refusal by a hook on the write-set, `git push` or the shell allowlist (the three concerns of section 6's table that line 945 names as policy) is recorded as an observation with `outcome` `blocking` and `blocking_kind` `violation`, and leads to STOP: violation, even though the refused action did not happen. Only an approved policy at the base may loosen this for a named concern (section 11 point 5).
- This extends specification 3's wording, which names "a write outside the write-set or another broken policy" [docs/specs/spec-03-resume-check-and-decision-engine.md:106], to an attempt that was refused; specification 3's consequence then applies in full: the lease is released and the change is rejected at acceptance [docs/specs/spec-03-resume-check-and-decision-engine.md:154]. Its cost is stated: one refused command ends the session, and a shell allowlist set too narrow can stop every session of a task; the bound on such repeats is an open point (section 11) (proposed).
- The STOP follows from the recorded observation, not from trust in the hook: the absence of a refusal record proves nothing, since a hook that does not fire neither refuses nor records (C6, unmeasured); below a measured T3 runtime, a violation is found afterwards by the gates (specification 3, section 8; specification 4's G0) (proposed).
- Scenario ADV-02 needs a runtime at T3 or above that observes a write outside the write-set [docs/pre-genesis/conformance-scenarios-initial.md:64]; its fixture is written by the replay adapter's form (section 5), so ADV-02 can run in conformance without a live runtime; a passing ADV-02 then shows only the core's handling of a recorded observation, not that any hook observes anything (proposed).

## 9. Conformance of adapters

- Each adapter passes the conformance scenarios that name its capability; the replay adapter is how a scenario that needs a runtime runs deterministically (proposed). Which scenarios, and their fixtures, are written in tasks of their own, each frozen by a fixture-freeze approval (Master Plan §4 M2; DM B1, B10).

## 10. Boundaries, and what stays the owner's

- The owner's, named here and not drafted as acts:
  - installing hooks, changing Claude Code settings, `CLAUDE.md`, the agents folder, and any act at a permission prompt (A51 item (4) [docs/pre-genesis/decision-matrix.md:112]; Master Plan §9 item 2);
  - every measurement of an adapter's assurance, including C6 and P-LOC (C6 [docs/pre-genesis/decision-matrix.md:178]; A30 [docs/pre-genesis/decision-matrix.md:91]; Master Plan §9 item 3);
  - raising any assurance or autonomy because of an adapter (Master Plan §9 item 5).
- An M5 task that carries out or changes such an act is approved by the owner (CR-002 part 4 limit 5 [docs/pre-genesis/CR-002-concept-errata.md:61]; Master Plan §4 M5).
- Specification 6's: the MCP tools and the Work Order's form; specification 7's: the CLI. No second vendor adapter in v0.1 [docs/pre-genesis/CR-001-concept-errata.md:11].

## 11. Open points and proposed choices

1. Platforms other than the Windows desktop runtime (WSL2, Linux and macOS terminals): outside v0.1's target configuration, not excluded later; assurance never carries across platforms (CR-001 E1).
2. The measurement of the Claude Code adapter (C6, P-LOC): the owner's; until then every assurance field reads at its weakest.
3. The adapter declaration's file and keys (section 3): for specification 2's next revision.
4. The observed read-set record's `evidence_type` name (section 7): for specification 2's next revision.
5. A refusal by a hook (section 8): proposed default, fail closed: every refusal on the write-set, `git push` or the shell allowlist is a violation and leads to STOP: violation; only an approved policy at the base may loosen this for a named concern.
6. The shell allowlist's content: a policy matter (the approved policy at the base), not this specification's.
7. The interface between an adapter and the core: the call names and shapes, the ids that tie an observation to a session and a lease, where the adapter takes the lease's write-set from, and the channel by which a hook on the agent's machine passes an observation to the core: for the first M5 contract, which states them (proposed).
8. The hooks mapping's detail: the runtime's tool and event names each hook point covers (file edit, notebook edit, shell, PowerShell, MCP tools), and path semantics on Windows (case, separators, relative and absolute paths, links and junctions, pattern matching, normalisation in records): for the first M5 contract that builds the Claude Code adapter (proposed).
9. The replay fixture's form (file, keys, order, the source of times, ids and tokens), and the T0 adapter's session flow (how it submits; violations found afterwards by the gates): for the M5 contracts that build them (proposed).
10. An abnormal session end (a crash, a lease that expires, a resume after compaction), beyond section 2 item 5's fallback: an open point for those contracts.
11. Which conformance scenarios each adapter must pass, beyond ADV-02 (for T0, and for the lease and fencing flow): set with their fixtures in tasks of their own (section 9).
12. A bound on repeated STOP: violation for one task (section 8), for example by the retry budget the governor reads: an open point.
13. The choices marked "(proposed)" throughout, among them the hooks mapping table (section 6), the replay adapter's form (section 5) and the reading order (section 1).
14. A consequence of section 3, stated: until a declaration of the self-build's runtime exists with a measurement record, check 7 gives STOP: runtime insufficient for its tasks, and with an unmeasured declaration for every task above low risk; so the self-build cannot lease such a task through the core (Master Plan M8) until the owner has measured the runtime (C6, P-LOC; Master Plan §9 item 3). Any interim rule that lets an unmeasured runtime take a task above low risk is a raise because of an adapter, and is the owner's (Master Plan §9 item 5); this specification proposes none. [Marker 2026-10-15: lifted by the owner (DM A69).]

## 12. Revisions

- Revision 0 (decision D-758's plan): first draft.
- Revision 1 (decision D-759): the guard sentence of section 6 (M1); a refusal by a hook is a violation, fail closed (section 8 and section 11 point 5; M2); who checks the fencing token at submission (section 2 item 4; M3).
- Revision 2 (decision D-763): the findings of five way-2 reviews of revision 1 (all "pass", no blocking finding): the target tier wording (section 1); the three declaration cases and gov-AIEOS's STOP: runtime insufficient until a declaration exists (section 3); the store's held lease, the refused submission and the session-end release (section 2); the replay records' class and determinism (section 5); the guard sentence's wording (section 6); the observed source absent until measured, and a lower bound (section 7); the STOP's extension of specification 3, its cost, and what a refusal record does and does not show (section 8); the C6 citation (section 10); open points 7 to 13 (section 11).
- Revision 3 (decision D-763): section 11 point 14, the consequence of section 3 for the self-build stated (no task above low risk leased through the core until the owner has measured the runtime; any interim rule is the owner's).
