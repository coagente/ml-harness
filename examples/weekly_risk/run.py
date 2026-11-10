"""weekly_risk: from the contract to the gate, end to end.

Decision: which K assets to inspect next week. The contract (contract.json) fixes the unit, the target, the allowed
features, the temporal splits, the metric and the gate. This script:
  1. builds asset-week matrices from immutable raw data, treating unobserved weeks as missing, not as zero;
  2. scores only assets seen before validation and reports the downtime that falls outside them (coverage);
  3. computes features from weeks strictly before each target week;
  4. compares simple baselines and two models with the decision metric, choosing on validation (ties go to the simpler);
  5. confirms once on test against the BEST baseline, with a block-bootstrap interval;
  6. writes a run record (data, code and contract hashes) that `python -m mlh.gate` reads.
--leak adds, on purpose, a feature known only after the week ends, to show what the gate catches.

Usage: python examples/weekly_risk/run.py [--leak]       (needs numpy and scikit-learn; see requirements.txt)
"""
import argparse
import csv
import datetime as dt
import sys
import warnings
from pathlib import Path

import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from mlh import contract as mc, registry  # noqa: E402
from mlh.metrics import block_bootstrap_ci, capture_at_k  # noqa: E402

TIE = 0.005   # validation difference in the metric treated as a tie; the simpler model wins a tie


def load(c):
    rows = list(csv.DictReader(open(ROOT / c['data']['path'], encoding='utf-8')))
    weeks = sorted({r['week_start'] for r in rows})
    assets = sorted({r['asset_id'] for r in rows})
    wi, ai = {w: i for i, w in enumerate(weeks)}, {a: i for i, a in enumerate(assets)}
    shape = (len(assets), len(weeks))
    minutes, events, observed = np.zeros(shape), np.zeros(shape), np.zeros(shape, dtype=bool)
    line = {}
    for r in rows:
        a, t = ai[r['asset_id']], wi[r['week_start']]
        minutes[a, t], events[a, t], observed[a, t] = float(r['downtime_min']), int(r['events']), r['observed'] == '1'
        line[a] = r['line']
    lines = sorted(set(line.values()))
    return weeks, assets, minutes, events, observed, np.array([lines.index(line[a]) for a in range(len(assets))]), lines


def week_index(weeks, iso):
    return weeks.index(iso)


def features(minutes, events, observed, line, t, leak):
    """Features for target week t from weeks < t only. Unobserved weeks are NaN, never zero."""
    h = np.where(observed[:, :t], minutes[:, :t], np.nan)
    e = np.where(observed[:, :t], events[:, :t], np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)       # all-NaN windows become NaN, then filled below
        mean = lambda n: np.nanmean(h[:, -n:], axis=1)
        cols = {'mean_4': mean(4), 'mean_13': mean(13), 'mean_26': mean(26)}
    fill = np.nan_to_num(cols['mean_26'])
    for n in (1, 2, 4):
        cols[f'lag_{n}'] = np.where(np.isnan(h[:, -n]), fill, h[:, -n])
    for k in ('mean_4', 'mean_13', 'mean_26'):
        cols[k] = np.nan_to_num(cols[k])
    cols['events_13'] = np.nansum(e[:, -13:], axis=1)
    last = [np.nonzero(np.nan_to_num(row) > 0)[0] for row in e]
    cols['weeks_since_event'] = np.array([min(t - 1 - l[-1], 26) if len(l) else 26 for l in last], dtype=float)
    cols['observed_share_13'] = observed[:, t - 13:t].mean(axis=1)
    cols['line'] = line.astype(float)
    if leak:
        cols['events_target_week'] = events[:, t]                 # known only after the week ends
    return cols


def table(minutes, events, observed, line, weeks_range, scored, leak):
    X, y, period, names = [], [], [], None
    for t in weeks_range:
        cols = features(minutes, events, observed, line, t, leak)
        names = list(cols)
        keep = scored & observed[:, t]                             # unobserved weeks are not targets
        X.append(np.column_stack([cols[n] for n in names])[keep])
        y.append(minutes[keep, t])
        period.append(np.full(keep.sum(), t))
    return np.vstack(X), np.concatenate(y), np.concatenate(period), names


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--leak', action='store_true', help='add a feature known only after the week ends (on purpose)')
    a = ap.parse_args()
    c = mc.load(Path(__file__).with_name('contract.json'))
    k, s = c['metric']['k'], c['splits']
    weeks, assets, minutes, events, observed, line, lines = load(c)
    train_end, val_end, test_end = (week_index(weeks, s[f]) for f in ('train_end', 'validation_end', 'test_end'))
    splits = {'train': range(s['history_periods'], train_end + 1), 'validation': range(train_end + 1, val_end + 1),
              'test': range(val_end + 1, test_end + 1)}
    scored = (events[:, :train_end + 1] > 0).any(axis=1)          # chosen with data before validation only
    data = {n: table(minutes, events, observed, line, r, scored, a.leak) for n, r in splits.items()}
    names = data['train'][3]
    col = {n: i for i, n in enumerate(names)}

    baselines = {'last_week': lambda X: X[:, col['lag_1']], 'mean_4': lambda X: X[:, col['mean_4']],
                 'mean_13': lambda X: X[:, col['mean_13']]}
    Xtr, ytr, _, _ = data['train']
    num = [i for n, i in col.items() if n != 'line']
    design = lambda X: np.column_stack([np.log1p(X[:, num])] + [(X[:, col['line']] == j).astype(float) for j in range(len(lines))])
    glm = make_pipeline(StandardScaler(), PoissonRegressor(alpha=1e-2, max_iter=1000)).fit(design(Xtr), ytr)
    gbm = HistGradientBoostingRegressor(loss='poisson', max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                        categorical_features=[col['line']], random_state=0).fit(Xtr, ytr)
    models = {'poisson_glm': lambda X: glm.predict(design(X)), 'gbm_poisson': gbm.predict}   # simplest first

    results, per_period = {}, {}
    for split in ('validation', 'test'):
        X, y, period, _ = data[split]
        results[split], per_period[split] = {}, {}
        for n, f in {**baselines, **models, 'oracle': None}.items():
            cap = capture_at_k(y, y if f is None else f(X), period, k)
            per_period[split][n], results[split][n] = cap, float(cap.mean())
    val, test = results['validation'], results['test']
    chosen_baseline = max(baselines, key=val.get)
    best = max(val[m] for m in models)
    model = next(m for m in models if val[m] >= best - TIE)
    best_test_baseline = max(baselines, key=test.get)              # conservative comparison on test
    delta, lo, hi = block_bootstrap_ci(per_period['test'][model] - per_period['test'][best_test_baseline],
                                       level=c['gate']['ci_level'], block=c['gate'].get('bootstrap_block', 1))
    outside = ~scored
    test_weeks = list(splits['test'])
    out_min = float((minutes[outside][:, test_weeks] * observed[outside][:, test_weeks]).sum())
    in_min = float((minutes[scored][:, test_weeks] * observed[scored][:, test_weeks]).sum())
    res = {
        'k': k, 'validation': val, 'test': test,
        'chosen': {'model': model, 'baseline_on_validation': chosen_baseline},
        'test_vs_best_baseline': {'baseline': best_test_baseline, 'delta': delta, 'ci_low': lo, 'ci_high': hi},
        'features_used': names, 'leak_on_purpose': a.leak,
        'coverage': {'scored_assets': int(scored.sum()), 'unscored_assets': int(outside.sum()),
                     'test_minutes_outside_scored': out_min, 'test_share_outside_scored': out_min / (in_min + out_min)},
        'splits': {n: [weeks[r.start], weeks[r.stop - 1]] for n, r in splits.items()},
    }
    code = [Path(__file__), ROOT / 'mlh/metrics.py', ROOT / 'mlh/contract.py', ROOT / 'mlh/registry.py']
    path = registry.record(c, code, {'leak': a.leak, 'tie': TIE}, res, evaluated_test=True,
                           versions={'numpy': np.__version__, 'scikit-learn': sklearn.__version__}, tag='leak' if a.leak else '')

    print(f'{c["name"]} v{c["version"]} · {int(scored.sum())} scored assets · K={k}' + (' · LEAK ON PURPOSE' if a.leak else ''))
    for split in ('validation', 'test'):
        print(f'{split}: ' + ', '.join(f'{n} {v:.3f}' for n, v in results[split].items()))
    print(f'chosen on validation: {model} (baseline {chosen_baseline}); on test vs best baseline {best_test_baseline}: '
          f'{delta:+.3f} [{lo:+.3f}, {hi:+.3f}]')
    print(f'coverage: {res["coverage"]["test_share_outside_scored"]:.1%} of test downtime falls on {int(outside.sum())} unscored assets')
    print(f'run record: {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}')
    print(f'next: make gate RUN={path}')


if __name__ == '__main__':
    main()
