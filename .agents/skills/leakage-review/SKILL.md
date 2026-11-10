---
name: leakage-review
description: Review an ML pipeline for data leakage - information from the future, from the test split or from the target reaching the features, the population or the preprocessing. Use before trusting any result, whenever a result looks too good, when a feature or the population changes, and before opening a pull request.
---

# Leakage review

Leakage makes a model look better on paper than it will ever be in use. The gate's ceiling rule only catches gross
leakage (near-oracle results); subtle leakage is caught here, by reading the contract and the diff.

## Checklist

1. **Window alignment.** For each feature, write the last period it reads. It must be strictly before the target
   period. Rolling windows and lags are the usual culprits (`t-3..t` instead of `t-4..t-1`).
2. **Known later.** Is any field filled or corrected after the fact: closing dates, final durations, reason codes
   assigned after an investigation, statuses? If the raw data is a snapshot, the value you see may not be what was
   known at the time. Write this limitation in the contract if you cannot reconstruct it.
3. **Population and thresholds.** Entities, categories, thresholds or normalizations chosen with data from validation
   or test leak information. Choose them with training data only.
4. **Preprocessing.** Scalers, encoders, imputers and feature selection fitted on all rows leak. Fit on training only.
5. **Duplicates and neighbours.** The same event, or near copies, in train and test. Group splits by entity when the
   question is about new entities.
6. **Target proxies.** Features that are the target under another name (event counts of the target period, flags set
   because the event happened).
7. **Test reuse.** How many times was the test split evaluated under this contract? Many looks are leakage by
   selection.

## Quick tests

- **Shift test:** shift a suspicious feature one more period into the past; a large drop in performance means it was
  carrying future information.
- **Too good to be true:** compare with the oracle in the run record. Close to the oracle means leakage until proven
  otherwise.
- **Contract diff:** `git diff main -- examples/*/contract.json` and the list `features_used` in the run record.

Report findings with file, line and a failure scenario. The example `make demo-leak` shows a leak that passes the
ceiling rule and is caught only by the contract rule.
