# SPDX-License-Identifier: MIT
"""Machine Yard placeholder machines: seven object assets built from primitives.

Each asset is an RFC-0011 object directory (`objects/<id>/<id>.gltf` + `.bin`, tile
textures, `object.json`) with the RFC-0013 draft `machine` trait and slots. Node, material
and slot names are the machines prototype's (`stage_1_lamp`, `item_spawn`, `label_title`...):
a states slot owns one node, one mesh and one material named like the slot.
Asset space: glTF metres, +Y up, front +Z, origin at the base centre (bounds min Y = 0).
The world.json `objectAssets[]` entry (world format 0.8) is written by build.py from the
same data: inline `scene` plus the decorative `animations` and the collision proxy.
"""
import json, math
from pathlib import Path
import bpy
from mathutils import Vector
import kit
from kit import Part, empty, bl, gl, MATS, CYAN, MINT, AMBER, RED, WARM_GREY, SLATE, IVORY

ATTRIBUTION = [{'path': '.', 'author': 'Hyprune contributors', 'license': 'CC-BY-4.0',
                'source': 'https://github.com/hyprune/worlds/tree/main/machine-yard'}]
STALE = {'id': 'stale', 'colour': [.3, .3, .3], 'emission': .1}

# Palettes: (id, linear colour, emission). The first entry is the rest state.
LAMP = [('idle', WARM_GREY, .15), ('running', AMBER, 3), ('ok', MINT, 3), ('fail', RED, 4)]
HEALTH = [('ok', MINT, 2.5), ('warn', AMBER, 3), ('fail', RED, 4), ('off', (.05, .06, .07), 0)]
LEVEL = [('ok', MINT, 2.5), ('warn', AMBER, 3), ('fail', RED, 4)]
PHASE = [('off', SLATE, .15), ('active', CYAN, 3), ('done', MINT, 2.5), ('fail', RED, 4)]
BEACON = [('off', SLATE, .15), ('active', AMBER, 3), ('live', MINT, 3.5), ('fail', RED, 4)]
FACE = [('idle', (.16, .2, .24), .4), ('running', CYAN, 2), ('ok', MINT, 2), ('fail', RED, 2.5)]
TOKEN = [('idle', IVORY, .2), ('running', CYAN, 2), ('ok', MINT, 2), ('fail', RED, 2.5)]
SPARK = [('mint', MINT, 3), ('amber', AMBER, 3), ('cyan', CYAN, 3)]
LABEL_COLOUR = [.55, 1.0, .85]


def slot_mat(name, palette, rough=.3):
    st = palette[0]
    MATS[name] = dict(color=st[1], rough=rough, emit=st[2], palette=palette)
    return name


def states(slot, palette):
    return {'id': slot, 'materials': [slot], 'palette': [
        {'id': s, 'colour': [round(c, 4) for c in col], 'emission': em} for s, col, em in palette] + [STALE]}


def pose(p, q=(0, 0, 0, 1)):
    return {'position': [round(v, 4) for v in p], 'rotation': list(q)}


def spin(node, axis, pivot, period, phase=0.0):
    a = {'node': node, 'type': 'spin', 'axis': list(axis), 'pivot': [round(v, 4) for v in pivot], 'period': period}
    if phase:
        a['phase'] = phase
    return a


def blade(p, mat, centre, angle, length, width, thick, axis='z'):
    """A flat blade from `centre` outwards at `angle` in the plane normal to `axis` (glTF)."""
    c = Vector(centre); pts = []
    d = Vector((math.cos(angle), math.sin(angle)))
    n = Vector((-d.y, d.x))
    for r in (.25 * length, length):
        for s in (-1, 1):
            for t in (-1, 1):
                u = d * r + n * s * width / 2
                off = {'z': Vector((u.x, u.y, t * thick / 2)), 'y': Vector((u.x, t * thick / 2, u.y))}[axis]
                pts.append(c + off)
    return p.hull(mat, [tuple(v) for v in pts])


def lens(p, mat, base, r, depth=.05, normal=(0, 0, 1), seg=20):
    b = Vector(base); n = Vector(normal)
    p.cyl(mat, tuple(b), tuple(b + n * depth * .6), r, seg=seg)
    p.cyl(mat, tuple(b + n * depth * .6), tuple(b + n * depth), r, seg=seg, r2=r * .72)
    return p


def crate(p, centre, size, wood='timber', band='metal-black'):
    x, y, z = centre; sx, sy, sz = size
    p.box(wood, (x, y, z), (sx - .02, sy - .02, sz - .02), bevel=.012)
    for dy in (-sy / 2 + .04, sy / 2 - .04):
        p.box(band, (x, y + dy, z), (sx, .03, sz), bevel=.004)
    return p


# ---------------------------------------------------------------------------- assets

def ci_conveyor():
    body = Part('conveyor')
    # Belt bed: rails, belt, legs, skirts, foot rails.
    for z in (-.36, .36):
        body.box('metal-black', (-.15, .88, z), (5.0, .12, .06), bevel=.01)
        body.box('metal', (-.15, .04, z), (5.1, .08, .12), bevel=.01)
        for x in (-2.55, -1.0, .55, 2.2):
            body.box('metal-black', (x, .45, z), (.08, .82, .08), bevel=.008)
        body.box('timber', (-.15, .55, z * 1.11), (4.9, .5, .04), bevel=.008)
    body.box('rubber', (-.15, .915, 0), (5.0, .07, .62), bevel=.02)
    body.box('strip-cyan', (-.15, .12, .425), (4.9, .025, .012))
    # Hopper: a funnel on four legs.
    hx = -2.45
    body.hull('metal', [(hx + sx * a, y, sz * a) for a, y in ((.45, 2.0), (.18, 1.3)) for sx in (-1, 1) for sz in (-1, 1)])
    for sx in (-1, 1):
        body.box('timber', (hx + sx * .46, 2.03, 0), (.06, .07, .98), bevel=.01)
        body.box('timber', (hx, 2.03, sx * .46), (.98, .07, .06), bevel=.01)
        for sz in (-1, 1):
            body.box('metal-black', (hx + sx * .42, 1.0, sz * .42), (.06, 2.0, .06), bevel=.006)
    # Stations: arches over the belt.
    stations = [-1.5, -.45, .6, 1.65]
    for x in stations:
        for z in (-.46, .46):
            body.box('metal-black', (x, .9, z), (.07, 1.8, .07), bevel=.008)
        body.box('metal', (x, 1.72, 0), (.42, .26, 1.06), bevel=.03)
        body.box('timber', (x, 1.875, 0), (.46, .05, 1.1), bevel=.01)
        body.cyl('metal-black', (x, 1.59, 0), (x, 1.5, 0), .02, seg=8)
    # Chute and bin at the outfeed.
    for t, i in ((-.3, 1), (.3, -1)):
        body.hull('metal', [(x, y + dy, zz) for x, y in ((2.35, .93), (2.6, .6)) for dy in (0, .12) for zz in (t, t + i * .03)])
    body.hull('metal', [(2.35, .9, -.3), (2.35, .93, -.3), (2.35, .9, .3), (2.35, .93, .3),
                        (2.6, .57, -.3), (2.6, .6, -.3), (2.6, .57, .3), (2.6, .6, .3)])
    bx, bw, bh, bd = 2.665, .47, .45, .75
    body.box('timber', (bx, .03, 0), (bw, .06, bd), bevel=.01)
    for s in (-1, 1):
        body.box('timber', (bx + s * (bw / 2 - .02), bh / 2, 0), (.04, bh, bd), bevel=.008)
        body.box('timber', (bx, bh / 2, s * (bd / 2 - .02)), (bw, bh, .04), bevel=.008)
    body.box('paint-amber', (bx, bh - .03, bd / 2 + .001), (bw, .04, .01))
    # Label panel (front skirt).
    body = body.finish()
    label = Part('label_title'); MATS['label_title'] = dict(color=(.01, .012, .016), rough=.3)
    label.box('label_title', (-.15, .55, .425), (1.6, .3, .01)); label = label.finish()

    lamps, spinners, anims = [], [], []
    for n, x in enumerate(stations, 1):
        name = slot_mat(f'stage_{n}_lamp', LAMP)
        p = Part(name, (x, 1.72, .53))
        lens(p, name, (x, 1.72, .53), .075)
        p.box(name, (x, 1.915, 0), (.12, .03, .9))
        lamps.append(p.finish())
        s = Part(f'stage_{n}_spinner', (x, 1.47, 0))
        s.cyl('metal-black', (x, 1.5, 0), (x, 1.44, 0), .05, seg=16)
        for k in range(4):
            blade(s, 'brass', (x, 1.47, 0), k * math.pi / 2 + .3, .19, .07, .012, axis='y')
        spinners.append(s.finish())
        anims.append(spin(f'stage_{n}_spinner', [0, 1, 0], (x, 1.47, 0), 1.6, phase=n * .13 % 1))
    # Alarm beacon on the hopper rim (a toggle: shown on failure).
    MATS['alarm'] = dict(color=RED, rough=.3, emit=4)
    ax, az = hx + .46, .46
    a = Part('alarm', (ax, 2.065, az))
    a.cyl('metal-black', (ax, 2.065, az), (ax, 2.1, az), .055, seg=16)
    a.cyl('alarm', (ax, 2.1, az), (ax, 2.22, az), .045, seg=16, r2=.03)
    a = a.finish()
    # Waiting stack: one crate node, drawn as copies by the runtime.
    w = Part('waiting_crate', (-2.72, 0, .62))
    crate(w, (-2.72, .15, .62), (.26, .3, .26)); w = w.finish()

    track = empty('track', (0, 0, 0))
    y = .952
    pts = [(hx, 1.32, 0), (hx, y, 0)] + [(x, y, 0) for x in stations] + [(2.33, y, 0), (2.6, .62, 0), (bx, .1, 0)]
    for i, p in enumerate(pts):
        empty(f'track_p{i:02d}', p, track)
    face_x = (0, .70711, 0, .70711)
    empty('item_spawn', pts[0]); empty('success_fx', (bx, .75, 0)); empty('fail_fx', (.075, 2.15, 0))
    proxy = Part('proxy'); proxy.box('proxy', (0, 1.0, 0), (5.8, 2.0, 1.0)); proxy.box('proxy', (-2.57, .45, .78), (.62, .9, .62)); proxy = proxy.finish()

    track_slot = {'id': 'belt', 'speed': .6,
                  'points': [{'position': [round(v, 4) for v in p], 'type': 'line'} for p in pts],
                  'items': {'assets': ['job-token'], 'max': 24, 'spacing': .45, 'overflow': 'drop-oldest'},
                  'sink': True, 'stops': [{'point': i, 'seconds': 1.2} for i in range(2, 6)]}
    machine = {
        'primary': 'status',
        'inputs': [
            {'id': 'status', 'type': 'enum', 'values': ['idle', 'running', 'ok', 'fail'], 'default': 'idle', 'label': 'Pipeline status',
             'explain': 'The alarm beacon on the hopper lights while the pipeline has failed.'},
            {'id': 'stage', 'type': 'enum', 'values': ['idle', 'running', 'ok', 'fail'], 'default': 'idle', 'repeat': 4, 'label': 'Stage status',
             'explain': 'Each station lamp shows its stage; its rotor turns while the stage runs.'},
            {'id': 'jobStarted', 'type': 'event', 'label': 'Job started', 'explain': 'Each started job drops a token from the hopper onto the belt.'},
            {'id': 'jobPassed', 'type': 'event', 'label': 'Job passed', 'explain': 'A passed job throws sparks over the outfeed bin.'},
            {'id': 'jobFailed', 'type': 'event', 'label': 'Job failed', 'explain': 'A failed job flashes red over the stations.'},
            {'id': 'queued', 'type': 'int', 'min': 0, 'max': 12, 'default': 0, 'label': 'Queued jobs', 'explain': 'Crates waiting beside the hopper, one per queued job.'},
            {'id': 'lastJob', 'type': 'text', 'maxLength': 24, 'label': 'Last job', 'explain': 'The newest job, on the front panel.'}],
        'drives': [
            {'input': 'stage.{n}', 'target': 'state:stage_{n}_lamp'},
            {'input': 'stage.{n}', 'target': 'animation:stage_{n}_spinner', 'map': {'cases': [{'equals': 'running', 'to': 1}], 'else': 0}},
            {'input': 'status', 'target': 'visible:alarm', 'map': {'cases': [{'equals': 'fail', 'to': True}], 'else': False}},
            {'input': 'jobStarted', 'target': 'spawn:item_spawn'},
            {'input': 'jobPassed', 'target': 'effect:success_fx'},
            {'input': 'jobFailed', 'target': 'effect:fail_fx'},
            {'input': 'queued', 'target': 'count:waiting'},
            {'input': 'lastJob', 'target': 'label:label_title'}],
        'positions': []}
    slots = {
        'states': [states(f'stage_{n}_lamp', LAMP) for n in range(1, 5)],
        'labels': [{'id': 'label_title', 'pose': pose((-.15, .55, .4305)), 'size': [1.56, .26], 'maxChars': 24, 'font': 'mono', 'colour': LABEL_COLOUR}],
        'tracks': [track_slot],
        'spawns': [{'id': 'item_spawn', 'pose': pose(pts[0], face_x), 'track': 'belt', 'items': ['job-token'], 'maxRate': 2}],
        'stacks': [{'id': 'waiting', 'node': 'waiting_crate', 'cap': 12, 'layout': {'grid': [2, 3, 2], 'spacing': [.3, .3, .3], 'fill': 'xzy'}}],
        'toggles': [{'id': 'alarm', 'nodes': ['alarm']}],
        'effects': [{'id': 'success_fx', 'pose': pose((bx, .75, 0)), 'kind': 'burst', 'colour': [.4, 1.0, .7], 'durationMs': 1500},
                    {'id': 'fail_fx', 'pose': pose((.075, 2.15, 0)), 'kind': 'flash', 'colour': [1.0, .2, .15], 'durationMs': 900}]}
    return dict(id='ci-conveyor', name='CI conveyor', tags=['ci', 'pipeline', 'conveyor'],
                description='A four-station conveyor: jobs drop from the hopper, pause under each station and leave by the chute.',
                animations=anims, machine=machine, slots=slots, proxy=proxy)


def queue_stack():
    body = Part('shelving')
    for sx in (-1, 1):
        for sz in (-1, 1):
            body.box('metal-black', (sx * 1.27, 1.33, sz * .36), (.07, 2.66, .07), bevel=.008)
            body.box('metal', (sx * 1.27, .02, sz * .36), (.14, .04, .14), bevel=.008)
    levels = [.10, .62, 1.14, 1.66, 2.18]
    for y in levels:
        body.box('timber', (0, y - .02, 0), (2.5, .04, .76), bevel=.008)
        for sz in (-1, 1):
            body.box('metal-black', (0, y - .05, sz * .37), (2.54, .05, .04), bevel=.006)
    for a, b in zip(levels, levels[1:]):  # back cross braces
        body.cyl('metal-black', (-1.24, a, -.37), (1.24, b - .05, -.37), .012, seg=6)
        body.cyl('metal-black', (1.24, a, -.37), (-1.24, b - .05, -.37), .012, seg=6)
        for sx in (-1, 1):
            body.cyl('metal-black', (sx * 1.27, a, -.33), (sx * 1.27, b - .05, .33), .01, seg=6)
    body.box('metal-black', (0, 2.43, .3), (2.62, .42, .1), bevel=.02)
    body.box('timber', (0, 2.66, .25), (2.66, .05, .24), bevel=.01)
    body.box('strip-cyan', (0, 2.215, .356), (2.5, .02, .012))
    body = body.finish()
    MATS['label_count'] = dict(color=(.01, .012, .016), rough=.3)
    label = Part('label_count'); label.box('label_count', (-.25, 2.43, .355), (1.5, .3, .01)); label = label.finish()
    lamp = slot_mat('age_lamp', LEVEL)
    p = Part('age_lamp', (.95, 2.43, .35))
    lens(p, lamp, (.95, 2.43, .35), .11)
    p.box(lamp, (1.27, 1.2, .41), (.03, 1.9, .012))
    p.finish()
    c = Part('crate', (-1.025, .10, .02)); crate(c, (-1.025, .29, .02), (.36, .38, .5)); c.finish()
    proxy = Part('proxy'); proxy.box('proxy', (0, 1.34, 0), (2.66, 2.68, .84)); proxy = proxy.finish()
    machine = {
        'primary': 'level',
        'inputs': [
            {'id': 'depth', 'type': 'int', 'min': 0, 'max': 500, 'default': 0, 'label': 'Queue depth', 'explain': 'Crates on the shelves fill bottom-up with the depth; the panel shows the number.'},
            {'id': 'level', 'type': 'enum', 'values': ['ok', 'warn', 'fail'], 'default': 'ok', 'label': 'Queue health', 'explain': 'The lamp and the stripe on the right post: green, amber or red with the oldest item age.'}],
        'drives': [
            {'input': 'depth', 'target': 'count:crates', 'map': {'scale': {'from': [0, 500], 'to': [0, 24]}, 'clamp': True, 'round': 'ceil'}},
            {'input': 'depth', 'target': 'label:label_count', 'map': {'format': {'decimals': 0, 'compact': True, 'unit': 'queued'}}},
            {'input': 'level', 'target': 'state:age_lamp'}],
        'positions': []}
    slots = {
        'states': [states('age_lamp', LEVEL)],
        'labels': [{'id': 'label_count', 'pose': pose((-.25, 2.43, .3605)), 'size': [1.46, .26], 'maxChars': 14, 'font': 'mono', 'colour': LABEL_COLOUR}],
        'stacks': [{'id': 'crates', 'node': 'crate', 'cap': 24, 'layout': {'grid': [6, 4, 1], 'spacing': [.41, .52, .5], 'fill': 'xzy'}}]}
    return dict(id='queue-stack', name='Queue stack', tags=['queue', 'crates', 'shelving'],
                description='Shelving that fills with crates as a queue grows, with a depth panel and a health lamp.',
                animations=[], machine=machine, slots=slots, proxy=proxy)


def server_rack():
    body = Part('cabinet')
    for sx in (-1, 1):
        body.box('timber-dark', (sx * .58, 1.17, 0), (.04, 2.34, 1.0), bevel=.012)
    body.box('metal-black', (0, 2.3, 0), (1.2, .1, 1.0), bevel=.015)
    body.box('metal-black', (0, .07, 0), (1.12, .14, .96), bevel=.01)
    body.box('metal-black', (0, 1.17, -.47), (1.12, 2.2, .03))
    body.box('strip-cyan', (0, 2.255, .5), (1.12, .02, .012))
    pitch, top = .255, 2.24
    lights, fans, anims = [], [], []
    for n in range(1, 9):
        y = top - pitch * (n - .5)
        body.box('metal-black', (0, y, 0), (1.1, .235, .9), bevel=.006)
        body.box('panel', (0, y, .456), (1.1, .225, .012), bevel=.003)
        for k in range(3):
            body.box('metal', (-.02 + k * .07, y, .465), (.05, .16, .008))
        body.torus('metal', (.33, y, .47), .09, .012, axis=(0, 0, 1), seg=24, sseg=6)
        name = slot_mat(f'unit_{n}_light', HEALTH)
        p = Part(name, (-.32, y, .47)); p.box(name, (-.32, y, .47), (.32, .035, .02), bevel=.005); lights.append(p.finish())
        f = Part(f'unit_{n}_fan', (.33, y, .465))
        f.cyl('metal-black', (.33, y, .455), (.33, y, .475), .025, seg=12)
        for k in range(5):
            blade(f, 'metal', (.33, y, .465), k * 2 * math.pi / 5 + n, .078, .035, .006, axis='z')
        fans.append(f.finish())
        anims.append(spin(f'unit_{n}_fan', [0, 0, 1], (.33, y, .465), 1.2, phase=(n * .37) % 1))
    body = body.finish()
    proxy = Part('proxy'); proxy.box('proxy', (0, 1.18, 0), (1.2, 2.36, 1.02)); proxy = proxy.finish()
    machine = {
        'primary': 'health',
        'inputs': [
            {'id': 'health', 'type': 'enum', 'values': ['ok', 'warn', 'fail', 'off'], 'default': 'ok', 'repeat': 8, 'label': 'Unit health', 'explain': 'One light per unit, top to bottom: green, amber, red or dark.'},
            {'id': 'load', 'type': 'number', 'min': 0, 'max': 1, 'default': 0, 'repeat': 8, 'label': 'Unit load', 'explain': 'Each unit fan turns faster with its load.'}],
        'drives': [
            {'input': 'health.{n}', 'target': 'state:unit_{n}_light'},
            {'input': 'load.{n}', 'target': 'animation:unit_{n}_fan', 'map': {'scale': {'from': [0, 1], 'to': [.2, 3]}, 'clamp': True}}],
        'positions': []}
    slots = {'states': [states(f'unit_{n}_light', HEALTH) for n in range(1, 9)]}
    return dict(id='server-rack', name='Server rack', tags=['servers', 'hosts', 'rack'],
                description='An eight-unit cabinet: one health light and one fan per unit, numbered top to bottom.',
                animations=anims, machine=machine, slots=slots, proxy=proxy)


def deploy_lift():
    body = Part('frame')
    for sx in (-1, 1):
        for sz in (-1, 1):
            body.box('metal', (sx * .98, 2.0, sz * .98), (.14, 4.0, .14), bevel=.015)
        body.box('metal-black', (sx * .7, 2.02, -.9), (.08, 3.88, .08), bevel=.008)  # rails
    for i in range(4):
        body.box('timber', (0, .55 + i * .9, -1.0), (1.82, .86, .05), bevel=.01)  # back cladding
    for sz in (-1, 1):
        body.box('metal-black', (0, 4.0, sz * .98), (2.1, .16, .14), bevel=.015)
        body.box('metal-black', (sz * .98, 4.0, 0), (.14, .16, 2.1), bevel=.015)
    body.box('metal-black', (0, .05, 0), (2.2, .1, 2.2), bevel=.015)
    body.box('paint-amber', (0, .101, 1.0), (1.9, .01, .1))
    body.box('strip-cyan', (0, 3.915, 1.051), (1.9, .02, .012))
    body.box('metal-black', (0, 3.75, 1.07), (1.3, .3, .04), bevel=.008)  # sign board
    body.cyl('metal-black', (0, 4.08, -.98), (0, 4.17, -.98), .12, seg=20)  # beacon base
    body = body.finish()
    MATS['label_env'] = dict(color=(.01, .012, .016), rough=.3)
    label = Part('label_env'); label.box('label_env', (0, 3.75, 1.0905), (1.22, .24, .001)); label.finish()
    travel, bottom = 2.6, .12
    rest = bottom + travel / 2
    pl = Part('platform', (0, rest, 0))
    pl.box('timber', (0, rest + .05, .05), (1.7, .1, 1.7), bevel=.012)
    pl.box('metal-black', (0, rest + .005, .05), (1.76, .04, 1.76), bevel=.008)
    for sx in (-1, 1):
        pl.box('metal-black', (sx * .7, rest + .2, -.83), (.16, .4, .1), bevel=.01)  # guide shoes
        pl.box('metal', (sx * .84, rest + .55, .05), (.03, .03, 1.66))
        for z in (-.75, .05, .85):
            pl.box('metal', (sx * .84, rest + .33, z), (.03, .46, .03))
    pl.box('metal', (0, rest + .55, -.78), (1.68, .03, .03))
    crate(pl, (.1, rest + .4, .15), (.8, .6, .6))
    pl.box('paint-amber', (.1, rest + .4, .451), (.5, .12, .006))
    pl.finish()
    lamps = []
    for n in range(1, 5):
        name = slot_mat(f'phase_lamp_{n}', PHASE)
        y = .9 + (n - 1) * .8
        p = Part(name, (-.98, y, 1.05))
        for sx in (-1, 1):
            p.box(name, (sx * .98, y, 1.06), (.1, .18, .02), bevel=.006)
        lamps.append(p.finish())
    bname = slot_mat('beacon', BEACON)
    bc = Part('beacon', (0, 4.27, -.98))
    bc.cyl(bname, (0, 4.17, -.98), (0, 4.37, -.98), .07, seg=20)
    for sx in (-1, 1):
        bc.box('metal-black', (sx * .1, 4.27, -.98), (.03, .2, .13), bevel=.006)
    bc.cyl('metal-black', (0, 4.37, -.98), (0, 4.4, -.98), .11, seg=20)
    bc.finish()
    gate = Part('gate', (0, .55, 1.12))
    for y in (.5, 1.0):
        gate.box('paint-amber', (0, y, 1.12), (1.82, .06, .04), bevel=.01)
    for x in (-.9, -.3, .3, .9):
        gate.box('metal-black', (x, .55, 1.12), (.04, .9, .04))
    gate.finish()
    empty('burst_fx', (0, 4.65, 0))
    proxy = Part('proxy'); proxy.box('proxy', (0, 2.1, 0), (2.2, 4.2, 2.3)); proxy = proxy.finish()
    anims = [{'node': 'platform', 'type': 'bob', 'axis': [0, 1, 0], 'amplitude': travel / 2, 'period': 24},
             spin('beacon', [0, 1, 0], (0, 4.27, -.98), 1.2)]
    machine = {
        'primary': 'status',
        'inputs': [
            {'id': 'status', 'type': 'enum', 'values': ['idle', 'deploying', 'done', 'failed'], 'default': 'idle', 'label': 'Deploy status',
             'explain': 'The beacon turns amber while deploying, green when done and red on failure; the gate opens when done.'},
            {'id': 'progress', 'type': 'number', 'min': 0, 'max': 1, 'default': 0, 'label': 'Progress', 'explain': 'The platform rises with progress; the four phase lamps light in turn.'},
            {'id': 'environment', 'type': 'text', 'maxLength': 20, 'label': 'Environment', 'explain': 'The target environment, on the sign.'},
            {'id': 'finished', 'type': 'event', 'label': 'Deploy finished', 'explain': 'Sparks over the mast when a deploy finishes.'}],
        'drives': [
            {'input': 'progress', 'target': 'position:platform'},
            {'input': 'status', 'target': 'state:beacon', 'map': {'cases': [{'equals': 'deploying', 'to': 'active'}, {'equals': 'done', 'to': 'live'}, {'equals': 'failed', 'to': 'fail'}], 'else': 'off'}},
            {'input': 'status', 'target': 'animation:beacon', 'map': {'cases': [{'equals': 'deploying', 'to': .6}, {'equals': 'done', 'to': 1.5}], 'else': 0}},
            {'input': 'status', 'target': 'visible:gate_closed', 'map': {'cases': [{'equals': 'done', 'to': False}], 'else': True}}]
        + [{'input': 'progress', 'target': f'state:phase_lamp_{n}',
            'map': {'thresholds': [{'below': (n - 1) / 4 + .001, 'to': 'off'}, {'below': n / 4, 'to': 'active'}], 'else': 'done'}} for n in range(1, 5)]
        + [{'input': 'finished', 'target': 'effect:burst_fx'},
           {'input': 'environment', 'target': 'label:label_env'}],
        'positions': [{'node': 'platform', 'range': [.75, 1.25]}]}
    slots = {
        'states': [states(f'phase_lamp_{n}', PHASE) for n in range(1, 5)] + [states('beacon', BEACON)],
        'labels': [{'id': 'label_env', 'pose': pose((0, 3.75, 1.0915)), 'size': [1.2, .22], 'maxChars': 20, 'font': 'mono', 'colour': LABEL_COLOUR}],
        'toggles': [{'id': 'gate_closed', 'nodes': ['gate']}],
        'effects': [{'id': 'burst_fx', 'pose': pose((0, 4.65, 0)), 'kind': 'burst', 'colour': [.4, 1.0, .7], 'durationMs': 1600}]}
    return dict(id='deploy-lift', name='Deploy lift', tags=['deploy', 'release', 'lift'],
                description='A lift whose platform rises with deploy progress, four phase lamps, a mast beacon and a gate that opens when done.',
                animations=anims, machine=machine, slots=slots, proxy=proxy,
                notes={'platformTravel': travel, 'platformBottom': bottom})


def build_monitor():
    body = Part('totem')
    body.box('metal-black', (0, .03, 0), (1.1, .06, 1.1), bevel=.01)
    body.box('stone', (0, .48, 0), (1.0, .84, 1.0), bevel=.03)
    body.box('timber', (0, .93, 0), (1.06, .08, 1.06), bevel=.015)
    body.box('strip-cyan', (0, .885, .531), (.98, .02, .01))
    body.cyl('metal-black', (0, .97, 0), (0, 1.52, 0), .12, seg=20)
    body.cyl('metal-black', (0, 2.1, -.08), (0, 2.1, .08), .62, seg=48)
    body.cyl('brass', (0, 2.1, .08), (0, 2.1, .09), .6, seg=48, r2=.56)
    body.cyl('brass', (0, 2.1, -.08), (0, 2.1, -.09), .6, seg=48, r2=.56)
    body.sphere('brass', (0, 2.78, 0), .05)
    body.cyl('metal-black', (0, 2.72, 0), (0, 2.76, 0), .02, seg=8)
    body = body.finish()
    MATS['label_title'] = dict(color=(.01, .012, .016), rough=.3)
    label = Part('label_title'); label.box('label_title', (0, .6, .505), (.8, .22, .01)); label.finish()
    face = slot_mat('face', FACE, rough=.2)
    f = Part('face', (0, 2.1, 0))
    f.cyl(face, (0, 2.1, .09), (0, 2.1, .1), .52, seg=48)
    f.cyl(face, (0, 2.1, -.09), (0, 2.1, -.1), .52, seg=48)
    f.finish()
    r = Part('ring', (0, 2.1, -.2))
    for k in range(8):
        a0 = k / 8 + .006; a1 = (k + 1) / 8 - .006
        r.torus('brass', (0, 2.1, -.2), .74, .035, axis=(0, 0, 1), seg=8, sseg=8, arc=(a0, a1))
        a = 2 * math.pi * (k + .5) / 8 if k % 2 == 0 else None
        if a is not None:
            r.sphere('strip-cyan', (.74 * math.cos(a), 2.1 + .74 * math.sin(a), -.2), .05, sub=1)
    r.finish()
    empty('burst_fx', (0, 3.05, 0))
    proxy = Part('proxy'); proxy.box('proxy', (0, .5, 0), (1.1, 1.0, 1.1)); proxy.box('proxy', (0, 1.8, 0), (.3, 1.6, .3)); proxy = proxy.finish()
    anims = [spin('ring', [0, 0, 1], (0, 2.1, -.2), 8)]
    machine = {
        'primary': 'status',
        'inputs': [
            {'id': 'status', 'type': 'enum', 'values': ['idle', 'running', 'ok', 'fail'], 'default': 'idle', 'label': 'Build status',
             'explain': 'The face shows the build: grey idle, cyan running, green passed, red failed; the ring turns fast while it runs.'},
            {'id': 'progress', 'type': 'number', 'min': 0, 'max': 1, 'default': 0, 'label': 'Progress', 'explain': 'The face brightens as the build progresses.'},
            {'id': 'passed', 'type': 'event', 'label': 'Build passed', 'explain': 'Sparks burst over the totem for each passed build.'},
            {'id': 'lastJob', 'type': 'text', 'maxLength': 20, 'label': 'Last build', 'explain': 'The newest build, on the pedestal panel.'}],
        'drives': [
            {'input': 'status', 'target': 'state:face'},
            {'input': 'status', 'target': 'animation:ring', 'map': {'cases': [{'equals': 'running', 'to': 1}], 'else': .15}},
            {'input': 'progress', 'target': 'emission:face', 'map': {'scale': {'from': [0, 1], 'to': [.6, 1.6]}, 'clamp': True}},
            {'input': 'passed', 'target': 'effect:burst_fx'},
            {'input': 'lastJob', 'target': 'label:label_title'}],
        'positions': []}
    slots = {
        'states': [states('face', FACE)],
        'labels': [{'id': 'label_title', 'pose': pose((0, .6, .5105)), 'size': [.76, .2], 'maxChars': 20, 'font': 'mono', 'colour': LABEL_COLOUR}],
        'effects': [{'id': 'burst_fx', 'pose': pose((0, 3.05, 0)), 'kind': 'burst', 'colour': [1.0, .75, .25], 'durationMs': 1600}]}
    return dict(id='build-monitor', name='Build monitor', tags=['build', 'status', 'totem'],
                description='A totem with a status face, a turning ring and sparks on every passed build.',
                animations=anims, machine=machine, slots=slots, proxy=proxy)


def job_token():
    MATS['token-shell'] = dict(color=(.62, .5, .36), rough=.5)
    band = slot_mat('job-token', TOKEN)
    p = Part('token')
    p.box('token-shell', (0, .09, 0), (.24, .18, .2), bevel=.035)
    p.box(band, (0, .09, 0), (.246, .05, .206), bevel=.01)
    p.finish()
    return dict(id='job-token', name='Job token', tags=['item', 'token'],
                description='A small token that rides a conveyor track; its band shows the job state.',
                animations=[], traits={'mover': {'speed': .6, 'item': True}},
                slots={'states': [{**states('band', TOKEN), 'materials': ['job-token']}]})


def fx_spark():
    MATS['fx-spark'] = dict(color=(.95, .95, .95), unlit=True)
    p = Part('spark')
    r = .03
    p.hull('fx-spark', [(r, 0, 0), (-r, 0, 0), (0, r * 1.4, 0), (0, -r * 1.4, 0), (0, 0, r * .6), (0, 0, -r * .6)])
    p.finish(smooth_angle=0)
    return dict(id='fx-spark', name='Spark', tags=['effect', 'particle'],
                description='A tiny unlit diamond: the stand-in effect piece, painted with the effect colour at runtime.',
                animations=[], lighting='unlit', traits={'mover': {'speed': 1, 'item': True}},
                slots={'states': [{**states('spark', SPARK), 'materials': ['fx-spark']}]})


BUILDERS = [ci_conveyor, queue_stack, server_rack, deploy_lift, build_monitor, job_token, fx_spark]


def export_asset(data, out):
    """Export the current Blender scene as one object asset into out/<id>/."""
    aid = data['id']; d = out / aid
    if d.exists():
        import shutil; shutil.rmtree(d)
    d.mkdir(parents=True)
    proxy = data.get('proxy')
    objs = list(bpy.context.scene.objects)
    names = [o.name for o in objs]
    assert len(names) == len(set(names)) and not any('.' in n for n in names), ('node names must be unique and unsuffixed', names)
    g = kit.export_gltf(d / f'{aid}.gltf', objs)
    nodes = {n['name']: i for i, n in enumerate(g['nodes'])}
    if proxy is not None:  # the collision proxy stays in nodes[] but leaves the drawn scene
        g['scenes'][0]['nodes'] = [i for i in g['scenes'][0]['nodes'] if i != nodes['proxy']]
        (d / f'{aid}.gltf').write_text(json.dumps(g, indent=1) + '\n')
    visible = [o for o in objs if o.type == 'MESH' and o is not proxy]
    bounds = kit.mesh_bounds(visible)
    # Every slot node / material the manifest names must exist exactly once.
    mats = [m['name'] for m in g.get('materials', [])]
    slots = data.get('slots', {})
    for s in slots.get('states', []):
        for m in s['materials']:
            assert mats.count(m) == 1, (aid, 'states material', m)
    for a in data['animations']:
        assert a['node'] in nodes, (aid, a['node'])
    for kind in ('labels', 'effects', 'spawns', 'stacks', 'toggles'):
        for s in slots.get(kind, []):
            for n in s.get('nodes', [s.get('node', s['id'])]) if kind in ('stacks', 'toggles') else [s['id']]:
                assert n in nodes, (aid, kind, n)
    traits = dict(data.get('traits', {}))
    if data['animations']:
        traits['decorative'] = {'animations': data['animations']}
    if proxy is not None:
        traits['collidable'] = {'node': 'proxy'}
    if data.get('machine'):
        traits['machine'] = data['machine']
    manifest = {'formatVersion': '0.10', 'id': aid, 'version': '0.1.0', 'name': data['name'], 'description': data['description'],
                'category': 'machines', 'tags': data['tags'], 'scene': f'{aid}.gltf', 'license': 'CC-BY-4.0', 'attribution': ATTRIBUTION,
                'bounds': bounds, 'lighting': {'mode': data.get('lighting', 'probe')}, 'traits': traits, 'slots': slots}
    (d / 'object.json').write_text(json.dumps(manifest, indent=1) + '\n')
    report = {'id': aid, 'triangles': kit.triangles(visible), 'proxyTriangles': kit.triangles([proxy]) if proxy else 0,
              'nodes': len(g['nodes']), 'materials': len(mats), 'bounds': bounds, **data.get('notes', {})}
    print('MACHINE', json.dumps(report), flush=True)
    return manifest, report


def build_all(out):
    """Build every asset in a fresh Blender scene (node names repeat across assets)."""
    reports = []
    for builder in BUILDERS:
        kit.reset()
        data = builder()
        reports.append(export_asset(data, out)[1])
    return reports
