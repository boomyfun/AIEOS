# DEF-0064: TASK-051's carried acceptance and its limits

- Status: open
- Opened: 2026-10-16 (decision D-991)
- Deferred by: decision agent (A41), D-991 (the bands of D-986 C4 and D-990 amendment 1 C3).
- Decision group: A (the order of work within an approved contract).

## What
- **TASK-051** (the adapter–core interface and the replay adapter; contract revision 1, commit C 11759796 on main; erratum E1 to AC7, D-987): its first task commit 65998de0 is on task/TASK-051 (aieos-checks run 319 passing). Five way-2 reviews at 65998de0: R1, R3 and R4 pass; R2 and R5 fail on one blocking finding (a commit_text that cannot be encoded as UTF-8 raised out of the replay after a grant). The fix and the dispositions D1 to D16 were read and approved by the decision agent under D-244 (D-991); they are kept in the session archive of session 78f4397c (its scratchpad's t051/ and revout51/ folders, with their hashes in the archive's manifest).
- **Left:** the second task commit on task/TASK-051 from the archived fix, its commit message carrying D12's wording ("a store that is not new (the document's epoch, counter 0)"); its CI read; the decision agent's own review, the other half of the cross-model entry; the acceptance (citing D1's fix and D-991 as the answer to R2's and R5's fail outcomes) and the landing on main.
- **Limits to carry at acceptance:** F-a (D-988): the repository has no project-state directory yet, so the replay's empty-log rule cannot tell a fresh scratch root from the self-build's own root before its first event; replay has no caller, and a caller must give a fresh root. D2: a start refused by the core leaves its session row open (AC8; reading R3). No observation or violation call; abnormal ends beyond the lease's expiry not handled; the write-set neither passed nor enforced; the token from the grant (M2 of D-983); a run against the real writer's files not tested; __all__ does not name the two modules.

## Resume when
- At the next session's start, after the decision files D-981 onward.

## Log
- 2026-10-16: opened (D-991).
