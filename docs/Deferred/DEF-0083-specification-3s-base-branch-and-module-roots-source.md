# DEF-0083: specification 3's source for the base branch and the module roots

- Status: done
- Opened: 2026-10-18 (session 1c0ea663; decisions D-1325, D-1326 C7)
- Deferred by: decision agent (A41, A51), D-1326 C7, after D-1325 found it outside the scope of specification 3 revision 5.
- Decision group: A (a text change of specification 3, in its next revision).

## What
- Specification 3 revision 5 (`docs/specs/spec-03-resume-check-and-decision-engine.md`, its section 1 input table, the row "The base branch's name and the module roots of section 4", and section 12 point 10) still says that specification 2 §7 has no key for the base branch and the module roots.
- Specification 2 §7 (revision 2 onward) has the policy keys `base_branch` and `module_roots`, with `main` as the self-build's default.
- So the row and point 10 are stale; the next revision of specification 3 cites spec 2 §7's keys, as revision 5 did for the observed read-set and the adapter declaration (citation only).

## Resume when
- With the next revision of specification 3, or the owner's word.

## Log
- 2026-10-18: opened (session 1c0ea663; D-1325, D-1326 C7).
- 2026-10-29: done: specification 3 revision 6 cites spec 2 section 7's keys in section 1 and section 12 point 10 (DM F72; decisions D-3604 and the decision that approves the row), in the commit that adds DM F72.
