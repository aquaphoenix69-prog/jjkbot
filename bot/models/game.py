from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

MAX_ENHANCEMENT_BY_RARITY = {
    "normal": 20,
    "rare": 30,
    "epic": 45,
    "legendary": 60,
}
RARITY_STAT_MULTIPLIER = {
    "normal": 1.0,
    "rare": 1.06,
    "epic": 1.12,
    "legendary": 1.2,
}


@dataclass(slots=True)
class CharacterDefinition:
    key: str
    name: str
    title: str
    rarity: str
    grade: str
    image_url: str
    base_hp: int
    base_attack: int
    base_defense: int
    base_speed: int
    base_energy: int
    basic_skill: str
    ultimate_skill: str
    passive: str
    domain_name: str
    banner_tags: list[str]
    drop_weight: int
    quote: str
    card_number: int = 0


@dataclass(slots=True)
class OwnedCharacter:
    instance_id: int
    player_id: int
    character_key: str
    level: int
    xp: int
    grade: int
    skill_level: int
    enhancement_level: int
    enhancement_xp: int
    evolution_stage: int
    hp_roll: int
    attack_roll: int
    defense_roll: int
    speed_roll: int
    energy_roll: int
    hp_bonus: int
    attack_bonus: int
    defense_bonus: int
    speed_bonus: int
    energy_bonus: int
    awakened: bool
    locked: bool
    acquired_at: datetime
    definition: CharacterDefinition

    @property
    def max_enhancement_level(self) -> int:
        return MAX_ENHANCEMENT_BY_RARITY.get(self.definition.rarity.lower(), 20)

    @property
    def stat_multiplier(self) -> float:
        rarity_bonus = RARITY_STAT_MULTIPLIER.get(self.definition.rarity.lower(), 1.0)
        return rarity_bonus * (1.0 + self.enhancement_level * 0.025 + self.evolution_stage * 0.18)

    @property
    def next_level_xp(self) -> int:
        return int(100 * (1.18 ** max(0, self.level - 1)))

    @property
    def next_enhancement_xp(self) -> int:
        return int(60 * (1.14 ** max(0, self.enhancement_level)))

    @property
    def max_hp_stat(self) -> int:
        return self.definition.base_hp * 2

    @property
    def max_attack_stat(self) -> int:
        return self.definition.base_attack * 2

    @property
    def max_defense_stat(self) -> int:
        return self.definition.base_defense * 2

    @property
    def max_speed_stat(self) -> int:
        return self.definition.base_speed * 2

    @property
    def max_energy_stat(self) -> int:
        return self.definition.base_energy * 2

    @property
    def rolled_hp(self) -> int:
        return max(1, min(self.max_hp_stat, self.definition.base_hp + self.hp_roll + self.hp_bonus))

    @property
    def rolled_attack(self) -> int:
        return max(1, min(self.max_attack_stat, self.definition.base_attack + self.attack_roll + self.attack_bonus))

    @property
    def rolled_defense(self) -> int:
        return max(1, min(self.max_defense_stat, self.definition.base_defense + self.defense_roll + self.defense_bonus))

    @property
    def rolled_speed(self) -> int:
        return max(1, min(self.max_speed_stat, self.definition.base_speed + self.speed_roll + self.speed_bonus))

    @property
    def rolled_energy(self) -> int:
        return max(1, min(self.max_energy_stat, self.definition.base_energy + self.energy_roll + self.energy_bonus))

    @property
    def effective_hp(self) -> int:
        return int(self.rolled_hp * self.stat_multiplier)

    @property
    def effective_attack(self) -> int:
        return int(self.rolled_attack * self.stat_multiplier)

    @property
    def effective_defense(self) -> int:
        return int(self.rolled_defense * self.stat_multiplier)

    @property
    def effective_speed(self) -> int:
        speed_bonus = 1.0 + self.enhancement_level * 0.01 + self.evolution_stage * 0.05
        return int(self.rolled_speed * speed_bonus)

    @property
    def effective_energy(self) -> int:
        energy_bonus = 1.0 + self.enhancement_level * 0.008 + self.evolution_stage * 0.04
        return int(self.rolled_energy * energy_bonus)

    @property
    def power(self) -> int:
        return (
            self.effective_attack
            + self.effective_defense
            + self.effective_hp // 8
            + self.level * 6
            + self.skill_level * 10
            + self.grade * 14
            + self.enhancement_level * 12
            + self.evolution_stage * 65
            + (40 if self.awakened else 0)
        )


@dataclass(slots=True)
class PlayerProfile:
    player_id: int
    user_id: int
    coins: int
    crystals: int
    stamina: int
    max_stamina: int
    pity_counter: int
    daily_streak: int
    last_daily_at: datetime | None
    rank_points: int
    training_scrolls: int
    grade_seals: int
    skill_scrolls: int
    story_stage: int
    last_stamina_at: datetime


@dataclass(slots=True)
class BattleLog:
    winner: str
    rounds: list[str] = field(default_factory=list)
    rewards: dict[str, int] = field(default_factory=dict)
    snapshots: list["BattleSnapshot"] = field(default_factory=list)


@dataclass(slots=True)
class BattleUnitState:
    name: str
    image_url: str
    rarity: str
    level: int
    evolution_stage: int
    hp: int
    max_hp: int
    energy: int
    max_energy: int
    skill_level: int
    passive: str
    status: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class BattleSnapshot:
    round_number: int
    actor_team: str
    actor_name: str
    target_name: str
    action_name: str
    detail: str
    left_team: list[BattleUnitState] = field(default_factory=list)
    right_team: list[BattleUnitState] = field(default_factory=list)
