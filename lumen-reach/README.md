# Lumen Reach

Hyprune's connected release world. Sun Court, Array Hall, Rime Vault and Signal
Rise are four workspace homes; each owns one wall workspace and its tool mounts.
See IDENTITY.md for the settlement's original language and symbols.

Build ONLY on the remote bake host:

```sh
python3 lumen-reach/materials/prepare.py
./tools/remote-lumen.sh --areas 4 --samples 64
```

`--areas 1` produces the first milestone; 2/3/4 include successive homes and
connecting paths. Source geometry is original procedural Blender Python.
Generated material masters/prompts/provenance are committed; distributable
scenes, PBR derivatives, bake atlases, renders and recordings remain in ignored
`dist/` and `artifacts/`. The dedicated runner refuses the local machine.
The test world's source and entrypoint remain intact.

World format 0.5, standard tiled UV0 and independent normalized UV1 irradiance.
Physical mount frames and the optional `com.hyprune.lumen-reach.mounts` extension
encode area/slot ownership. Free-placement volumes are declared in the optional
placement extension and continuously swept against exported visual triangles.
Unknown extensions are optional. Static screen UI is labeled authored artwork;
live applications come from core's actual window capture.

Verification and nested review:

```sh
make lumen-validate
GLTF_VALIDATOR_DIR=/tmp/hyprune-gltf-audit/node_modules node tools/validate-gltf.mjs dist/com.hyprune.lumen-reach
python3 tools/check-lumen-session.py
python3 tools/check-lumen-session.py --routes
python3 tools/check-lumen-session.py --record
```

The scenario uses core's actual nested session implementation under the shared
lifetime flock. Its verified controller checks the nested process, configuration,
compositor lock, socket and display. Recording binds four actual compositor
workspaces to the authored homes and places real kitty windows on owned mounts.
Core performs capsule-checked auto-drive; camera turns happen while stationary.
The recording includes Quickshell's actual leased HUD. Captures are staged in
`artifacts/lumen-reach` for review. Build host Blender is never launched by
validation or nested capture.

`reports/` contains milestone evidence, exact package/core hashes, two-size
window sweeps, free-volume checks, all route branches, UV1 and GPU allocation
accounting. Package figures include every file; conservative GPU figures include
all mip levels, color/data views and expanded visible geometry. Process DRM
memory, when exposed by the kernel, is recorded separately from this estimate.

The latest release record is `reports/release.json`; earlier ones are
`reports/release-<version>.json`. `make lumen-release` produces a sorted,
fixed-date tar.zst archive and checksum without a network publication. Core M2
is required for the transparent steam cards and typed workspace/tool behavior;
the manifest remains schema-valid world 0.5 through the coordinated adapter.
The four lighting moods come from baked irradiance. Core M2 currently exposes
world-wide atmosphere and static environment reflections, so these are not
presented as independently changing per-area atmosphere.

Visible stairs use continuous sloped collision beds beneath the individual
treads. Both the graph ramps and alternate stair flights receive independent
support/capsule checks. The graph stays within core's 64-node/256-edge limits.
Placement checks include both requested window sizes and each full mount
rectangle, plus every reserved volume interior, against exported visual meshes.

Lightmap atlases are independent per architectural area; the leaf-card atlas
uses 2px gutters at 1024, and the architectural atlases use 4px gutters. Their
samplers clamp and filter linearly at the base level. Generated PBR tiles use
640px periodic derivatives, verified matching edge pixels, to leave headroom
for captured applications. See [RENDER-REVIEW.md](RENDER-REVIEW.md) and the
render reviews in `reports/` for the measured differences between Cycles, the
engine and the concept references.

Measured figures and archive hashes for each release are in the release
records above. The original milestones are summarized in
[reports/milestone-01.md](reports/milestone-01.md) through
[reports/milestone-04.md](reports/milestone-04.md). The primary-wall capture requires core commit d20d7fe or later: this corrects sampling
of client buffers with no mip chain. `--diagnose` is a short real four-wall check;
run it in a fresh locked session separately from the complete route audit.


Visual polish v2 adds seated entry fixtures, textured material aliases, detailed
service kits, original rock terrain and a ribbed dish/feed assembly. Run the
complete automated release review in three fresh nested sessions under one
shared lifetime lock:

```sh
python3 tools/check-lumen-session.py --release-review
```

This captures 4K stills and per-home Medium/iGPU timing samples, traverses every
route and alternate stair, then records a 60–90 second live-app tour at 1080p.
The script uses core's effective Medium preset when available and records the
loaded plugin hash. The current tour uses shell protocol 0.7, explicitly returns
home applications to workspace composites and checks that the HUD stays live.
Tour encoding happens in a unique `/tmp/lumen-tour-v2-*`
directory before moving the finished MP4 and JSON into artifacts.

`make lumen-validate` now includes named mechanical fixture checks and thin
emissive triangle probes. `tests/test_emissive_check.py` covers 2cm-wide lenses
on all three axes. Source decals have explicit backplates; authoring evidence
ships as `fixture-audit.json` and `decal-audit.json`. The material-factor audit
prevents generated textures from losing their authored color tints on export.
See [materials/README.md](materials/README.md) for texture reuse and provenance,
and the release records in `reports/` for the delivery numbers.


Rime Vault v3 adds a directional frost/ice material set, console banks, overhead
pipe racks, grated cable channels, purge vents and a lit pressure-door kit.
The original 24 interactive mounts and all walking/placement contracts remain
unchanged. See [reports/render-review-0.6.0.md](reports/render-review-0.6.0.md)
for the Vault review and `reports/release-0.6.1.json` for 0.6.1 evidence.

For a matched short camera clip, prepare an output directory with `views.json`
and run `tools/check-lumen-session.py --vault-clip --package <package> --output
<directory>` once for each version. `tools/package-rime-clip.py <before-dir>
<after-dir> <output-dir>` alternates the same three views and writes string-only
JSON metadata. It encodes in `/tmp`; inspect the clip before publishing it.
`tools/check-rime-v3.py` checks budget growth and unchanged mount/route contracts.

## Residents

Since 0.11.0 (world format 0.9) four residents live in the world, one per area:
Desert in Sun Court, Crimson in Array Hall, Ember in Rime Vault and Blue in
Signal Rise. `residents.json` is the source: the characters, the bench table,
the keepClear volumes, the routes (`paths[]` with stops) and the residents with
their interactions. `build.py` builds the benches from the table and calls
`residents.py` while it writes world.json; `python3 lumen-reach/residents.py
PACKAGE --in-place` re-applies the data to a built package without a bake.

- **Characters.** The starter-kit residents (`characters/<id>/`, the same bytes
  as `com.hyprune.starter@0.1.1`) ship inside the package as directory assets.
  Official worlds stay self-contained: core resolves a library asset only
  against an installed `id@version` and refuses activation otherwise, and
  installers do not install a world's library dependencies.
- **Routes.** Each resident walks a calm route with three stops: a vista, a spot
  beside a tool screen (outside its approach zone) and a bench seat. Crimson
  marks the way to Rime Vault (a waypoint); Ember walks the player to Signal
  Rise's home (`to-signal-rise`, from just north-east of the vault bench, which
  every point of Ember's route and its seat's approach point reach in a straight
  line), also when asked while seated: core stands it up first and it sits down
  again afterwards.
- **Seats.** 0.40 m benches: both Sun Court seats, one between the second and
  third desks in Array Hall facing the hanging wall, one at Rime Vault's south
  edge facing the console and one in Signal Rise's south field facing the map
  terminal and the fortress. Two `seats[]` anchors each, at the middle of each
  half of the bench, 0.16 m in front of the seat's front edge. Core sits a
  resident down by moving its root back from the anchor by the sit clip's
  travel (0.36-0.42 m) with the hips over the root, so the pelvis lands 0.20-0.26
  m inside the front edge. The seat's collision stops 0.16 m short of its front
  (and the supports stand under that footprint), so the walker's body is clear
  of collision at the anchor, which core requires of the last approach step. The
  residents' `sit` clip fits anchors up to 0.41 m (Desert) to 0.52 m (Blue).
- **keepClear.** In front of the four primary walls and at the doors between
  areas: no stop or seat approach lies in one.
- **Lighting.** Residents take core's probe light. Blue carries an authored
  ambient (moonlit, like the Sun Court armillary's): at night the probe sees
  only the dark sky dome while the baked snow is lit by area lights.
- **Say lines** stay within 36 characters: core shows a line as a one-line
  caption and cuts longer ones.

Checks: `tools/check-residents.py` (in `make lumen-validate` and
`lumen-release-check`; `NPC_CHECK` names core's `hyprune-npc-check` for the
seat fit) applies core's walkability rules every 0.25 m (floor, ledge, body
clear of collision, playable volume, screen approach zones), keeps the body
clear of render-only props too, and gates the navmesh island, 1.2 m clear
width, stops outside keepClear and at least 0.5 m from approach zones, seat
legs, the seated pelvis at least 0.15 m inside the seat's front edge and ends,
0.3 m of room around each bench (stairs and rails included) from the floor to
1.3 m above the seat, seat fit, and the guide's join leg from every route
sample and seat approach point.
`make lumen-residents-session` runs the nested check: bound routes, walking
speed, every seat taken (stills from the front and from the bench's end),
every stop reached, say, waypoint, guides from walking and from a seat, and
frames with residents out of the frustum (residents in the frustum behind walls
are recorded: core culls characters by frustum and visibility regions).

## Visibility

Since 0.9.0 the build derives visibility regions from geometry
(`tools/derive-visibility.py --in-place` in `make lumen-build`; see
`VISIBILITY.md`). Before that, `visibility.json` (now
`visibility.hand-written.json`, kept as a reference fixture) owned camera-region
bounds, stable glTF subtree names and directed links. The exporter resolves names after every bake. To update an existing
package without rebaking or changing any asset:

```sh
make visibility-annotate
make visibility-validate
make visibility-nested
```

Regions do not alter workspaces, collision or navigation. Overlapping doorway
bounds union the visible sets; outside all bounds core draws everything. Shared
architecture/art stays unassigned and always visible. See `VISIBILITY.md` for
links, retained sightlines and paired 4K Intel timing evidence.


Any-angle review (0.7.0) uses a closed spherical sky, a textured mountain shell
around the cold basin, solid watershed shelves and modeled distant masonry.
Exposed roofs have stone roofing, metal copings and extraction housings. Stair
soffits use corrected outward winding, textured finishes and baked grazing fill.
Sun Court and Signal Rise now use 2048px lightmaps to keep exposed faces readable.

```sh
python3 tools/check-any-angle-session.py --core ../core-visibility-bench --output artifacts/any-angle-0.7.0/final
```

The script takes core's shared nested flock internally. It replays the
sanitized review poses, samples route positions and elevated views with seed 7009,
checks culling pairs, and tests walking barriers plus a free-flight witness.
`make lumen-validate` checks sky topology, mapping, seams and the far-clip
margin as well as existing placement/walking/material contracts. The finite
image sweep complements these structural checks; it is not an exhaustive proof
of every possible view. Contact sheets and raw images are written to the
`--output` directory; per-release sweep records are in `reports/any-angle-*/`.

`playable-volumes.json` is authoring metadata. Its footprint union generates
static collision backstops because world format 0.5 has no movement-volume
contract. Each piece rises only `walkClearance` (2.5 m) above the highest
walkable top within 3 m inside it: walking and jumping stop inside, ordinary fly
passes over. Visibility bounds remain separate. An elevated review region retains
all homes above 21m, where room-level occlusion assumptions no longer apply.
