# Session 2026-11-20 and 2026-11-21, fifth stretch (UTC+7, D-6795 to D-6818): M8 stage 8, BT3a (the CI-evidence module of DEF-0136 and DEF-0152), TASK-151: the BT3 design, the contract, the change, a pair of blind reviews, one fix commit, the acceptance by the decision agent and the landing on main

> - **Status:** working record, non-authoritative; written by Claude from the checkpoint files and the decision files; a claim, not evidence. Owner decisions are in `docs/pre-genesis/decision-matrix.md` (DM). Delegated decisions (each decided by: decision agent (A41, A51); none of them is the owner's) are in the decision files listed below (kept outside the repository, in `AIEOS-REG0-lite/decisions`). The decisions D-6795 to D-6798 of the design and the contract of this task are named in the header of `docs/tasks/TASK-151.yaml`; the contract's approval and its local commit are D-6799.
> - **Session and transcript:** session `dc7cf6ca-d094-4438-af81-93586ed7658b` (the same session as the pages of TASK-147 to TASK-150); the worker's checkpoints of this stretch are copied unchanged to `AIEOS-REG0-lite/checkpoints` and listed below.
> - **Models:** the main session `claude-sonnet-5-5`; every decision-agent instance `claude-opus-5-5`, definition revision 14 (SHA-256 a787e712...d5e7d, DM row A41); the two blind reviewers of TASK-151 `claude-haiku-5-5` in their own sessions (the listing agent_models_t151.py: every Haiku agent used only Glob, Grep, Read and SubagentHandback, no Fable agent, the main transcript Sonnet only). One further subagent transcript in that listing ran on Sonnet 5.5: the Explore agent of the BT2 reading (stated at the acceptance, D-6813 R3; lesson L-0044). No Fable (D-6206).
> - **Dates:** all times are UTC+7.
> - **Repository:** at the start of this stretch main = origin/main = 7777bbf2 (the records of TASK-150); at the end main = origin/main = 03c46d4812d07e2ea6b99dbbec5997d6f20d4166 (the TASK-151 fix commit; two task commits, dc367083 and 03c46d48, on the contract commit 0dd462be). This page is carried by a later commit.

## Summary

- **The task:** BT3a, the pure CI-evidence module of the evaluation runner (DEF-0136, DEF-0152): a core function `ci_evidence` that decides whether the saved CI data of ONE task commit may be used as gate evidence and, if so, turns it into the gate-result records of the maker `gate_records`. It checks in one place, before the maker is called, the duties that DEF-0152 names for the caller: the detect step of the log must name the task and carry the contract sha256, only runs of the commit's sha, the push event, the pinned workflow and the task branch count, all attempts must agree (a disagreement is refused), the plan entries are passed without the args key, and a task that changes anything under .github is refused. It fails closed with a closed set of reasons. The run-made plan's G3 "review" gate still has no CI evidence and stays uncovered; the owner's question (D-6770) is not answered here (DEF-0153).
- **The design and the contract:** the close of TASK-150 and the start of the BT3 reading (D-6795), the BT3 design: option (A) only, the detect step's output lines of a saved `gh run view --log` fetched by an executor step outside src, no network reader or credential in src (D-6796), the contract draft v1 returned and v2 with R7 (D-6797, D-6798), its approval and local commit (D-6799), the branch push, the fast-forward of main and the push of main (D-6800 to D-6802), the CI reads of the contract landing and the release of the build (D-6803).
- **The change (dc367083):** two new paths, `src/aieos_bootstrap/ci_evidence.py` (228 lines at the first commit; one public function; imports `hashlib`, `re` and `aieos_bootstrap.gate_records` only) and `tests/unit/test_ci_evidence.py` (466 lines, 39 tests, with two embedded log fixtures cut byte for byte from the saved logs of the TASK-150 CI runs and a test with the public `governor.evaluate`). Built in a scratch clone (D-6804), committed with its own scripts (D-6805, D-6806), pushed to the branch task/TASK-151 (D-6806); the branch CI succeeded and met the targets written first (D-6807).
- **The review pair and the fix:** two blind reviewers on Haiku 5.5 read the whole first head (D-6808, D-6809): both VERDICT findings, no BLOCKING (A: 2 SHOULD FIX and 6 NOTE; B: 5 SHOULD FIX and 8 NOTE). The decision agent settled the findings (D-6809): one real defect, a log with a lone surrogate was refused only after the maker ran and with the wrong reason; one proof gap in the choice of the highest (run_id, attempt); the rest became docstring limits and duties of BT3b (every attempt, every changed path including the old side of a rename, the metadata trusted like the log, the CI class asserted not verified, same-sha runs of other forms ignored). One fix commit (03c46d48: one behaviour change, docstring limits, six more tests; 45 tests; a mutation proof one process per mutant, 46 mutants all killed) built under D-6810, pushed under D-6811, its branch CI read at D-6812. The fix was NOT blind-reviewed and it changed behaviour (D-6809); the acceptance text says so.
- **Acceptance and landing:** the acceptance text `docs/runs/TASK-151-acceptance.md` and the DEF-0152 log lines were approved with exact replacements (D-6813); the decision agent accepted TASK-151 by explicit decision at D-6814 (evaluator paths: GOV-003 :94 and INV-011 :78 bar auto-accept); main was fast-forwarded locally (D-6815) and pushed (D-6816); the CI of main at 03c46d48 succeeded and matched the expected shape written first (D-6817, D-6818).
- **The numbers:** two commits on the contract commit; range numstat 241/0 and 555/0 (new files); 45 tests in the new file; 3363 tests in the whole suite (3318 at the base plus 45), one known skip; the CI runs 2908 + 229 + 226; `deterministic_rule: files 270, changed paths 2, findings 0`; GOV-003 base tests 3318 run, 0 failed; bandit zero issues in five runs.
- **The slips of the route (all before any effect or caught by a gate; for the lessons, entered by the records commit where a decision names them):** guard refusals of the worker's own command forms (L-0010); a literal byte-order-mark character that the editor wrote for a typed escape, in the test file and in the module (fixed before the task commit; the escape is built from chr()); the one-process mutation run whose failure count stayed constant (replaced by a fresh process per mutant); an expected value of the worker's own new test that was wrong at the first run (TASK-1500 is a well-formed detect line of another task); the expected shape of the first branch read that guessed GOV-003 wrongly (D-6803); a citation of the acceptance rule by the wrong line (L-0046); stale header comments in generated scripts (L-0039); the harness delivered each reviewer's report before the byte check of its prompt could run (ruled at D-6809: the checks ran straight after and were equal).
- **The departures (stated in the acceptance text):** the same-vendor review pair on Haiku 5.5 (D-6206); the fix commit not reviewed by the pair and a behaviour change; pyflakes and bandit only in the CI; the Explore agent on Sonnet 5.5; the identity override of the commit scripts left empty where the repository identity was already the no-reply address.

## State at the end and next step

At the end local main = origin/main = 03c46d48 before the records commit; the working tree is clean. The records commit (this page, the acceptance text, the DEF-0152 log lines and four lesson occurrence bullets) comes to the decision agent as one package. Next: its real commit and push on a records branch, then BT3b (the input assembler, the provenance records and the `aieos evaluate` wiring; a note v1 first, D-6796 C5), the owner's answer on the G3 question (DEF-0153), and the second real run (any launch needs the owner's typed yes).

## The decision files D-6795 to D-6818 (generated by script from the files outside the repository: name, size in bytes, SHA-256)

- `D-6795-task147-build-r153-d-6794-c5-and-c6.md` (12689 bytes) `401943875c186678aa2bb2041520895941581ef9e0df518de699aa85d0b5d035`
- `D-6796-task147-build-r154-d-6795-c3-the-bt3.md` (14855 bytes) `82f33463d664856338418c73de9a5078e7d650cdde325d706e1543a76adccca3`
- `D-6797-task147-build-r155-d-6796-c3-and-c4.md` (15369 bytes) `ccd80de57314300c32ee694d12bd8778a10f9ae6aff6940a70befb101d9ad283`
- `D-6798-task147-build-r156-d-6797-c1-to-c4.md` (8900 bytes) `7c0dbf6d0ce6761a22ff80d50ffca4977adc40f37c05ad99a1e745268af6ebc6`
- `D-6799-task147-build-r157-d-6798-c1-and-c2.md` (11348 bytes) `a148407e4420e94eef03d15530ddcaeba6111d6a8ee36117ce606bee5f6f71e3`
- `D-6800-task147-build-r158-d-6799-c2-to-c6.md` (12608 bytes) `2e4abfc96269ecee3e33ba53ef4b91a4c82c89f4b47c906c92c927d14b50e78a`
- `D-6801-task147-build-r158-d-6799-c2-to-c6.md` (12618 bytes) `100aa6925da0973d44e6f77382bbb42bee3d85f50c5d29cb1ed0029e80cb0259`
- `D-6802-task147-build-r158-d-6799-c2-to-c6.md` (12632 bytes) `c827545e2bc6c2a699959cf10a7f04e9f878d2026e024cd288de9f44d3d8ca66`
- `D-6803-task147-build-r159-d-6800-to-d-6802.md` (10551 bytes) `e8cd1e700db38551cb21165e4b6ba8984d431ce780c201b646158ca3208316bd`
- `D-6804-task147-build-r160-the-d-6803-c4-package.md` (12245 bytes) `380bc9c81916cd31b6507cc33eb561db43e4722b2746ac0fc7fb2698df3f6a95`
- `D-6805-task147-build-r161-d-6804-c1-to-c3.md` (9631 bytes) `aaecbcbb3f7207d02de22328b40d9fe37b17ab3d0c99a1a3c36a8b7ad383ae89`
- `D-6806-task147-build-r162-d-6805-c1-to-c4.md` (9242 bytes) `51bae4905b20af74a1369663b70cab17a2ddcc47a0e92a96a62406b487f4dcee`
- `D-6807-task147-build-r163-d-6806-c2-and-c4.md` (10106 bytes) `8748cee5e4febef726ab7674f2bc1652ad030defe41764ca2b2c5167c60459cf`
- `D-6808-task147-build-r164-the-d-6807-c1-request.md` (11153 bytes) `73d736fcf2c0eeec056d5d60982c0318803459acb059bbd67cef7dea7930a1b9`
- `D-6809-task147-build-r165-the-d-6808-c5-package.md` (15812 bytes) `42473e0bc6b8be041e7bbfaf155c27ea411e46fbd60bf6504ca6cd8cf2b4eff3`
- `D-6810-task147-build-r166-the-task-151-fix-build.md` (11432 bytes) `5cd2b2f104c4867a452306ee6e080313b516811ab91b1694d064db943d42e6df`
- `D-6811-task147-build-r167-the-task-151-fix-commit.md` (8950 bytes) `10ee7143ba9160088f3f58821f566188885667c1a022e425826ed9e58b168fcc`
- `D-6812-task147-build-r168-the-task-151-fix-push.md` (10496 bytes) `4ebe05ef5dba4a6d0109b8a01b34e3a3fecf213138b322cb0426714dfd99075d`
- `D-6813-task147-build-r169-the-task-151-acceptance-draft.md` (14795 bytes) `2138493f2ba79c6eaca340f5fe6ed826e9d27cf9f3ffc6d63a926fd5e492b0de`
- `D-6814-task147-build-r170-the-corrected-task-151-drafts.md` (11772 bytes) `24d8b9105833c962a9269a3b3a12547c8b12a5247ee593a367e870913db79b7c`
- `D-6815-task147-build-r171-the-local-fast-forward-of.md` (9094 bytes) `4c508668abfb997db65048a25ddc10a538d28e773d683558856c7939d768a78e`
- `D-6816-task147-build-r172-the-push-of-main-to.md` (9538 bytes) `e5bfa12168b114eb43295c7c04ff1c81d7bc767aa623622435b3fe5c59f50ba6`
- `D-6817-task147-build-r173-d-6816-c3-the-push.md` (8532 bytes) `fe4f3634820eb48fe371270a5160f286d49f603d7c188a9b10812fd41d2e4424`
- `D-6818-task147-build-r174-d-6817-c3-the-main.md` (9093 bytes) `0be11c4c0805bc054da987c525fa5f9085f13fd18fbb5349dfa8106b9f590a30`

Numbers in the range with no file in the folder when this page was made (a list generated by the same script): none.

## The worker's checkpoint files of this stretch (generated by script from `AIEOS-REG0-lite/checkpoints`: name, size in bytes, SHA-256; a snapshot at the time this page was made)

- `dc7cf6ca-...-bt2-closed-bt3-reading-start.md` (2875 bytes) `e1de9b0b9e5cfb1d90441b27b73bee0cb440ba6051046654a0fc09789f483796`
- `dc7cf6ca-...-bt3-design-decided.md` (4176 bytes) `a973c93048874de519e83e3f231294a86369b3b3943f95750e2f097e93ffa143`
- `dc7cf6ca-...-bt3a-acceptance-drafted-151.md` (1323 bytes) `ae095fedebeaa41ebf2a7f5a0c59feea7957df195b4b42e1c500ea1a8f29d518`
- `dc7cf6ca-...-bt3a-acceptance-v2-151.md` (1340 bytes) `92b711f6279eaefa4e640ddde73366a7d956cb0e3edfde65612e3db492d14079`
- `dc7cf6ca-...-bt3a-accepted-land-prepared-151.md` (1708 bytes) `e7ffa3397cc4973a9a8827ca71faea8d52dc90bee6d0ea531dc52e21fbcdb297`
- `dc7cf6ca-...-bt3a-build-done-151.md` (1866 bytes) `5cf9ff18e3dc6847796e17e6a5033a8cace46952fcba13dcd4135e732e53137f`
- `dc7cf6ca-...-bt3a-build-started-151.md` (2310 bytes) `aee01568766e646bde0907215a83ab21c94eb48a094b9a7fe1bd8289f26122cf`
- `dc7cf6ca-...-bt3a-contract-commit-151.md` (1994 bytes) `cb01dd0c552604da5cc100cd373c2fb686f20292c1317b104dbbd262cae57a14`
- `dc7cf6ca-...-bt3a-contract-dry-151.md` (2306 bytes) `6bed6276e1c30098fad66c2d870fb7129911a4c025ad683ed80ec91c3ce80f40`
- `dc7cf6ca-...-bt3a-contract-landed-151.md` (2727 bytes) `d757e6c8217ad43fe9f407460322a24cff09bde780753c6dfce160dc8df3005e`
- `dc7cf6ca-...-bt3a-contract-v2-prepared.md` (2396 bytes) `139c51e919bc94f01246e2632c4a5fc7fcfd4d929770bd87cb4b79b3048049a6`
- `dc7cf6ca-...-bt3a-fix-built-151.md` (1720 bytes) `54fe59b9d6893e7b1a22cbf6ef8c5a331a083aed4b844837d35b505a6fcdb83f`
- `dc7cf6ca-...-bt3a-fix-commit-real-151.md` (1398 bytes) `9861257452bff658332f00e12c5d23d8178f9d2744adbaf95da6133e06c72b28`
- `dc7cf6ca-...-bt3a-fix-pushed-151.md` (1357 bytes) `91d39b4a23751b93c381f424bbf69062eeed6bbc8c9b3f214d7f9c75239b7f77`
- `dc7cf6ca-...-bt3a-main-ci-read-151.md` (1690 bytes) `91f3e3f0576ace9e51a1bdceb724d2a086f7b825536d7f283d5b6a6404281627`
- `dc7cf6ca-...-bt3a-main-ff-done-151.md` (1289 bytes) `f2357e94a615945ee8d6216c178c771471f2d0da629f37043a949bc529bb5c11`
- `dc7cf6ca-...-bt3a-main-pushed-151.md` (959 bytes) `2dd024ee32e25efe0ff1dba53f3696994410689707b349abdb02ad44948f8848`
- `dc7cf6ca-...-bt3a-review-prep-151.md` (1353 bytes) `2e6384e62756d34d4b93c5ac187d83b4358aded2df0dd73711baf66bd4d6d023`
- `dc7cf6ca-...-bt3a-reviews-done-151.md` (1470 bytes) `9fbc9a027e03a01726965b3b97ad91044d308fbc66d86d8f98707e40127f5d0c`
- `dc7cf6ca-...-bt3a-task-commit-dry-151.md` (2556 bytes) `6110f30e3c7fa35503786a01ca6538433c7c5ea0902a10fd343ce62e5743ea89`
- `dc7cf6ca-...-bt3a-task-commit-real-151.md` (1895 bytes) `315b8d9da5744ccc2f4dec4b636a143df58dde273ad6f7d90918cca61f7503de`
- `dc7cf6ca-...-bt3a-task-pushed-151.md` (1285 bytes) `929408b5ecb3233549a9c546b44c7384552daab2ee1c29e762cb20c79f31942b`
