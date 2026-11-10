# ml-harness

An agent harness for evidence-based machine learning with Claude Code and Codex. Data contracts, simple baselines first,
run records with hashes and a promotion gate. Hooks enforce them while the agent works, and CI checks them again on
every pull request.

> **The idea.** The difference between an experiment and a model in operation is not the algorithm. It is the process:
> a clear decision, a data contract, simple baselines, the error that matters and a gate that decides.

## Quickstart

```sh
git clone https://github.com/coagente/ml-harness.git && cd ml-harness
make setup        # .venv with pinned numpy and scikit-learn (Python 3.12)
make check        # "All checks passed."
make test
make demo         # weekly_risk: contract -> baselines -> models -> run record
make gate         # PASS: +4.3 points over the best baseline, interval above zero
make demo-leak && make gate    # FAIL: a leak that only the contract rule catches
make demo-small   # do you need a neural network with 16 rows?
```

New to Claude Code? Follow **[Install the harness on macOS, Windows (WSL 2) or Linux, with Claude Code in VS Code](docs/install-claude-code-vscode.md)**.
On Windows, run everything inside WSL 2.

## What is inside

| Path | What it is |
|---|---|
| [AGENTS.md](AGENTS.md) | Single source of instructions for coding agents; [CLAUDE.md](CLAUDE.md) imports it |
| [.agents/skills/](.agents/skills/) | Six skills: `data-contract`, `run-experiment`, `leakage-review`, `promotion-gate`, `record-decision`, `close-change` |
| [.claude/](.claude/) | Settings with permissions and hooks, and the `ml-reviewer` subagent |
| [tools/guard.py](tools/guard.py) | Hook: protects raw data, generated files, secrets and the main branch; orients at start; rechecks at stop |
| [tools/check.py](tools/check.py) | `make check`: manifest, contracts, run records, skills, settings, links, secrets |
| [mlh/](mlh/) | Contract validation, run registry, decision metrics (capture@K, block bootstrap) and the promotion gate |
| [examples/weekly_risk/](examples/weekly_risk/) | End to end: which K assets to inspect next week, on synthetic data with exposure, new assets, drift and bursts |
| [examples/small_data/](examples/small_data/) | Sixteen rows, twelve features: domain formula vs ridge vs neural network |
| [docs/](docs/) | [Methodology](docs/methodology.md), [harness guide](docs/harness-guide.md), [install guide](docs/install-claude-code-vscode.md), [ADRs](docs/adr/) |
| [.github/workflows/](.github/workflows/) | CI on pull requests: a cheap harness job, an ML job that asserts the gate verdicts, and an install job that runs the install guide on Ubuntu, macOS and Windows |

## What the harness enforces

| Rule (AGENTS.md) | Enforced by |
|---|---|
| Raw data is immutable | Guard (deny edits and deletions), `make check` (hashes) |
| Contract before model | `mlh/contract.py`, `make check`, gate rule "contract" |
| Baselines first, best baseline on test | `run.py` pattern, gate rule "improvement" |
| Time flows one way | Leakage-review skill, gate rule "ceiling", `ml-reviewer` subagent |
| Every number has a run record | `mlh/registry.py`; guard denies hand edits to `runs/` |
| The gate decides promotion | `make gate`, CI |
| Secrets stay out | Permissions, guard, `make check` |
| No direct changes to main | Guard, pull requests, CI |

## Example output

```
Gate · weekly_risk v1.0.0 · model poisson_glm
  [pass] improvement  +0.043 vs mean_13 (needs >= 0.020)
  [pass] certainty    90% interval [+0.023, +0.062]
  [pass] ceiling      0.346 vs oracle 0.668 (must stay below 90%)
  [pass] contract     only allowed features
  [pass] test budget  1 evaluation(s) of the test split (budget 3)
  [pass] fresh        contract, data and code unchanged since the run
PASS: the model moves to the next review (contract, diff, pilot with users). This does not validate business value.
```

Every `make demo` spends one of the contract's three test evaluations. That is on purpose: after the budget, the gate
fails, because repeated looks at the test split are tuning on test. The budget is counted in the run-record folder, so
to experiment freely use a fresh scratch folder each time:
`export MLH_RUNS_DIR=$(mktemp -d)`, then `make demo` and `make gate RUN=$(ls -t "$MLH_RUNS_DIR"/*.json | head -1)`.

## Use it for your project

See [docs/harness-guide.md](docs/harness-guide.md#5-adapt-it-to-your-project). In short: put your data in `data/raw/`
and run `make manifest`. Write the contract with the `data-contract` skill and agree the gate thresholds before
training. Then follow the order of `examples/weekly_risk/run.py` and open a pull request.

## Requirements

Git, `make` and `python3` 3.9 or later: the guard, the checks, the contract, the registry and the gate use only the
standard library. The examples need Python 3.12 with numpy and scikit-learn (pinned in
[requirements.txt](requirements.txt)): `make setup` builds that `.venv` with [uv](https://docs.astral.sh/uv/), which
downloads Python 3.12 if needed, or with your `python3` if it is 3.12. On Windows, use WSL 2; step by step for each
system in the [install guide](docs/install-claude-code-vscode.md). The data is synthetic and
generated by [generate_data.py](examples/weekly_risk/generate_data.py).

## License

[Apache-2.0](LICENSE).
