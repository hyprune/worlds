# Switchyard 0.1.2: authored visibility

The package adopts world format **0.5**. Camera bounds, exclusive glTF subtree
ownership and directed visibility links are authored in [visibility.json](visibility.json).
The exporter resolves stable node names after every bake. The annotation tool can
also update an existing package without rebaking.

Geometry, textures, anchors, collisions, navigation, spawns, work volumes,
lightmaps and route/stair contracts remain unchanged. **70 asset files**
are byte-identical to the preceding package. The manifest changes only version,
formatVersion and visibility. Visibility filtering reduces submissions; it does
not unload textures or reduce allocated GPU memory.

## Regions and sightlines

Concourse and six docks own their existing chunks. Three longitudinal aisles and
a cross aisle have camera bounds but empty ownership lists: the continuous hall
floor is shared. Hall structure, roof vault and vista remain unassigned.

All docks are open-sided. Adjacent station canopies remain visible above the
low screen walls, and the cross aisles preserve long views across the terminal.
All region links therefore retain the neighboring docks. The engine correctly
submits all 134 batches with culling on or off. Claiming a culling gain here would
require removing visible architecture. Enclosed future additions can use the
same ownership and link recipe without changing workspace identity.

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
| 01-concourse | 134 → 134 (0.00%) | 0.401 → 0.382 | 3.875 → 5.561 | 16.660 → 16.663 |
| 03-build | 134 → 134 (0.00%) | 0.511 → 0.515 | 5.833 → 6.356 | 16.662 → 16.651 |
| 04-route | 134 → 134 (0.00%) | 0.457 → 0.439 | 6.156 → 5.507 | 16.667 → 16.661 |

Clock changes and concurrent host activity can move GPU medians even when no
batch count changes. These short paired runs are not a sustained FPS guarantee.
The Switchyard manifest and selected node sets remained unchanged throughout
the final Lumen aperture refinement. Unchanged-count controls also show timing
movement, so no reliable FPS improvement is claimed. Per-block medians and every raw sample are in
[reports/visibility-0.1.2/timing-summary.json](reports/visibility-0.1.2/timing-summary.json)
and `nested.json` beside it.

## Verification and delivery

- World 0.5 schema and core package loading pass; Khronos glTF reports zero
  errors and zero warnings.
- Package UV/material budgets and existing walking/collision/route checks pass. Exclusive subtree ownership and unknown-link checks pass.
- 11 paired 4K views pass the visible-loss comparison, including
  entrances and outside-region fallback. The world viewport is ungraded.
- 87 in-engine camera probes check all region centers,
  inclusive AABB boundaries and authored route points against expected submission
  counts. Regression tests cover directed links, overlap, outside fallback and
  conflicting subtree assignments.
- All nested runs hold `/tmp/worldshell-nested.lock` and use verified disposable
  PID/socket/config identities. The host session was never controlled. No Blender
  process was needed for this metadata-only pass.

A shared in-progress core binary initially failed shader compilation. Measurements
therefore use a separately built, clean checkout of published core
`2494c136ab43c55f20084514e7ae3799ef75822a`; loaded plugin SHA256 is
`c3a8c3d79933ade9a12d1a53b1ee3dc88b2f0d1b48fe1e61685cd0160a6cad1e`. Core's active checkout was not edited.

Archive: `artifacts/releases/com.hyprune.switchyard-0.1.2.tar.zst`
SHA256: `e041570442de717f3cbb36ca252977b47732ba873f014a8ba78c06ada370e7fd`
Every extracted file matches the package.

To reproduce with the retained isolated build:

```sh
make visibility-annotate
make visibility-validate
make visibility-nested VISIBILITY_CORE=../core-visibility-bench
```
