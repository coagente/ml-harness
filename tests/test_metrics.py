import unittest

try:
    import numpy as np
    from mlh.metrics import block_bootstrap_ci, capture_at_k
except ImportError:   # the harness checks run without numpy; these tests need it
    np = None


@unittest.skipIf(np is None, 'numpy is not installed')
class MetricsTest(unittest.TestCase):
    def test_capture_at_k_perfect_and_worst(self):
        y = np.array([5.0, 3.0, 0.0, 2.0])
        period = np.zeros(4)
        self.assertAlmostEqual(capture_at_k(y, y, period, 2)[0], 0.8)
        self.assertAlmostEqual(capture_at_k(y, -y, period, 2)[0], 0.2)

    def test_periods_without_loss_are_skipped(self):
        y = np.array([0.0, 0.0, 1.0, 1.0])
        period = np.array([0, 0, 1, 1])
        self.assertEqual(len(capture_at_k(y, y, period, 1)), 1)

    def test_ties_do_not_favour_input_order(self):
        y = np.array([0.0] * 9 + [10.0])
        period = np.zeros(10)
        caps = [capture_at_k(y, np.zeros(10), period, 1, seed=s)[0] for s in range(50)]
        self.assertTrue(0 < np.mean(caps) < 0.5)

    def test_block_bootstrap_interval_contains_mean(self):
        d = np.random.default_rng(0).normal(0.03, 0.02, 13)
        mean, lo, hi = block_bootstrap_ci(d, level=0.9, block=3)
        self.assertLess(lo, mean)
        self.assertLess(mean, hi)


if __name__ == '__main__':
    unittest.main()
