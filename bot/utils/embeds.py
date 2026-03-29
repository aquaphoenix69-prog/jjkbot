from __future__ import annotations

import discord

from bot.data.characters import SUMMON_TYPES
from bot.models.game import BattleLog, BattleSnapshot, CharacterDefinition, OwnedCharacter, PlayerProfile


def profile_embed(user: discord.abc.User, profile: PlayerProfile) -> discord.Embed:
    embed = discord.Embed(
        title=f"{user.display_name}'s Sorcerer Profile",
        color=discord.Color.dark_teal(),
        description="Your current progression across Tokyo Jujutsu High.",
    )
    embed.add_field(name="Coins", value=f"{profile.coins:,}", inline=True)
    embed.add_field(name="Stamina", value=f"{profile.stamina}/{profile.max_stamina}", inline=True)
    embed.add_field(name="Daily Streak", value=str(profile.daily_streak), inline=True)
    embed.add_field(name="Rank Points", value=str(profile.rank_points), inline=True)
    embed.add_field(name="Crystals", value=f"{profile.crystals:,}", inline=True)
    embed.add_field(
        name="Materials",
        value=(
            f"Training Scrolls: {profile.training_scrolls}\n"
            f"Skill Scrolls: {profile.skill_scrolls}\n"
            f"Grade Seals: {profile.grade_seals}"
        ),
        inline=False,
    )
    embed.set_footer(text=f"Story Stage {profile.story_stage}")
    return embed


def summon_embed(
    user: discord.abc.User,
    summon_type: str,
    character: OwnedCharacter,
    profile: PlayerProfile,
    amount: int,
    image_name: str | None = None,
) -> discord.Embed:
    summon_data = SUMMON_TYPES[summon_type]
    embed = discord.Embed(
        title=f"{user.display_name} used {summon_data['name']}",
        color=discord.Color(summon_data["color"]),
        description=summon_data["description"],
    )
    embed.add_field(
        name="Result",
        value=(
            f"`Card #{character.definition.card_number}` {character.definition.name}\n"
            f"Print: `#{character.instance_id}`\n"
            f"Rarity: {character.definition.rarity}\n"
            f"Sorcerer Grade: {character.definition.grade}\n"
            f"Basic Skill: {character.definition.basic_skill}\n"
            f"Ultimate: {character.definition.ultimate_skill}"
        ),
        inline=False,
    )
    embed.add_field(name="Quote", value=character.definition.quote, inline=False)
    embed.add_field(
        name="Wallet",
        value=(
            f"Spent: {SUMMON_TYPES[summon_type]['cost'] * amount:,} Coins\n"
            f"Remaining Coins: {profile.coins:,}"
        ),
        inline=False,
    )
    if image_name:
        embed.set_image(url=f"attachment://{image_name}")
    elif character.definition.image_url:
        embed.set_image(url=character.definition.image_url)
    return embed


def inventory_page_embed(
    user: discord.abc.User,
    characters: list[OwnedCharacter],
    page: int,
    per_page: int,
    *,
    inventory_serials: dict[int, int] | None = None,
    sort_label: str = "Default",
    rarity_filter: str | None = None,
) -> discord.Embed:
    total_pages = max(1, (len(characters) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    page_items = characters[start : start + per_page]

    embed = discord.Embed(
        title=f"{user.display_name}'s JJK Collection",
        color=discord.Color.teal(),
        description="All your owned cards are listed below. Inventory numbers are for `y!info` and `y!enh`. Prints are the permanent summon serials.",
    )
    if not page_items:
        embed.add_field(name="Collection", value="No characters collected yet.", inline=False)
    else:
        lines = []
        for owned in page_items:
            inventory_number = inventory_serials.get(owned.instance_id, owned.instance_id) if inventory_serials else owned.instance_id
            lines.append(
                f"`{inventory_number}.` **{owned.definition.name}** [{owned.definition.rarity}]\n"
                f"`Rarity {owned.definition.rarity}` `Print {owned.instance_id}` `Evo {owned.evolution_stage}` `Enh {owned.enhancement_level}`"
            )
        chunks = _chunk_inventory_lines(lines)
        for index, chunk in enumerate(chunks, start=1):
            name = "Inventory" if index == 1 else f"Inventory {index}"
            embed.add_field(name=name, value=chunk, inline=False)
        if page_items[0].definition.image_url:
            embed.set_thumbnail(url=page_items[0].definition.image_url)
    filter_text = rarity_filter.title() if rarity_filter else "All"
    embed.set_footer(text=f"Page {page + 1}/{total_pages} | Sort: {sort_label} | Filter: {filter_text}")
    return embed


def summon_summary_embed(
    user: discord.abc.User,
    summon_type: str,
    recruits: list[OwnedCharacter],
    profile: PlayerProfile,
) -> discord.Embed:
    summon_data = SUMMON_TYPES[summon_type]
    counts: dict[str, int] = {}
    grouped: dict[tuple[str, str], int] = {}
    for recruit in recruits:
        rarity = recruit.definition.rarity
        counts[rarity] = counts.get(rarity, 0) + 1
        key = (recruit.definition.name, recruit.definition.rarity)
        grouped[key] = grouped.get(key, 0) + 1
    grouped_lines = [
        f"{count} {name} [{rarity}] summoned"
        for (name, rarity), count in sorted(grouped.items(), key=lambda item: (-item[1], item[0][0].lower()))
    ]

    embed = discord.Embed(
        title=f"{user.display_name} used {summon_data['name']} x{len(recruits)}",
        color=discord.Color(summon_data["color"]),
        description="Large summon completed. Showing grouped results for faster output.",
    )
    embed.add_field(
        name="Rarity Summary",
        value="\n".join(f"{rarity}: {count}" for rarity, count in sorted(counts.items())) or "No recruits",
        inline=False,
    )
    embed.add_field(
        name="Summon Results",
        value="\n".join(grouped_lines[:20]) or "No recruits",
        inline=False,
    )
    embed.add_field(name="Remaining Coins", value=f"{profile.coins:,}", inline=False)
    return embed


def resource_embed(user: discord.abc.User, label: str, value: str, color: discord.Color) -> discord.Embed:
    embed = discord.Embed(
        title=f"{user.display_name}'s {label}",
        color=color,
    )
    embed.description = value
    return embed


def team_embed(user: discord.abc.User, team: list[OwnedCharacter]) -> discord.Embed:
    embed = discord.Embed(
        title=f"{user.display_name}'s Active Team",
        color=discord.Color.dark_magenta(),
    )
    if not team:
        embed.description = "No team configured yet."
        return embed
    for slot, owned in enumerate(team, start=1):
        embed.add_field(
            name=f"Slot {slot}",
            value=(
                f"`Inst #{owned.instance_id}` `Card #{owned.definition.card_number}` {owned.definition.name}\n"
                f"{owned.definition.title}\n"
                f"Lore Grade: {owned.definition.grade}\n"
                f"Lv.{owned.level} | Grade {owned.grade} | Skill {owned.skill_level} | Enh {owned.enhancement_level} | Evo {owned.evolution_stage}"
            ),
            inline=False,
        )
    if team[0].definition.image_url:
        embed.set_thumbnail(url=team[0].definition.image_url)
    return embed


def battle_embed(title: str, log: BattleLog) -> discord.Embed:
    color = (
        discord.Color.green()
        if "Allies" in log.winner or "Attacker" in log.winner or "Raiders" in log.winner
        else discord.Color.red()
    )
    embed = discord.Embed(title=title, color=color)
    embed.description = f"Winner: **{log.winner}**"
    snippet = log.rounds[:12]
    if len(log.rounds) > 12:
        snippet.append("...battle log truncated...")
    embed.add_field(name="Combat Log", value="\n".join(snippet) or "No actions recorded.", inline=False)
    if log.rewards:
        reward_lines = [f"{key.replace('_', ' ').title()}: {value}" for key, value in log.rewards.items()]
        embed.add_field(name="Rewards", value="\n".join(reward_lines), inline=False)
    return embed


def daily_embed(profile: PlayerProfile, rewards: dict[str, int]) -> discord.Embed:
    embed = discord.Embed(
        title="Daily Rewards Claimed",
        color=discord.Color.orange(),
        description=f"Streak is now **{profile.daily_streak}** days.",
    )
    embed.add_field(
        name="Rewards",
        value="\n".join(f"{key.replace('_', ' ').title()}: {value}" for key, value in rewards.items()),
        inline=False,
    )
    return embed


def upgrade_embed(character: OwnedCharacter, action: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"{character.definition.name} upgraded",
        color=discord.Color.fuchsia(),
        description=f"Applied `{action}` successfully.",
    )
    embed.add_field(
        name="Current State",
        value=(
            f"Lv.{character.level}\n"
            f"Grade {character.grade}\n"
            f"Skill {character.skill_level}\n"
            f"Enhancement {character.enhancement_level}\n"
            f"Evolution {character.evolution_stage}\n"
            f"Awakened: {'Yes' if character.awakened else 'No'}"
        ),
        inline=False,
    )
    return embed


def battle_snapshot_embed(title: str, snapshot: BattleSnapshot, winner: str | None = None) -> discord.Embed:
    color = discord.Color.orange() if winner is None else (discord.Color.green() if winner == snapshot.actor_team else discord.Color.red())
    embed = discord.Embed(title=title, color=color)
    embed.description = (
        f"**Round {snapshot.round_number}**\n"
        f"{snapshot.detail}"
    )
    left_lines = [_unit_summary(unit) for unit in snapshot.left_team[:3]]
    right_lines = [_unit_summary(unit) for unit in snapshot.right_team[:3]]
    embed.add_field(name="Allies", value="\n".join(left_lines) or "None", inline=True)
    embed.add_field(name="Enemies", value="\n".join(right_lines) or "None", inline=True)
    if winner:
        embed.add_field(name="Winner", value=winner, inline=False)
    return embed


def enhancement_embed(
    character: OwnedCharacter,
    consumed_count: int,
    levels_gained: int,
    fodder_rarity: str,
    *,
    pending: bool = False,
    in_progress: bool = False,
    inventory_number: int | None = None,
) -> discord.Embed:
    if pending:
        title = f"Confirm enhancement for {character.definition.name}"
        description = (
            f"Inventory No. **{inventory_number}** will use up to **{consumed_count}** unlocked "
            f"**{fodder_rarity.title()}** card(s) for **+{levels_gained}** enhancement levels.\n"
            "Press **Confirm Enhance** to continue."
        )
    elif in_progress:
        title = f"Enhancing {character.definition.name}..."
        description = (
            f"Inventory No. **{inventory_number}** is being enhanced with unlocked "
            f"**{fodder_rarity.title()}** cards."
        )
    else:
        title = f"{character.definition.name} enhanced"
        description = (
            f"Inventory No. **{inventory_number}** consumed {consumed_count} unlocked "
            f"{fodder_rarity.title()} card(s) for +{levels_gained} enhancement levels."
        )
    embed = discord.Embed(
        title=title,
        color=discord.Color.gold(),
        description=description,
    )
    embed.add_field(
        name="Current State",
        value=(
            f"Print {character.instance_id}\n"
            f"Enhancement {character.enhancement_level}\n"
            f"Evolution {character.evolution_stage}\n"
            f"HP {character.effective_hp}\n"
            f"ATK {character.effective_attack}\n"
            f"DEF {character.effective_defense}\n"
            f"SPD {character.effective_speed}"
        ),
        inline=False,
    )
    return embed


def evolution_embed(character: OwnedCharacter, consumed_ids: list[int]) -> discord.Embed:
    embed = discord.Embed(
        title=f"{character.definition.name} evolved",
        color=discord.Color.dark_gold(),
        description=f"Evolved to stage {character.evolution_stage}/3 by consuming copies: {', '.join(f'#{item}' for item in consumed_ids)}",
    )
    embed.add_field(
        name="Current State",
        value=(
            f"Enhancement {character.enhancement_level}/{character.max_enhancement_level}\n"
            f"Evolution {character.evolution_stage}\n"
            f"HP {character.effective_hp}\n"
            f"ATK {character.effective_attack}\n"
            f"DEF {character.effective_defense}\n"
            f"Power {character.power}"
        ),
        inline=False,
    )
    return embed


def card_info_embed(character: OwnedCharacter, inventory_number: int) -> discord.Embed:
    embed = discord.Embed(
        title=character.definition.name,
        color=_rarity_color(character.definition.rarity),
        description=character.definition.title,
    )
    embed.add_field(
        name="Card Info",
        value=(
            f"Inventory No: **{inventory_number}**\n"
            f"Card ID: **{character.definition.card_number}**\n"
            f"Print: **{character.instance_id}**\n"
            f"Rarity: **{character.definition.rarity}**\n"
            f"Grade: **{character.definition.grade}**"
        ),
        inline=False,
    )
    embed.add_field(
        name="Progression",
        value=(
            f"Level: **{character.level}**\n"
            f"Skill: **{character.skill_level}**\n"
            f"Enhancement: **{character.enhancement_level}**\n"
            f"Evolution: **{character.evolution_stage}**\n"
            f"Awakened: **{'Yes' if character.awakened else 'No'}**\n"
            f"Locked: **{'Yes' if character.locked else 'No'}**"
        ),
        inline=False,
    )
    embed.add_field(
        name="Stats",
        value=(
            f"HP: **{character.effective_hp}**\n"
            f"ATK: **{character.effective_attack}**\n"
            f"DEF: **{character.effective_defense}**\n"
            f"SPD: **{character.effective_speed}**\n"
            f"ENERGY: **{character.effective_energy}**\n"
            f"POWER: **{character.power}**"
        ),
        inline=False,
    )
    embed.add_field(
        name="Abilities",
        value=(
            f"Basic: **{character.definition.basic_skill}**\n"
            f"Ultimate: **{character.definition.ultimate_skill}**\n"
            f"Passive: **{character.definition.passive}**\n"
            f"Domain: **{character.definition.domain_name}**"
        ),
        inline=False,
    )
    embed.add_field(name="Quote", value=character.definition.quote, inline=False)
    if character.definition.image_url:
        embed.set_image(url=character.definition.image_url)
        embed.set_thumbnail(url=character.definition.image_url)
    return embed


def character_catalog_embed(character: CharacterDefinition) -> discord.Embed:
    embed = discord.Embed(
        title=character.name,
        color=_rarity_color(character.rarity),
        description=character.title,
    )
    embed.add_field(
        name="Card Info",
        value=(
            f"Card ID: **{character.card_number}**\n"
            f"Series: **Jujutsu Kaisen**\n"
            f"Rarity: **{character.rarity}**\n"
            f"Grade: **{character.grade}**"
        ),
        inline=False,
    )
    embed.add_field(
        name="Base Stats",
        value=(
            f"HP: **{character.base_hp}**\n"
            f"ATK: **{character.base_attack}**\n"
            f"DEF: **{character.base_defense}**\n"
            f"SPD: **{character.base_speed}**\n"
            f"ENERGY: **{character.base_energy}**"
        ),
        inline=False,
    )
    embed.add_field(
        name="Techniques",
        value=(
            f"Basic Skill: **{character.basic_skill}**\n"
            f"Ultimate Skill: **{character.ultimate_skill}**\n"
            f"Passive: **{character.passive}**\n"
            f"Domain: **{character.domain_name}**"
        ),
        inline=False,
    )
    embed.add_field(name="Quote", value=character.quote, inline=False)
    if character.image_url:
        embed.set_image(url=character.image_url)
        embed.set_thumbnail(url=character.image_url)
    return embed


def leaderboard_embed(
    stat_title: str,
    stat_label: str,
    entries: list[tuple[str, int]],
    available_stats: list[str],
) -> discord.Embed:
    embed = discord.Embed(
        title=f"Jujutsu {stat_title} Leaderboard",
        color=discord.Color.brand_green(),
    )
    embed.description = "\n".join(
        f"**#{index}** {name} - {value:,} {stat_label}" for index, (name, value) in enumerate(entries, start=1)
    ) or "No players on this board yet."
    embed.set_footer(text=f"Categories: {', '.join(available_stats)}")
    return embed


def _unit_summary(unit) -> str:
    status = ""
    if unit.status:
        status = " [" + ", ".join(name for name, turns in unit.status.items() if turns > 0) + "]"
    return f"**{unit.name}** Lv.{unit.level} Evo {unit.evolution_stage}\nHP {unit.hp:,}/{unit.max_hp:,} | EN {unit.energy}/{unit.max_energy}{status}"


def _rarity_color(rarity: str) -> discord.Color:
    mapping = {
        "normal": discord.Color.light_grey(),
        "rare": discord.Color.blue(),
        "epic": discord.Color.purple(),
        "legendary": discord.Color.gold(),
    }
    return mapping.get(rarity.lower(), discord.Color.blurple())


def _chunk_inventory_lines(lines: list[str]) -> list[str]:
    chunks: list[str] = []
    current = ""
    for line in lines:
        candidate = line if not current else f"{current}\n\n{line}"
        if len(candidate) > 950:
            if current:
                chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks or ["No characters collected yet."]
