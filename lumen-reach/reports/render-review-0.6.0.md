# Lumen Reach 0.6.0 render review

This pass focuses on Rime Vault against its concept sketch (not included).
The sixteen previous camera poses remain unchanged; two additional poses inspect
its console row and sealed continuation. Eighteen raw 3840×2160 Medium captures
are in `artifacts/lumen-reach-v3/after-4k/`. Dynamic
internal resolution is recorded separately from native output size.

The before/after comparison uses freshly captured 0.5.0 and 0.6.0 views at the
same 1920×1080 output, pose and 60° vertical FOV. Three identical seven-second
camera paths alternate before/after in the video. Only labels and cuts are
added. Engine stills are ungraded; thumbnail comparison sheets preserve aspect
ratio. The concept is a composition/mood reference, not a matched camera.
Run `python3 tools/compare-rime-v3.py` for the linked raw-image review in
`artifacts/lumen-reach-v3/render-review.html`.

The concept's defining density is long console banks, layered overhead services,
edge frost, wet metal, low warm practicals and a lit sealed continuation. The new
Vault has five low floor stations and a three-station wall bank, keyboard beds,
foot lights, power leads, cases, grated cable channels and a purge-vent cluster.
Pipe racks now have flanges, captive bolts, channels and hangers. The center lane
and the full interactive screen approaches remain clear; the room is broader
than the concept's tight corridor because those validated work volumes remain.

The mottled all-over frost is gone from the Vault. Dark directional steel,
glazed vertical condensation and pale granular rime are separate materials.
Rime geometry follows pipe tops and console sills; thin icicles have blue cores
and small emissive edge facets. Corner snowbanks stay out of the routes.
The opaque ice treatment suggests scattering but provides no true transmission.
The new source masters, exact prompts and hashes are retained in `materials/`.

Warm amber instrument lines, console grazing light, red practicals and blue
upper fill make the room more coherent with the concept. The pressure door has
layered jambs, interlocks, reinforcement, a center light seam and warm guide
lights. It reads as a closed extension with light beyond. The engine retains
less specular sheen and softer floor light pools than Cycles. Floors remain
smoother and less wet-looking than the painted reference, and steam is still a
static alpha-card approximation. These limits remain visible in the raw output.

Engine review caught a real bake failure: too many tiny beveled parts exhausted
fixed lightmap gutters, collapsing useful UV area despite valid ranges and no
overlaps. Thin detail now avoids those bevels; the Vault's separate atlas is
2048px with 19.2% useful UV coverage. An authoring/package guard rejects a pack
below 3%. The final engine captures show the restored lighting on the new kit.

Sun Court, Array Hall, Signal Rise, foliage and connector geometry retain their
triangle counts. Their matched views were captured again for regression review.
The preceding all-home review is preserved in `reports/render-review-0.5.0.md`.
All 24 interactive anchors, route/stair graphs and free-placement volumes keep
their original contracts. New fixed consoles are authored process artwork, not
additional interactive mounts or claims about live application state.

See `reports/polish-v3/` and `reports/release-0.6.0.json` for budgets,
shader/material coverage, lightmap evidence, full route traversal, engine hashes
and the archive. Blender ran only on the bake host. Engine testing held the
nested lock; the host session was untouched.
