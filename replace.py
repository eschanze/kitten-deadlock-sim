from sim import *

# Vindicta's base stats
hp = 550
damage = 13
fire_rate = 5.26 
ammo = 22

current_build = [basic_magazine, high_velocity_mag, hollow_point_ward, long_range, swift_striker, intensifying_magazine]

all_items = [basic_magazine, headshot_booster, high_velocity_mag, hollow_point_ward, rapid_rounds, restorative_shot,
        long_range, swift_striker,
        burst_fire, intensifying_magazine, pristine_emblem, warp_stone,
        glass_cannon, vampiric_burst]

possible_items = [item for item in all_items if item not in current_build]

def simulate_build(build):
    attacker = Hero("Vindicta", hp, damage, fire_rate, ammo, build=build)
    defender = Hero("Abrams", 5000, 0, 1, 1)
    simulator = CombatSimulator(attacker, defender)
    simulator.run_simulation()
    return simulator.stats

results = []

for i, item_to_replace in enumerate(current_build):
    for new_item in possible_items:
        if new_item.souls >= item_to_replace.souls:
            new_build = current_build.copy()
            new_build[i] = new_item
            
            stats = simulate_build(new_build)

            results.append({
                'replaced_item': item_to_replace.name,
                'new_item': new_item.name,
                'dps': stats.dps,
                'build': [item.name for item in new_build],
                'total_dmg': stats.total_damage_dealt
            })

sorted_results = sorted(results, key=lambda x: x['total_dmg'], reverse=False)

print("Results of replacing one item with the new item, sorted by DPS:")
for i, result in enumerate(sorted_results, 1):
    print(f"\n{i}. Replace {result['replaced_item']} with {result['new_item']}")
    print(f"    New build: {result['build']}")
    print(f"    DPS: {result['dps']:.2f}")
    print(f"    Total damage: {result['total_dmg']}")

best_replacement = sorted_results[-1]
print("\nBest Replacement:")
print(f"Replace {best_replacement['replaced_item']} with {best_replacement['new_item']}")
print(f"New build: {best_replacement['build']}")
print(f"DPS: {best_replacement['dps']:.2f}")
print(f"Total damage: {best_replacement['total_dmg']}")

original_dps = simulate_build(current_build).dps
print(f"\nOriginal build DPS: {original_dps:.2f}")
print(f"DPS improvement: {best_replacement['dps'] - original_dps:.2f}")