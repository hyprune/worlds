# RFC-0004 authoring gaps found by Switchyard

Contract reviewed: RFC-0004 including its **M1 format 0.2 amendment**, RFC-0005, RFC-0001, schema v0.2 and core `docs/M1.md`. Switchyard **0.1.1** uses world format **0.2** and the standard M1 material profile. Remaining proposals below are optional; this world requires no experimental extension. Core revision/plugin hash and the exact manifest/scene used for capture are retained in `switchyard/reports/nested-report.json`.

1. **Map view has no blueprint contract.** Propose optional `extensions.com.hyprune.switchyard.map` for this prototype: `{version, path, projection: "xz", north: [0,0,-1], bounds: [minX,minZ,maxX,maxZ]}`. `path` names an original local `map.svg`; its coordinates derive from the station authoring spec. A shared SDK/RFC should standardize a safe image format, world-to-image transform, orientation and semantic label locations. Runtime must never fetch SVG references or execute it; this SVG has neither scripts nor external resources. Unknown optional metadata is ignored.
2. **Navigation is mesh only, not a graph.** Supply the normative triangular navigation mesh and an optional `com.hyprune.switchyard.routes` authoring graph `{version, nodes:[{id,position}], edges:[{from,to,width}], semantics}`. All edges are bidirectional, in world meters. It describes static centerlines, not autopilot scripts, travel transactions or rail riding. Propose a shared declarative graph extension with connectivity/capsule tests; Core M1 now provides authenticated IPC 0.2 explicit routes and collision-checked autodrive, used by the engine walk capture. Loading this optional authoring graph automatically remains an SDK/shell contract gap.
3. **Helper node visibility is implicit.** Collision and navigation references may point at glTF nodes outside the default scene. Explicitly define whether those nodes are legal and must stay invisible; require full world transforms to remain evaluable. Switchyard uses unparented helper nodes, no transforms dependent on invisible ancestors. Current core's loader processes collision for these nodes and renders only scene members.
4. **Spawn position reference point is unstated.** RFC says capsule at spawn but does not specify feet/eye/capsule center. Current core treats position as feet and adds 1.7 m for the camera. This package follows that implementation. Specify capsule feet and eye offset separately before other authors guess.
5. **Lightmap production requirements need precision.** RGB irradiance and decoding are well defined. The RFC does not specify normalization peak, denoiser, minimum atlas island separation/mip depth, or a sample reference scene. This pipeline records measured normalization and intensity per atlas, excludes albedo/emission, uses OIDN RTLightmap, authored atlas padding and Cycles dilation. Propose numerical reference fixtures and a supported mip/gutter policy; do not silently change the lighting equation.
6. **Variants are not a built-in contract.** Quiet mode can be a shell presentation preference; this world is already static and silent. Different illumination needs separately versioned data or a future explicit variant structure. No new undocumented top-level fields are added.
7. **Spatial semantics vs lightweight schema.** The CLI validates manifest shape, not indexed assets, UV islands, spawn clearance, connectivity, scale or coplanarity. The SDK should expose a single package check covering these. This repo supplies supplemental checks and retains their evidence; a schema pass alone is not labeled a full package audit.
8. **Distribution policy was unspecified.** The initial worlds README does not say whether generated scenes belong in git. Sources, recipes, provenance, small reports and authoring specs are committed; GLTF/BIN/PNG/BLEND/video outputs stay ignored and are built on the remote host for directory/tar.zst releases. Bake CI and reproducibility tolerances across Blender/GPU versions remain future infrastructure work.
9. **Static anchors do not define project identity.** RFC-0005 gives screen-type bindings, not project collections, workspace assignment, telemetry or persistence keys. Docks use the guaranteed planar-window type; IDs are stable. Project-context and live platform signals remain SDK/shell work. This package contains no fictitious integration state or executable hooks.

10. **M1 closes the tiling/material-profile gap.** RFC-0004 format 0.2 now defines sampler modes, mip filtering, `KHR_texture_transform` per slot, negative/mirrored UVs, transformed normal handedness and independent UV1 irradiance. Switchyard adopts it: physical UV0 tiles and the original brass trim sheet remain, while the pane's new emissive sheen uses a standard per-slot texture transform. Its normal map stays on untransformed UV0. Shared atlas rectangle/gutter and texel-density authoring metadata are still unspecified; package-local provenance records them. The exported density audit measures substantial tiled triangles independently, rather than inferring density from texture dimensions alone.
11. **Alpha and atmosphere still need a renderer contract.** Core M1 renders world alpha as opaque. The polish replaces glazing with open opaque ceramic slats and removes haze cards, giving both renderers the same visible geometry. Original opaque city layers and a continuous procedural gradient sky sphere provide the fallback. Propose an optional atmosphere/sky profile specifying alpha modes/sorting, camera-relative fog, palette/color space and an opaque fallback. Core's current fixed fog depends on distance from the world origin, not distance from the camera, and also affects unlit sky art; the package cannot tune its density/color. The matched images preserve this difference instead of grading it away.
12. **Glossy reflection/environment profile is absent.** M1's analytic key/sky specular produces useful roughness detail, but cannot reflect the warm practical lights or architectural surroundings as Cycles does. Prioritise an environment/IBL or bounded reflection probe contract with color space, orientation, diffuse/specular separation and resource budgets. Switchyard's low-energy original pane/bronze sheen maps are explicit emissive approximations, separate from base color and irradiance. They remain fixed as the camera moves. Geometry-specific contact shadows are baked; SSAO/contact darkening remains a measured core quality/budget decision.
13. **Tone mapping, bloom and HDR emission need measurable parity fixtures.** Cycles beauty/film use AgX Medium High Contrast plus restrained Fog Glow; the inspected M1 renderer uses a fixed ACES-style curve and display encoding. Lightmap intensity retains measured linear irradiance normalization, with no display curve baked into UV1. Matched views show the remaining highlight/floor/wood differences. The inspected tone pass has no spatial glow kernel, so practicals are sharper than Cycles; define supported bloom/exposure behavior and reference images before promising visual parity. Core also ignores `KHR_materials_emissive_strength`: Switchyard now keeps practicals within ordinary glTF emissive range and exports no strength extension. Future HDR emission support should honor the standard extension rather than changing lightmap energy or painting highlights into albedo.
14. **Camera/presentation controls are not a package capability.** IPC 0.2 exposes camera pose but no lens/FOV. Core's fixed 60-degree vertical FOV forced shared authoring camera/lens changes for a valid comparison. Propose explicit camera FOV and capture/reticle presentation controls outside the immutable world manifest. The comparison images are unretouched captures, including core's center reticle. A private nested config suppresses the start-hyprland debug banner and hides the idle native pointer; core sources and the owner's session remain untouched.

Current evidence: five identical-pose 1920×1080 comparisons, a 27-second collision-checked core walk, all three-axis coplanar probes, independent exported UV0 density/UV1 overlap checks, v0.2 schema and Khronos validation. GPU accounting now mirrors M1's expanded visible vertices, **all mip levels** and separate linear/sRGB texture views inside 512 MiB; lightmaps retain clamp/linear sampling even though the current core allocates their mip chains. See `switchyard/RENDER-REVIEW.md` and `switchyard/reports/` for measured results.

## Lumen Reach: workspace homes and mount vocabulary (2026-10-07)

Each of the four connected areas is one workspace home, not a selection of
unrelated workspaces. Sun Court owns slot 01, Array Hall slot 02, Rime Vault slot
03, Signal Rise slot 04. Each declares exactly one primary workspace anchor and
its own tool mounts. User configuration binds a slot to a real workspace; this
package never hardcodes compositor workspace IDs. Future homes instantiate a
consistent theme kit under new area/slot IDs without changing existing anchors.

Until RFC-0004/0005 standardize typed mounts, the valid format 0.2 package uses
`extensions.com.hyprune.lumen-reach.mounts` (optional; never required):

```json
{
  "version": 1,
  "areas": [{"id":"sun-court","workspaceSlot":"01","theme":"sun-court",
    "primaryAnchor":"sun-court-slot-01-facade-wall-01",
    "toolAnchors":[],"dataAnchors":[]}],
  "mounts": [{"anchorId":"sun-court-slot-01-facade-wall-01",
    "areaId":"sun-court","workspaceSlot":"01","mountType":"facade-wall",
    "role":"mounted-workspace"}],
  "objects": []
}
```

Roles are `mounted-workspace`, `tool`, `data`. Mount types are `facade-wall`,
`hanging-wall`, `wall-inset-console`, `banner`, `lectern`, `operator-desk`,
`field-rig`, `kiosk-pillar`, `globe`, `crate`, `blast-door-screen`,
`terminal-bench`, `radar-dish`. Screen mounts have ordinary RFC anchors with
`com.hyprune.window`, exact front-facing world pose/size and physical frames.
Data objects are extension `objects` entries `{id,pose,mountType,areaId,
workspaceSlot,node?}` and appear in their area's `dataAnchors`; they do not
pretend a globe or dish is a rectangular window. Stable IDs follow
`<area-id>-slot-<two-digit-slot>-<mount-kind>-<ordinal>`. Optional node fields
are re-resolved after every export, never used as persistent identity.

Proposal for core: normalize this declarative extension into typed spatial
mounts and workspace homes, preserving anchor IDs; publish role, mount type,
owner area and slot. Primary mounted workspace focus uses its owner's complete
workspace. Pulled-out tools retain that ownership when placed on its mounts.
Data objects should expose data bindings separately from window capture. Unknown
extension metadata remains ignored; the base package stays schema-valid.
See `lumen-reach/IDENTITY.md`; the reference brief's working titles and lettering
are not shipped identity. Coordination has been sent to the active core agent.

Lumen Reach also reserves open work space per home. Optional
`com.hyprune.lumen-reach.placement` version 1 declares `zones` with stable ID,
world AABB, supported `windowSizes` (1.6×0.9 and 3.2×1.8 m) and clearance.
Mount metadata records 4 m tool approach depth and 16 m primary wall approach.
The package clearance audit sweeps both rectangles ahead of every anchor and
through the reserved volumes against exported visual triangles. A collision-only
or origin-point check would miss screen/frame intersections. Travel corridors
contain no work mounts. Core should expose these volumes for user placement,
then collision-check any requested window pose against actual geometry. Metadata
reserves useful space; it neither permits intersecting placements nor snaps user
windows without a requested operation.
