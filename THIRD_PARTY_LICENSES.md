# Third-Party Licenses

| Component | Version | License | How GeoAlpha uses it |
|---|---|---|---|
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | v0.7.1 (git tag) | Apache-2.0 | Python dependency, extended by subclass (`GeoAlphaTradingGraph`). Not modified. |
| [Kronos](https://github.com/shiyu-coder/Kronos) | commit `67b630e` | MIT | `model/` vendored unmodified under `backend/src/geoalpha/vendor/kronos/` with its LICENSE (added with the forecast feature). Weights downloaded from Hugging Face at runtime. |
| [worldmonitor-sdk](https://pypi.org/project/worldmonitor-sdk/) | 0.1.2 | MIT | Python client for the WorldMonitor API / MCP server. |
| [WorldMonitor platform](https://github.com/koala73/worldmonitor) | n/a | AGPL-3.0 | **Called over the network only** (hosted or self-hosted). No WorldMonitor source is vendored or modified in this repository. |
| [lightweight-charts](https://github.com/tradingview/lightweight-charts) | 5.x | Apache-2.0 | Forecast chart (added with the forecast feature). Requires TradingView attribution, shown in the chart. |

Other npm and PyPI dependencies are listed in `frontend/package.json` and `backend/pyproject.toml` with their own licences.
