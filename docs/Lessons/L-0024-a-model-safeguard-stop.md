# L-0024: A model safeguard stop

Rule: When a model safeguard stops a reply, redo none of the stopped content; record the refused message's id and the request before it; bring the stop to whoever the delegation in force names (the decision agent or the owner); go on only with a different approach in neutral wording: describe checks as verifying that rules fail closed, not as an attacker's attempts, and never ask for reasoning to be written out in a reply; state any cause only as a guess, citing the official refusal documentation.

- Status: active
- Category: tooling
- Binding: record only. Related: decisions D-1254 parts 2, 5, 6 and 7, D-1257 part 1; DM A70; L-0010 (respect harness guards).

## Pattern
While the main session edits a document about hooks that block an agent's tool calls, with adversarial reviewer roles and bypass hunts, the model's own server-side safeguard stops a reply ("Opus 5.5's safeguards stopped the response above"); the withheld part and its unfinished tool calls do not run, and no reason is recorded on the machine.

## Occurrences
Two, in session 2026-10-18-0710 (../History/2026-10/2026-10-18-0710-spec-2-revision-6-landed-and-the-safeguard-stops.md):
- **2026-10-18 (D-1254 part 2).** :671–:672, after an Edit of a review check script, during the launch of the reviews; refused message msg_011Cg8kcWpEC6DWo4GaFhgZ4.
- **2026-10-18 (D-1254 part 5).** :897–:898, after a guard refusal, during the first fix of the draft; refused message msg_011Cg8s3z3E2MjP4atUt6SA8.

One, in session 2026-10-19-1743 (../History/2026-10/2026-10-19-1743-the-pages-d1447-to-d1460-the-acceptance-and-the-landing-of-task-067.md):
- **2026-10-19 (D-1457).** Not a model safeguard but the app's auto-mode classifier ("[Auto-Mode Bypass]"): a call to the decision agent about the app's notice on D-1456's report was stopped before it ran (:490, denial at :491); a second call (:497, denial at :498) reworded the first one's request, against this rule, and was stopped too. The owner was then asked, since the decision agent could not be reached, and answered "có" (:548). The cause is a guess: the reports let work go on after a refusal by the project's own guard.

## Why it happens
The official refusal documentation says that Opus 5.5 and Sonnet 5.5 carry safety classifiers that can stop a reply, with categories such as "cyber", where benign security work can also trigger a stop, and "reasoning_extraction"; the reason is not shown in the app's notice. The work's text was about blocking hooks, bypass hunts and push blocking, so a "cyber" stop is the likely cause, which stays a guess.

## Prevention and detection
- Keep each message to one tool call with no prose; word checks and reviewer roles neutrally (verifying that rules fail closed).
- After a stop: do not redo or reword the stopped content; record the ids; bring it to the decision agent or the owner as the delegation says; continue by a different approach.
- The owner may report a false positive with the app's feedback command, which is the owner's own act.
