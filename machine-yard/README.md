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
| `ci-1` | `ci-conveyor` | (0, 0.15, -7) | south, along the north parapet |
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
- Lightmaps: Cycles diffuse bakes on UV1 (four groups), OIDN denoised. The machines are
  placed objects, lit by core's probes, never baked; they are present as occluders in the bake.

## Machines

The machine assets in `objects/<id>/` are **placeholders** built from primitives
(`machines.py`) with the slot names of the machines prototype: a states slot owns one node, one
mesh and one material named like the slot (`stage_1_lamp`, `unit_3_light`, `face`...).
Each directory carries an RFC-0011/RFC-0013 `object.json` (format **0.10** manifests: the
`machine` trait with typed inputs and drives, and `states`, `labels`, `tracks`, `spawns`,
`stacks`, `toggles` and `effects` slots). The world's `objectAssets[]` entries stay world
format 0.8 (inline `scene`, `animations`, `collision`), so today's core loads the package;
the 0.10 manifests are read only by the machines prototype. The package becomes a world
format 0.10 package (`objectAssets[].dir`) once core supports it.

`job-token` (the conveyor's item) and `fx-spark` (the stand-in effect piece) are listed in
`objectAssets` without placed instances.

| Asset | Inputs | Slots |
| --- | --- | --- |
| `ci-conveyor` | `status`, `stage` x4, `jobStarted`, `jobPassed`, `jobFailed`, `queued`, `lastJob` | 4 lamp states, 4 spinner animations, `belt` track with 4 station stops, `item_spawn`, `waiting` stack, `alarm` toggle, `success_fx`, `fail_fx`, `label_title` |
| `queue-stack` | `depth`, `level` | `crates` stack (24 on four shelves), `age_lamp`, `label_count` |
| `server-rack` | `health` x8, `load` x8 | 8 light states, 8 fan animations |
| `deploy-lift` | `status`, `progress`, `environment`, `finished` | `platform` (value-driven `bob`), 4 phase lamps, `beacon` (states + spin, on the mast), `gate_closed` toggle, `burst_fx`, `label_env` |
| `build-monitor` | `status`, `progress`, `passed`, `lastJob` | `face` state, `ring` animation, `burst_fx`, `label_title` |

## Bindings

`machines.bindings.json` (also installed at the package root) binds each placed instance's
inputs to the simulated sources `com.hyprune.sources.{ci,queue,rack,deploy,build}`:

```sh
HYPRUNE_MACHINES_PROTOTYPE=<package>/machines.bindings.json
```

It maps the sources' API-like words onto the machines' inputs (`success` -> `ok`, deploy
`phase` -> `deploying`/`done`/`failed`), turns counters into events and binds repeated inputs
once with `{n}` in the key. Without the prototype the world loads as an ordinary 0.8 world:
machines rest in their first palette state and spin at their authored speed.

## Build

```sh
make machine-yard          # objects, scene, bake, export, review stills (Blender on the bake host)
make machine-yard-stills   # re-render the stills from the saved .blend
make machine-yard-check    # schema 0.8 and core's hyprune-world-check
```

Output: `dist/com.hyprune.machine-yard/`; stills and reports in `artifacts/machine-yard/`.
The review stills show a plausible running moment (some lamps lit, tokens on the belt, crates
on the shelves); the package itself rests in each palette's first state.
