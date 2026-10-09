# Lumen Reach 0.7.1 handoff — 2026-10-09

**Release candidate verified; not published, not pushed.** The lead reviews
first. No nested session or bake is left running. Published baseline: 0.7.0
(original package kept at `artifacts/any-angle-0.7.1/before/`, SHA-identical
to the 0.7.0 record in `reports/release-0.7.0.json`).

Scope (owner direction): fix only the three defects from the owner's 0.7.0
live walk; playable over glossy, no redesign.

## Release candidate

- Package: `dist/com.hyprune.lumen-reach/` (fourth 0.7.1 bake on 10.2.2.2,
  build inputs at `2dfd3dd`)
- Manifest SHA256 `15e18acc05200e6fb90bd9d084c8105ae0b165f6cd54972bb4667c34da8a6af2`
- Scene SHA256 `ff8e95bf3f11ddf76b444b2764c4a7d73d82973b8d53a05c967894e88790ab73`
- Archive `artifacts/releases/com.hyprune.lumen-reach-0.7.1.tar.zst`,
  46,888,010 bytes, SHA256
  `326406931e5b8c9cebb6e385cc1aed9303a0f7a47141048fdeec8eb0738e2549`.
  All 76 extracted files are identical to `dist/`; the extracted copy passes
  schema 0.5 and core world-check.
- Record: `reports/release.json`; evidence under `reports/any-angle-0.7.1/`.
- Gallery (`screenshots/release-world-v4/`): `lumen-0.7.1-before-after.jpg`
  (owner live | nested 0.7.0 | nested 0.7.1 at the exact capture poses) and
  `lumen-0.7.1-any-angle-contact-sheet.jpg`.

## Causes and fixes

1. **Day panorama doubled/ghosted** (capture-1791554896814). Not two layers:
   `materials/sky.py` "healed" the longitude seam by cross-fading each edge
   with its *mirror* (48 columns) and adding every row's full seam offset as
   a ramp across the whole width. That superimposed a mirrored ghost and
   row streaks, and the seam (u=0) faced due south, centred in the Sun
   Court's main view. A bilinear software reprojection of the texture alone
   reproduced the capture. Fix: low-pass seam join (no detail blended),
   gradual cloud-row softening above the peaks, uniform polar rows; the
   sphere's seam now faces the Signal massif (`DAY_SEAM`), which hides the
   seam's landscape rows from every walkable eye. The grey wavy bands were
   the terrain disk's outer shelves (r >= 174 m) cresting near eye level;
   they now fall away as a bowl, >= 13.9 deg below every walkable eye.
   Side effect: the painting is rotated ~161 deg, so every direction shows
   a different part of it (the Court's south view now shows its centre).
2. **Snow-service stair capped** (…572827, …584009, …632233). The 0.7.0
   "Rise cliff foundations" rock block (top at z −0.38 over the whole yard)
   capped the passage; its south slope plus the mountain shell walled the
   bottom; the closed night sky crossed it (the blue rectangle). All are
   render-only, so collision route harnesses walked through. Fix: a declared
   portal (`portals.json`) bisects and deletes exactly the shell faces inside
   the passage (cut edges hidden in its walls, slab and ceiling). Opening it
   exposed two follow-ons, also fixed: visibility culling dropped the Vault
   passage when seen from the Rise (0.6.1 regions assumed rock between
   them; two sightline regions added), and the alternate flight's foot
   ended on the perimeter apron open to the outside (short wall/side/roof).
3. **Night sky pixelated/ringed** (…599880, …632233). Not a core sampler
   bug (samplers are LINEAR/LINEAR_MIPMAP_LINEAR; the bilinear reprojection
   reproduces the blocks). The basin ellipsoid's walls are 1–20 m from the
   yard, so the painted 2048×1024 master was magnified up to ~930 screen
   px per texel at 4K. Fix: a band-limited procedural gradient with soft
   ridge bands (every texel step <= 4 levels). The new leak check also
   showed the ellipsoid met the y=112 rail only at x=57: both yard corners
   stood outside the basin and saw the day sky / Sun Court or the shell from
   outside. The basin and shell are now power-4 superellipsoids (south wall
   0.4–0.8 m beyond the rail). Honest note: the painted night mountains are
   gone from the basin sky; it is plain and smooth.

## New deterministic checks (in `make lumen-validate`)

- `tools/check-sky.py`: opaque single-sided sky layers, no large blended
  backdrop cards, seam mirror-ghost and row-streak scores, hard seam rows
  occluded from all ~955 walkable eyes, no view leak past a culled sky/shell,
  no terrain inside a closed sky, distant terrain >= 6 deg below eye level,
  screen px per sky texel (4K, 60°) vs local texture step, uniform pole bands.
- `tools/check-route-clearance.py`: render-geometry headroom rays, body
  capsule and eye sightlines along all 14 stair flights and 63 route edges.
  Six reviewed pre-existing findings are pinned (see "Not fixed").
- `tools/check-any-angle.py`: accepts sky holes only at declared portals and
  checks the power-4 basin shape.
- Both new checks fail 0.7.0 on every owner defect class
  (`reports/any-angle-0.7.1/baseline-0.7.0/`).

## Verified on the release package

- `make lumen-validate` PASS; glTF validator 0 errors/0 warnings; core
  `hyprune-world-check` (core-visibility-bench `0735e4d`).
- Any-angle nested (`artifacts/any-angle-0.7.1/sweep/`): 66 views incl. the
  five new owner poses and new targeted views, 66/66 culling pairs
  unchanged, 6/6 walking probes stop inside, jump stops at x=25.64, fly
  crosses to x=30.21.
- Route traversal (`artifacts/any-angle-0.7.1/routes/`): 64 nodes, 126
  directed traversals, 14 alternate stairs, 18 hero stills. PASS.
- Budgets: 244,526 triangles, 99 batches, 372.65 conservative GPU MiB
  (0.7.0: 244,312 / 99 / 372.62). Collision unchanged (5,122 triangles).

## Not fixed (reported, out of scope)

- Roof bridge: a render-only metal member 0.88–1.12 m above the 16 m bridge
  crosses the `roof-final>roof-bridge` centreline (walk passes through it).
  Candidate fix for the next release.
- Minor clearances (0.2 m) beside routes: landing wall at the top of
  `roof-ascent-lower`, a mullion at `hall-upper`, one leaf tip, and the
  snow stair's wall-side lane passing its wall lamps.
- Fly views above ~25° can face the softened cloud join of the day seam;
  the massif's jagged crown and soft 4K panorama remain as in 0.7.0.
- Transient: one sweep run (bake 3) hung in `grim` on random-14 (no frame
  delivered by the nested compositor); the rerun on the final package
  captured it normally. Core lead may want to look if it recurs.

## Next steps for the lead

Review the before/after sheet, then push `worlds` and publish
`lumen-reach-v0.7.1` with the archive above; update
`hyprune/worlds/releases.json` in the meta repo with its URL and hash.
Every commit ends with:

```
Co-Authored-By: Krombopulos Michael <Krombopulos.Michael@mail99.me>
```
