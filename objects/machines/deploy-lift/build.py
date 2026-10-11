# SPDX-License-Identifier: MIT
"""deploy-lift: a deploy as a platform lift (RFC-0013 machine, draft).

A four-column timber shaft on a stone base. The platform carries the release
crate up past four stops (queued, building, rolling, live) to the live deck at
the top; a lamp at each stop shows the phase, a gate bar closes the deck until
the release is live, and a beacon on the mast turns while it rolls out.

The platform is a `bob` animation made value-driven by `positions` (range
0.75-1.25 = bottom to top), so a plain 0.8 world shows it riding up and down.

    make machines        (Blender on the bake host)
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kit
from kit import Part, empty, lamp, spin

ID = 'deploy-lift'
COL = 1.0                       # column centres at (+-COL, +-COL)
BOTTOM, TOP = .32, 3.2          # platform top surface at the lowest stop and at the deck
MID = (BOTTOM + TOP) / 2
STOPS = [BOTTOM, BOTTOM + (TOP - BOTTOM) / 3, BOTTOM + 2 * (TOP - BOTTOM) / 3, TOP]


def main():
    kit.reset()
    body = Part('body')
    body.box('stone', (0, 0, .1), (2.7, 2.7, .2), bevel=.03)
    body.box('panel', (0, 0, .205), (1.8, 1.8, .01))                            # pit
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * COL, sy * COL
            body.box('timber', (x, y, 2.05), (.2, .2, 3.7), grain='z')
            body.box('metal-black', (x - sx * .11, y - sy * .11, 2.0), (.04, .04, 3.6))   # guide rail
            body.box('metal', (x, y, .28), (.26, .26, .16), bevel=.02)                   # foot
    # live deck: a frame of stone slabs around the shaft, ivory railing on three sides
    for c, s in [((0, 1.12, TOP - .06), (2.7, .46, .12)), ((-1.12, 0, TOP - .06), (.46, 1.78, .12)), ((1.12, 0, TOP - .06), (.46, 1.78, .12)),
                 ((0, -1.12, TOP - .06), (2.7, .46, .12))]:
        body.box('stone', c, s, bevel=.015)
    for c, s in [((0, 1.33, TOP + .5), (2.7, .04, .04)), ((-1.33, 0, TOP + .5), (.04, 2.7, .04)), ((1.33, 0, TOP + .5), (.04, 2.7, .04)),
                 ((-.9, -1.33, TOP + .5), (.9, .04, .04)), ((.9, -1.33, TOP + .5), (.9, .04, .04))]:
        body.box('ivory', c, s)
    for x, y in [(-1.33, -1.33), (1.33, -1.33), (-1.33, 1.33), (1.33, 1.33), (-.45, -1.33), (.45, -1.33), (0, 1.33), (-1.33, 0), (1.33, 0)]:
        body.box('ivory', (x, y, TOP + .25), (.04, .04, .5))
    body.box('strip-mint', (0, -1.352, TOP - .06), (2.6, .01, .03))
    # top frame, sheave and the header for the environment label
    for sy in (-1, 1):
        body.box('timber', (0, sy * COL, 3.95), (2.2, .16, .16), grain='x')
        body.box('timber', (sy * COL, 0, 3.95), (.16, 2.2, .16), grain='y')
    body.cyl('brass', (-.12, 0, 3.8), (.12, 0, 3.8), .2, seg=16)
    body.box('metal-black', (0, 0, 3.92), (.3, .08, .1))
    body.box('metal', (0, -COL - .1, 3.95), (1.6, .06, .34), bevel=.02, grain='x')
    # stop ticks on the front-left column, lamp brackets
    for k, z in enumerate(STOPS):
        body.box('metal-black', (-COL, -COL - .13, z + .2), (.2, .06, .2), bevel=.012)
        for j in range(k + 1):
            body.box('ivory', (-COL, -COL - .101, z + .02 + j * .035), (.08, .006, .018))
    # beacon mast on the back-right column
    body.box('metal-black', (COL, COL, 4.35), (.06, .06, .65))
    body.cyl('brass', (COL, COL, 4.66), (COL, COL, 4.69), .13, seg=14)
    body.cyl('metal-black', (COL, COL, 4.96), (COL, COL, 5.0), .13, seg=14)
    body.box('canvas-red', (COL - .2, COL, 4.4), (.3, .012, .2))
    body.finish()

    lamps = [lamp(f'phase-lamp-{k + 1}', 'phase', (-COL, -COL - .16, z + .2), r=.085, depth=.07, axis='-y', seg=14) for k, z in enumerate(STOPS)]
    kit.slot_material('beacon', 'beacon')
    bc = Part('beacon', (COL, COL, 4.69))
    bc.cyl('beacon', (COL, COL, 4.69), (COL, COL, 4.96), .11, seg=14)
    bc.box('metal-black', (COL, COL, 4.825), (.2, .03, .25))                    # reflector fin: the turn reads
    beacon = bc.finish()
    # platform at mid travel (the bob rest pose)
    pl = Part('platform', (0, 0, MID))
    pl.box('metal', (0, 0, MID - .06), (1.74, 1.74, .1), bevel=.015, grain='x')
    for k in range(6):
        pl.box('timber', (-.72 + k * .288, 0, MID - .005), (.27, 1.66, .02), grain='y')
    for sx in (-1, 1):
        for sy in (-1, 1):
            pl.box('metal-black', (sx * .86, sy * .86, MID - .06), (.08, .08, .16))
    pl.box('strip-amber', (0, -.875, MID - .06), (1.6, .01, .03))
    pl.box('timber', (0, .1, MID + .3), (.6, .6, .6), bevel=.02)                    # the release crate
    pl.box('metal-black', (0, .1, MID + .45), (.62, .62, .04))
    pl.box('strip-cyan', (0, .1, MID + .2), (.615, .615, .04))
    pl.box('ivory', (0, -.205, MID + .3), (.2, .006, .1))
    platform = pl.finish()
    kit.MATS['label-env'] = dict(kit.MATS['panel'])
    Part('label-env', (0, -COL - .132, 3.95)).quad('label-env', (0, -COL - .132, 3.95), 1.44, .26).finish()
    Part('gate', (0, -1.33, TOP + .3)).box('strip-amber', (0, -1.33, TOP + .3), (.86, .05, .05)).finish()
    empty('burst-fx', (0, 0, TOP + 1.0))
    proxy = kit.proxy_boxes([((0, 0, .1), (2.7, 2.7, .2)), ((0, 0, 2.0), (2.25, 2.25, 4.0))])
    kit.recentre(exclude=proxy)

    phases = ['idle', 'queued', 'building', 'rolling', 'live', 'failed']

    def lamp_map(k):  # stop k (1 queued .. 4 live)
        cases = [{'equals': 'idle', 'to': 'off'}, {'equals': 'failed', 'to': 'fail'}]
        cases += [{'equals': p, 'to': 'active' if j == k else ('done' if j > k else 'off')} for j, p in enumerate(phases[1:5], 1)]
        return {'cases': cases, 'else': 'off'}

    inputs = [
        {'id': 'status', 'type': 'enum', 'values': phases, 'default': 'idle', 'label': 'Deploy phase',
         'explain': 'The lamp at each stop: queued, building, rolling, live. Live opens the deck gate; failed turns every lamp and the beacon red.'},
        {'id': 'progress', 'type': 'number', 'min': 0, 'max': 1, 'default': 0, 'label': 'Progress',
         'explain': 'The platform height: the release crate rides from the base (0) to the live deck (1).'},
        {'id': 'environment', 'type': 'text', 'maxLength': 20, 'label': 'Environment', 'explain': 'The header above the shaft.'},
        {'id': 'finished', 'type': 'event', 'label': 'Deploy finished', 'explain': 'A burst over the live deck.'},
    ]
    drives = [{'input': 'progress', 'target': 'position:platform'}]
    drives += [{'input': 'status', 'target': f'state:phase-lamp-{k}', 'map': lamp_map(k)} for k in range(1, 5)]
    drives += [
        {'input': 'status', 'target': 'state:beacon', 'map': {'cases': [{'in': ['queued', 'building', 'rolling'], 'to': 'active'},
                                                                        {'equals': 'live', 'to': 'live'}, {'equals': 'failed', 'to': 'fail'}], 'else': 'off'}},
        {'input': 'status', 'target': 'animation:beacon', 'map': {'cases': [{'in': ['building', 'rolling'], 'to': 1}, {'equals': 'failed', 'to': 2}], 'else': 0}},
        {'input': 'status', 'target': 'visible:gate', 'map': {'cases': [{'equals': 'live', 'to': False}], 'else': True}},
        {'input': 'finished', 'target': 'effect:burst-fx'},
        {'input': 'environment', 'target': 'label:label-env'},
    ]
    amp = round((TOP - BOTTOM) / 2, 4)
    m = kit.base_manifest(ID, 'Deploy lift', 'A deploy as a platform lift: the release crate rises past queued, building and rolling stops to the live deck.',
                          ['deploy', 'release', 'environment', 'lift'])
    m['traits'] = {
        'decorative': {'animations': [{'node': 'platform', 'type': 'bob', 'axis': [0, 1, 0], 'amplitude': amp, 'period': 16},
                                      spin(beacon, (0, 0, 1), 1.5)]},
        'collidable': {'node': 'proxy'},
        'movable': {'surfaces': ['floor'], 'upright': True},
        'machine': {'primary': 'status', 'inputs': inputs, 'drives': drives,
                    'positions': [{'node': 'platform', 'range': [.75, 1.25]}],
                    'recipes': [{'name': 'Deployment JSON', 'fields': {
                        'status': '/deployment/status', 'progress': '/deployment/progress', 'environment': '/deployment/environment',
                        'finished': '/deployment/finished_count'}}]},
    }
    m['slots'] = {
        'states': [kit.states_slot(f'phase-lamp-{k}') for k in range(1, 5)] + [kit.states_slot('beacon')],
        'labels': [{'id': 'label-env', 'pose': {'pose@': 'label-env'}, 'size': [1.44, .26], 'maxChars': 20, 'font': 'mono'}],
        'effects': [{'id': 'burst-fx', 'pose': {'pose@': 'burst-fx'}, 'kind': 'burst', 'colour': list(kit.MINT), 'durationMs': 1800}],
        'toggles': [{'id': 'gate', 'nodes': ['gate']}],
    }
    kit.export(kit.out_dir(ID), m, proxy=proxy)


main()
