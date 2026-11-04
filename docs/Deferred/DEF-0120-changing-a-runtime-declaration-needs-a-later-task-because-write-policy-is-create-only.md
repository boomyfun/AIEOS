# DEF-0120: changing a runtime declaration in the policy file needs a later task, because write_policy is create-only (found at TASK-117)

- Status: open
- Opened: 2026-11-05 (session a0a0bdef-5258-47a7-94c1-6ba559edca43; TASK-117)
- Deferred by: decision agent (A41, A51), D-4776
- Decision group: A (self-build)

## What
TASK-117 adds writer.write_policy(root, text): it creates .aieos/project.yaml only if the file is absent or empty, in the form of write_contract (AC4). It cannot replace or extend an existing file. So, once the state commit P1-3 has put the declaration into Git, a changed declaration (a new adapter, a changed tier, a changed max_risk, a measurement key) needs a later task that adds a replacing or updating writer, or an owner-kept manual change. The contract states this limit in AC8 and asks for this entry at acceptance.

## Resume when
A change to the declaration is wanted: for example the owner measures the runtime (every measurement of an adapter's assurance is the owner's, spec-02:248 at X3; the record's form is spec-02 section 10 point 12, open), or a second adapter is declared. Any raise of an assurance or of max_risk stays the owner's (spec-02:251 at X3; spec-05 section 10).

## Follow-ups owed
- A task that adds the replacing or updating writer, with its own contract and the critical profile (the writer is a security-critical part).

## Depends on
TASK-117 (AC4, AC8); the state commit P1-3.

## Log
- 2026-11-05: opened at the acceptance of TASK-117.
