from dataclasses import dataclass, field
from math import ceil, prod
from typing import Optional

from event import Event, EventQueue
from items import Category, Effect, EffectType, Item, weapon_investment_bonus

# past max range, bullets keep this fraction of their full damage
MIN_FALLOFF_DAMAGE = 0.1

# every damage over time effect ticks this often (seconds)
DOT_TICK_RATE = 0.5

# headshots deal 1.65x damage (most heroes, Vindicta included)
HEADSHOT_MULTIPLIER = 1.65


@dataclass
class Buff:
    type: EffectType
    value: float
    end_time: float
    until_reload: bool = False


@dataclass
class Debuff:
    value: float
    end_time: float


@dataclass
class DamageOverTime:
    damage_per_second: float
    end_time: float


def combined_resist(sources: list[float]) -> float:
    # sources stack multiplicatively, and reductions are stacked the same way then subtracted
    # e.g. [0.3, 0.2] => 1 - (0.7 * 0.8) => 44% resist
    resists = [source for source in sources if source >= 0]
    reductions = [-source for source in sources if source < 0]
    total_resist = 1 - prod(1 - resist for resist in resists)
    total_reduction = 1 - prod(1 - reduction for reduction in reductions)
    return total_resist - total_reduction


def active_debuffs(debuffs: dict[Item, Debuff], current_time: float) -> list[float]:
    # as negative resist sources, for combined_resist
    return [-debuff.value for debuff in debuffs.values() if debuff.end_time >= current_time]


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
    bullet_resist_sources: list[float] = field(default_factory=list)  # negative values reduce resist
    spirit_resist_sources: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.health = self.base_health + sum(item.health for item in self.build)
        self.max_health = self.health
        weapon_souls = sum(item.souls for item in self.build if item.category == Category.WEAPON)
        self.weapon_damage_bonus = sum(item.weapon_damage for item in self.build) + weapon_investment_bonus(weapon_souls)
        # extra ammo rounds up (the rounding first absorbs float noise, e.g. 19 * 1.3 => 24.700000000000003)
        self.ammo = ceil(round(self.base_ammo * (1 + sum(item.ammo for item in self.build)), 6))
        self.current_ammo = self.ammo
        # item stats don't change mid fight, and summing them on every bullet dominated batch runtime
        self.item_fire_rate = sum(item.fire_rate for item in self.build)
        self.falloff_scale = 1 + sum(item.falloff_range for item in self.build)
        self.active_buffs: list[Buff] = []
        # timed resist reductions, one per item so reapplying refreshes instead of stacking
        self.bullet_resist_debuffs: dict[Item, Debuff] = {}
        self.spirit_resist_debuffs: dict[Item, Debuff] = {}
        self.health_drain = 0.0  # per second
        self.distance_to_target = 0.0  # meters
        self.headshot = False  # whether the bullet being resolved is a headshot

    def bullet_resist(self, current_time: float = 0.0) -> float:
        return combined_resist(self.bullet_resist_sources + active_debuffs(self.bullet_resist_debuffs, current_time))

    def spirit_resist(self, current_time: float = 0.0) -> float:
        return combined_resist(self.spirit_resist_sources + active_debuffs(self.spirit_resist_debuffs, current_time))

    def apply_buff(self, effect: Effect, current_time: float) -> Optional[Buff]:
        if effect.value <= 0 or effect.duration <= 0:
            return None
        buff = Buff(effect.type, effect.value, current_time + effect.duration, effect.until_reload)
        self.active_buffs.append(buff)
        return buff

    def remove_buff(self, buff: Buff) -> None:
        self.active_buffs.remove(buff)

    def falloff_range(self) -> tuple[float, float]:
        # falloff range items stretch both ends of the range
        return self.min_range * self.falloff_scale, self.max_range * self.falloff_scale

    def falloff_multiplier(self) -> float:
        # linear falloff from full damage at min range down to 10% at max range
        # e.g. range 20-60m and target at 40m => halfway => 55% damage
        min_range, max_range = self.falloff_range()
        if self.distance_to_target < min_range:
            return 1.0
        falloff_distance = min(self.distance_to_target, max_range) - min_range
        return 1 + (MIN_FALLOFF_DAMAGE - 1) * falloff_distance / (max_range - min_range)

    def current_fire_rate(self) -> float:
        buff_bonus = sum(buff.value for buff in self.active_buffs if buff.type == EffectType.FIRE_RATE)
        return self.base_fire_rate * (1 + self.item_fire_rate + buff_bonus)


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
        headshot_chance: float = 0.0,
        verbose: bool = True,
    ) -> None:
        self.attacker = attacker
        self.defender = defender
        self.event_queue = EventQueue()
        self.current_time = 0.0
        self.stats = CombatStats()
        # fixed window (instead of a single magazine) so reloads cost time and big-ammo builds are compared fairly
        self.fight_duration = fight_duration
        self.headshot_chance = headshot_chance
        self.headshot_charge = 0.0
        # per-bullet logging dominates runtime in batch runs, so it can be switched off
        self.verbose = verbose
        # kept so it can be cancelled when an item empties the magazine early
        self.next_attack: Optional[Event] = None
        self.damage_over_time: dict[Item, DamageOverTime] = {}
        self.on_hit_items = [item for item in attacker.build if item.on_hit]

        self.attacker.distance_to_target = distance_to_target

        # items are shared module-level objects, so clear timers left over from previous simulations
        for item in self.attacker.build:
            item.reset()

    def log(self, message: str, prefix: str = "*") -> None:
        if self.verbose:
            print(f"[{prefix}] {self.current_time:>5.2f}s => {message}")

    ## Events

    def schedule_attack(self, time: float) -> None:
        self.next_attack = Event(time, self.attack)
        self.event_queue.schedule(self.next_attack)

    def attack(self) -> None:
        self.attacker.current_ammo -= 1
        self.log(f"attack => {self.attacker.name} -> {self.defender.name} ({self.attacker.current_ammo}/{self.attacker.ammo})")

        # bullets are hitscan, so damage lands right away (but after this attack is done)
        self.event_queue.schedule(Event(self.current_time, self.on_damage))

        if self.attacker.current_ammo > 0:
            self.schedule_attack(self.current_time + 1 / self.attacker.current_fire_rate())
        else:
            self.start_reload()

    def start_reload(self) -> None:
        self.event_queue.schedule(Event(self.current_time + self.attacker.base_reload_time, self.reload))

    def reload(self) -> None:
        self.attacker.current_ammo = self.attacker.ammo
        self.log(f"reload => {self.attacker.name} ({self.attacker.current_ammo}/{self.attacker.ammo})")

        for buff in [buff for buff in self.attacker.active_buffs if buff.until_reload]:
            self.remove_buff(self.attacker, buff)
        for item in self.attacker.build:
            if item.on_reload:
                self.apply_effects(item.on_reload(self.attacker, item, self.current_time), item)

        self.schedule_attack(self.current_time)

    def on_damage(self) -> None:
        if self.attacker.health_drain:
            self.attacker.health = max(1.0, self.attacker.max_health - self.attacker.health_drain * self.current_time)
        # set before the on hit items run, since headshot items check it
        self.attacker.headshot = self.roll_headshot()

        weapon_damage = 1.0 + self.attacker.weapon_damage_bonus
        flat_damage = 0.0
        damage_multiplier = 1.0
        ammo_cost = 0

        for item in self.on_hit_items:
            for effect in self.on_hit_effects(item):
                if effect.type == EffectType.WEAPON_DAMAGE:
                    weapon_damage += effect.value
                elif effect.type == EffectType.FLAT_DAMAGE:
                    flat_damage += effect.value
                elif effect.type == EffectType.DAMAGE_MULTIPLIER:
                    damage_multiplier *= 1 + effect.value
                elif effect.type == EffectType.AMMO_COST:
                    ammo_cost += int(effect.value)
                else:
                    self.apply_effect(effect, item)

        damage = self.falloff_damage(weapon_damage, flat_damage) * damage_multiplier
        if self.attacker.headshot:
            damage *= HEADSHOT_MULTIPLIER
        damage *= 1 - self.defender.bullet_resist(self.current_time)

        if self.verbose:
            fire_rate_bonus = self.attacker.current_fire_rate() / self.attacker.base_fire_rate - 1
            self.log(f"bonus => +{(weapon_damage - 1) * 100:.0f}% weapon damage, +{fire_rate_bonus * 100:.0f}% fire rate")

        self.deal_damage(damage, " (headshot)" if self.attacker.headshot else "")
        self.stats.total_attacks += 1

        if ammo_cost:
            self.consume_ammo(ammo_cost)

    def roll_headshot(self) -> bool:
        # like chance procs, headshots land on a fixed rhythm instead of randomly, e.g. 25% => every 4th bullet
        self.headshot_charge = round(self.headshot_charge + self.headshot_chance, 9)
        if self.headshot_charge < 1:
            return False
        self.headshot_charge -= 1
        return True

    def on_hit_effects(self, item: Item) -> list[Effect]:
        result = item.on_hit(self.attacker, self.defender, item, self.current_time)
        if result is None:
            return []
        return [result] if isinstance(result, Effect) else result

    def falloff_damage(self, weapon_damage: float, flat_damage: float) -> float:
        full_damage = self.attacker.base_bullet_damage * weapon_damage + flat_damage
        # bullets always deal at least 1 damage
        return max(1.0, full_damage * self.attacker.falloff_multiplier())

    def deal_damage(self, damage: float, source: str) -> None:
        previous_health = self.defender.health
        self.defender.health = max(0.0, self.defender.health - damage)
        self.stats.total_damage += damage
        self.log(f"damage => {self.defender.name} takes {damage:.2f}{source} ({previous_health:.2f} -> {self.defender.health:.2f})")

    def deal_spirit_damage(self, damage: float, item: Item) -> None:
        self.deal_damage(damage * (1 - self.defender.spirit_resist(self.current_time)), f" spirit damage from {item.name}")

    def consume_ammo(self, amount: int) -> None:
        if self.attacker.current_ammo <= 0:
            return
        self.attacker.current_ammo = max(0, self.attacker.current_ammo - amount)
        if self.attacker.current_ammo > 0:
            return
        # the next attack was already scheduled when this bullet was fired, so reload instead
        if self.next_attack:
            self.next_attack.cancelled = True
        self.start_reload()

    ## Effects

    def apply_effects(self, effects: list[Effect], item: Item) -> None:
        for effect in effects:
            self.apply_effect(effect, item)

    def apply_effect(self, effect: Effect, item: Item) -> None:
        if effect.type == EffectType.FIRE_RATE:
            self.schedule_buff(self.attacker, effect)
        elif effect.type == EffectType.CURRENT_AMMO:
            # only the magazine in hand gets the extra bullets
            self.attacker.current_ammo = round(self.attacker.current_ammo * (1 + effect.value))
        elif effect.type == EffectType.BONUS_AMMO:
            self.attacker.current_ammo += int(effect.value)
        elif effect.type == EffectType.HEALTH_DRAIN:
            self.attacker.health_drain += effect.value
        elif effect.type == EffectType.SPIRIT_DAMAGE:
            self.deal_spirit_damage(effect.value, item)
        elif effect.type == EffectType.SPIRIT_DOT:
            self.apply_damage_over_time(effect, item)
        elif effect.type == EffectType.BULLET_RESIST_REDUCTION:
            self.defender.bullet_resist_debuffs[item] = Debuff(effect.value, self.current_time + effect.duration)
        elif effect.type == EffectType.SPIRIT_RESIST_REDUCTION:
            self.defender.spirit_resist_debuffs[item] = Debuff(effect.value, self.current_time + effect.duration)

    def schedule_buff(self, hero: Hero, effect: Effect) -> None:
        buff = hero.apply_buff(effect, self.current_time)
        if buff is None:
            return
        self.log(f"buff => {hero.name} gains +{buff.value * 100:.0f}% {buff.type.value} for {effect.duration:.2f}s")
        self.event_queue.schedule(Event(buff.end_time, lambda: self.remove_buff(hero, buff)))

    def remove_buff(self, hero: Hero, buff: Buff) -> None:
        # buffs that end on reload may already be gone when their timer runs out
        if buff not in hero.active_buffs:
            return
        hero.remove_buff(buff)
        self.log(f"buff => {hero.name} loses +{buff.value * 100:.0f}% {buff.type.value}")

    def apply_damage_over_time(self, effect: Effect, item: Item) -> None:
        end_time = self.current_time + effect.duration
        existing = self.damage_over_time.get(item)
        if existing:
            # refresh, the ticks already running keep their rhythm
            existing.damage_per_second = effect.value
            existing.end_time = end_time
            return
        self.damage_over_time[item] = DamageOverTime(effect.value, end_time)
        self.log(f"dot => {item.name} deals {effect.value:.2f} spirit damage per second for {effect.duration:.2f}s")
        self.event_queue.schedule(Event(self.current_time + DOT_TICK_RATE, lambda: self.tick_damage_over_time(item)))

    def tick_damage_over_time(self, item: Item) -> None:
        dot = self.damage_over_time[item]
        # small tolerance, tick times are sums of floats
        if self.current_time > dot.end_time + 1e-9:
            del self.damage_over_time[item]
            return
        self.deal_spirit_damage(dot.damage_per_second * DOT_TICK_RATE, item)
        self.event_queue.schedule(Event(self.current_time + DOT_TICK_RATE, lambda: self.tick_damage_over_time(item)))

    ## Simulation

    def run(self) -> CombatStats:
        self.apply_pre_combat_effects()
        self.schedule_attack(0.0)

        while not self.event_queue.is_empty():
            event = self.event_queue.pop()
            if event.cancelled:
                continue
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
            if item.bullet_resist_reduction:
                self.defender.bullet_resist_sources.append(-item.bullet_resist_reduction)
            if item.spirit_resist_reduction:
                self.defender.spirit_resist_sources.append(-item.spirit_resist_reduction)
        # actives go after the resist reductions, so their damage is already amplified by them
        for item in self.attacker.build:
            if item.active:
                self.apply_effects(item.active(), item)

    def calculate_dps(self) -> None:
        if self.stats.total_attacks == 0 or self.current_time <= 0:
            return
        self.stats.dps = self.stats.total_damage / self.current_time
        self.log(f"result => {self.stats.dps:.2f} dps ({self.stats.total_damage:.2f} damage over {self.current_time:.2f}s)", prefix="+")
