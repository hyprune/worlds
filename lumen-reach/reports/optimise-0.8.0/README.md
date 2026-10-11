# Lumen Reach 0.8.0: proven third-party optimisations (2026-10-10)

Source: `core/docs/research/2026-10-proven-techniques.md` (A.3, A.5, B, C).
All measurements are isolated nested sessions (native 3840x2160, Intel, quality medium,
fixed render scale 0.5, continuous rendering) on core `49c8408` (the commit the
meta repo pins), packages alternating in one compositor. Raw sessions live
under `artifacts/opt-0.8.0/`.

## 1. World format 0.7 release build

`make lumen-release` now validates the source package, optimises it on the bake
host (basisu 2.1.0 UASTC KTX2 for the 56 material textures, full mips; glTF-
Transform reorder + 16-bit quantisation + EXT_meshopt_compression, cleanup off;
PNG lightmaps re-appended) and archives the format 0.7 package. `verify.mjs`
proves every world.json index unchanged (301 nodes, 106 materials, 78 lightmap
bindings), collision within 2.1 mm, UV1/UV0 areas within the quantisation
bound. Schema 0.7 VALID, core world-check PASS. The optimiser is deterministic
(two runs byte-identical, 76/76 files).

`ab-summary.json` (3 rounds, 0.7.2 | 0.8.0 source | 0.8.0 release):

| | 0.7.2 | 0.8.0 release | change |
|---|---|---|---|
| package | 70.46 MiB | 41.37 MiB | -41.3 % |
| GPU memory (core `upload.gpuBytes`) | 270.54 MiB | 149.80 MiB | -44.6 % |
| load to ready (warm, median) | 2678 ms | 2058 ms | -23.1 % |
| upload CPU (warm) | 53.7 ms | 38.2 ms | -28.9 % |
| upload steps | 111 | 68 | |
| GPU ms, mean of 4 spawn poses | 9.43 | 9.40 | -0.3 % (noise ~ +/-5 % per round) |
| world shading pass, median | 3.24 ms | 3.13 ms | -3.5 % |

The 4K Intel frame is fill-bound, so compression saves memory, load and
package size, not frame time. Visual (`stills-compare.json`, CIEDE2000):
0.7.2 -> 0.8.0 release PSNR 36.2-41.3 dB, mean dE 0.53-0.87, p95 1.6-2.2,
2.8-6.6 % of pixels over dE 2; the worst 64 px blocks (UI placeholder text,
a vista card, stone) are indistinguishable at 1:1. Compression alone (0.8.0
source -> release) accounts for nearly all of it; mips + rebake alone are
48-55 dB. A before/after comparison sheet was reviewed (not included here).

Nested on the release package: any-angle sweep 69 views, 0 culling losses,
6/6 walking probes inside, jump x=25.64, fly x=30.27; route traversal 64
nodes, 126 directed traversals, 14 alternate stairs, 18 hero stills.

## 2. Lightmap mips

Groups with 4 px bake gutters (all but foliage) get LINEAR_MIPMAP_LINEAR;
core caps lightmap LOD at 2. A/B on the 0.8.0 source package (only the
lightmap sampler differs), three 24-frame walks at 3.5 m/s, 60 Hz
(`lightmap-mips-flicker.json`): the mips change 2.1-7.4 % of pixels; shimmer
(mean |second temporal difference| of luminance) on those pixels -4.4 % in the
Sun Court, -0.5 % on the Rise, +0.2 % in the Hall. No memory cost (core
already allocates the lightmap mip chain: 270.54 MiB either way), mean visual
change < 0.25/255. Included in 0.8.0: a small win, never a loss. Most residual
shimmer comes from material textures and thin geometry, which lightmap mips
cannot touch. An A/B comparison sheet was reviewed (not included here).

## 3. xatlas

Not adopted. See `uv-charting/README.md`: not clearly better than
smart_project (+5..29 % density on six groups, -42 % foliage, 10-25x less
uniform density). The real lever is the 34-43 % of each large atlas taken by
sub-2x2-texel charts (small parts with padding).

## 4. Perf gate

`make lumen-perf-gate` (in `lumen-release`): `tools/check-perf-gate.py` runs a
scripted nested route capture (400 eye-height poses every 3 m along all 126
directed route edges, 2 alternating rounds) and fails if GPU frame ms p50
grows > 8 %, p95 > 12 %, or the settled dynamic-resolution scale drops by >
0.05 (p50) / 0.08 (p05) against the previous release. With
`LUMEN_PERF_BASELINE=<previous package>` both are measured in one session;
otherwise it needs a record (`reports/perf/<version>.json`) from the same core
build. A/A noise is ~1 % per pose. Unit tests: `tests/test_perf_gate.py`.

0.8.0 vs 0.7.2, same session, inside `make lumen-release`: p50 9.039 -> 9.074
ms (+0.4 %), p95 10.548 -> 10.511 ms (-0.4 %), settled scale 0.5 / 0.5: PASS
(an earlier standalone run: +0.3 % / -0.3 %). The settled scale is a tripwire
on Intel 4K: core holds 0.5 while the GPU average stays inside its 10 ms budget
band. Record: `reports/perf/0.8.0.json`.
