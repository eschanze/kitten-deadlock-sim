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
    VITALITY = "vitality"


# weapon items grant extra weapon damage depending on their tier
WEAPON_TIER_BONUS = {1: 0.06, 2: 0.10, 3: 0.14, 4: 0.18}

# long range items only work against targets at least this far away (meters)
LONG_RANGE_DISTANCE = 15


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
    health: float = 0.0
    bullet_resist_reduction: float = 0.0  # applied to the enemy

    # conditional effects, checked on every bullet
    on_hit: Optional[Callable[[Hero, Hero, Item, float], Optional[Effect]]] = None
    cooldown: float = 0.0  # seconds
    last_triggered: Optional[float] = None

    # active abilities, assumed to be used right as the fight starts
    active: Optional[Callable[[], list[Effect]]] = None

    @property
    def total_weapon_damage(self) -> float:
        tier_bonus = WEAPON_TIER_BONUS[self.tier] if self.category == Category.WEAPON else 0.0
        return self.weapon_damage + tier_bonus

    def is_ready(self, current_time: float) -> bool:
        return self.last_triggered is None or current_time - self.last_triggered >= self.cooldown


### Weapon items

## Tier 1

# Basic Magazine
basic_magazine = Item(
    name="Basic Magazine",
    category=Category.WEAPON,
    tier=1,
    souls=500,
    weapon_damage=0.15,
    ammo=0.24,
)


# Headshot Booster: +40 bonus damage, every 7 seconds
def headshot_booster_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if not item.is_ready(current_time):
        return None
    item.last_triggered = current_time
    return Effect(EffectType.FLAT_DAMAGE, 40)


headshot_booster = Item(
    name="Headshot Booster",
    category=Category.WEAPON,
    tier=1,
    souls=500,
    fire_rate=0.05,
    on_hit=headshot_booster_on_hit,
    cooldown=7.0,
)

# High-Velocity Mag
high_velocity_mag = Item(
    name="High-Velocity Mag",
    category=Category.WEAPON,
    tier=1,
    souls=500,
    weapon_damage=0.14,
)


# Hollow Point Ward: +20% weapon damage while above 60% health
def hollow_point_ward_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if attacker.health / attacker.base_health > 0.6:
        return Effect(EffectType.WEAPON_DAMAGE, 0.2)
    return None


hollow_point_ward = Item(
    name="Hollow Point Ward",
    category=Category.WEAPON,
    tier=1,
    souls=500,
    on_hit=hollow_point_ward_on_hit,
)

# Rapid Rounds
rapid_rounds = Item(
    name="Rapid Rounds",
    category=Category.WEAPON,
    tier=1,
    souls=500,
    fire_rate=0.09,
)

# Restorative Shot
restorative_shot = Item(
    name="Restorative Shot",
    category=Category.WEAPON,
    tier=1,
    souls=500,
    weapon_damage=0.08,
)

## Tier 2



# Long Range: +40% weapon damage against distant targets
def long_range_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if attacker.distance_to_target >= LONG_RANGE_DISTANCE:
        return Effect(EffectType.WEAPON_DAMAGE, 0.4)
    return None


long_range = Item(
    name="Long Range",
    category=Category.WEAPON,
    tier=2,
    souls=1250,
    ammo=0.2,
    on_hit=long_range_on_hit,
)

# Swift Striker
swift_striker = Item(
    name="Swift Striker",
    category=Category.WEAPON,
    tier=2,
    souls=1250,
    fire_rate=0.22,
    ammo=0.1,
)

## Tier 3


# Burst Fire: +30% fire rate for 4 seconds, every 8 seconds
def burst_fire_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if not item.is_ready(current_time):
        return None
    item.last_triggered = current_time
    return Effect(EffectType.FIRE_RATE, 0.3, duration=4.0)


burst_fire = Item(
    name="Burst Fire",
    category=Category.WEAPON,
    tier=3,
    souls=3000,
    fire_rate=0.12,
    on_hit=burst_fire_on_hit,
    cooldown=8.0,
)


# Intensifying Magazine: weapon damage ramps up to +60% over 3 seconds of continuous fire
def intensifying_magazine_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    max_bonus = 0.6
    ramp_up_time = 3.0

    # last_triggered marks when the ramp up started
    if item.last_triggered is None:
        item.last_triggered = current_time

    time_firing = current_time - item.last_triggered
    bonus = min(max_bonus * time_firing / ramp_up_time, max_bonus)
    return Effect(EffectType.WEAPON_DAMAGE, bonus)


intensifying_magazine = Item(
    name="Intensifying Magazine",
    category=Category.WEAPON,
    tier=3,
    souls=3000,
    weapon_damage=0.2,
    ammo=0.25,
    on_hit=intensifying_magazine_on_hit,
)


# Pristine Emblem: +25% weapon damage while the enemy is above 50% health
def pristine_emblem_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if defender.health / defender.base_health > 0.5:
        return Effect(EffectType.WEAPON_DAMAGE, 0.25)
    return None


pristine_emblem = Item(
    name="Pristine Emblem",
    category=Category.WEAPON,
    tier=3,
    souls=3000,
    weapon_damage=0.25,
    on_hit=pristine_emblem_on_hit,
)


# Sharpshooter: +70% weapon damage against distant targets
def sharpshooter_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if attacker.distance_to_target >= LONG_RANGE_DISTANCE:
        return Effect(EffectType.WEAPON_DAMAGE, 0.7)
    return None


sharpshooter = Item(
    name="Sharpshooter",
    category=Category.WEAPON,
    tier=3,
    souls=4250,
    ammo=0.2,
    on_hit=sharpshooter_on_hit,
)

# Warp Stone
warp_stone = Item(
    name="Warp Stone",
    category=Category.WEAPON,
    tier=3,
    souls=3000,
    weapon_damage=0.2,
)

## Tier 4

# Crippling Headshot
crippling_headshot = Item(
    name="Crippling Headshot",
    category=Category.WEAPON,
    tier=4,
    souls=6200,
    weapon_damage=0.2,
    bullet_resist_reduction=0.24,
)

# Glass Cannon
glass_cannon = Item(
    name="Glass Cannon",
    category=Category.WEAPON,
    tier=4,
    souls=6200,
    weapon_damage=0.7,
    fire_rate=0.1,
)


# Vampiric Burst: +40% fire rate and +50% current ammo for 4.5 seconds
def vampiric_burst_active() -> list[Effect]:
    return [
        Effect(EffectType.FIRE_RATE, 0.4, duration=4.5),
        Effect(EffectType.CURRENT_AMMO, 0.5, duration=4.5),
    ]


vampiric_burst = Item(
    name="Vampiric Burst",
    category=Category.WEAPON,
    tier=4,
    souls=6200,
    weapon_damage=0.25,
    active=vampiric_burst_active,
)

### Vitality items

## Tier 2

# Combat Barrier
combat_barrier = Item(
    name="Combat Barrier",
    category=Category.VITALITY,
    tier=2,
    souls=1250,
    weapon_damage=0.28,
    fire_rate=0.08,
)


ALL_ITEMS = [
    basic_magazine, headshot_booster, high_velocity_mag, hollow_point_ward, rapid_rounds, restorative_shot,
    long_range, swift_striker,
    burst_fire, intensifying_magazine, pristine_emblem, sharpshooter, warp_stone,
    crippling_headshot, glass_cannon, vampiric_burst,
    combat_barrier,
]
