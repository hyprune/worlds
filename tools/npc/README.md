# NPC characters: import tooling

`tools/npc-import` turns a Meshy Pro export (GLB, Mixamo skeleton template, skin, 30 fps;
FBX as a fallback) into the canonical NPC character core loads (RFC-0010 draft; spec in
the docs page "NPC characters"). Blender runs only on the bake host.

```
tools/npc-import npc-src/resident/resident.glb build/resident.glb --strip-fingers --render build/
tools/npc-import npc-src/porter/porter.glb build/porter.glb --clips-from npc-src/resident/resident.glb --render build/
```

| Step | What it does |
| --- | --- |
| `provenance.py` | Requires `PROVENANCE` beside the source: Source, Author, Licence (CC-BY-4.0/CC0), Animations, Resemblance check. |
| `npc_import.py` (Blender) | Metres (cm/mm fixed), Z up / facing -Y in Blender = Y up / +Z in glTF, feet at the origin, `root` added, object-level keys dropped, optional finger strip (weights to the hands), optional `--clips-from` (rotations by bone name, Hips translation x hip-height ratio; missing/extra bones and rest-orientation differences reported), clip names by `clip-map.json` (unknown names pass through), Hips held in place (default: horizontal translation zeroed; `--keep-sway` removes only the travel), 30 fps, 4 weights, decimation over `--max-tris` (8000). |
| `compress.mjs` | meshopt + 16-bit quantization (one volume: one shared skin), KTX2 textures (basisu), `extras.speed` from the measured root motion. |
| `npc_render.py` (Blender) | Check video: idle turntable, walk side-on over a checker floor scrolling at the walk speed (foot sliding shows), walk front three-quarter. |
| `npc_compare.py` (Blender) | Two characters side by side (e.g. a retargeted clip vs the rig's own), walk then run, side and front, each over a floor scrolling at its own planted-foot speed. |
| `npc_silhouette.py` (Blender) | Rest-pose silhouettes of the source vs the decimated output from four sides, centroid-aligned IoU and an overlay PNG. |
| `compare_clips.py` | Local rotations of two clips per bone (median/worst degrees) and, with `--sliding`, the planted-foot speed and its spread. |
| `make_test_rig.py` (Blender) | Mixamo-named test rigs with the usual export faults, for testing the tools. |

`--clips-from` retargets: for each shared `mixamorig` bone (not fingers) the source's
rotation change from its rest pose, in world space, is applied to the target's rest pose;
other bones stay at rest; the Hips translation is scaled by the hip-height ratio. Measured
against rigs' own clips from the authoring tool it matches with a median of 2.5-8 deg per
bone and slides no more than the tool's own clips. `--leg-ik` (a two-bone leg IK onto the
source's foot path) made both worse in that test, so it is off by default. `--keep-own A,B`
keeps the target's own clips of those names. Translation is kept on the Hips only (authoring
tools key every bone). The clip map is in priority order: each canonical name takes the
first alias present; other clips keep their names in lowercase.

The output report (`OUT.report.json`) lists every step, warnings, clip renames, measured
speeds and the `--clips-from` bone report. `hyprune-npc-check` (core) checks the result.
