# L-0044: Before a reviewer's model is chosen, read the owner's standing rules on models and name them in the request

Rule: Before any reviewer, helper or auditor is given a model, search the memory and the decision log for the owner's instructions on models, and write the rule that applies into the request; a model the owner excluded is not used, whoever proposes it.

- Status: active
- Category: process
- Binding: record only. Related: D-1157 Q1, L-0038, D-4064.

## Pattern
L-0038 checks by machine that a reviewer's model differs from every model that did task work; it does not check the owner's own list. The owner wrote "đừng sử dụng model Fable, ưu tiên sử dụng opus 5.5 hoặc sonnet 5.5" (session c52ac282, transcript :1071; in translation: do not use the Fable model, prefer Opus 5.5 or Sonnet 5.5), and D-1157 Q1 read it as "no reviewer runs on Fable from now on". In TASK-107, when the usable models were listed, Fable was the only one left that had done no task work, and the code review, the way-2 review R7w and the counted way-2 review R7w2 were all sent to it. Neither the worker nor the decision agent cited D-1157; the acceptance rested on one of the three reviews.

## Occurrences
- 2026-10-31 (../History/2026-10/2026-10-31-1018-m8-stage-8-task-107-the-shared-resolution-of-a-task-contract-s-path.md, D-4048, D-4057, D-4058, D-4060, D-4064): three claude-fable-5-1 instances reviewed TASK-107 read-only; found by the decision agent while checking the records; the owner is asked one question (the DEF-0105 Log line waits for it).

## Why it happens
The rule lives in a decision of an old session and in the History files' header lines, not in a place a request template reads; the model choice was made from the list of models that had done no task work, which is a different test.

## Prevention and detection
- A request that proposes a reviewer or helper model quotes the owner's model rules (grep the memory, the decision log and the last History header for "Fable", "Opus", "Sonnet", "Haiku") and says which models are left.
- The History header of every session states the models used and whether any is excluded by the owner.
- If the usable set is empty or has one member, the question goes to the owner before the review is sent.
