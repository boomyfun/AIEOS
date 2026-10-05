# Working records

> **Status: working records of the AIEOS build. Non-authoritative.**
> Claude and its agents write them during the work. Every statement is a claim, not evidence, and points to its evidence.
> Nothing here is a decision:
> - owner decisions are in `pre-genesis/decision-matrix.md`;
> - decisions of the decision agent are in its decision log, which is kept outside this repository.
>
> This repository is public and its history is permanent. Write nothing here that must not be public (see "Public-safety rules").

## The four folders

| Folder | Holds | Unit | How it grows |
|---|---|---|---|
| `History/` | what each working session did | one file per session, in a month folder | a new file per session; old files never change |
| `Progress/` | finished, verifiable outcomes | one file per month | entries are appended; each month starts a new file |
| `Deferred/` | work put off, with the condition to resume it | one file per item | a new file per item; its status changes in place |
| `Lessons/` | recurring mistakes and how to prevent them | one file per pattern | a repeat appends an occurrence to the existing lesson |

Why this split:
- **History and Progress grow with time,** so they are split by time (session, month). No file grows without limit, and closed periods are never edited.
- **Deferred items and lessons have a life of their own.** Each gets its own small file that can be linked by its ID:
  - an item is opened, resumed and closed;
  - a pattern can be seen again.
- **There is no hand-kept index.** File names and fixed lines are the single source of truth, and lists are produced from them (see "At the start of a session").

## Names and IDs

- History: `History/YYYY-MM/YYYY-MM-DD-HHMM-<slug>.md`. The date and time are the session's start in local time (UTC+7), so several sessions on one day sort in order.
- Progress: `Progress/YYYY-MM.md`.
- Deferred: `Deferred/DEF-NNNN-<slug>.md`.
- Lessons: `Lessons/L-NNNN-<slug>.md`.
- ID numbers:
  - the next number is the highest existing number plus one;
  - numbers are never reused;
  - files are never renumbered or deleted.
- Slugs are lowercase ASCII words joined by hyphens.

## At the start of a session

Read in this order:

1. **The latest History file:** its section "State at the end and next step".
2. **Every lesson rule:** `grep -h "^Rule: " docs/Lessons/L-*.md`.
3. **Open deferred items:** `grep -lE "^- Status: (open|waiting-owner)" docs/Deferred/DEF-*.md`.
4. **For decisions:** the decision matrix, and the decision log for delegated decisions.

If the session started from an automatic summary of an earlier conversation, check facts against these files and the raw records before acting on the summary.

## At the end of a session

End at a checkpoint: the work is finished and recorded, not in the middle of a change. Before ending:

1. Write the session's History file.
2. Append finished outcomes to the month's Progress file.
3. Open new Deferred items, and update the ones that changed. A finished item gets `Status: done` and a dated Log line. It is never deleted.
4. Add new Lessons, or append occurrences to existing ones.
5. Give the owner a short prompt for starting the next session.

These files are committed and pushed like any other change in this repository, under the same rules.

## Public-safety rules

- No e-mail addresses of any kind.
- No passwords, tokens or keys, and nothing that says where credentials are stored. Never copy probe content from trust-boundary measurements.
- No commit IDs or ref names from before the history rewrite of 2026-10-05.
- No names of unrelated projects, and no GitHub account, organization name or repository URL; write "the GitHub repository".
- No personal descriptions of the owner. Record requests and decisions only.
- Owner words are quoted verbatim, in Vietnamese, with the date and transcript line, and kept short.
- Text from advisors (other AI models) is summarized in a few words. It is never quoted at length, and never presented as an owner decision.

## Relation to other records

| Record | Where | Role |
|---|---|---|
| Decision matrix | `docs/pre-genesis/decision-matrix.md` | owner decisions and project rules (authoritative) |
| Decision log | outside the repository (owner's machine) | the decision agent's decisions, verbatim |
| Change-set records | outside the repository (owner's machine) | plans, execution records and their hashes |
| Session transcripts | outside the repository (owner's machine) | raw evidence; History cites their line numbers |
| Claude's memory and rules book | outside the repository (Claude only) | short project state, and Claude's binding working rules |
| Git history | this repository | what changed, when, by which commit |

How lessons relate to rules:
- **A lesson is a record, not a rule.** It becomes one of Claude's binding working rules only when the owner says yes and it is written into the rules book.
- **A lesson may add caution.** It never relaxes a rule in the rules book, the decision matrix or the decision agent's definition.
