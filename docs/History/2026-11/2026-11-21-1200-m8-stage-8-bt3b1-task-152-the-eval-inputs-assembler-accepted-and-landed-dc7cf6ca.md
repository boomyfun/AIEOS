# Session 2026-11-21, sixth stretch (UTC+7, D-6826 to D-6865): M8 stage 8, BT3b-1 (the pure input assembler of the evaluation runner, DEF-0136 and DEF-0152), TASK-152: the reading, the contract, the change, a pair of blind reviews, one fix commit, the acceptance by the decision agent, the landing on main and the read of the CI of main

> - **Status:** working record, non-authoritative; written by Claude from the checkpoint files and the decision files; a claim, not evidence. Owner decisions are in `docs/pre-genesis/decision-matrix.md` (DM). Delegated decisions (each decided by: decision agent (A41, A51); none of them is the owner's) are in the decision files listed below (kept outside the repository, in `AIEOS-REG0-lite/decisions`). The reading of BT3b and the contract of this task are D-6826 to D-6830 (the contract's approval is D-6830).
> - **Session and transcript:** session `dc7cf6ca-d094-4438-af81-93586ed7658b` (the same session as the pages of TASK-147 to TASK-151); the worker's checkpoints of this stretch are copied unchanged to `AIEOS-REG0-lite/checkpoints` and listed below.
> - **Models:** the main session `claude-sonnet-5-5`; every decision-agent instance `claude-opus-5-5` (DM row A41); the blind reviewers of the first head and of the fix `claude-haiku-5-5` in their own sessions; no Fable (D-6206). A machine listing of the agent models of this stretch was not made for this page: the statement is the worker's claim, to be checked against the subagent transcripts.
> - **Dates:** all times are UTC+7.
> - **Repository:** at the start of this stretch main = origin/main = c0e1b61f (the records of TASK-151); at the end main = origin/main = e60561a21ac1fc855be59a17c78ed020956823ca (the TASK-152 fix commit; two task commits, 5302a2fe and e60561a2, on the contract commit 2f966c4b07bcaa340cb7182d958cec1c0cbfe710). This page is carried by a later commit.

## Summary

- **The task:** BT3b-1, the pure input assembler of the evaluation runner: a core function `eval_inputs` in the new module `src/aieos_bootstrap/eval_inputs.py` that assembles, from plain data, every input of `evaluation.evaluate_task` that a repository file can give, and REFUSES with one reason that names every open gap when one cannot be given. The duties that stay with BT3b-2 and BT3c are named in the log lines of DEF-0152.
- **The change (5302a2fe, e60561a2):** two new paths at the first commit, `eval_inputs.py` and `tests/unit/test_eval_inputs.py`; the fix commit changed both (the module is 304 lines, the test file 579 lines with 53 tests). Built in a scratch clone, committed with its own scripts, pushed to the branch task/TASK-152; the branch CI of the fix head ran 3416 tests (3363 at the base plus 53).
- **The review pair and the fix:** two blind reviewers on Haiku 5.5 read the first head (D-6846); the decision agent settled the findings and set the fix (D-6847): a contract whose autonomy has no budgets key is refused as retries, `requirement_profiles` must be a list whose dict entries have a text id, a text that UTF-8 cannot encode is refused, and the docstring states the real path of each source. The fix was reviewed (D-6858, D-6859).
- **Acceptance and landing:** the acceptance text `docs/runs/TASK-152-acceptance.md` and the DEF-0152 log lines were approved with exact replacements (D-6860); the decision agent accepted TASK-152 by explicit decision at D-6861 (evaluator paths: GOV-003 :94 and INV-011 :78 bar auto-accept); main was fast-forwarded locally (D-6862) and pushed (D-6863).
- **The CI of main:** read at D-6864 against the shape written first: 5 of 6 items MATCH, item 2 DEPART; accepted as SUCCESS by the decision agent at D-6865, with two flaws that are the worker's (the pattern of item 2 also matched file paths; item 1 needed a branch-filtered run list). The acceptance text quotes the comparison output unedited.
- **The slips of the route (for the lessons, entered by the records commit where a decision names them):** guard refusals of the worker's own command forms (L-0010); hashes, names and replacement counts typed or called "counted" where a machine did not count them (L-0039); statements not read against the source, and the shape of the CI of main with a pattern that matched paths and a run count that named no branch (L-0046). The route departures (the same-vendor review pair on Haiku 5.5; the fix commit and its review) are stated in the acceptance text.

## State at the end and next step

At the end local main = origin/main = e60561a2 before the records commit; the working tree is clean. The records commit (this page, the acceptance text, the DEF-0152 log lines and three lesson occurrence bullets) comes to the decision agent as one package. Next: its real commit and push on a records branch (records/TASK-152), the local fast-forward and the push of main, then BT3c (the policy file, a note v1 first), BT3b-2 (the provenance records and the `aieos evaluate` wiring), the pin tasks (BT5), the owner's answer on the G3 question (DEF-0153), and the second real run (any launch needs the owner's typed yes).

## The decision files D-6826 to D-6865 (generated by script from the files outside the repository: name, size in bytes, SHA-256)

- `D-6826-task147-build-r182-d-6825-c5-the-bt3b.md` (15021 bytes) `3b953b2a81573d17d075ebef8f3963399f5489f37250d225a4c04a1328eab41f`
- `D-6827-task147-build-r183-d-6826-next-2-to.md` (12371 bytes) `ae5fd4972649fafc9d75759a7e6058d6ee853d2de26acb81ca8b365ed366c2d2`
- `D-6828-task147-build-r184-d-6827-next-2-and.md` (13927 bytes) `ff4009f6c9321ee1aae735261787b650dee369a8401f639c38ea1adac4bfaf41`
- `D-6829-task147-build-r185-d-6828-c2-to-c4.md` (12030 bytes) `06acf4e8017ac55cc1c979f25e9a3f39603e73ba9c46b58d882d5cfe0a07aca6`
- `D-6830-task147-build-r186-d-6829-c2-to-c5.md` (10079 bytes) `7557935fa2978ca5dd0cd97ff9f4f5bcf2a50cc6b768ad64dafea869cd31fe46`
- `D-6831-task147-build-r187-d-6830-c2-to-c5.md` (10639 bytes) `f8031e670206b0d0fff0b286baf069710dfa689c5c43fec310f1145f9df4ad1c`
- `D-6832-task147-build-r188-d-6831-c3-outputs-contract.md` (9264 bytes) `4ead53cc7de299b144b4455cc8ba94d899924148e3bf40cce1f7fa780af5887b`
- `D-6833-task147-build-r189-d-6832-c3-outputs-local.md` (9135 bytes) `71936d81c36711049600367087c40acb66894aa75866848a4b7fa9ae217ad1db`
- `D-6834-task147-build-r190-d-6833-c3-push-output.md` (9514 bytes) `2495fc90760173ea996139f45278a7acb91d56b68f592f761027fc147cce4bec`
- `D-6835-task147-build-r191-d-6834-c3-the-main.md` (7491 bytes) `c78724c5bd16e1dffafbe6f6fbee0327d74cb97084deaa24295aa005d8d9f380`
- `D-6836-task147-build-r192-bt3b-1-task-152-build.md` (14018 bytes) `33507ed7c2352622adcd59f610f87d5862cacf8dbc2f47f289bfb9ffa47c3e67`
- `D-6837-task147-build-r193-bt3b-1-task-152-build.md` (9077 bytes) `47f980a04d8237636fe7d9f4249518fddd6fad8ba501e053ea2dd887baa9cd51`
- `D-6838-task147-build-r194-bt3b-1-task-152-mutation.md` (10057 bytes) `43ba4b890bbb05abfd63ccd2569d9f4ebe291fed6cb80bf0ff8dbe653013f2d1`
- `D-6839-task147-build-r195-bt3b-1-task-152-24.md` (8305 bytes) `0cfacdeebdc581a387059fb7c697b334ccf3b47f32c2a48f6ac1a3b2458527cc`
- `D-6840-task147-build-r196-bt3b-1-task-152-ci.md` (7385 bytes) `6c722d7e82489e51825f7cf02250336ef0b297546b8abc70de450d6bfc32ea08`
- `D-6841-task147-build-r197-bt3b-1-task-152-pin.md` (7769 bytes) `f6f8fa7d425f7cdeb8fb1ff494976dcb85e9f54aff46864f451b5851f9a8ffda`
- `D-6842-task147-build-r198-bt3b-1-task-152-pre.md` (9498 bytes) `9252165b042fdf1c124b5d8aaff075122e2a213841e847fe13d419ba71bdbcd1`
- `D-6843-task147-build-r199-the-commit-scripts-and-dry.md` (11774 bytes) `30d5cfe3cdae963101c630a18b2d6387047b35049475d22c2ba375f15b5efb8a`
- `D-6844-task147-build-r200-the-real-run-output-of.md` (11992 bytes) `6476ace8b1ce4f166c1d3ee516c4e3c702428398cfc4d894ce638b1c2581285e`
- `D-6845-task147-build-r201-the-task-152-branch-push.md` (12577 bytes) `86964e98fc5bcb4aeff4266a5d420b30a778ead780bfa1de53d7c432029fbe65`
- `D-6846-task147-build-r202-the-task-152-review-preparation.md` (11527 bytes) `c6d30ad0a0abced359b150d45f5a352bd433b3d2bc0e0eca5b9d36220adbf1c8`
- `D-6847-task147-build-r203-the-task-152-review-findings.md` (12204 bytes) `ef608b941f436b230e534319345ea20a80f4e8b9dbc698d7f25bba179af5f759`
- `D-6848-task147-build-r204-the-task-152-fix-step.md` (11429 bytes) `b7d9654fe80c527ed65b128d355f84f64c996e1d37b594763889b818f48e01b9`
- `D-6849-task147-build-r205-the-mutation-proof-of-the.md` (7904 bytes) `98cc8da3e73cf1770cdfe791b8d450eaeae50f65f79a35804d006db1e6c23593`
- `D-6850-task147-build-r206-the-24-slice-run-of.md` (8066 bytes) `c7d38ce167f7d876ce7f06d7fd327b327da89a0fec211af80fc93701545c51c5`
- `D-6851-task147-build-r207-ci-rules-and-ascii-on.md` (7003 bytes) `2d4925fef2bd29fa609be9170b5d76c9de469153fad956624b47ad72291cdf86`
- `D-6852-task147-build-r208-pin-scan-of-the-two.md` (10045 bytes) `744d6cc3dde2803e8aad849932deb34ce346d9c4b00f1a11e11f679b5fbe8de6`
- `D-6853-task147-build-r209-pre-registered-targets-for-the.md` (8223 bytes) `12842c88d5bff38ef11fc0741d788b779f0e23264fccebc23c06d904b7abafae`
- `D-6854-task147-build-r210-the-commit-scripts-of-the.md` (12053 bytes) `9a6b1c2d6cdb464cb8872caa5a85660cfd535120cc052a090e3cd4ab00ba62fb`
- `D-6855-task147-build-r211-the-real-task-152-fix.md` (9357 bytes) `d9dda75ccfa3240d0a7b000580fa4b3868bab36288ef9556775881ad0707603e`
- `D-6856-task147-build-r212-the-task-152-fix-commit.md` (11463 bytes) `d143d7df7a678c3b147361e05f5852c3858fc7233756e2f43f5461e4af354001`
- `D-6857-task147-build-r213-the-task-152-fix-push.md` (9576 bytes) `914c54447b92bf1895c30765e9592e0b35c1e39253647c77a564e2617355f41b`
- `D-6858-task147-build-r214-the-preparation-of-the-blind.md` (9746 bytes) `6232cc9d5c480a9c29920feb879d0e42e861029a2c3fc8421afbc0be0de0dabd`
- `D-6859-task147-build-r215-the-blind-review-of-the.md` (10438 bytes) `f559d4015304ff73bb79c63b91a8a4c30f7c2c034ddd80d73646eae5e3da3792`
- `D-6860-task147-build-r216-the-task-152-acceptance-draft.md` (14802 bytes) `56c3cbcfc65b8d70966bd1a10e8980fa96f6b31340090d1559d3f3337789eb5e`
- `D-6861-task147-build-r217-the-acceptance-of-task-152.md` (9586 bytes) `1fda40b098059148587052932dbee1aad0faf4ee15c662a24a5ccb2a5673b18c`
- `D-6862-task147-build-r218-the-local-fast-forward-of.md` (9325 bytes) `ac8bd508416eb5cfa915b2648e178ba22d21ce94dba5a0ab6536f481cf303316`
- `D-6863-task147-build-r219-the-push-of-main-to.md` (11153 bytes) `050a94602c9716c4e9428377874e9f4f5278c2144aba836bc2b0f86be80e5512`
- `D-6864-task147-build-r220-the-read-only-ci-read.md` (8092 bytes) `1b801d32598277f41e4131d50bad087816ea54cdf40ff4034a015ec7f1b66ce8`
- `D-6865-task147-build-r221-the-ruling-on-the-read.md` (9861 bytes) `fdc8a30acdb77af4f0956ef4f1f80453b06b6e1f38d7642a3e779f795de1f5ea`

Numbers in the range with no file in the folder when this page was made (a list generated by the same script): none.

## The worker's checkpoint files of this stretch (generated by script from `AIEOS-REG0-lite/checkpoints`: name, size in bytes, SHA-256; a snapshot at the time this page was made)

- `dc7cf6ca-...-bt3b-build-step1-r192-152.md` (1313 bytes) `ff6fd3ae460e143a6e32e726599009b919796c87a94f4580618dd6a47fc988d4`
- `dc7cf6ca-...-bt3b-contract-branch-pushed-152.md` (2224 bytes) `1551c34bca01469012cf48bd4754ea4b51be682807059e1d1fff32c2b2f8c1bc`
- `dc7cf6ca-...-bt3b-contract-commit-dry-152.md` (2159 bytes) `93b3a1c71e4d80d870412b12544eb8fd4889429c3f95e684d38ae44fce17e4f3`
- `dc7cf6ca-...-bt3b-contract-committed-152.md` (1913 bytes) `7d94940dd4ea179be59e2a0e922a8312ebded85bfbc43e9e74ce3f0df851941e`
- `dc7cf6ca-...-bt3b-contract-drafted-152.md` (2114 bytes) `45feebc5077ea885b25f135e752d7fa76e0d6c56a0ef7dc572e82094eb3b79d1`
- `dc7cf6ca-...-bt3b-contract-ff-done-152.md` (1282 bytes) `c93f2da0233d47e09a2fb457c24731a11ba09c6a109f1131a981f3626a1825b2`
- `dc7cf6ca-...-bt3b-contract-main-pushed-152.md` (1336 bytes) `c8e7c57f22d9f9d1c87ffa3fad5ed169346a0aafa4a2668490d6f3918f6b7c61`
- `dc7cf6ca-...-bt3b-contract-prepared-152.md` (2578 bytes) `419d61fcb347fd413d6b333e9f076ec63b84888aca4aa4945d85a65e07de52ae`
- `dc7cf6ca-...-bt3b-d6836-step1b-built-152.md` (1348 bytes) `f878a2b126856326744d4509b53e5522bfd869a6bd0025339470a8adf3fb2ee4`
- `dc7cf6ca-...-bt3b-d6837-mutation-proof-152.md` (1289 bytes) `f3fb7bde1e41ab796fbd63f580197b740a1bf60dc2186eef2ba93ae54f0a6776`
- `dc7cf6ca-...-bt3b-d6838-slices-run-152.md` (1539 bytes) `2d73235d2bf17df286c7e8466c28e4d8cd14b55b0c473f73de5bb2ccdbbbecc0`
- `dc7cf6ca-...-bt3b-d6839-ci-rules-ascii-152.md` (1214 bytes) `b3ed24cf83dbd70c2fdf7b2d34ba90a1084648fb6339216a5de91da463be98a3`
- `dc7cf6ca-...-bt3b-d6840-pin-scan-152.md` (1124 bytes) `eaff97cae7172d604e78a6096cdb50045da815a9ef3e6a455a11f27cefc82cfd`
- `dc7cf6ca-...-bt3b-d6841-ci-targets-152.md` (1093 bytes) `cfcf25062bad93d8c538aa2647bca8c649da7db195e699d643bf1036abb45f33`
- `dc7cf6ca-...-bt3b-d6842-commit-scripts-152.md` (1557 bytes) `590010c9f6011da1194344cdd41bab3744cd84d1c6ac5733602776d57178285f`
- `dc7cf6ca-...-bt3b-d6843-real-commit-152.md` (1103 bytes) `c805ef36adf1a96145c2ad6eb4382473d18f420d4ee2cefd082e8cff57d6abfb`
- `dc7cf6ca-...-bt3b-d6843-real-commit-done-152.md` (1545 bytes) `3187439fb1d2eb716781bb277c619134ec2ea4aa219d6572550bde2851dd8f22`
- `dc7cf6ca-...-bt3b-d6844-push-152.md` (1423 bytes) `8ba70ad72ea764a4b9712051b7981a07f02f4771de4bd295b735510a73306d93`
- `dc7cf6ca-...-bt3b-d6844-pushed-ci-read-152.md` (1947 bytes) `125cb92a986f22a6d491d19d85d4e598577991f824f56d4acf3de3cc38290a42`
- `dc7cf6ca-...-bt3b-d6845-review-prep-152.md` (1921 bytes) `e7be15c76edb1207859854d60af1ad244a9fe77727764246a4610ee42ea7f8e2`
- `dc7cf6ca-...-bt3b-d6846-reviews-152.md` (1717 bytes) `adfb0b8f5a03c3fc3c1b9c643341b5c66bfeb93306b703aa3bc3749c8bcf4058`
- `dc7cf6ca-...-bt3b-d6846-reviews-done-152.md` (1886 bytes) `1fa2c777dd6eb29a82b30e43fb8288913c6f4d3a7afbe5f8bf568b01b4cae751`
- `dc7cf6ca-...-bt3b-d6847-fix-step-152.md` (1999 bytes) `6b9c66d0626709558e221d79ed851743d0e5a275c82dd0a3de6e37bd275e015f`
- `dc7cf6ca-...-bt3b-d6848-mutation-fix-152.md` (1627 bytes) `d177b344d1102288a0b843ad4a0a322be4fc58f4820569df7234e9d9be3b108e`
- `dc7cf6ca-...-bt3b-d6849-slices-fix-152.md` (1415 bytes) `3d8e67475d63d0921faf0f6320bd4e8622c784cdc520df527175f9cdfd4e6f33`
- `dc7cf6ca-...-bt3b-d6850-ci-rules-fix-152.md` (1476 bytes) `67ed6a9c940c7e37ba57a6890d92dd94337fcaba76df7506223413b77555934e`
- `dc7cf6ca-...-bt3b-d6851-pin-scan-fix-152.md` (1302 bytes) `8d0d204e32137dc11a83aa486e4101496c857884352ab1edf1297820d2e504f5`
- `dc7cf6ca-...-bt3b-d6852-fix-targets-152.md` (2060 bytes) `cec179f1d59b455255dc2d8e3226fd2bb4d32d1f21df390f7f29674fbb693580`
- `dc7cf6ca-...-bt3b-d6853-fix-commit-scripts-152.md` (1563 bytes) `ec3a0113158f42710ddf40379240fb5c30172030caf2ca476234103b78a310be`
- `dc7cf6ca-...-bt3b-d6854-real-fix-commit-152.md` (1434 bytes) `545be1800c5233aa4c90d15d62e3b94eb792de09529fec2375354fcaf4f92a9f`
- `dc7cf6ca-...-bt3b-d6855-fix-commit-done-152.md` (1805 bytes) `712770ba19bda8df91e0db6cb225dd49c88427e98b6de2793e7756edfbf9683d`
- `dc7cf6ca-...-bt3b-d6855-real-fix-commit-run-152.md` (1310 bytes) `a259675329fe6ced98a0b4d8e548bdf700bf696bfe727f97ed13eb20ef5fa682`
- `dc7cf6ca-...-bt3b-d6856-fix-pushed-ci-152.md` (1958 bytes) `7f88c92bd5a9ba30334b8b691098ab8f1909e652f20b9bc4da546360590f472d`
- `dc7cf6ca-...-bt3b-d6857-fix-review-prep-152.md` (2193 bytes) `f3f28e27114b1ba932084eb0cbb8f6cdd9ee6e7abb39299e1a02727d7ec01737`
- `dc7cf6ca-...-bt3b-d6858-fix-review-done-152.md` (2169 bytes) `a6ce4d6d25fe7087aedf0ff5ee40842449af2050f2ad1946a8c578a8116d834d`
- `dc7cf6ca-...-bt3b-d6859-acceptance-draft-152.md` (2002 bytes) `0075d3b59003dbaad3bc692b64d149cfbc6afddf3c530a78b2ba65a66b337b0b`
- `dc7cf6ca-...-bt3b-d6860-acceptance-v2-152.md` (1843 bytes) `d3d3d1ce87bb852b174e7977e56d59e55d1f590a45b1e8e5f2ec297826ece0f5`
- `dc7cf6ca-...-bt3b-d6861-ff-scripts-152.md` (2140 bytes) `87e962bf84886851f98c9fa384c5532571a18118359de7bfd2e08c8fa43ab9e9`
- `dc7cf6ca-...-bt3b-d6862-ff-done-push-pkg-152.md` (1724 bytes) `fa123470bb5e947c7a5a0b2554c5765a82b8719a161d64ab9b19e8a1368d61c9`
- `dc7cf6ca-...-bt3b-d6863-main-pushed-152.md` (1438 bytes) `8621ac03b5fd7c6013b85ed817e0aa0d0763386420b9b4de88582f57aba32bbc`
- `dc7cf6ca-...-bt3b-d6864-main-ci-read-152.md` (2555 bytes) `8eff0a5db1ee7973694a5cd368550b0c309360272a661047eafcb7ac64aa0851`
- `dc7cf6ca-...-bt3b-main-ci-read-and-build-step1-152.md` (2981 bytes) `e199605a9ad3ef69f2ec15d64dc6c846a50bd816449f893482025d537fa87d59`
- `dc7cf6ca-...-bt3b-records152-stage1-texts.md` (1490 bytes) `460f6e01a5d6ba42183cde925e290ea96cc5e716c8da1afd8030b826ac15fd5a`
