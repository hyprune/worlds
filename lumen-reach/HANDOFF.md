# Lumen Reach 0.9.0 handoff — 2026-10-10

**Release candidate verified; not published, not pushed.** Published
baseline: 0.8.1 (release package at `artifacts/opt-0.9.0/before/`, source at
`before-src/`; record `reports/release-0.8.1.json`).

Lead decisions implemented: derived visibility as a build step; per-area
playable volumes (format 0.6+) with maxFlyHeight 60 m; only walking backstops.

## Release candidate

- Release package `dist-07/com.hyprune.lumen-reach/` (format 0.7) from the
  source `dist/` (format 0.6) built at `ff5e8d3`.
- Manifest SHA256 `375478640875…` (full hashes in `reports/release.json`).
- Archive `artifacts/releases/com.hyprune.lumen-reach-0.9.0.tar.zst`,
  39,733,854 bytes, SHA256
  `52fc38bf3ce95643ee26e7acdd9b216a7334f36b32b175cbe40bbedbc779dda2`.
  76 extracted files identical to `dist-07/`; schema 0.7 VALID; core
  world-check PASS.
- Built by `make lumen-release LUMEN_PERF_BASELINE=artifacts/opt-0.9.0/before`
  end to end (38.5 min).
- Core: the meta repo's pin `35ace21`. My `core-optimise` worktree now sits
  there (`OPTIMISE_CORE`).
- Gallery: `screenshots/optimise-2026-10/lumen-0.9.0-perimeter-and-playable.png`.

## Changes

1. **Derived visibility** (`make lumen-build` runs `tools/derive-visibility.py
   --in-place` after the bake, about 106 s with the kernel on the bake host).
   - Result: 805 cells, 184 areas, 0 of 29,781 eye samples hide a
     sampled-visible unit.
   - `check-visibility --spec` verifies reproducibility. The hand-written
     spec is `lumen-reach/visibility.hand-written.json` (fixture/reference).
   - Fix found on the way: cells sampled a 3x3 grid per 4 m column, so small
     raised floors (landings, platforms) got no cell and 49 m2 of walkable
     floor sat outside every region (check-navmesh). Cells now also sample
     every polygon's centroid and inset corners.
2. **Canonical contract + playable volumes**.
   - `lumen-reach/contract.py` writes canonical `areas[]`, anchor mounts,
     `dataObjects` and `placementZones` (core reads area volumes only from
     canonical areas and rejects mixing them with the legacy extension).
   - The 13 `playable-volumes.json` footprints become 12 per-area boxes
     (connectors join a neighbour), plus a world `maxFlyHeight` of 60. The
     source is format 0.6.
   - `tools/world_contract.py` lets the checks read either shape.
3. **Walking backstops only**. Backstop heights now count only tops a walker
   can reach (route/stair seeded, jump/drop expanded).

   | | 0.8.1 | 0.9.0 |
   |---|---|---|
   | pieces over 15 m | 71 | 17 |
   | max height | 24.1 m | 19.5 m |
   | mean height | 9.5 m | 6.6 m |

   The 17 left ring the facade rooftop, which the roof route reaches on foot.
   Guard rails and walking collision are unchanged.

## Verified

- `make lumen-validate` PASS on the source: all gates; schema 0.6;
  check-visibility against the generated spec; navmesh with an empty
  allow-list.
- verify.mjs PASS; schema 0.7; core world-check (`35ace21`): 4 areas, 24
  anchors, 37 objects, 4 placement zones, 0 warnings.
- Any-angle nested (core 35ace21): 72 views, 0 culling losses.
  - 6/6 walking probes stop inside; jump x=25.64.
  - Fly is now bounded: x=26.50 at the court's east bound (26 + 0.5
    allowance), y=60.50 at the ceiling (60 + 0.5).
- Route traversal: 64 nodes, 126 directed traversals, 14 alternate stairs,
  18 stills.
- Visibility vs 0.8.1 (same 72 poses): batches 44.2 -> 40.4. Culled vs
  unculled identical 72/72 (0.8.1: 71/72).
- Perf gate vs 0.8.1, same session: p50 8.923 -> 8.934 ms (+0.1 %), p95
  10.264 -> 10.340 ms (+0.7 %): PASS. Record `reports/perf/0.9.0.json`.

## Notes

- The any-angle sweep expects bounded fly whenever a world declares
  `playable`; worlds without it keep the old pass-over expectation.
- Long jobs: `make lumen-release` takes about 40 min (the perf gate is about
  26). A single foreground tool call is capped at 10 min here, so I ran it
  detached and watched it in under-10-minute foreground chunks.

## Next steps for the lead

Review, then push `worlds` and publish `lumen-reach-v0.9.0`; update
`hyprune/worlds/releases.json`. Requires a core that loads format 0.7 and
honours 0.6 playable (the pinned `35ace21`).

---

# (previous) Lumen Reach 0.8.1 handoff — 2026-10-10

**Patch release candidate verified; not published, not pushed.** Published
baseline: 0.8.0 (release package kept at `artifacts/opt-0.8.1/before/`,
SHA-identical to `reports/release-0.8.0.json`; source at `before-src/`).

## Release candidate

- Release package `dist-07/com.hyprune.lumen-reach/` (format 0.7) from the
  source `dist/` baked on the bake host at `1f21028`.
- Manifest SHA256 `4f047839cbd6…` (full hashes in `reports/release.json`).
- Archive `artifacts/releases/com.hyprune.lumen-reach-0.8.1.tar.zst`,
  39,736,290 bytes, SHA256
  `d86878a981ed38ee851a6bc09aa545dcea781345d65cce604313c8fe71617766`.
  76 extracted files identical to `dist-07/`; schema 0.7 VALID; core
  world-check (`49c8408`) PASS. Built by `make lumen-release
  LUMEN_PERF_BASELINE=artifacts/opt-0.8.1/before` end to end (38 min).
- Gallery: `screenshots/optimise-2026-10/lumen-0.8.1-vault-slot-before-after.jpg`.

## Fix

**Rime Vault ceiling slot.** The vault ceiling and both side shells stopped at
authoring y 76; the floor runs to 74. That left a 2 m strip open to the sky
over the descent threshold and the north lip. It was visible from reachable
positions: looking up from the vault spawn showed day sky overhead (nested
`vault-north-up`). They now reach y 74. The wide north opening onto the vista
is designed and unchanged.

**Check extended.** `check-sky.py --enclosures lumen-reach/enclosures.json`
(in `lumen-validate`): declared indoor rooms (rime-vault, connector-descent,
entry-vestibule) with their designed open faces. From every walkable eye
inside, an upper-hemisphere ray that reaches the sky must leave through an
open face. 0.8.0 FAILS (rime-vault: 290 sky rays from 49 eyes, out through
the roof and west side of the strip); 0.8.1 PASSES (0 leaks). Side effect:
the 0.19 m2 walkable sliver outside the visibility areas was the east end of
the same lip; `check-navmesh` flagged its pin as stale. Lumen now has no
pinned navmesh findings.

## Verified (0.8.1 release package unless noted)

- `make lumen-validate` PASS on the source (all gates, enclosures included).
- verify.mjs PASS (indices unchanged, collision within 2.1 mm).
- Any-angle nested: 72 views (+3 vault views), 0 culling losses, 6/6 walking
  probes inside, jump x=25.64, fly x=30.27.
- Route traversal: 64 nodes, 126 directed traversals, 14 alternate stairs.
- Perf gate vs 0.8.0, same session: p50 9.116 -> 9.132 ms (+0.2 %), p95
  10.419 -> 10.496 ms (+0.7 %): PASS. Record `reports/perf/0.8.1.json`.

## Derived visibility evaluation

`reports/any-angle-0.8.1/visibility-evaluation.md`: hand-written vs
`tools/derive-visibility.py` on the 0.8.1 release package, same 72 views.

- Batches: 44.2 -> 40.4 (-8.6 %); some poses -45 %.
- Identical frames: 72/72 for derived vs 71/72 for hand-written (the
  hand-written vault region hides a real sub-pixel sight line).
- GPU ms along the routes: unchanged (fill-bound).

Recommendation: switch to derived visibility in 0.9.0 as a build step, for
correctness and maintenance; 0.8.1 keeps the hand-written regions.

## Next steps for the lead

Review the sheet, then push `worlds` and publish `lumen-reach-v0.8.1` with the
archive above. Update `hyprune/worlds/releases.json`. Decide on derived
visibility for 0.9.0.

---

# (previous) Lumen Reach 0.8.0 handoff — 2026-10-10

**Release candidate verified; not published, not pushed.** First release on
world format 0.7. Published baseline: 0.7.2 (package kept at
`artifacts/opt-0.8.0/before/`, SHA-identical to `reports/release-0.7.2.json`).

Scope (owner's overnight direction): the remaining proven third-party
optimisations from `core/docs/research/2026-10-proven-techniques.md`. No
content changes beyond lightmap samplers. Full write-up with numbers:
`reports/optimise-0.8.0/README.md`.

## Release candidate

- Release package: `dist-07/com.hyprune.lumen-reach/` (format 0.7), the
  deterministic optimisation of the source package `dist/` (format 0.5, baked
  on the bake host from build inputs at `f5e8b82`).
- Manifest SHA256 `68632d462d9077ef…`, scene SHA256 `50c03d10094d1a30…`
  (full hashes in `reports/release.json`).
- Archive `artifacts/releases/com.hyprune.lumen-reach-0.8.0.tar.zst`,
  39,390,230 bytes, SHA256
  `3b507f8ba151c99983496d82a413526b3090e0c38057a841b54ee2758dcb27e1`
  (`sha256sum -c artifacts/releases/LUMEN-SHA256SUMS` from the repo root).
  76 extracted files identical to `dist-07/`; schema 0.7 VALID; core
  world-check PASS.
- Built by `make lumen-release LUMEN_PERF_BASELINE=artifacts/opt-0.8.0/before
  LUMEN_BASELINE=artifacts/opt-0.8.0/before` end to end (42 min).
- Core for every check and nested run: worktree `core-optimise` at `49c8408`
  (the commit the meta repo pins), plugin `a98e051d…`. `OPTIMISE_CORE` in the
  Makefile points there; set it to any build of the pinned core.
- Gallery `screenshots/optimise-2026-10/`: `lumen-0.8.0-before-after.jpg`
  (0.7.2 | 0.8.0 | CIEDE2000 heatmap | 1:1 crop of the worst block),
  `lumen-0.8.0-lightmap-mips-ab.jpg`, `lumen-0.8.0-any-angle-contact-sheet.jpg`.

## Results (0.8.0 release vs 0.7.2, nested, same session)

| | 0.7.2 | 0.8.0 | |
|---|---|---|---|
| package | 70.46 MiB | 41.37 MiB | -41 % |
| archive | 46.8 MB | 39.4 MB | -16 % |
| GPU memory | 270.5 MiB | 149.8 MiB | -45 % |
| load to ready (warm) | 2.68 s | 2.06 s | -23 % |
| GPU ms, 4 spawn poses | 9.43 | 9.40 | noise |
| route p50 / p95 GPU ms | 9.04 / 10.55 | 9.07 / 10.51 | noise |
| PSNR / mean dE2000 | | 36.2-41.3 dB / 0.53-0.87 | worst blocks equal at 1:1 |

1. **Format 0.7 build**: in `make lumen-release` (validate source -> remote
   optimise + verify -> schema 0.7 + world-check -> perf gate -> budgets ->
   archive). Switchyard's `optimize` stays behind `HYPRUNE_FORMAT_07=1`.
2. **Lightmap mips**: on for the six 4 px-gutter groups (not foliage).
   Shimmer on affected pixels -4.4 % (Sun Court), about 0 elsewhere. No memory
   or visual cost. Included.
3. **xatlas**: not adopted. It isn't clearly better than smart_project, and
   the lever is elsewhere: sub-2x2-texel charts take 34-43 % of each large
   atlas (`reports/optimise-0.8.0/uv-charting/`).
4. **Perf gate**: `make lumen-perf-gate`, in `lumen-release`. PASS (+0.4 % /
   -0.4 %). Record `reports/perf/0.8.0.json` is the next baseline when the
   same core build is used; otherwise pass `LUMEN_PERF_BASELINE=<0.8.0 package>`.

## Verified

- `make lumen-validate` PASS on the source package (all gates incl. navmesh,
  sky, route clearance; only the 0.19 m2 vault sliver allow-listed).
- `verify.mjs` PASS: 301 nodes / 106 materials / 78 lightmap bindings keep
  their indices; collision within 2.1 mm.
- Any-angle nested on the release package: 69 views, 0 culling losses, 6/6
  walking probes inside, jump x=25.64, fly x=30.27.
- Route traversal on the release package: 64 nodes, 126 directed
  traversals, 14 alternate stairs, 18 hero stills. PASS.

## Notes and open items

- The Python checks read format 0.5 only; validation runs on the source
  package and verify.mjs proves the release copy equivalent.
- The settled dynamic-resolution scale holds at 0.5 on Intel 4K for both
  releases (inside core's 10 ms budget band). It is a tripwire; GPU ms
  p50/p95 are the sensitive gate.
- Per-round GPU spread is about +/-5 % when several packages share a session
  (A/A on one package is ~1 %). Small GPU deltas are noise.
- The nested lock is shared with other agents overnight (core perf,
  shell upscaler); my runs queued behind them. Timings were taken while
  holding the lock.
- Remaining residual shimmer is material-texture and thin-geometry aliasing,
  not lightmaps.
- Not done: the stage-3 "small props without atlas space" work that the
  xatlas evaluation points to (needs a probe/vertex-AO path, which is a format
  question for the lead).

## Next steps for the lead

Review the sheets, then push `worlds` and publish `lumen-reach-v0.8.0` with
the archive above. Update `hyprune/worlds/releases.json` in the meta repo with
its URL and hash. It requires a core that loads format 0.7 (`49c8408`+).
