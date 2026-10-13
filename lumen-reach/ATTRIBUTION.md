# Lumen Reach attribution

All package assets: Hyprune contributors, CC-BY-4.0. Original procedural geometry,
geometric lettering, instrument/UI designs and numeric palettes. Original
imagegen material masters and complete prompts are in materials/generation.json;
PBR derivatives use the documented periodic seam-healing recipe. UV1 irradiance
is baked on the remote host with Cycles and OIDN. Layout and mood were informed
by private concept sketches; no concept imagery, wording or marks are included.
No imported game assets or iconography.
See texture-provenance.json in the built package for individual texture records.
Authoring source code is MIT, consistent with the existing world pipeline.

The 0.7.0 sky master is an original generated spherical panorama based on the
original watershed painting. `materials/sky.py` makes longitude periodic and
converges latitude to uniform pole colors. The cold basin derivative retains
the original night panorama provenance. All terrain, arches, spires, roof
details and walking bounds are procedural source geometry.

Residents (0.11.0): the four characters in `characters/` are the Hyprune
starter-kit residents (Hyprune contributors, CC-BY-4.0; provenance in the
repository's `characters/ATTRIBUTION.md` and each `object.json`), copied
unchanged. Their routes, benches and lines are original to this world.
