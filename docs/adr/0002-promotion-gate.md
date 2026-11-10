# ADR-0002: A model is promoted only through the gate, against the best baseline

Status: accepted · Date: 2026-11-09 · Decides: repository maintainers

**In one line.** For models that will drive operational decisions, facing results that look good on paper and do not
hold, we chose a mechanical promotion gate with six rules and rejected promotion by judgment alone or against a single
chosen baseline, accepting that some genuinely useful models will need more evidence before they pass.

## Context

Common failure modes: comparing against a weak baseline, tuning on the test split, leakage that inflates results,
reporting numbers that cannot be reproduced. Each one is cheap to detect mechanically once a run record exists
([methodology](../methodology.md)).

## Decision

`mlh/gate.py` reads a run record and requires: improvement over the **best** simple baseline on test of at least
`gate.min_improvement`; a block-bootstrap interval above zero; results below `gate.ceiling_fraction` of the oracle;
only features allowed by the contract; at most `gate.max_test_evaluations` test evaluations per contract; and unchanged
contract, data and code hashes. Thresholds live in the contract and are agreed with the owner of the decision before
results are seen. PASS sends the model to review and a pilot; it does not certify business value.

## Rejected alternatives

| Alternative | Why not |
|---|---|
| Compare only with the baseline chosen on validation | A weak pick on validation lets a model pass that loses to another simple rule on test |
| Promote by reviewer judgment | Inconsistent, and easy to rationalize after seeing results |
| Ceiling rule as the only leakage defence | Catches gross leakage only; the leak in `make demo-leak` stays below the ceiling |

## What changes

- **For people:** agree thresholds per contract; read FAIL as a result.
- **For agents:** run `make gate` after every test evaluation and report the verdict (promotion-gate skill).
- **What is checked:** unit tests of every rule; CI asserts PASS for the honest demo and FAIL for the leaky one.

## When to revisit

If teams start changing thresholds after results, or if a passed model repeatedly fails in pilots.
