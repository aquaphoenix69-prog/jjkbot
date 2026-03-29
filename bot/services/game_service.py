from __future__ import annotations

import json
import random
from datetime import UTC, date, datetime, timedelta

from bot.config import get_settings
from bot.data.characters import CHARACTERS, SUMMON_TYPES
from bot.db.database import Database
from bot.models.game import CharacterDefinition, OwnedCharacter, PlayerProfile


class GameService:
    INVENTORY_SORT_LABELS: dict[str, str] = {
        "default": "Default",
        "name": "Name",
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
    STAT_FIELDS = {
        "hp": ("hp_bonus", "max_hp_stat"),
        "atk": ("attack_bonus", "max_attack_stat"),
        "attack": ("attack_bonus", "max_attack_stat"),
        "def": ("defense_bonus", "max_defense_stat"),
        "defense": ("defense_bonus", "max_defense_stat"),
        "spd": ("speed_bonus", "max_speed_stat"),
        "speed": ("speed_bonus", "max_speed_stat"),
        "energy": ("energy_bonus", "max_energy_stat"),
    }
    RARITY_ORDER = {
        "normal": 0,
        "rare": 1,
        "epic": 2,
        "legendary": 3,
    }
    ENHANCEMENT_LEVEL_XP_BY_RARITY = {
        "normal": 180,
        "rare": 420,
        "epic": 820,
        "legendary": 1200,
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

    async def get_guild_prefix(self, guild_id: int) -> str:
        value = await self.db.fetchval(
            "SELECT prefix FROM guild_settings WHERE guild_id = $1",
            guild_id,
        )
        return str(value) if value else "y!"

    async def set_guild_prefix(self, guild_id: int, prefix: str) -> str:
        await self.db.execute(
            """
            INSERT INTO guild_settings (guild_id, prefix)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE SET
                prefix = EXCLUDED.prefix
            """,
            guild_id,
            prefix,
        )
        return prefix

    async def create_clan(self, player_id: int, name: str) -> dict[str, object]:
        existing = await self.db.fetchrow(
            "SELECT clan_id FROM clan_members WHERE player_id = $1",
            player_id,
        )
        if existing:
            raise ValueError("You are already in a clan.")
        if len(name.strip()) < 3:
            raise ValueError("Clan name must be at least 3 characters long.")
        clan = await self.db.fetchrow(
            """
            INSERT INTO clans (name, leader_player_id)
            VALUES ($1, $2)
            RETURNING *
            """,
            name.strip(),
            player_id,
        )
        if not clan:
            raise ValueError("Failed to create clan.")
        await self.db.execute(
            """
            INSERT INTO clan_members (clan_id, player_id, role)
            VALUES ($1, $2, $3)
            """,
            clan["id"],
            player_id,
            "leader",
        )
        return await self.get_clan_by_player(player_id)

    async def get_clan_by_player(self, player_id: int) -> dict[str, object] | None:
        clan = await self.db.fetchrow(
            """
            SELECT c.*
            FROM clans c
            JOIN clan_members cm ON cm.clan_id = c.id
            WHERE cm.player_id = $1
            """,
            player_id,
        )
        if not clan:
            return None
        members = await self.db.fetch(
            "SELECT player_id, role FROM clan_members WHERE clan_id = $1 ORDER BY joined_at ASC",
            clan["id"],
        )
        return {
            "id": clan["id"],
            "name": clan["name"],
            "level": clan["level"],
            "xp": clan["xp"],
            "coins_bank": clan["coins_bank"],
            "image_url": clan["image_url"],
            "leader_player_id": clan["leader_player_id"],
            "vice_leader_player_id": clan["vice_leader_player_id"],
            "members": [{"player_id": row["player_id"], "role": row["role"]} for row in members],
            "coin_boost_pct": clan["level"] * 2,
            "battle_boost_pct": clan["level"],
        }

    async def set_clan_image(self, player_id: int, image_url: str) -> dict[str, object]:
        clan = await self.get_clan_by_player(player_id)
        if not clan:
            raise ValueError("You are not in a clan.")
        role = await self.db.fetchval("SELECT role FROM clan_members WHERE player_id = $1", player_id)
        if role not in {"leader", "vice_leader"}:
            raise ValueError("Only the leader or vice leader can change the clan image.")
        await self.db.execute(
            "UPDATE clans SET image_url = $2 WHERE id = $1",
            clan["id"],
            image_url,
        )
        return await self.get_clan_by_player(player_id)

    async def upgrade_clan(self, player_id: int, coins: int) -> dict[str, object]:
        clan = await self.get_clan_by_player(player_id)
        if not clan:
            raise ValueError("You are not in a clan.")
        role = await self.db.fetchval("SELECT role FROM clan_members WHERE player_id = $1", player_id)
        if role not in {"leader", "vice_leader"}:
            raise ValueError("Only the leader or vice leader can upgrade the clan.")
        profile = await self.get_profile_by_player_id(player_id)
        if coins < 1:
            raise ValueError("Upgrade contribution must be at least 1 coin.")
        if profile.coins < coins:
            raise ValueError("Not enough coins.")
        await self.db.executemany(
            [
                ("UPDATE players SET coins = coins - $2 WHERE id = $1", (player_id, coins)),
                ("UPDATE clans SET coins_bank = coins_bank + $2, xp = xp + $2 WHERE id = $1", (clan["id"], coins)),
            ]
        )
        clan_row = await self.db.fetchrow("SELECT * FROM clans WHERE id = $1", clan["id"])
        if not clan_row:
            raise ValueError("Clan not found after upgrade.")
        level = int(clan_row["level"])
        xp = int(clan_row["xp"])
        while xp >= self._clan_next_level_xp(level):
            xp -= self._clan_next_level_xp(level)
            level += 1
        await self.db.execute(
            "UPDATE clans SET level = $2, xp = $3 WHERE id = $1",
            clan["id"],
            level,
            xp,
        )
        return await self.get_clan_by_player(player_id)

    async def promote_vice_leader(self, leader_player_id: int, target_user_id: int) -> dict[str, object]:
        clan = await self.get_clan_by_player(leader_player_id)
        if not clan:
            raise ValueError("You are not in a clan.")
        role = await self.db.fetchval("SELECT role FROM clan_members WHERE player_id = $1", leader_player_id)
        if role != "leader":
            raise ValueError("Only the clan leader can assign a vice leader.")
        target_profile = await self.get_profile(target_user_id)
        if not target_profile:
            raise ValueError("That user does not have a profile.")
        target_membership = await self.db.fetchval("SELECT clan_id FROM clan_members WHERE player_id = $1", target_profile.player_id)
        if target_membership != clan["id"]:
            raise ValueError("That user is not in your clan.")
        await self.db.executemany(
            [
                ("UPDATE clan_members SET role = 'member' WHERE clan_id = $1 AND role = 'vice_leader'", (clan["id"],)),
                ("UPDATE clan_members SET role = 'vice_leader' WHERE player_id = $1", (target_profile.player_id,)),
                ("UPDATE clans SET vice_leader_player_id = $2 WHERE id = $1", (clan["id"], target_profile.player_id)),
            ]
        )
        return await self.get_clan_by_player(leader_player_id)

    async def create_trade(self, requester_player_id: int, receiver_player_id: int) -> dict[str, object]:
        if requester_player_id == receiver_player_id:
            raise ValueError("You cannot trade with yourself.")
        existing = await self._get_open_trade_for_player(requester_player_id)
        if existing:
            raise ValueError("Finish or cancel your current trade first.")
        other_existing = await self._get_open_trade_for_player(receiver_player_id)
        if other_existing:
            raise ValueError("That player is already in another active trade.")
        row = await self.db.fetchrow(
            """
            INSERT INTO trades (
                requester_player_id, receiver_player_id, requester_offer, receiver_offer
            )
            VALUES ($1, $2, $3, $4)
            RETURNING *
            """,
            requester_player_id,
            receiver_player_id,
            json.dumps(self._empty_offer()),
            json.dumps(self._empty_offer()),
        )
        if not row:
            raise ValueError("Failed to create trade.")
        return self._trade_from_row(row)

    async def accept_trade(self, receiver_player_id: int) -> dict[str, object]:
        row = await self.db.fetchrow(
            "SELECT * FROM trades WHERE receiver_player_id = $1 AND status = 'pending' ORDER BY id DESC LIMIT 1",
            receiver_player_id,
        )
        if not row:
            raise ValueError("You do not have a pending trade request.")
        await self.db.execute(
            "UPDATE trades SET status = 'active', updated_at = $2 WHERE id = $1",
            row["id"],
            self._now_value(),
        )
        updated = await self.db.fetchrow("SELECT * FROM trades WHERE id = $1", row["id"])
        return self._trade_from_row(updated)

    async def get_active_trade(self, player_id: int) -> dict[str, object] | None:
        row = await self._get_open_trade_for_player(player_id)
        return self._trade_from_row(row) if row else None

    async def add_trade_assets(
        self,
        player_id: int,
        *,
        coins: int = 0,
        skill_scrolls: int = 0,
        grade_seals: int = 0,
        cards_by_name: str | None = None,
    ) -> dict[str, object]:
        row = await self._get_open_trade_for_player(player_id)
        if not row:
            raise ValueError("You are not in an active trade.")
        trade = self._trade_from_row(row)
        side = "requester" if row["requester_player_id"] == player_id else "receiver"
        offer = dict(trade[f"{side}_offer"])
        profile = await self.get_profile_by_player_id(player_id)

        if coins:
            if profile.coins < offer["coins"] + coins:
                raise ValueError("Not enough coins for that trade offer.")
            offer["coins"] += coins
        if skill_scrolls:
            if profile.skill_scrolls < offer["skill_scrolls"] + skill_scrolls:
                raise ValueError("Not enough skill scrolls for that trade offer.")
            offer["skill_scrolls"] += skill_scrolls
        if grade_seals:
            if profile.grade_seals < offer["grade_seals"] + grade_seals:
                raise ValueError("Not enough grade seals for that trade offer.")
            offer["grade_seals"] += grade_seals
        if cards_by_name:
            matched = await self._match_trade_cards(player_id, cards_by_name, offer["card_ids"])
            if not matched:
                raise ValueError("No unlocked cards matched that search for trading.")
            offer["card_ids"].extend(matched)

        await self._save_trade_offer(row["id"], side, offer)
        updated = await self.db.fetchrow("SELECT * FROM trades WHERE id = $1", row["id"])
        return self._trade_from_row(updated)

    async def confirm_trade(self, player_id: int) -> dict[str, object]:
        row = await self._get_open_trade_for_player(player_id)
        if not row:
            raise ValueError("You are not in an active trade.")
        side = "requester" if row["requester_player_id"] == player_id else "receiver"
        await self.db.execute(
            f"UPDATE trades SET {side}_confirmed = TRUE, updated_at = $2 WHERE id = $1",
            row["id"],
            self._now_value(),
        )
        updated = await self.db.fetchrow("SELECT * FROM trades WHERE id = $1", row["id"])
        trade = self._trade_from_row(updated)
        if trade["requester_confirmed"] and trade["receiver_confirmed"]:
            return await self._finalize_trade(updated)
        return trade

    async def cancel_trade(self, player_id: int) -> None:
        row = await self._get_open_trade_for_player(player_id)
        if not row:
            raise ValueError("You are not in an active trade.")
        await self.db.execute(
            "UPDATE trades SET status = 'cancelled', updated_at = $2 WHERE id = $1",
            row["id"],
            self._now_value(),
        )

    async def add_character(self, player_id: int, character_key: str) -> int:
        definition = self.character_map.get(character_key)
        if not definition:
            raise ValueError("Unknown character key.")
        instance_id = await self.db.fetchval(
            """
            INSERT INTO player_characters (
                player_id, character_key, hp_roll, attack_roll, defense_roll, speed_roll, energy_roll
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            player_id,
            character_key,
            0,
            0,
            0,
            0,
            0,
        )
        return int(instance_id)

    async def get_owned_characters(
        self,
        player_id: int,
        *,
        sort_key: str | list[str] = "default",
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

    async def get_inventory_serial_map(self, player_id: int) -> dict[int, int]:
        records = await self.db.fetch(
            """
            SELECT id
            FROM player_characters
            WHERE player_id = $1
            ORDER BY id ASC
            """,
            player_id,
        )
        return {
            int(row["id"]): index
            for index, row in enumerate(records, start=1)
        }

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
        sort_key: str = "id",
        rarity_filter: str | None = None,
        ascending: bool = True,
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
        if target.level >= target.max_level:
            raise ValueError(f"This character is already at its level cap of {target.max_level}.")

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

        chosen = list(fodder)
        new_level, new_xp, consumed_count = self._calculate_enhancement_progress(target, chosen)
        await self.db.execute(
            """
            UPDATE player_characters
            SET level = $3,
                xp = $4,
                enhancement_level = 0,
                enhancement_xp = 0
            WHERE player_id = $1 AND id = $2
            """,
            player_id,
            target_instance_id,
            new_level,
            new_xp,
        )
        consumed_ids = [character.instance_id for character in chosen[:consumed_count]]
        if consumed_ids:
            placeholders = ", ".join(f"${index}" for index in range(2, len(consumed_ids) + 2))
            await self.db.execute(
                f"DELETE FROM player_characters WHERE player_id = $1 AND id IN ({placeholders})",
                player_id,
                *consumed_ids,
            )
        updated = await self.get_character_instance(player_id, target_instance_id)
        if not updated:
            raise ValueError("Enhancement completed but the character could not be reloaded.")
        return updated, consumed_count, new_level - target.level

    async def preview_enhancement(
        self,
        player_id: int,
        target_instance_id: int,
        fodder_rarity: str,
    ) -> tuple[int, int]:
        target = await self.get_character_instance(player_id, target_instance_id)
        if not target:
            raise ValueError("Character instance not found.")
        if target.level >= target.max_level:
            raise ValueError(f"This character is already at its level cap of {target.max_level}.")

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

        _, _, consumed_count = self._calculate_enhancement_progress(
            target,
            [
                character
                for character in owned
                if character.instance_id != target_instance_id
                and not character.locked
                and character.definition.rarity.lower() == normalized_rarity
            ],
        )
        preview_target = await self.get_character_instance(player_id, target_instance_id)
        if not preview_target:
            raise ValueError("Character instance not found.")
        new_level, _, _ = self._calculate_enhancement_progress(
            preview_target,
            [
                character
                for character in owned
                if character.instance_id != target_instance_id
                and not character.locked
                and character.definition.rarity.lower() == normalized_rarity
            ],
        )
        return consumed_count, new_level - target.level

    async def evolve_character(
        self,
        player_id: int,
        target_instance_id: int,
        sacrifice_instance_id: int,
    ) -> tuple[OwnedCharacter, list[int]]:
        target = await self.get_character_instance(player_id, target_instance_id)
        if not target:
            raise ValueError("Character instance not found.")
        if target.evolution_stage >= 3:
            raise ValueError("This character is already at max evolution.")
        if target_instance_id == sacrifice_instance_id:
            raise ValueError("Use two different inventory cards for evolution.")
        if target.level < target.max_level:
            raise ValueError(f"{target.definition.name} must be at max level before evolving.")

        sacrifice = await self.get_character_instance(player_id, sacrifice_instance_id)
        if not sacrifice:
            raise ValueError("The sacrifice card was not found.")
        if sacrifice.locked:
            raise ValueError("Unlock the sacrifice card before evolving.")
        if sacrifice.character_key != target.character_key:
            raise ValueError("Both cards must be the same character to evolve.")
        if sacrifice.evolution_stage != target.evolution_stage:
            raise ValueError("Both cards must be at the same evolution stage.")
        if sacrifice.level < sacrifice.max_level:
            raise ValueError(f"{sacrifice.definition.name} must also be at max level before evolving.")

        await self.db.executemany(
            [
                (
                    """
                    UPDATE player_characters
                    SET evolution_stage = evolution_stage + 1,
                        hp_roll = $3,
                        attack_roll = $4,
                        defense_roll = $5,
                        speed_roll = $6,
                        energy_roll = $7
                    WHERE player_id = $1 AND id = $2
                    """,
                    (
                        player_id,
                        target_instance_id,
                        random.randint(-1000, 1000),
                        random.randint(-100, 100),
                        random.randint(-100, 100),
                        random.randint(-100, 100),
                        random.randint(-100, 100),
                    ),
                ),
                ("DELETE FROM player_characters WHERE player_id = $1 AND id = $2", (player_id, sacrifice.instance_id)),
            ]
        )
        updated = await self.get_character_instance(player_id, target_instance_id)
        if not updated:
            raise ValueError("Evolution completed but the character could not be reloaded.")
        return updated, [sacrifice.instance_id]

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

    async def admin_add_character_stat(
        self,
        player_id: int,
        inventory_position: int,
        stat_name: str,
        amount: int,
    ) -> OwnedCharacter:
        character = await self.get_inventory_entry_by_position(player_id, inventory_position)
        if not character:
            raise ValueError("That inventory number does not exist.")
        normalized = stat_name.lower().strip()
        field_data = self.STAT_FIELDS.get(normalized)
        if not field_data:
            raise ValueError("Stat must be hp, atk, def, spd, or energy.")
        bonus_column, cap_attr = field_data
        current_total = {
            "hp_bonus": character.definition.base_hp + character.hp_roll + character.hp_bonus,
            "attack_bonus": character.definition.base_attack + character.attack_roll + character.attack_bonus,
            "defense_bonus": character.definition.base_defense + character.defense_roll + character.defense_bonus,
            "speed_bonus": character.definition.base_speed + character.speed_roll + character.speed_bonus,
            "energy_bonus": character.definition.base_energy + character.energy_roll + character.energy_bonus,
        }[bonus_column]
        cap_value = getattr(character, cap_attr)
        applied = min(amount, max(0, cap_value - current_total))
        if applied <= 0:
            raise ValueError("That stat is already at its cap for this card.")
        await self.db.execute(
            f"""
            UPDATE player_characters
            SET {bonus_column} = {bonus_column} + $3
            WHERE player_id = $1 AND id = $2
            """,
            player_id,
            character.instance_id,
            applied,
        )
        updated = await self.get_character_instance(player_id, character.instance_id)
        if not updated:
            raise ValueError("Card updated but could not be reloaded.")
        return updated

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
            if character.level >= character.max_level:
                raise ValueError(f"This character is already at its level cap of {character.max_level}.")
            new_level, new_xp = self._apply_level_xp(character, 120)
            await self.db.executemany(
                [
                    ("UPDATE players SET training_scrolls = training_scrolls - 1 WHERE id = $1", (player_id,)),
                    (
                        """
                        UPDATE player_characters
                        SET level = $3, xp = $4
                        WHERE player_id = $1 AND id = $2
                        """,
                        (player_id, instance_id, new_level, new_xp),
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
            if character.level < character.max_level or character.grade < 5 or character.evolution_stage < 3:
                raise ValueError(f"Awakening needs max level ({character.max_level}), grade 5, and evo 3.")
            if profile.grade_seals < 12 or profile.skill_scrolls < 12 or profile.crystals < 5000 or profile.coins < 2500000:
                raise ValueError("Awakening needs 12 Grade Seals, 12 Skill Scrolls, 5000 Crystals, and 2500000 Coins.")
            await self.db.executemany(
                [
                    (
                        """
                        UPDATE players
                        SET grade_seals = grade_seals - 12,
                            skill_scrolls = skill_scrolls - 12,
                            crystals = crystals - 5000,
                            coins = coins - 2500000
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

    def _apply_level_xp(self, character: OwnedCharacter, gained_xp: int) -> tuple[int, int]:
        level = character.level
        xp = character.xp + gained_xp
        while level < character.max_level:
            requirement = int(90 * (1.11 ** max(0, level - 1)))
            if xp < requirement:
                break
            xp -= requirement
            level += 1
        if level >= character.max_level:
            level = character.max_level
            xp = 0
        return level, xp

    def _calculate_enhancement_progress(
        self,
        target: OwnedCharacter,
        fodder_cards: list[OwnedCharacter],
    ) -> tuple[int, int, int]:
        level = target.level
        xp = target.xp
        consumed = 0
        for fodder in fodder_cards:
            if level >= target.max_level:
                break
            temp_target = OwnedCharacter(
                instance_id=target.instance_id,
                player_id=target.player_id,
                character_key=target.character_key,
                level=level,
                xp=xp,
                grade=target.grade,
                skill_level=target.skill_level,
                enhancement_level=0,
                enhancement_xp=0,
                evolution_stage=target.evolution_stage,
                hp_roll=target.hp_roll,
                attack_roll=target.attack_roll,
                defense_roll=target.defense_roll,
                speed_roll=target.speed_roll,
                energy_roll=target.energy_roll,
                hp_bonus=target.hp_bonus,
                attack_bonus=target.attack_bonus,
                defense_bonus=target.defense_bonus,
                speed_bonus=target.speed_bonus,
                energy_bonus=target.energy_bonus,
                awakened=target.awakened,
                locked=target.locked,
                acquired_at=target.acquired_at,
                definition=target.definition,
            )
            gained_xp = self.ENHANCEMENT_LEVEL_XP_BY_RARITY.get(fodder.definition.rarity.lower(), 180)
            level, xp = self._apply_level_xp(temp_target, gained_xp)
            consumed += 1
            if level >= target.max_level:
                level = target.max_level
                xp = 0
                break
        return level, xp, consumed

    def _clan_next_level_xp(self, level: int) -> int:
        return int(50000 * (1.35 ** max(0, level - 1)))

    def _empty_offer(self) -> dict[str, object]:
        return {
            "coins": 0,
            "skill_scrolls": 0,
            "grade_seals": 0,
            "card_ids": [],
        }

    def _trade_from_row(self, row) -> dict[str, object]:
        if not row:
            raise ValueError("Trade not found.")
        return {
            "id": row["id"],
            "requester_player_id": row["requester_player_id"],
            "receiver_player_id": row["receiver_player_id"],
            "status": row["status"],
            "requester_offer": json.loads(row["requester_offer"]),
            "receiver_offer": json.loads(row["receiver_offer"]),
            "requester_confirmed": bool(row["requester_confirmed"]),
            "receiver_confirmed": bool(row["receiver_confirmed"]),
        }

    async def _get_open_trade_for_player(self, player_id: int):
        return await self.db.fetchrow(
            """
            SELECT *
            FROM trades
            WHERE status IN ('pending', 'active')
              AND (requester_player_id = $1 OR receiver_player_id = $1)
            ORDER BY id DESC
            LIMIT 1
            """,
            player_id,
        )

    async def _save_trade_offer(self, trade_id: int, side: str, offer: dict[str, object]) -> None:
        other_side = "receiver" if side == "requester" else "requester"
        await self.db.execute(
            f"""
            UPDATE trades
            SET {side}_offer = $2,
                {side}_confirmed = FALSE,
                {other_side}_confirmed = FALSE,
                updated_at = $3
            WHERE id = $1
            """,
            trade_id,
            json.dumps(offer),
            self._now_value(),
        )

    async def _match_trade_cards(self, player_id: int, query: str, excluded_ids: list[int]) -> list[int]:
        owned = await self.get_owned_characters(player_id, sort_key="id", ascending=True)
        normalized = query.lower().strip()
        matched = [
            character.instance_id
            for character in owned
            if not character.locked
            and character.instance_id not in excluded_ids
            and normalized in character.definition.name.lower()
        ]
        return matched

    async def _finalize_trade(self, row) -> dict[str, object]:
        trade = self._trade_from_row(row)
        requester_offer = trade["requester_offer"]
        receiver_offer = trade["receiver_offer"]
        requester_id = trade["requester_player_id"]
        receiver_id = trade["receiver_player_id"]
        await self._validate_trade_side(requester_id, requester_offer)
        await self._validate_trade_side(receiver_id, receiver_offer)

        statements: list[tuple[str, tuple[object, ...]]] = [
            (
                """
                UPDATE players
                SET coins = coins - $2 + $3,
                    skill_scrolls = skill_scrolls - $4 + $5,
                    grade_seals = grade_seals - $6 + $7
                WHERE id = $1
                """,
                (
                    requester_id,
                    requester_offer["coins"],
                    receiver_offer["coins"],
                    requester_offer["skill_scrolls"],
                    receiver_offer["skill_scrolls"],
                    requester_offer["grade_seals"],
                    receiver_offer["grade_seals"],
                ),
            ),
            (
                """
                UPDATE players
                SET coins = coins - $2 + $3,
                    skill_scrolls = skill_scrolls - $4 + $5,
                    grade_seals = grade_seals - $6 + $7
                WHERE id = $1
                """,
                (
                    receiver_id,
                    receiver_offer["coins"],
                    requester_offer["coins"],
                    receiver_offer["skill_scrolls"],
                    requester_offer["skill_scrolls"],
                    receiver_offer["grade_seals"],
                    requester_offer["grade_seals"],
                ),
            ),
        ]
        statements.extend(
            ("UPDATE player_characters SET player_id = $2 WHERE id = $1", (card_id, receiver_id))
            for card_id in requester_offer["card_ids"]
        )
        statements.extend(
            ("UPDATE player_characters SET player_id = $2 WHERE id = $1", (card_id, requester_id))
            for card_id in receiver_offer["card_ids"]
        )
        statements.append(
            ("UPDATE trades SET status = 'completed', updated_at = $2 WHERE id = $1", (trade["id"], self._now_value()))
        )
        await self.db.executemany(statements)
        updated = await self.db.fetchrow("SELECT * FROM trades WHERE id = $1", trade["id"])
        return self._trade_from_row(updated)

    async def _validate_trade_side(self, player_id: int, offer: dict[str, object]) -> None:
        profile = await self.get_profile_by_player_id(player_id)
        if profile.coins < int(offer["coins"]):
            raise ValueError("A trade participant no longer has enough coins.")
        if profile.skill_scrolls < int(offer["skill_scrolls"]):
            raise ValueError("A trade participant no longer has enough skill scrolls.")
        if profile.grade_seals < int(offer["grade_seals"]):
            raise ValueError("A trade participant no longer has enough grade seals.")
        for card_id in offer["card_ids"]:
            card = await self.get_character_instance(player_id, int(card_id))
            if not card:
                raise ValueError("A trade participant no longer owns one of the offered cards.")
            if card.locked:
                raise ValueError("Locked cards cannot be traded.")

    def _now_value(self):
        return datetime.now(UTC).isoformat() if self.db.is_sqlite else datetime.now(UTC)

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
            enhancement_xp=row["enhancement_xp"],
            evolution_stage=row["evolution_stage"],
            hp_roll=row["hp_roll"],
            attack_roll=row["attack_roll"],
            defense_roll=row["defense_roll"],
            speed_roll=row["speed_roll"],
            energy_roll=row["energy_roll"],
            hp_bonus=row["hp_bonus"],
            attack_bonus=row["attack_bonus"],
            defense_bonus=row["defense_bonus"],
            speed_bonus=row["speed_bonus"],
            energy_bonus=row["energy_bonus"],
            awakened=bool(row["awakened"]),
            locked=bool(row["locked"]),
            acquired_at=acquired_at,
            definition=definition,
        )

    def _sort_owned_characters(
        self,
        characters: list[OwnedCharacter],
        *,
        sort_key: str | list[str],
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

        sorters = {
            "default": lambda owned: (
                owned.locked,
                owned.awakened,
                owned.evolution_stage,
                owned.level,
                -owned.instance_id,
            ),
            "name": lambda owned: (
                owned.definition.name.lower(),
                owned.definition.rarity.lower(),
                owned.instance_id,
            ),
            "rarity": lambda owned: (
                self.RARITY_ORDER.get(owned.definition.rarity.lower(), -1),
                owned.evolution_stage,
                owned.level,
                owned.power,
                -owned.instance_id,
            ),
            "hp": lambda owned: (owned.effective_hp, owned.power, -owned.instance_id),
            "attack": lambda owned: (owned.effective_attack, owned.power, -owned.instance_id),
            "defense": lambda owned: (owned.effective_defense, owned.power, -owned.instance_id),
            "speed": lambda owned: (owned.effective_speed, owned.power, -owned.instance_id),
            "energy": lambda owned: (owned.effective_energy, owned.power, -owned.instance_id),
            "power": lambda owned: (owned.power, owned.effective_attack, -owned.instance_id),
            "level": lambda owned: (owned.level, owned.evolution_stage, owned.power, -owned.instance_id),
            "enhancement": lambda owned: (owned.level, owned.evolution_stage, owned.power, -owned.instance_id),
            "evolution": lambda owned: (owned.evolution_stage, owned.level, owned.power, -owned.instance_id),
            "id": lambda owned: owned.instance_id,
            "card": lambda owned: (owned.definition.card_number, -owned.instance_id),
        }
        sort_keys = sort_key if isinstance(sort_key, list) else [sort_key]
        normalized_sorts = []
        for item in sort_keys:
            normalized = item.lower().strip()
            if normalized not in self.INVENTORY_SORT_LABELS:
                continue
            normalized_sorts.append(normalized)
        if not normalized_sorts:
            normalized_sorts = ["default"]

        ordered = list(characters)
        for normalized in reversed(normalized_sorts):
            ordered = sorted(
                ordered,
                key=sorters[normalized],
                reverse=False if normalized in {"name", "id", "card"} and ascending else not ascending,
            )
        return ordered

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
