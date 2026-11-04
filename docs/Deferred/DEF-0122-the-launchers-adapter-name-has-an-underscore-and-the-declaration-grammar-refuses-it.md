# DEF-0122: the launcher's adapter name has an underscore and the declaration grammar refuses it, so `aieos launch` is refused at the step "declaration" (found at TASK-117)

- Status: done
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
- 2026-11-05 (session a0a0bdef): closed by TASK-118, accepted in decision D-4831 at the task commit X 66ca7c42b5836dfd0895f4668ed9830464123f6a (launcher.LAUNCH_ADAPTER is 'claude-code', which meets the id pattern of adapter_declaration.py:80; the agreement test test_the_launchers_adapter_name_is_a_declaration_id in tests/unit/test_launcher.py); X is on main since the push of D-4832 and the local fast-forward of D-4834; the branch CI runs aieos-checks 41921916719 and aieos-native 41921916870 both succeeded.
- 2026-11-05 (session a0a0bdef): note per TASK-118 AC3 (D-4831): the id pattern [a-z0-9]+(?:-[a-z0-9]+)* (adapter_declaration.py:80) admits an id made of digits only, such as 123, where spec-02:237 says lowercase ASCII words (review117_way2c finding F8); the effect stays within low and the pattern is kept unchanged; this task changes no specification, grammar or writer.
- 2026-11-05 (session a0a0bdef): P1-3 (the state commit of the declaration through write_policy) and every scripted launch stay later, each its own decision; the role of the adapter name in leases and records was examined at TASK-118 (decision D-4835, DA-1 and DA-4): at a base with no declaration the Resume Check refuses with "the runtime has no declaration" and no lease is granted.
