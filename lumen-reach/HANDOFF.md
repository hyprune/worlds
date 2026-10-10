# Lumen Reach 0.8.1 handoff — 2026-10-10

**Patch release candidate verified; not published, not pushed.** Published
baseline: 0.8.0 (release package kept at `artifacts/opt-0.8.1/before/`,
SHA-identical to `reports/release-0.8.0.json`; source at `before-src/`).

## Release candidate

- Release package `dist-07/com.hyprune.lumen-reach/` (format 0.7) from the
  source `dist/` baked on 10.2.2.2 at `1f21028`.
- Manifest SHA256 `4f047839cbd6…` (full hashes in `reports/release.json`).
- Archive `artifacts/releases/com.hyprune.lumen-reach-0.8.1.tar.zst`,
  39,736,290 bytes, SHA256
  `d86878a981ed38ee851a6bc09aa545dcea781345d65cce604313c8fe71617766`.
  76 extracted files identical to `dist-07/`; schema 0.7 VALID; core
  world-check (`49c8408`) PASS. Built by `make lumen-release
  LUMEN_PERF_BASELINE=artifacts/opt-0.8.1/before` end to end (38 min).
- Gallery: `screenshots/optimise-2026-10/lumen-0.8.1-vault-slot-before-after.jpg`.

## Fix

**Rime Vault ceiling slot.** The vault ceiling and both side shells stopped at
authoring y 76; the floor runs to 74. That left a 2 m strip open to the sky
over the descent threshold and the north lip. It was visible from reachable
positions: looking up from the vault spawn showed day sky overhead (nested
`vault-north-up`). They now reach y 74. The wide north opening onto the vista
is designed and unchanged.

**Check extended.** `check-sky.py --enclosures lumen-reach/enclosures.json`
(in `lumen-validate`): declared indoor rooms (rime-vault, connector-descent,
entry-vestibule) with their designed open faces. From every walkable eye
inside, an upper-hemisphere ray that reaches the sky must leave through an
open face. 0.8.0 FAILS (rime-vault: 290 sky rays from 49 eyes, out through
the roof and west side of the strip); 0.8.1 PASSES (0 leaks). Side effect:
the 0.19 m2 walkable sliver outside the visibility areas was the east end of
the same lip; `check-navmesh` flagged its pin as stale. Lumen now has no
pinned navmesh findings.

## Verified (0.8.1 release package unless noted)

- `make lumen-validate` PASS on the source (all gates, enclosures included).
- verify.mjs PASS (indices unchanged, collision within 2.1 mm).
- Any-angle nested: 72 views (+3 vault views), 0 culling losses, 6/6 walking
  probes inside, jump x=25.64, fly x=30.27.
- Route traversal: 64 nodes, 126 directed traversals, 14 alternate stairs.
- Perf gate vs 0.8.0, same session: p50 9.116 -> 9.132 ms (+0.2 %), p95
  10.419 -> 10.496 ms (+0.7 %): PASS. Record `reports/perf/0.8.1.json`.

## Derived visibility evaluation

`reports/any-angle-0.8.1/visibility-evaluation.md`: hand-written vs
`tools/derive-visibility.py` on the 0.8.1 release package, same 72 views.

- Batches: 44.2 -> 40.4 (-8.6 %); some poses -45 %.
- Identical frames: 72/72 for derived vs 71/72 for hand-written (the
  hand-written vault region hides a real sub-pixel sight line).
- GPU ms along the routes: unchanged (fill-bound).

Recommendation: switch to derived visibility in 0.9.0 as a build step, for
correctness and maintenance; 0.8.1 keeps the hand-written regions.

## Next steps for the lead

Review the sheet, then push `worlds` and publish `lumen-reach-v0.8.1` with the
archive above. Update `hyprune/worlds/releases.json`. Decide on derived
visibility for 0.9.0.

---

# (previous) Lumen Reach 0.8.0 handoff — 2026-10-10

**Release candidate verified; not published, not pushed.** First release on
world format 0.7. Published baseline: 0.7.2 (package kept at
`artifacts/opt-0.8.0/before/`, SHA-identical to `reports/release-0.7.2.json`).

Scope (owner's overnight direction): the remaining proven third-party
optimisations from `core/docs/research/2026-10-proven-techniques.md`. No
content changes beyond lightmap samplers. Full write-up with numbers:
`reports/optimise-0.8.0/README.md`.

## Release candidate

- Release package: `dist-07/com.hyprune.lumen-reach/` (format 0.7), the
  deterministic optimisation of the source package `dist/` (format 0.5, baked
  on 10.2.2.2 from build inputs at `f5e8b82`).
- Manifest SHA256 `68632d462d9077ef…`, scene SHA256 `50c03d10094d1a30…`
  (full hashes in `reports/release.json`).
- Archive `artifacts/releases/com.hyprune.lumen-reach-0.8.0.tar.zst`,
  39,390,230 bytes, SHA256
  `3b507f8ba151c99983496d82a413526b3090e0c38057a841b54ee2758dcb27e1`
  (`sha256sum -c artifacts/releases/LUMEN-SHA256SUMS` from the repo root).
  76 extracted files identical to `dist-07/`; schema 0.7 VALID; core
  world-check PASS.
- Built by `make lumen-release LUMEN_PERF_BASELINE=artifacts/opt-0.8.0/before
  LUMEN_BASELINE=artifacts/opt-0.8.0/before` end to end (42 min).
- Core for every check and nested run: worktree `core-optimise` at `49c8408`
  (the commit the meta repo pins), plugin `a98e051d…`. `OPTIMISE_CORE` in the
  Makefile points there; set it to any build of the pinned core.
- Gallery `screenshots/optimise-2026-10/`: `lumen-0.8.0-before-after.jpg`
  (0.7.2 | 0.8.0 | CIEDE2000 heatmap | 1:1 crop of the worst block),
  `lumen-0.8.0-lightmap-mips-ab.jpg`, `lumen-0.8.0-any-angle-contact-sheet.jpg`.

## Results (0.8.0 release vs 0.7.2, nested, same session)

| | 0.7.2 | 0.8.0 | |
|---|---|---|---|
| package | 70.46 MiB | 41.37 MiB | -41 % |
| archive | 46.8 MB | 39.4 MB | -16 % |
| GPU memory | 270.5 MiB | 149.8 MiB | -45 % |
| load to ready (warm) | 2.68 s | 2.06 s | -23 % |
| GPU ms, 4 spawn poses | 9.43 | 9.40 | noise |
| route p50 / p95 GPU ms | 9.04 / 10.55 | 9.07 / 10.51 | noise |
| PSNR / mean dE2000 | | 36.2-41.3 dB / 0.53-0.87 | worst blocks equal at 1:1 |

1. **Format 0.7 build**: in `make lumen-release` (validate source -> remote
   optimise + verify -> schema 0.7 + world-check -> perf gate -> budgets ->
   archive). Switchyard's `optimize` stays behind `HYPRUNE_FORMAT_07=1`.
2. **Lightmap mips**: on for the six 4 px-gutter groups (not foliage).
   Shimmer on affected pixels -4.4 % (Sun Court), about 0 elsewhere. No memory
   or visual cost. Included.
3. **xatlas**: not adopted. It isn't clearly better than smart_project, and
   the lever is elsewhere: sub-2x2-texel charts take 34-43 % of each large
   atlas (`reports/optimise-0.8.0/uv-charting/`).
4. **Perf gate**: `make lumen-perf-gate`, in `lumen-release`. PASS (+0.4 % /
   -0.4 %). Record `reports/perf/0.8.0.json` is the next baseline when the
   same core build is used; otherwise pass `LUMEN_PERF_BASELINE=<0.8.0 package>`.

## Verified

- `make lumen-validate` PASS on the source package (all gates incl. navmesh,
  sky, route clearance; only the 0.19 m2 vault sliver allow-listed).
- `verify.mjs` PASS: 301 nodes / 106 materials / 78 lightmap bindings keep
  their indices; collision within 2.1 mm.
- Any-angle nested on the release package: 69 views, 0 culling losses, 6/6
  walking probes inside, jump x=25.64, fly x=30.27.
- Route traversal on the release package: 64 nodes, 126 directed
  traversals, 14 alternate stairs, 18 hero stills. PASS.

## Notes and open items

- The Python checks read format 0.5 only; validation runs on the source
  package and verify.mjs proves the release copy equivalent.
- The settled dynamic-resolution scale holds at 0.5 on Intel 4K for both
  releases (inside core's 10 ms budget band). It is a tripwire; GPU ms
  p50/p95 are the sensitive gate.
- Per-round GPU spread is about +/-5 % when several packages share a session
  (A/A on one package is ~1 %). Small GPU deltas are noise.
- The nested lock is shared with other agents overnight (core perf,
  shell upscaler); my runs queued behind them. Timings were taken while
  holding the lock.
- Remaining residual shimmer is material-texture and thin-geometry aliasing,
  not lightmaps.
- Not done: the stage-3 "small props without atlas space" work that the
  xatlas evaluation points to (needs a probe/vertex-AO path, which is a format
  question for the lead).

## Next steps for the lead

Review the sheets, then push `worlds` and publish `lumen-reach-v0.8.0` with
the archive above. Update `hyprune/worlds/releases.json` in the meta repo with
its URL and hash. It requires a core that loads format 0.7 (`49c8408`+).
