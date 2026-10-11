# SPDX-License-Identifier: MIT
"""Normalise a glTF/GLB into an object asset (RFC-0011 asset conventions); tools/object-import step.

    blender -b --factory-startup -P tools/object/object_import.py -- --in SRC.glb --out OUT/object.gltf
        [--report R.json] [--units m|cm|mm] [--up y|z] [--forward +z|-z|+x|-x]
        [--surface floor|wall|ceiling|any|keep] [--max-tris N] [--max-texture PX]
        [--collision none|box|convex] [--keep NODE ...]

Blender runs on the bake host only. Steps: units to metres; +Y up and the front along +Z
(glTF); the origin where the object touches its support (floor: base centre, wall: back
centre, ceiling: top centre, any: bounds centre); decimation to the triangle budget
(collapse, per mesh in proportion; nodes named with --keep are left whole); textures
scaled to the size limit; an optional collision proxy `proxy` (the bounds box, or the
convex hull at most 2,000 triangles) kept outside the glTF scene so it is never drawn;
export as .gltf with external .bin and PNG/JPEG textures. Skinned characters are not
handled here: tools/object-import --character runs tools/npc-import.
"""
import argparse, json, math, os, sys
if os.environ.get('HYPRUNE_REMOTE_BLENDER') != '1':
    raise SystemExit('Blender runs on the bake host only (HYPRUNE_REMOTE_BLENDER=1 there)')
import bmesh, bpy
from mathutils import Matrix, Vector

ap = argparse.ArgumentParser()
ap.add_argument('--in', dest='src', required=True); ap.add_argument('--out', required=True); ap.add_argument('--report')
ap.add_argument('--units', choices=['m', 'cm', 'mm'], default='m'); ap.add_argument('--up', choices=['y', 'z'], default='y')
ap.add_argument('--forward', choices=['+z', '-z', '+x', '-x'], default='+z')
ap.add_argument('--surface', choices=['floor', 'wall', 'ceiling', 'any', 'keep'], default='floor')
ap.add_argument('--max-tris', type=int, default=50000); ap.add_argument('--max-texture', type=int, default=2048)
ap.add_argument('--collision', choices=['none', 'box', 'convex'], default='none'); ap.add_argument('--keep', action='append', default=[])
a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:])
report = {'source': os.path.basename(a.src), 'steps': [], 'warnings': []}
step = lambda text: (report['steps'].append(text), print('OBJECT-IMPORT', text))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.src)
sc = bpy.context.scene
objects = list(sc.objects)
if any(o.type == 'ARMATURE' for o in objects):
    raise SystemExit('OBJECT-IMPORT: the source is skinned; characters use tools/object-import --character (tools/npc-import)')
for o in objects:
    if o.animation_data:
        o.animation_data_clear()
if bpy.data.actions:
    report['warnings'].append(f'{len(bpy.data.actions)} glTF animations dropped: objects animate with traits.decorative')
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
# A source may carry its own proxy (an off-scene node named `proxy`): kept with --collision none,
# replaced otherwise; it never counts toward bounds or the triangle budget.
proxy = bpy.data.objects.get('proxy')
if proxy is not None and a.collision != 'none':
    bpy.data.objects.remove(proxy, do_unlink=True); objects = list(sc.objects); proxy = None
meshes = [o for o in objects if o.type == 'MESH' and o is not proxy]
if not meshes:
    raise SystemExit('OBJECT-IMPORT: no meshes')


def triangles(objs):
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs if o.type == 'MESH')


def world_points():
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); pts = []
    for o in meshes:
        ev = o.evaluated_get(dg); me = ev.to_mesh(); pts += [ev.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear()
    return pts


def bounds(pts):
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


# Blender is Z up and the importer already converts glTF +Y up; glTF +Z (front) is Blender -Y.
scale = {'m': 1, 'cm': 0.01, 'mm': 0.001}[a.units]
correction = Matrix.Scale(scale, 4)
if a.up == 'z':  # authored Z up and exported without axis conversion: it arrives lying down
    correction = Matrix.Rotation(math.radians(90), 4, 'X') @ correction
yaw = {'+z': 0, '-z': 180, '+x': 90, '-x': -90}[a.forward]  # turn the source's front onto glTF +Z (Blender -Y)
correction = Matrix.Rotation(math.radians(-yaw), 4, 'Z') @ correction
roots = [o for o in objects if o.parent is None]
for o in roots:
    o.matrix_world = correction @ o.matrix_world
lo, hi = bounds(world_points())
size = hi - lo
if max(size) > 50 or max(size) < 0.02:
    report['warnings'].append(f'size {[round(v, 3) for v in size]} m: check --units')
# Origin per support surface (Blender axes: glTF X = X, glTF Y = Z, glTF Z = -Y).
centre = (lo + hi) / 2
origin = {'floor': Vector((centre.x, centre.y, lo.z)), 'wall': Vector((centre.x, hi.y, centre.z)),
          'ceiling': Vector((centre.x, centre.y, hi.z)), 'any': centre, 'keep': Vector()}[a.surface]
for o in roots:
    o.matrix_world = Matrix.Translation(-origin) @ o.matrix_world
step(f'units {a.units}, up {a.up}, front {a.forward}, origin {a.surface}: size {[round(v, 3) for v in size]} m')

before = triangles(meshes)
report['trianglesIn'] = before
if before > a.max_tris:
    keep = set(a.keep)
    fixed = triangles([o for o in meshes if o.name in keep])
    ratio = max(0.01, (a.max_tris - fixed) / max(1, before - fixed)) * 0.98
    for o in meshes:
        if o.name in keep:
            continue
        m = o.modifiers.new('budget', 'DECIMATE'); m.decimate_type = 'COLLAPSE'; m.ratio = ratio; m.use_collapse_triangulate = True
    step(f'decimated {before} -> about {int(fixed + (before - fixed) * ratio)} triangles (ratio {ratio:.3f}, kept {sorted(keep)})')

resized = []
for image in bpy.data.images:
    w, h = image.size
    if max(w, h) > a.max_texture:
        f = a.max_texture / max(w, h); image.scale(max(1, int(w * f)), max(1, int(h * f))); resized.append(f'{image.name} {w}x{h}')
if resized:
    step(f'textures scaled to {a.max_texture} px: {", ".join(resized)}')

if a.collision != 'none':
    pts = world_points()
    bm = bmesh.new()
    if a.collision == 'box':
        lo, hi = bounds(pts)
        verts = [bm.verts.new(Vector((x, y, z))) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
        bmesh.ops.convex_hull(bm, input=verts)
    else:
        verts = [bm.verts.new(p) for p in pts[::max(1, len(pts) // 50000)]]
        bmesh.ops.convex_hull(bm, input=verts)
        for v in [v for v in bm.verts if not v.link_faces]:
            bm.verts.remove(v)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    data = bpy.data.meshes.new('proxy'); bm.to_mesh(data); bm.free()
    proxy = bpy.data.objects.new('proxy', data); sc.collection.objects.link(proxy)
    if len(data.polygons) > 2000:
        m = proxy.modifiers.new('budget', 'DECIMATE'); m.ratio = 1900 / len(data.polygons)
    step(f'collision proxy "proxy": {a.collision}')

os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=a.out, export_format='GLTF_SEPARATE', use_selection=True, export_yup=True, export_apply=True,
                          export_animations=False, export_cameras=False, export_lights=False, export_extras=False,
                          export_materials='EXPORT', export_image_format='AUTO')
g = json.loads(open(a.out).read())
if proxy is not None:
    index = next(i for i, n in enumerate(g['nodes']) if n.get('name') == 'proxy')
    for s in g.get('scenes', []):
        s['nodes'] = [n for n in s['nodes'] if n != index]
    g.setdefault('materials', [])
open(a.out, 'w').write(json.dumps(g, indent=1) + '\n')
names = [n.get('name') for n in g['nodes']]
renamed = [n for n in names if n and n[-4:-3] == '.' and n[-3:].isdigit()]
if renamed:
    report['warnings'].append(f'duplicate names were suffixed by Blender: {renamed}')
report.update({'trianglesOut': triangles([o for o in bpy.context.evaluated_depsgraph_get().objects if o.type == 'MESH' and o.name != 'proxy']),
               'nodes': names, 'materials': [m.get('name') for m in g.get('materials', [])]})
if a.report:
    open(a.report, 'w').write(json.dumps(report, indent=1) + '\n')
step(f'exported {a.out}')
