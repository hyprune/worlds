# NPC characters

Ambient characters for worlds (RFC-0010 draft, "Ambient characters (NPCs)"; the author's
spec is the docs page "NPC characters"). Each character is an RFC-0011 object directory,
`characters/<id>/` with `object.json` (the `character` trait: measured clips, walk and run
speeds, height), `object.glb` and `thumbnail.png`, checked by `tools/object-check`.
`object.glb` is the canonical output of `tools/npc-import` (metres, +Y up, facing +Z, a
`root` bone at the feet, clips in place at 30 fps, at most 4 weights, meshopt geometry and
KTX2 textures at 1024 px: UASTC + zstd for base colour and normal map, ETC1S for
metallic-roughness), published under its public name by `tools/npc/publish.py`;
`tools/object-import --adopt` wrote the manifest and the thumbnail. `characters/<id>.glb`
links to `<id>/object.glb` for tools that use the flat paths. `characters.json` lists each
file's size, hash, budget, measured walk/run speed and clips. Lumen Reach 0.11.0
(world format 0.9) places all four, one per area; core's nested NPC test walks two
through Switchyard.

| Character | Size | Triangles | Bones | Walk / run | Clips |
| --- | --- | --- | --- | --- | --- |
| `resident-blue` | 3.79 MB | 8,000 | 38 | 0.87 / 3.05 m/s | shared (hips x1.049) |
| `resident-crimson` | 3.80 MB | 8,000 | 37 | 1.01 / 3.59 m/s | shared (hips x1.157) |
| `resident-desert` | 3.72 MB | 7,999 | 33 | 0.75 / 3.41 m/s | own |
| `resident-ember` | 3.69 MB | 8,000 | 37 | 0.80 / 3.10 m/s | shared (hips x1.085) |

All four share one skeleton template. `resident-desert` carries its authored clip set;
the others take the same clips through `tools/npc-import --clips-from` (rest-relative
retarget, hips scaled by hip height). `idle` is the calmest of the authored idles (least
arm motion); a livelier one is `idle_fidget`, which core plays rarely when the player is
near. Each has a single baked material, so colour variants are separate characters.

Textures (library 0.1.1, objects 1.0.1): a core that keeps character KTX2 images
GPU-compressed (BC7 where the GPU has it; older cores expand them to RGBA) holds the three
1024 px maps of a resident in 4 MiB with mips instead of 16 MiB. Either way the GPU format
is the same for ETC1S and UASTC, so the base colour moved from ETC1S to UASTC: rendered
in Lumen Reach (Sun Court daylight and Array Hall, faces from 1 m and full figures from
4 m) against the same characters with lossless PNG textures, the mean CIEDE2000 on the
characters fell from 1.4-2.3 to 0.5-0.7 (95th percentile 5-8 to about 2), and the ETC1S
block edges on faces and scarves are gone. 512 px maps were measurably worse at 4 m, so
the maps stay at 1024 px.

The `sit` clips end with the thighs below the root plane (a seat height under 0 m by the
RFC-0011 measure), so their manifests list `sit` and `sit_idle` without a `seatHeight`.
Core seats them by lifting the root (anchor height minus the measured seat height) and
accepts an anchor while the feet then hang at most 0.45 m: seats up to about 0.41 m
(desert), 0.47 m (ember), 0.48 m (crimson) and 0.52 m (blue). Lumen Reach uses 0.40 m.

Content: CC-BY-4.0, Hyprune contributors (see ATTRIBUTION.md and LICENSE). Scripts: MIT.
