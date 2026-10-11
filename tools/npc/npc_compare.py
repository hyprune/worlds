# SPDX-License-Identifier: MIT
"""Blender (bake host only): side-by-side clip check of two canonical NPC .glbs.

    blender --background --factory-startup --python tools/npc/npc_compare.py -- \
        LEFT.glb RIGHT.glb OUTDIR --clips LEFTWALK,RIGHTWALK,LEFTRUN,RIGHTRUN \
        --speeds LW,RW,LR,RR --labels "left text" "right text"

Left and right figures each stand on their own checker strip (0.5 m squares) that scrolls
at that clip's planted-foot speed, so foot sliding shows as feet drifting over the tiles.
Frames 1-90 walk from the side (angled), 91-150 walk from the front, 151-240 run from the side,
241-300 run from the front. 960x540, 30 fps, EEVEE; PNG frames to OUTDIR.
"""
import bpy, math, os, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
LEFT, RIGHT, OUT = argv[0], argv[1], argv[2]
clips = argv[argv.index('--clips') + 1].split(',')
speeds = [float(x) for x in argv[argv.index('--speeds') + 1].split(',')]
i = argv.index('--labels'); labels = argv[i + 1:i + 3]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene; scene.render.fps = 30

def load(path, x, walk, run, ws, rs, label):
    before = set(bpy.data.objects); acts = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.parent is None:
            o.location.x += x
    arm = next(o for o in new if o.type == 'ARMATURE')
    mine = {a.name: a for a in bpy.data.actions if a not in acts}
    ad = arm.animation_data
    ad.action = None
    for t in list(ad.nla_tracks):
        ad.nla_tracks.remove(t)
    track = ad.nla_tracks.new()
    for name, start, end in ((walk, 1, 150), (run, 151, 300)):
        a = mine.get(name) or next(v for k, v in mine.items() if k.startswith(name))
        s = track.strips.new(name, start, a)
        if getattr(a, 'slots', None) and len(a.slots) and hasattr(s, 'action_slot'):
            s.action_slot = a.slots[0]
        s.repeat = (end - start + 1) / max(1.0, a.frame_range[1] - a.frame_range[0])
    # This figure's floor strip, scrolling back (+Y) at its own planted speed.
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x, 0, 0)); fl = bpy.context.object
    fl.scale = (1.1, 40, 1)
    m = bpy.data.materials.new('floor'); m.use_nodes = True; nt = m.node_tree
    tc, mp, ck = nt.nodes.new('ShaderNodeTexCoord'), nt.nodes.new('ShaderNodeMapping'), nt.nodes.new('ShaderNodeTexChecker')
    ck.inputs['Scale'].default_value = 1
    ck.inputs['Color1'].default_value = (.78, .78, .74, 1); ck.inputs['Color2'].default_value = (.25, .27, .3, 1)
    mp.inputs['Scale'].default_value = (2 * 1.1, 2 * 40, 2)  # the unit plane's object space is scaled: back to metres, 0.5 m squares
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], ck.inputs['Vector'])
    nt.links.new(ck.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
    fl.data.materials.append(m)
    loc = mp.inputs['Location']
    walk_end = -ws * 149 / 30 * 2
    for frame, off in ((1, 0.0), (150, walk_end), (151, walk_end), (300, walk_end - rs * 149 / 30 * 2)):
        loc.default_value = (0, off, 0); loc.keyframe_insert('default_value', frame=frame)
    try:
        curves = [fc for l in nt.animation_data.action.layers for st in l.strips for b in st.channelbags for fc in b.fcurves]
    except AttributeError:
        curves = list(nt.animation_data.action.fcurves)
    for fc in curves:
        for k in fc.keyframe_points:
            k.interpolation = 'LINEAR'
    bpy.ops.object.text_add(location=(x, .2, 2.05)); t = bpy.context.object
    t.data.body = label; t.data.align_x = 'CENTER'; t.data.size = .13; t.rotation_euler = (math.radians(90), 0, 0)
    return arm

load(LEFT, -1.0, clips[0], clips[2], speeds[0], speeds[2], labels[0])
load(RIGHT, 1.0, clips[1], clips[3], speeds[1], speeds[3], labels[1])
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); scene.collection.objects.link(sun)
sun.data.energy = 3.5; sun.rotation_euler = (math.radians(50), 0, math.radians(35))
scene.world = bpy.data.worlds.new('w'); scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.32, .36, .42, 1)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scene.collection.objects.link(cam); scene.camera = cam
cam.data.lens = 32
def view(frame, eye, at=Vector((0, 0, .9))):
    cam.location = eye; cam.rotation_euler = (at - eye).to_track_quat('-Z', 'Y').to_euler()
    cam.keyframe_insert('location', frame=frame); cam.keyframe_insert('rotation_euler', frame=frame)
side = Vector((4.9, -3.4, 1.05))  # mostly from the side, angled so neither figure hides the other
for a, b, eye in ((1, 90, side), (91, 150, Vector((0, -6.2, 1.2))), (151, 240, side), (241, 300, Vector((0, -6.2, 1.2)))):
    view(a, eye); view(b, eye)
try:
    curves = [fc for l in cam.animation_data.action.layers for st in l.strips for bb in st.channelbags for fc in bb.fcurves]
except AttributeError:
    curves = list(cam.animation_data.action.fcurves)
for fc in curves:
    for k in fc.keyframe_points:
        k.interpolation = 'CONSTANT'
for engine in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
    try:
        scene.render.engine = engine; break
    except TypeError:
        continue
scene.render.resolution_x, scene.render.resolution_y = 960, 540
scene.frame_start, scene.frame_end = 1, 300
scene.render.filepath = os.path.join(OUT, 'f'); scene.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(animation=True)
print('NPC-COMPARE', LEFT, RIGHT, OUT)
