---
name: promotion-gate
description: Run and interpret the promotion gate on a run record - improvement over the best baseline, certainty, ceiling, contract, test budget and freshness. Use after every experiment that evaluated the test split, in CI, and before proposing a model for a pilot. Also use when someone wants to change the gate thresholds.
---

# Promotion gate

`make gate RUN=runs/<record>.json` (or `python3 -I tools/gate.py <record>`) exits 0 on PASS and 1 on FAIL.

| Rule | Passes when | If it fails |
|---|---|---|
| improvement | the model beats the **best** baseline on test by at least `min_improvement` | Keep the baseline. Report the size of the gap |
| certainty | the lower bound of the block-bootstrap interval is above zero | The gain may be noise. More test periods, not more tuning |
| ceiling | the model stays below `ceiling_fraction` of the oracle | Treat as leakage until proven otherwise (leakage-review skill) |
| contract | every feature used is in `features.allowed` and there is no leak on purpose | Review the new feature; changing the contract needs a new version and an ADR |
| test budget | test evaluations under this contract ≤ `max_test_evaluations` | You have been tuning on test. New contract version with a new test window |
| fresh | contract, data and code hashes match the files | Something changed since the run: rerun |

## What PASS and FAIL mean

- **FAIL is a result.** Report it with the run id. "The model does not beat a 13-week mean" is valuable information.
- **PASS is not business value.** It means the model may move to the next review: the contract and the diff are
  reviewed (ml-reviewer subagent), and a pilot with users measures whether acting on it helps.

## Changing thresholds

Thresholds belong to the owner of the decision (`owners.thresholds` in the contract) and are agreed before results are
seen. Changing them after a FAIL to make it pass is not allowed: write an ADR, bump the contract version and evaluate
on a new test window.
