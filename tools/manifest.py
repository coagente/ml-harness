"""`make manifest`: register new raw data files in data/raw/MANIFEST.sha256. Standard library only.

Only appends: a file already registered keeps its hash, and a registered file whose bytes changed is reported as an
error instead of being re-hashed (raw data is immutable).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mlh.contract import sha256_file  # noqa: E402

SKIP = {'MANIFEST.sha256', 'README.md', '.gitkeep'}


def main():
    raw = ROOT / 'data/raw'
    manifest = raw / 'MANIFEST.sha256'
    listed = {}
    if manifest.exists():
        for line in manifest.read_text(encoding='utf-8').splitlines():
            if line.strip():
                sha, name = line.split(maxsplit=1)
                listed[name.strip()] = sha
    changed = [n for n, sha in listed.items() if (raw / n).exists() and sha256_file(raw / n) != sha]
    if changed:
        print('Refusing to update: these registered files changed and raw data is immutable: ' + ', '.join(changed))
        return 1
    new = sorted(f.name for f in raw.iterdir() if f.is_file() and f.name not in SKIP and f.name not in listed)
    with open(manifest, 'a', encoding='utf-8') as out:
        for n in new:
            out.write(f'{sha256_file(raw / n)}  {n}\n')
    print(f'{len(new)} new file(s) registered' + (': ' + ', '.join(new) if new else '.'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
