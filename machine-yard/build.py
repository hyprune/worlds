# SPDX-License-Identifier: MIT
"""Machine Yard: a compact test world for live machines (world format 0.8).

A paved terrace yard in the Lumen Reach language: pale stone, warm timber, dark metal,
cyan/mint/amber practical light. Two timber roof wings on columns frame an open court;
the north parapet and the east colonnade look over a valley to the mountains. Five machine
bays stand on low plinths around a paved walking loop, each with at least 3 m clear around
it and 4 m in front. The machines are placed object assets (machines.py), so the prototype
in core can drive them from data through machines.bindings.json.

    make machine-yard      (Blender through tools/remote-blender.sh, like the other worlds)

Stages: build (objects, scene, bake, export, stills), objects (assets only), stills (from the
saved .blend). Output: dist/com.hyprune.machine-yard/, stills in artifacts/machine-yard/.
Coordinates in this file are glTF/world space: metres, +Y up, north is -Z.
"""
import argparse, json, math, os, shutil, subprocess, sys, time
if os.environ.get('HYPRUNE_REMOTE_BLENDER') != '1':
    raise SystemExit('Use make machine-yard (tools/remote-blender.sh); never local Blender on the laptop')
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit, machines
from kit import Part, bl, MATS, CYAN, AMBER

ROOT = HERE.parent
OUT = ROOT / 'dist/com.hyprune.machine-yard'
ART = ROOT / 'artifacts/machine-yard'
WORLD_ID = 'com.hyprune.machine-yard'
VERSION = '0.1.0'

# Light: late-afternoon sun from the south-west; the core atmosphere uses the same values.
SUN_DIR = Vector((-.55, .57, .61)).normalized()  # towards the sun (world space)
SUN_COLOUR = (1.0, .85, .65)
SKY = {'zenith': (.16, .30, .62), 'horizon': (.55, .64, .74), 'ground': (.07, .07, .065)}

Q_EAST = [0, .70711, 0, .70711]    # asset front (+Z) turned to +X
Q_WEST = [0, -.70711, 0, .70711]   # asset front turned to -X
INSTANCES = [  # id, asset, position (plinth top), rotation, plinth centre (x, z) and size (x, z)
    ('ci-1', 'ci-conveyor', (0, .15, -7.0), [0, 0, 0, 1], (0, -7.0), (7.0, 2.8)),
    ('queue-1', 'queue-stack', (-10.5, .15, -3.5), Q_EAST, (-10.5, -3.5), (2.0, 3.6)),
    ('rack-1', 'server-rack', (-10.5, .15, 4.5), Q_EAST, (-10.5, 4.5), (2.0, 2.0)),
    ('deploy-1', 'deploy-lift', (10.5, .15, -3.0), Q_WEST, (10.5, -3.0), (3.2, 3.2)),
    ('build-1', 'build-monitor', (0, .15, 1.0), [0, 0, 0, 1], (0, 1.0), (2.2, 2.2)),
]
ITEM_ASSETS = ['job-token', 'fx-spark']
SPAWN = (0, 0, 8.6)
SCREEN = {'id': 'yard-screen', 'position': (11.25, 2.9, 10.97), 'size': (4.8, 2.7)}
COLUMNS = [(x, z) for x in (-7.5, 7.5) for z in (-10.4, .4, 10.4)]
PIERS = [-11.2, -5.6, 0, 5.6, 11.2]
LOOP = {'north': -3.5, 'south': 6.0, 'west': -6.0, 'east': 6.0, 'width': 2.4}
ROUTE = [  # walking loop nodes (feet), label for waypoints
    ('entrance', (0, 0, 8.6), 'Entrance'), ('monitor-view', (0, 0, 6.0), 'Build monitor'),
    ('loop-sw', (-6, 0, 6.0), None), ('rack-view', (-6, 0, 4.5), 'Server rack'),
    ('queue-view', (-6, 0, -3.5), 'Queue stack'), ('conveyor-view', (0, 0, -3.5), 'CI conveyor'),
    ('lift-view', (6, 0, -3.0), 'Deploy lift'), ('loop-se', (6, 0, 6.0), None)]
GROUPS = {}       # name -> Part, then the finished object
COLLISION = []    # (min, max) world boxes
BLOCKS = []       # navigation blockers (min, max) in x/z
LIGHTMAPS = {}
LIGHTMAP_SIZE = {'ground': 4096, 'walls': 4096, 'roof': 2048, 'props': 2048}
UNBAKED = {'vista', 'terrace'}

MATS.update({
    'meadow': dict(color=(.17, .23, .12), rough=.95),
    'forest': dict(color=(.10, .15, .09), rough=.95),
    'hill-rock': dict(color=(.75, .72, .66), rough=.9, tex='rock', tile=8),
    'ridge-mid': dict(color=(.30, .39, .47), unlit=True),
    'ridge-far': dict(color=(.43, .53, .63), unlit=True),
    'ridge-snow': dict(color=(.70, .77, .86), unlit=True),
})


def log(s):
    print('MACHINE-YARD | ' + s, flush=True)


def part(group):
    if group not in GROUPS:
        GROUPS[group] = Part('Visual-' + group, prefix=group)
    return GROUPS[group]


def solid(group, mat, lo, hi, bevel=0.0, collide=True, block=True):
    """An axis-aligned box from world min/max corners, optionally collision."""
    c = [(a + b) / 2 for a, b in zip(lo, hi)]; s = [b - a for a, b in zip(lo, hi)]
    part(group).box(mat, c, s, bevel=bevel)
    if collide:
        COLLISION.append((list(lo), list(hi)))
        if block and hi[1] > .2 and lo[1] < 1.8:
            BLOCKS.append(((lo[0], lo[2]), (hi[0], hi[2])))


# ---------------------------------------------------------------------------- scene

def ground():
    # The yard floor: only its top face is drawn (the slab's sides and bottom are never seen).
    part('ground').quad('stone-warm', (0, 0, 0), 31.0, 23.0, normal=(0, 1, 0))
    COLLISION.append(([-15.5, -.6, -11.5], [15.5, 0, 11.5]))
    w = LOOP['width'] / 2; y = .006
    bands = [((LOOP['west'] - w, LOOP['north'] - w), (LOOP['east'] + w, LOOP['north'] + w)),
             ((LOOP['west'] - w, LOOP['south'] - w), (LOOP['east'] + w, LOOP['south'] + w)),
             ((LOOP['west'] - w, LOOP['north'] + w), (LOOP['west'] + w, LOOP['south'] - w)),
             ((LOOP['east'] - w, LOOP['north'] + w), (LOOP['east'] + w, LOOP['south'] - w)),
             ((-w, LOOP['south'] + w), (w, 10.95))]
    for (x0, z0), (x1, z1) in bands:
        part('ground').box('paving', ((x0 + x1) / 2, y - .03, (z0 + z1) / 2), (x1 - x0, .06, z1 - z0))
    # Machine plinths: 0.15 m stone, a dark band and a cyan base strip.
    for _, _, _, _, (cx, cz), (sx, sz) in INSTANCES:
        solid('ground', 'stone', (cx - sx / 2, -.02, cz - sz / 2), (cx + sx / 2, .15, cz + sz / 2), bevel=.03, block=True)
        part('ground').box('metal-black', (cx, .045, cz), (sx + .02, .05, sz + .02))
        part('ground').box('strip-cyan', (cx, .085, cz), (sx + .016, .012, sz + .016))


def walls():
    H = 5.6
    # West wall with a timber dado, sconces and a cyan strip under the roof.
    solid('walls', 'stone', (-15.5, 0, -11.5), (-15.0, H, 11.5))
    part('walls').box('timber', (-14.97, .75, 0), (.06, 1.3, 22.0), bevel=.01)
    part('walls').box('metal-black', (-14.96, 1.43, 0), (.08, .06, 22.0))
    for z in (-8.4, -2.8, 2.8, 8.4):
        part('walls').box('metal-black', (-14.93, 3.2, z), (.12, .5, .22), bevel=.02)
        part('walls').box('sconce', (-14.86, 3.2, z), (.02, .36, .1))
    # South wall: entrance portal with closed timber doors, the screen wall to the east.
    solid('walls', 'stone', (-15.0, 0, 11.0), (-1.7, H, 11.5))
    solid('walls', 'stone', (1.7, 0, 11.0), (15.0, H, 11.5))
    solid('walls', 'stone', (-1.7, 4.3, 11.0), (1.7, H, 11.5), collide=False)
    solid('walls', 'timber-dark', (-1.6, 0, 11.3), (1.6, 4.3, 11.42), collide=True)
    part('walls').box('metal-black', (0, 2.15, 11.25), (.04, 4.3, .1))
    for x in (-1.68, 1.68):
        part('walls').box('metal-black', (x, 2.2, 11.0), (.16, 4.4, .1), bevel=.01)
    part('walls').box('metal-black', (0, 4.38, 11.0), (3.52, .16, .1), bevel=.01)
    for x in (-.25, .25):
        part('walls').box('brass', (x, 1.1, 11.27), (.05, .5, .04), bevel=.01)
    part('walls').box('metal-black', (0, 4.75, 10.94), (.9, .2, .12), bevel=.02)
    part('walls').box('sconce', (0, 4.75, 10.875), (.7, .06, .01))
    for x in (-8.4, -4.2, 4.2):
        part('walls').box('metal-black', (x, 3.2, 10.93), (.22, .5, .12), bevel=.02)
        part('walls').box('sconce', (x, 3.2, 10.865), (.1, .36, .01))
    sx, sy, sz = SCREEN['position']; w, h = SCREEN['size']
    for dx, dy, size in [(0, h / 2 + .08, (w + .32, .16, .06)), (0, -h / 2 - .08, (w + .32, .16, .06)),
                         (w / 2 + .08, 0, (.16, h, .06)), (-w / 2 - .08, 0, (.16, h, .06))]:
        part('walls').box('timber', (sx + dx, sy + dy, 10.97), size, bevel=.01)
    part('walls').box('panel', (sx, sy, 10.99), (w, h, .02))
    # North parapet and east balustrade with timber coping; east piers carry the roof.
    solid('walls', 'stone', (-15.5, 0, -11.5), (15.5, 1.0, -11.0))
    COLLISION.append(([-15.5, 1.0, -11.5], [15.5, 1.6, -11.0]))
    part('walls').box('timber', (0, 1.04, -11.25), (31.0, .08, .62), bevel=.01)
    solid('walls', 'stone', (15.0, 0, -11.0), (15.5, 1.0, 11.0))
    COLLISION.append(([15.0, 1.0, -11.0], [15.5, 1.6, 11.0]))
    part('walls').box('timber', (15.25, 1.04, 0), (.62, .08, 22.0), bevel=.01)
    for z in PIERS:
        solid('walls', 'stone', (14.95, 0, z - .35), (15.55, H, z + .35), bevel=.03)
    part('walls').box('strip-cyan', (-14.93, 5.05, 0), (.02, .03, 22.0))
    # Timber columns on stone bases.
    for x, z in COLUMNS:
        solid('walls', 'stone', (x - .32, 0, z - .32), (x + .32, .5, z + .32), bevel=.03)
        solid('walls', 'timber', (x - .2, .5, z - .2), (x + .2, 5.3, z + .2), bevel=.02)
        part('walls').box('metal-black', (x, .53, z), (.46, .06, .46), bevel=.01)


def roof():
    for side in (-1, 1):
        x0, x1 = (-15.5, -7.1) if side < 0 else (7.1, 15.5)
        cx = (x0 + x1) / 2
        solid('roof', 'stone', (x0, 5.6, -11.5), (x1, 5.8, 11.5), block=False)
        part('roof').box('timber', (cx, 5.57, 0), (x1 - x0, .06, 23.0))
        for z in (-10.4, .4, 10.4):
            part('roof').box('timber', (cx, 5.3, z), (x1 - x0 - .1, .5, .3), bevel=.02)
        z = -11.0
        while z < 11.1:
            part('roof').box('timber-dark', (cx, 5.42, z), (x1 - x0 - .2, .2, .1), bevel=.01)
            z += 1.1
        bays = [(-10.5, -3.5), (-10.5, 4.5)] if side < 0 else [(10.5, -3.0), (12.5, 5.5)]
        for bx, bz in bays:
            for dx in (-.45, .45):
                part('roof').box('metal-black', (bx + dx, 5.28, bz), (.16, .08, 1.9), bevel=.01)
                part('roof').box('sconce', (bx + dx, 5.235, bz), (.1, .012, 1.8))
        edge = x1 if side < 0 else x0
        part('roof').box('metal-black', (edge, 5.55, 0), (.14, .5, 23.0), bevel=.02)
        part('roof').box('strip-cyan', (edge - side * .08, 5.33, 0), (.02, .03, 23.0))


def props():
    def bench(x, z, yaw):
        p = part('props')
        c, s = math.cos(yaw), math.sin(yaw)
        def at(dx, dz):
            return x + dx * c + dz * s, z - dx * s + dz * c
        for dx in (-.85, .85):
            bx, bz = at(dx, 0)
            p.box('metal-black', (bx, .22, bz), (.06, .44, .46) if abs(s) < .5 else (.46, .44, .06), bevel=.01)
        for k in range(4):
            sx_, sz_ = at(0, -.18 + k * .12)
            p.box('timber', (sx_, .46, sz_), (1.9, .04, .1) if abs(s) < .5 else (.1, .04, 1.9), bevel=.01)
        lo = [x - 1.0, 0, z - .3] if abs(s) < .5 else [x - .3, 0, z - 1.0]
        hi = [x + 1.0, .5, z + .3] if abs(s) < .5 else [x + .3, .5, z + 1.0]
        COLLISION.append((lo, hi)); BLOCKS.append(((lo[0], lo[2]), (hi[0], hi[2])))

    def planter(x, z, size=1.3):
        solid('props', 'stone', (x - size / 2, 0, z - size / 2), (x + size / 2, .6, z + size / 2), bevel=.04)
        part('props').box('soil', (x, .58, z), (size - .16, .04, size - .16))
        part('props').cyl('timber-dark', (x, .58, z), (x, 2.0, z), .08, seg=10)
        for dx, dy, dz, r in [(-.25, 2.25, 0, .55), (.3, 2.5, .15, .5), (0, 2.85, -.1, .42)]:
            part('props').sphere('leaf' if dy < 2.6 else 'leaf-light', (x + dx, dy, z + dz), r, sub=2)

    def bollard(x, z):
        p = part('props')
        p.cyl('metal-black', (x, 0, z), (x, .85, z), .09, seg=16)
        p.cyl('strip-cyan', (x, .7, z), (x, .76, z), .093, seg=16)
        p.cyl('brass', (x, .85, z), (x, .9, z), .1, seg=16, r2=.08)
        COLLISION.append(([x - .1, 0, z - .1], [x + .1, .9, z + .1])); BLOCKS.append(((x - .1, z - .1), (x + .1, z + .1)))

    bench(13.6, 3.5, math.pi / 2); bench(13.6, -8.5, math.pi / 2)
    for x, z in [(-4.2, 9.6), (4.2, 9.6), (-6.6, -9.2), (6.6, -9.2)]:
        planter(x, z)
    for x, z in [(-1.7, 7.6), (1.7, 7.6), (-7.7, 7.7), (7.7, 7.7), (-7.7, -5.2), (7.7, -5.2)]:
        bollard(x, z)


def ridge(p, mat, radius, base, height, seed, a0=0, a1=2 * math.pi, steps=160):
    rng = np.random.default_rng(seed)
    waves = [(rng.uniform(2, 30), rng.uniform(0, 6.3), rng.uniform(.2, 1) / (1 + k)) for k in range(7)]
    total = sum(w for _, _, w in waves)
    b = bmesh.new(); bottom, top = [], []
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        ridged = 1 - abs(sum(w * math.sin(f * a + ph) for f, ph, w in waves) / total)
        h = height * (.3 + .7 * ridged ** 1.6)
        r = radius * (1 + .04 * math.sin(3 * a + seed))
        bottom.append(b.verts.new(bl((r * math.sin(a), base, -r * math.cos(a)))))
        top.append(b.verts.new(bl((r * math.sin(a) * .97, base + h, -r * math.cos(a) * .97))))
    for i in range(steps):
        b.faces.new([bottom[i], bottom[i + 1], top[i + 1], top[i]])
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    for f in b.faces:  # face the yard
        c = f.calc_center_median()
        if f.normal.dot(-c) < 0:
            f.normal_flip()
    p._take(b, mat)


def vista():
    t = part('terrace')
    # The terrace falls to the valley on the north and east; the hillside continues south and west.
    t.box('stone', (0, -4.8, -11.25), (31.0, 8.4, .5))
    t.box('stone', (15.25, -4.8, 0), (.5, 8.4, 22.0))
    t.box('hill-rock', (-28, -4.5, 6), (25.0, 9.0, 36.0))
    t.box('hill-rock', (0, -4.5, 24.5), (31.0, 9.0, 26.0))
    t.box('hill-rock', (28, -4.5, 24.5), (25.0, 9.0, 26.0))
    rng = np.random.default_rng(7)
    for i in range(14):
        a = rng.uniform(-.6, 1.9); r = rng.uniform(17, 30)
        t.sphere('hill-rock', (r * math.sin(a), -9 + rng.uniform(0, 2), -r * math.cos(a) * .9), rng.uniform(1.5, 4), sub=1)
    v = part('vista')
    v.box('meadow', (0, -9.5, 0), (2000, 1.0, 2000))
    ridge(v, 'forest', 300, -9.5, 45, 3, a0=-1.3, a1=2.7, steps=220)
    ridge(v, 'ridge-mid', 620, -9.5, 140, 5, steps=260)
    ridge(v, 'ridge-far', 1000, -9.5, 260, 8, steps=260)
    ridge(v, 'ridge-snow', 1500, -9.5, 520, 11, a0=-1.0, a1=2.4, steps=200)


def atmosphere_blender():
    s = bpy.context.scene
    s.world = bpy.data.worlds.new('Machine Yard sky'); s.world.use_nodes = True; nt = s.world.node_tree
    bg = nt.nodes['Background']; bg.inputs[1].default_value = 1.0
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB'); r = ramp.color_ramp
    r.elements[0].position = .45; r.elements[0].color = (*SKY['ground'], 1)
    r.elements[1].position = 1.0; r.elements[1].color = (*SKY['zenith'], 1)
    e = r.elements.new(.5); e.color = (*SKY['horizon'], 1)
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -1; mr.inputs['From Max'].default_value = 1
    nt.links.new(sep.outputs['Z'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    d = bpy.data.lights.new('Sun', 'SUN'); d.energy = 3.2; d.color = SUN_COLOUR; d.angle = math.radians(1.2)
    o = bpy.data.objects.new('Sun', d); s.collection.objects.link(o)
    o.rotation_euler = (-bl(SUN_DIR)).to_track_quat('-Z', 'Y').to_euler()
    # Warm pools under the roof wings over the bays (baked; the fixtures above are the visible source).
    for x, z in [(-10.5, -3.5), (-10.5, 4.5), (10.5, -3.0), (12.5, 5.5)]:
        a = bpy.data.lights.new('Bay pool', 'AREA'); a.energy = 900; a.color = (1, .74, .48); a.shape = 'RECTANGLE'; a.size = 1.9; a.size_y = 2.4
        lo = bpy.data.objects.new('Bay pool', a); s.collection.objects.link(lo); lo.location = bl((x, 5.2, z))


def render_settings(samples):
    s = bpy.context.scene
    s.render.engine = 'CYCLES'; s.cycles.samples = samples; s.cycles.use_denoising = True
    s.cycles.max_bounces = 6; s.cycles.diffuse_bounces = 4
    prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == 'OPTIX'
    s.cycles.device = 'GPU'
    s.view_settings.view_transform = 'AgX'; s.view_settings.look = 'AgX - Medium High Contrast'
    s.render.resolution_x, s.render.resolution_y = 1920, 1080
    s.render.image_settings.file_format = 'PNG'; s.render.image_settings.color_mode = 'RGB'
    s.render.use_stamp_filename = False; s.render.use_stamp_hostname = False


def import_machines():
    """Placed instances of the built assets, for the bake (occluders) and the stills."""
    roots = []
    for oid, asset, pos, q, _, _ in INSTANCES:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(OUT / 'objects' / asset / f'{asset}.gltf'))
        new = [o for o in bpy.data.objects if o not in before]
        holder = bpy.data.objects.new('Instance-' + oid, None); bpy.context.scene.collection.objects.link(holder)
        for o in new:
            if o.name.startswith('proxy'):
                o.hide_render = True; o.hide_viewport = True
            if o.parent is None:
                o.parent = holder
        holder.location = bl(pos); holder.rotation_euler = (0, 0, 2 * math.atan2(q[1], q[3]))
        holder['machine'] = True
        roots.append(holder)
    bpy.context.view_layer.update()
    return roots


def machine_emission(roots, on):
    for h in roots:
        for o in h.children_recursive:
            for slot in getattr(o, 'material_slots', []):
                m = slot.material
                if not m or not m.use_nodes:
                    continue
                p = m.node_tree.nodes.get('Principled BSDF')
                if p:
                    if 'yard_emit' not in m:
                        m['yard_emit'] = p.inputs['Emission Strength'].default_value
                    p.inputs['Emission Strength'].default_value = m['yard_emit'] if on else 0


DEMO_STATES = {  # review stills only: a plausible running moment (the package rests in the first palette state)
    'ci-1': {'stage_1_lamp': 'ok', 'stage_2_lamp': 'ok', 'stage_3_lamp': 'running', 'stage_4_lamp': 'idle'},
    'queue-1': {'age_lamp': 'warn'},
    'rack-1': {**{f'unit_{n}_light': 'ok' for n in range(1, 9)}, 'unit_3_light': 'warn', 'unit_6_light': 'fail'},
    'deploy-1': {'phase_lamp_1': 'done', 'phase_lamp_2': 'done', 'phase_lamp_3': 'active', 'beacon': 'active'},
    'build-1': {'face': 'running'},
}


def demo_population(roots):
    """Paint review states and add the runtime's copies (tokens, crates) for the stills."""
    def base(o):
        return o.name.split('.')[0]
    palettes = {}
    for _, asset, *_ in INSTANCES:
        for st in json.loads((OUT / 'objects' / asset / 'object.json').read_text())['slots'].get('states', []):
            palettes[st['id']] = {e['id']: e for e in st['palette']}
    for h in roots:
        oid = h.name.removeprefix('Instance-'); kids = {base(o): o for o in h.children_recursive}
        for slot, state in DEMO_STATES.get(oid, {}).items():
            e = palettes[slot][state]
            for ms in kids[slot].material_slots:
                m = ms.material.copy(); ms.material = m; p = m.node_tree.nodes.get('Principled BSDF')
                p.inputs['Base Color'].default_value = (*e['colour'], 1)
                p.inputs['Emission Color'].default_value = (*e['colour'], 1); p.inputs['Emission Strength'].default_value = e['emission']
        def copies(node, offsets):
            src = kids[node]
            for d in offsets:
                c = src.copy(); bpy.context.scene.collection.objects.link(c); c.parent = h
                c.location = src.location + Vector((d[0], -d[2], d[1]))
        if oid == 'queue-1':
            copies('crate', [((i % 6) * .41, (i // 6) * .52, 0) for i in range(1, 15)])
        if oid == 'ci-1':
            copies('waiting_crate', [(.3, 0, 0), (0, 0, .3), (.3, 0, .3), (0, .3, 0)])
            before = set(bpy.data.objects)
            bpy.ops.import_scene.gltf(filepath=str(OUT / 'objects/job-token/job-token.gltf'))
            token = [o for o in bpy.data.objects if o not in before][0]; token.parent = h
            for ms in token.material_slots:
                if ms.material.name.startswith('job-token'):
                    p = ms.material.node_tree.nodes.get('Principled BSDF'); e = {'colour': (.11, .48, .68), 'emission': 2}
                    p.inputs['Base Color'].default_value = (*e['colour'], 1); p.inputs['Emission Color'].default_value = (*e['colour'], 1); p.inputs['Emission Strength'].default_value = 2
            spots = [(-1.5, .952, 0), (-.45, .952, 0), (.6, .952, 0), (1.1, .952, 0)]
            token.location = bl(spots[0]); token.rotation_euler = (0, 0, math.pi / 2)
            for sp in spots[1:]:
                c = token.copy(); bpy.context.scene.collection.objects.link(c); c.parent = h; c.location = bl(sp)
    bpy.context.view_layer.update()


def finish_groups():
    for name in list(GROUPS):
        o = GROUPS[name].finish(smooth_angle=30)
        GROUPS[name] = o
        if name in UNBAKED:
            continue
        # Faces looking down at floor level are never seen: keep them out of the lightmap.
        b = bmesh.new(); b.from_mesh(o.data)
        hidden = [f for f in b.faces if f.normal.z < -.9 and f.calc_center_median().z < .05]
        bmesh.ops.delete(b, geom=hidden, context='FACES'); b.to_mesh(o.data); b.free(); o.data.update()
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        uv = o.data.uv_layers.new(name='UV1'); o.data.uv_layers.active = uv
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(40), island_margin=.002, margin_method='FRACTION', scale_to_bounds=True)
        bpy.ops.uv.pack_islands(rotate=True, scale=True, margin_method='FRACTION', margin=8 / LIGHTMAP_SIZE[name])
        bpy.ops.object.mode_set(mode='OBJECT')
        o.data.uv_layers.active = o.data.uv_layers['UV0']; o.data.uv_layers['UV0'].active_render = True


def save_srgb(path, a):
    s = bpy.context.scene; old = (s.view_settings.view_transform, s.view_settings.look)
    s.view_settings.view_transform = 'Standard'; s.view_settings.look = 'None'
    im = bpy.data.images.new(path.stem, width=a.shape[1], height=a.shape[0], alpha=False, float_buffer=True); im.pixels.foreach_set(a.ravel())
    im.save_render(str(path), scene=s); bpy.data.images.remove(im)
    s.view_settings.view_transform, s.view_settings.look = old


def bake(samples):
    s = bpy.context.scene; s.cycles.samples = samples; s.render.bake.margin = 8; s.render.bake.use_clear = True
    rows = []
    (OUT / 'textures').mkdir(parents=True, exist_ok=True)
    for name, o in GROUPS.items():
        if name in UNBAKED:
            continue
        t = time.time(); n = LIGHTMAP_SIZE[name]
        im = bpy.data.images.new('Irradiance ' + name, width=n, height=n, alpha=False, float_buffer=True)
        for m in o.data.materials:
            node = m.node_tree.nodes.new('ShaderNodeTexImage'); node.name = 'bake target'; node.image = im; m.node_tree.nodes.active = node
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, uv_layer='UV1')
        a = np.empty(n * n * 4, dtype=np.float32); im.pixels.foreach_get(a); a = a.reshape(n, n, 4)
        src, dst = ART / 'raw.pfm', ART / 'denoised.pfm'
        with src.open('wb') as f:
            f.write(f'PF\n{n} {n}\n-1.0\n'.encode()); f.write(np.ascontiguousarray(a[:, :, :3], dtype='<f4').tobytes())
        subprocess.run(['oidnDenoise', '-v', '0', '-f', 'RTLightmap', '--hdr', str(src), '-o', str(dst), '--threads', '16'], check=True)
        with dst.open('rb') as f:
            assert f.readline().strip() == b'PF'; f.readline(); f.readline()
            a[:, :, :3] = np.frombuffer(f.read(), dtype='<f4').reshape(n, n, 3)
        src.unlink(); dst.unlink()
        peak = float(np.percentile(a[:, :, :3], 99.9)); assert peak > .05, (name, 'empty bake', peak)
        intensity = max(1.0, math.ceil(peak * 10) / 10)
        a[:, :, :3] = np.clip(a[:, :, :3] / intensity, 0, 1); a[:, :, 3] = 1
        save_srgb(OUT / 'textures' / f'lightmap-{name}.png', a); LIGHTMAPS[name] = intensity
        for m in o.data.materials:
            m.node_tree.nodes.remove(m.node_tree.nodes['bake target'])
        bpy.data.images.remove(im)
        rows.append({'group': name, 'resolution': n, 'peakLinear999': round(peak, 3), 'intensity': intensity, 'samples': samples, 'seconds': round(time.time() - t, 1)})
        log(f'baked {name}: {rows[-1]}')
    (ART / 'bake-report.json').write_text(json.dumps(rows, indent=1) + '\n')


def helpers():
    """Collision boxes and a grid navigation mesh: nodes outside the drawn scene."""
    cols = []
    for i, (lo, hi) in enumerate(COLLISION):
        me = bpy.data.meshes.new(f'Collision-{i}'); b = bmesh.new(); bmesh.ops.create_cube(b, size=1)
        bmesh.ops.scale(b, vec=Vector((hi[0] - lo[0], hi[2] - lo[2], hi[1] - lo[1])), verts=b.verts); b.to_mesh(me); b.free()
        o = bpy.data.objects.new(f'Collision-{i}', me); bpy.context.scene.collection.objects.link(o)
        o.location = bl([(a + c) / 2 for a, c in zip(lo, hi)]); cols.append(o)
    blocks = BLOCKS + [((x - .2, z - .2), (x + .2, z + .2)) for x, z in COLUMNS]
    for oid, asset, pos, q, (cx, cz), (sx, sz) in INSTANCES:
        blocks.append(((cx - sx / 2, cz - sz / 2), (cx + sx / 2, cz + sz / 2)))
    verts, faces, step = [], [], .5
    for xi in range(60):
        for zi in range(44):
            x, z = -15 + xi * step, -11 + zi * step
            if any(x + step > lo[0] - .3 and x < hi[0] + .3 and z + step > lo[1] - .3 and z < hi[1] + .3 for lo, hi in blocks):
                continue
            i = len(verts); verts += [bl((x, 0, z)), bl((x + step, 0, z)), bl((x + step, 0, z + step)), bl((x, 0, z + step))]
            faces += [(i, i + 2, i + 1), (i, i + 3, i + 2)]
    me = bpy.data.meshes.new('Navigation'); me.from_pydata(verts, [], faces); me.update()
    nav = bpy.data.objects.new('Navigation', me); bpy.context.scene.collection.objects.link(nav)
    return cols, nav


def export_scene(cols, nav):
    for o in cols + [nav]:
        o.data.materials.clear()
    objs = list(GROUPS.values()) + cols + [nav]
    g = kit.export_gltf(OUT / 'scene.gltf', objs)
    nodes = {n['name']: i for i, n in enumerate(g['nodes'])}
    hidden = {nodes[o.name] for o in cols + [nav]}
    g['scenes'][0]['nodes'] = [i for i in g['scenes'][0]['nodes'] if i not in hidden]
    lightmaps = []
    if LIGHTMAPS:
        g['samplers'].append({'magFilter': 9729, 'minFilter': 9729, 'wrapS': 33071, 'wrapT': 33071}); ls = len(g['samplers']) - 1
        for name, intensity in LIGHTMAPS.items():
            g['images'].append({'uri': f'textures/lightmap-{name}.png', 'mimeType': 'image/png'})
            g['textures'].append({'source': len(g['images']) - 1, 'sampler': ls}); ti = len(g['textures']) - 1
            for mi, m in enumerate(g['materials']):
                if m['name'].startswith(name + '--'):
                    lightmaps.append({'material': mi, 'texture': ti, 'texCoord': 1, 'encoding': 'srgb', 'intensity': intensity})
    (OUT / 'scene.gltf').write_text(json.dumps(g, indent=1) + '\n')
    return g, nodes, lightmaps, [nodes[o.name] for o in cols], nodes['Navigation']


def manifest(g, nodes, lightmaps, col_nodes, nav_node):
    assets = []
    for asset in [i[1] for i in INSTANCES] + ITEM_ASSETS:
        obj = json.loads((OUT / 'objects' / asset / 'object.json').read_text())
        entry = {'id': asset, 'scene': f'objects/{asset}/{asset}.gltf'}
        anims = obj['traits'].get('decorative', {}).get('animations', [])
        if anims:
            entry['animations'] = anims
        if 'collidable' in obj['traits']:
            entry['collision'] = {'node': obj['traits']['collidable']['node']}
        entry['lighting'] = obj['lighting']
        assets.append(entry)
    objects = [{'id': oid, 'asset': asset, 'pose': {'position': list(pos), 'rotation': q}} for oid, asset, pos, q, _, _ in INSTANCES]
    visual = [nodes['Visual-' + n] for n in ('ground', 'walls', 'roof', 'props')]
    sx, sy, sz = SCREEN['position']
    m = {
        'formatVersion': '0.8', 'id': WORLD_ID, 'version': VERSION, 'name': 'Machine Yard',
        'description': 'A compact terrace yard with five machine bays around a walking loop: a test world for live machines.',
        'license': 'CC-BY-4.0', 'scene': 'scene.gltf', 'preview': 'preview.png', 'defaultSpawn': 'entrance',
        'spawns': [{'id': 'entrance', 'pose': {'position': list(SPAWN), 'rotation': [0, 0, 0, 1]}}],
        'attribution': [{'path': '.', 'author': 'Hyprune contributors', 'license': 'CC-BY-4.0', 'source': 'https://github.com/hyprune/worlds/tree/main/machine-yard'}],
        'anchors': [{'id': SCREEN['id'], 'pose': {'position': [sx, sy, sz], 'rotation': [0, 1, 0, 0]}, 'size': list(SCREEN['size']),
                     'screenType': 'com.hyprune.window', 'mount': {'type': 'facade-wall', 'role': 'mounted-workspace', 'interaction': 'focus-in'}}],
        'areas': [{'id': 'yard', 'workspaceSlot': '01', 'primaryAnchor': SCREEN['id'], 'toolAnchors': [], 'dataAnchors': [], 'theme': 'machine-yard', 'spawnId': 'entrance'}],
        'zones': [{'id': 'yard', 'name': 'Machine Yard', 'bounds': {'min': [-15, -.5, -11], 'max': [15, 6, 11]}}],
        'navigation': {'kind': 'mesh', 'node': nav_node, 'agentRadius': .3, 'agentHeight': 1.8},
        'collision': [{'node': n, 'shape': 'mesh', 'layer': 'static'} for n in col_nodes],
        'lightmaps': lightmaps,
        'atmosphere': {'fog': {'color': [.55, .6, .66], 'density': .0025, 'heightFalloff': .02, 'baseHeight': -10, 'excludeUnlit': False},
                       'sky': {'zenith': list(SKY['zenith']), 'horizon': list(SKY['horizon']), 'ground': list(SKY['ground']),
                               'sun': {'direction': [round(v, 4) for v in SUN_DIR], 'color': list(SUN_COLOUR), 'intensity': 3, 'angularRadius': .025}},
                       'exposure': 1, 'toneMapping': 'aces', 'bloom': {'strength': .12, 'threshold': 1, 'radius': 3}},
        'visibility': {'areas': [{'id': 'yard', 'bounds': {'min': [-15.5, -1, -11.5], 'max': [15.5, 7, 11.5]}, 'nodes': visual, 'visibleFrom': []}]},
        'playable': {'volumes': [{'type': 'box', 'min': [-15, -1, -11], 'max': [15, 7, 11]}], 'maxFlyHeight': 7},
        'objectAssets': assets, 'objects': objects,
        'extensions': {'com.hyprune.lumen-reach.routes': {'version': 1,
            'nodes': [{'id': i, 'position': list(p), 'waypoint': lbl is not None, **({'label': lbl} if lbl else {})} for i, p, lbl in ROUTE],
            'edges': []}},
        'requiredExtensions': []}
    loop = [r[0] for r in ROUTE[1:]]
    edges = [{'from': 'entrance', 'to': 'monitor-view', 'width': 2.4}] + [{'from': a, 'to': b, 'width': 2.4} for a, b in zip(loop, loop[1:] + loop[:1])]
    m['extensions']['com.hyprune.lumen-reach.routes']['edges'] = edges
    (OUT / 'world.json').write_text(json.dumps(m, indent=2) + '\n')
    # Bindings for the machines prototype, checked against the placed instances.
    b = json.loads((HERE / 'machines.bindings.json').read_text())
    assert b['worldId'] == WORLD_ID and set(b['instances']) == {i[0] for i in INSTANCES}, 'bindings instances'
    for asset, path in b['manifests'].items():
        assert (OUT / path).exists(), path
    shutil.copy2(HERE / 'machines.bindings.json', OUT / 'machines.bindings.json')
    (OUT / 'LICENSE').write_text((ROOT / 'LICENSE').read_text())
    shutil.copy2(HERE / 'ATTRIBUTION.md', OUT / 'ATTRIBUTION.md')
    return m


VIEWS = [  # id, eye, target, lens (mm), hide roof
    ('01-entrance', (0, 1.7, 9.6), (0, 1.3, -4), 22, False),
    ('02-overview', (2.0, 13.0, 15.5), (0, 0, -2), 20, False),
    ('03-conveyor', (3.4, 1.65, -2.2), (-.4, 1.0, -7), 26, False),
    ('04-west-bays', (-4.0, 1.7, 8.0), (-10.5, 1.3, -.5), 24, False),
    ('05-lift', (4.2, 1.7, -.6), (10.5, 2.0, -3.4), 24, False),
    ('06-plan', (0, 45, 0), (0, 0, 0), 0, True),
]


def stills(samples=96, only=None):
    s = bpy.context.scene; render_settings(samples)
    cam = bpy.data.objects.get('Still camera')
    if cam is None:
        cam = bpy.data.objects.new('Still camera', bpy.data.cameras.new('Still camera')); s.collection.objects.link(cam)
    s.camera = cam
    for vid, eye, target, lens, hide in VIEWS:
        if only and vid not in only:
            continue
        cam.location = bl(eye)
        direction = bl(target) - bl(eye)
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y' if abs(direction.normalized().z) < .99 else 'Z').to_euler()
        if lens:
            cam.data.type = 'PERSP'; cam.data.lens = lens
        else:
            cam.data.type = 'ORTHO'; cam.data.ortho_scale = 34; cam.rotation_euler = (0, 0, 0)
        roof = GROUPS.get('roof') or bpy.data.objects.get('Visual-roof')
        if roof:
            roof.hide_render = hide
        s.render.filepath = str(ART / f'{vid}.png'); bpy.ops.render.render(write_still=True)
        log('still ' + vid)
    roof = bpy.data.objects.get('Visual-roof')
    if roof:
        roof.hide_render = False
    if (ART / '01-entrance.png').exists() and OUT.exists():
        shutil.copy2(ART / '01-entrance.png', OUT / 'preview.png')


def build(samples):
    kit.reset()
    ground(); walls(); roof(); props(); vista()
    atmosphere_blender(); render_settings(samples)
    finish_groups()
    roots = import_machines()
    machine_emission(roots, False)
    bake(samples)
    machine_emission(roots, True)
    cols, nav = helpers()
    g, nodes, lightmaps, col_nodes, nav_node = export_scene(cols, nav)
    for o in cols + [nav]:
        o.hide_render = True
    manifest(g, nodes, lightmaps, col_nodes, nav_node)
    demo_population(roots)
    bpy.ops.wm.save_as_mainfile(filepath=str(ART / 'machine-yard.blend'))
    log(f'collision boxes {len(COLLISION)}, lightmaps {LIGHTMAPS}')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--stage', choices=['build', 'objects', 'stills'], default='build')
    p.add_argument('--samples', type=int, default=128)
    p.add_argument('--only', nargs='*')
    p.add_argument('--still-samples', type=int, default=96)
    a = p.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    ART.mkdir(parents=True, exist_ok=True)
    if a.stage == 'objects':
        (OUT / 'objects').mkdir(parents=True, exist_ok=True)
        reports = machines.build_all(OUT / 'objects')
        (ART / 'objects-report.json').write_text(json.dumps(reports, indent=1) + '\n')
    elif a.stage == 'build':
        if OUT.exists():
            shutil.rmtree(OUT)
        (OUT / 'objects').mkdir(parents=True)
        reports = machines.build_all(OUT / 'objects')
        (ART / 'objects-report.json').write_text(json.dumps(reports, indent=1) + '\n')
        build(a.samples)
        stills(a.still_samples, only=a.only)
    else:
        bpy.ops.wm.open_mainfile(filepath=str(ART / 'machine-yard.blend'))
        stills(a.still_samples, only=a.only)
    log('complete ' + a.stage)
