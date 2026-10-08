# Specification 2: the `.aieos/` File Format

> - **Status:** revision 1. Whether it is approved and baselined is recorded in DM section F, not in this file. It decides nothing that a decision matrix (DM) row or a bound document decides.
> - **Drafted under:** decision agent decisions D-146 (the M1 drafting plan, item 2) and D-150 (Master Plan §4 M1). Decision files are kept outside the repository (`docs/WORKING-RECORDS.md`).
> - **Path:** `docs/specs/spec-02-aieos-file-format.md` is interim, like `docs/plan/` and specification 1. This specification proposes the layout (DM B7) and a text for CR-001 E4 (working record DEF-0018); both stay the owner's to settle (A22; CR-002 part 8), so the layout part stays proposed until then.
> - **Sources:** "concept line N" is a line of `AIEOS-concept.md` (v0.5, unchanged, A22). "DM B7" is a row of `docs/pre-genesis/decision-matrix.md`; B3, B5, B7 and B9 are rows of DM section B, "Proposed architecture (not ratified)". "Spec 1" is `docs/specs/spec-01-state-and-event-model.md` revision 1 (DM F11). "(proposed)" marks a choice of this specification where the concept is silent or says less; each one is also listed in section 10.

## 1. Purpose and scope

- This is the second of the seven technical specifications of concept §18 (line 992): "Schema YAML/MD cho constitution, requirement, spec, ADR, task contract, handoff".
- It fixes how the project-state directory is laid out, how each entity of spec 1 §3 is written as a file or as an event, and the spelling of every name that spec 1 left to it (spec 1 §4, §5; its section 10 points 1 and 2). Within it: the task contract format (concept §7.1, lines 425-484), the field names of the decision contract (`governor-spec.md` §11 point 8; A15) and the record formats the governor reads and writes (`governor-spec.md` §3.1, §3.3, §6.1).
- Not in scope: what the risk rules say (the self-build's risk rules, the third M1 document); the Resume Check and the content of execution decisions (specification 3); evidence profiles and the gate pipeline beyond the names used here (specification 4); the adapters' own files (specification 5). It creates no file. Only the AIEOS core writes the project-state directory (constitution INV-004), and the first code task's write-set has nothing under `.aieos/` (Master Plan §8).

## 2. General rules

- Text files are UTF-8 without a byte-order mark, with LF line ends (proposed).
- Structured entities are YAML files; prose entities are Markdown files that start with a YAML front-matter block between two `---` lines (concept line 992, "YAML/MD"; the split is proposed).
- Field names are lowercase `snake_case`, as in the concept's examples (lines 333-387, 429-470). Event types are lowercase words joined by dots, as in spec 1 §5. State names are the concept's, in capitals: DRAFT, READY, IN_PROGRESS, VERIFYING, ACCEPTED, DONE, IN_REVIEW, REWORK, ESCALATED, REJECTED, BLOCKED, STALE (lines 521-529).
- Ids follow the concept's examples: `REQ-012`, `SPEC-012.1`, `ARC-auth`, `ADR-031` (lines 403-406), `TASK-142` (line 430); constitution articles `INV-001`, `SEC-001`, `OPS-001` and the like (lines 335-356); change requests `CHG-NNN` (proposed; not `CR-`, which the concept errata use). A file is named after its id, `<id>.yaml` or `<id>.md`, except the two single files `project.yaml` and `constitution.yaml` and the handoffs (section 5.2) (proposed).
- Versions are written `v1`, `v2`, … (line 437). Every intent entity has one (line 409).
- A commit id is written in full, as Git prints it, in lowercase hex; never abbreviated (proposed).
- Hashes (all proposed): a file's content hash is the SHA-256 of its bytes, written as 64 lowercase hex digits. A contract's `contract_hash` is the content hash of its file (spec 1 §3). The `task_content_hash` of an evaluation (A42; `governor-spec.md` §3.1, proposed there) is the SHA-256 of the contract file's bytes followed by one LF and the evaluated commit id. Spec 1 §3 and §5.4 name one "contract hash"; this specification spells it as these two, because a contract is approved before any evaluated commit exists (section 6.2, `approval_binding`).
- Unknown fields are an error: a file or event with a field that this specification does not name is malformed (`governor-spec.md` §4 rules 6 and 7 treat a malformed input as not used or as giving no decision) (proposed). This applies to field names, not to the values of open vocabularies (section 6.2).

## 3. Layout (proposed; DM B7; owner point)

```text
.aieos/
├── project.yaml            # the policy: risk rules, autonomy, adapters (concept line 868)
├── constitution.yaml       # concept line 869
├── intent/                 # concept lines 870-871; B7: the single intent root
│   ├── requirements/  specs/  architecture/  decisions/  conventions/
├── changes/                # change requests (proposed)
├── tasks/                  # task contracts (concept line 872)
├── handoffs/               # concept line 873
├── genesis/                # B7
├── conformance/            # B7
├── plan/                   # B7
├── events.jsonl            # the append-only event log (concept line 874); committed (proposed reading)
└── local/                  # the local store; ignored by Git, never committed (concept line 876; proposed)
```

- `intent/decisions/` holds the ADRs (concept line 871; B7). It does not hold the governor's decision records, which are records of the event log (section 6).
- The local store (leases and sessions, spec 1 §5.2) is SQLite and is never committed (concept line 876). Proposed: `.aieos/local/state.sqlite`, with `.aieos/local/` listed as ignored by Git. Its tables (proposed): `store` (`epoch`, `counter`), `leases` (`task_id`, `holder`, `session_id`, `fencing_epoch`, `fencing_counter`, `granted_at`, `expires_at`) and `sessions` (`session_id`, `holder`, `started_at`, `ended_at`); times as in section 6.1.
- Only the AIEOS core writes this directory, through one writer (concept lines 858, 879; constitution INV-004).
- B7 adds `genesis/`, `conformance/` and `plan/` to the concept's tree (lines 866-877); `changes/` and `local/` are this specification's. B7 gives names only; what this section says each one holds is this specification's reading. Where the interim documents now under `docs/plan/` and `docs/specs/` move is open (section 10).
- Proposed text for CR-001 E4, for the owner (A22; CR-002 part 8), in the errata's language, aligned with the tree above: "§13.4 (dòng 865-877): cây thư mục `.aieos/` có thêm `genesis/`, `conformance/` và `plan/` (theo DM B7), `changes/` (các Change Request) và `local/` (local store của lease và session, không commit, như dòng 876)." Not asked here; it goes in this specification's approval request as an owner point (D-150 C5).

## 4. Intent files

### 4.1 Constitution: `constitution.yaml`

A top-level `version` and a list `constitution` of articles (concept lines 333-362, 375-387; constitution.md §2):

| Field | Required | Values and source |
|---|---|---|
| `id` | yes | the article id (line 335) |
| `category` | yes | `architecture`, `correctness`, `security`, `operational` (lines 336-357); for gov-AIEOS also `governance` (constitution.md §2) |
| `rule` | yes | the rule in words (line 337) |
| `source` | for gov-AIEOS | where the article comes from (constitution.md §2) |
| `check` | yes | `deterministic`, `partial` or `judgment` (lines 364-367) |
| `tool` | for `deterministic` and `partial` where a checker exists | `{type, …}`: `type` names the checker kind, and the other keys are those of that kind (proposed), for example `from` and `forbid` for `dependency_rule` and `require` and `in` for `pattern` (lines 339, 346); SEC-001 has none (lines 350-354) |
| `evidence_required` | for `partial` and `judgment` | a list of evidence types (lines 347, 360) |
| `severity` | yes | `blocking`, … (line 340) |
| `scope` | no | `{components: [component ids], paths: [...]}`; absent means project-wide, run at project time only (lines 378-380, 397) |
| `applicability` | no | `{task_types: [...]}` (lines 381-382; section 5.1, `task_type`) |
| `enforcement` | no | `{mode, checker, cost}`: `mode` is `blocking`, `warning` or `advisory`, and `cost` is `cheap`, `moderate` or `expensive` (lines 383-386) |

The bound constitution of the self-build (`docs/pre-genesis/constitution.md`) states these fields in Markdown, `source` and the `governance` category included. Writing it as `constitution.yaml` is a later task of its own (open, section 10). The keys of each `tool` type are set with that checker (open, section 10); until a type's keys are set, the unknown-field rule does not judge its other keys.

### 4.2 Requirement, specification, architecture, ADR, convention: `intent/<kind>/<id>.md`

Front matter, then the prose (concept lines 401-409):

| Kind | Front-matter fields |
|---|---|
| requirement | `id`, `version`, `title`; `evidence_profile`, by dimension, only where it differs from the risk default (lines 676-685, 697) |
| specification | `id`, `version`, `title`, `traces_to` (requirements); the body holds acceptance criteria with ids, each verifiable (line 404) |
| architecture | `id`, `version`, `title`, `components`, `interfaces`; the body holds responsibilities and boundaries (line 405) |
| ADR | `id`, `version`, `title`; the body holds the decision, the reasons and the options set aside (line 406) |
| convention | `id`, `version`, `title`; `becomes_article` when it is raised into the constitution (line 407; proposed) |

- `components` is a list of `{id, paths: [...], tags: [...]}`; `interfaces` a list of `{id, component}` (line 405; proposed). A constitution `scope.components` names component ids, and a risk rule's `component_tags` matches a change when a changed path lies under the paths of a component carrying one of those tags (lines 592, 599; section 7; proposed).
- A file carries no `status`. Whether a specification is draft, baselined or superseded (B9) is derived from its `authority` records (section 6.2), as a projection (spec 1 §6); for gov-AIEOS, a delegated approval is also recorded as a DM section F row, as F11 records spec 1's (proposed).

### 4.3 Change request: `changes/<id>.md` (proposed)

Front matter `id` (`CHG-NNN`), `targets` (entity ids with their current versions) and `new_versions`; the body says what changes and why. It carries no `status`: its approval is an `authority` record bound to its content hash (section 6.2), and its rejection an `authority` record too. Intent changes only through an approved one (line 409).

## 5. Task files

### 5.1 Task contract: `tasks/<id>.yaml`

The twelve parts of concept line 473, with the field names of its example (lines 429-470), and the fields the Master Plan requires of a contract (Master Plan §8):

| Field | Part | Values and source |
|---|---|---|
| `task` | — | the task id (line 430) |
| `contract_version` | — | `v1`, `v2`, …; a replanned task gets a new one (spec 1 §5.1; proposed) |
| `task_type` | — | the kind of task, which a constitution article's `applicability` names: `implementation`, `refactoring` (line 382) and others (an open vocabulary, section 10) (proposed) |
| `objective` | Objective | text (line 431) |
| `traces_to` | — | requirement and specification ids (line 432); for the first code task, an approved specification (Master Plan §8) |
| `input_state` | Input state; Dependencies | `{base_commit, depends_on: [task ids], intent_versions: {id: version}}` (lines 434-437); the Dependencies part is `input_state.depends_on`, not a field of its own (line 436) |
| `write_set` | Write-set | `{paths: [...]}` (lines 439-440) |
| `read_set` | Read-set | `{paths, interfaces, schemas}`, the declared source (lines 441-444, 475-483) |
| `forbidden` | Forbidden | paths (line 445) |
| `constitution` | Constitution | article ids (line 447) |
| `acceptance_criteria` | Acceptance criteria | a list of one-entry maps from an id to its text, as in the concept: `- AC1: <text>` (lines 449-452) |
| `capabilities` | Capabilities | `{filesystem: {read, write}, shell: {allow}, network: {allow}, git: {allow, forbid}, secrets, external_side_effects}` (lines 454-458, 565-571); `secrets` and `external_side_effects` are `deny` or a list of what is allowed (proposed); a capability that is absent is denied (line 562) |
| `risk` | — | `low`, `medium`, `high` or `critical` as declared (line 460); a lower risk declared here than the risk rules give is not used (`governor-spec.md` §3.2) |
| `autonomy` | Budget | `{max_level, budgets: {tokens, wall_time, retries, human_attention}}` (lines 461-463); `max_level` is `L0` to `L4`; `tokens` is a whole number, with `k` (thousands) or `m` (millions) allowed, as `400k`; `wall_time` and `human_attention` are a whole number with `s`, `m` or `h`, as `45m`; `retries` is a whole number, the limit the governor reads (spec 1 §5.1) (value syntax proposed) |
| `verification_plan` | Verification plan | a list of gates, written `{gate, check, args}`: `gate` is `G0`, `G1`, …, `check` the gate's check and `args` an optional list, so line 466's "G2 tests(AC1–AC3)" is `{gate: G2, check: tests, args: [AC1, AC2, AC3]}`; `{gate: G0, check: scope}` is always one of them (line 466; `governor-spec.md` §3.2) (entry form proposed; the gates themselves are specification 4's) |
| `exit_conditions` | Exit conditions | `{success, escalate: [...]}` (lines 468-470) |
| `owner_kept_act` | — | for gov-AIEOS, `true` when the task carries out or changes anything for which `governor-spec.md` §3.2 sets the owner-kept act input (an act that A51 item (4) keeps, a change to who may approve what in the governor, or a change that A54 point 2 keeps with the owner), else `false`. The Master Plan asks it of the first code task's contract (§8); this specification asks it of every gov-AIEOS contract (proposed). With A56, this declaration is how such an act is recognised besides the constitution's path rules; `false` never overrides a matching rule, and a rule that cannot be evaluated sets the governor's input (`governor-spec.md` §3.2) |

### 5.2 Handoff: `handoffs/<task id>-<session id>.md`

Front matter `task`, `session`, `commit` (the commit the session submitted, if any; proposed), then the six lists of concept line 537 as front-matter lists of strings: `done`, `not_done`, `assumptions`, `discoveries`, `risks`, `proposals` (proposed); the body holds free notes. Each item of `discoveries` and `proposals` also enters the log as one `claim` record whose `refers_to` is the handoff file and the item's place in its list (spec 1 §3; proposed); the file never makes them facts (line 537).

## 6. The event log: `events.jsonl`

### 6.1 Line format

One JSON object per line, in sequence order (concept line 874; spec 1 §4):

| Key | Required | Value |
|---|---|---|
| `event_id` | yes | a unique id; appending a known one has no effect (concept line 856) |
| `type` | yes | one of section 6.3 |
| `appended_at` | yes | UTC time, ISO 8601 with `Z` (proposed) |
| `seq` | yes | an integer: 1 on the first line, then one more than the previous line's (proposed) |
| `task_id` | when the event concerns a task | the task id |
| `fencing_token` | on every event that results from a lease holder's action (spec 1 §4), `task.submitted` among them | `{epoch, counter}` (spec 1 §8) |
| `corrects` | on a correction | the `event_id` it corrects (spec 1 §4) |
| `payload` | yes | an object, by type (sections 6.2 to 6.4) |

When the payload is a record whose `subject` is a task id, the envelope's `task_id` is that same id; a record about an intent entity has no `task_id` (proposed).

### 6.2 Records

A record (`record.added`, and the records that sections 6.3 and 6.4 name) has the fields of `governor-spec.md` §3.3 and B5:

| Key | Value |
|---|---|
| `record_id` | unique and idempotent (concept line 856) |
| `fact_kind` | `claim`, `observation`, `interpretation` or `authority` (B5) |
| `source_class` | one of B3, for example `agent_declared`, `deterministic_tool_external_ci`, `decision_agent`, `human_authority` |
| `recorder` | who or what wrote it |
| `subject` | the task id; also an entity id, for a record about an intent entity or a change request (this widening of `governor-spec.md` §3.3 is proposed) |
| `evidence_type`, `dimension` | for an observation, what it proves (concept lines 681-684) |
| `gate` | for a gate result, the gate id of the contract's `verification_plan` (section 5.1) |
| `outcome` | `pass`, `fail` or `blocking`; with `blocking_kind`: `out_of_scope`, `forbidden_path`, `violation`, `constitution` or `other` |
| `commit`, `intent_versions` | what it is bound to (concept line 728) |
| `approval_binding` | for an authority record, what it approves: `{kind, hash}`, where `kind` is `contract` (the `contract_hash`, at `task.approved`), `acceptance` (the `task_content_hash`, when it accepts a task: A42; `governor-spec.md` §4 rule 5), `change_request` (the change request's content hash) or `baseline` (the specification file's content hash, B9) (proposed) |
| `decision_ref` | for a `decision_agent` record or an `other_model_review`, the decision of the decision agent under which it was made |
| `models` | for an `other_model_review`: `{reviewer, implementer}` |
| `basis`, `stands_for` | for a `decision_agent_review` (`governor-spec.md` §3.3) |
| `refers_to` | for a record about another record, an event, a change request or a handoff item: its id (proposed) |

- Evidence types and dimensions are open vocabularies in v0.1: the names of concept lines 681-684 and 701-704, of B3 and of `governor-spec.md` §4 rule 3, and others that a requirement or an article names. A type is satisfied only by records that `governor-spec.md` §4 rule 3 lets satisfy it, so a type that no checker and no review counted there produces is never satisfied (fail closed; proposed).
- The core's own observations of spec 1 §7 and §8 are records with `source_class` `deterministic_tool_local` and `evidence_type` `unfenced_write` (a commit at recovery whose lease is not held) or `refused_submission` (a token or expiry refusal), `outcome` `fail` (proposed). A refused submission changes nothing (spec 1 §8), so it does not block the task; whether an unfenced write should block the task's acceptance is open (section 10).

### 6.3 Event types and payloads

The names of spec 1 §5, spelled as there. Payloads (all proposed except where a source is given):

| Event | Payload |
|---|---|
| `task.drafted` | `contract_version`, `contract_hash` |
| `task.approved` | `contract_version`, `contract_hash`, `approval_record` (the `record_id` of the authority record that approves the contract, bound with kind `contract`) |
| `task.blocked`, `task.unblocked` | `reason`; for `task.blocked`, `blocked_by`, the ids that block it |
| `task.submitted` | `commit`; `compensating`, `true` only for the event the core appends at recovery (spec 1 §7 step 1), else `false` |
| `decision.acceptance`, `decision.execution` | the decision record (section 6.4) |
| `task.done` | `decision_record`, the `record_id` of the decision that accepted the task |
| `task.stale` | `cause`, `intent_change` or `conflict`, and `refers_to`, the `event_id` of that `intent.changed` or `conflict.detected` |
| `task.replanned` | the new `contract_version` and its `contract_hash` (spec 1 §5.1) |
| `intent.changed` | `entity`, `from_version`, `to_version`, `change_request` (the `CHG-` id) |
| `drift.detected` | `paths` and `entities` concerned; the classification, the proposal and the choice follow as records whose `refers_to` is this event (spec 1 §5.3) |
| `violation.detected` | one `observation` record with `outcome` `blocking` and `blocking_kind` `violation` (spec 1 §5.3) |
| `evidence.stale` | `records`, the stale record ids, and `reason`, `commit` or `intent_version` |
| `conflict.detected` | `tasks`, the task ids, and `paths` or `interfaces` where they collide |
| `record.added` | one record (section 6.2) |

### 6.4 The decision contract (A15)

Bootstrap and native write the same JSON object (A15); it is the payload of `decision.acceptance` and `decision.execution`, whose event type says which decision it is. It is a record (section 6.2): `record_id`, `fact_kind`, `source_class` (the class of where the governor ran, for example `deterministic_tool_external_ci` in the CI channel; proposed), `recorder` (the governor's identity) and `subject` (the task id); then `decision`, which is `null` exactly when `error` is present (`governor-spec.md` §4 rule 7).

- Acceptance (`governor-spec.md` §6.1; B5): `fact_kind` `interpretation`; `decision` is one of `ACCEPT`, `NEEDS_REVIEW`, `INSUFFICIENT_EVIDENCE`, `NEEDS_REWORK`, `REJECT` (concept lines 299-303); and `task_content_hash`, `evaluated_commit`, `intent_versions`, `next_task_state` (a state name, section 2), `table_row`, `profile_used` (a list of `{dimension, required, satisfied_by, missing_types}`), `missing_gates`, `blocking`, `failed_gates`, `reverify`, `approval_record`, `policy_version`, `level_version`, `governor_identity`, `ruleset_version`, `scenario_set_hash`, `uncovered`, and for gov-AIEOS `rests_on_ai` (what rests only on AI review or AI approval, `governor-spec.md` §6.2). The key names are proposed.
- Execution: `decision` is one of the A15 strings, exactly `CONTINUE`, `CONTINUE_WITH`, `REPLAN`, `STOP: scope invalid`, `STOP: runtime insufficient`, `STOP: violation`, `BLOCKED`, `ESCALATE`. Its `fact_kind` is open (spec 1 §10 point 9), and its other keys are specification 3's (proposed).

### 6.5 The evaluation request

The governor's input (`governor-spec.md` §3.1), a JSON object: `task_id`, `task_content_hash`, `evaluated_commit`, `intent_versions`, `task_state` (a state name), `changed_paths`, `retry_count` (`{used, limit}`).

### 6.6 Commit trailers

A commit made under a lease carries `AIEOS-Task: <task id>` (concept line 847) and `AIEOS-Fence: <epoch>:<counter>` (spec 1 §8; proposed spelling).

## 7. The policy: `project.yaml`

Keys (concept line 868; A35): `policy_version`; `risk_rules`, a list of `{match, risk}` where `match` holds `paths`, `component_tags` or `touches` (lines 595-602) and the highest matching rule wins (line 592); `autonomy`, the level in force per risk class, `L0` to `L4` (lines 618-624), each with its `level_version` (A35; `governor-spec.md` §3.2), every class at L1 unless raised (A35); `default_profiles` by risk, for v0.1 low and medium only (lines 697-704; line 947); `auto_accept`, by risk class, absent unless the policy allows it explicitly (A35); `adapters` (specification 5). The names `default_profiles` and `auto_accept` are proposed. The content of the self-build's risk rules is the third M1 document's, not this one's.

## 8. Genesis, conformance and plan files

Their formats follow the documents that define them (`genesis-model.md`, `conformance-methodology.md`, the Master Plan) and are not set here; this specification gives only their place (section 3; proposed).

## 9. Before AIEOS governs its own build

No file of this format exists yet. Records of the bootstrap carry their recorder and are not authoritative (CR-001 E3; constitution INV-004); where the governor's records are kept before the event log exists is open (Master Plan §4 M2 and §10; spec 1 §9).

## 10. Open points

1. The layout (section 3) and the text for CR-001 E4: the owner's (A22; CR-002 part 8; DEF-0018).
2. Where `docs/plan/` and `docs/specs/` move once the layout is settled; proposed: `.aieos/plan/` and `.aieos/intent/specs/`. The published specifications have no front matter, so the move needs a conversion that adds it (section 4.2).
3. Writing the bound constitution as `constitution.yaml` (section 4.1), as its own task.
4. The keys of each constitution `tool` type (section 4.1).
5. The task-type vocabulary beyond `implementation` and `refactoring` (section 5.1).
6. The record type of an execution decision (spec 1 §10 point 9) and its keys beyond those of section 6.4 (specification 3).
7. Whether the core's observation of an unfenced write blocks the task's acceptance (section 6.2; spec 1 §10 point 6).
8. The formats of Genesis, conformance and plan files (section 8).
9. The choices marked "(proposed)": the UTF-8 and LF rule, the YAML/MD split and file names (section 2); the hash rules, the two task hashes and the full commit id; unknown fields as an error; `changes/`, the `CHG-` prefix, the change-request fields and the status derived from records (sections 3, 4.2, 4.3); `local/`, its path and tables, and the event log committed; the component and interface entries and the `component_tags` match; `becomes_article`; `contract_version`; `task_type`; the capability values and the budget value syntax; the verification-plan entry form; `owner_kept_act` in every contract; the handoff file name, its `commit` and its lists in front matter; `appended_at`, `seq` and its start; the `task_id` equality rule; the widened `subject`, `approval_binding` and `refers_to`; the open vocabularies; the core's observation types; the payloads of section 6.3; the decision contract's key names, `null` with `error`, `missing_gates` and `rests_on_ai`; the `AIEOS-Fence` trailer; the names `default_profiles` and `auto_accept`.

## 11. Revisions

- Revision 0: first draft (D-146, D-150).
- Revision 1: applies the eighteen findings of one read-only checker round (claude-sonnet-5-5), each verified against its source lines: two task hashes and what each approval binds; the decision contract as a record with its B5 fields; a payload for every event type; the constitution's `source`, `governance` category and per-type `tool` keys; the concept's acceptance-criteria form, the §8.2 capabilities and the budget value syntax; the verification-plan entry; components, interfaces and task types; the E4 text aligned with the tree; `owner_kept_act` with A56; no `status` in files; `CHG-` for change requests; the conversion of the published specifications; the local store's tables; proposed choices marked and listed in section 10.
