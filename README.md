# kitten-deadlock-sim

Proof of concept: an event queue combat simulator used to optimize item builds in Deadlock.

```
python3 main.py
```

## Limits

- Only Vindicta, shooting a target dummy
- Only weapon items, and only the 44 whose effects matter against a dummy. Skipped: Ballistic Enchantment, Berserker,
  Crushing Fists, Melee Charge, Monster Rounds, Silencer, Slowing Bullets, Spellslinger and Split Shot (they need
  abilities, melee, NPCs, incoming damage or more than one target)
- Item and Vindicta stats are from the current patch (Oct 2026)
- Every bullet hits. Headshot % sets how many are headshots (1.65x damage, and they trigger Headshot Booster, Headhunter,
  Weakening Headshot, Crippling Headshot and Spirit Rend's stacks), default 0%
- Actives are used once at the start of the fight, and so are triggered passives like Kinetic Dash's dash-jump
- Headshots and chance procs (Lucky Shot, Tesla Bullets, Capacitor) land on a fixed rhythm instead of randomly, e.g. 25% => every 4th bullet
- Build ranking simulates every valid build when there are up to 50k of them. Past that (e.g. 8 items with no
  budget, ~177M builds) a beam search with a swap pass picks the most promising ones, which matched the exhaustive top 15
  in every test against full runs of up to ~900k builds
- Build-up items (Toxic Bullets, Spiritual Overflow) use the [deadlock.wiki formula](https://deadlock.wiki/Module:Buildup)
- Spirit damage ignores spirit power scaling, and the dummy has no spirit resist of its own
