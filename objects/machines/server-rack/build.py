# SPDX-License-Identifier: MIT
"""server-rack: hosts as a rack of eight units (RFC-0013 machine, draft).

A dark metal cabinet with timber cheeks on a stone plinth. Each unit has a fan
behind a brass ring (its speed follows load) and a light bar for its health
(off, ok, warn, fail). A name plate sits above the units; the back carries
vent grilles so the rack holds up from behind.

    make machines        (Blender on the bake host)
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kit
from kit import Part, spin

ID = 'server-rack'
UNITS = 8
Z0, PITCH = .36, .2             # first unit centre, unit pitch
FRONT = -.5                     # cabinet front face (Y)
FAN_X, LIGHT_X = -.24, .2


def fan(name, c, r=.072, blades=5):
    p = Part(name, c)
    p.cyl('metal-black', (c[0], c[1] + .006, c[2]), (c[0], c[1] - .012, c[2]), .022, seg=8)
    for k in range(blades):
        a = 2 * math.pi * k / blades
        p.box('ivory', (c[0] + math.cos(a) * r * .55, c[1], c[2] + math.sin(a) * r * .55), (r * .9, .006, .03), rot=(0.35, -a, 0))
    return p.finish()


def main():
    kit.reset()
    body = Part('body')
    body.box('stone', (0, 0, .08), (1.24, 1.3, .16), bevel=.025)
    body.box('metal', (0, 0, 1.13), (.9, 1.0, 1.94), bevel=.03, grain='z')
    for sx in (-1, 1):
        body.box('timber', (sx * .475, 0, 1.13), (.05, 1.06, 1.96), bevel=.01, grain='z')
    body.box('stone', (0, 0, 2.13), (1.06, 1.14, .06), bevel=.015)
    body.box('strip-cyan', (0, FRONT - .055, 2.095), (.9, .01, .02))
    body.box('panel', (0, FRONT - .006, 2.0), (.8, .01, .12))                  # name plate backing
    lights, fans = [], []
    for i in range(UNITS):
        z = Z0 + i * PITCH
        body.box('metal-black', (0, FRONT - .012, z), (.84, .024, .18), bevel=.006)
        body.cyl('brass', (FAN_X, FRONT - .024, z), (FAN_X, FRONT - .05, z), .085, seg=14, caps=False)
        body.cyl('panel', (FAN_X, FRONT - .025, z), (FAN_X, FRONT - .026, z), .08, seg=14)
        for k in range(3):   # vent slits between fan and light
            body.box('panel', (-.04 + k * .045, FRONT - .025, z), (.018, .004, .11))
        body.box('panel', (LIGHT_X, FRONT - .025, z), (.27, .004, .06))
        kit.slot_material(f'unit-{i + 1}-light', 'health')
        lights.append(Part(f'unit-{i + 1}-light', (LIGHT_X, FRONT - .03, z)).box(f'unit-{i + 1}-light', (LIGHT_X, FRONT - .03, z), (.24, .02, .04)).finish())
        fans.append(fan(f'unit-{i + 1}-fan', (FAN_X, FRONT - .04, z)))
        # back: a vent grille per unit
        for k in range(4):
            body.box('metal-black', (0, -FRONT + .008, z - .06 + k * .04), (.7, .016, .016))
    body.box('timber-dark', (0, -FRONT + .01, 1.95), (.7, .02, .1))
    body.finish()
    kit.MATS['label-name'] = dict(kit.MATS['panel'])
    Part('label-name', (0, FRONT - .012, 2.0)).quad('label-name', (0, FRONT - .012, 2.0), .74, .1).finish()
    proxy = kit.proxy_boxes([((0, 0, .08), (1.24, 1.3, .16)), ((0, 0, 1.13), (1.0, 1.1, 2.0))])
    kit.recentre(exclude=proxy)

    inputs = [
        {'id': 'health', 'type': 'enum', 'values': ['off', 'ok', 'warn', 'fail'], 'default': 'off', 'repeat': UNITS, 'label': 'Unit health',
         'explain': 'Units 1-8 from the bottom: each light bar shows its host (dark = no data or off).'},
        {'id': 'load', 'type': 'number', 'min': 0, 'max': 1, 'default': 0, 'label': 'Load',
         'explain': 'Fan speed: the fans idle slowly at no load and race at full load.'},
        {'id': 'name', 'type': 'text', 'maxLength': 20, 'label': 'Rack name', 'explain': 'The plate above the units.'},
    ]
    drives = [{'input': f'health.{i}', 'target': f'state:unit-{i}-light'} for i in range(1, UNITS + 1)]
    drives += [{'input': 'load', 'target': f'animation:unit-{i}-fan', 'map': {'scale': {'from': [0, 1], 'to': [.15, 4]}, 'clamp': True}}
               for i in range(1, UNITS + 1)]
    drives.append({'input': 'name', 'target': 'label:label-name'})
    m = kit.base_manifest(ID, 'Server rack', 'Hosts as a rack of eight units: a health light bar per unit and fans whose speed follows load.',
                          ['servers', 'hosts', 'health', 'rack'])
    m['traits'] = {
        'decorative': {'animations': [spin(o, (0, 1, 0), 1.6, phase=(k * .37) % 1) for k, o in enumerate(fans)]},
        'collidable': {'node': 'proxy'},
        'movable': {'surfaces': ['floor'], 'upright': True},
        'machine': {'primary': 'health', 'inputs': inputs, 'drives': drives,
                    'recipes': [{'name': 'Host list JSON', 'fields': {
                        **{f'health.{i}': f'/hosts/{i - 1}/status' for i in range(1, UNITS + 1)}, 'load': '/load', 'name': '/name'}}]},
    }
    m['slots'] = {
        'states': [kit.states_slot(f'unit-{i}-light') for i in range(1, UNITS + 1)],
        'labels': [{'id': 'label-name', 'pose': {'pose@': 'label-name'}, 'size': [.74, .1], 'maxChars': 20, 'font': 'mono'}],
    }
    kit.export(kit.out_dir(ID), m, proxy=proxy)


main()
