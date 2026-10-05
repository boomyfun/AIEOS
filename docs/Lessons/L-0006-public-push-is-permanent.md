# L-0006: Anything pushed to the public repository is permanent

Rule: Before content enters the public repository, scan it for e-mail addresses, account names, credentials or probe details, references to other projects and pre-rewrite commit IDs, and treat every push as permanent.

- Status: active
- Category: governance
- Binding: record only. Related: DM A1 ("Public history is permanent") and the A41 push conditions, which require a scan for passwords, tokens and secret keys before each push.

## Pattern
Content written for local use later becomes public. Removing it from public history is costly and incomplete.

## Occurrences
Five in session 2026-10-04-1817 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md):
- **2026-10-05 (:749, :810).** The repository became public while its commit history still carried an earlier author identity. A history rewrite and a force-push (M4, :4023) corrected it within the scope the owner decided (:814), but replaced commits may stay reachable on GitHub by ID (DEF-0010).
- **2026-10-05 (:729, :866).** A safety classifier twice stopped credential-probe content drafted for the public measurement protocol. P-CRED details now stay out of public files (MP §1.3).
- **2026-10-05 (238fae0).** DM row A24 names GitHub accounts in a public file. D-004 and the CS-3 v2 self-check noted this as pre-existing, but it was never raised with the owner (DEF-0010).
- **2026-10-05 (:3886, corrected :3904).** Before M4, Claude made an unchecked statement to the owner about the author addresses in the history.
- **2026-10-05 (:4357, corrected :4439).** Claude told the owner that wrong content pushed publicly is exposed only until it is fixed.

Good practice: a token-exposure scan ran before M4 (:3886).

## Why it happens
- The visibility changed after the content already existed.
- Claude underestimated how permanent public history is.

## Prevention and detection
- Run the scan in the rule before every push. The decision agent checks it for normal pushes.
- Keep sensitive working material in the working folder outside the repository.
- Push only explicit refspecs. Never push backup refs, and never use `--all`, `--mirror` or `--tags`.
