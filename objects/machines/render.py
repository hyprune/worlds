# SPDX-License-Identifier: MIT
"""Concept renders of the machine object assets (Blender Eevee, bake host).

Imports the built glTFs from dist/objects/machines/<id>/ and shows them in
states described by scenarios (scenarios.py): palette states, animation
angles, stack counts, toggles, labels, items on tracks, value-driven positions
and effects. Renders what the assets contain; only labels' text, items and
effects are added here, as a runtime would.

    blender -b -P objects/machines/render.py -- --mode sheet --machine ci-conveyor --out DIR
    modes: sheet (hero, states, callout view + slot projections), thumb, lineup, turntable
"""
import argparse, json, math, os, random, re, sys
from pathlib import Path
if os.environ.get('HYPRUNE_REMOTE_BLENDER') != '1':
    raise SystemExit('Blender runs on the bake host only (HYPRUNE_REMOTE_BLENDER=1 there)')
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler, Matrix, Quaternion, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import scenarios

DIST = ROOT / 'dist/objects/machines'
FONT = os.environ.get('MACHINES_FONT', '/usr/share/fonts/TTF/JetBrainsMonoNLNerdFont-Regular.ttf')
BASE = re.compile(r'\.\d{3}$')


def g2b(v):
    return Vector((v[0], -v[2], v[1]))


def g2b_quat(q):
    x, y, z, w = q
    return Quaternion((w, x, -z, y))


# Scene ----------------------------------------------------------------------

def setup_scene(res=(1920, 1080), samples=64, floor=True, sky=(0.36, 0.48, 0.62)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    for engine in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            sc.render.engine = engine; break
        except TypeError:
            continue
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    ee = sc.eevee
    for attr, val in (('taa_render_samples', samples), ('use_shadows', True), ('use_raytracing', True), ('shadow_ray_count', 2),
                      ('shadow_step_count', 8), ('use_gtao', True), ('fast_gi_method', 'GLOBAL_ILLUMINATION')):
        if hasattr(ee, attr):
            try:
                setattr(ee, attr, val)
            except Exception:
                pass
    # Standard view (no filmic curve), close to core's direct sRGB output; a light bloom for practicals.
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.exposure = 0.0
    bloom(sc)
    # World: a high-valley sky (pale warm horizon, blue zenith)
    w = bpy.data.worlds.new('sky'); sc.world = w; w.use_nodes = True; nt = w.node_tree
    bg = nt.nodes.get('Background'); tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = .0; ramp.color_ramp.elements[0].color = (.78, .76, .70, 1)
    ramp.color_ramp.elements[1].position = .6; ramp.color_ramp.elements[1].color = (*sky, 1)
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    mp = nt.nodes.new('ShaderNodeMapRange'); mp.inputs['From Min'].default_value = 0.0; mp.inputs['From Max'].default_value = 1.0
    nt.links.new(sep.outputs['Z'], mp.inputs['Value']); nt.links.new(mp.outputs['Result'], ramp.inputs[0])
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = .9
    # Sun: warm late-morning light
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 2.6; sun.color = (1.0, .93, .82); sun.angle = math.radians(2.5)
    so = bpy.data.objects.new('sun', sun); so.rotation_euler = Euler((math.radians(50), 0, math.radians(-35))); sc.collection.objects.link(so)
    if floor:
        make_floor()
    return sc


def bloom(sc):
    try:
        t = bpy.data.node_groups.new('comp', 'CompositorNodeTree')
        t.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
        rl = t.nodes.new('CompositorNodeRLayers'); gl = t.nodes.new('CompositorNodeGlare'); out = t.nodes.new('NodeGroupOutput')
        gl.inputs['Type'].default_value = 'Bloom'; gl.inputs['Threshold'].default_value = .9; gl.inputs['Strength'].default_value = .45
        try:
            gl.inputs['Size'].default_value = .55
        except Exception:
            pass
        t.links.new(rl.outputs['Image'], gl.inputs['Image']); t.links.new(gl.outputs['Image'], out.inputs[0])
        sc.compositing_node_group = t
    except Exception as e:
        print('bloom unavailable:', e)


def make_floor(size=60):
    me = bpy.data.meshes.new('floor')
    s = size / 2
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    me.uv_layers.new(name='UV0')
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        me.uv_layers[0].data[loop.index].uv = (co.x / 3.2, co.y / 3.2)
    m = bpy.data.materials.new('floor'); m.use_nodes = True; nt = m.node_tree; p = nt.nodes.get('Principled BSDF')
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(str(ROOT / 'lumen-reach/materials/tiles/concrete-albedo.png'))
    mix = nt.nodes.new('ShaderNodeMixRGB'); mix.blend_type = 'MULTIPLY'; mix.inputs[0].default_value = 1; mix.inputs[2].default_value = (.62, .6, .58, 1)
    nt.links.new(t.outputs['Color'], mix.inputs[1]); nt.links.new(mix.outputs[0], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = .7
    me.materials.append(m)
    o = bpy.data.objects.new('floor', me); bpy.context.scene.collection.objects.link(o)
    return o


# Machines -------------------------------------------------------------------

class Machine:
    def __init__(self, mid, location=(0, 0, 0), yaw=0.0, tag=None):
        self.id = mid
        self.dir = DIST / mid
        self.manifest = json.loads((self.dir / 'object.json').read_text())
        self.root = bpy.data.objects.new(f'{tag or mid}-root', None)
        bpy.context.scene.collection.objects.link(self.root)
        self.root.location = location; self.root.rotation_euler = (0, 0, yaw)
        before = set(bpy.data.objects); mats_before = set(bpy.data.materials)
        bpy.ops.import_scene.gltf(filepath=str(self.dir / 'object.gltf'))
        new = [o for o in bpy.data.objects if o not in before]
        self.nodes = {BASE.sub('', o.name): o for o in new}
        self.materials = {BASE.sub('', m.name): m for m in bpy.data.materials if m not in mats_before}
        for o in new:
            if o.parent is None:
                o.parent = self.root
        for o in new:  # importer may add a converted root; keep names stable
            o['machine'] = self.id
        bpy.context.view_layer.update()
        self.rest = {n: (o.location.copy(), o.rotation_quaternion.copy() if o.rotation_mode == 'QUATERNION' else o.rotation_euler.to_quaternion())
                     for n, o in self.nodes.items()}
        for o in self.nodes.values():
            o.rotation_mode = 'QUATERNION'
        if 'proxy' in self.nodes:  # the importer brings in off-scene nodes; core never draws the proxy
            self.nodes['proxy'].hide_render = True; self.nodes['proxy'].hide_viewport = True
        self.extra = []
        self.anims = {a['node']: a for a in self.manifest.get('traits', {}).get('decorative', {}).get('animations', [])}
        self.slots = self.manifest.get('slots', {})

    # asset space (Blender axes) -> world
    def world(self, p):
        return self.root.matrix_world @ Vector(p)

    def clear_extra(self):
        for o in self.extra:
            bpy.data.objects.remove(o, do_unlink=True)
        self.extra = []
        for n, o in self.nodes.items():
            o.hide_render = o.hide_viewport = n == 'proxy'
            loc, rot = self.rest[n]; o.location = loc.copy(); o.rotation_quaternion = rot.copy()

    def palette(self, slot_id, state, emission=1.0):
        slot = next(s for s in self.slots.get('states', []) if s['id'] == slot_id)
        entry = next(e for e in slot['palette'] if e['id'] == state)
        for mname in slot.get('materials', []):
            m = self.materials[mname]; p = m.node_tree.nodes.get('Principled BSDF')
            p.inputs['Base Color'].default_value = (*entry['colour'], 1)
            p.inputs['Emission Color'].default_value = (*entry['colour'], 1)
            p.inputs['Emission Strength'].default_value = entry['emission'] * emission

    def anim_pose(self, node, angle=None, value=None):
        """Pose an animated node: angle (radians) for spin/orbit, or value-driven position 0..1."""
        a = self.anims[node]; o = self.nodes[node]; loc, rot = self.rest[node]
        axis = g2b(a['axis']).normalized()
        if a['type'] == 'spin':
            q = Quaternion(axis, angle)
            pivot = g2b(a['pivot'])
            o.location = pivot + q @ (loc - pivot); o.rotation_quaternion = q @ rot
        elif a['type'] == 'bob':
            if value is not None:
                rng = next((p['range'] for p in self.manifest['traits'].get('machine', {}).get('positions', []) if p['node'] == node), [0, 1])
                angle = 2 * math.pi * (rng[0] + value * (rng[1] - rng[0]))
            o.location = loc + axis * a['amplitude'] * math.sin(angle)

    def count(self, stack_id, n):
        st = next(s for s in self.slots.get('stacks', []) if s['id'] == stack_id)
        node = self.nodes[st['node']]
        nx, ny, nz = st['layout']['grid']; sx, sy, sz = st['layout']['spacing']
        n = min(n, st['cap'])
        node.hide_render = n == 0
        order = []
        for iy in range(ny):
            for iz in range(nz):
                for ix in range(nx):
                    order.append((ix, iy, iz))
        if st['layout'].get('fill', 'xzy') != 'xzy':
            raise ValueError('only xzy fill is rendered here')
        for k in range(1, n):
            ix, iy, iz = order[k]
            c = node.copy(); bpy.context.scene.collection.objects.link(c)
            c.location = node.location + g2b((ix * sx, iy * sy, iz * sz))
            self.extra.append(c)

    def toggle(self, tid, visible):
        t = next(s for s in self.slots.get('toggles', []) if s['id'] == tid)
        for n in t['nodes']:
            self.nodes[n].hide_render = not visible

    def label(self, lid, text, colour=(.85, .9, .82)):
        sl = next(s for s in self.slots.get('labels', []) if s['id'] == lid)
        w, h = sl['size']
        cu = bpy.data.curves.new(f'{lid}-text', 'FONT'); cu.body = text; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
        try:
            cu.font = bpy.data.fonts.load(FONT, check_existing=True)
        except Exception:
            pass
        cu.size = h * .62
        o = bpy.data.objects.new(f'{lid}-text', cu); bpy.context.scene.collection.objects.link(o)
        m = bpy.data.materials.new(f'{lid}-ink'); m.use_nodes = True; p = m.node_tree.nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value = (*colour, 1); p.inputs['Emission Color'].default_value = (*colour, 1); p.inputs['Emission Strength'].default_value = 1.6
        cu.materials.append(m)
        pos = g2b(sl['pose']['position']); rot = g2b_quat(sl['pose']['rotation'])
        o.parent = self.root
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = rot @ Quaternion((1, 0, 0), math.radians(90))
        o.location = pos + rot @ Vector((0, -.004, 0))
        bpy.context.view_layer.update()
        if o.dimensions.x > w * .94:
            cu.size *= w * .94 / o.dimensions.x
        self.extra.append(o)

    def track_points(self, tid):
        t = next(s for s in self.slots.get('tracks', []) if s['id'] == tid)
        return [g2b(p['position']) for p in t['points']]

    def track_at(self, tid, f):
        pts = self.track_points(tid)
        seg = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
        d = f * sum(seg)
        for i, L in enumerate(seg):
            if d <= L or i == len(seg) - 1:
                t = min(d / L, 1) if L else 0
                return pts[i].lerp(pts[i + 1], t), (pts[i + 1] - pts[i]).normalized()
            d -= L

    def item(self, tid, f, state, token):
        p, d = self.track_at(tid, f)
        o = token.instance(state)
        o.parent = self.root
        yaw = math.atan2(d.y, d.x) + math.pi / 2          # token front (-Y) along d
        pitch = math.asin(max(-1, min(1, d.z)))
        o.rotation_mode = 'XYZ'; o.rotation_euler = Euler((0, 0, yaw)); o.rotation_euler.rotate(Euler((0, 0, 0)))
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.location = p
        # pitch about the token's local X (front tips down a slope)
        o.rotation_euler = (Euler((0, 0, yaw)).to_matrix() @ Matrix.Rotation(-pitch, 3, 'X')).to_euler()
        self.extra.append(o)

    def effect(self, eid, seed=1, scale=1.0):
        e = next(s for s in self.slots.get('effects', []) if s['id'] == eid)
        c = g2b(e['pose']['position']); col = e.get('colour', [1, .8, .2]); kind = e.get('kind', 'burst')
        rnd = random.Random(seed)
        objs = []
        if kind == 'burst':
            palette = [col, (1, .42, .085), (.62, .73, .82), (.11, .48, .68)]
            for k in range(46):
                v = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-.2, 1))).normalized() * rnd.uniform(.25, .9) * scale
                bpy.ops.mesh.primitive_plane_add(size=rnd.uniform(.035, .06) * scale, location=c + v)
                o = bpy.context.object; o.rotation_euler = (rnd.uniform(0, 6.3), rnd.uniform(0, 6.3), rnd.uniform(0, 6.3))
                o.data.materials.append(glow_material(palette[k % len(palette)], 3.0)); objs.append(o)
        else:  # flash / pulse / ring: a bright ring and a glow sphere
            bpy.ops.mesh.primitive_torus_add(major_radius=.32 * scale, minor_radius=.018 * scale, location=c, major_segments=40, minor_segments=6)
            o = bpy.context.object; o.data.materials.append(glow_material(col, 4.0)); objs.append(o)
            bpy.ops.mesh.primitive_uv_sphere_add(radius=.12 * scale, location=c, segments=16, ring_count=8)
            o = bpy.context.object; o.data.materials.append(glow_material(col, 5.0)); objs.append(o)
        light = bpy.data.lights.new(f'{eid}-light', 'POINT'); light.energy = 60 * scale; light.color = col[:3]; light.shadow_soft_size = .2
        lo = bpy.data.objects.new(f'{eid}-light', light); bpy.context.scene.collection.objects.link(lo); lo.location = c; objs.append(lo)
        for o in objs:
            o.parent = self.root; o.matrix_parent_inverse = Matrix.Identity(4)
        self.extra += objs

    def apply(self, sc, token=None, t=0.0):
        """Apply a scenario dict (see scenarios.py) at animation time t (s)."""
        self.clear_extra()
        for slot in self.slots.get('states', []):
            st = sc.get('states', {}).get(slot['id'], sc.get('states', {}).get('*', slot['palette'][0]['id']))
            self.palette(slot['id'], st, sc.get('emission', {}).get(slot['id'], 1.0))
        speeds = sc.get('speeds', {})
        for node, a in self.anims.items():
            if a['type'] == 'bob' and node in sc.get('positions', {}):
                self.anim_pose(node, value=sc['positions'][node]); continue
            s = speeds.get(node, speeds.get('*', 1.0))
            ang = 2 * math.pi * (t * s / a['period'] + a.get('phase', 0) + sc.get('phase', 0))
            self.anim_pose(node, angle=ang)
        for sid, n in sc.get('counts', {}).items():
            self.count(sid, n)
        for st in self.slots.get('stacks', []):
            if st['id'] not in sc.get('counts', {}):
                self.count(st['id'], 0)
        for tid, vis in sc.get('toggles', {}).items():
            self.toggle(tid, vis)
        for lid, text in sc.get('labels', {}).items():
            self.label(lid, text)
        if token:
            for tid, f, state in sc.get('items', []):
                self.item(tid, f, state, token)
        for k, eid in enumerate(sc.get('effects', [])):
            self.effect(eid, seed=k + 1)


_glow = {}


def glow_material(col, strength):
    key = (tuple(round(c, 3) for c in col[:3]), strength)
    if key not in _glow:
        m = bpy.data.materials.new('glow'); m.use_nodes = True; p = m.node_tree.nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value = (*col[:3], 1); p.inputs['Emission Color'].default_value = (*col[:3], 1)
        p.inputs['Emission Strength'].default_value = strength
        _glow[key] = m
    return _glow[key]


class Token:
    """The job-token item asset, copied per item with a per-state band material."""

    def __init__(self):
        self.m = Machine('job-token', location=(0, 0, -50))
        self.mats = {}
        band = self.m.materials['band']
        for e in self.m.slots['states'][0]['palette']:
            mm = band.copy(); p = mm.node_tree.nodes.get('Principled BSDF')
            p.inputs['Base Color'].default_value = (*e['colour'], 1); p.inputs['Emission Color'].default_value = (*e['colour'], 1)
            p.inputs['Emission Strength'].default_value = e['emission']
            self.mats[e['id']] = mm

    def instance(self, state):
        holder = bpy.data.objects.new('token', None); bpy.context.scene.collection.objects.link(holder)
        for n, o in self.m.nodes.items():
            if o.type != 'MESH':
                continue
            c = o.copy(); c.data = o.data.copy() if n == 'band' else o.data
            if n == 'band':
                c.data.materials.clear(); c.data.materials.append(self.mats[state])
            bpy.context.scene.collection.objects.link(c); c.parent = holder; c.matrix_parent_inverse = Matrix.Identity(4)
            c.location = o.location.copy(); c.rotation_quaternion = o.rotation_quaternion.copy()
            holder['children'] = holder.get('children', 0) + 1
        return holder


# Cameras --------------------------------------------------------------------

def bounds_world(m):
    b = m.manifest['bounds']
    lo, hi = g2b(b['min']), g2b(b['max'])
    xs, ys, zs = sorted((lo.x, hi.x)), sorted((lo.y, hi.y)), sorted((lo.z, hi.z))
    corners = [m.world((x, y, z)) for x in xs for y in ys for z in zs]
    return corners


def camera(name='cam', lens=50, ortho=None):
    cam = bpy.data.cameras.new(name); cam.lens = lens; cam.clip_end = 400
    if ortho:
        cam.type = 'ORTHO'; cam.ortho_scale = ortho
    o = bpy.data.objects.new(name, cam); bpy.context.scene.collection.objects.link(o); bpy.context.scene.camera = o
    return o


def frame(cam, corners, azimuth, elevation, margin=1.12, target=None):
    """Place cam looking at the corners' centre from azimuth/elevation (degrees; azimuth 0 = front, -Y),
    distance chosen so every corner fits."""
    c = target if target is not None else sum(corners, Vector()) / len(corners)
    az, el = math.radians(azimuth), math.radians(elevation)
    d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    sc = bpy.context.scene
    dist = 10.0
    for _ in range(12):
        cam.location = c + d * dist
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()
        pts = [world_to_camera_view(sc, cam, p) for p in corners]
        ext = max(max(abs(p.x - .5), abs(p.y - .5)) for p in pts) * 2
        dist *= ext * margin if ext > 0 else 1
    cam.location = c + d * dist; bpy.context.view_layer.update()
    return dist


def project(cam, p):
    v = world_to_camera_view(bpy.context.scene, cam, p)
    sc = bpy.context.scene
    return [round(v.x * sc.render.resolution_x, 1), round((1 - v.y) * sc.render.resolution_y, 1), round(v.z, 3)]


def slot_points(m):
    """Callout anchors for every slot and animated node, in world space."""
    out = []
    def centre(o):
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        return sum(pts, Vector()) / 8
    for s in m.slots.get('states', []):
        objs = [o for o in m.nodes.values() if o.type == 'MESH' and any(BASE.sub('', ms.name) in s.get('materials', []) for ms in o.data.materials if ms)]
        for o in objs:
            out.append({'kind': 'states', 'id': s['id'], 'target': f"state:{s['id']}", 'p': centre(o)})
    for node in m.anims:
        out.append({'kind': 'animation', 'id': node, 'target': f'animation:{node}', 'p': centre(m.nodes[node])})
    for kind, prefix in (('labels', 'label'), ('spawns', 'spawn'), ('effects', 'effect')):
        for s in m.slots.get(kind, []):
            out.append({'kind': kind, 'id': s['id'], 'target': f"{prefix}:{s['id']}", 'p': m.world(g2b(s['pose']['position']))})
    for s in m.slots.get('tracks', []):
        pts = [m.world(g2b(p['position'])) for p in s['points']]
        out.append({'kind': 'tracks', 'id': s['id'], 'target': f"track {s['id']}", 'p': pts[len(pts) // 2], 'path': pts})
    for s in m.slots.get('stacks', []):
        out.append({'kind': 'stacks', 'id': s['id'], 'target': f"count:{s['id']}", 'p': centre(m.nodes[s['node']])})
    for s in m.slots.get('toggles', []):
        for n in s['nodes']:
            out.append({'kind': 'toggles', 'id': s['id'], 'target': f"visible:{s['id']}", 'p': centre(m.nodes[n])})
    return out


def render(path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


# Modes ----------------------------------------------------------------------

def mode_sheet(mid, out):
    out.mkdir(parents=True, exist_ok=True)
    spec = scenarios.SHEETS[mid]
    setup_scene(res=(1920, 1280), samples=96)
    token = Token() if spec.get('token') else None
    m = Machine(mid)
    cam = camera(lens=spec.get('lens', 40))
    corners = bounds_world(m)
    # hero
    m.apply(spec['hero'], token, t=spec['hero'].get('t', 1.3))
    frame(cam, corners, *spec.get('hero_view', (-32, 16)), margin=spec.get('margin', 1.08))
    render(out / 'hero.png')
    # states
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1100, 900
    for k, st in enumerate(spec['states']):
        m.apply(st, token, t=st.get('t', 1.3))
        frame(cam, corners, *spec.get('state_view', spec.get('hero_view', (-32, 16))), margin=spec.get('margin', 1.08))
        render(out / f'state-{k}.png')
    # callout view
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1920, 1280
    m.apply(spec.get('callout', spec['hero']), token, t=1.3)
    frame(cam, corners, *spec.get('callout_view', (-24, 20)), margin=spec.get('callout_margin', 1.3))
    render(out / 'callout.png')
    pts = [{**{k: v for k, v in p.items() if k not in ('p', 'path')}, 'xy': project(cam, p['p']),
            **({'path': [project(cam, q) for q in p['path']]} if 'path' in p else {})} for p in slot_points(m)]
    # thumbnail: 256 x 256, the hero state, transparent film off
    bpy.context.scene.render.resolution_x = bpy.context.scene.render.resolution_y = 512
    m.apply(spec['hero'], token, t=1.3)
    frame(cam, corners, *spec.get('thumb_view', spec.get('hero_view', (-32, 16))), margin=1.04)
    render(out / 'thumb-512.png')
    tris = json.loads((DIST / mid / 'build-report.json').read_text())
    (out / 'sheet.json').write_text(json.dumps({'id': mid, 'name': m.manifest['name'], 'description': m.manifest['description'],
                                                'manifest': m.manifest, 'report': tris, 'callouts': pts,
                                                'states': [s.get('caption', '') for s in spec['states']]}, indent=1))


def mode_lineup(out):
    out.mkdir(parents=True, exist_ok=True)
    setup_scene(res=(3200, 1300), samples=96)
    token = Token()
    x = 0.0; machines = []
    order = scenarios.LINEUP
    widths = []
    for mid in order:
        b = json.loads((DIST / mid / 'object.json').read_text())['bounds']
        widths.append(b['max'][0] - b['min'][0])
    gap = 1.1
    total = sum(widths) + gap * (len(order) + 1) + .8
    x = -total / 2
    fig_x = x + .4; x += .8 + gap
    for mid, w in zip(order, widths):
        m = Machine(mid, location=(x + w / 2, 0, 0)); m.apply(scenarios.SHEETS[mid]['hero'], token, t=1.3); machines.append(m)
        x += w + gap
    figure((fig_x, 0, 0))
    cam = camera(lens=60)
    corners = [c for m in machines for c in bounds_world(m)] + [Vector((fig_x - .3, -.3, 0)), Vector((fig_x + .3, .3, 1.7))]
    frame(cam, corners, 0, 6, margin=1.04)
    render(out / 'lineup.png')
    bpy.context.view_layer.update()
    marks = {'figure': [project(cam, Vector((fig_x, 0, 1.7))), project(cam, Vector((fig_x, 0, 0)))]}
    for m in machines:
        b = m.manifest['bounds']
        marks[m.id] = [project(cam, m.world(Vector((0, 0, b['max'][1])))), project(cam, m.world(Vector((0, 0, 0)))), m.manifest['name'], b]
    (out / 'lineup.json').write_text(json.dumps(marks, indent=1))


def figure(pos, h=1.7):
    """A plain 1.7 m scale figure (capsule body, head) in ivory."""
    m = bpy.data.materials.new('figure'); m.use_nodes = True; p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (.55, .52, .46, 1); p.inputs['Roughness'].default_value = .6
    x, y, z = pos
    parts = []
    head_r = .11
    bpy.ops.mesh.primitive_uv_sphere_add(radius=head_r, location=(x, y, h - head_r), segments=24, ring_count=12); parts.append(bpy.context.object)
    bpy.ops.mesh.primitive_cylinder_add(radius=.055, depth=.08, location=(x, y, h - 2 * head_r - .02)); parts.append(bpy.context.object)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, 1.18)); o = bpy.context.object; o.scale = (.38, .2, .56); parts.append(o)
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(radius=.075, depth=.86, location=(x + sx * .1, y, .45)); parts.append(bpy.context.object)
        bpy.ops.mesh.primitive_cylinder_add(radius=.045, depth=.62, location=(x + sx * .245, y, 1.13)); parts.append(bpy.context.object)
    for o in parts:
        o.data.materials.append(m)
        for mod in [o.modifiers.new('bevel', 'BEVEL')]:
            mod.width = .03; mod.segments = 3
    return parts


def mode_turntable(out, fps=30, seconds=10.0):
    """Frames for every machine: one full orbit while its turntable scenarios cycle."""
    out.mkdir(parents=True, exist_ok=True)
    setup_scene(res=(1920, 1080), samples=32)
    token = Token()
    cam = camera(lens=40)
    frame_no = 0
    machines = scenarios.LINEUP
    only = os.environ.get('TURNTABLE_ONLY')
    for mid in machines:
        m = Machine(mid, location=(0, 0, 0))
        spec = scenarios.SHEETS[mid]
        tt = spec['turntable']
        n = int(seconds * fps)
        corners = bounds_world(m)
        for f in range(n):
            t = f / fps
            sc = tt[min(int(t / (seconds / len(tt))), len(tt) - 1)]
            sc = scenarios.at_time(sc, t - int(t / (seconds / len(tt))) * (seconds / len(tt)))
            if only and mid != only:
                frame_no += 1; continue
            m.apply(sc, token, t=t)
            frame(cam, corners, -40 + 360 * f / n, spec.get('turntable_elevation', 14), margin=spec.get('turntable_margin', 1.18),
                  target=sum(corners, Vector()) / len(corners) + Vector((0, 0, -.1)))
            render(out / f'{frame_no:05d}.png')
            frame_no += 1
        m.clear_extra()
        for o in list(m.nodes.values()) + [m.root]:
            bpy.data.objects.remove(o, do_unlink=True)
    (out / 'turntable.json').write_text(json.dumps({'fps': fps, 'seconds': seconds, 'machines': machines, 'captions': {
        mid: [s.get('caption', '') for s in scenarios.SHEETS[mid]['turntable']] for mid in machines}}, indent=1))


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser(); ap.add_argument('--mode', required=True); ap.add_argument('--machine'); ap.add_argument('--out', required=True)
    ap.add_argument('--seconds', type=float, default=10.0)
    a = ap.parse_args(argv)
    out = Path(a.out)
    if a.mode == 'sheet':
        mode_sheet(a.machine, out)
    elif a.mode == 'lineup':
        mode_lineup(out)
    elif a.mode == 'turntable':
        mode_turntable(out, seconds=a.seconds)
    else:
        raise SystemExit('unknown mode')


main()
