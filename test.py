from sim import *

# Vindicta's base stats
hp = 550
damage = 13
fire_rate = 5.26 
ammo = 22

attacker = Hero("Vindicta", hp, damage, fire_rate, ammo, build=[basic_magazine, rapid_rounds, swift_striker, intensifying_magazine, sharpshooter])
defender = Hero("Abrams", 5000, 0, 1, 1)

simulator = CombatSimulator(attacker, defender)
simulator.run_simulation()