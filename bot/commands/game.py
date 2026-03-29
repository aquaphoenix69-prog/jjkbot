from __future__ import annotations

import io

import aiohttp
import discord
from discord.ext import commands

from bot.data.characters import SUMMON_TYPES
from bot.utils.embeds import (
    card_info_embed,
    character_catalog_embed,
    daily_embed,
    enhancement_embed,
    evolution_embed,
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
    def __init__(
        self,
        owner_id: int,
        entries: list[tuple[discord.Embed, bytes | None, str | None]],
    ) -> None:
        super().__init__(timeout=120)
        self.owner_id = owner_id
        self.entries = entries
        self.index = 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the summoner can use these buttons.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Previous Result", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = (self.index - 1) % len(self.entries)
        await self._edit(interaction)

    @discord.ui.button(label="Next Result", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = (self.index + 1) % len(self.entries)
        await self._edit(interaction)

    async def _edit(self, interaction: discord.Interaction) -> None:
        embed, image_bytes, image_name = self.entries[self.index]
        attachments = []
        if image_bytes and image_name:
            attachments = [discord.File(io.BytesIO(image_bytes), filename=image_name)]
        await interaction.response.edit_message(embed=embed, attachments=attachments, view=self)


class EnhancementConfirmView(discord.ui.View):
    def __init__(
        self,
        owner_id: int,
        *,
        inventory_number: int,
        target_instance_id: int,
        fodder_rarity: str,
    ) -> None:
        super().__init__(timeout=60)
        self.owner_id = owner_id
        self.inventory_number = inventory_number
        self.target_instance_id = target_instance_id
        self.fodder_rarity = fodder_rarity
        self.confirmed = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the command author can confirm this enhancement.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm Enhance", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.confirmed = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.confirmed = False
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="Enhancement cancelled.", embed=None, view=self)
        self.stop()


class GameCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.admin_usernames = {"__gloom", "_nez_24", "frustated_fungus"}
        self.help_categories = {
            "profile": {
                "description": "Account setup, progression overview, streaks, and ranking.",
                "commands": ["start", "profile", "daily", "leaderboard", "ping"],
            },
            "game": {
                "description": "Collection management, summoning, teams, and upgrades.",
                "commands": ["summon", "inventory", "info", "cinfo", "team", "lock", "enh", "evo", "upgrade"],
            },
            "admin": {
                "description": "Owner-only economy and inventory controls.",
                "commands": ["admincoins", "admincrystals", "adminmaterials", "admincard", "adminreset"],
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
        aliases=["h", "commands", "cmds"],
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
        aliases=["p"],
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
        aliases=["begin", "register"],
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
        aliases=["pf", "me", "stats"],
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
        aliases=["sum", "pull", "roll"],
        help="Summon characters with normal, rare, epic, or legendary rituals.",
        extras={
            "category": "game",
            "usage": "y!summon <normal|rare|epic|legendary> [1|n-x|all]",
            "examples": ["y!summon normal", "y!summon rare n-3", "y!summon legendary n-10", "y!summon epic all"],
            "details": "Summon cost is paid in coins. Costs are normal 100, rare 2000, epic 100000, legendary 500000. Use `n-x` to multi-summon x times, or `all` to spend all possible coins on that summon type.",
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
        amount = self._parse_summon_amount(amount_token, profile.coins, summon_type)
        if amount is None or amount < 1:
            await ctx.send("Amount must be `1`, `all`, or in `n-x` format like `n-10`.")
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
        entries = [
            await self._build_summon_entry(ctx.author, summon_type, recruit, updated, amount)
            for recruit in recruits
        ]
        if not entries:
            await ctx.send("No characters were summoned.")
            return
        first_embed, first_bytes, first_name = entries[0]
        first_file = None
        if first_bytes and first_name:
            first_file = discord.File(io.BytesIO(first_bytes), filename=first_name)
        await ctx.send(
            embed=first_embed,
            file=first_file,
            view=SummonResultView(ctx.author.id, entries),
        )

    def _parse_summon_amount(self, raw: str, available_coins: int, summon_type: str) -> int | None:
        normalized = raw.lower().strip()
        if normalized == "all":
            cost = SUMMON_TYPES[summon_type]["cost"]
            return available_coins // cost
        if normalized.isdigit():
            return int(normalized)
        if normalized.startswith("n-"):
            tail = normalized[2:]
            if tail.isdigit():
                return int(tail)
        return None

    def _parse_inventory_options(self, options: list[str]) -> tuple[str, str | None, bool]:
        sort_key = "default"
        rarity_filter: str | None = None
        ascending = False
        index = 0
        sort_aliases = {
            "-hp": "hp",
            "-atk": "attack",
            "-attack": "attack",
            "-def": "defense",
            "-defense": "defense",
            "-spd": "speed",
            "-speed": "speed",
            "-energy": "energy",
            "-pow": "power",
            "-power": "power",
            "-lvl": "level",
            "-level": "level",
            "-enh": "enhancement",
            "-enhancement": "enhancement",
            "-evo": "evolution",
            "-evolution": "evolution",
            "-id": "id",
            "-card": "card",
        }
        rarity_aliases = {
            "n": "normal",
            "normal": "normal",
            "r": "rare",
            "rare": "rare",
            "e": "epic",
            "epic": "epic",
            "l": "legendary",
            "legendary": "legendary",
        }

        while index < len(options):
            option = options[index].lower().strip()
            if option == "-asc":
                ascending = True
            elif option == "-r":
                next_token = options[index + 1].lower().strip() if index + 1 < len(options) else None
                if next_token in rarity_aliases:
                    rarity_filter = rarity_aliases[next_token]
                    index += 1
                else:
                    sort_key = "rarity"
            elif option in sort_aliases:
                sort_key = sort_aliases[option]
            else:
                raise ValueError(
                    "Unknown inventory option. Use `-r [rarity]`, `-hp`, `-atk`, `-def`, `-spd`, `-energy`, `-power`, `-lvl`, `-enh`, `-evo`, `-id`, `-card`, or `-asc`."
                )
            index += 1

        return sort_key, rarity_filter, ascending

    def _parse_enhancement_rarity(self, options: list[str]) -> str:
        if len(options) != 2 or options[0].lower().strip() != "-r":
            raise ValueError("Use `y!enh <inventory_number> -r <n|r|e|l>`.")
        rarity_aliases = {
            "n": "normal",
            "normal": "normal",
            "r": "rare",
            "rare": "rare",
            "e": "epic",
            "epic": "epic",
            "l": "legendary",
            "legendary": "legendary",
        }
        rarity = rarity_aliases.get(options[1].lower().strip())
        if not rarity:
            raise ValueError("Rarity must be `n`, `r`, `e`, `l`, or the full rarity name.")
        return rarity

    async def _build_summon_entry(
        self,
        user: discord.abc.User,
        summon_type: str,
        recruit,
        profile,
        amount: int,
    ) -> tuple[discord.Embed, bytes | None, str | None]:
        image_bytes, image_name = await self._download_character_image(recruit.definition)
        embed = summon_embed(
            user,
            summon_type,
            recruit,
            profile,
            amount,
            image_name=image_name if image_bytes else None,
        )
        return embed, image_bytes, image_name if image_bytes else None

    async def _download_character_image(
        self, definition
    ) -> tuple[bytes | None, str | None]:
        if not definition.image_url:
            return None, None
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            }
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(definition.image_url, allow_redirects=True) as response:
                    if response.status != 200:
                        return None, None
                    data = await response.read()
            safe_name = f"{definition.key}.png"
            return data, safe_name
        except Exception:
            return None, None

    def _is_admin(self, user: discord.abc.User) -> bool:
        return user.name.lower() in self.admin_usernames

    async def _require_admin(self, ctx: commands.Context) -> bool:
        if self._is_admin(ctx.author):
            return True
        await ctx.send("You are not allowed to use admin commands.")
        return False

    async def _get_or_create_target_profile(self, member: discord.Member):
        profile = await self.bot.game.get_profile(member.id)
        if profile:
            return profile
        return await self.bot.game.create_profile(member.id)

    @commands.command(
        aliases=["inv", "bag", "cards"],
        help="Browse every character you own.",
        extras={
            "category": "game",
            "usage": "y!inventory [-r [rarity]] [-hp|-atk|-def|-spd|-energy|-power|-lvl|-enh|-evo|-id|-card] [-asc]",
            "examples": ["y!inventory", "y!inv -r", "y!inv -r legendary", "y!inv -atk", "y!inv -power -asc"],
            "details": "Use `-r` alone to sort by rarity or `-r legendary` to filter to one rarity. Stat flags sort by that stat. `-asc` flips the order.",
        },
    )
    @commands.cooldown(1, 4.0, commands.BucketType.user)
    async def inventory(self, ctx: commands.Context, *options: str) -> None:
        profile = await self.bot.game.get_profile(ctx.author.id)
        if not profile:
            await ctx.send("Use `y!start` first.")
            return
        try:
            sort_key, rarity_filter, ascending = self._parse_inventory_options(list(options))
        except ValueError as exc:
            await ctx.send(str(exc))
            return
        characters = await self.bot.game.get_owned_characters(
            profile.player_id,
            sort_key=sort_key,
            rarity_filter=rarity_filter,
            ascending=ascending,
        )
        embeds = [
            inventory_page_embed(
                ctx.author,
                characters,
                page,
                8,
                sort_label=self.bot.game.INVENTORY_SORT_LABELS.get(sort_key, "Default"),
                rarity_filter=rarity_filter,
            )
            for page in range(max(1, (len(characters) + 7) // 8))
        ]
        await ctx.send(embed=embeds[0], view=InventoryView(ctx.author.id, embeds))

    @commands.command(
        aliases=["cardinfo", "invinfo"],
        help="Show the full details for one owned card using its inventory number.",
        extras={
            "category": "game",
            "usage": "y!info <inventory_number>",
            "examples": ["y!info 1", "y!info 12"],
            "details": "Uses the numbered order shown in `y!inventory` and displays the chosen owned card with stats, progression, skills, passive, and art.",
        },
    )
    @commands.cooldown(1, 2.0, commands.BucketType.user)
    async def info(self, ctx: commands.Context, inventory_number: int) -> None:
        profile = await self.bot.game.get_profile(ctx.author.id)
        if not profile:
            await ctx.send("Use `y!start` first.")
            return
        character = await self.bot.game.get_inventory_entry_by_position(profile.player_id, inventory_number)
        if not character:
            await ctx.send("That inventory number does not exist.")
            return
        await ctx.send(embed=card_info_embed(character, inventory_number))

    @commands.command(
        aliases=["charinfo", "dex", "ci"],
        help="Search the card catalog by name and view a character's base info.",
        extras={
            "category": "game",
            "usage": "y!cinfo <character name>",
            "examples": ["y!cinfo gojo", "y!cinfo yuta okkotsu"],
            "details": "Searches the catalog by character name, title, or key and shows the base card data, stats, passive, skills, and image.",
        },
    )
    @commands.cooldown(1, 2.0, commands.BucketType.user)
    async def cinfo(self, ctx: commands.Context, *, query: str) -> None:
        character = self.bot.game.find_character_definition(query)
        if not character:
            await ctx.send("No character matched that search.")
            return
        await ctx.send(embed=character_catalog_embed(character))

    @commands.command(
        name="enh",
        aliases=["enhlvl"],
        help="Feed unlocked cards of one rarity into a target card for enhancement levels.",
        extras={
            "category": "game",
            "usage": "y!enh <inventory_number> -r <n|r|e|l>",
            "examples": ["y!enh 1 -r r", "y!enh 3 -r l"],
            "details": "Uses the numbered position from `y!inventory`. It consumes every unlocked card of the chosen rarity except the target until that unit reaches its enhancement cap, but asks for confirmation first.",
        },
    )
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def enh(self, ctx: commands.Context, inventory_number: int, *options: str) -> None:
        profile = await self.bot.game.get_profile(ctx.author.id)
        if not profile:
            await ctx.send("Use `y!start` first.")
            return
        try:
            fodder_rarity = self._parse_enhancement_rarity(list(options))
            target = await self.bot.game.get_inventory_entry_by_position(profile.player_id, inventory_number)
            if not target:
                await ctx.send("That inventory number does not exist.")
                return
            preview_count, preview_levels = await self.bot.game.preview_enhancement(
                profile.player_id,
                target.instance_id,
                fodder_rarity,
            )
        except ValueError as exc:
            await ctx.send(str(exc))
            return
        confirm_view = EnhancementConfirmView(
            ctx.author.id,
            inventory_number=inventory_number,
            target_instance_id=target.instance_id,
            fodder_rarity=fodder_rarity,
        )
        preview_embed = enhancement_embed(
            target,
            preview_count,
            preview_levels,
            fodder_rarity,
            pending=True,
            inventory_number=inventory_number,
        )
        message = await ctx.send(embed=preview_embed, view=confirm_view)
        await confirm_view.wait()
        if not confirm_view.confirmed:
            if confirm_view.is_finished():
                return
            await message.edit(content="Enhancement timed out.", embed=None, view=None)
            return

        await message.edit(embed=enhancement_embed(target, preview_count, preview_levels, fodder_rarity, in_progress=True, inventory_number=inventory_number), view=None)
        try:
            character, consumed_count, levels_gained = await self.bot.game.enhance_character(
                profile.player_id,
                target.instance_id,
                fodder_rarity,
            )
        except ValueError as exc:
            await message.edit(content=str(exc), embed=None, view=None)
            return
        await message.edit(embed=enhancement_embed(character, consumed_count, levels_gained, fodder_rarity, inventory_number=inventory_number), content=None, view=None)

    @commands.command(
        aliases=["evolve"],
        help="Evolve a unit by consuming two unlocked duplicate copies at the same evo stage.",
        extras={
            "category": "game",
            "usage": "y!evo <instance_id>",
            "examples": ["y!evo 14"],
            "details": "Consumes two unlocked duplicates of the same character at the same current evo stage. Evolution caps at evo 3.",
        },
    )
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def evo(self, ctx: commands.Context, instance_id: int) -> None:
        profile = await self.bot.game.get_profile(ctx.author.id)
        if not profile:
            await ctx.send("Use `y!start` first.")
            return
        try:
            character, consumed_ids = await self.bot.game.evolve_character(profile.player_id, instance_id)
        except ValueError as exc:
            await ctx.send(str(exc))
            return
        await ctx.send(embed=evolution_embed(character, consumed_ids))

    @commands.command(
        aliases=["tm", "squad", "lineup"],
        help="Set your active three-character battle team.",
        extras={
            "category": "game",
            "usage": "y!team [slot1] [slot2] [slot3]",
            "examples": ["y!team", "y!team 1 2 3", "y!team 7 9"],
            "details": "With no ids it shows your current team. To update the lineup, pass your inventory instance ids from `y!inventory`. Duplicate ids are not allowed.",
        },
    )
    @commands.cooldown(1, 4.0, commands.BucketType.user)
    async def team(self, ctx: commands.Context, slot1: int | None = None, slot2: int | None = None, slot3: int | None = None) -> None:
        profile = await self.bot.game.get_profile(ctx.author.id)
        if not profile:
            await ctx.send("Use `y!start` first.")
            return

        if slot1 is None and slot2 is None and slot3 is None:
            current_team = await self.bot.game.get_team(profile.player_id)
            await ctx.send(embed=team_embed(ctx.author, current_team))
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
        aliases=["lk", "fav", "favorite"],
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
        aliases=["claim", "dailyreward"],
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
        aliases=["up", "enhance"],
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
        aliases=["lb", "top", "leader"],
        help="Show leaderboard categories like coins, crystals, rank, streak, story, or collection.",
        extras={
            "category": "profile",
            "usage": "y!leaderboard [rank|coins|crystals|streak|story|collection]",
            "examples": ["y!leaderboard", "y!leaderboard coins", "y!leaderboard collection"],
            "details": "Displays a leaderboard for the requested stat. Available boards are rank points, coins, crystals, daily streak, story progress, and collection size.",
        },
    )
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def leaderboard(self, ctx: commands.Context, stat: str = "rank") -> None:
        try:
            stat_title, stat_label, entries = await self.bot.game.get_leaderboard(stat)
        except ValueError:
            choices = ", ".join(self.bot.game.LEADERBOARD_STATS.keys())
            await ctx.send(f"Unknown leaderboard category. Use one of: `{choices}`")
            return
        resolved: list[tuple[str, int]] = []
        for user_id, value in entries:
            user = self.bot.get_user(user_id)
            if user is None:
                try:
                    user = await self.bot.fetch_user(user_id)
                except discord.HTTPException:
                    user = None
            resolved.append((user.display_name if user else f"User {user_id}", value))
        await ctx.send(
            embed=leaderboard_embed(
                stat_title,
                stat_label,
                resolved,
                list(self.bot.game.LEADERBOARD_STATS.keys()),
            )
        )

    @commands.command(
        aliases=["addcoins"],
        help="Admin only: add coins to your profile or another player's profile.",
        extras={
            "category": "admin",
            "usage": "y!admincoins <@user> <amount>",
            "examples": ["y!admincoins @digipompu 500000", "y!admincoins @friend 99999999"],
            "details": "Adds any amount of coins to the target player's profile. Creates the profile automatically if needed.",
        },
    )
    async def admincoins(self, ctx: commands.Context, target: discord.Member, amount: int) -> None:
        if not await self._require_admin(ctx):
            return
        profile = await self._get_or_create_target_profile(target)
        updated = await self.bot.game.admin_grant_resources(profile.player_id, coins=amount)
        await ctx.send(f"Gave {amount:,} coins to {target.display_name}. New total: {updated.coins:,}.")

    @commands.command(
        aliases=["addcrystals"],
        help="Admin only: add crystals to a player.",
        extras={
            "category": "admin",
            "usage": "y!admincrystals <@user> <amount>",
            "examples": ["y!admincrystals @digipompu 5000"],
            "details": "Adds any amount of crystals to the target player's profile.",
        },
    )
    async def admincrystals(self, ctx: commands.Context, target: discord.Member, amount: int) -> None:
        if not await self._require_admin(ctx):
            return
        profile = await self._get_or_create_target_profile(target)
        updated = await self.bot.game.admin_grant_resources(profile.player_id, crystals=amount)
        await ctx.send(f"Gave {amount:,} crystals to {target.display_name}. New total: {updated.crystals:,}.")

    @commands.command(
        aliases=["addmaterials", "addmats"],
        help="Admin only: add materials and stamina to a player.",
        extras={
            "category": "admin",
            "usage": "y!adminmaterials <@user> <training> <skill> <seals> [stamina=0]",
            "examples": ["y!adminmaterials @digipompu 50 25 10 120"],
            "details": "Adds training scrolls, skill scrolls, grade seals, and optional stamina to the target profile.",
        },
    )
    async def adminmaterials(
        self,
        ctx: commands.Context,
        target: discord.Member,
        training: int,
        skill: int,
        seals: int,
        stamina: int = 0,
    ) -> None:
        if not await self._require_admin(ctx):
            return
        profile = await self._get_or_create_target_profile(target)
        updated = await self.bot.game.admin_grant_resources(
            profile.player_id,
            training_scrolls=training,
            skill_scrolls=skill,
            grade_seals=seals,
            stamina=stamina,
        )
        await ctx.send(
            f"Updated {target.display_name}: "
            f"Training {updated.training_scrolls}, Skill {updated.skill_scrolls}, "
            f"Seals {updated.grade_seals}, Stamina {updated.stamina}/{updated.max_stamina}."
        )

    @commands.command(
        aliases=["addcard", "givecard"],
        help="Admin only: grant character copies directly into a player's inventory.",
        extras={
            "category": "admin",
            "usage": "y!admincard <@user> <character_key> [amount=1]",
            "examples": ["y!admincard @digipompu gojo_six_eyes", "y!admincard @friend sukuna_king 5"],
            "details": "Adds any character by key straight into the target inventory. Use keys from the source data like `yuji_student`, `gojo_six_eyes`, or `sukuna_king`.",
        },
    )
    async def admincard(
        self,
        ctx: commands.Context,
        target: discord.Member,
        character_key: str,
        amount: int = 1,
    ) -> None:
        if not await self._require_admin(ctx):
            return
        if amount < 1:
            await ctx.send("Amount must be at least 1.")
            return
        profile = await self._get_or_create_target_profile(target)
        try:
            granted = await self.bot.game.admin_add_character_copies(profile.player_id, character_key, amount)
        except ValueError as exc:
            await ctx.send(str(exc))
            return
        await ctx.send(
            f"Granted {len(granted)} copy/copies of `{character_key}` to {target.display_name}."
        )

    @commands.command(
        aliases=["wipeplayer"],
        help="Admin only: completely reset one player's save.",
        extras={
            "category": "admin",
            "usage": "y!adminreset <@user>",
            "examples": ["y!adminreset @digipompu"],
            "details": "Deletes the target player's team, characters, and profile so they can start fresh.",
        },
    )
    async def adminreset(self, ctx: commands.Context, target: discord.Member) -> None:
        if not await self._require_admin(ctx):
            return
        profile = await self.bot.game.get_profile(target.id)
        if not profile:
            await ctx.send("That user does not have a profile yet.")
            return
        await self.bot.game.admin_reset_profile(profile.player_id)
        await ctx.send(f"Reset {target.display_name}'s save data.")

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
