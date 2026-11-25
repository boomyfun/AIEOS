# L-0053: Map every contract sentence to a code line before the first task commit

Rule: Before the first task commit, and again before each review request, the worker takes every sentence of the contract's acceptance criteria that speaks of the module and writes beside it the line of the code that meets it and the test that would fail without it; a sentence with no line or no test is a defect to fix before the commit, and a review prompt asks the reviewer to do the same reading literally, sentence by sentence.

- Status: active
- Category: process
- Binding: record only. Related: L-0034, L-0037, L-0046; decisions D-7085, D-7086, D-7090.

## Pattern
A module was built, reviewed as a draft and read twice by the decision agent, and one literal sentence of AC6 ("The result of every call (present or refused) is checked with evaluation_derive.plain_data_problem before it is returned") was not met: only the present answer was checked. The drafts, the tests and the first reviews followed the AC2 order, which places the check at the assembly step only.

## Occurrences
- 2026-11-25 (session 0be70981, TASK-158): the other_model_review of the commit 005e995a gave BLOCK on that sentence (D-7086); the fix needed a second commit, a second review pair and a new run of the whole route (D-7086 to D-7091).

## Why it happens
Two sentences of a contract can speak of the same check in different places; a reading by sections of the code follows the order section and skips a sentence that applies everywhere ("every call").

## Prevention and detection
- Write the sentence-to-line table before the first commit and bring it with the build request.
- Treat the words "every", "each", "never", "any" and "exactly" as separate checks of their own.
- A review prompt asks for a literal reading of every sentence of the acceptance criteria that speaks of the module (D-7090).
