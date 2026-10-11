# Derived visibility (prototype)

`tools/derive-visibility.py` derives the world `visibility` regions (format
0.5+) from geometry, so packages need not hand-author `visibility.json`.

1. **Cells.** Recast navmesh from the collision mesh (RFC-0004 capsule),
   4 m columns, one cell per floor level, eyes from crouch (1.0 m) to the
   jump apex (1.7 + 1.27 m).
2. **From-cell visibility** (`pvs.cpp`, run on the bake host): a unit (glTF
   mesh node) is visible from a cell if a forward ray (Fibonacci sphere) or a
   segment to a sample on the unit's surface first hits it. Opaque triangles
   occlude; single-sided back faces do not (the renderer culls them).
3. **Conservative margin.** Each cell's set is unioned with its 26
   neighbours', and units within 2 m of a cell are always visible.
4. **Regions.** Cells with identical sets merge into maximal boxes; each
   visibility class becomes an owner area whose `visibleFrom` lists the
   regions that see it. Units visible from everywhere stay unowned. Outside
   every area, core draws everything.

```
tools/derive-visibility.py dist/com.hyprune.lumen-reach --output /tmp/pvs \
  [--apply /tmp/pvs-package]      # kernel runs on $HYPRUNE_BAKE_HOST (environment or dev.env)
```

Outputs: `visibility.generated.json` (authored format), `report.json`
(comparison with the package's regions at every eye sample), `cells.json`
(per-cell sampled and dilated sets, for maps and for tracing a sight line).

## Lumen Reach 0.7.2 (2026-10-10)

- 1048 navmesh polygons → 702 cells → 153 regions + 7 owner areas; 239 M rays,
  ~20 s on the bake host (51 s end to end). Deterministic for a fixed seed.
- 0 cell eyes where the generated regions hide a sampled-visible unit.
- Nested any-angle (64 views + 5 vault probes, culling on vs off): changed
  pixel fraction 0.0 everywhere.
- Batches submitted (with frustum culling), mean of 64 views: hand-written
  44.7, generated 40.5 (13 fewer, 49 equal, 2 more). Region-culled mean
  3.0 → 13.6.
- Where the generator culls less than the hand-written regions: in the
  Rime Vault, signal-rise stays visible. A sampled segment from the vault
  floor grazes the south stair-door frame (misses by ~4 mm) and reaches
  signal-rise geometry inside the ascent tunnel. That sight line is real but
  sub-pixel; the hand-written region hides signal-rise from the whole vault.
- The vault ceiling stops at z = -76.0 while the floor runs to -74.0: a 2 m
  roof slot along the north wall, open to the sky. Forward rays reach the
  vista and array hall through it.

Limits: sampled rather than exact (dilation and the near rule cover the
gaps); cells are 4 m, so thin occluders between close rooms are not used;
moving objects (`objects`) are not occluders.
