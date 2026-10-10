# Lumen Reach delivery

One connected release world with four original workspace homes: Sun Court,
Array Hall, Rime Vault and Signal Rise. Each owns one primary mounted workspace
and its physical tool mounts; stable area/slot names and reusable themed kits
support future homes. The settlement identity and original marks are in
[IDENTITY.md](../IDENTITY.md).

| Milestone | Local commit |
| --- | --- |
| Sun Court | d16f2a0 |
| Array Hall | 0c14cdd |
| Rime Vault | 190f5ac |
| Signal Rise and connected world | db28820 |

The world includes 24 planar anchors (four primary walls and twenty tools),
21 data objects, four free-placement volumes, 64 route nodes, 63 bidirectional
edges, 14 alternate stair flights, balconies, rooftop work shelter, lower
maintenance deck, operator room and antenna/cable gantry. Paving rails and
practicals follow travel routes; the sealed continuation leaves an expansion
destination. Tool approaches reserve 4m and primary walls reserve 16m.

Original generated masters, prompts and hashes are committed. Seam-healed PBR
tiles, trim bands, physical screen frames and original UI use the shared bake
pipeline; procedural geometry, UV1 lightmaps and Cycles renders ran exclusively
on 10.2.2.2. No local Blender execution or owner-session control occurred.

| Delivery measurement | Result |
| --- | --- |
| Package files | 55.13 MiB |
| Compressed archive | 32.94 MiB |
| Conservative world GPU allocation | 272.45 MiB |
| Sampled nested process peak with live apps and recording | 786.02 MiB |
| Tour | 83.13s, 1920×1080, 30 fps |

The GPU sample includes the nested compositor, renderer and imported
application buffers (97 samples), and does not establish an upper bound
between samples. Conservative world accounting includes all mip levels,
color/data texture views and expanded visible geometry. Exact hashes, bytes and
measurement scopes are in [release.json](release.json).

Schema 0.2, glTF (zero errors and warnings), independent/non-overlapping UV1,
provenance, full-anchor and two requested window-size sweeps, free-volume
interiors, capsule support and graph limits pass. The real engine audit passed
all 126 directed graph traversals and all 14 stair flights. Its scene hash
matches the final tour; the later core change affects capture sampling. The
tour passes real travel, four placed terminals, actual keyboard input and
authenticated Quickshell HUD. A separate four-wall diagnostic verifies useful
live btop content on every primary wall.

The gallery has twelve raw matched engine compositions, additional live primary
and tool views, and the reviewed tour (gallery `videos/release-world-tour.mp4`)
with its title/tag/notes JSON. Files are local. The gallery autocommit/push
service is stopped; the gallery server remains available. Worlds was pulled
before every milestone and closing commit; no worlds push was made.

The local installable archive is
`artifacts/releases/com.hyprune.lumen-reach-0.4.0.tar.zst`; its SHA256 is
`4e6fcabf7c01db1f7a2947cd84092cbb2c0a12bd46be337640505ee73733e6ef`. Build and verification commands are in [README.md](../README.md).
Core d20d7fe or later is needed for correct primary capture sampling;
shell ee66bff supplies the visible Overview terminology. Switchyard remains
an unchanged walkable test world and its existing validation passed.

The concept/engine/Cycles review is [RENDER-REVIEW.md](../RENDER-REVIEW.md),
with raw image links in the generated comparison HTML. Engine contrast remains
harder than Cycles; steam and environment reflections are static, atmosphere
is world-wide, and the snowy dish/terrain use simpler procedural detail than
the painted concept. Unusual high views can expose opaque night-card seams.
These limits remain visible in the ungraded evidence.
