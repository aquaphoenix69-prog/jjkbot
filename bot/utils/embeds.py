from __future__ import annotations

import discord

from bot.data.characters import BANNERS
from bot.models.game import BattleLog, OwnedCharacter, PlayerProfile


def profile_embed(user: discord.abc.User, profile: PlayerProfile) -> discord.Embed:
    embed = discord.Embed(
        title=f"{user.display_name}'s Sorcerer Profile",
        color=discord.Color.dark_teal(),
        description="Your current progression across Tokyo Jujutsu High.",
    )
    embed.add_field(name="Coins", value=f"{profile.coins:,}", inline=True)
    embed.add_field(name="Crystals", value=f"{profile.crystals:,}", inline=True)
    embed.add_field(name="Stamina", value=f"{profile.stamina}/{profile.max_stamina}", inline=True)
    embed.add_field(name="Pity", value=f"{profile.pity_counter}/30", inline=True)
    embed.add_field(name="Daily Streak", value=str(profile.daily_streak), inline=True)
    embed.add_field(name="Rank Points", value=str(profile.rank_points), inline=True)
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
    banner_key: str,
    characters: list[OwnedCharacter],
    profile: PlayerProfile,
) -> discord.Embed:
    banner = BANNERS[banner_key]
    embed = discord.Embed(
        title=f"{user.display_name} opened {banner['name']}",
        color=discord.Color.gold(),
        description=banner["description"],
    )
    lines = []
    for owned in characters:
        awakened = " | Domain Ready" if owned.awakened else ""
        lines.append(
            f"`#{owned.instance_id}` {owned.definition.name} [{owned.definition.rarity}]"
            f" | {owned.definition.basic_skill}{awakened}"
        )
    embed.add_field(name="Recruits", value="\n".join(lines), inline=False)
    embed.set_footer(text=f"Remaining pity: {profile.pity_counter}/30")
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
        description="Instance ids are used for `/team`, `/upgrade`, and `/lock`.",
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
                f" Lv.{owned.level} G{owned.grade} S{owned.skill_level}{suffix}"
            )
        embed.add_field(name="Sorcerers", value="\n".join(lines), inline=False)
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
                f"Lv.{owned.level} | Grade {owned.grade} | Skill {owned.skill_level}"
            ),
            inline=False,
        )
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


def leaderboard_embed(entries: list[tuple[str, int]]) -> discord.Embed:
    embed = discord.Embed(
        title="Jujutsu Ranked Leaderboard",
        color=discord.Color.brand_green(),
    )
    embed.description = "\n".join(
        f"**#{index}** {name} - {points} RP" for index, (name, points) in enumerate(entries, start=1)
    ) or "No ranked players yet."
    return embed
