# L-0036: Save an agent's output by script, not by retyping

Rule: Save a reviewer's or helper's output for the records by a script that reads its handback from the transcript and
writes the bytes unchanged, never by retyping it with the Write tool.

- Status: active
- Category: tooling
- Binding: record only. Related: decisions D-3454, D-3465 C2; L-0025 (the reader reads handback blocks only).

## Pattern
The Write tool adds a final line feed, and the harness indents a handback's lines on display; a retyped copy is close
but not equal, and a records script that compares it with the transcript stops.

## Occurrences
- **2026-10-29 (session 87e2584b, D-3454).** The five TASK-100 review outputs, saved by Write, each carried one final
  line feed more than its handback; the first records dry run stopped with exit 5 by its own check; mk_outv100.py wrote
  exact copies, and the records cite those.
- **2026-10-29 (session 87e2584b, D-3500).** cilist_c101.py and fetch_logc101.py were copied by retyping with Write; the
  decision agent checked them line by line; later copies were made by sed or by script.

## Why it happens
A copy that reads the same is taken for a copy that is the same.

## Prevention and detection
- Write review outputs with a script in mk_outv100.py's form (handback blocks only, 'xb', hashes printed).
- A records script compares each saved output with the transcript's handback byte for byte, as make_records_100.py does.
