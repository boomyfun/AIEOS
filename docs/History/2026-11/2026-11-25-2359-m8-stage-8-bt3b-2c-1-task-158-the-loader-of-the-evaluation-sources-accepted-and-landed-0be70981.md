# Session 2026-11-21 and 2026-11-25, eleventh stretch (UTC+7, D-7059 to D-7098): M8 stage 8, BT3b-2c-1 = TASK-158 (the loader of the evaluation sources): contract landed, built, reviewed (one BLOCK, fixed), accepted, landed on main and CI accepted

> - **Status:** working record, non-authoritative; written by Claude from the checkpoint files and the decision files; a claim, not evidence. Owner decisions are in `docs/pre-genesis/decision-matrix.md` (DM). The acceptance of TASK-158 is the decision agent's (D-7095) and the evidence is same-lineage, not independent.
> - **Session and transcript:** session `0be70981-5509-45c7-8aef-d99c1e965c5a`, the continuation of `dc7cf6ca-d094-4438-af81-93586ed7658b`; the worker's checkpoints are in `AIEOS-REG0-lite/checkpoints` (entries 31 to 55 of the file named by the session id).
> - **Models:** the main session `claude-sonnet-5-5` (the worker; checked by script, `models_0be70981_158_out.txt`); every decision-agent instance `claude-opus-5-5`; every reviewer run `claude-haiku-5-5` in its own session with read-only tools (D-6206: never Fable).
> - **Dates:** all times are UTC+7.
> - **Repository:** at the start of this stretch main = origin/main = 96ca8f15a25cb9a556aa2eb76c5db62d5d2affe0 (records of TASK-157); the TASK-158 contract landed as 4e7026617fd7f44a2c2da7e13eda4b443b379fe5; the task landed as 005e995a12af18b991dad2daaaad1f7943be8c67 and 1ee645090ee98d62195c4c06639f2a5396bb6683; main = origin/main = 1ee645090ee98d62195c4c06639f2a5396bb6683 after the landing.

## Summary

- **The split:** BT3b-2c was split; 2c-2 was dropped and the guarded append and the provenance manifest moved to 2d, so 2c-1 (TASK-158) is the loader of the evaluation sources only (D-7059 to D-7066).
- **The task:** TASK-158 (risk high): src/aieos_bootstrap/evaluation_sources.py with load_sources, pinned_governor and parse_json (108 tests), and six entries more in EVIDENCE_DEFINING_PATHS (sixteen in all). intent_versions stays an open gap (DEF-0156). Five paths.
- **The build:** drafts in the scratchpad and a scratch clone; the decision agent returned the first drafts (D-7079, M1 to M12); a Haiku 5.5 draft review; fixes; the D2 script over four saved CI logs and the whole suite by chunks.
- **The BLOCK:** the other_model_review of the commit 005e995a found that load_sources checked only the present answer with plain_data_problem while AC6 requires every answer; the fix went into a second commit with no history rewrite (D-7086, D-7087); a new review pair on the head 1ee64509 gave APPROVE (Haiku 5.5) and APPROVE (decision agent, D-7091). Lesson L-0053.
- **The landing:** the task branch was pushed (D-7092), its CI matched 7 of 7 pre-registered items (D-7094), the task was accepted (D-7095), main was fast-forwarded (D-7096) and pushed (D-7097), and the main CI matched 6 of 6 items (D-7098). The origin/HEAD line that follows origin/main was accepted at D-7098.
- **Route facts:** the guard of the owner refused `python -I` (the condition D-7092 C6 was withdrawn at D-7093), a heredoc and stray `python -c` and `python --version` commands, each before anything ran; an old scratch folder (`c158`, the contract clone) was found and left; the Edit tool twice turned a typed escape into a literal byte-order mark, found by a byte scan and replaced by script; one request cited a wrong sha256 prefix (found by the decision agent).

## Open

- The records commit of TASK-158 (this page, the acceptance text, DEF-0156, log lines, lessons) and its push.
- BT3b-2d (`aieos evaluate`, the manifest, the append), BT5; the owner question of D-7016 M6; the DEF-0153 reminder; DEF-0136, DEF-0152, DEF-0153, DEF-0154, DEF-0155 and DEF-0156 stay open.
- The session's closing writes (memory update, next prompt) and the owner answer recorded in the decision matrix are not done at the time of this page.
