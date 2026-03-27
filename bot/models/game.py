from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


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


@dataclass(slots=True)
class OwnedCharacter:
    instance_id: int
    player_id: int
    character_key: str
    level: int
    xp: int
    grade: int
    skill_level: int
    awakened: bool
    locked: bool
    acquired_at: datetime
    definition: CharacterDefinition

    @property
    def power(self) -> int:
        return (
            self.definition.base_attack
            + self.definition.base_defense
            + self.definition.base_hp // 8
            + self.level * 6
            + self.skill_level * 10
            + self.grade * 14
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
