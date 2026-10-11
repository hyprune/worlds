# SPDX-License-Identifier: MIT
"""queue-stack: a queue as crates on a shelf rack (RFC-0013 machine, draft).

A timber rack with four dark metal shelves. Crates fill it back to front and
bottom to top, one crate per ten queued items (a stack slot, cap 48). A counter
header shows the depth; a lantern and a stripe show the oldest-item level, and
a red canvas flag rises on warn and fail so the level reads without colour.

    make machines        (Blender on the bake host)
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kit
from kit import Part, empty, lamp

ID = 'queue-stack'
XS = [-.69, -.23, .23, .69]     # crate columns
YS = [.46, 0, -.46]             # rows, back to front (front is -Y)
SHELF = [.30, .80, 1.30, 1.80]  # shelf centres (top = +.02)
C = .40                         # crate size


def crate(p, c):
    p.box('timber', c, (C, C, C), bevel=.018, grain='z')
    for dz in (-C * .32, C * .32):
        p.box('metal-black', (c[0], c[1], c[2] + dz), (C + .012, C + .012, .03))
    p.box('ivory', (c[0], c[1] - C / 2 - .007, c[2]), (.14, .006, .07))


def main():
    kit.reset()
    body = Part('body')
    body.box('stone', (0, 0, .09), (2.5, 1.8, .18), bevel=.03)
    for sx in (-1, 1):
        for sy in (-1, 1):
            body.box('timber', (sx * 1.05, sy * .72, 1.24), (.1, .1, 2.12))
        for z in (.55, 1.05, 1.55, 2.05):   # side slats
            body.box('timber', (sx * 1.05, 0, z), (.05, 1.44, .07), grain='y')
    for z in SHELF:
        body.box('timber-dark', (0, 0, z), (2.0, 1.44, .04), bevel=.01, grain='x')
        body.box('metal-black', (0, -.725, z - .03), (2.0, .03, .06))
    for sy in (-1, 1):  # top beams
        body.box('timber', (0, sy * .72, 2.28), (2.2, .1, .1), grain='x')
    # back X-brace
    for s in (-1, 1):
        body.box('metal-black', (0, .735, 1.26), (2.3, .02, .035), rot=(0, s * math.atan2(1.9, 2.0), 0))
    # counter header
    body.box('metal', (0, -.1, 2.55), (1.3, .26, .44), bevel=.035, grain='x')
    body.box('brass', (0, -.1, 2.785), (1.34, .3, .03))
    for sx in (-1, 1):
        body.box('metal-black', (sx * .55, -.1, 2.31), (.06, .06, .1))
    body.box('metal-black', (.82, -.1, 2.55), (.24, .2, .14), bevel=.02)        # lantern bracket
    body.cyl('brass', (.82, -.1, 2.62), (.82, -.1, 2.645), .1, seg=12)
    body.cyl('metal-black', (.82, -.1, 2.845), (.82, -.1, 2.88), .1, seg=12)
    body.cyl('brass', (.82, -.1, 2.88), (.82, -.1, 2.92), .02, seg=8)
    # flag mast (the flag itself is a toggle)
    body.box('metal-black', (-1.05, -.72, 2.62), (.035, .035, .6))
    body.box('strip-cyan', (0, -.905, .17), (2.2, .01, .02))
    body.box('panel', (0, -.902, .09), (1.3, .006, .11))                         # name plate backing
    body.finish()
    kit.MATS['label-count'] = dict(kit.MATS['panel']); kit.MATS['label-name'] = dict(kit.MATS['panel'])
    Part('label-count', (0, -.232, 2.55)).quad('label-count', (0, -.232, 2.55), 1.06, .3).finish()
    Part('label-name', (0, -.906, .09)).quad('label-name', (0, -.906, .09), 1.2, .09).finish()
    kit.slot_material('level-lamp', 'level'); kit.slot_material('level-stripe', 'level')
    lamp('level-lamp', 'level', (.82, -.1, 2.645), r=.085, depth=.2, axis='z', seg=12, dome=False)
    Part('level-stripe', (0, -.74, 2.28)).box('level-stripe', (0, -.775, 2.28), (2.0, .012, .05)).finish()
    flag = Part('alarm-flag', (-1.05, -.72, 2.82))
    flag.box('canvas-red', (-.87, -.72, 2.8), (.34, .012, .22)); flag.finish()
    cr = Part('crate', (XS[0], YS[0], SHELF[0] + .02 + C / 2)); crate(cr, (XS[0], YS[0], SHELF[0] + .02 + C / 2)); cr.finish()
    proxy = kit.proxy_boxes([((0, 0, .09), (2.5, 1.8, .18)), ((0, 0, 1.4), (2.2, 1.55, 2.8))])
    kit.recentre(exclude=proxy)

    inputs = [
        {'id': 'depth', 'type': 'int', 'min': 0, 'max': 500, 'default': 0, 'label': 'Queue depth',
         'explain': 'Crates on the rack, one per ten queued items (48 crates = 480+); the header shows the exact number.'},
        {'id': 'level', 'type': 'enum', 'values': ['ok', 'warn', 'fail'], 'default': 'ok', 'label': 'Oldest item',
         'explain': 'How long the oldest item has waited: the lantern and stripe turn amber, then red, and the red flag rises.'},
        {'id': 'name', 'type': 'text', 'maxLength': 24, 'label': 'Queue name', 'explain': 'The plate on the plinth.'},
    ]
    drives = [
        {'input': 'depth', 'target': 'count:crates', 'map': {'scale': {'from': [0, 480], 'to': [0, 48]}, 'clamp': True, 'round': 'ceil'}},
        {'input': 'depth', 'target': 'label:label-count', 'map': {'format': {'decimals': 0, 'compact': True}}},
        {'input': 'level', 'target': 'state:level'},
        {'input': 'level', 'target': 'visible:alarm-flag', 'map': {'cases': [{'equals': 'ok', 'to': False}], 'else': True}},
        {'input': 'name', 'target': 'label:label-name'},
    ]
    m = kit.base_manifest(ID, 'Queue stack', 'A queue as crates on a shelf rack: one crate per ten items, a depth counter, and a lantern, stripe and flag for the oldest item.',
                          ['queue', 'backlog', 'jobs', 'crates'])
    m['traits'] = {
        'collidable': {'node': 'proxy'},
        'movable': {'surfaces': ['floor'], 'upright': True},
        'machine': {'primary': 'level', 'inputs': inputs, 'drives': drives,
                    'recipes': [{'name': 'Queue stats JSON', 'fields': {
                        'depth': '/depth', 'level': '/oldest_age_seconds', 'name': '/name'},
                        'maps': {'level': {'thresholds': [{'below': 300, 'to': 'ok'}, {'below': 1800, 'to': 'warn'}], 'else': 'fail'}}}]},
    }
    m['slots'] = {
        'states': [kit.states_slot('level', ['level-lamp', 'level-stripe'])],
        'labels': [{'id': 'label-count', 'pose': {'pose@': 'label-count'}, 'size': [1.06, .3], 'maxChars': 12, 'font': 'mono'},
                   {'id': 'label-name', 'pose': {'pose@': 'label-name'}, 'size': [1.2, .09], 'maxChars': 24, 'font': 'mono'}],
        'stacks': [{'id': 'crates', 'node': 'crate', 'cap': 48, 'layout': {'grid': [4, 4, 3], 'spacing': [.46, .5, .46], 'fill': 'xzy'}}],
        'toggles': [{'id': 'alarm-flag', 'nodes': ['alarm-flag']}],
    }
    kit.export(kit.out_dir(ID), m, proxy=proxy)


main()
