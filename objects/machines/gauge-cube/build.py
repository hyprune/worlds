# SPDX-License-Identifier: MIT
"""gauge-cube: a value 0-100 as voxels in a 5 x 5 x 4 cube (RFC-0013 machine, draft).

A faint glass case with light edges stands on a tray and stem above a round
plinth. One voxel per unit (stack `voxels`, cap 100) fills it bottom-up, row by
row, so the empty space above reads against the case. A white halo ring around
the case (a `levels` slide over its height) shows the running average. The
plate on the plinth front carries label and display.

    make machines        (Blender on the bake host)
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kit
from kit import Part, GAUGE_TOP

ID = 'gauge-cube'
R_PLINTH = .30
P = .09                    # voxel pitch
V = .082                   # voxel size: a 0.8 cm (9 %) gap
Z0 = .655                  # tray top = bottom of the voxel grid
HC = 4 * P                 # grid height
G = 2.5 * P + .003         # glass case half-width: 7 mm outside the outer voxel faces
GT = Z0 + HC + .008        # glass case top
R_RING, r_RING = .38, .012  # case corners at .325: inner edge .368


def main():
    kit.reset()
    body = Part('body')
    kit.gauge_plinth(body, R_PLINTH)
    c, up, n = kit.gauge_plate(body, -(R_PLINTH + .025), -.16)
    body.cyl('plinth', (0, 0, GAUGE_TOP - .004), (0, 0, Z0 - .04), .06, seg=24)
    body.cyl('plinth', (0, 0, Z0 - .04), (0, 0, Z0 - .028), .06, r2=.13, seg=24)
    body.box('stone', (0, 0, Z0 - .015), (2 * G + .03, 2 * G + .03, .03), bevel=.006)
    # light edges of the case (the glass panels' edges sit inside them)
    e = .01
    for sx in (-1, 1):
        for sy in (-1, 1):
            body.box('steel', (sx * G, sy * G, (Z0 - .002 + GT) / 2), (e, e, GT - Z0 + .002))
            body.box('steel', (sx * G, 0, GT), (e, 2 * G + e, e))
        body.box('steel', (0, sx * G, GT), (2 * G, e * .8, e * .8))
    body.finish(smooth_angle=35)
    case = Part('case')
    for sx in (-1, 1):  # four walls and a lid, single quads facing out
        case.quad('glass', (sx * G, 0, (Z0 + GT) / 2), 2 * G, GT - Z0, rot=(0, 0, sx * math.pi / 2))
        case.quad('glass', (0, sx * G, (Z0 + GT) / 2), 2 * G, GT - Z0, rot=(0, 0, math.pi if sx > 0 else 0))
    case.quad('glass', (0, 0, GT), 2 * G, 2 * G, rot=(-math.pi / 2, 0, 0))
    case.finish()
    kit.gauge_labels(c, up, n)
    kit.slot_material('fill', 'gauge', rough=.3)
    # the first voxel: left, back (+Y in Blender = -Z in glTF), bottom
    first = (-2 * P, 2 * P, Z0 + P / 2)
    Part('voxel', first).box('fill', first, (V, V, V), bevel=.006).finish()
    kit.gauge_halo('average-ring', (0, 0, Z0), R_RING, r_RING, seg=64, sseg=10)
    proxy = kit.proxy_boxes([((0, -.012, GAUGE_TOP / 2), (2 * R_PLINTH, 2 * R_PLINTH + .03, GAUGE_TOP)),
                             ((0, 0, (GAUGE_TOP + GT) / 2), (2 * G + .04, 2 * G + .04, GT - GAUGE_TOP))])
    kit.recentre(exclude=proxy)

    drives = [{'input': 'value', 'target': 'count:voxels', 'map': {'scale': {'from': [0, 100], 'to': [0, 100]}, 'round': 'nearest'}}]
    slots = {
        'stacks': [{'id': 'voxels', 'node': 'voxel', 'cap': 100, 'rate': 40,
                    'layout': {'grid': [5, 4, 5], 'spacing': [P, P, P], 'fill': 'xzy'}}],
        'levels': [kit.level_slot('average-ring', 'average-ring', 'slide', HC)],
    }
    m = kit.gauge_manifest(ID, 'Gauge: voxel cube', 'A voxel cube gauge: one amber voxel per unit fills a 5 x 5 x 4 case from the bottom, a white halo ring shows the running average.',
                           ['gauge', 'meter', 'percent', 'voxels', 'average'],
                           {'value': 'Voxels in the case, one per unit: 25 to a layer, four layers, filling from the bottom.',
                            'level': 'The voxel colour: amber when ok, orange on warn, red on fail; grey while the data is stale.'},
                           drives, slots)
    kit.export(kit.out_dir(ID), m, proxy=proxy)


main()
