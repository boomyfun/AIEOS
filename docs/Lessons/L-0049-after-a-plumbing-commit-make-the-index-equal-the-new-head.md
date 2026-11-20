# L-0049: After a plumbing commit, make the real index equal the new HEAD, and end the script with an empty status

Rule: A script that makes a commit by plumbing (a temporary index, commit-tree, update-ref) ends with `git read-tree HEAD` on the real index, and its after-checks include an empty `git status --porcelain --untracked-files=all`; otherwise the status shows the commit's change as staged ("MM").

- Status: active
- Category: tooling
- Binding: record only. Related: L-0043, L-0023; decisions D-6577, D-6578.

## Pattern
The temporary index holds the new tree, but the real index still holds the old one. After update-ref moves main, git compares the real index with the new HEAD and reports the change as staged, while the working file shows it as modified again.

## Occurrences
- 2026-11-20 (session dc7cf6ca; the worker's own claim until checked): the first dry run of commit_state_d6577.py, in a scratch clone, stopped at its own last check ("REFUSED: after: the status is not empty") with the status "MM .aieos/events.jsonl"; nothing was written outside the scratch clone; the corrected copy commit_state_d6577b.py added `git read-tree HEAD` after the update-ref, its second dry run gave an empty status, and the real run (D-6578) did too (the earlier executor session_capture.py restores the index with `git restore --staged`, so it did not show this).

## Why it happens
A plumbing commit moves a ref and leaves the working index alone, and nothing in the plan said which index the status is read from.

## Prevention and detection
- Run every new commit script in a scratch clone first and end it with an empty-status assertion (as commit_state_d6577b.py does).
- After update-ref on the checked-out branch, bring the real index to the new HEAD with `git read-tree HEAD` (the working tree is not touched).
