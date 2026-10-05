# DEF-0010: Public-exposure leftovers

- Status: open
- Opened: 2026-10-05 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md)
- Deferred by: Claude (proposal, not a decision). Item (b) was left to the owner's own choice (:810, :4023).
- Decision group: B (a DM section A row, a history rewrite, a force-push or a deletion: decision agent group B, items 1 and 6)

## What
a. **Account names in A24.** DM row A24 names the owner's and the agent's GitHub accounts, and it has been public since the 2026-10-05 push. These working records avoid account names in public text, but nobody has asked the owner whether A24 should keep them. Changing A24 is a section A change. Removing the names from history would need another rewrite and force-push.
b. **Old commits.** Commits from before the 2026-10-05 history rewrite may stay reachable on GitHub by ID, in caches and in forks. Full removal needs GitHub Support (:810, :4023).
c. **Local backup refs.** Refs of the old history remain on the owner's machine. Keeping or deleting them is a deletion decision (group B). They must never be pushed:
   - push only explicit refspecs;
   - never use `--all`, `--mirror` or `--tags`.


## Why deferred
- (a) was noted as pre-existing by D-004 and in the CS-3 v2 self-check, but never raised with the owner.
- (b) and (c) were left open in the session.

## Resume when
At the next owner review of public content, or with the next owner question.

## Depends on
Nothing.

## Log
- 2026-10-05: history rewritten locally (:939) and force-pushed (M4, :4023).
- 2026-10-06: A24 noted as pre-existing during the CS-3 v2 checks (D-004; compaction summary :4631).
