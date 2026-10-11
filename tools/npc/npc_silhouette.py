# SPDX-License-Identifier: MIT
"""Blender (bake host only): silhouette check of a decimated NPC against its source.

    blender --background --factory-startup --python tools/npc/npc_silhouette.py -- SOURCE.glb OUTPUT.glb OUT.json [OUT.png]

Both in their rest pose, orthographic masks from front, side, back and three-quarter
(512 px); IoU per view. A decimation that keeps the silhouette scores above ~0.97.
"""
import bpy, json, math, os, sys
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
SRC, DST, OUT = argv[0], argv[1], argv[2]
PNG = argv[3] if len(argv) > 3 else None
def masks(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=path)
    for o in sc.objects:
        if o.type == 'ARMATURE':
            o.data.pose_position = 'REST'
    mats = bpy.data.materials.new('flat'); mats.use_nodes = True
    for o in sc.objects:
        if o.type == 'MESH':
            o.data.materials.clear(); o.data.materials.append(mats)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in sc.objects if o.type == 'MESH' for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    centre, h = (lo + hi) / 2, hi.z - lo.z  # each on its own bounds: normalisation moves the feet to the origin
    cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.0  # fixed: same pixels per metre for both
    sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = 512
    out = []
    for yaw in (0, 90, 180, 45):
        a = math.radians(yaw)
        cam.location = centre + Vector((math.sin(a) * 6, -math.cos(a) * 6, 0))
        cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()
        f = f'/tmp/sil-{os.getpid()}-{yaw}.png'
        sc.render.filepath = f; bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(f); px = np.array(img.pixels[:]).reshape(512, 512, 4)[:, :, 3] > .5
        out.append(px); os.remove(f)
    return out
a, b = masks(SRC), masks(DST)
def align(x, y):  # shape, not placement: move y's centroid onto x's
    cx, cy = np.argwhere(x).mean(0), np.argwhere(y).mean(0)
    dy, dx = np.round(cx - cy).astype(int)
    return np.roll(np.roll(y, dy, 0), dx, 1)
b = [align(x, y) for x, y in zip(a, b)]
iou = [float((x & y).sum() / max(1, (x | y).sum())) for x, y in zip(a, b)]
result = {'source': os.path.basename(SRC), 'output': os.path.basename(DST), 'iou': [round(v, 4) for v in iou], 'worst': round(min(iou), 4)}
json.dump(result, open(OUT, 'w'), indent=2)
if PNG:  # both outlines: grey = both, red = only source, cyan = only decimated
    rows = []
    for x, y in zip(a, b):
        img = np.zeros((512, 512, 3)); img[x & y] = (.6, .6, .6); img[x & ~y] = (1, .2, .2); img[~x & y] = (.2, .9, 1)
        rows.append(img[::-1])
    strip = np.concatenate(rows, axis=1)
    im = bpy.data.images.new('sil', strip.shape[1], strip.shape[0])
    im.pixels = np.concatenate([strip[::-1], np.ones(strip.shape[:2] + (1,))], axis=2).ravel().tolist()
    im.filepath_raw = PNG; im.file_format = 'PNG'; im.save()
print('NPC-SILHOUETTE', json.dumps(result))
