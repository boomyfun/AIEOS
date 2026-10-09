# L-0016: Give reviewers scratchpad copies only, and bring a tool slip first

Rule: Give every reviewer agent copies in the scratchpad only, with its tool rule as the brief's first line and no path into the repository, and bring any tool call outside that rule to the decision agent before the review's output is used.

- Status: active
- Category: review method
- Binding: record only. Related: decisions D-211 C6, D-218 Q2 and C2, D-219 Q1; L-0001 (act only within authorization).

## Pattern
Reviewer briefs said "Read, Grep and Glob only" in the middle of the text and named files in the repository's working tree. Reviewers still made shell calls, and one read-only `git status` in the working tree rewrote its index file. The worker then used the reviews before the decision agent had ruled on the slips.

## Occurrences
Four in session 2026-10-09-1248 (../History/2026-10/2026-10-09-1248-ci-revision-3-and-governor-contract.md):
- **2026-10-09 (first round, security reviewer).** One `ls` of scratchpad folders.
- **2026-10-09 (first round, correctness reviewer).** Three read-only shell calls, one of them `git status` in the repository's working tree, which rewrote `.git/index` (stat cache only).
- **2026-10-09 (D-218 request).** Both reviews used to fix the draft before the slips were brought; accepted as disclosed (D-218 Q2).
- **2026-10-09 (re-check).** One no-op call ("echo skip"), brought before the owner question as D-218 C2 required.

## Why it happens
A brief's tool rule competes with the reviewer's habit of checking things by shell, and a path into the working tree makes a read-only command able to touch it.

## Prevention and detection
- Copy what a reviewer needs into a scratchpad folder; name no repository path in the brief.
- Put the tool rule on the brief's first line.
- List every reviewer's tools by script before reading its output; any call outside the rule goes to the decision agent first.
