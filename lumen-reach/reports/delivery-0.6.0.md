# Lumen Reach 0.6.0 — Rime Vault frost and density pass

Prepared locally for owner publication; no push or GitHub release was performed.
The preceding published world is preserved in [delivery-0.5.0.md](delivery-0.5.0.md).

## Rime Vault changes

- Three original material masters replace mottled frost with vertically streaked
  frozen steel, pale crystalline rime and glazed frozen condensation. Rime shells
  sit on pipe tops; ice fringes collect along pipe sides and console sills.
  Icicles use opaque blue cores and low-emission facing facets to suggest light
  scattering. Small snowbanks gather in perimeter corners.
- Five low console stations form two floor banks, with keyboards, foot lights,
  power leads and Reach-mark badges. A three-station wall bank fills a service
  wall. These are fixed process instruments; all 24 existing interactive mounts
  retain their IDs, poses, sizes and clear approaches.
- Overhead racks have insulated pipes, coupling flanges, captive bolts, support
  channels and threaded hangers. Grated service channels expose cable runs;
  warning edges, Reach-marked cases and a three-stack purge cluster add floor
  detail while retaining a broad central walking route.
- The sealed continuation has pressure jambs, interlocks, reinforced leaves,
  a lit center seam, guide lamps and warm spill suggesting an extension beyond.
  Amber console/floor pools and red practicals lead the room; blue fill picks
  out high cold services. Original Rime instrument art now uses warm amber lines.

Other home geometry and all route, stair and free-placement contracts are
unchanged. The visual fit is documented in [RENDER-REVIEW.md](../RENDER-REVIEW.md),
with raw comparisons in `artifacts/lumen-reach-v3/render-review.html`.

## Materials and bake quality

The three built-in imagegen assets are saved in `lumen-reach/materials/source/`
as `frost-metal-v3.png`, `rime-crust-v3.png` and `condensation-v3.png`. Exact
prompts are in [frost-v3-prompts.json](../materials/frost-v3-prompts.json); master
hashes, attribution and licenses are in [generation.json](../materials/generation.json).
Periodic 640px albedo/normal/ORM derivatives pass edge checks. All physical
materials retain texture coverage and explicit authored tint factors.

A first dense pack collapsed to 0.00010 useful UV1 area and produced a black
engine lightmap despite valid ranges and no overlaps. Thin parts now omit
unnecessary bevels, the Vault owns a 2048px atlas, and both authoring and package
checks reject useful UV1 area below 0.03. Final Vault area is **0.19210**.
The bad package is confirmed to fail the new guard. This fix changes the asset
pipeline only; it does not alter the owner’s renderer settings.

## Budgets

| Measurement | 0.5.0 | 0.6.0 |
| --- | ---: | ---: |
| World triangles | 199,911 | 222,403 |
| Rime Vault triangles | 22,236 | 44,700 |
| Estimated world draws | 84 | 87 |
| Conservative world GPU MiB | 285.62 | 326.2 |
| Package MiB | 57.81 | 66.57 |

World triangle growth is **11.25%**, below the 30%
allowance; estimated draw growth is **3.57%**, below 40%.
Static geometry remains merged by material within home/connector chunks, with
shared distant artwork and screen art. Draw estimates exclude applications,
HUD and postprocessing. GPU estimates include mip chains, color/data texture
views and expanded vertices. Runtime chunk culling/LOD remains a documented
core gap in [NOTES-rfc-gaps.md](../../NOTES-rfc-gaps.md).

The 4K Medium run used **Mesa Intel(R) Graphics (PTL)**.
Rime Vault's short stationary sample measured **59.98 rendered
frames/s**, with render scales **0.375, 0.4375** and
median GPU pass sum **4.54 ms**. Output remained 3840×2160.
These are short observations, not a sustained route FPS guarantee. Full samples
and loaded binary hashes are retained under `polish-v3/`.

## Verification and delivery

Schema 0.2, glTF, UV packing, original material provenance, fixture/decal checks,
all mount approaches and free volumes, walking support and capsule checks pass.
The isolated nested engine traversed **126 directed graph edges** and **14
alternate stair flights**. The comparison uses freshly captured 0.5.0 and 0.6.0
camera paths on the same test harness. Switchyard's complete validation suite
passes unchanged. All Blender execution used 10.2.2.2 via the remote wrapper.
All engine sessions held `/tmp/worldshell-nested.lock`; the real session was
never controlled, and the gallery autocommit process was never signaled.

- Eighteen raw 4K stills: `gallery:screenshots/release-world-v3`
- Before/after clip: `gallery:videos/rime-vault-v3.mp4`
- String-only metadata: `gallery:videos/rime-vault-v3.json`
- Clip: **42.00s, 1920×1080, 30 fps**; three
  matched views alternate before/after with labels, no grading or retouching.
- Archive: `artifacts/releases/com.hyprune.lumen-reach-0.6.0.tar.zst`
- Archive size: **43.12 MiB**
- Archive SHA256: `fe2f7b492cd21578964a7f4cd4ac5f799209c318f7350c506df04bb46be28dd4`

Video encoding occurred in `/tmp`, then completed files were staged and moved
into the gallery after inspection. Screen art in this focused comparison is
static authored UI. Steam and baked illumination are static; ice scattering is
an opaque-material approximation. Large workspace and walking clearances keep
the room broader than the narrow painted concept corridor.
