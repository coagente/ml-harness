"""Data contracts: what a model is for, what it may use, how it is split and what it must beat.

A contract is a JSON file next to the experiment (see examples/weekly_risk/contract.json). It is written before any
model is trained and changed only through a recorded decision (docs/adr). Standard library only, so the guard, the
checks and the gate can use it without installing anything.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path

METRICS = {'capture_at_k', 'mae'}
TEXT_FIELDS = ('name', 'version', 'decision', 'unit', 'entity', 'period', 'population', 'zero_means')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def _date(value, field, problems):
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError):
        problems.append(f'{field} must be an ISO date (YYYY-MM-DD), got {value!r}')


def validate(c):
    """Return a list of problems; an empty list means the contract is usable."""
    p = []
    for f in TEXT_FIELDS:
        if not isinstance(c.get(f), str) or not c[f].strip():
            p.append(f'{f} must be a non-empty string')
    data = c.get('data', {})
    if not isinstance(data.get('path'), str):
        p.append('data.path must point to a file under data/raw/')
    elif not data['path'].startswith('data/raw/'):
        p.append('data.path must be under data/raw/ (raw data is immutable and hashed)')
    target = c.get('target', {})
    for f in ('column', 'description'):
        if not isinstance(target.get(f), str):
            p.append(f'target.{f} must be a string')
    feats = c.get('features', {})
    if not isinstance(feats.get('allowed'), list) or not feats.get('allowed'):
        p.append('features.allowed must list the features known before the cutoff')
    if not isinstance(feats.get('forbidden'), list):
        p.append('features.forbidden must list what is only known after the cutoff (may be empty)')
    elif set(feats.get('allowed') or []) & set(feats['forbidden']):
        p.append('a feature cannot be both allowed and forbidden')
    s = c.get('splits', {})
    if not isinstance(s.get('history_periods'), int) or s.get('history_periods', 0) < 1:
        p.append('splits.history_periods must be a positive integer')
    fechas = [_date(s.get(f), f'splits.{f}', p) for f in ('train_end', 'validation_end', 'test_end')]
    if all(fechas) and not fechas[0] < fechas[1] < fechas[2]:
        p.append('splits must satisfy train_end < validation_end < test_end')
    m = c.get('metric', {})
    if m.get('name') not in METRICS:
        p.append(f'metric.name must be one of {sorted(METRICS)}')
    if m.get('name') == 'capture_at_k' and (not isinstance(m.get('k'), int) or m['k'] < 1):
        p.append('metric.k must be a positive integer for capture_at_k')
    g = c.get('gate', {})
    if not isinstance(g.get('min_improvement'), (int, float)) or g['min_improvement'] < 0:
        p.append('gate.min_improvement must be a number >= 0')
    if not isinstance(g.get('ci_level'), float) or not 0 < g['ci_level'] < 1:
        p.append('gate.ci_level must be between 0 and 1, e.g. 0.9')
    if not isinstance(g.get('ceiling_fraction'), float) or not 0 < g['ceiling_fraction'] <= 1:
        p.append('gate.ceiling_fraction must be in (0, 1]')
    if not isinstance(g.get('max_test_evaluations'), int) or g['max_test_evaluations'] < 1:
        p.append('gate.max_test_evaluations must be a positive integer')
    if 'bootstrap_block' in g and (not isinstance(g['bootstrap_block'], int) or g['bootstrap_block'] < 1):
        p.append('gate.bootstrap_block must be a positive integer')
    owners = c.get('owners', {})
    for f in ('data', 'decision', 'thresholds'):
        if not isinstance(owners.get(f), str):
            p.append(f'owners.{f} must name a role')
    return p


def load(path):
    """Load and validate a contract; raise ValueError listing every problem. Adds _path and _sha256."""
    path = Path(path)
    c = json.loads(path.read_text(encoding='utf-8'))
    problems = validate(c)
    if problems:
        raise ValueError(f'{path}: ' + '; '.join(problems))
    c['_path'] = str(path)
    c['_sha256'] = sha256_file(path)
    return c
