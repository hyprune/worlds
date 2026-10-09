# Switchyard · 0.1.2

An original blue-hour transit terminal for an explorable desktop. A twenty-meter bronze vault frames six timber-canopied project stations: Build, Research, Commons, Studio, Systems and Archive. Colored floor routes connect them to a concourse with a route-map sculpture, upholstered lounges and planting. The smaller sculpture stands beside the route, preserving the front station sightlines. A three-layer skyline includes stepped towers, a lantern crown, twin relay towers, a rooftop observatory halo, lit signage and aviation markers. Cargo has labels, straps, fasteners and skids; station signals, cable trays, railings, practical lights and an original elevated rail-city vista complete the place. Applications dock on six permanent screen anchors. Static signs and signals identify locations; they never claim live project status.

## Build and inspect

Run `make preview` to generate textures and judge the architecture before baking. `make build`, `make validate`, `make gltf-check`, `make film`, then `make gallery` produce and inspect the complete world. `make nested` captures all five matching core M1 views and exercises the actual core nested harness under `/tmp/worldshell-nested.lock`. `make engine-film` additionally records a 27-second collision-checked engine walk. `make compare` assembles unretouched side-by-sides. `make release` produces a data-only tar.zst package and SHA256. `switchyard/views.json` shares all five positions/targets and the fixed 60° vertical FOV between Blender and core. `make stills` rerenders five 1920×1080 Cycles beauty frames. Local dependencies: SSH, rsync, Python 3 + NumPy/Pillow, Node >=22.12 and the sibling schema repo's dependencies. Matching captures additionally use the built sibling core, its supported Hyprland, grim, wtype, wf-recorder, local FFmpeg and fontconfig for diagnostic labels. Khronos validation uses an installed `gltf-validator` module; see `tools/validate-gltf.mjs`. Remote dependencies: Blender 5.2, Cycles/OptiX, Blender's NumPy, `oidnDenoise` RTLightmap and FFmpeg.

**Blender must run on the mains-powered bake host, never locally.** `tools/remote-blender.sh` defaults to `10.2.2.2`; configure `HYPRUNE_BAKE_HOST` and `HYPRUNE_BAKE_DIR` for another remote host/directory. It transfers this repo's source, serializes remote Blender with flock and retrieves outputs even after failure. Generated GLTF/BIN, derived textures, BLENDs, renders and video remain ignored; original texture master PNGs are intentionally committed as reproducible source inputs (eight files, about 24 MiB). The initial repo did not define generated binary distribution policy; release directories/archives are the chosen approach. No automatic CI bake is claimed.

Package: `dist/com.hyprune.switchyard/`. Editable source scene, five stills, lighting report, nested screenshots and film: `artifacts/switchyard/`. The 36-second Cycles film is 24 fps, 1080p H.264/yuv420p with faststart, bitrate capped below 40 MB. Frames remain on the host and resume only when the saved scene/script digest matches. The gallery receives `world-switchyard.mp4`, `world-switchyard-engine.mp4` and their title/tag/notes JSON. For a long bake that survives SSH loss, use `make film-start`, `make film-status`, then `make film-fetch`. The source scene/script digest invalidates stale frame caches; review `--stage film-preview` before starting the final job.

## Spatial and material contracts

One unit is one meter. Blender `(x,y,z)` becomes glTF `(x,z,-y)`. Arrival spawn `[0,0,10]` is capsule feet; core adds the eye offset. Docks face +Z with stable `<station>-dock` IDs, 4.2 × 2.36 m, `com.hyprune.window`. The idle pane and original route schematic sit behind the interaction plane. Applications are user bound; the world launches nothing.

The floor is continuous and level. The inset 0.5 m triangular navigation grid excludes capsule-expanded prop footprints. Collision uses simplified static boxes for the slab, walls, rails and substantial props; those helpers and navigation live outside the visual scene. The independent route checker compares the actual exported collision/nav geometry with authoring records, tests a 0.3 × 1.8 m capsule every 5 cm along each graph edge, and checks connectivity to all six stations. Optional map/routes metadata derives from the same station spec.

The package opts into world format **0.5**, retaining the RFC-0004 material profile. Original material tiles repeat on UV0 at **512–1024 px/m** (2 m stone tiles, 1 m other used tiles; the glass master remains in the source library). Original normal and ORM maps preserve glTF meanings; roughness is green and metallic blue, no lightmap is hidden in occlusion. Sign trim uses the brass band of an original eight-band atlas with explicit gutters. Two original low-energy emissive sheen maps preserve the pane and bronze trim appearance without glossy reflections: these are explicit view-independent approximations, independent of albedo and irradiance. The pane sheen uses `KHR_texture_transform`; normals and lightmaps keep their own coordinates. Normal scale is 0.22 for cloth, 0.32 for coated metal and 0.40 for other textured materials. Practical emission stays within the base glTF profile, avoiding unsupported HDR emissive-strength behavior. Source prompts, seam healing, offset/repeat inspection, atlas rectangles, texture hashes and scale are recorded under `materials/`.

Nine spatial groups each own nonoverlapping UV1: hall 4096²; vault, concourse and six stations 2048² each. Eight-pixel island separation and eight-pixel Cycles dilation are recorded; the shipped lightmap sampler is linear without mipmaps. Cycles DIFFUSE DIRECT + INDIRECT, excluding COLOR, yields lighting-only irradiance; OIDN RTLightmap denoises it. Each measured peak controls normalization into an sRGB PNG and the matching manifest intensity. Core multiplies decoded albedo by decoded irradiance once and adds emission; dynamic/specular terms remain separate. Unlit sky/city scenery has no lightmap binding. Open opaque ceramic roof slats replace translucent glazing, and opaque distance-layered city geometry supplies atmosphere. Both renderers receive the same geometry; there are no beauty-only haze cards or alpha-dependent roof sheets. Beauty/film use the original lights, with no double lightmap multiplication; AgX renders and core's tone mapping/specular approximation can differ.

The Map SVG, graph, reflection, HDR emission, atmosphere and presentation gaps are documented in [NOTES-rfc-gaps.md](../NOTES-rfc-gaps.md). No experimental extension is required. The world is naturally quiet: no sound, flashing status, ambient motion or forced travel. Rights and modifications: [ATTRIBUTION.md](ATTRIBUTION.md). Content CC-BY-4.0; scripts MIT.

## Authored visibility

`visibility.json` owns camera-region bounds, stable glTF subtree names and directed
links. The exporter resolves names after every bake. To update an existing
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
