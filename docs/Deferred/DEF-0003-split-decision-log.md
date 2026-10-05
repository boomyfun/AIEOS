# DEF-0003: Split the decision log into several files

- Status: open
- Opened: 2026-10-06 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md)
- Deferred by: owner ("Tuy nhiên chúng ta sẽ tiếp tục những việc này trong phiên sau.", transcript :5113)
- Decision group: B. The decision-agent definition names the log file, and changing that file is group B, item 3. Moving or removing existing entries would be group B, item 1.

## What
The owner asked: "sổ ghi quyết định có thể bị phình rất nhanh, vì vậy chúng ta nên tạo nhiều file sổ ghi quyết định khác nhau" (:5113).

The log `%USERPROFILE%\AIEOS-REG0-lite\decisions\decision-log.md` is append-only ("Entries are never edited or removed"). At the end of the session that opened this item, it held 801 lines for D-001 to D-006.

## Why deferred
The owner chose to do this in the next session (:5113).

## Resume when
The next session.

## Depends on
- A layout that keeps the append-only rule. Suggestion only, not decided: new files for new entries, with the existing file left unchanged.
- Updating the four references to the log in `aieos-decider.md` (group B).

## Log
- 2026-10-06: requested and deferred by the owner (:5113).
- 2026-10-06 (session 5fd3e494): the line count above was corrected. It said "556 lines for D-001 to D-005"; the log ended that session with D-001 to D-006 (D-010 C8).
- 2026-10-06 (session 5fd3e494): Claude proposed one file per decision. The existing log stays unchanged, apart from a final pointer line. The owner answered "có" (:832). Implementation needs a change to the agent definition (four references to the log), and therefore an A41 marker. Not yet done.
