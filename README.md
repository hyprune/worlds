# Hyprune worlds

> **Hyprune** is an explorable, world-driven desktop environment for Hyprland: your workspaces become places you can walk through, with live windows on the walls. This repository holds the official **worlds** (Lumen Reach, Switchyard): sources, build pipeline and provenance; packages are published as GitHub releases. Install Hyprune through the [hyprune](https://github.com/hyprune/hyprune) repository (starter kits, Nix, Arch); learn more at [hyprune.com](https://hyprune.com). Licence: world content CC-BY-4.0, scripts MIT.

Official, original places for your desktop. **Early preview, building in the open.**

> What if the computer itself were an explorable world?

Worlds owns official environments, authoring source scenes, glTF exports, manifests, attribution and reproducible export recipes. It excludes runtime code, executable world behavior, shell UI and personal-use game assets.

A package is a data-only directory containing `world.json`, glTF 2.0 geometry and local assets. Use meters, +Y up, stable spawn/anchor IDs and separate UV1 lightmaps when baking illumination. Switchyard 0.1.1 targets the RFC-0004/core M1 world material profile 0.2. See [RFC-0004](https://hyprune.com/rfcs/0004-world-format/) before exporting.

**Worlds in this repo**

- **[Lumen Reach](lumen-reach/README.md)** (release world): Sun Court, Array Hall, Rime Vault and Signal Rise are four connected workspace homes, with physical tool mounts, open work zones, mountain vistas and paths to terraces, a rooftop, lower rooms and a cable gantry.
- **[Switchyard](switchyard/README.md)** (test world): Hyprune's first original world, an original blue-hour terminal with a bronze vault, six timber-canopied docks, a concourse, labeled cargo, a rail-city vista, surface anchors, collision, navigation and UV1 lightmaps. Kept as a walkable test map for paths, navigation, docking and renderer parity, and as a record of how the worlds evolved.

Schema examples remain synthetic manifest fixtures, not playable packages.

## Developer settings (`dev.env`)

Machine-specific values never go into this repository. The tools read them from
the environment, or from an optional `~/.config/hyprune/dev.env` (`$XDG_CONFIG_HOME`
if set): one `KEY=VALUE` per line, `#` comments, `~` expanded. The environment wins.

```sh
# ~/.config/hyprune/dev.env
HYPRUNE_BAKE_HOST=bakebox                  # SSH host with Blender; "local" on that host itself
HYPRUNE_GALLERY_DIR=~/review/stills        # stills for review (tools/check-lumen-session.py --gallery)
HYPRUNE_VIDEO_DIR=~/review/videos          # review videos (make gallery, tools/check-nested.py)
HYPRUNE_CONCEPT_DIR=~/concepts/release-world  # private concept sheets for tools/compare-*.py (not in this repo)
```

`HYPRUNE_BAKE_HOST` has no default: the bake wrappers refuse to start without it,
and refuse a host that resolves to the machine they run on (use `local` there).
An unconfigured stills or video directory prints one warning naming where the
output went instead. `tools/devenv.py` prints the effective values.

## Build and distribution

Run `make build`, `make validate`, and `make film`. Blender runs only on the remote mains-powered bake host through `tools/remote-blender.sh`; set `HYPRUNE_BAKE_HOST` (see Developer settings below). Generated worlds live in `dist/`, beauty stills and films in `artifacts/`. Sources, original texture master PNGs, provenance, build recipes and small validation reports belong in git. Generated glTF/BIN/PNG/BLEND/video files are ignored and produced for directory or `make release` tar.zst distribution; no automatic CI bake is configured yet. See [RFC gaps](NOTES-rfc-gaps.md) for the optional Map and route-graph proposals.

Validation also needs Node: run `make navmesh-deps` once (installs the pinned Recast/Detour build, `recast-navigation-js`, into `tools/navmesh/`). `tools/check-navmesh.py` builds a navmesh from each package's exported collision with the Hyprune agent (radius 0.3 m, height 1.8 m, climb 0.35 m, route slope 0.4). It checks that every spawn, route node and edge, stair lane and screen approach is reachable from the default spawn, and gates narrow routes, undeclared jump-up roofs, drop-in pits and walkable floor outside the visibility areas. It writes a JSON report and a top-down `navmesh.svg`. Reviewed exceptions live in each world's `navmesh-allow.json`, pinned by id and area. The check sees collision only: render-only obstructions are `check-route-clearance.py`'s job.

**Blueprint plans.** `tools/derive-blueprint.py PACKAGE [--output DIR] [--in-place] [--levels auto|N] [--svg-preview OUT.png] [--create-map]` derives the optional `com.hyprune.blueprint` 0.1 extension (RFC-0004 amendment; the Director's Map shows it from IPC 0.20): one technical plan per level, `blueprint/<level>.svg`, in the frame of the package map (`com.hyprune.map`, or the legacy Switchyard map's documented 900 x 1000 transform). It reads source (0.6) and release (0.7) packages, builds the navmesh as above and draws walkable floors, plan-cut walls (collision cut 0.9 m above each floor), hatched stairs and ramps, openings, mounted screens, tool/data mounts, area outlines and names, the walking graph, a 10 m grid and a title block with scale bar and north arrow. Levels are split from the navmesh floor heights wherever floor lies over floor (1..6, `--levels N` forces N). Elements carry a role `class` and per-role stroke widths but no colours, so the consumer's theme colours them. SVGs are simplified until each fits 64 KiB and all fit 256 KiB, or the tool fails. `--in-place` writes the SVGs and the extension into the package (`make lumen-build` and `make build`/`make blueprint` do this); `--svg-preview` renders a dark review image (`{level}` in the name gives one PNG per level); `--create-map` gives a package without any map a north-up `com.hyprune.map` frame and an overview `map.svg`. The tool depends only on this repository (`make navmesh-deps`, plus `make gltf-deps` for 0.7 packages). `tools/check-blueprint.py PACKAGE` (in `make validate`, `make lumen-validate` and on the release package in `make lumen-release-check`) enforces the extension shape, level ordering, byte budgets, core's map SVG subset plus the class vocabulary, the frame, and that every spawn and route node lies in a level band. `make blueprint-test` runs the unit tests. Method, heuristics and limits are documented at the top of `tools/blueprint.py`; the opening finder is deliberately conservative (collinear tall wall jambs with the wall continuing past both, floor at one height through the gap), so open-plan worlds show few or none.

`make lumen-budgets` / `make budgets` (part of the release targets; `make gltf-deps` once) write glTF-Transform `inspect()` budgets: visible triangles, draws and GPU MiB including mips and lightmaps. `LUMEN_BASELINE=<previous package>` adds deltas.

Since Lumen Reach 0.8.0, `make lumen-release` ships a world format 0.7 package. It validates the source package (`dist/`), then `tools/remote-optimize.sh` runs on the bake host: material textures become UASTC KTX2 with basisu 2.1.0, geometry gets glTF-Transform meshopt with 16-bit quantisation (stock cleanup off), and the PNG lightmaps are re-appended. `tools/gltf/verify.mjs` then diffs every world.json index against the source. Schema 0.7 and core world-check (`OPTIMISE_CORE`, a build of the core the meta repo pins) follow. The perf gate (`tools/check-perf-gate.py`: nested route capture, p50/p95 GPU ms and settled dynamic-resolution scale against the previous release; `LUMEN_PERF_BASELINE=<previous package>` measures both in one session) runs before the archive, which is built from `dist-07/`. Switchyard's `optimize` stays behind `HYPRUNE_FORMAT_07=1`. gltfpack is not used: it renumbers nodes and materials.

## Content policy

Official assets must be original or properly attributed CC0/CC-BY-4.0. Nothing without that provenance, even as temporary tests, screenshots or thumbnails. For every asset record author, source, license and modifications in the manifest/ATTRIBUTION.md. Keep editable sources and document reproducible export steps.

Default original content license: **CC-BY-4.0** (see LICENSE). Scripts and tooling are **MIT** (see LICENSE-MIT); mark each script `SPDX-License-Identifier: MIT`. Original documentation is CC-BY-4.0 here. Third-party assets retain their upstream license; preserve notices and mark exceptions explicitly. Attribute original content to “Hyprune contributors,” link the package source, link the license and indicate modifications.

## Boundaries and contracts

- [RFC-0001: umbrella architecture](https://hyprune.com/rfcs/0001-umbrella/)
- [RFC-0003: IPC `0.2` (core also accepts `0.1`)](https://hyprune.com/rfcs/0003-ipc/)
- [RFC-0004: world format `0.2`](https://hyprune.com/rfcs/0004-world-format/)
- [Machine-readable schemas and fixtures](https://github.com/hyprune/schema)
- [Roadmap M0–M3](https://hyprune.com/roadmap/)

RFCs are proposed implementation targets pending review. Read them now in [the docs source](https://github.com/hyprune/docs/tree/main/src/content/docs/rfcs) if the site is not deployed. Each core release must publish its exact Hyprland compatibility target and supported contract versions. Hyprune is new code; Hypr3D is a lessons-only historical reference.

## Contributing

See the [organization guide](https://github.com/hyprune/.github/blob/main/CONTRIBUTING.md) and [Code of Conduct](https://github.com/hyprune/.github/blob/main/CODE_OF_CONDUCT.md). Contract changes begin with an RFC amendment and schema fixtures. Keep provenance and failure evidence with your PR.

Licenses: [CC-BY-4.0 content](LICENSE), [MIT scripts](LICENSE-MIT).
