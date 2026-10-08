# Lumen Reach render review

The final four-home package is reviewed in core's real nested engine. Twelve
ungraded engine stills share the Cycles cameras and 60° vertical FOV. The owner
art is a composition and mood reference; it is not a camera-matched render.
Run `python3 tools/compare-lumen.py` to produce the local three-column review
at `artifacts/lumen-reach/render-review.html`, with links to full raw captures.

Sun Court keeps a dominant framed workspace facade, foreground canvas work
shelter, a raised armillary terrace, red foliage, wet paving rails and a mountain
watershed panorama. The stairs, west lookout, expansion bridge and rooftop
shelter are usable destinations. The engine is cooler and less softly lit than
Cycles; the concrete texture and large clear screen approach stay legible.

Array Hall keeps a tall ribbed atrium, hanging workspace wall, ceiling ring,
lecterns, banners, server blocks and side balconies. Warm irradiance and floor
and pillar practicals separate it from the court. The engine shows harder
contrast under the balcony, and bright upper concrete, compared with Cycles'
AgX tone map. These differences remain in the delivered captures.

Rime Vault is reached by a real descending service route. It has a broad cold
work room, inset workspace, angled desks, diagnostics, pipes, grating, maintenance
platform and sealed continuation. Amber/red practicals and original instrument
artwork carry the dark composition. Its engine metal and shadows are darker
than the Cycles reference. Generated alpha plume cards replace the earlier
opaque steam fallback; the plumes are static, not simulated vapor.

Signal Rise adds a snow basin with blue night, armor-framed wall workspace,
angled terminal bench and side menu, door diagnostics, antenna dish, masts,
cable gantry, amber landing ring and red warnings. Stairs and ramps reach the
dish, operator room and gantry. An opaque rock ridge isolates its night vista
from the daylight homes. The original panorama fades into the opaque zenith
closure to avoid a stretched star row; seams can become visible from unusual
high viewpoints. The dish and snowy terrain remain deliberately stylized
procedural geometry rather than the reference's dense painted detailing.

Every primary workspace and tool mount has a physical frame and stable area/slot
ownership. The audit sweeps 1.6×0.9m, 3.2×1.8m and the full anchor rectangle
continuously against exported visual triangles, with 4m tool and 16m primary
approaches. Four reserved volumes support free placement. The full engine route
audit traverses every graph edge both ways and every alternate stair flight.
A slab lip found by that audit was replaced by a continuous roof landing.

All masters are original imagegen assets with prompts and hashes. Periodic PBR
derivatives, trim bands and UI are generated locally; geometry, UV1 packing,
Cycles irradiance and matched renders run only on the remote bake host. Static
screen artwork is a placeholder; the final tour uses actual captured applications
and the shell's real HUD. No capture is graded, retouched or composited to conceal
engine behavior. Thumbnail contact sheets are only review aids.

Core M2 provides alpha and world-wide atmosphere/static environment reflections.
Area moods here come from distinct baked light and opaque vistas. The package
stays valid format 0.2 through optional coordinated extensions. Per-area dynamic
weather, animated vapor and view-dependent reflections are not implemented.

Exact package, GPU and engine evidence is in `reports/package-check.json`,
`reports/milestone-04-nested-report.json`, `reports/tour-nested-report.json` and
`reports/release.json`. GPU texture estimates and kernel process residency are
separate measurements; the latter includes the nested compositor, renderer and
imported application buffers. The tour's exact scene/plugin hashes are recorded.

The reviewed delivery runs 83.13 seconds at 1920×1080/30 fps. Live application
content is visible on all four primary walls; four real terminals are placed
on owned mounts, and the opening includes actual terminal typing. The full
recording contact sheet and selected full-resolution frames were inspected.
Core d20d7fe corrects the incomplete-mipmap client sampling found during this
review. The final nested process peak is 786.02 MiB across 97 kernel samples;
the 55.13 MiB package has a conservative 272.45 MiB world GPU estimate.
See reports/final-report.md for the local gallery and installable archive.
