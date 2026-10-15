# kitten-deadlock-sim

Proof of concept: an event queue combat simulator used to optimize item builds in Deadlock.

```
python3 main.py
```

Or open `web/index.html` in a browser for a standalone web view (no server needed).

## Limits

- Only Vindicta, shooting a target dummy
- Only weapon items, and only the ones whose passives matter against a dummy (no actives, spirit damage, mobility or melee)
- Item and Vindicta stats are from the current patch (Oct 2026), except `web/index.html`, which is still on the old data
- Every bullet hits, no headshots
- Actives are used once at the start of the fight
