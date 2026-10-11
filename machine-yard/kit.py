# SPDX-License-Identifier: MIT
"""Machine Yard authoring kit: primitives in glTF coordinates, materials from specs,
glTF post-processing. Imported by build.py and effects.py inside Blender.

All positions and sizes here are glTF asset/world space: metres, +Y up, front +Z.
The kit converts to Blender (Z up) internally:
bl((x, y, z)) = (x, -z, y); the exporter's +Y-up conversion maps it back.
"""
import json, math, shutil
from pathlib import Path
import bpy, bmesh
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
TILES = ROOT / 'lumen-reach/materials/tiles'

# Linear accent colours (the Lumen Reach practical-light palette).
CYAN = (.11, .48, .68)
MINT = (.16, .72, .45)
AMBER = (1.0, .42, .085)
RED = (.9, .06, .02)
WARM_GREY = (.30, .27, .23)
SLATE = (.10, .12, .14)
IVORY = (.70, .66, .54)

# Material specs: colour (linear factor, multiplies the tile texture), roughness,
# metallic, tex (Lumen Reach tile name) + tile (metres per repeat), emit (strength),
# unlit, normal (use the tile's normal map).
MATS = {
    'timber':      dict(color=(1.0, .9, .8), rough=.55, tex='wood', tile=1.2),
    'timber-dark': dict(color=(.55, .45, .38), rough=.6, tex='wood', tile=1.2),
    'stone':       dict(color=(1.0, .97, .92), rough=.82, tex='concrete', tile=2.0),
    'stone-warm':  dict(color=(1.0, .9, .78), rough=.85, tex='concrete', tile=2.5),
    'paving':      dict(color=(.95, .92, .88), rough=.8, tex='paving', tile=2.0),
    'metal':       dict(color=(.85, .88, .9), rough=.42, metal=.6, tex='metal', tile=1.0),
    'metal-black': dict(color=(.035, .04, .045), rough=.38, metal=.7),
    'brass':       dict(color=(.62, .43, .19), rough=.32, metal=.85),
    'rubber':      dict(color=(.02, .022, .025), rough=.85),
    'panel':       dict(color=(.008, .012, .018), rough=.25, metal=.2),
    'paint-amber': dict(color=(.75, .38, .06), rough=.5),
    'soil':        dict(color=(.03, .022, .015), rough=.95),
    'leaf':        dict(color=(.07, .2, .09), rough=.7),
    'leaf-light':  dict(color=(.16, .32, .1), rough=.7),
    'strip-cyan':  dict(color=CYAN, emit=2.0),
    'strip-amber': dict(color=AMBER, emit=1.6),
    'strip-mint':  dict(color=MINT, emit=1.6),
    'sconce':      dict(color=(1.0, .78, .5), emit=3.0),
    'proxy':       dict(color=(.5, .5, .5), rough=1),
}

_bmats = {}
_images = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _bmats.clear(); _images.clear()


def bl(p):
    """glTF (x, y up, z front) -> Blender (x, y, z up)."""
    return Vector((p[0], -p[2], p[1]))


def gl(v):
    return [round(v[0], 5), round(v[2], 5), round(-v[1], 5)]


def _image(name):
    if name not in _images:
        _images[name] = bpy.data.images.load(str(TILES / f'{name}.png'), check_existing=True)
    return _images[name]


def bmat(name, base=None):
    """Blender material `name` from MATS[base or name] (Cycles look; the glTF material is
    rewritten from the same spec after export)."""
    if name in _bmats:
        return _bmats[name]
    spec = MATS[base or name]
    MATS.setdefault(name, spec)
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; p = nt.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*spec['color'], 1)
    p.inputs['Roughness'].default_value = spec.get('rough', .5); p.inputs['Metallic'].default_value = spec.get('metal', 0)
    if spec.get('tex'):
        uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = 'UV0'
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = _image(spec['tex'] + '-albedo')
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1
        mix.inputs[7].default_value = (*spec['color'], 1)
        nt.links.new(uv.outputs['UV'], t.inputs['Vector']); nt.links.new(t.outputs['Color'], mix.inputs[6])
        nt.links.new(mix.outputs[2], p.inputs['Base Color'])
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = _image(spec['tex'] + '-normal'); n.image.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = .4
        nt.links.new(uv.outputs['UV'], n.inputs['Vector']); nt.links.new(n.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], p.inputs['Normal'])
    if spec.get('emit') or spec.get('unlit'):
        p.inputs['Emission Color'].default_value = (*spec['color'], 1); p.inputs['Emission Strength'].default_value = spec.get('emit', 1)
    if spec.get('unlit'):
        out = nt.nodes.get('Material Output'); e = nt.nodes.new('ShaderNodeEmission')
        e.inputs['Color'].default_value = (*spec['color'], 1); e.inputs['Strength'].default_value = 1
        nt.links.new(e.outputs[0], out.inputs['Surface'])
    _bmats[name] = m
    return m


class Part:
    """One mesh node assembled from primitives given in glTF space. `pivot` (glTF) is the
    node origin; the mesh is stored relative to it. `prefix` names material copies
    (`<prefix>--<mat>`), used by world groups so each owns its lightmap."""

    def __init__(self, name, pivot=(0, 0, 0), prefix=None):
        self.name, self.pivot, self.prefix = name, bl(pivot), prefix
        self.bm = bmesh.new(); self.uv = self.bm.loops.layers.uv.new('UV0'); self.mats = []

    def _mi(self, mat):
        name = f'{self.prefix}--{mat}' if self.prefix else mat
        if name not in self.mats:
            self.mats.append(name); bmat(name, mat)
        return self.mats.index(name)

    def _take(self, src, mat, matrix=None):
        if matrix is not None:
            bmesh.ops.transform(src, matrix=matrix, verts=src.verts)
        src.normal_update()  # faces built by hand have no normal yet (UV0 picks its plane from it)
        mi = self._mi(mat); tile = MATS[mat].get('tile', 1.0)
        vmap = {v: self.bm.verts.new(v.co) for v in src.verts}
        for f in src.faces:
            try:
                nf = self.bm.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            nf.material_index = mi; nf.smooth = f.smooth
            n = f.normal; ax = max(range(3), key=lambda i: abs(n[i])); u_i, v_i = [i for i in range(3) if i != ax]
            for loop in nf.loops:
                co = loop.vert.co
                loop[self.uv].uv = (co[u_i] / tile, co[v_i] / tile)
        src.free()
        return self

    def box(self, mat, center, size, bevel=0.0, yaw=0.0):
        b = bmesh.new(); bmesh.ops.create_cube(b, size=1.0)
        bmesh.ops.scale(b, vec=Vector((size[0], size[2], size[1])), verts=b.verts)
        if bevel:
            bmesh.ops.bevel(b, geom=list(b.edges), offset=min(bevel, min(size) * .45), segments=2, profile=.5, affect='EDGES')
        m = Matrix.Translation(bl(center)) @ Matrix.Rotation(yaw, 4, 'Z')
        return self._take(b, mat, m)

    def cyl(self, mat, a, b, r, seg=16, r2=None, smooth=True):
        a, b = bl(a), bl(b); d = b - a
        c = bmesh.new()
        bmesh.ops.create_cone(c, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=d.length)
        if smooth:
            for f in c.faces:
                f.smooth = len(f.verts) == 4
        m = Matrix.Translation((a + b) / 2) @ d.normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()
        return self._take(c, mat, m)

    def torus(self, mat, center, R, r, axis=(0, 1, 0), seg=32, sseg=8, arc=(0, 1)):
        """A torus (or an arc of one, fractions of a turn) around `axis` (glTF)."""
        b = bmesh.new(); rings = []
        closed = arc == (0, 1); n = seg if closed else seg + 1
        for i in range(n):
            t = 2 * math.pi * (arc[0] + (arc[1] - arc[0]) * i / seg)
            ring = []
            for j in range(sseg):
                c = 2 * math.pi * j / sseg; rr = R + r * math.cos(c)
                ring.append(b.verts.new((rr * math.cos(t), rr * math.sin(t), r * math.sin(c))))
            rings.append(ring)
        for i in range(seg):
            for j in range(sseg):
                f = b.faces.new([rings[i][j], rings[(i + 1) % n][j], rings[(i + 1) % n][(j + 1) % sseg], rings[i][(j + 1) % sseg]]); f.smooth = True
        if not closed:
            b.faces.new(list(reversed(rings[0]))); b.faces.new(rings[-1])
        bmesh.ops.recalc_face_normals(b, faces=b.faces)
        m = Matrix.Translation(bl(center)) @ bl(axis).normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()
        return self._take(b, mat, m)

    def hull(self, mat, points):
        b = bmesh.new(); vs = [b.verts.new(bl(p)) for p in points]
        r = bmesh.ops.convex_hull(b, input=vs)
        bmesh.ops.delete(b, geom=[g for g in r.get('geom_interior', []) + r.get('geom_unused', []) if isinstance(g, bmesh.types.BMVert)], context='VERTS')
        bmesh.ops.dissolve_limit(b, angle_limit=.001, verts=b.verts, edges=b.edges)
        bmesh.ops.recalc_face_normals(b, faces=b.faces)
        return self._take(b, mat)

    def sphere(self, mat, center, r, sub=2):
        b = bmesh.new(); bmesh.ops.create_icosphere(b, subdivisions=sub, radius=r)
        for f in b.faces:
            f.smooth = True
        return self._take(b, mat, Matrix.Translation(bl(center)))

    def quad(self, mat, center, w, h, normal=(0, 0, 1)):
        """A w x h rectangle facing `normal` (glTF; +Z by default, or +-X)."""
        b = bmesh.new(); n = Vector(normal)
        if abs(n.z) > .5:
            right, up = Vector((n.z, 0, 0)), Vector((0, 1, 0))
        elif abs(n.x) > .5:
            right, up = Vector((0, 0, -n.x)), Vector((0, 1, 0))
        else:
            right, up = Vector((1, 0, 0)), Vector((0, 0, -n.y))
        c = Vector(center)
        corners = [c - right * w / 2 - up * h / 2, c + right * w / 2 - up * h / 2, c + right * w / 2 + up * h / 2, c - right * w / 2 + up * h / 2]
        b.faces.new([b.verts.new(bl(p)) for p in corners])
        return self._take(b, mat)

    def finish(self, parent=None, smooth_angle=35):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-5)
        bmesh.ops.translate(self.bm, vec=-self.pivot, verts=self.bm.verts)
        me = bpy.data.meshes.new(self.name); self.bm.to_mesh(me); self.bm.free()
        for name in self.mats:
            me.materials.append(_bmats[name])
        if smooth_angle:
            me.set_sharp_from_angle(angle=math.radians(smooth_angle))
        o = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(o)
        place(o, self.pivot, parent)
        return o


def place(o, world_blender, parent=None):
    if parent is not None:
        o.parent = parent
        o.location = world_blender - parent.matrix_world.translation
    else:
        o.location = world_blender
    bpy.context.view_layer.update()
    return o


def empty(name, pos, parent=None):
    o = bpy.data.objects.new(name, None); o.empty_display_size = .1
    bpy.context.scene.collection.objects.link(o)
    return place(o, bl(pos), parent)


def world_pos(o):
    return gl(o.matrix_world.translation)


def gltf_material(name, spec, textures):
    """glTF material from a spec; `textures` maps a tile name -> (albedo index, normal index)."""
    pbr = {'baseColorFactor': [*[round(c, 4) for c in spec['color']], 1],
           'metallicFactor': spec.get('metal', 0), 'roughnessFactor': spec.get('rough', .5)}
    m = {'name': name, 'pbrMetallicRoughness': pbr}
    if spec.get('tex'):
        albedo, normal = textures[spec['tex']]
        pbr['baseColorTexture'] = {'index': albedo}
        m['normalTexture'] = {'index': normal, 'scale': .4}
    e = spec.get('emit', 0)
    if e and not spec.get('unlit'):
        m['emissiveFactor'] = [round(c, 4) for c in spec['color']]
        if e != 1:
            m['extensions'] = {'KHR_materials_emissive_strength': {'emissiveStrength': round(e, 3)}}
    if spec.get('unlit'):
        pbr['metallicFactor'], pbr['roughnessFactor'] = 0, 1
        m['extensions'] = {'KHR_materials_unlit': {}}
    return m


def export_gltf(path, objects, texture_dir='textures'):
    """Export `objects` (and their children) to path (.gltf + .bin), then rewrite every
    material from its spec, with the Lumen Reach tiles copied to path.parent/texture_dir.
    Returns the glTF dict (written)."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLTF_SEPARATE', use_selection=True, export_yup=True,
                              export_apply=True, export_animations=False, export_cameras=False, export_lights=False,
                              export_extras=False, export_materials='EXPORT', export_image_format='NONE')
    g = json.loads(path.read_text())
    for k in ('images', 'textures', 'samplers'):
        g.pop(k, None)
    tiles = sorted({MATS[m['name']]['tex'] for m in g.get('materials', []) if MATS[m['name']].get('tex')})
    textures = {}
    if tiles:
        g['samplers'] = [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}]
        g['images'], g['textures'] = [], []
        (path.parent / texture_dir).mkdir(exist_ok=True)
        for t in tiles:
            idx = []
            for kind in ('albedo', 'normal'):
                shutil.copy2(TILES / f'{t}-{kind}.png', path.parent / texture_dir / f'{t}-{kind}.png')
                g['images'].append({'uri': f'{texture_dir}/{t}-{kind}.png', 'mimeType': 'image/png'})
                g['textures'].append({'source': len(g['images']) - 1, 'sampler': 0}); idx.append(len(g['textures']) - 1)
            textures[t] = tuple(idx)
    ext = set()
    for i, m in enumerate(g.get('materials', [])):
        g['materials'][i] = gltf_material(m['name'], MATS[m['name']], textures)
        ext |= set(g['materials'][i].get('extensions', {}))
    g['extensionsUsed'] = sorted(ext)
    if not g['extensionsUsed']:
        g.pop('extensionsUsed')
    g.pop('extensionsRequired', None)
    g['asset']['copyright'] = 'Hyprune contributors, CC-BY-4.0'
    path.write_text(json.dumps(g, indent=1) + '\n')
    return g


def mesh_bounds(objects):
    pts = [o.matrix_world @ v.co for o in objects if o.type == 'MESH' for v in o.data.vertices]
    lo = [min(p[i] for p in pts) for i in range(3)]; hi = [max(p[i] for p in pts) for i in range(3)]
    # Blender -> glTF AABB
    return {'min': [round(lo[0], 4), round(lo[2], 4), round(-hi[1], 4)], 'max': [round(hi[0], 4), round(hi[2], 4), round(-lo[1], 4)]}


def triangles(objects):
    return sum(len(p.vertices) - 2 for o in objects if o.type == 'MESH' for p in o.data.polygons)
