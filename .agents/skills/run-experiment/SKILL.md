---
name: run-experiment
description: Run an ML experiment the harness way - simple baselines first, features from the past only, choose on validation, confirm once on test, and write a run record with data, code and contract hashes. Use whenever you train or compare models, or need a number for a report.
---

# Run an experiment

## Before you start

- The task has a valid contract (data-contract skill) and `make check` is green.
- Read the latest run records for the contract in `runs/` and how many test evaluations it has spent.

## Steps

1. **Baselines first.** Implement the simple rules a team could use tomorrow (last period, recent means, a domain
   formula). They are the bar, not decoration.
2. **Features from the past.** Every feature for period t uses periods < t only. Unobserved periods are missing, never
   zero. Fit any preprocessing on the training split only.
3. **Models, simplest first.** Order candidates from simple to complex. On a validation tie (within the tolerance in
   the script) the simpler one wins.
4. **Choose on validation.** Pick the model and the baseline on validation. Do not look at test while choosing.
5. **Confirm once on test.** Compare the chosen model with the **best** baseline on test, with a block-bootstrap interval
   (`mlh.metrics.block_bootstrap_ci`). Report coverage: what falls outside the scored population.
6. **Record.** Write the run record with `mlh.registry.record(...)`, `evaluated_test=True`. Never edit records by hand
   (the guard denies it).
7. **Gate.** `make gate RUN=runs/<record>.json`. Report PASS or FAIL as the result.

## Rules

- Every number you report cites its run record (`run_id`).
- Iterating on test spends the budget (`gate.max_test_evaluations`). If you need many looks, you are tuning on test:
  stop and use validation, or open a new contract version with a new test window.
- Write scratch outputs to a temporary folder (`MLH_RUNS_DIR=/tmp/...`) when you are only exploring.

The reference implementation is [examples/weekly_risk/run.py](../../../examples/weekly_risk/run.py).
