# L-0033: A test helper's default must not be a value a test case passes

Rule: When a test helper takes an optional argument that a test also passes as a case value (None among them), give the helper a private sentinel as its default, never a value a case may pass, and check each case list against the helper's defaults before the first run.

- Status: active
- Category: tooling
- Binding: record only. Related: decisions D-3104, D-3110 (Q2); L-0004.

## Pattern
A helper such as run(argv, answer=None) reads None as "use the good default". A test then lists None as one of its bad cases and passes it through the helper; the helper swaps in the good answer, so the case tests nothing, or, as here, fails for the wrong reason. Static checks of the draft cannot see it; only a run shows it.

## Occurrences
One, in session ea6ea0a3 (2026-10-25, TASK-093):
- **D-3104.** test_answers_out_of_form listed the answer None among its out-of-form cases, and run() took None as the default good answer; the first unit run gave one failure (exit 0 and the good lines where the out-of-form finding was expected). The code under test was right. The helper was given GOOD = object() as its default (one Edit, chk93 and diff93 rerun, the file placed again by place93b), and the runs were then green.

## Why it happens
The helper's default and the cases are written at different moments, and None reads as both "nothing given" and "a value to test".

## Prevention and detection
- Give a helper's optional answer-like argument a sentinel default (GOOD = object()) whenever None, '' or 0 is a case value.
- Before the first run, read each case list of a test against the defaults of the helpers it passes through.
