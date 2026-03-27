from __future__ import annotations

import discord
from discord.ext import commands

from bot.utils.embeds import battle_embed


class BattleCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(
        help="Fight a story mission or a boss raid.",
        extras={
            "category": "battle",
            "usage": "y!battle <story|boss>",
            "examples": ["y!battle story", "y!battle boss"],
            "details": "Story battles advance your progression and reward materials. Boss raids are harder and cost more stamina, but their rewards are bigger.",
        },
    )
    @commands.cooldown(1, 6.0, commands.BucketType.user)
    async def battle(self, ctx: commands.Context, mode: str = "story") -> None:
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
                log = await self.bot.battles.run_boss_raid(profile.player_id)
                title = "Boss Raid Result"
            else:
                log = await self.bot.battles.run_story_battle(profile.player_id)
                title = "Story Battle Result"
        except ValueError as exc:
            await ctx.send(str(exc))
            return

        await ctx.send(embed=battle_embed(title, log))

    @commands.command(
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
        await ctx.send(embed=battle_embed("Ranked PvP Result", log))

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
