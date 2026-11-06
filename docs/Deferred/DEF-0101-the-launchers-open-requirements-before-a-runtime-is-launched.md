# DEF-0101: the launcher's open requirements before a runtime is launched

- Status: open
- Opened: 2026-10-24 (session 3797498a; TASK-086's contract, decisions D-2673, D-2681)
- Deferred by: decision agent (A41, A51), D-2681 Q1 and Q3 (TASK-086's launcher writes no observed read-set record
  and leaves max_risk to its caller; these requirements are carried here).
- Decision group: A (later M7 tasks within the self-build; launching with a runtime stays the owner's, DM A51 item (4)).
- Blocks v0.1: yes (the first real run launches a runtime and `aieos launch` ships no starter; the item says a launch waits for its open points)
- Scheduled in: M8, the launcher root-after-check task, before the first real run

## What
TASK-086's launcher (src/aieos_bootstrap/launcher.py) runs the core's expiry, the Resume Check and the grant over
adapter.start and adapter.end, and starts no runtime. Before a runtime is launched with it, these stay open:
- closed: the observed read-set record before every lease release (specification 7 :45, specification 5 :112;
  read_set_record.py :19-24) at its three call places: the normal end and the gone session's record at the end after
  a violation or an expiry are written by TASK-089's launcher.end, with the stored reads' removal; the third, the gone
  session's record at the next start (specification 5 :125), with its listing of gone sessions through
  writer.read_sessions, is written by TASK-090's launcher.start before the expiry (decision D-2956);
- closed: the check that HEAD is the base branch's tip: launcher.start's step "base" (TASK-106, decision D-3970) reads
  refs/heads/<base> (the base is "main" unless a caller passes another; `aieos launch` passes none) once, after the head
  and before the log, and does not grant unless HEAD is that tip; AIEOS_BASE is the head_commit read once, found equal to
  the tip at that read (the race, the local ref only and the strict name rule are stated in launcher.py's docstrings);
- closed: check 0 of the contract (specification 5 :121; specification 7 :49) is made by the Resume Check at every
  start (resume_check.py :529-:530), not by the launcher's hook; TASK-106's composed-path test in
  tests/integration/test_launcher_repo.py shows it on the real adapter.start and the real Resume Check;
- closed at the grant: the check that the project's root is untouched before a launch (specification 5 :121;
  specification 7 revision 7 section 5): launcher.start's step "root" (TASK-109, decisions D-4143 and D-4167) reads
  gitread's fifth read-only form, status, in one fixed form that leaves the project-state directory out, once, after the
  base check and before the log, and does not grant unless the answer is clean (any entry gives "not granted", an answer
  out of form "refused", both with reason "root"); the eight stated limits are in the docstrings of launcher.py and
  gitread.py (once, before the grant; the state directory left out; the ignore set; what may not be counted; the filter
  question; the first run of the workflow's SUBCOMMANDS check and the later DM A66 decision; the git version; the
  self-build's clean-root consequence);
- open: that the root stays untouched after the check (between the read and the grant, and during the session) is not
  checked;
- closed at the grant, with stated leftovers: the filter route (TASK-110, decisions D-4203 to D-4227 and D-4271):
  `status` could make git start a program that a clone's own configuration names as a filter driver (the way-2 review
  R109 found INV-001 "does not hold on the filter route only", a stated limit in D-4139 (a), D-4165, D-4167);
  launcher.start's step "root" now first reads gitread's sixth read-only form, config (`git config --list -z`, includes
  and worktree configuration included), once, before the status read, and does not grant when a key begins with
  "filter." or equals "core.worktree" (an answer out of form "refused", a refused key "not granted", both with reason
  "root"); the way-2 review R110 found INV-001 holds "with stated limits (gitread.py:50-76)" (the TASK-110 record, line 21);
  the root check's own limits are (1) to (9) of launcher.py's docstring. The leftovers: the two reads are not atomic, so a configuration change made between them is
  not seen by the configuration read and the status read itself acts on it; the match is on the key text only and other
  keys that change what status counts are not refused; and the partial-clone lazy fetch is a separate route by which git
  can start a transport program, closed only from git 2.44, not a limit of the filter refusal (launcher.py's
  docstring);
- launching with a runtime (for the self-build the decision agent's decision since A73; permission prompts and what Claude's safety rules or the owner's command guard require the owner to permit stay the owner's) is not before this item's open points are closed: the root's state after the
  check, and max_risk; this is a statement, not a lock;
- max_risk is the caller's: a caller passing a non-null max_risk declares the runtime's tier, which only a measurement
  under the measurement protocol can back (the protocol stays the owner's; approving its findings for the self-build is the decision agent's under A73) (C6, P-LOC); the self-build passes null until then, so the launcher never grants (decision
  D-2673 ruling 2);
- closed: a stand-in start giving a non-list truthy findings value would raise past the launcher's step guard; end's
  own findings handling was fixed in TASK-089, and start's two places by TASK-090, which keep only a list's or a
  tuple's str items (DEF-0102, decision D-2956).

## Why deferred
D-2681 Q1: the three record call places and the stored reads' removal were planned as one task after TASK-086, split
by decision D-2771 into TASK-089 (end's two call places and the removal) and TASK-090 (the next start's record); Q3:
max_risk stays the caller's until a tier is measured.

## Resume when
The record's three call places are closed by TASK-089 and TASK-090 (decisions D-2876, D-2956); the base-tip check and
check 0 were closed by TASK-106 and the untouched-root check at the grant by TASK-109 and its filter route by TASK-110; this item closes when the part
of the root check that stays open (the state after the check) is met or moved by its own decision;
max_risk stays the caller's, as its bullet states.

## Depends on
TASK-086 (the launcher), TASK-089 (end's record and the stored reads' removal), TASK-064 (read_set_record, the
record's core side; read_set_record.py :1), TASK-066 to TASK-068 (the read hook that writes the reads; DEF-0097 :14),
TASK-051 (adapter); specification 5 section 11 points 7 and 10, specification 7 section 5.

## Log
- 2026-10-24: opened with TASK-086's records (session 3797498a; decisions D-2681, D-2758).
- 2026-10-25: TASK-089 accepted (decision D-2876): end writes the record at two of the three call places and removes
  the stored reads; the next start's record and the launch line now name TASK-090 (session 3797498a; decisions D-2771,
  D-2876).
- 2026-10-25: TASK-090 accepted (decision D-2956): start writes the gone sessions' records at the next start and
  removes their stored reads; start's findings handling closed; the launch line now names the base-tip check, check 0
  and max_risk (session ea6ea0a3; decisions D-2910, D-2953, D-2956).
- 2026-10-25: TASK-094 accepted (decision D-3178): launcher.launch_outside composes one launch from outside the runtime
  (start with max_risk None and a lease of two hours, the contract's write set at the grant's head, the caller's
  starter, the end in every case after a grant, the handoff after a done end), and the shipped command `aieos launch`
  passes no starter and refuses "no runtime starter"; open for the task that adds a real starter, which stays the
  owner's and is asked separately: gitread's pinned list or another wrapper, the workflow's pattern rule, INV-001's
  question whether an allowed executable runs a model, the lease length and its renewal, and a finish refused
  "stored_reads", which launch_outside leaves to `aieos end` or the lease's expiry with no end_outside call (session
  ea6ea0a3; decisions D-3154, D-3164, D-3172, D-3178).
- 2026-10-29: M7 exited (`docs/plan/m7-exit-review.md`): the base-tip check, check 0 and max_risk stay open before any runtime launch (session ea6ea0a3).
- 2026-10-31: TASK-106 accepted (decision D-3970): launcher.start gains the step "base" (the base-tip check) and the
  keyword base; gitread's rev-parse takes refs/heads/<base> as a third name form; check 0 is closed for the launcher by
  the Resume Check at every start, shown by a composed-path test; the untouched-root check stays open, and so does
  max_risk; `aieos launch` now refuses unless HEAD is the tip of the local refs/heads/main (session 85a45f06; decisions
  D-3918, D-3919, D-3927, D-3938, D-3970).
- 2026-11-01: TASK-109 accepted (decision D-4167): launcher.start gains the step "root" (the untouched-root check at
  the grant) and gitread its fifth read-only form, status; GOV-003 and INV-001's filter route are stated departures of
  the acceptance (D-4139 (a), D-4165, D-4167); the part of the check after the grant and the filter route stay open, with
  the candidate fix of the way-2 review R109 named; the workflow's SUBCOMMANDS check accepts four or five forms until a
  later DM A66 decision narrows it to the five (session c7d6f32b; decisions D-4128 to D-4147, D-4165, D-4167, D-4172).
- 2026-11-01: DM A66 narrowed the workflow's SUBCOMMANDS check (aieos-checks.yml revision 16: exactly the five gitread
  forms; revision 17: exactly the six), which settles the wording above about "four or five forms until a later
  decision"; TASK-110 accepted (decision D-4271): gitread gains its sixth read-only form, config, and launcher.start's
  step "root" reads it before the status read; GOV-003 'does not hold' is a stated departure of the acceptance
  (DEF-0107 points 2 to 5, the compensating controls named in D-4271); the way-2 review R110 found INV-001 holds with its
  stated limits; the part of the check after the grant stays open (session 79c5920b; decisions D-4203 to D-4279).
- 2026-11-03: TASK-116, the first task whose contract the core wrote (`aieos run`, decision D-4674; the contract is
  under `.aieos/tasks/`), is launched by no session, because `aieos launch` ships no runtime starter (cli.py NO_STARTER,
  specification 7 :35); this item's subject is unchanged; this item stays open (session 08342c65; decision D-4674).
- 2026-11-03: the entry above (TASK-116) was put on main by TASK-116's own task commit b202e609 before the task was accepted, and
  TASK-116 was not accepted (decision D-4685, DEF-0118: functional lint has no producer); the statement of the entry is
  unchanged by this; this item stays open (session 08342c65; decisions D-4685 and D-4692).
- 2026-11-03: the owner answered "có" to the runtime-tier question of decision D-4713 (session 08342c65, main transcript :11093; decision matrix row A74): for the lowest-risk tasks of the self-build only, without a prior measurement, unmeasured and advisory, judged by Claude itself; so a 'low' tier for those tasks can rest on the owner's yes instead of a measurement, and every tier above low still needs one; how a 'low' declaration is supplied (read at the base, never passed by the caller; specification 5 :33-37, matrix row F54) is a later decision, and the root's state after the check stays open; this item stays open and nothing is launched by this line (decisions D-4713, D-4719, D-4727).
- 2026-11-05 (session a0a0bdef): TASK-117 accepted: the launcher no longer takes max_risk from its caller; the core reads the runtime's declaration from .aieos/project.yaml at the base (read_declaration), every declaration at its weakest (max_risk low, no measurement resolves); the declaration file itself is put into Git by the state commit P1-3, a separate step; until then there is no declaration at the base and check 7 gives STOP: runtime insufficient (spec-02:249 at X3); and launch_outside is refused at the step "declaration" whatever the base holds, until DEF-0122 is settled. DEF-0120 to DEF-0123 state the limits and the residuals.
- 2026-11-05 (session 6550f093): P1-3 done: the state commit 711d7a95 put .aieos/project.yaml (the declaration for claude-code, unmeasured and advisory, max_risk low, resting on A74; configuration version 2.1.317 as re-read at P1-3, D-4859) into main as a one-commit fast-forward (D-4863); the CI of main on it was read and clean (aieos-native 41946898850 and aieos-checks 41946899053, D-4864 to D-4866). With TASK-118 (the launcher's adapter name agrees with the grammar), `aieos launch` at a base that holds the declaration is expected to read low for claude-code at the step "declaration" (a reading of spec-02 and TASK-118, not run); no launcher is started by this line; this item stays open (decisions D-4858 to D-4866).
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass C decisions D-5257 and D-5258): read in full; closed per its Log: the observed read-set records (TASK-089, TASK-090), the base-tip check (TASK-106), check 0, the untouched root at the grant (TASK-109), the filter route (TASK-110), max_risk read from the declaration (TASK-117, state commit 711d7a95, DEF-0122 done); open: the root's state after the check (option A of D-5258 K6: a task that re-reads the root's state at the session's end or before the state commit and gives a finding) and the real runtime starter, whose launching for the self-build is the decision agent's under DM A73 (permission prompts and what the safety rules or the command guard require stay the owner's, DEF-0101:46). State: open; Blocks v0.1: yes (the first real run launches a runtime and `aieos launch` ships no starter; the item says a launch waits for its open points); Scheduled in: M8, the launcher root-after-check task, before the first real run.
- 2026-11-07 (session ce14b08a): the owner answered "có" to the question of decision D-5304 about the acceptance of the runtime-starter software of `aieos launch` (decision matrix row A75; decision D-5306): that software, and nothing else, is accepted by the decision agent in the owner's place and the owner is told afterwards; permission prompts stay the owner's; CR-002 part 4 limit 5 for other tasks is not changed; the real runtime starter stays the last task to build, so this item stays open, and nothing is launched by this line.
