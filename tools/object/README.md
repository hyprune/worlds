# Object directories: import, check and libraries

Tools for [RFC-0011](https://hyprune.com/rfcs/0011-objects/) object directories
(`object.json` + glTF + `thumbnail.png`) and object libraries. The rules live in the
schema repository's shared validator (`validate('object')`, `validate('library')`); these
tools gather what it needs and run it. Blender runs only on the bake host.

```sh
tools/object-import src/lamp/lamp.glb objects/street-lamp --name "Street lamp" --surface floor --collision box
tools/object-import src/resident/resident.glb characters/resident-teal --character --name "Resident (teal)" --strip-fingers
tools/object-import --adopt characters/resident-blue --character --name "Resident (blue)" --license CC-BY-4.0 --author "Hyprune contributors"
tools/object-check objects/armillary objects/machines/*/ characters/resident-*/
tools/library-pack hyprune-starter --version 0.1.0 --dry-run
```

## tools/object-import

Every source needs a `PROVENANCE` note beside it (`Source:`, `Author:`, `Licence:`; characters
also `Animations:` and `Resemblance check:`, see `tools/npc/provenance.py`). Licence and author
default to the note.

| Step | Where | What it does |
| --- | --- | --- |
| `gltf/object-prep.mjs` | bake host | Decodes meshopt and quantisation and unpacks KTX2 to PNG (basisu), so Blender can read any glTF. |
| `object/object_import.py` | bake host, Blender | Metres (`--units`), +Y up (`--up`), front +Z (`--forward`); origin at the support point of `--surface` (floor: base centre, wall: back centre, ceiling: top centre, any: bounds centre); decimation to `--max-tris` (default 50,000; `--item` 2,000; `--keep NODE` leaves a node whole); textures to `--max-texture` (2,048 px; `--item` 512); `--collision box\|convex` adds a `proxy` node outside the glTF scene (never drawn, at most 2,000 triangles); export to `.gltf` + `.bin` + PNG. Skinned sources are refused (use `--character`). |
| `remote-optimize.sh` | bake host | meshopt + 16-bit quantised geometry, UASTC KTX2 textures with mips, and `verify.mjs` (same nodes, meshes and materials by index and name). `--no-compress` skips it. |
| `object/thumbnail.py` | bake host, Blender | 256 x 256 PNG with alpha: three-quarter front view from the left, 20 deg up, framed on the drawn geometry; characters in the first frame of `idle`. |
| `gltf/object.mjs measure` | here | Exact rest-pose bounds (skinned meshes skinned at rest), triangles, largest texture, GPU estimate; for characters clip speeds (`extras.speed`), height and the `sit` seat height. |
| `object/manifest.py` | here | Writes `object.json`: flags over `--base` (traits, slots or a machine an author wrote) over defaults; measured bounds and character values always win. Without `--fixed` the object gets `movable` (`--surface`, `--free-rotation`, `--scale-range`). |
| `object-check` | here | Below. |

`--character` replaces the first three steps with `tools/npc-import` (rig, clips, in-place
motion, budget, meshopt + KTX2, `hyprune-npc-check`) and records the measured clips, height
and seat height in the `character` trait. The seat height is the lowest point of the middle
of the thighs above the root in the `sit` clip's final pose; it is listed only within the
0.2-1 m range seat anchors use. `--adopt DIR` takes a directory whose scene is already
normalised (published characters, objects built by a script): thumbnail, measurement,
manifest (the existing `object.json` is the base) and check.

## tools/object-check

`tools/object-check DIR... [--format F] [--json]` reads each directory and calls the shared
validator (`SCHEMA_DIR`, default `../schema`) with the glTF, the file list, the thumbnail
size and the measured values: manifest schema and trait rules, glTF extension rules, node,
material and variant names, character clips and speeds, bounds within 1 cm of the decoded
geometry, triangle, texture and GPU budgets, thumbnail size, directory limits and attribution
coverage. Build sources (`build.py`, `PROVENANCE`, `README.md`, `*.report.json`) are listed as
ignored and never packed. Links, devices and executable files fail. Exit 0 when every
directory passes.

## tools/library-pack

Builds a library (`library.json`, `LICENSE`, `ATTRIBUTION.md`, `objects/<id>/`) from a spec in
`libraries/<name>.json`, checks every object and the library with the shared validator,
writes a reproducible `<id>-<version>.tar.zst` (sorted, fixed time, numeric owner 0) and
the record for the meta repository's `libraries/releases.json` (`sha256`, `nixHash`,
`published: false`). `--dry-run` stops before anything is tagged or uploaded; publishing is a
separate, reviewed step.
