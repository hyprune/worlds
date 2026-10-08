# Lumen Reach 0.5.0 — visual polish v2

Four connected, original workspace homes. This delivery keeps all 24 mounts,
four free-placement volumes, 64 route nodes, 63 bidirectional edges and 14
alternate stair flights. The former release is documented in
[delivery-0.4.0.md](delivery-0.4.0.md).

## Changes by home

- **Sun Court:** supported entrance jambs and seated light backplates; facade
  maintenance plates, drains, vents and fasteners; canopy seams, power leads,
  luminaires, Reach-marked repair cases, service hatches and red foliage.
  Entry fixtures have a dedicated close engine view. Pier/lintel overlaps and
  the vestibule's overlapping ground face are removed.
- **Array Hall:** ribbed architectural bays and collars, populated rack drawers
  and indicators, service cabinets, balcony structure, suspended ring housing,
  banners and backed signs. Physical watershed spires and a sculpted rock divide
  replace the flat blank mass in the rear vista. Warm lighting is retained.
- **Rime Vault:** large frosted coolant trunks, flanges and hangers; bundled
  cables and trays; ice pendants, reinforced service panels, pump cabinets,
  keyboards, Reach-marked cases and local grated/hazard floor panels. Blue fill
  and warm grazing lights reveal the service detail while keeping a cold room.
- **Signal Rise:** a deeper reflector with front seams, radial/back hoop ribs,
  a feed horn, three struts and trunnions; snowbanks and near rock crags; frosted
  ledges, vents, icicles, cases and hanging gantry cables. Overlapping fortress
  pier/crown faces are removed. Blue night and amber/red practicals remain distinct.

Every lit physical material has a base-color texture. Eleven generated masters,
periodic 640px PBR derivatives and an eight-band trim sheet have prompt/hash
provenance. The new rock master used built-in imagegen; the exact prompt and
SHA256 are in [generation.json](../materials/generation.json). Explicit glTF
factors preserve red canvas, foliage and dark housings that the exporter otherwise
washed out. No world names or marks were borrowed from the reference lettering.

## Budgets

| Measurement | 0.4.0 | 0.5.0 |
| --- | ---: | ---: |
| Visible triangles | 210,067 | 199,911 |
| World draw estimate | 65 | 84 |
| Conservative world GPU MiB | 272.45 | 285.62 |
| Package MiB | 55.13 | 57.81 |

Draws count visible glTF primitives only, excluding applications, HUD and
postprocessing. Geometry is merged by material within four home chunks plus
two independently baked connector chunks; foliage and distant artwork are
separate. Reduced small-part tessellation pays for the added kit detail. GPU
accounting includes all mip levels, separate color/data views and expanded
40-byte vertices. Core currently has no runtime LOD or chunk culling; this gap
is recorded in [NOTES-rfc-gaps.md](../../NOTES-rfc-gaps.md).

The tour's sampled nested process peak is
**765.63 MiB GTT** across
103 samples. This includes compositor/output and
imported application buffers and is separate from the world allocation.

## Automated engine verification

Core's nested harness ran under `/tmp/worldshell-nested.lock`, with the actual
**Medium** preset on **Mesa Intel(R) Graphics (PTL)**.
The 4K output stayed native; dynamic render scale was recorded. Thirty IPC timing
samples per stationary home view produced these observations:

| Home | Rendered frames/s | Median GPU pass sum ms | Render scales |
| --- | ---: | ---: | --- |
| sun-court | 59.88 | 8.697 | 0.4375 |
| array-hall | 59.94 | 7.018 | 0.5 |
| rime-vault | 60.31 | 8.054 | 0.5 |
| signal-rise | 60.06 | 6.892 | 0.5, 0.5625 |

These short samples are not a sustained whole-route FPS guarantee. Exact samples,
loaded plugin hashes and the core working-tree state are preserved in
[polish-v2/v2-4k-nested.json](polish-v2/v2-4k-nested.json). Core was being developed
concurrently; the loaded binary hashes identify what actually ran.

Schema 0.2, glTF (zero errors/warnings), UV1 packing, texture provenance/tints,
all mount rectangles and two requested window sizes, reserved-volume interiors,
walking support and capsule checks pass. All **126 directed graph traversals**
and **14 alternate stair flights** pass in-engine. The narrow-emitter checker
passes; the named authoring audit seats **175 strips** and backs **173 signs/marks**.
The original scene had 48 narrow-emitter overlap probe hits. The new 2cm-lens
regression checks cover all three axes. Switchyard 0.1.1 was rebuilt remotely
and its complete validation suite passed.

## Delivery paths

- Stills: `/home/rick/workspace/rick-the-alien/worldshell-gallery/screenshots/release-world-v2`
- Tour: `/home/rick/workspace/rick-the-alien/worldshell-gallery/videos/release-world-tour-v2.mp4`
- Metadata: `/home/rick/workspace/rick-the-alien/worldshell-gallery/videos/release-world-tour-v2.json`
- Installable archive: `/home/rick/workspace/hyprune/worlds/artifacts/releases/com.hyprune.lumen-reach-0.5.0.tar.zst`
- Archive SHA256: `d730d3867bc3a89bfb88a0540458999a22206b7c6f9891ed3f1a36cf54b9181c`
- Archive size: **36.70 MiB**
- Tour: **83.50s, 1920×1080, 30 fps**, real placed terminals and mounted
  workspace content, actual input and the shell HUD.

The sixteen engine stills include twelve unchanged comparison poses and four
additional detail views. They are ungraded. The tour was encoded in `/tmp`,
inspected, then copied to a staging file and atomically moved into the gallery.
The gallery autocommit process was left untouched.
All Blender execution used `tools/remote-blender.sh` on 10.2.2.2. The owner's
real session was never controlled. Worlds commits remain local; no push,
GitHub release or publication was performed by this work.

The concept review is [RENDER-REVIEW.md](../RENDER-REVIEW.md). The delivered
geometry remains stylized and less densely detailed than the painted concepts;
large work approaches stay intentionally open. Steam, baked lighting and vistas
are static; unusual high views can still expose the night enclosure. These
limits remain visible in the raw evidence.
