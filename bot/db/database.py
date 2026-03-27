from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import re
from typing import Any

import aiosqlite
import asyncpg

from bot.config import get_settings


SCHEMA_SQL_POSTGRES = """
CREATE TABLE IF NOT EXISTS character_catalog (
    key TEXT PRIMARY KEY,
    card_number INTEGER NOT NULL DEFAULT 0,
    name TEXT NOT NULL,
    title TEXT NOT NULL,
    rarity TEXT NOT NULL,
    grade_label TEXT NOT NULL,
    image_url TEXT NOT NULL,
    base_hp INTEGER NOT NULL,
    base_attack INTEGER NOT NULL,
    base_defense INTEGER NOT NULL,
    base_speed INTEGER NOT NULL,
    base_energy INTEGER NOT NULL,
    basic_skill TEXT NOT NULL,
    ultimate_skill TEXT NOT NULL,
    passive TEXT NOT NULL,
    domain_name TEXT NOT NULL,
    banner_tags TEXT[] NOT NULL,
    drop_weight INTEGER NOT NULL,
    quote TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS players (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL,
    coins INTEGER NOT NULL DEFAULT 0,
    crystals INTEGER NOT NULL DEFAULT 0,
    stamina INTEGER NOT NULL DEFAULT 120,
    max_stamina INTEGER NOT NULL DEFAULT 120,
    pity_counter INTEGER NOT NULL DEFAULT 0,
    daily_streak INTEGER NOT NULL DEFAULT 0,
    last_daily_at TIMESTAMPTZ,
    rank_points INTEGER NOT NULL DEFAULT 1000,
    training_scrolls INTEGER NOT NULL DEFAULT 15,
    grade_seals INTEGER NOT NULL DEFAULT 5,
    skill_scrolls INTEGER NOT NULL DEFAULT 6,
    story_stage INTEGER NOT NULL DEFAULT 1,
    last_stamina_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS player_characters (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    character_key TEXT NOT NULL REFERENCES character_catalog(key),
    level INTEGER NOT NULL DEFAULT 1,
    xp INTEGER NOT NULL DEFAULT 0,
    grade INTEGER NOT NULL DEFAULT 1,
    skill_level INTEGER NOT NULL DEFAULT 1,
    awakened BOOLEAN NOT NULL DEFAULT FALSE,
    locked BOOLEAN NOT NULL DEFAULT FALSE,
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS teams (
    player_id BIGINT PRIMARY KEY REFERENCES players(id) ON DELETE CASCADE,
    slot1 BIGINT REFERENCES player_characters(id) ON DELETE SET NULL,
    slot2 BIGINT REFERENCES player_characters(id) ON DELETE SET NULL,
    slot3 BIGINT REFERENCES player_characters(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS pvp_history (
    id BIGSERIAL PRIMARY KEY,
    attacker_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    defender_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    winner_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

SCHEMA_SQL_SQLITE = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS character_catalog (
    key TEXT PRIMARY KEY,
    card_number INTEGER NOT NULL DEFAULT 0,
    name TEXT NOT NULL,
    title TEXT NOT NULL,
    rarity TEXT NOT NULL,
    grade_label TEXT NOT NULL,
    image_url TEXT NOT NULL,
    base_hp INTEGER NOT NULL,
    base_attack INTEGER NOT NULL,
    base_defense INTEGER NOT NULL,
    base_speed INTEGER NOT NULL,
    base_energy INTEGER NOT NULL,
    basic_skill TEXT NOT NULL,
    ultimate_skill TEXT NOT NULL,
    passive TEXT NOT NULL,
    domain_name TEXT NOT NULL,
    banner_tags TEXT NOT NULL,
    drop_weight INTEGER NOT NULL,
    quote TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    coins INTEGER NOT NULL DEFAULT 0,
    crystals INTEGER NOT NULL DEFAULT 0,
    stamina INTEGER NOT NULL DEFAULT 120,
    max_stamina INTEGER NOT NULL DEFAULT 120,
    pity_counter INTEGER NOT NULL DEFAULT 0,
    daily_streak INTEGER NOT NULL DEFAULT 0,
    last_daily_at TEXT,
    rank_points INTEGER NOT NULL DEFAULT 1000,
    training_scrolls INTEGER NOT NULL DEFAULT 15,
    grade_seals INTEGER NOT NULL DEFAULT 5,
    skill_scrolls INTEGER NOT NULL DEFAULT 6,
    story_stage INTEGER NOT NULL DEFAULT 1,
    last_stamina_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS player_characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    character_key TEXT NOT NULL REFERENCES character_catalog(key),
    level INTEGER NOT NULL DEFAULT 1,
    xp INTEGER NOT NULL DEFAULT 0,
    grade INTEGER NOT NULL DEFAULT 1,
    skill_level INTEGER NOT NULL DEFAULT 1,
    awakened INTEGER NOT NULL DEFAULT 0,
    locked INTEGER NOT NULL DEFAULT 0,
    acquired_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teams (
    player_id INTEGER PRIMARY KEY REFERENCES players(id) ON DELETE CASCADE,
    slot1 INTEGER REFERENCES player_characters(id) ON DELETE SET NULL,
    slot2 INTEGER REFERENCES player_characters(id) ON DELETE SET NULL,
    slot3 INTEGER REFERENCES player_characters(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS pvp_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attacker_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    defender_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    winner_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self.is_sqlite = dsn.startswith("sqlite:///")
        self.pool: asyncpg.Pool | None = None
        self.sqlite_path: Path | None = None
        if self.is_sqlite:
            self.sqlite_path = Path(dsn.removeprefix("sqlite:///")).expanduser().resolve()

    async def connect(self) -> None:
        if self.is_sqlite:
            assert self.sqlite_path is not None
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            return
        self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    async def initialize(self) -> None:
        if self.is_sqlite:
            await self._sqlite_exec_script(SCHEMA_SQL_SQLITE)
            await self._sqlite_ensure_column("character_catalog", "card_number", "INTEGER NOT NULL DEFAULT 0")
            return
        await self.execute(SCHEMA_SQL_POSTGRES)
        await self.execute(
            "ALTER TABLE character_catalog ADD COLUMN IF NOT EXISTS card_number INTEGER NOT NULL DEFAULT 0"
        )

    async def execute(self, query: str, *args: Any) -> str:
        if self.is_sqlite:
            await self._sqlite_execute(query, args)
            return "OK"
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def executemany(self, statements: list[tuple[str, tuple[Any, ...]]]) -> None:
        if self.is_sqlite:
            async with aiosqlite.connect(self.sqlite_path) as conn:  # type: ignore[arg-type]
                conn.row_factory = aiosqlite.Row
                await conn.execute("PRAGMA foreign_keys = ON")
                await conn.execute("BEGIN")
                try:
                    for query, args in statements:
                        await conn.execute(self._convert_sqlite_query(query), args)
                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise
            return

        assert self.pool is not None
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for query, args in statements:
                    await conn.execute(query, *args)

    async def fetch(self, query: str, *args: Any) -> list[Any]:
        if self.is_sqlite:
            return await self._sqlite_fetch(query, args)
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> Any | None:
        if self.is_sqlite:
            return await self._sqlite_fetchrow(query, args)
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: Any) -> Any:
        if self.is_sqlite:
            row = await self._sqlite_fetchrow(query, args)
            if row is None:
                return None
            return next(iter(dict(row).values()))
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def ensure_stamina(self, user_id: int) -> None:
        settings = get_settings()
        record = await self.fetchrow(
            """
            SELECT id, stamina, max_stamina, last_stamina_at
            FROM players
            WHERE user_id = $1
            """,
            user_id,
        )
        if not record:
            return

        now = datetime.now(UTC)
        stamina = record["stamina"]
        max_stamina = record["max_stamina"]
        last_tick = self._parse_datetime(record["last_stamina_at"])
        if stamina >= max_stamina:
            if now - last_tick > timedelta(minutes=settings.stamina_regen_minutes):
                await self.execute(
                    "UPDATE players SET last_stamina_at = $2 WHERE id = $1",
                    record["id"],
                    self._serialize_datetime(now),
                )
            return

        elapsed_minutes = int((now - last_tick).total_seconds() // 60)
        regen_points = elapsed_minutes // settings.stamina_regen_minutes
        if regen_points <= 0:
            return

        new_stamina = min(max_stamina, stamina + regen_points)
        new_tick = last_tick + timedelta(minutes=regen_points * settings.stamina_regen_minutes)
        await self.execute(
            """
            UPDATE players
            SET stamina = $2, last_stamina_at = $3
            WHERE id = $1
            """,
            record["id"],
            new_stamina,
            self._serialize_datetime(new_tick),
        )

    async def _sqlite_exec_script(self, script: str) -> None:
        async with aiosqlite.connect(self.sqlite_path) as conn:  # type: ignore[arg-type]
            await conn.executescript(script)
            await conn.commit()

    async def _sqlite_ensure_column(self, table: str, column: str, definition: str) -> None:
        async with aiosqlite.connect(self.sqlite_path) as conn:  # type: ignore[arg-type]
            cursor = await conn.execute(f"PRAGMA table_info({table})")
            rows = await cursor.fetchall()
            if any(row[1] == column for row in rows):
                return
            await conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            await conn.commit()

    async def _sqlite_execute(self, query: str, args: tuple[Any, ...]) -> None:
        async with aiosqlite.connect(self.sqlite_path) as conn:  # type: ignore[arg-type]
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON")
            sql, ordered_args = self._prepare_sqlite_query(query, args)
            await conn.execute(sql, ordered_args)
            await conn.commit()

    async def _sqlite_fetch(self, query: str, args: tuple[Any, ...]) -> list[aiosqlite.Row]:
        async with aiosqlite.connect(self.sqlite_path) as conn:  # type: ignore[arg-type]
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON")
            sql, ordered_args = self._prepare_sqlite_query(query, args)
            cursor = await conn.execute(sql, ordered_args)
            if self._is_mutating_query(query):
                await conn.commit()
            return await cursor.fetchall()

    async def _sqlite_fetchrow(self, query: str, args: tuple[Any, ...]) -> aiosqlite.Row | None:
        async with aiosqlite.connect(self.sqlite_path) as conn:  # type: ignore[arg-type]
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON")
            sql, ordered_args = self._prepare_sqlite_query(query, args)
            cursor = await conn.execute(sql, ordered_args)
            row = await cursor.fetchone()
            if self._is_mutating_query(query):
                await conn.commit()
            return row

    def _prepare_sqlite_query(self, query: str, args: tuple[Any, ...]) -> tuple[str, tuple[Any, ...]]:
        indexes = [int(match.group(1)) for match in re.finditer(r"\$(\d+)", query)]
        converted = re.sub(r"\$(\d+)", "?", query)
        ordered_args = tuple(args[index - 1] for index in indexes)
        return converted, ordered_args

    def _is_mutating_query(self, query: str) -> bool:
        normalized = query.lstrip().upper()
        return normalized.startswith("INSERT") or normalized.startswith("UPDATE") or normalized.startswith("DELETE")

    def _serialize_datetime(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat()

    def _parse_datetime(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        parsed = datetime.fromisoformat(str(value).replace(" ", "T"))
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
