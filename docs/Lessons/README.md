# Lessons

Recurring mistakes and how to prevent them. There is one file per pattern (`Lessons/L-NNNN-<slug>.md`), not one per incident: when a mistake happens again, a dated occurrence is added to the existing lesson. The general rules are in [`../WORKING-RECORDS.md`](../WORKING-RECORDS.md).

- **Rule line:** each file has exactly one line starting with `Rule: `, near the top. To list all of them, run `grep -h "^Rule: " docs/Lessons/L-*.md`. Read the list at the start of every session.
- **A lesson is a record, not a binding rule.** It becomes one of Claude's binding working rules only when the owner says yes and it is written into the rules book. The "Binding" field says which applies.
- **A lesson may only add caution.** It never relaxes a rule in the rules book, the decision matrix or the decision agent's definition.
- **Retiring a lesson:** a lesson that no longer applies gets `Status: retired`, with the reason. It is never deleted.

## Template

```markdown
# L-NNNN: <title>

Rule: <one imperative sentence>

- Status: active
- Category: <process | technical | communication | governance | accuracy>
- Binding: <record only | working rule N in the rules book (owner yes, YYYY-MM-DD)>

## Pattern
## Occurrences
- YYYY-MM-DD (../History/YYYY-MM/<file>.md, transcript :N): <what happened>
## Why it happens
## Prevention and detection
```
