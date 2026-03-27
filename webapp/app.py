from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiohttp
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bot.config import Settings, get_settings
from bot.db.database import Database
from bot.services.game_service import GameService

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@dataclass(slots=True)
class DiscordIdentity:
    user_id: int
    username: str
    display_name: str
    avatar_url: str


class DiscordIdentityService:
    def __init__(self, token: str) -> None:
        self.token = token
        self._session: aiohttp.ClientSession | None = None
        self._cache: dict[int, tuple[datetime, DiscordIdentity]] = {}

    async def start(self) -> None:
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def fetch(self, user_id: int) -> DiscordIdentity:
        cached = self._cache.get(user_id)
        now = datetime.now(UTC)
        if cached and now - cached[0] < timedelta(minutes=30):
            return cached[1]

        if not self._session:
            raise RuntimeError("Identity session not initialized.")

        headers = {"Authorization": f"Bot {self.token}", "User-Agent": "YutafraudDashboard/1.0"}
        try:
            async with self._session.get(f"https://discord.com/api/v10/users/{user_id}", headers=headers) as response:
                if response.status == 200:
                    payload = await response.json()
                    identity = self._from_payload(payload)
                    self._cache[user_id] = (now, identity)
                    return identity
        except aiohttp.ClientError:
            pass

        fallback = DiscordIdentity(
            user_id=user_id,
            username=f"user_{user_id}",
            display_name=f"Sorcerer {user_id}",
            avatar_url=self._default_avatar_url(user_id),
        )
        self._cache[user_id] = (now, fallback)
        return fallback

    def _from_payload(self, payload: dict[str, Any]) -> DiscordIdentity:
        user_id = int(payload["id"])
        avatar = payload.get("avatar")
        if avatar:
            extension = "gif" if avatar.startswith("a_") else "png"
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.{extension}?size=256"
        else:
            avatar_url = self._default_avatar_url(user_id, payload.get("discriminator"))
        return DiscordIdentity(
            user_id=user_id,
            username=payload.get("username", f"user_{user_id}"),
            display_name=payload.get("global_name") or payload.get("username", f"Sorcerer {user_id}"),
            avatar_url=avatar_url,
        )

    def _default_avatar_url(self, user_id: int, discriminator: str | None = None) -> str:
        if discriminator and discriminator.isdigit() and discriminator != "0":
            index = int(discriminator) % 5
        else:
            index = (int(user_id) >> 22) % 6
        return f"https://cdn.discordapp.com/embed/avatars/{index}.png"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db = Database(settings.database_url)
    game = GameService(db)
    identities = DiscordIdentityService(settings.discord_token)

    await db.connect()
    await db.initialize()
    await game.seed_characters()
    await identities.start()

    app.state.settings = settings
    app.state.db = db
    app.state.game = game
    app.state.identities = identities
    try:
        yield
    finally:
        await identities.close()
        await db.close()


app = FastAPI(title="Yutafraud Dashboard", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def app_settings(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[return-value]


def app_game(request: Request) -> GameService:
    return request.app.state.game  # type: ignore[return-value]


def app_db(request: Request) -> Database:
    return request.app.state.db  # type: ignore[return-value]


def app_identities(request: Request) -> DiscordIdentityService:
    return request.app.state.identities  # type: ignore[return-value]


def build_game_settings(settings: Settings) -> list[dict[str, str]]:
    return [
        {"name": "Prefix", "value": "y!"},
        {"name": "Normal Summon", "value": "100 Coins"},
        {"name": "Rare Summon", "value": "2,000 Coins"},
        {"name": "Epic Summon", "value": "100,000 Coins"},
        {"name": "Legendary Summon", "value": "500,000 Coins"},
        {"name": "Starting Coins", "value": f"{settings.starting_coins:,}"},
        {"name": "Starting Crystals", "value": f"{settings.starting_crystals:,}"},
        {"name": "Stamina Regen", "value": f"1 every {settings.stamina_regen_minutes} minutes"},
    ]


async def build_leaderboards(request: Request, limit: int = 8) -> dict[str, dict[str, Any]]:
    game = app_game(request)
    identities = app_identities(request)
    boards: dict[str, dict[str, Any]] = {}
    for stat_key in game.LEADERBOARD_STATS:
        title, label, entries = await game.get_leaderboard(stat_key, limit=limit)
        identity_rows = await asyncio.gather(*(identities.fetch(user_id) for user_id, _ in entries))
        boards[stat_key] = {
            "title": title,
            "label": label,
            "entries": [
                {
                    "rank": index,
                    "value": value,
                    "identity": identity,
                }
                for index, ((_, value), identity) in enumerate(zip(entries, identity_rows), start=1)
            ],
        }
    return boards


async def build_profile_context(request: Request, user_id: int) -> dict[str, Any]:
    game = app_game(request)
    db = app_db(request)
    settings = app_settings(request)
    identities = app_identities(request)

    profile = await game.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")

    identity = await identities.fetch(user_id)
    team = await game.get_team(profile.player_id)
    owned = await game.get_owned_characters(profile.player_id)
    strongest = max(owned, key=lambda unit: unit.power, default=None)
    locked_count = sum(1 for unit in owned if unit.locked)
    awakened_count = sum(1 for unit in owned if unit.awakened)
    recent_battles = await db.fetch(
        """
        SELECT created_at, winner_id
        FROM pvp_history
        WHERE attacker_id = $1 OR defender_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        profile.player_id,
        6,
    )

    battle_feed = []
    for record in recent_battles:
        winner_profile = await game.get_profile_by_player_id(record["winner_id"])
        winner_identity = await identities.fetch(winner_profile.user_id)
        created_at = record["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace(" ", "T"))
        battle_feed.append({"winner": winner_identity.display_name, "created_at": created_at})

    return {
        "identity": identity,
        "profile": profile,
        "team": team,
        "owned": owned,
        "strongest": strongest,
        "locked_count": locked_count,
        "awakened_count": awakened_count,
        "battle_feed": battle_feed,
        "game_settings": build_game_settings(settings),
    }


def spotlight_member(boards: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    entries = boards.get("rank", {}).get("entries", [])
    return entries[0] if entries else None


@app.get("/")
async def home(request: Request):
    db = app_db(request)
    boards = await build_leaderboards(request)
    spotlight = spotlight_member(boards)
    player_count = await db.fetchval("SELECT COUNT(*) FROM players")
    collection_count = await db.fetchval("SELECT COUNT(*) FROM player_characters")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "boards": boards,
            "spotlight": spotlight,
            "player_count": int(player_count or 0),
            "collection_count": int(collection_count or 0),
            "game_settings": build_game_settings(app_settings(request)),
            "cat_gif": "https://media.giphy.com/media/ICOgUNjpvO0PC/giphy.gif",
        },
    )


@app.get("/lookup")
async def lookup_profile(user_id: int):
    return RedirectResponse(url=f"/profiles/{user_id}", status_code=303)


@app.get("/profiles/{user_id}")
async def profile_page(request: Request, user_id: int):
    boards = await build_leaderboards(request, limit=5)
    context = await build_profile_context(request, user_id)
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={"boards": boards, **context},
    )


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
