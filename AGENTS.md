# ml-harness · instructions for coding agents

This file is the single source of instructions for Claude Code and Codex (`CLAUDE.md` imports it). It is a map: the
detail lives in [docs/](docs/) and in the skills. Keep it under 200 lines.

## Map

| Path | What it is |
|---|---|
| `mlh/` | Library: contracts, run registry, decision metrics, promotion gate |
| `examples/` | Worked tasks. `weekly_risk/` (contract → run → gate) and `small_data/` (do you need a network with 16 rows?) |
| `data/raw/` | Immutable raw data, hashed in `MANIFEST.sha256` |
| `runs/` | Run records written by `mlh.registry`; never edited by hand |
| `tools/` | Guard (hooks), checks, gate entry point, manifest and skill sync |
| `.agents/skills/` | Skills shared by Claude Code and Codex; `.claude/skills/` only links here |
| `.claude/` | Claude Code settings (permissions, hooks) and the `ml-reviewer` subagent |
| `docs/` | Methodology, harness guide, install guide, ADRs and templates |

## Rules that never break

1. **Raw data is immutable.** Files in `data/raw/` are evidence: add new files, never modify or delete existing ones.
   Fix problems downstream, in code. The guard enforces it; `make check` verifies the hashes.
2. **Contract before model.** Every modeling task has a data contract (data-contract skill). It is changed only with a
   new version, and after a test evaluation only with an ADR.
3. **Baselines first.** Every model is compared with simple rules under the same protocol, and against the best of
   them on test.
4. **Time flows one way.** Features use only periods before the target period. Choose on validation; confirm once on
   test. Unobserved is missing, never zero.
5. **Every number has a run record.** Reported results cite a record in `runs/` written by `mlh.registry`. Records
   and the raw manifest are generated: never edit them by hand.
6. **The gate decides promotion.** `make gate RUN=...`. FAIL is a valid, reportable result. PASS is not business value:
   the model moves to review and a pilot. Results close to the oracle are leakage until proven otherwise.
7. **Evidence apart from opinion.** Claims cite a file, run or source. Mark your own reading as (inference),
   (proposal) or (not verified).
8. **Secrets stay out.** Never read, print or commit `.env` files, keys or tokens. Use `.env.example` for names only.
9. **No direct changes to main.** Work on a branch, open a pull request, `make check` and `make test` green before
   saying done. Never skip hooks.

## How to work

1. **Orient.** `make help`, the contract of the task, the latest run records.
2. **Plan if it is big.** Expensive-to-reverse choices get an ADR (record-decision skill).
3. **Do the change** with the skill that fits (table below).
4. **Close** with the close-change skill.
5. **Report** what changed, what you checked, the gate verdict and what a human must decide.

## Commands

| Command | What it does |
|---|---|
| `make setup` | Create `.venv` with the pinned dependencies (uses uv if present) |
| `make check` | Harness and evidence checks: manifest, contracts, runs, skills, settings, links, secrets |
| `make test` | Unit tests |
| `make demo` / `make demo-leak` | Run the weekly_risk example; the second adds a leak on purpose |
| `make demo-small` | Run the small_data example |
| `make gate RUN=runs/<record>.json` | Promotion gate on a run record (latest run if RUN is empty) |
| `make manifest` | Register new raw files (never re-hashes existing ones) |
| `make sync` | Link skills from `.agents/skills/` into `.claude/skills/` |

## Skills

| Skill | When |
|---|---|
| `data-contract` | Before modeling; when population, target, features, splits, metric or thresholds change |
| `run-experiment` | Training or comparing models; any number for a report |
| `leakage-review` | Before trusting a result; when it looks too good; before a pull request |
| `promotion-gate` | After a test evaluation; in CI; when someone wants to change thresholds |
| `record-decision` | Decisions that are expensive to reverse |
| `close-change` | At the end of every task that touched files |

Subagent: `ml-reviewer`, an independent review with a clean context; it never edits.

## When to stop and ask

- The decision, the owner of the thresholds or the meaning of a zero is unclear.
- A result would require changing the contract or the gate after seeing test results.
- Two sources disagree, or the data looks different from what the contract says.
- Before deleting files you did not create, adding a dependency or touching CI.
