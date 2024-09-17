import itertools

from heroes import target_dummy, vindicta
from items import ALL_ITEMS, Item
from sim import CombatSimulator, CombatStats

BUILD_SIZE = 5
MAX_COST = 8250  # souls
TARGET_HEALTH = 5000


def simulate(build: list[Item]) -> CombatStats:
    simulator = CombatSimulator(vindicta(build), target_dummy(TARGET_HEALTH), verbose=False)
    return simulator.run()


def run() -> None:
    best_build: list[Item] = []
    best_stats = CombatStats()

    for combination in itertools.combinations(ALL_ITEMS, BUILD_SIZE):
        build = list(combination)
        if sum(item.souls for item in build) > MAX_COST:
            continue

        stats = simulate(build)
        if stats.dps > best_stats.dps:
            best_build, best_stats = build, stats

    best_cost = sum(item.souls for item in best_build)
    print(f"[+] best build => {[item.name for item in best_build]}")
    print(f"    cost => {best_cost} souls")
    print(f"    dps => {best_stats.dps:.2f}")
    print(f"    value => {best_stats.dps / best_cost:.4f} dps per soul")


if __name__ == "__main__":
    run()
