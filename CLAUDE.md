@AGENTS.md

## Claude Code only

- Skills are invoked as `/data-contract`, `/run-experiment`, etc. `.claude/skills/` only holds links to
  `.agents/skills/`: edit the source there and run `make sync`.
- The `ml-reviewer` subagent reviews a change with a clean context; ask for it before opening a pull request.
- Hooks in `.claude/settings.json` run `tools/guard.py` at session start (orientation), before tools (raw data,
  generated files, secrets, main branch) and at stop (new `make check` problems). If the guard denies a call, the reason
  says where the change belongs.
- Rules for this project go in AGENTS.md or an ADR, not in personal memory.
