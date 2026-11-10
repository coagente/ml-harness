"""`make check`: verify that the harness and the evidence are consistent. Standard library only.

Groups: raw data manifest, contracts, run records, skills and their links, subagents, Claude Code settings, agent
instructions, relative links in Markdown and secrets. Prints one line per group and exits 1 if any problem was found.
`problems(root)` returns the list, for the guard.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mlh.contract import sha256_file, validate  # noqa: E402

RAW_EXTRA = {'MANIFEST.sha256', 'README.md', '.gitkeep'}
# Built by concatenation so this file does not match its own patterns.
SECRET_CONTENT = re.compile('|'.join([
    '-----BEGIN ' + r'(?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
    'AKIA' + r'[0-9A-Z]{16}',
    'gh' + r'[pousr]_[A-Za-z0-9]{36}',
    'sk-' + r'(?:ant-|proj-)?[A-Za-z0-9_-]{20,}',
    'xox' + r'[abprs]-[A-Za-z0-9-]{10,}',
]))
SECRET_NAME = re.compile(r'(?:^|/)(?:\.env(?:\.(?!example$)[\w.-]+)?|[\w.-]+\.(?:pem|key|p12|pfx)|id_(?:rsa|ed25519)|credentials\.json)$')
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')


def tracked_files(root):
    try:
        out = subprocess.run(['git', 'ls-files', '-co', '--exclude-standard'], cwd=root, capture_output=True, text=True, timeout=20)
        if out.returncode == 0:
            return [f for f in out.stdout.splitlines() if (root / f).is_file()]
    except (OSError, subprocess.SubprocessError):
        pass
    return [p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '.git' not in p.parts and '.venv' not in p.parts]


def frontmatter(path):
    text = path.read_text(encoding='utf-8')
    if not text.startswith('---\n'):
        return {}
    fields = {}
    for line in text[4:text.find('\n---', 4)].splitlines():
        if ':' in line and not line.startswith(' '):
            k, v = line.split(':', 1)
            fields[k.strip()] = v.strip()
    return fields


def check_manifest(root):
    p, raw = [], root / 'data/raw'
    manifest = raw / 'MANIFEST.sha256'
    if not manifest.exists():
        return ['data/raw/MANIFEST.sha256 is missing: run `make manifest`']
    listed = {}
    for line in manifest.read_text(encoding='utf-8').splitlines():
        if line.strip():
            sha, name = line.split(maxsplit=1)
            listed[name.strip()] = sha
    for f in sorted(x for x in raw.iterdir() if x.is_file() and x.name not in RAW_EXTRA):
        if f.name not in listed:
            p.append(f'data/raw/{f.name} is not in the manifest: run `make manifest`')
        elif sha256_file(f) != listed[f.name]:
            p.append(f'data/raw/{f.name} changed after it was registered: raw data is immutable')
    p += [f'data/raw/{n} is in the manifest but missing' for n in listed if not (raw / n).exists()]
    return p


def check_contracts(root):
    p = []
    for f in sorted(root.glob('examples/*/contract.json')):
        r = f.relative_to(root).as_posix()
        try:
            c = json.loads(f.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            p.append(f'{r}: invalid JSON ({e})')
            continue
        p += [f'{r}: {x}' for x in validate(c)]
        data = c.get('data', {}).get('path')
        if isinstance(data, str) and not (root / data).exists():
            p.append(f'{r}: data.path {data} does not exist')
    return p


def check_runs(root):
    p = []
    for f in sorted(root.glob('runs/*.json')):
        try:
            r = json.loads(f.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            p.append(f'runs/{f.name}: invalid JSON')
            continue
        missing = [k for k in ('run_id', 'contract', 'data', 'code', 'results', 'evaluated_test') if k not in r]
        if missing:
            p.append(f'runs/{f.name}: missing {", ".join(missing)}')
    return p


def check_skills(root):
    p, source, links = [], root / '.agents/skills', root / '.claude/skills'
    names = sorted(d.name for d in source.iterdir() if d.is_dir()) if source.exists() else []
    if not names:
        p.append('.agents/skills/ has no skills')
    for n in names:
        fm = frontmatter(source / n / 'SKILL.md') if (source / n / 'SKILL.md').exists() else None
        if fm is None:
            p.append(f'.agents/skills/{n}/SKILL.md is missing')
            continue
        if fm.get('name') != n:
            p.append(f'.agents/skills/{n}/SKILL.md: frontmatter name must be {n}')
        if not fm.get('description'):
            p.append(f'.agents/skills/{n}/SKILL.md: frontmatter needs a description')
        link = links / n
        if not link.is_symlink() or link.resolve() != (source / n).resolve():
            p.append(f'.claude/skills/{n} must be a link to .agents/skills/{n}: run `make sync`')
    if links.exists():
        p += [f'.claude/skills/{x.name} has no source in .agents/skills/' for x in links.iterdir() if x.name not in names]
    return p


def check_agents(root):
    p = []
    for f in sorted(root.glob('.claude/agents/*.md')):
        fm = frontmatter(f)
        for k in ('name', 'description'):
            if not fm.get(k):
                p.append(f'.claude/agents/{f.name}: frontmatter needs {k}')
    return p


def check_settings(root):
    f = root / '.claude/settings.json'
    try:
        s = json.loads(f.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        return [f'.claude/settings.json: {e}']
    hooks = s.get('hooks', {})
    return [f'.claude/settings.json: the {ev} hook must run tools/guard.py' for ev in ('SessionStart', 'PreToolUse', 'Stop')
            if 'tools/guard.py' not in json.dumps(hooks.get(ev, []))]


def check_instructions(root):
    p = []
    agents = root / 'AGENTS.md'
    if not agents.exists():
        return ['AGENTS.md is missing']
    if len(agents.read_text(encoding='utf-8').splitlines()) > 200:
        p.append('AGENTS.md is longer than 200 lines: move detail to docs/ or a skill')
    claude = root / 'CLAUDE.md'
    if not claude.exists() or '@AGENTS.md' not in claude.read_text(encoding='utf-8').splitlines():
        p.append('CLAUDE.md must import AGENTS.md with a line that says @AGENTS.md')
    return p


def check_links(root, files):
    p = []
    for f in (x for x in files if x.endswith('.md')):
        text = re.sub(r'```.*?```', '', (root / f).read_text(encoding='utf-8'), flags=re.S)
        for target in LINK.findall(text):
            if re.match(r'^(?:https?:|mailto:|#)', target):
                continue
            dest = (root / f).parent / target.split('#')[0]
            if not dest.exists():
                p.append(f'{f}: broken link to {target}')
    return p


def check_secrets(root, files):
    p = [f'{f} looks like a secret file and must not be in the repository' for f in files if SECRET_NAME.search(f)]
    for f in files:
        path = root / f
        if path.stat().st_size > 2_000_000:
            continue
        try:
            if SECRET_CONTENT.search(path.read_text(encoding='utf-8')):
                p.append(f'{f} contains something that looks like a credential')
        except (UnicodeDecodeError, OSError):
            continue
    return p


def groups(root):
    files = tracked_files(root)
    return [('raw data manifest', check_manifest(root)), ('contracts', check_contracts(root)), ('run records', check_runs(root)),
            ('skills', check_skills(root)), ('subagents', check_agents(root)), ('settings and hooks', check_settings(root)),
            ('agent instructions', check_instructions(root)), ('links', check_links(root, files)), ('secrets', check_secrets(root, files))]


def problems(root=ROOT):
    return [x for _, ps in groups(Path(root)) for x in ps]


def main():
    bad = 0
    for name, ps in groups(ROOT):
        print(f'[{"ok" if not ps else "FAIL"}] {name}')
        for x in ps:
            print(f'       - {x}')
        bad += len(ps)
    print('All checks passed.' if not bad else f'{bad} problem(s).')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
