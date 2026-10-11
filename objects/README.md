# World objects

Reusable objects that worlds place by reference (world format 0.8 `objectAssets`
and `objects`; RFC-0004 amendment "world 0.8 placed objects"). Each object is a
small glTF asset plus an `object.json` descriptor: the `objectAssets` entry a
world copies, with `scene` made package-relative. Objects are render-only unless
they declare a static collision proxy, and are lit at runtime (sun plus an
ambient probe from the world's baked light), never lightmapped. Animations are
declarative per node (spin, orbit, bob), so core can pause them off-screen and
honour reduced motion.

| Object | Build | Notes |
| --- | --- | --- |
| `armillary` | `objects/armillary/build.py` | Instrument globe with a cyan network inside three nested rings. Each ring spins about an axis in its own plane (its own path around the sphere); the globe turns slowly. First placed at the Lumen Reach Sun Court instrument terrace. |

| `machines/*` | `make machines`, `make machines-install` | Five starter machines (CI conveyor, queue stack, server rack, deploy lift, build monitor) and the job token item, as RFC-0011 object directories with RFC-0013 machine traits (drafts). See [machines/README.md](machines/README.md). |

`make objects` builds them on the bake host into `dist/objects/<id>/`.
Original procedural geometry, CC-BY-4.0, Hyprune contributors.
