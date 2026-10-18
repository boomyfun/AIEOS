# DEF-0082: the next text change of claude_code_reads.py and its tests

- Status: open
- Opened: 2026-10-18 (session 0c786edd; decision D-1312 C2)
- Deferred by: decision agent (A41, A51), D-1312, after the way-2 reviews of TASK-065 at its head.
- Decision group: A (a text and test change of src/aieos_bootstrap/claude_code_reads.py and its tests, in a task of its own).

## What
TASK-065's module (src/aieos_bootstrap/claude_code_reads.py) was accepted with these points carried, each non-blocking:
- Text points:
  - The AC6 word check of tests/unit/test_claude_code_reads.py is partial (session 1947b313, the matcher, "live evidence is negative" and others are not matched) and its docstring says "each required point"; widen the list or narrow the docstring (R4-1, R3-3).
  - "The tool names are those seen in this project's transcripts" is wider than its source (MultiEdit and NotebookEdit never seen; PowerShell, Task and Agent not shown); say it of the covered name Read (R4-2).
  - The module does not say how much of the documentation page was summarised (characters 0 to 200000); say it (R4-3).
  - "No exception escapes" holds for Exception only, not BaseException; qualify it (R4-5).
  - "Lower bound at best" (coverage across calls) beside "over-inclusive" (a single call); state both senses (R2-4).
- Untested points:
  - Duplicate keys tested only at the top level, and only NaN among the constants; a lone surrogate, NUL or whitespace-only path is untested (R2-2, R5-3).
  - The parity test checks only a non-allow verdict and exit code 2, not the reasons, and only for the listed inputs (R3-1).
  - Mutant R5 is killed by the R2 and property tests, not by an R5 test (R3-2).
  - Key checks compare against the module's own RESULT_KEYS (R3-4).
  - test_deterministic's bytes(data) is the same object (R3-5).
  - No broken copies for the input kinds, Glob, MCP, the subagent class, a non-string file_path or a non-object tool_input (R3-6, R2-3, R5-4).
- Limits only, not for a text change: the commit message's "the tests of AC1 to AC9" (R4-4, permanent history) and the contract header's "carries tool_name 'Read'" (R5-2; the contract is not edited, D-359).

## Resume when
- With the next change of that module (for example the hook process, part CC-3's neighbour), or the owner's word.

## Log
- 2026-10-18: opened (session 0c786edd; D-1312).
