from dataclasses import dataclass, field
from typing import List, Tuple
from event import Event, EventQueue
from items import *

@dataclass
class Hero:
    name: str
    base_health: float
    base_bullet_damage: float
    base_fire_rate: float
    base_ammo: int
    build: list[Item] = field(default_factory=list)
    active_buffs: list = field(default_factory=list)

    def __post_init__(self):
        # Apply base stats
        self.health = self.base_health + sum(item.health for item in self.build)
        self.weapon_damage_multiplier = sum(item.weapon_damage for item in self.build)
        self.bullet_damage = self.base_bullet_damage
        self.fire_rate = self.base_fire_rate * (1 + sum(item.fire_rate for item in self.build))
        self.ammo = int(round(self.base_ammo * (1 + sum(item.ammo for item in self.build))))
        self.current_ammo = self.ammo
    
@dataclass
class CombatStats:
    total_damage_dealt: float = 0.0
    total_attacks: int = 0
    dps: float = 0.0

@dataclass
class ActiveBuff:
    hero: 'Hero'
    effect_type: EffectType
    value: float
    end_time: float

class CombatSimulator:
    def __init__(self, attacker: 'Hero', defender: 'Hero'):
        self.attacker = attacker
        self.defender = defender
        self.event_queue = EventQueue()
        self.current_time = 0.0
        self.stats = CombatStats()
        self.active_buffs: List[ActiveBuff] = []

    def schedule_attack(self, time: float):
        self.event_queue.schedule_event(Event(time, self.attack))

    def attack(self):
        self.attacker.current_ammo -= 1
        #print(f"[ {self.current_time:>{5}.2f} ][ ATTACK ] {self.attacker.name} -> {self.defender.name} ( {self.attacker.current_ammo}/{self.attacker.ammo} )")
        damage_time = self.current_time + 0.0 # Travel time
        self.event_queue.schedule_event(Event(damage_time, self.on_damage))
        if self.attacker.current_ammo > 0:
            next_attack_time = self.current_time + (1 / self.get_current_fire_rate(self.attacker))
            self.schedule_attack(next_attack_time)
        else:
            self.event_queue.schedule_event(Event(damage_time, self.calculate_dps))

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
                    self.apply_buff(self.attacker, effect)

        damage = (self.attacker.base_bullet_damage * total_multiplier) + flat_damage
        bonus_fire_rate = ((self.get_current_fire_rate(self.attacker) / self.attacker.base_fire_rate) - 1) * 100.0
        #print(f"[ MULTIPLIER ] Additional Weapon Damage: {total_multiplier:.2f} ( Total: +{int((total_multiplier - 1) * 100.0)}% )")
        #print(f"[ MULTIPLIER ] Total Fire Rate: +{int(round(bonus_fire_rate))}%")

        previous_health = self.defender.health
        self.defender.health = max(0, self.defender.health - damage)
        self.stats.total_damage_dealt += damage
        self.stats.total_attacks += 1
        #print(f"[ {self.current_time:>{5}.2f} ][ DAMAGE ] {self.defender.name} takes {damage:.2f} ( {previous_health:.2f} -> {self.defender.health:.2f} )")

        for item in self.attacker.build:
            if item.on_damage:
                item.on_damage(self.attacker, self.defender)

        if self.defender.health <= 0:
            self.event_queue.schedule_event(Event(self.current_time, self.end_combat))

    def apply_buff(self, hero: 'Hero', effect: Tuple[EffectType, float, float]):
        effect_type, value, duration = effect
        #existing_buff = next((buff for buff in self.active_buffs if buff.hero == hero and buff.effect_type == effect_type and buff.source == source), None)
        if value > 0 and duration > 0:
            end_time = self.current_time + duration
            self.active_buffs.append(ActiveBuff(hero, effect_type, value, end_time))
            #print(f"[ BUFF ] Applied {effect_type.value} to {hero.name}: +{value:.2f} for {duration:.2f} seconds")
            self.event_queue.schedule_event(Event(end_time, lambda: self.remove_buff(hero, effect_type, value)))

    def remove_buff(self, hero: 'Hero', effect_type: EffectType, value: float):
        self.active_buffs = [buff for buff in self.active_buffs if not (buff.hero == hero and buff.effect_type == effect_type and buff.value == value)]
        #print(f"[ {self.current_time:>{5}.2f} ][ BUFF ] Removed {effect_type.value} from {hero.name}: -{value:.2f}")

    def get_current_fire_rate(self, hero: 'Hero') -> float:
        base_fire_rate = hero.base_fire_rate
        item_fire_rate_bonus = sum(item.fire_rate for item in hero.build)
        active_fire_rate_buffs = sum(buff.value for buff in self.active_buffs if buff.hero == hero and buff.effect_type == EffectType.FireRateBuff)
        
        return base_fire_rate * (1 + item_fire_rate_bonus + active_fire_rate_buffs)

    def end_combat(self):
        #print(f"[ {self.current_time:.2f} ][ END ] {self.defender.name} died.")
        self.calculate_dps()

    def calculate_dps(self):
        if self.stats.total_attacks > 0 and self.current_time > 0:
            self.stats.dps = self.stats.total_damage_dealt / self.current_time
            #print(f"[ RESULT ] Total DPS: {self.stats.dps:.2f} ( {self.stats.total_damage_dealt:.2f} over {self.current_time:.2f} seconds )")

    def run_simulation(self):
        self.schedule_attack(0.0)

        while not self.event_queue.is_empty():
            event = self.event_queue.next_event()
            self.current_time = event.time
            event.type()

            if self.defender.health <= 0:
                self.end_combat()
                break