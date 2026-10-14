from dataclasses import dataclass, field
from typing import List, Tuple
from event import Event, EventQueue
from items import *

@dataclass
class Buff:
    effect_type: EffectType
    value: float
    end_time: float

@dataclass
class Hero:
    name: str
    base_health: float
    base_bullet_damage: float
    base_fire_rate: float
    base_ammo: int
    min_range: float
    max_range: float
    build: list[Item] = field(default_factory=list) 
    bullet_resist_sources: List[float] = field(default_factory=list)
    base_reload_time: float = 0.0 # seconds

    def __post_init__(self):
        self.health = self.base_health + sum(item.health for item in self.build)
        self.weapon_damage_multiplier = sum(item.weapon_damage for item in self.build)
        self.bullet_damage = self.base_bullet_damage
        self.fire_rate = self.base_fire_rate * (1 + sum(item.fire_rate for item in self.build))
        self.ammo = int(round(self.base_ammo * (1 + sum(item.ammo for item in self.build))))
        self.current_ammo = self.ammo
        self.active_buffs: List[Buff] = []

        self.distance_to_target = 0 # meters

    def calculate_bullet_resist(self):
        positives = [r for r in self.bullet_resist_sources if r >= 0]
        negatives = [r for r in self.bullet_resist_sources if r < 0]
        
        positive_resist = 1 - self._prod(1 - r for r in positives)
        
        if negatives:
            negative_resist = 1 - self._prod(1 - abs(r) for r in negatives)
            return positive_resist - negative_resist
        else:
            return positive_resist

    @staticmethod
    def _prod(iterable):
        result = 1
        for x in iterable:
            result *= x
        return result

    def apply_buff(self, effect_type: EffectType, value: float, duration: float, current_time: float):
        if value > 0 and duration > 0:
            end_time = current_time + duration
            self.active_buffs.append(Buff(effect_type, value, end_time))
            return end_time, Buff(effect_type, value, end_time)
        return None, None

    def remove_buff(self, buff: Buff):
        self.active_buffs.remove(buff)

    def get_current_fire_rate(self) -> float:
        item_fire_rate_bonus = sum(item.fire_rate for item in self.build)
        active_fire_rate_buffs = sum(buff.value for buff in self.active_buffs if buff.effect_type == EffectType.FireRateBuff)
        return self.base_fire_rate * (1 + item_fire_rate_bonus + active_fire_rate_buffs)

@dataclass
class CombatStats:
    total_damage_dealt: float = 0.0
    total_attacks: int = 0
    dps: float = 0.0

class CombatSimulator:
    def __init__(self, attacker: Hero, defender: Hero, distance_to_target: float=30, fight_duration: float=10.0):
        self.attacker = attacker
        self.defender = defender
        self.event_queue = EventQueue()
        self.current_time = 0.0
        self.stats = CombatStats()
        # fixed window (instead of a single magazine) so reloads cost time and big-ammo builds are compared fairly
        self.fight_duration = fight_duration

        # items are shared module-level objects, so clear timers left over from previous simulations
        for item in self.attacker.build:
            item.last_triggered = None

        self.distance_to_target = distance_to_target # meters
        self.attacker.distance_to_target = self.distance_to_target

    def schedule_attack(self, time: float):
        self.event_queue.schedule_event(Event(time, self.attack))

    def attack(self):
        self.attacker.current_ammo -= 1
        print(f"[ {self.current_time:>{5}.2f} ][ ATTACK ] {self.attacker.name} -> {self.defender.name} ( {self.attacker.current_ammo}/{self.attacker.ammo} )")
        damage_time = self.current_time + 0.0 # Travel time
        self.event_queue.schedule_event(Event(damage_time, self.on_damage))
        if self.attacker.current_ammo > 0:
            next_attack_time = self.current_time + (1 / self.attacker.get_current_fire_rate())
            self.schedule_attack(next_attack_time)
        else:
            self.event_queue.schedule_event(Event(self.current_time + self.attacker.base_reload_time, self.reload))

    def reload(self):
        self.attacker.current_ammo = self.attacker.ammo
        print(f"[ {self.current_time:>{5}.2f} ][ RELOAD ] {self.attacker.name} ( {self.attacker.current_ammo}/{self.attacker.ammo} )")
        # intensifying magazine ramps up while firing continuously, so the bonus restarts after a reload
        if intensifying_magazine in self.attacker.build:
            intensifying_magazine.last_triggered = None
        self.schedule_attack(self.current_time)

    def on_damage(self):
        total_multiplier = 1.0 + self.attacker.weapon_damage_multiplier
        flat_damage = 0

        for item in self.attacker.build:
            if item.on_hit:
                effect = item.on_hit(self.attacker, self.defender, item, self.current_time)
                if effect[0] == EffectType.WeaponDamageMultiplier:
                    total_multiplier += effect[1]
                elif effect[0] == EffectType.BonusFlatDamage:
                    flat_damage += effect[1]
                elif effect[0] == EffectType.FireRateBuff:
                    self.schedule_buff(self.attacker, effect)

        # Damage calculation (distance-based)
        damage = self.calculate_distance_based_damage(total_multiplier, flat_damage)
        
        bonus_fire_rate = ((self.attacker.get_current_fire_rate() / self.attacker.base_fire_rate) - 1) * 100.0
        print(f"[ MULTIPLIER ] Additional Weapon Damage: {total_multiplier:.2f} ( Total: +{int((total_multiplier - 1) * 100.0)}% )")
        print(f"[ MULTIPLIER ] Total Fire Rate: +{int(round(bonus_fire_rate))}%")

        damage *= 1 - self.defender.calculate_bullet_resist()
        previous_health = self.defender.health
        self.defender.health = max(0, self.defender.health - damage)
        self.stats.total_damage_dealt += damage
        self.stats.total_attacks += 1
        print(f"[ {self.current_time:>{5}.2f} ][ DAMAGE ] {self.defender.name} takes {damage:.2f} ( {previous_health:.2f} -> {self.defender.health:.2f} )")

        for item in self.attacker.build:
            if item.on_damage:
                item.on_damage(self.attacker, self.defender)

    def calculate_distance_based_damage(self, total_multiplier: float, flat_damage: float) -> float:
        min_range, max_range = self.attacker.min_range, self.attacker.max_range
        '''if sharpshooter in self.attacker.build:
            min_range += 15
            max_range += 15'''
        print(f"[ DEBUG ] range = {min_range} - {max_range} m.")
        print(f"[ DEBUG ] distance to target = {self.attacker.distance_to_target} m.")
        damage = (self.attacker.base_bullet_damage * total_multiplier) + flat_damage
        print(f"[ DEBUG ] max_damage = {damage}")
        min_damage = damage * 0.1
        print(f"[ DEBUG ] min_damage = {min_damage}")
        
        if self.attacker.distance_to_target >= min_range:
            slope = (min_damage - damage) / (max_range - min_range)
            print(f"[ DEBUG ] slope = {slope}")
            # past max range the falloff bottoms out at min_damage instead of continuing to drop
            falloff_distance = min(self.attacker.distance_to_target, max_range) - min_range
            damage = (slope * falloff_distance) + damage
            # Min. damage is always 1
            damage = max(1, damage)
            print(f"[ DEBUG ] actual_damage = {damage}")
        
        return damage

    def schedule_buff(self, hero: Hero, effect: Tuple[EffectType, float, float]):
        effect_type, value, duration = effect
        end_time, buff = hero.apply_buff(effect_type, value, duration, self.current_time)
        if end_time:
            print(f"[ {self.current_time:>{5}.2f} ][ BUFF ] Applied {effect_type.value} to {hero.name}: +{value:.2f}% for {duration:.2f} seconds")
            self.event_queue.schedule_event(Event(end_time, lambda: self.remove_buff(hero, buff)))

    def remove_buff(self, hero: Hero, buff: Buff):
        hero.remove_buff(buff)
        print(f"[ {self.current_time:>{5}.2f} ][ BUFF ] Removed {buff.effect_type.value} from {hero.name}: -{buff.value:.2f}%")

    def end_combat(self):
        print(f"[ {self.current_time:.2f} ][ END ] {self.defender.name} died.")
        self.calculate_dps()

    def calculate_dps(self):
        if self.stats.total_attacks > 0 and self.current_time > 0:
            self.stats.dps = self.stats.total_damage_dealt / self.current_time
            print(f"[ RESULT ] Total DPS: {self.stats.dps:.2f} ( {self.stats.total_damage_dealt:.2f} over {self.current_time:.2f} seconds )")

    def run_simulation(self):
        self.apply_pre_combat_effects()
        self.schedule_attack(0.0)

        while not self.event_queue.is_empty():
            event = self.event_queue.next_event()
            if event.time > self.fight_duration:
                break
            self.current_time = event.time
            event.type()

            if self.defender.health <= 0:
                self.end_combat()
                return

        # target survived the whole window, so average over the full window (reload downtime included)
        self.current_time = self.fight_duration
        self.calculate_dps()

    def apply_pre_combat_effects(self):
        if vampiric_burst in self.attacker.build:
            effects = vampiric_burst.active(self.attacker, self.defender, vampiric_burst, self.current_time)
            for effect in effects:
                if effect[0] == EffectType.FireRateBuff:
                    self.schedule_buff(self.attacker, effect)
                elif effect[0] == EffectType.CurrentAmmoBuff:
                    self.attacker.current_ammo = int(round(self.attacker.current_ammo * (1 + effect[1])))
        if crippling_headshot in self.attacker.build:
            self.defender.bullet_resist_sources.append(-0.24)