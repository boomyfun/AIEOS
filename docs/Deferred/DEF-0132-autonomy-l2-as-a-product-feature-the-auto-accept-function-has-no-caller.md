# DEF-0132: autonomy L2 as a product feature: `autonomy.auto_accept_allowed` has no caller and the governor's row 4 is not wired

- Status: open
- Opened: 2026-11-06 (../History/2026-11/2026-11-06-1701-m8-stage-8-the-decision-files-d5198-to-d5236-and-the-coverage-map-ce14b08a.md)
- Deferred by: decision agent (A41, A51), D-5246, D-5247 (the gaps of the coverage map, D-5245)
- Decision group: A (the wiring as a governor change of the self-build); raising any real level stays the owner's or as A54 point 2 allows (master-plan section 9 point 5)
- Blocks v0.1: yes (concept line 949 lists "autonomy L1-L2" in the v0.1 list)
- Scheduled in: M8, the governor row 4 wiring task, scheduled ahead of new work in M8 (master-plan section 6, deferral rule point (2))

## What
`autonomy.auto_accept_allowed(levels, allowance, risk, status, touches)` (autonomy.py line 101) is one pure function, the policy's half of the governor's row 4; it has no caller, the governor keeps `LEVEL_AT_LEAST_L2 = False` and its row 4 stays unreachable (autonomy.py lines 14-15: "Connecting this function to the governor is a separate governor change"; the M4 exit review, limit L-a). This item is to wire it as a product feature, with the policy inputs; it sets no real level for gov-AIEOS, which stays L1 (A35; A54 point 2; CR-001 E7: auto-accept applies only at L2 and above).

## Why deferred
The wiring is a governor change of its own and the self-build is at L1; found by the coverage map (decisions D-5244 and D-5245). Carried before as log points of DEF-0030 (its log of 2026-10-15: TASK-036's function has no caller; M4 exit limit L-a), which has no 'Blocks v0.1' field; this item is now its carrier, and the triage (decision D-5143 C3) records that in DEF-0030, which is not changed here.

## Resume when
When the triage schedules the governor changes of M8, or when a task needs auto-accept for the product, whichever comes first.

## Depends on
DEF-0030 (log of 2026-10-15, limit L-a); TASK-036 (the function); the governor (TASK-020 and later); the policy and status inputs (assurance-model section 6; C13 and P-CRED, which are the owner's measurements).

## Log
- 2026-11-06: opened (session ce14b08a; decisions D-5245, D-5246).
- 2026-11-06 (session ce14b08a; triage decision D-5143 C3, pass F batch 3, decision D-5269 (C2)): read in full; autonomy.py and governor.py are unchanged since TASK-102; Resume-when ('when the triage schedules the governor changes of M8') is met by this entry; the task sets no real level (gov-AIEOS stays L1), and its approval is classified at its contract: if it falls under CR-002 part 4 limit 5 or limit 8 it is the owner's (master-plan.md :103, :135); the M4 limit L-a recorded in DEF-0030's Log is carried here. State: open; Blocks v0.1: yes (concept line 949 lists "autonomy L1-L2" in the v0.1 list); Scheduled in: M8, the governor row 4 wiring task, scheduled ahead of new work in M8 (master-plan section 6, deferral rule point (2)).
