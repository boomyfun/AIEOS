# DEF-0052: the review findings carried from TASK-024, the Git reader

- Status: open
- Opened: 2026-10-12 (decisions D-580 and D-584)
- Deferred by: decision agent (A41), D-580 (the dispositions F1 to F17 of the first round of five way-2 reviews, and erratum E1) and D-584 (the dispositions G1 to G8 of the second round of three, on the fix).
- Decision group: A (tests, limits and caller requirements within the self-build).

## What
- **Erratum E1** to TASK-024 revision 0 (decided by: decision agent (A41, A51), D-580; its exact text is in that decision's file): run refuses, before any process starts, a PATH that is empty or, split by os.pathsep, has an empty or non-absolute entry; the environment also holds GIT_NO_LAZY_FETCH "1"; on Windows the program search does not use that PATH, so the refusal closes the route on POSIX only; an older git ignores GIT_NO_LAZY_FETCH (before 2.44) or GIT_CONFIG_GLOBAL (before 2.32); output is not capped in size. The contract on main is unchanged; the erratum stands beside it, as TASK-008's errata did (D-359).
- Carried from the first round (D-580): F6's caller requirement (below, in DEF-0030); F8 (the first commit message's strongest claim, corrected in the second commit's message); F13 (AC11 has no test of its own; the listing is its check); F14 (the integration test needs the full history; stated in its docstring); F15 (the repository path is the caller's; a UNC path may touch the network); F16 (an empty trailer value is accepted).
- Carried from the second round (D-584): G1 (an absolute PATH entry inside the repository or a writable directory is still trusted; a caller requirement, in DEF-0030); G2 (the Windows limit could name the current directory searched by process creation); G3 (no test shows that the checked environment is the one passed); G4 (a PATH holding a NUL byte passes path_error and subprocess.run then raises ValueError, against "raises nothing"; reachable only through a patched environment; it predates E1); G5 (on POSIX a split on ':' cannot be told from os.pathsep; drive-relative, UNC, NUL and middle-empty entries untested); G7 (the integration test fails on a machine whose real PATH has an empty or relative entry; fail closed by intent).

## Why deferred
None is blocking; each is a test gap, a stated limit or a requirement on the caller, and the module has no caller yet (D-584 option (b) on G4).

## Resume when
At the submission path (TASK-025), the first caller of gitread, or at the next task that changes gitread.py.

## Depends on
DEF-0030 (the core's caller).

## Log
- 2026-10-12 (session 6f7d6716): opened. TASK-024 accepted at 057cc530 and on `main` (decision D-584; records 62f1d1b3, D-585). ../History/2026-10/2026-10-12-0048-the-git-reader-accepted-and-on-main.md
