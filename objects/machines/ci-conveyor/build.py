# SPDX-License-Identifier: MIT
"""ci-conveyor: a CI pipeline as a conveyor (RFC-0013 machine, draft).

Jobs drop from an intake hopper onto a belt, pass four portal stations (build,
test, package, deploy; each with a lantern lamp and a geared spinner through its
housing) and slide down a chute into the output bin. A failed job is pushed off
behind the deploy station into the reject bin under a red canvas flag. Waiting
jobs stack on a pallet beside the hopper; a ten-pip rail shows progress.

    make machines        (Blender on the bake host)

Writes dist/objects/machines/ci-conveyor/ (object.gltf, object.json).
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kit
from kit import Part, empty, lamp, spin

ID = 'ci-conveyor'
BELT = .80                       # belt top (item base)
X0, X1 = -2.75, 2.55             # belt ends
SX = [-1.35, -.25, .85, 1.95]    # station centres
HX = -2.55                       # hopper centre
RX = 2.3                         # reject branch


def gear(name, c, r=.12, teeth=6):
    """Two geared discs on the housing's front and back faces, one node turning about Y."""
    p = Part(name, c)
    for side in (-1, 1):
        y0, y1 = c[1] + side * .53, c[1] + side * .575
        p.cyl('metal', (c[0], y0, c[2]), (c[0], y1, c[2]), r, seg=12)
        p.cyl('brass', (c[0], y1, c[2]), (c[0], y1 + side * .02, c[2]), .04, seg=8)
        for k in range(teeth):
            a = 2 * math.pi * k / teeth
            p.box('brass', (c[0] + (r + .02) * math.cos(a), (y0 + y1) / 2, c[2] + (r + .02) * math.sin(a)), (.05, .04, .04), rot=(0, -a, 0))
        p.box('ivory', (c[0] + r * .5, y1 + side * .004, c[2]), (r * .8, .008, .022))   # the marker spoke shows the turn
    return p.finish(smooth_angle=35)


def crate(p, c, size, mat='timber'):
    w, h, d = size
    p.box(mat, c, size, bevel=.014, grain='z')
    for dz in (-h * .3, h * .3):
        p.box('metal-black', (c[0], c[1], c[2] + dz), (w + .01, d + .01, .025))


def main():
    kit.reset()
    kit.MATS['pip'] = dict(color=kit.MINT, rough=.3, emit=1.2)
    body = Part('body')
    # Plinth and belt bed
    body.box('stone', ((-4.1 + 3.75) / 2, .375, .09), (7.85, 2.05, .18), bevel=.03)
    L, mx = X1 - X0, (X0 + X1) / 2
    body.box('metal', (mx, 0, .70), (L, .62, .16), bevel=.02, grain='x')
    body.box('rubber', (mx, 0, .79), (L, .54, .02))
    for x in (X0, X1):
        body.cyl('metal-black', (x, -.31, .71), (x, .31, .71), .09, seg=16)
    body.box('timber', (mx, -.34, .84), (L, .05, .16), bevel=.01, grain='x')
    # the back rail opens where failed jobs are pushed off
    gap0, gap1 = RX - .2, RX + .2
    body.box('timber', ((X0 + gap0) / 2, .34, .84), (gap0 - X0, .05, .16), bevel=.01, grain='x')
    body.box('timber', ((gap1 + X1) / 2, .34, .84), (X1 - gap1, .05, .16), bevel=.01, grain='x')
    for x in (-2.45, -.8, .3, 1.4, 2.35):
        for y in (-.24, .24):
            body.box('metal-black', (x, y, .40), (.07, .07, .44))
    for y in (-.315, .315):
        body.box('strip-cyan', (mx, y, .655), (L - .3, .01, .022))
    # progress rail: a dark channel on the front rail; the pips are a stack
    body.box('panel', (-.275, -.368, .845), (4.6, .006, .07))
    # Intake hopper
    body.hull('metal', [(HX + sx * a, sy * a, z) for a, z in ((.22, 1.16), (.5, 1.95)) for sx in (-1, 1) for sy in (-1, 1)])
    body.quad('panel', (HX, 0, 1.952), .9, .9, rot=(-math.pi / 2, 0, 0))
    for sy in (-1, 1):
        body.box('timber', (HX, sy * .5, 1.97), (1.08, .07, .07), grain='x')
        body.box('timber', (HX + sy * .5, 0, 1.97), (.07, 1.08, .07), grain='y')
    body.box('metal', (HX, 0, 1.12), (.36, .36, .12), bevel=.015)
    for sx in (-1, 1):
        for sy in (-1, 1):
            body.box('timber', (HX + sx * .43, sy * .43, .89), (.09, .09, 1.42))
        body.box('timber', (HX + sx * .43, 0, 1.55), (.07, .86, .07), grain='y')
        body.box('timber', (HX, sx * .43, 1.55), (.86, .07, .07), grain='x')
    # Title board behind the hopper
    for sx in (-1, 1):
        body.box('metal-black', (HX + sx * .55, .58, 1.36), (.06, .06, 2.36))
    body.box('timber', (HX, .58, 2.35), (1.34, .06, .44), bevel=.012, grain='x')
    body.box('ivory', (HX, .58, 2.585), (1.4, .08, .03))
    title = Part('label-title', (HX, .548, 2.35)); kit.MATS['label-title'] = dict(kit.MATS['panel'])
    title.quad('label-title', (HX, .548, 2.35), 1.18, .3); title.finish()
    # Stations
    lamps, spinners = [], []
    for i, x in enumerate(SX, 1):
        for sx in (-1, 1):
            for sy in (-1, 1):
                body.box('timber', (x + sx * .28, sy * .46, .90), (.12, .12, 1.44))
        for sy in (-1, 1):
            body.box('timber', (x, sy * .46, 1.47), (.68, .08, .09), grain='x')
        body.box('metal', (x, 0, 1.76), (.74, 1.06, .34), bevel=.04, grain='x')
        body.box('metal-black', (x, 0, 1.945), (.6, .9, .03), bevel=.01)
        body.cyl('brass', (x, 0, 1.94), (x, 0, 1.965), .155, seg=14)
        body.cyl('metal-black', (x, 0, 2.225), (x, 0, 2.265), .155, seg=14)
        body.cyl('brass', (x, 0, 2.265), (x, 0, 2.31), .025, seg=8)
        for k in range(i):  # numbered ticks, front and back
            for side in (-1, 1):
                body.box('ivory', (x + .22 + k * .04 - (i - 1) * .02, side * .532, 1.75), (.022, .006, .12))
        if i == 1:    # build: a press
            body.box('metal', (x, 0, 1.38), (.36, .36, .18), bevel=.02)
            body.cyl('brass', (x, 0, 1.47), (x, 0, 1.6), .03, seg=10)
        elif i == 2:  # test: a scanning arch
            for sy in (-1, 1):
                body.box('ivory', (x, sy * .3, 1.01), (.08, .04, .42))
            body.box('ivory', (x, 0, 1.24), (.08, .64, .04))
            body.box('strip-cyan', (x, 0, 1.214), (.05, .56, .012))
        elif i == 3:  # package: wrapping rollers
            for sy in (-1, 1):
                body.cyl('timber-dark', (x, sy * .245, .81), (x, sy * .245, 1.13), .05, seg=12)
                body.cyl('brass', (x, sy * .245, 1.13), (x, sy * .245, 1.6), .015, seg=8)
        else:         # deploy: a stamp nozzle with an amber ring
            body.cyl('metal', (x, 0, 1.6), (x, 0, 1.3), .14, r2=.07, seg=16)
            body.torus('strip-amber', (x, 0, 1.32), .08, .012, seg=20, sseg=6)
        lamps.append(lamp(f'stage-{i}-lamp', 'lamp', (x, 0, 1.965), r=.13, depth=.26, axis='z', seg=14, dome=False))
        spinners.append(gear(f'stage-{i}-spinner', (x, 0, 1.75)))
    # Output chute and bin
    a = math.atan2(.28, .45)
    body.box('metal', (2.825, 0, .625), (.55, .4, .03), rot=(0, a, 0))
    for sy in (-1, 1):
        body.box('timber', (2.825, sy * .215, .67), (.55, .03, .14), rot=(0, a, 0), grain='x')
    for c, s in [((3.3, 0, .2), (.56, .66, .04)), ((3.04, 0, .35), (.04, .66, .3)), ((3.56, 0, .38), (.04, .66, .36)),
                 ((3.3, -.31, .37), (.56, .04, .34)), ((3.3, .31, .37), (.56, .04, .34))]:
        body.box('timber', c, s)
    body.box('strip-mint', (3.3, -.333, .45), (.4, .006, .03))
    # Reject chute and bin behind the deploy station
    b = math.atan2(.34, .62)
    body.box('metal', (RX, .67, .595), (.36, .72, .03), rot=(-b, 0, 0))
    for sx in (-1, 1):
        body.box('timber', (RX + sx * .195, .67, .64), (.03, .72, .13), rot=(-b, 0, 0), grain='y')
    for c, s in [((RX, 1.13, .2), (.46, .42, .04)), ((RX - .21, 1.13, .34), (.04, .42, .28)), ((RX + .21, 1.13, .34), (.04, .42, .28)),
                 ((RX, .94, .3), (.46, .04, .2)), ((RX, 1.32, .34), (.46, .04, .28))]:
        body.box('timber-dark', c, s)
    body.box('metal-black', (RX + .27, 1.32, .8), (.035, .035, 1.24))
    body.box('canvas-red', (RX + .43, 1.32, 1.28), (.3, .012, .2))
    # Waiting pallet beside the hopper
    body.box('timber-dark', (-3.6, 0, .21), (.92, 1.0, .06), bevel=.01, grain='x')
    body.finish()

    # Stacks: a waiting crate (3 x 2 x 3 on the pallet) and a progress pip (10 along the rail)
    wc = Part('waiting-crate', (-3.9, .3, .37)); crate(wc, (-3.9, .3, .37), (.26, .26, .26)); wc.finish()
    pip = Part('progress-pip', (-2.3, -.373, .845)); pip.box('pip', (-2.3, -.373, .845), (.3, .012, .045), bevel=.004); pip.finish()

    # Tracks (asset-space polylines; nodes for runtimes that read the glTF)
    belt = [(HX, 0, BELT), *[(x, 0, BELT) for x in SX], (RX, 0, BELT), (X1, 0, BELT), (2.75, 0, .70), (3.05, 0, .50), (3.3, 0, .24)]
    reject = [(RX, 0, BELT), (RX, .36, BELT), (RX, .98, .46), (RX, 1.13, .24)]
    tracks = {}
    for tid, pts in (('track', belt), ('reject', reject)):
        root = empty(tid, pts[0])
        for k, pt in enumerate(pts):
            empty(f'{tid}-p{k:02d}', [pt[j] - pts[0][j] for j in range(3)], parent=root)
        tracks[tid] = pts
    empty('item-spawn', belt[0], rot=(0, 0, math.pi / 2))      # items face +X along the belt
    empty('reject-in', reject[0], rot=(0, 0, math.pi))         # pushed off toward the back
    empty('success-fx', (3.3, 0, 1.05))
    empty('fail-fx', (RX, 1.13, 1.05))
    proxy = kit.proxy_boxes([((-.175, .375, .09), (7.85, 2.05, .18)), ((-.1, 0, .5), (5.4, .8, 1.0)), ((HX, 0, 1.0), (1.0, 1.0, 2.0)),
                             *[((x, 0, 1.0), (.66, 1.02, 2.0)) for x in SX], ((3.3, 0, .35), (.6, .7, .7)),
                             ((RX, 1.0, .35), (.5, .8, .7)), ((-3.6, 0, .45), (.92, 1.0, .9)), ((HX, .58, 1.3), (1.34, .1, 2.6))])
    shift = kit.recentre(exclude=proxy)

    def g(p):
        return kit.b2g([p[0] + shift.x, p[1] + shift.y, p[2] + shift.z])

    statuses = ['idle', 'running', 'ok', 'fail']
    inputs = [
        {'id': 'stage', 'type': 'enum', 'values': statuses, 'default': 'idle', 'repeat': 4, 'label': 'Stage status',
         'explain': 'Stations 1-4 (build, test, package, deploy): the lamp shows the stage state and its gears turn while it runs.'},
        {'id': 'jobStarted', 'type': 'event', 'label': 'Job started', 'explain': 'Each started job drops a crate from the hopper onto the belt.'},
        {'id': 'jobPassed', 'type': 'event', 'label': 'Job passed', 'explain': 'A passed job lands in the output bin with a burst.'},
        {'id': 'jobFailed', 'type': 'event', 'label': 'Job failed', 'explain': 'A failed job is pushed into the reject bin under the red flag.'},
        {'id': 'progress', 'type': 'number', 'min': 0, 'max': 1, 'default': 0, 'label': 'Progress',
         'explain': 'The pip rail along the belt: one pip per tenth of the pipeline.'},
        {'id': 'queued', 'type': 'int', 'min': 0, 'max': 18, 'default': 0, 'label': 'Queued jobs',
         'explain': 'Crates waiting on the pallet beside the hopper, one per queued job.'},
        {'id': 'pipeline', 'type': 'text', 'maxLength': 24, 'label': 'Pipeline name', 'explain': 'The board above the hopper.'},
    ]
    drives = []
    for i in range(1, 5):
        drives += [{'input': f'stage.{i}', 'target': f'state:stage-{i}-lamp'},
                   {'input': f'stage.{i}', 'target': f'animation:stage-{i}-spinner', 'map': {'cases': [{'equals': 'running', 'to': 1}], 'else': 0}}]
    drives += [
        {'input': 'jobStarted', 'target': 'spawn:item-spawn'},
        {'input': 'jobPassed', 'target': 'effect:success-fx'},
        {'input': 'jobFailed', 'target': 'spawn:reject-in'},
        {'input': 'jobFailed', 'target': 'effect:fail-fx'},
        {'input': 'progress', 'target': 'count:progress', 'map': {'scale': {'from': [0, 1], 'to': [0, 10]}, 'clamp': True, 'round': 'floor'}},
        {'input': 'queued', 'target': 'count:waiting'},
        {'input': 'pipeline', 'target': 'label:label-title'},
    ]
    anims = [spin(o, (0, 1, 0), 2.4, phase=k * .17) for k, o in enumerate(spinners)]
    m = kit.base_manifest(ID, 'CI conveyor', 'A CI pipeline as a conveyor: jobs drop from a hopper, pass four lit stations (build, test, package, deploy) and land in the output or the reject bin.',
                          ['ci', 'pipeline', 'jobs', 'build'])
    item_rot = {'pose@': 'item-spawn'}
    m['traits'] = {
        'decorative': {'animations': anims},
        'collidable': {'node': 'proxy'},
        'movable': {'surfaces': ['floor'], 'upright': True},
        'machine': {
            'primary': 'stage', 'inputs': inputs, 'drives': drives,
            'recipes': [{'name': 'Pipeline summary JSON', 'fields': {
                'stage.1': '/stages/0/status', 'stage.2': '/stages/1/status', 'stage.3': '/stages/2/status', 'stage.4': '/stages/3/status',
                'jobStarted': '/counters/started', 'jobPassed': '/counters/passed', 'jobFailed': '/counters/failed',
                'progress': '/progress', 'queued': {'countWhere': {'array': '/jobs', 'pointer': '/status', 'equals': 'queued'}},
                'pipeline': '/name'}}]},
    }
    m['slots'] = {
        'states': [kit.states_slot(f'stage-{i}-lamp') for i in range(1, 5)],
        'labels': [{'id': 'label-title', 'pose': {'pose@': 'label-title'}, 'size': [1.18, .3], 'maxChars': 24, 'font': 'mono'}],
        'tracks': [
            {'id': 'track', 'speed': .6, 'points': [{'position': g(p), 'type': 'curve' if k in (7, 8) else 'line'} for k, p in enumerate(tracks['track'])],
             'items': {'assets': ['job-token'], 'max': 24, 'spacing': .45, 'overflow': 'drop-oldest'}, 'sink': True},
            {'id': 'reject', 'speed': .8, 'points': [{'position': g(p), 'type': 'line'} for p in tracks['reject']],
             'items': {'assets': ['job-token'], 'max': 8, 'spacing': .4, 'overflow': 'drop-oldest'}, 'sink': True}],
        'spawns': [{'id': 'item-spawn', 'pose': item_rot, 'track': 'track', 'items': ['job-token'], 'maxRate': 2},
                   {'id': 'reject-in', 'pose': {'pose@': 'reject-in'}, 'track': 'reject', 'items': ['job-token'], 'maxRate': 2}],
        'effects': [{'id': 'success-fx', 'pose': {'pose@': 'success-fx'}, 'kind': 'burst', 'colour': list(kit.MINT), 'durationMs': 1500},
                    {'id': 'fail-fx', 'pose': {'pose@': 'fail-fx'}, 'kind': 'flash', 'colour': list(kit.RED), 'durationMs': 900}],
        'stacks': [{'id': 'waiting', 'node': 'waiting-crate', 'cap': 18, 'layout': {'grid': [3, 2, 3], 'spacing': [.3, .28, .3], 'fill': 'xzy'}},
                   {'id': 'progress', 'node': 'progress-pip', 'cap': 10, 'layout': {'grid': [10, 1, 1], 'spacing': [.45, 0, 0], 'fill': 'xzy'}}],
    }
    kit.export(kit.out_dir(ID), m, proxy=proxy)


main()
