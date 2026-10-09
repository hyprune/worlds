# Lumen Reach 0.7.2 handoff — 2026-10-09

**Release candidate verified; not published, not pushed.** The lead reviews
first. No nested session or bake is left running. Published baseline: 0.7.1
(package kept at `artifacts/any-angle-0.7.2/before/`, SHA-identical to
`reports/release-0.7.1.json`).

Scope (lead direction): two small fixes found by the new navmesh and
route-clearance checks; no redesign.

## Release candidate

- Package: `dist/com.hyprune.lumen-reach/` (third 0.7.2 bake on 10.2.2.2,
  build inputs at `b0ad62d`)
- Manifest SHA256 `9ce52ac96e5fd1ffce5c77b5fa2461ef82233505f5ba6983a0f1fdf2fc414f03`
- Scene SHA256 `12c587d4dda1f87e5fe4d561fcaee3c8c62f72f747f789edfefd114b033f9d40`
- Archive `artifacts/releases/com.hyprune.lumen-reach-0.7.2.tar.zst`,
  46,817,572 bytes, SHA256
  `cb1adac2e85f2d15df2c17af0bb196c8a5a460b7a3a113aac4966b58ed55f33c`
  (`sha256sum -c artifacts/releases/LUMEN-SHA256SUMS` from the repo root).
  All 76 extracted files are identical to `dist/`; the extracted copy passes
  schema 0.5 and core world-check.
- Record: `reports/release.json`; evidence under `reports/any-angle-0.7.2/`.
- Gallery: `screenshots/release-world-v4/lumen-0.7.2-before-after.jpg`
  (exact poses, nested 0.7.1 | nested 0.7.2),
  `lumen-0.7.2-any-angle-contact-sheet.jpg`, and
  `screenshots/navmesh-2026-10-09/lumen-0.7.2-navmesh.png`.

## Fixes

1. **Roof ramp access** (check-navmesh). The final roof ramp's foot sat on
   the y=12 `Roof upper landing`'s open south lip; its rails start 0.5 m up
   the ramp and the slab under the ramp has no headroom, so the only way on
   was a 0.5 m gap between the rail ends and an 8 m drop. Core's capsule
   could overhang the lip (the nested route walk passed); a navmesh agent
   could not, so the whole upper roof was a separate island. The landing now
   extends 1.5 m south (`build.py`) with a parapet and end returns. The
   roof route is on the main navmesh (main area 7,114 -> 7,366 m2) and the
   pin is gone from `navmesh-allow.json`.
2. **Roof bridge member** (check-route-clearance). The render-only `Hall
   service lintel` (`polish.py`, west bay y 34..42, z 17) crossed the roof
   bridge 0.88-1.12 m above the deck. Raised to z 18.4 (2.28 m clear). Both
   pins are gone from `check-route-clearance.py`.
3. **Found while fixing 1-2, same passage.** With the roof joined, the
   navmesh showed the `roof-final>roof-bridge` centreline ran along the
   bridge's south lip, beside an open 1.5 m slot (x -8.5..-7, between the
   ramp and the bridge-run rails) that drops to the ground. Also the
   render-only `Atrium secondary rib` (x -5.8, y 36.8) stood inside the
   1.5 m bridge walkway (0.65 m off the old centreline, so the
   route-clearance lane missed it). The rib now stops under the deck and
   resumes 2.6 m above. `roof-bridge` sits 0.9 m into the bridge, so the
   route clears the slot. `roof-start(-west)` and `roof-final` keep their
   0.7.1 positions at the ramp ends: check-walking samples straight
   node-to-node profiles, and the graph is at core's 64-node limit, so no
   nodes were added.

## Verified on the release package

- `make lumen-validate` PASS, including check-navmesh (only the 0.19 m2
  vault sliver stays allow-listed), check-route-clearance (4 pre-existing
  pins, none on the roof), check-sky, geometry, walking and placement.
- glTF validator 0 errors / 0 warnings; core `hyprune-world-check`
  (core-visibility-bench `0735e4d`, plugin `18f26a66…`, as for 0.7.1).
- Any-angle nested (`artifacts/any-angle-0.7.2/sweep/`): 69 views (66 + the
  new `roof-ramp-foot`, `roof-ramp-foot-eye`, `roof-bridge-eye`), 69/69
  culling pairs unchanged, 6/6 walking probes stop inside, jump stops at
  x=25.64, fly crosses to x=30.28. Streak candidates: maximum 0.012 at
  `rise-corner-sw`, as in 0.7.1.
- Route traversal (`artifacts/any-angle-0.7.2/routes/`): 64 nodes, 126
  directed traversals, 14 alternate stairs, 18 hero stills. PASS.
- Budgets: 245,330 triangles (+804), 99 draws, 277.92 GPU MiB
  (glTF-Transform estimate, +0.09), 372.74 conservative MiB; collision
  5,194 triangles.

## Not fixed (reported, out of scope)

- **The roof walkway is mostly unguarded.** Rails exist only along the
  ramp, the bridge run's west side (x -7) and the new apron. The 1.5 m
  bridge's north edge (z -37.5), its east end, the run's east edge (x -3)
  and the slot opening beside the ramp top drop 8-16 m. Routes keep
  >= 0.6 m from these edges. Railing them is a small, separate decision
  (design: does the rooftop stay open?).
- The landing's west edge (x -20, y 20..24) is also unrailed, as before.
- Unchanged from 0.7.1: minor 0.2 m clearances (roof-ascent-lower landing
  wall, hall-upper mullion, a leaf tip, snow stair wall lamps), the soft
  cloud join of the day seam above ~25 deg fly views.
- Nested harness note: `check-lumen-session.py --routes --output <dir>`
  needs the bake's `artifacts/lumen-reach/views.json` copied into `<dir>`.

## Next steps for the lead

Review the before/after sheet, then push `worlds` and publish
`lumen-reach-v0.7.2` with the archive above; update
`hyprune/worlds/releases.json` in the meta repo with its URL and hash.
Every commit ends with:

```
Co-Authored-By: Krombopulos Michael <Krombopulos.Michael@mail99.me>
```
