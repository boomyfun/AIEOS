# DEF-0102: the launcher's findings values taken without a list check

- Status: open
- Opened: 2026-10-25 (session 3797498a; TASK-089's records, decisions D-2858, D-2871, D-2872)
- Deferred by: decision agent (A41, A51), D-2871 C1 and D-2872 C2 (found during TASK-089's acceptance review; the
  places lie outside TASK-089's own fix and are carried here).
- Decision group: A (a later task that changes the launcher's start or these helpers, within the self-build).

## What
At the task head of TASK-089, 25aba8fa, these places took a findings value from another function's result without
checking that it is a list, so a non-list value raises (a number) or is split into its letters (a string); the three
launcher.py places are closed by TASK-090 (decision D-2956), which keeps only a list's or a tuple's str items, with a
test of a string, a number and a mapping at each; read_set_record.py's _core stays open:
- src/aieos_bootstrap/launcher.py :280, in start (TASK-086): `findings = list(started.get('findings') or [])`;
- src/aieos_bootstrap/launcher.py :290, in start (TASK-086): `more = list(ended.get('findings') or []) if
  isinstance(ended, dict) else []`;
- src/aieos_bootstrap/launcher.py :333, _store_findings (TASK-089): `more = [f for f in (getattr(answer, 'findings',
  None) or []) if isinstance(f, str)]`;
- src/aieos_bootstrap/read_set_record.py :163-165, _core (TASK-064): `found = getattr(w, 'findings', ()) or ()` and
  `[str(x) for x in found]`.
end's own two findings lines were fixed in TASK-089's second code commit 25aba8fa (review t89x-S1 finding F4,
decision D-2852). In end every call of _store_findings sits inside a try, so end still never raises; start's two lines
sit after its try. The real adapter.start, adapter.end and the writer's results always give a list or a tuple of
strings, so no failure is known; only a stand-in or a later change could give another form.

## Why deferred
D-2858 C3 and D-2871: start belongs to TASK-086's contract, which TASK-089 did not change; _store_findings and _core
were not part of review finding F4; a fix here is a change of its own, with its tests.

## Resume when
At the next task that changes read_set_record.py's _core, which its scope note names; this item closes when _core
keeps only a list's (or a tuple's) str items, with a test of a non-list value.

## Depends on
TASK-086 (start), TASK-089 (end and _store_findings), TASK-064 (read_set_record's _core).

## Log
- 2026-10-25: opened with TASK-089's records (session 3797498a; decisions D-2858, D-2871, D-2872, D-2876).
- 2026-10-25: TASK-090 accepted (decision D-2956): launcher.py's start (two places) and _store_findings closed;
  read_set_record.py's _core stays open (session ea6ea0a3; decisions D-2910, D-2956).
