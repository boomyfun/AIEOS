# L-0005: Keep only AIEOS in scope

Rule: Use only AIEOS material as input, and before giving any document to agents or reviewers, check it for references to other projects and remove them.

- Status: active
- Category: accuracy
- Binding: record only. It follows the owner's instruction: "Chúng ta đang build AIEOS, và chỉ đề cập đến AIEOS. Đã có nhầm lẫn ở đây." (transcript :571).

## Pattern
Once Claude writes a reference to another project into a document, the reference spreads to every agent and advisor that reads that document.

## Occurrences
Three in session 2026-10-04-1817 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md):
- **2026-10-04 (:136, :579).** Claude added another project to concept v0.3 (§16 and §17 Q4). The frozen concept still contains it. DM B13 plans its removal through CR-001 (DEF-0007).
- **2026-10-05 (:476, :563).** Review agents carried the reference into their recommendations, and the owner objected (:571).
- **2026-10-05 (:587, :608, :652).** The owner's saved copy of Claude's first evaluation, an old file outside the repository, still contained it, so the advisor proposed a pilot of that project.

Context: the 30-step process the owner asked Claude to adapt came from another project (:365), and Claude's adapted list still named it (:369).

## Why it happens
- Material from outside AIEOS appears in pasted text and examples.
- Agents trust what the concept says and repeat it.

## Prevention and detection
- Before sending any document to agents or advisors, search it for other project names. Keep the list of names private, not in public files.
- Treat copies saved outside the repository as possibly stale.
- Fix the concept only through CR-001.
