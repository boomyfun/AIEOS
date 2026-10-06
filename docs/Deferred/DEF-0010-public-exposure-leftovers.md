# DEF-0010: Public-exposure leftovers

- Status: done
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
- 2026-10-06 (session 02bd7476): Claude put four questions to the owner (:672), and the owner answered "2 giữ, 3 không, 4 không, 5 giữ" (:676):
  - (a) A24 keeps the account names ("2 giữ"). Both names are already public through the GitHub repository and the commit authors.
  - Question 3 concerned a further history rewrite; the owner answered no ("3 không"). Its details are kept in decision file D-033, outside the repository.
  - (b) No request to GitHub Support ("4 không").
  - (c) The local backup refs are kept ("5 giữ"). They are still never pushed: explicit refspecs only, never `--all`, `--mirror` or `--tags`.
  - Status: done.
