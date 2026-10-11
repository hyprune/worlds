# Hand-written vs derived visibility for Lumen Reach 0.8.x (2026-10-10)

Both variants are the 0.8.1 release package (format 0.7, core `49c8408`),
identical except `world.json` `visibility`: the hand-written
`lumen-reach/visibility.json` (13 areas), or `tools/derive-visibility.py`
output for the 0.8.1 source (144 regions + 7 owner areas; 52 s, 243 M rays on
the bake host; deterministic). Isolated nested session, native 4K Intel, Medium, fixed
0.5 scale.

| measure | hand-written | derived |
|---|---|---|
| batches submitted, mean of 72 any-angle views (of 99) | 44.2 | 40.4 (-8.6 %) |
| median | 34.5 | 33.5 |
| views with fewer / equal / more batches (derived vs hand) | | 13 / 57 / 2 |
| region-culled batches, mean | 3.4 | 12.6 |
| culled frame identical to unculled (changed px > 8 levels) | 71 / 72 | 72 / 72 |
| hand vs derived frames identical | 71 / 72 (the 1 differs by 8e-7 of pixels) | |
| route capture GPU ms p50 / p95 (400 poses, 2 alternating rounds) | 9.124 / 10.442 | 9.124 / 10.466 |
| CPU render ms, mean over views | 0.185 | 0.169 |
| eye samples where regions hide a sampled-visible unit | n/a | 0 of 14892 |
| world.json | 100 KB | 155 KB |

Per view (`visibility-hand-vs-derived.json`): the derived regions cut the
Sun Court home view 94 -> 78 batches, three review poses 92 -> 50, 89 -> 53 and
58 -> 36, `rise-corner-se` 63 -> 27. They cost more at `03-rime-vault`
(35 -> 51): the hand-written region hides Signal Rise from the whole vault,
but a real sight line through the stair-door frame reaches it. That is why the
hand-written variant is the one not identical to its unculled frame there
(about 4 pixels missing). It is under the sweep's loss threshold, but it is a
culling error the derived set does not make.

## Recommendation

Switch Lumen to derived visibility in the next minor release (0.9.0), not in
the 0.8.1 patch. The case is correctness and maintenance, not frame rate:

- Correct on every measured view (72/72 identical, 0 hidden-visible eye
  samples), where the hand-written set already misses one real sight line;
  every geometry change (0.7.1's portal, 0.8.1's vault edge) otherwise needs
  hand edits and a nested review.
- About 9 % fewer batches overall, up to 45 % on some poses, and slightly
  less CPU submission.
- No measurable GPU gain: the 4K Intel frame is fill-bound (same p50,
  +0.2 % p95, within noise).

Wire it as a build step (derive on the bake host after the bake, before
`lumen-validate`), keep `check-visibility.py` plus the sweep's culling pairs
as the gate, and keep `lumen-reach/visibility.json` only as an input of
declared openings if needed. 0.8.1 keeps the hand-written regions.
