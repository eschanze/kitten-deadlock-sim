# kitten-deadlock-sim

Proof of concept: an event queue combat simulator used to optimize item builds in Deadlock.

```
python3 main.py
```

## Limits

- Only Vindicta, shooting a target dummy
- Only weapon items, and only the ones whose passives matter against a dummy (no actives, spirit damage, mobility or melee)
- Item and Vindicta stats are from the current patch (Oct 2026)
- Every bullet hits, no headshots
- Actives are used once at the start of the fight
