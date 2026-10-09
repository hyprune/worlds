# Lightmap UV charting: xatlas vs Blender smart_project (2026-10-09)

Run on the bake host (`tools/uv-eval/`): `dump_groups.py` (Blender 5.2) dumps
each Lumen 0.8.0 lightmap group's triangulated world-space mesh, its baked UV1
and a timed re-run of the build's `smart_project` + `pack_islands`;
`evaluate.py` charts and packs the same mesh with xatlas 0.0.10 (MIT) at the
group's bake resolution and padding (texels-per-unit shrunk until one atlas
fits; `result.json`). `waste.py` measures how much atlas the smallest charts
take (`waste.json`).

| group | res | coverage B / X | median px/m B / X | density CV B / X | charts B / X | charts < 2x2 texels B / X | unwrap s B / X |
|---|---|---|---|---|---|---|---|
| sun-court | 2048 | 0.183 / 0.220 | 8.4 / 8.8 | 0.005 / 0.127 | 17807 / 7612 | 14177 / 2704 | 1.0 / 4.9 |
| foliage | 1024 | 0.213 / 0.076 | 33.4 / 19.5 | 0.017 / 0.076 | 10368 / 10368 | 45 / 1809 | 0.3 / 12.2 |
| array-hall | 1536 | 0.110 / 0.199 | 5.2 / 6.7 | 0.004 / 0.123 | 13948 / 5400 | 11852 / 2639 | 0.6 / 3.8 |
| rime-vault | 2048 | 0.198 / 0.212 | 9.8 / 9.8 | 0.006 / 0.093 | 18904 / 9641 | 14747 / 5259 | 0.8 / 6.5 |
| signal-rise | 2048 | 0.159 / 0.214 | 5.6 / 6.2 | 0.009 / 0.120 | 22551 / 9575 | 19316 / 4295 | 0.6 / 6.5 |
| connector-descent | 768 | 0.466 / 0.639 | 12.1 / 13.9 | 0.008 / 0.021 | 1555 / 369 | 1216 / 29 | 12.2 / 0.2 |
| connector-ascent | 768 | 0.470 / 0.628 | 11.7 / 13.4 | 0.006 / 0.020 | 1573 / 344 | 1216 / 24 | 12.3 / 0.1 |

B = Blender (current build), X = xatlas. Bake time is unchanged by
construction: same resolution and samples (bake 1.9-4.8 s per group, OptiX).

**Recommendation: keep smart_project; do not adopt xatlas.** xatlas gives +5 to
+29 % median texel density on six groups but -42 % on foliage, 10-25x less
uniform texel density (CV 9-13 % vs < 1 %), and 4-12x slower unwraps on the big
groups. Tuning xatlas chart cost changed nothing: chart count is set by mesh
connectivity (thousands of separate small parts), which no charter can merge.

**What would help instead (follow-up, not in 0.8.0).** In the five large
groups, charts under 2x2 texels hold only 0.19-0.29 % of the lit area but,
with the 4 px bake margin on every side, occupy **34-43 % of the atlas**
(`waste.json`). Lighting those parts without atlas space (the research doc's
stage 3: probe or object-AO lighting for small props, or merging them into
their parent's chart) would free about a third of each lightmap, roughly
1.3x linear texel density at the same memory or the same density in ~60 % of
the lightmap memory (lightmaps are ~87 MiB of Lumen's GPU budget).
