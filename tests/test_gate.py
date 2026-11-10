import copy
import tempfile
import unittest
from pathlib import Path

from mlh.contract import sha256_file
from mlh.gate import evaluate


class GateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name, text in {'contract.json': '{}', 'data.csv': 'a\n1\n', 'run.py': 'print(1)\n'}.items():
            (self.root / name).write_text(text, encoding='utf-8')
        self.rec = {
            'run_id': 'test',
            'contract': {'name': 'c', 'version': '1', 'path': 'contract.json', 'sha256': sha256_file(self.root / 'contract.json'),
                         'gate': {'min_improvement': 0.02, 'ci_level': 0.9, 'ceiling_fraction': 0.9, 'max_test_evaluations': 3},
                         'features_allowed': ['lag_1', 'mean_4']},
            'data': {'path': 'data.csv', 'sha256': sha256_file(self.root / 'data.csv')},
            'code': {'run.py': sha256_file(self.root / 'run.py')},
            'test_evaluations_for_contract': 1,
            'results': {'chosen': {'model': 'glm'}, 'test': {'glm': 0.40, 'oracle': 0.70},
                        'test_vs_best_baseline': {'baseline': 'mean_4', 'delta': 0.05, 'ci_low': 0.01, 'ci_high': 0.09},
                        'features_used': ['lag_1', 'mean_4'], 'leak_on_purpose': False},
        }

    def tearDown(self):
        self.tmp.cleanup()

    def failing(self, rec):
        passed, rules = evaluate(rec, self.root)
        return passed, [name for name, ok, _ in rules if not ok]

    def test_honest_model_passes(self):
        self.assertEqual(self.failing(self.rec), (True, []))

    def test_small_improvement_fails(self):
        r = copy.deepcopy(self.rec)
        r['results']['test_vs_best_baseline']['delta'] = 0.01
        self.assertEqual(self.failing(r), (False, ['improvement']))

    def test_uncertain_improvement_fails(self):
        r = copy.deepcopy(self.rec)
        r['results']['test_vs_best_baseline']['ci_low'] = -0.001
        self.assertEqual(self.failing(r), (False, ['certainty']))

    def test_near_oracle_fails(self):
        r = copy.deepcopy(self.rec)
        r['results']['test']['glm'] = 0.65
        self.assertEqual(self.failing(r), (False, ['ceiling']))

    def test_feature_outside_contract_fails(self):
        r = copy.deepcopy(self.rec)
        r['results']['features_used'].append('events_target_week')
        self.assertEqual(self.failing(r), (False, ['contract']))

    def test_leak_on_purpose_fails(self):
        r = copy.deepcopy(self.rec)
        r['results']['leak_on_purpose'] = True
        self.assertEqual(self.failing(r), (False, ['contract']))

    def test_test_budget(self):
        r = copy.deepcopy(self.rec)
        r['test_evaluations_for_contract'] = 4
        self.assertEqual(self.failing(r), (False, ['test budget']))

    def test_changed_code_is_not_fresh(self):
        (self.root / 'run.py').write_text('print(2)\n', encoding='utf-8')
        self.assertEqual(self.failing(self.rec), (False, ['fresh']))


if __name__ == '__main__':
    unittest.main()
