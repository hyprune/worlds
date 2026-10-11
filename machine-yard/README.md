# Machine Yard (test world)

`com.hyprune.machine-yard` 0.1.0, world format **0.8**. A compact terrace yard (30 x 22 m) in
the Lumen Reach language, built as the test world for **live machines** (RFC-0013): five
machine bays around a paved walking loop, so a walk-through can see each machine up close.
Original procedural content, CC-BY-4.0, Hyprune contributors; scripts MIT.

## Layout

North is -Z. The spawn `entrance` stands inside the south doors, looking north.

| Instance | Asset | Position (plinth top) | Facing |
| --- | --- | --- | --- |
| `build-1` | `build-monitor` | (0, 0.15, 1) | south (+Z), centre of the court |
| `ci-1` | `ci-conveyor` | (0, 0.15, -6.8) | south, along the north parapet |
| `queue-1` | `queue-stack` | (-10.5, 0.15, -3.5) | east, under the west roof |
| `rack-1` | `server-rack` | (-10.5, 0.15, 4.5) | east, under the west roof |
| `deploy-1` | `deploy-lift` | (10.5, 0.15, -3) | west, under the east roof |

- A paved loop (x -6..6, z -3.5..6, 2.4 m wide) passes in front of every machine; a spur leads
  to the entrance. Each bay is a 0.15 m stone plinth with a cyan base strip, with at least
  3 m clear around the machine and 4 m in front of it.
- Two timber roof wings on columns frame an open court. The north parapet and the east
  colonnade look over a valley to layered mountain ridges.
- One mounted workspace wall (`yard-screen`, 4.8 x 2.7 m) on the south wall, east of the
  doors, is the home of area `yard`.
- Collision: floor, walls, parapets, columns, plinths and props; each machine has a static
  box proxy (`proxy`, outside the drawn scene). A grid navigation mesh, one visibility area,
  a playable box and the walking loop as `com.hyprune.lumen-reach.routes` nodes (the route
  adapter core reads today) complete the package.
- Lightmaps: Cycles diffuse bakes on UV1 (four groups), OIDN denoised, with warm pools under
  the roof wings. The machines are placed objects, lit by core's probes, never baked; Blender
  imports decoded copies (`decode-objects.mjs`: meshopt decoded, KTX2 swapped for the PNG
  tiles they encode) as occluders in the bake and for the stills.

## Machines

The machines are the object assets in [`objects/machines/`](../objects/machines/README.md),
copied into the package's `objects/<id>/` (data files only): RFC-0011/RFC-0013 format
**0.10** manifests (`object.json` with the `machine` trait: typed inputs, drives and slots)
next to optimised glTF (meshopt, KTX2). The world's `objectAssets[]` entries stay world
format 0.8 (inline `scene`, the decorative `animations` and the `proxy` collision node), so
today's core loads the package; the 0.10 manifests are read only by the machines prototype.
The package becomes a world format 0.10 package (`objectAssets[].dir`) once core supports it.

`job-token` (the conveyor's item) and `fx-spark` (the stand-in effect piece built here by
`effects.py`, a small unlit diamond painted with the effect colour at runtime) are listed in
`objectAssets` without placed instances.

| Asset | Inputs | Slots |
| --- | --- | --- |
| `ci-conveyor` | `stage` x4, `jobStarted`, `jobPassed`, `jobFailed`, `progress`, `queued`, `pipeline` | states `stage-1-lamp`, `stage-2-lamp`, `stage-3-lamp`, `stage-4-lamp`; labels `label-title`; tracks `track`, `reject`; spawns `item-spawn`, `reject-in`; effects `success-fx`, `fail-fx`; stacks `waiting`, `progress` |
| `queue-stack` | `depth`, `level`, `name` | states `level`; labels `label-count`, `label-name`; stacks `crates`; toggles `alarm-flag` |
| `server-rack` | `health` x8, `load`, `name` | states `unit-1-light`, `unit-2-light`, `unit-3-light`, `unit-4-light`, `unit-5-light`, `unit-6-light`, `unit-7-light`, `unit-8-light`; labels `label-name` |
| `deploy-lift` | `status`, `progress`, `environment`, `finished` | states `phase-lamp-1`, `phase-lamp-2`, `phase-lamp-3`, `phase-lamp-4`, `beacon`; labels `label-env`; effects `burst-fx`; toggles `gate` |
| `build-monitor` | `status`, `progress`, `succeeded` | states `face`, `ring-glow`; effects `burst-fx`; toggles `glyph-ok`, `glyph-fail`, `glyph-run` |

## Bindings

`machines.bindings.json` (also installed at the package root) binds each placed instance's
inputs to the simulated sources `com.hyprune.sources.{ci,queue,rack,deploy,build}`:

```sh
HYPRUNE_MACHINES_PROTOTYPE=<package>/machines.bindings.json
```

It maps the sources' API-like words onto the machines' inputs (`success` -> `ok`,
`failed` -> `fail`, anything else -> `idle`), turns counters into events
(`jobsStarted` -> `jobStarted`, `successes` -> `succeeded`, `deploys` -> `finished`) and binds
repeated inputs once with `{n}` in the key (`health.{n}`, `stage.{n}`). `queue-1`'s `name`
has no source key and keeps its default. Without the prototype the world loads as an ordinary 0.8 world:
machines rest in their first palette state and spin at their authored speed.

## Build

```sh
make machine-yard          # decode the machines for Blender, then scene, bake, export, review stills
make machine-yard-stills   # re-render the stills from the saved .blend
make machine-yard-check    # schema 0.8, core's hyprune-world-check, and machines-check if built
                           # (YARD_MACHINES_CHECK=<core build>/machines-check)
```

Output: `dist/com.hyprune.machine-yard/`; stills and reports in `artifacts/machine-yard/`.
The review stills show a plausible running moment (some lamps lit, tokens on the belt, crates
on the shelves); the package itself rests in each palette's first state.
