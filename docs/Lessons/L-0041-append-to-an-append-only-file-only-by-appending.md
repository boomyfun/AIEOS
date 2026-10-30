# L-0041: Append to an append-only file only by appending after its last byte, never by an Edit that replaces text inside an earlier entry

Rule: Add to the session checkpoint file (and every other append-only record) only with a command or an Edit that writes after the last line (`printf '%s\n' '...' >> file`); an Edit whose old text is inside an earlier entry is a change to that entry, even if the new text keeps the old words.

- Status: active
- Category: process
- Binding: record only. Related: D-1940 C2 (the checkpoint file is append-only), L-0014.

## Pattern
An Edit used the tail of the last line as its anchor and put the new entry in the middle of that line, so an earlier entry was split.

## Occurrences
- **2026-10-30 (session 578ea88b, D-3853, D-3854 C1).** The D-3853 entry was first put inside the D-3852 entry; the decision agent had it restored and the entry appended.
- **2026-10-30 (session 578ea88b, D-3879, D-3880 C1).** The D-3879 entry was added by an Edit anchored in the middle of the D-3878 line; corrected by a note appended at the end (nothing removed).

## Why it happens
The tool's Edit needs a unique old text, and the last sentence of the last line looks like a safe anchor.

## Prevention and detection
- Use `printf '%s\n' '<text>' >> <file>` for the checkpoint file; read the last two lines afterwards.
- If an Edit is needed, anchor on a whole unique line and add the new entry after it as a new line, keeping the old line byte for byte.
