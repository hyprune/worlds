# SPDX-License-Identifier: MIT
"""Catalog thumbnail of an object asset (RFC-0011: PNG, 256 x 256, sRGB, alpha).

    blender -b --factory-startup -P tools/object/thumbnail.py -- SCENE.glb OUT.png [--hide proxy] [--clip idle]

Blender runs on the bake host only (tools/object-import calls it there). SCENE must be
readable by Blender's importer: run tools/gltf/object-prep.mjs first for KTX2 textures.
A three-quarter front view from the left, 20 deg above, framed on the visible geometry,
over a transparent background with a soft key, fill and rim; Standard view transform.
Nodes outside the glTF scene (collision proxies) are never drawn; --hide removes more by
name. Characters show the first frame of --clip (default idle).
"""
import argparse, math, os, sys
if os.environ.get('HYPRUNE_REMOTE_BLENDER') != '1':
    raise SystemExit('Blender runs on the bake host only (HYPRUNE_REMOTE_BLENDER=1 there)')
import bpy
from mathutils import Vector

ap = argparse.ArgumentParser()
ap.add_argument('scene'); ap.add_argument('out')
ap.add_argument('--hide', action='append', default=[])
ap.add_argument('--clip', default='idle')
ap.add_argument('--size', type=int, default=256)
ap.add_argument('--samples', type=int, default=64)
a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.scene)
sc = bpy.context.scene
for o in list(sc.objects):
    if o.name in a.hide or o.name.split('.')[0] in a.hide:
        bpy.data.objects.remove(o, do_unlink=True)
for arm in [o for o in sc.objects if o.type == 'ARMATURE']:
    action = bpy.data.actions.get(a.clip)
    if action:
        arm.animation_data_create(); arm.animation_data.action = action
        if getattr(action, 'slots', None):
            arm.animation_data.action_slot = action.slots[0]
        sc.frame_set(int(action.frame_range[0]))
bpy.context.view_layer.update()

# Framing: the evaluated (posed, modified) visible meshes.
dg = bpy.context.evaluated_depsgraph_get()
points = []
shapes = {pb.custom_shape for arm in sc.objects if arm.type == 'ARMATURE' for pb in arm.pose.bones if pb.custom_shape}
for o in shapes:
    o.hide_render = True
for o in sc.objects:
    if o.type != 'MESH' or o.hide_render or o in shapes:
        continue
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    points += [ev.matrix_world @ v.co for v in me.vertices]
    ev.to_mesh_clear()
if not points:
    raise SystemExit('THUMBNAIL: nothing to render')
lo = Vector([min(p[i] for p in points) for i in range(3)]); hi = Vector([max(p[i] for p in points) for i in range(3)])
centre = (lo + hi) / 2
# Blender is Z up and glTF +Z (front) is Blender -Y: view from front-left, above.
yaw, pitch = math.radians(-35), math.radians(20)
direction = Vector((math.sin(yaw) * math.cos(pitch), -math.cos(yaw) * math.cos(pitch), math.sin(pitch)))
cam_data = bpy.data.cameras.new('thumb'); cam_data.lens = 50; cam_data.sensor_width = 36; cam_data.clip_end = 10000
cam = bpy.data.objects.new('thumb', cam_data); sc.collection.objects.link(cam); sc.camera = cam
cam.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()
# Distance so every point fits with a 6% margin (perspective, square frame).
half = math.atan(cam_data.sensor_width / 2 / cam_data.lens) * 0.94
right = (cam.rotation_euler.to_matrix() @ Vector((1, 0, 0))); up = (cam.rotation_euler.to_matrix() @ Vector((0, 1, 0)))
dist = 0
for p in points[::max(1, len(points) // 20000)]:
    d = p - centre
    depth = d.dot(direction)
    for side in (abs(d.dot(right)), abs(d.dot(up))):
        dist = max(dist, depth + side / math.tan(half))
cam.location = centre + direction * dist
cam_data.clip_start = max(0.001, dist / 1000)

for name, energy, rot, size in (('key', 3.2, (55, 0, -40), 4), ('fill', 1.0, (65, 0, 60), 10), ('rim', 2.0, (110, 0, 160), 3)):
    light = bpy.data.lights.new(name, 'SUN'); light.energy = energy; light.angle = math.radians(size)
    lo_ = bpy.data.objects.new(name, light); lo_.rotation_euler = tuple(math.radians(v) for v in rot); sc.collection.objects.link(lo_)
world = bpy.data.worlds.new('thumb'); sc.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.42, 0.45, 0.5, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8

for engine in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try:
        sc.render.engine = engine; break
    except TypeError:
        continue
for attr, val in (('taa_render_samples', a.samples), ('use_gtao', True), ('use_shadows', True)):
    if hasattr(sc.eevee, attr):
        setattr(sc.eevee, attr, val)
sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = a.size; sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
sc.render.image_settings.compression = 100
sc.view_settings.view_transform = 'Standard'
sc.render.filepath = a.out
bpy.ops.render.render(write_still=True)
print('THUMBNAIL', a.out, os.path.getsize(a.out))
