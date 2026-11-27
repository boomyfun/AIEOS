# DEF-0135: the findings of the two reviews of TASK-135 deferred at D-6256: a placement test, the read-set limit in the docstring, the tools/list check, the import chain of a test

- Status: done
- Opened: 2026-11-14 (../History/2026-11/2026-11-14-2148-m8-stage-8-task-135-the-judge-fix-accepted-and-landed-26136a0a.md)
- Deferred by: decision agent (A41, A51), D-6256 (the route to acceptance; the findings deferred to one DEF)
- Decision group: A (scheduling)
- Blocks v0.1: no (none is a breach of the contract of TASK-135; the first real run needs the fix, not these)
- Scheduled in: M8, as one small task, or with the first task that touches claude_code.py or its tests

## What
Four findings (three low, one informational) of the two Haiku 5.5 reviews of TASK-135 (commit 5bd65778; the saved reports in the lasting copy C:\Users\Admin\AIEOS-REG0-lite\sessions\26136a0a-b135-4cb1-9db0-95258ca6f5b5\scratchpad-evidence\TASK-135\: the A59 review, review_r1_exact.txt, and the per-article review, review_r2_exact.txt), each not applied under D-6256:
1. (the A59 review, review_r1_exact.txt, finding 1) No test fails if the new branch of claude_code._judge (`if tool in MCP_TOOLS`) were moved before the argument findings: the placement is not tested (no MCP name with a wrong argument; the argument tests use Write only).
2. (per-article review, finding 1) The reads of get_work_order and query are not in the observed read-set (mcp_server.py :67-70; claude_code_reads.py :92-93 skips every mcp__ name), so the allow widens a read path that was refused before; the docstring of claude_code.py does not say so (the contract has it only as AC5 (3); AC4 allowed no other sentence). Add the sentence.
3. (per-article review, finding 2) The drift test compares MCP_TOOLS with mcp_server.TOOL_NAMES, a derived constant, not with what the server's tools/list answer returns; a hand edit that broke only the TOOL_NAMES expression would not be caught. A test that calls handle() on tools/list would check what a client sees.
4. (per-article review, finding 6) tests/unit/test_claude_code.py now imports mcp_server (the drift test), which imports writer, base_inputs and context_compiler; a grep found no subprocess in them, but their import-time side effects were not read in full.

## Why deferred
None is a defect against the contract of TASK-135, and the first real run needs the fix at once; a second task commit would need new bytes, a new dry pair, a new CI run and new reviews (D-6256 option 2).

## Resume when
With the first task that touches src/aieos_bootstrap/claude_code.py or tests/unit/test_claude_code.py, or at the M8 exit review.

## Depends on
None.

## Log
- 2026-11-14: opened (session 26136a0a; decisions D-6255, D-6256, D-6257).
- 2026-11-27 (session 228f426b; closure pass 2 of the deferred items, D-7443, D-7485; decided by: decision agent (A41, A51), D-7485, D-7486): stays in M8 under point (6) (f): finding 2, the reads of get_work_order and query are not in the observed read-set (mcp_server.py :67-:70; claude_code_reads.py :92-:93). Schedule unchanged.
- 2026-11-28 (session 228f426b; TASK-171, accepted at D-7727, commit a2c808305d3f28df413e2771bfc247b4d3559a5a, docs/runs/TASK-171-acceptance.md; main CI runs 46058827716 and 46058827710 success): closed, done. 1: tests/unit/test_claude_code.py:393, which fails on a copy with the MCP branch moved first. 2: src/aieos_bootstrap/claude_code.py:16-18 and test_claude_code.py:357-358. 3: test_claude_code.py:400. 4, the worker's reading of the import-time code (parsed with Python's ast, nothing imported) of mcp_server, writer, base_inputs, context_compiler and the own modules they reach (eventlog, base_files, contract_path, gitread, records, resume_check, __init__): beyond imports and function definitions only assignments of constants (mcp_server.py:92-140 and writer.py:108-142 among them), calls of re.compile, frozenset, list, tuple, datetime.timedelta, TABLES.items and records._one_of (records.py:266-267), a read of os.devnull (gitread.py:100), class definitions, a few constant default values, __all__ lists and a __main__ guard (mcp_server.py:534-535); no statement run at import reads or writes a file, starts a process, opens a store or a connection, reads the environment or the clock, or changes state outside the module; the standard library imports were not read; review r1 found the reading consistent with the code as far as it checked, not every module-level line.
