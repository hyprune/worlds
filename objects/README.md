# World objects

Reusable objects that worlds place by reference (world format 0.8 `objectAssets`
and `objects`; RFC-0004 amendment "world 0.8 placed objects"). Each object is an
[RFC-0011](https://hyprune.com/rfcs/0011-objects/) object directory: a glTF asset,
`object.json` (id, licence, bounds, traits, slots) and `thumbnail.png`, checked by
`tools/object-check` (`make objects-check`) and ready for a library
(`tools/library-pack`, see [tools/object](../tools/object/README.md)). A world 0.8
package copies the glTF and adds an `objectAssets` entry: `scene` made
package-relative, `animations` from `traits.decorative`, `lighting`. Objects are render-only unless
they declare a static collision proxy, and are lit at runtime (sun plus an
ambient probe from the world's baked light), never lightmapped. Animations are
declarative per node (spin, orbit, bob), so core can pause them off-screen and
honour reduced motion.

| Object | Build | Notes |
| --- | --- | --- |
| `armillary` | `objects/armillary/build.py` | Instrument globe with a cyan network inside three nested rings. Each ring spins about an axis in its own plane (its own path around the sphere); the globe turns slowly. First placed at the Lumen Reach Sun Court instrument terrace. Traits `decorative` and `movable` (surfaces `any`: it floats, origin at the globe centre). |
| `machines/*` | `objects/machines/<id>/build.py` | Live machines and their item (object format 0.10 draft, RFC-0013); see [machines](machines/README.md). |
| `screens/*` | `python3 objects/screens/build.py` | Workspace screens (object format 0.11 `mount` trait): wall bezels and stands at 16:9 (3.2 x 1.8 m) and 21:9 (4.2 x 1.8 m). Placed, each shows the next free workspace (or the one you choose) and becomes its home. Thumbnails by `tools/object/thumbnail.py` (bake host). |

| `machines/*` | `make machines`, `make machines-install` | Five starter machines (CI conveyor, queue stack, server rack, deploy lift, build monitor) and the job token item, as RFC-0011 object directories with RFC-0013 machine traits (drafts). See [machines/README.md](machines/README.md). |

`make objects` builds the armillary on the bake host into `dist/objects/armillary/`,
renders its thumbnail, checks it and installs it into `objects/armillary/` (Lumen Reach's
build reads `dist/objects/`).
Original procedural geometry, CC-BY-4.0, Hyprune contributors.
