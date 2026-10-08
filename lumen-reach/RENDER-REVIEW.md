# Lumen Reach 0.5.0 render review

The owner’s four concepts establish composition, material density and mood.
The delivery keeps the original twelve inspection poses and adds four close
views for the entrance fixtures, hall vista, vault services and reflector.
Final raw engine captures are in `artifacts/lumen-reach/v2-4k/`, taken with
core’s isolated nested harness under the shared lock at the effective Medium
preset. Output is native 3840×2160; internal dynamic render scale is recorded
in the report. The matched Cycles cameras use the same pose and 60° vertical
FOV. The concept artwork itself is not camera matched.

Run `python3 tools/compare-lumen.py` for
`artifacts/lumen-reach/render-review.html`: concept, Cycles and engine side by
side, with raw images linked. The engine captures have no grading, retouching
or compositing. Comparison thumbnails only resize images for review.

**Sun Court.** The facade and red canvas remain the focal structure, with a
clear approach and working shelters at its edges. Tiled concrete, maintenance
plates, drains, vents, pipe clamps, canopy hems, practical fixtures, instrument
cases and additional red foliage break up the former blank surfaces. Entry
lights now have structural jambs and seated backplates, inspected in a close
engine view. Pier/lintel and vestibule-floor overlaps are removed. Mountains,
waterfall artwork and bridges combine with physical rock and spire layers.
The engine’s daylight is cooler and harder than the softly painted concept.

**Array Hall.** Warm floor and column practicals frame the suspended workspace.
Layered ribs, metal collars, cabinet drawers and indicators populate the tall
bays; balcony ribs, banners and the supported ring give the upper volume more
structure. The former blank rear mass is sculpted rock with physical watershed
spires. Large walking and workspace volumes stay open. The engine retains
stronger contrast under balconies than the concept and Cycles’ AgX render.

**Rime Vault.** Frosted coolant trunks, coupling flanges, suspension brackets,
cable bundles, trays, crossbeams, riveted panels, ice pendants and service
cabinets now read across the room. Metal floor with local grating and hazard
panels replaces repetitive all-over striping. Cold fill reveals the pipes;
amber grazing light separates the work stations and sealed continuation.
This is a serviced cold room rather than an empty dark box. Steam cards remain
static and sparse, with no simulated vapor or dynamic accumulation.

**Signal Rise.** The reflector is a curved bowl with radial and hoop structure,
a feed horn, three supports and trunnions. Near rock crags, snowbanks, frosted
ledges, icicles, crates and gantry cables add depth around the fortress and
landing ring. Blue night and amber/red practicals retain the reference mood.
The overlapping fortress pier/crown faces are removed. Terrain and metalwork
remain visibly stylized; the painted reference has finer irregular detail.
Unusual high viewpoints can still reveal the opaque night enclosure.

All lit physical materials have original generated texture masters, periodic
PBR derivatives and/or trim atlas coverage. Exact prompts and source hashes
are in `materials/generation.json`; the new rock master is part of the same
provenance chain. Explicit exported material factors preserve red cloth and
foliage and dark housings. Signs and cases use the Reach mark and vocabulary.
The package adds no imported game assets or reference lettering.

Clearances take priority over filling the work approaches. Automated checks
cover 24 mounts, four reserved volumes, support and capsule clearance; the
engine checks every directed route and alternate stair flight. The final tour
uses real mounted application content, placed terminals, actual keyboard input
and the shell HUD. Recording and encoding occur outside the gallery before the
finished files are moved in; its autocommit process is untouched.

The renderer supplies global atmosphere and static environment reflections.
Distinct area moods come from baked lighting and opaque vista separation.
Lighting, steam and distant artwork are static. These limits and the remaining
stylization are visible in the raw delivery, not concealed by postprocessing.

See `reports/final-report.md` for before/after budgets, measured 4K observations,
validation results, archive and gallery paths. Exact engine binaries, core
working-tree hashes and timing samples are in `reports/polish-v2/`; the core
was being developed concurrently. World GPU estimates and nested process
residency measure different scopes and are reported separately.
