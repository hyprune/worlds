# SPDX-License-Identifier: MIT
"""gauge-tube: a liquid column in a glass tube (RFC-0013 machine, draft).

A glass tube in a dark collar and cap on a round plinth. The amber liquid
column (a `levels` fill with a sloshing surface) shows the value 0-100; a white
halo ring outside the glass (a `levels` slide) shows its running average. The
fill colour follows the level (ok, warn, fail); the plate on the plinth front
carries the label and the display text.

    make machines        (Blender on the bake host)
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kit
from kit import Part, GAUGE_TOP, empty

ID = 'gauge-tube'
R_PLINTH = .26
R_GLASS, R_INNER = .11, .104       # glass wall 6 mm
R_LIQUID = .100                    # 4 mm inside the inner wall
COLLAR_TOP = .36
Z0, Z1 = .365, 1.28                # liquid column: bottom (node origin) and full top
CAP_Z = 1.29
R_RING, r_RING = .145, .011        # ring inner edge .134: 2.4 cm outside the glass


def main():
    kit.reset()
    body = Part('body')
    kit.gauge_plinth(body, R_PLINTH)
    c, up, n = kit.gauge_plate(body, -(R_PLINTH + .025), -.12)
    # collar and cap hold the glass; three steel stays between them (inside the ring)
    body.cyl('plinth', (0, 0, GAUGE_TOP - .004), (0, 0, COLLAR_TOP - .01), .128, seg=48)
    body.cyl('plinth', (0, 0, COLLAR_TOP - .01), (0, 0, COLLAR_TOP), .128, r2=.12, seg=48)
    body.cyl('plinth', (0, 0, CAP_Z), (0, 0, CAP_Z + .04), .128, seg=48)
    body.cyl('plinth', (0, 0, CAP_Z + .04), (0, 0, CAP_Z + .05), .128, r2=.112, seg=48)
    body.cyl('steel', (0, 0, CAP_Z + .045), (0, 0, CAP_Z + .075), .03, r2=.022, seg=20)
    for a in (90, 210, 330):
        x, y = .118 * math.cos(math.radians(a)), .118 * math.sin(math.radians(a))
        body.cyl('steel', (x, y, COLLAR_TOP - .005), (x, y, CAP_Z + .005), .005, seg=8)
    body.finish(smooth_angle=40)
    glass = Part('glass')
    glass.lathe('glass', [(R_INNER, .33), (R_GLASS, .33), (R_GLASS, CAP_Z + .012), (R_INNER, CAP_Z + .012), (R_INNER, .33)], seg=48)
    glass.finish(smooth_angle=60)
    kit.gauge_labels(c, up, n)
    kit.slot_material('fill', 'gauge', rough=.3)
    # liquid: an empty node at the column bottom (the fill's origin; the optimiser's quantisation
    # moves mesh node origins, never an empty's) holding the column, bottom cap + side and no
    # top cap (the surface, a sibling, is the cap)
    liquid = empty('liquid', (0, 0, Z0))
    column = Part('liquid-column', (0, 0, Z0))
    column.lathe('fill', [(0, Z0), (R_LIQUID, Z0), (R_LIQUID, Z1)], seg=40)
    column = column.finish(smooth_angle=60)
    column.parent = liquid; column.location = (0, 0, 0)
    Part('liquid-surface', (0, 0, Z1)).disc('fill', (0, 0, Z1), R_LIQUID, seg=40).finish()
    kit.gauge_halo('average-ring', (0, 0, Z0), R_RING, r_RING)
    proxy = kit.proxy_boxes([((0, -.012, GAUGE_TOP / 2), (2 * R_PLINTH, 2 * R_PLINTH + .03, GAUGE_TOP)),
                             ((0, 0, (GAUGE_TOP + CAP_Z + .075) / 2), (.32, .32, CAP_Z + .075 - GAUGE_TOP))])
    kit.recentre(exclude=proxy)

    L = Z1 - Z0
    drives = [{'input': 'value', 'target': 'level:liquid', 'map': {'scale': {'from': [0, 100], 'to': [0, 1]}}}]
    slots = {'levels': [kit.level_slot('liquid', 'liquid', 'fill', L, surface='liquid-surface', settle='spring'),
                        kit.level_slot('average-ring', 'average-ring', 'slide', L)]}
    m = kit.gauge_manifest(ID, 'Gauge: tube', 'A glass tube gauge: an amber liquid column shows a value from 0 to 100, a white halo ring its running average.',
                           ['gauge', 'meter', 'percent', 'level', 'average'],
                           {'value': 'The liquid height, 0 (empty) to 100 (full); the liquid sloshes as it settles.',
                            'level': 'The liquid colour: amber when ok, orange on warn, red on fail; grey while the data is stale.'},
                           drives, slots)
    kit.export(kit.out_dir(ID), m, proxy=proxy)


main()
