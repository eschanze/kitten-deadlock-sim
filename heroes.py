from typing import Optional

from items import Item
from sim import Hero


def vindicta(build: Optional[list[Item]] = None) -> Hero:
    return Hero(
        name="Vindicta",
        base_health=550,
        base_bullet_damage=13,
        base_fire_rate=5.26,
        base_ammo=22,
        min_range=22,
        max_range=58,
        base_reload_time=2.0,
        build=build or [],
    )


def target_dummy(health: float, name: str = "Abrams") -> Hero:
    # the defender only soaks up damage, so its weapon stats don't matter
    return Hero(
        name=name,
        base_health=health,
        base_bullet_damage=0,
        base_fire_rate=1,
        base_ammo=1,
        min_range=1,
        max_range=1,
    )
