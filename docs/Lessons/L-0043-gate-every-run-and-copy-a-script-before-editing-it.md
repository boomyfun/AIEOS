# L-0043: Gate every run of a script whose hash is known, dry runs included, and copy a script before editing it so a diff exists

Rule: Run every script behind `sha256sum -c` with the hash taken from the machine (a dry run too), and make a copy of a script (`cp -n x x.orig`) before editing it in place, so that the decision agent has a diff to read.

- Status: active
- Category: process
- Binding: record only. Related: D-3955 C4, D-3977, D-3990, L-0039.

## Pattern
A script that was just made is run in the same call as its diff and hash, or an approved script is changed with an Edit that leaves no copy of the old text.

## Occurrences
- 2026-10-31 (../History/2026-10/2026-10-30-2323-m8-stage-8-task-106-the-base-tip-check.md, D-3955, D-3977): the second dry run of the commit executor, and a page builder's dry run, ran without a hash gate (both read-only); accepted once, with the rule that a script whose hash is known runs only behind its gate (D-3955 C4).
- 2026-10-31 (../History/2026-10/2026-10-30-2323-m8-stage-8-task-106-the-base-tip-check.md, D-3990): exec_def106.sh was edited in place with the Edit tool, so no diff file existed for the decision agent's condition; it read both texts instead and asked for a copy before editing from then on.
- 2026-10-31 (../History/2026-10/2026-10-31-1739-m8-stage-8-task-108-the-reader-of-the-last-handoff.md, D-4119): the dry copy of exec_108d.sh was run once before the request that asked for it (read-only, nothing written); the decision agent ruled it harmless and asked that it not be repeated.

## Why it happens
A new file has no hash until it exists, so the first run is done before a gate can be written; the Edit tool changes the file in place.

## Prevention and detection
- Make the file, hash it in its own call, then run it gated in the next call.
- Before editing a script under review: `cp -n x x.orig`; bring `diff x.orig x`.
