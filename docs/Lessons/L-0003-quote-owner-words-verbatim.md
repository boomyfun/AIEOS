# L-0003: Quote owner words verbatim

Rule: When recording or citing an owner decision, quote the owner's exact words with the transcript line, label any wording of Claude's as Claude's, and never add, drop, narrow or upgrade content.

- Status: active
- Category: accuracy
- Binding: record only. Related: working rules 4 and 6 in the rules book, and the decision agent's definition, which forbids text that says the owner decided something unless the owner's own words for it are found in the transcript.

## Pattern
Drafts drift from what the owner said. The drift takes the form of paraphrase, added rules, a narrowed scope, or a Claude proposal labelled as an owner decision.

## Occurrences
At least ten in session 2026-10-04-1817 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md):
- **2026-10-05 (:484 → DM A5 in 238fae0; found :3615).** The owner's permission "Claude code vẫn Có thể sử dụng WSL2" (:484; see the source notes in the session History) became the fact "sessions execute inside WSL2" in A5, without a check of Claude's own environment. GitHub still shows it until 79f5a39 is pushed. See also L-0007.
- **2026-10-05 (:1941, :1987, :2103).** D5 was read as requiring another model. It required only a fresh session.
- **2026-10-05 (:2282, :2331).** The CS-1 and CS-2 drafts added normative content that the decisions did not contain (3 blocking findings).
- **2026-10-05 (:2423, :2594).** Two drafting errors:
  - A34 and the CS-1 commit message labelled a Claude proposal as an owner decision.
  - A36 weakened "writes two records" to "may produce".
- **2026-10-05 (:3190).** A35 and A36 called proposed errata candidates "the content decided for CR-001" (blocking).
- **2026-10-05 (:3757).** The first memory-remedy drafts misquoted the owner and called a Claude recommendation an owner decision.
- **2026-10-05 (:3950).** Claude wrote that the owner had decided M4 option (a) themselves. In fact the owner had delegated the choice (:3890) and approved Claude's plan (:3912). The significance is uncertain.
- **2026-10-06 (:4603).** D-003 found eight faults in A41, (a) to (h), among them:
  - it paraphrased the owner's question 1;
  - it dropped one of the question's cases;
  - it narrowed "the whole project" to pre-Genesis.
- **2026-10-06 (:4895).** D-004 found "đổi" (change) narrowed to "reversing".
- **2026-10-06 (:5058).** The activation sentence of `aieos-decider.md` overstates the owner's yes, and its question-1 quote is not verbatim. Line 25 of the same file also turns the owner's "phan tích" (:4385) into "phân tích" (open, DEF-0002). Both were corrected on 2026-10-06 in session 8b846883, under D-025 (DEF-0002 item c).

Related: the automatic compaction summary silently corrected an owner typo (:4631).

Five in session 02bd7476 (../History/2026-10/2026-10-07-0033-hardening-choice-and-step-3-close.md and the History files of 2026-10-06 16:35 to 2026-10-07 00:19), all caught by the decision agent before the text reached the owner or GitHub:
- **D-030.** A pasted block was labelled "Lời owner" without its qualifier.
- **D-031, D-036.** Commit messages paraphrased the owner's words instead of quoting them.
- **D-034.** The owner's "bỏ qua" for P5 was first written as "Dropped".
- **D-041.** The first CR-001 draft added clauses that the source rows do not contain.
- **D-046.** The first finding said the owner had opened Task Manager and kept a screenshot; the owner had reported only the comparison.

## Why it happens
- Translating from Vietnamese and summarising both invite small changes.
- Claude wrote both the question and the record, so its own wording feels like the owner's.

## Prevention and detection
- Copy the owner's words from the transcript, with the line number. Never retype them.
- Mark Claude's wording, for example: "the rest of this row is Claude's wording" (as A38 to A41 now do).
- Before showing a record, compare every owner quote and every "owner decided" side by side with the transcript.
- When an owner decision sets a condition for a task, state that condition in the owner's words in the task's instructions (REG-0-lite closure record, lessons 5 and 7).
