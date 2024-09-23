from dataclasses import dataclass

from heroes import target_dummy, vindicta
from items import (
    ALL_ITEMS, Item,
    basic_magazine, high_velocity_mag, hollow_point_ward, intensifying_magazine, long_range, swift_striker,
)
from sim import CombatSimulator, CombatStats

TARGET_HEALTH = 5000

CURRENT_BUILD = [basic_magazine, high_velocity_mag, hollow_point_ward, long_range, swift_striker, intensifying_magazine]


@dataclass
class Replacement:
    replaced_item: Item
    new_item: Item
    build: list[Item]
    stats: CombatStats


def simulate(build: list[Item]) -> CombatStats:
    simulator = CombatSimulator(vindicta(build), target_dummy(TARGET_HEALTH), verbose=False)
    return simulator.run()


def find_replacements() -> list[Replacement]:
    candidates = [item for item in ALL_ITEMS if item not in CURRENT_BUILD]
    replacements = []

    for slot, replaced_item in enumerate(CURRENT_BUILD):
        # only upgrades, selling an item for a cheaper one is never the goal
        for new_item in (item for item in candidates if item.souls >= replaced_item.souls):
            build = CURRENT_BUILD.copy()
            build[slot] = new_item
            replacements.append(Replacement(replaced_item, new_item, build, simulate(build)))

    return replacements


def print_replacement(replacement: Replacement) -> None:
    print(f"    build => {[item.name for item in replacement.build]}")
    print(f"    dps => {replacement.stats.dps:.2f}")
    print(f"    total damage => {replacement.stats.total_damage:.2f}")


def run() -> None:
    # worst first, so the best replacements end up at the bottom of the terminal
    replacements = sorted(find_replacements(), key=lambda replacement: replacement.stats.total_damage)

    for rank, replacement in zip(range(len(replacements), 0, -1), replacements):
        print(f"\n[*] #{rank} => replace {replacement.replaced_item.name} with {replacement.new_item.name}")
        print_replacement(replacement)

    best = replacements[-1]
    original_stats = simulate(CURRENT_BUILD)
    print(f"\n[+] best replacement => replace {best.replaced_item.name} with {best.new_item.name}")
    print_replacement(best)
    print(f"    dps gain => {best.stats.dps - original_stats.dps:+.2f} (from {original_stats.dps:.2f})")


if __name__ == "__main__":
    run()
