# Vendored: Kronos

- **Upstream:** https://github.com/shiyu-coder/Kronos
- **Commit:** `67b630e` (2026-04-13)
- **Files:** `model/__init__.py`, `model/kronos.py`, `model/module.py`, `LICENSE` (MIT)
- **Vendored on:** 2026-11-03

## Why vendored

Kronos has no package metadata (it can't be installed with pip), and its `requirements.txt` pins
`pandas==2.2.2`, which conflicts with TradingAgents' `pandas>=3.0.6`. See
`specs/001-geoalpha-mvp/plan.md` → Complexity Tracking.

## Local edits

Exactly one:

1. `model/kronos.py`: `from model.module import *` → `from .module import *`. The upstream absolute
   import only works when the repo root is on `sys.path`.

Everything else is byte-for-byte upstream. GeoAlpha code only wraps it
(`geoalpha/forecast/kronos_service.py`). Weights are downloaded from Hugging Face at runtime.

## Updating

Copy the three files from a new upstream commit, re-apply the edit above, update the commit here,
and run `uv run pytest -m integration tests/integration/test_kronos_smoke.py`.
