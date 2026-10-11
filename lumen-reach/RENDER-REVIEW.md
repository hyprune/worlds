# Lumen Reach 0.7.0 render review

0.7.0 is a playability pass, not an art pass. The review standard was: no holes,
no sky leaks, no missing faces, no windows lost in geometry, and nothing that
blocks walking or ordinary fly. The previous Rime Vault art review is preserved
in `reports/render-review-0.6.0.md`; 0.5.0's is in `reports/render-review-0.5.0.md`.

Engine evidence is the sixth bake only (manifest `f7b53674…`). The any-angle
sweep captured 56 native-4K views: nine sanitized review poses, four homes,
eleven targeted inspections (pole, seam, roofs, soffits, aqueduct, spires,
basin exterior) and 32 views from seed 7009, half walkable and half elevated up
to 60 m. Every view was captured with visibility culling on and off; all 56
pairs have zero changed central pixels. The route harness captured the 18 hero
poses. All home screens and tool anchors are visible and clear of walls.

Reviewed and accepted:

- `rise-exterior` is an inspection pose pressed against the mountain shell
  crown. The frame shows rock and snow faces with no sky through them, so it is
  a too-close camera rather than a missing face.
- `random-20`/`random-26` are inside the closed basin sky at 47–52 m looking
  high. The flat dark blue matches the night texture's uniform upper band; it is
  not the clear colour.

Known and deliberately out of scope for 0.7.0: the jagged mountain crown seen
from above, soft distant panorama at 4K (1774×887 master), and angular joints
in the aqueduct arch blocks (they read as joints, not holes, in the sweep).

Contact sheets and selected raw stills were reviewed outside the repository;
the sweep and route records are in `reports/any-angle-0.7.0/`.
Blender ran only on the bake host. Engine testing was nested only.
