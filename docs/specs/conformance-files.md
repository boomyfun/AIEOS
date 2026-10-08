# The conformance files of gov-AIEOS: fixtures, the frozen set and the run record

> - **Status:** revision 1. Whether it is approved is recorded in DM section F, not in this file. It decides nothing that a decision matrix (DM) row or a bound document decides.
> - **What it is:** a document of A14 step 9, milestone M2 (Master Plan §4 M2), drafted under decision agent decisions D-194 (C3) and D-195 (P1, C2). It settles, for the conformance files of gov-AIEOS (A53) only, the canonical form and the fixture format that `conformance-methodology.md` §10 point 4 leaves to step 9, and the formats of conformance files that specification 2 §10 point 8 leaves open. It is not one of the seven specifications of concept §18 (lines 987-997) and takes no number among them. Decision files are kept outside the repository (`docs/WORKING-RECORDS.md`).
> - **Path:** `docs/specs/conformance-files.md` is interim, like specifications 1 and 2. The files it describes live under `tests/conformance/` until a core exists to write `.aieos/conformance/` (specification 2 §3; DM B7; constitution INV-004).
> - **Sources:** "CM" is `docs/pre-genesis/conformance-methodology.md` (bound, Genesis instance 2). "The set" is `docs/pre-genesis/conformance-scenarios-initial.md` revision 4, set version 2, 32 scenarios (Genesis charter version 2 §2 and §5). "GS" is `docs/pre-genesis/governor-spec.md`. "Spec 2" is `docs/specs/spec-02-aieos-file-format.md` revision 1 (DM F12, F16). "(proposed)" marks a choice of this document where its sources are silent; each one is listed in section 9.

## 1. Purpose and scope

- It fixes three file kinds that CM names but does not format: the executable fixture of a scenario (CM §2, last point), the frozen set file (CM §4) and the run record (CM §4). It also fixes the governor entry point that the runner calls, and how a run compares observed with expected results, no wider than CM §3.
- It changes no scenario, no expected result and no rule of CM. Approving a scenario stays as CM §5 says; freezing a fixture is a separate approval (section 7).
- Not in scope: the content of any fixture; the runner's and the governor's code (Master Plan §4 M2); the CI workflow (the owner's: A61; constitution SEC-003).
- Not covered by these files: a fixture gives the inputs of GS §3.2 as values, so how the governor derives them from the task contract, the requirements, the policy and the constitution is not tested by a conformance run; an acceptance that rests on such a run lists it as not covered (GS §6.2).

## 2. Files, paths and the canonical form

- `tests/conformance/set.json`: the frozen set file (section 3). `tests/conformance/fixtures/<scenario id>.json`: one fixture file per realised scenario (section 4). These paths are proposed; a run record is the runner's output in the CI channel, not a file of the repository (section 6).
- The fixture files and the set file are scenario files in the sense of constitution GOV-002 (section 8), and they are "code" in the sense of Master Plan §8, so a task that adds them needs an approved contract and the relay of its start.
- CM §2 lists repositories, commits and records as fixture material. A fixture realises the repository and commits only as values of the evaluation request (commit ids, changed paths) and as records; no repository is built (proposed).
- Canonical form, for every file of this document (proposed): JSON (RFC 8259) in UTF-8 without a byte-order mark; LF line ends; object keys sorted by Unicode code point; an indent of two spaces, one key or list item per line; an empty list written `[]` and an empty object `{}`; `true`, `false` and `null` allowed; integers only, no fractions or exponents; in strings, only `"` and `\` are escaped with a backslash, and control characters as `\u` with four lowercase hex digits; one final LF. A file not in this form is malformed (section 6). A file's identity is the SHA-256 of its bytes.

## 3. The frozen set file

| Key | Value |
|---|---|
| `scenario_set_version` | the version of the bound set the file realises: `2` |
| `scenario_set_file_hash` | the SHA-256 of the set's file at that version, as Genesis charter version 2 §2 binds it |
| `fixture_set_version` | this file's own version: `1` for the first frozen set, one more at each later freeze (proposed) |
| `scenarios` | one entry for each of the 32 scenarios of the set, in the order of the set's rows (the order of charter version 2 §5): `{id, row_hash, capability, fixture}`, where `row_hash` is the SHA-256 of the scenario's row line without its line end (decision D-115 C1's method; charter version 2 §5), `capability` is one of `Verification`, `Resume Check`, `Risk Engine` and `Capability Boundaries` (the set's section 1), and `fixture` is `{path, sha256}` of its fixture file, with `path` relative to the repository root and written with `/`, or `null` |

- The file holds the whole bound set. In M2 a fixture is written for each of the 19 scenarios of the Verification capability (ACC-01 to ACC-17, ADV-01, ADV-03); one that cannot be realised faithfully gets `null` (section 5). The other 13 have `null` and are `NOT_RUN` until their milestones (Master Plan §4 M2, exit; CM §3).

## 4. The fixture file

| Key | Value |
|---|---|
| `scenario`, `row_hash` | the scenario's id and row hash, equal to its set-file entry |
| `cases` | a list of cases, one per task the scenario's Given names (one for every scenario except ACC-13, which names three) (proposed) |

Each case (proposed structure):

| Key | Value |
|---|---|
| `request` | the evaluation request of spec 2 §6.5 |
| `inputs` | the inputs of GS §3.2, one object: `traces_to` (a list of entity ids), `risk` (`low`, `medium`, `high` or `critical`), `owner_kept_act`, `weakens_evidence`, `delegation_in_force` and `auto_accept` (each `true` or `false`; `auto_accept` for the task's risk class), `verification_plan` (a list of gate ids), `evidence_profile` (a list of `{dimension, evidence_types}`), `applicable_articles` (a list of `{id, evidence_required}`, the latter a list of evidence types as the constitution gives them), `policy_version`, `level_version` and `ruleset_version` (strings) (proposed spelling and forms of GS's inputs) |
| `records` | the records the governor reads, each in the form of spec 2 §6.2 |
| `when` | `evaluate` (acceptance is evaluated; `request.task_state` is `VERIFYING`) or `re_evaluate` (after a record is written; `request.task_state` is `IN_REVIEW`; GS §5, "Leaving IN_REVIEW"); a `when` that does not agree with `request.task_state` makes the fixture malformed |
| `expected` | `decision`: a list of decision values; `next_state`: a list of task states; `missing`: the complete list of `{dimension, evidence_type}` pairs reported missing (empty when none is); `reverify`: a list of record ids; `approval`: `null`, or `{record_id, source_class}` of the approval record that must be cited; `ai_approval_shown`: `true` when the decision must show that the acceptance rests on an AI approval, `false` when it must show that it does not; `not_fixed`: the names of the other keys of `expected` that the scenario does not fix |

- Every key of `expected` other than `not_fixed` is present with a value or named in `not_fixed`, never both; a fixture that breaks this is malformed.
- The key names of `expected` are this document's; section 6 says which field of the decision record each is read from. Expected values use only the concept's and the DM's terms: the decision values of concept lines 299-303, task states, dimensions, evidence types and source classes. No expected value uses a name that a later specification defines (CM §2).

## 5. Faithfulness

- A fixture realises exactly one scenario and names its id and row hash.
- `expected` comes only from the scenario's own Expected cell, read with its Source cell. Nothing in GS, in another specification or in the governor's behaviour supplies an expected value: an element the Expected cell does not fix is named in `not_fixed` and is not compared (CM §2, "not fixed").
- The Given comes from the scenario's Given cell and the set's section 1 defaults; where the task's risk is high or critical (ACC-16, ACC-17), its profile is that of `assurance-model.md` §5. Values that none of these fix (identifiers, hashes, times) are placeholders of their spec 2 form, and no expected element depends on them.
- A scenario that no fixture can realise faithfully gets no fixture: its set-file entry is `null` and it is `NOT_RUN`. It is never re-expected, narrowed or replaced to make a fixture possible (CM §5; CR-002 part 4 limit 8).

## 6. The run, the governor entry point and the comparison

- The runner calls one governor function per case with the case's `request`, `inputs` and `records`, and receives one acceptance decision record in the form of spec 2 §6.4 (proposed: the function `evaluate` of the module `aieos_bootstrap.governor`, both taken from the base, GS §4 rule 1). Where spec 2 §6.4 names `rests_on_ai` but not its form, the decision record gives it as `{entries, approval}`: `entries` the `{dimension, evidence_type}` pairs that rest only on AI review, and `approval` `true` exactly when the cited approval record is a delegated approval of the decision agent (GS §6.2) (proposed).
- Each key of `expected` is read from the decision record as follows: `decision` from `decision`; `next_state` from `next_task_state`; `missing` from the `missing_types` of each entry of `profile_used`, with that entry's `dimension`; `reverify` from `reverify`; `approval` from `approval_record`, whose `source_class` is read from the case's records; `ai_approval_shown` from `rests_on_ai.approval`.
- A case passes only if every key not in `not_fixed` is observed: the observed decision and next state are in their lists; the observed missing pairs equal the expected list as a set; every expected `reverify` id is in the observed list; the cited approval record and its source class equal `approval`; and the observed `rests_on_ai.approval` equals `ai_approval_shown`. No decision outside the expected list is emitted (CM §3). The comparison is on these values, never on wording.
- A scenario is `FAIL` if any of its cases fails. Otherwise it is `NOT_RUN`, never a pass, if its set-file entry is `null`; its fixture is missing or malformed; its fixture's hash differs from the set file; its row hash differs from the row in the bound scenario file read from the base; the entry point is absent; or a call raises or returns a record that is not a decision record. Otherwise it is `PASS` (CM §3).
- A run does not count, and every scenario of it is `NOT_RUN`, if the set file is missing or malformed, its hash differs from the hash its freeze approval binds (section 7), or its `scenario_set_file_hash` differs from the bound scenario file (CM §5: "Until approved, no acceptance may rest on the set").
- The run record (CM §4) is a file in the canonical form with these keys (proposed): `set_file_sha256`, `scenario_set_version`, `fixture_set_version`, `runner` (`{path, sha256}` of the runner's module at the base), `governor_identity` (GS §2), `commit` (the evaluated commit), `counts` (`true` or `false`, as the previous point says) and `results` (one `{id, result}` per scenario, in the set file's order, `result` being `PASS`, `FAIL` or `NOT_RUN`). It is recorded as one record of spec 2 §6.2 with only that section's keys: `fact_kind` `observation`, `source_class` `deterministic_tool_external_ci`, `recorder` the runner's `path` and `sha256`, `subject` the evaluated task, `evidence_type` `conformance_run` and `dimension` `functional` (proposed), `outcome` `pass` exactly when the run counts and every scenario with a fixture is `PASS`, otherwise `fail`, `commit`, and `refers_to` the run-record file's SHA-256. Only a run in the CI channel can count (CM §6; A19 (5)); its effect is advisory (CM §9).

## 7. Freezing a fixture

- Adding a fixture is a `normal_cr` with a fixture-freeze approval on its hash (DM B1, B10). For gov-AIEOS the decision agent gives these approvals in the owner's place (B10 note; A51).
- They are given in the decision that accepts the task that adds the fixtures, as separate elements before the acceptance itself: one per fixture file, bound to its SHA-256, and one for the set file, bound to its SHA-256. Each is an `authority` record of spec 2 §6.2 in the task's records file (`docs/records/<task>.jsonl`; decision D-188 C5), with `approval_binding` `{kind: change_request, hash}`, the hash being the frozen file's SHA-256 (proposed: spec 2 §6.2 gives this kind for a change request's content hash, and B10 makes adding a scenario a `normal_cr`); one DM section F row lists the set file's hash and names the decision that lists the fixture hashes.
- A frozen file changes only by a new freeze approval on its new hash (proposed). A change that makes a fixture's `expected` accept something its frozen version rejects (a wider decision or state list, a missing pair removed, a key moved to `not_fixed`), so that a record counts or a task is accepted where the frozen version does not, weakens evidence requirements and is the owner's; so is removing a fixture whose expected result is that a record does not count or a task is not accepted (CM §5, applied to fixtures; CR-002 part 4 limit 8) (proposed).

## 8. Fixture tasks and the constitution

- The task type `fixture` (proposed; it settles specification 2 §10 point 5 for this one value) is a task whose every changed path is either a file of sections 2 to 4 under `tests/conformance/`, or a test module `test_conformance_*.py` directly under `tests/unit/`, `tests/integration/` or `tests/property/`, the folders whose tests the CI channel runs, that checks only those files against this document and the bound scenario file. A task with any other changed path is not a fixture task.
- A fixture task is neither an implementation nor a refactoring task, so GOV-002, whose applicability is those two types, does not apply to it, as the constitution writes it. For every other article whose applicability names implementation, a fixture task is treated as an implementation task (proposed; stricter than the constitution's text). GOV-002 has no `evidence_required` (its check is deterministic), so its not applying adds and removes no entry of the task's evidence profile (GS §3.2, applicable articles), and every other article applies as it would to an implementation task: no evidence requirement narrows (CR-002 part 4 limit 8; GS §3.2, weakens evidence).
- GOV-003 applies: A29 counts fixtures and scenarios in the evaluator, so a fixture task changes the evaluator.
- The fixture files and the set file are scenario files: `tests/conformance/**`, and `.aieos/conformance/**` once it exists, are in the forbidden set of every `implementation` and `refactoring` task (constitution GOV-002; concept line 445).

## 9. Open points and proposed choices

1. The choices marked "(proposed)": the paths (section 2); the reduction of CM §2's repositories and commits (section 2); the canonical form (section 2); `fixture_set_version` (section 3); the structure of a fixture and its cases, the spelling and forms of GS's inputs and the keys of `expected` (section 4); the entry point's name, the form of `rests_on_ai`, the run record's file and its record (section 6); `change_request` for a freeze and the change rules of a frozen file (section 7); the task type `fixture` and its treatment (section 8).

## 10. Revisions

- Revision 0: first draft (D-194 C3; D-195 P1 and C2).
- Revision 1: applies the findings of one read-only checker round (claude-sonnet-5-5), each checked against its source lines: the run record as its own file with a record of spec 2 §6.2's keys only; `expected` keys of this document's own, each mapped to a decision-record field, with an exact `missing` set, the approval's source class and the AI-approval display, and every key present or `not_fixed`; expected values only from the scenario's own cells; the value forms of the inputs; more `NOT_RUN` and does-not-count conditions, with `FAIL` first; the canonical form and the set order completed; the fixture task type defined by its paths and treated as `implementation` except for GOV-002; GOV-003 named; the change rules of a frozen file marked proposed and widened to every acceptance-widening change; and, under decision D-196: fixture tasks may add their own test modules where the CI channel runs tests, GOV-002's non-application stated as the constitution's own applicability, `ai_approval_shown` compared both ways, and the derivation of GS §3.2's inputs stated as not covered.
