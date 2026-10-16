from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from math import inf
from typing import TYPE_CHECKING, NamedTuple, Optional, Union

if TYPE_CHECKING:
    from sim import Hero


class EffectType(Enum):
    # only change the current bullet
    WEAPON_DAMAGE = "weapon damage"
    FLAT_DAMAGE = "flat damage"
    DAMAGE_MULTIPLIER = "damage multiplier"  # applied after everything else, 1.0 => double damage
    AMMO_COST = "ammo cost"  # extra bullets taken from the magazine

    # buffs on the attacker
    FIRE_RATE = "fire rate"
    CURRENT_AMMO = "current ammo"
    BONUS_AMMO = "bonus ammo"  # flat bullets added to the magazine in hand
    HEALTH_DRAIN = "health drain"  # per second, for the rest of the fight

    # spirit damage ignores falloff and bullet resist
    SPIRIT_DAMAGE = "spirit damage"
    SPIRIT_DOT = "spirit damage over time"  # value is per second, reapplying it refreshes the duration

    # debuffs on the defender, reapplying one refreshes it instead of stacking
    BULLET_RESIST_REDUCTION = "bullet resist reduction"
    SPIRIT_RESIST_REDUCTION = "spirit resist reduction"


class Effect(NamedTuple):
    type: EffectType
    value: float
    duration: float = 0.0  # seconds, 0 means it only applies to the current bullet
    until_reload: bool = False  # buffs that also end on the next reload


# what an item's on hit callback returns
OnHitResult = Union[Effect, list[Effect], None]


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
STALKER_RANGE = 8
HUNTERS_AURA_RADIUS = 15

# Weakening Headshot and Crippling Headshot debuff the target for this long after a headshot (seconds)
HEADSHOT_DEBUFF_DURATION = 12.0


def weapon_investment_bonus(weapon_souls: int) -> float:
    reached = [bonus for threshold, bonus in WEAPON_INVESTMENT_BONUS if weapon_souls >= threshold]
    return reached[-1] if reached else 0.0


def proc(item: Item, chance: float) -> bool:
    # chance procs fire on a fixed rhythm instead of randomly, so builds rank the same on every run
    # e.g. 25% => every 4th bullet
    item.charge = round(item.charge + chance, 9)
    if item.charge < 1:
        return False
    item.charge -= 1
    return True


def build_up(attacker: Hero, item: Item, build_up_per_shot: float) -> bool:
    # deadlock.wiki/Module:Buildup => each bullet adds 100 / (build up per shot * (rounds per second + 1)) percent,
    # and falloff lowers it at range, e.g. toxic bullets on vindicta => 14.7% per bullet up close, 7 bullets to proc
    item.charge += 100 / (build_up_per_shot * (attacker.base_fire_rate + 1)) * attacker.falloff_multiplier()
    if item.charge < 100:
        return False
    item.charge = 0.0
    return True


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
    spirit_resist_reduction: float = 0.0  # applied to the enemy

    # conditional effects, checked on every bullet
    on_hit: Optional[Callable[[Hero, Hero, Item, float], OnHitResult]] = None
    on_reload: Optional[Callable[[Hero, Item, float], list[Effect]]] = None
    cooldown: float = 0.0  # seconds
    last_triggered: Optional[float] = None
    charge: float = 0.0  # build up or proc chance accumulated so far

    # active abilities, assumed to be used right as the fight starts
    active: Optional[Callable[[], list[Effect]]] = None

    def is_ready(self, current_time: float) -> bool:
        return self.last_triggered is None or current_time - self.last_triggered >= self.cooldown

    def reset(self) -> None:
        self.last_triggered = None
        self.charge = 0.0


### Weapon items
# Only effects that matter when shooting a target dummy are modeled. Skipped: mobility, melee, healing, spirit power
# scaling, and items that need the target to fight back or other targets around (see the README).

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


# Headshot Booster: +45 bonus damage on a headshot, every 9 seconds
def headshot_booster_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if not attacker.headshot or not item.is_ready(current_time):
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


# Active Reload: +25% fire rate for 7 seconds after a reload, every 12 seconds
# (assumes every reload is an active one, but the reload isn't shortened since the window's timing isn't known)
def active_reload_on_reload(attacker: Hero, item: Item, current_time: float) -> list[Effect]:
    if not item.is_ready(current_time):
        return []
    item.last_triggered = current_time
    return [Effect(EffectType.FIRE_RATE, 0.25, duration=7.0)]


active_reload = Item(
    name="Active Reload",
    category=Category.WEAPON,
    tier=2,
    souls=1600,
    ammo=0.2,
    on_reload=active_reload_on_reload,
    cooldown=12.0,
)

# Fleetfoot (its active is mobility only)
fleetfoot = Item(
    name="Fleetfoot",
    category=Category.WEAPON,
    tier=2,
    souls=1600,
    weapon_damage=0.06,
)


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


def intensifying_magazine_on_reload(attacker: Hero, item: Item, current_time: float) -> list[Effect]:
    # it ramps up while firing continuously, so the bonus restarts after a reload
    item.last_triggered = None
    return []


intensifying_magazine = Item(
    name="Intensifying Magazine",
    category=Category.WEAPON,
    tier=2,
    souls=1600,
    ammo=0.2,
    on_hit=intensifying_magazine_on_hit,
    on_reload=intensifying_magazine_on_reload,
)


# Kinetic Dash: +25% fire rate and +6 bullets until the next reload (up to 7 seconds) after a dash-jump
# (a passive, but dash-jumping into the fight is treated like an active used at the start)
def kinetic_dash_active() -> list[Effect]:
    return [Effect(EffectType.FIRE_RATE, 0.25, duration=7.0, until_reload=True), Effect(EffectType.BONUS_AMMO, 6)]


kinetic_dash = Item(
    name="Kinetic Dash",
    category=Category.WEAPON,
    tier=2,
    souls=1600,
    active=kinetic_dash_active,
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


# Mystic Shot: +40 spirit damage, every 8 seconds
def mystic_shot_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> OnHitResult:
    if not item.is_ready(current_time):
        return None
    item.last_triggered = current_time
    return Effect(EffectType.SPIRIT_DAMAGE, 40)


mystic_shot = Item(
    name="Mystic Shot",
    category=Category.WEAPON,
    tier=2,
    souls=1600,
    on_hit=mystic_shot_on_hit,
    cooldown=8.0,
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

# Spirit Shredder: -8% spirit resist on the target
spirit_shredder = Item(
    name="Spirit Shredder",
    category=Category.WEAPON,
    tier=2,
    souls=1600,
    # the debuff lasts 8s and is refreshed by every bullet, so it is always on while firing
    spirit_resist_reduction=0.08,
)


# Stalker: within 8m, a wound that deals 17 spirit damage per second and takes 6% bullet resist for 5 seconds,
# every 6 seconds
def stalker_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> OnHitResult:
    if attacker.distance_to_target > STALKER_RANGE or not item.is_ready(current_time):
        return None
    item.last_triggered = current_time
    return [
        Effect(EffectType.SPIRIT_DOT, 17, duration=5.0),
        Effect(EffectType.BULLET_RESIST_REDUCTION, 0.06, duration=5.0),
    ]


stalker = Item(
    name="Stalker",
    category=Category.WEAPON,
    tier=2,
    souls=1600,
    health=50,
    on_hit=stalker_on_hit,
    cooldown=6.0,
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

# Weakening Headshot: headshots take 12% bullet resist for 12 seconds
def weakening_headshot_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> OnHitResult:
    if not attacker.headshot:
        return None
    return Effect(EffectType.BULLET_RESIST_REDUCTION, 0.12, duration=HEADSHOT_DEBUFF_DURATION)


weakening_headshot = Item(
    name="Weakening Headshot",
    category=Category.WEAPON,
    tier=2,
    souls=1600,
    health=60,
    on_hit=weakening_headshot_on_hit,
)

## Tier 3


# Alchemical Fire: a pool that deals spirit damage and takes 7% bullet resist for 5 seconds
def alchemical_fire_active() -> list[Effect]:
    # its 45 dps ramps up by 7 every second, so this is the average over the 5 seconds
    return [
        Effect(EffectType.SPIRIT_DOT, 45 + 7 * 5 / 2, duration=5.0),
        Effect(EffectType.BULLET_RESIST_REDUCTION, 0.07, duration=5.0),
    ]


alchemical_fire = Item(
    name="Alchemical Fire",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    active=alchemical_fire_active,
)


# Blood Tribute: a toggle for +35% fire rate that costs 50 health per second
def blood_tribute_active() -> list[Effect]:
    return [Effect(EffectType.FIRE_RATE, 0.35, duration=inf), Effect(EffectType.HEALTH_DRAIN, 50)]


blood_tribute = Item(
    name="Blood Tribute",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    active=blood_tribute_active,
)


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

# Cultist Sacrifice (assumes an NPC was consumed before the fight, its buff lasts 160s)
cultist_sacrifice = Item(
    name="Cultist Sacrifice",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    weapon_damage=0.10,
    health=50,
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


# Express Shot: every 8 seconds, the next attack fires 2 bullets with +125% weapon damage, using 2 ammo
def express_shot_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> OnHitResult:
    # current ammo is already down by this bullet, so the second one needs one more left
    if not item.is_ready(current_time) or attacker.current_ammo < 1:
        return None
    item.last_triggered = current_time
    return [
        Effect(EffectType.WEAPON_DAMAGE, 1.25),
        Effect(EffectType.DAMAGE_MULTIPLIER, 1.0),
        Effect(EffectType.AMMO_COST, 1),
    ]


express_shot = Item(
    name="Express Shot",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    weapon_damage=0.08,
    on_hit=express_shot_on_hit,
    cooldown=8.0,
)


# Headhunter: +75 bonus damage on a headshot, every 8 seconds
def headhunter_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> Optional[Effect]:
    if not attacker.headshot or not item.is_ready(current_time):
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


# Heroic Aura: +26% fire rate for 7 seconds (its bullet resist only matters when getting shot)
def heroic_aura_active() -> list[Effect]:
    return [Effect(EffectType.FIRE_RATE, 0.26, duration=7.0)]


heroic_aura = Item(
    name="Heroic Aura",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    active=heroic_aura_active,
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


# Hunter's Aura: -20% bullet resist on the target within 15m (10%, doubled when it's the only enemy hero around)
def hunters_aura_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> OnHitResult:
    if attacker.distance_to_target <= HUNTERS_AURA_RADIUS:
        return Effect(EffectType.BULLET_RESIST_REDUCTION, 0.2, duration=inf)
    return None


hunters_aura = Item(
    name="Hunter's Aura",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    health=100,
    on_hit=hunters_aura_on_hit,
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


# Shadow Weave: +25% fire rate for 5 seconds, from the ambush when leaving stealth
def shadow_weave_active() -> list[Effect]:
    return [Effect(EffectType.FIRE_RATE, 0.25, duration=5.0)]


shadow_weave = Item(
    name="Shadow Weave",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    active=shadow_weave_active,
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

SPIRIT_REND_STACK_DURATION = 8.0
SPIRIT_REND_MAX_STACKS = 4


# Spirit Rend: -8% spirit resist on the target, and headshots add a stack of -7% spirit resist for 8 seconds
# (up to 4 stacks, one every 2 seconds)
def spirit_rend_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> OnHitResult:
    if not attacker.headshot or not item.is_ready(current_time):
        return None
    # each new stack refreshes all of them, so they only drop off together
    stacked = item.last_triggered is not None and current_time - item.last_triggered <= SPIRIT_REND_STACK_DURATION
    item.charge = min(item.charge + 1, SPIRIT_REND_MAX_STACKS) if stacked else 1
    item.last_triggered = current_time
    # stacks multiply, e.g. 4 stacks => 1 - 0.93^4 => -25% spirit resist
    return Effect(EffectType.SPIRIT_RESIST_REDUCTION, 1 - 0.93 ** item.charge, duration=SPIRIT_REND_STACK_DURATION)


spirit_rend = Item(
    name="Spirit Rend",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    health=75,
    # the debuff lasts 8s and is refreshed by every bullet, so it is always on while firing
    spirit_resist_reduction=0.08,
    on_hit=spirit_rend_on_hit,
    cooldown=2.0,
)


# Tesla Bullets: 15% chance for +33 spirit damage (the chain only matters with more than one target)
def tesla_bullets_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> OnHitResult:
    if proc(item, 0.15):
        return Effect(EffectType.SPIRIT_DAMAGE, 33)
    return None


tesla_bullets = Item(
    name="Tesla Bullets",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    on_hit=tesla_bullets_on_hit,
)

TOXIC_BLEED_DURATION = 4.0


# Toxic Bullets: bullets build up a bleed that deals 1.9% of the target's max health per second for 4 seconds
def toxic_bullets_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> OnHitResult:
    # bullets on a bleeding target refresh the bleed instead of building it up again
    bleeding = item.last_triggered is not None and current_time - item.last_triggered <= TOXIC_BLEED_DURATION
    if not bleeding and not build_up(attacker, item, 1.28):
        return None
    item.last_triggered = current_time
    return Effect(EffectType.SPIRIT_DOT, 0.019 * defender.max_health, duration=TOXIC_BLEED_DURATION)


toxic_bullets = Item(
    name="Toxic Bullets",
    category=Category.WEAPON,
    tier=3,
    souls=3200,
    on_hit=toxic_bullets_on_hit,
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

# Armor Piercer (its piercing bullets ignore bullet resist, and the dummy has none)
armor_piercer = Item(
    name="Armor Piercer",
    category=Category.WEAPON,
    tier=4,
    souls=6400,
    weapon_damage=0.08,
)


# Capacitor: 20% chance for +43 spirit damage, and its active deals 100 spirit damage
def capacitor_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> OnHitResult:
    if proc(item, 0.2):
        return Effect(EffectType.SPIRIT_DAMAGE, 43)
    return None


def capacitor_active() -> list[Effect]:
    return [Effect(EffectType.SPIRIT_DAMAGE, 100)]


capacitor = Item(
    name="Capacitor",
    category=Category.WEAPON,
    tier=4,
    souls=6400,
    fire_rate=0.05,
    on_hit=capacitor_on_hit,
    active=capacitor_active,
)

# Crippling Headshot: headshots take 16% bullet and spirit resist for 12 seconds
def crippling_headshot_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> OnHitResult:
    if not attacker.headshot:
        return None
    return [
        Effect(EffectType.BULLET_RESIST_REDUCTION, 0.16, duration=HEADSHOT_DEBUFF_DURATION),
        Effect(EffectType.SPIRIT_RESIST_REDUCTION, 0.16, duration=HEADSHOT_DEBUFF_DURATION),
    ]


crippling_headshot = Item(
    name="Crippling Headshot",
    category=Category.WEAPON,
    tier=4,
    souls=6400,
    health=125,
    on_hit=crippling_headshot_on_hit,
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

# Lucky Shot: 25% chance for a bullet to deal double damage
def lucky_shot_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> OnHitResult:
    if proc(item, 0.25):
        return Effect(EffectType.DAMAGE_MULTIPLIER, 1.0)
    return None


lucky_shot = Item(
    name="Lucky Shot",
    category=Category.WEAPON,
    tier=4,
    souls=6400,
    ammo=0.3,
    on_hit=lucky_shot_on_hit,
)

# Ricochet (the bounces only matter with more than one target)
ricochet = Item(
    name="Ricochet",
    category=Category.WEAPON,
    tier=4,
    souls=6400,
    fire_rate=0.18,
)

SPIRITUAL_OVERFLOW_DURATION = 15.0


# Spiritual Overflow: bullets build up +25% fire rate for 15 seconds
def spiritual_overflow_on_hit(attacker: Hero, defender: Hero, item: Item, current_time: float) -> OnHitResult:
    # it only builds up again once the buff is over
    active = item.last_triggered is not None and current_time - item.last_triggered < SPIRITUAL_OVERFLOW_DURATION
    if active or not build_up(attacker, item, 1.08):
        return None
    item.last_triggered = current_time
    return Effect(EffectType.FIRE_RATE, 0.25, duration=SPIRITUAL_OVERFLOW_DURATION)


spiritual_overflow = Item(
    name="Spiritual Overflow",
    category=Category.WEAPON,
    tier=4,
    souls=6400,
    health=90,
    on_hit=spiritual_overflow_on_hit,
)


ALL_ITEMS = [
    close_quarters, extended_magazine, headshot_booster, high_velocity_rounds, rapid_rounds, restorative_shot,
    active_reload, fleetfoot, intensifying_magazine, kinetic_dash, long_range, mystic_shot, opening_rounds,
    recharging_rush, spirit_shredder, stalker, swift_striker, titanic_magazine, weakening_headshot,
    alchemical_fire, blood_tribute, burst_fire, cultist_sacrifice, escalating_resilience, express_shot, headhunter,
    heroic_aura, hollow_point, hunters_aura, point_blank, shadow_weave, sharpshooter, spirit_rend, tesla_bullets,
    toxic_bullets, weighted_shots,
    armor_piercer, capacitor, crippling_headshot, frenzy, glass_cannon, lucky_shot, ricochet, spiritual_overflow,
]

# upgrade items consume their components, so owning both makes no sense
INCOMPATIBLE_PAIRS = [
    (extended_magazine, titanic_magazine), (extended_magazine, escalating_resilience),
    (rapid_rounds, swift_striker), (rapid_rounds, burst_fire),
    (headshot_booster, headhunter),
    (close_quarters, point_blank),
    (high_velocity_rounds, opening_rounds), (high_velocity_rounds, sharpshooter),
    (high_velocity_rounds, express_shot), (high_velocity_rounds, armor_piercer),
    (long_range, sharpshooter),
    (weakening_headshot, crippling_headshot),
    (spirit_shredder, spirit_rend),
    (tesla_bullets, capacitor),
]


def has_component_conflict(build: list[Item]) -> bool:
    return any(first in build and second in build for first, second in INCOMPATIBLE_PAIRS)
