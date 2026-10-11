# Lumen Reach 0.6.1 — authored visibility

Prepared locally for owner publication. No push or GitHub release was performed.
The published art pass is preserved in [delivery-0.6.0.md](delivery-0.6.0.md).

The world now uses format 0.5 with visibility bounds, subtree ownership and
explicit directed links for every home and connector. Conservative aperture
regions retain shells and architecture seen through entrances. Shared foliage
and vistas stay visible. See [VISIBILITY.md](../VISIBILITY.md) for the full links,
paired timing table, visual checks, core hashes and limitations.

| Matched view | World submissions off → on (saved) | CPU render ms | GPU pass sum ms | Delivered frame ms |
| --- | ---: | ---: | ---: | ---: |
| 01-sun-court | 87 → 84 (3.45%) | 0.320 → 0.288 | 5.459 → 4.785 | 16.669 → 16.670 |
| 02-array-hall | 87 → 84 (3.45%) | 0.266 → 0.263 | 5.881 → 6.523 | 16.667 → 16.666 |
| 03-rime-vault | 87 → 73 (16.09%) | 0.275 → 0.246 | 5.480 → 4.582 | 16.667 → 16.672 |
| 04-signal-rise | 87 → 68 (21.84%) | 0.274 → 0.219 | 4.285 → 4.302 | 16.671 → 16.661 |
| court-east | 87 → 87 (0.00%) | 0.348 → 0.280 | 7.331 → 7.231 | 16.668 → 16.664 |

Native 4K on Intel PTL Low, fixed 0.5 internal scale, 64 samples per state in
ABBA order. Delivered frame cadence can remain at 60 Hz; short GPU deltas are
subject to clock/host noise. The final aperture correction was remeasured;
other views were retained only after verifying identical final submission sets.
Every record preserves its measured manifest hash and phase. Raw samples and
per-block medians are retained.

All physical assets and non-visibility manifest contracts are byte-identical.
World totals remain **222,403 triangles, 87 unfiltered material batches and
326.20 conservative GPU MiB**. The annotations save submissions, not resident
texture memory. Switchyard 0.1.2 is also annotated and validated; its open docks
conservatively retain all 134 batches. Its evidence is in
[Switchyard VISIBILITY.md](../../switchyard/VISIBILITY.md).

Validation passes for world schema 0.5, core loading, glTF, UV/material/placement,
walking/collision/routes, emissive fixtures and the visibility ownership/link
contract. 30 paired engine views and 134
region/route probes pass. Testing was nested only under the global flock; no
Blender bake, owner-session control or gallery-process action occurred.

Archive: `artifacts/releases/com.hyprune.lumen-reach-0.6.1.tar.zst`
Archive SHA256: `f0bf4f25abe4db0bda0029128d75404da011be5cc7194a9c4e0e68306a39e616`
Extracted files all match the final package. New engine comparison evidence is
under `artifacts/visibility-0.6.1/verified/`; the existing v3 gallery art delivery
remains the 0.6.0 image set because this release changes only visibility metadata.
