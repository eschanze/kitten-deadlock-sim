from dataclasses import replace

from heroes import target_dummy, vindicta
from items import burst_fire, sharpshooter
from sim import CombatSimulator

BUILD = [sharpshooter, burst_fire]
DISTANCE = 30  # meters
TARGET_HEALTH = 3000

# how much dps is lost with a shorter max range (45m) compared to vindicta's default (64m)
SHORT_MAX_RANGE = 45
DEFAULT_MAX_RANGE = 64


def simulate_dps(max_range: float) -> float:
    # replace() rebuilds the hero, so its derived stats are recalculated too
    attacker = replace(vindicta(BUILD), max_range=max_range)
    simulator = CombatSimulator(attacker, target_dummy(TARGET_HEALTH), distance_to_target=DISTANCE, verbose=False)
    return simulator.run().dps


def run() -> None:
    short_dps = simulate_dps(SHORT_MAX_RANGE)
    default_dps = simulate_dps(DEFAULT_MAX_RANGE)

    print(f"[*] {SHORT_MAX_RANGE}m max range @ {DISTANCE}m => {short_dps:.2f} dps")
    print(f"[*] {DEFAULT_MAX_RANGE}m max range @ {DISTANCE}m => {default_dps:.2f} dps")
    print(f"[+] dps loss => {(1 - short_dps / default_dps) * 100:.3f}%")


if __name__ == "__main__":
    run()
