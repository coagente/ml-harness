---
name: record-decision
description: Write an architecture or method decision record (ADR) in docs/adr - for choices that are expensive to reverse, such as repository layout, a contract change after test results, gate thresholds, a new data source or a modeling approach. Use when a decision is proposed, accepted or replaced.
---

# Record a decision

1. Copy [docs/templates/adr.md](../../../docs/templates/adr.md) to `docs/adr/NNNN-short-title.md`, with the next free
   number. Numbers are never reused.
2. Fill in the one-line summary: "For <context>, facing <problem>, we chose <option> and rejected <others>, accepting
   <cost>."
3. Context with links to evidence (run records, contracts). Mark your own reading as (inference) or (proposal).
4. At least two rejected alternatives, with the reason.
5. What changes for people, for agents (the one line that goes into AGENTS.md, if any) and what is checked
   automatically.
6. When to revisit: the signal that would make this decision wrong.
7. Status starts as `proposed`. Only a human accepts it; agents never mark their own ADR as accepted.

If the decision changes a rule agents must follow, update AGENTS.md in the same pull request.
