# SPDX-License-Identifier: MIT
"""gauge-abacus: a value 0-100 as beads on ten rods (RFC-0013 machine, draft).

A dark frame of ten horizontal rods (rod 1 at the bottom) on a rounded plinth.
Each bead is one unit: amber beads pushed to the right (stack `pushed`, filling
rod by rod from the bottom, right to left) count the value; ivory beads resting
on the left (stack `rest`, from the top rod down) make up the hundred, so every
rod always holds ten. A white halo collar on the outboard rail at the right
(a `levels` slide) rides from below rod 1 (0) to above rod 10 (100) and shows
the running average. The plate on the plinth front carries label and display.

    make machines        (Blender on the bake host)
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kit
from kit import Part, GAUGE_TOP

ID = 'gauge-abacus'
HALF, R_PLINTH = .35, .21          # stadium plinth: x +-(HALF + R_PLINTH)
POST_X, POST = .40, .05            # frame posts (centres) and their square section
ROD1, PITCH = .44, .075            # rod 1 height and the rod pitch
ROD10 = ROD1 + 9 * PITCH
BEAD_P = .05                       # bead pitch along a rod
BEAD_X = .325                      # outermost bead centres (+ pushed, - rest); clear gap .20 m
BEAD_R, BEAD_W = .03, .044
RAIL_X = .49                       # outboard rail carrying the halo collar
FRAME_TOP = 1.20


def bead(p, x, z, mat):
    w, r = BEAD_W, BEAD_R
    # a rounded bead along X: chamfer, barrel, chamfer
    p.cyl(mat, (x - w / 2, 0, z), (x - w / 2 + .011, 0, z), r * .55, r2=r, seg=20)
    p.cyl(mat, (x - w / 2 + .011, 0, z), (x + w / 2 - .011, 0, z), r, seg=20, caps=False)
    p.cyl(mat, (x + w / 2 - .011, 0, z), (x + w / 2, 0, z), r, r2=r * .55, seg=20)
    return p


def main():
    kit.reset()
    body = Part('body')
    kit.gauge_stadium(body, HALF, R_PLINTH, seg=14)
    c, up, n = kit.gauge_plate(body, -(R_PLINTH + .025), -(R_PLINTH - .05))
    inner = POST_X - POST / 2
    for sx in (-1, 1):  # posts with a foot
        body.box('plinth', (sx * POST_X, 0, (GAUGE_TOP + FRAME_TOP) / 2), (POST, POST, FRAME_TOP - GAUGE_TOP + .004), bevel=.004)
        body.box('plinth', (sx * POST_X, 0, GAUGE_TOP + .015), (POST + .03, POST + .05, .03), bevel=.006)
    for z, h in ((ROD1 - PITCH * .75, .04), (FRAME_TOP - .025, .04)):  # rails (shallower than the posts)
        body.box('plinth', (0, 0, z), (2 * inner + .01, .04, h), bevel=.003)
    for k in range(10):
        z = ROD1 + k * PITCH
        body.cyl('steel', (-inner - .004, 0, z), (inner + .004, 0, z), .006, seg=8)
        body.box('steel', (-POST_X, -POST / 2 - .0015, z), (.022, .003, .006))   # rod ticks on the left post
    # outboard rail for the halo collar, with top and bottom brackets
    body.cyl('steel', (RAIL_X, 0, GAUGE_TOP - .004), (RAIL_X, 0, FRAME_TOP - .005), .011, seg=12)
    for z in (.35, FRAME_TOP - .015):
        body.box('plinth', ((POST_X + POST / 2 + RAIL_X) / 2, 0, z), (RAIL_X - POST_X - POST / 2 + .01, .022, .02))
    body.cyl('plinth', (RAIL_X, 0, FRAME_TOP - .03), (RAIL_X, 0, FRAME_TOP), .016, seg=12)
    body.finish(smooth_angle=35)
    kit.gauge_labels(c, up, n)
    kit.slot_material('fill', 'gauge', rough=.3)
    kit.MATS['bead-rest'] = dict(color=kit.IVORY, rough=.45)
    bead(Part('bead-pushed', (BEAD_X, 0, ROD1)), BEAD_X, ROD1, 'fill').finish(smooth_angle=50)
    bead(Part('bead-rest', (-BEAD_X, 0, ROD10)), -BEAD_X, ROD10, 'bead-rest').finish(smooth_angle=50)
    z_lo = ROD1 - PITCH / 2
    kit.gauge_halo('average-ring', (RAIL_X, 0, z_lo), .04, .011, seg=32, sseg=10)
    proxy = kit.proxy_boxes([((0, -.012, GAUGE_TOP / 2), (2 * (HALF + R_PLINTH), 2 * R_PLINTH + .03, GAUGE_TOP)),
                             ((.03, 0, (GAUGE_TOP + FRAME_TOP) / 2), (2 * POST_X + .17, .1, FRAME_TOP - GAUGE_TOP))])
    kit.recentre(exclude=proxy)

    drives = [
        {'input': 'value', 'target': 'count:pushed', 'map': {'scale': {'from': [0, 100], 'to': [0, 100]}, 'round': 'floor'}},
        {'input': 'value', 'target': 'count:rest', 'map': {'scale': {'from': [0, 100], 'to': [100, 0]}, 'round': 'ceil'}},
    ]
    slots = {
        'stacks': [{'id': 'pushed', 'node': 'bead-pushed', 'cap': 100, 'rate': 40,
                    'layout': {'grid': [10, 10, 1], 'spacing': [-BEAD_P, PITCH, 0], 'fill': 'xyz'}},
                   {'id': 'rest', 'node': 'bead-rest', 'cap': 100, 'rate': 40,
                    'layout': {'grid': [10, 10, 1], 'spacing': [BEAD_P, -PITCH, 0], 'fill': 'xyz'}}],
        'levels': [kit.level_slot('average-ring', 'average-ring', 'slide', 10 * PITCH)],
    }
    m = kit.gauge_manifest(ID, 'Gauge: abacus', 'An abacus gauge: amber beads pushed right count a value from 0 to 100, a white halo collar its running average.',
                           ['gauge', 'meter', 'percent', 'abacus', 'average'],
                           {'value': 'Amber beads pushed to the right, one per unit, filling rod by rod from the bottom; ivory beads on the left make up the hundred.',
                            'level': 'The pushed beads\' colour: amber when ok, orange on warn, red on fail; grey while the data is stale.'},
                           drives, slots)
    kit.export(kit.out_dir(ID), m, proxy=proxy)


main()
