# ADR-0001: Decisions that are expensive to reverse are recorded as ADRs

Status: accepted · Date: 2026-11-09 · Decides: repository maintainers

**In one line.** For an ML project where agents and people change contracts, data and gates, facing decisions that are
forgotten or silently reversed, we chose short ADRs in `docs/adr/` and rejected decisions in chat or in commit messages
only, accepting a few minutes of writing per decision.

## Context

Agents act on what the repository says. A decision that lives only in a conversation is invisible to the next session.
Contract changes after a test evaluation, gate thresholds and data sources are the decisions that most change what a
result means.

## Decision

We write an ADR from [the template](../templates/adr.md) for decisions that are expensive to reverse. Agents may draft
ADRs with status `proposed`; only a person accepts them. Numbers are never reused.

## Rejected alternatives

| Alternative | Why not |
|---|---|
| Decisions in pull request descriptions | Hard to find later; not linked from AGENTS.md |
| A single decisions log file | Grows without structure; no status per decision |

## What changes

- **For people:** accept or reject proposed ADRs in review.
- **For agents:** use the record-decision skill; never mark your own ADR as accepted.
- **What is checked:** links in ADRs, by `make check`.

## When to revisit

If ADRs pile up unread, or decisions keep being made without one.
