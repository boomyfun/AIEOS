# DEF-0156: the intent-version mapper: the source intent_versions of the evaluation has no producer, so no real evaluation can pass the gap check

- Status: open
- Opened: 2026-11-25 (session 0be70981; the records of TASK-158; D-7061 M8, D-7063 S13, D-7095)
- Deferred by: decision agent (A41, A51), D-7061 (Q-IV (ii))
- Decision group: A for a mapper that only implements a written spec rule; any new or changed rule of what a version is goes to the owner or waits for CR-002, as does any spec text (docs/specs/** is risk R6)
- Blocks v0.1: yes (proposed: eval_inputs refuses the open gap, so no real evaluation passes until a producer exists)
- Scheduled in: not scheduled; before the first real use of `aieos evaluate` (with or after BT3b-2d)

## What
The loader of TASK-158 (src/aieos_bootstrap/evaluation_sources.py) gives intent_versions as None, an open gap. Run-made contracts write intent_versions {} (launcher.py :1661, :1863; this is the launcher's gap); ci_evidence refuses an empty mapping and wants {name: "v" and digits} (ci_evidence.py :95-:99); self-build contracts hold path -> SHA-256 (evaluation.py :86-:87) and base_inputs.contract_at refuses dotted keys. For the run-made contracts that eval_inputs is for (eval_inputs.py :42-:43), spec-02 gives the entities a version field (requirement, specification, architecture, ADR and convention; spec-02 :77-:81, :103, :160, :177; governor-spec :32). Spec 2 section 6.2 revision 5 (D-1107, D-1108, DEF-0074; marked proposed) gives a mapping rule for gov-AIEOS (v<N> from the DM row that names the file's SHA-256 with "revision N", failing closed; its "fixed pattern" is not written in the docs: a History page names an archived scratchpad tool with three fixed forms) and says "at this revision no module computes the mapping".

## Why deferred
It is its own task: the run-made mapper reads the project-state directory, so DEF-0155 and the F3 standing condition apply to it; the gov-AIEOS mapper needs the pattern decided first.

## Resume when
A producer is chosen, one of: (a) a run-made mapper that reads the version field of each traced entity; (b) the gov-AIEOS section 6.2 mapper once its pattern is decided; (c) the producer in BT3b-2d. It closes when load_sources (or its caller) gives intent_versions for a real run and eval_inputs passes the gap check, with the duty of DEF-0152 about base_inputs.contract_at's refusal of dotted intent_versions keys read and settled.

## Related
DEF-0152 (the producer and that duty); DEF-0154; DEF-0155; DEF-0074; docs/tasks/TASK-158.yaml (AC9 (1)); docs/runs/TASK-158-acceptance.md.

## Log
- 2026-11-25: opened (session 0be70981; the records of TASK-158; D-7061 M8, D-7095).
- 2026-11-26 (session 228f426b; D-7118, D-7119, D-7120): a producer is chosen: the contract holds the traced entities as a path and a SHA-256, and the versions are read from the decision matrix by the rule of spec 2 section 6.2 (revision 5) with the fixed pattern the self-build already uses (the scratchpad tool map_versions.py; D-1130 approved its revision r1, and where its revision r2 was accepted is not yet shown, see D-7119 C2); group A (D-7119). The order is BT3b-2d-1, then 2d-3 (the mapper and the intent_versions of the loader), then 2d-2 (the command); a traced file whose bytes at policy_ref do not match the contract's SHA-256 is refused. 2d-1 (TASK-159, D-7120 and later) gives no intent_versions. Before the contract of 2d-3 the conditions D-7119 C2 and C3 apply (among them: show where revision r2 was accepted). This item stays open until a real run passes the gap check (D-7119 C5).
