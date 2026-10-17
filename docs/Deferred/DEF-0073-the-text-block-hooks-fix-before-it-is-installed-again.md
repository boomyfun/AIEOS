# DEF-0073: the text-block hook's fix before it is installed again

- Status: open
- Opened: 2026-10-16 (session 1702974f; decisions D-1057, D-1058 and the session-end decision)
- Deferred by: decision agent (A41), the session-end decision of session 1702974f, after the owner's "gỡ ra".
- Decision group: B for any install (Claude Code settings and hooks, A51 item (4)); A for the fix in the scratchpad.

## What
- The hook aieos_textblock_guard.py (session c239e39e's design, narrowed to this project) was installed with the owner's own permission and removed at the owner's word the same session: its live check (ii) failed. When Claude Code runs a PreToolUse hook, the pending call's own record is not yet in the transcript, so the hook's "last assistant record" is the previous message; after a turn-final reply (text, no tool call) the first call of the next turn was refused. The replay test could not show this, because it judged each call after its record was written. The decision agent's returns also stopped arriving while it was active.
- A fix to consider: judge only an assistant record that is not a finished turn (skip a last record whose stop_reason is end_turn), and test it by a replay that judges each call before its record is written, plus a live test with the owner present.
- The file C:/Users/Admin/.claude/hooks/aieos_textblock_guard.py stays on disk, inert (no settings entry runs it).
- Any new install needs the owner's own word again.

## Resume when
- When the owner asks, or when text slips recur and the decision agent proposes the fixed hook to the owner.

## Log
- 2026-10-16: opened (session 1702974f).
- 2026-10-17: evidence: five text slips in session 797bc984 and one in session 3f57da38 (:724), each at a step change; six Bash calls before the first tbq.sh call in session 3f57da38 after five in 797bc984 (D-1146 C5); the rules lowered the cost of each slip, not their number (D-1144 amendment 3, D-1148 amendment 1).
