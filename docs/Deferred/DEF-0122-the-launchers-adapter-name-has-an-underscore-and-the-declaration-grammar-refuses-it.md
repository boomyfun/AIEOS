# DEF-0122: the launcher's adapter name has an underscore and the declaration grammar refuses it, so `aieos launch` is refused at the step "declaration" (found at TASK-117)

- Status: open
- Opened: 2026-11-05 (session a0a0bdef-5258-47a7-94c1-6ba559edca43; TASK-117)
- Deferred by: decision agent (A41, A51), D-4776
- Decision group: A (self-build)

## What
launcher.LAUNCH_ADAPTER is 'claude_code' (launcher.py:1068 at X3, by Grep of the X3 work tree). The declaration grammar of TASK-117 (adapter_declaration.py, g5; TASK-117.yaml AC2) accepts only a lowercase ASCII word or words joined by single hyphens as an adapter id (spec-02:237, which launcher.LAUNCH_ADAPTER does not meet), and the declaration the task records (AC6) is for 'claude-code'. The step "declaration" of launcher.start is called with the adapter name the caller gives; launch_outside gives 'claude_code', which adapter_declaration refuses ("error"), so launch_outside ends at the step "declaration" with reason "declaration" and no lease, whatever the base holds. Before TASK-117 it ended at check 7 (not granted, "the runtime has no declaration") because the tier was None. Neither ever granted. The parser's id pattern, [a-z0-9]+(?:-[a-z0-9]+)*, also admits words of digits only, such as 123, where spec-02:237 and AC2 say lowercase ASCII words (review117_way2c finding F8); the effect stays within low, and the pattern is settled together with the id.

## Resume when
`aieos launch` or any path that calls launcher.start with LAUNCH_ADAPTER is to grant a task, or the first scripted run goes through the launcher.

## Follow-ups owed
- A task that makes the two names agree: either LAUNCH_ADAPTER becomes 'claude-code' (a change to launcher.py and its tests, its risk set by the risk rules) or the grammar accepts an underscore (a change to the contract's grammar and to spec-02 section 7.1, a specification revision approved by its own decision). P1-3 (the state commit of the declaration) and every scripted launch wait until a task has aligned the id and examined its role in leases and records (D-4767 C6). The adapter name is also the id in the events and the leases of other modules; a search of its other uses comes first.

## Depends on
TASK-117 (AC2, AC3, AC6); DEF-0101.

## Log
- 2026-11-05: opened at the acceptance of TASK-117.
