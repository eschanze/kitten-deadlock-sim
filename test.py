from sim import *

# Vindicta's base stats
hp = 550
damage = 13
fire_rate = 5.26 
ammo = 22
reload_time = 2.0 # seconds

logs = []
for distance in [30]:
    results = []
    for max_range in [45, 58]:
        attacker = Hero("Vindicta", hp, damage, fire_rate, ammo, 22, max_range, build=[sharpshooter, burst_fire], base_reload_time=reload_time)
        defender = Hero("Abrams", 3000, 0, 1, 1, 1, 2)

        simulator = CombatSimulator(attacker, defender, distance)
        simulator.run_simulation()
        results.append(simulator.stats.dps)
        print("\n--\n")

    logs.append(f"[ RESULT @ {distance} m. ] TOTAL DPS LOSS = {(1 - (results[0] / results[1])) * 100.0:.3f}%")

for log in logs:
    print(log)