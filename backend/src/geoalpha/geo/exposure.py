"""Which countries, commodities and chokepoints a ticker is exposed to (research R5).
Cached per (ticker, quarter): business mix changes slowly."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel, Field

from geoalpha.db.models import ExposureProfileRow
from geoalpha.db.session import session_scope
from geoalpha.geo.fixture import exposure_fixture

log = logging.getLogger(__name__)

Impact = str  # positive | negative | mixed | uncertain


class ExposureCountry(BaseModel):
    iso2: str = Field(pattern=r"^[A-Z]{2}$")
    weight: float = Field(ge=0, le=1)
    reason: str


class ExposureProfile(BaseModel):
    countries: list[ExposureCountry] = Field(min_length=1, max_length=6)
    commodities: list[str] = []
    chokepoints: list[str] = []
    themes: list[str] = Field(default_factory=list, max_length=5)
    # How each signal category tends to affect this ticker (used by the deterministic assessor).
    impact: dict[str, Impact] = {}

    def normalized(self) -> ExposureProfile:
        total = sum(c.weight for c in self.countries)
        if total > 1:
            for c in self.countries:
                c.weight = round(c.weight / total, 3)
        return self


def quarter_of(d: date) -> str:
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


_DEFAULT = ExposureProfile(
    countries=[ExposureCountry(iso2="US", weight=0.5, reason="Primary listing market")]
)


def get_exposure(
    ticker: str, analysis_date: date, *, fixture: bool, quick_llm: Any = None
) -> ExposureProfile:
    if fixture:
        data = exposure_fixture(ticker)
        return ExposureProfile.model_validate(data).normalized() if data else _DEFAULT
    quarter = quarter_of(analysis_date)
    with session_scope() as s:
        row = s.get(ExposureProfileRow, (ticker, quarter))
        if row is not None:
            return ExposureProfile.model_validate(row.data)
    profile = _llm_exposure(ticker, quick_llm) if quick_llm is not None else _DEFAULT
    with session_scope() as s:
        s.merge(
            ExposureProfileRow(
                ticker=ticker,
                quarter=quarter,
                data=profile.model_dump(),
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
    return profile


def _company_profile(ticker: str) -> str:
    try:
        import yfinance as yf

        info = yf.Ticker(ticker).get_info()
    except Exception:  # noqa: BLE001
        return f"Ticker {ticker} (profile unavailable)."
    keys = ("longName", "sector", "industry", "country", "longBusinessSummary")
    return "\n".join(f"{k}: {info.get(k)}" for k in keys if info.get(k))


def _llm_exposure(ticker: str, llm: Any) -> ExposureProfile:
    prompt = (
        "You map a listed company to its material geopolitical exposures.\n\n"
        f"{_company_profile(ticker)}\n\n"
        "Return up to 6 countries (ISO 3166-1 alpha-2) where revenue, production, supply chain "
        "or key routes are concentrated, each with a weight 0-1 (weights sum to at most 1) and a "
        "short reason; the commodities it is sensitive to; relevant shipping chokepoints "
        "(e.g. strait_of_hormuz, red_sea, taiwan_strait, suez_canal, panama_canal, "
        "strait_of_malacca); up to 5 themes; and for each signal category (conflict, "
        "instability, sanctions, supply_route, commodity_shock, energy, cyber, disaster, policy) "
        "whether escalation is typically positive, negative, mixed or uncertain for this stock."
    )
    try:
        out = llm.with_structured_output(ExposureProfile).invoke(prompt)
        profile = out if isinstance(out, ExposureProfile) else ExposureProfile.model_validate(out)
        return profile.normalized()
    except Exception:  # noqa: BLE001 - a generic profile beats failing the stage
        log.exception("exposure LLM step failed for %s", ticker)
        return _DEFAULT
