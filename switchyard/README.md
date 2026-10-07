# Switchyard · 0.1.0

A compact, original transit hall for your desktop. Three colored routes connect a shared concourse to six permanent project stations: Build, Research, Commons, Studio, Systems and Archive. Files have cargo drawers; applications have planar docks. The world is a place, not a collector or a process controller. Its static signs and signal colors identify locations and never claim live project status.

## Build and inspect

From this repository, run `make build`, `make validate`, `make film`, then `make gallery`. `make release` produces the data-only package archive and its SHA256. `make stills` rerenders four original beauty frames. Authoring dependencies on the remote host: Blender 5.2, NumPy in Blender, Cycles/OptiX, `oidnDenoise` with RTLightmap, and FFmpeg. Local tools: SSH, rsync, Python 3 + NumPy, Node >=22.12 and the sibling schema repo's `npm ci`. Khronos validation additionally uses `tools/validate-gltf.mjs` with an installed `gltf-validator` module (documented in that script).

**Blender must run on the mains-powered bake host, never locally.** `tools/remote-blender.sh` defaults to `10.2.2.2`. Set `HYPRUNE_BAKE_HOST` and `HYPRUNE_BAKE_DIR` to use another remote host/directory. It transfers only this repo's source, serializes remote Blender with flock, and retrieves `dist/` and `artifacts/` even after a failure. No historical art directories are transferred. Artifacts are ignored by git; this repo previously had no binary distribution policy. Review source here, then distribute generated immutable directories or release archives. There is no automatic CI bake yet.

Generated package: `dist/com.hyprune.switchyard/`. Editable source scene and lighting bake report: `artifacts/switchyard/`. All stills are 1920×1080; the 36 s flythrough is 24 fps H.264/yuv420p, faststart, rate capped to remain below 40 MB. Film frames remain on the host and resume automatically; delete the host's `artifacts/switchyard/film-frames` before regenerating a changed film.

## Spatial and lighting contracts

One unit is one meter. Blender authoring `(x,y,z)` becomes glTF `(x,z,-y)`. Spawn positions are capsule feet at floor height; core places the camera above them. Docks face +Z and use stable anchor IDs `<station>-dock`, 4.2 × 2.36 m, `com.hyprune.window`. Applications are user bound; the world never launches them. The textured idle pane is behind the interaction plane. Unknown screen types must show core's placeholder.

The floor is continuous and level, with three 2.4 m circulation aisles. Navigation is an inset 0.5 m triangular grid excluding the capsule-expanded footprint of props. Collision uses simplified static boxes, including the slab, walls and substantial props, in separate glTF nodes outside the visual scene. Navigation and collision helper geometry must not be rendered. The optional route graph uses the same coordinates as the geometry and blueprint; it grants no movement behavior.

Each of seven spatial groups has its own nonoverlapping UV1 atlas: 4096² for the hall, 2048² for each station. Island separation is eight pixels; four pixels of padding on each side support two mip levels, while the shipped lightmap sampler uses linear filtering without mipmaps. Cycles supplies an eight-pixel dilation margin. Original procedural tile images use UV0. Cycles DIFFUSE with DIRECT + INDIRECT, excluding COLOR, yields lighting-only irradiance. OIDN RTLightmap denoises it. Each atlas is normalized by its measured peak, stored as an sRGB PNG, and bound to every material in that group with its matching intensity and `texCoord: 1`. Emission stays in the glTF materials. No lightmap is placed into glTF's occlusion slot. Core must multiply once and avoid duplicating direct diffuse lighting. Beauty/film renders use the original physically lit scene rather than a second lightmap multiplication.

The Map SVG and route graph are proposed optional namespaced extensions; see [NOTES-rfc-gaps.md](../NOTES-rfc-gaps.md). Neither is required for activation. Quiet mode is naturally static: no ambient animation, sound, flashing status, or forced travel. A separate time-of-day package would need a new immutable version and is deferred.

Rights and modifications: [ATTRIBUTION.md](ATTRIBUTION.md). Content CC-BY-4.0; all scripts MIT.
