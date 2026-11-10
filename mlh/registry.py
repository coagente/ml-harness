"""Run records: every reported number comes from a JSON file that says how to reproduce it.

A record stores the hashes of the data, the code and the contract, library versions, the git commit, parameters and
results. Records are written once and never edited (the guard denies hand edits to runs/). The number of times a
contract's test split has been evaluated is counted from earlier records: every look at the test set spends budget.
Standard library only.
"""
import datetime as dt
import json
import os
import platform
import subprocess
from pathlib import Path

from .contract import sha256_file

ROOT = Path(__file__).resolve().parents[1]


def runs_dir():
    """MLH_RUNS_DIR lets CI write to a scratch folder instead of the committed history."""
    return Path(os.environ.get('MLH_RUNS_DIR', ROOT / 'runs'))


def _git(*args):
    try:
        return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def test_evaluations(contract_sha):
    """How many recorded runs already evaluated the test split under this exact contract."""
    n = 0
    for f in sorted(runs_dir().glob('*.json')):
        try:
            r = json.loads(f.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        if r.get('contract', {}).get('sha256') == contract_sha and r.get('evaluated_test'):
            n += 1
    return n


def record(contract, code_files, params, results, evaluated_test, versions=None, tag=''):
    """Write a run record and return its path. results must already be JSON-serializable."""
    now = dt.datetime.now(dt.timezone.utc)
    data_path = ROOT / contract['data']['path']
    previous = test_evaluations(contract['_sha256'])
    rec = {
        'run_id': now.strftime('%Y%m%dT%H%M%SZ') + (f'_{tag}' if tag else ''),
        'created_utc': now.isoformat(timespec='seconds'),
        'contract': {'name': contract['name'], 'version': contract['version'],
                     'path': os.path.relpath(contract['_path'], ROOT), 'sha256': contract['_sha256'],
                     'gate': contract['gate'], 'metric': contract['metric'],
                     'features_allowed': contract['features']['allowed']},
        'data': {'path': contract['data']['path'], 'sha256': sha256_file(data_path)},
        'code': {os.path.relpath(f, ROOT): sha256_file(f) for f in code_files},
        'git': {'commit': _git('rev-parse', 'HEAD'), 'dirty': bool(_git('status', '--porcelain'))},
        'environment': {'python': platform.python_version(), **(versions or {})},
        'params': params,
        'evaluated_test': evaluated_test,
        'test_evaluations_for_contract': previous + (1 if evaluated_test else 0),
        'results': results,
    }
    out = runs_dir()
    out.mkdir(parents=True, exist_ok=True)
    path = out / f'{rec["run_id"]}_{contract["name"]}.json'
    path.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    return path
