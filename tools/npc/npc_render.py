# SPDX-License-Identifier: MIT
"""Blender (bake host only): turntable + walk-cycle check render of a canonical NPC .glb.

    blender --background --factory-startup --python tools/npc/npc_render.py -- IN.glb OUTDIR [--speed M/S]

Frames 1-90: idle on a turntable (the camera circles once). 91-210: walk seen from the
side over a checker floor that scrolls at the walk speed (extras.speed, else --speed, else
1.3 m/s): planted feet must move with the tiles, so foot sliding shows as feet drifting over
them. 211-270: the walk from the front three-quarter. 640x360 at 30 fps, EEVEE; PNG frames
in OUTDIR (tools/npc-import encodes them).
"""
import bpy, json, math, os, struct, sys
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = argv[0], argv[1]
SPEED = float(argv[argv.index('--speed') + 1]) if '--speed' in argv else None
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in scene.objects if o.type == 'ARMATURE')
meshes = [o for o in scene.objects if o.type == 'MESH']
# The walk speed the import step recorded (animation extras.speed), read from the GLB.
with open(SRC, 'rb') as f:
    data = f.read()
gltf = json.loads(data[20:20 + struct.unpack('<I', data[12:16])[0]])
speeds = {a.get('name'): a.get('extras', {}).get('speed') for a in gltf.get('animations', [])}
speed = SPEED or speeds.get('walk') or 1.3  # the import report's measurement wins
height = max((o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box)

actions = {a.name: a for a in bpy.data.actions}
def find(name):
    for key, a in actions.items():
        if key == name or key.startswith(name + '_') or key.endswith('|' + name) or key.split('_')[0] == name:
            return a
    return None
arm.animation_data_create()
arm.animation_data.action = None
for t in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(t)
track = arm.animation_data.nla_tracks.new()
def place(action, start, end):
    if not action:
        return
    length = max(1.0, action.frame_range[1] - action.frame_range[0])
    strip = track.strips.new(action.name, start, action)
    if getattr(action, 'slots', None) and len(action.slots) and hasattr(strip, 'action_slot'):
        strip.action_slot = action.slots[0]
    strip.repeat = (end - start) / length
place(find('idle'), 1, 90)
place(find('walk'), 91, 270)

# Floor: checker (0.5 m squares) scrolling backwards (+Y, the character faces -Y) at the walk speed.
bpy.ops.mesh.primitive_plane_add(size=40)
floor = bpy.context.object
mat = bpy.data.materials.new('floor'); mat.use_nodes = True
nt = mat.node_tree
coords, mapping, checker = nt.nodes.new('ShaderNodeTexCoord'), nt.nodes.new('ShaderNodeMapping'), nt.nodes.new('ShaderNodeTexChecker')
checker.inputs['Scale'].default_value = 1.0
checker.inputs['Color1'].default_value = (.75, .75, .72, 1); checker.inputs['Color2'].default_value = (.28, .3, .33, 1)
mapping.inputs['Scale'].default_value = (2, 2, 2)  # object metres x2 at checker scale 1: 0.5 m squares
nt.links.new(coords.outputs['Object'], mapping.inputs['Vector']); nt.links.new(mapping.outputs['Vector'], checker.inputs['Vector'])
nt.links.new(checker.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
floor.data.materials.append(mat)
loc = mapping.inputs['Location']
for frame, offset in ((91, 0.0), (270, -speed * (270 - 91) / 30 * 2)):  # x2: mapping scale
    loc.default_value = (0, offset, 0); loc.keyframe_insert('default_value', frame=frame)
for fc in (mat.node_tree.animation_data.action and [fc for fc in getattr(mat.node_tree.animation_data.action, 'fcurves', [])] or []):
    for k in fc.keyframe_points:
        k.interpolation = 'LINEAR'
try:  # Blender 4.4+ layered actions
    for layer in mat.node_tree.animation_data.action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for k in fc.keyframe_points:
                        k.interpolation = 'LINEAR'
except AttributeError:
    pass

# Light and world.
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); scene.collection.objects.link(sun)
sun.data.energy = 3.5; sun.rotation_euler = (math.radians(50), 0, math.radians(30))
scene.world = bpy.data.worlds.new('w'); scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.32, .36, .42, 1)

# Camera: turntable (1-90), side (91-210), front three-quarter (211-270).
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scene.collection.objects.link(cam); scene.camera = cam
cam.data.lens = 32
target = Vector((0, 0, height * .52))
def look(at_frame, eye):
    cam.location = eye
    d = target - eye
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam.keyframe_insert('location', frame=at_frame); cam.keyframe_insert('rotation_euler', frame=at_frame)
radius = height * 2.3
for i in range(0, 91, 5):
    a = 2 * math.pi * i / 90
    look(1 + i, Vector((math.sin(a) * radius, -math.cos(a) * radius, height * .62)))
look(91, Vector((radius * 1.05, 0, height * .5))); look(210, Vector((radius * 1.05, 0, height * .5)))
look(211, Vector((radius * .7, -radius * .8, height * .6))); look(270, Vector((radius * .7, -radius * .8, height * .6)))
for o in (cam,):
    ad = o.animation_data
    if ad and ad.action:
        try:
            curves = [fc for layer in ad.action.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
        except AttributeError:
            curves = list(ad.action.fcurves)
        for fc in curves:
            for k in fc.keyframe_points:
                k.interpolation = 'CONSTANT' if fc.data_path == 'rotation_euler' and False else 'LINEAR'

for engine in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
    try:
        scene.render.engine = engine; break
    except TypeError:
        continue
scene.render.resolution_x, scene.render.resolution_y = 640, 360
scene.frame_start, scene.frame_end = 1, 270
scene.render.filepath = os.path.join(OUT, 'f')
scene.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(animation=True)
print('NPC-RENDER', SRC, 'walk speed', speed, 'm/s', 'frames', OUT)
