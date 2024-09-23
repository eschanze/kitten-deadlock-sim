import combinations
import replace
from heroes import target_dummy, vindicta
from items import basic_magazine, intensifying_magazine, rapid_rounds, sharpshooter, swift_striker
from sim import CombatSimulator

SAMPLE_BUILD = [basic_magazine, rapid_rounds, swift_striker, intensifying_magazine, sharpshooter]
TARGET_HEALTH = 5000


def simulate_sample_build() -> None:
    attacker = vindicta(SAMPLE_BUILD)
    defender = target_dummy(TARGET_HEALTH)
    CombatSimulator(attacker, defender).run()


MENU_OPTIONS = {
    "1": ("simulate sample build", simulate_sample_build),
    "2": ("rank builds", combinations.run),
    "3": ("find best item replacement", replace.run),
}


def show_menu() -> None:
    print("\n[*] kitten deadlock sim")
    for key, (label, _) in MENU_OPTIONS.items():
        print(f"    {key} => {label}")
    print("    q => quit")


def main() -> None:
    while True:
        show_menu()
        choice = input("[?] option => ").strip().lower()
        if choice == "q":
            break

        option = MENU_OPTIONS.get(choice)
        if option is None:
            print(f"[-] invalid option => {choice}")
            continue

        _, action = option
        action()


if __name__ == "__main__":
    main()
