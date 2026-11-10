---
name: data-contract
description: Write or change the data contract of an ML task before any model is trained - decision, unit, population, meaning of zero and missing, allowed features, temporal splits, decision metric, gate thresholds and owners. Use when starting a new modeling task, when someone proposes a new feature, population or metric, or when results suggest changing the split.
---

# Data contract

A model is only as honest as the contract it was evaluated under. Write it **before** training, and never change it
after looking at test results without a new version and an ADR.

## Steps

1. **Decision.** One sentence: who decides what, how often, with which capacity. Example: "which K assets to inspect
   next week". If you cannot write it, stop and ask; there is no metric without a decision.
2. **Unit, entity and period.** What one row is (asset-week), its key, and the period column.
3. **Population.** Which entities are scored and how they are chosen, using only data before the validation window.
   Say what happens to entities that appear later: they are reported as **coverage**, not silently dropped.
4. **Zero and missing.** Write what a zero means and how "not observed" is represented. A zero without exposure is not
   "no failure". Unobserved periods are missing in features and excluded as targets.
5. **Data.** The file lives under `data/raw/`, is registered with `make manifest`, and is never edited.
6. **Target.** Column, unit and how it is aggregated per row.
7. **Features.** `allowed`: each one computable from periods strictly before the target period. `forbidden`: what is
   only known later (target-period aggregates, fields corrected afterwards, final durations, closing dates).
8. **Splits.** `history_periods`, then `train_end < validation_end < test_end`, with test as the most recent window.
9. **Metric.** Tied to the decision (for capacity K: `capture_at_k`). State the denominator.
10. **Gate.** `min_improvement`, `ci_level`, `ceiling_fraction`, `max_test_evaluations`, `bootstrap_block`. Agree them
    with the owner of the decision **before** seeing results.
11. **Owners.** Roles for the data, the decision and the thresholds.

Then run `make check` (validates every `examples/*/contract.json` with `mlh/contract.py`).

## Changing a contract

- Before any test evaluation: edit, bump `version`, explain in the PR.
- After a test evaluation: new `version`, an ADR (record-decision skill) and, if the change was motivated by test
  results, a new test window. The test budget is per contract hash: a new contract starts a new budget.

See [docs/methodology.md](../../../docs/methodology.md) and the example
[contract.json](../../../examples/weekly_risk/contract.json).
