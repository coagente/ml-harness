"""Claude Code hook that enforces the rules of AGENTS.md that a machine can check. Standard library only.

Wired in .claude/settings.json for three events; the payload arrives as JSON on stdin:
  SessionStart - adds a short orientation (branch, contracts, latest runs, current check problems) to the context and
                 remembers the problems that already existed.
  PreToolUse   - denies, with the reason shown to the agent:
                   * modifying or deleting existing files under data/raw/ (raw data is immutable; adding files is fine);
                   * hand edits to generated files: run records in runs/ and data/raw/MANIFEST.sha256;
                   * reading or touching secrets (.env, keys, credentials), except .env.example;
                   * committing on main/master, pushing to main/master and skipping hooks with --no-verify.
  Stop         - if the session introduced new `make check` problems, sends the agent back once to fix them.
A guard that crashes must not stop work: any internal error lets the call through.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = 'data/raw/'
GENERATED = (re.compile(r'^runs/.+\.json$'), re.compile(r'^data/raw/MANIFEST\.sha256$'))
SECRET = re.compile(r'(?<![\w.-])(?:[\w./-]*/)?(?:\.env(?:\.(?!example\b)[\w.-]+)?|[\w.-]+\.(?:pem|key|p12|pfx)|id_(?:rsa|ed25519)'
                    r'|credentials\.json|secrets/[\w./-]*)(?![\w.-])')
EDIT_TOOLS = {'Edit', 'Write', 'MultiEdit', 'NotebookEdit'}
READ_TOOLS = {'Read', 'Grep', 'Glob'}
WRITES_RAW = re.compile(r'(?:\brm\b|\bmv\b|\btruncate\b|\bshred\b|\bsed\s+-i|\btee\b|>>?|\bgit\s+(?:rm|checkout\s+--|restore)\b)'
                        r'[^|;&]*\bdata/raw/')
PROTECTED_BRANCHES = ('main', 'master')


def rel(path, root):
    p = Path(path)
    p = p if p.is_absolute() else root / p
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def deny(reason):
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': reason}}


def current_branch(root):
    try:
        return subprocess.run(['git', 'branch', '--show-current'], cwd=root, capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def pre_tool_use(tool, inp, root, branch):
    path = inp.get('file_path') or inp.get('notebook_path') or inp.get('path')
    if tool in EDIT_TOOLS | READ_TOOLS and path:
        if SECRET.search(Path(path).as_posix()):
            return deny(f'{path} looks like a secret. Secrets never enter the conversation or the repository (AGENTS.md, rule 8).')
        r = rel(path, root)
        if tool in EDIT_TOOLS and r:
            if r.startswith(RAW) and (root / r).exists() and r != 'data/raw/MANIFEST.sha256':
                return deny(f'{r} is raw data and raw data is immutable (AGENTS.md, rule 1). Add a new file and fix problems '
                            'downstream, in code.')
            if any(g.match(r) for g in GENERATED):
                return deny(f'{r} is generated: run records come from mlh.registry and the manifest from `make manifest`. '
                            'Rerun instead of editing (AGENTS.md, rule 5).')
    if tool == 'Bash':
        cmd = inp.get('command', '')
        if SECRET.search(cmd):
            return deny('The command touches a file that looks like a secret (AGENTS.md, rule 8).')
        if WRITES_RAW.search(cmd):
            return deny('The command would modify or delete raw data under data/raw/ (AGENTS.md, rule 1).')
        if re.search(r'\bgit\b[^|;&]*--no-verify\b', cmd):
            return deny('Do not skip git hooks with --no-verify (AGENTS.md, rule 9).')
        if re.search(r'\bgit\s+commit\b', cmd) and branch in PROTECTED_BRANCHES:
            return deny(f'You are on {branch}. Create a branch first; changes reach {branch} only through a pull request (AGENTS.md, rule 9).')
        if re.search(r'\bgit\s+push\b', cmd) and (re.search(r'\b(?:main|master)\b', cmd) or branch in PROTECTED_BRANCHES):
            return deny('Pushing to main/master is not allowed; push your branch and open a pull request (AGENTS.md, rule 9).')
    return None


def check_problems(root):
    sys.path.insert(0, str(root / 'tools'))
    import check  # noqa: E402  (same folder; standard library only)
    return check.problems(root)


def state_file(session):
    safe = re.sub(r'[^\w-]', '', session or 'default')
    return Path(tempfile.gettempdir()) / f'mlh-guard-{safe}.json'


def session_start(payload, root):
    problems = check_problems(root)
    state_file(payload.get('session_id')).write_text(json.dumps(problems), encoding='utf-8')
    contracts = sorted(p.parent.name for p in root.glob('examples/*/contract.json'))
    runs = sorted(root.glob('runs/*.json'))[-3:]
    lines = [f'Branch: {current_branch(root) or "unknown"}. Contracts: {", ".join(contracts) or "none"}.',
             f'Latest runs: {", ".join(p.name for p in runs) or "none yet"}.',
             f'make check: {"all green" if not problems else f"{len(problems)} problem(s) already present: " + "; ".join(problems[:3])}.',
             'Read AGENTS.md before changing anything; close every change with the close-change skill.']
    return {'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': '\n'.join(lines)}}


def stop(payload, root):
    if payload.get('stop_hook_active'):
        return None
    f = state_file(payload.get('session_id'))
    before = set(json.loads(f.read_text(encoding='utf-8'))) if f.exists() else set()
    new = [p for p in check_problems(root) if p not in before]
    if not new:
        return None
    return {'decision': 'block', 'reason': 'make check reports problems this session introduced. Fix them, or explain why '
                                           'they are expected, before finishing: ' + '; '.join(new[:5])}


def main():
    try:
        payload = json.load(sys.stdin)
        event = payload.get('hook_event_name')
        root = Path(payload.get('cwd') or ROOT) if (Path(payload.get('cwd') or ROOT) / 'AGENTS.md').exists() else ROOT
        if event == 'PreToolUse':
            out = pre_tool_use(payload.get('tool_name', ''), payload.get('tool_input') or {}, root, current_branch(root))
        elif event == 'SessionStart':
            out = session_start(payload, root)
        elif event == 'Stop':
            out = stop(payload, root)
        else:
            out = None
        if out:
            print(json.dumps(out))
    except Exception as e:  # noqa: BLE001 - a broken guard must not block work
        print(f'guard error ignored: {e}', file=sys.stderr)
    sys.exit(0)


if __name__ == '__main__':
    main()
