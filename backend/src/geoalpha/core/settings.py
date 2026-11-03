"""Runtime configuration, read from environment variables and the repo-root `.env`."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]

# Provider name -> env var holding its key (subset TradingAgents supports most often).
_PROVIDER_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "xai": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    engine: Literal["tradingagents", "fake"] = Field("fake", alias="GEOALPHA_ENGINE")
    geo_provider: Literal["worldmonitor", "snapshot", "fixture"] = Field(
        "fixture", alias="GEOALPHA_GEO_PROVIDER"
    )
    data_dir: Path = Field(Path("./data"), alias="GEOALPHA_DATA_DIR")
    max_concurrent_runs: int = Field(2, ge=1, le=8, alias="GEOALPHA_MAX_CONCURRENT_RUNS")
    forecast_model: str = Field("NeoQuasar/Kronos-small", alias="GEOALPHA_FORECAST_MODEL")
    fake_forecast: bool = Field(False, alias="GEOALPHA_FAKE_FORECAST")
    fake_step_delay_s: float = Field(0.8, alias="GEOALPHA_FAKE_STEP_DELAY_S")

    llm_provider: str = Field("anthropic", alias="TRADINGAGENTS_LLM_PROVIDER")
    deep_model: str = Field("claude-opus-5-5", alias="TRADINGAGENTS_DEEP_THINK_LLM")
    quick_model: str = Field("claude-sonnet-5", alias="TRADINGAGENTS_QUICK_THINK_LLM")
    max_debate_rounds: int = Field(1, alias="TRADINGAGENTS_MAX_DEBATE_ROUNDS")

    worldmonitor_api_key: str | None = Field(None, alias="WORLDMONITOR_API_KEY")
    worldmonitor_base_url: str | None = Field(None, alias="WORLDMONITOR_BASE_URL")
    worldmonitor_mcp_url: str | None = Field(None, alias="WORLDMONITOR_MCP_URL")

    @property
    def resolved_data_dir(self) -> Path:
        path = self.data_dir if self.data_dir.is_absolute() else REPO_ROOT / self.data_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def llm_configured(self) -> bool:
        if self.engine == "fake":
            return True
        key_env = _PROVIDER_KEY_ENV.get(self.llm_provider)
        return key_env is None or bool(os.getenv(key_env))

    @property
    def geo_configured(self) -> bool:
        if self.geo_provider != "worldmonitor":
            return True
        return bool(self.worldmonitor_api_key or self.worldmonitor_base_url)

    def problems(self) -> list[str]:
        """User-facing configuration problems that block starting a run."""
        found: list[str] = []
        if not self.llm_configured:
            key_env = _PROVIDER_KEY_ENV.get(self.llm_provider, "the provider API key")
            found.append(
                f"{key_env} is not set, so the {self.llm_provider} models cannot run. "
                "Add it to .env or set GEOALPHA_ENGINE=fake for an offline demo."
            )
        if not self.geo_configured:
            found.append(
                "GEOALPHA_GEO_PROVIDER=worldmonitor needs WORLDMONITOR_API_KEY (hosted) "
                "or WORLDMONITOR_BASE_URL (self-hosted)."
            )
        return found


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # pydantic-settings reads .env into the model only; TradingAgents and the LLM SDKs
    # read os.environ, so export the .env keys too (never overriding real env vars).
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env", override=False)
    return settings
