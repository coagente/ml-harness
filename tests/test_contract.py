import copy
import json
import unittest
from pathlib import Path

from mlh.contract import validate

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / 'examples/weekly_risk/contract.json').read_text(encoding='utf-8'))


def broken(**changes):
    c = copy.deepcopy(EXAMPLE)
    for path, value in changes.items():
        node = c
        *parents, last = path.split('__')
        for p in parents:
            node = node[p]
        node[last] = value
    return validate(c)


class ContractTest(unittest.TestCase):
    def test_example_is_valid(self):
        self.assertEqual(validate(EXAMPLE), [])

    def test_splits_must_be_ordered(self):
        self.assertTrue(any('train_end < validation_end' in p for p in broken(splits__validation_end='2025-01-01')))

    def test_data_must_be_raw(self):
        self.assertTrue(any('data/raw/' in p for p in broken(data__path='data/derived/x.csv')))

    def test_feature_cannot_be_allowed_and_forbidden(self):
        self.assertTrue(any('both allowed and forbidden' in p for p in broken(features__forbidden=['lag_1'])))

    def test_gate_thresholds_are_checked(self):
        self.assertTrue(any('ci_level' in p for p in broken(gate__ci_level=1.5)))
        self.assertTrue(any('max_test_evaluations' in p for p in broken(gate__max_test_evaluations=0)))

    def test_decision_is_required(self):
        self.assertTrue(any(p.startswith('decision') for p in broken(decision='')))


if __name__ == '__main__':
    unittest.main()
