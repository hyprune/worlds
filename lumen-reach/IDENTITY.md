# Lumen Reach

A working settlement on the high terraces of a mountain watershed. Its people
maintain the paths, instruments and connections that let distant places work
together. The world is lived in: cases are stacked beside desks, canvas shelters
shade repairs, warm lamps guide travelers, and sealed passages invite expansion.

## Four workspace homes

| Area ID | Signage | Slot | Theme and purpose |
|---|---|---|---|
| sun-court | SUN COURT / 01 | 01 | Warm daylight, pale concrete, wet stone, red foliage; arrival and field work |
| array-hall | ARRAY HALL / 02 | 02 | Golden interior, vertical ribs, servers, amber floor strips; making and testing |
| rime-vault | RIME VAULT / 03 | 03 | Frosted metal, service tunnels, red-amber instruments; maintenance and archives |
| signal-rise | SIGNAL RISE / 04 | 04 | Snow, blue night, concrete terraces, antenna silhouettes; communications |

The settlement's landmark is the **Watershed Spire**. Far bridges cross the
**Upper Cascade**. The closed lower passage is labeled **CONTINUATION / SEALED**.
Screen placeholders say WORKSPACE HOME, CONNECTIONS, TASKS, ENVIRONMENTS,
BUILD QUEUE, ROUTES, ARCHIVES, POWER, COOLANT, LINK HEALTH, and SIGNAL MAP.
These are static authored placeholders, never claims about live telemetry.

## The Reach mark

Three staggered horizontal bars, with one vertical rising stem at their right
ends: a stepped horizon and a path upward. No enclosed triangle, diamond,
faction crest or borrowed icon. Smaller signs use parallel ticks and numbered
route lines. Ivory lettering, oxidized red canvas, amber practicals and blue
instrument traces recur across the settlement.

## Expansion and identities

One area owns one workspace slot, one primary mounted workspace and its tool
mounts. Anchor IDs are `<area-id>-slot-<two-digit-slot>-<mount-kind>-<ordinal>`.
Example: `sun-court-slot-01-facade-wall-01`. Additional homes instantiate the
same thematic kit using new area IDs and slot numbers, never renaming old anchors.
Data objects use the same IDs and owner slot but remain separate from planar
window anchors. Core/user state supplies actual workspace IDs and applications;
this immutable package declares slot membership, not compositor configuration.

## Asset identity

All geometry is authored procedurally in Blender Python. All material masters
are generated for this settlement, with recorded prompts/hashes and seam healing.
The owner's reference compositions inform architecture, props and illumination;
reference lettering and marks are excluded. No imported game models, textures,
names, logos, fonts or audio are used.

## Theme kits

The home ID and workspace slot are independent of the theme index in
`set_area`. A future home chooses a new `area_id`, `title` and `slot` while
retaining one of the four theme indices. `owner` and `anchor_id` derive all
mount and data identities from that home. Duplicate home IDs or slots fail
at authoring time. The existing four identities remain stable.

Sun Court's kit is canvas shelters, pale facade/terrace blocks, operator benches,
field rig rails, planters and armillary instruments. Array Hall's kit is tall
ribbed columns, a suspended light ring/wall, lecterns, framed banners, server
blocks and balcony flights. Rime Vault's kit is inset consoles, frosted service
panels, ceiling pipes, maintenance benches and amber/red route practicals.
Signal Rise's kit is segmented armor, warning grilles, angled terminal benches,
snow-capped cases, dishes, masts and cable gantries. Shared meter-based frame,
stair, ramp, canopy, case and instrument primitives give each kit consistent
proportions. New connected areas still require their own authored floor layout,
lighting bake, routes, work clearances and engine review.
