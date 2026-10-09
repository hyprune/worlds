# Lumen Reach 0.7.0 checkpoint — 2026-10-09

Stopped at the owner's explicit request to move work to a new lead session.
**This is a committed candidate, not a validated release. Do not publish it yet.**
No push, GitHub release, 0.7.0 archive or new gallery delivery was performed.
All jobs started by this task have ended. No nested session or bake is left running.

Repository: `/home/rick/workspace/hyprune/worlds`.
Published baseline: Lumen Reach 0.6.1. It was pulled before work; original package
is preserved at `artifacts/any-angle-0.7.0/before/com.hyprune.lumen-reach/`.

## Done

- `786a939`: seeded any-angle nested harness, sanitized owner camera poses,
  structural sky checks, and baseline defect measurements.
- `102d78f`: environment/architecture candidate and bounds checkpoint.
- `any_angle.py`: full closed day sphere, properly ranged spherical UVs,
  inward winding, welded seam, real pole vertices; closed cold-basin sky with a
  textured mountain exterior instead of the 40m flat lid. Day radius 310m,
  center Blender `(20,65,0)`, stays within core's 500m far plane throughout the
  audited box through 60m height.
- Original `materials/source/sky-v7.png`, exact imagegen prompt/hash in
  `materials/generation.json`; `materials/sky.py` makes longitude periodic and
  poles uniform. Original night master is retained with provenance.
- Solid valley shelves and cliff foundations replace the cropped cliff card.
  Distance fog applies to emission-textured terrain; actual skies are excluded.
  Aqueduct has deep arch blocks, masonry spandrels, end piers, deep foundations,
  deck/parapets. Spires have solid faces, textured directional shading and bases.
- Roofing, copings and vent housings; darker shelter canvas; repaired descending
  ramp winding and textured, lit soffits. The owner's black stair slab became
  properly lit in matched engine captures. Court and Signal lightmaps increased
  from 1280 to 2048; useful UV coverage improved substantially.
- Per-home/connector footprints in `playable-volumes.json`; union perimeter
  collision backstops and guard collisions. Landing openings prevent guards
  blocking the roof route. Last bake adds short supported aprons at the descent
  and ascent alternate-stair starts and expands the corresponding footprint ends.
- Elevated visibility source region conservatively retains every home above
  21m. Fixed an existing 22–23m region gap that hid buildings from an owner pose.
- Source/build/release target versions are 0.7.0. Switchyard source unchanged;
  `make validate` passed during this task (`/tmp/lumen-v7-switchyard.log`).
- Existing 0.6.1 root reports are preserved; candidate evidence is explicitly
  separated under `reports/any-angle-0.7.0/`. Historical delivery also copied to
  `reports/delivery-0.6.1.md`. `reports/final-report.md` still describes 0.6.1.

## Current build and evidence

The **fourth bake completed successfully** on 10.2.2.2 and downloaded to:

- `dist/com.hyprune.lumen-reach/`
- `artifacts/lumen-reach/lumen-reach.blend`, bake reports, fixture audit and stills
- Log: `/tmp/lumen-v7-bake4.log`
- Current manifest SHA256: `c34216c1567b7b37c0f8b66f8c71dcddf4cf3b807a631cb9c29771336240f1e7`
- Current scene SHA256: `76d5ac53060a5ea6e4e2a28fc01229751060a83d9ecb1183e8d9e516a1e18699`

Only the explanatory `runtimeContract` text in the local source/build/package
boundary reports was corrected after this bake to acknowledge the failed fly
witness. No visual or collision bytes were patched locally.

**Fourth-bake validation and engine captures have NOT run.** Its changes relative
to the third candidate are bridge end support/spandrels/deeper piers and the two
stair aprons/footprint adjustments. Never attribute third-candidate results to it.

Third-candidate evidence:

- `artifacts/any-angle-0.7.0/final/report.json` and 112 raw 4K PNGs. Despite the
  directory name, **status is FAIL**, and this is not the final package.
- All **56 culling on/off view pairs** had zero changed central-viewport pixels:
  nine owner poses, four homes, eleven targeted views, 32 seeded random views.
- All six walking-boundary probes moved toward and stopped inside the perimeter.
- Final **ordinary-fly escape witness failed**: x ended at 25.7 instead of >26.5.
  The tall static backstop appears to constrain ordinary fly too. Do not claim
  fly bypass works. The harness assertion is intentionally retained.
- Review contact sheet: `artifacts/any-angle-0.7.0/iteration-3-review.jpg`.
  It is a draft review sheet, not gallery-delivered approval.
- Compact committed evidence: `reports/any-angle-0.7.0/iteration-3-*.json`.
- Geometry/sky, package, placement, emissive, core load and glTF checks passed
  on that candidate (glTF zero errors/warnings). Offline walking failed only at
  the two alternate-stair starts now addressed by the fourth bake.
- Full in-engine route test was queued, then stopped while still waiting for
  the flock because those offline failures required repair. It did not run.
- Earlier iterations: `artifacts/any-angle-0.7.0/{iteration-1,iteration-2}/`.
  Iteration 1 intersected Vault clearances with the basin shell; fixed in 2.
  Iteration 2 passed its seven paired inspection views.

Last measured budgets, **third candidate only**:

| | 0.6.1 baseline | Third 0.7.0 candidate |
|---|---:|---:|
| Visible triangles | 222,403 | 242,232 |
| Unfiltered material batches | 87 | 99 |
| Conservative GPU MiB | 326.20 | 372.39 |

Fresh baseline engine timings/captures are in `before-engine/` (Court/Hall) and
`before-cold-homes/` (Vault/Signal). All are native 3840×2160, Intel, Medium,
fixed 0.5 internal scale. Raw timing samples are retained. Recompute final
numbers; do not reuse historical Low-preset visibility timing tables.

## Open items

1. Resolve the fly/backstop conflict before claiming the requested movement
   behavior. Format 0.5 has no playable-volume/movement-mode boundary contract;
   `zones` and visibility bounds do not enforce movement. See NOTES-rfc-gaps.md.
   Ordinary fly is not the same as held authoring photos/noclip. Investigate
   core's actual fly collision behavior before deciding how to lower/split or
   otherwise replace the tall invisible perimeter. Preserve walking protection.
2. Validate fourth-bake alternate stair starts and all route clearances. The
   previous exact failures were `service-descent` feet `(33.85,0,-52)` and
   `snow-service-ascent` feet `(57.85,-6,-100)` in glTF coordinates.
3. Finish art review. The mountain exterior has a rather jagged crown from
   above and can read coarse against the painting. `rise-exterior` at
   `[110,60,-170]` may be inside/too near its outer shell; distinguish an invalid
   embedded inspection camera from a missing face, then choose a valid exterior
   pose. Do not silently discard a real artifact. The new panorama master is
   1774×887, exported as 2048×1024; distant imagery is soft at 4K. Triangle/UV
   checks prove seam/pole continuity, not photorealism or every possible view.
4. Review the newly completed bridge masonry in-engine. Small arch-block joints
   still use angular gaps; check they read as joints rather than holes.
5. Full final any-angle sweep, route traversal, final performance/budget report,
   gallery contact sheet/stills, release documentation, archive and extracted
   archive verification remain unfinished. No 0.7.0 archive currently exists.

## Exact next steps

Use the clean isolated core checkout already built at published commit `0735e4d`:
`/home/rick/workspace/hyprune/core-visibility-bench`.
Do not overwrite a concurrent developer's `/home/rick/workspace/hyprune/core`.
The loaded plugin hash is recorded in each session report.

Start with offline checks of the current fourth bake:

```sh
cd /home/rick/workspace/hyprune/worlds
make lumen-validate
GLTF_VALIDATOR_DIR=/tmp/hyprune-gltf-audit/node_modules node tools/validate-gltf.mjs dist/com.hyprune.lumen-reach
../core-visibility-bench/build/hyprune-world-check dist/com.hyprune.lumen-reach
```

Then address the open movement/art issues. If source geometry changes, build
only remotely, and retain a distinct output directory per review iteration:

```sh
python3 lumen-reach/materials/prepare.py
./tools/remote-lumen.sh --areas 4 --samples 64
python3 tools/check-any-angle-session.py --core ../core-visibility-bench --output artifacts/any-angle-0.7.0/iteration-4
mkdir -p artifacts/any-angle-0.7.0/routes-final
cp artifacts/lumen-reach/views.json artifacts/any-angle-0.7.0/routes-final/views.json
HYPRUNE_NESTED_4K=1 python3 tools/check-lumen-session.py --core ../core-visibility-bench --output artifacts/any-angle-0.7.0/routes-final --routes
```

Both harnesses acquire `/tmp/worldshell-nested.lock` internally for their full
lifetime and use private state. Do not wrap them in another exclusive flock on
the same file. Never use the owner's real session. The all-angle harness writes
its final contact sheet only after the boundary/fly probes; a failed witness
leaves all raw captures/report but no completed contact sheet.

After final validation and visual review, place the contact sheet and selected
raw in-engine stills in the proposed gallery folder:
`/home/rick/workspace/rick-the-alien/worldshell-gallery/screenshots/release-world-v4/`.
No files have been delivered there by this task. Never stop/signal gallery
`autocommit.py`. No new video was requested for this 0.7.0 pass.

Update `RENDER-REVIEW.md`, `reports/final-report.md`, `reports/release.json`, and
any budget/visibility documentation whose current figures changed. Run
`make lumen-release` only after resolving failures; it makes
`artifacts/releases/com.hyprune.lumen-reach-0.7.0.tar.zst`. Verify its extracted
files and record SHA256. Commit logical steps, **do not push or publish**.
Every commit must end with:

```
Co-Authored-By: Krombopulos Michael <Krombopulos.Michael@mail99.me>
```
