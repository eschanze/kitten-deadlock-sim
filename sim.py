from dataclasses import dataclass, field
from typing import Optional

from event import Event, EventQueue
from items import Effect, EffectType, Item, intensifying_magazine

# past max range, bullets keep this fraction of their full damage
MIN_FALLOFF_DAMAGE = 0.1


@dataclass
class Buff:
    type: EffectType
    value: float
    end_time: float


@dataclass
class Hero:
    name: str
    base_health: float
    base_bullet_damage: float
    base_fire_rate: float  # bullets per second
    base_ammo: int
    min_range: float  # meters, falloff starts here
    max_range: float  # meters, falloff bottoms out here
    base_reload_time: float = 0.0  # seconds
    build: list[Item] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.health = self.base_health + sum(item.health for item in self.build)
        self.weapon_damage_bonus = sum(item.total_weapon_damage for item in self.build)
        self.ammo = round(self.base_ammo * (1 + sum(item.ammo for item in self.build)))
        self.current_ammo = self.ammo
        self.active_buffs: list[Buff] = []
        self.distance_to_target = 0.0  # meters

    def apply_buff(self, effect: Effect, current_time: float) -> Optional[Buff]:
        if effect.value <= 0 or effect.duration <= 0:
            return None
        buff = Buff(effect.type, effect.value, current_time + effect.duration)
        self.active_buffs.append(buff)
        return buff

    def remove_buff(self, buff: Buff) -> None:
        self.active_buffs.remove(buff)

    def current_fire_rate(self) -> float:
        item_bonus = sum(item.fire_rate for item in self.build)
        buff_bonus = sum(buff.value for buff in self.active_buffs if buff.type == EffectType.FIRE_RATE)
        return self.base_fire_rate * (1 + item_bonus + buff_bonus)


@dataclass
class CombatStats:
    total_damage: float = 0.0
    total_attacks: int = 0
    dps: float = 0.0


class CombatSimulator:
    def __init__(
        self,
        attacker: Hero,
        defender: Hero,
        distance_to_target: float = 30.0,
        fight_duration: float = 10.0,
        verbose: bool = True,
    ) -> None:
        self.attacker = attacker
        self.defender = defender
        self.event_queue = EventQueue()
        self.current_time = 0.0
        self.stats = CombatStats()
        # fixed window (instead of a single magazine) so reloads cost time and big-ammo builds are compared fairly
        self.fight_duration = fight_duration
        # per-bullet logging dominates runtime in batch runs, so it can be switched off
        self.verbose = verbose

        self.attacker.distance_to_target = distance_to_target

        # items are shared module-level objects, so clear timers left over from previous simulations
        for item in self.attacker.build:
            item.last_triggered = None

    def log(self, message: str, prefix: str = "*") -> None:
        if self.verbose:
            print(f"[{prefix}] {self.current_time:>5.2f}s => {message}")

    ## Events

    def schedule_attack(self, time: float) -> None:
        self.event_queue.schedule(Event(time, self.attack))

    def attack(self) -> None:
        self.attacker.current_ammo -= 1
        self.log(f"attack => {self.attacker.name} -> {self.defender.name} ({self.attacker.current_ammo}/{self.attacker.ammo})")

        # bullets are hitscan, so damage lands right away (but after this attack is done)
        self.event_queue.schedule(Event(self.current_time, self.on_damage))

        if self.attacker.current_ammo > 0:
            self.schedule_attack(self.current_time + 1 / self.attacker.current_fire_rate())
        else:
            self.event_queue.schedule(Event(self.current_time + self.attacker.base_reload_time, self.reload))

    def reload(self) -> None:
        self.attacker.current_ammo = self.attacker.ammo
        self.log(f"reload => {self.attacker.name} ({self.attacker.current_ammo}/{self.attacker.ammo})")
        # intensifying magazine ramps up while firing continuously, so the bonus restarts after a reload
        if intensifying_magazine in self.attacker.build:
            intensifying_magazine.last_triggered = None
        self.schedule_attack(self.current_time)

    def on_damage(self) -> None:
        weapon_damage = 1.0 + self.attacker.weapon_damage_bonus
        flat_damage = 0.0

        for item in self.attacker.build:
            effect = item.on_hit(self.attacker, self.defender, item, self.current_time) if item.on_hit else None
            if effect is None:
                continue
            if effect.type == EffectType.WEAPON_DAMAGE:
                weapon_damage += effect.value
            elif effect.type == EffectType.FLAT_DAMAGE:
                flat_damage += effect.value
            elif effect.type == EffectType.FIRE_RATE:
                self.schedule_buff(self.attacker, effect)

        damage = self.falloff_damage(weapon_damage, flat_damage)

        fire_rate_bonus = self.attacker.current_fire_rate() / self.attacker.base_fire_rate - 1
        self.log(f"bonus => +{(weapon_damage - 1) * 100:.0f}% weapon damage, +{fire_rate_bonus * 100:.0f}% fire rate")

        previous_health = self.defender.health
        self.defender.health = max(0.0, self.defender.health - damage)
        self.stats.total_damage += damage
        self.stats.total_attacks += 1
        self.log(f"damage => {self.defender.name} takes {damage:.2f} ({previous_health:.2f} -> {self.defender.health:.2f})")

    def falloff_damage(self, weapon_damage: float, flat_damage: float) -> float:
        # linear falloff from full damage at min range down to 10% at max range
        # e.g. range 22-58m and target at 40m => halfway => 55% damage
        full_damage = self.attacker.base_bullet_damage * weapon_damage + flat_damage
        min_range, max_range = self.attacker.min_range, self.attacker.max_range
        if self.attacker.distance_to_target < min_range:
            return full_damage

        min_damage = full_damage * MIN_FALLOFF_DAMAGE
        slope = (min_damage - full_damage) / (max_range - min_range)
        falloff_distance = min(self.attacker.distance_to_target, max_range) - min_range
        # bullets always deal at least 1 damage
        return max(1.0, full_damage + slope * falloff_distance)

    def schedule_buff(self, hero: Hero, effect: Effect) -> None:
        buff = hero.apply_buff(effect, self.current_time)
        if buff is None:
            return
        self.log(f"buff => {hero.name} gains +{buff.value * 100:.0f}% {buff.type.value} for {effect.duration:.2f}s")
        self.event_queue.schedule(Event(buff.end_time, lambda: self.remove_buff(hero, buff)))

    def remove_buff(self, hero: Hero, buff: Buff) -> None:
        hero.remove_buff(buff)
        self.log(f"buff => {hero.name} loses +{buff.value * 100:.0f}% {buff.type.value}")

    ## Simulation

    def run(self) -> CombatStats:
        self.apply_pre_combat_effects()
        self.schedule_attack(0.0)

        while not self.event_queue.is_empty():
            event = self.event_queue.pop()
            if event.time > self.fight_duration:
                # target survived the whole window, so average over all of it (reload downtime included)
                self.current_time = self.fight_duration
                break
            self.current_time = event.time
            event.callback()

            if self.defender.health <= 0:
                self.log(f"end => {self.defender.name} died", prefix="+")
                break

        self.calculate_dps()
        return self.stats

    def apply_pre_combat_effects(self) -> None:
        for item in self.attacker.build:
            if not item.active:
                continue
            for effect in item.active():
                if effect.type == EffectType.FIRE_RATE:
                    self.schedule_buff(self.attacker, effect)
                elif effect.type == EffectType.CURRENT_AMMO:
                    # only the magazine in hand gets the extra bullets
                    self.attacker.current_ammo = round(self.attacker.current_ammo * (1 + effect.value))

    def calculate_dps(self) -> None:
        if self.stats.total_attacks == 0 or self.current_time <= 0:
            return
        self.stats.dps = self.stats.total_damage / self.current_time
        self.log(f"result => {self.stats.dps:.2f} dps ({self.stats.total_damage:.2f} damage over {self.current_time:.2f}s)", prefix="+")
