# Session 2026-11-20, third stretch (UTC+7, D-6737 to D-6759): M8 stage 8, BT1b, TASK-148 (the capture-and-submit step of `aieos launch`): the contract, the change, a pair of blind reviews, one fix commit, the real-git harness, the acceptance by the decision agent and the landing on main

> - **Status:** working record, non-authoritative; written by Claude from the checkpoint files and the decision files; a claim, not evidence. Owner decisions are in `docs/pre-genesis/decision-matrix.md` (DM). Delegated decisions (each decided by: decision agent (A41, A51); none of them is the owner's) are in the decision files D-6737 to D-6759 listed below (kept outside the repository, in `AIEOS-REG0-lite/decisions`). The decisions D-6604 to D-6736 of the same task's earlier drafting are named in the header of `docs/tasks/TASK-148.yaml` and in earlier pages.
> - **Session and transcript:** session `dc7cf6ca-d094-4438-af81-93586ed7658b` (the same session as the pages of TASK-147 and TASK-149); the worker's checkpoints of this stretch were written as scratch files (cp300 to cp314) and copied unchanged to `AIEOS-REG0-lite/checkpoints` (D-6760 C2); listed below.
> - **Models:** the main session `claude-sonnet-5-5`; every decision-agent instance `claude-opus-5-5`, definition revision 14 (SHA-256 a787e712...d5e7d, DM row A41); the two blind reviewers of TASK-148 `claude-haiku-5-5` in their own sessions (the listing agent_models_t148.py: every Haiku agent used only Glob, Grep, Read and SubagentHandback, no Fable agent, the main transcript Sonnet only). No Fable (D-6206).
> - **Dates:** all times are UTC+7.
> - **Repository:** at D-6737 main = origin/main = c3036085 (lessons batch 8); at the end of the stretch main = origin/main = b0ef430faa03240495658b3f126f0519480f921b (the TASK-148 fix commit; two task commits, 8d59a65e and b0ef430f, on the contract commit 96463d6e). This page is carried by a later commit.

## Summary

- **The task:** BT1b, the core part of route (c) of DEF-0149: after a launched session returns, `aieos launch` writes the changes the session left in the working tree as one commit on `refs/heads/task/<id>`, submits it while the lease is held, and puts the tree back only after a submission that was accepted. The git-writing functions of the runtime module (TASK-147, fixed by TASK-149) are injected by the entry line of `cli.py`; the core imports nothing from the runtime package.
- **The contract:** a v3 of the draft, built on the modifications D-6633 (M1 to M16) with the design rulings D-6737 (injection of capture and restore; the matcher; the status parser; the lease facts), D-6738 (the pin scan found three test files, not one: they join the write set as named departures) and D-6739 (the launch reason "capture"; no restore after a refused submit; the forbidden key); checked by scripts (D-6740), dry-run (D-6741), committed on a contract branch (D-6742, 96463d6e), pushed (D-6743), fast-forwarded to main (D-6744) and pushed (D-6745); the CI of the contract commit was read (D-6746).
- **The change (8d59a65e):** seven paths: the new module `src/aieos_bootstrap/capture_submit.py` (319 lines, one public function `capture_and_submit`), `launcher.py` (+62/-7: the launch reason "capture", the keywords capture and restore, the step inside the try whose finally makes the end), `cli.py` (+21/-11: the keywords and the entry block that passes `task_capture.capture` and `task_capture.restore`), the new test file `tests/unit/test_capture_submit.py` (26 tests at the first head) and amendments of the three existing test files at exactly the named assertions. It was built in a scratch clone and brought as one package (D-6747), committed locally (D-6747, the real commit), pushed to the task branch (D-6748) and its branch CI read (D-6749: every pre-registered target met).
- **The real-git harness:** BT1b_harness_148_v2.py makes throwaway repositories and runs the new function with the real git reader and the real `capture` and `restore` of the runtime module and a stub submit; the acceptance run on a copy of `src/` of 8d59a65e (a new empty folder) gave 10 CASE blocks, 17 OK lines, 0 FAIL (D-6750). The commit message of 8d59a65e says nine cases; it ran ten (a correction carried in the acceptance text).
- **The review pair and the fix:** two blind reviewers on Haiku 5.5 read the whole first head (D-6750 to D-6752): both VERDICT findings, no BLOCKING. The decision agent ruled (D-6752) that two test gaps were real (the scope test did not show the forbidden and the state-directory refusals each alone; the BaseException test raised from a replaced step instead of the callee) and that three docstring statements needed correction; the worker built a one-purpose fix commit (b0ef430f: tests and docstrings only, the module without its docstring has an equal abstract syntax tree; a mutation proof shows that removing either scope branch or widening either handler to BaseException fails a new test; D-6752 C2, C3, D-6753), pushed (D-6754) and read its branch CI (D-6755). The fix commit was read by the decision agent, not by the pair. One reviewer prompt held 28 bytes more than its file (pasted by hand in error, the worker's account); a byte check showed the rest equal and the decision agent ruled the review valid with the deviation disclosed (D-6752).
- **Acceptance and landing:** the acceptance text docs/runs/TASK-148-acceptance.md and the lease-margin deferred item DEF-0151 were drafted and corrected by exact replacements (D-6756); main was fast-forwarded locally (D-6757) and pushed (D-6758); the CI of main at b0ef430f succeeded (aieos-checks run 44769437589, aieos-native run 44769436854; the conformance base run ran (by the worker's count, the head commit carries one task trailer); the CI read accepted at D-6759).
- **The numbers:** two commits on the contract commit; range numstat 319/0, 21/11, 62/7, 535/0, 12/9, 262/6 and 6/4; 28 tests in the new file and 14 new tests in `test_cli_launch.py`; 3283 tests in the whole suite (3241 at the base plus 42), one known skip; the CI runs 2828 + 229 + 226; `deterministic_rule: files 266, changed paths 7, findings 0`; GOV-003 base tests 3241 run, 4 failed (the four assertions the contract amends); bandit zero issues in five runs.
- **The slips of the route (all before any effect or caught by a gate; for the lessons, entered by the records commit where a decision names them):** three guard refusals of the worker's own command forms, each before the command ran (D-6747); an early run of the CI source rules on a launcher that bandit would have flagged for a try/except/pass, caught by reading (D-6747 C4); a harness rerun by mistake (D-6747 C4); a package that said "nine cases" where the harness ran ten (D-6747, D-6752); an expected forbidden-list count of 63 where the list holds 67 (D-6740); a request to draft the contract's v3 whose named base left out the earlier decision on the same contract, a gap the decision agent's own earlier condition shared (D-6737), and a draft that kept a restore after a refused submission, from a phrase of the decision agent's own earlier modification (D-6739); a writer's regex anchor (an unescaped parenthesis, the worker's account) and an evidence file in the wrong folder, both stopped by gates before any write (D-6751); a reviewer's first message that held 28 bytes more than its prompt file (D-6752; that it was pasted by hand is the worker's account).
- **The departures (stated in the acceptance text):** no per-file bandit line (the src-wide call covers the three files); the harness ran on 8d59a65e and is carried to b0ef430f by an equal abstract syntax tree; the fix commit not reviewed by the pair; the same-vendor review pair (D-6206); no shadow governor result; the last THREE defaults of the launch parameters checked where the contract says two.

## State at the end and next step

At the end local main = origin/main = b0ef430f before the records commit; the working tree is clean. The records commit and its landing are decided at D-6760 and later. Next: the records commit that carries this page, the acceptance text, DEF-0151 and the lessons, its push and the CI read of main; then BT2 (the gate maker), BT3 (the evaluation runner) and the second real run (any launch needs the owner's typed yes).

## The decision files D-6737 to D-6759 (generated by script from the files outside the repository: name, size in bytes, SHA-256)

- `D-6737-task147-build-r97-the-d-6736-memory-write.md` (14418 bytes) `3d1043044cc141d43129b96a923e52a2fc7d3c9780c3a9cac1e4f57092b43893`
- `D-6738-task147-build-r98-the-d-6737-c4-pin.md` (10182 bytes) `e9f4d34e231c14e5118c5196af3c8586892265be6ceeda4c46e88424e0f76174`
- `D-6739-task147-build-r99-the-task-148-bt1b-contract.md` (12954 bytes) `28f7d248cd6c154b1450d3519516185d4a1cfdea6f50ea24b688ba865af0d3cc`
- `D-6740-task147-build-r100-d-6739-c1-output-and.md` (10889 bytes) `46b875049eff6f398ae6123d1eef2d14b923a0a472374161c087085c3fa401e6`
- `D-6741-task147-build-r101-d-6740-c1-to-c3.md` (10224 bytes) `034471ee99f8c6e2460876f26d819f1abd591d6ea2c291c754c31894b36e3233`
- `D-6742-task147-build-r102-the-d-6741-dry-output.md` (9652 bytes) `898bf2bc5d0b6d9f10f8f66793849c5288a4331ad0007da6720e4157fa56d0bd`
- `D-6743-task147-build-r103-the-d-6742-real-commit.md` (9355 bytes) `f0b7128d892d073664f897c6128188907722f1ba0959cd1f2ffae45e1cb19d72`
- `D-6744-task147-build-r104-the-d-6743-branch-push.md` (8192 bytes) `bdfa718965d828b537085d9a703fb46a1b34041a2962e9bbd0868b3526d3fd99`
- `D-6745-task147-build-r105-the-d-6744-fast-forward.md` (9752 bytes) `9397acd35e47a05fa3833b98e26f1428ff616cf91a6d9873b0ee48331fe64425`
- `D-6746-task147-build-r106-the-ci-read-of-main.md` (14704 bytes) `66ea0007a3a24baa2d27a35ae52edd7785a7d7397ea3231a927e86b906084417`
- `D-6747-task147-build-r107-the-task-148-s6-package.md` (14617 bytes) `86a9e724699040b13c8ce2cd02e9ab650308f23ecde5afedc1f29ff4b287cf81`
- `D-6748-task147-build-r108-the-d-6747-c1-to.md` (10798 bytes) `5609c54dfc9806ef156b2418af5b839e8062bdde85396fdd2cd50371fb5b9da8`
- `D-6749-task147-build-r109-the-d-6748-c1-to.md` (10213 bytes) `04b8643a3e7c184302e3f12a57065d5f6332e9c5f932681266c9ed0f8c8c070d`
- `D-6750-task147-build-r110-the-d-6749-c1-request.md` (13727 bytes) `d1a363811afa410c85a1f78c9c0a9eecebf05b47adfbd4e76ee160f45433b631`
- `D-6751-task147-build-r111-the-d-6750-c3-maker.md` (10186 bytes) `83fadcec103c9bb4fd1714c83f30a47f27af1b12e6bae7c1e97bce8086fbd233`
- `D-6752-task147-build-r112-the-d-6751-c3-package.md` (12241 bytes) `e9a857f5d7aed6479077754a4e7c38e67de9e82c47d7debf29b0595d92f28e5d`
- `D-6753-task147-build-r113-the-d-6752-c4-request.md` (10213 bytes) `ae2b342117726b9594de928221e0855b6c368e6ebed479f19b5a87bdfaef3803`
- `D-6754-task147-build-r114-the-d-6753-c1-to.md` (10584 bytes) `1f709a34a9dc81be762e4717487e8f167b82d3a95bd6c13e155ebc1c27ed5c34`
- `D-6755-task147-build-r115-the-d-6754-c1-to.md` (14147 bytes) `8ac9eee14cf684bc5b6cee86bf9b618d2579a935e48ce2abe35b55040912bd75`
- `D-6756-task147-build-r116-the-d-6755-c1-drafts.md` (17640 bytes) `3f517f0d30a5cc71dc723e14e6847508ea625fd61b067ca552bb48dc53e7cbed`
- `D-6757-task147-build-r117-the-d-6755-c2-a.md` (8566 bytes) `cf48499f0f1f32ccf5ac1689f9c815b6e3b45ab488c1da2177ff16e2acf5c51d`
- `D-6758-task147-build-r118-the-d-6755-c2-b.md` (8509 bytes) `9700fdb6545fb9e53a0d0070610fa2593f530894674049d3be59c09a7deb2f84`
- `D-6759-task147-build-r119-the-d-6758-push-output.md` (10861 bytes) `bd0ac88c844675740742583d2142b8c9fe7222e654775dee5213fd514bfc1756`

Numbers in the range with no file in the folder when this page was made (a list generated by the same script): none.

## The worker's checkpoint files of this stretch (scratch files of the session, generated by script: name, size in bytes, SHA-256; a snapshot at the time this page was made; lasting copies with the same SHA-256 are in `AIEOS-REG0-lite/checkpoints` as `dc7cf6ca-d094-4438-af81-93586ed7658b-cpNNN.md`, D-6760 C2)

- `cp300.md` (1651 bytes) `bd2cc01065fd5f03aa4bffb99b29d6be118fbd48755aaeb79ce2553edff1b0de`
- `cp301.md` (1760 bytes) `5f7e972b075629caa627529676c82d21636b7b2347be0956ade7eee9f9375841`
- `cp302.md` (2694 bytes) `7d576cbb1488f14beb89e6a3b4e4588f21b9c64ba015a0775961b7b7db835e06`
- `cp303.md` (2114 bytes) `53ab0319af0608219ef071ec9b9a9aa1aee17a378135c95cd0070a5adffca1bb`
- `cp304.md` (1656 bytes) `4812f2e5e3b25a3c37f749e96b4c0ec8e46fd8d55efc6a0c82c79bc4633673ae`
- `cp305.md` (1985 bytes) `8e91e69be181cb4c4fe387acf37e891d79b2478a1b108f2b33876581ca751436`
- `cp306.md` (3165 bytes) `50a521ad944a894993a45a1edf5958fac7f2db24e6b2edc78f19a0d283c2aed2`
- `cp307.md` (2090 bytes) `9ca83b9d8b9849b1a0ad59e8f33a5fdb1b4084c7aebd286e0506fce84c995407`
- `cp308.md` (1783 bytes) `2910b5df48350467597d1118c99a7d69c9670429b712867f28b35340733eb437`
- `cp309.md` (1850 bytes) `9ebb0c746df4c9e039334d6b1ec096f38916f9872cfc8baf33b72481c68257ec`
- `cp310.md` (1784 bytes) `fa283acf10c6013a4040a086f15359890152c1eb6ff416a255e4664c791a0214`
- `cp311.md` (2479 bytes) `693024a7992e6373b05e52dfd143c3d4bcb2be1a037db0e6128977c7420017d4`
- `cp312.md` (1359 bytes) `ca9ad75e166753a86a95aab63474a3731f864ae635e16e75396ada8a6d53ad7c`
- `cp313.md` (2554 bytes) `52fa83485479534f99899507550f374e605efa5c2be092730aed2a33c7984aca`
- `cp314.md` (2382 bytes) `aabe79ca8725a2d60ec63790ea9320330916bcc1751764587098ad4a14a6f09c`
