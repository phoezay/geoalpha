"""Scripted offline engine (GEOALPHA_ENGINE=fake): walks the 8 TradingAgents stages with
canned reports so the whole app can be demoed and e2e-tested without any API key.

Ticker FAILME fails the Trader stage on its first attempt (exercises retry/resume).
"""

from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path
from typing import Any

from geoalpha.core.stages import RATING_CHOICES
from geoalpha.db import repo
from geoalpha.runner.orchestrator import EngineContext, EngineResult, StageFailed

_FIXTURES = Path(__file__).parent / "fixtures" / "fake_reports"
_KNOWN_RATINGS = {
    "XOM": "Overweight",
    "CVX": "Hold",
    "KO": "Hold",
    "LMT": "Buy",
    "TSM": "Underweight",
    "GLD": "Overweight",
    "NEWIPO": "Hold",
    "FAILME": "Hold",
}
FIXTURE_TICKERS = frozenset(_KNOWN_RATINGS)


def _sections(ticker: str, date: str, rating: str) -> dict[str, str]:
    path = _FIXTURES / f"{ticker}.md"
    text = (path if path.exists() else _FIXTURES / "default.md").read_text(encoding="utf-8")
    text = text.format(ticker=ticker, date=date, rating=rating, rating_lower=rating.lower())
    parts = re.split(r"<!-- stage:(\w+) -->\n", text)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def _rating_for(ticker: str) -> str:
    if ticker in _KNOWN_RATINGS:
        return _KNOWN_RATINGS[ticker]
    digest = int(hashlib.sha256(ticker.encode()).hexdigest(), 16)
    return RATING_CHOICES[digest % len(RATING_CHOICES)]


class FakeEngine:
    def __init__(self, step_delay_s: float = 0.8) -> None:
        self.delay = step_delay_s

    def run(self, ctx: EngineContext) -> EngineResult:
        run = ctx.run
        rating = _rating_for(run.ticker)
        s = _sections(run.ticker, run.analysis_date.isoformat(), rating)

        def done(key: str) -> bool:
            return repo.get_stage(run.run_id, key).status == "done"

        def step(
            key: str, report: str | None, payload: dict[str, Any] | None = None, wait: float = 1.0
        ) -> None:
            if done(key):
                return
            ctx.on_stage(key, "running")
            time.sleep(self.delay * wait)
            ctx.on_stage(key, "done", report_md=report, payload=payload)

        # Analysts run side by side upstream: start all four, finish them staggered.
        analysts = [k for k in ("market", "sentiment", "news", "fundamentals") if not done(k)]
        for key in analysts:
            ctx.on_stage(key, "running")
        for i, key in enumerate(analysts):
            time.sleep(self.delay * (0.6 + 0.3 * i))
            ctx.on_stage(key, "done", report_md=s[key])

        debate = {"bull_history": s["bull"], "bear_history": s["bear"], "judge": s["judge"]}
        step("research_debate", s["judge"], debate, wait=1.5)

        if not done("trader"):
            ctx.on_stage("trader", "running")
            time.sleep(self.delay)
            if run.ticker == "FAILME" and repo.get_stage(run.run_id, "trader").attempts == 1:
                raise StageFailed("trader", "Simulated trader failure (FAILME test ticker)")
            ctx.on_stage("trader", "done", report_md=s["trader"])

        risk = {k: s[k] for k in ("aggressive", "conservative", "neutral")}
        step("risk_debate", s["neutral"], risk, wait=1.5)

        ctx.on_stage("decision", "running")
        time.sleep(self.delay)
        return EngineResult(pm_text=s["decision"], rating=rating)
