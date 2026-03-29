from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _is_railway_environment() -> bool:
    railway_markers = (
        "RAILWAY_ENVIRONMENT",
        "RAILWAY_PROJECT_ID",
        "RAILWAY_SERVICE_ID",
        "RAILWAY_REPLICA_ID",
        "RAILWAY_STATIC_URL",
    )
    return any(os.getenv(marker) for marker in railway_markers)


@dataclass(slots=True)
class Settings:
    discord_token: str
    database_url: str
    dev_guild_id: int | None
    starting_coins: int = 5000
    starting_crystals: int = 300
    starting_stamina: int = 120
    stamina_regen_minutes: int = 12
    summon_cost_crystals: int = 100
    summon_cost_coins: int = 1000
    summon_pity_threshold: int = 30


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    token = os.getenv("DISCORD_TOKEN", "")
    database_url = os.getenv("DATABASE_URL", "")
    dev_guild_id_raw = os.getenv("DEV_GUILD_ID")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    if _is_railway_environment() and database_url.startswith("sqlite:///"):
        raise RuntimeError(
            "Railway deployments cannot use sqlite:/// for DATABASE_URL because the container filesystem is ephemeral. "
            "Attach a Railway PostgreSQL service and set DATABASE_URL to that Postgres connection string."
        )

    return Settings(
        discord_token=token,
        database_url=database_url,
        dev_guild_id=int(dev_guild_id_raw) if dev_guild_id_raw else None,
    )
