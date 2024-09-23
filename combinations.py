from sim import *
import itertools

# Vindicta's base stats
hp = 550
damage = 5.5
fire_rate = 11.1
ammo = 52

current_build = []

all_items = [basic_magazine, headshot_booster, high_velocity_mag, hollow_point_ward, rapid_rounds, restorative_shot,
        long_range, swift_striker,
        burst_fire, intensifying_magazine, pristine_emblem, warp_stone, sharpshooter,
        glass_cannon, vampiric_burst]

incompatible_pairs = [
    (long_range, sharpshooter)
]

def is_valid_build(build):
    for item1, item2 in incompatible_pairs:
        if item1 in build and item2 in build:
            return False
    starter_items = sum(1 for item in build if item.souls == 500)
    if starter_items > 3:
        return False
    return True

possible_items = [item for item in all_items if item not in current_build]
additional_items = list(itertools.combinations(possible_items, 5))

possible_builds = [current_build + list(combination) for combination in additional_items if is_valid_build(current_build + list(combination))]

all_builds = []

for b in possible_builds:
    build_names = [i.name for i in b]
    total_cost = sum([i.souls for i in b])
    attacker = Hero("Vindicta", hp, damage, fire_rate, ammo, build=b)
    defender = Hero("Abrams", 3000, 0, 1, 1)

    simulator = CombatSimulator(attacker, defender)
    simulator.run_simulation()
    value = simulator.stats.dps / total_cost

    if total_cost <= 10000:
        all_builds.append({
            'build': build_names,
            'total_cost': total_cost,
            'value': value,
            'dps': simulator.stats.dps,
            'total_dmg': simulator.stats.total_damage_dealt
        })

sorted_builds = sorted(all_builds, key=lambda x: x['dps'], reverse=False)

print("All builds sorted by value (DPS / Souls):")
for i, build in enumerate(sorted_builds, 1):
    print(f"\n{i}. Build: {build['build']}")
    print(f"   Total cost: {build['total_cost']}")
    print(f"   Value = {build['value']:.4f}")
    print(f"   DPS: {build['dps']:.2f}")
    print(f"   Total damage: {build['total_dmg']}")