from __future__ import annotations

import discord
from discord.ext import commands

from bot.data.characters import SUMMON_TYPES
from bot.utils.embeds import (
    daily_embed,
    inventory_page_embed,
    leaderboard_embed,
    profile_embed,
    summon_embed,
    team_embed,
    upgrade_embed,
)


class InventoryView(discord.ui.View):
    def __init__(self, owner_id: int, embeds: list[discord.Embed]) -> None:
        super().__init__(timeout=120)
        self.owner_id = owner_id
        self.embeds = embeds
        self.index = 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the command author can use these buttons.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = (self.index - 1) % len(self.embeds)
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = (self.index + 1) % len(self.embeds)
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)


class SummonResultView(discord.ui.View):
    def __init__(self, owner_id: int, embeds: list[discord.Embed]) -> None:
        super().__init__(timeout=120)
        self.owner_id = owner_id
        self.embeds = embeds
        self.index = 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the summoner can use these buttons.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Previous Result", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = (self.index - 1) % len(self.embeds)
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

    @discord.ui.button(label="Next Result", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = (self.index + 1) % len(self.embeds)
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)


class GameCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.help_categories = {
            "profile": {
                "description": "Account setup, progression overview, streaks, and ranking.",
                "commands": ["start", "profile", "daily", "leaderboard", "ping"],
            },
            "game": {
                "description": "Collection management, summoning, teams, and upgrades.",
                "commands": ["summon", "inventory", "team", "lock", "upgrade"],
            },
            "battle": {
                "description": "PvE fights, boss raids, and PvP challenges.",
                "commands": ["battle", "pvp"],
            },
            "help": {
                "description": "Command discovery and detailed usage information.",
                "commands": ["help"],
            },
        }

    @commands.command(
        name="help",
        help="Show command categories, category-specific help, or full help for one command.",
        extras={
            "category": "help",
            "usage": "y!help [category|command]",
            "examples": ["y!help", "y!help game", "y!help summon"],
            "details": "Without arguments it shows categories. With a category it lists every command in that category. With a command name it shows full usage, aliases, and examples.",
        },
    )
    async def help_prefix(self, ctx: commands.Context, *, topic: str | None = None) -> None:
        if topic is None:
            embed = discord.Embed(
                title="JJK Battle Nexus Help",
                color=discord.Color.red(),
                description="Use `y!help <category>` or `y!help <command>` for more detail.",
            )
            for name, data in self.help_categories.items():
                embed.add_field(
                    name=name.title(),
                    value=data["description"],
                    inline=False,
                )
            await ctx.send(embed=embed)
            return

        normalized = topic.lower().strip()
        if normalized in self.help_categories:
            data = self.help_categories[normalized]
            embed = discord.Embed(
                title=f"{normalized.title()} Commands",
                color=discord.Color.dark_red(),
                description=data["description"],
            )
            for command_name in data["commands"]:
                command = self.bot.get_command(command_name)
                if command:
                    usage = command.extras.get("usage", f"y!{command.qualified_name}")
                    embed.add_field(
                        name=f"`{usage}`",
                        value=command.help or "No description available.",
                        inline=False,
                    )
            await ctx.send(embed=embed)
            return

        command = self.bot.get_command(normalized)
        if command:
            embed = discord.Embed(
                title=f"Help: y!{command.qualified_name}",
                color=discord.Color.orange(),
                description=command.help or "No description available.",
            )
            embed.add_field(name="Category", value=command.extras.get("category", "general").title(), inline=True)
            embed.add_field(name="Usage", value=f"`{command.extras.get('usage', f'y!{command.qualified_name}')}`", inline=False)
            aliases = ", ".join(f"`y!{alias}`" for alias in command.aliases) if command.aliases else "None"
            embed.add_field(name="Aliases", value=aliases, inline=False)
            embed.add_field(name="Details", value=command.extras.get("details", "No extra details available."), inline=False)
            examples = command.extras.get("examples", [])
            if examples:
                embed.add_field(name="Examples", value="\n".join(f"`{example}`" for example in examples), inline=False)
            await ctx.send(embed=embed)
            return

        await ctx.send("No help entry found for that category or command.")

    @commands.command(
        help="Check whether the bot is alive and how fast it is responding.",
        extras={
            "category": "profile",
            "usage": "y!ping",
            "examples": ["y!ping"],
            "details": "Replies with Pong and shows the current websocket latency in milliseconds so you can verify the bot is online.",
        },
    )
    async def ping(self, ctx: commands.Context) -> None:
        latency_ms = round(self.bot.latency * 1000)
        await ctx.send(f"Pong! `{latency_ms}ms`")

    @commands.command(
        help="Create your JJK profile and receive your starter unit.",
        extras={
            "category": "profile",
            "usage": "y!start",
            "examples": ["y!start"],
            "details": "Creates your profile, gives starting currencies and materials, and adds Yuji Itadori as your starter character.",
        },
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def start(self, ctx: commands.Context) -> None:
        profile = await self.bot.game.create_profile(ctx.author.id)
        await ctx.send(embed=profile_embed(ctx.author, profile))

    @commands.command(
        help="View your resources, stamina, materials, and rank.",
        extras={
            "category": "profile",
            "usage": "y!profile",
            "examples": ["y!profile"],
            "details": "Shows your account overview including coins, crystals, stamina, streak, rank points, and upgrade materials.",
        },
    )
    @commands.cooldown(1, 4.0, commands.BucketType.user)
    async def profile(self, ctx: commands.Context) -> None:
        profile = await self.bot.game.get_profile(ctx.author.id)
        if not profile:
            await ctx.send("Use `y!start` first.")
            return
        await ctx.send(embed=profile_embed(ctx.author, profile))

    @commands.command(
        help="Summon characters with normal, rare, epic, or legendary rituals.",
        extras={
            "category": "game",
            "usage": "y!summon <normal|rare|epic|legendary> [1|n-x]",
            "examples": ["y!summon normal", "y!summon rare n-3", "y!summon legendary n-10"],
            "details": "Summon cost is paid in coins. Costs are normal 100, rare 2000, epic 100000, legendary 500000. Use `n-x` to multi-summon x times.",
        },
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def summon(
        self,
        ctx: commands.Context,
        summon_type: str = "normal",
        amount_token: str = "1",
    ) -> None:
        profile = await self.bot.game.get_profile(ctx.author.id)
        if not profile:
            await ctx.send("Use `y!start` first.")
            return
        summon_type = summon_type.lower()
        if summon_type not in SUMMON_TYPES:
            await ctx.send("Unknown summon type. Use `normal`, `rare`, `epic`, or `legendary`.")
            return
        amount = self._parse_summon_amount(amount_token)
        if amount is None or amount < 1:
            await ctx.send("Amount must be `1` or in `n-x` format like `n-10`.")
            return

        try:
            recruits, updated = await self.bot.game.summon(
                profile.player_id,
                summon_type,
                amount,
            )
        except ValueError as exc:
            await ctx.send(str(exc))
            return
        embeds = [
            summon_embed(ctx.author, summon_type, recruit, updated, amount)
            for recruit in recruits
        ]
        if not embeds:
            await ctx.send("No characters were summoned.")
            return
        await ctx.send(embed=embeds[0], view=SummonResultView(ctx.author.id, embeds))

    def _parse_summon_amount(self, raw: str) -> int | None:
        normalized = raw.lower().strip()
        if normalized.isdigit():
            return int(normalized)
        if normalized.startswith("n-"):
            tail = normalized[2:]
            if tail.isdigit():
                return int(tail)
        return None

    @commands.command(
        help="Browse every character you own.",
        extras={
            "category": "game",
            "usage": "y!inventory",
            "examples": ["y!inventory"],
            "details": "Shows your collection with instance ids, levels, grades, and skill levels. Use the buttons to switch pages.",
        },
    )
    @commands.cooldown(1, 4.0, commands.BucketType.user)
    async def inventory(self, ctx: commands.Context) -> None:
        profile = await self.bot.game.get_profile(ctx.author.id)
        if not profile:
            await ctx.send("Use `y!start` first.")
            return
        characters = await self.bot.game.get_owned_characters(profile.player_id)
        embeds = [
            inventory_page_embed(ctx.author, characters, page, 8)
            for page in range(max(1, (len(characters) + 7) // 8))
        ]
        await ctx.send(embed=embeds[0], view=InventoryView(ctx.author.id, embeds))

    @commands.command(
        help="Set your active three-character battle team.",
        extras={
            "category": "game",
            "usage": "y!team <slot1> [slot2] [slot3]",
            "examples": ["y!team 1 2 3", "y!team 7 9"],
            "details": "Pass your character instance ids from `y!inventory`. Duplicate ids are not allowed.",
        },
    )
    @commands.cooldown(1, 4.0, commands.BucketType.user)
    async def team(self, ctx: commands.Context, slot1: int, slot2: int | None = None, slot3: int | None = None) -> None:
        profile = await self.bot.game.get_profile(ctx.author.id)
        if not profile:
            await ctx.send("Use `y!start` first.")
            return

        raw_ids = [slot1, slot2, slot3]
        unique_ids = [value for value in raw_ids if value is not None]
        if len(set(unique_ids)) != len(unique_ids):
            await ctx.send("Each team slot must use a different character.")
            return

        for instance_id in unique_ids:
            if not await self.bot.game.get_character_instance(profile.player_id, instance_id):
                await ctx.send(f"Character `#{instance_id}` is not in your inventory.")
                return

        await self.bot.game.set_team(profile.player_id, raw_ids)
        team = await self.bot.game.get_team(profile.player_id)
        await ctx.send(embed=team_embed(ctx.author, team))

    @commands.command(
        help="Lock or unlock a character in your collection.",
        extras={
            "category": "game",
            "usage": "y!lock <instance_id>",
            "examples": ["y!lock 4"],
            "details": "Locked characters are marked in your inventory and can be kept safe for future systems like auto-merge or auto-sacrifice.",
        },
    )
    @commands.cooldown(1, 2.0, commands.BucketType.user)
    async def lock(self, ctx: commands.Context, instance_id: int) -> None:
        profile = await self.bot.game.get_profile(ctx.author.id)
        if not profile:
            await ctx.send("Use `y!start` first.")
            return
        character = await self.bot.game.get_character_instance(profile.player_id, instance_id)
        if not character:
            await ctx.send("Character not found.")
            return
        state = await self.bot.game.toggle_lock(profile.player_id, instance_id)
        await ctx.send(f"`#{instance_id}` is now {'locked' if state else 'unlocked'}.")

    @commands.command(
        help="Claim your daily rewards and streak bonus.",
        extras={
            "category": "profile",
            "usage": "y!daily",
            "examples": ["y!daily"],
            "details": "Claims coins, crystals, stamina, and materials once per day. Consecutive claims increase your streak reward.",
        },
    )
    @commands.cooldown(1, 4.0, commands.BucketType.user)
    async def daily(self, ctx: commands.Context) -> None:
        profile = await self.bot.game.get_profile(ctx.author.id)
        if not profile:
            await ctx.send("Use `y!start` first.")
            return
        try:
            updated, rewards = await self.bot.game.claim_daily(profile.player_id)
        except ValueError as exc:
            await ctx.send(str(exc))
            return
        await ctx.send(embed=daily_embed(updated, rewards))

    @commands.command(
        help="Upgrade a character's level, skill, grade, or awaken them.",
        extras={
            "category": "game",
            "usage": "y!upgrade <instance_id> <level|skill|grade|awaken>",
            "examples": ["y!upgrade 3 level", "y!upgrade 8 skill", "y!upgrade 12 awaken"],
            "details": "Use materials from battles and dailies to strengthen units. Awakening is only for Special Grade units that meet the requirements.",
        },
    )
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def upgrade(self, ctx: commands.Context, instance_id: int, action: str) -> None:
        profile = await self.bot.game.get_profile(ctx.author.id)
        if not profile:
            await ctx.send("Use `y!start` first.")
            return
        action = action.lower()
        if action not in {"level", "skill", "grade", "awaken"}:
            await ctx.send("Action must be `level`, `skill`, `grade`, or `awaken`.")
            return
        try:
            character = await self.bot.game.upgrade_character(profile.player_id, instance_id, action)
        except ValueError as exc:
            await ctx.send(str(exc))
            return
        await ctx.send(embed=upgrade_embed(character, action))

    @commands.command(
        help="Show the top ranked sorcerers.",
        extras={
            "category": "profile",
            "usage": "y!leaderboard",
            "examples": ["y!leaderboard"],
            "details": "Displays the current rank point leaderboard using stored PvP progression.",
        },
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def leaderboard(self, ctx: commands.Context) -> None:
        entries = await self.bot.game.get_leaderboard()
        resolved: list[tuple[str, int]] = []
        for user_id, points in entries:
            user = self.bot.get_user(user_id)
            if user is None:
                try:
                    user = await self.bot.fetch_user(user_id)
                except discord.HTTPException:
                    user = None
            resolved.append((user.display_name if user else f"User {user_id}", points))
        await ctx.send(embed=leaderboard_embed(resolved))

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Slow down a bit. Try again in {error.retry_after:.1f}s.")
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing argument: `{error.param.name}`. Try `y!help {ctx.command}`.")
            return
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid argument. Try `y!help {ctx.command}`.")
            return
        raise error


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GameCog(bot))
