# Lumen Reach changelog

Measured figures, gates and archive hashes for each release are in the
release records (`reports/release*.json`).

## 0.11.0

Residents (world format 0.9). Four starter-kit residents, one per area in its
colour (Desert in Sun Court, Crimson in Array Hall, Ember in Rime Vault, Blue
in Signal Rise), each walking an authored route with a vista, a spot beside a
tool screen and a bench where it sits. Each says a few lines about its area;
Crimson marks the way to Rime Vault and Ember walks the player to Signal Rise,
also from its seat. The characters ship in the package (`characters/<id>/`, byte-identical to
the published `com.hyprune.starter@0.1.1`: UASTC base colour).

- **Benches.** Both Sun Court seats are 0.40 m benches (they were 0.61 m,
  higher than the residents' sit fits). New 0.40 m benches: Array Hall between
  the second and third desks (facing the hanging wall), Rime Vault's south edge
  (facing the console) and Signal Rise's south field (facing the map terminal
  and the fortress). Seat anchors sit mid-half and close to the seat, so the
  seated pelvis lands well inside the seat; the seat collision stops short of
  the front so the sit approach stays walkable.
- **keepClear** volumes in front of the four primary walls and at the doors
  between areas.
- Source in `residents.json`; checks in `tools/check-residents.py` and the
  nested `tools/check-residents-session.py`.

## 0.10.3

The Sun Court plaza paving is plain: the bent pair of inset route rails (with
their amber edge) and the seven metal expansion seams across the plaza are
gone. From eye height they read as stray black lines across the floor. The
paving under them was continuous, so nothing else changes; the hall, vault
and terrace inset rails stay.

## 0.10.2

Array Hall's enclosure walls are detailed in the hall's own vocabulary: high
clerestory glazing on the south and east walls (glass with collision, metal
mullions every 2 m, head and sill rails, an amber sill light) between a solid
lower wall and a header; secondary ribs, collars and service lintels on the
south wall; a recessed screen bay facing the 16 m approach; no outer seam at
16.5 m. The enclosure keeps 0 sky leaks.

## 0.10.1

Array Hall is an enclosed hall, and no walkable edge near a route drops out
of the world.

- **Array Hall enclosure.** The hall's sides were open from 0.4.0 onward: the
  west wall covered only y 42-56, the east wall stopped 1.4 m below the roof
  beams, and the south side above the vestibule had no wall at all. Open sky
  showed between the structures from the hall floor. The hall now has walls on
  the east, south and west sides, running up into the roof beams, with
  openings only where routes pass:
  - the vestibule;
  - an annex door at grade;
  - the 4 m balcony portal;
  - a 5 m service passage under a crown;
  - the 16 m rooftop walkway's west and south doors.

  The north panorama stays open as the designed vista. The south wall's outer
  face carries facade ribs and seams toward the Sun Court rooftop, and the
  annex banner moves 0.3 m west, clear of the annex wall. Roof margin slabs close
  the strips between the edge beams and the skylight, and 7.9 m panes close
  the slits beside the mullions.
- **Enclosure gate.** `enclosures.json` declares the hall, and the
  `check-sky.py` enclosure test accepts per-room door `openings`. On the 0.9.2
  package the test reports 878 sky leaks from the hall; on 0.10.1 it reports
  none.
- **Walk-off fixes.** In nested walk probes on 0.9.2, a walker fell out of the
  world at the hall's south-west corner. That is where the hall's south wall
  now stands. Walkers also fell out at these edges, which now have guards:
  - the annex's south edge (parapet);
  - beside the service threshold (a floor and end wall for the unfloored nook,
    and a parapet on the threshold's south edge);
  - the 4 m balconies' north edge (rail);
  - the Sun Court 4 m landing's north edge, either side of the roof ramp and
    its stair (rails);
  - beside the Signal Rise ascent shell (a snow verge over the 0.75 m slot).

  A 5 m/s jump reaches 1.27 m, so each void edge also has a 2.5 m
  collision-only guard behind its parapet or rail (walk-and-jump probes had
  cleared them).
- **Floating pieces.**
  - The old light-ring hangers touched nothing and are removed (the radial
    suspensions carry the ring).
  - The rib above the roof bridge now rests on the walkway door head.
  - Ribs over the annex door and the service passage start at the opening
    head.
  - The archive rack drawers now sit on the racks. They had been 5 cm proud,
    and two sets had no rack behind them.
  - The Sun Court facade service drains reach the paving (they hung 0.25 m
    up).
