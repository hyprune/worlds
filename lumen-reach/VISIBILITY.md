# Lumen Reach visibility

**Since 0.9.0 the regions are derived, not authored.** `make lumen-build` runs
`tools/derive-visibility.py --in-place` on the baked package (Recast cells over
the collision navmesh, from-cell ray visibility on the bake host; see
`tools/pvs/README.md`). `check-visibility.py --spec
artifacts/lumen-reach/pvs/visibility.generated.json` checks reproducibility, and
the any-angle sweep's culling on/off pairs check that no visible geometry is
culled. The hand-written spec below is kept as
[visibility.hand-written.json](visibility.hand-written.json): a reference and
test fixture, no longer used by the build. Evaluation:
`reports/any-angle-0.8.1/visibility-evaluation.md`.

---

## Before 0.9.0 (0.6.1-0.8.1): authored visibility

The package adopts world format **0.5**. Camera bounds, exclusive glTF subtree
ownership and directed visibility links are authored in [visibility.hand-written.json](visibility.hand-written.json).
The exporter resolves stable node names after every bake. The annotation tool can
also update an existing package without rebaking.

Geometry, textures, anchors, collisions, navigation, spawns, work volumes,
lightmaps and route/stair contracts remain unchanged. **74 asset files**
are byte-identical to the preceding package. The manifest changes only version,
formatVersion and visibility. Visibility filtering reduces submissions; it does
not unload textures or reduce allocated GPU memory.

## Regions and sightlines

Each home owns its existing mesh chunk. The descending and ascending connectors
own independent chunks. Empty ownership lists describe the Court entrance, exposed east edge, upper
terraces and vestibule where geometry already belongs to another chunk.
Foliage and vistas remain shared and always visible.

The Court entrance sightline deliberately overestimates the aperture view cone:
most of the west approach can see part of the service shell through Array Hall.
The east Court also retains the above-grade shell and a narrow ascending-tunnel
edge around the facade pier. The
combined shell/interior chunk is therefore kept conservatively throughout the
Court; this pass does not split or rebake that asset. Both sides of
entrances overlap so the visible sets union before a crossing. The Vault retains
Sun Court/Array Hall silhouettes through its wide north opening and the far
ascending tunnel mouth. The opaque rock divide blocks Signal Rise from the
Vault and the buried rooms from the snow basin. Links are explicit and directed;
there is no transitive portal traversal.

Region bounds select camera membership, not geometry containment. Overlap unions
the visible sets; outside all regions everything draws. No collision, navigation,
application screen or HUD is removed by this metadata.

## Paired Intel measurements

Native output **3840×2160**, Intel PTL, **Low** preset (the legacy `intel` mapping),
fixed **0.5 internal world scale**, dynamic resolution disabled and offload off.
The camera is held by a granted IPC 0.13 photo session. Outline is disabled to
measure the region change alone. Each view uses four warm-up/sample blocks in
**off/on/on/off** order, with **64 samples per state**. These are core render
measurements; GPU pass sums exclude the host compositor. Delivered frame time is
reported separately and can remain at the 60 Hz presentation interval.

| Matched view | World submissions off → on (saved) | CPU render ms | GPU pass sum ms | Delivered frame ms |
| --- | ---: | ---: | ---: | ---: |
| 01-sun-court | 87 → 84 (3.45%) | 0.320 → 0.288 | 5.459 → 4.785 | 16.669 → 16.670 |
| 02-array-hall | 87 → 84 (3.45%) | 0.266 → 0.263 | 5.881 → 6.523 | 16.667 → 16.666 |
| 03-rime-vault | 87 → 73 (16.09%) | 0.275 → 0.246 | 5.480 → 4.582 | 16.667 → 16.672 |
| 04-signal-rise | 87 → 68 (21.84%) | 0.274 → 0.219 | 4.285 → 4.302 | 16.671 → 16.661 |
| court-east | 87 → 87 (0.00%) | 0.348 → 0.280 | 7.331 → 7.231 | 16.668 → 16.664 |

Clock changes and concurrent host activity can move GPU medians even when no
batch count changes. These short paired runs are not a sustained FPS guarantee.
The final Court-edge refinement was remeasured. Other views are reused only
after verifying that the final metadata selects exactly the same glTF nodes;
each record retains its measured manifest hash and phase. All final Lumen region
and route probes were rerun. Unchanged-count controls also show timing movement,
so no reliable FPS improvement is claimed. Per-block medians and every raw sample are in
[reports/visibility-0.6.1/timing-summary.json](reports/visibility-0.6.1/timing-summary.json)
and `nested.json` beside it.

## Verification and delivery

- World 0.5 schema and core package loading pass; Khronos glTF reports zero
  errors and zero warnings.
- Package UV/material budgets and existing walking/collision/route checks pass. Exclusive subtree ownership and unknown-link checks pass.
- 30 paired 4K views pass the visible-loss comparison, including
  entrances and outside-region fallback. The world viewport is ungraded.
- 134 in-engine camera probes check all region centers,
  inclusive AABB boundaries and authored route points against expected submission
  counts. Regression tests cover directed links, overlap, outside fallback and
  conflicting subtree assignments.
- All nested runs hold `/tmp/worldshell-nested.lock` and use verified disposable
  PID/socket/config identities. The real session was never controlled. No Blender
  process was needed for this metadata-only pass.

A shared in-progress core binary initially failed shader compilation. Measurements
therefore use a separately built, clean checkout of published core
`2494c136ab43c55f20084514e7ae3799ef75822a`; loaded plugin SHA256 is
`c3a8c3d79933ade9a12d1a53b1ee3dc88b2f0d1b48fe1e61685cd0160a6cad1e`. Core's active checkout was not edited.

Archive: `/home/rick/workspace/hyprune/worlds/artifacts/releases/com.hyprune.lumen-reach-0.6.1.tar.zst`
SHA256: `f0bf4f25abe4db0bda0029128d75404da011be5cc7194a9c4e0e68306a39e616`
Every extracted file matches the package; no release or push was performed.

To reproduce with the retained isolated build:

```sh
make visibility-annotate
make visibility-validate
make visibility-nested VISIBILITY_CORE=../core-visibility-bench
```
