"""Decision metrics and uncertainty. Needs numpy.

capture_at_k answers the question a maintenance planner actually has: if I can review K entities this period, what share
of the period's loss falls on the K I chose? Intervals come from resampling whole periods (block bootstrap), because rows
within a period are not independent.
"""
import numpy as np


def capture_at_k(y, pred, period, k, seed=0):
    """Per period: share of the actual total that falls on the k rows with the highest prediction.

    Ties are broken at random with a fixed seed, so a baseline full of zeros does not get a lucky order for free.
    Periods whose actual total is zero are skipped (nothing to capture). Returns one value per period, in period order.
    """
    rng = np.random.default_rng(seed)
    out = []
    for t in np.unique(period):
        m = period == t
        total = y[m].sum()
        if total <= 0:
            continue
        order = np.lexsort((rng.random(m.sum()), -pred[m]))[:k]
        out.append(y[m][order].sum() / total)
    return np.array(out)


def block_bootstrap_ci(per_period_diff, level=0.9, reps=2000, block=3, seed=0):
    """Mean and two-sided interval of a per-period difference, resampling circular blocks of consecutive periods.

    Neighbouring periods look alike, so resampling single periods would make the interval too narrow.
    """
    d = np.asarray(per_period_diff, dtype=float)
    n = len(d)
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n, size=(reps, -(-n // block)))
    idx = ((starts[:, :, None] + np.arange(block)) % n).reshape(reps, -1)[:, :n]
    boot = d[idx].mean(1)
    a = (1 - level) / 2
    return float(d.mean()), float(np.quantile(boot, a)), float(np.quantile(boot, 1 - a))
