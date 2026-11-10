---
name: close-change
description: Close any change before saying it is done - make check and make test green, run records for every reported number, gate result, docs and decisions updated, and a short report with evidence. Use at the end of every task that touched files.
---

# Close a change

A change is done when someone else can pick it up by reading the repository alone.

1. **Regenerate what is derived.** New raw files: `make manifest`. New or renamed skills: `make sync`.
2. **Checks.** `make check` and `make test`. If something was already broken before you started, say so; do not hide it.
3. **Evidence.** Every number you report has a run record in `runs/` and, if the test split was evaluated, a gate
   result (`make gate RUN=...`).
4. **Docs.** Update the README or docs if behaviour changed; an ADR if a decision was made (record-decision skill);
   AGENTS.md if an agent rule changed.
5. **Review.** For model changes, ask the `ml-reviewer` subagent for an independent review and address what it finds.
6. **Report**, briefly: what changed (paths), what you checked and its result, the gate verdict, and what a human must
   decide.

Do not commit or push unless asked. Never commit to main: create a branch and open a pull request.
