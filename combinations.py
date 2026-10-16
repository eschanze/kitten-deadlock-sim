from collections.abc import Iterator
from dataclasses import dataclass
from itertools import islice

from heroes import target_dummy, vindicta
from items import ALL_ITEMS, Item, has_component_conflict
from sim import CombatSimulator

BUILD_SIZE = 5
MAX_COST = 8000  # souls
MAX_STARTER_ITEMS = 3
DISTANCE = 35  # meters
HEADSHOT_CHANCE = 0.0  # 0.25 => every 4th bullet is a headshot
TARGET_HEALTH = 3000

# items already owned, the search only fills the remaining slots
CURRENT_BUILD: list[Item] = []

# past this many builds, simulating every one takes hours (8 slots and no budget => ~177M), so a beam search finds the
# best ones instead. against exhaustive runs of ~900k builds it found the same top 15 every time
# (the default 5 items for 8000 souls is ~36k, so it stays exhaustive)
EXHAUSTIVE_LIMIT = 50000
# partial builds kept after filling each slot
BEAM_WIDTH = 100
# the best builds then get each of their items swapped for every other one, until the top doesn't change
SWAP_TOP = 40
MAX_SWAP_ROUNDS = 5


@dataclass
class BuildResult:
    build: list[Item]
    cost: int
    dps: float
    total_damage: float

    @property
    def value(self) -> float:
        return self.dps / self.cost


def is_valid_build(build: list[Item], candidates: list[Item], empty_slots: int = 0) -> bool:
    if has_component_conflict(build):
        return False
    starter_items = sum(1 for item in build if item.tier == 1)
    if starter_items > MAX_STARTER_ITEMS:
        return False
    # filter on cost before simulating, otherwise most of the simulations get thrown away
    # (the slots still empty must fit in the budget too, even with the cheapest items left)
    cheapest = [item for item in candidates if item not in build][:empty_slots]
    return len(cheapest) == empty_slots and sum(item.souls for item in build + cheapest) <= MAX_COST


def affordable_combinations(items: list[Item], size: int, budget: int, start: int = 0) -> Iterator[list[Item]]:
    # like itertools.combinations, but skips whole branches that go over budget instead of building them
    # (items must be sorted by cost, so once one doesn't fit none of the following ones do)
    if size == 0:
        yield []
        return
    for index in range(start, len(items)):
        item = items[index]
        if item.souls > budget:
            break
        for rest in affordable_combinations(items, size - 1, budget - item.souls, index + 1):
            yield [item] + rest


def simulate(build: list[Item]) -> BuildResult:
    simulator = CombatSimulator(
        vindicta(build), target_dummy(TARGET_HEALTH), distance_to_target=DISTANCE,
        headshot_chance=HEADSHOT_CHANCE, verbose=False,
    )
    stats = simulator.run()
    return BuildResult(build, sum(item.souls for item in build), stats.dps, stats.total_damage)


def build_key(build: list[Item]) -> frozenset[Item]:
    # the same items in another order are the same build
    return frozenset(build)


class BuildSearch:
    def __init__(self, current_build: list[Item]) -> None:
        self.current_build = current_build
        self.candidates = sorted((item for item in ALL_ITEMS if item not in current_build), key=lambda item: item.souls)
        self.slots = max(0, BUILD_SIZE - len(current_build))
        # every build simulated so far, partial ones included
        self.evaluated: dict[frozenset[Item], BuildResult] = {}

    def evaluate(self, build: list[Item]) -> BuildResult:
        key = build_key(build)
        if key not in self.evaluated:
            self.evaluated[key] = simulate(build)
        return self.evaluated[key]

    def ranked(self) -> list[BuildResult]:
        full_size = len(self.current_build) + self.slots
        results = [result for result in self.evaluated.values() if len(result.build) == full_size]
        return sorted(results, key=lambda result: result.dps, reverse=True)

    def run(self) -> tuple[list[BuildResult], bool]:
        # returns the builds best first, and whether every valid build was simulated
        budget = MAX_COST - sum(item.souls for item in self.current_build)
        combinations = affordable_combinations(self.candidates, self.slots, budget)
        if sum(1 for _ in islice(combinations, EXHAUSTIVE_LIMIT + 1)) <= EXHAUSTIVE_LIMIT:
            self.exhaustive_search(budget)
            return self.ranked(), True
        self.beam_search()
        self.swap_search()
        return self.ranked(), False

    def exhaustive_search(self, budget: int) -> None:
        for combination in affordable_combinations(self.candidates, self.slots, budget):
            build = self.current_build + combination
            if is_valid_build(build, self.candidates):
                self.evaluate(build)

    def beam_search(self) -> None:
        # fill one slot at a time, keeping only the best partial builds
        beam = [self.current_build]
        for filled in range(1, self.slots + 1):
            extended: dict[frozenset[Item], BuildResult] = {}
            for partial in beam:
                for item in self.candidates:
                    if item in partial:
                        continue
                    build = partial + [item]
                    key = build_key(build)
                    if key in extended or not is_valid_build(build, self.candidates, self.slots - filled):
                        continue
                    extended[key] = self.evaluate(build)
            best = sorted(extended.values(), key=lambda result: result.dps, reverse=True)[:BEAM_WIDTH]
            beam = [result.build for result in best]

    def swap_search(self) -> None:
        # the beam can drop a partial build that only pays off with the right last items, and swapping one item at a
        # time finds most of those
        for _ in range(MAX_SWAP_ROUNDS):
            top = [result.build for result in self.ranked()[:SWAP_TOP]]
            for build in top:
                for slot in range(len(self.current_build), len(build)):
                    for item in self.candidates:
                        if item in build:
                            continue
                        swapped = build.copy()
                        swapped[slot] = item
                        if build_key(swapped) not in self.evaluated and is_valid_build(swapped, self.candidates):
                            self.evaluate(swapped)
            if [result.build for result in self.ranked()[:SWAP_TOP]] == top:
                break


def run() -> None:
    results, exhaustive = BuildSearch(CURRENT_BUILD).run()
    # worst first, so the best builds end up at the bottom of the terminal
    results.reverse()

    for rank, result in zip(range(len(results), 0, -1), results):
        print(f"\n[*] #{rank} => {[item.name for item in result.build]}")
        print(f"    cost => {result.cost} souls")
        print(f"    dps => {result.dps:.2f}")
        print(f"    value => {result.value:.4f} dps per soul")
        print(f"    total damage => {result.total_damage:.2f}")

    if not exhaustive:
        print(f"\n[*] too many builds to simulate them all, so these are the {len(results)} most promising (beam search)")


if __name__ == "__main__":
    run()
