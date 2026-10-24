# DEF-0098: TASK-083's departures from specification 6, for its next revision

- Status: open
- Opened: 2026-10-24 (session 3797498a; TASK-083's contract, decisions D-2403 and D-2409)
- Deferred by: decision agent (A41, A51), D-2409 (the departures of TASK-083's two MCP tools, carried for specification 6's next revision).
- Decision group: A (a revision of specification 6, approved in its own decision; nothing here changes the specification).

## What
TASK-083 builds get_work_order and query in src/aieos_bootstrap/mcp_server.py over base_inputs and context_compiler. Its stated choices depart from specification 6 revision 7 (docs/specs/spec-06-mcp-protocol-and-work-orders.md) at these points:
- (a) query also answers the items the Work Order holds in full, wider than :38's "one item the Work Order names only by reference".
- (b) query answers only the refs the Work Order holds, narrower than :38's "an intent entity, constitution article or component that the contract's traces reach"; no rule for "reach" is written (:62 names the graph's edges only); any other ref gives out_of_scope.
- (c) A core_error carries its findings: the answer {"error": "core_error", "detail": [the findings]}, beside :74's closed vocabulary and the answer form {"error": <word>} of src/aieos_bootstrap/mcp_server.py :26-27.
- (d) AIEOS_BASE missing or out of form (not exactly 40 lowercase hexadecimal characters) gives no_session, which :39 and :74 do not name for the base; the base taken as part of the session's identity (:27 has the server take the base from the environment with the session id and the root; specification 7 :45).
- (e) The Work Order is compiled at each call, so :54's "the same object for the whole session" (repeated by specification 7 :55) holds only while the task's last task.approved and last decision.execution stay the same; a new grant, or a later lease on another task in the same session (tests/unit/test_writer.py :2235-2246), gives another object; nothing is stored (:55).
- A stale line left by TASK-083: src/aieos_bootstrap/context_compiler.py :38 ("No reader of the inputs and no MCP tool are here … Nothing calls build_work_order but its tests") is no longer true once mcp_server calls build_work_order; context_compiler.py was not in TASK-083's write set.

## Why deferred
Specification 7 :56 keeps specification 6's tool contracts unchanged and lists wording changes for a separate later revision of specification 6; a task cannot revise a specification (docs/** is forbidden to it). Specification 7 :56 ("Specification 6's tool contracts are unchanged") and its section 10 item 8 (:84) are no longer true in the code once these departures stand, and are to be corrected at specification 7's next revision.

## Resume when
At specification 6's next revision, or a task whose write set holds context_compiler.py (for the stale line); this item closes when each point above is either written into specification 6 or reversed in the code by its own decision.

## Depends on
TASK-083 (the two tools), TASK-082 (base_inputs), TASK-080 (context_compiler); specification 6 sections 4, 5 and 8; specification 7 sections 5 and 6.

## Log
- 2026-10-24: opened (session 3797498a; decisions D-2403, D-2409).
