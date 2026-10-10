# Lumen Reach 0.7.0 — any-angle environment and playable bounds

Prepared locally for owner review. **No push or GitHub release was performed.**
The 0.6.1 report is preserved in [delivery-0.6.1.md](delivery-0.6.1.md) and
[release-0.6.1.json](release-0.6.1.json).

0.7.0 is a playability release. The world holds up from any reachable angle and
keeps walkers inside the authored settlement without blocking ordinary fly.

- Closed day sky sphere and closed cold-basin sky inside a textured mountain shell
  (the 40 m flat lid is gone). Solid valley shelves, cliff foundations, aqueduct
  and spire bodies replace cards that showed holes from off-route angles.
- Roofing, copings, soffits and repaired ramp winding; lit stair undersides.
- Per-home/connector footprints in `playable-volumes.json` generate
  collision-only perimeter backstops plus guard collision on visible rails.
  Each <=2 m backstop piece rises 2.5 m above the highest walkable top within 3 m
  inside it (370 pieces, tops -3.5…24.1 m). Core's jump lifts feet 1.27 m, so
  walking and jumping stop inside while ordinary fly (collision on) passes over.
- Supported aprons at the two alternate-stair starts.

Format stays **0.5**. No new required extension.

## Validation (sixth bake, manifest `f7b53674…`, scene `00f8a832…`)

| Check | Result |
| --- | --- |
| `make lumen-validate` (sky/geometry, visibility, schema 0.5, package, placement, walking, emissive, decals) | PASS |
| glTF validator | 0 errors, 0 warnings |
| core `hyprune-world-check` (bench `0735e4d`) | PASS |
| Any-angle nested sweep: 9 owner poses, 4 homes, 11 targeted, 32 seeded random views | 56/56 culling on/off pairs unchanged |
| Walking boundary probes (6) | all stop inside |
| Repeated jump at court east | stops at x=25.64 (limit 26) |
| Ordinary fly at 6 m eye over court east | crosses to x=30.28 |
| Route traversal: 64 nodes, 126 directed traversals, 140 traversed, 14 alternate stairs | PASS |
| 18 hero stills at matched 60° poses | PASS |

Evidence: [release-session-summary.json](any-angle-0.7.0/release-session-summary.json),
[release-routes-summary.json](any-angle-0.7.0/release-routes-summary.json),
[playable-boundary-report.json](any-angle-0.7.0/playable-boundary-report.json).
Raw 4K captures are under `artifacts/any-angle-0.7.0/{iteration-4,routes-final}/`.
All nested testing used core's private state under the shared flock.

Visual review notes: `rise-exterior` is an inspection pose pressed against the
mountain shell crown (rock and snow, no sky through, so not a hole). Two
elevated views inside the basin sky show its flat upper night band, matching
the texture. Out of scope for 0.7.0 by the owner's direction: crown smoothing,
panorama resolution and bridge joint aesthetics.

## Budgets

| | 0.6.1 | 0.7.0 |
| --- | ---: | ---: |
| Visible triangles | 222,403 | 244,312 |
| Unfiltered material batches | 87 | 99 |
| Conservative GPU MiB | 326.20 | 372.62 |

Matched home poses, native 4K, Intel, Medium, fixed 0.5 scale, 32 samples.
0.6.1 baseline from `artifacts/any-angle-0.7.0/{before-engine,before-cold-homes}/`.

| Home | GPU pass sum ms 0.6.1 → 0.7.0 | Frame ms 0.7.0 |
| --- | ---: | ---: |
| 01-sun-court | 8.21 → 7.52 | 16.66 |
| 02-array-hall | 9.11 → 8.26 | 16.67 |
| 03-rime-vault | 14.35 → 13.85 | 16.67 |
| 04-signal-rise | 12.52 → 8.53 | 16.66 |

Delivered cadence stays at 60 Hz; GPU deltas include clock/host noise.

## Archive

`artifacts/releases/com.hyprune.lumen-reach-0.7.0.tar.zst`
(47,941,863 bytes)

SHA256 `31a1449cb76ee2ed97cba33b0b55a3d6dcc91f23646fbe3ec7f3bdf679b0666d`

All 76 extracted files are identical to the package; the extracted copy passes
schema 0.5 and core world-check. Gallery: `screenshots/release-world-v4/`.
