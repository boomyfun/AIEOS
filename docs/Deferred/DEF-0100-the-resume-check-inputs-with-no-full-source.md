# DEF-0100: the Resume Check inputs with no full source, for specification 3's next revision

- Status: open
- Opened: 2026-10-24 (session 3797498a; TASK-088's contract, decisions D-2582 and D-2584)
- Deferred by: decision agent (A41, A51), D-2582 ruling 1 (TASK-088 reads every input whose source exists today and
  gives a stated value for the rest; the rest is carried here).
- Decision group: A (specification 3's next revision is its own decision; nothing here changes a specification).

## What
TASK-088's resume_log_inputs.log_inputs gives these inputs a stated value, not a read one:
- dependencies' stale_evidence: read as true when the log holds an evidence.stale event of the dependency after its
  last task.done (TASK-088's reading); specification 3 and conformance-files.md section 9 (:94) do not fix its
  meaning, and the Resume Check checks it for form only (resume_check.py :245-250); an evidence.stale with no
  task_id (records.py :675) is never counted.
- budget_use for tokens, wall_time and human_attention: reported false (used 0), since no source reads a runtime's
  reports (specification 5); the Resume Check names each as uncovered (resume_check.py :648-650).
- budget_use's retries: used is read (the count of specification 1 section 5.1), but the contract's limit is a str
  (base_inputs.py :17 keeps values as strs), so check 8 gives "a form that cannot be parsed" for retries
  (resume_check.py :652-655; rv85b N11, disp85 row 17).
- articles' scope: each article's prose scope given as a str, running from "Scope: " to the first ". " or the line's
  end, since constitution.md states scope in prose, not as paths or components (constitution.md :30, :35); a scope
  that is not a mapping makes every article whose applicability is null or names the task's task_type applicable
  (resume_check.py :443-447, :425-426; specification 3 :45), a departure from conformance-files.md section 9's {paths,
  components} form, kept until specification 3's next revision (a null scope would leave an unlisted article out,
  :421-424).
- risk_rules' component_tags rules: given as their TAGS_MATCH entry's paths (src/** and tests/**), the risk rules'
  point 3 reading (risk-rules-gov-aieos.md :18), kept until the architecture names components (D-2602 C1).
- intent_current: each entity read as a file path and its version as the SHA-256 of the file (the self-build's
  contracts' form, not specification 1's "id and version"); an entity that is not a path in form, a non-UTF-8 or
  over-size file fails the call; an entity deeper than base_files.MAX_DEPTH whose folder is not listed gives null.
- check 8: with three budgets unreported and the retries limit a str, check 8 is inert for every budget of the
  self-build (its fail-closed backstop, specification 3 :47, never fires).
- the whole-call failures: a symbolic link, a submodule or an out-of-form name under a listed folder, and the
  repository read at one moment; an intent entity at the repository root lists the whole tree (base_inputs.py
  :415-418), so one such entry anywhere fails the call.
- articles' violated: null for every article at an unevaluated commit (no check result exists before CI); the
  Resume Check names each applicable one as uncovered (resume_check.py :624-625).
- observed_read_set: null by rule while no runtime's tier is measured (read_set_record.py :38-43; C6, P-LOC).

## Why deferred
D-2582 ruling 1: each needs a source or a reading that a specification revision fixes, or a change to resume_check
(TASK-008's code), which is not a readers task's.

## Resume when
At specification 3's next revision, or a task that changes resume_check's budget parse; this item closes when each
point above is read from a fixed source or ruled by that revision's decision.

## Depends on
TASK-085 and TASK-088 (the readers), TASK-008 (resume_check); specification 3 sections 1, 2 and 9;
conformance-files.md section 9; DEF-0097 (open; it closes at TASK-086's records).

## Log
- 2026-10-24: opened (session 3797498a; decisions D-2582, D-2584).
- 2026-10-24: written with TASK-088's records (decision D-2662).
