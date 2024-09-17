from sim import *
import itertools

# Example: Vindicta vs Abrams with buffed HP
hp = 550
damage = 13
fire_rate = 5.26
ammo = 22

items = [basic_magazine, headshot_booster, high_velocity_mag, hollow_point_ward, rapid_rounds, restorative_shot,
        long_range, swift_striker,
        burst_fire, intensifying_magazine, pristine_emblem]

possible_builds = [list(comb) for comb in itertools.combinations(items, 5)]

best_build = []
best_value = 0
best_dps = 0

for b in possible_builds:
    build_names =[i.name for i in b]
    total_cost = sum([i.souls for i in b])
    attacker = Hero("Vindicta", hp, damage, fire_rate, ammo, build=b)
    defender = Hero("Abrams", 5000, 0, 1, 1)

    simulator = CombatSimulator(attacker, defender)
    simulator.run_simulation()
    value = simulator.stats.dps / total_cost

    print(f"Build: {build_names}")
    print(f"Total cost: {total_cost}")
    print(f"DPS / Souls value = {value}")
    print(f"DPS: {best_dps}\n")

    #if value > best_value:
    if total_cost <= 8250:
        if simulator.stats.dps > best_dps:
            best_value = value
            best_build = build_names
            best_dps = simulator.stats.dps

print("\n---")
print(f"Best build: {best_build}")
print(f"DPS / Souls value = {best_value}")
print(f"Best DPS: {best_dps}")