from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime

from bot.data.characters import CHARACTERS
from bot.models.game import BattleLog, CharacterDefinition, OwnedCharacter
from bot.services.game_service import GameService


@dataclass
class Fighter:
    name: str
    definition: CharacterDefinition
    max_hp: int
    hp: int
    attack: int
    defense: int
    speed: int
    energy: int
    skill_level: int
    awakened: bool
    team: str
    status: dict[str, int] = field(default_factory=dict)
    domain_used: bool = False

    @property
    def alive(self) -> bool:
        return self.hp > 0


class BattleService:
    def __init__(self, game: GameService) -> None:
        self.game = game
        self.enemy_pool = [character for character in CHARACTERS if "boss" in character.banner_tags]

    async def run_story_battle(self, player_id: int) -> BattleLog:
        team = await self.game.get_team(player_id)
        if not team:
            raise ValueError("Set a team first with /team.")
        profile = await self.game.get_profile_by_player_id(player_id)
        await self.game.spend_stamina(player_id, 15)

        enemies = self._generate_story_enemies(profile.story_stage)
        log = self._simulate(self._build_team(team, "Allies"), self._build_team(enemies, "Curses"))
        if log.winner == "Allies":
            rewards = {
                "coins": 450 + profile.story_stage * 90,
                "crystals": 20 if profile.story_stage % 3 == 0 else 10,
                "training_scrolls": 1,
                "skill_scrolls": 1 if profile.story_stage % 5 == 0 else 0,
                "grade_seals": 1 if profile.story_stage % 8 == 0 else 0,
                "story_stage": 1,
            }
            log.rewards = rewards
            await self.game.reward_player(player_id, rewards)
        return log

    async def run_boss_raid(self, player_id: int) -> BattleLog:
        team = await self.game.get_team(player_id)
        if not team:
            raise ValueError("Set a team first with /team.")
        await self.game.spend_stamina(player_id, 25)

        definition = random.choice(self.enemy_pool)
        boss = OwnedCharacter(
            instance_id=0,
            player_id=0,
            character_key=definition.key,
            level=75,
            xp=0,
            grade=4,
            skill_level=7,
            awakened=True,
            locked=False,
            acquired_at=datetime.utcnow(),
            definition=definition,
        )
        log = self._simulate(self._build_team(team, "Raiders"), self._build_team([boss], "Boss"))
        log.rewards = {"coins": 1800, "crystals": 80, "grade_seals": 1, "training_scrolls": 2} if log.winner == "Raiders" else {"coins": 600}
        await self.game.reward_player(player_id, log.rewards)
        return log

    async def run_pvp(self, attacker_id: int, defender_id: int) -> BattleLog:
        attacker_team = await self.game.get_team(attacker_id)
        defender_team = await self.game.get_team(defender_id)
        if not attacker_team or not defender_team:
            raise ValueError("Both players need a team of sorcerers.")

        await self.game.spend_stamina(attacker_id, 10)
        battle_log = self._simulate(
            self._build_team(attacker_team, "Attacker"),
            self._build_team(defender_team, "Defender"),
        )
        attacker_won = battle_log.winner == "Attacker"
        winner_id = attacker_id if attacker_won else defender_id

        await self.game.record_pvp(attacker_id, defender_id, winner_id)
        await self.game.update_rank_points(attacker_id, 25 if attacker_won else -18)
        await self.game.update_rank_points(defender_id, -12 if attacker_won else 20)
        battle_log.rewards = {"rank_points": 25 if attacker_won else -18}
        return battle_log

    def _generate_story_enemies(self, stage: int) -> list[OwnedCharacter]:
        picks = random.sample(self.enemy_pool, k=min(3, len(self.enemy_pool)))
        enemies: list[OwnedCharacter] = []
        for index, definition in enumerate(picks, start=1):
            enemies.append(
                OwnedCharacter(
                    instance_id=index,
                    player_id=0,
                    character_key=definition.key,
                    level=min(90, 5 + stage * 3),
                    xp=0,
                    grade=min(5, 1 + stage // 4),
                    skill_level=min(10, 1 + stage // 5),
                    awakened=stage >= 12,
                    locked=False,
                    acquired_at=datetime.utcnow(),
                    definition=definition,
                )
            )
        return enemies

    def _build_team(self, team: list[OwnedCharacter], label: str) -> list[Fighter]:
        fighters: list[Fighter] = []
        for owned in team:
            scale = 1 + (owned.level - 1) * 0.03 + (owned.grade - 1) * 0.09
            awaken_bonus = 1.12 if owned.awakened else 1.0
            fighters.append(
                Fighter(
                    name=owned.definition.name,
                    definition=owned.definition,
                    max_hp=int(owned.definition.base_hp * scale * awaken_bonus),
                    hp=int(owned.definition.base_hp * scale * awaken_bonus),
                    attack=int((owned.definition.base_attack + owned.skill_level * 5) * scale * awaken_bonus),
                    defense=int(owned.definition.base_defense * scale * awaken_bonus),
                    speed=int(owned.definition.base_speed * (1 + owned.level * 0.005)),
                    energy=owned.definition.base_energy,
                    skill_level=owned.skill_level,
                    awakened=owned.awakened,
                    team=label,
                )
            )
        return fighters

    def _simulate(self, left_team: list[Fighter], right_team: list[Fighter]) -> BattleLog:
        battle_log = BattleLog(winner="Draw")
        for round_number in range(1, 16):
            order = sorted(
                [fighter for fighter in left_team + right_team if fighter.alive],
                key=lambda fighter: (fighter.speed, random.random()),
                reverse=True,
            )
            if not order:
                break

            battle_log.rounds.append(f"Round {round_number}")
            for fighter in order:
                if not fighter.alive:
                    continue
                if self._resolve_status_start(fighter, battle_log):
                    continue

                opponents = right_team if fighter.team == left_team[0].team else left_team
                living_opponents = [enemy for enemy in opponents if enemy.alive]
                if not living_opponents:
                    battle_log.winner = fighter.team
                    return battle_log

                target = random.choice(living_opponents)
                action_name, damage, extra = self._perform_action(fighter, target)
                target.hp = max(0, target.hp - damage)
                if target.definition.passive == "Infinity":
                    reduced = int(damage * 0.35)
                    target.hp = min(target.max_hp, target.hp + reduced)
                    damage -= reduced
                    extra += " Infinity softened the blow."
                battle_log.rounds.append(
                    f"{fighter.name} used {action_name} on {target.name} for {damage} damage.{extra}"
                )
                if target.hp == 0:
                    battle_log.rounds.append(f"{target.name} was exorcised.")

                if self._all_defeated(opponents):
                    battle_log.winner = fighter.team
                    return battle_log

            self._tick_statuses(left_team + right_team, battle_log)

        left_alive = sum(1 for fighter in left_team if fighter.alive)
        right_alive = sum(1 for fighter in right_team if fighter.alive)
        battle_log.winner = left_team[0].team if left_alive >= right_alive else right_team[0].team
        return battle_log

    def _perform_action(self, fighter: Fighter, target: Fighter) -> tuple[str, int, str]:
        critical = random.random() < 0.18
        base_damage = max(40, fighter.attack - int(target.defense * 0.6))
        bonus = 1.5 if critical else 1.0
        extra = " Critical hit." if critical else ""

        if fighter.energy >= 140 and (fighter.awakened or fighter.definition.rarity == "Special Grade") and not fighter.domain_used:
            fighter.energy -= 140
            fighter.domain_used = True
            damage = int(base_damage * (2.1 + fighter.skill_level * 0.08) * bonus)
            extra += f" Domain Expansion: {fighter.definition.domain_name}."
            self._apply_status_from_skill(fighter, target)
            return fighter.definition.ultimate_skill, damage, extra

        if fighter.energy >= 60 and random.random() < 0.45:
            fighter.energy -= 60
            damage = int(base_damage * (1.4 + fighter.skill_level * 0.05) * bonus)
            self._apply_status_from_skill(fighter, target)
            self._apply_passive(fighter, target, damage)
            return fighter.definition.basic_skill, damage, extra

        fighter.energy = min(fighter.definition.base_energy + 40, fighter.energy + 20)
        damage = int(base_damage * bonus)
        self._apply_passive(fighter, target, damage)
        return "Cursed Strike", damage, extra

    def _apply_status_from_skill(self, fighter: Fighter, target: Fighter) -> None:
        passive = fighter.definition.passive.lower()
        if "speech" in passive or "seal" in passive:
            target.status["stun"] = 1
        elif "burn" in passive or fighter.definition.name == "Jogo":
            target.status["burn"] = 2
        elif fighter.definition.name == "Nobara Kugisaki":
            target.status["cursed_seal"] = 2

    def _apply_passive(self, fighter: Fighter, target: Fighter, damage: int) -> None:
        passive = fighter.definition.passive.lower()
        if passive == "lifesteal":
            fighter.hp = min(fighter.max_hp, fighter.hp + int(damage * 0.2))
        elif passive == "shikigami summons" and random.random() < 0.2:
            target.hp = max(0, target.hp - int(damage * 0.25))

    def _resolve_status_start(self, fighter: Fighter, battle_log: BattleLog) -> bool:
        if fighter.status.get("stun", 0) > 0:
            battle_log.rounds.append(f"{fighter.name} is stunned and loses the turn.")
            return True
        return False

    def _tick_statuses(self, fighters: list[Fighter], battle_log: BattleLog) -> None:
        for fighter in fighters:
            if not fighter.alive:
                continue
            if fighter.status.get("burn", 0) > 0:
                burn_damage = int(fighter.max_hp * 0.05)
                fighter.hp = max(0, fighter.hp - burn_damage)
                battle_log.rounds.append(f"{fighter.name} suffers {burn_damage} burn damage.")
            if fighter.status.get("cursed_seal", 0) > 0:
                seal_damage = int(fighter.max_hp * 0.03)
                fighter.hp = max(0, fighter.hp - seal_damage)
                battle_log.rounds.append(f"{fighter.name}'s cursed seal deals {seal_damage} damage.")

            for key in ("burn", "stun", "cursed_seal"):
                if fighter.status.get(key, 0) > 0:
                    fighter.status[key] -= 1

    def _all_defeated(self, team: list[Fighter]) -> bool:
        return all(not fighter.alive for fighter in team)
