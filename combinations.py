import itertools
from dataclasses import dataclass

from heroes import target_dummy, vindicta
from items import ALL_ITEMS, Item, has_component_conflict
from sim import CombatSimulator

BUILD_SIZE = 5
MAX_COST = 8000  # souls
MAX_STARTER_ITEMS = 3
DISTANCE = 35  # meters
TARGET_HEALTH = 3000

# items already owned, the search only fills the remaining slots
CURRENT_BUILD: list[Item] = []


@dataclass
class BuildResult:
    build: list[Item]
    cost: int
    dps: float
    total_damage: float

    @property
    def value(self) -> float:
        return self.dps / self.cost


def is_valid_build(build: list[Item]) -> bool:
    if has_component_conflict(build):
        return False
    starter_items = sum(1 for item in build if item.tier == 1)
    if starter_items > MAX_STARTER_ITEMS:
        return False
    # filter on cost before simulating, otherwise most of the simulations get thrown away
    return sum(item.souls for item in build) <= MAX_COST


def simulate(build: list[Item]) -> BuildResult:
    simulator = CombatSimulator(vindicta(build), target_dummy(TARGET_HEALTH), distance_to_target=DISTANCE, verbose=False)
    stats = simulator.run()
    return BuildResult(build, sum(item.souls for item in build), stats.dps, stats.total_damage)


def run() -> None:
    candidates = [item for item in ALL_ITEMS if item not in CURRENT_BUILD]
    builds = [CURRENT_BUILD + list(combination) for combination in itertools.combinations(candidates, BUILD_SIZE)]
    builds = [build for build in builds if is_valid_build(build)]

    results = [simulate(build) for build in builds]
    # worst first, so the best builds end up at the bottom of the terminal
    results.sort(key=lambda result: result.dps)

    for rank, result in zip(range(len(results), 0, -1), results):
        print(f"\n[*] #{rank} => {[item.name for item in result.build]}")
        print(f"    cost => {result.cost} souls")
        print(f"    dps => {result.dps:.2f}")
        print(f"    value => {result.value:.4f} dps per soul")
        print(f"    total damage => {result.total_damage:.2f}")


if __name__ == "__main__":
    run()
