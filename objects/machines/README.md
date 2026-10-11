# Machine objects

Five starter **machines** and the item they move: world objects that show the
state of real systems (CI pipelines, queues, hosts, deploys, builds) once data
is bound to them. Each is an object directory in the shape of
[RFC-0011](https://hyprune.com/rfcs/0011-objects/) (`object.json`, a glTF,
thumbnail), with the `machine` trait and slots of
[RFC-0013](https://hyprune.com/rfcs/0013-live-objects/). Both RFCs are drafts,
so these manifests (`formatVersion` `"0.10"`, the format that adds movers,
items and machines) are drafts too. Until a core supports them, worlds can
place the glTFs as world format 0.8 objects (below).

Original procedural geometry in the Lumen Reach language (warm timber, pale
stone, dark metal, cyan, mint and amber light). Textures are 256 px copies of
the Lumen Reach wood, concrete and metal masters. CC-BY-4.0, Hyprune
contributors; build scripts MIT.

| Machine | Shows | Inputs | Triangles |
| --- | --- | --- | --- |
| `ci-conveyor` | A CI pipeline: jobs drop from a hopper, pass four lit stations (build, test, package, deploy) and land in the output bin, or the reject bin when they fail. | `stage` enum ×4, `jobStarted`/`jobPassed`/`jobFailed` events, `progress`, `queued`, `pipeline` | 4,612 |
| `queue-stack` | A queue: one crate per ten items on a shelf rack, a depth counter, a lantern, stripe and flag for the oldest item. | `depth` 0–500, `level` ok/warn/fail, `name` | 888 (+ crate copies) |
| `server-rack` | Hosts: eight units, each with a health light and a fan whose speed follows load. | `health` enum ×8, `load` 0–1, `name` | 2,818 |
| `deploy-lift` | A deploy: the release crate rides a platform past queued, building and rolling stops to the live deck. | `status`, `progress`, `environment`, `finished` | 1,974 |
| `build-monitor` | A build: a glowing face with a state glyph, a halo that turns while building, a burst on success. | `status`, `progress`, `succeeded` | 1,568 |
| `job-token` | The item that rides the conveyor's tracks (`mover`, `item: true`), its band showing the job state. | (item state) | 116 |

## Conventions

- **Axes and origin.** glTF +Y up, metres, front +Z; the origin is the base
  centre (bounds min Y = 0), as RFC-0011 asks of floor objects.
- **Names.** A glTF node name, the material of a state slot and the slot id are
  the same slug (`stage-1-lamp`), so a drive target `state:stage-1-lamp` or
  `animation:stage-1-spinner` names the node directly. Numbered parts count from
  1, bottom to top or along the flow.
- **State slots** own their node, mesh and one material named like the slot, so
  a palette applied to one slot never touches another.
- **Palettes** are RFC-0013's colour + emission entries in `object.json`; the
  first entry is the rest state. Every state is *also* authored in the glTF as a
  material `<palette>-<state>` (for example `lamp-running`) listed with
  `KHR_materials_variants`: optional (never in `extensionsRequired`), ignored by
  loaders that do not know it, and handy for previewing states in any glTF
  viewer. The manifest's palette is authoritative; the variant materials carry
  the same colour and emission.
- **Stacks** (`waiting`, `progress`, `crates`) name one node drawn at its first
  grid cell; a runtime hides it at rest and draws copies by the layout.
- **Toggles** are plain nodes (`alarm-flag`, `gate`, `glyph-ok` …).
- **Tracks** are asset-space polylines in `slots.tracks`; the conveyor also
  carries them as nodes (`track`, `track-p00` …) for tools that read the glTF.
- **Collision.** Each machine has a box proxy node `proxy` outside the scene's
  node list (never drawn), referenced by the `collidable` trait.
- **Value-driven lift.** The platform is a `bob` (amplitude 1.44 m, period 16 s)
  listed in `machine.positions` with range 0.75–1.25, bottom to top. A plain
  0.8 world shows it riding up and down.
- **Non-colour cues.** States differ in more than hue where it matters: the
  queue's flag, the monitor's glyphs, the lift's gate, the conveyor's reject bin.

## Placing them in a world format 0.8 package

Copy the directory under the package (for example `objects/ci-conveyor/`) and
add an `objectAssets` entry from the manifest:

```json
{"id": "ci-conveyor", "scene": "objects/ci-conveyor/object.gltf",
 "animations": <traits.decorative.animations>, "collision": {"node": "proxy"}}
```

## Building

```sh
make machines           # Blender on the bake host -> dist/objects/machines/<id>/
make machines-install   # optimise (UASTC KTX2, meshopt, quantisation; verify.mjs) -> objects/machines/<id>/
python3 objects/machines/check.py   # schema validator + hyprune-world-check on a test package, draft rules
```

`build.py` in each directory builds one asset with `kit.py` (shared geometry,
materials, palettes and the RFC-0011/0013 manifest writer). `optimise.sh` stages
each build as a minimal package so the world optimiser
(`tools/remote-optimize.sh`) runs unchanged.

Concept renders (Eevee, bake host) come from the built glTFs:

```sh
blender -b -P objects/machines/render.py -- --mode sheet --machine ci-conveyor --out OUT
python3 objects/machines/sheet.py OUT sheet.png --thumbnail dist/objects/machines/ci-conveyor
blender -b -P objects/machines/render.py -- --mode lineup --out OUT && python3 objects/machines/lineup.py OUT lineup.png
blender -b -P objects/machines/render.py -- --mode turntable --seconds 10 --out FRAMES
```

`scenarios.py` holds the input values each render shows. Labels' text, items
and effects in the renders stand in for what a runtime draws.
