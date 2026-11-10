"""`make sync`: link every skill in .agents/skills/ from .claude/skills/, so Claude Code and Codex share one source.

Removes links whose skill no longer exists. Standard library only.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    source, links = ROOT / '.agents/skills', ROOT / '.claude/skills'
    links.mkdir(parents=True, exist_ok=True)
    names = {d.name for d in source.iterdir() if d.is_dir()}
    for n in sorted(names):
        link = links / n
        if link.is_symlink() or link.exists():
            if link.is_symlink() and link.resolve() == (source / n).resolve():
                continue
            link.unlink()
        os.symlink(Path('..', '..', '.agents', 'skills', n), link)
        print(f'linked .claude/skills/{n}')
    for x in links.iterdir():
        if x.name not in names and x.is_symlink():
            x.unlink()
            print(f'removed stale link .claude/skills/{x.name}')


if __name__ == '__main__':
    main()
