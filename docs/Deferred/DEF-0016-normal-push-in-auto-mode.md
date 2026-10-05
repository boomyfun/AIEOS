# DEF-0016: Make normal pushes to GitHub work in auto mode

- Status: waiting-owner
- Opened: 2026-10-06 (../History/2026-10/2026-10-06-0306-real-decider-rechecks-and-push.md)
- Deferred by: Claude (proposal, not a decision)
- Decision group: B (Claude Code settings are the owner's: decision agent group B, item 2)

## What
On 2026-10-06 the Claude Code auto-mode classifier blocked an approved normal push of 79f5a39 ("[Out-of-Place Publication]", transcript :552). The push went through only after the owner added a one-command allow rule and told Claude to run it (:906, :980). The owner then removed the rule.

Claude read the settings, read-only. The auto-mode environment description does not mention AIEOS or its GitHub repository; it describes a different setup in which nothing is published externally. Claude's guess is that this is why the push was judged out of place. The guess is not verified.

Options, all of them owner acts:
- the owner adds an accurate description of AIEOS (a public GitHub repository, where pushes of approved change-sets are expected) to the auto-mode environment settings;
- the owner runs each push themselves;
- a one-command allow rule per push, added and then removed.

## Why deferred
Changing settings is the owner's act, and the owner has not chosen yet. Claude offered to draft the description lines.

## Resume when
Before the next push, or when the owner asks.

## Depends on
The owner's choice.

## Log
- 2026-10-06 (session 5fd3e494): opened after the block at :552 and the push at :989.
