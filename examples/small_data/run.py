"""small_data: do you need a neural network with 16 rows to find out which features drive a quote?

A synthetic quoting world where the truth is known: the price floor is the sum of five cost components times a margin,
plus noise. Two more features are correlated with costs and five have no effect. Values are invented.

Three questions:
  1. With 16 quotes and leave-one-out validation, which model errs least?
  2. Which features does the network look like it uses? Permutation importance measured on its own 16 rows (what a
     team with only those rows would do) versus on 500 rows it never saw; repeated over 30 draws of 16 rows.
  3. How many rows until the network is worth it?

Usage: python examples/small_data/run.py        (needs numpy and scikit-learn; about 10 seconds)
"""
import warnings

import numpy as np
from sklearn.compose import TransformedTargetRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.inspection import permutation_importance
from sklearn.linear_model import RidgeCV
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

COSTS = ['material', 'labor', 'overhead', 'tooling', 'freight']
PROXIES = ['weight_kg', 'standard_hours']
NOISE = ['region', 'month', 'revision', 'platform_code', 'response_days']
FEATURES = COSTS + PROXIES + NOISE
warnings.filterwarnings('ignore', category=ConvergenceWarning)   # a network on 16 rows often fails to converge


def generate(n, rng):
    material, labor = rng.uniform(20, 120, n), rng.uniform(5, 30, n)
    x = {'material': material, 'labor': labor, 'overhead': rng.uniform(4, 20, n), 'tooling': rng.uniform(1, 10, n),
         'freight': rng.uniform(1, 6, n), 'weight_kg': material / 1.6 + rng.normal(0, 6, n),
         'standard_hours': labor / 18 + rng.normal(0, 0.25, n), 'region': rng.integers(1, 5, n).astype(float),
         'month': rng.integers(1, 13, n).astype(float), 'revision': rng.integers(1, 6, n).astype(float),
         'platform_code': rng.integers(1, 31, n).astype(float), 'response_days': rng.uniform(5, 60, n)}
    y = sum(x[c] for c in COSTS) * (1 + rng.normal(0.12, 0.01, n)) + rng.normal(0, 1.0, n)
    return np.column_stack([x[c] for c in FEATURES]), y


class CostFormula:
    """Domain knowledge: add the five costs and learn a single number, the median margin."""
    idx = [FEATURES.index(c) for c in COSTS]

    def fit(self, X, y):
        self.margin = float(np.median(y / X[:, self.idx].sum(1)))
        return self

    def predict(self, X):
        return X[:, self.idx].sum(1) * self.margin


class Mean:
    def fit(self, X, y):
        self.m = float(y.mean())
        return self

    def predict(self, X):
        return np.full(len(X), self.m)


def ridge():
    return make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-3, 3, 13)))


def net(seed):
    mlp = MLPRegressor(hidden_layer_sizes=(32, 16), alpha=1e-3, max_iter=3000, random_state=seed)
    return TransformedTargetRegressor(regressor=make_pipeline(StandardScaler(), mlp), transformer=StandardScaler())


def loo_median_error(X, y, make):
    p = np.empty(len(y))
    for i in range(len(y)):
        m = np.arange(len(y)) != i
        p[i] = make().fit(X[m], y[m]).predict(X[i:i + 1])[0]
    return 100 * float(np.median(np.abs(p / y - 1)))


def main():
    X, y = generate(16, np.random.default_rng(42))
    print('1. Median error with leave-one-out on 16 quotes:')
    for name, make in [('mean', Mean), ('cost formula', CostFormula), ('ridge, 12 features', ridge)]:
        print(f'   {name:24} {loo_median_error(X, y, make):5.1f}%')
    nets = [loo_median_error(X, y, lambda s=s: net(s)) for s in range(5)]
    print(f'   {"network, 12 features":24} {min(nets):5.1f}% to {max(nets):.1f}% depending on the random seed')

    Xu, yu = generate(500, np.random.default_rng(999))
    counts = {'network, on its 16 rows': 0, 'network, on 500 unseen rows': 0, 'ridge, on its 16 rows': 0}
    for r in range(30):
        Xs, ys = generate(16, np.random.default_rng(1000 + r))
        n, rg = net(r).fit(Xs, ys), ridge().fit(Xs, ys)
        for key, (model, Xe, ye) in {'network, on its 16 rows': (n, Xs, ys), 'network, on 500 unseen rows': (n, Xu, yu),
                                     'ridge, on its 16 rows': (rg, Xs, ys)}.items():
            imp = permutation_importance(model, Xe, ye, n_repeats=10, random_state=r).importances_mean
            counts[key] += any(FEATURES[i] in NOISE for i in np.argsort(-imp)[:3])
    print('2. Out of 30 draws of 16 quotes, how often a no-effect feature made the top 3 by permutation importance:')
    for key, v in counts.items():
        print(f'   {key:28} {v:2} of 30')

    Xt, yt = generate(5000, np.random.default_rng(7))
    print('3. Median error on 5,000 new quotes by training size (cost formula / ridge / network):')
    for size in (16, 64, 256, 1024, 4096):
        errs = []
        for make in (CostFormula, ridge, lambda: net(0)):
            Xs, ys = generate(size, np.random.default_rng(size))
            errs.append(100 * float(np.median(np.abs(make().fit(Xs, ys).predict(Xt) / yt - 1))))
        print(f'   n={size:5}   {errs[0]:4.1f}%   {errs[1]:4.1f}%   {errs[2]:5.1f}%')
    print('Takeaway: with few rows, structure comes from domain knowledge and a regularized simple model; measure importance '
          'on data the model never saw.')


if __name__ == '__main__':
    main()
