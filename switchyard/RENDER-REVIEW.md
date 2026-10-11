# Switchyard visual review

## Initial flagship 0.1.0

The owner's feedback changed the target from a functional transit maquette to a flagship original environment. The owner's earlier original prototype scripts and images were reviewed, together with the Switchyard concept and an earlier prototype's walkthrough video. The resulting direction is a warm bronze/timber transit terminal against a blue-hour city, with a strong arrival silhouette and deliberate human-scale furnishings.

Review passes retained locally in ignored artifacts and logs:

1. Replace the maquette with a twenty-meter double-ribbed vault, arched station canopies, cargo hardware, signals, cables, upholstered seating, folded-leaf plants and a layered original vista. The first Cycles arrival render was overcrowded by the route sculpture; the main sign was outside the frame.
2. Move arrival back, rotate/lower the sculpture rings, darken walnut, soften practical-light intensity and move the sign into view. Review the five beauty views and material repeat sheet. The diffuser's pattern phase needed a procedural regular-cell correction in addition to edge healing.
3. Reduce the arrival sign, add compass/expansion-joint floor inlays and static idle route schematics. Asset checks caught collision helpers in the Blender beauty pass (the default glTF scene already excluded them), tiny UV1 overlaps around curved details, and touching buried undersides. Hide helpers for beauty rendering; tighten UV projection and separate buried bottoms/stem roots.
4. Inspect corrected Cycles stills and revalidate exported geometry. Explicitly convert emission-only vista materials to standard unlit art. Deduplicate texture objects to meet core's 512 MiB budget. Export tangents, including deterministic orthogonal fallback at 78 isolated degenerate caps. Schema/Khronos/UV/coplanar/navigation checks pass.
5. Inspect real core screenshots after a locked nested load/render/walk/exit test. Tiled surfaces, normals/roughness details, lightmaps and all six docks load. Core's opaque clerestory, distance fog and tone mapping differ from Cycles; editable haze cards are intentionally excluded from the default package scene until alpha support is available.
6. Review both ends of four film shots. Eevee hit its shadow-cache limit, so the final film uses GPU Cycles with denoising. Shorten the dock move to avoid a foreground canopy post and shorten/retarget the route move to finish on Studio rather than plain skyline. Finish with an elevated view showing the complete terminal structure. A restrained compositor glow softens practical lights.

All five final beauty stills and eight film endpoint previews were inspected. Six decoded MP4 frames at 0, 8.8, 13.5, 22, 27.5 and 35 seconds were inspected before gallery delivery; codec, size, duration, frame count and faststart also passed. Camera shots depict the authored environment and static dock graphics; there is no staged fake desktop telemetry. The actual runtime evidence is separately retained as `nested-arrival.png` and `nested-route.png`, with core revision and movement results in the nested report.


## Polish 0.1.1 / core M1

The owner's five requested changes were reviewed against actual core renders, rather than inferring fidelity from Cycles. `views.json` retains the five camera positions and targets, and specifies 1920×1080 with 60° vertical FOV. Blender derives its 36 mm sensor lens from that FOV; core's authenticated camera API supplies identical eye positions and roll-free orientations. The pose roundtrip is checked numerically. Comparison assembly adds labels/scales only; it never grades, crops or paints the engine image.

- The rounded D has a continuous left stem and a visibly curved right side, differing from O at eight pixels. Every glyph and every unique generated signage string appears in `lettering-proof.png`; coverage/shape checks accompany visual inspection of BUILD, STUDIO, APPLICATION DOCK and SWITCHYARD in the actual renders.
- The exhibit moves to x=-4.4 m, with a 1.1 m plinth and smaller orbit ribs. BUILD, RESEARCH and COMMONS read from both the default arrival and the matched concourse view. Its new collision footprint leaves the route clear.
- The original city kit gains three separated depth layers, terraced shafts, fork/sloped crowns, facade fins, occupied ribbon windows, signs, antennas and aviation markers. Three original landmarks are the Meridian lantern/spire, paired Relay towers/sky bridge and Observatory rooftop halo. Clear landmark footprints, terrace gaps and recessed bridge ends resolved the all-axis coplanar audit findings. A continuous original gradient sky sphere removes the old rectangular backdrop's upper edge.
- Translucent roof sheets become open ceramic slats and beauty-only haze cards are removed. Both renderers see the same visible geometry. No alpha support is needed for this package.
- Two original low-energy emissive maps provide fixed pane/bronze sheen. The pane's emission slot uses `KHR_texture_transform`; UV0 normal detail and UV1 irradiance remain independent. Cloth normal scale falls to 0.22, coated metal to 0.32. Ordinary emissive range replaces the unsupported HDR strength extension.
- Tiled surface density is measured from exported triangle UV area and physical area: stone's area-weighted median is 512 px/m; most other substantial surfaces are 1024 px/m, with curved brass near 1000 px/m. New GPU accounting includes M1's expanded visible vertices, both color/data views and every mip. All package PNG textures have individual provenance.

Multiple rebuilt still/engine pairs were inspected. The final five pairs and contact sheet are under `artifacts/switchyard/comparison-*.png` and `engine-blender-contact-sheet.png`; raw engine images are `engine-01-concourse.png` through `engine-05-vault.png`. The primary remaining differences are warm reflections/highlight roll-off, wood sheen, practical halo spread and the engine's fixed world-origin fog. UV1 remains normalized linear irradiance encoded in sRGB; no tone curve is baked into it to disguise these differences. AgX Medium High Contrast/Fog Glow and core's fixed ACES-style display curve are intentionally identified.

The actual 27-second engine walk uses IPC 0.2 collision-checked route/autodrive. Camera changes between segments change orientation at the current physical position; no translated camera path is substituted for walking. A 45° turn keeps the cross-concourse leg focused on the architecture; the last leg stops at the Studio approach with a settled dock view. Decoded frames are reviewed at 0, 5, 10, 15, 20 and 26 seconds. Native pointer hiding and debug-banner suppression apply only to the private nested startup config; core's reticle remains in the capture.

The revised 36-second Blender film retains the arrival/dock/route shots and ends with a wider elevated terminal/skyline view. Both endpoints of every shot are reviewed before the full render. Film rendering uses both remote RTX 3090s, 24 Cycles samples and GPU Open Image Denoise at full 1080p/24 fps. The full rerender was stopped at the owner’s wrap-up request, before delivery. The gallery retains the previous Blender film; the polished endpoint previews and completed engine walk remain available. All generated images, scenes and films remain ignored in git.


## Owner decision and closeout

The owner judged the rendering and lighting good, but found the uniform grid lifeless and lacking a world feeling. Switchyard will not be the release world. The finished polish, measured engine comparisons and RFC findings are retained as an original authoring reference for core and the next world. Further Switchyard work stopped at the owner’s request. The new release-world concept brief is untouched.
