# Lumen Reach 0.7.0 handoff — 2026-10-09

**Release candidate verified; not published.** The archive is built and checked.
No push and no GitHub release yet: the lead reviews first. No nested session or
bake is left running.

Repository: `/home/rick/workspace/hyprune/worlds`. Published baseline: 0.6.1
(original package kept at `artifacts/any-angle-0.7.0/before/`).
Owner direction for this release: playable over glossy. Fix real defects only;
no redesigns or art-polish passes.

## Release candidate

- Package: `dist/com.hyprune.lumen-reach/` (sixth bake, source `141be25`,
  baked on 10.2.2.2; log `/tmp/lumen-v7-bake6.log`)
- Manifest SHA256 `f7b536749fd85ae8d677fd0339a49b7b539477633ab09129c9e1468e20b6f34d`
- Scene SHA256 `00f8a83249ab16f73ae45fbe145b1924f2bec81cdb7aa32a3cd61afa40758a18`
- Archive `artifacts/releases/com.hyprune.lumen-reach-0.7.0.tar.zst`,
  47,941,863 bytes, SHA256
  `31a1449cb76ee2ed97cba33b0b55a3d6dcc91f23646fbe3ec7f3bdf679b0666d`.
  All 76 extracted files are identical to `dist/`; the extracted copy passes
  schema 0.5 and core world-check.
- Gallery: `~/workspace/rick-the-alien/worldshell-gallery/screenshots/release-world-v4/`
  (any-angle contact sheet, hero-stills sheet, five raw 4K stills).
- Reports: `reports/final-report.md`, `reports/release.json`, `RENDER-REVIEW.md`,
  `reports/any-angle-0.7.0/release-*.json`. 0.6.1 records are preserved as
  `reports/release-0.6.1.json`, `reports/delivery-0.6.1.md` and
  `reports/render-review-0.6.0.md`.

## What this session changed

1. **Fly vs backstop** (`8ce1cf4`, `141be25`). The uniform −20…65 m invisible
   perimeter blocked ordinary fly. Core's `Fly::step` resolves the capsule
   against all collision, so the fix was in the world. Each ≤2 m backstop piece
   now rises `walkClearance` 2.5 m above the highest walkable top
   (collision faces, prop boxes, guard rails) within 3 m inside it. Isolated
   pieces with no walkable surface follow neighbours within 3 m. Result: 370
   pieces, tops −3.5…24.1 m. Core's jump lifts feet 1.27 m.
2. **Any-angle harness**: adds a repeated-jump probe at court east and flies the
   witness at 6 m eye (collision on, not noclip).
3. **Route harness** (`tools/check-lumen-session.py`): the 0.7.0 guard
   collision put the `01-sun-court` hero camera inside the court's south
   guardrail line, so collision moved it 0.36 m and the pose assert failed
   (this would also have failed on bakes 3–4; routes never ran on them). Hero
   stills are authoring poses, so the harness now holds noclip (`v`, verified
   via the diag state) while placing them and restores collision before routes.

## Verified on the sixth bake

- `make lumen-validate`, glTF validator (0 errors/0 warnings), core
  `hyprune-world-check` from `core-visibility-bench` `0735e4d`.
- Any-angle nested (`artifacts/any-angle-0.7.0/iteration-4/`; harness iteration
  4, build = sixth bake): 56/56 culling pairs unchanged, 6/6 walking probes
  stop inside, jump stops at x=25.64 (limit 26), fly crosses to x=30.28.
- Route traversal (`artifacts/any-angle-0.7.0/routes-final/`): 64 nodes, 126
  directed traversals, 140 traversed, 14 alternate stairs, 18 hero stills. PASS,
  including the two alternate-stair starts that failed on candidate 3.
- Budgets: 244,312 triangles, 99 batches, 372.62 conservative GPU MiB (0.6.1:
  222,403 / 87 / 326.20). Matched-pose GPU pass sums did not regress at any home.

Earlier candidates' evidence (`iteration-1..3`, `final/`, `iteration-3-*`) is
superseded; never cite it for this build.

## Known limits (accepted for 0.7.0)

- Fly below backstop height is still stopped at the perimeter: static collision
  cannot tell modes apart. Near court east, fly needs eye height ≳ 5.2 m to pass.
- Out of scope by owner direction: jagged mountain crown from above, soft 4K
  panorama, angular aqueduct joints (they read as joints, not holes).
  `rise-exterior` is a too-close inspection pose, not a missing face.
- Transient nested failure seen once: Xwayland `xkbcomp` "not enough space" on
  `/run/user/1000` (free again seconds later; a rerun passed).

## Switching to world format 0.6 later (not done; release stays on 0.5)

Schema `2c1be9b` adds optional `playable` eye-position volumes (box or convex,
≤8 per area, ≤64 total) per area and at top level, plus `maxFlyHeight`. Once
core enforces them:

- Bump `formatVersion` to 0.6. Emit `areas[].playable.volumes` boxes from each
  area's rects in `playable-volumes.json` (glTF coords: x, y-up, z = −Blender y).
  Use eye-height ranges spanning that area's lowest floor to its highest walkable
  top + 1.7 m. All areas fit (≤4 rects each).
- Set `maxFlyHeight` to about 60 m (the audited sky box is valid up to 60 m).
- Remove the static `Playable perimeter` from collision in `any_angle.boundaries`
  and keep the visible guard collisions. Rerun the boundary probes, expecting fly
  to follow the volumes instead of colliding.
- Check RFC-0004's motion semantics for walk vs fly vs noclip before relying on
  them.

## Next steps for the lead

Review, then push `worlds` and publish `lumen-reach-v0.7.0` with the archive
above. Update `hyprune/worlds/releases.json` in the meta repo with its URL and
hash. Every commit ends with:

```
Co-Authored-By: Krombopulos Michael <Krombopulos.Michael@mail99.me>
```
