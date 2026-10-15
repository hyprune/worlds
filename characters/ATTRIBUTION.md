# Characters attribution

All characters: **Hyprune contributors**, [original source](https://github.com/hyprune/worlds/tree/main/characters), [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).

This covers the models, skins, textures and animation clips of `resident-blue`,
`resident-crimson`, `resident-desert` and `resident-ember`. The project made the models,
rigs and animations with an AI 3D tool from its own concepts; the project holds full
rights to that tool's output, including the clips from its animation library, and
licenses them here under CC-BY-4.0. The designs were reviewed before publication and
resemble no third-party or game character. No third-party art, models or game assets are
imported.

Modifications from the tool's exports, all by `tools/npc-import` and `tools/npc/publish.py`:
units, axes and a `root` bone; translation keys kept on the hips only and the horizontal
travel removed (in-place clips, speed kept as `extras.speed`); clips renamed to the NPC
spec; for `resident-blue`, `resident-crimson` and `resident-ember`, clips retargeted from
`resident-desert`; weights limited to 4; decimated to 8,000 triangles; textures scaled to
1024 px and compressed (KTX2); geometry quantised and meshopt-compressed; public names and
licence metadata; in 1.1.0, `sit` and `sit_idle` removed (`tools/gltf/drop-clips.mjs`: the
starter motion pack's sit replaces them). `object.json` and `thumbnail.png` (a render of the character) are written
by `tools/object-import --adopt`. The raw exports are not part of this repository.

Retain attribution and document changes when redistributing modified content. Scripts
carry `SPDX-License-Identifier: MIT` and are covered by the repository's LICENSE-MIT.
