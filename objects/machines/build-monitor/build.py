# SPDX-License-Identifier: MIT
"""build-monitor: a desk-height build totem (RFC-0013 machine, draft).

A stone base and timber column carry a round head whose two faces glow in the
build state. A brass halo ring with three glow arcs turns around the head while
a build runs; the arcs brighten with progress. Glyphs on both faces (a tick, a
cross, three dots) name the state without colour, and a burst anchor sits above.

    make machines        (Blender on the bake host)
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kit
from kit import Part, empty, spin

ID = 'build-monitor'
HC = 1.18          # head centre height
FR = .36           # face radius
RR = .53           # halo ring radius


def glyph(name, bars):
    """A glyph of (x, z, length, angle) bars on both faces (mirrored on the back so it
    reads the same from behind), as one toggle node."""
    p = Part(name, (0, 0, HC))
    for side in (-1, 1):
        for x, z, L, a in bars:
            p.box('panel', (x * -side, side * .081, HC + z), (L, .006, .045), rot=(0, a * -side, 0))
    return p.finish()


def main():
    kit.reset()
    body = Part('body')
    body.cyl('stone', (0, 0, 0), (0, 0, .14), .4, seg=24)
    body.cyl('brass', (0, 0, .14), (0, 0, .16), .3, seg=20)
    body.cyl('strip-cyan', (0, 0, .07), (0, 0, .09), .405, seg=24, caps=False)
    body.box('timber', (0, 0, .5), (.2, .2, .7), bevel=.015)
    body.box('metal-black', (0, 0, .84), (.24, .24, .08), bevel=.01)
    body.cyl('metal', (0, -.07, HC), (0, .07, HC), FR + .06, seg=28)          # the head (bezel)
    body.cyl('brass', (0, -.071, HC), (0, -.076, HC), FR + .03, seg=28, caps=False)
    body.cyl('brass', (0, .071, HC), (0, .076, HC), FR + .03, seg=28, caps=False)
    body.finish()
    kit.slot_material('face', 'face')
    face = Part('face', (0, 0, HC))
    for side in (-1, 1):
        face.cyl('face', (0, side * .07, HC), (0, side * .078, HC), FR, seg=28)
    face.finish()
    kit.slot_material('ring-glow', 'glow')
    ring = Part('ring', (0, 0, HC))
    ring.torus('brass', (0, 0, HC), RR, .02, seg=40, sseg=6, rot=(math.pi / 2, 0, 0))
    for k in range(3):
        for j in range(5):
            a = 2 * math.pi * k / 3 + j * .075
            ring.box('ring-glow', (RR * math.cos(a), 0, HC + RR * math.sin(a)), (.045, .055, .055), rot=(0, -(a + math.pi / 2), 0))
    ring = ring.finish(smooth_angle=50)
    glyph('glyph-ok', [(-.075, -.025, .14, math.radians(45)), (.06, .035, .28, -math.radians(49))])
    glyph('glyph-fail', [(0, 0, .3, math.radians(45)), (0, 0, .3, -math.radians(45))])
    glyph('glyph-run', [(-.12, -.02, .06, 0), (0, .04, .06, 0), (.12, -.02, .06, 0)])
    empty('burst-fx', (0, 0, 2.0))
    proxy = kit.proxy_boxes([((0, 0, .45), (.8, .8, .9)), ((0, 0, HC), (1.12, .2, 1.12))])
    kit.recentre(exclude=proxy)

    inputs = [
        {'id': 'status', 'type': 'enum', 'values': ['idle', 'running', 'ok', 'fail'], 'default': 'idle', 'label': 'Build status',
         'explain': 'The face colour and glyph: three dots while running, a tick when it passes, a cross when it fails. The halo turns while running.'},
        {'id': 'progress', 'type': 'number', 'min': 0, 'max': 1, 'default': 0, 'label': 'Progress',
         'explain': 'How bright the halo arcs glow.'},
        {'id': 'succeeded', 'type': 'event', 'label': 'Build succeeded', 'explain': 'A burst above the head (also when the status becomes ok after running).'},
    ]
    drives = [
        {'input': 'status', 'target': 'state:face'},
        {'input': 'status', 'target': 'state:ring-glow'},
        {'input': 'progress', 'target': 'emission:ring-glow', 'map': {'scale': {'from': [0, 1], 'to': [.35, 1.6]}, 'clamp': True}},
        {'input': 'status', 'target': 'animation:ring', 'map': {'cases': [{'equals': 'running', 'to': 1}], 'else': 0}},
        {'input': 'status', 'target': 'visible:glyph-ok', 'map': {'cases': [{'equals': 'ok', 'to': True}], 'else': False}},
        {'input': 'status', 'target': 'visible:glyph-fail', 'map': {'cases': [{'equals': 'fail', 'to': True}], 'else': False}},
        {'input': 'status', 'target': 'visible:glyph-run', 'map': {'cases': [{'equals': 'running', 'to': True}], 'else': False}},
        {'input': 'succeeded', 'target': 'effect:burst-fx'},
        {'input': 'status', 'target': 'effect:burst-fx', 'map': {'becomes': 'ok', 'from': 'running'}},
    ]
    m = kit.base_manifest(ID, 'Build monitor', 'A desk-height build totem: a glowing face with a state glyph, a halo that turns while building, and a burst on success.',
                          ['build', 'ci', 'status', 'monitor'])
    m['traits'] = {
        'decorative': {'animations': [spin(ring, (0, 1, 0), 6)]},
        'collidable': {'node': 'proxy'},
        'movable': {'surfaces': ['floor'], 'upright': True},
        'machine': {'primary': 'status', 'inputs': inputs, 'drives': drives,
                    'recipes': [{'name': 'Latest build JSON', 'fields': {'status': '/builds/0/status', 'progress': '/builds/0/progress',
                                                                        'succeeded': '/counters/succeeded'}}]},
    }
    m['slots'] = {
        'states': [kit.states_slot('face'), kit.states_slot('ring-glow')],
        'effects': [{'id': 'burst-fx', 'pose': {'pose@': 'burst-fx'}, 'kind': 'burst', 'colour': list(kit.MINT), 'durationMs': 1500}],
        'toggles': [{'id': 'glyph-ok', 'nodes': ['glyph-ok']}, {'id': 'glyph-fail', 'nodes': ['glyph-fail']}, {'id': 'glyph-run', 'nodes': ['glyph-run']}],
    }
    kit.export(kit.out_dir(ID), m, proxy=proxy)


main()
