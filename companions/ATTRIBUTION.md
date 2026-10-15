# Companions attribution

All companions: **Hyprune contributors**, [original source](https://github.com/hyprune/worlds/tree/main/companions), [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).

This covers the models, skins, textures and animation clips of `neon-cyber-muse`,
`skeptical-ember` and `starlit-stretch`, and the `companion-moves` motion pack made from the
same source. The project made the models, rigs and animations with an AI 3D tool from its own
concepts; the project holds full rights to that tool's output, including the clips from its
animation library, and licenses them here under CC-BY-4.0. No third-party art, models or game
assets are imported.

Modifications from the tool's exports, all by `tools/npc-import`, `tools/gltf/motion-pack.mjs`
and the publishing step: units, axes and a `root` bone; finger bones removed; translation keys
kept on the hips only and the horizontal travel removed (in-place clips, speed kept as
`extras.speed`); clips renamed; `idle` retargeted from `resident-desert`; weights limited to
4; decimated to 8,000 triangles; textures scaled to 1024 px and compressed (KTX2); geometry
quantised and meshopt-compressed; public names and licence metadata. `object.json` and
`thumbnail.png` (a render of the character) are written by `tools/object-import --adopt`.
The raw exports are not part of this repository.

Retain attribution and document changes when redistributing modified content. Scripts
carry `SPDX-License-Identifier: MIT` and are covered by the repository's LICENSE-MIT.
