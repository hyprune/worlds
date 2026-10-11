# Machine Yard: attribution

Machine Yard (`com.hyprune.machine-yard`) is original content by **Hyprune contributors**,
licensed [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). Source and build recipe:
<https://github.com/hyprune/worlds/tree/main/machine-yard>.

| Path | Author | Licence | Provenance |
| --- | --- | --- | --- |
| `scene.gltf`, `scene.bin` | Hyprune contributors | CC-BY-4.0 | Original procedural geometry, `machine-yard/build.py` (Blender). |
| `objects/ci-conveyor/`, `objects/queue-stack/`, `objects/server-rack/`, `objects/deploy-lift/`, `objects/build-monitor/`, `objects/job-token/` | Hyprune contributors | CC-BY-4.0 | The machine object assets of this repository, [`objects/machines/`](https://github.com/hyprune/worlds/tree/main/objects/machines): original procedural geometry (each directory's `build.py`), KTX2 encodes of the Lumen Reach tiles, thumbnails. Unmodified copies (build scripts left out). |
| `objects/fx-spark/` | Hyprune contributors | CC-BY-4.0 | Original procedural geometry, `machine-yard/effects.py`. |
| `textures/*-albedo.png`, `textures/*-normal.png` | Hyprune contributors | CC-BY-4.0 | The Lumen Reach material tiles (concrete, paving, wood, metal, rock): original generated masters recorded in `lumen-reach/materials/generation.json`, made periodic by `lumen-reach/materials/prepare.py`. Unmodified copies. |
| `textures/lightmap-*.png` | Hyprune contributors | CC-BY-4.0 | Cycles diffuse irradiance bakes (direct + indirect, no albedo) on UV1, OIDN RTLightmap denoised, peak-normalised sRGB. |
| `object.json` files, `world.json`, `machines.bindings.json` | Hyprune contributors | CC-BY-4.0 | Written by the build. |
| `preview.png` | Hyprune contributors | CC-BY-4.0 | Cycles render of the built scene with the machines placed. |

No third-party assets, fonts or images are used.
