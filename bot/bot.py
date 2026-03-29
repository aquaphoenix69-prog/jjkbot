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
        self.default_prefix = "y!"
        super().__init__(
            command_prefix=self._get_prefix,
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
        try:
            if self.settings.dev_guild_id:
                guild = discord.Object(id=self.settings.dev_guild_id)
                synced = await self.tree.sync(guild=guild)
                LOGGER.info("Cleared or synced %s guild slash commands; prefix commands are active with y!", len(synced))
            else:
                synced = await self.tree.sync()
                LOGGER.info("Cleared or synced %s global slash commands; prefix commands are active with y!", len(synced))
        except discord.MissingApplicationID:
            LOGGER.warning("Skipping app command sync during startup because application_id is not available yet.")

    async def close(self) -> None:
        await super().close()
        await self.db.close()

    async def _get_prefix(self, bot: commands.Bot, message: discord.Message):
        prefix = self.default_prefix
        if message.guild and getattr(self.db, "pool", None) is not None or self.db.is_sqlite:
            try:
                stored = await self.game.get_guild_prefix(message.guild.id) if message.guild else None
                if stored:
                    prefix = stored
            except Exception:
                prefix = self.default_prefix
        return commands.when_mentioned_or(prefix)(bot, message)

    async def on_command_error(self, context: commands.Context, exception: commands.CommandError) -> None:
        if isinstance(exception, commands.CommandNotFound):
            content = context.message.content.strip()
            prefixes = await self.get_prefix(context.message)
            if isinstance(prefixes, str):
                prefixes = [prefixes]
            prefix_text = next((item for item in prefixes if not item.startswith("<@")), self.default_prefix)
            if any(content.lower().startswith(item.lower()) for item in prefixes if isinstance(item, str)):
                await context.send(
                    f"That isn't a valid command. Use `{prefix_text}help` to see categories, or `{prefix_text}help <command>` for details."
                )
            return
        await super().on_command_error(context, exception)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if self.user and message.guild and message.content.strip() in {f"<@{self.user.id}>", f"<@!{self.user.id}>"}:
            prefix = await self.game.get_guild_prefix(message.guild.id)
            await message.channel.send(f"My prefix here is `{prefix}`")
            return
        await self.process_commands(message)
