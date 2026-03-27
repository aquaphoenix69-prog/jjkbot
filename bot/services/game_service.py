from __future__ import annotations

import random
from datetime import UTC, date, datetime, timedelta

from bot.config import get_settings
from bot.data.characters import CHARACTERS, SUMMON_TYPES
from bot.db.database import Database
from bot.models.game import CharacterDefinition, OwnedCharacter, PlayerProfile


class GameService:
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
                    key, name, title, rarity, grade_label, image_url, base_hp, base_attack,
                    base_defense, base_speed, base_energy, basic_skill,
                    ultimate_skill, passive, domain_name, banner_tags, drop_weight, quote
                )
                VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8,
                    $9, $10, $11, $12,
                    $13, $14, $15, $16, $17, $18
                )
                ON CONFLICT (key) DO UPDATE SET
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

    async def get_owned_characters(self, player_id: int) -> list[OwnedCharacter]:
        records = await self.db.fetch(
            """
            SELECT pc.*, cc.name, cc.title, cc.rarity, cc.grade_label, cc.base_hp,
                   cc.image_url, cc.base_attack, cc.base_defense, cc.base_speed, cc.base_energy,
                   cc.basic_skill, cc.ultimate_skill, cc.passive, cc.domain_name,
                   cc.banner_tags, cc.drop_weight, cc.quote
            FROM player_characters pc
            JOIN character_catalog cc ON cc.key = pc.character_key
            WHERE pc.player_id = $1
            ORDER BY pc.locked DESC, pc.awakened DESC, pc.level DESC, pc.id ASC
            """,
            player_id,
        )
        return [self._owned_from_record(row) for row in records]

    async def get_character_instance(
        self, player_id: int, instance_id: int
    ) -> OwnedCharacter | None:
        row = await self.db.fetchrow(
            """
            SELECT pc.*, cc.name, cc.title, cc.rarity, cc.grade_label, cc.base_hp,
                   cc.image_url, cc.base_attack, cc.base_defense, cc.base_speed, cc.base_energy,
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

    async def get_leaderboard(self, limit: int = 10) -> list[tuple[int, int]]:
        rows = await self.db.fetch(
            "SELECT user_id, rank_points FROM players ORDER BY rank_points DESC LIMIT $1",
            limit,
        )
        return [(row["user_id"], row["rank_points"]) for row in rows]

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
        )
        return OwnedCharacter(
            instance_id=row["id"],
            player_id=row["player_id"],
            character_key=row["character_key"],
            level=row["level"],
            xp=row["xp"],
            grade=row["grade"],
            skill_level=row["skill_level"],
            awakened=bool(row["awakened"]),
            locked=bool(row["locked"]),
            acquired_at=acquired_at,
            definition=definition,
        )

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
