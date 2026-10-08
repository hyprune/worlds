# Lumen Reach material library

Eleven original generated seamless material masters cover the physical kit:
concrete, metal, paving, canvas, wood, frost, glass, strips, grating, snow and
rock. `generation.json` retains each exact prompt, tool provenance, author,
license and master SHA256. `source/rock.png` was generated with the built-in
imagegen tool on 2026-10-08 for the sculpted watershed divide and snow-basin
crags. The other masters remain the original release-world assets.

`python3 lumen-reach/materials/prepare.py` produces periodic 640px base-color,
normal and ORM derivatives and tests matching edge pixels. An eight-band 1024px
trim atlas reuses those masters with 8px gutters. Screens use the original Reach
alphabet and stepped-horizon icon; static UI remains authored placeholder art.
Derivatives and contact sheets are generated into ignored `tiles/`.

Former flat-color materials now reuse these images with explicit linear glTF
base-color factors: canvas for standards/leaves, concrete for earth/ivory, metal
for dark housings, frost for ice, and glass for practical-light lenses. These
aliases share texture objects and their mip chains. `material-factors.json` in
the built package records the factors because Blender's exporter can omit
constant Multiply colors. Cycles uses the same factors during rendering.

UV0 remains physically tiled, separate from UV1 irradiance. Architectural
atlases use 4px gutters; the shared leaf-card atlas uses 2px. Four home chunks,
two connector chunks, foliage and distant artwork retain independent spatial
organization; the current renderer has no runtime LOD selection or chunk
visibility contract. See `NOTES-rfc-gaps.md` and the final report for budgets.

## Rime Vault 0.6.0

Three additional built-in imagegen masters replace the Vault's mottled frost:
`frost-metal-v3` has fine vertical streaks, `rime-crust-v3` supplies pale granular
pipe-top buildup, and `condensation-v3` supplies glazed wall runoff. Exact prompts
are in `frost-v3-prompts.json`; source hashes and licensing remain in
`generation.json`. All three have periodic 640px albedo/normal/ORM derivatives.
Existing homes retain their former materials.

Rime coverage is geometric: upper pipe shells, local sills and small corner
snowbanks. Icicles use an opaque blue core and a separate low-emission facing
facet to suggest light scattering; this is a deliberate approximation with no
transmission extension or alpha-sorting dependency. Warm work lights illuminate
console fronts and floor trenches, with softer blue fill on high services.

The Vault has its own 2048px lightmap. A minimum UV1 area check rejects a pack
whose tiny islands would otherwise produce a mostly black engine bake. Thin
keys, grates and fixtures avoid unnecessary bevel islands.
