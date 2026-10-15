# L-0020: A measurement record change trips OPS-002

Rule: Before a push that changes a path under docs/pre-genesis/measurements/ or the measurement protocol, expect OPS-002 to fail by design; say so in the request and to the owner beforehand (D-790).

- Status: active
- Category: verification
- Binding: record only. Related: decisions D-788, D-789, D-790; L-0019 (a CI check a dry run cannot foresee).

## Pattern
A change-set touches an owner-kept measurement path; the dry run passes, since it runs no CI step, and main's CI then fails the OPS-002 step, which routes such changes to the owner by failing.

## Occurrences
One in session 2026-10-15-0830 (../History/2026-10/2026-10-15-0830-the-benchmark-workflow-accepted-and-on-main.md):
- **2026-10-15 (D-789, D-790).** CS-201 added the owner-decided marker to the P-CRED baseline record; main's run 261 failed only OPS-002 ("a change to an owner-kept path, routed to the owner"); accepted as the step working as designed, since the change records the owner's own decision (DM A69).

## Why it happens
The request and the dry run checked the executor's own conditions, not the CI's path rules for the changed paths.

## Prevention and detection
- Before a request whose change-set touches a measurement path or the measurement protocol, name the OPS-002 failure in the request and in the owner text.
