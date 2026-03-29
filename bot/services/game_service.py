from __future__ import annotations

import random
from datetime import UTC, date, datetime, timedelta

from bot.config import get_settings
from bot.data.characters import CHARACTERS, SUMMON_TYPES
from bot.db.database import Database
from bot.models.game import CharacterDefinition, OwnedCharacter, PlayerProfile


class GameService:
    INVENTORY_SORT_LABELS: dict[str, str] = {
        "default": "Default",
        "rarity": "Rarity",
        "hp": "HP",
        "attack": "Attack",
        "defense": "Defense",
        "speed": "Speed",
        "energy": "Energy",
        "power": "Power",
        "level": "Level",
        "enhancement": "Enhancement",
        "evolution": "Evolution",
        "id": "Inventory ID",
        "card": "Card Number",
    }
    RARITY_ORDER = {
        "normal": 0,
        "rare": 1,
        "epic": 2,
        "legendary": 3,
    }
    LEADERBOARD_STATS: dict[str, dict[str, str]] = {
        "rank": {
            "column": "rank_points",
            "label": "RP",
            "title": "Rank Points",
        },
        "coins": {
            "column": "coins",
            "label": "Coins",
            "title": "Coins",
        },
        "crystals": {
            "column": "crystals",
            "label": "Crystals",
            "title": "Crystals",
        },
        "streak": {
            "column": "daily_streak",
            "label": "Days",
            "title": "Daily Streak",
        },
        "story": {
            "column": "story_stage",
            "label": "Stage",
            "title": "Story Stage",
        },
        "collection": {
            "column": "collection",
            "label": "Units",
            "title": "Collection Size",
        },
    }

    def __init__(self, db: Database) -> None:
        self.db = db
        self.settings = get_settings()
        self.character_map = {character.key: character for character in CHARACTERS}

    async def seed_characters(self) -> None:
        for character in CHARACTERS:
            banner_tags = (
                "|".join(character.banner_tags)
                if self.db.is_sqlite
                else character.banner_tags
            )
            await self.db.execute(
                """
                INSERT INTO character_catalog (
                    key, card_number, name, title, rarity, grade_label, image_url, base_hp, base_attack,
                    base_defense, base_speed, base_energy, basic_skill,
                    ultimate_skill, passive, domain_name, banner_tags, drop_weight, quote
                )
                VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9,
                    $10, $11, $12, $13,
                    $14, $15, $16, $17, $18, $19
                )
                ON CONFLICT (key) DO UPDATE SET
                    card_number = EXCLUDED.card_number,
                    name = EXCLUDED.name,
                    title = EXCLUDED.title,
                    rarity = EXCLUDED.rarity,
                    grade_label = EXCLUDED.grade_label,
                    image_url = EXCLUDED.image_url,
                    base_hp = EXCLUDED.base_hp,
                    base_attack = EXCLUDED.base_attack,
                    base_defense = EXCLUDED.base_defense,
                    base_speed = EXCLUDED.base_speed,
                    base_energy = EXCLUDED.base_energy,
                    basic_skill = EXCLUDED.basic_skill,
                    ultimate_skill = EXCLUDED.ultimate_skill,
                    passive = EXCLUDED.passive,
                    domain_name = EXCLUDED.domain_name,
                    banner_tags = EXCLUDED.banner_tags,
                    drop_weight = EXCLUDED.drop_weight,
                    quote = EXCLUDED.quote
                """,
                character.key,
                character.card_number,
                character.name,
                character.title,
                character.rarity,
                character.grade,
                character.image_url,
                character.base_hp,
                character.base_attack,
                character.base_defense,
                character.base_speed,
                character.base_energy,
                character.basic_skill,
                character.ultimate_skill,
                character.passive,
                character.domain_name,
                banner_tags,
                character.drop_weight,
                character.quote,
            )

    async def create_profile(self, user_id: int) -> PlayerProfile:
        existing = await self.get_profile(user_id)
        if existing:
            return existing

        now_value = datetime.now(UTC).isoformat() if self.db.is_sqlite else datetime.now(UTC)
        if self.db.is_sqlite:
            record = await self.db.fetchrow(
                """
                INSERT INTO players (
                    user_id, coins, crystals, stamina, max_stamina, last_stamina_at
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
                """,
                user_id,
                self.settings.starting_coins,
                self.settings.starting_crystals,
                self.settings.starting_stamina,
                self.settings.starting_stamina,
                now_value,
            )
        else:
            record = await self.db.fetchrow(
                """
                INSERT INTO players (
                    user_id, coins, crystals, stamina, max_stamina, last_stamina_at
                )
                VALUES ($1, $2, $3, $4, $4, $5)
                RETURNING *
                """,
                user_id,
                self.settings.starting_coins,
                self.settings.starting_crystals,
                self.settings.starting_stamina,
                now_value,
            )
        if not record:
            raise ValueError("Failed to create profile.")

        profile = self._profile_from_record(record)
        starter_instance = await self.add_character(profile.player_id, "yuji_student")
        await self.set_team(profile.player_id, [starter_instance, None, None])
        return profile

    async def get_profile(self, user_id: int) -> PlayerProfile | None:
        await self.db.ensure_stamina(user_id)
        record = await self.db.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        return self._profile_from_record(record) if record else None

    async def get_profile_by_player_id(self, player_id: int) -> PlayerProfile:
        record = await self.db.fetchrow("SELECT * FROM players WHERE id = $1", player_id)
        if not record:
            raise ValueError("Profile not found.")
        return self._profile_from_record(record)

    async def add_character(self, player_id: int, character_key: str) -> int:
        instance_id = await self.db.fetchval(
            """
            INSERT INTO player_characters (player_id, character_key)
            VALUES ($1, $2)
            RETURNING id
            """,
            player_id,
            character_key,
        )
        return int(instance_id)

    async def get_owned_characters(
        self,
        player_id: int,
        *,
        sort_key: str = "default",
        rarity_filter: str | None = None,
        ascending: bool = False,
    ) -> list[OwnedCharacter]:
        records = await self.db.fetch(
            """
            SELECT pc.*, cc.name, cc.title, cc.rarity, cc.grade_label, cc.base_hp,
                   cc.card_number, cc.image_url, cc.base_attack, cc.base_defense, cc.base_speed, cc.base_energy,
                   cc.basic_skill, cc.ultimate_skill, cc.passive, cc.domain_name,
                   cc.banner_tags, cc.drop_weight, cc.quote
            FROM player_characters pc
            JOIN character_catalog cc ON cc.key = pc.character_key
            WHERE pc.player_id = $1
            ORDER BY pc.id ASC
            """,
            player_id,
        )
        characters = [self._owned_from_record(row) for row in records]
        return self._sort_owned_characters(
            characters,
            sort_key=sort_key,
            rarity_filter=rarity_filter,
            ascending=ascending,
        )

    async def get_character_instance(
        self, player_id: int, instance_id: int
    ) -> OwnedCharacter | None:
        row = await self.db.fetchrow(
            """
            SELECT pc.*, cc.name, cc.title, cc.rarity, cc.grade_label, cc.base_hp,
                   cc.card_number, cc.image_url, cc.base_attack, cc.base_defense, cc.base_speed, cc.base_energy,
                   cc.basic_skill, cc.ultimate_skill, cc.passive, cc.domain_name,
                   cc.banner_tags, cc.drop_weight, cc.quote
            FROM player_characters pc
            JOIN character_catalog cc ON cc.key = pc.character_key
            WHERE pc.player_id = $1 AND pc.id = $2
            """,
            player_id,
            instance_id,
        )
        return self._owned_from_record(row) if row else None

    async def get_inventory_entry_by_position(
        self,
        player_id: int,
        position: int,
        *,
        sort_key: str = "default",
        rarity_filter: str | None = None,
        ascending: bool = False,
    ) -> OwnedCharacter | None:
        if position < 1:
            return None
        characters = await self.get_owned_characters(
            player_id,
            sort_key=sort_key,
            rarity_filter=rarity_filter,
            ascending=ascending,
        )
        if position > len(characters):
            return None
        return characters[position - 1]

    def find_character_definition(self, query: str) -> CharacterDefinition | None:
        normalized = query.lower().strip()
        if not normalized:
            return None
        exact = [
            character
            for character in CHARACTERS
            if character.key.lower() == normalized or character.name.lower() == normalized
        ]
        if exact:
            return exact[0]
        partial = [
            character
            for character in CHARACTERS
            if normalized in character.name.lower() or normalized in character.key.lower() or normalized in character.title.lower()
        ]
        if partial:
            return partial[0]
        return None

    async def get_team(self, player_id: int) -> list[OwnedCharacter]:
        record = await self.db.fetchrow("SELECT * FROM teams WHERE player_id = $1", player_id)
        if not record:
            return []
        team: list[OwnedCharacter] = []
        for slot_id in [record["slot1"], record["slot2"], record["slot3"]]:
            if slot_id:
                character = await self.get_character_instance(player_id, slot_id)
                if character:
                    team.append(character)
        return team

    async def set_team(self, player_id: int, slots: list[int | None]) -> None:
        while len(slots) < 3:
            slots.append(None)
        await self.db.execute(
            """
            INSERT INTO teams (player_id, slot1, slot2, slot3)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (player_id) DO UPDATE SET
                slot1 = EXCLUDED.slot1,
                slot2 = EXCLUDED.slot2,
                slot3 = EXCLUDED.slot3
            """,
            player_id,
            slots[0],
            slots[1],
            slots[2],
        )

    async def toggle_lock(self, player_id: int, instance_id: int) -> bool:
        locked = await self.db.fetchval(
            """
            UPDATE player_characters
            SET locked = NOT locked
            WHERE player_id = $1 AND id = $2
            RETURNING locked
            """,
            player_id,
            instance_id,
        )
        return bool(locked)

    async def enhance_character(
        self,
        player_id: int,
        target_instance_id: int,
        fodder_rarity: str,
    ) -> tuple[OwnedCharacter, int, int]:
        target = await self.get_character_instance(player_id, target_instance_id)
        if not target:
            raise ValueError("Character instance not found.")
        if target.enhancement_level >= target.max_enhancement_level:
            raise ValueError(f"This character is already at the enhancement cap of {target.max_enhancement_level}.")

        normalized_rarity = fodder_rarity.lower().strip()
        if normalized_rarity not in self.RARITY_ORDER:
            raise ValueError("Rarity must be `normal`, `rare`, `epic`, or `legendary`.")

        owned = await self.get_owned_characters(player_id, sort_key="id", ascending=True)
        fodder = [
            character
            for character in owned
            if character.instance_id != target_instance_id
            and not character.locked
            and character.definition.rarity.lower() == normalized_rarity
        ]
        if not fodder:
            raise ValueError(f"You do not have any unlocked {normalized_rarity.title()} cards to use.")

        levels_needed = target.max_enhancement_level - target.enhancement_level
        chosen = fodder[:levels_needed]
        new_level = min(target.max_enhancement_level, target.enhancement_level + len(chosen))
        statements: list[tuple[str, tuple[object, ...]]] = [
            (
                """
                UPDATE player_characters
                SET enhancement_level = $3
                WHERE player_id = $1 AND id = $2
                """,
                (player_id, target_instance_id, new_level),
            ),
        ]
        statements.extend(
            (
                "DELETE FROM player_characters WHERE player_id = $1 AND id = $2",
                (player_id, character.instance_id),
            )
            for character in chosen
        )
        await self.db.executemany(statements)
        updated = await self.get_character_instance(player_id, target_instance_id)
        if not updated:
            raise ValueError("Enhancement completed but the character could not be reloaded.")
        return updated, len(chosen), new_level - target.enhancement_level

    async def preview_enhancement(
        self,
        player_id: int,
        target_instance_id: int,
        fodder_rarity: str,
    ) -> tuple[int, int]:
        target = await self.get_character_instance(player_id, target_instance_id)
        if not target:
            raise ValueError("Character instance not found.")
        if target.enhancement_level >= target.max_enhancement_level:
            raise ValueError(f"This character is already at the enhancement cap of {target.max_enhancement_level}.")

        normalized_rarity = fodder_rarity.lower().strip()
        if normalized_rarity not in self.RARITY_ORDER:
            raise ValueError("Rarity must be `normal`, `rare`, `epic`, or `legendary`.")

        owned = await self.get_owned_characters(player_id, sort_key="id", ascending=True)
        usable_count = sum(
            1
            for character in owned
            if character.instance_id != target_instance_id
            and not character.locked
            and character.definition.rarity.lower() == normalized_rarity
        )
        if usable_count < 1:
            raise ValueError(f"You do not have any unlocked {normalized_rarity.title()} cards to use.")

        levels_needed = target.max_enhancement_level - target.enhancement_level
        levels_gained = min(levels_needed, usable_count)
        return usable_count if usable_count < levels_needed else levels_needed, levels_gained

    async def evolve_character(self, player_id: int, target_instance_id: int) -> tuple[OwnedCharacter, list[int]]:
        target = await self.get_character_instance(player_id, target_instance_id)
        if not target:
            raise ValueError("Character instance not found.")
        if target.evolution_stage >= 3:
            raise ValueError("This character is already at max evolution.")

        owned = await self.get_owned_characters(player_id, sort_key="id", ascending=True)
        sacrifices = [
            character
            for character in owned
            if character.instance_id != target_instance_id
            and not character.locked
            and character.character_key == target.character_key
            and character.evolution_stage == target.evolution_stage
        ]
        if len(sacrifices) < 2:
            next_stage = target.evolution_stage + 1
            raise ValueError(
                f"You need 2 unlocked duplicate copies of this unit at evo {target.evolution_stage} to reach evo {next_stage}."
            )

        consumed = sacrifices[:2]
        await self.db.executemany(
            [
                (
                    """
                    UPDATE player_characters
                    SET evolution_stage = evolution_stage + 1
                    WHERE player_id = $1 AND id = $2
                    """,
                    (player_id, target_instance_id),
                ),
                *[
                    ("DELETE FROM player_characters WHERE player_id = $1 AND id = $2", (player_id, item.instance_id))
                    for item in consumed
                ],
            ]
        )
        updated = await self.get_character_instance(player_id, target_instance_id)
        if not updated:
            raise ValueError("Evolution completed but the character could not be reloaded.")
        return updated, [item.instance_id for item in consumed]

    async def summon(
        self, player_id: int, summon_type: str, amount: int
    ) -> tuple[list[OwnedCharacter], PlayerProfile]:
        profile = await self.get_profile_by_player_id(player_id)
        summon_data = SUMMON_TYPES.get(summon_type)
        if not summon_data:
            raise ValueError("Unknown summon type.")
        cost_per = summon_data["cost"]
        resource_name = "coins"
        total_cost = cost_per * amount
        if getattr(profile, resource_name) < total_cost:
            raise ValueError(f"Not enough {resource_name}. Need {total_cost}.")

        pool = self._build_summon_pool(summon_type)
        obtained: list[OwnedCharacter] = []

        for _ in range(amount):
            chosen = self._roll_character(pool)
            instance_id = await self.add_character(player_id, chosen.key)
            owned = await self.get_character_instance(player_id, instance_id)
            if owned:
                obtained.append(owned)

        await self.db.execute(
            f"""
            UPDATE players
            SET {resource_name} = {resource_name} - $2
            WHERE id = $1
            """,
            player_id,
            total_cost,
        )
        return obtained, await self.get_profile_by_player_id(player_id)

    async def claim_daily(self, player_id: int) -> tuple[PlayerProfile, dict[str, int]]:
        profile = await self.get_profile_by_player_id(player_id)
        today = date.today()
        if profile.last_daily_at and profile.last_daily_at.date() == today:
            raise ValueError("Daily rewards already claimed today.")

        streak = profile.daily_streak + 1
        if profile.last_daily_at and profile.last_daily_at.date() < today - timedelta(days=1):
            streak = 1

        rewards = {
            "coins": 1200 + streak * 180,
            "crystals": 60 + min(streak, 7) * 10,
            "training_scrolls": 3,
            "skill_scrolls": 1,
            "grade_seals": 1 if streak % 3 == 0 else 0,
            "stamina": 25,
        }
        if self.db.is_sqlite:
            current_stamina = min(profile.max_stamina, profile.stamina + rewards["stamina"])
            await self.db.execute(
                """
                UPDATE players
                SET coins = coins + $2,
                    crystals = crystals + $3,
                    training_scrolls = training_scrolls + $4,
                    skill_scrolls = skill_scrolls + $5,
                    grade_seals = grade_seals + $6,
                    stamina = $7,
                    daily_streak = $8,
                    last_daily_at = $9
                WHERE id = $1
                """,
                player_id,
                rewards["coins"],
                rewards["crystals"],
                rewards["training_scrolls"],
                rewards["skill_scrolls"],
                rewards["grade_seals"],
                current_stamina,
                streak,
                datetime.now(UTC).isoformat(),
            )
        else:
            await self.db.execute(
                """
                UPDATE players
                SET coins = coins + $2,
                    crystals = crystals + $3,
                    training_scrolls = training_scrolls + $4,
                    skill_scrolls = skill_scrolls + $5,
                    grade_seals = grade_seals + $6,
                    stamina = LEAST(max_stamina, stamina + $7),
                    daily_streak = $8,
                    last_daily_at = $9
                WHERE id = $1
                """,
                player_id,
                rewards["coins"],
                rewards["crystals"],
                rewards["training_scrolls"],
                rewards["skill_scrolls"],
                rewards["grade_seals"],
                rewards["stamina"],
                streak,
                datetime.now(UTC),
            )
        return await self.get_profile_by_player_id(player_id), rewards

    async def spend_stamina(self, player_id: int, amount: int) -> None:
        profile = await self.get_profile_by_player_id(player_id)
        if profile.stamina < amount:
            raise ValueError("Not enough stamina for that action.")
        await self.db.execute(
            "UPDATE players SET stamina = stamina - $2 WHERE id = $1",
            player_id,
            amount,
        )

    async def reward_player(self, player_id: int, rewards: dict[str, int]) -> PlayerProfile:
        await self.db.execute(
            """
            UPDATE players
            SET coins = coins + $2,
                crystals = crystals + $3,
                training_scrolls = training_scrolls + $4,
                skill_scrolls = skill_scrolls + $5,
                grade_seals = grade_seals + $6,
                story_stage = story_stage + $7,
                rank_points = rank_points + $8
            WHERE id = $1
            """,
            player_id,
            rewards.get("coins", 0),
            rewards.get("crystals", 0),
            rewards.get("training_scrolls", 0),
            rewards.get("skill_scrolls", 0),
            rewards.get("grade_seals", 0),
            rewards.get("story_stage", 0),
            rewards.get("rank_points", 0),
        )
        return await self.get_profile_by_player_id(player_id)

    async def admin_grant_resources(
        self,
        player_id: int,
        *,
        coins: int = 0,
        crystals: int = 0,
        stamina: int = 0,
        training_scrolls: int = 0,
        skill_scrolls: int = 0,
        grade_seals: int = 0,
        rank_points: int = 0,
    ) -> PlayerProfile:
        profile = await self.get_profile_by_player_id(player_id)
        new_stamina = max(0, min(profile.max_stamina, profile.stamina + stamina))
        await self.db.execute(
            """
            UPDATE players
            SET coins = coins + $2,
                crystals = crystals + $3,
                stamina = $4,
                training_scrolls = training_scrolls + $5,
                skill_scrolls = skill_scrolls + $6,
                grade_seals = grade_seals + $7,
                rank_points = rank_points + $8
            WHERE id = $1
            """,
            player_id,
            coins,
            crystals,
            new_stamina,
            training_scrolls,
            skill_scrolls,
            grade_seals,
            rank_points,
        )
        return await self.get_profile_by_player_id(player_id)

    async def admin_add_character_copies(
        self, player_id: int, character_key: str, amount: int
    ) -> list[OwnedCharacter]:
        if character_key not in self.character_map:
            raise ValueError("Unknown character key.")
        granted: list[OwnedCharacter] = []
        for _ in range(amount):
            instance_id = await self.add_character(player_id, character_key)
            owned = await self.get_character_instance(player_id, instance_id)
            if owned:
                granted.append(owned)
        return granted

    async def admin_reset_profile(self, player_id: int) -> None:
        await self.db.executemany(
            [
                ("DELETE FROM teams WHERE player_id = $1", (player_id,)),
                ("DELETE FROM player_characters WHERE player_id = $1", (player_id,)),
                ("DELETE FROM players WHERE id = $1", (player_id,)),
            ]
        )

    async def update_rank_points(self, player_id: int, delta: int) -> None:
        if self.db.is_sqlite:
            profile = await self.get_profile_by_player_id(player_id)
            new_value = max(100, profile.rank_points + delta)
            await self.db.execute(
                "UPDATE players SET rank_points = $2 WHERE id = $1",
                player_id,
                new_value,
            )
        else:
            await self.db.execute(
                """
                UPDATE players
                SET rank_points = GREATEST(100, rank_points + $2)
                WHERE id = $1
                """,
                player_id,
                delta,
            )

    async def record_pvp(self, attacker_id: int, defender_id: int, winner_id: int) -> None:
        await self.db.execute(
            """
            INSERT INTO pvp_history (attacker_id, defender_id, winner_id)
            VALUES ($1, $2, $3)
            """,
            attacker_id,
            defender_id,
            winner_id,
        )

    async def get_leaderboard(self, stat: str = "rank", limit: int = 10) -> tuple[str, str, list[tuple[int, int]]]:
        normalized = stat.lower().strip()
        if normalized not in self.LEADERBOARD_STATS:
            raise ValueError("Unknown leaderboard stat.")

        stat_data = self.LEADERBOARD_STATS[normalized]
        if normalized == "collection":
            rows = await self.db.fetch(
                """
                SELECT p.user_id, COUNT(pc.id) AS value
                FROM players p
                LEFT JOIN player_characters pc ON pc.player_id = p.id
                GROUP BY p.id, p.user_id
                ORDER BY value DESC, p.user_id ASC
                LIMIT $1
                """,
                limit,
            )
        else:
            column = stat_data["column"]
            rows = await self.db.fetch(
                f"SELECT user_id, {column} AS value FROM players ORDER BY {column} DESC, user_id ASC LIMIT $1",
                limit,
            )

        entries = [(row["user_id"], int(row["value"])) for row in rows]
        return stat_data["title"], stat_data["label"], entries

    async def upgrade_character(self, player_id: int, instance_id: int, action: str) -> OwnedCharacter:
        profile = await self.get_profile_by_player_id(player_id)
        character = await self.get_character_instance(player_id, instance_id)
        if not character:
            raise ValueError("Character instance not found.")

        if action == "level":
            if profile.training_scrolls < 1:
                raise ValueError("You need at least 1 Training Scroll.")
            if character.level >= 100:
                raise ValueError("This character is already level 100.")
            await self.db.executemany(
                [
                    ("UPDATE players SET training_scrolls = training_scrolls - 1 WHERE id = $1", (player_id,)),
                    (
                        """
                        UPDATE player_characters
                        SET level = level + 1, xp = xp + 100
                        WHERE player_id = $1 AND id = $2
                        """,
                        (player_id, instance_id),
                    ),
                ]
            )
        elif action == "skill":
            if profile.skill_scrolls < 1:
                raise ValueError("You need at least 1 Skill Scroll.")
            if character.skill_level >= 10:
                raise ValueError("Skill mastery is already maxed.")
            await self.db.executemany(
                [
                    ("UPDATE players SET skill_scrolls = skill_scrolls - 1 WHERE id = $1", (player_id,)),
                    (
                        """
                        UPDATE player_characters
                        SET skill_level = skill_level + 1
                        WHERE player_id = $1 AND id = $2
                        """,
                        (player_id, instance_id),
                    ),
                ]
            )
        elif action == "grade":
            if profile.grade_seals < 1:
                raise ValueError("You need at least 1 Grade Seal.")
            if character.grade >= 5:
                raise ValueError("Sorcerer grade is already maxed.")
            await self.db.executemany(
                [
                    ("UPDATE players SET grade_seals = grade_seals - 1 WHERE id = $1", (player_id,)),
                    (
                        """
                        UPDATE player_characters
                        SET grade = grade + 1
                        WHERE player_id = $1 AND id = $2
                        """,
                        (player_id, instance_id),
                    ),
                ]
            )
        elif action == "awaken":
            if character.awakened:
                raise ValueError("This sorcerer already awakened.")
            if "special grade" not in character.definition.grade.lower():
                raise ValueError("Only Special Grade units can awaken.")
            if character.level < 50 or character.grade < 3:
                raise ValueError("Awakening needs level 50 and grade 3.")
            if profile.grade_seals < 2 or profile.skill_scrolls < 2:
                raise ValueError("Awakening needs 2 Grade Seals and 2 Skill Scrolls.")
            await self.db.executemany(
                [
                    (
                        """
                        UPDATE players
                        SET grade_seals = grade_seals - 2, skill_scrolls = skill_scrolls - 2
                        WHERE id = $1
                        """,
                        (player_id,),
                    ),
                    (
                        """
                        UPDATE player_characters
                        SET awakened = TRUE
                        WHERE player_id = $1 AND id = $2
                        """,
                        (player_id, instance_id),
                    ),
                ]
            )
        else:
            raise ValueError("Unknown upgrade action.")

        updated = await self.get_character_instance(player_id, instance_id)
        if not updated:
            raise ValueError("Upgrade completed but character could not be reloaded.")
        return updated

    def _profile_from_record(self, record) -> PlayerProfile:
        def parse_optional(value):
            if not (self.db.is_sqlite and value):
                return value
            parsed = datetime.fromisoformat(str(value).replace(" ", "T"))
            return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)

        def parse_required(value):
            if not self.db.is_sqlite:
                return value
            parsed = datetime.fromisoformat(str(value).replace(" ", "T"))
            return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)

        return PlayerProfile(
            player_id=record["id"],
            user_id=record["user_id"],
            coins=record["coins"],
            crystals=record["crystals"],
            stamina=record["stamina"],
            max_stamina=record["max_stamina"],
            pity_counter=record["pity_counter"],
            daily_streak=record["daily_streak"],
            last_daily_at=parse_optional(record["last_daily_at"]),
            rank_points=record["rank_points"],
            training_scrolls=record["training_scrolls"],
            grade_seals=record["grade_seals"],
            skill_scrolls=record["skill_scrolls"],
            story_stage=record["story_stage"],
            last_stamina_at=parse_required(record["last_stamina_at"]),
        )

    def _owned_from_record(self, row) -> OwnedCharacter:
        banner_tags = row["banner_tags"].split("|") if self.db.is_sqlite else list(row["banner_tags"])
        acquired_at = row["acquired_at"]
        if self.db.is_sqlite:
            parsed = datetime.fromisoformat(str(acquired_at).replace(" ", "T"))
            acquired_at = parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
        definition = CharacterDefinition(
            key=row["character_key"],
            name=row["name"],
            title=row["title"],
            rarity=row["rarity"],
            grade=row["grade_label"],
            image_url=row["image_url"],
            base_hp=row["base_hp"],
            base_attack=row["base_attack"],
            base_defense=row["base_defense"],
            base_speed=row["base_speed"],
            base_energy=row["base_energy"],
            basic_skill=row["basic_skill"],
            ultimate_skill=row["ultimate_skill"],
            passive=row["passive"],
            domain_name=row["domain_name"],
            banner_tags=banner_tags,
            drop_weight=row["drop_weight"],
            quote=row["quote"],
            card_number=row["card_number"],
        )
        return OwnedCharacter(
            instance_id=row["id"],
            player_id=row["player_id"],
            character_key=row["character_key"],
            level=row["level"],
            xp=row["xp"],
            grade=row["grade"],
            skill_level=row["skill_level"],
            enhancement_level=row["enhancement_level"],
            evolution_stage=row["evolution_stage"],
            awakened=bool(row["awakened"]),
            locked=bool(row["locked"]),
            acquired_at=acquired_at,
            definition=definition,
        )

    def _sort_owned_characters(
        self,
        characters: list[OwnedCharacter],
        *,
        sort_key: str,
        rarity_filter: str | None,
        ascending: bool,
    ) -> list[OwnedCharacter]:
        if rarity_filter:
            normalized_filter = rarity_filter.lower().strip()
            characters = [
                character
                for character in characters
                if character.definition.rarity.lower() == normalized_filter
            ]

        normalized_sort = sort_key.lower().strip()
        if normalized_sort not in self.INVENTORY_SORT_LABELS:
            normalized_sort = "default"

        if normalized_sort == "default":
            return sorted(
                characters,
                key=lambda owned: (
                    owned.locked,
                    owned.awakened,
                    owned.evolution_stage,
                    owned.enhancement_level,
                    owned.level,
                    -owned.instance_id,
                ),
                reverse=True,
            )

        sorters = {
            "rarity": lambda owned: (
                self.RARITY_ORDER.get(owned.definition.rarity.lower(), -1),
                owned.evolution_stage,
                owned.enhancement_level,
                owned.power,
                -owned.instance_id,
            ),
            "hp": lambda owned: (owned.effective_hp, owned.power, -owned.instance_id),
            "attack": lambda owned: (owned.effective_attack, owned.power, -owned.instance_id),
            "defense": lambda owned: (owned.effective_defense, owned.power, -owned.instance_id),
            "speed": lambda owned: (owned.effective_speed, owned.power, -owned.instance_id),
            "energy": lambda owned: (owned.effective_energy, owned.power, -owned.instance_id),
            "power": lambda owned: (owned.power, owned.effective_attack, -owned.instance_id),
            "level": lambda owned: (owned.level, owned.enhancement_level, owned.power, -owned.instance_id),
            "enhancement": lambda owned: (owned.enhancement_level, owned.evolution_stage, owned.power, -owned.instance_id),
            "evolution": lambda owned: (owned.evolution_stage, owned.enhancement_level, owned.power, -owned.instance_id),
            "id": lambda owned: owned.instance_id,
            "card": lambda owned: (owned.definition.card_number, -owned.instance_id),
        }
        return sorted(characters, key=sorters[normalized_sort], reverse=not ascending)

    def _build_summon_pool(self, summon_type: str) -> list[tuple[CharacterDefinition, float]]:
        summon_data = SUMMON_TYPES[summon_type]
        pool: list[tuple[CharacterDefinition, float]] = []
        for grade_name, chance in summon_data["rates"].items():
            grade_chars = [
                character
                for character in CHARACTERS
                if "boss" not in character.banner_tags and self._matches_grade_bucket(character.grade, grade_name)
            ]
            if not grade_chars:
                continue
            total_weight = sum(character.drop_weight for character in grade_chars)
            for character in grade_chars:
                scaled_weight = chance * (character.drop_weight / total_weight)
                pool.append((character, scaled_weight))
        return pool

    def _roll_character(self, pool: list[tuple[CharacterDefinition, float]]) -> CharacterDefinition:
        return random.choices(
            [character for character, _ in pool],
            weights=[weight for _, weight in pool],
            k=1,
        )[0]

    def _matches_grade_bucket(self, character_grade: str, target_grade: str) -> bool:
        normalized = character_grade.lower()
        if target_grade == "Grade 1":
            return "grade 1" in normalized or "semi-grade 1" in normalized
        if target_grade == "Special Grade":
            return "special grade" in normalized
        return target_grade.lower() in normalized
