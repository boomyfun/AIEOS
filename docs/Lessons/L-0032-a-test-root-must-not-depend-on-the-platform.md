# L-0032: A test root must not depend on the platform

Rule: Before commit X, check every new test for paths whose meaning depends on the platform (a drive letter, a backslash, os.path rules), and make the root a literal that the code under test reads the same on Windows and on the Linux CI.

- Status: active
- Category: tooling
- Binding: record only. Related: decision D-2822a (C3).

## Pattern
A test passes on the Windows machine but would fail on the Linux CI because the root it builds is read differently there.

## Occurrences
One, in session 3797498a (2026-10-24):
- **D-2822a.** TASK-089's end tests needed a literal Windows root (END_ROOT and ROOT 'C:/…') so the code's root check gives the same answer on the Linux CI; found while drafting, before CI.

## Why it happens
The local runs are all on Windows; CI is the first Linux run.

## Prevention and detection
- A Grep of new test files for os.path, tempfile roots and drive-letter forms before commit X.
- Where the code checks a root's form, the tests use a fixed literal root.
