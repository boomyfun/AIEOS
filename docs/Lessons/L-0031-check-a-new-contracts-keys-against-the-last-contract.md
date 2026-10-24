# L-0031: Check a new contract's keys against the last contract

Rule: At r0, compare the new contract's top-level keys, in order, with the last accepted contract's, by a script, and bring any missing, added or moved key to the decision agent before the reviews.

- Status: active
- Category: process
- Binding: record only. Related: decisions D-2808 (C3), D-2809.

## Pattern
A key is left out of a contract draft, and two reviews and the decision agent's read do not see it; only the parse at commit C finds it.

## Occurrences
One, in session 3797498a (2026-10-24):
- **D-2808.** TASK-089's r2 lacked owner_kept_act; reviews rv89a, rv89b and rv89c missed it; parse89 found it before commit C, and r2b added it by one Edit (D-2809).

## Why it happens
Drafts are made by copy and Edit from scope notes, not from the last contract's key list, and reviewers read the content, not the frame.

## Prevention and detection
- r0's maker asserts the key list equals the previous contract's (or names each difference).
- The reviewer brief asks for a key-list check as its own item.
