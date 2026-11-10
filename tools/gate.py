"""Entry point for the promotion gate that works with `python3 -I` (isolated mode ignores the current folder).

Usage: python3 -I tools/gate.py runs/<run>.json      (or `make gate RUN=runs/<run>.json`)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mlh.gate import main  # noqa: E402

sys.exit(main())
