"""Generate the synthetic raw data of the weekly_risk example: one row per asset and week.

The world is invented, with enough structure for a model to find and enough traps to make shortcuts fail:
  - each asset has its own base rate of downtime events, and lines differ;
  - some assets degrade over time, and short bursts of failures make recent weeks informative;
  - a yearly season, plant shutdowns at the end of each year and short line stoppages;
  - some assets are commissioned in the middle of the period (they did not exist before);
  - `observed` says whether the asset was operating and monitored that week. A zero with observed=0 is not "no downtime".

This is how data/raw/weekly_events.csv was produced. Raw data is immutable: the script refuses to overwrite it, and
`make check` verifies its hash in data/raw/MANIFEST.sha256. Needs numpy.

Usage: python examples/weekly_risk/generate_data.py [--out data/raw/weekly_events.csv]
"""
import argparse
import csv
import datetime as dt
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
START = dt.date(2024, 1, 1)   # a Monday
WEEKS, ASSETS, LINES, SEED = 104, 240, 6, 20240101


def generate(rng):
    line = rng.integers(0, LINES, ASSETS)
    line_mult = np.array([0.6, 0.8, 1.0, 1.1, 1.3, 1.6])[line]
    base = rng.gamma(0.7, 1.5, ASSETS) * line_mult
    w = np.arange(WEEKS)
    rate = np.outer(base, 1 + 0.15 * np.sin(2 * np.pi * w / 52))
    # Degradation: 20% of the assets get worse from a random week on, up to 3-6 times their rate.
    for a in rng.choice(ASSETS, ASSETS // 5, replace=False):
        start = rng.integers(10, WEEKS - 20)
        top = rng.uniform(3, 6)
        rate[a, start:] *= np.linspace(1, top, WEEKS - start)
    # Bursts: a few episodes of 2-5 weeks with 3-6 times the rate.
    for a in range(ASSETS):
        for _ in range(rng.poisson(2)):
            s = rng.integers(0, WEEKS - 2)
            rate[a, s:s + rng.integers(2, 6)] *= rng.uniform(3, 6)
    observed = np.ones((ASSETS, WEEKS), dtype=int)
    observed[:, [51, 52, 103]] = 0                                   # end-of-year plant shutdowns
    for l in range(LINES):                                           # short line stoppages
        for _ in range(rng.integers(1, 4)):
            s = rng.integers(0, WEEKS - 2)
            observed[line == l, s:s + rng.integers(1, 3)] = 0
    for a in rng.choice(ASSETS, ASSETS // 10, replace=False):        # commissioned mid-period
        observed[a, :rng.integers(40, 85)] = 0
    events = rng.poisson(rate * observed)
    minutes = np.zeros_like(rate)
    for a, t in zip(*np.nonzero(events)):
        minutes[a, t] = rng.lognormal(1.0, 1.8, events[a, t]).sum()
    return line, observed, events, minutes


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', default=str(ROOT / 'data/raw/weekly_events.csv'))
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists():
        raise SystemExit(f'{out} exists and raw data is immutable; write to another path to compare')
    line, observed, events, minutes = generate(np.random.default_rng(SEED))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', newline='', encoding='utf-8') as f:
        wr = csv.writer(f, lineterminator='\n')
        wr.writerow(['week_start', 'asset_id', 'line', 'observed', 'events', 'downtime_min'])
        for t in range(WEEKS):
            week = (START + dt.timedelta(weeks=t)).isoformat()
            for a in range(ASSETS):
                wr.writerow([week, f'A{a:03d}', f'L{line[a] + 1}', observed[a, t], events[a, t], f'{minutes[a, t]:.1f}'])
    print(f'{WEEKS * ASSETS:,} rows written to {out}')


if __name__ == '__main__':
    main()
