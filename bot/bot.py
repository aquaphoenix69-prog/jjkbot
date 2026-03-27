from __future__ import annotations

import logging

import discord
from discord.ext import commands

from bot.config import Settings, get_settings
from bot.db.database import Database
from bot.services.battle_service import BattleService
from bot.services.game_service import GameService

LOGGER = logging.getLogger(__name__)


class JJKBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix="y!",
            intents=intents,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True,
        )
        self.settings: Settings = get_settings()
        self.db = Database(self.settings.database_url)
        self.game = GameService(self.db)
        self.battles = BattleService(self.game)

    async def setup_hook(self) -> None:
        await self.db.connect()
        await self.db.initialize()
        await self.game.seed_characters()

        await self.load_extension("bot.commands.game")
        await self.load_extension("bot.commands.battle")
        if self.settings.dev_guild_id:
            guild = discord.Object(id=self.settings.dev_guild_id)
            synced = await self.tree.sync(guild=guild)
            LOGGER.info("Cleared or synced %s guild slash commands; prefix commands are active with y!", len(synced))
        else:
            synced = await self.tree.sync()
            LOGGER.info("Cleared or synced %s global slash commands; prefix commands are active with y!", len(synced))

    async def close(self) -> None:
        await super().close()
        await self.db.close()

    async def on_command_error(self, context: commands.Context, exception: commands.CommandError) -> None:
        if isinstance(exception, commands.CommandNotFound):
            content = context.message.content.strip()
            if content.lower().startswith("y!"):
                await context.send(
                    "That isn't a valid `y!` command. Use `y!help` to see categories, or `y!help <command>` for details."
                )
            return
        await super().on_command_error(context, exception)
