from __future__ import annotations

import discord

from bot.data.characters import SUMMON_TYPES
from bot.models.game import BattleLog, OwnedCharacter, PlayerProfile


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
            f"`#{character.instance_id}` {character.definition.name}\n"
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
) -> discord.Embed:
    total_pages = max(1, (len(characters) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    page_items = characters[start : start + per_page]

    embed = discord.Embed(
        title=f"{user.display_name}'s JJK Collection",
        color=discord.Color.blurple(),
        description="Instance ids are used for `y!team`, `y!upgrade`, and `y!lock`.",
    )
    if not page_items:
        embed.add_field(name="Collection", value="No characters collected yet.", inline=False)
    else:
        lines = []
        for owned in page_items:
            flags = []
            if owned.locked:
                flags.append("Locked")
            if owned.awakened:
                flags.append("Awakened")
            suffix = f" ({', '.join(flags)})" if flags else ""
            lines.append(
                f"`#{owned.instance_id}` {owned.definition.name} [{owned.definition.rarity}]"
                f" | {owned.definition.grade} | Lv.{owned.level} G{owned.grade} S{owned.skill_level}{suffix}"
            )
        embed.add_field(name="Sorcerers", value="\n".join(lines), inline=False)
        if page_items[0].definition.image_url:
            embed.set_thumbnail(url=page_items[0].definition.image_url)
    embed.set_footer(text=f"Page {page + 1}/{total_pages}")
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
                f"`#{owned.instance_id}` {owned.definition.name}\n"
                f"{owned.definition.title}\n"
                f"Lore Grade: {owned.definition.grade}\n"
                f"Lv.{owned.level} | Grade {owned.grade} | Skill {owned.skill_level}"
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
            f"Awakened: {'Yes' if character.awakened else 'No'}"
        ),
        inline=False,
    )
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
