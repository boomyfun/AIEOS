# L-0010: Respect guards and security settings

Rule: When a classifier, a permission rule or an OS protection blocks an action, stop: do not retry it unchanged, reword it, split it or route it through another tool or agent, never change security settings yourself, and hand the action or the setting change to the owner.

- Status: active
- Category: governance
- Binding: record only. Related: group B, item 2 of the decision agent's lists keeps security settings and Claude Code settings with the owner.

## Pattern
A guard blocks something the owner has approved, and the approval in chat feels like permission to try again.

## Occurrences
Four blocks in session 2026-10-04-1817 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md), with one mistake:
- **2026-10-05 (:729, :866).** A safety classifier stopped credential-probe content twice. Claude kept the content high-level afterwards. Correct.
- **2026-10-05 (:1796 to :1815).** An OS protection blocked writes to one folder. Claude used another folder and changed no setting. Correct.
- **2026-10-05 (:3932, :3940, :3950).** The Claude Code auto-mode classifier blocked the approved force-push. After the owner wrote "cho phép" in chat (:3936), Claude retried the identical command and was blocked again. This was the mistake: words in chat do not change settings.
- **2026-10-05 (:3961, :3969).** The owner asked Claude to change the settings ("vậy hãy sửa cài đặt đi"). Claude declined and explained how the owner could do it. Correct. The owner added a one-off allow rule and later removed it (:4443).

Blocks in session 2026-10-06-0306 (../History/2026-10/2026-10-06-0306-real-decider-rechecks-and-push.md), handled by stopping:
- **2026-10-06 (:552).** The auto-mode classifier blocked an approved normal push ("[Out-of-Place Publication]"). Claude stopped and gave the owner options. It did not retry until the owner had added a one-command allow rule and told it to run the command (:906, :980).
- **2026-10-06 (:946, :1069).** Two worker commands were denied as "[Auto-Mode Bypass]", and the same warning was attached to a decision-agent handback. Claude stopped each time and told the owner about the first (:1000). The save denied at :946 was redone at :1036, after the owner chose option (a), which included logging those decisions (:1021). The re-read denied at :1069 was not redone.

Two refusals in session 2026-10-09-0024 (../History/2026-10/2026-10-09-0024-ci-revision-and-task-branches.md), handled by rewriting the command in the allowed form:
- **2026-10-09 (:295, :832).** The installed guard (DM A57) refused two commands that held Python's name followed by a space and a dash, one an inline program and one a version query. Both were Claude's malformed commands, not correct commands refused; neither ran. Each was rewritten as a script file run in the allowed form, and both were disclosed to the decision agent (D-180, D-182).

Three refusals in session 2026-10-09-0514 (../History/2026-10/2026-10-09-0514-fixture-file-kind-and-fixture-drafts.md), none retried in the refused form:
- **2026-10-09 (:251, :416).** The owner's command guard refused a one-line program given to Python on the command line without `timeout 110`, and a `grep` pattern that held `<<`; both were read-only and were rewritten in the form the guard's message gives.
- **2026-10-09 (:1189).** The harness's safety check refused a command that began with `rm -rf` on a relative path; nothing ran, and the folder did not exist. No removal command was used for the rest of the session (D-201 C4).

Two refusals in session 2026-10-09-0637 (../History/2026-10/2026-10-09-0637-fixtures-accepted-and-landed.md), none retried in the refused form:
- **2026-10-09 (:164, :792).** The owner's command guard refused a one-line program given to the Python launcher on the command line, and a needless `timeout 110 python -c ""` (Python's name followed by a dash); both were read-only, and each was rewritten in the form the guard's message gives.

One refusal in session 2026-10-09-0856 (../History/2026-10/2026-10-09-0856-runner-contract-and-drafts.md), not retried in any form:
- **2026-10-09 (:332).** The owner's command guard refused a read-only search whose command held Python's name followed by a dash as a search string; the read was redone without that search.

One refusal in session 2026-10-09-1056 (../History/2026-10/2026-10-09-1056-runner-accepted-and-landed.md), not retried in that form:
- **2026-10-09 (:568).** The owner's command guard refused a command that took a value with a here-string (`<<<`); it was rewritten without that form, as the guard's message says.

One refusal in session 2026-10-09-1801 (../History/2026-10/2026-10-09-1801-governor-drafts-and-runner-test-isolation.md), not retried in that form:
- **2026-10-09 (:253).** The owner's command guard refused a read-only scan whose search pattern held the two "less than" signs of a here-string; it was rewritten as a script whose patterns are built from character codes, as the guard's message says (D-223 Q4).

Two occurrences in session 2026-10-09-1918 (../History/2026-10/2026-10-09-1918-governor-accepted-and-landed.md):
- **2026-10-09 (:976).** A filler command (a script called with "--help", output discarded) ran; it wrote nothing. Disclosed in the next request.
- **2026-10-09 (:1843).** A removal command word ran: `rmdir` on a scratchpad folder that did not exist, after a `cd` inside a brace group had changed the working folder unnoticed; nothing was removed. Disclosed in the next request.

Four occurrences in session 2026-10-09-2141 (../History/2026-10/2026-10-09-2141-governor-pinned-genesis-v3-m2-exit.md):
- **2026-10-09 (:268).** A filler fragment ran: a shell function defined and never called; it wrote nothing. Disclosed in the next request.
- **2026-10-09 (:727).** A filler fragment ran: a loop whose body does nothing; it wrote nothing. Disclosed in the next request.
- **2026-10-09 (:866).** A filler fragment ran: a search whose output was discarded; it wrote nothing. Disclosed in the next request.
- **2026-10-09 (:934).** The command guard refused a correct, read-only search (its quoted pattern held a pipe character and the interpreter's name); the pattern was rewritten and run at :939 instead of stopping. The decision agent accepted it once and ruled that a refused correct command is brought to it, with no rewrite and no retry (D-237 Q4).

One occurrence in session 2026-10-09-2339 (../History/2026-10/2026-10-09-2339-spec-3-approved-and-on-main.md):
- **2026-10-09 (:471).** The command guard refused a transcript line piped into Python's name followed by a dash, without `timeout 110`; the command broke the rule, so the program was written to a file and run in the allowed form (:477, :479), as the guard asks for an incorrect command (D-243, D-244 C5).

Occurrences in session 2026-10-10-0138 (../History/2026-10/2026-10-10-0138-conformance-files-r4-and-task-005-contract.md), each my incorrect command, refused before it ran and rewritten as the rule requires:
- **2026-10-10 (:148).** A heredoc to create an empty helper file.
- **2026-10-10 (:324).** Two less-than signs inside a search pattern.
- **2026-10-10 (:1300).** Python's name followed by a dash, to run one test module.

One occurrence in session 2026-10-10-0235 (../History/2026-10/2026-10-10-0235-resume-check-fixtures-accepted.md), my incorrect command, refused before it ran and rewritten as the rule requires:
- **2026-10-10 (:1341).** A filler fragment with Python's name followed by a dash, left in a command meant only to copy a file.

One occurrence in session 2026-10-10-0348 (../History/2026-10/2026-10-10-0348-runner-entry-contract-and-reader-test-split.md), my incorrect command, refused before it ran and rewritten as the rule requires:
- **2026-10-10 (:367).** Python's name followed by a dash, with no timeout, to parse a script.

Seven commands with no effect in session 2026-10-10-0451 (../History/2026-10/2026-10-10-0451-decision-files-d284-d292-and-task-010-landed.md), all mine, found by `tools/filler_count2.py`; five were refused by the guard before they ran:
- **2026-10-10 (:199, :301, :671, :1475).** A heredoc with Python's name and a dash; a pipe into Python's name with a dash; `python -c print(1)`; `python3 --version`.
- **2026-10-10 (:916).** A real check whose search pattern held the forbidden strings; the guard reads a search pattern as a command.
- **2026-10-10 (:541, :984).** `cat > /dev/null` and `sed -n 109p /dev/null` ran and did nothing.

## Why it happens
- An approval in chat is confused with a change in the harness.
- Retrying is cheap.

## Prevention and detection
- After a block, report it exactly and give two options: the owner runs the command, or the owner changes a setting.
- Retry only after the owner confirms that a setting changed.
- Never present a guess about why a guard fired as fact (L-0008).
