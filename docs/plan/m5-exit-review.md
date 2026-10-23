# M5's exit review

> - **Status:** revision 0 (decisions D-1929, D-1930, D-2017 and the decision that approves it). It is not binding, like the Master Plan; it plans, and it approves no specification and no task. M5's exit is decided in the request of the change-set that adds this document, as its own decision of the decision agent (A41, A51; Master Plan §6, `docs/plan/master-plan.md:102`), DELEGATED and advisory, as M3's (D-415) and M4's (`docs/plan/m4-exit-review.md:36`, D-755) were; it is recorded in the working records (History and Progress) and the decision files, not here.
> - **Sources:** Master Plan revision 4 (`docs/plan/master-plan.md`), §4 M5 (:68-71) and §6 (:102); DM rows A41 and A51 (`docs/pre-genesis/decision-matrix.md:102`, :112), F57 (:290) and F59 (:292); specification 5 revision 5 (`docs/specs/spec-05-adapter-contract.md`, DM F57); specification 2 revision 9 (DM F59); the M5 coverage check of decisions D-1929 and D-1930 (kept outside the repository); the open Deferred items DEF-0004, DEF-0089, DEF-0092 and DEF-0093. Line references are to main at 912dceff.

## 1. What the review must rule

- Whether M5 exits now, and with which named limits (Master Plan §6, :102: a milestone with tasks exits when its deliverables' tasks are accepted and the decision agent approves the milestone).
- M5's goal (Master Plan :69): specification 5, the adapter contract; the Claude Code adapter (hooks that enforce the write-set and the shell allowlist, block `git push`, record the observed read-set; advisory until measured: A25, C6, CR-001 E1); the T0 manual adapter; the replay adapter (A12). Its owner act (:70): installing hooks or changing Claude Code settings (A51 item (4)).

## 2. M5's state: the goal against accepted work on `main`

| M5 element (Master Plan :69) | Accepted work on `main` | What is left |
|---|---|---|
| Specification 5, the adapter contract | `docs/specs/spec-05-adapter-contract.md` revision 5 (:3), approved in the owner's place (DM F57, `decision-matrix.md:290`) | section 11's open points and proposed choices (:98) stay open; section 11 point 6's text on the shell allowlist's source and reading (left there to specification 2's next revision and a later contract, now settled by specification 2 revision 9 and TASK-076) and the citations of the PreToolUse program at points 6 and 7 are stale (DEF-0093), for its next revision |
| Write-set enforcement | the judge `claude_code.py:288` (`judge` :335; TASK-061); the hook entry `claude_code_hook.py:162` (TASK-062); the PreToolUse program `claude_code_pretool_hook.py:343` (`_run` :308; TASK-072, TASK-074, TASK-076) | not placed (owner act); DEF-0092's points |
| `git push` block | the judge's push concern `claude_code.py:234` and :241 (TASK-061), recorded by the PreToolUse program | not placed (owner act) |
| Shell allowlist | the judge's matching `claude_code.py:327`; the entry check `claude_code_hook.py:111` (TASK-062); the reader `claude_code_shell_allow.py:306` with `parse_policy` :174, `parse_contract_shell` :219 and `combine` :262 (TASK-076); the PreToolUse program passes the one list for a Bash or PowerShell call (`claude_code_pretool_hook.py:223`, :327); the source and the rule in specification 2 revision 9 section 7.2 (DM F59, `decision-matrix.md:292`) | no list exists: no policy file and no contract with entries in the form, so every leased shell call stays refused (`claude_code_pretool_hook.py:74`); each entry is a policy change approved on its own; the entry check's two edges (section 3) |
| Observed read-set | the record `read_set_record.py:137` (TASK-064); the read-path extraction `claude_code_reads.py:122` (TASK-065); the store's `reads` table `writer.py:80` and `add_reads` :734 (TASK-067); the read hook program `claude_code_read_hook.py:154` (TASK-068, TASK-073) | not placed (owner act); the hook sees Read calls only and may lose a read silently, so the read-set is a lower bound (`claude_code_read_hook.py:49`); the record is written at the session's end by the launcher (specification 7, M7; `claude_code_read_hook.py:32`); DEF-0089's points |
| Advisory until measured | the channel states its own limits as unmeasured (`claude_code_channel.py:75`; TASK-063); every hook program says that nothing wires it into Claude Code (`claude_code_pretool_hook.py:8`, `claude_code_read_hook.py:5`) | measurement is the owner's (C6; DEF-0004) |
| T0 manual adapter | `t0.py` (TASK-060; `claim_event_id` :130) | none named |
| Replay adapter | `adapter.py:132` (`start`) and `replay.py` (TASK-051) | none named |
| The core's violation path tied by the lease | `session_violation.py:198` (TASK-069, TASK-070) | none named |

## 3. The entry check's two edges

- **Too narrow for the project's own runs.** The entry check accepted with TASK-062 refuses an entry whose first word's name is a program that runs code or commands, `timeout` and `python` among them (`claude_code_hook.py:68`), as specification 2 revision 9 section 7.2 states. So no list can allow the project's own command forms, for example `timeout 110 python <file> < /dev/null`, which the self-build's rules require for every Python run. Under a placed hook, the worker's own Python runs would stay refused, and each refusal with a live tied lease ends the session (specification 5 §11 point 5; specification 2 §7.2). This matters only once the owner places the hook; nothing is placed now. Ways out, stated and not chosen: a later change of the entry check in a task of its own; a launcher-side form of these runs in specification 7 (M7); or the owner's choice at placement (A51 item (4)).
- **Not a full guard.** The entry check's lists are a minimum, not complete (`claude_code_hook.py:44`): an entry for a program that runs code but is not on them (a versioned interpreter name, for example) passes the form check and allows everything that program does, a push it assembles while running included (specification 2 §7.2, "What an entry admits"). Each entry's approval has to weigh that reach; no entry exists now.

## 4. Named limits at the exit

- No hook is placed, no matcher is chosen and no Claude Code setting is changed: the owner's act (Master Plan :70; A51 item (4)).
- Nothing is measured: the adapters' enforcement stays advisory (A25, C6, CR-001 E1; DEF-0004). A hook that does not start, is killed or ends with another exit code lets the call go ahead, as Claude Code's documentation states (unmeasured; `claude_code_hook.py:24`, `claude_code_pretool_hook.py:105`).
- The contract's `forbidden` list is not enforced by the hook; the gates find a forbidden path afterwards (`claude_code_pretool_hook.py:95`).
- The PreToolUse program's tie, contract reader and judge compose on a Windows root, while CI runs on Linux, so that composition with the real store is shown only with stand-ins (`claude_code_pretool_hook.py:108`).
- The launcher that sets `AIEOS_SESSION_ID`, `AIEOS_ROOT` and `AIEOS_BASE` is specification 7's (M7); until it exists, a leased session would stop at its first judged call; the base is fixed at the grant, and a nested runtime chooses its own session id, root and base (`claude_code_pretool_hook.py:83`; DEF-0093).
- No shell allowlist entry exists (section 2); the entry check's two edges (section 3).
- Specification 5 section 11's open points stay open, among them point 8 (the path semantics of the read-set), point 10 (an abnormal session end: with no later start of that task, no read-set record is written) and point 12 (no bound on repeated STOPs); DEF-0089, DEF-0092 and DEF-0093 stay open with their resume conditions.

## 5. Proposal

- **Proposed:** M5 exits now, decided by the decision agent (A41, A51; Master Plan §6), DELEGATED, advisory, as M3 and M4 did, with the limits of sections 3 and 4 named.
- M6 (Master Plan :73-74) may then start with its specification's drafting; no M6 task starts before the owner has been told (section 6).

## 6. What the owner is told (plain Vietnamese; no question)

Giai đoạn 5 (các bộ chuyển tiếp) đã xong phần chương trình: các chương trình kiểm tra phạm vi ghi, chặn đưa lên GitHub, đọc danh sách lệnh được phép, và ghi lại các tệp đã đọc đều đã có và được nghiệm thu. Agent quyết định đã quyết định kết thúc giai đoạn 5 thay bạn, như các giai đoạn trước, khi lưu bản tổng kết này. Các chương trình này chưa được đo nên chỉ có giá trị tham khảo, và có thể để lọt nếu bị tắt hay hỏng. Vẫn là việc của riêng bạn, khi bạn muốn: đặt các chương trình chặn vào máy, mọi thay đổi cài đặt, và mọi phép đo. Hiện chưa có lệnh nào được phép chạy, và các lệnh chạy chương trình của chính dự án sẽ vẫn bị chặn khi bạn đặt chương trình chặn; cách xử lý điều đó sẽ được bàn sau. Giai đoạn 6 không cần bạn làm gì lúc này.
