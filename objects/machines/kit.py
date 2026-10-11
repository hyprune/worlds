# SPDX-License-Identifier: MIT
"""Shared kit for the machine object assets (objects/machines/<id>/build.py).

Procedural Blender geometry in the Lumen Reach language (warm timber, pale
stone, dark metal, cyan/mint/amber accent light), exported as an RFC-0011
object directory: object.gltf (+ .bin, PNG tiles) and object.json.

Conventions (see objects/machines/README.md):
- Blender is Z up with the machine's front facing -Y; glTF is +Y up, front +Z.
  Origin: the base centre of the rest-pose bounds (bounds min Y = 0).
- A slot that external data drives is a uniquely named node. A state slot owns
  its node, its mesh and one material named like the node, so changing one
  slot never touches another.
- Node names, state-slot material names and slot ids are the same slug
  (RFC-0013: `state:stage-1-lamp`, `animation:stage-1-spinner`).
- Palettes are colour + emission (RFC-0011/0013). Each state is mirrored as an
  authored glTF material `<palette>-<state>` listed with KHR_materials_variants
  (optional, never required), so glTF viewers and tools can preview states.
- The collision proxy is a node outside the scene's node list (not drawn).
"""
import json, math, os, shutil, sys
from pathlib import Path
if os.environ.get('HYPRUNE_REMOTE_BLENDER') != '1':
    raise SystemExit('Use make machines (tools/remote-blender.sh); never local Blender on the laptop')
import bpy, bmesh
from mathutils import Euler, Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[2]
TILES = ROOT / 'lumen-reach/materials/tiles'
TILE_PX = 256

# Linear accent colours (Lumen Reach practicals and instrument traces).
CYAN = (.11, .48, .68)
MINT = (.20, .85, .35)
AMBER = (1.0, .42, .085)
RED = (.9, .06, .02)
SLATE = (.10, .12, .14)
ICE = (.62, .73, .82)
IVORY = (.70, .66, .54)

# Material specs: colour (linear factor), roughness, metallic, tile texture and
# metres per tile, emission (colour x strength), unlit.
MATS = {
    'timber':      dict(color=(1.0, .92, .85), rough=.55, tex='wood', tile=.9),
    'timber-dark': dict(color=(.55, .45, .38), rough=.6, tex='wood', tile=.9),
    'stone':       dict(color=(1.0, 1.0, 1.0), rough=.82, tex='concrete', tile=1.6),
    'metal':       dict(color=(.30, .32, .35), rough=.42, metal=.65, tex='metal', tile=1.0),
    'metal-black': dict(color=(.035, .04, .045), rough=.38, metal=.7),
    'brass':       dict(color=(.62, .43, .19), rough=.32, metal=.85),
    'ivory':       dict(color=IVORY, rough=.5),
    'rubber':      dict(color=(.02, .022, .025), rough=.85),
    'panel':       dict(color=(.008, .012, .018), rough=.18, metal=.2),
    'canvas-red':  dict(color=(.33, .065, .035), rough=.9),
    'strip-cyan':  dict(color=CYAN, emit=1.2),
    'strip-amber': dict(color=AMBER, emit=1.0),
    'strip-mint':  dict(color=MINT, emit=1.0),
    'glow-ivory':  dict(color=ICE, emit=.8),
}

# State palettes: (state, linear colour, emission). Emission > 1 is written
# with KHR_materials_emissive_strength.
PALETTES = {
    'lamp':   [('idle', SLATE, .25), ('running', CYAN, 1.8), ('ok', MINT, 1.6), ('fail', RED, 2.2)],
    'health': [('off', (.05, .06, .07), 0.0), ('ok', MINT, 1.4), ('warn', AMBER, 1.6), ('fail', RED, 2.2)],
    'level':  [('ok', MINT, 1.3), ('warn', AMBER, 1.8), ('fail', RED, 2.2)],
    'glow':   [('idle', (.16, .2, .24), .4), ('running', CYAN, 2.0), ('ok', MINT, 1.8), ('fail', RED, 2.2)],
    'phase':  [('off', SLATE, .15), ('active', CYAN, 2.0), ('done', ICE, .7), ('fail', RED, 2.2)],
    'beacon': [('off', SLATE, .15), ('active', AMBER, 2.0), ('live', MINT, 2.2), ('fail', RED, 2.4)],
    'face':   [('idle', (.16, .2, .24), .35), ('running', CYAN, 1.2), ('ok', MINT, 1.1), ('fail', RED, 1.4)],
    'token':  [('queued', IVORY, .3), ('running', CYAN, 1.2), ('ok', MINT, 1.1), ('fail', RED, 1.4)],
}

_bmats = {}
_images = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _bmats.clear(); _images.clear()


def _image(tex):
    if tex not in _images:
        im = bpy.data.images.load(str(TILES / f'{tex}-albedo.png'))
        im.scale(TILE_PX, TILE_PX); im.name = tex
        _images[tex] = im
    return _images[tex]


def bmat(name, spec=None):
    """Blender material for `name` (the export only needs names, UVs and textures;
    the final glTF material is written from the spec in finish())."""
    if name in _bmats:
        return _bmats[name]
    spec = spec or MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; p = nt.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*spec['color'], 1)
    p.inputs['Roughness'].default_value = spec.get('rough', .5); p.inputs['Metallic'].default_value = spec.get('metal', 0)
    if spec.get('tex'):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = _image(spec['tex'])
        nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
    if spec.get('emit'):
        p.inputs['Emission Color'].default_value = (*spec['color'], 1); p.inputs['Emission Strength'].default_value = spec['emit']
    m['spec'] = json.dumps(spec)
    _bmats[name] = m
    return m


class Part:
    """One mesh node built from primitives in asset (Blender) space. `origin` is
    the node's pivot: the mesh is stored relative to it."""

    def __init__(self, name, origin=(0, 0, 0)):
        self.name, self.origin = name, Vector(origin)
        self.bm = bmesh.new(); self.uv = self.bm.loops.layers.uv.new('UV0'); self.mats = []

    def _mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _take(self, src, mat, grain='z', matrix=None):
        """Merge bmesh `src` (asset-space after `matrix`) with material `mat`."""
        if matrix is not None:
            bmesh.ops.transform(src, matrix=matrix, verts=src.verts)
        mi = self._mi(mat); spec = MATS.get(mat, {}); tile = spec.get('tile', 1.0)
        vmap = {v: self.bm.verts.new(v.co) for v in src.verts}
        gi = 'xyz'.index(grain)
        for f in src.faces:
            nf = self.bm.faces.new([vmap[v] for v in f.verts]); nf.material_index = mi
            n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
            others = [i for i in range(3) if i != ax]
            if gi in others:  # grain runs along V
                u_i, v_i = [i for i in others if i != gi][0], gi
            else:
                u_i, v_i = others
            for loop, l2 in zip(nf.loops, f.loops):
                co = l2.vert.co
                loop[self.uv].uv = (co[u_i] / tile, co[v_i] / tile)
        src.free()
        return self

    # Primitives -------------------------------------------------------------
    def box(self, mat, center, size, bevel=0.0, rot=(0, 0, 0), grain='z'):
        b = bmesh.new(); bmesh.ops.create_cube(b, size=1.0)
        bmesh.ops.scale(b, vec=Vector(size), verts=b.verts)
        if bevel:
            bmesh.ops.bevel(b, geom=list(b.edges), offset=min(bevel, min(size) * .45), segments=1, profile=.5, affect='EDGES')
        m = Matrix.Translation(Vector(center)) @ Euler(rot).to_matrix().to_4x4()
        return self._take(b, mat, grain, matrix=m)

    def cyl(self, mat, a, b, r, seg=16, r2=None, caps=True, grain='z'):
        """Cylinder or frustum from point a to point b (radius r at a, r2 at b)."""
        a, b = Vector(a), Vector(b); d = b - a
        bm_ = bmesh.new()
        bmesh.ops.create_cone(bm_, cap_ends=caps, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=d.length)
        q = d.normalized().to_track_quat('Z', 'Y')
        m = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4()
        self._take(bm_, mat, grain, matrix=m)
        return self

    def torus(self, mat, center, R, r, seg=32, sseg=8, rot=(0, 0, 0)):
        b = bmesh.new()
        verts = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            ring = []
            for j in range(sseg):
                c = 2 * math.pi * j / sseg
                rr = R + r * math.cos(c)
                ring.append(b.verts.new((rr * math.cos(a), rr * math.sin(a), r * math.sin(c))))
            verts.append(ring)
        for i in range(seg):
            for j in range(sseg):
                b.faces.new([verts[i][j], verts[(i + 1) % seg][j], verts[(i + 1) % seg][(j + 1) % sseg], verts[i][(j + 1) % sseg]])
        m = Matrix.Translation(Vector(center)) @ Euler(rot).to_matrix().to_4x4()
        return self._take(b, mat, matrix=m)

    def hull(self, mat, points, grain='z'):
        b = bmesh.new()
        vs = [b.verts.new(p) for p in points]
        r = bmesh.ops.convex_hull(b, input=vs)
        bmesh.ops.delete(b, geom=[g for g in r.get('geom_interior', []) + r.get('geom_unused', []) if isinstance(g, bmesh.types.BMVert)], context='VERTS')
        bmesh.ops.dissolve_limit(b, angle_limit=.001, verts=b.verts, edges=b.edges)
        bmesh.ops.recalc_face_normals(b, faces=b.faces)
        return self._take(b, mat, grain)

    def prism(self, mat, profile, depth, plane='xz', offset=0.0, grain='z'):
        """Extrude a 2D polygon `profile` (CCW) across `depth`. plane 'xz': profile in
        X/Z, extruded along Y from offset-depth/2; 'yz': in Y/Z along X; 'xy': along Z."""
        b = bmesh.new()
        def p3(u, v, w):
            return {'xz': (u, w, v), 'yz': (w, u, v), 'xy': (u, v, w)}[plane]
        lo = [b.verts.new(p3(u, v, offset - depth / 2)) for u, v in profile]
        hi = [b.verts.new(p3(u, v, offset + depth / 2)) for u, v in profile]
        n = len(profile)
        b.faces.new(lo); b.faces.new(list(reversed(hi)))
        for i in range(n):
            b.faces.new([lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]])
        bmesh.ops.recalc_face_normals(b, faces=b.faces)
        return self._take(b, mat, grain)

    def quad(self, mat, center, w, h, rot=(0, 0, 0)):
        """A w x h rectangle facing -Y (the front) before `rot`."""
        b = bmesh.new()
        vs = [b.verts.new((x, 0, z)) for x, z in [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]]
        b.faces.new(vs)
        m = Matrix.Translation(Vector(center)) @ Euler(rot).to_matrix().to_4x4()
        return self._take(b, mat, 'z', matrix=m)

    def finish(self, smooth_angle=None, collection=None):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-5)
        bmesh.ops.translate(self.bm, vec=-self.origin, verts=self.bm.verts)
        me = bpy.data.meshes.new(self.name); self.bm.to_mesh(me); self.bm.free()
        for mname in self.mats:
            me.materials.append(bmat(mname))
        o = bpy.data.objects.new(self.name, me); o.location = self.origin
        (collection or bpy.context.scene.collection).objects.link(o)
        if smooth_angle:
            for p in me.polygons:
                p.use_smooth = True
            me.set_sharp_from_angle(angle=math.radians(smooth_angle))
        return o


def empty(name, loc, rot=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None); o.location = loc; o.rotation_euler = rot; o.empty_display_size = .1
    bpy.context.scene.collection.objects.link(o)
    if parent:
        o.parent = parent
    return o


def lamp(name, palette, center, r=.09, depth=.05, axis='-y', seg=20, dome=True):
    """A state lamp: its own node, mesh and material `name` (initially the palette's first state)."""
    st = PALETTES[palette][0]
    spec = dict(color=st[1], rough=.25, emit=st[2], palette=palette)
    MATS[name] = spec
    c = Vector(center); d = {'-y': Vector((0, -1, 0)), 'z': Vector((0, 0, 1)), 'x': Vector((1, 0, 0)), '-x': Vector((-1, 0, 0)), 'y': Vector((0, 1, 0))}[axis]
    p = Part(name, c)
    if dome:  # a lens: short cylinder + chamfered cap
        p.cyl(name, c, c + d * depth * .6, r, seg=seg)
        p.cyl(name, c + d * depth * .6, c + d * depth, r, seg=seg, r2=r * .72)
    else:
        p.cyl(name, c, c + d * depth, r, seg=seg)
    return p.finish(smooth_angle=40)


def bar_lamp(name, palette, center, size, bevel=.006):
    st = PALETTES[palette][0]
    MATS[name] = dict(color=st[1], rough=.25, emit=st[2], palette=palette)
    return Part(name, center).box(name, center, size, bevel=bevel).finish()


def slot_material(name, palette, rough=.25):
    st = PALETTES[palette][0]
    MATS[name] = dict(color=st[1], rough=rough, emit=st[2], palette=palette)
    return name


# Export -------------------------------------------------------------------

def b2g(v):
    return [round(v[0], 5), round(v[2], 5), round(-v[1], 5)]


def _gltf_material(name, spec):
    m = {'name': name, 'pbrMetallicRoughness': {'baseColorFactor': [*[round(c, 4) for c in spec['color']], 1],
                                                 'metallicFactor': spec.get('metal', 0), 'roughnessFactor': spec.get('rough', .5)}}
    e = spec.get('emit', 0)
    if e:
        m['emissiveFactor'] = [round(c * min(e, 1), 4) for c in spec['color']]
        if e > 1:
            m['extensions'] = {'KHR_materials_emissive_strength': {'emissiveStrength': round(e, 3)}}
    if spec.get('unlit'):
        m.setdefault('extensions', {})['KHR_materials_unlit'] = {}
    return m


def recentre(exclude=None):
    """Move every root object so the rest-pose bounds (drawn meshes) sit on the floor, centred."""
    bpy.context.view_layer.update()
    lo, hi = bounds_blender([o for o in bpy.context.scene.collection.objects if o.type == 'MESH' and o is not exclude])
    shift = Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    for o in bpy.context.scene.collection.objects:
        if o.parent is None:
            o.location += shift
    bpy.context.view_layer.update()
    return shift


def bounds_blender(objects):
    pts = [o.matrix_world @ v.co for o in objects if o.type == 'MESH' for v in o.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def triangles(objects):
    return sum(len(p.vertices) - 2 for o in objects if o.type == 'MESH' for p in o.data.polygons)


def export(out, manifest, proxy=None, slots_nodes=None):
    """Write out/object.gltf (+bin, PNG tiles) and out/object.json.

    manifest: the RFC-0011 object.json without bounds (computed here)."""
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    scene_objs = [o for o in bpy.context.scene.collection.objects if o is not proxy]
    visible = [o for o in scene_objs if o.type == 'MESH']
    lo, hi = bounds_blender(visible)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=str(out / 'object.gltf'), export_format='GLTF_SEPARATE', use_selection=True, export_yup=True,
                              export_apply=True, export_animations=False, export_cameras=False, export_lights=False, export_extras=False,
                              export_materials='EXPORT', export_image_format='AUTO')
    g = json.loads((out / 'object.gltf').read_text())
    # Materials from the specs (the exporter keeps base colour textures; factors, emission and unlit are ours).
    used = set()
    for m in g.get('materials', []):
        spec = MATS[m['name']]
        new = _gltf_material(m['name'], spec)
        tex = m.get('pbrMetallicRoughness', {}).get('baseColorTexture')
        if tex:
            new['pbrMetallicRoughness']['baseColorTexture'] = {'index': tex['index']}
        m.clear(); m.update(new); used.add(m['name'])
    # State variants: every palette state as an authored material, mapped per slot primitive.
    variants = []
    var_mat = {}
    for name, spec in list(MATS.items()):
        if 'palette' not in spec or name not in used:
            continue
        for state, col, em in PALETTES[spec['palette']]:
            vname = f"{spec['palette']}-{state}"
            if vname not in var_mat:
                vspec = dict(color=col, rough=spec.get('rough', .25), emit=em)
                g['materials'].append(_gltf_material(vname, vspec)); var_mat[vname] = len(g['materials']) - 1
            if state not in variants:
                variants.append(state)
    mat_index = {m['name']: i for i, m in enumerate(g['materials'])}
    for mesh in g.get('meshes', []):
        for prim in mesh['primitives']:
            mname = g['materials'][prim['material']]['name'] if 'material' in prim else None
            spec = MATS.get(mname, {})
            if 'palette' in spec:
                prim.setdefault('extensions', {})['KHR_materials_variants'] = {'mappings': [
                    {'material': var_mat[f"{spec['palette']}-{s}"], 'variants': [variants.index(s)]} for s, _, _ in PALETTES[spec['palette']]]}
    ext_used = set(g.get('extensionsUsed', []))
    if variants:
        g.setdefault('extensions', {})['KHR_materials_variants'] = {'variants': [{'name': v} for v in variants]}
        ext_used.add('KHR_materials_variants')
    for m in g['materials']:
        ext_used |= set(m.get('extensions', {}))
    g['extensionsUsed'] = sorted(ext_used)
    g.pop('extensionsRequired', None)
    # The collision proxy stays in nodes[] but leaves the scene (never drawn).
    node_index = {n['name']: i for i, n in enumerate(g['nodes'])}
    if proxy:
        pi = node_index[proxy.name]
        g['scenes'][0]['nodes'] = [n for n in g['scenes'][0]['nodes'] if n != pi]
    g['asset']['copyright'] = 'Hyprune contributors, CC-BY-4.0'
    (out / 'object.gltf').write_text(json.dumps(g, indent=1) + '\n')

    def pose_of(name):
        n = g['nodes'][node_index[name]]
        return {'position': [round(x, 4) for x in n.get('translation', [0, 0, 0])], 'rotation': [round(x, 5) for x in n.get('rotation', [0, 0, 0, 1])]}

    gl_lo, gl_hi = b2g(lo), b2g(hi)
    bounds = {'min': [round(gl_lo[0], 4), round(gl_lo[1], 4), round(gl_hi[2], 4)], 'max': [round(gl_hi[0], 4), round(gl_hi[1], 4), round(gl_lo[2], 4)]}
    manifest = dict(manifest)
    manifest['bounds'] = bounds
    # Resolve slot poses from the exported nodes ("@node" placeholders).
    def resolve(x):
        if isinstance(x, dict):
            if set(x) == {'pose@'}:
                return pose_of(x['pose@'])
            return {k: resolve(v) for k, v in x.items()}
        if isinstance(x, list):
            return [resolve(v) for v in x]
        return x
    manifest = resolve(manifest)
    (out / 'object.json').write_text(json.dumps(manifest, indent=1) + '\n')
    tris = triangles(visible)
    proxy_tris = triangles([proxy]) if proxy else 0
    report = {'id': manifest['id'], 'triangles': tris, 'proxyTriangles': proxy_tris, 'nodes': len(g['nodes']),
              'materials': len(g['materials']), 'variants': variants, 'bounds': bounds}
    (out / 'build-report.json').write_text(json.dumps(report, indent=1) + '\n')
    print('MACHINE', json.dumps(report))
    return g, manifest


def proxy_boxes(boxes, name='proxy'):
    """Collision proxy from (center, size) boxes; kept out of the drawn scene."""
    p = Part(name)
    MATS.setdefault('proxy', dict(color=(.5, .5, .5), rough=1))
    for c, s in boxes:
        p.box('proxy', c, s)
    return p.finish()


def spin(node_obj, axis_b, period, phase=0.0):
    """A 0.8 spin animation about the node's own origin (its pivot)."""
    ax = Vector(axis_b).normalized()
    return {'node': node_obj.name, 'type': 'spin', 'axis': b2g(ax), 'pivot': b2g(node_obj.matrix_world.translation), 'period': period, **({'phase': phase} if phase else {})}


def states_slot(slot_id, materials=None):
    materials = materials or [slot_id]
    pal = MATS[materials[0]]['palette']
    return {'id': slot_id, 'materials': materials,
            'palette': [{'id': s, 'colour': [round(c, 4) for c in col], 'emission': em} for s, col, em in PALETTES[pal]]}


def base_manifest(id_, name, description, tags, version='0.1.0'):
    return {
        'formatVersion': '0.10', 'id': id_, 'version': version, 'name': name, 'description': description,
        'category': 'machines', 'tags': tags, 'scene': 'object.gltf', 'license': 'CC-BY-4.0',
        'attribution': [{'path': '.', 'author': 'Hyprune contributors', 'license': 'CC-BY-4.0',
                         'source': 'https://github.com/hyprune/worlds'},
                        {'path': 'build.py', 'author': 'Hyprune contributors', 'license': 'MIT',
                         'source': 'https://github.com/hyprune/worlds'}],
        'thumbnail': 'thumbnail.png', 'lighting': {'mode': 'probe'},
    }


def out_dir(id_):
    return ROOT / 'dist/objects/machines' / id_
