# L-0038: A reviewer's model is checked by machine against every model that did task work

Rule: Before a review is called independent or cross-model, list by machine the model of every agent that did task work (the main session, the line-finding helpers, the decision agent when it wrote texts) and the model of each reviewer, from the transcripts; do not state from memory that no other agent worked on the task.

- Status: active
- Category: process
- Binding: record only. Related: decisions D-3697, D-3698, D-3537 (DA-3's pair on another model).

## Pattern
The session's main model was claude-sonnet-5-5 and the reviewers ran on claude-opus-5-5, so an opus review looked cross-model. The statement "no other agent did task work" was wrong: the four line-finding helpers of step 1 and the decision agent (which wrote exact edit texts) ran on claude-opus-5-5. The machine listing of the agents' models (agent_models.py) showed it before the review was launched; the architecture line came from a reviewer on claude-haiku-5-5, a model that did no task work, and its model was read from its transcript.

## Occurrences
- **2026-10-30 (session 1c1bf794, D-3697 C2, D-3698).** The listing of 134 agents and the main transcript showed claude-opus-5-5 on every agent; the planned opus article review was replaced by a haiku review.

## Why it happens
The main session's model is the one in view; helper agents and the decision agent are taken for readers, not authors.

## Prevention and detection
- Run a models listing over the session's agent transcripts (agent_models.py's form: model set, tool counts and handback subject per agent) before a review is launched as cross-model.
- Have the records script read the reviewer's model from its transcript and assert it differs from the main session's and from every model that did task work.
