from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, Any

class EffectType(Enum):
    WeaponDamageMultiplier = "WeaponDamageMultiplier"
    BonusFlatDamage = "BonusFlatDamage"
    FireRateBuff = "FireRateBuff"
    # etc...

@dataclass
class Item:
    type: str
    name: str
    ## Stats
    # Weapon
    weapon_damage: float = 0.0 # Weapon Damage as % increase
    fire_rate: float = 0.0 # Fire Rate as % increase
    ammo: float = 0.0 # Ammo as % increase
    # Vitality
    health: float = 0.0
    # Spirit
    spirit: int = 0
    # Callbacks
    on_hit: callable = None  # Function for on-hit effects
    on_damage: callable = None  # Function for on-damage effects
    # Timers
    cooldown: float = 0.0  # Cooldown duration for passive effects
    last_triggered: float = field(default=None)  # Last time the effect was triggered

## Tier 1 items

# Basic Magazine
basic_magazine = Item(
    type="Weapon",
    name="Basic Magazine",
    weapon_damage=(0.15+0.06),
    ammo=0.24
)

# Headshot Booster: adds +40 damage every 7 seconds
def headshot_booster_on_hit(attacker, defender, item, current_time):
    cooldown_time = item.cooldown
    bonus_damage = 40

    if item.last_triggered is None or (current_time - item.last_triggered >= cooldown_time):
        item.last_triggered = current_time
        print(f"[ BONUS ] Headshot Booster: +{bonus_damage} bonus damage!")
        return (EffectType.BonusFlatDamage, bonus_damage)
    return (EffectType.BonusFlatDamage, 0)

headshot_booster = Item(
    type="Weapon",
    name="Headshot Booster",
    weapon_damage=0.06,
    fire_rate=0.05,
    on_hit=headshot_booster_on_hit,
    cooldown=7.0
)

# High-Velocity Mag
high_velocity_mag = Item(
    type="Weapon",
    name="High-Velocity Mag",
    weapon_damage=(0.14+0.06)
)

# Hollow Point Ward
def hollow_point_ward_on_hit(attacker, defender, item, current_time):
    bonus_percentage = 0.2
    health_threshold = 0.6

    if attacker.health / attacker.base_health > health_threshold:
        print(f"[ BONUS ] Hollow Point Ward: +{int(bonus_percentage * 100.0)}% weapon damage")
        return (EffectType.WeaponDamageMultiplier, bonus_percentage)
    return (EffectType.WeaponDamageMultiplier, 0.0)

hollow_point_ward = Item(
    type="Weapon",
    name="Hollow Point Ward",
    weapon_damage=0.06,
    on_hit=hollow_point_ward_on_hit
)

# Rapid Rounds
rapid_rounds = Item(
    type="Weapon",
    name="Rapid Rounds",
    weapon_damage=0.06,
    fire_rate=0.09
)

# Restorative Shot
restorative_shot = Item(
    type="Weapon",
    name="Restorative Shot",
    weapon_damage=(0.08+0.06)
)

## Tier 2 items

# Active Reload

# Kinetic Dash

# Long Range
long_range = Item(
    type="Weapon",
    name="Long Range",
    weapon_damage=(0.4+0.1),
    ammo=0.2
)

# Mystic Shot

# Slowing Bullets

# Soul Shredder Bullets 

# Swift Striker
swift_striker = Item(
    type="Weapon",
    name="Swift Striker",
    weapon_damage=0.1,
    fire_rate=0.22,
    ammo=0.1
)

# Fleetfoot

## Tier 3 items

# Burst Fire: increase fire rate by 30% for 4 seconds, every 8 seconds
def burst_fire_on_hit(attacker, defender, item, current_time):
    cooldown_time = 8.0
    buff_duration = 4.0
    fire_rate_increase = 0.30

    if item.last_triggered is None or (current_time - item.last_triggered >= cooldown_time):
        item.last_triggered = current_time
        print(f"[ BONUS ] Burst Fire: +{int(fire_rate_increase * 100)}% fire rate for {buff_duration} seconds!")
        return (EffectType.FireRateBuff, fire_rate_increase, buff_duration)
    return (EffectType.FireRateBuff, 0, 0)

burst_fire = Item(
    type="Weapon",
    name="Burst Fire",
    on_hit=burst_fire_on_hit,
    weapon_damage=0.14,
    fire_rate=0.12,
    cooldown=8.0
)

# Escalating Resilience

# Headhunter

# Intensifying Magazine: increases damage by up to 75% over 3 seconds
def intensifying_magazine_on_hit(attacker, defender, item, current_time):
    max_increase = 0.75
    ramp_up_time = 3.0

    if item.last_triggered is None:
        item.last_triggered = current_time

    time_elapsed = current_time - item.last_triggered
    damage_multiplier = min(1 + (max_increase * time_elapsed / ramp_up_time), 1 + max_increase)

    print(f"[ BONUS ] Increasing Magazine: +{int((damage_multiplier - 1) * 100.0)}% weapon damage")
    return (EffectType.WeaponDamageMultiplier, damage_multiplier - 1)

intensifying_magazine = Item(
    type="Weapon",
    name="Increasing Magazine",
    weapon_damage=(0.2 + 0.14),
    ammo=0.25,
    on_hit=intensifying_magazine_on_hit
)

# Pristine Emblem: +25% weapon damage if enemy has >50% health
def pristine_emblem_on_hit(attacker, defender, item, current_time):
    bonus_percentage = 0.25
    health_threshold = 0.5

    if defender.health / defender.base_health > health_threshold:
        print(f"[ BONUS ] Pristine Emblem: +{int(bonus_percentage * 100.0)}% weapon damage")
        return (EffectType.WeaponDamageMultiplier, bonus_percentage)
    return (EffectType.WeaponDamageMultiplier, 0.0)

pristine_emblem = Item(
    type="Weapon",
    name="Pristine Emblem",
    weapon_damage=(0.25 + 0.14),
    on_hit=pristine_emblem_on_hit
)

# Sharpshooter

# Titanic Magazine

# Alchemical Fire

# Warp Stone

## Tier 4 items