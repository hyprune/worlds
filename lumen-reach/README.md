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

World format 0.2, standard tiled UV0 and independent normalized UV1 irradiance.
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
`artifacts/lumen-reach` for review before copying to the gallery. Build host Blender is
never launched by validation or nested capture.

`reports/` contains milestone evidence, exact package/core hashes, two-size
window sweeps, free-volume checks, all route branches, UV1 and GPU allocation
accounting. Package figures include every file; conservative GPU figures include
all mip levels, color/data views and expanded visible geometry. Process DRM
memory, when exposed by the kernel, is recorded separately from this estimate.

The complete package is version 0.5.0. `make lumen-release` produces its sorted,
fixed-date tar.zst archive and checksum without a network publication. Core M2
is required for the transparent steam cards and typed workspace/tool behavior;
the manifest remains schema-valid world 0.2 through the coordinated adapter.
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
for captured applications. See the final render review and reports for the
measured differences between Cycles, the engine and the owner's concepts.

The delivered tour, local archive, all four milestone commits and exact measured
figures are indexed in [reports/final-report.md](reports/final-report.md). The
primary-wall capture requires core commit d20d7fe or later: this corrects sampling
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
loaded plugin hash. Tour encoding happens in a unique `/tmp/lumen-tour-v2-*`
directory before moving the finished MP4 and JSON into artifacts. Gallery files
are copied only after review; its autocommit service is never controlled.

`make lumen-validate` now includes named mechanical fixture checks and thin
emissive triangle probes. `tests/test_emissive_check.py` covers 2cm-wide lenses
on all three axes. Source decals have explicit backplates; authoring evidence
ships as `fixture-audit.json` and `decal-audit.json`. The material-factor audit
prevents generated textures from losing their authored color tints on export.
See [materials/README.md](materials/README.md) for texture reuse and provenance,
and [reports/final-report.md](reports/final-report.md) for the delivery numbers.
