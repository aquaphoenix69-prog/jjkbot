from __future__ import annotations

import asyncio
import io

import discord
from discord.ext import commands

from bot.utils.battle_visuals import render_battle_snapshot
from bot.utils.embeds import battle_embed, battle_snapshot_embed


class BattleCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(
        aliases=["bt", "fight", "raid"],
        help="Fight a story mission or a boss raid.",
        extras={
            "category": "battle",
            "usage": "y!battle <story|boss> [-r <n|r|e|l>]",
            "examples": ["y!battle story", "y!battle boss", "y!battle boss -r legendary"],
            "details": "Story battles advance your progression and reward materials. Boss raids support difficulty from normal to legendary and give bigger rewards at higher difficulty.",
        },
    )
    @commands.cooldown(1, 6.0, commands.BucketType.user)
    async def battle(self, ctx: commands.Context, mode: str = "story", *options: str) -> None:
        profile = await self.bot.game.get_profile(ctx.author.id)
        if not profile:
            await ctx.send("Use `y!start` first.")
            return

        mode = mode.lower()
        if mode not in {"story", "boss"}:
            await ctx.send("Mode must be `story` or `boss`.")
            return

        try:
            if mode == "boss":
                difficulty = self._parse_boss_difficulty(list(options))
                log = await self.bot.battles.run_boss_raid(profile.player_id, difficulty=difficulty)
                title = f"Boss Raid Result [{difficulty.title()}]"
            else:
                log = await self.bot.battles.run_story_battle(profile.player_id)
                title = "Story Battle Result"
        except ValueError as exc:
            await ctx.send(str(exc))
            return
        await self._play_battle(ctx, title, log)

    @commands.command(
        aliases=["duel", "challenge"],
        help="Challenge another player in ranked PvP.",
        extras={
            "category": "battle",
            "usage": "y!pvp <@opponent>",
            "examples": ["y!pvp @YutaMain"],
            "details": "Consumes stamina and runs a ranked battle between your current team and the tagged opponent's team. Rank points are adjusted after the duel.",
        },
    )
    @commands.cooldown(1, 10.0, commands.BucketType.user)
    async def pvp(self, ctx: commands.Context, opponent: discord.Member) -> None:
        if opponent.bot:
            await ctx.send("You can only challenge human sorcerers.")
            return
        if opponent.id == ctx.author.id:
            await ctx.send("Mirror matches are not allowed.")
            return

        attacker = await self.bot.game.get_profile(ctx.author.id)
        defender = await self.bot.game.get_profile(opponent.id)
        if not attacker or not defender:
            await ctx.send("Both players must use `y!start` first.")
            return

        try:
            log = await self.bot.battles.run_pvp(attacker.player_id, defender.player_id)
        except ValueError as exc:
            await ctx.send(str(exc))
            return
        await self._play_battle(ctx, "Ranked PvP Result", log)

    async def _play_battle(self, ctx: commands.Context, title: str, log) -> None:
        if not log.snapshots:
            await ctx.send(embed=battle_embed(title, log))
            return

        message = await ctx.send("Entering battle...")
        first_snapshot = log.snapshots[0]
        image_bytes, image_name = await render_battle_snapshot(first_snapshot)
        await message.edit(
            content=None,
            embed=battle_snapshot_embed(title, first_snapshot),
            attachments=[discord.File(io.BytesIO(image_bytes), filename=image_name)],
        )

        max_updates = min(len(log.snapshots), 12)
        selected = log.snapshots[:max_updates]
        for snapshot in selected[1:]:
            await asyncio.sleep(0.65)
            image_bytes, image_name = await render_battle_snapshot(snapshot)
            await message.edit(
                embed=battle_snapshot_embed(title, snapshot),
                attachments=[discord.File(io.BytesIO(image_bytes), filename=image_name)],
            )

        await asyncio.sleep(0.45)
        await message.edit(content=None, embed=battle_embed(title, log), attachments=[])

    def _parse_boss_difficulty(self, options: list[str]) -> str:
        if not options:
            return "normal"
        if len(options) != 2 or options[0].lower().strip() != "-r":
            raise ValueError("Use `y!battle boss -r <n|r|e|l>`.")
        aliases = {
            "n": "normal",
            "normal": "normal",
            "r": "rare",
            "rare": "rare",
            "e": "epic",
            "epic": "epic",
            "l": "legendary",
            "legendary": "legendary",
        }
        difficulty = aliases.get(options[1].lower().strip())
        if not difficulty:
            raise ValueError("Boss difficulty must be `normal`, `rare`, `epic`, or `legendary`.")
        return difficulty

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Your cursed technique needs a moment. Retry in {error.retry_after:.1f}s.")
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing argument: `{error.param.name}`. Try `y!help {ctx.command}`.")
            return
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid argument. Try `y!help {ctx.command}`.")
            return
        raise error


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BattleCog(bot))
