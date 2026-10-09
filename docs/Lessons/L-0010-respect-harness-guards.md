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

## Why it happens
- An approval in chat is confused with a change in the harness.
- Retrying is cheap.

## Prevention and detection
- After a block, report it exactly and give two options: the owner runs the command, or the owner changes a setting.
- Retry only after the owner confirms that a setting changed.
- Never present a guess about why a guard fired as fact (L-0008).
