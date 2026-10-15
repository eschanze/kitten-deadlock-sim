from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, NamedTuple, Optional

if TYPE_CHECKING:
    from sim import Hero


class EffectType(Enum):
    WEAPON_DAMAGE = "weapon damage"
    FLAT_DAMAGE = "flat damage"
    FIRE_RATE = "fire rate"
    CURRENT_AMMO = "current ammo"


class Effect(NamedTuple):
    type: EffectType
    value: float
    duration: float = 0.0  # seconds, 0 means it only applies to the current bullet


class Category(Enum):
    WEAPON = "weapon"


# weapon items also grant extra weapon damage depending on the total souls spent on them (not on each item's tier)
# (total weapon souls, accumulative weapon damage), e.g. owning 3200 souls of weapon items => +18%
WEAPON_INVESTMENT_BONUS = [
    (800, 0.09), (1600, 0.12), (2400, 0.15), (3200, 0.18), (4800, 0.46), (6400, 0.54),
    (8000, 0.62), (11200, 0.74), (16000, 0.86), (22400, 1.00), (28800, 1.15),
]

# long range items only work against targets at least this far away, close range ones at most this far (meters)
LONG_RANGE_DISTANCE = 15
CLOSE_RANGE_DISTANCE = 15


def weapon_investment_bonus(weapon_souls: int) -> float:
    reached = [bonus for threshold, bonus in WEAPON_INVESTMENT_BONUS if weapon_souls >= threshold]
    return reached[-1] if reached else 0.0


@dataclass(eq=False)
class Item:
    name: str
    category: Category
    tier: int
    souls: int

    # stats, as fractional increases (0.2 => +20%)
    weapon_damage: float = 0.0
    fire_rate: float = 0.0
    ammo: float = 0.0
    health: float = 0.0  # flat bonus health
    falloff_range: float = 0.0  # applies to both ends of the hero's falloff range
    bullet_resist_reduction: float = 0.0  # applied to the enemy

    # conditional effects, checked on every bullet
    on_hit: Optional[Callable[[Hero, Hero, Item, float], Optional[Effect]]] = None
    cooldown: float = 0.0  # seconds
    last_triggered: Optional[float] = None

    # active abilities, assumed to be used right as the fight starts
    active: Optional[Callable[[], list[Effect]]] = None

    def is_ready(self, current_time: float) -> bool:
        return self.last_triggered is None or current_time - self.last_triggered >= self.cooldown


### Weapon items
# Only passive stats and effects that matter when shooting a target dummy are modeled. Skipped for now:
# actives, spirit damage, mobility, melee, and items that need the target to fight back or crit.

## Tier 1

# Close Quarters: +20% weapon damage within 15m
def close_quarters_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if attacker.distance_to_target <= CLOSE_RANGE_DISTANCE:
        return Effect(EffectType.WEAPON_DAMAGE, 0.2)
    return None


close_quarters = Item(
    name="Close Quarters",
    category=Category.WEAPON,
    tier=1,
    souls=800,
    on_hit=close_quarters_on_hit,
)

# Extended Magazine
extended_magazine = Item(
    name="Extended Magazine",
    category=Category.WEAPON,
    tier=1,
    souls=800,
    weapon_damage=0.08,
    ammo=0.30,
)


# Headshot Booster: +45 bonus damage, every 9 seconds
def headshot_booster_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if not item.is_ready(current_time):
        return None
    item.last_triggered = current_time
    return Effect(EffectType.FLAT_DAMAGE, 45)


headshot_booster = Item(
    name="Headshot Booster",
    category=Category.WEAPON,
    tier=1,
    souls=800,
    health=30,
    on_hit=headshot_booster_on_hit,
    cooldown=9.0,
)

# High-Velocity Rounds
high_velocity_rounds = Item(
    name="High-Velocity Rounds",
    category=Category.WEAPON,
    tier=1,
    souls=800,
    weapon_damage=0.08,
)

# Rapid Rounds
rapid_rounds = Item(
    name="Rapid Rounds",
    category=Category.WEAPON,
    tier=1,
    souls=800,
    fire_rate=0.09,
)

# Restorative Shot
restorative_shot = Item(
    name="Restorative Shot",
    category=Category.WEAPON,
    tier=1,
    souls=800,
    weapon_damage=0.06,
)

## Tier 2


# Intensifying Magazine: weapon damage ramps up to +45% over 2.5 seconds of continuous fire
def intensifying_magazine_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    max_bonus = 0.45
    ramp_up_time = 2.5

    # last_triggered marks when the ramp up started
    if item.last_triggered is None:
        item.last_triggered = current_time

    time_firing = current_time - item.last_triggered
    bonus = min(max_bonus * time_firing / ramp_up_time, max_bonus)
    return Effect(EffectType.WEAPON_DAMAGE, bonus)


intensifying_magazine = Item(
    name="Intensifying Magazine",
    category=Category.WEAPON,
    tier=2,
    souls=1600,
    ammo=0.2,
    on_hit=intensifying_magazine_on_hit,
)


# Long Range: +40% weapon damage against distant targets
def long_range_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if attacker.distance_to_target >= LONG_RANGE_DISTANCE:
        return Effect(EffectType.WEAPON_DAMAGE, 0.4)
    return None


long_range = Item(
    name="Long Range",
    category=Category.WEAPON,
    tier=2,
    souls=1600,
    falloff_range=0.08,
    on_hit=long_range_on_hit,
)


# Opening Rounds: +25% weapon damage while the enemy is above 50% health
def opening_rounds_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if defender.health / defender.base_health > 0.5:
        return Effect(EffectType.WEAPON_DAMAGE, 0.25)
    return None


opening_rounds = Item(
    name="Opening Rounds",
    category=Category.WEAPON,
    tier=2,
    souls=1600,
    weapon_damage=0.08,
    on_hit=opening_rounds_on_hit,
)

# Recharging Rush
recharging_rush = Item(
    name="Recharging Rush",
    category=Category.WEAPON,
    tier=2,
    souls=1600,
    weapon_damage=0.10,
    ammo=0.2,
)

# Swift Striker
swift_striker = Item(
    name="Swift Striker",
    category=Category.WEAPON,
    tier=2,
    souls=1600,
    fire_rate=0.20,
)

# Titanic Magazine
titanic_magazine = Item(
    name="Titanic Magazine",
    category=Category.WEAPON,
    tier=2,
    souls=1600,
    weapon_damage=0.14,
    ammo=1.0,
)

# Weakening Headshot: -12% bullet resist on the target
weakening_headshot = Item(
    name="Weakening Headshot",
    category=Category.WEAPON,
    tier=2,
    souls=1600,
    health=60,
    bullet_resist_reduction=0.12,
)

## Tier 3


# Burst Fire: +32% fire rate for 4.5 seconds, every 9 seconds
def burst_fire_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if not item.is_ready(current_time):
        return None
    item.last_triggered = current_time
    return Effect(EffectType.FIRE_RATE, 0.32, duration=4.5)


burst_fire = Item(
    name="Burst Fire",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    fire_rate=0.10,
    on_hit=burst_fire_on_hit,
    cooldown=9.0,
)

# Escalating Resilience
escalating_resilience = Item(
    name="Escalating Resilience",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    weapon_damage=0.18,
    ammo=0.35,
    health=75,
)


# Headhunter: +75 bonus damage, every 8 seconds
def headhunter_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if not item.is_ready(current_time):
        return None
    item.last_triggered = current_time
    return Effect(EffectType.FLAT_DAMAGE, 75)


headhunter = Item(
    name="Headhunter",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    weapon_damage=0.05,
    health=50,
    on_hit=headhunter_on_hit,
    cooldown=8.0,
)


# Hollow Point: +35% weapon damage while above 65% health, and bullets reduce the target's bullet resist by 10%
def hollow_point_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if attacker.health / attacker.base_health > 0.65:
        return Effect(EffectType.WEAPON_DAMAGE, 0.35)
    return None


hollow_point = Item(
    name="Hollow Point",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    health=125,
    # the debuff lasts 8s and is refreshed by every bullet, so it is always on while firing
    bullet_resist_reduction=0.10,
    on_hit=hollow_point_on_hit,
)


# Point Blank: +50% weapon damage within 15m
def point_blank_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if attacker.distance_to_target <= CLOSE_RANGE_DISTANCE:
        return Effect(EffectType.WEAPON_DAMAGE, 0.5)
    return None


point_blank = Item(
    name="Point Blank",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    health=75,
    on_hit=point_blank_on_hit,
)


# Sharpshooter: +60% weapon damage against distant targets
def sharpshooter_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if attacker.distance_to_target >= LONG_RANGE_DISTANCE:
        return Effect(EffectType.WEAPON_DAMAGE, 0.6)
    return None


sharpshooter = Item(
    name="Sharpshooter",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    weapon_damage=0.10,
    falloff_range=0.20,
    on_hit=sharpshooter_on_hit,
)

# Weighted Shots
weighted_shots = Item(
    name="Weighted Shots",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    weapon_damage=0.30,
)

## Tier 4

# Crippling Headshot
crippling_headshot = Item(
    name="Crippling Headshot",
    category=Category.WEAPON,
    tier=4,
    souls=6400,
    health=125,
    bullet_resist_reduction=0.16,
)

# Frenzy (its low health passive is not modeled)
frenzy = Item(
    name="Frenzy",
    category=Category.WEAPON,
    tier=4,
    souls=6400,
    fire_rate=0.15,
    health=160,
)

# Glass Cannon (its max health penalty and kill stacks are not modeled)
glass_cannon = Item(
    name="Glass Cannon",
    category=Category.WEAPON,
    tier=4,
    souls=6400,
    weapon_damage=0.8,
)

# Ricochet (the bounces only matter with more than one target)
ricochet = Item(
    name="Ricochet",
    category=Category.WEAPON,
    tier=4,
    souls=6400,
    fire_rate=0.18,
)


ALL_ITEMS = [
    close_quarters, extended_magazine, headshot_booster, high_velocity_rounds, rapid_rounds, restorative_shot,
    intensifying_magazine, long_range, opening_rounds, recharging_rush, swift_striker, titanic_magazine,
    weakening_headshot,
    burst_fire, escalating_resilience, headhunter, hollow_point, point_blank, sharpshooter, weighted_shots,
    crippling_headshot, frenzy, glass_cannon, ricochet,
]

# upgrade items consume their components, so owning both makes no sense
INCOMPATIBLE_PAIRS = [
    (extended_magazine, titanic_magazine), (extended_magazine, escalating_resilience),
    (rapid_rounds, swift_striker), (rapid_rounds, burst_fire),
    (headshot_booster, headhunter),
    (close_quarters, point_blank),
    (high_velocity_rounds, opening_rounds), (high_velocity_rounds, sharpshooter),
    (long_range, sharpshooter),
    (weakening_headshot, crippling_headshot),
]


def has_component_conflict(build: list[Item]) -> bool:
    return any(first in build and second in build for first, second in INCOMPATIBLE_PAIRS)
