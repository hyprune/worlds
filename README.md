# Hyprune worlds

Official, original places for your desktop. **Early, building in the open.**

> What if the computer itself were an explorable world?

Worlds owns official environments, authoring source scenes, glTF exports, manifests, attribution and reproducible export recipes. It excludes runtime code, executable world behavior, shell UI and personal-use game assets.

A package is a data-only directory containing `world.json`, glTF 2.0 geometry and local assets. Use meters, +Y up, stable spawn/anchor IDs and separate UV1 lightmaps when baking illumination. Switchyard 0.1.1 targets the RFC-0004/core M1 world material profile 0.2. See [RFC-0004](https://hyprune.com/rfcs/0004-world-format/) before exporting.

**Worlds in this repo**

- **[Lumen Reach](lumen-reach/README.md)** (release world): Sun Court, Array Hall, Rime Vault and Signal Rise are four connected workspace homes, with physical tool mounts, open work zones, mountain vistas and paths to terraces, a rooftop, lower rooms and a cable gantry.
- **[Switchyard](switchyard/README.md)** (test world): Hyprune's first original world, an original blue-hour terminal with a bronze vault, six timber-canopied docks, a concourse, labeled cargo, a rail-city vista, surface anchors, collision, navigation and UV1 lightmaps. Kept as a walkable test map for paths, navigation, docking and renderer parity, and as a record of how the worlds evolved.

Schema examples remain synthetic manifest fixtures, not playable packages.

## Build and distribution

Run `make build`, `make validate`, and `make film`. Blender runs only on the remote mains-powered bake host through `tools/remote-blender.sh`; configure `HYPRUNE_BAKE_HOST` as needed. Generated worlds live in `dist/`, beauty stills and films in `artifacts/`. Sources, original texture master PNGs, provenance, build recipes and small validation reports belong in git. Generated glTF/BIN/PNG/BLEND/video files are ignored and produced for directory or `make release` tar.zst distribution; no automatic CI bake is configured yet. See [RFC gaps](NOTES-rfc-gaps.md) for the optional Map and route-graph proposals.

Validation also needs Node: run `make navmesh-deps` once (installs the pinned Recast/Detour build, `recast-navigation-js`, into `tools/navmesh/`). `tools/check-navmesh.py` builds a navmesh from each package's exported collision with the Hyprune agent (radius 0.3 m, height 1.8 m, climb 0.35 m, route slope 0.4). It checks that every spawn, route node and edge, stair lane and screen approach is reachable from the default spawn, and gates narrow routes, undeclared jump-up roofs, drop-in pits and walkable floor outside the visibility areas. It writes a JSON report and a top-down `navmesh.svg`. Reviewed exceptions live in each world's `navmesh-allow.json`, pinned by id and area. The check sees collision only: render-only obstructions are `check-route-clearance.py`'s job.

## Content policy

Official assets must be original or properly attributed CC0/CC-BY-4.0. Nothing without that provenance, even as temporary tests, screenshots or thumbnails. For every asset record author, source, license and modifications in the manifest/ATTRIBUTION.md. Keep editable sources and document reproducible export steps.

Default original content license: **CC-BY-4.0** (see LICENSE). Scripts and tooling are **MIT** (see LICENSE-MIT); mark each script `SPDX-License-Identifier: MIT`. Original documentation is CC-BY-4.0 here. Third-party assets retain their upstream license; preserve notices and mark exceptions explicitly. Attribute original content to “Hyprune contributors,” link the package source, link the license and indicate modifications.

## Boundaries and contracts

- [RFC-0001: umbrella architecture](https://hyprune.com/rfcs/0001-umbrella/)
- [RFC-0003: IPC `0.2` (core also accepts `0.1`)](https://hyprune.com/rfcs/0003-ipc/)
- [RFC-0004: world format `0.2`](https://hyprune.com/rfcs/0004-world-format/)
- [Machine-readable schemas and fixtures](https://github.com/hyprune/schema)
- [Roadmap M0–M3](https://hyprune.com/roadmap/)

RFCs are proposed implementation targets pending owner review. Read them now in [the docs source](https://github.com/hyprune/docs/tree/main/src/content/docs/rfcs) if the site is not deployed. Each core release must publish its exact Hyprland compatibility target and supported contract versions. Hyprune is new code; Hypr3D is a lessons-only historical reference.

## Contributing

See the [organization guide](https://github.com/hyprune/.github/blob/main/CONTRIBUTING.md) and [Code of Conduct](https://github.com/hyprune/.github/blob/main/CODE_OF_CONDUCT.md). Contract changes begin with an RFC amendment and schema fixtures. Keep provenance and failure evidence with your PR.

Licenses: [CC-BY-4.0 content](LICENSE), [MIT scripts](LICENSE-MIT).
