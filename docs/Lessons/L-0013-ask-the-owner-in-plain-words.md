# L-0013: Ask the owner in plain words

Rule: Put every question to the owner in plain Vietnamese, with a recommendation and what the answer changes, and when an approval must be bound to an exact hash, ref or setting, check that binding by script and say in plain words what it binds instead of asking the owner to compare technical values themselves.

- Status: active
- Category: communication
- Binding: record only. Related: the decision agent's rules for its FOR THE OWNER text ("No technical words") and group B item 10 of its lists, which turns a doubt into a question about values, risk, money or what becomes public.

## Pattern
Claude put approvals and choices to the owner in terms of hashes, refs, ruleset rules and settings, and suggested answers built around those values. The approval then rested on values the question did not explain.

## Occurrences
At least five in session 2026-10-04-1817 (../History/2026-10/2026-10-04-1817-idea-to-cs3v2.md):
- **2026-10-05 (:3016 to :3020).** CS-1 was approved by its hash ("duyệt, hash đã chính xác", :3020).
- **2026-10-05 (:3483 to :3487).** CS-2 was approved the same way ("duyệt hash đã chính xác", :3487).
- **2026-10-05 (:3872, :3973).** After explanations in technical terms, the owner asked whether their GitHub token would be exposed (:3872) and why the push was blocked for AIEOS only (:3973).
- **2026-10-05 (:3904, :3912).** M4 was put to the owner as options about refs and a lease, and approved with "duyệt" (:3912).
- **2026-10-05 (:4237, :4344).** CS-3 v1 asked for approval "kèm hai hash", with an example answer that contained both hashes.

Remedy so far: the owner asked for an agent that decides on their behalf in the whole project (:4348). Claude acknowledged that it had asked the owner to approve hashes, refs and ruleset rules (:4357). The decision agent's FOR THE OWNER text has no technical words.

## Why it happens
- Claude's approval gates were designed around exact artifacts, and their identifiers went into the question unchanged.
- Explaining what a hash binds takes more words than showing it.

## Prevention and detection
- Write each owner question in plain Vietnamese: what changes, what becomes public, the risk, and Claude's recommendation.
- Keep any required binding to an exact text, such as a plan hash, but check it by script and say in plain words what it binds.
- Before sending, check the question for hashes, refs, file paths and English terms, as the FOR THE OWNER rule does.
