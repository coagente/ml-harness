"""Promotion gate: decide from a run record whether a model moves on to the next review.

Rules, with thresholds taken from the contract stored in the record:
  1. improvement - the model beats the BEST simple baseline on the test split by at least gate.min_improvement
                   (conservative: it must beat any rule the team could use tomorrow, not only the one picked earlier);
  2. certainty   - the lower bound of the interval of that improvement is above zero;
  3. ceiling     - the model stays below gate.ceiling_fraction of the oracle: near-perfect usually means leakage;
  4. contract    - the run used only features the contract allows and no leak on purpose;
  5. test budget - the test split was not evaluated more than gate.max_test_evaluations times under this contract;
  6. fresh       - the contract, the data and the code still have the hashes the run was produced with.
Rule 3 only catches gross leakage; subtle leakage is caught by reviewing the contract and the diff. Passing does not
validate business value: the model moves to the next review (contract, diff and a pilot with users).
Exit code 0 when every rule passes and 1 otherwise, so it works as a CI step. Standard library only.

Usage: python3 -I -m mlh.gate runs/<run>.json
"""
import argparse
import json
import sys
from pathlib import Path

from .contract import sha256_file

ROOT = Path(__file__).resolve().parents[1]


def _same(path, sha):
    return path.exists() and sha256_file(path) == sha


def evaluate(rec, root=ROOT):
    """Return (passed, rules) where rules is a list of (name, ok, detail)."""
    g = rec['contract']['gate']
    res = rec['results']
    cmp_ = res['test_vs_best_baseline']
    model = res['chosen']['model']
    test = res['test']
    outside = [f for f in res['features_used'] if f not in rec['contract']['features_allowed']]
    in_contract = not outside and not res['leak_on_purpose']
    fresh = (_same(root / rec['contract']['path'], rec['contract']['sha256'])
             and _same(root / rec['data']['path'], rec['data']['sha256'])
             and all(_same(root / f, sha) for f, sha in rec['code'].items()))
    rules = [
        ('improvement', cmp_['delta'] >= g['min_improvement'],
         f'{cmp_["delta"]:+.3f} vs {cmp_["baseline"]} (needs >= {g["min_improvement"]:.3f})'),
        ('certainty', cmp_['ci_low'] > 0, f'{int(g["ci_level"] * 100)}% interval [{cmp_["ci_low"]:+.3f}, {cmp_["ci_high"]:+.3f}]'),
        ('ceiling', test[model] < g['ceiling_fraction'] * test['oracle'],
         f'{test[model]:.3f} vs oracle {test["oracle"]:.3f} (must stay below {g["ceiling_fraction"]:.0%})'),
        ('contract', in_contract, 'only allowed features' if in_contract else
         'outside the contract: ' + ', '.join(outside + (['leak on purpose'] if res['leak_on_purpose'] else []))),
        ('test budget', rec['test_evaluations_for_contract'] <= g['max_test_evaluations'],
         f'{rec["test_evaluations_for_contract"]} evaluation(s) of the test split (budget {g["max_test_evaluations"]})'),
        ('fresh', fresh, 'contract, data and code unchanged since the run' if fresh else 'contract, data or code changed: rerun'),
    ]
    return all(ok for _, ok, _ in rules), rules


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('run', help='path to a run record in runs/')
    a = ap.parse_args(argv)
    rec = json.loads(Path(a.run).read_text(encoding='utf-8'))
    passed, rules = evaluate(rec)
    model = rec['results']['chosen']['model']
    print(f'Gate · {rec["contract"]["name"]} v{rec["contract"]["version"]} · model {model} · run {rec["run_id"]}')
    for name, ok, detail in rules:
        print(f'  [{"pass" if ok else "FAIL"}] {name:12} {detail}')
    print('PASS: the model moves to the next review (contract, diff, pilot with users). This does not validate business value.'
          if passed else 'FAIL: keep the baseline; the model is not promoted.')
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
