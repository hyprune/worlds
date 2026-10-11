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
| `make_test_rig.py` (Blender) | Mixamo-named test rigs with the usual export faults, for testing the tools. |

The output report (`OUT.report.json`) lists every step, warnings, clip renames, measured
speeds and the `--clips-from` bone report. `hyprune-npc-check` (core) checks the result.
