# DEF-0007: Concept errata CR-001

- Status: done
- Opened: 2026-10-05 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md)
- Deferred by: Claude (proposal, not a decision). CR-001 is planned and its content candidates are recorded in DM B13 and B18. The remaining decisions belong to A14 step 5.
- Decision group: B (the concept and CR-001 are owner acts, DM A22; decision agent group B, item 5)

## What
Write CR-001 as a separate normative errata document in Vietnamese. Concept v0.5 stays byte-identical (DM A22). The content so far:
- **B13:**
  - adapter assurance measured per runtime × platform × version × configuration (§8.5);
  - Codex out of v0.1;
  - a bootstrap exception to §13.3;
  - layout;
  - removing the references to another project in §16 and §17 Q4.
- **B18 candidates:**
  1. §11: auto-accept only at L2 and above (A35).
  2. §5.3 and §7.4: human-produced evidence and IN_REVIEW (A36).
  3. The "(8.4)" cross-reference at §8.2, line 574.
  4. §9.2, line 703: the high-risk profile versus A6. This one is open (DEF-0008).
- **Not in B13/B18 and not yet checked:** concept self-contradictions found by Claude's read-only audit (:1474):
  - the Claude Code adapter declares its own strength while B13 is only proposed;
  - the Truth Hierarchy conflicts with the recovery rules;
  - the Resume Check is described as deterministic;
  - the risk classifier has no fail-closed default;
  - `tests/**` is in the agent write-set;
  - plus 17 implied obligations, counted in chat (:1474); the list exists only in that session's agent output.
- **CX-002:** the runtime read-set may not cover dynamic dependencies or configuration, so a freshness check may miss a change (A37). This is a known coverage gap for later spec work.

## Why deferred
The concept is frozen, and changes go only through CR-001 (A22). The A14 order puts the remaining decisions at step 5.

## Resume when
At A14 step 5, or earlier if the owner asks.

## Depends on
DEF-0008, for B18 (4).

## Log
- 2026-10-05: CR-001 first proposed (:579); errata form decided (A22, in 238fae0).
- 2026-10-05: concept audit (:1474); B18 recorded by CS-2 (5390902).
- 2026-10-06 (session 02bd7476): resumed at A14 step 5 (A44). A CR-001 draft (8 corrections from B13 and B18, 2 left open) was approved by the decision agent as a draft (D-041) and put to the owner for approval (A22). ../History/2026-10/2026-10-06-2245-a14-continues-at-step-5.md
- 2026-10-07 (session 02bd7476): the owner approved CR-001: "kết quả: có; đính chính: có" (:1927). It is `docs/pre-genesis/CR-001-concept-errata.md`. E4 ("layout") and E10 (§9.2, step 6, DEF-0008) stay open. Status: done. ../History/2026-10/2026-10-06-2309-a14-steps-2-to-4.md
